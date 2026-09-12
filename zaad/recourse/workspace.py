"""Vault adapter for adaptive recourse (P4, migration 019): the operator's declared recourse
specification, attached to a planning request only when asked for. Absent table, no row or
`enabled` false: nothing is attached and the frozen request is built."""
from __future__ import annotations

import json
from typing import Any

import pandas as pd


def _present(value: Any) -> bool:
    try:
        return value is not None and not bool(pd.isna(value))
    except (TypeError, ValueError):
        return value is not None


def recourse_table(conn: Any):
    try:
        return conn.execute("SELECT operator_id, enabled, review_periods, observables, actions, demand_grid, fill_grid, confirmation_lag, "
                            "continuations, perfect_information, provenance FROM stg_recourse_spec ORDER BY declared_at DESC").fetchdf()
    except Exception:
        return None


def recourse_block(conn: Any, operator_id: str) -> dict[str, Any] | None:
    """The declared RecourseSpec payload for the operator, or None when nothing is declared."""
    table = recourse_table(conn)
    if table is None or not len(table):
        return None
    rows = table[table["operator_id"] == operator_id] if "operator_id" in table.columns else table
    if not len(rows):
        return None
    row = rows.iloc[0]
    out: dict[str, Any] = {"enabled": bool(row.get("enabled")) if _present(row.get("enabled")) else False}
    for key in ("review_periods", "observables", "actions"):
        value = row.get(key)
        if _present(value) and str(value).strip():
            out[key] = json.loads(str(value))
    for key in ("demand_grid", "fill_grid"):
        value = row.get(key)
        if _present(value):
            out[key] = float(value)
    for key in ("confirmation_lag", "continuations"):
        value = row.get(key)
        if _present(value):
            out[key] = int(value)
    if _present(row.get("perfect_information")):
        out["perfect_information"] = bool(row.get("perfect_information"))
    if _present(row.get("provenance")) and str(row.get("provenance")).strip():
        out["provenance"] = str(row.get("provenance"))
    return out
