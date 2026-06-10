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
    operator_id: str | None = None,
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

    # Operator-scoped path: copy the raw original into the vault FIRST
    # (write-once ground truth), then process against the vault DB.
    vault_dbm = None
    upload_session_id = None
    if operator_id is not None:
        import uuid as _uuid
        from infrastructure.db_manager import DBManager
        from infrastructure.operator_registry import (
            OperatorNotFoundError, OperatorRegistry,
        )
        from infrastructure.vault_storage import store_raw_upload
        try:
            registry = OperatorRegistry()
            store_raw_upload(registry, operator_id,
                             file.filename or "upload.csv", contents)
            vault_dbm = DBManager(registry)
            conn = vault_dbm.get_operator_connection(operator_id)
        except (OperatorNotFoundError, FileNotFoundError):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Unknown operator {operator_id!r}")
        upload_session_id = f"upl-{_uuid.uuid4().hex[:10]}"

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

        # Hard validation: negatives, reversed dates, unparseable required
        # dates → reject the file with named violations; magnitude / unit
        # issues → load but surface as warnings.
        from ingestion.validators import validate_staging_df

        validation = validate_staging_df(table, mapped_df)
        warnings.extend(validation.warnings)
        if not validation.ok:
            errors.extend(validation.errors)
            return {
                "table": table,
                "description": meta["description"],
                "rows_inserted": 0,
                "warnings": warnings,
                "errors": errors,
            }

        # Ingest. On the operator-scoped path every row is stamped with
        # lineage and REJECTED if provenance is incomplete; the legacy
        # single-operator path is unchanged.
        if operator_id is not None:
            from infrastructure.lineage import (
                assert_lineage_present, stamp_lineage,
            )
            from ingestion.column_mapper import insert_from_df

            ins_df = mapped_df.dropna(axis=1, how="all")
            for dcol in meta["date_cols"]:
                if dcol in ins_df.columns:
                    ins_df[dcol] = pd.to_datetime(
                        ins_df[dcol], errors="coerce").dt.date
            ins_df = stamp_lineage(
                ins_df, operator_id=operator_id,
                upload_session_id=upload_session_id,
                source_file=file.filename or "upload.csv")
            assert_lineage_present(ins_df)
            rows_inserted = insert_from_df(conn, table, ins_df,
                                           on_conflict="none")
        else:
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
        if vault_dbm is not None:
            vault_dbm.close_all()


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


# ── LLM extraction endpoints (smart upload) ───────────────────────────────────

@router.post("/extract")
async def extract_files(
    files: list[UploadFile] = File(...),
    operator_id: str | None = None,
    conn=Depends(get_conn),
):
    """Smart upload: any-format files → ExtractionResult for confirmation.

    Nothing is inserted here. The result (mock or real per USE_REAL_LLM)
    goes to the confirmation UI; rows reach staging only via
    POST /intake/confirm after operator review.
    """
    import tempfile
    from pathlib import Path as _P

    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="No files uploaded")

    registry = None
    if operator_id is not None:
        from infrastructure.operator_registry import (
            OperatorNotFoundError, OperatorRegistry,
        )
        try:
            registry = OperatorRegistry()
            registry.get_operator(operator_id)
        except OperatorNotFoundError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Unknown operator {operator_id!r}")

    tmp_paths: list[_P] = []
    try:
        for f in files:
            content = await f.read()
            if registry is not None:
                from infrastructure.vault_storage import store_raw_upload
                store_raw_upload(registry, operator_id,
                                 f.filename or "upload.bin", content)
            suffix = _P(f.filename or "upload.csv").suffix or ".csv"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(content)
                tmp_paths.append(_P(tmp.name))

        from ingestion.llm_extractor import extract as llm_extract
        try:
            result = llm_extract(tmp_paths)
        except ValueError as e:   # unsupported file type etc.
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e))
        payload = result.model_dump()
        # original filenames, not temp names, for the UI
        payload["source_files"] = [f.filename for f in files]
        payload["operator_id"] = operator_id
        return payload
    finally:
        for p in tmp_paths:
            p.unlink(missing_ok=True)


@router.get("/session/{session_id}")
def get_extraction_session(session_id: str):
    """Fetch a logged extraction session for the confirmation UI."""
    from ingestion.extraction_sessions import load_session

    data = load_session(session_id)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"No session {session_id!r}")
    return data


@router.post("/confirm")
def confirm_extraction(body: dict, conn=Depends(get_conn)):
    """Operator-confirmed rows → Layer-1 validation → staging insert.

    Body: {session_id, rows: [{row_index, table, fields, accepted}],
           corrections: [...], actioned_flag_indices: [...]}

    Enforcement: every row the extraction flagged requires_confirmation
    must appear in actioned_flag_indices (accepted, edited, or excluded
    by the operator) — unactioned flags block the confirm. Confirmed rows
    still pass the existing hard validators; a validation error returns
    422 and inserts nothing.
    """
    import pandas as pd

    from ingestion.extraction_sessions import load_session, log_confirmation
    from ingestion.validators import validate_staging_df

    session_id = body.get("session_id")
    rows = body.get("rows", [])
    corrections = body.get("corrections", [])
    actioned = set(body.get("actioned_flag_indices", []))

    session = load_session(session_id) if session_id else None
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"No session {session_id!r}")

    flagged = {r["row_index"] for r in session.get("extracted_rows", [])
               if r.get("requires_confirmation") and not r.get("rejected")}
    unactioned = flagged - actioned
    if unactioned:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{len(unactioned)} flagged row(s) not actioned "
                   f"(indices {sorted(unactioned)[:10]}). Every flag must "
                   f"be accepted, edited, or excluded before confirming.")

    accepted_rows = [r for r in rows if r.get("accepted", True)]
    by_table: dict[str, list[dict]] = {}
    for r in accepted_rows:
        fields = {k: v for k, v in r.get("fields", {}).items()
                  if not k.startswith("_")}
        by_table.setdefault(r["table"], []).append(fields)

    # Layer-1 hard validation per table — the LLM never bypasses it
    errors: list[str] = []
    frames: dict[str, pd.DataFrame] = {}
    for table, recs in by_table.items():
        df = pd.DataFrame(recs).dropna(axis=1, how="all")
        v = validate_staging_df(table, df)
        if not v.ok:
            errors.extend(f"{table}: {e}" for e in v.errors)
        frames[table] = df
    if errors:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"validation_errors": errors})

    from ingestion.column_mapper import insert_from_df

    operator_id = body.get("operator_id")
    vault_dbm = None
    if operator_id is not None:
        from infrastructure.db_manager import DBManager
        from infrastructure.lineage import (
            assert_lineage_present, stamp_lineage,
        )
        from infrastructure.operator_registry import (
            OperatorNotFoundError, OperatorRegistry,
        )
        try:
            registry = OperatorRegistry()
            vault_dbm = DBManager(registry)
            conn = vault_dbm.get_operator_connection(operator_id)
        except (OperatorNotFoundError, FileNotFoundError):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Unknown operator {operator_id!r}")
        frames = {
            t: stamp_lineage(df, operator_id=operator_id,
                             upload_session_id=session_id,
                             source_file=",".join(
                                 session.get("source_files", [])) or "extract")
            for t, df in frames.items()
        }
        for df in frames.values():
            assert_lineage_present(df)

    inserted: dict[str, int] = {}
    try:
        for table, df in frames.items():
            if df.empty:
                continue
            inserted[table] = insert_from_df(conn, table, df,
                                             on_conflict="none")
    finally:
        if vault_dbm is not None:
            vault_dbm.close_all()

    log_confirmation(session_id, accepted_rows, corrections)

    # Vault copy of the confirmed snapshot (operator-scoped sessions/)
    if operator_id is not None:
        try:
            import json as _json
            from infrastructure.vault_storage import store_session_snapshot
            store_session_snapshot(
                registry, operator_id, session_id,
                _json.dumps({"session_id": session_id,
                             "rows": accepted_rows,
                             "corrections": corrections}, default=str))
        except Exception:  # noqa: BLE001  vault copy must not block the load
            pass

    # Training corpus: every confirmed session is a labeled example —
    # operator corrections are the gold labels (Phase 4 accumulator).
    try:
        from training.data_accumulator import record_confirmed_session
        record_confirmed_session(
            session_id,
            mock_mode=bool(session.get("mock_mode", True)),
            prompt_version=session.get("prompt_version", "unknown"),
            raw_input_sample=", ".join(session.get("source_files", [])),
            llm_response={"column_mappings": session.get("column_mappings", []),
                          "summary": session.get("summary", {})},
            operator_corrections=corrections,
            final_clean_output={t: len(rs) for t, rs in by_table.items()}
            | {"rows": accepted_rows[:50]},
        )
    except Exception:  # noqa: BLE001  corpus write must never block the load
        pass

    return {
        "session_id": session_id,
        "rows_inserted": inserted,
        "total_inserted": sum(inserted.values()),
        "corrections_recorded": len(corrections),
        "sufficiency_warnings": session.get("sufficiency_warnings", []),
    }
