"""Revalidation of the single-period two-stage SP (the agriculture core).

Passing tests were not taken as proof. Each property below is recomputed
from the solved model's variables, independently of the code that built
the objective, so a bug in the formulation and a bug in the check cannot
cancel.
"""
from __future__ import annotations

import pandas as pd
import pyomo.environ as pyo
import pytest

from optimization.two_stage_sp import TwoStageStochasticLP, _normalized_weights

WK = "2026-01-05"


def _scen(demands, weights=None, products=("A",)):
    n = len(demands)
    rows = []
    for w, d in enumerate(demands):
        for j in products:
            rows.append({"scenario_index": w, "scenario_weight": (weights[w] if weights else 1 / n),
                         "product_id": j, "week_start": WK,
                         "demand_kg": float(d if not isinstance(d, dict) else d[j])})
    return pd.DataFrame(rows)


def _supply(caps: dict, price=2.0):
    return pd.DataFrame([{"supplier_id": i, "product_id": j, "week_start": WK,
                          "capacity_kg": float(c), "price_per_kg": price}
                         for (i, j), c in caps.items()])


def _model(cu=3.0, cw=1.0, **kw):
    return TwoStageStochasticLP(newsvendor_objective=True,
                                unmet_cost_by_product={"A": cu, "B": cu},
                                waste_cost_by_product={"A": cw, "B": cw}, **kw)


class TestBalanceAndSigns:
    def test_balance_holds_per_scenario_with_yield_applied_exactly_once(self):
        scen = _scen([80, 120, 160])
        sup = _supply({("S1", "A"): 100, ("S2", "A"): 100})
        fills = {(0, "S1"): 0.9, (1, "S1"): 0.7, (2, "S1"): 1.0,
                 (0, "S2"): 0.8, (1, "S2"): 0.95, (2, "S2"): 0.6}
        r = _model().solve(scen, sup, yield_scenarios=fills)
        assert r["usable"]
        m = r["model"]
        d = {int(x.scenario_index): float(x.demand_kg) for x in scen.itertuples()}
        for w in m.W:
            delivered = sum(fills[(w, i)] * pyo.value(m.x[i, "A"]) for i in ("S1", "S2"))
            lhs = delivered + pyo.value(m.s["A", w]) - pyo.value(m.w["A", w]) + pyo.value(m.u["A", w])
            assert lhs == pytest.approx(d[w], abs=1e-6)

    def test_no_negative_decisions(self):
        r = _model().solve(_scen([50, 150]), _supply({("S1", "A"): 100}))
        m = r["model"]
        for var in (m.x, m.s, m.w, m.u):
            for v in var.values():
                assert pyo.value(v) >= -1e-9

    def test_capacity_binding_never_exceeded(self):
        r = _model(cu=50.0).solve(_scen([500, 500]), _supply({("S1", "A"): 37.5}))
        assert all(v <= 37.5 + 1e-9 for v in r["x"].values())

    def test_waste_and_unmet_never_both_positive_in_a_scenario(self):
        """Holding surplus and shortage at once in the same scenario is
        never optimal with positive costs on both."""
        r = _model().solve(_scen([60, 140, 100]), _supply({("S1", "A"): 200}))
        m = r["model"]
        for w in m.W:
            assert min(pyo.value(m.w["A", w]), pyo.value(m.u["A", w])) == pytest.approx(0.0, abs=1e-6)


class TestProbability:
    def test_weights_normalise_and_complete(self):
        w = _normalized_weights({0: 2.0, 1: 6.0}, [0, 1, 2])
        assert sum(w.values()) == pytest.approx(1.0)
        assert w[2] == pytest.approx((1 / 3) / (2 + 6 + 1 / 3))
        assert all(v >= 0 for v in w.values())

    def test_objective_equals_weighted_recourse(self):
        scen = _scen([80, 120, 200], weights=[0.5, 0.3, 0.2])
        r = _model(cu=3.0, cw=1.0, spot_cost_multiplier=1.3).solve(scen, _supply({("S1", "A"): 150}))
        m = r["model"]
        premium = 2.0 * 0.3   # avg contract price x (multiplier - 1)
        expect = sum(wt * (3.0 * pyo.value(m.u["A", w]) + 1.0 * pyo.value(m.w["A", w])
                           + premium * pyo.value(m.s["A", w]))
                     for w, wt in zip(m.W, (0.5, 0.3, 0.2)))
        assert r["objective"] == pytest.approx(expect, rel=1e-6)

    def test_spot_premium_caps_the_effective_underage_cost(self):
        """With spot available at a premium below the lost margin, the model
        uses spot rather than losing the sale, so the effective underage
        cost is min(lost margin, spot premium). That is correct economics
        and it lowers the critical fractile: a reviewer expecting the pure
        newsvendor answer must switch spot off."""
        scen = _scen([80, 120, 160, 200])
        with_spot = _model(cu=3.0, cw=1.0, spot_cost_multiplier=1.3).solve(scen, _supply({("S1", "A"): 500}))
        no_spot = _model(cu=3.0, cw=1.0, spot_capacity_factor=0.0).solve(scen, _supply({("S1", "A"): 500}))
        assert with_spot["x"][("S1", "A")] < no_spot["x"][("S1", "A")]


class TestInformationTiming:
    def test_first_stage_has_no_scenario_index(self):
        r = _model().solve(_scen([80, 120]), _supply({("S1", "A"): 150}))
        assert r["model"].x.index_set().dimen == 2

    def test_commitment_does_not_change_when_scenario_order_is_permuted(self):
        a = _model().solve(_scen([80, 120, 160]), _supply({("S1", "A"): 150}))
        b = _model().solve(_scen([160, 80, 120]), _supply({("S1", "A"): 150}))
        assert a["x"][("S1", "A")] == pytest.approx(b["x"][("S1", "A")], abs=1e-6)

    def test_fixed_first_stage_cannot_beat_free_first_stage(self):
        """Evaluating a given x against the scenarios (the EEV machinery)
        must never report a lower expected cost than the optimum."""
        scen = _scen([80, 120, 160]); sup = _supply({("S1", "A"): 150})
        best = _model().solve(scen, sup)
        for xf in (60.0, 100.0, 150.0):
            fixed = _model().solve_with_fixed_first_stage(scen, sup, {("S1", "A"): xf})
            assert fixed["usable"]
            assert fixed["objective"] >= best["objective"] - 1e-6


class TestEconomics:
    def test_critical_fractile_recovered(self):
        """Newsvendor: with cu/(cu+cw) = 0.75 and three equiprobable
        scenarios, the optimal commitment is the 75th percentile demand."""
        scen = _scen([80, 120, 160, 200])
        r = _model(cu=3.0, cw=1.0, spot_capacity_factor=0.0).solve(scen, _supply({("S1", "A"): 500}))
        assert r["x"][("S1", "A")] == pytest.approx(160.0, abs=1e-6)

    def test_service_floor_is_honoured_in_expectation(self):
        scen = _scen([80, 120, 160])
        r = _model(cu=0.01, cw=5.0, service_level_floor=0.9).solve(scen, _supply({("S1", "A"): 500}))
        m = r["model"]
        exp_unmet = sum(pyo.value(m.u["A", w]) / 3 for w in m.W)
        assert exp_unmet <= 0.1 * 120 + 1e-6

    def test_deterministic_equivalence(self):
        one = _model().solve(_scen([100]), _supply({("S1", "A"): 500}))
        dup = _model().solve(_scen([100, 100, 100]), _supply({("S1", "A"): 500}))
        assert one["x"][("S1", "A")] == pytest.approx(dup["x"][("S1", "A")], abs=1e-6)
        assert one["objective"] == pytest.approx(dup["objective"], abs=1e-6)

    def test_spot_premium_exploit_closed(self):
        """Spot at no premium with unlimited capacity would make committing
        pointless; the recourse must cost at least the contract price."""
        with pytest.raises(ValueError):
            from domain.economics import CostConfig
            CostConfig(emergency_cost_multiplier=0.5)
