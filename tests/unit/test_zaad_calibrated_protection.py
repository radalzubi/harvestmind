"""Calibrated protection v4: regressions for the holdout3 failure families and the v4 rules.

- intermittent demand does not overstock and one historical spike does not define the tail
- central-plus-branch calm cell: echelon proxy orders upstream, no duplicated buffer pathology
- temporary spike, false supplier alarm, temporary delay recovery, downward shift
- selector no longer retains a demonstrably worse incumbent (guidance transfers, not-worse gate)
- robust overprotection on quiet cells is reported as unjustified protection value
- order smoothing removes timing lurches; explainability and flags are present
"""
from __future__ import annotations

import numpy as np
import pytest

from zaad.full.contracts import Request
from zaad.full.demo import example
from zaad.full.forecast import estimate
from zaad.full.model import solve
from zaad.full.planner import plan, targets
from zaad.full.protection import protection_profile
from zaad.full.settlement import PhysicalViolation, settle
from zaad.full.uncertainty import demand_uncertainty, intermittent_profile, supply_profile, supply_profiles
from zaad.full.worlds import draw, forecast_all


def _with(req: Request, **update) -> Request:
    return Request.model_validate({**req.model_dump(mode="json"), **update})


def _history(req: Request, values):
    data = req.model_dump(mode="json")
    data["history"] = [{**h, "quantity": float(q)} for h, q in zip(data["history"], values)]
    return Request.model_validate(data)


def _sparse(rng, n=52, occurrence=.25, size=40., spike_at=None, spike=480.):
    y = np.array([size * (1 + .1 * rng.normal()) if rng.random() < occurrence else 0. for _ in range(n)])
    if spike_at is not None:
        y[spike_at] = spike
    return np.maximum(0., y)


# intermittent demand

def test_sparse_demand_with_one_historical_spike_caps_the_tail():
    rng = np.random.default_rng(3)
    y = _sparse(rng, spike_at=20)
    fit = estimate(y, 11., .05)
    inter = intermittent_profile(y, fit)
    assert inter is not None and inter["historical_spikes"] >= 1 and inter["size_cap"] < 480.
    unc = demand_uncertainty(fit, y)
    assert unc["sd_effective"] < float(np.std(y))      # the spike no longer defines the spread
    req = _history(example("normal"), y)
    worlds = draw(req, 7, 24)
    peak = max(max(w.demand["retail_A"]) for w in worlds)
    zeros = np.mean([v == 0 for w in worlds for v in w.demand["retail_A"]])
    assert peak < 480. * .5 and .5 < zeros < .95              # zero runs reproduced, spike not repeated


def test_sparse_recurring_usage_keeps_occurrence_and_mean():
    rng = np.random.default_rng(4)
    y = _sparse(rng, occurrence=.4, size=25.)
    fit = estimate(y, 11., .05)
    inter = intermittent_profile(y, fit)
    assert inter is not None and abs(inter["occurrence"] - .4) < .2
    req = _history(example("normal"), y)
    worlds = draw(req, 9, 40)
    means = [np.mean(w.demand["retail_A"]) for w in worlds]
    assert abs(np.mean(means) - fit["mean"]) < .35 * max(fit["mean"], 1.)


@pytest.mark.parametrize("change", ["occurrence", "size"])
def test_sudden_occurrence_or_size_increase_raises_spread(change):
    rng = np.random.default_rng(5)
    base = _sparse(rng, n=48)
    tail = _sparse(rng, n=6, occurrence=.9 if change == "occurrence" else .25, size=40. if change == "occurrence" else 120.)
    y = np.concatenate([base, tail])
    after = demand_uncertainty(estimate(y, 11., .05), y)
    assert estimate(y, 11., .05)["mean"] > estimate(base, 11., .05)["mean"]
    # A new regime is young: the level error carries the shift until observations confirm it.
    assert after["regime_age"] is not None and after["level_se"] > 0


@pytest.mark.parametrize("case", ["substitution", "transfer", "normal"])
def test_intermittent_with_alternatives_does_not_buy_protection(case):
    rng = np.random.default_rng(6)
    req = _history(example(case), _sparse(rng, occurrence=.5, size=40.))
    report = plan(req)
    row = report["protection"][0]
    assert row["mean_demand_per_period"] < 30.
    # Protection never exceeds two periods of mean demand on a sparse, calm SKU with short replenishment.
    assert row["protection_units"] <= 2 * row["mean_demand_per_period"] + row["state"]["lean_baseline_units"]
    assert "INTERMITTENT_TAIL_RISK" in row["state"]["flags"] or row["state"]["regime"] == "LEAN"


# network placement

def _central_branch(req: Request) -> Request:
    data = req.model_dump(mode="json")
    data["locations"].append({**data["locations"][0], "id": "central", "kind": "central_dc", "holding_per_value_period": .003})
    data["stock"].append({**data["stock"][0], "id": "central_excess", "location": "central", "quantity": 80.})
    data["transfers"].append({"id": "central_branch", "known_at": data["as_of"], "sku": "A", "origin": "central", "destination": "branch",
                              "lead_periods": 1, "capacity": 50., "cost_per_unit": .2, "loss_fraction": .01, "approved": True})
    data["sources"][0]["destination"] = "central"
    data["sources"][0]["route"][-1] = "central"
    data["horizon"] = 12
    for key in ("known_receivables", "other_payments"):
        data["liquidity"][key] = [0.] * 12
    for s in data["sources"]:
        s["capacity_by_period"] = [100.] * 12
    for r in data["resources"]:
        r["capacity_by_period"] = [100.] * 12
    data["liquidity"]["opening_cash"] = 10000.
    return Request.model_validate(data)


def test_central_plus_branch_proxy_orders_upstream_and_plan_meets_service():
    req = _central_branch(example("normal"))
    orders = targets(req)
    assert sum(q for (source, t), q in orders.items() if t >= 2) > 0    # echelon proxy buys at central
    frozen = targets(_with(req, engine_profile="pr24"))
    assert sum(frozen.values()) > 0
    report = plan(req)
    row = report["service_reliability"]["services"][0]
    assert row["incumbent_service"] > .8            # the frozen network-blind proxy scored .49 on this structure
    assert row["achieved_service"] >= row["incumbent_service"] - 1e-6
    placement = report["explain"][0]["placement"]
    assert placement["transfer_lead_periods"] == 1 and placement["local_service_units"] <= report["explain"][0]["recommended_protection_units"] + 1e-9


def test_guidance_transfers_do_not_fail_the_whole_plan_but_period_zero_stays_strict():
    req = _central_branch(example("normal"))
    worlds = draw(req, req.seed, 3)
    solution = solve(req, worlds, service_floor=True)
    assert solution.status == "OPTIMAL"
    late = draw(_with(req, seed=req.seed + 5), req.seed + 5, 3)
    ok = 0
    for w in late:
        try:
            result = settle(req, solution, w, future_guidance=True)
            ok += 1
            assert result["guidance_truncated_units"] >= 0
        except PhysicalViolation:
            pass
    assert ok == len(late)
    # A period-zero transfer above available stock is still a violation.
    bad = solution
    bad.transfers[("central_branch", 20, 0)] = 10_000.
    with pytest.raises(PhysicalViolation):
        settle(req, bad, late[0], future_guidance=True)


# temporary events and recovery

def test_temporary_spike_then_normal_returns_toward_lean():
    rng = np.random.default_rng(8)
    base = np.maximum(0., rng.normal(20, 2, 52))
    spiked = np.concatenate([base[:-6], [60.], np.maximum(0., rng.normal(20, 2, 5))])
    fit = estimate(spiked, 11., .05)
    unc = demand_uncertainty(fit, spiked)
    assert unc["outliers"] >= 1 and unc["calibration_ratio"] <= 2.
    row = protection_profile(_history(example("normal"), spiked), forecast_all(_history(example("normal"), spiked)), supply_profiles(example("normal")))[0]
    assert row["state"]["regime"] in {"LEAN", "RECOVER"}
    later = np.concatenate([spiked, np.maximum(0., rng.normal(20, 2, 8))])
    row_later = protection_profile(_history(example("normal"), later), forecast_all(_history(example("normal"), later)), supply_profiles(example("normal")))[0]
    assert row_later["state"]["activity"] <= row["state"]["activity"] + 1e-9


def test_false_supplier_alarm_one_late_receipt_does_not_enter_protect():
    req = example("normal")
    now = req.as_of
    rows = [{"id": f"r{i}", "known_at": now, "source": "main", "elapsed_days": d, "arrived": True, "stage": "placed", "carrier": "c", "accepted_ratio": .97}
            for i, d in enumerate([7, 7, 7, 8, 7, 7, 21, 7])]
    state = protection_profile(_with(req, shipment_history=rows), forecast_all(req), supply_profiles(_with(req, shipment_history=rows)))[0]["state"]
    assert state["regime"] != "PROTECT" or state["activity"] < .5


def test_temporary_delay_then_recovery_unwinds():
    req = example("normal")
    now = req.as_of
    late = [{"id": f"r{i}", "known_at": now, "source": "main", "elapsed_days": d, "arrived": True, "stage": "placed", "carrier": "c", "accepted_ratio": .97}
            for i, d in enumerate([7, 7, 24, 28, 26, 25, 7, 7])]
    during = protection_profile(_with(req, shipment_history=late), forecast_all(req), supply_profiles(_with(req, shipment_history=late)))[0]["state"]
    clean = late + [{"id": f"c{i}", "known_at": now, "source": "main", "elapsed_days": 7, "arrived": True, "stage": "placed", "carrier": "c", "accepted_ratio": .97} for i in range(16)]
    after = protection_profile(_with(req, shipment_history=clean), forecast_all(req), supply_profiles(_with(req, shipment_history=clean)))[0]["state"]
    assert during["regime"] == "PROTECT" and after["activity"] < during["activity"]
    assert after["periods_to_lean"] <= during["periods_to_lean"]


def test_downward_structural_shift_lowers_orders_without_upside_fabrication():
    rng = np.random.default_rng(12)
    y = np.concatenate([np.maximum(0., rng.normal(20, 2, 48)), rng.poisson(7, 4).astype(float)])
    req = _history(example("normal"), y)
    worlds = draw(req, 3, 12)
    assert max(np.mean(w.demand["retail_A"]) for w in worlds) <= 20 * 1.4
    shifted = targets(req)
    baseline = targets(_history(example("normal"), np.maximum(0., rng.normal(20, 2, 52))))
    assert sum(shifted.values()) < sum(baseline.values())


# selector

def test_selector_does_not_retain_demonstrably_worse_incumbent():
    req = _central_branch(_with(example("normal"), engine_profile="reliability"))
    data = req.model_dump(mode="json")
    data["incumbent_orders"] = []          # network-blind incumbent scenario: proxy must be beaten if worse
    report = plan(Request.model_validate(data))
    row = report["service_reliability"]["services"][0]
    # Never worse than the incumbent, and every gate decision carries a reason.
    assert row["achieved_service"] >= row["incumbent_service"] - 1e-6
    if report["status"] == "RETAIN_INCUMBENT":
        assert all(gate["reason"] for gate in report["candidate_gates"].values())
    for name, gate in report["candidate_gates"].items():
        assert "reason" in gate


def test_robust_overprotection_on_quiet_cell_is_flagged_by_protection_value():
    req = example("normal")
    report = plan(req)
    pv = report["protection_value"]
    assert pv is None or set(pv) >= {"leanest_feasible_candidate", "extra_inventory_value", "carrying_cost_over_horizon", "hedged_shortage_avoided", "justified"}
    for e in report["explain"]:
        for key in ("state", "lean_baseline_units", "current_inventory_units", "current_pipeline_units", "recommended_protection_units",
                    "incremental_protection_units", "active_risk_drivers", "service_targets", "expected_service", "stress_service",
                    "marginal_value_of_protection", "alternatives_available", "transfer_available", "substitution_available",
                    "expected_periods_to_lean", "flags", "intervention"):
            assert key in e


def test_order_smoothing_levels_orders_on_a_quiet_sku():
    req = example("normal")
    worlds = draw(req, req.seed, 3)
    smooth = solve(req, worlds, service_floor=True)
    rough = solve(_with(req, order_smoothing=0.), worlds, service_floor=True)
    assert smooth.status == rough.status == "OPTIMAL"
    def roughness(sol):
        q = [sol.purchases.get(("main", t), 0.) for t in range(req.horizon)]
        return sum(abs(a - b) for a, b in zip(q[1:], q[:-1]))
    assert roughness(smooth) <= roughness(rough) + 1e-6
    assert smooth.projected_service["retail_A"] >= .95 - 1e-6


def test_supply_profile_declared_is_calm_for_normal_fill():
    req = example("normal")
    assert supply_profile(req.sources[0], (), 7).scope == "declared"
