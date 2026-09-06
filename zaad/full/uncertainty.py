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
YOUNG_REGIME = 8
FLOOR_CREDIBILITY = .1    # the declared stress never drops below a tenth of its weight          # observations before a detected level shift is treated as confirmed


def z_for(level: float) -> float:
    """Standard-normal quantile for a service level, floored at the median."""
    return float(norm.ppf(min(max(level, .5), .9999)))


def _predict(a: np.ndarray, method: str) -> float:
    return float(np.mean(a[-4:])) if method == "recent_level" else point(a, method)


def residual_calibration(y: np.ndarray, method: str, window: int = 12) -> dict:
    """One-step-ahead residuals of the chosen method on the most recent observations.

    calibration_ratio > 1 means realized errors are wider than the fitted spread implies; the
    protection layer scales by it instead of trusting the fitted standard deviation.
    """
    start = max(4, len(y) - window)
    residuals = np.asarray([y[t] - _predict(y[:t], method) for t in range(start, len(y))])
    sd = float(np.std(y)) if len(y) > 1 else 0.
    if not len(residuals):
        return {"residual_sd": sd, "abs_q80": 1.2816 * sd, "calibration_ratio": 1., "bias": 0., "window": 0}
    residual_sd = float(np.sqrt(np.mean(residuals ** 2)))
    abs_q80 = float(np.quantile(np.abs(residuals), .8))
    ratio = abs_q80 / max(1.2816 * sd, 1e-9) if sd > 0 else 1.
    return {"residual_sd": residual_sd, "abs_q80": abs_q80, "calibration_ratio": float(min(4., max(.25, ratio))),
            "bias": float(np.mean(residuals)), "window": int(len(residuals))}


def demand_uncertainty(fit: dict, y: np.ndarray) -> dict:
    """Effective spread, level standard error and regime uncertainty for one service."""
    origin = int(fit.get("segment_origin", 0))
    segment = y[origin:]
    calibration = residual_calibration(segment, fit["method"])
    n = max(1, len(segment))
    level_se = calibration["residual_sd"] / math.sqrt(n)
    regime = 0.
    if origin > 0 and n < YOUNG_REGIME:
        # A young regime: the level is only known to within the size of the shift itself.
        pre_mean = float(np.mean(y[:origin]))
        regime = abs(float(fit["mean"]) - pre_mean) * (1. - n / YOUNG_REGIME)
    level_se = math.sqrt(level_se ** 2 + regime ** 2)
    sd_effective = max(float(fit["sd"]), calibration["residual_sd"])
    return {"sd_fitted": float(fit["sd"]), "sd_effective": float(sd_effective),
            "residual_sd": calibration["residual_sd"], "calibration_ratio": calibration["calibration_ratio"],
            "bias": calibration["bias"], "level_se": float(level_se), "regime_uncertainty": float(regime),
            "segment_count": int(n), "history_count": int(len(y)),
            "data_sufficiency": "thin" if len(y) < 26 or n < 4 else "adequate",
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


def supply_profile(source: Source, history: tuple[ShipmentObservation, ...], period_days: int = 7) -> SupplyProfile:
    """Per source fill and lead distributions from its own censored history, else declared.

    "Late" means arriving more than half a planning period after the declared lead, since
    anything inside that lands in the same review period."""
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
    return SupplyProfile(source.id, "observed" if observed else "declared", eta.records, eta.censored,
                         fill_mean, fill_sd, partial, ratios, declared, float(source.lead_sd_days), eta.support, eta.p50, p90,
                         float(min(1., late)), int(tail), eta.unresolved_mass)


def supply_profiles(req: Request) -> dict[str, SupplyProfile]:
    return {s.id: supply_profile(s, req.shipment_history, req.period_days) for s in req.sources}


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
        score = min(1., profile.late_probability + profile.partial_probability + severity)
        drivers[source.id] = {"late_probability": profile.late_probability, "partial_probability": profile.partial_probability,
                              "signal_severity": severity, "scope": profile.scope, "score": score}
        worst = max(worst, score)
    credibility = min(1., max(FLOOR_CREDIBILITY, worst))
    return {"credibility": credibility, "effective_stress_weight": req.stress_weight * credibility,
            "drivers": drivers, "scope": "max over approved sources of late + partial + signal severity, floored"}


def profile_dict(profile: SupplyProfile) -> dict:
    return asdict(profile)
