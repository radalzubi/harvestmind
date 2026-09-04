"""Trust regions and plan-stability inside the MILP, and the engine's
leakage guard at fold origins."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from optimization.multi_period_sp import MultiPeriodStochasticLP

T = 4


def _scen(paths):
    n = len(paths)
    return pd.DataFrame([{"scenario_index": w, "scenario_weight": 1 / n, "product_id": "A",
                          "period": t, "demand_kg": float(paths[w][t])} for w in range(n) for t in range(T)])


def _sup(cap=400.0):
    return pd.DataFrame([{"supplier_id": "S", "product_id": "A", "capacity_kg": cap, "price_per_kg": 2.0}])


def _kw(unmet=5.0, holding=0.02, waste=2.0, **extra):
    d = dict(n_periods=T, spot_cost_multiplier=1.0, spot_capacity_factor=0.0,
             holding_cost_by_product={"A": holding}, unmet_cost_by_product={"A": unmet},
             waste_cost_by_product={"A": waste}, decay_rate_by_product={"A": 0.0})
    d.update(extra)
    return d


SCEN = _scen([[100, 120, 90, 110], [140, 80, 130, 100], [60, 150, 110, 90]])
LEADS = {(w, "S"): 1 for w in range(3)}
BASE = {("S", "A", t): 50.0 for t in range(T)}          # a lean incumbent the optimizer wants to leave


class TestTrustRegion:
    def test_bounds_hold_per_key(self):
        free = MultiPeriodStochasticLP(**_kw()).solve(SCEN, _sup(), lead_times=LEADS)
        r = MultiPeriodStochasticLP(**_kw(baseline_schedule=BASE, trust_region_by_product={"A": 0.2})).solve(
            SCEN, _sup(), lead_times=LEADS)
        assert r["usable"] and r["trust_region"] == {"A": 0.2}
        for k, b in BASE.items():
            assert b * 0.8 - 1e-6 <= r["x"][k] <= b * 1.2 + 1e-6
        # the unconstrained solve wanted more than the region allows
        assert sum(free["x"].values()) > sum(r["x"].values()) + 1.0

    def test_wider_region_costs_no_more(self):
        tight = MultiPeriodStochasticLP(**_kw(baseline_schedule=BASE, trust_region_by_product={"A": 0.1})).solve(
            SCEN, _sup(), lead_times=LEADS)
        wide = MultiPeriodStochasticLP(**_kw(baseline_schedule=BASE, trust_region_by_product={"A": 0.8})).solve(
            SCEN, _sup(), lead_times=LEADS)
        assert wide["expected_cost"] <= tight["expected_cost"] + 1e-6

    def test_zero_baseline_allows_one_lot(self):
        base0 = {("S", "A", t): 0.0 for t in range(T)}
        r = MultiPeriodStochasticLP(**_kw(baseline_schedule=base0, trust_region_by_product={"A": 0.5})).solve(
            SCEN, _sup(), lead_times=LEADS)
        assert r["usable"] and max(r["x"].values()) <= 1.0 + 1e-6      # one lot


class TestPlanStability:
    def test_change_cost_reduces_churn_against_previous_plan(self):
        prev = {("S", "A", t): 100.0 for t in range(T)}
        free = MultiPeriodStochasticLP(**_kw()).solve(SCEN, _sup(), lead_times=LEADS)
        stable = MultiPeriodStochasticLP(**_kw(previous_schedule=prev, change_cost_by_product={"A": 3.0})).solve(
            SCEN, _sup(), lead_times=LEADS)
        churn = lambda x: sum(abs(x.get(k, 0.0) - prev[k]) for k in prev)  # noqa: E731
        assert stable["usable"] and stable["plan_stabilised"]
        assert churn(stable["x"]) < churn(free["x"])

    def test_zero_change_cost_is_the_free_problem(self):
        prev = {("S", "A", t): 100.0 for t in range(T)}
        free = MultiPeriodStochasticLP(**_kw()).solve(SCEN, _sup(), lead_times=LEADS)
        z = MultiPeriodStochasticLP(**_kw(previous_schedule=prev, change_cost_by_product={"A": 0.0})).solve(
            SCEN, _sup(), lead_times=LEADS)
        assert not z["plan_stabilised"]
        assert z["expected_cost"] == pytest.approx(free["expected_cost"], rel=1e-6)


class TestEngineLeakage:
    def test_estimate_sees_only_events_before_origin(self):
        from adaptive.engine import estimate
        from backtesting.counterfactual import FoldInputs
        from domain.model import fmcg_policy
        pol = fmcg_policy({})
        good = {t: (0.96, 2) for t in range(-40, 0)}          # keys are relative to the origin
        # a catastrophe recorded AT and AFTER the origin must be invisible
        leaky = dict(good)
        for t in range(0, 20):
            leaky[t] = (0.30, 6)
        kw = dict(horizon=8, products=["A"], supplier_of={"A": "S"}, lead_of={"S": 2},
                  train_demand={"A": [100.0] * 40}, train_fill={"S": [0.96]}, unit_cost={"A": 1.0},
                  margin={"A": 0.3}, capacity={"A": 1000.0}, opening={"A": 200.0}, pipeline={}, policy=pol)
        a = estimate(FoldInputs(origin=40, supply_events={"S": good}, **kw))
        b = estimate(FoldInputs(origin=40, supply_events={"S": leaky}, **kw))
        assert a.supplier["S"].probabilities == b.supplier["S"].probabilities
        assert b.supplier["S"].p_disruptive() < 0.3
        # the same events BEFORE the origin are seen
        seen = dict(good)
        for t in range(-10, 0):
            seen[t] = (0.30, 6)
        c = estimate(FoldInputs(origin=40, supply_events={"S": seen}, **kw))
        assert c.supplier["S"].p_disruptive() > 0.6
        assert c.posture.commit_window < a.posture.commit_window
        assert c.posture.cvar_lambda > a.posture.cvar_lambda


class TestAdaptiveCandidateEndToEnd:
    def test_adaptive_sp_solves_and_reports_posture(self):
        from backtesting.counterfactual import EXTRA_CANDIDATES
        from scripts.run_fmcg_counterfactuals import fold_from_history
        from synthetic.fmcg.distributor_sim import build_history
        h = build_history("C_constrained_supplier", seed=3)
        fi, _ = fold_from_history(h, 60, 8, 52, 2.0, 0.95, 0.02 / 4.33)
        sched, meta = EXTRA_CANDIDATES["adaptive_sp"](fi, None, np.random.default_rng(0), 10)
        assert meta["candidate"] == "adaptive_sp" and "posture" in meta
        assert sched is not None and all(v >= 0 for v in sched.values())
        assert meta["anchored"]
        assert meta["posture"]["mode"] in ("EFFICIENCY", "BALANCED", "PROTECTION")
        if meta["posture"]["mode"] != "EFFICIENCY":
            assert meta["trust_region"]
