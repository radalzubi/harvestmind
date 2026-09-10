"""Scenarios that believe what the state estimator believes.

The unconditional generator resamples history as if the future were drawn
from the same urn. This one conditions on the current state: with the
estimated probability of a disruptive regime, a scenario draws a
DISRUPTION PATH — deterioration, a persistent trough, then recovery —
whose depth and length come from observed episodes where history has
them and from the disruption presets (ASSUMED, labelled) where it does
not. Route groups share one latent disruption state per scenario so that
every supplier on the route degrades together. Demand spread is scaled
by the posture's scenario width. Everything is dated at or before the
origin; the leakage tests check the fold boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from risk.supply_paths import build_supply_paths


@dataclass
class DisruptionProfile:
    depth_fill: float = 0.65          # trough fill multiplier
    lead_mult: float = 2.0
    onset_periods: int = 2            # periods to reach the trough
    trough_periods: int = 3
    recovery_periods: int = 3
    source: str = "ASSUMED"

    def path(self, horizon: int, start: int = 0) -> list:
        """Fill multiplier per period from ``start``; 1.0 outside the episode."""
        out = [1.0] * horizon
        t = start
        for k in range(self.onset_periods):
            if t < horizon:
                out[t] = 1.0 - (1.0 - self.depth_fill) * (k + 1) / self.onset_periods
            t += 1
        for _ in range(self.trough_periods):
            if t < horizon:
                out[t] = self.depth_fill
            t += 1
        for k in range(self.recovery_periods):
            if t < horizon:
                out[t] = self.depth_fill + (1.0 - self.depth_fill) * (k + 1) / (self.recovery_periods + 1)
            t += 1
        return out


def profile_from_history(events: dict, low: float = 0.85) -> DisruptionProfile | None:
    """Depth and length of the worst contiguous below-``low`` episode in a
    supplier's own history, if there is one long enough to learn from."""
    seq = [v[0] for _, v in sorted(events.items())]
    leads = [v[1] for _, v in sorted(events.items())]
    best = None
    i = 0
    while i < len(seq):
        if seq[i] < low:
            j = i
            while j < len(seq) and seq[j] < low:
                j += 1
            ep = seq[i:j]
            if len(ep) >= 2 and (best is None or min(ep) < best[0]):
                base_lead = np.median(leads[:i]) if i > 0 else np.median(leads)
                ep_lead = np.median(leads[i:j])
                best = (min(ep), len(ep), float(ep_lead / max(base_lead, 1e-9)))
            i = j
        else:
            i += 1
    if best is None:
        return None
    depth, length, lm = best
    return DisruptionProfile(depth_fill=float(depth), lead_mult=float(max(lm, 1.0)),
                             onset_periods=max(1, length // 3), trough_periods=max(1, length - 2 * max(1, length // 3)),
                             recovery_periods=max(1, length // 3), source="MEASURED")


@dataclass
class ConditionalSupply:
    fills: dict
    leads: dict
    disruption_drawn: dict           # (w, route) -> bool
    profiles: dict                   # route -> DisruptionProfile
    assumptions: list = field(default_factory=list)
    p_disruptive_by_route: dict = field(default_factory=dict)


def conditional_supply_paths(supply_events: dict, suppliers: list, route_of: dict, p_disruptive: dict,
                             n_scen: int, horizon: int, rng, persistence: int = 3,
                             in_recovery: dict | None = None, default_lead: int = 2,
                             preset_profile: DisruptionProfile | None = None) -> ConditionalSupply:
    """
    p_disruptive: route (or supplier when untagged) -> probability the state
                  estimator assigns to a disruptive regime NOW.
    in_recovery:  route -> True when the estimator reads RECOVERY; the path
                  then starts in the recovery leg rather than at onset.
    """
    base = build_supply_paths({s_: supply_events.get(s_, {}) for s_ in suppliers}, suppliers, n_scen, horizon, rng,
                              block_length=max(1, persistence), default_lead=default_lead)
    fills, leads = dict(base.fills), dict(base.leads)
    routes = sorted(set(route_of.get(s_, s_) for s_ in suppliers))
    profiles: dict = {}
    assumptions = list(base.assumptions)
    for r_ in routes:
        members = [s_ for s_ in suppliers if route_of.get(s_, s_) == r_]
        learned = None
        for s_ in members:
            pr = profile_from_history(supply_events.get(s_, {}))
            if pr and (learned is None or pr.depth_fill < learned.depth_fill):
                learned = pr
        profiles[r_] = learned or preset_profile or DisruptionProfile()
        if learned is None:
            assumptions.append(f"route {r_}: no observed disruption episode; profile ASSUMED "
                               f"(depth {profiles[r_].depth_fill:.2f}, lead x{profiles[r_].lead_mult})")
    drawn: dict = {}
    for w in range(n_scen):
        for r_ in routes:
            p = float(p_disruptive.get(r_, 0.0))
            hit = rng.random() < p
            drawn[(w, r_)] = hit
            if not hit:
                continue
            prof = profiles[r_]
            recovering = bool(in_recovery and in_recovery.get(r_))
            start = -(prof.onset_periods + prof.trough_periods) if recovering else int(rng.integers(0, max(1, min(3, horizon))))
            path = prof.path(horizon + max(0, -start), start=max(start, 0))
            if start < 0:
                path = path[-start:] if -start < len(path) else [1.0] * horizon
            for s_ in [x for x in suppliers if route_of.get(x, x) == r_]:
                for t in range(horizon):
                    mult = path[t] if t < len(path) else 1.0
                    fills[(w, s_, t)] = float(min(1.0, fills[(w, s_, t)] * mult))
                    if mult < 0.999:
                        leads[(w, s_, t)] = int(round(leads[(w, s_, t)] * (1.0 + (prof.lead_mult - 1.0) * (1.0 - mult) / max(1.0 - prof.depth_fill, 1e-9))))
    return ConditionalSupply(fills, leads, drawn, profiles, assumptions,
                             {r_: float(p_disruptive.get(r_, 0.0)) for r_ in routes})


def widen_demand(rows: list, width: float, rng) -> list:
    """Scale each scenario's deviation from the cross-scenario mean by
    ``width`` (>1 widens, <1 narrows) without moving the mean."""
    if abs(width - 1.0) < 1e-9 or not rows:
        return rows
    by_key: dict = {}
    for r in rows:
        by_key.setdefault((r["product_id"], r["period"]), []).append(r)
    for key, rs in by_key.items():
        mu = sum(x["demand_kg"] for x in rs) / len(rs)
        for x in rs:
            x["demand_kg"] = max(0.0, mu + (x["demand_kg"] - mu) * width)
    return rows
