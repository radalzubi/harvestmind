"""Forward-looking risk from leading indicators, and the tools to check
whether they actually lead.

``disruption_outlook`` combines whatever indicator signals exist for a lane
at ``as_of`` into a probability-like risk in [0, 1] with a named
contribution per indicator. The weights are DESIGN CONSTANTS (ASSUMED);
they are not fitted, and the returned ``quality`` falls with every
indicator that is missing or stale, so an outlook built on one feed is
weaker evidence than one built on five. Missing feeds contribute nothing
and are listed, never treated as "normal".

``lead_lag`` is the honest check: cross-correlation between an indicator
and the outcome it is supposed to anticipate at candidate leads, on real
history. ``scripts/validate_leading_indicators.py`` runs it on the Red Sea
crisis and writes the result, positive or not.
"""

from __future__ import annotations

import math
import statistics as st
from dataclasses import dataclass, field
from datetime import datetime

from adaptive.indicators import PORT_OF_ROUTE, ROUTE_CHOKEPOINTS, ROUTE_TOPIC
from adaptive.signals import SignalStore

# ASSUMED weights on standardised evidence; every term is documented in the
# engine document and reported per call.
W = {"chokepoint_transit_index": 2.5, "port_throughput_index": 2.0, "conflict_index": 1.0,
     "gscpi": 0.8, "fuel_index": 0.6, "freight_index_yoy": 0.4}
BIAS = -2.2                        # logit at "everything at its norm" -> ~10% risk


@dataclass
class Outlook:
    entity: str
    risk: float                    # [0, 1]
    quality: float                 # [0, 1]; falls with missing / stale feeds
    contributions: dict = field(default_factory=dict)
    missing: list = field(default_factory=list)
    stale: list = field(default_factory=list)
    reasons: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return dict(self.__dict__)


def _evidence(store: SignalStore, et: str, eid: str, metric: str, as_of: datetime | None) -> tuple[float | None, dict]:
    stt = store.status(et, eid, metric, as_of)
    if not stt.available:
        return None, stt.__dict__
    latest = store.latest(et, eid, metric, as_of)
    return (latest.value if latest else None), stt.__dict__


def disruption_outlook(store: SignalStore, route: str, as_of: datetime | None = None) -> Outlook:
    """Risk that the lane's supply deteriorates over the coming weeks."""
    logit = BIAS
    contrib: dict = {}
    missing: list = []
    stale: list = []
    reasons: list = []
    n_feeds = 0
    # chokepoints: transit index below 1 = fewer ships than the lane's own norm
    for cp in ROUTE_CHOKEPOINTS.get(route, ()):
        v, stt = _evidence(store, "chokepoint", cp.upper(), "chokepoint_transit_index", as_of)
        if v is None:
            missing.append(f"chokepoint:{cp}")
            continue
        n_feeds += 1
        w = 0.5 if stt.get("stale") else 1.0
        if stt.get("stale"):
            stale.append(f"chokepoint:{cp}")
        c = W["chokepoint_transit_index"] * max(0.0, 1.0 - v) * 2.0 * w      # 0.5 index -> full weight
        contrib[f"chokepoint:{cp}"] = c
        logit += c
        if v < 0.85:
            reasons.append(f"{cp} transits at {v:.0%} of their trailing norm")
    port = PORT_OF_ROUTE.get(route)
    if port:
        v, stt = _evidence(store, "port", port, "throughput_index", as_of)
        if v is None:
            missing.append(f"port:{port}")
        else:
            n_feeds += 1
            w = 0.5 if stt.get("stale") else 1.0
            if stt.get("stale"):
                stale.append(f"port:{port}")
            c = W["port_throughput_index"] * max(0.0, 1.0 - v) * 2.0 * w
            contrib[f"port:{port}"] = c
            logit += c
            if v < 0.85:
                reasons.append(f"{port} imports at {v:.0%} of their trailing norm")
    topic = ROUTE_TOPIC.get(route)
    if topic:
        v, stt = _evidence(store, "topic", topic.upper(), "conflict_index", as_of)
        if v is None:
            missing.append(f"topic:{topic}")
        else:
            n_feeds += 1
            w = 0.5 if stt.get("stale") else 1.0
            c = W["conflict_index"] * max(0.0, math.log(max(v, 1e-6))) * w      # 2x coverage -> 0.69 weight
            contrib[f"conflict:{topic}"] = c
            logit += c
            if v > 1.5:
                reasons.append(f"news coverage of {topic.replace('_', ' ')} at {v:.1f}x its norm")
    for metric, et, eid, fn in (("gscpi", "region", "GLOBAL", lambda x: max(0.0, x)),
                                ("fuel_index", "region", "GLOBAL", lambda x: max(0.0, x - 1.0) * 4.0),
                                ("freight_index_yoy", "region", "US", lambda x: max(0.0, -x) * 10.0)):
        v, stt = _evidence(store, et, eid, metric, as_of)
        if v is None:
            missing.append(metric)
            continue
        n_feeds += 1
        w = 0.5 if stt.get("stale") else 1.0
        if stt.get("stale"):
            stale.append(metric)
        c = W[metric] * fn(v) * w
        contrib[metric] = c
        logit += c
        if c > 0.5:
            reasons.append(f"{metric} elevated ({v:.2f})")
    risk = 1.0 / (1.0 + math.exp(-logit))
    total = len(ROUTE_CHOKEPOINTS.get(route, ())) + (1 if port else 0) + (1 if topic else 0) + 3
    quality = (n_feeds / total) * (1.0 - 0.3 * len(stale) / max(n_feeds, 1)) if total else 0.0
    if not n_feeds:
        reasons.append("no leading indicators available for this lane; outlook UNAVAILABLE")
    return Outlook(route, float(risk), float(quality), contrib, missing, stale, reasons)


def demand_outlook(store: SignalStore, region: str = "US", as_of: datetime | None = None) -> Outlook:
    """Demand-side pressure: positive = demand running above its norm."""
    contrib: dict = {}
    missing: list = []
    reasons: list = []
    score = 0.0
    n = 0
    v, stt = _evidence(store, "region", region, "demand_index_yoy", as_of)
    if v is None:
        missing.append("demand_index_yoy")
    else:
        n += 1
        contrib["demand_index_yoy"] = v
        score += v * 5.0                          # +10% yoy -> +0.5
        if abs(v) > 0.05:
            reasons.append(f"retail sales {v:+.0%} year on year")
    v, stt = _evidence(store, "region", region, "sentiment_z", as_of)
    if v is None:
        missing.append("sentiment_z")
    else:
        n += 1
        contrib["sentiment_z"] = v
        score += v * 0.15
    risk = 1.0 / (1.0 + math.exp(-score)) if n else 0.5
    return Outlook(region, float(risk), n / 2.0, contrib, missing, [], reasons)


def lead_lag(indicator: list, outcome: list, max_lead_weeks: int = 12, step_days: int = 7) -> dict:
    """Pearson correlation between the indicator at t and the outcome at
    t + lead, for lead = 0..max_lead_weeks, on weekly-aligned series of
    (datetime, value). Returns the correlations and the best lead. A best
    lead of zero, or a weak correlation, means the indicator does NOT lead."""
    from datetime import timedelta
    if not indicator or not outcome:
        return {"n": 0}

    def weekly(xs):
        out = {}
        for d, v in xs:
            wk = (d.date() - timedelta(days=d.weekday()))
            out.setdefault(wk, []).append(v)
        return {k: st.mean(v) for k, v in out.items()}
    a, b = weekly(indicator), weekly(outcome)
    res = {}
    for lead in range(0, max_lead_weeks + 1):
        pairs = [(a[k], b[k + timedelta(weeks=lead)]) for k in a if k + timedelta(weeks=lead) in b]
        if len(pairs) < 12:
            continue
        xa, xb = [p[0] for p in pairs], [p[1] for p in pairs]
        sa, sb = st.pstdev(xa), st.pstdev(xb)
        if sa == 0 or sb == 0:
            continue
        ma, mb = st.mean(xa), st.mean(xb)
        r = sum((x - ma) * (y - mb) for x, y in pairs) / (len(pairs) * sa * sb)
        res[lead] = {"r": float(r), "n": len(pairs)}
    if not res:
        return {"n": 0}
    best = max(res, key=lambda k: res[k]["r"])
    # "leads" needs three things: a positive best lead, a material margin over
    # the contemporaneous correlation, and a correlation that clears the
    # ~95% noise level for that sample size (2/sqrt(n)); scanning many leads
    # on noise will otherwise always find one.
    n_best = res[best]["n"]
    sig = 2.0 / math.sqrt(max(n_best, 1))
    r0 = res.get(0, {}).get("r", -1.0)
    return {"by_lead": res, "best_lead_weeks": best, "best_r": res[best]["r"], "r_at_zero": res.get(0, {}).get("r"),
            "noise_level_r": sig,
            "leads": bool(best > 0 and res[best]["r"] > r0 + 0.05 and res[best]["r"] > sig)}
