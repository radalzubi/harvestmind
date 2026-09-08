"""Calendar-aware paths and distinct, explicitly assumed misspecification envelopes."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import math
import json

import numpy as np

from zaad.full.contracts import Calendar, Request, Source, Stress
from zaad.full.eta import conditional_eta
from zaad.full.forecast import estimate, sample
from zaad.full.uncertainty import MIN_SUPPLY_RECORDS, OUTLIER_Z, demand_uncertainty, failure_domains_for, lead_quantile, overdue_periods, recent_fill_run, supply_profiles
from zaad.signals import Signal, route_evidence
from scipy.stats import norm


@dataclass(frozen=True)
class World:
    name: str
    weight: float
    demand: dict[str, tuple[float, ...]]
    arrival: dict[tuple[str, int], int]
    fills: dict[tuple[str, int], float]
    po_due: dict[str, int]
    po_fill: dict[str, float]


def next_open(date: datetime, calendar: Calendar) -> datetime:
    value = date
    if value.hour >= calendar.cutoff_hour_utc:
        value = (value + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    for _ in range(732):
        if value.weekday() in calendar.weekdays and value.date().isoformat() not in calendar.blackout_dates:
            return value
        value = (value + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    raise ValueError("calendar has no feasible date within two years")


def dates(req: Request, source: Source, t: int, extra_days: int = 0) -> tuple[int, int]:
    calendars = {c.id: c for c in req.calendars}
    location = next(location_key for location_key in req.locations if location_key.id == source.destination)
    origin = req.as_of + timedelta(days=req.period_days * t)
    order = next_open(origin, calendars[source.order_calendar])
    production = order
    if source.production_workdays:
        assert source.production_calendar is not None
    for _ in range(source.production_workdays):
        assert source.production_calendar is not None
        production = next_open(production + timedelta(days=1), calendars[source.production_calendar])
    depart = next_open(production + timedelta(days=source.dispatch_days), calendars[source.shipping_calendar])
    if source.leg_transit_days:
        arrive = depart
        for days, calendar in zip(source.leg_transit_days, source.leg_arrival_calendars):
            arrive = next_open(arrive + timedelta(days=days), calendars[calendar])
        arrive += timedelta(days=extra_days)
        arrive = next_open(arrive, calendars[location.receiving_calendar])
    else:
        arrive = next_open(depart + timedelta(days=max(1, source.lead_days + extra_days)),
                           calendars[location.receiving_calendar])
    def period(d):
        return math.ceil((d - req.as_of).total_seconds() / (86400 * req.period_days))
    return period(depart), max(t + 1, period(arrive))


def history_series(req: Request) -> dict[str, np.ndarray]:
    result = {}
    for service in req.services:
        rows = sorted((r for r in req.history if r.service == service.id), key=lambda r: r.period)
        if [r.period for r in rows] != list(range(-len(rows), 0)):
            raise ValueError("demand history must be consecutive and end before origin")
        result[service.id] = np.asarray([r.quantity for r in rows])
    return result


def forecast_all(req: Request, adaptive: bool = True) -> dict:
    skus = {s.id: s for s in req.skus}
    locations = {location_key.id: location_key for location_key in req.locations}
    result = {}
    series = history_series(req)
    for service in req.services:
        fit = estimate(series[service.id], service.selling_price + service.sla_per_unmet,
                       locations[service.location].holding_per_value_period * skus[service.sku].asset_value,
                       adaptive, req.demand_adaptation)
        if req.engine_profile == "reliability":
            fit["uncertainty"] = demand_uncertainty(fit, series[service.id], req.protection_decay)
        result[service.id] = fit
    return result


# Diagnostic switches (P1 cell-90 investigation). Shipped behaviour is both True; an isolating arm
# flips one at a time. STRATIFY_BODY False draws the body worlds over the whole unit interval
# (tail world still added); STRATIFY_WEIGHTS False gives every world weight 1/count.
STRATIFY_BODY = True
STRATIFY_WEIGHTS = True
# When True the stratified uniforms come from a generator of their own (seeded from the draw seed),
# so the supply shocks drawn after demand are the same stream as an unstratified draw. Diagnostic
# default False reproduces the coupled behaviour under investigation.
STRATIFY_DECOUPLED_RNG = False


def draw(req: Request, seed: int, count: int, stress: Stress | None = None,
         deterministic: bool = False, adaptive: bool = True) -> list[World]:
    rng = np.random.default_rng(seed)
    fits = forecast_all(req, adaptive)
    resources = {r.id: r for r in req.resources}
    sources_by_id = {s.id: s for s in req.sources}
    signals = tuple(Signal.model_validate_json(json.dumps(v)) for v in req.signals)
    reliability = req.engine_profile == "reliability"
    supply = supply_profiles(req) if reliability else {}
    worlds = []
    # Target-stratified worlds (P1 closure): the last world is the tail beyond the lowest service
    # target, the others the body below it, each weighted by its stratum's probability mass.
    stratified = bool(req.stratified_scenarios) and count >= 2 and not deterministic
    q_tail = min((s.target for s in req.services), default=.95) if stratified else None
    weights = ([q_tail / (count - 1)] * (count - 1) + [1. - q_tail]) if (stratified and STRATIFY_WEIGHTS) else [1. / count] * count
    rng_strata = np.random.default_rng(seed + 7_000_003) if (stratified and STRATIFY_DECOUPLED_RNG) else rng
    for w in range(count):
        demand, arrival, fills, po_due, po_fill = {}, {}, {}, {}, {}
        for service in req.services:
            f = fits[service.id]
            if stratified:
                lo, hi = (q_tail, 1.) if w == count - 1 else ((0., q_tail) if STRATIFY_BODY else (0., 1.))
                d = sample(f, rng, req.horizon, u=lo + rng_strata.random(req.horizon) * (hi - lo))
                if rng_strata is rng:
                    pass
                elif not deterministic:
                    # keep the main stream aligned with an unstratified draw: consume what sample() would have
                    rng.choice(np.asarray(f["sizes"]) if len(f["sizes"]) else np.zeros(1), req.horizon); rng.random(req.horizon)
            else:
                d = np.full(req.horizon, f["mean"]) if deterministic else sample(f, rng, req.horizon)
            if reliability and req.protection_decay and not deterministic and f.get("uncertainty", {}).get("intermittent"):
                # Sparse demand: Bernoulli occurrence at the observed rate, positive size resampled
                # from history with the size tail capped, mean preserved. Zero runs are realistic
                # and a single historical spike cannot recur every period.
                inter = f["uncertainty"]["intermittent"]
                sizes = np.asarray(f["sizes"])
                sizes = np.minimum(sizes, inter["size_cap"])
                occurs = rng.random(req.horizon) < inter["occurrence"]
                draw_sizes = rng.choice(sizes, req.horizon) if len(sizes) else np.zeros(req.horizon)
                scale = f["mean"] / max(1e-9, inter["occurrence"] * float(np.mean(sizes))) if len(sizes) and f["mean"] > 0 else 1.
                d = np.where(occurs, draw_sizes * min(scale, 1.5), 0.)
            if reliability and not deterministic and f["mean"] > 0:
                u = f["uncertainty"]
                # Calibration: when realized one-step errors have been wider than the fitted spread,
                # widen the sampled deviations by that ratio (never narrow them).
                ratio = max(1., u["calibration_ratio"])
                if ratio > 1.:
                    d = np.maximum(0., f["mean"] + (d - f["mean"]) * ratio)
                if req.protection_decay and u.get("outliers", 0) and not u.get("intermittent"):
                    # One abnormal week is not a demand regime: cap sampled sizes at the outlier
                    # bound so a single spike does not populate the scenarios for a whole window.
                    bound = f["mean"] + OUTLIER_Z * max(u["residual_sd"], 1.) * ratio
                    d = np.minimum(d, bound)
                # Model uncertainty: the level itself is uncertain by its calibrated standard error,
                # perfectly correlated across the horizon. While a regime change is young, some
                # worlds keep the old level instead (bounded mixture), so a drop does not fabricate
                # demand above the old level and a rise does not fabricate demand below it.
                u = f["uncertainty"]
                if stratified and w == count - 1:
                    # The tail world is the tail of the per-period noise at the fitted level; the
                    # level uncertainty and the young-regime mixture stay with the body worlds, so
                    # the tail never compounds a high level with high noise into a path no fitted
                    # world could produce. With decoupled strata the level draws are still consumed
                    # (and discarded) so the supply stream that follows matches an unstratified draw.
                    if STRATIFY_DECOUPLED_RNG:
                        if u.get("pre_change_level") is not None and u.get("pre_change_weight", 0.) > 0:
                            if not (float(rng.random()) < u["pre_change_weight"]):
                                rng.normal()
                        else:
                            rng.normal()
                elif u.get("pre_change_level") is not None and u.get("pre_change_weight", 0.) > 0 and float(rng.random()) < u["pre_change_weight"]:
                    d = d * max(0., u["pre_change_level"] / f["mean"])
                else:
                    d = d * max(0., 1. + float(rng.normal()) * u["level_se"] / f["mean"])
            for event in req.events:
                if event.service == service.id:
                    d[event.start:min(req.horizon, event.end + 1)] *= event.multiplier
            if stress:
                d *= stress.demand_multiplier
            for line in req.order_lines:
                if line.service == service.id and line.due_in < req.horizon and line.open_quantity > 0:
                    # Firm lines replace the forecast lower bound, not double-counted additive demand.
                    firm = sum(x.open_quantity for x in req.order_lines
                               if x.service == service.id and x.due_in == line.due_in)
                    d[line.due_in] = max(d[line.due_in], firm)
            demand[service.id] = tuple(float(x) for x in d)
        common = {}
        for source in req.sources:
            if reliability:
                domains = list(failure_domains_for(source, resources))
            else:
                domains = sorted({d for r in source.resources for d in resources[r].failure_domains})
            evidence = route_evidence(signals, [source.id, source.supplier, *source.route, *source.resources, *domains], req.as_of)
            severity = max(evidence.physical_severity, evidence.official_severity)
            for t in range(req.horizon):
                active = stress is not None and t < stress.recovery_period and (not stress.affected_resources or bool(set(source.resources) & set(stress.affected_resources)))
                # Shared-domain Gaussian factor; exact duplicates share the same shock.
                keys = domains or [source.id]
                if active and stress is not None and stress.shared_failure:
                    keys = ["stress_common_failure"]
                for key in keys:
                    if (key, t) not in common:
                        common[key, t] = float(rng.normal())
                z = 0. if deterministic else sum(common[key, t] for key in keys) / math.sqrt(len(keys))
                profile = supply.get(source.id)
                if profile is not None and profile.scope == "observed":
                    # The source's own history through the shared factor: fill from its accepted
                    # ratios, lead from its censored Kaplan-Meier support, tail included.
                    u = float(norm.cdf(z))
                    f = float(np.quantile(profile.fill_samples, u)) if len(profile.fill_samples) >= MIN_SUPPLY_RECORDS else float(np.clip(profile.fill_mean + profile.fill_sd * z, 0, 1))
                    delay = max(0, lead_quantile(profile, 1 - u) - profile.declared_lead_days)
                else:
                    f = float(np.clip(source.fill_mean + source.fill_sd * z, 0, 1))
                    delay = max(0, round(-source.lead_sd_days * z))
                # Recent fill run (v5): a run of short receipts sets the fill expectation for the next
                # orders even when the whole record is too short, or too long, to show it.
                run = recent_fill_run(profile) if (req.protection_v5 and profile is not None) else None
                if run is not None and profile is not None:
                    f = min(f, float(np.clip(run + profile.fill_sd * z, 0, 1)))
                # Declared mapping retained from v1, not a learned disruption probability.
                f *= 1 - .3 * severity
                delay += math.ceil(3 * severity) * req.period_days
                if active and stress is not None:
                    f *= stress.fill_multiplier
                    delay += stress.extra_lead_days
                fills[source.id, t] = 1. if req.force_unit_fills else f
                arrival[source.id, t] = dates(req, source, t, delay)[1]
        # Backlog-implied lead (v5): when a source's recent orders are all late and some are already
        # overdue, its outstanding orders ship in sequence, so no younger order can land before the
        # oldest overdue one would. The freshest order stops being "due next period" while the
        # backlog stands; the planner sources elsewhere or transfers instead of waiting again.
        backlog_age: dict[str, int] = {}
        if req.protection_v5:
            for po in req.pipeline:
                profile = supply.get(po.source)
                age = max(0, (req.as_of - po.placed_at).days)
                if profile is not None and profile.recent_records >= 3 and profile.recent_late_probability >= .5 \
                        and overdue_periods(sources_by_id[po.source], age, req.period_days) >= 1:
                    backlog_age[po.source] = max(backlog_age.get(po.source, 0), age)
        for po in req.pipeline:
            keep = next(o for o in po.options if o.action == "keep")
            eta = conditional_eta(req.shipment_history, po.source,
                                  max(0, (req.as_of - po.placed_at).days), po.stage, po.carrier)
            # An unreceived PO is not opening stock, even if its quoted ETA is
            # overdue. Replay materializes observed receipts before planning.
            due = max(1, keep.due_in)
            if eta.support:
                u, cdf = (.5 if deterministic else float(rng.random())), 0.
                due = req.horizon + 1  # unsupported survival tail stays outside horizon
                for days, mass in eta.support:
                    cdf += mass
                    if u <= cdf:
                        due = max(1, math.ceil(days / req.period_days))
                        break
            elif eta.scope == "outside_support":
                due = req.horizon + 1
            elif req.protection_v5:
                # Overdue-order survival (v5): with too little history for a conditional ETA, an order
                # already past the declared lead-time tail is not assumed to land next period forever.
                # Each overdue period halves the chance it lands inside the horizon; the rest of the
                # mass stays outside it, so the planner sources elsewhere instead of waiting.
                age = max(0, (req.as_of - po.placed_at).days)
                behind = overdue_periods(sources_by_id[po.source], age, req.period_days)
                if behind >= 1:
                    p_in = .5 ** behind
                    inside = (p_in >= .5) if deterministic else (float(rng.random()) < p_in)
                    due = max(1, keep.due_in) if inside else req.horizon + 1
            if po.source in backlog_age:
                age = max(0, (req.as_of - po.placed_at).days)
                if age < backlog_age[po.source]:
                    due = max(due, math.ceil((backlog_age[po.source] - age) / req.period_days) + 1)
            # No history is explicitly quote-based, not falsely labelled calibrated ETA.
            if stress and due < stress.recovery_period:
                due += math.ceil(stress.extra_lead_days / req.period_days)
            po_due[po.id] = due
            po_fill[po.id] = po.expected_accepted_remaining / po.remaining if po.remaining > 0 else 0.
            if req.protection_v5 and po.source in supply:
                # An open order is filled the way the source is filling now, not the way it was quoted.
                run = recent_fill_run(supply[po.source])
                if run is not None:
                    po_fill[po.id] = min(po_fill[po.id], run)
            if stress:
                po_fill[po.id] *= stress.fill_multiplier
            if req.force_unit_fills:
                po_fill[po.id] = 1.
        label = f"{stress.name if stress else 'fitted'}:{seed}:{w}" + (":tail" if stratified and w == count - 1 else "")
        worlds.append(World(label, weights[w], demand, arrival, fills, po_due, po_fill))
    return worlds
