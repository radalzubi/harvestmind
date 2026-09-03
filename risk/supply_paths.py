"""Time-varying, correlated supplier paths for the live FMCG scenario set.

WHAT WAS WRONG BEFORE. The live generator drew one fill per (scenario,
supplier) and held it for the whole horizon, used the mean lead for every
scenario, and sampled suppliers independently. Real supply failure is
episodic (a port congests for weeks), recovers, and hits every supplier on
the same route together. The simulator already knew that
the planner did
not.

WHAT THIS DOES. From each supplier's observed per-period history of
(fill, lead), it builds joint paths for W scenarios and H periods by
MOVING-BLOCK BOOTSTRAP over the joint per-period vector of all suppliers:
a block of consecutive periods is copied for every supplier at once, so
both temporal persistence and cross-supplier co-movement survive
resampling. Periods with no observation for a supplier carry that
supplier's last known state forward (labelled in the result). An optional
route overlay then applies a two-state Markov disruption per route group,
estimated from history where tags exist and otherwise ASSUMED from the
disruption presets, multiplying fill and lead for every supplier in the
group while the state is on.

Output keys are (scenario, supplier, period) and drop straight into
MultiPeriodStochasticLP. What remains assumed is listed in
``SupplyPaths.assumptions``.
"""

from __future__ import annotations

from dataclasses import dataclass, field



@dataclass
class SupplyPaths:
    fills: dict                # (w, i, t) -> fill in [0, 1]
    leads: dict                # (w, i, t) -> integer periods
    disrupted: dict            # (w, route, t) -> bool
    method: str
    block_length: int
    assumptions: list = field(default_factory=list)
    coverage: dict = field(default_factory=dict)   # supplier -> observed periods


def _estimate_markov(states: list[bool]) -> tuple[float, float]:
    """(p_start, p_end) from an on/off sequence; conservative if thin."""
    if len(states) < 8:
        return 0.05, 0.30
    starts = sum(1 for a, b in zip(states, states[1:]) if not a and b)
    ends = sum(1 for a, b in zip(states, states[1:]) if a and not b)
    off = max(sum(1 for s_ in states[:-1] if not s_), 1)
    on = max(sum(1 for s_ in states[:-1] if s_), 1)
    return min(max(starts / off, 0.005), 0.5), min(max(ends / on, 0.05), 0.95)


def build_supply_paths(history: dict, suppliers: list, n_scen: int, horizon: int, rng,
                       block_length: int = 4, route_of: dict | None = None,
                       route_disruption: dict | None = None,
                       default_fill: float = 0.95, default_lead: int = 2) -> SupplyPaths:
    """
    history:          supplier -> {rel_period (int, < 0) -> (fill, lead)} observed
                      before the origin. Only pre-origin keys are honoured.
    route_of:         supplier -> route group tag (optional).
    route_disruption: route -> {"fill_mult", "lead_mult", "p_start", "p_end"}
                      overlay
                      p_start/p_end are estimated from history when
                      the history carries a 'disrupted' state, else assumed.
    """
    sups = list(suppliers)
    periods = sorted({t for s_ in sups for t in history.get(s_, {}) if t < 0})
    assumptions = []
    if not periods:
        assumptions.append("no supplier history: fills and leads are the defaults for every period")
        fills = {(w, s_, t): default_fill for w in range(n_scen) for s_ in sups for t in range(horizon)}
        leads = {(w, s_, t): default_lead for w in range(n_scen) for s_ in sups for t in range(horizon)}
        return SupplyPaths(fills, leads, {}, "defaults", 0, assumptions, {s_: 0 for s_ in sups})

    # Joint per-period matrix with last-known carry-forward.
    seq_f: dict = {s_: [] for s_ in sups}
    seq_l: dict = {s_: [] for s_ in sups}
    last = {s_: (default_fill, default_lead) for s_ in sups}
    carried = {s_: 0 for s_ in sups}
    for t in periods:
        for s_ in sups:
            if t in history.get(s_, {}):
                f, L = history[s_][t]
                last[s_] = (float(min(max(f, 0.0), 1.0)), int(max(L, 0)))
            else:
                carried[s_] += 1
            seq_f[s_].append(last[s_][0])
            seq_l[s_].append(last[s_][1])
    n = len(periods)
    b = max(1, min(block_length, n))
    if any(c > 0 for c in carried.values()):
        assumptions.append("periods without an observation carry the supplier's last known state")
    fills, leads = {}, {}
    for w in range(n_scen):
        t = 0
        while t < horizon:
            start = int(rng.integers(0, n - b + 1)) if n > b else 0
            for k in range(b):
                if t >= horizon:
                    break
                idx = min(start + k, n - 1)
                for s_ in sups:
                    fills[(w, s_, t)] = seq_f[s_][idx]
                    leads[(w, s_, t)] = seq_l[s_][idx]
                t += 1
    disrupted: dict = {}
    if route_of and route_disruption:
        routes = sorted(set(route_of.values()))
        for r_ in routes:
            spec = route_disruption.get(r_)
            if not spec:
                continue
            p_start, p_end = spec.get("p_start"), spec.get("p_end")
            if p_start is None or p_end is None:
                # estimate from a fill-below-threshold state if history has one
                members = [s_ for s_ in sups if route_of.get(s_) == r_]
                states = [any(seq_f[s_][k] < 0.85 for s_ in members) for k in range(n)] if members else []
                p_start, p_end = _estimate_markov(states)
                assumptions.append(f"route {r_}: disruption start/end rates estimated from fill<0.85 episodes")
            fm, lm = float(spec.get("fill_mult", 0.75)), float(spec.get("lead_mult", 2.0))
            assumptions.append(f"route {r_}: disruption multipliers fill x{fm}, lead x{lm} (ASSUMED)")
            for w in range(n_scen):
                on = False
                for t in range(horizon):
                    on = (rng.random() >= p_end) if on else (rng.random() < p_start)
                    disrupted[(w, r_, t)] = on
                    if on:
                        for s_ in sups:
                            if route_of.get(s_) == r_:
                                fills[(w, s_, t)] = min(1.0, fills[(w, s_, t)] * fm)
                                leads[(w, s_, t)] = int(round(leads[(w, s_, t)] * lm))
    return SupplyPaths(fills, leads, disrupted, "moving_block_bootstrap", b, assumptions,
                       {s_: n - carried[s_] for s_ in sups})
