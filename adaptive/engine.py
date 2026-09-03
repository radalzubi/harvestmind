"""Glue: FoldInputs (+ signal store) -> per-entity states -> posture.

``estimate`` reads only what the fold carries — demand history, recorded
supplier events dated before the origin, planned promotions inside the
horizon, current cover — plus whatever the signal store holds at or
before ``as_of``. It never looks at truth. ``adaptive_kwargs`` then turns
the posture into optimizer arguments: state-conditioned scenarios,
CVaR weight/level, regret budget, anchoring scale, trust regions and the
plan-stability cost against the previously published schedule.
"""

from __future__ import annotations

import statistics as st
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from adaptive.controller import Posture, PostureConfig, posture_from_state
from adaptive.signals import SignalStore
from adaptive.state_estimator import (REGIMES, EntityState, StateConfig, StateTracker, TrackerBank, aggregate,
                                      sku_state, supplier_state)


@dataclass
class Estimate:
    portfolio: EntityState
    sku: dict
    supplier: dict
    posture: Posture
    signals: dict = field(default_factory=dict)
    change_points: dict = field(default_factory=dict)
    as_of: str | None = None

    def as_dict(self) -> dict:
        return {
            "as_of": self.as_of,
            "portfolio": {"probabilities": self.portfolio.probabilities, "dominant": self.portfolio.dominant,
                          "stress": self.portfolio.stress, "components": self.portfolio.components,
                          "reasons": self.portfolio.reasons, "data_quality": self.portfolio.data_quality},
            "sku": {j: {"dominant": s.dominant, "p_disruptive": s.p_disruptive(), "stress": s.stress,
                        "probabilities": s.probabilities, "reasons": s.reasons[:3]} for j, s in self.sku.items()},
            "supplier": {i: {"dominant": s.dominant, "p_disruptive": s.p_disruptive(), "stress": s.stress,
                             "probabilities": s.probabilities, "reasons": s.reasons[:3],
                             "change_points": s.change_points} for i, s in self.supplier.items()},
            "posture": self.posture.as_dict(),
            "signals": self.signals,
            "change_points": self.change_points,
        }


def _cover_periods(fi, j: str) -> float:
    mu = st.mean(fi.train_demand[j][-8:]) if fi.train_demand.get(j) else 0.0
    pos = float(fi.opening.get(j, 0.0)) + sum(q for (jj, _t), q in fi.pipeline.items() if jj == j)
    return pos / mu if mu > 0 else 99.0


def estimate(fi, store: SignalStore | None = None, as_of: datetime | None = None,
             tracker: StateTracker | None = None, *, evidence_strength: float = 0.0,
             calibration_confidence: float = 0.5, economics_quality: float | None = None,
             state_cfg: StateConfig | None = None, posture_cfg: PostureConfig | None = None,
             port_of_route: dict | None = None) -> Estimate:
    state_cfg = state_cfg or StateConfig()
    sups = sorted(set(fi.supplier_of.values()))
    sig_status: dict = {}
    sup_states: dict = {}
    for s_ in sups:
        ev = fi.supply_events.get(s_, {}) if fi.supply_events else {}
        keys = sorted(k for k in ev if k < 0)                     # keys are relative to the origin; < 0 = observed
        fills = [ev[k][0] for k in keys] or list(fi.train_fill.get(s_, []))
        leads = [ev[k][1] for k in keys]
        route = (fi.route_of or {}).get(s_)
        port = (port_of_route or {}).get(route, route) if route else None
        p_idx, p_status = None, None
        if store is not None and port:
            stt = store.status("port", str(port).upper(), "throughput_index", as_of)
            p_status = stt.__dict__
            sig_status[f"port:{str(port).upper()}"] = p_status
            latest = store.latest("port", str(port).upper(), "throughput_index", as_of)
            p_idx = latest.value if latest else None
            flag = store.latest("port", str(port).upper(), "disruption_flag", as_of)
            if flag is not None and (p_idx is None or 1.0 - flag.value < p_idx):
                p_idx = 1.0 - flag.value           # an operator flag is evidence too
        elif route:
            p_status = {"available": False, "stale": True, "reason": "no signal store attached"}
        sup_states[s_] = supplier_state(s_, fills, leads, p_idx, p_status, state_cfg)
    sku_states: dict = {}
    for j in fi.products:
        promo = any(k[0] == j and v > 1.0 for k, v in (fi.promo_multiplier or {}).items())
        sku_states[j] = sku_state(j, fi.train_demand.get(j, []), _cover_periods(fi, j), promo,
                                  sup_states.get(fi.supplier_of[j]), state_cfg)
    weights = [float(fi.unit_cost.get(j, 1.0)) * (st.mean(fi.train_demand[j]) if fi.train_demand.get(j) else 1.0)
               for j in fi.products]
    portfolio = aggregate([sku_states[j] for j in fi.products], weights)
    tracked = None
    sku_flags: dict = {}
    if isinstance(tracker, TrackerBank):
        for j in fi.products:
            tr = tracker.get(j)
            sku_states[j].probabilities = tr.update(sku_states[j].probabilities)
            sku_flags[j] = tr.posture_disrupted
        portfolio = aggregate([sku_states[j] for j in fi.products], weights)
        portfolio.probabilities = tracker.get("*").update(portfolio.probabilities)
        tracked = tracker.get("*").posture_disrupted or any(sku_flags.values())
    elif tracker is not None:
        portfolio.probabilities = tracker.update(portfolio.probabilities)
        tracked = tracker.posture_disrupted
    # share of value sitting in SKUs the estimator reads as disrupted: a
    # third of the portfolio at p=0.8 is a disruption, whatever the mean says
    tot_w = sum(weights) or 1.0
    portfolio.features["value_share_disrupted"] = sum(
        w for w, j in zip(weights, fi.products) if sku_states[j].p_disruptive() > 0.5) / tot_w
    if economics_quality is None:
        prov = fi.provenance or {}
        economics_quality = 1.0
        if prov.get("shortage_cost_per_unit") in ("unknown", "UNKNOWN", "assumed", "ASSUMED"):
            economics_quality = 0.4
        elif prov.get("holding_rate_per_period") in ("assumed", "ASSUMED"):
            economics_quality = 0.7
    posture = posture_from_state(portfolio, sku_states, evidence_strength=evidence_strength,
                                 calibration_confidence=calibration_confidence, economics_quality=economics_quality,
                                 tracker_disrupted=tracked, sku_flags=sku_flags, cfg=posture_cfg)
    cps = {s_: sup_states[s_].change_points for s_ in sups}
    return Estimate(portfolio, sku_states, sup_states, posture, sig_status, cps,
                    as_of.isoformat() if as_of else None)


def p_disruptive_by_route(est: Estimate, fi) -> dict:
    out: dict = {}
    for s_, stt in est.supplier.items():
        r_ = (fi.route_of or {}).get(s_, s_)
        out[r_] = max(out.get(r_, 0.0), stt.p_disruptive())
    return out


def in_recovery_by_route(est: Estimate, fi) -> dict:
    out: dict = {}
    for s_, stt in est.supplier.items():
        r_ = (fi.route_of or {}).get(s_, s_)
        out[r_] = out.get(r_, False) or stt.dominant == "RECOVERY"
    return out


def adaptive_kwargs(fi, posture: Posture, base_schedule: dict, unit_cost: dict) -> dict:
    """Optimizer keyword overrides implied by a posture."""
    from backtesting.counterfactual import anchor_penalties
    rho = {j: v * posture.rho_scale for j, v in anchor_penalties(fi).items()}
    kw: dict[str, Any] = {
        "baseline_schedule": base_schedule,
        "anchor_rho_by_product": rho,
        "regret_cvar_alpha": posture.cvar_alpha,
        "regret_cvar_lambda": posture.cvar_lambda,
        "trust_region_by_product": dict(posture.trust_region),
    }
    if posture.regret_budget_share is not None:
        kw["regret_budget_share"] = posture.regret_budget_share
    prev = getattr(fi, "previous_schedule", None)
    if prev:
        kw["previous_schedule"] = prev
        kw["change_cost_by_product"] = {j: unit_cost[j] * posture.change_cost_rate for j in fi.products}
    return kw


REGIME_NAMES = REGIMES
