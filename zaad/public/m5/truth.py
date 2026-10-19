"""Settlement truth for an M5 replay window: observed weekly sales as demand, declared supply drawn once per
(series, window, scenario) through the planner's own `worlds.draw`. M5 has no stockout annotation, so there is one
demand track (OBSERVED) and the fill figures measure service against sales, not against unobservable demand."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from typing import Any

from zaad.full.contracts import Request
from zaad.full.worlds import World, draw
from zaad.public.m5.request_builder import SeriesWeeks


def demand_path(series: SeriesWeeks, origin: date, *, periods: int) -> tuple[list[float], dict[str, Any]]:
    future = series.from_(origin)[:periods]
    if len(future) < periods:
        raise ValueError(f"only {len(future)} full weeks from {origin}, {periods} needed")
    return [w.sales for w in future], {"track": "observed", "evidence": "OBSERVED weekly unit sales as the settlement demand (stockouts unobservable in M5)",
                                       "first_week": future[0].start.isoformat(), "last_week": future[-1].end.isoformat()}


def truth_world(req: Request, series: SeriesWeeks, origin: date, *, periods: int, seed: int) -> tuple[World, dict[str, Any]]:
    path, record = demand_path(series, origin, periods=periods)
    long = req.model_copy(update={"horizon": periods,
                                  "sources": tuple(s.model_copy(update={"capacity_by_period": tuple([s.capacity_by_period[0]] * periods)}) for s in req.sources),
                                  "resources": tuple(r.model_copy(update={"capacity_by_period": tuple([r.capacity_by_period[0]] * periods)}) for r in req.resources),
                                  "liquidity": req.liquidity.model_copy(update={"known_receivables": tuple([0.] * periods), "other_payments": tuple([0.] * periods)}),
                                  "stresses": tuple(s.model_copy(update={"recovery_period": periods}) for s in req.stresses)})
    drawn = draw(long, seed, 1)[0]
    service = req.services[0].id
    world = replace(drawn, name=f"truth-{origin.isoformat()}", weight=1., demand={service: tuple(float(x) for x in path)})
    record.update({"periods": periods, "supply_seed": seed, "arrival_offsets": sorted({world.arrival[k] - k[1] for k in world.arrival}),
                   "fill_min": min(world.fills.values()), "fill_max": max(world.fills.values()), "supply_evidence": "SYNTHETIC draw from the declaration",
                   "last_truth_day": (origin + timedelta(weeks=periods) - timedelta(days=1)).isoformat()})
    return world, record
