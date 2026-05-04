"""Tests for ingestion/csv_ingestor.py."""

from __future__ import annotations

import pandas as pd
import pytest

# Use a real allowlisted table for ingestion tests (the function rejects
# non-allowlisted names; we exercise the whole code path via `dim_products`).


@pytest.fixture
def small_db():
    import duckdb
    conn = duckdb.connect(":memory:")
    # Two-column primary-keyed table so DuckDB's INSERT OR IGNORE can run.
    conn.execute(
        "CREATE TABLE dim_products (a INTEGER PRIMARY KEY, b VARCHAR)"
    )
    yield conn
    conn.close()


def test_ingest_csv_inserts_rows(tmp_path, small_db):
    from ingestion.csv_ingestor import ingest_csv

    csv = tmp_path / "rows.csv"
    pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]}).to_csv(csv, index=False)

    n = ingest_csv(csv, "dim_products", small_db, column_map={})
    assert n == 3
    assert small_db.execute("SELECT COUNT(*) FROM dim_products").fetchone()[0] == 3


def test_ingest_csv_empty_file_returns_zero(tmp_path, small_db):
    from ingestion.csv_ingestor import ingest_csv

    csv = tmp_path / "empty.csv"
    pd.DataFrame({"a": [], "b": []}).to_csv(csv, index=False)
    assert ingest_csv(csv, "dim_products", small_db, column_map={}) == 0


def test_ingest_csv_invalid_if_exists_raises(tmp_path, small_db):
    from ingestion.csv_ingestor import ingest_csv

    csv = tmp_path / "rows.csv"
    pd.DataFrame({"a": [1], "b": ["x"]}).to_csv(csv, index=False)

    with pytest.raises(ValueError, match="if_exists must be"):
        ingest_csv(csv, "dim_products", small_db, column_map={}, if_exists="upsert")


def test_ingest_csv_propagates_column_count_mismatch(tmp_path, small_db):
    """Column-count mismatches must raise — not be silently masked.

    Regression: earlier code had a bare `except Exception` fallback that
    re-tried the insert with a different syntax, hiding genuine DB errors.
    DuckDB itself only catches *count* mismatches (it matches by position
    when counts agree), so test with a truly wrong number of columns.
    """
    from ingestion.csv_ingestor import ingest_csv

    csv = tmp_path / "rows.csv"
    pd.DataFrame({"a": [1, 2], "b": ["x", "y"], "c": ["extra", "col"]}).to_csv(csv, index=False)
    with pytest.raises(Exception):  # duckdb.BinderException at runtime
        ingest_csv(csv, "dim_products", small_db, column_map={})
