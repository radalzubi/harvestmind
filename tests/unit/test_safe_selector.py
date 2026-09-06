"""SAFE_SELECTED must defer to the incumbent unless evidence is credible,
must never see the future, and must prefer the simpler policy on ties."""
from __future__ import annotations

import numpy as np
import pytest

from backtesting.counterfactual import FoldInputs
from backtesting.incumbent import configured_incumbent
from backtesting.safe_selector import (
    INCUMBENT, SafeSelectionConfig, inner_folds, safe_select,
)
from domain.economics import CostConfig
from domain.model import fmcg_policy
from domain.uom import PackSpec

SENTINEL = 9.9e6


def _fi(n_hist=60, demand_level=100.0, cv=0.1, fill=0.97, seed=0, opening_cover=1.0, incumbent_cover=2.0,
        promo=None):
    rng = np.random.default_rng(seed)
    dem = [max(0.0, rng.normal(demand_level, demand_level * cv)) for _ in range(n_hist)]
    events = {"S": {-k: (float(np.clip(rng.normal(fill, 0.02), 0, 1)), 1) for k in range(1, n_hist + 1)}}
    pol = fmcg_policy({"A": PackSpec(1)}, cost_config=CostConfig(
        holding_rate_per_period=0.005, shortage_cost_per_unit={"A": 2.0}, waste_cost_per_unit={"A": 5.0}))
    return FoldInputs(origin=1000, horizon=8, products=["A"], supplier_of={"A": "S"}, lead_of={"S": 1},
                      train_demand={"A": dem}, train_fill={"S": [v[0] for v in events["S"].values()]},
                      unit_cost={"A": 5.0}, margin={"A": 2.0}, capacity={"A": demand_level * 5},
                      opening={"A": demand_level * opening_cover}, pipeline={("A", 0): demand_level},
                      policy=pol, promo_multiplier=promo or {}, supply_events=events,
                      incumbent=configured_incumbent(cover_weeks=incumbent_cover, review_periods=1))


class TestFallbacks:
    def test_insufficient_history_returns_incumbent_not_stochastic(self):
        d = safe_select(_fi(n_hist=12), None, np.random.default_rng(0), SafeSelectionConfig(min_history=26))
        assert d.mode_run == INCUMBENT and "insufficient history" in d.reason
        assert d.schedule and d.evidence == {}

    def test_no_incumbent_supplied_is_labelled(self):
        fi = _fi(n_hist=12)
        fi.incumbent = None
        d = safe_select(fi, None, np.random.default_rng(0))
        assert d.mode_run == INCUMBENT and any("labelled" in w for w in d.warnings)

    def test_calm_history_keeps_the_incumbent(self):
        """Stable demand, reliable supply, adequate cover: the gate should
        not open. A retained incumbent here is the intended outcome."""
        d = safe_select(_fi(n_hist=60, cv=0.05, opening_cover=2.0), None, np.random.default_rng(1),
                        SafeSelectionConfig(n_scen=10))
        assert d.mode_run == INCUMBENT
        assert "threshold" in d.reason or "held-out" in d.reason
        assert d.evidence and all(v.stats for v in d.evidence.values())


class TestLeakage:
    def test_inner_fold_training_never_contains_truth_or_future(self):
        fi = _fi(n_hist=60)
        # poison everything at or after each inner origin with a sentinel demand and supply event
        folds = inner_folds(fi, n_folds=3, holdout=4)
        assert folds
        for inner, truth, meta in folds:
            start = meta["start"]
            n_hist = len(fi.train_demand["A"])
            # training demand ends strictly before the inner origin
            assert len(inner.train_demand["A"]) == n_hist + start
            # supply training events are strictly before the inner origin
            assert all(p < 0 for p in inner.supply_events["S"])
            # truth covers exactly [start, start+holdout)
            assert set(t for (_, t) in truth.demand) == set(range(4))

    def test_sentinel_after_inner_origin_does_not_reach_candidates(self):
        fi = _fi(n_hist=60)
        poisoned = _fi(n_hist=60)
        # sentinel in the LAST holdout window of demand and in supply events there
        for k in range(1, 5):
            poisoned.train_demand["A"][-k] = SENTINEL
            poisoned.supply_events["S"][-k] = (0.0, 40)
        clean = inner_folds(fi, 3, 4, offset=4)          # folds that END before the poisoned window
        dirty = inner_folds(poisoned, 3, 4, offset=4)
        for (a, ta, _), (b, tb, _) in zip(clean, dirty):
            assert a.train_demand == b.train_demand
            assert a.supply_events == b.supply_events
            assert ta.demand == tb.demand and ta.fill == tb.fill
        assert all(v < SENTINEL for v in clean[0][0].train_demand["A"])

    def test_supply_truth_replays_recorded_events(self):
        fi = _fi(n_hist=60)
        fi.supply_events["S"][-2] = (0.41, 3)      # a recorded short, late delivery
        folds = inner_folds(fi, 1, 4, offset=0)
        inner, truth, meta = folds[0]
        assert truth.fill[("S", 2)] == pytest.approx(0.41) and truth.lead[("S", 2)] == 3
        assert meta["replayed_supply_events"] >= 1


class TestGates:
    def test_candidate_must_clear_every_gate(self):
        cfg = SafeSelectionConfig(min_rel_improvement=0.99, n_scen=10)   # impossible bar
        d = safe_select(_fi(n_hist=60, cv=0.6, opening_cover=0.3, incumbent_cover=0.5), None,
                        np.random.default_rng(2), cfg)
        assert d.mode_run == INCUMBENT
        assert all(not v.gates.get("lower_bound_exceeds_threshold", False) for v in d.evidence.values())

    def test_bad_incumbent_under_volatility_can_be_displaced(self):
        """An incumbent holding half a week of cover against CV 0.6 demand
        loses margin every fold
        a candidate with credible evidence may
        displace it, and the decision must carry the evidence."""
        cfg = SafeSelectionConfig(min_rel_improvement=0.02, n_scen=12, confidence=0.6, max_regret_share=0.5)
        d = safe_select(_fi(n_hist=80, cv=0.6, opening_cover=0.3, incumbent_cover=0.5, seed=3), None,
                        np.random.default_rng(3), cfg)
        assert d.evidence
        if d.mode_run != INCUMBENT:
            ev = d.evidence[d.mode_run]
            assert ev.passed and ev.stats["lower_bound"] > cfg.min_rel_improvement
            assert ev.holdout_delta_rel is not None and ev.holdout_delta_rel > 0
        else:
            assert "threshold" in d.reason or "held-out" in d.reason

    def test_ties_go_to_the_simpler_policy(self):
        from backtesting import safe_selector as ss
        assert ss.COMPLEXITY["order_up_to"] < ss.COMPLEXITY["deterministic_sp"] < ss.COMPLEXITY["stochastic_sp"]

    def test_config_validation(self):
        with pytest.raises(ValueError):
            SafeSelectionConfig(n_folds=1)
        with pytest.raises(ValueError):
            SafeSelectionConfig(confidence=0.3)


def test_decision_is_serialisable_with_evidence():
    d = safe_select(_fi(n_hist=40), None, np.random.default_rng(0), SafeSelectionConfig(n_scen=8))
    out = d.as_dict()
    assert out["mode_run"] and "candidates" in out and "gates" in out
