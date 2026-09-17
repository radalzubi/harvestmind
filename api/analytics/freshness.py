"""Dataset versions: an explicit identity for "the data as it was when this was computed".

A version is derived from the vault, never declared: per staging table, the latest upload stamp
and the row count; per operating table, the latest write. The id is a hash of that description,
so the same data gives the same id in every process and a new upload gives a new one. Versions
are recorded in `zaad_analytics_dataset_versions` (additive migration 028) the first time they
are seen, so a saved analysis, an export or a plan can say which version it read and whether the
data has moved since. Nothing here touches the per-row lineage stamps the uploads already carry.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from api.product.catalog import _columns, _one, has_table

STAGING = ("stg_fmcg_skus", "stg_fmcg_orders", "stg_fmcg_inventory", "stg_fmcg_purchase_orders", "stg_fmcg_receipts",
           "stg_fmcg_suppliers", "stg_fmcg_locations", "stg_fmcg_lanes", "stg_fmcg_transfers", "stg_fmcg_sources",
           "stg_po_commitments", "stg_po_options", "stg_atp_customer_orders", "stg_atp_service_classes")
OPERATING = (("zaad_draft_orders", "updated_at"), ("zaad_decision_responses", "updated_at"), ("zaad_outcomes", "created_at"))
CUTOFF_DATES = (("stg_fmcg_orders", "order_date"), ("stg_fmcg_inventory", "snapshot_date"), ("stg_fmcg_receipts", "receipt_date"),
                ("stg_fmcg_purchase_orders", "po_date"))


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def describe(conn: Any, operator: str) -> dict[str, Any]:
    """The per-table state the version is derived from."""
    tables: dict[str, dict[str, Any]] = {}
    for table in STAGING:
        if not has_table(conn, table):
            continue
        cols = _columns(conn, table)
        stamp_col = "_uploaded_at" if "_uploaded_at" in cols else ("imported_at" if "imported_at" in cols else None)
        scoped = "operator_id" in cols and table.startswith(("stg_po_", "stg_atp_"))
        where = " WHERE operator_id = ?" if scoped else ""
        params = [operator] if scoped else []
        n = int(_one(conn, f"SELECT count(*) FROM {table}{where}", params) or 0)  # noqa: S608  # nosec B608 - literal names; the operator binds
        stamp = _one(conn, f"SELECT max({stamp_col}) FROM {table}{where}", params) if (stamp_col and n) else None  # noqa: S608  # nosec B608
        sessions = None
        if "_upload_session_id" in cols and n:
            sessions = int(_one(conn, f"SELECT count(DISTINCT _upload_session_id) FROM {table}{where}", params) or 0)  # noqa: S608  # nosec B608
        tables[table] = {"rows": n, "last_updated": _iso(stamp), "upload_sessions": sessions}
    for table, col in OPERATING:
        if has_table(conn, table):
            n = int(_one(conn, f"SELECT count(*) FROM {table} WHERE operator_id = ?", [operator]) or 0)  # noqa: S608  # nosec B608
            stamp = _one(conn, f"SELECT max({col}) FROM {table} WHERE operator_id = ?", [operator]) if n else None  # noqa: S608  # nosec B608
            tables[table] = {"rows": n, "last_updated": _iso(stamp), "upload_sessions": None}
    cutoff: str | None = None
    for table, col in CUTOFF_DATES:
        if table in tables and tables[table]["rows"]:
            value = _iso(_one(conn, f"SELECT max({col}) FROM {table}"))  # noqa: S608  # nosec B608
            if value and (cutoff is None or value > cutoff):
                cutoff = value
    stamps = [t["last_updated"] for t in tables.values() if t["last_updated"]]
    return {"tables": tables, "last_updated": max(stamps) if stamps else None, "data_cutoff": cutoff[:10] if cutoff else None}


def version_id(description: dict[str, Any]) -> str:
    text = json.dumps({k: {"rows": v["rows"], "last_updated": v["last_updated"]} for k, v in description["tables"].items()}, sort_keys=True)
    return "dv_" + hashlib.sha256(text.encode()).hexdigest()[:16]


def ensure_table(conn: Any) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS zaad_analytics_dataset_versions (dataset_version_id VARCHAR NOT NULL, operator_id VARCHAR NOT NULL, "
                 "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_updated VARCHAR, data_cutoff VARCHAR, tables VARCHAR)")


def current(conn: Any, operator: str, *, record: bool = True) -> dict[str, Any]:
    """The dataset version the vault is at now; recorded on first sight."""
    description = describe(conn, operator)
    identity = version_id(description)
    first_seen = None
    if record:
        try:
            ensure_table(conn)
            row = _one(conn, "SELECT created_at FROM zaad_analytics_dataset_versions WHERE operator_id = ? AND dataset_version_id = ?", [operator, identity])
            if row is None:
                conn.execute("INSERT INTO zaad_analytics_dataset_versions (dataset_version_id, operator_id, created_at, last_updated, data_cutoff, tables) VALUES (?, ?, ?, ?, ?, ?)",
                             [identity, operator, datetime.now(timezone.utc).replace(tzinfo=None), description["last_updated"], description["data_cutoff"],
                              json.dumps(description["tables"], sort_keys=True)])
                first_seen = datetime.now(timezone.utc).isoformat(timespec="seconds")
            else:
                first_seen = _iso(row)
        except Exception:  # noqa: BLE001 - a read-only or pre-migration vault still gets its version, unrecorded
            first_seen = None
    return {"dataset_version_id": identity, "last_updated": description["last_updated"], "data_cutoff": description["data_cutoff"],
            "first_seen": first_seen, "tables": {k: v["rows"] for k, v in description["tables"].items()}}


def moved_since(conn: Any, operator: str, recorded_version: str | None) -> dict[str, Any]:
    """Whether the data has moved since `recorded_version`, and which tables did."""
    now = current(conn, operator)
    if not recorded_version or recorded_version == now["dataset_version_id"]:
        return {"stale": False, "current": now["dataset_version_id"], "recorded": recorded_version, "tables_moved": []}
    moved: list[str] = []
    try:
        row = _one(conn, "SELECT tables FROM zaad_analytics_dataset_versions WHERE operator_id = ? AND dataset_version_id = ?", [operator, recorded_version])
        then = json.loads(row) if row else {}
        for table, state in describe(conn, operator)["tables"].items():
            before = then.get(table)
            if before is None or before.get("rows") != state["rows"] or before.get("last_updated") != state["last_updated"]:
                moved.append(table)
    except Exception:  # noqa: BLE001
        moved = ["unknown"]
    return {"stale": True, "current": now["dataset_version_id"], "recorded": recorded_version, "tables_moved": moved}
