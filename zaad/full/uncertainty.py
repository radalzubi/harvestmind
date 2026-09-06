"""Calibrated demand and supply uncertainty from what was actually observed.

No universal buffer factor lives here. Demand spread is checked against realized one-step
errors of the chosen forecast, widened while a regime change is still young, and carries a
level standard error so a single optimistic point forecast cannot drive a lean plan on its
own. Supply spread comes from the source's own accepted-ratio and censored lead-time history
when there is enough of it, and from the declared parameters otherwise, labelled as such.
Shared route nodes are treated as shared failure domains: two suppliers through one port are
not two independent sources.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math

import numpy as np
from scipy.stats import norm

from zaad.forecast import point
from zaad.full.contracts import Request, Resource, ShipmentObservation, Source
from zaad.full.eta import conditional_eta

MIN_SUPPLY_RECORDS = 6
RECENT_RECEIPTS = 6       # receipts that decide whether a supply risk source is still active
YOUNG_REGIME = 8
RESIDUAL_WINDOW = 12      # recent one-step residuals that define the calibrated spread
DEAD_BAND = 1.25          # calibration ratio below which the fitted spread is trusted as is
RATIO_CAP = 2.            # calibration widening never more than doubles the fitted spread
OUTLIER_Z = 3.            # a residual beyond this many robust sd is an outlier, not a regime
FLOOR_CREDIBILITY = .1    # the declared stress never drops below a tenth of its weight          # observations before a detected level shift is treated as confirmed


def z_for(level: float) -> float:
    """Standard-normal quantile for a service level, floored at the median."""
    return float(norm.ppf(min(max(level, .5), .9999)))


def _predict(a: np.ndarray, method: str) -> float:
    return float(np.mean(a[-4:])) if method == "recent_level" else point(a, method)


def residual_calibration(y: np.ndarray, method: str, window: int = RESIDUAL_WINDOW, robust: bool = True) -> dict:
    """One-step-ahead residuals of the chosen method on the most recent observations.

    calibration_ratio > 1 means realized errors are wider than the fitted spread implies; the
    protection layer scales by it instead of trusting the fitted standard deviation. With
    robust=True the residual scale is the 80th percentile of absolute residuals (one abnormal
    week does not widen it for the whole window); robust=False is the PR30 root-mean-square.
    """
    start = max(4, len(y) - window)
    residuals = np.asarray([y[t] - _predict(y[:t], method) for t in range(start, len(y))])
    sd = float(np.std(y)) if len(y) > 1 else 0.
    if not len(residuals):
        return {"residual_sd": sd, "residual_rms": sd, "abs_q80": 1.2816 * sd, "calibration_ratio": 1., "bias": 0.,
                "window": 0, "last_outlier_age": None, "outliers": 0}
    residual_rms = float(np.sqrt(np.mean(residuals ** 2)))
    abs_q80 = float(np.quantile(np.abs(residuals), .8))
    robust_sd = abs_q80 / 1.2816
    residual_sd = robust_sd if robust else residual_rms
    ratio = abs_q80 / max(1.2816 * sd, 1e-9) if sd > 0 else 1.
    flags = np.abs(residuals) > OUTLIER_Z * max(robust_sd, 1.)
    ages = [len(residuals) - 1 - i for i, f in enumerate(flags) if f]
    return {"residual_sd": float(residual_sd), "residual_rms": residual_rms, "abs_q80": abs_q80,
            "calibration_ratio": float(min(4., max(.25, ratio))), "bias": float(np.mean(residuals)),
            "window": int(len(residuals)), "last_outlier_age": (min(ages) if ages else None), "outliers": int(flags.sum())}


def demand_state(uncertainty: dict) -> float:
    """How active the demand risk driver is, 0 (calm) to 1. Only events count: a level change
    still younger than YOUNG_REGIME observations, or a cluster of outliers (two or more in the
    residual window). Persistent calibration widening is not an event: it already widens the
    scenario spread, and counting it here as well would double-protect a noisy but steady SKU."""
    age = uncertainty.get("regime_age")
    young = max(0., 1. - age / YOUNG_REGIME) if age is not None else 0.
    outliers = int(uncertainty.get("outliers", 0) or 0)
    last = uncertainty.get("last_outlier_age")
    cluster = .5 if outliers >= 2 and last is not None and last < RESIDUAL_WINDOW // 2 else 0.
    return float(max(young, cluster))


def periods_to_lean_demand(uncertainty: dict) -> int:
    """Reviews until the active demand drivers leave the evidence windows, if nothing new happens."""
    remaining = 0
    outliers = int(uncertainty.get("outliers", 0) or 0)
    age_out = uncertainty.get("last_outlier_age")
    if outliers >= 2 and age_out is not None:
        remaining = max(remaining, RESIDUAL_WINDOW // 2 - int(age_out))
    age = uncertainty.get("regime_age")
    if age is not None and age < YOUNG_REGIME:
        remaining = max(remaining, YOUNG_REGIME - int(age))
    return int(remaining)


INTERMITTENT_ZERO_SHARE = .3


def intermittent_profile(y: np.ndarray, fit: dict) -> dict | None:
    """Occurrence probability and conditional positive size for sparse demand, with a robust
    size spread so one historical spike does not define the tail. None for regular demand."""
    if float(fit.get("zero_probability", 0.)) < INTERMITTENT_ZERO_SHARE:
        return None
    origin = int(fit.get("segment_origin", 0))
    segment = y[origin:] if len(y[origin:]) >= 8 else y
    positives = segment[segment > 0]
    if len(positives) < 3:
        return None
    occurrence = float(np.mean(segment > 0))
    med = float(np.median(positives))
    mad = float(np.median(np.abs(positives - med))) * 1.4826
    robust_sd = max(mad, .1 * med)
    cap = med + OUTLIER_Z * robust_sd
    spikes = int(np.sum(positives > cap))
    size_mean = float(np.mean(np.minimum(positives, cap)))
    per_period_var = occurrence * (robust_sd ** 2 + size_mean ** 2) - (occurrence * size_mean) ** 2
    return {"occurrence": occurrence, "size_median": med, "size_mean_capped": size_mean, "size_robust_sd": robust_sd,
            "size_cap": float(cap), "historical_spikes": spikes, "per_period_sd": float(math.sqrt(max(0., per_period_var))),
            "scope": "Bernoulli occurrence x capped positive size; zero runs reproduce the observed occurrence rate"}


def demand_uncertainty(fit: dict, y: np.ndarray, decay: bool = True) -> dict:
    """Effective spread, level standard error and regime uncertainty for one service.

    decay=True (state-dependent protection): robust residual scale, a dead band and cap on the
    calibration ratio, and a young regime represented as a bounded mixture (the old level may
    still be the truth, with a weight that fades as observations confirm the new one) instead
    of a symmetric widening by the size of the shift. decay=False is the PR30 behaviour.
    """
    origin = int(fit.get("segment_origin", 0))
    segment = y[origin:]
    calibration = residual_calibration(segment, fit["method"], robust=decay)
    n = max(1, len(segment))
    level_se = calibration["residual_sd"] / math.sqrt(n)
    regime, pre_mean, pre_weight, downward = 0., None, 0., False
    if origin > 0 and n < YOUNG_REGIME:
        pre_mean = float(np.mean(y[:origin]))
        regime = abs(float(fit["mean"]) - pre_mean) * (1. - n / YOUNG_REGIME)
        downward = float(fit["mean"]) < pre_mean
        # Bounded mixture after a drop: the chance the old, higher level still holds, fading to
        # zero as the regime ages. After a rise the shortage side is the expensive one, so the
        # level error keeps the full shift-sized widening (the PR30 rule) instead of a mixture
        # that would lean the plan toward the old, lower level.
        pre_weight = .5 * (1. - n / YOUNG_REGIME) if downward else 0.
    raw_ratio = float(calibration["calibration_ratio"])
    if decay:
        # Calibrate the spread to realized one-step error: the residual RMS against the fitted
        # spread, inside a small dead band and the cap. Under-coverage widens, never narrows.
        # Robust residual scale (one spike does not widen it) against the fitted spread.
        rms_ratio = calibration["residual_sd"] / max(float(fit["sd"]), 1e-9) if fit["sd"] > 0 else 1.
        ratio = 1. if rms_ratio <= 1.1 else min(RATIO_CAP, rms_ratio)
        level_total = level_se if downward or regime == 0. else math.sqrt(level_se ** 2 + regime ** 2)
    else:
        ratio = raw_ratio
        level_total = math.sqrt(level_se ** 2 + regime ** 2)
        pre_weight = 0.
    sd_effective = max(float(fit["sd"]), calibration["residual_sd"])
    intermittent = intermittent_profile(y, fit) if decay else None
    if intermittent is not None:
        # Sparse demand: the spread is the occurrence/size decomposition with a capped size tail,
        # not the raw standard deviation of a series that is mostly zeros with one spike in it.
        sd_effective = intermittent["per_period_sd"]
        ratio = 1.
    return {"sd_fitted": float(fit["sd"]), "sd_effective": float(sd_effective), "intermittent": intermittent,
            "residual_sd": calibration["residual_sd"], "residual_rms": calibration["residual_rms"],
            "calibration_ratio": float(ratio), "calibration_ratio_raw": raw_ratio,
            "bias": calibration["bias"], "level_se": float(level_total), "regime_uncertainty": float(regime),
            "regime_age": (int(n) if origin > 0 else None), "pre_change_level": pre_mean, "pre_change_weight": float(pre_weight),
            "last_outlier_age": calibration["last_outlier_age"], "outliers": calibration["outliers"],
            "segment_count": int(n), "history_count": int(len(y)),
            "data_sufficiency": "thin" if len(y) < 26 or n < 4 else "adequate",
            "decay": decay,
            "scope": "one-step residuals of the chosen method since the last detected change"}


@dataclass(frozen=True)
class SupplyProfile:
    source: str
    scope: str                         # "declared" or "observed"
    records: int
    censored: int
    fill_mean: float
    fill_sd: float
    partial_probability: float         # P(accepted ratio < .95)
    fill_samples: tuple[float, ...]
    declared_lead_days: int
    lead_sd_days: float
    lead_support: tuple[tuple[int, float], ...]   # unconditional Kaplan-Meier support in days
    lead_p50: int | None
    lead_p90: int | None
    late_probability: float            # mass arriving after the declared lead, unresolved tail included
    tail_days: int                     # p90 minus declared lead, never negative
    unresolved_mass: float
    recent_late_probability: float = 0.   # last RECENT_RECEIPTS arrived records only (risk-source half-life)
    recent_partial_probability: float = 0.
    recent_records: int = 0


def supply_profile(source: Source, history: tuple[ShipmentObservation, ...], period_days: int = 7,
                   overdue_as_late: bool = False) -> SupplyProfile:
    """Per source fill and lead distributions from its own censored history, else declared.

    "Late" means arriving more than half a planning period after the declared lead, since
    anything inside that lands in the same review period. With overdue_as_late (v5) an open
    order that is already past the declared lead counts as a late record in the recent window:
    a closure shows in the risk state while the orders are still outstanding, not only once
    they finally land."""
    ratios = tuple(float(r.accepted_ratio) for r in history
                   if r.source == source.id and r.arrived and r.accepted_ratio is not None)
    declared = source.lead_days + source.dispatch_days
    eta = conditional_eta(history, source.id, 0)
    observed = len(ratios) >= MIN_SUPPLY_RECORDS or bool(eta.support)
    if len(ratios) >= MIN_SUPPLY_RECORDS:
        fill_mean, fill_sd = float(np.mean(ratios)), float(np.std(ratios))
        partial = float(np.mean(np.asarray(ratios) < .95))
    else:
        fill_mean, fill_sd = source.fill_mean, source.fill_sd
        partial = float(norm.cdf((.95 - fill_mean) / fill_sd)) if fill_sd > 0 else float(fill_mean < .95)
    slack = period_days / 2.
    if eta.support:
        late = sum(m for d, m in eta.support if d > declared + slack) + eta.unresolved_mass
        p90 = eta.p90
    else:
        late = float(1 - norm.cdf(slack / source.lead_sd_days)) if source.lead_sd_days > 0 else 0.
        p90 = int(round(declared + 1.2816 * source.lead_sd_days))
    tail = max(0, (p90 if p90 is not None else declared) - declared)
    # Recency: the risk *state* follows the last few receipts, the distribution keeps the whole
    # record. A route that closed and reopened, or a supplier that recovered, shows clean recent
    # receipts long before its full history looks clean again.
    arrived = sorted((r for r in history if r.source == source.id and r.arrived), key=lambda r: r.known_at)
    overdue = [r for r in history if r.source == source.id and not r.arrived and r.elapsed_days > declared + slack] if overdue_as_late else []
    recent = sorted(arrived + overdue, key=lambda r: r.known_at)[-RECENT_RECEIPTS:]
    recent_late = float(np.mean([r.elapsed_days > declared + slack for r in recent])) if recent else (late if not eta.support else late)
    recent_ratios = [float(r.accepted_ratio) for r in recent if r.arrived and r.accepted_ratio is not None]
    recent_partial = float(np.mean(np.asarray(recent_ratios) < .9)) if recent_ratios else partial
    return SupplyProfile(source.id, "observed" if observed else "declared", eta.records, eta.censored,
                         fill_mean, fill_sd, partial, ratios, declared, float(source.lead_sd_days), eta.support, eta.p50, p90,
                         float(min(1., late)), int(tail), eta.unresolved_mass,
                         recent_late_probability=recent_late, recent_partial_probability=recent_partial, recent_records=len(recent))


def supply_profiles(req: Request) -> dict[str, SupplyProfile]:
    return {s.id: supply_profile(s, req.shipment_history, req.period_days, overdue_as_late=req.protection_v5) for s in req.sources}


def overdue_periods(source: Source, age_days: int, period_days: int) -> int:
    """Whole planning periods an open order is past the source's declared lead-time tail
    (declared lead plus dispatch plus 1.28 sd). Zero while the declared model still covers it."""
    tail = source.lead_days + source.dispatch_days + 1.2816 * source.lead_sd_days
    return max(0, math.ceil((age_days - tail) / period_days))


def lead_quantile(profile: SupplyProfile, u: float) -> int:
    """Lead time in days at probability u from the observed support, else the declared spread."""
    if profile.lead_support:
        cumulative = 0.
        for days, mass in profile.lead_support:
            cumulative += mass
            if u <= cumulative + 1e-12:
                return int(days)
        # Beyond the observed support: the unresolved tail is at least as long as the longest arrival.
        return int(profile.lead_support[-1][0]) + profile.declared_lead_days
    z = float(norm.ppf(min(max(u, 1e-6), 1 - 1e-6)))
    return max(0, int(round(profile.declared_lead_days + z * profile.lead_sd_days)))


def failure_domains_for(source: Source, resources: dict[str, Resource]) -> tuple[str, ...]:
    """Declared resource failure domains plus every intermediate itinerary node.

    Ports, borders, terminals, lanes and carriers on the route are shared exposure whether or
    not an operator declared them as a resource domain. The supplier itself and the receiving
    location are excluded: the supplier is its own domain, and the destination is common to
    every source serving it.
    """
    declared = {d for r in source.resources for d in resources[r].failure_domains}
    return tuple(sorted(declared | set(source.route[1:-1])))


def diversification(req: Request, sku: str, location: str, profile: str = "reliability") -> dict:
    """Capacity-weighted effective number of independent sources for one SKU at one location."""
    resources = {r.id: r for r in req.resources}
    eligible = [s for s in req.sources if s.sku == sku and s.destination == location
                and s.approved and s.compliance == "cleared"]
    if not eligible:
        return {"eligible_sources": 0, "effective_independent_sources": 0., "shared_domains": [],
                "suppliers": [], "scope": "no approved cleared source"}
    capacity = np.asarray([max(0., min(s.maximum, s.capacity_by_period[0])) for s in eligible])
    share = capacity / capacity.sum() if capacity.sum() > 0 else np.full(len(eligible), 1. / len(eligible))
    if profile == "reliability":
        domains = {s.id: set(failure_domains_for(s, resources)) for s in eligible}
    else:
        domains = {s.id: {d for r in s.resources for d in resources[r].failure_domains} for s in eligible}
    n = len(eligible)
    rho = np.eye(n)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = eligible[i], eligible[j]
            if a.supplier == b.supplier or domains[a.id] & domains[b.id]:
                rho[i, j] = rho[j, i] = 1.
    concentration = float(share @ rho @ share)
    effective = 1. / max(1e-9, concentration)
    shared = sorted(set.intersection(*(domains[s.id] for s in eligible))) if n > 1 else []
    return {"eligible_sources": n, "effective_independent_sources": effective,
            "shared_domains": shared, "suppliers": sorted({s.supplier for s in eligible}),
            "domains": {s.id: sorted(domains[s.id]) for s in eligible},
            "scope": "capacity-weighted; sources sharing a supplier or any failure domain count as one"}


def supply_state(profile: SupplyProfile, severity: float = 0., recency: bool = False) -> float:
    """How active the supply risk driver is, 0 to 1: lateness beyond the declared lead, a fill
    mean materially below full delivery, a wide fill spread, and licensed route signals. A
    source that delivers about 95% on time with a tight spread scores zero: that is normal
    supply, not a risk driver. With recency=True (v5) the lateness and partial-delivery terms
    come from the last RECENT_RECEIPTS receipts, so the driver retires after a clean run instead
    of after the whole history has been diluted."""
    shortfall = max(0., (.9 - profile.fill_mean) * 5.)
    spread = max(0., (profile.fill_sd - .05) * 10.)
    if recency and profile.recent_records >= 3:
        late = profile.recent_late_probability
        partial = profile.recent_partial_probability
        return float(min(1., 2. * late + 1.5 * partial + shortfall * (.5 if partial == 0 else 1.) + spread * .5 + severity))
    return float(min(1., 2. * profile.late_probability + shortfall + spread + severity))


def resilience(window: int, effective_sources: float, substitute_cover: float, demand_per_window: float,
               alternative_inside_window: bool | None = None) -> float:
    """How much the SKU can absorb a shock without protection: short replenishment plus a real
    alternative (independent source that can arrive inside the service window, or substitute
    stock covering the window) is 1, one of the two is .5, neither is 0. An alternate that is
    approved but too slow or too small to land inside the window earns no credit (v5)."""
    short = window <= 2
    usable_alternate = effective_sources >= 1.5 and (alternative_inside_window is None or alternative_inside_window)
    alternative = usable_alternate or substitute_cover >= demand_per_window
    return 1. if short and alternative else (.5 if short or alternative else 0.)


def protection_activity(demand: float, supply: float, resilient: float) -> float:
    """Protection state in [0, 1]: the most active risk driver, discounted by resilience.
    Zero means lean; the optimizer's quantile protection and the stress hedge scale with it."""
    return float(max(0., min(1., max(demand, supply) * (1. - .5 * resilient))))


def stress_credibility(req: Request, supply: dict[str, SupplyProfile]) -> dict:
    """How much weight the declared stress envelopes deserve right now, from evidence only.

    The declared stress is an assumption. It earns weight when the sources' own lateness and
    partial-delivery probabilities (observed history, else declared spread) or licensed route
    evidence say the supply tail is real, and loses weight when the observed supply is clean.
    The floor keeps a small hedge; the ceiling is the operator's stress_weight.
    """
    from zaad.signals import Signal, route_evidence
    resources = {r.id: r for r in req.resources}
    signals = tuple(Signal.model_validate_json(json.dumps(v)) for v in req.signals)
    worst, drivers = 0., {}
    for source in req.sources:
        if not (source.approved and source.compliance == "cleared"):
            continue
        profile = supply[source.id]
        evidence = route_evidence(signals, [source.id, source.supplier, *source.route, *source.resources,
                                            *failure_domains_for(source, resources)], req.as_of)
        severity = max(evidence.physical_severity, evidence.official_severity)
        score = supply_state(profile, severity, recency=req.protection_v5)
        drivers[source.id] = {"late_probability": profile.late_probability, "partial_probability": profile.partial_probability,
                              "signal_severity": severity, "scope": profile.scope, "score": score}
        worst = max(worst, score)
    # The floor is a hedge against having no record at all. Once every approved source has an
    # observed record, the evidence alone decides and a clean record means no hedge.
    declared_only = any(supply[s.id].scope == "declared" for s in req.sources if s.approved and s.compliance == "cleared")
    floor = FLOOR_CREDIBILITY if (declared_only or not req.protection_decay) else 0.
    if req.protection_decay and declared_only:
        # Selective robustness: with no observed record, a long replenishment and no independent
        # alternative earn the declared stress twice the floor; a short, diversified lane earns none.
        from zaad.full.worlds import dates
        eligible = [s for s in req.sources if s.approved and s.compliance == "cleared"]
        longest = max((dates(req, s, 0)[1] for s in eligible), default=0)
        suppliers = {s.supplier for s in eligible}
        if longest >= 3 and len(suppliers) < 2:
            floor = min(1., 2 * FLOOR_CREDIBILITY)
        elif longest <= 1 and len(suppliers) >= 2:
            floor = 0.
    credibility = min(1., max(floor, worst))
    return {"credibility": credibility, "effective_stress_weight": req.stress_weight * credibility, "floor": floor,
            "drivers": drivers, "scope": "max over approved sources of the supply risk state (lateness, fill shortfall, fill spread, signals); floored only while a source has no observed record"}


def profile_dict(profile: SupplyProfile) -> dict:
    return asdict(profile)
