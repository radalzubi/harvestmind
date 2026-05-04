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
