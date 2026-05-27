"""Unit tests for dashboard/lib/diagnostic_metrics.py.

All tests use an isolated in-memory DuckDB with the staging tables created
from the migration-010 DDL. Deterministic test data is seeded programmatically
rather than reading from disk to avoid date-drift in the sample CSVs.

Fixed reference date: 2026-05-27 ("today" for the test suite).
  - near-expiry window = 2026-05-27 to 2026-05-30
  - expired = any date before 2026-05-27
"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd
import pytest

# Reference date shared across all tests
_TODAY = date(2026, 5, 27)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def stg_db():
    """In-memory DuckDB with all 5 staging tables and deterministic seed data."""
    conn = duckdb.connect(":memory:")

    # ── Create staging tables ──────────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE stg_products (
            product_id VARCHAR, product_name VARCHAR NOT NULL,
            category VARCHAR, unit VARCHAR DEFAULT 'kg',
            default_shelf_life_days INTEGER, traceability_required BOOLEAN DEFAULT FALSE
        )
    """)
    conn.execute("""
        CREATE TABLE stg_supplier_deliveries (
            delivery_id VARCHAR, supplier_id VARCHAR, supplier_name VARCHAR,
            product_id VARCHAR, product_name VARCHAR,
            delivery_date DATE,
            ordered_quantity DOUBLE, delivered_quantity DOUBLE,
            accepted_quantity DOUBLE, rejected_quantity DOUBLE,
            unit_cost DOUBLE, quality_grade VARCHAR, lot_id VARCHAR
        )
    """)
    conn.execute("""
        CREATE TABLE stg_inventory_lots (
            lot_id VARCHAR, product_id VARCHAR, product_name VARCHAR,
            supplier_id VARCHAR, quantity_on_hand DOUBLE, unit VARCHAR DEFAULT 'kg',
            arrival_date DATE, expiration_date DATE,
            warehouse_location VARCHAR, quality_grade VARCHAR,
            committed_quantity DOUBLE DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE stg_buyer_orders (
            order_id VARCHAR, buyer_id VARCHAR, buyer_name VARCHAR,
            product_id VARCHAR, product_name VARCHAR,
            order_date DATE, delivery_date DATE,
            requested_quantity DOUBLE, fulfilled_quantity DOUBLE,
            substituted_quantity DOUBLE DEFAULT 0,
            sales_price DOUBLE, required_quality_grade VARCHAR
        )
    """)
    conn.execute("""
        CREATE TABLE stg_waste_adjustments (
            adjustment_id VARCHAR, date DATE,
            product_id VARCHAR, product_name VARCHAR, lot_id VARCHAR,
            quantity_lost DOUBLE, reason VARCHAR,
            estimated_value_lost DOUBLE
        )
    """)

    # ── Seed: supplier deliveries ──────────────────────────────────────────────
    # S001 = good supplier: fill ~97%  S002 = bad supplier: fill ~62%
    conn.executemany("""
        INSERT INTO stg_supplier_deliveries
            (delivery_id, supplier_id, supplier_name, product_name,
             delivery_date, ordered_quantity, delivered_quantity,
             accepted_quantity, rejected_quantity)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        ("D1", "S001", "Good Farms",    "Tomatoes",  "2026-05-01", 500, 490, 485, 5),
        ("D2", "S001", "Good Farms",    "Cucumbers", "2026-05-05", 200, 198, 195, 3),
        ("D3", "S002", "Risky Produce", "Tomatoes",  "2026-05-03", 400, 250, 248, 2),
        ("D4", "S002", "Risky Produce", "Lettuce",   "2026-05-08", 300, 185, 180, 5),
    ])

    # ── Seed: inventory lots ──────────────────────────────────────────────────
    # LOT-A: fresh tomatoes, no issues
    # LOT-B: near-expiry tomatoes (expires 2026-05-28 = 1 day from ref date)
    # LOT-C: expired strawberries (expiry 2026-05-22 = 5 days ago)
    # LOT-D: cucumbers, complete lot
    # LOT-E: missing lot_id, missing supplier_id → traceability failure
    conn.executemany("""
        INSERT INTO stg_inventory_lots
            (lot_id, product_id, product_name, supplier_id,
             quantity_on_hand, unit, arrival_date, expiration_date, committed_quantity)
        VALUES (?, ?, ?, ?, ?, 'kg', ?, ?, ?)
    """, [
        ("LOT-A", "P001", "Tomatoes",     "S001", 200.0, "2026-05-01", "2026-06-10",  50.0),
        ("LOT-B", "P001", "Tomatoes",     "S002",  80.0, "2026-05-10", "2026-05-28",   0.0),
        ("LOT-C", "P004", "Strawberries", "S002",  30.0, "2026-05-05", "2026-05-22",   0.0),
        ("LOT-D", "P002", "Cucumbers",    "S001", 100.0, "2026-05-01", "2026-06-20",  20.0),
        (None,    "P001", "Tomatoes",     None,    40.0, "2026-05-12", "2026-06-05",   0.0),
    ])

    # ── Seed: buyer orders ─────────────────────────────────────────────────────
    # B001 = good buyer: ~97% fulfillment
    # B002 = risky buyer: ~67% fulfillment
    conn.executemany("""
        INSERT INTO stg_buyer_orders
            (order_id, buyer_id, buyer_name, product_name,
             delivery_date, requested_quantity, fulfilled_quantity,
             substituted_quantity, sales_price)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        ("O1", "B001", "Good Buyer",  "Tomatoes",  "2026-05-10", 100, 97, 3, 2.50),
        ("O2", "B001", "Good Buyer",  "Cucumbers", "2026-05-12",  80, 80, 0, 1.80),
        ("O3", "B002", "Risky Buyer", "Tomatoes",  "2026-05-10", 150, 90, 5, 2.50),
        ("O4", "B002", "Risky Buyer", "Tomatoes",  "2026-05-15", 120, 80, 0, 2.50),
        ("O5", "B002", "Risky Buyer", "Lettuce",   "2026-05-15",  90, 55, 0, 3.20),
    ])

    # ── Seed: waste adjustments ────────────────────────────────────────────────
    conn.executemany("""
        INSERT INTO stg_waste_adjustments
            (adjustment_id, date, product_name, lot_id,
             quantity_lost, reason, estimated_value_lost)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [
        ("A1", "2026-05-10", "Strawberries", "LOT-C", 20.0, "Spoilage",         140.0),
        ("A2", "2026-05-12", "Tomatoes",     None,    15.0, "Overripe",           37.5),
        ("A3", "2026-05-15", "Lettuce",      None,    10.0, "Temperature abuse",  32.0),
        ("A4", "2026-05-20", "Tomatoes",     None,     8.0, "Overripe",           None),
        # A4 has no estimated_value_lost → fallback to qty × price
    ])

    yield conn
    conn.close()


@pytest.fixture(scope="module")
def empty_db():
    """In-memory DuckDB with staging tables but NO rows — tests empty-data paths."""
    conn = duckdb.connect(":memory:")
    for ddl in [
        "CREATE TABLE stg_supplier_deliveries (delivery_id VARCHAR, supplier_id VARCHAR, supplier_name VARCHAR, product_name VARCHAR, delivery_date DATE, ordered_quantity DOUBLE, delivered_quantity DOUBLE, accepted_quantity DOUBLE, rejected_quantity DOUBLE, unit_cost DOUBLE, quality_grade VARCHAR, lot_id VARCHAR)",
        "CREATE TABLE stg_inventory_lots (lot_id VARCHAR, product_id VARCHAR, product_name VARCHAR, supplier_id VARCHAR, quantity_on_hand DOUBLE, unit VARCHAR DEFAULT 'kg', arrival_date DATE, expiration_date DATE, warehouse_location VARCHAR, quality_grade VARCHAR, committed_quantity DOUBLE DEFAULT 0)",
        "CREATE TABLE stg_buyer_orders (order_id VARCHAR, buyer_id VARCHAR, buyer_name VARCHAR, product_id VARCHAR, product_name VARCHAR, order_date DATE, delivery_date DATE, requested_quantity DOUBLE, fulfilled_quantity DOUBLE, substituted_quantity DOUBLE DEFAULT 0, sales_price DOUBLE, required_quality_grade VARCHAR)",
        "CREATE TABLE stg_waste_adjustments (adjustment_id VARCHAR, date DATE, product_id VARCHAR, product_name VARCHAR, lot_id VARCHAR, quantity_lost DOUBLE, reason VARCHAR, estimated_value_lost DOUBLE)",
    ]:
        conn.execute(ddl)
    yield conn
    conn.close()


# ── Waste Loss ────────────────────────────────────────────────────────────────

def test_waste_loss_total_usd(stg_db):
    from dashboard.lib.diagnostic_metrics import waste_loss_usd

    result = waste_loss_usd(stg_db)
    # A1 = 140.0, A2 = 37.5, A3 = 32.0; A4 has no value → fallback $1.50/kg → 12.0
    assert result["total_usd"] > 0
    assert result["n_rows"] == 4
    assert len(result["by_product"]) > 0
    assert len(result["by_reason"]) > 0


def test_waste_loss_by_product_sorted_descending(stg_db):
    from dashboard.lib.diagnostic_metrics import waste_loss_usd

    result = waste_loss_usd(stg_db)
    losses = [r["loss_usd"] for r in result["by_product"]]
    assert losses == sorted(losses, reverse=True)


def test_waste_loss_empty_returns_zeros(empty_db):
    from dashboard.lib.diagnostic_metrics import waste_loss_usd

    result = waste_loss_usd(empty_db)
    assert result["total_usd"] == 0.0
    assert result["n_rows"] == 0
    assert result["by_product"] == []
    assert result["by_reason"] == []


def test_waste_loss_estimated_value_used_when_present(stg_db):
    from dashboard.lib.diagnostic_metrics import waste_loss_usd

    result = waste_loss_usd(stg_db)
    # Strawberry loss: A1 → 140.0 (direct estimated_value_lost, not qty*price)
    strawberry = next(
        (r for r in result["by_product"] if "Straw" in str(r["product_name"])), None
    )
    assert strawberry is not None
    assert strawberry["loss_usd"] == pytest.approx(140.0, abs=1.0)


# ── Shortage Loss ─────────────────────────────────────────────────────────────

def test_shortage_loss_identifies_risky_buyer(stg_db):
    from dashboard.lib.diagnostic_metrics import shortage_loss_usd

    result = shortage_loss_usd(stg_db)
    # B002 missed qty on O3: max(150-90-5, 0)=55 and O4: max(120-80-0, 0)=40 and O5: max(90-55-0, 0)=35
    assert result["n_at_risk"] >= 3
    assert result["total_usd"] > 0


def test_shortage_loss_empty_returns_zeros(empty_db):
    from dashboard.lib.diagnostic_metrics import shortage_loss_usd

    result = shortage_loss_usd(empty_db)
    assert result["total_usd"] == 0.0
    assert result["n_at_risk"] == 0


def test_shortage_loss_by_buyer_sorted_descending(stg_db):
    from dashboard.lib.diagnostic_metrics import shortage_loss_usd

    result = shortage_loss_usd(stg_db)
    losses = [r["loss_usd"] for r in result["by_buyer"]]
    assert losses == sorted(losses, reverse=True)


# ── Supplier Reliability ──────────────────────────────────────────────────────

def test_supplier_reliability_detects_risky_supplier(stg_db):
    from dashboard.lib.diagnostic_metrics import supplier_reliability_scores

    result = supplier_reliability_scores(stg_db)
    # S002 ordered 700 total, accepted ~428 → fill rate ≈ 61% → High risk
    risky = [s for s in result["suppliers"] if s["risk_level"] == "High"]
    assert len(risky) >= 1
    assert result["n_risky"] >= 1


def test_supplier_fill_rate_capped_at_1(stg_db):
    from dashboard.lib.diagnostic_metrics import supplier_reliability_scores

    result = supplier_reliability_scores(stg_db)
    for s in result["suppliers"]:
        assert 0.0 <= s["fill_rate"] <= 1.0


def test_supplier_reliability_empty_returns_empty(empty_db):
    from dashboard.lib.diagnostic_metrics import supplier_reliability_scores

    result = supplier_reliability_scores(empty_db)
    assert result["suppliers"] == []
    assert result["n_risky"] == 0


def test_supplier_reliability_sorted_fill_rate_ascending(stg_db):
    from dashboard.lib.diagnostic_metrics import supplier_reliability_scores

    result = supplier_reliability_scores(stg_db)
    rates = [s["fill_rate"] for s in result["suppliers"]]
    assert rates == sorted(rates)


# ── Buyer Fulfillment ─────────────────────────────────────────────────────────

def test_buyer_fulfillment_detects_risky_buyer(stg_db):
    from dashboard.lib.diagnostic_metrics import buyer_fulfillment_rates

    result = buyer_fulfillment_rates(stg_db)
    # B002: total_requested=360, total_fulfilled=225 → rate≈0.625 → High
    risky = [b for b in result["buyers"] if b["risk_level"] == "High"]
    assert len(risky) >= 1
    assert result["n_risky"] >= 1


def test_buyer_fulfillment_rates_sum_to_one(stg_db):
    from dashboard.lib.diagnostic_metrics import buyer_fulfillment_rates

    result = buyer_fulfillment_rates(stg_db)
    for b in result["buyers"]:
        total = b["fulfillment_rate"] + b["substitution_rate"] + b["missed_rate"]
        assert total == pytest.approx(1.0, abs=0.01)


def test_buyer_fulfillment_empty_returns_empty(empty_db):
    from dashboard.lib.diagnostic_metrics import buyer_fulfillment_rates

    result = buyer_fulfillment_rates(empty_db)
    assert result["buyers"] == []
    assert result["n_risky"] == 0


# ── Traceability Coverage ─────────────────────────────────────────────────────

def test_traceability_detects_incomplete_lots(stg_db):
    from dashboard.lib.diagnostic_metrics import traceability_coverage

    result = traceability_coverage(stg_db)
    # LOT-E row has lot_id=None and supplier_id=None → incomplete
    assert result["total_lots"] == 5
    assert result["complete_lots"] < 5
    assert result["completeness_pct"] < 1.0
    assert len(result["incomplete_lots"]) >= 1


def test_traceability_missing_breakdown_contains_lot_id(stg_db):
    from dashboard.lib.diagnostic_metrics import traceability_coverage

    result = traceability_coverage(stg_db)
    # The row with null lot_id should show up in missing_breakdown
    assert "lot_id" in result["missing_breakdown"]
    assert result["missing_breakdown"]["lot_id"] >= 1


def test_traceability_empty_returns_zeros(empty_db):
    from dashboard.lib.diagnostic_metrics import traceability_coverage

    result = traceability_coverage(empty_db)
    assert result["completeness_pct"] == 0.0
    assert result["total_lots"] == 0
    assert result["missing_breakdown"] == {}


# ── Available-to-Promise ──────────────────────────────────────────────────────

def test_atp_expired_stock_excluded_from_usable(stg_db):
    from dashboard.lib.diagnostic_metrics import atp_by_product

    result = atp_by_product(stg_db, as_of_date=_TODAY)
    # LOT-C (Strawberries, 30kg) expired 2026-05-22 → expired_kg=30, atp=0
    strawberry = next(
        (p for p in result["products"] if "Straw" in str(p["product_name"])), None
    )
    assert strawberry is not None
    assert strawberry["expired_kg"] == pytest.approx(30.0)
    assert strawberry["atp_kg"] == pytest.approx(0.0)


def test_atp_near_expiry_flagged(stg_db):
    from dashboard.lib.diagnostic_metrics import atp_by_product

    result = atp_by_product(stg_db, as_of_date=_TODAY)
    # LOT-B (Tomatoes, 80kg) expires 2026-05-28 = 1 day from ref date → near expiry
    tomatoes = next(
        (p for p in result["products"] if p["product_name"] == "Tomatoes"), None
    )
    assert tomatoes is not None
    assert tomatoes["near_expiry_kg"] >= 80.0


def test_atp_committed_quantity_subtracted(stg_db):
    from dashboard.lib.diagnostic_metrics import atp_by_product

    result = atp_by_product(stg_db, as_of_date=_TODAY)
    # LOT-D (Cucumbers, 100kg, committed=20) → atp=80
    cucumbers = next(
        (p for p in result["products"] if p["product_name"] == "Cucumbers"), None
    )
    assert cucumbers is not None
    assert cucumbers["atp_kg"] == pytest.approx(80.0)


def test_atp_risky_product_count(stg_db):
    from dashboard.lib.diagnostic_metrics import atp_by_product

    result = atp_by_product(stg_db, as_of_date=_TODAY)
    # Strawberries should be risky (expired, atp=0)
    assert result["n_risky"] >= 1


def test_atp_empty_returns_no_products(empty_db):
    from dashboard.lib.diagnostic_metrics import atp_by_product

    result = atp_by_product(empty_db, as_of_date=_TODAY)
    assert result["products"] == []
    assert result["n_risky"] == 0


def test_atp_subtracts_near_expiry_from_committable_quantity(stg_db):
    """Regression guard: ATP must exclude near-expiry stock.

    LOT-A (Tomatoes, 200kg, fresh, committed=50)  +
    LOT-B (Tomatoes, 80kg, expires 2026-05-28 = near-expiry, committed=0) +
    LOT-E (Tomatoes, 40kg, expires 2026-06-05 = fresh, committed=0)
    Expected for Tomatoes:
        on_hand   = 200 + 80 + 40 = 320
        expired   = 0
        near_exp  = 80
        committed = 50
        ATP       = 320 - 0 - 50 - 80 = 190   (NOT 270)
    """
    from dashboard.lib.diagnostic_metrics import atp_by_product

    result = atp_by_product(stg_db, as_of_date=_TODAY)
    tomatoes = next(p for p in result["products"] if p["product_name"] == "Tomatoes")
    assert tomatoes["near_expiry_kg"] == pytest.approx(80.0)
    assert tomatoes["committed_kg"] == pytest.approx(50.0)
    # The key assertion: ATP excludes near-expiry
    assert tomatoes["atp_kg"] == pytest.approx(190.0)


def test_atp_lot_counted_in_only_one_bucket(stg_db):
    """A single lot can be expired OR near-expiry, never both.

    LOT-C (Strawberries, 30kg) expired 2026-05-22. It must contribute to
    ``expired_kg`` and NOT to ``near_expiry_kg``.
    """
    from dashboard.lib.diagnostic_metrics import atp_by_product

    result = atp_by_product(stg_db, as_of_date=_TODAY)
    strawberry = next(p for p in result["products"] if "Straw" in str(p["product_name"]))
    assert strawberry["expired_kg"] == pytest.approx(30.0)
    assert strawberry["near_expiry_kg"] == pytest.approx(0.0)


# ── Estimated Annual Savings ──────────────────────────────────────────────────

def test_estimated_savings_annualizes_from_period():
    """With period_days=90 the function should scale period loss to a full year."""
    from dashboard.lib.diagnostic_metrics import estimated_annual_savings

    waste = {"total_usd": 1000.0}
    shortage = {"total_usd": 2000.0}
    result = estimated_annual_savings(waste, shortage, period_days=90)

    # Raw period loss preserved
    assert result["addressable_loss_usd_period"] == pytest.approx(3000.0)
    # Annualized: 3000 × (365/90) = 12166.67
    assert result["addressable_loss_usd"] == pytest.approx(12166.67, abs=0.01)
    # Backwards-compat field still resolves to the high (30%) figure
    assert result["estimated_annual_savings_usd"] == pytest.approx(12166.67 * 0.30, abs=0.01)
    assert result["reduction_pct_assumed"] == pytest.approx(0.30)


def test_estimated_savings_returns_low_high_range():
    """The output exposes a 15%–30% reduction band so the report can show a range."""
    from dashboard.lib.diagnostic_metrics import estimated_annual_savings

    waste = {"total_usd": 5000.0}
    shortage = {"total_usd": 5000.0}
    result = estimated_annual_savings(waste, shortage, period_days=365)  # already annual

    assert result["reduction_pct_low"] == pytest.approx(0.15)
    assert result["reduction_pct_high"] == pytest.approx(0.30)
    assert result["estimated_annual_savings_usd_low"] == pytest.approx(1500.0)
    assert result["estimated_annual_savings_usd_high"] == pytest.approx(3000.0)
    assert result["estimated_annual_savings_usd_low"] < result["estimated_annual_savings_usd_high"]


def test_estimated_savings_clamps_tiny_periods():
    """A 1-day sample should not extrapolate by 365×; period clamps to >= 7 days."""
    from dashboard.lib.diagnostic_metrics import estimated_annual_savings

    waste = {"total_usd": 100.0}
    shortage = {"total_usd": 0.0}
    result = estimated_annual_savings(waste, shortage, period_days=1)

    # Clamp pulls 1 → 7, so annualization factor is 365/7 ≈ 52.14, not 365
    assert result["period_days"] == 7
    assert result["annualization_factor"] == pytest.approx(365.0 / 7, abs=0.01)


def test_estimated_savings_zero_inputs():
    from dashboard.lib.diagnostic_metrics import estimated_annual_savings

    result = estimated_annual_savings({"total_usd": 0.0}, {"total_usd": 0.0}, period_days=90)
    assert result["estimated_annual_savings_usd"] == 0.0
    assert result["addressable_loss_usd"] == 0.0
    assert result["estimated_annual_savings_usd_low"] == 0.0


# ── Full Diagnostic Summary ───────────────────────────────────────────────────

def test_diagnostic_summary_keys(stg_db):
    from dashboard.lib.diagnostic_metrics import diagnostic_summary

    result = diagnostic_summary(stg_db, partner_name="Test Co", days=365)

    required_keys = [
        "partner_name", "as_of", "period_days", "row_counts",
        "waste", "shortage", "supplier", "buyer",
        "traceability", "atp", "recommendations", "savings", "top_risks",
        "total_waste_loss_usd", "total_shortage_loss_usd",
        "n_risky_suppliers", "n_risky_buyers", "n_risky_products",
        "traceability_completeness_pct",
    ]
    for key in required_keys:
        assert key in result, f"Missing key: {key}"


def test_diagnostic_summary_partner_name_preserved(stg_db):
    from dashboard.lib.diagnostic_metrics import diagnostic_summary

    result = diagnostic_summary(stg_db, partner_name="Acme Food Hub")
    assert result["partner_name"] == "Acme Food Hub"


def test_diagnostic_summary_top_risks_max_5(stg_db):
    from dashboard.lib.diagnostic_metrics import diagnostic_summary

    result = diagnostic_summary(stg_db)
    assert len(result["top_risks"]) <= 5


def test_diagnostic_summary_row_counts_present(stg_db):
    from dashboard.lib.diagnostic_metrics import diagnostic_summary

    result = diagnostic_summary(stg_db)
    counts = result["row_counts"]
    assert "stg_supplier_deliveries" in counts
    assert counts["stg_supplier_deliveries"] == 4
    assert counts["stg_inventory_lots"] == 5


# ── Period auto-detection ─────────────────────────────────────────────────────

def test_diagnostic_summary_auto_detects_period_days(stg_db):
    """When days=None, period is read from the actual date range in the data."""
    from dashboard.lib.diagnostic_metrics import diagnostic_summary

    result = diagnostic_summary(stg_db, days=None)
    # Fixture spans 2026-05-01 to 2026-05-20 across deliveries/orders/waste
    # That's 20 days inclusive
    assert result["period_days_detected"] >= 18
    assert result["period_days_detected"] <= 22
    assert result["period_days"] == result["period_days_detected"]


def test_diagnostic_summary_savings_uses_detected_period(stg_db):
    """The savings module receives the auto-detected period_days, not 365."""
    from dashboard.lib.diagnostic_metrics import diagnostic_summary

    result = diagnostic_summary(stg_db, days=None)
    savings = result["savings"]
    assert savings["period_days"] == result["period_days"]
    # Annualization factor should be > 1 since the sample is < 1 year
    assert savings["annualization_factor"] > 1.0


# ── Unvalued-row tracking ─────────────────────────────────────────────────────

def test_waste_loss_tracks_unvalued_rows(stg_db):
    """A4 has no estimated_value_lost and the fixture has no unit_cost data,
    so it must show up as unvalued rather than silently contributing $0
    via a magic-number fallback."""
    from dashboard.lib.diagnostic_metrics import waste_loss_usd

    result = waste_loss_usd(stg_db)
    # A4 (Tomatoes, 8kg, no estimated_value_lost) → unvalued in this fixture
    assert result["n_rows_unvalued"] >= 1
    assert "n_rows_unvalued" in result


def test_shortage_loss_falls_back_to_avg_product_price(empty_db):
    """When a row has no sales_price but another order for the same product
    does have one, the missing row's loss is valued at the product average."""
    from dashboard.lib.diagnostic_metrics import shortage_loss_usd

    # Seed: two orders for Tomatoes, one priced, one not
    empty_db.executemany("""
        INSERT INTO stg_buyer_orders
            (order_id, buyer_name, product_name, delivery_date,
             requested_quantity, fulfilled_quantity, sales_price)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [
        ("X1", "B1", "Tomatoes", "2026-05-10", 100, 60, 2.00),  # priced; miss=40
        ("X2", "B2", "Tomatoes", "2026-05-11", 100, 50, None),  # unpriced; miss=50 → fallback to avg $2.00
    ])
    try:
        result = shortage_loss_usd(empty_db)
        # X1: 40 × 2.00 = 80; X2: 50 × 2.00 (fallback) = 100 → total 180
        assert result["total_usd"] == pytest.approx(180.0, abs=0.01)
        assert result["n_at_risk"] == 2
        assert result["n_at_risk_unvalued"] == 0
    finally:
        empty_db.execute("DELETE FROM stg_buyer_orders")


# ── Supplier Unknown tier ─────────────────────────────────────────────────────

def test_supplier_with_no_orders_returns_unknown_tier(empty_db):
    """A supplier with no ordered_quantity history should be 'Unknown',
    not silently rated 100% fill rate."""
    from dashboard.lib.diagnostic_metrics import supplier_reliability_scores

    empty_db.executemany("""
        INSERT INTO stg_supplier_deliveries
            (delivery_id, supplier_id, supplier_name, product_name, delivery_date,
             ordered_quantity, delivered_quantity, accepted_quantity)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        # Supplier with no ordered_quantity (NULL)
        ("D-U1", "S-UNK", "Mystery Supplier", "Tomatoes", "2026-05-01", None, 100, 100),
    ])
    try:
        result = supplier_reliability_scores(empty_db)
        unknown = next(s for s in result["suppliers"] if s["supplier_id"] == "S-UNK")
        assert unknown["fill_rate"] is None
        assert unknown["risk_level"] == "Unknown"
        # Unknown suppliers excluded from n_risky
        assert result["n_unknown"] >= 1
    finally:
        empty_db.execute("DELETE FROM stg_supplier_deliveries")
