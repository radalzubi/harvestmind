"""Read-only DuckDB access for the dashboard.

Cached at module level so we don't reopen the file on every Streamlit rerun.
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]


def _db_path() -> str:
    return os.getenv("DUCKDB_PATH", str(ROOT / "harvestmind.duckdb"))


@st.cache_resource(show_spinner=False)
def get_conn() -> duckdb.DuckDBPyConnection:
    """One read-only DuckDB connection per Streamlit session."""
    return duckdb.connect(_db_path(), read_only=True)


def db_path() -> Path:
    return Path(_db_path())


def is_available() -> bool:
    return db_path().exists()
