"""Security regression tests for ingestion/csv_ingestor.py.

The ingestor accepts a file path and a target table name from callers.
Both must be validated before reaching DuckDB — table name is interpolated
into raw SQL, and the file path is opened by pandas. These tests pin the
contract.
"""

from __future__ import annotations

import duckdb
import pandas as pd
import pytest

from ingestion.csv_ingestor import (
    ALLOWED_EXTENSIONS,
    ALLOWED_TABLES,
    ingest_csv,
)


@pytest.fixture
def mini_db():
    conn = duckdb.connect(":memory:")
    # PRIMARY KEY required so DuckDB's INSERT OR IGNORE has a conflict
    # target; mirrors the production fact_orders schema in db/migrations.
    conn.execute(
        "CREATE TABLE fact_orders ("
        "order_id VARCHAR PRIMARY KEY, buyer_id VARCHAR, "
        "order_date DATE, week_start DATE, status VARCHAR, notes VARCHAR)"
    )
    yield conn
    conn.close()


def test_table_must_be_in_allowlist(tmp_path, mini_db):
    csv = tmp_path / "x.csv"
    csv.write_text("a,b\n1,2\n")
    with pytest.raises(ValueError, match="ingestion allowlist"):
        ingest_csv(csv, "evil_table; DROP TABLE x; --", mini_db, column_map={})


def test_known_table_accepted(tmp_path, mini_db):
    """`fact_orders` is in the allowlist and matches our toy schema."""
    csv = tmp_path / "orders.csv"
    pd.DataFrame({
        "order_id": ["O1"], "buyer_id": ["B1"],
        "order_date": ["2025-01-01"], "week_start": ["2024-12-30"],
        "status": ["confirmed"], "notes": [None],
    }).to_csv(csv, index=False)
    n = ingest_csv(csv, "fact_orders", mini_db, column_map={})
    assert n == 1


def test_path_must_be_csv(tmp_path, mini_db):
    bad = tmp_path / "data.txt"
    bad.write_text("x,y\n1,2\n")
    with pytest.raises(ValueError, match="unsupported file extension"):
        ingest_csv(bad, "fact_orders", mini_db, column_map={})


def test_path_must_exist(tmp_path, mini_db):
    with pytest.raises(FileNotFoundError):
        ingest_csv(tmp_path / "nope.csv", "fact_orders", mini_db, column_map={})


def test_path_must_be_regular_file(tmp_path, mini_db):
    """A directory ending in .csv must still be rejected."""
    d = tmp_path / "dir.csv"
    d.mkdir()
    with pytest.raises(ValueError, match="not a regular file"):
        ingest_csv(d, "fact_orders", mini_db, column_map={})


def test_empty_csv_returns_zero_rows(tmp_path, mini_db):
    """A CSV that is empty (no data lines and no header) should yield 0
    inserts rather than crashing on EmptyDataError."""
    csv = tmp_path / "empty.csv"
    csv.write_text("")
    assert ingest_csv(csv, "fact_orders", mini_db, column_map={}) == 0


def test_allowlist_constants_are_safe_identifiers():
    """Belt-and-braces: every allowlisted table is a plain SQL identifier."""
    import re
    ident = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
    for tbl in ALLOWED_TABLES:
        assert ident.match(tbl), f"{tbl!r} is not a safe identifier"
    for ext in ALLOWED_EXTENSIONS:
        assert ext.startswith(".")
