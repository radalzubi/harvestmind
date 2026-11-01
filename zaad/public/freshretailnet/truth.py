"""The settlement truth for a replay window: public demand, declared supply.

Demand comes from the dataset day by day after the origin (track A: observed sales; track B: recovered demand under
the pre-origin profile), so every policy is settled against the same path. Supply (arrival periods and fill ratios
per order) is drawn once per (series, origin, scenario, seed) from the DECLARED source parameters through the
frozen `zaad.full.worlds.draw`, exactly as the planner's own scenario machinery draws it, then the drawn demand is
replaced by the public path. The historical stockout flags never enter the truth: each policy's shortages and
stockouts are its own, produced by the settlement from its own stock and orders.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from typing import Any

from zaad.full.contracts import Request
from zaad.full.worlds import World, draw
from zaad.public.freshretailnet import recovery
from zaad.public.freshretailnet.request_builder import SeriesDays


def demand_path(series: SeriesDays, origin: date, *, track: str, periods: int) -> tuple[list[float], dict[str, Any]]:
    """The settlement demand for `periods` days from `origin` under one track, with its provenance."""
    future = [r for r in series.from_(origin)][:periods]
    if len(future) < periods:
        raise ValueError(f"only {len(future)} days from {origin}, {periods} needed")
    if track == "observed":
        return [r.sales for r in future], {"track": "observed", "evidence": "OBSERVED daily sales as the settlement demand (censored on the retailer's own stockout days)"}
    if track == "recovered":
        rec = recovery.recover_series(series.records, origin=origin)
        by_day = {r.day: r for r in rec}
        return [by_day[r.day].recovered for r in future], {"track": "recovered", **recovery.summary([by_day[r.day] for r in future]),
                                                            "note": "profile fitted on fully in-stock days before the origin only"}
    raise ValueError(track)


def with_demand(world: World, req: Request, path: list[float], name: str) -> World:
    """The same supply realization (arrivals, fills) with another demand path: the two tracks share one supply truth."""
    return replace(world, name=name, demand={req.services[0].id: tuple(float(x) for x in path)})


def truth_world(req: Request, series: SeriesDays, origin: date, *, track: str, periods: int, seed: int) -> tuple[World, dict[str, Any]]:
    """A truth covering `periods` daily periods from `origin` for the single service of `req`."""
    path, record = demand_path(series, origin, track=track, periods=periods)
    # declared supply, drawn through the planner's own machinery over the needed number of periods
    long = req.model_copy(update={"horizon": periods,
                                  "sources": tuple(s.model_copy(update={"capacity_by_period": tuple([s.capacity_by_period[0]] * periods)}) for s in req.sources),
                                  "resources": tuple(r.model_copy(update={"capacity_by_period": tuple([r.capacity_by_period[0]] * periods)}) for r in req.resources),
                                  "liquidity": req.liquidity.model_copy(update={"known_receivables": tuple([0.] * periods), "other_payments": tuple([0.] * periods)}),
                                  "stresses": tuple(s.model_copy(update={"recovery_period": periods}) for s in req.stresses)})
    drawn = draw(long, seed, 1)[0]
    service = req.services[0].id
    world = replace(drawn, name=f"truth-{track}-{origin.isoformat()}", weight=1., demand={service: tuple(float(x) for x in path)})
    record.update({"periods": periods, "first_day": origin.isoformat(), "last_day": (origin + timedelta(days=periods - 1)).isoformat(),
                   "supply_seed": seed, "arrival_offsets": sorted({world.arrival[k] - k[1] for k in world.arrival}),
                   "fill_min": min(world.fills.values()), "fill_max": max(world.fills.values()), "supply_evidence": "SYNTHETIC draw from the declaration"})
    return world, record
