"""Row-level lineage: who, what file, when, which session.

Migration 011 adds four nullable lineage columns to every staging table.
This module stamps them on ingest and enforces their presence on the
operator-scoped path: a row arriving in a vault without lineage is
rejected — an untraceable number can never reach a diagnostic.

The legacy single-operator dev mode (root DB, no operator_id) is exempt
by design; lineage is nullable there for backward compatibility.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

LINEAGE_COLUMNS = ("_upload_session_id", "_uploaded_at",
                   "_source_file", "_operator_id")


def stamp_lineage(
    df: pd.DataFrame,
    *,
    operator_id: str,
    upload_session_id: str,
    source_file: str,
) -> pd.DataFrame:
    """Return a copy with the four lineage columns populated."""
    out = df.copy()
    out["_upload_session_id"] = upload_session_id
    out["_uploaded_at"] = datetime.now(timezone.utc)
    out["_source_file"] = source_file
    out["_operator_id"] = operator_id
    return out


def assert_lineage_present(df: pd.DataFrame) -> None:
    """Reject operator-scoped inserts that lack lineage."""
    missing = [c for c in LINEAGE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"rows rejected: lineage columns missing {missing} — every "
            f"vault row must carry who/what/when/session provenance")
    for c in LINEAGE_COLUMNS:
        if df[c].isna().any():
            raise ValueError(
                f"rows rejected: {int(df[c].isna().sum())} row(s) have "
                f"null {c} — lineage is required on the operator-scoped "
                f"path")


def trace_row(conn, table: str, where_sql: str) -> list[dict]:
    """Trace rows back to their source: returns lineage tuples for the
    matching rows — the audit path from any number to its upload."""
    cols = ", ".join(LINEAGE_COLUMNS)
    rows = conn.execute(
        f"SELECT {cols}, COUNT(*) AS n FROM {table} "  # noqa: S608
        f"WHERE {where_sql} GROUP BY {cols}").fetchall()
    return [dict(zip([*LINEAGE_COLUMNS, "n_rows"], r)) for r in rows]
