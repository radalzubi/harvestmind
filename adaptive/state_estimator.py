"""Probabilistic operating state from observed evidence, with hysteresis.

Regimes are not a hard label. Each entity (supplier, SKU, route) and the
portfolio get a probability vector over

  CALM, NORMAL, WATCH, TIGHT, DEMAND_VOLATILE, SUPPLY_CONSTRAINED,
  PORT_DISRUPTION, SEVERE_DISRUPTION, PROMOTION, RECOVERY

produced by a transparent evidence model: every regime accumulates a
score from named features (fill decline, lead drift, port index, demand
CV, cover, change-point alarms, ...), scores go through a softmax, and
the result is smoothed over time. Hysteresis lives in ``StateTracker``:
a disruption posture is ENTERED above one probability and LEFT only
below a lower one for a configurable number of observations, so one
signal wobble cannot flip the engine.

Everything is computed from evidence dated at or before ``as_of``; the
caller is responsible for handing in only that evidence, and the fold
tests check it.
"""

from __future__ import annotations

import math
import statistics as st
from dataclasses import dataclass, field
from typing import Any

from adaptive.change_point import cusum, page_hinkley, recent_shift_onset, recent_vs_longrun

REGIMES = ("CALM", "NORMAL", "WATCH", "TIGHT", "DEMAND_VOLATILE", "SUPPLY_CONSTRAINED",
           "PORT_DISRUPTION", "SEVERE_DISRUPTION", "PROMOTION", "RECOVERY")
DISRUPTIVE = ("TIGHT", "SUPPLY_CONSTRAINED", "PORT_DISRUPTION", "SEVERE_DISRUPTION")
SUPPLY_REGIMES = ("WATCH", "TIGHT", "SUPPLY_CONSTRAINED", "PORT_DISRUPTION", "SEVERE_DISRUPTION", "RECOVERY")


@dataclass
class StateConfig:
    recent_n: int = 4
    fill_low: float = 0.90
    fill_decline_pts: float = 0.06      # recent vs long-run fill drop that reads as deterioration
    lead_drift_ratio: float = 1.3
    demand_cv_volatile: float = 0.45
    cover_thin: float = 1.0
    port_index_watch: float = 0.85
    port_index_disruption: float = 0.70
    ewma_alpha: float = 0.5             # smoothing of regime probabilities over updates
    enter_disruption: float = 0.60
    exit_disruption: float = 0.35
    exit_persistence: int = 2           # consecutive updates below exit before leaving
    temperature: float = 0.6            # softmax temperature over evidence scores
    # Prior scores: with NO evidence the mass sits on NORMAL/CALM, not spread
    # evenly over ten regimes (four of which are disruptive). Evidence has
    # to overcome the prior, which is the point.
    prior_normal: float = 2.0
    prior_calm: float = 1.0


@dataclass
class EntityState:
    entity_type: str
    entity_id: str
    probabilities: dict
    stress: float
    components: dict                    # named stress components in [0, 1]
    features: dict
    change_points: dict
    reasons: list = field(default_factory=list)
    data_quality: float = 1.0           # 0..1, from evidence counts and signal status

    @property
    def dominant(self) -> str:
        return max(self.probabilities, key=lambda k: self.probabilities[k])

    def p_disruptive(self) -> float:
        return sum(self.probabilities[r] for r in DISRUPTIVE)


def _softmax(scores: dict, temperature: float) -> dict:
    m = max(scores.values())
    ex = {k: math.exp((v - m) / max(temperature, 1e-6)) for k, v in scores.items()}
    z = sum(ex.values())
    return {k: v / z for k, v in ex.items()}


def _clip01(x: float) -> float:
    return float(min(max(x, 0.0), 1.0))


def supplier_state(entity_id: str, fills: list, leads: list, port_index: float | None,
                   port_status: dict | None, cfg: StateConfig | None = None,
                   outlook: Any = None) -> EntityState:
    """fills, leads: chronological, dated at or before as_of. ``outlook`` is
    an ``adaptive.leading.Outlook`` for the supplier's lane: forward-looking
    evidence from public indicators, weighted by its own quality."""
    cfg = cfg or StateConfig()
    f = [float(x) for x in fills]
    L = [float(x) for x in leads]
    feats: dict = {}
    scores = {r: 0.0 for r in REGIMES}
    scores["NORMAL"] += cfg.prior_normal
    scores["CALM"] += cfg.prior_calm
    comps: dict = {}
    reasons: list = []
    n = len(f)
    dq = _clip01(n / 12.0)

    if n:
        drift = recent_vs_longrun(f, cfg.recent_n)
        feats.update(fill_mean=st.mean(f), fill_recent=drift["recent_mean"], fill_longrun=drift["longrun_mean"],
                     fill_shift=drift["shift"], fill_sd=st.pstdev(f) if n > 1 else 0.0)
        # Thresholds scale with the supplier's OWN noise: a supplier that has
        # always filled 85% +/- 8 is not in a regime change; one that filled
        # 95% +/- 2 and now fills 85% is. A change-point alarm only counts
        # when the estimated shift is material (>= fill_decline_pts).
        sd_ref = max(feats["fill_sd"], 0.02)
        cp = cusum(f, reference_n=min(8, max(3, n // 2)), h=5.0)
        ph = page_hinkley(f, delta=0.5 * sd_ref, lam=4.0 * sd_ref, direction="down")
        material = abs(cp.magnitude) >= cfg.fill_decline_pts
        cps = {"cusum": cp.detected and material, "cusum_index": cp.index if material else None,
               "cusum_direction": cp.direction if material else "none",
               "page_hinkley": ph.detected and abs(ph.magnitude) >= cfg.fill_decline_pts,
               "page_hinkley_index": ph.index, "shift": cp.magnitude}
        chronic_low = feats["fill_longrun"] < cfg.fill_low
        declining = feats["fill_shift"] < -cfg.fill_decline_pts
        sustained = cps["cusum"] and cp.direction == "down" or cps["page_hinkley"]
        depth = feats["fill_longrun"] - feats["fill_recent"]            # points lost vs own norm
        recovering = (cps.get("cusum_direction") == "down" or min(f[-cfg.recent_n * 2:-cfg.recent_n] or f) < feats["fill_longrun"] - 2 * cfg.fill_decline_pts) and \
            feats["fill_recent"] >= feats["fill_longrun"] - cfg.fill_decline_pts and \
            feats["fill_recent"] > min(f[-cfg.recent_n * 2:-cfg.recent_n] or f) + cfg.fill_decline_pts
        comps["fill_level"] = _clip01(depth / 0.35)
        comps["fill_decline"] = _clip01(-feats["fill_shift"] / 0.25)
        comps["fill_variance"] = _clip01(max(0.0, feats["fill_sd"] - 0.05) / 0.15)
        if declining and not sustained:
            scores["WATCH"] += 1.5
            reasons.append(f"fill down {-feats['fill_shift']*100:.0f} pts over the last {cfg.recent_n} receipts (not yet sustained)")
        if sustained and declining:
            scores["SUPPLY_CONSTRAINED"] += 2.5 + 4.0 * _clip01(depth / 0.3)
            scores["TIGHT"] += 1.0
            reasons.append(f"sustained fill deterioration: recent {feats['fill_recent']:.0%} vs long-run {feats['fill_longrun']:.0%}")
        if depth > 0.25 and feats["fill_recent"] < 0.70:
            scores["SEVERE_DISRUPTION"] += 2.0 + 4.0 * _clip01((depth - 0.25) / 0.3)
            reasons.append(f"recent fill {feats['fill_recent']:.0%}, {depth*100:.0f} pts below its norm")
        if recovering and not declining:
            scores["RECOVERY"] += 2.5
            reasons.append(f"fill recovering to {feats['fill_recent']:.0%}")
        if chronic_low and not (declining or sustained):
            scores["SUPPLY_CONSTRAINED"] += 0.5     # a known feature of this supplier, priced by the incumbent
            reasons.append(f"chronically low fill ({feats['fill_longrun']:.0%}), no recent change")
        if not (declining or sustained or recovering):
            scores["CALM"] += 1.0 if feats["fill_sd"] < 0.04 else 0.0
            scores["NORMAL"] += 1.0
    else:
        cps = {}
        scores["NORMAL"] += 0.3
        reasons.append("no fill history; evidence absent")
        comps["fill_level"] = 0.3

    if len(L) >= 4:
        ld = recent_vs_longrun(L, cfg.recent_n)
        ratio = ld["recent_mean"] / max(ld["longrun_mean"], 1e-9)
        feats.update(lead_mean=st.mean(L), lead_recent=ld["recent_mean"], lead_ratio=ratio,
                     lead_sd=st.pstdev(L) if len(L) > 1 else 0.0)
        comps["lead_drift"] = _clip01((ratio - 1.0) / 1.0)
        comps["lead_variance"] = _clip01(feats["lead_sd"] / max(feats["lead_mean"], 1e-9) / 0.6)
        if ratio > cfg.lead_drift_ratio:
            scores["TIGHT"] += 1.5
            scores["PORT_DISRUPTION"] += 1.0
            reasons.append(f"lead time {ratio:.1f}x its long-run mean")
    else:
        comps["lead_drift"] = 0.0
        comps["lead_variance"] = 0.0

    if port_status is not None and not port_status.get("available", False):
        comps["port"] = 0.35                                    # absence is NOT normality
        reasons.append("port signal UNAVAILABLE: logistics evidence missing, uncertainty widened")
        scores["WATCH"] += 0.5
        dq *= 0.85
    elif port_index is not None:
        stale = bool(port_status and port_status.get("stale"))
        w = 0.5 if stale else 1.0
        comps["port"] = _clip01((1.0 - port_index) / 0.5) * w
        feats["port_index"] = port_index
        if port_index < cfg.port_index_disruption:
            scores["PORT_DISRUPTION"] += 2.5 * w
            reasons.append(f"port throughput index {port_index:.2f}{' (stale)' if stale else ''}")
        elif port_index < cfg.port_index_watch:
            scores["WATCH"] += 1.0 * w
            reasons.append(f"port throughput index {port_index:.2f} below watch level")
    else:
        comps["port"] = 0.0

    # Leading indicators: evidence that the lane is ABOUT to deteriorate.
    # They raise WATCH (and, when strong, PORT_DISRUPTION) before receipts
    # can show anything, scaled by the outlook's quality so a one-feed
    # outlook counts for little. Excess risk over the ~10% base is what counts.
    if outlook is not None and getattr(outlook, "quality", 0.0) > 0:
        excess = max(0.0, float(outlook.risk) - 0.12)
        q = float(outlook.quality)
        comps["outlook"] = _clip01(excess / 0.6) * q
        feats["outlook_risk"] = float(outlook.risk)
        feats["outlook_quality"] = q
        if excess > 0.08:
            scores["WATCH"] += 3.0 * excess * q
            reasons.append(f"leading indicators put lane risk at {outlook.risk:.0%} (quality {q:.2f})")
            reasons.extend(list(outlook.reasons)[:2])
        if excess > 0.35:
            scores["PORT_DISRUPTION"] += 3.0 * (excess - 0.35) * q
    else:
        comps["outlook"] = 0.0
    weights = {"fill_level": 0.28, "fill_decline": 0.22, "fill_variance": 0.08, "lead_drift": 0.14,
               "lead_variance": 0.04, "port": 0.12, "outlook": 0.12}
    stress = _clip01(sum(weights[k] * comps.get(k, 0.0) for k in weights))
    probs = _softmax(scores, cfg.temperature)
    return EntityState("supplier", entity_id, probs, stress, comps, feats, cps, reasons, dq)


def sku_state(entity_id: str, demand: list, cover_periods: float, promo_ahead: bool,
              supplier: EntityState | None, cfg: StateConfig | None = None) -> EntityState:
    cfg = cfg or StateConfig()
    d = [float(x) for x in demand]
    scores = {r: 0.0 for r in REGIMES}
    scores["NORMAL"] += cfg.prior_normal
    scores["CALM"] += cfg.prior_calm
    comps: dict = {}
    feats: dict = {}
    reasons: list = []
    n = len(d)
    dq = _clip01(n / 26.0)
    if n >= 4:
        mu = st.mean(d)
        cv = (st.pstdev(d) / mu) if mu > 0 else 0.0
        drift = recent_vs_longrun(d, cfg.recent_n)
        inter = sum(1 for x in d if x <= 0) / n
        spike = (max(d[-cfg.recent_n:]) / mu) if mu > 0 else 0.0
        cp = cusum(d, reference_n=min(12, max(4, n // 2)))
        feats.update(demand_cv=cv, demand_shift_sd=drift["shift_sd"], intermittency=inter, spike_ratio=spike,
                     cover_periods=cover_periods,
                     demand_shift_age=recent_shift_onset(d)["age"])
        comps["demand_cv"] = _clip01((cv - 0.2) / 0.8)
        comps["demand_drift"] = _clip01(abs(drift["shift_sd"]) / 3.0)
        comps["cover"] = _clip01((cfg.cover_thin * 1.5 - cover_periods) / (cfg.cover_thin * 1.5))
        cps = {"cusum": cp.detected, "cusum_index": cp.index, "cusum_direction": cp.direction}
        if cv > cfg.demand_cv_volatile or inter > 0.35:
            scores["DEMAND_VOLATILE"] += 2.0
            reasons.append(f"demand CV {cv:.2f}, zero-share {inter:.0%}")
        if cp.detected and abs(drift["shift_sd"]) > 2.0:
            scores["DEMAND_VOLATILE"] += 1.5
            reasons.append(f"demand level shift {drift['shift_sd']:+.1f} sd (change point at {cp.index})")
        if spike > 2.0:
            scores["DEMAND_VOLATILE"] += 0.5
        if cover_periods < cfg.cover_thin:
            scores["TIGHT"] += 1.5
            reasons.append(f"cover {cover_periods:.1f} periods")
        if not (cv > cfg.demand_cv_volatile or inter > 0.35 or cover_periods < cfg.cover_thin or cp.detected):
            scores["CALM"] += 1.0 if cv < 0.2 else 0.5
            scores["NORMAL"] += 1.0
    else:
        cps = {}
        comps.update(demand_cv=0.3, demand_drift=0.0, cover=0.0)
        scores["NORMAL"] += 0.3
        reasons.append("thin demand history")
    if promo_ahead:
        scores["PROMOTION"] += 4.0          # a planned promotion is known, not inferred
        reasons.append("planned promotion inside the horizon")
    probs = _softmax(scores, cfg.temperature)
    if supplier is not None:
        # A SKU sourced from a disrupted supplier IS supply-disrupted: the
        # supplier's supply-regime mass enters the SKU's distribution as a
        # mixture, the SKU's own (demand, cover, promotion) evidence keeps
        # the remainder. Nothing is diluted by the number of regimes.
        supply_mass = sum(supplier.probabilities.get(r, 0.0) for r in SUPPLY_REGIMES)
        mixed = {r: supplier.probabilities.get(r, 0.0) * (1.0 if r in SUPPLY_REGIMES else 0.0)
                 + probs[r] * (1.0 - supply_mass) for r in REGIMES}
        z = sum(mixed.values()) or 1.0
        probs = {r: v / z for r, v in mixed.items()}
        comps["supply"] = supplier.stress
        reasons.extend(supplier.reasons[:2])
        dq = min(dq, max(supplier.data_quality, 0.3))
    weights = {"demand_cv": 0.25, "demand_drift": 0.15, "cover": 0.25, "supply": 0.35}
    stress = _clip01(sum(weights[k] * comps.get(k, 0.0) for k in weights))
    # Demand severity is its own channel: volatility, level shift, a planned
    # promotion. It opens the UPSIDE of the trust region and widens the
    # scenarios without pretending a supply problem exists.
    feats["demand_severity"] = _clip01(0.6 * (probs.get("DEMAND_VOLATILE", 0.0) + probs.get("PROMOTION", 0.0))
                                       + 0.4 * comps.get("demand_drift", 0.0)
                                       + (0.3 if feats.get("demand_shift_sd", 0.0) > 2.0 else 0.0))
    return EntityState("sku", entity_id, probs, stress, comps, feats, cps, reasons, dq)


def aggregate(states: list, weights: list | None = None) -> EntityState:
    """Portfolio state: value-weighted mix of entity probabilities and stress."""
    if not states:
        return EntityState("portfolio", "*", {r: (1.0 if r == "NORMAL" else 0.0) for r in REGIMES}, 0.0, {}, {}, {},
                           ["no entities"], 0.0)
    w = weights or [1.0] * len(states)
    tot = sum(w) or 1.0
    probs = {r: sum(wi * s.probabilities.get(r, 0.0) for wi, s in zip(w, states)) / tot for r in REGIMES}
    stress = sum(wi * s.stress for wi, s in zip(w, states)) / tot
    comps: dict = {}
    for s in states:
        for k, v in s.components.items():
            comps[k] = comps.get(k, 0.0) + v / len(states)
    reasons = []
    for s in sorted(states, key=lambda x: -x.stress)[:3]:
        reasons.extend([f"{s.entity_id}: {r}" for r in s.reasons[:1]])
    dq = sum(wi * s.data_quality for wi, s in zip(w, states)) / tot
    feats = {"demand_severity": sum(wi * float(s.features.get("demand_severity", 0.0)) for wi, s in zip(w, states)) / tot,
             # share of value in SKUs whose demand level shifted within the last 12 periods: when it is
             # large, backtest folds that predate the shift are not evidence about the present
             "demand_shift_fresh_share": sum(wi for wi, s in zip(w, states)
                                             if (s.features.get("demand_shift_age") or 99) <= 12
                                             and abs(float(s.features.get("demand_shift_sd", 0.0))) > 2.0) / tot}
    return EntityState("portfolio", "*", probs, stress, comps, feats, {}, reasons, dq)


@dataclass
class StateTracker:
    """Smoothing plus hysteresis over successive state updates."""
    cfg: StateConfig = field(default_factory=StateConfig)
    smoothed: dict | None = None
    posture_disrupted: bool = False
    _below_exit: int = 0
    history: list = field(default_factory=list)

    def update(self, raw_probs: dict) -> dict:
        if self.smoothed is None:
            self.smoothed = dict(raw_probs)
        else:
            a = self.cfg.ewma_alpha
            self.smoothed = {r: (1 - a) * self.smoothed.get(r, 0.0) + a * raw_probs.get(r, 0.0) for r in REGIMES}
        p_dis = sum(self.smoothed[r] for r in DISRUPTIVE)
        if not self.posture_disrupted:
            if p_dis > self.cfg.enter_disruption:
                self.posture_disrupted = True
                self._below_exit = 0
        else:
            if p_dis < self.cfg.exit_disruption:
                self._below_exit += 1
                if self._below_exit >= self.cfg.exit_persistence:
                    self.posture_disrupted = False
                    self._below_exit = 0
            else:
                self._below_exit = 0
        self.history.append({"p_disruptive": p_dis, "posture_disrupted": self.posture_disrupted})
        return dict(self.smoothed)


@dataclass
class TrackerBank:
    """One tracker for the portfolio and one per SKU, created lazily, so
    hysteresis is applied where the trust regions are: per SKU."""
    cfg: StateConfig = field(default_factory=StateConfig)
    portfolio: StateTracker | None = None
    sku: dict = field(default_factory=dict)

    def get(self, key: str) -> StateTracker:
        if key == "*":
            if self.portfolio is None:
                self.portfolio = StateTracker(self.cfg)
            return self.portfolio
        if key not in self.sku:
            self.sku[key] = StateTracker(self.cfg)
        return self.sku[key]
