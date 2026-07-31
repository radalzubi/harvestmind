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


def test_gamma_saturates_at_soyster_limit(small_demand):
    """At Γ >= n every constraint is fully protected — the Soyster (1973)
    extreme, which Bertsimas-Sim recovers at the top of the budget range."""
    demand, supply = small_demand  # 10 products × 1 week → n = 10
    at_n = GammaRobustLP(gamma=10).solve(demand, supply)
    beyond = GammaRobustLP(gamma=20).solve(demand, supply)

    assert at_n["n_fully_protected"] == 10
    assert beyond["n_fully_protected"] == 10
    assert beyond["gamma_effective"] == 10          # clipped to n
    # Total protection equals the full uncertainty budget on every product.
    expected = float(demand["demand_kg"].sum() * 0.20)
    assert at_n["total_protection_kg"] == pytest.approx(expected, rel=1e-9)
    assert beyond["objective"] == pytest.approx(at_n["objective"], rel=1e-9)


def test_gamma_protects_largest_deviations_first(small_demand):
    """Bertsimas-Sim allocates the budget to the WORST deviations, not
    uniformly. With Γ=1 exactly one product should be protected, and it
    must be the one with the largest demand (hence largest deviation)."""
    demand, supply = small_demand
    result = GammaRobustLP(gamma=1).solve(demand, supply)
    assert result["n_fully_protected"] == 1
    biggest = float(demand["demand_kg"].max()) * 0.20
    assert result["total_protection_kg"] == pytest.approx(biggest, rel=1e-9)


def test_fractional_gamma_allocates_remainder(small_demand):
    """A fractional budget protects ⌊Γ⌋ fully plus a partial next one."""
    demand, supply = small_demand
    result = GammaRobustLP(gamma=2.5).solve(demand, supply)
    assert result["n_fully_protected"] == 2
    devs = sorted(demand["demand_kg"] * 0.20, reverse=True)
    expected = devs[0] + devs[1] + 0.5 * devs[2]
    assert result["total_protection_kg"] == pytest.approx(expected, rel=1e-9)


def test_violation_bound_matches_theorem_2():
    """Bertsimas & Sim Theorem 2: Pr(violation) <= exp(-Γ²/(2n))."""
    import math

    from optimization.gamma_robust_lp import (
        gamma_for_target_risk,
        violation_probability_bound,
    )
    assert violation_probability_bound(0, 10) == pytest.approx(1.0)
    assert violation_probability_bound(4, 10) == pytest.approx(
        math.exp(-16 / 20), rel=1e-12)
    # Bound decreases as the budget grows.
    bounds = [violation_probability_bound(g, 20) for g in (0, 2, 4, 8)]
    assert all(a > b for a, b in zip(bounds, bounds[1:]))
    # Inverting the bound round-trips.
    g = gamma_for_target_risk(0.05, 20)
    assert violation_probability_bound(g, 20) == pytest.approx(0.05, rel=1e-9)
