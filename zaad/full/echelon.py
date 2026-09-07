"""Echelon base-stock comparator (v6).

An independent MEIO-style policy against which ZAAD's network logic is tested. It is not ZAAD:
it uses the fitted demand mean and spread only (no calibration, no risk state, no stress), the
declared supplier lead, and the classic two-level echelon base-stock rule:

- every branch fed only by transfer holds a *local* base stock covering demand over the transfer
  lead plus one review at its own service quantile;
- the central location (or any location that buys directly) holds an *echelon* base stock over
  supplier lead + review + downstream transfer lead for all demand it serves, with the safety
  term pooled as the root of the summed branch variances;
- transfers refill each branch to its local base stock, capped by arc capacity and by what the
  origin physically holds; purchases refill the echelon position (own stock + branch stock +
  pipeline + transfers in flight).

The policy is projected deterministically over the horizon, exactly as the projected base-stock
proxy is, and executed through the common model as purchase targets per source-period and
transfer targets per arc-period.
"""
from __future__ import annotations

import math

from zaad.full.contracts import Request, Transfer
from zaad.full.uncertainty import z_for
from zaad.full.worlds import dates, forecast_all


def echelon_targets(req: Request) -> dict:
    fits = forecast_all(req)
    direct = {(s.sku, s.destination) for s in req.sources if s.approved and s.compliance == "cleared"}
    feeders: dict[tuple[str, str], Transfer] = {}
    for arc in sorted(req.transfers, key=lambda a: (a.lead_periods, -a.capacity, a.id)):
        if arc.approved and (arc.sku, arc.destination) not in direct and (arc.sku, arc.origin) in direct:
            feeders.setdefault((arc.sku, arc.destination), arc)
    fed_by: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for (sku, dest), arc in feeders.items():
        fed_by.setdefault((sku, arc.origin), []).append((sku, dest))
    stock = {(s.id, location.id): sum(x.usable for x in req.stock if x.sku == s.id and x.location == location.id)
             for s in req.skus for location in req.locations}
    sources = {s.id: s for s in req.sources}
    pending: list[tuple[str, str, int, float]] = []          # (sku, location, due period, units)
    for po in req.pipeline:
        source = sources[po.source]
        pending.append((source.sku, source.destination, next(o.due_in for o in po.options if o.action == "keep"), po.expected_accepted_remaining))
    for row in req.inbound_transfers:
        pending.append((row.sku, row.destination, row.due_in, row.accepted_quantity))
    own = {(s.sku, s.location): [s for s in req.services if s.sku == s.sku and s.location == s.location] for s in req.services}
    own = {(sku, loc): [s for s in req.services if s.sku == sku and s.location == loc] for (sku, loc) in own}

    def demand(services):
        mu = sum(fits[s.id]["mean"] for s in services)
        var = sum(fits[s.id]["sd"] ** 2 for s in services)
        z = z_for(max((s.target for s in services), default=.95))
        return mu, var, z

    targets: dict = {}
    for t in range(req.horizon):
        for (sku, location) in stock:
            stock[sku, location] += sum(q for k, loc, due, q in pending if k == sku and loc == location and due == t)
        # Branch transfers: refill each fed branch to its local base stock from what the origin holds now.
        for (sku, dest), arc in feeders.items():
            mu, var, z = demand(own.get((sku, dest), []))
            window = arc.lead_periods + 1
            local_base = mu * window + z * math.sqrt(var * window)
            in_flight = sum(q for k, loc, due, q in pending if k == sku and loc == dest and due > t)
            need = max(0., local_base - stock[sku, dest] - in_flight)
            q = max(0., min(need, arc.capacity, stock[sku, arc.origin]))
            targets["transfer", arc.id, t] = q
            stock[sku, arc.origin] -= q
            pending.append((sku, dest, t + arc.lead_periods, q * (1 - arc.loss_fraction)))
        # Purchases: refill the echelon position of every buying location.
        for (sku, location) in direct:
            downstream = fed_by.get((sku, location), [])
            services = own.get((sku, location), []) + [s for pair in downstream for s in own.get(pair, [])]
            mu, var, z = demand(services)
            tail = max((feeders[pair].lead_periods for pair in downstream), default=0)
            eligible = sorted((s for s in req.sources if s.sku == sku and s.destination == location and s.approved and s.compliance == "cleared"),
                              key=lambda s: (s.unit_price + s.freight_per_unit + s.handling_per_unit, s.id))
            for source in eligible:
                lead = dates(req, source, t)[1] - t
                window = lead + 1 + tail
                echelon_base = mu * window + z * math.sqrt(var * window)
                position = stock[sku, location] + sum(stock[pair] for pair in downstream)
                position += sum(q for k, loc, due, q in pending if k == sku and (loc == location or (k, loc) in downstream) and due > t)
                q = max(0., echelon_base - position) / max(source.fill_mean, 1e-6)
                q = min(source.capacity_by_period[t], source.maximum, q)
                targets[source.id, t] = q
                pending.append((sku, location, t + lead, q * source.fill_mean))
        for (sku, location) in stock:
            mu = sum(fits[s.id]["mean"] for s in own.get((sku, location), []))
            stock[sku, location] = max(0., stock[sku, location] - mu)
    for source in req.sources:
        for t in range(req.horizon):
            targets.setdefault((source.id, t), 0.)
    for arc in feeders.values():
        for t in range(req.horizon):
            targets.setdefault(("transfer", arc.id, t), 0.)
    return targets
