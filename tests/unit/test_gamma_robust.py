"""Unit tests for the Γ-robust LP — guards against the free-supply arbitrage bug."""

import pandas as pd
import pytest

from optimization.gamma_robust_lp import GammaRobustLP
from optimization.lp_baseline import LPBaseline


@pytest.fixture
def small_demand():
    """10 products × 1 week, demand 100..280 kg, capacity 500/each, $2/kg."""
    products = [f"PRD-{i:03d}" for i in range(1, 11)]
    demand = pd.DataFrame([
        {"product_id": p, "week_start": "2026-01-01", "demand_kg": 100.0 + i * 20}
        for i, p in enumerate(products)
    ])
    supply = pd.DataFrame([
        {"supplier_id": "SUP-001", "product_id": p,
         "week_start": "2026-01-01", "capacity_kg": 500.0, "price_per_kg": 2.0}
        for p in products
    ])
    return demand, supply


def test_gamma_zero_matches_deterministic(small_demand):
    """Γ=0 must reduce to the deterministic LP exactly."""
    demand, supply = small_demand
    det_obj = LPBaseline().solve(demand, supply)["objective"]
    rob_obj = GammaRobustLP(gamma=0).solve(demand, supply)["objective"]
    assert rob_obj == pytest.approx(det_obj, rel=1e-6)


def test_gamma_increases_cost_monotonically(small_demand):
    """Cost must be non-decreasing as Γ grows."""
    demand, supply = small_demand
    objs = []
    for g in [0, 1, 2, 4, 8, 12]:
        result = GammaRobustLP(gamma=g).solve(demand, supply)
        assert result["status"] in ("optimal", "locallyOptimal")
        objs.append(result["objective"])
    for prev, curr in zip(objs, objs[1:]):
        assert curr >= prev - 1e-6, f"non-monotone: {objs}"


def test_no_free_supply_arbitrage(small_demand):
    """Γ-robust must never undercut the deterministic objective.

    Regression test for the bug where per-(j,t) auxiliary β variables created
    a free-supply arbitrage (cost 1/unit) that beat real spot supply (2.6/unit).
    """
    demand, supply = small_demand
    det_obj = LPBaseline().solve(demand, supply)["objective"]
    for g in [0, 1, 2, 4, 8, 12]:
        rob_obj = GammaRobustLP(gamma=g).solve(demand, supply)["objective"]
        assert rob_obj >= det_obj - 1e-6, f"Γ={g} produced ${rob_obj:.2f} < deterministic ${det_obj:.2f}"


def test_gamma_factor_saturates_at_one(small_demand):
    """gamma_factor must cap at 1.0 (full worst-case)."""
    demand, supply = small_demand  # 10 products × 1 week → n_constraints=10
    result_high = GammaRobustLP(gamma=20).solve(demand, supply)
    assert result_high["gamma_factor"] == 1.0
    result_n = GammaRobustLP(gamma=10).solve(demand, supply)
    assert result_n["gamma_factor"] == 1.0
