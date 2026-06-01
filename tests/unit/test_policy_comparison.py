"""Tests for backtesting/policy_comparison.py."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pytest

from backtesting.policy_comparison import compare_policies

ROOT = Path(__file__).resolve().parents[2]
_TODAY = date(2026, 5, 27)


@pytest.fixture(scope="module")
def sample_db():
    """Loads the bundled sample dataset, the same data used in demos."""
    from ingestion.csv_ingestor import ingest_csv, COLUMN_MAPS

    conn = duckdb.connect(":memory:")
    mig = (ROOT / "db" / "migrations" / "010_diagnostic_staging.sql").read_text()
    for stmt in mig.split(";"):
        if stmt.strip():
            try:
                conn.execute(stmt)
            except Exception:
                pass
    samples = ROOT / "data" / "samples"
    for table, dcols in [
        ("stg_products", []),
        ("stg_supplier_deliveries", ["delivery_date"]),
        ("stg_inventory_lots", ["arrival_date", "expiration_date"]),
        ("stg_buyer_orders", ["order_date", "delivery_date"]),
        ("stg_waste_adjustments", ["date"]),
    ]:
        ingest_csv(samples / f"{table}.csv", table, conn,
                   column_map=COLUMN_MAPS.get(table, {}), date_cols=dcols,
                   if_exists="replace")
    yield conn
    conn.close()


def test_comparison_runs_and_has_summary(sample_db):
    result = compare_policies(sample_db, as_of_date=_TODAY, lead_time_days=3)
    assert "total_realized_loss_usd" in result
    assert "total_estimated_avoided_usd" in result
    assert "estimated_reduction_pct" in result
    assert len(result["products"]) > 0


def test_avoided_never_exceeds_realized(sample_db):
    # The core honesty guarantee: you cannot avoid more than actually occurred.
    result = compare_policies(sample_db, as_of_date=_TODAY, lead_time_days=3)
    assert result["total_estimated_avoided_usd"] <= result["total_realized_loss_usd"] + 1e-6
    for row in result["products"]:
        assert row["estimated_avoided_usd"] <= row["realized_loss_usd"] + 1e-6
        assert 0.0 <= row["covered_fraction"] <= 1.0


def test_reduction_pct_in_unit_range(sample_db):
    result = compare_policies(sample_db, as_of_date=_TODAY, lead_time_days=3)
    assert 0.0 <= result["estimated_reduction_pct"] <= 1.0


def test_longer_lead_time_is_more_conservative(sample_db):
    # A longer delivery lead time discounts more near-expiry stock, so the new
    # policy holds back at least as much.
    short = compare_policies(sample_db, as_of_date=_TODAY, lead_time_days=1)
    long = compare_policies(sample_db, as_of_date=_TODAY, lead_time_days=7)
    short_hold = sum(r["extra_holdback_kg"] for r in short["products"])
    long_hold = sum(r["extra_holdback_kg"] for r in long["products"])
    assert long_hold >= short_hold - 1e-6
