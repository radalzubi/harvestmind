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
from zaad.signals import Signal, route_evidence


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


def forecast_all(req: Request, adaptive: bool = True) -> dict:
    skus = {s.id: s for s in req.skus}
    locations = {location_key.id: location_key for location_key in req.locations}
    result = {}
    for service in req.services:
        rows = sorted((r for r in req.history if r.service == service.id), key=lambda r: r.period)
        if [r.period for r in rows] != list(range(-len(rows), 0)):
            raise ValueError("demand history must be consecutive and end before origin")
        result[service.id] = estimate(np.asarray([r.quantity for r in rows]),
                                     service.selling_price + service.sla_per_unmet,
                                     locations[service.location].holding_per_value_period * skus[service.sku].asset_value,
                                     adaptive)
    return result


def draw(req: Request, seed: int, count: int, stress: Stress | None = None,
         deterministic: bool = False, adaptive: bool = True) -> list[World]:
    rng = np.random.default_rng(seed)
    fits = forecast_all(req, adaptive)
    resources = {r.id: r for r in req.resources}
    signals = tuple(Signal.model_validate_json(json.dumps(v)) for v in req.signals)
    worlds = []
    for w in range(count):
        demand, arrival, fills, po_due, po_fill = {}, {}, {}, {}, {}
        for service in req.services:
            f = fits[service.id]
            d = np.full(req.horizon, f["mean"]) if deterministic else sample(f, rng, req.horizon)
            for event in req.events:
                if event.service == service.id:
                    d[event.start:min(req.horizon, event.end + 1)] *= event.multiplier
            if stress:
                d *= stress.demand_multiplier
            for line in req.order_lines:
                if line.service == service.id and line.due_in < req.horizon:
                    # Firm lines replace the forecast lower bound, not double-counted additive demand.
                    firm = sum(x.quantity - x.filled - x.cancelled for x in req.order_lines
                               if x.service == service.id and x.due_in == line.due_in)
                    d[line.due_in] = max(d[line.due_in], firm)
            demand[service.id] = tuple(float(x) for x in d)
        common = {}
        for source in req.sources:
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
                f = float(np.clip(source.fill_mean + source.fill_sd * z, 0, 1))
                delay = max(0, round(-source.lead_sd_days * z))
                # Declared mapping retained from v1, not a learned disruption probability.
                f *= 1 - .3 * severity
                delay += math.ceil(3 * severity) * req.period_days
                if active and stress is not None:
                    f *= stress.fill_multiplier
                    delay += stress.extra_lead_days
                fills[source.id, t] = 1. if req.force_unit_fills else f
                arrival[source.id, t] = dates(req, source, t, delay)[1]
        for po in req.pipeline:
            keep = next(o for o in po.options if o.action == "keep")
            eta = conditional_eta(req.shipment_history, po.source,
                                  max(0, (req.as_of - po.placed_at).days), po.stage, po.carrier)
            due = keep.due_in
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
            # No history is explicitly quote-based, not falsely labelled calibrated ETA.
            if stress and due < stress.recovery_period:
                due += math.ceil(stress.extra_lead_days / req.period_days)
            po_due[po.id] = due
            po_fill[po.id] = po.expected_accepted_remaining / po.remaining
            if stress:
                po_fill[po.id] *= stress.fill_multiplier
            if req.force_unit_fills:
                po_fill[po.id] = 1.
        worlds.append(World(f"{stress.name if stress else 'fitted'}:{seed}:{w}", 1 / count,
                            demand, arrival, fills, po_due, po_fill))
    return worlds
