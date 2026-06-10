"""FastAPI dependency injection: database connection and shared state."""

from __future__ import annotations

import os
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parents[1]


def get_db_path() -> str:
    return os.getenv("DUCKDB_PATH", str(ROOT / "harvestmind.duckdb"))


def get_conn():
    """Yield a per-request DuckDB connection that is closed after the response.

    Generator-form dependency so FastAPI can run cleanup even if the route
    raises. Prevents connection leaks under exceptions.
    """
    conn = duckdb.connect(get_db_path())
    try:
        yield conn
    finally:
        conn.close()


def get_readonly_conn():
    """Yield a read-only connection for query-heavy endpoints."""
    conn = duckdb.connect(get_db_path(), read_only=True)
    try:
        yield conn
    finally:
        conn.close()


def get_request_conn(operator_id: str | None = None, root_conn=None):
    """Resolve the connection for a request.

    - operator_id absent → the legacy single-operator root DB (dev mode;
      all existing flows unchanged).
    - operator_id present → the operator's VAULT database via the
      registry/DBManager. Unknown ids raise 404. This is the only way an
      API request reaches a vault — no endpoint opens vault files itself.
    """
    from fastapi import HTTPException

    if operator_id is None:
        yield from get_conn()
        return

    from infrastructure.db_manager import DBManager
    from infrastructure.operator_registry import (
        OperatorNotFoundError, OperatorRegistry,
    )
    try:
        dbm = DBManager(OperatorRegistry())
        conn = dbm.get_operator_connection(operator_id)
    except (OperatorNotFoundError, FileNotFoundError):
        raise HTTPException(status_code=404,
                            detail=f"Unknown operator {operator_id!r}")
    try:
        yield conn
    finally:
        dbm.close_all()
