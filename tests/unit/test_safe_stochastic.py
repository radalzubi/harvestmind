"""Fixed schedules, time-varying supply, anchoring, CVaR regret, DRO, VSS/EVPI."""
from __future__ import annotations

import pandas as pd
import pyomo.environ as pyo
import pytest

from optimization.multi_period_sp import MultiPeriodStochasticLP
from optimization.safe_stochastic import AnchorConfig, regret_summary, solve_anchored, solve_dro
from optimization.vss_evpi import value_of_information

T = 4
P = ("A",)


def _scen(paths):
    n = len(paths)
    return pd.DataFrame([{"scenario_index": w, "scenario_weight": 1 / n, "product_id": "A",
                          "period": t, "demand_kg": float(paths[w][t])} for w in range(n) for t in range(T)])


def _sup(cap=400.0):
    return pd.DataFrame([{"supplier_id": "S", "product_id": "A", "capacity_kg": cap, "price_per_kg": 2.0}])


def _kw(unmet=1.0, holding=0.02, waste=2.0):
    return dict(n_periods=T, spot_cost_multiplier=1.0, spot_capacity_factor=0.0,
                holding_cost_by_product={"A": holding}, unmet_cost_by_product={"A": unmet},
                waste_cost_by_product={"A": waste}, decay_rate_by_product={"A": 0.0})


SCEN = _scen([[100, 120, 90, 110], [140, 80, 130, 100], [60, 150, 110, 90]])
LEADS = {(w, "S"): 1 for w in range(3)}


class TestFixedAndTimeVaryingSupply:
    def test_fixed_schedule_reproduces_the_optimum_cost(self):
        r = MultiPeriodStochasticLP(**_kw()).solve(SCEN, _sup(), lead_times=LEADS)
        f = MultiPeriodStochasticLP(**_kw(), fixed_schedule=r["x"]).solve(SCEN, _sup(), lead_times=LEADS)
        assert f["usable"] and f["expected_cost"] == pytest.approx(r["expected_cost"], rel=1e-6)
        for k in r["x"]:
            assert f["x"][k] == pytest.approx(r["x"][k], abs=1e-6)

    def test_period_specific_lead_wins_over_scenario_lead(self):
        """A lead of 3 at placement period 0 means nothing ordered at t=0
        can arrive before t=3
        inventory in t=1,2 must come from elsewhere."""
        scen = _scen([[0, 100, 100, 100]])
        leads = {(0, "S"): 1, (0, "S", 0): 3}
        r = MultiPeriodStochasticLP(**_kw(unmet=50.0)).solve(scen, _sup(), lead_times=leads)
        m = r["model"]
        # order at t=0 lands at t=3; t=1 demand can only be met by an order at t=0 with lead 1 -> impossible
        assert pyo.value(m.u["A", 1, 0]) == pytest.approx(100.0, abs=1e-6)
        assert pyo.value(m.u["A", 2, 0]) == pytest.approx(0.0, abs=1e-6)   # order at t=1, lead 1

    def test_period_specific_fill_applies_at_placement(self):
        scen = _scen([[0, 100, 0, 0]])
        fills = {(0, "S"): 1.0, (0, "S", 0): 0.5}
        r = MultiPeriodStochasticLP(**_kw(unmet=50.0)).solve(scen, _sup(), lead_times={(0, "S"): 1},
                                                            yield_scenarios=fills)
        assert r["x"][("S", "A", 0)] == pytest.approx(200.0, abs=1e-6)   # grossed up for the 50% fill


class TestAnchoringAndRegret:
    def test_zero_penalty_equals_plain_stochastic(self):
        plain = MultiPeriodStochasticLP(**_kw()).solve(SCEN, _sup(), lead_times=LEADS)
        base = {k: 0.0 for k in plain["x"]}
        anch = solve_anchored(_kw(), SCEN, _sup(), baseline_schedule=base,
                              anchor=AnchorConfig(rho_by_product={"A": 0.0}), lead_times=LEADS, yield_scenarios={})
        assert anch["expected_cost"] == pytest.approx(plain["expected_cost"], rel=1e-6)

    def test_large_penalty_returns_the_baseline(self):
        base = {("S", "A", t): 100.0 for t in range(T)}
        anch = solve_anchored(_kw(), SCEN, _sup(), baseline_schedule=base,
                              anchor=AnchorConfig(rho_by_product={"A": 1e4}), lead_times=LEADS, yield_scenarios={})
        assert anch["usable"] and anch["anchored"]
        for k, v in base.items():
            assert anch["x"][k] == pytest.approx(v, abs=1e-6)

    def test_regret_is_relative_to_the_baseline_and_cvar_is_bounded_by_budget(self):
        base = {("S", "A", t): 100.0 for t in range(T)}
        r = solve_anchored(_kw(), SCEN, _sup(), baseline_schedule=base,
                           anchor=AnchorConfig(rho_by_product={}, cvar_alpha=0.67, cvar_lambda=1.0),
                           lead_times=LEADS, yield_scenarios={})
        assert r["usable"] and r["baseline_scenario_costs"]
        for w, reg in r["regret_by_scenario"].items():
            assert reg == pytest.approx(r["scenario_costs"][w] - r["baseline_scenario_costs"][w], abs=1e-6)
        s = regret_summary(r["regret_by_scenario"], r["scenario_weights"], alpha=0.67)
        assert s["worst_regret"] >= s["expected_regret"] >= s["best_regret"]
        # a hard budget at zero regret CVaR forces a decision no worse than baseline in the tail
        b = solve_anchored(_kw(), SCEN, _sup(), baseline_schedule=base,
                           anchor=AnchorConfig(rho_by_product={}, cvar_alpha=0.67, cvar_budget=0.0),
                           lead_times=LEADS, yield_scenarios={})
        assert b["usable"]
        if not b.get("budget_relaxed"):
            assert b["regret_cvar"] <= 1e-6

    def test_baseline_above_capacity_is_clipped_for_the_reference(self):
        """The incumbent is evaluated the way the settlement treats it: an
        order above supplier capacity is clipped, not declared infeasible,
        and the clipping is reported."""
        base = {("S", "A", 0): 10_000.0}          # far above the 400 capacity
        r = solve_anchored(_kw(), SCEN, _sup(), baseline_schedule=base,
                           anchor=AnchorConfig(rho_by_product={}, cvar_lambda=1.0), lead_times=LEADS, yield_scenarios={})
        assert r["usable"] and r["baseline_scenario_costs"]
        assert any("clipped" in w for w in r["warnings"])
        clipped = MultiPeriodStochasticLP(**_kw(), fixed_schedule={("S", "A", 0): 400.0}).solve(SCEN, _sup(), lead_times=LEADS)
        for w, c in clipped["scenario_costs"].items():
            assert r["baseline_scenario_costs"][w] == pytest.approx(c, rel=1e-6)


class TestDRO:
    def test_radius_zero_is_nominal(self):
        plain = MultiPeriodStochasticLP(**_kw()).solve(SCEN, _sup(), lead_times=LEADS)
        d = solve_dro(_kw(), SCEN, _sup(), radius=0.0, lead_times=LEADS, yield_scenarios={})
        assert d["expected_cost"] == pytest.approx(plain["expected_cost"], rel=1e-6)

    def test_positive_radius_never_lowers_worst_case_and_reports_history(self):
        d = solve_dro(_kw(), SCEN, _sup(), radius=0.3, lead_times=LEADS, yield_scenarios={})
        assert d["usable"] and d["candidate"] == "dro"
        assert d["worst_case_expected_cost"] >= d["nominal_expected_cost"] - 1e-6
        assert all(h["worst_weights_tv"] <= 0.3 + 1e-6 for h in d["dro_history"])

    def test_bad_radius_rejected(self):
        with pytest.raises(ValueError):
            solve_dro(_kw(), SCEN, _sup(), radius=1.5, lead_times=LEADS, yield_scenarios={})


class TestVSSEVPI:
    def test_sign_conventions_hold(self):
        iv = value_of_information(_kw(unmet=3.0), SCEN, _sup(), LEADS, {})
        assert iv.vss >= 0 and iv.evpi >= 0
        assert iv.eev >= iv.rp >= iv.ws - 1e-9
        assert iv.classification in ("LOW_INFORMATION_VALUE", "LOW_VSS", "HIGH_VSS", "HIGH_VSS_LOW_CONFIDENCE")

    def test_no_uncertainty_means_no_value(self):
        same = _scen([[100, 120, 90, 110]] * 3)
        iv = value_of_information(_kw(), same, _sup(), LEADS, {})
        assert iv.vss == pytest.approx(0.0, abs=1e-6) and iv.evpi == pytest.approx(0.0, abs=1e-6)
        assert iv.classification == "LOW_INFORMATION_VALUE"

    def test_more_asymmetric_costs_raise_vss(self):
        low = value_of_information(_kw(unmet=0.05), SCEN, _sup(), LEADS, {})
        high = value_of_information(_kw(unmet=20.0), SCEN, _sup(), LEADS, {})
        assert high.vss >= low.vss - 1e-9
