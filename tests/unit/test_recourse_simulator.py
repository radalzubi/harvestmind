"""Unit tests for optimization.recourse_simulator."""

from __future__ import annotations

import pandas as pd

from optimization.recourse_simulator import simulate_recourse


def _supply(*rows):
    return pd.DataFrame(
        rows,
        columns=["supplier_id", "product_id", "actual_available_kg"],
    )


def test_perfectly_covered_demand_has_no_spot_or_waste():
    commit = pd.DataFrame([{
        "supplier_id": "S1", "product_id": "P1",
        "committed_kg": 100.0, "price_per_kg": 2.0,
    }])
    demand = pd.DataFrame([{"product_id": "P1", "demand_kg": 100.0}])
    supply = _supply(("S1", "P1", 100.0))

    rec = simulate_recourse(commit, demand, supply)
    assert rec["spot_kg"] == 0
    assert rec["waste_kg"] == 0
    assert rec["service_level_pct"] == 100.0
    assert rec["commit_cost"] == 200.0  # 100 kg × $2


def test_undersupply_triggers_spot():
    commit = pd.DataFrame([{
        "supplier_id": "S1", "product_id": "P1",
        "committed_kg": 60.0, "price_per_kg": 2.0,
    }])
    demand = pd.DataFrame([{"product_id": "P1", "demand_kg": 100.0}])
    supply = _supply(("S1", "P1", 60.0))

    rec = simulate_recourse(commit, demand, supply, spot_cost_multiplier=1.5)
    assert rec["spot_kg"] == 40.0
    # 40 × 2.0 (default sp) × 1.5 = 120
    assert rec["spot_cost"] == 120.0
    assert rec["service_level_pct"] == 100.0  # spot fills the gap


def test_oversupply_creates_waste():
    commit = pd.DataFrame([{
        "supplier_id": "S1", "product_id": "P1",
        "committed_kg": 100.0, "price_per_kg": 2.0,
    }])
    demand = pd.DataFrame([{"product_id": "P1", "demand_kg": 60.0}])
    supply = _supply(("S1", "P1", 100.0))

    rec = simulate_recourse(commit, demand, supply, waste_cost_per_kg=0.5)
    assert rec["spot_kg"] == 0
    assert rec["waste_kg"] == 40.0
    assert rec["waste_cost"] == 20.0  # 40 × 0.5


def test_capacity_caps_committed_quantity():
    """If realised cap is below the commitment, only the cap is received."""
    commit = pd.DataFrame([{
        "supplier_id": "S1", "product_id": "P1",
        "committed_kg": 100.0, "price_per_kg": 2.0,
    }])
    demand = pd.DataFrame([{"product_id": "P1", "demand_kg": 100.0}])
    supply = _supply(("S1", "P1", 70.0))  # supplier failed to deliver in full

    rec = simulate_recourse(commit, demand, supply)
    assert rec["spot_kg"] == 30.0
    assert rec["commit_cost"] == 140.0  # 70 kg actually received × $2


def test_zero_demand_returns_full_service_level():
    commit = pd.DataFrame(columns=["supplier_id", "product_id", "committed_kg", "price_per_kg"])
    demand = pd.DataFrame([{"product_id": "P1", "demand_kg": 0.0}])
    supply = _supply(("S1", "P1", 50.0))

    rec = simulate_recourse(commit, demand, supply)
    assert rec["service_level_pct"] == 100.0
    assert rec["spot_kg"] == 0
    assert rec["waste_kg"] == 0


def test_uses_passed_spot_price():
    commit = pd.DataFrame(columns=["supplier_id", "product_id", "committed_kg", "price_per_kg"])
    demand = pd.DataFrame([{"product_id": "P1", "demand_kg": 50.0}])
    supply = _supply(("S1", "P1", 0.0))
    spot_prices = pd.DataFrame([{"product_id": "P1", "avg_price": 4.0}])

    rec = simulate_recourse(
        commit, demand, supply,
        spot_price=spot_prices, spot_cost_multiplier=1.0,
    )
    assert rec["spot_cost"] == 200.0  # 50 kg × $4 × 1.0 multiplier
