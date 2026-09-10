"""Integration tests for the real-data ingestion pipeline.

These tests exercise the column_mapper + validate_real_data + ingest_real_data
pipeline against synthetic CSVs that mirror Local Line / QuickBooks shapes.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import pytest

from ingestion.column_mapper import (
    auto_map_columns,
    detect_and_convert_units,
    infer_missing_columns,
    insert_from_df,
)


# ── Schema bootstrap ─────────────────────────────────────────────────────────

def _bootstrap_schema(conn) -> None:
    """Run the project's migrations to set up the schema in the test DB."""
    repo_root = Path(__file__).resolve().parents[2]
    migrations_dir = repo_root / "db" / "migrations"
    for sql in sorted(migrations_dir.glob("*.sql")):
        conn.execute(sql.read_text())


@pytest.fixture
def conn():
    c = duckdb.connect(":memory:")
    _bootstrap_schema(c)
    # Seed the dim_buyers / dim_suppliers / dim_products entries the test data references,
    # so FK constraints don't reject inserts.
    c.execute(
        "INSERT INTO dim_buyers (buyer_id, buyer_name, buyer_type) VALUES "
        "(?, 'IU Health', 'institution'), "
        "(?, 'Market Wagon', 'institution')",
        ["BUY-IU", "BUY-MW"],
    )
    c.execute(
        "INSERT INTO dim_suppliers (supplier_id, supplier_name, supplier_type) VALUES "
        "(?, 'Full Hand Farm', 'farm'), "
        "(?, 'Prairie Wind', 'farm')",
        ["SUP-FH", "SUP-PW"],
    )
    c.execute(
        "INSERT INTO dim_products (product_id, crop_name, crop_category, shelf_life_days) VALUES "
        "(?, 'Carrots', 'root_veg', 30), "
        "(?, 'Lettuce', 'leafy_green', 7)",
        ["PRD-001", "PRD-002"],
    )
    return c


# ── Helper ───────────────────────────────────────────────────────────────────

def _ingest_one(conn, df, schema, table) -> int:
    renamed, mapping, _ = auto_map_columns(df, schema)
    df_units, _ = detect_and_convert_units(renamed, df.columns)
    df_inferred, _ = infer_missing_columns(df_units, schema)
    if df_inferred.empty:
        return 0
    return insert_from_df(conn, table, df_inferred, on_conflict="ignore")


# ── Tests ────────────────────────────────────────────────────────────────────

def test_local_line_orders_round_trip(conn, tmp_path):
    """Local Line export with renamed headers ingests correctly."""
    df = pd.DataFrame({
        "Order Number": ["LL-1", "LL-2"],
        "Customer":     ["BUY-IU", "BUY-MW"],
        "Order Date":   ["2025-06-02", "2025-06-09"],
    })
    n = _ingest_one(conn, df, "orders", "fact_orders")
    assert n == 2
    count = conn.execute("SELECT COUNT(*) FROM fact_orders").fetchone()[0]
    assert count == 2


def test_quickbooks_orders_round_trip(conn):
    df = pd.DataFrame({
        "Num":  ["QB-1"],
        "Name": ["BUY-IU"],
        "Date": ["2025-07-01"],
    })
    n = _ingest_one(conn, df, "orders", "fact_orders")
    assert n == 1


def test_pounds_column_converts_to_kg(conn):
    """A delivery row in lbs becomes kg in the DB."""
    df = pd.DataFrame({
        "Delivery ID":     ["D-1"],
        "Vendor":          ["SUP-FH"],
        "Item":            ["PRD-001"],
        "Delivery Date":   ["2025-06-04"],
        "Qty Received (lbs)": [100.0],   # original col includes 'lbs'
    })
    _ingest_one(conn, df, "deliveries", "fact_deliveries")
    qty = conn.execute(
        "SELECT qty_received_kg FROM fact_deliveries WHERE delivery_id = ?",
        ["D-1"],
    ).fetchone()[0]
    assert round(float(qty), 2) == round(100.0 * 0.453592, 2)


def test_missing_week_start_inferred_from_order_date(conn):
    df = pd.DataFrame({
        "order_id":   ["O-1"],
        "buyer_id":   ["BUY-IU"],
        "order_date": ["2025-06-04"],   # Wednesday → week_start = 2025-06-02
    })
    _ingest_one(conn, df, "orders", "fact_orders")
    row = conn.execute(
        "SELECT week_start FROM fact_orders WHERE order_id = ?",
        ["O-1"],
    ).fetchone()
    assert str(row[0]) == "2025-06-02"


def test_duplicate_rows_skipped(conn):
    df = pd.DataFrame({
        "order_id":   ["O-DUP"],
        "buyer_id":   ["BUY-IU"],
        "order_date": ["2025-06-02"],
    })
    n1 = _ingest_one(conn, df, "orders", "fact_orders")
    _ingest_one(conn, df, "orders", "fact_orders")  # second insert
    final = conn.execute("SELECT COUNT(*) FROM fact_orders WHERE order_id='O-DUP'").fetchone()[0]
    assert n1 == 1
    assert final == 1   # idempotent on PK


def test_empty_csv_no_crash(conn):
    df = pd.DataFrame(columns=["order_id","buyer_id","order_date"])
    n = _ingest_one(conn, df, "orders", "fact_orders")
    assert n == 0


def test_validation_failure_blocks_ingest(tmp_path):
    """A file with invalid quantities should be rejected by the validator."""
    from scripts.validate_real_data import validate_file

    bad = tmp_path / "deliveries.csv"
    bad.write_text(
        "Delivery ID,Vendor,Item,Delivery Date,Qty Received (kg),Qty Rejected (kg)\n"
        "D-1,SUP-FH,PRD-001,2025-06-04,100,50\n"      # ok
        "D-2,SUP-FH,PRD-001,2025-06-05,40,80\n"        # rejected > received
    )
    n_rows, n_errors, errors, _ = validate_file(bad)
    assert n_errors >= 1
    assert any("qty_rejected_kg" in e and "qty_received_kg" in e for e in errors)
