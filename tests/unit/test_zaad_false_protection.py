"""State-dependent protection decay: protection falls toward lean when demand and supply are
calm, replenishment is short and alternatives exist; stays high when they are not; and the
report says which driver is active, whether it is decaying and how long until lean."""
from __future__ import annotations

import numpy as np
import pytest

from zaad.full.contracts import Request
from zaad.full.demo import example
from zaad.full.forecast import estimate
from zaad.full.planner import plan
from zaad.full.protection import protection_profile
from zaad.full.uncertainty import (DEAD_BAND, demand_state, demand_uncertainty, periods_to_lean_demand, protection_activity,
                                   residual_calibration, resilience, supply_profile, supply_profiles, supply_state)
from zaad.full.worlds import draw, forecast_all


def _with(req: Request, **update) -> Request:
    return Request.model_validate({**req.model_dump(mode="json"), **update})


def _history(rng, n=52, level=20., sd=2.):
    return np.array([max(0., rng.normal(level, sd)) for _ in range(n)])


def _row(req: Request) -> dict:
    return protection_profile(req, forecast_all(req), supply_profiles(req))[0]


def _receipts(req: Request, days: list[int], ratio: float = .97) -> list[dict]:
    return [{"id": f"r{i}", "known_at": req.as_of, "source": "main", "elapsed_days": d, "arrived": True, "stage": "placed", "carrier": "c", "accepted_ratio": ratio}
            for i, d in enumerate(days)]


# stable demand / stable supply

def test_stable_demand_stable_supply_is_lean():
    req = example("normal")
    row = _row(req)
    state = row["state"]
    assert state["activity"] <= .05 and not state["risk_active"] and state["periods_to_lean"] == 0
    assert row["stance"] == "lean" and state["incremental_protection_units"] <= state["lean_baseline_units"] + 1.
    report = plan(req)
    assert report["false_protection"]["quantile_levels"]["retail_A"] == 0.
    assert report["stress_weight"] <= req.stress_weight * .1 + 1e-9


# one temporary spike then normal

def test_one_spike_does_not_widen_robust_spread_or_hold_protection():
    rng = np.random.default_rng(5)
    y = np.concatenate([_history(rng), [60.], rng.poisson(20, 6).astype(float)])
    fit = estimate(y, 11., .05, True, "symmetric")
    robust = residual_calibration(y[fit["segment_origin"]:], fit["method"], robust=True)
    rms = residual_calibration(y[fit["segment_origin"]:], fit["method"], robust=False)
    assert robust["outliers"] >= 1 and robust["residual_sd"] < rms["residual_sd"] * .8
    unc = demand_uncertainty(fit, y)
    assert unc["last_outlier_age"] == 6
    assert demand_state(unc) == 0.          # one spike is not an event; two in the window would be
    older = demand_uncertainty(fit, np.concatenate([y, rng.poisson(20, 4).astype(float)]))
    assert periods_to_lean_demand(older) <= periods_to_lean_demand(unc)
    # Scenarios drawn after the spike stay bounded: the 60 does not repopulate the futures.
    req = example("normal")
    data = req.model_dump(mode="json")
    data["history"] = [{**h, "quantity": float(q)} for h, q in zip(data["history"], y[-52:])]
    spiked = Request.model_validate(data)
    assert max(max(w.demand["retail_A"]) for w in draw(spiked, 3, 12)) < 60.


# temporary supplier delay then recovery

def test_supplier_delay_raises_supply_state_then_recovers():
    req = example("normal")
    late = _with(req, shipment_history=_receipts(req, [7, 7, 21, 28, 24, 7, 7, 26]))
    active = _row(late)["state"]
    assert active["supply_score"] > .3 and active["risk_active"] and any(d["driver"] == "supply" for d in active["active_drivers"])
    assert active["periods_to_lean"] >= 1
    recovered = _with(req, shipment_history=_receipts(req, [7, 7, 21, 28, 24, 7, 7, 26] + [7] * 12))
    calm = _row(recovered)["state"]
    assert calm["supply_score"] < active["supply_score"]
    # The stress hedge weight follows the evidence: no floor once the record is observed and clean.
    assert plan(recovered)["stress_credibility"]["floor"] == 0.


# temporary correlated route disruption then recovery (two suppliers through one port)

def test_correlated_route_disruption_protects_then_decays():
    req = example("normal")
    data = req.model_dump(mode="json")
    data["sources"].append({**data["sources"][0], "id": "alt", "supplier": "other", "route": ["other", "port", "branch"], "resources": ["alt_cap"]})
    data["resources"].append({**data["resources"][0], "id": "alt_cap", "failure_domains": []})
    shared = Request.model_validate(data)
    row = _row(shared)
    assert row["effective_independent_sources"] == pytest.approx(1.) and row["state"]["resilience"] < 1.
    # A route disruption seen in both suppliers' receipts.
    disrupted = _with(shared, shipment_history=_receipts(shared, [7, 7, 28, 35, 30, 7, 28, 7]) + [{**r, "id": "alt-" + r["id"], "source": "alt"} for r in _receipts(shared, [7, 8, 30, 33, 28, 7, 27, 7])])
    active = _row(disrupted)["state"]
    assert active["risk_active"] and active["supply_score"] > .3
    clean = [{**r, "id": "clean-" + r["id"]} for r in _receipts(disrupted, [7] * 14)]
    recovered = _with(disrupted, shipment_history=[r.model_dump() for r in disrupted.shipment_history] + clean
                      + [{**r, "id": "alt-" + r["id"], "source": "alt"} for r in clean])
    assert _row(recovered)["state"]["supply_score"] < active["supply_score"]


# sustained demand increase and decrease: the old level is a bounded alternative, not a symmetric blow-up

@pytest.mark.parametrize("factor", [1.8, .35])
def test_young_regime_is_bounded_mixture_not_symmetric_widening(factor):
    rng = np.random.default_rng(9)
    y = np.concatenate([_history(rng), rng.poisson(20 * factor, 3).astype(float)])
    fit = estimate(y, 11., .05, True, "symmetric")
    assert fit["segment_origin"] > 0
    unc = demand_uncertainty(fit, y)
    old = demand_uncertainty(fit, y, decay=False)
    assert unc["pre_change_level"] == pytest.approx(float(np.mean(y[:fit["segment_origin"]])))
    if factor < 1:
        assert 0 < unc["pre_change_weight"] <= .5
        assert unc["level_se"] < old["level_se"]       # after a drop the shift size no longer inflates the level error
    else:
        assert unc["pre_change_weight"] == 0. and unc["level_se"] == pytest.approx(old["level_se"])   # after a rise the upside is kept
    assert demand_state(unc) > .5 and periods_to_lean_demand(unc) >= 1
    # Scenario levels stay between the two regimes.
    req = example("normal")
    data = req.model_dump(mode="json")
    data["history"] = [{**h, "quantity": float(q)} for h, q in zip(data["history"], np.concatenate([_history(np.random.default_rng(9), 49), rng.poisson(20 * factor, 3).astype(float)]))]
    shifted = Request.model_validate(data)
    worlds = draw(shifted, 1, 12)
    means = [np.mean(w.demand["retail_A"]) for w in worlds]
    lo, hi = sorted([20., 20. * factor])
    assert min(means) >= lo * .6
    if factor < 1:
        assert max(means) <= hi * 1.4


def test_young_regime_ages_out():
    rng = np.random.default_rng(9)
    base = _history(rng)
    young = np.concatenate([base, rng.poisson(36, 3).astype(float)])
    mature = np.concatenate([base, rng.poisson(36, 10).astype(float)])
    u_young = demand_uncertainty(estimate(young, 11., .05), young)
    u_mature = demand_uncertainty(estimate(mature, 11., .05), mature)
    assert u_young["regime_uncertainty"] > 0 and u_mature["regime_uncertainty"] == 0
    assert demand_state(u_mature) < demand_state(u_young)


# long lead time with no alternatives vs short lead time with an alternate supplier

def test_replenishment_and_alternatives_condition_activity():
    assert resilience(2, 1., 0., 40.) == .5 and resilience(2, 2., 0., 40.) == 1. and resilience(5, 1., 0., 100.) == 0.
    assert protection_activity(.8, 0., 1.) == pytest.approx(.4) and protection_activity(.8, 0., 0.) == pytest.approx(.8)
    req = example("normal")
    data = req.model_dump(mode="json")
    data["sources"][0]["lead_days"] = 35
    data["sources"][0]["lead_sd_days"] = 10.
    slow = Request.model_validate(data)
    slow_row = _row(slow)
    assert slow_row["replenishment_periods"] >= 5 and slow_row["state"]["resilience"] == 0. and slow_row["state"]["risk_active"]
    data = req.model_dump(mode="json")
    data["sources"][0]["lead_sd_days"] = 10.
    data["sources"].append({**data["sources"][0], "id": "alt", "supplier": "other", "route": ["other", "other_port", "branch"], "resources": ["alt_cap"], "lead_sd_days": 0.})
    data["resources"].append({**data["resources"][0], "id": "alt_cap", "failure_domains": ["other_port"]})
    fast = Request.model_validate(data)
    fast_row = _row(fast)
    assert fast_row["state"]["resilience"] == 1. and fast_row["state"]["activity"] < slow_row["state"]["activity"]


# substitution available

def test_substitution_counts_as_resilience():
    row = _row(example("substitution"))
    assert row["substitute_cover_units"] > 0 and row["state"]["resilience"] >= .5 and row["protection_units"] == 0.


# high-priority 99% and low-priority 90% customers

def test_customer_targets_set_the_lean_baseline_not_the_activity():
    req = example("normal")
    data = req.model_dump(mode="json")
    data["customers"] = [{**data["customers"][0], "id": "supermarket", "priority": 3., "service_class": "strategic"},
                         {**data["customers"][0], "id": "spot", "priority": .3, "service_class": "spot"}]
    data["services"] = [{**data["services"][0], "id": "super_A", "customer": "supermarket", "target": .99},
                        {**data["services"][0], "id": "spot_A", "customer": "spot", "target": .9}]
    noise = np.random.default_rng(4)
    data["history"] = ([{**h, "service": "super_A", "quantity": float(max(0., noise.normal(20, 2)))} for h in data["history"]]
                       + [{**h, "service": "spot_A", "quantity": float(max(0., noise.normal(5, 1)))} for h in data["history"]])
    both = Request.model_validate(data)
    row = _row(both)
    assert row["weighted_target"] > .97                       # the 99% customer dominates the quantile
    assert row["state"]["activity"] <= .05                    # calm state regardless of target
    assert row["state"]["lean_baseline_units"] > 0            # but the lean baseline honours the higher target
    report = plan(both)
    levels = report["false_protection"]["quantile_levels"]
    assert levels["super_A"] == 0. and levels["spot_A"] == 0.


def test_supply_state_treats_normal_fill_as_calm():
    req = example("normal")
    assert supply_state(supply_profile(req.sources[0], (), 7)) < .05
    data = req.model_dump(mode="json")
    data["sources"][0]["fill_mean"] = .7
    assert supply_state(supply_profile(Request.model_validate(data).sources[0], (), 7)) >= .9


def test_pr30_profile_is_reproducible_via_switch():
    req = _with(example("normal"), protection_decay=False)
    unc = forecast_all(req)["retail_A"]["uncertainty"]
    assert unc["decay"] is False and unc["pre_change_weight"] == 0.
    report = plan(req)
    assert report["false_protection"]["quantile_levels"] is None
    assert report["stress_credibility"]["floor"] == .1
    assert unc["calibration_ratio"] == unc["calibration_ratio_raw"]


def test_dead_band_and_cap():
    rng = np.random.default_rng(2)
    y = _history(rng)
    unc = demand_uncertainty(estimate(y, 11., .05), y)
    assert unc["calibration_ratio_raw"] <= DEAD_BAND + .5
    assert 1. <= unc["calibration_ratio"] <= 2.      # robust residual scale against the fitted spread, capped
