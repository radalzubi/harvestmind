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

import io
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from loguru import logger

from api.dependencies import get_conn, rate_limiter, require_operator
from ingestion.csv_ingestor import COLUMN_MAPS, ingest_csv

router = APIRouter(prefix="/intake", tags=["intake"])

# Upper bound on a single uploaded file. Operator CSV/PDF intake is well
# under this; the cap prevents an unbounded body from being read fully into
# memory (memory-exhaustion DoS). A fronting proxy should also enforce a
# limit, but the app must not rely on one being present.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB
MAX_EXTRACT_FILES = 20


def _reject_if_too_large(contents: bytes, filename: str | None) -> None:
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"File {filename or 'upload'!r} exceeds the "
                f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit."
            ),
        )

# ── Staging table allowlist ───────────────────────────────────────────────────

STAGING_TABLES: dict[str, dict[str, Any]] = {
    # ── FMCG (eaches; see db/migrations/013_fmcg_staging.sql) ──────────────
    "stg_fmcg_skus": {"required_cols": {"sku", "unit_cost"}, "date_cols": [],
                      "description": "FMCG SKU master with pack structure"},
    "stg_fmcg_orders": {"required_cols": {"sku", "qty_ordered", "order_date"},
                        "date_cols": ["order_date", "requested_delivery_date"],
                        "description": "FMCG customer order lines"},
    "stg_fmcg_purchase_orders": {"required_cols": {"po_id", "sku", "qty_ordered", "po_date"},
                                 "date_cols": ["po_date", "expected_delivery_date"],
                                 "description": "FMCG purchase orders"},
    "stg_fmcg_receipts": {"required_cols": {"po_id", "qty_received", "receipt_date"},
                          "date_cols": ["receipt_date"], "description": "FMCG supplier receipts"},
    "stg_fmcg_inventory": {"required_cols": {"sku", "on_hand", "snapshot_date"},
                           "date_cols": ["snapshot_date"], "description": "FMCG inventory snapshots"},
    "stg_fmcg_promotions": {"required_cols": {"sku", "week_start", "uplift"},
                            "date_cols": ["week_start"], "description": "FMCG promotion calendar"},
    "stg_fmcg_suppliers": {"required_cols": {"supplier_id"}, "date_cols": [],
                           "description": "FMCG supplier master with route/manufacturer tags and capacity"},
    "stg_fmcg_economics": {"required_cols": {"key", "value"}, "date_cols": [],
                           "description": "FMCG economic parameters with provenance"},
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
    force: bool = False,
    anonymize: bool = True,
    conn=Depends(get_conn),
    authed: str | None = Depends(require_operator),
):
    """Upload a CSV file into a staging table.

    ``anonymize=true`` (default) replaces identifier columns with keyed
    hashes and drops free-text name/contact columns BEFORE the file
    reaches the vault, using a per-operator secret held only in the
    registry (see docs/security/DATA_HANDLING.md). Files anonymised
    client-side with scripts/anonymize_export.py pass through unchanged.
    With HARVESTMIND_REQUIRE_ANONYMIZED=1 a raw file is refused.

    ``force=true`` loads a file whose exact content was already uploaded;
    otherwise a repeat is refused with a rejection report, so a retry or a
    double click cannot double the staged quantities.

    Returns:
        table          target table name
        rows_inserted  number of rows loaded
        warnings       list of non-blocking issues
        errors         list of blocking issues (empty on success)
    """
    operator_id = authed or operator_id   # token wins; query param is dev fallback
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
    _reject_if_too_large(contents, file.filename)

    warnings: list[str] = []
    errors: list[str] = []
    anonymization: dict | None = None

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
        from infrastructure.vault_storage import (
            DuplicateUploadError, store_raw_upload,
        )
        try:
            registry = OperatorRegistry()
            import os as _os

            import pandas as _pd

            from ingestion.anonymize import anonymize_csv_bytes, looks_anonymized
            try:
                _already = looks_anonymized(_pd.read_csv(io.BytesIO(contents), nrows=200))
            except Exception:  # noqa: BLE001
                _already = False
            if anonymize and not _already:
                secret = registry.anonymization_secret(operator_id)
                contents, rep = anonymize_csv_bytes(contents, secret)
                anonymization = {**rep.as_dict(), "mode": "server"}
            elif _already:
                anonymization = {"mode": "client", "note": "file arrived pseudonymised; stored as received"}
            elif _os.environ.get("HARVESTMIND_REQUIRE_ANONYMIZED", "").strip() in ("1", "true", "yes"):
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail="raw identifiers refused: anonymise the export "
                                           "(anonymize=true or scripts/anonymize_export.py)")
            else:
                anonymization = {"mode": "none", "warning": "raw identifiers stored at operator's request"}
            try:
                store_raw_upload(registry, operator_id,
                                 file.filename or "upload.csv", contents,
                                 allow_duplicate=force)
            except DuplicateUploadError as dup:
                return {
                    "table": table, "rows_inserted": 0, "warnings": [],
                    "errors": [f"{dup}. Nothing was loaded. Clear the table "
                               f"or re-send with force=true if this repeat "
                               f"is deliberate."],
                }
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
                status_code=422,
                detail=f"Could not parse CSV ({type(e).__name__}); check the delimiter, encoding and header row",
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

        # Columns the staging table cannot hold are dropped with a warning
        # rather than passed to the insert, which previously surfaced as a
        # DuckDB binder error and a 500. The operator sees which columns
        # were ignored; nothing is silently reinterpreted.
        try:
            known_cols = {row[1] for row in conn.execute(
                f"PRAGMA table_info('{table}')").fetchall()}  # nosec B608 - table allowlisted
        except Exception:  # noqa: BLE001
            known_cols = set()
        if known_cols:
            extra = [c for c in mapped_df.columns if c not in known_cols]
            if extra:
                warnings.append(
                    f"Ignored {len(extra)} column(s) not in {table}: "
                    f"{extra[:8]}{' ...' if len(extra) > 8 else ''}")
                mapped_df = mapped_df.drop(columns=extra)
                full_df = full_df.drop(columns=[c for c in full_df.columns
                                                 if col_map.get(c, c) in extra])
                # legacy path re-reads the temp file: rewrite it without the
                # dropped columns so both paths see the same frame
                full_df.to_csv(tmp_path, index=False)

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
                upload_session_id=upload_session_id or "",
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
            "anonymization": anonymization,
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
        # Do not echo the absolute server path back to the client (recon leak);
        # log it server-side for operators/debugging instead.
        logger.error("Sample data directory not found at {}", samples_dir)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample data is not available on this server.",
        )

    rows_by_table: dict[str, int] = {}
    errors: list[str] = []

    for table, meta in STAGING_TABLES.items():
        if table.startswith("stg_fmcg_"):
            # FMCG samples live under data/samples/fmcg/ and are uploaded
            # through the FMCG flow; this demo loader is the produce onboarding.
            continue
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
    conn.execute(f"DELETE FROM {table}")  # noqa: S608  table is allowlisted  # nosec B608 - table allowlisted by _validate_staging_table
    return {"table": table, "status": "cleared"}


@router.get("/status")
def intake_status(conn=Depends(get_conn)):
    """Row counts across all staging tables."""
    result: dict[str, Any] = {}
    for table, meta in STAGING_TABLES.items():
        try:
            row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # noqa: S608  # nosec B608 - table allowlisted by _validate_staging_table
            count = int(row[0]) if row else 0
        except Exception:
            count = 0
        result[table] = {
            "description": meta["description"],
            "row_count": count,
            "loaded": count > 0,
        }
    # Two table families, one per operating domain. "all loaded" is asked
    # per family: a produce operator never uploads FMCG tables and vice
    # versa, so a single flag across both would never be true.
    families = {
        "produce": [t for t in result if not t.startswith("stg_fmcg_")],
        "fmcg": [t for t in result if t.startswith("stg_fmcg_")],
    }
    fam = {name: {"tables": ts,
                  "any_loaded": any(result[t]["loaded"] for t in ts),
                  "all_loaded": all(result[t]["loaded"] for t in ts)}
           for name, ts in families.items()}
    any_loaded = any(v["loaded"] for v in result.values())
    return {
        "tables": result,
        "families": fam,
        "any_data_loaded": any_loaded,
        # Legacy flag: the produce family, which is what every existing
        # caller meant by "all tables".
        "all_tables_loaded": fam["produce"]["all_loaded"],
    }


# ── LLM extraction endpoints (smart upload) ───────────────────────────────────

@router.post("/extract", dependencies=[Depends(rate_limiter)])
async def extract_files(
    files: list[UploadFile] = File(...),
    operator_id: str | None = None,
    conn=Depends(get_conn),
    authed: str | None = Depends(require_operator),
):
    """Smart upload: any-format files → ExtractionResult for confirmation.

    Nothing is inserted here. The result (mock or real per USE_REAL_LLM)
    goes to the confirmation UI; rows reach staging only via
    POST /intake/confirm after operator review.
    """
    import tempfile
    from pathlib import Path as _P

    operator_id = authed or operator_id   # token wins; query param is dev fallback
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="No files uploaded")
    if len(files) > MAX_EXTRACT_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many files (max {MAX_EXTRACT_FILES} per request).")

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
            _reject_if_too_large(content, f.filename)
            if registry is not None:
                from infrastructure.vault_storage import store_raw_upload
                # Nothing loads until the mapping is confirmed, so re-sending
                # the same file is a re-read, not a double load.
                store_raw_upload(registry, operator_id or "",
                                 f.filename or "upload.bin", content, allow_duplicate=True)
            suffix = _P(f.filename or "upload.csv").suffix or ".csv"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(content)
                tmp_paths.append(_P(tmp.name))

        from ingestion.llm_extractor import extract as llm_extract
        try:
            result = llm_extract(list(tmp_paths))
        except ValueError as e:   # unsupported file type etc.
            raise HTTPException(
                status_code=422,
                detail=f"Confirmation failed ({type(e).__name__})")
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
def confirm_extraction(body: dict, conn=Depends(get_conn),
                       authed: str | None = Depends(require_operator)):
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
        table = r.get("table")
        # A confirmed row may only target one of the five staging tables.
        # Without this the endpoint would insert into ANY table named in the
        # request body (master/fact tables included), and a row missing the
        # key would raise an unhandled KeyError → 500.
        if table not in STAGING_TABLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid or missing target table {table!r}. "
                    f"Confirmed rows must target one of: {sorted(STAGING_TABLES)}."
                ),
            )
        fields = {k: v for k, v in r.get("fields", {}).items()
                  if not k.startswith("_")}
        by_table.setdefault(table, []).append(fields)

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
        raise HTTPException(status_code=422,
                            detail={"validation_errors": errors})

    from ingestion.column_mapper import insert_from_df

    operator_id = authed or body.get("operator_id")   # token wins; body is dev fallback
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
                             upload_session_id=str(session_id or ""),
                             source_file=",".join(
                                 session.get("source_files", [])) or "extract")
            for t, df in frames.items()
        }
        for df in frames.values():
            assert_lineage_present(df)

    inserted: dict[str, int] = {}
    try:
        # Atomic: a multi-table confirm either lands completely or not at all.
        # Without the transaction, a failure on the second table would leave
        # the first table's rows committed (DuckDB autocommits per statement),
        # corrupting the vault and inviting duplicate re-confirms.
        conn.execute("BEGIN TRANSACTION")
        try:
            for table, df in frames.items():
                if df.empty:
                    continue
                inserted[table] = insert_from_df(conn, table, df,
                                                 on_conflict="none")
            conn.execute("COMMIT")
        except HTTPException:
            conn.execute("ROLLBACK")
            raise
        except Exception:  # noqa: BLE001 — surface a clean 422, log internally
            conn.execute("ROLLBACK")
            logger.exception("confirm insert failed for session %s", session_id)
            raise HTTPException(
                status_code=422,
                detail="Could not insert confirmed rows; no data was written.",
            )
    finally:
        if vault_dbm is not None:
            vault_dbm.close_all()

    log_confirmation(str(session_id or ""), accepted_rows, corrections)

    # Vault copy of the confirmed snapshot (operator-scoped sessions/)
    pool_result = None
    if operator_id is not None:
        try:
            import json as _json
            from infrastructure.vault_storage import store_session_snapshot
            store_session_snapshot(
                registry, operator_id, str(session_id or ""),
                _json.dumps({"session_id": session_id,
                             "rows": accepted_rows,
                             "corrections": corrections}, default=str))
        except Exception:  # noqa: BLE001  vault copy must not block the load
            pass
        # Pool contribution — consent-gated, anonymized, never blocking
        try:
            from pool.pool_contributor import PoolContributor
            pool_result = PoolContributor(registry).contribute_session(
                operator_id).model_dump()
        except Exception:  # noqa: BLE001
            pool_result = None

    # Training corpus: every confirmed session is a labeled example —
    # operator corrections are the gold labels (Phase 4 accumulator).
    try:
        from training.data_accumulator import record_confirmed_session
        record_confirmed_session(str(session_id or ""),
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
        "pool_contribution": pool_result,
    }


# ── Synthetic sample for commercial workspaces ───────────────────────────────
def load_fmcg_sample_into(conn, seed: int = 7, archetype: str = "E_mixed_portfolio") -> dict:
    """Load a labelled SYNTHETIC distributor history (mixed lanes, promotions,
    a constrained supplier) into the FMCG staging tables. Replaces any
    existing FMCG data in the vault. Never real operator data."""
    import pandas as pd

    from synthetic.fmcg.distributor_sim import build_history
    h = build_history(archetype, seed=seed)
    skus = h.skus[["sku", "supplier_id", "unit_cost", "unit_price", "units_per_case", "moq_units", "category"]]
    orders = h.order_lines.merge(h.customer_orders[["order_id", "customer_id", "order_date"]], on="order_id")
    orders = orders[["order_id", "customer_id", "order_date", "sku", "qty_ordered"]]
    inv = h.inventory_snapshots.rename(columns={"week_start": "snapshot_date"})[["snapshot_date", "sku", "on_hand", "in_transit"]]
    sup = h.suppliers[["supplier_id"]].copy()
    sup["route"] = ["aqaba" if i % 2 == 0 else "road_saudi" for i in range(len(sup))]
    sup["origin_iso3"] = ["DEU" if i % 2 == 0 else "SAU" for i in range(len(sup))]
    frames = (("stg_fmcg_skus", skus), ("stg_fmcg_orders", orders),
              ("stg_fmcg_purchase_orders", h.purchase_orders[["po_id", "po_date", "supplier_id", "sku", "qty_ordered", "unit_cost"]]),
              ("stg_fmcg_receipts", h.receipts[["po_id", "receipt_date", "sku", "qty_received"]]),
              ("stg_fmcg_inventory", inv), ("stg_fmcg_suppliers", sup))
    loaded: dict = {}
    for table, df in frames:
        conn.execute(f"DELETE FROM {table}")  # nosec B608 - table names are literals above
        frame = df.copy()
        for c in frame.columns:
            if "date" in c:
                frame[c] = pd.to_datetime(frame[c]).dt.date
        conn.register("_sample_df", frame)
        cols = ", ".join(frame.columns)
        conn.execute(f"INSERT INTO {table} ({cols}) SELECT {cols} FROM _sample_df")  # nosec B608 - literals
        conn.unregister("_sample_df")
        loaded[table] = int(len(frame))
    return {"tables": loaded, "total_rows": int(sum(loaded.values())), "classification": "SYNTHETIC CALIBRATED",
            "note": "a made-up distributor with mixed lanes and a constrained supplier; replaces existing FMCG data"}


@router.post("/load-sample-fmcg", status_code=status.HTTP_200_OK)
def load_sample_fmcg(seed: int = 7, conn=Depends(get_conn)):
    return load_fmcg_sample_into(conn, seed=seed)
