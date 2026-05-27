"""Unit tests for RollingOriginEngine — focused on the realized-supply window fix."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from backtesting.rolling_origin_engine import RollingOriginEngine


@pytest.fixture
def deliveries_two_years():
    """Deliveries spanning a window straddling the horizon boundary.

    Rows are placed at weekly intervals from Jan 1 → Mar 31 2025. We will
    test horizons that should pull only a subset.
    """
    rows = []
    base = date(2025, 1, 1)
    for week in range(13):  # 13 weeks of data
        d = base + timedelta(weeks=week)
        rows.append({
            "supplier_id": "S-A",
            "product_id":  "P-1",
            "delivery_date": d,
            "qty_received_kg": 100.0,
            "qty_rejected_kg": 10.0,
        })
        rows.append({
            "supplier_id": "S-B",
            "product_id":  "P-1",
            "delivery_date": d,
            "qty_received_kg": 50.0,
            "qty_rejected_kg": 0.0,
        })
    return pd.DataFrame(rows)


def test_realized_supply_uses_horizon_window_only(deliveries_two_years):
    """Critical regression: realized supply must NOT include training-window rows."""
    # 4-week horizon: weeks 9, 10, 11, 12 (Mar 5, 12, 19, 26)
    horizon_weeks = [
        date(2025, 3, 5),
        date(2025, 3, 12),
        date(2025, 3, 19),
        date(2025, 3, 26),
    ]
    realized = RollingOriginEngine._to_realized_supply(deliveries_two_years, horizon_weeks)

    # Two suppliers × one product = 2 rows
    assert len(realized) == 2

    # Supplier A: 4 weeks × (100 received - 10 rejected) = 360
    sup_a = realized[realized["supplier_id"] == "S-A"]["actual_available_kg"].iloc[0]
    assert sup_a == pytest.approx(360.0)

    # Supplier B: 4 weeks × 50 = 200 (no rejection)
    sup_b = realized[realized["supplier_id"] == "S-B"]["actual_available_kg"].iloc[0]
    assert sup_b == pytest.approx(200.0)


def test_realized_supply_excludes_pre_horizon_rows(deliveries_two_years):
    """If we ask for a 1-week horizon, only that week's deliveries should be in the total."""
    horizon_weeks = [date(2025, 2, 5)]  # exactly 1 row per supplier in that week
    # Wait — Feb 5 isn't on the weekly grid. Use Feb 5 (Wed) — the deliveries
    # are placed at Jan 1 + N*7 days, so Feb 5 falls between week 5 (Feb 5)
    # and week 6 (Feb 12). Let's use the actual grid date.
    horizon_weeks = [date(2025, 2, 12)]  # week 6 in the fixture
    realized = RollingOriginEngine._to_realized_supply(deliveries_two_years, horizon_weeks)

    # +6 days from Feb 12 = Feb 18, so the window is [Feb 12, Feb 18].
    # That contains exactly week 6 row → S-A: 90, S-B: 50
    sup_a = realized[realized["supplier_id"] == "S-A"]["actual_available_kg"].iloc[0]
    sup_b = realized[realized["supplier_id"] == "S-B"]["actual_available_kg"].iloc[0]
    assert sup_a == pytest.approx(90.0)
    assert sup_b == pytest.approx(50.0)


def test_realized_supply_empty_when_no_horizon_weeks():
    df = pd.DataFrame({
        "supplier_id": ["S-A"],
        "product_id":  ["P-1"],
        "delivery_date": [date(2025, 1, 1)],
        "qty_received_kg": [100.0],
        "qty_rejected_kg": [0.0],
    })
    assert RollingOriginEngine._to_realized_supply(df, []).empty


def test_realized_supply_empty_when_no_deliveries_in_window(deliveries_two_years):
    # Horizon entirely before the data starts
    horizon_weeks = [date(2024, 1, 1), date(2024, 1, 8)]
    result = RollingOriginEngine._to_realized_supply(deliveries_two_years, horizon_weeks)
    assert result.empty
    assert list(result.columns) == ["supplier_id", "product_id", "actual_available_kg"]


def test_realized_supply_handles_missing_rejected_column():
    """qty_rejected_kg is optional; falls back to received-only."""
    df = pd.DataFrame({
        "supplier_id": ["S-A"],
        "product_id":  ["P-1"],
        "delivery_date": [date(2025, 1, 1)],
        "qty_received_kg": [100.0],
    })
    result = RollingOriginEngine._to_realized_supply(df, [date(2025, 1, 1)])
    assert result["actual_available_kg"].iloc[0] == pytest.approx(100.0)


def test_realized_supply_clips_negative_accepted_to_zero():
    """If rejected > received (data error), accepted should be clipped to 0, not negative."""
    df = pd.DataFrame({
        "supplier_id": ["S-A"],
        "product_id":  ["P-1"],
        "delivery_date": [date(2025, 1, 1)],
        "qty_received_kg": [50.0],
        "qty_rejected_kg": [80.0],
    })
    result = RollingOriginEngine._to_realized_supply(df, [date(2025, 1, 1)])
    assert result["actual_available_kg"].iloc[0] == pytest.approx(0.0)
