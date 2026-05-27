"""CSV intake API router.

POST /intake/upload/{table}
  Accepts a CSV file upload, validates required columns, loads into a
  staging table (stg_*), and returns row counts + validation errors.

POST /intake/clear/{table}
  Truncates a staging table (for re-upload during pilot onboarding).

GET /intake/status
  Returns row counts across all 5 staging tables.

Security: table parameter is validated against the staging allowlist.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status

from api.dependencies import get_conn
from ingestion.csv_ingestor import COLUMN_MAPS, ingest_csv

router = APIRouter(prefix="/intake", tags=["intake"])

# ── Staging table allowlist ───────────────────────────────────────────────────

STAGING_TABLES: dict[str, dict[str, Any]] = {
    "stg_products": {
        "required_cols": {"product_name"},
        "date_cols": [],
        "description": "Product catalog",
    },
    "stg_supplier_deliveries": {
        "required_cols": {"product_name", "delivery_date"},
        "date_cols": ["delivery_date"],
        "description": "Supplier delivery history",
    },
    "stg_inventory_lots": {
        "required_cols": {"product_name", "quantity_on_hand"},
        "date_cols": ["arrival_date", "expiration_date"],
        "description": "Inventory lots",
    },
    "stg_buyer_orders": {
        "required_cols": {"product_name", "requested_quantity"},
        "date_cols": ["order_date", "delivery_date"],
        "description": "Buyer orders",
    },
    "stg_waste_adjustments": {
        "required_cols": {"product_name", "quantity_lost"},
        "date_cols": ["date"],
        "description": "Waste / spoilage adjustments",
    },
}


def _validate_staging_table(table: str) -> dict[str, Any]:
    if table not in STAGING_TABLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unknown staging table {table!r}. "
                f"Valid options: {sorted(STAGING_TABLES)}"
            ),
        )
    return STAGING_TABLES[table]


def _check_required_columns(
    df_columns: list[str],
    required: set[str],
    column_map: dict[str, str],
) -> list[str]:
    """Return list of required column names missing from the CSV.

    Checks both raw column names and their mapped equivalents.
    """
    # Build inverse map: schema_name → possible CSV names
    mapped_targets = set(column_map.values())
    raw_lower = {c.lower().strip() for c in df_columns}

    missing = []
    for req in required:
        # Accept if present as schema column name (post-mapping)
        if req in raw_lower:
            continue
        # Accept if any CSV header maps to this schema column
        found = any(
            column_map.get(c, "").lower() == req.lower()
            or c.lower().strip() == req.lower()
            for c in df_columns
        )
        if not found:
            missing.append(req)
    return missing


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/upload/{table}")
async def upload_csv(
    table: str,
    file: UploadFile = File(...),
    conn=Depends(get_conn),
):
    """Upload a CSV file into a staging table.

    Returns:
        table          target table name
        rows_inserted  number of rows loaded
        warnings       list of non-blocking issues
        errors         list of blocking issues (empty on success)
    """
    meta = _validate_staging_table(table)

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a .csv",
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    warnings: list[str] = []
    errors: list[str] = []

    # Write to temp file (ingest_csv requires a path)
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp.write(contents)
        tmp_path = Path(tmp.name)

    try:
        import pandas as pd

        # Peek at headers for column validation
        try:
            preview = pd.read_csv(tmp_path, nrows=0)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not parse CSV: {e}",
            )

        raw_cols = list(preview.columns)
        col_map = COLUMN_MAPS.get(table, {})

        missing_required = _check_required_columns(
            raw_cols, meta["required_cols"], col_map
        )
        if missing_required:
            errors.append(
                f"Missing required columns: {missing_required}. "
                f"Got: {raw_cols}"
            )
            return {
                "table": table,
                "rows_inserted": 0,
                "warnings": warnings,
                "errors": errors,
            }

        # Per-column quick checks
        full_df = pd.read_csv(tmp_path)
        n_rows = len(full_df)

        # Apply column map for checks
        mapped_df = full_df.rename(columns=col_map)

        # Check for all-null required columns after mapping
        for req in meta["required_cols"]:
            if req in mapped_df.columns:
                null_count = int(mapped_df[req].isna().sum())
                if null_count > 0:
                    pct = round(null_count / n_rows * 100, 1)
                    warnings.append(
                        f"Column '{req}': {null_count} missing values ({pct}%)"
                    )

        # Check date columns for parse failures
        for dcol in meta["date_cols"]:
            if dcol in mapped_df.columns:
                try:
                    parsed = pd.to_datetime(mapped_df[dcol], errors="coerce")
                    bad = int(parsed.isna().sum())
                    if bad > 0:
                        warnings.append(
                            f"Date column '{dcol}': {bad} rows could not be parsed"
                        )
                except Exception:
                    pass

        # Check for negative quantities
        qty_cols = [
            c for c in mapped_df.columns
            if any(k in c for k in ("quantity", "qty", "value", "price", "cost"))
        ]
        for qcol in qty_cols:
            try:
                neg = int((pd.to_numeric(mapped_df[qcol], errors="coerce") < 0).sum())
                if neg > 0:
                    warnings.append(
                        f"Column '{qcol}': {neg} negative values found"
                    )
            except Exception:
                pass

        # Ingest
        rows_inserted = ingest_csv(
            path=tmp_path,
            table=table,
            conn=conn,
            column_map=col_map,
            date_cols=meta["date_cols"],
            if_exists="append",  # staging tables have no PK; clear via /intake/clear
        )

        return {
            "table": table,
            "description": meta["description"],
            "rows_inserted": rows_inserted,
            "warnings": warnings,
            "errors": errors,
        }

    finally:
        tmp_path.unlink(missing_ok=True)


@router.post("/load-sample-data", status_code=status.HTTP_200_OK)
def load_sample_data(conn=Depends(get_conn)):
    """Load bundled sample CSVs into all staging tables.

    Clears any existing staging data and reloads the 5 sample CSVs from
    ``data/samples/``.  Designed for demo onboarding — idempotent and
    repeatable.  Returns per-table row counts.

    Security: file paths are resolved relative to a known project directory;
    no user-controlled input touches the file system.
    """
    samples_dir = Path(__file__).resolve().parents[2] / "data" / "samples"
    if not samples_dir.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Sample data directory not found at {samples_dir}. "
                "Ensure the repository includes data/samples/."
            ),
        )

    rows_by_table: dict[str, int] = {}
    errors: list[str] = []

    for table, meta in STAGING_TABLES.items():
        csv_path = samples_dir / f"{table}.csv"
        if not csv_path.exists():
            errors.append(f"Sample file not found: {csv_path.name}")
            rows_by_table[table] = 0
            continue
        try:
            col_map = COLUMN_MAPS.get(table, {})
            n = ingest_csv(
                path=csv_path,
                table=table,
                conn=conn,
                column_map=col_map,
                date_cols=meta["date_cols"],
                if_exists="replace",  # clear + reload for repeatable demo
            )
            rows_by_table[table] = n
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{table}: {exc}")
            rows_by_table[table] = 0

    total_rows = sum(rows_by_table.values())
    tables_loaded = sum(1 for n in rows_by_table.values() if n > 0)

    return {
        "status": "loaded" if not errors else "partial",
        "tables_loaded": tables_loaded,
        "rows_by_table": rows_by_table,
        "total_rows": total_rows,
        "errors": errors,
    }


@router.post("/clear/{table}", status_code=status.HTTP_200_OK)
def clear_staging_table(table: str, conn=Depends(get_conn)):
    """Truncate a staging table to allow clean re-upload."""
    _validate_staging_table(table)
    conn.execute(f"DELETE FROM {table}")  # noqa: S608  table is allowlisted
    return {"table": table, "status": "cleared"}


@router.get("/status")
def intake_status(conn=Depends(get_conn)):
    """Row counts across all staging tables."""
    result: dict[str, Any] = {}
    for table, meta in STAGING_TABLES.items():
        try:
            row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # noqa: S608
            count = int(row[0]) if row else 0
        except Exception:
            count = 0
        result[table] = {
            "description": meta["description"],
            "row_count": count,
            "loaded": count > 0,
        }
    any_loaded = any(v["loaded"] for v in result.values())
    all_loaded = all(v["loaded"] for v in result.values())
    return {
        "tables": result,
        "any_data_loaded": any_loaded,
        "all_tables_loaded": all_loaded,
    }
