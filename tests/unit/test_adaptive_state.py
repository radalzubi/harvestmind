"""The adaptive state layer: change points, probabilities, hysteresis,
signals, posture and conditional scenarios."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from adaptive.change_point import cusum, page_hinkley, recent_vs_longrun
from adaptive.conditional_scenarios import DisruptionProfile, conditional_supply_paths, profile_from_history, widen_demand
from adaptive.controller import autonomy_score, posture_from_state
from adaptive.signals import Signal, SignalStore
from adaptive.state_estimator import (DISRUPTIVE, REGIMES, EntityState, StateConfig, StateTracker, aggregate,
                                      sku_state, supplier_state)

AS_OF = datetime(2026, 9, 1, tzinfo=timezone.utc)


# ── change points ────────────────────────────────────────────────────────
def test_cusum_ignores_single_bad_delivery_but_catches_sustained_shift():
    calm = [0.96, 0.97, 0.95, 0.98, 0.96, 0.97, 0.96, 0.95]
    one_off = calm + [0.70, 0.96, 0.97, 0.96]
    sustained = calm + [0.80, 0.78, 0.75, 0.74, 0.72, 0.70]
    assert not cusum(one_off).detected
    d = cusum(sustained)
    assert d.detected and d.direction == "down" and d.index >= len(calm)
    assert d.magnitude < -0.1


def test_cusum_short_series_reports_nothing():
    assert not cusum([0.9, 0.9, 0.9]).detected


def test_page_hinkley_detects_downward_drift():
    xs = [0.95] * 8 + [0.95 - 0.03 * k for k in range(1, 8)]
    assert page_hinkley(xs, delta=0.005, lam=0.05).detected
    assert not page_hinkley([0.95 + 0.01 * ((-1) ** k) for k in range(16)], delta=0.005, lam=0.05).detected


def test_recent_vs_longrun_shift_in_sd_units():
    xs = [100.0 + (k % 3) for k in range(20)] + [140.0] * 4
    r = recent_vs_longrun(xs, recent=4)
    assert r["shift"] > 30 and r["shift_sd"] > 5


# ── state estimator ──────────────────────────────────────────────────────
def _calm_supplier():
    return supplier_state("S1", [0.96, 0.97, 0.95, 0.96, 0.97, 0.96, 0.95, 0.97, 0.96, 0.96, 0.97, 0.96],
                          [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2], None, None)


def test_probabilities_sum_to_one_and_cover_all_regimes():
    s = _calm_supplier()
    assert set(s.probabilities) == set(REGIMES)
    assert abs(sum(s.probabilities.values()) - 1.0) < 1e-9
    assert s.dominant in ("CALM", "NORMAL")
    assert s.stress < 0.25


def test_deterioration_moves_probability_to_supply_constrained():
    fills = [0.96] * 10 + [0.85, 0.80, 0.76, 0.72, 0.70, 0.68]
    leads = [2] * 10 + [3, 3, 4, 4, 5, 5]
    s = supplier_state("S1", fills, leads, None, None)
    assert s.p_disruptive() > 0.6
    assert s.dominant in DISRUPTIVE
    assert s.stress > 0.4
    assert any("fill" in r for r in s.reasons)
    assert s.change_points["cusum"] or s.change_points["page_hinkley"]


def test_recovery_is_recognised():
    fills = [0.96] * 8 + [0.70, 0.68, 0.70, 0.72] + [0.90, 0.93, 0.95, 0.96]
    s = supplier_state("S1", fills, [2] * 16, None, None)
    assert s.probabilities["RECOVERY"] > s.probabilities["SEVERE_DISRUPTION"]


def test_missing_port_signal_is_not_read_as_normal():
    calm_with = supplier_state("S1", [0.96] * 12, [2] * 12, 1.0, {"available": True, "stale": False})
    calm_missing = supplier_state("S1", [0.96] * 12, [2] * 12, None, {"available": False, "stale": True})
    assert calm_missing.stress > calm_with.stress
    assert calm_missing.data_quality < calm_with.data_quality
    assert any("UNAVAILABLE" in r for r in calm_missing.reasons)


def test_stale_port_signal_carries_reduced_weight():
    fresh = supplier_state("S1", [0.96] * 12, [2] * 12, 0.6, {"available": True, "stale": False})
    stale = supplier_state("S1", [0.96] * 12, [2] * 12, 0.6, {"available": True, "stale": True})
    assert fresh.probabilities["PORT_DISRUPTION"] > stale.probabilities["PORT_DISRUPTION"]
    assert stale.probabilities["PORT_DISRUPTION"] > _calm_supplier().probabilities["PORT_DISRUPTION"]


def test_sku_state_inherits_supplier_evidence_and_flags_promotion():
    bad = supplier_state("S1", [0.96] * 10 + [0.7] * 6, [2] * 16, None, None)
    sku_bad = sku_state("A", [100.0] * 30, 2.0, False, bad)
    sku_ok = sku_state("A", [100.0] * 30, 2.0, False, _calm_supplier())
    assert sku_bad.p_disruptive() > sku_ok.p_disruptive()
    promo = sku_state("A", [100.0] * 30, 2.0, True, _calm_supplier())
    assert promo.probabilities["PROMOTION"] > 0.4
    vol = sku_state("B", list(np.random.default_rng(0).gamma(0.8, 100, 40)), 2.0, False, _calm_supplier())
    assert vol.probabilities["DEMAND_VOLATILE"] > sku_ok.probabilities["DEMAND_VOLATILE"]


def test_thin_cover_raises_tightness():
    thin = sku_state("A", [100.0] * 30, 0.4, False, _calm_supplier())
    deep = sku_state("A", [100.0] * 30, 4.0, False, _calm_supplier())
    assert thin.probabilities["TIGHT"] > deep.probabilities["TIGHT"]
    assert thin.stress > deep.stress


def test_aggregate_is_value_weighted():
    a = sku_state("A", [100.0] * 30, 4.0, False, _calm_supplier())
    b = sku_state("B", [100.0] * 30, 4.0, False,
                  supplier_state("S2", [0.96] * 10 + [0.6] * 6, [2] * 16, None, None))
    heavy_b = aggregate([a, b], [1.0, 9.0])
    heavy_a = aggregate([a, b], [9.0, 1.0])
    assert heavy_b.p_disruptive() > heavy_a.p_disruptive()
    assert abs(sum(heavy_b.probabilities.values()) - 1.0) < 1e-9


# ── hysteresis ────────────────────────────────────────────────────────────
def _probs(p_dis):
    out = {r: 0.0 for r in REGIMES}
    out["SUPPLY_CONSTRAINED"] = p_dis
    out["NORMAL"] = 1.0 - p_dis
    return out


def test_tracker_does_not_thrash_on_a_single_wobble():
    tr = StateTracker(StateConfig(ewma_alpha=1.0, enter_disruption=0.6, exit_disruption=0.35, exit_persistence=2))
    seq = [0.1, 0.7, 0.3, 0.7, 0.3, 0.7, 0.2, 0.2, 0.2]
    flags = []
    for p in seq:
        tr.update(_probs(p))
        flags.append(tr.posture_disrupted)
    # entered at 0.7, single dips to 0.3 do not exit, two consecutive lows do
    assert flags == [False, True, True, True, True, True, True, False, False]


def test_tracker_smoothing_delays_entry_to_noise():
    tr = StateTracker(StateConfig(ewma_alpha=0.3))
    tr.update(_probs(0.05))
    tr.update(_probs(0.9))          # one loud observation
    assert not tr.posture_disrupted
    tr.update(_probs(0.9))
    tr.update(_probs(0.9))
    assert tr.posture_disrupted


# ── signals ───────────────────────────────────────────────────────────────
def test_signal_store_status_and_leakage():
    st_ = SignalStore(max_age_days=30)
    for k in range(6):
        st_.add(Signal(AS_OF - timedelta(days=100 - 15 * k), "port", "AQABA", "throughput_index", 0.9,
                       "REAL_PUBLIC", 0.8))
    assert st_.status("port", "AQABA", "throughput_index", AS_OF).available
    assert not st_.status("port", "AQABA", "throughput_index", AS_OF).stale
    assert st_.status("port", "AQABA", "throughput_index", AS_OF - timedelta(days=200)).available is False
    assert st_.status("port", "AQABA", "throughput_index", AS_OF + timedelta(days=200)).stale
    assert not st_.status("port", "HAIFA", "throughput_index", AS_OF).available
    with pytest.raises(ValueError):
        Signal(AS_OF, "port", "X", "m", 1.0, "MADE_UP")


# ── posture ───────────────────────────────────────────────────────────────
def _portfolio(p_dis, stress, dq=1.0):
    probs = _probs(p_dis)
    return EntityState("portfolio", "*", probs, stress, {}, {}, {}, ["x"], dq)


def test_posture_is_monotone_in_severity():
    calm = posture_from_state(_portfolio(0.05, 0.1), {"A": _portfolio(0.05, 0.1)})
    bad = posture_from_state(_portfolio(0.85, 0.8), {"A": _portfolio(0.85, 0.8)})
    assert bad.cvar_lambda > calm.cvar_lambda and bad.cvar_alpha > calm.cvar_alpha
    assert bad.scenario_width > calm.scenario_width and bad.persistence > calm.persistence
    assert bad.commit_window < calm.commit_window
    # calm = EFFICIENCY mode: region off (>= 1), full candidate set, normal gate
    assert calm.mode == "EFFICIENCY" and calm.trust_region["A"] >= 1.0
    assert bad.mode == "PROTECTION" and bad.trust_region["A"] < 1.0
    mid = posture_from_state(_portfolio(0.4, 0.4), {"A": _portfolio(0.4, 0.4)})
    assert mid.mode == "BALANCED" and mid.trust_region["A"] < 1.0
    assert bad.trust_region["A"] > mid.trust_region["A"]
    assert "stochastic_sp" in calm.candidates and "stochastic_sp" in bad.candidates
    assert "stochastic_sp" not in mid.candidates
    assert calm.regret_budget_share is None and bad.regret_budget_share is not None
    assert calm.min_rel_improvement <= mid.min_rel_improvement


def test_demand_severity_opens_the_trust_region_and_widens_scenarios():
    sup = _portfolio(0.4, 0.4)
    sku_quiet = _portfolio(0.4, 0.4)
    sku_surge = _portfolio(0.4, 0.4)
    sku_surge.features["demand_severity"] = 0.8
    quiet = posture_from_state(sup, {"A": sku_quiet})
    surge_port = _portfolio(0.4, 0.4)
    surge_port.features["demand_severity"] = 0.8
    surge = posture_from_state(surge_port, {"A": sku_surge})
    assert surge.trust_region["A"] > quiet.trust_region["A"]
    assert surge.scenario_width > quiet.scenario_width
    assert surge.demand_severity > quiet.demand_severity
    assert "stochastic_sp" in surge.candidates


def test_autonomy_falls_with_poor_data_and_unknown_economics():
    good, _ = autonomy_score(_portfolio(0.5, 0.5, dq=1.0), 0.5, 0.9, 1.0)
    poor, why = autonomy_score(_portfolio(0.5, 0.5, dq=0.2), 0.5, 0.9, 1.0)
    unk, _ = autonomy_score(_portfolio(0.5, 0.5, dq=1.0), 0.5, 0.9, 0.3)
    assert poor < good and unk < good
    assert any("data quality" in r for r in why)
    none_ev, _ = autonomy_score(_portfolio(0.5, 0.5), 0.0, 0.9, 1.0)
    assert none_ev < good


def test_hysteresis_flag_keeps_disrupted_posture_through_a_dip():
    dip = posture_from_state(_portfolio(0.3, 0.3), {"A": _portfolio(0.3, 0.3)}, tracker_disrupted=True)
    free = posture_from_state(_portfolio(0.3, 0.3), {"A": _portfolio(0.3, 0.3)}, tracker_disrupted=False)
    assert dip.cvar_lambda > free.cvar_lambda
    assert any("hysteresis" in r for r in dip.reasons)


def test_dro_admitted_only_when_disrupted_and_uncertain():
    p = posture_from_state(_portfolio(0.8, 0.7, dq=0.3), {"A": _portfolio(0.8, 0.7)}, calibration_confidence=0.3)
    q = posture_from_state(_portfolio(0.8, 0.7, dq=1.0), {"A": _portfolio(0.8, 0.7)}, calibration_confidence=0.9)
    assert "dro" in p.candidates and "dro" not in q.candidates


# ── conditional scenarios ────────────────────────────────────────────────
def test_disruption_profile_path_shape():
    pth = DisruptionProfile(depth_fill=0.6, onset_periods=2, trough_periods=2, recovery_periods=2).path(10)
    assert pth[0] > pth[1] >= 0.6 and pth[2] == pth[3] == 0.6 and pth[5] > pth[4] and pth[8] == 1.0


def test_profile_learned_from_history_when_an_episode_exists():
    ev = {t: (0.96, 2) for t in range(20)}
    for t in range(8, 13):
        ev[t] = (0.65, 4)
    pr = profile_from_history(ev)
    assert pr is not None and pr.source == "MEASURED" and abs(pr.depth_fill - 0.65) < 1e-9 and pr.lead_mult == 2.0
    assert profile_from_history({t: (0.96, 2) for t in range(20)}) is None


def test_conditional_paths_widen_with_p_disruptive_and_share_route_state():
    rng = np.random.default_rng(0)
    ev = {s: {t: (0.96, 2) for t in range(30)} for s in ("S1", "S2")}
    calm = conditional_supply_paths(ev, ["S1", "S2"], {"S1": "R", "S2": "R"}, {"R": 0.0}, 40, 8,
                                    np.random.default_rng(1))
    hot = conditional_supply_paths(ev, ["S1", "S2"], {"S1": "R", "S2": "R"}, {"R": 0.8}, 40, 8, rng)
    mean_calm = np.mean([v for v in calm.fills.values()])
    mean_hot = np.mean([v for v in hot.fills.values()])
    assert mean_hot < mean_calm - 0.05
    assert sum(hot.disruption_drawn.values()) > 20
    # both suppliers on the route degrade in the same scenarios
    for w in range(40):
        if hot.disruption_drawn[(w, "R")]:
            assert min(hot.fills[(w, "S1", t)] for t in range(8)) < 0.9
            assert min(hot.fills[(w, "S2", t)] for t in range(8)) < 0.9
    assert any("ASSUMED" in a for a in hot.assumptions)


def test_widen_demand_keeps_the_mean():
    rows = [{"product_id": "A", "period": 0, "demand_kg": d} for d in (80.0, 100.0, 120.0)]
    out = widen_demand([dict(r) for r in rows], 1.5, None)
    assert abs(sum(r["demand_kg"] for r in out) / 3 - 100.0) < 1e-9
    assert max(r["demand_kg"] for r in out) == 130.0


def test_state_evidence_selection_needs_a_fresh_demand_shift():
    """A fresh level shift on a third of value + high demand severity lets
    the gate select the state-conditioned candidate under a hard regret
    budget; without the shift the backtest gate runs as usual."""
    from types import SimpleNamespace
    from backtesting.safe_selector import SafeSelectionConfig, safe_select
    from backtesting.counterfactual import FoldInputs
    from domain.model import fmcg_policy
    pol = fmcg_policy({})
    kw = dict(origin=60, horizon=6, products=["A"], supplier_of={"A": "S"}, lead_of={"S": 1},
              train_demand={"A": [100.0] * 54 + [180.0] * 6}, train_fill={"S": [0.96]}, unit_cost={"A": 1.0},
              margin={"A": 0.5}, capacity={"A": 5000.0}, opening={"A": 150.0}, pipeline={}, policy=pol,
              supply_events={"S": {t: (0.96, 1) for t in range(-52, 0)}})
    calls = []

    def fake_adaptive(fi, cap, rng, n):
        calls.append(fi.origin)
        return {("S", "A", 0): 180.0}, {"status": "optimal", "usable": True}
    post = SimpleNamespace(demand_severity=0.7, demand_shift_fresh_share=1.0, regret_budget_share=0.10,
                           min_rel_improvement=0.02, confidence=0.8, candidates=("order_up_to", "adaptive_sp"),
                           as_dict=lambda: {})
    d = safe_select(FoldInputs(**kw), None, np.random.default_rng(0),
                    SafeSelectionConfig(n_boot=50, n_scen=5, allow_state_evidence=True),
                    posture=post, extra_candidates={"adaptive_sp": fake_adaptive})
    assert d.mode_run == "adaptive_sp" and "state-evidence" in d.reason and d.meta["selection_basis"] == "state"
    assert calls == [60]
    quiet = SimpleNamespace(demand_severity=0.1, demand_shift_fresh_share=0.0, regret_budget_share=None,
                            min_rel_improvement=0.02, confidence=0.8, candidates=("order_up_to",), as_dict=lambda: {})
    d2 = safe_select(FoldInputs(**kw), None, np.random.default_rng(0), SafeSelectionConfig(n_boot=50, n_scen=5),
                     posture=quiet, extra_candidates={"adaptive_sp": fake_adaptive})
    assert d2.mode_run != "adaptive_sp" and "state-evidence" not in d2.reason


def test_fresh_demand_shift_is_measured():
    sup = _calm_supplier()
    shifted = sku_state("A", [100.0] * 40 + [170.0] * 6, 2.0, False, sup)
    flat = sku_state("A", [100.0] * 46, 2.0, False, sup)
    assert shifted.features.get("demand_shift_age") is not None and shifted.features["demand_shift_age"] <= 8
    assert flat.features.get("demand_shift_age") is None
    port = aggregate([shifted, flat], [1.0, 1.0])
    assert abs(port.features["demand_shift_fresh_share"] - 0.5) < 1e-9
    assert shifted.features["demand_severity"] > flat.features["demand_severity"]
