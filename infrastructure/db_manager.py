"""All vault database access goes through here. CONVENTION (enforced by
review + the isolation tests): application code never calls
duckdb.connect on a vault path directly — only DBManager resolves
operator ids to connections, so isolation has exactly one place to be
right.

Cross-operator visibility exists in ONE method only:
get_cross_operator_connection — read-only, requires a stated purpose
(logged to data/registry/cross_access_log.jsonl), and is used solely by
the pool contribution pipeline. The diagnostic and the optimizer never
touch it.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from infrastructure.operator_registry import OperatorRegistry


class DBManager:
    def __init__(self, registry: OperatorRegistry | None = None) -> None:
        self.registry = registry or OperatorRegistry()
        self._open: list[duckdb.DuckDBPyConnection] = []

    # ── single-operator access ───────────────────────────────────────────

    def get_operator_connection(self, operator_id: str) -> duckdb.DuckDBPyConnection:
        path = self.registry.get_db_path(operator_id)
        conn = duckdb.connect(str(path))
        self._open.append(conn)
        return conn

    def get_read_only_connection(self, operator_id: str) -> duckdb.DuckDBPyConnection:
        path = self.registry.get_db_path(operator_id)
        conn = duckdb.connect(str(path), read_only=True)
        self._open.append(conn)
        return conn

    # ── the ONLY multi-operator path ─────────────────────────────────────

    def get_cross_operator_connection(
        self,
        operator_ids: list[str],
        purpose: str,
    ) -> duckdb.DuckDBPyConnection:
        """Read-only view across EXACTLY the named operators.

        Each vault is ATTACHed READ_ONLY into an in-memory connection
        under the alias ``op_<id>`` — queries must name the operator they
        read from (``op_xxx.stg_buyer_orders``), so no query can
        accidentally sweep everyone. Purpose is mandatory and logged.
        """
        if not operator_ids:
            raise ValueError(
                "get_cross_operator_connection requires explicit operator "
                "ids — there is no 'all operators' shortcut by design")
        if not purpose or not purpose.strip():
            raise ValueError("a stated purpose is required and is logged")

        paths = {oid: self.registry.get_db_path(oid)  # raises on unknown
                 for oid in operator_ids}

        conn = duckdb.connect(":memory:")
        for oid, path in paths.items():
            conn.execute(
                f"ATTACH '{path}' AS {oid} (READ_ONLY)")
        self._open.append(conn)

        log_dir = self.registry.registry_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "cross_access_log.jsonl").open("a") as f:
            f.write(json.dumps({
                "at": datetime.now(timezone.utc).isoformat(),
                "operator_ids": sorted(operator_ids),
                "purpose": purpose,
            }) + "\n")
        return conn

    def close_all(self) -> None:
        for c in self._open:
            try:
                c.close()
            except Exception:  # noqa: BLE001
                pass
        self._open = []
