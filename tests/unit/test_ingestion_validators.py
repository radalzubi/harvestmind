"""Unit tests for ingestion/validators.py — hard upload validation.

Errors must block the upload (negatives, reversed dates, unparseable
required dates); warnings must not (units, magnitudes, far-future dates).
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from ingestion.validators import validate_staging_df

_TODAY = date(2026, 5, 27)


def test_clean_dataframe_passes():
    df = pd.DataFrame({
        "product_name": ["Tomatoes"],
        "delivery_date": ["2026-05-01"],
        "ordered_quantity": [100.0],
        "accepted_quantity": [95.0],
        "unit_cost": [2.10],
    })
    result = validate_staging_df("stg_supplier_deliveries", df, today=_TODAY)
    assert result.ok
    assert result.errors == []


def test_negative_quantity_rejected():
    df = pd.DataFrame({
        "product_name": ["Tomatoes", "Lettuce"],
        "delivery_date": ["2026-05-01", "2026-05-02"],
        "ordered_quantity": [100.0, -40.0],
    })
    result = validate_staging_df("stg_supplier_deliveries", df, today=_TODAY)
    assert not result.ok
    assert any("ordered_quantity" in e and "negative" in e for e in result.errors)


def test_negative_price_rejected():
    df = pd.DataFrame({
        "product_name": ["Tomatoes"],
        "requested_quantity": [50.0],
        "sales_price": [-3.20],
    })
    result = validate_staging_df("stg_buyer_orders", df, today=_TODAY)
    assert not result.ok
    assert any("sales_price" in e for e in result.errors)


def test_reversed_dates_rejected_inventory_lots():
    df = pd.DataFrame({
        "product_name": ["Tomatoes"],
        "quantity_on_hand": [80.0],
        "arrival_date": ["2026-05-20"],
        "expiration_date": ["2026-05-10"],  # before arrival → reversed
    })
    result = validate_staging_df("stg_inventory_lots", df, today=_TODAY)
    assert not result.ok
    assert any("expiration_date before arrival_date" in e for e in result.errors)


def test_reversed_dates_rejected_buyer_orders():
    df = pd.DataFrame({
        "product_name": ["Tomatoes"],
        "requested_quantity": [50.0],
        "order_date": ["2026-05-20"],
        "delivery_date": ["2026-05-15"],  # before order → reversed
    })
    result = validate_staging_df("stg_buyer_orders", df, today=_TODAY)
    assert not result.ok


def test_unparseable_required_date_rejected():
    df = pd.DataFrame({
        "product_name": ["Tomatoes"],
        "delivery_date": ["not-a-date"],
        "ordered_quantity": [100.0],
    })
    result = validate_staging_df("stg_supplier_deliveries", df, today=_TODAY)
    assert not result.ok
    assert any("delivery_date" in e and "unparseable" in e for e in result.errors)


def test_unparseable_optional_date_warns_only():
    df = pd.DataFrame({
        "product_name": ["Tomatoes"],
        "quantity_on_hand": [80.0],
        "expiration_date": ["garbled"],
    })
    result = validate_staging_df("stg_inventory_lots", df, today=_TODAY)
    assert result.ok  # loads
    assert any("expiration_date" in w for w in result.warnings)


def test_unknown_unit_warns_only():
    df = pd.DataFrame({
        "product_name": ["Tomatoes"],
        "quantity_on_hand": [80.0],
        "unit": ["pallets-of-mystery"],
    })
    result = validate_staging_df("stg_inventory_lots", df, today=_TODAY)
    assert result.ok
    assert any("unit" in w for w in result.warnings)


def test_implausible_magnitude_warns_only():
    df = pd.DataFrame({
        "product_name": ["Tomatoes"],
        "requested_quantity": [5_000_000.0],  # 5,000 tonnes in one order line
    })
    result = validate_staging_df("stg_buyer_orders", df, today=_TODAY)
    assert result.ok
    assert any("requested_quantity" in w for w in result.warnings)


def test_error_messages_name_rows():
    """Messages must be actionable: name the column and example rows."""
    df = pd.DataFrame({
        "product_name": ["A", "B", "C"],
        "delivery_date": ["2026-05-01"] * 3,
        "ordered_quantity": [10.0, -1.0, -2.0],
    })
    result = validate_staging_df("stg_supplier_deliveries", df, today=_TODAY)
    assert not result.ok
    msg = result.errors[0]
    assert "2 negative" in msg
    assert "rows" in msg


def test_empty_dataframe_passes():
    result = validate_staging_df("stg_buyer_orders", pd.DataFrame(), today=_TODAY)
    assert result.ok
    assert result.n_rows == 0


def test_quality_report_includes_violations():
    """The data-quality scorecard exposes the same validator results."""
    import duckdb
    from dashboard.lib.metrics import full_data_quality_report

    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE stg_products (product_id VARCHAR, product_name VARCHAR);
    """)
    conn.execute("""
        CREATE TABLE stg_supplier_deliveries (
            product_name VARCHAR, delivery_date DATE, ordered_quantity DOUBLE);
    """)
    conn.execute("""
        CREATE TABLE stg_inventory_lots (
            product_name VARCHAR, quantity_on_hand DOUBLE,
            arrival_date DATE, expiration_date DATE);
    """)
    conn.execute("""
        CREATE TABLE stg_buyer_orders (
            product_name VARCHAR, requested_quantity DOUBLE);
    """)
    conn.execute("""
        CREATE TABLE stg_waste_adjustments (
            product_name VARCHAR, quantity_lost DOUBLE);
    """)
    conn.execute("INSERT INTO stg_products VALUES ('P1', 'Tomatoes')")

    report = full_data_quality_report(conn)
    assert "violations" in report
    assert "stg_products" in report["violations"]
    assert report["violations"]["stg_products"]["ok"] is True
