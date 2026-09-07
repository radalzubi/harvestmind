"""Capital decomposition (v7): where every unit of inventory comes from, and which of it is
justified by a physical or service obligation.

V6 placed inventory better but did not make the network leaner. This module is the diagnosis
before the engine change: for every SKU and location at a review it partitions the units on hand
into named reasons that sum exactly to the total, names the owner of each unit (inherited from the
opening position, purchased by the plan, or transferred in), and quantifies three specific
suspicions - a buffer held twice for the same risk, stock parked at a branch a fast arc could
serve from the origin, and stock bought before it was needed.

Two partitions of the same units are reported:

  reason   a waterfall over named obligations, most defensible first, so the residual is the
           part with no operational reason left to give it
  owner    inherited / purchased / transferred, tracked by the caller through the replay

The waterfall order is deliberate. Cycle stock turns over inside one review and is never
questioned; local service stock at a transfer-fed branch is demand that must be on the shelf
before any transfer could arrive; source protection is the declared lead and fill spread of the
cheapest usable source; pooled stock at an origin covers the branches it feeds; active protection
is the increment a live risk driver justifies. What is left over after those has no live reason:
pack rounding, an order that arrived early, positioning beyond a branch's own need, or protection
whose driver has already expired.

Periods of demand are reported only where they mean something. On intermittent demand the mean is
a poor divisor - a location with 0.4 units of mean demand and one pack on hand reads as fifty
periods of cover and tells nobody anything - so `periods_meaningful` is false there and the units
are the number to read.
"""
from __future__ import annotations

import math

from zaad.full.contracts import Request
from zaad.full.uncertainty import z_for
from zaad.full.worlds import dates

# Reason categories in waterfall order. Every unit on hand is assigned to exactly one.
REASONS = ("demand_cycle", "local_service", "source_lead", "pooled_network", "active_protection",
           "moq_pack", "early_order", "transfer_positioning", "stale_protection",
           "inherited_excess", "unexplained")


def _feeders(req: Request, sku: str, location: str) -> list:
    return [a for a in req.transfers if a.approved and a.sku == sku and a.destination == location]


def _fed_branches(req: Request, sku: str, origin: str) -> list[str]:
    direct = {(s.sku, s.destination) for s in req.sources if s.approved and s.compliance == "cleared"}
    return sorted({a.destination for a in req.transfers
                   if a.approved and a.sku == sku and a.origin == origin and (sku, a.destination) not in direct})


def _cheapest_source(req: Request, sku: str, location: str):
    eligible = sorted((s for s in req.sources if s.sku == sku and s.destination == location
                       and s.approved and s.compliance == "cleared"),
                      key=lambda s: (s.unit_price + s.freight_per_unit + s.handling_per_unit, s.id))
    return eligible[0] if eligible else None


def decompose(req: Request, fits: dict, protection: list[dict], *,
              inherited: dict[tuple[str, str], float] | None = None,
              transferred: dict[tuple[str, str], float] | None = None,
              early_units: dict[tuple[str, str], float] | None = None) -> list[dict]:
    """One row per SKU/location on hand at this review. `inherited`, `transferred` and
    `early_units` come from the replay, which is the only place that knows the provenance of a
    lot; absent them the owner split degrades to purchased-or-inherited unknown and the early
    -order reason is skipped, and the reason waterfall is unaffected."""
    by_pair = {(row["sku"], row["location"]): row for row in protection}
    if inherited is not None and inherited and isinstance(next(iter(inherited)), str):
        inherited = {tuple(k.split("|", 1)): v for k, v in inherited.items()}   # request carries string keys
    rows: list[dict] = []
    pairs = sorted({(lot.sku, lot.location) for lot in req.stock}
                   | {(s.sku, s.location) for s in req.services}
                   | {(s.sku, s.destination) for s in req.sources}
                   | {(a.sku, a.origin) for a in req.transfers} | {(a.sku, a.destination) for a in req.transfers})
    for sku, location in pairs:
        on_hand = sum(lot.usable for lot in req.stock if lot.sku == sku and lot.location == location)
        services = [s for s in req.services if s.sku == sku and s.location == location]
        mu = sum(fits[s.id]["mean"] for s in services)
        sd = math.sqrt(sum(fits[s.id]["sd"] ** 2 for s in services))
        state = by_pair.get((sku, location))
        intermittent = any((fits[s.id].get("uncertainty") or {}).get("intermittent") for s in services)
        z = state["quantile_z"] if state else (z_for(max((s.target for s in services), default=.95)) if services else 0.)
        feeders = _feeders(req, sku, location)
        transfer_lead = min((a.lead_periods for a in feeders), default=None)
        source = _cheapest_source(req, sku, location)
        window = (dates(req, source, 0)[1] + 1) if source is not None else max(1, (transfer_lead or 0) + 1)
        # Named obligations, each the units that obligation alone would justify.
        #
        # The protection terms are taken from the engine's own echelon partition rather than
        # recomputed here. Recomputing them from the fitted standard deviation was a defect: on
        # intermittent demand the engine sizes protection from the occurrence/size decomposition,
        # which is far wider than the raw fitted sd, so the decomposition under-claimed and dumped
        # the difference into `unexplained` (cell 35 branch: 45.6 claimed against 109.9 on hand).
        cycle = mu * max(1., window)
        echelon = (state["state"].get("echelon") or {}) if state else {}
        if echelon:
            local = float(echelon.get("local_service_units") or 0.)
            pooled_claim = float(echelon.get("pooled_network_units") or 0.)
            source_lead = float(echelon.get("source_protection_units") or 0.)
        elif transfer_lead is not None and source is None:
            local, pooled_claim, source_lead = z * sd * math.sqrt(transfer_lead + 1), 0., 0.
        else:
            declared_lead_sd = (source.lead_sd_days / req.period_days) if source is not None else 0.
            declared_fill_sd = source.fill_sd if source is not None else 0.
            demand_var = window * sd ** 2
            supply_var = (mu * declared_lead_sd) ** 2 + (mu * window * declared_fill_sd) ** 2
            local = z * math.sqrt(demand_var)
            pooled_claim = 0.
            source_lead = z * (math.sqrt(demand_var + supply_var) - math.sqrt(demand_var))
        pooled = pooled_claim
        fed = _fed_branches(req, sku, location)
        if fed:
            branch_mu = 0.
            branch_var = 0.
            for branch in fed:
                bs = [s for s in req.services if s.sku == sku and s.location == branch]
                branch_mu += sum(fits[s.id]["mean"] for s in bs)
                branch_var += sum(fits[s.id]["sd"] ** 2 for s in bs)
            arcs = [a for a in req.transfers if a.approved and a.sku == sku and a.origin == location and a.destination in fed]
            arc_lead = min((a.lead_periods for a in arcs), default=1)
            # Pooled cover for the branches this origin feeds: their demand over the origin's own
            # replenishment window, with the safety term pooled (root of the summed variances).
            pooled = max(pooled, branch_mu * window + z * math.sqrt(branch_var * max(1, window - arc_lead)))
        active = max(0., state["state"]["incremental_protection_units"]) if state and state["state"]["activity"] > .05 else 0.
        pack = 0.
        if source is not None:
            increment = max(source.multiple, source.case_multiple, source.pallet_multiple, source.transport_multiple)
            pack = increment / 2. if increment > 0 else 0.
        early = (early_units or {}).get((sku, location), 0.)
        positioning = 0.
        if transfer_lead is not None and source is None:
            positioning = max(0., (transferred or {}).get((sku, location), 0.))
        stale = max(0., state["state"]["incremental_protection_units"]) if state and state["state"]["activity"] <= .05 else 0.
        # Inherited excess (v8): units that came from the opening position and are still on hand
        # after every operating obligation is met. The optimizer did not create them; naming them
        # separately is the difference between "ZAAD is holding too much" and "ZAAD started with
        # too much and is working it down".
        inherited_here = (inherited or {}).get((sku, location))
        claims = {"demand_cycle": cycle, "local_service": local, "source_lead": source_lead,
                  "pooled_network": pooled, "active_protection": active, "moq_pack": pack,
                  "early_order": early, "transfer_positioning": positioning, "stale_protection": stale,
                  "inherited_excess": (min(on_hand, inherited_here) if inherited_here is not None else 0.)}
        # Waterfall: each reason takes what is left, in order, so the parts sum to the total exactly.
        remaining = on_hand
        reason: dict[str, float] = {}
        for name in REASONS[:-1]:
            take = min(remaining, max(0., claims.get(name, 0.)))
            reason[name] = take
            remaining -= take
        reason["unexplained"] = max(0., remaining)
        inherited_units = min(on_hand, (inherited or {}).get((sku, location), 0.)) if inherited is not None else None
        rows.append({
            "sku": sku, "location": location, "on_hand_units": on_hand,
            "mean_demand_per_period": mu, "periods_meaningful": bool(mu > 0 and not intermittent),
            "periods_of_demand": (on_hand / mu) if mu > 0 and not intermittent else None,
            "reason": reason,
            "reason_periods": {k: (v / mu if mu > 0 and not intermittent else None) for k, v in reason.items()},
            "owner": ({"inherited": inherited_units, "purchased_or_transferred": on_hand - inherited_units}
                      if inherited_units is not None else None),
            "risk_source": (state["state"]["exit"]["active_risk_source"] if state else None),
            "incremental_vs_lean": (max(0., on_hand - state["state"]["lean_baseline_units"]) if state else None),
            "justified_units": on_hand - reason["unexplained"] - reason["stale_protection"] - reason["early_order"] - reason["transfer_positioning"],
            "reconciles": abs(sum(reason.values()) - on_hand) < 1e-6})
    return rows


def duplication(req: Request, fits: dict, protection: list[dict]) -> list[dict]:
    """Explicit duplicated-buffer detection (v7). A pair of buffers duplicates when both cover the
    same risk source over the same interval for the same service obligation, sit at different
    echelons, and the upstream one can physically reach the downstream one inside the window it
    would have to cover. The overlap is the smaller of the two surpluses above their own needs;
    it is reported with the pair that produced it, never silently netted off a target."""
    by_pair = {(row["sku"], row["location"]): row for row in protection}
    out: list[dict] = []
    for (sku, branch), row in sorted(by_pair.items()):
        feeders = _feeders(req, sku, branch)
        if not feeders or _cheapest_source(req, sku, branch) is not None:
            continue                       # a branch that buys directly is not fed, so nothing is pooled for it
        services = [s for s in req.services if s.sku == sku and s.location == branch]
        if not services:
            continue
        mu = sum(fits[s.id]["mean"] for s in services)
        sd = math.sqrt(sum(fits[s.id]["sd"] ** 2 for s in services))
        z = row["quantile_z"]
        for arc in sorted(feeders, key=lambda a: (a.lead_periods, -a.capacity, a.id)):
            origin_row = by_pair.get((sku, arc.origin))
            origin_stock = sum(lot.usable for lot in req.stock if lot.sku == sku and lot.location == arc.origin)
            branch_stock = row["on_hand_units"]
            # Interval: what the branch must cover on its own is demand until a transfer ordered
            # now could arrive. Beyond that the origin can serve the same obligation.
            local_need = mu * arc.lead_periods + z * sd * math.sqrt(arc.lead_periods + 1)
            # The origin's own need is its own demand plus the pooled cover for every branch it feeds.
            fed = _fed_branches(req, sku, arc.origin)
            origin_services = [s for s in req.services if s.sku == sku and s.location == arc.origin]
            origin_mu = sum(fits[s.id]["mean"] for s in origin_services)
            pooled_mu, pooled_var = 0., 0.
            for other in fed:
                bs = [s for s in req.services if s.sku == sku and s.location == other]
                pooled_mu += sum(fits[s.id]["mean"] for s in bs)
                pooled_var += sum(fits[s.id]["sd"] ** 2 for s in bs)
            source = _cheapest_source(req, sku, arc.origin)
            window = (dates(req, source, 0)[1] + 1) if source is not None else 1
            origin_need = (origin_mu + pooled_mu) * window + z * math.sqrt(pooled_var * window)
            # Reachable: the arc must both carry a period of demand and land inside the interval
            # the branch's own stock is there to cover. An arc slower than that cannot stand in for
            # branch stock at all, however much the origin happens to be holding.
            reachable = arc.capacity >= mu and arc.lead_periods <= max(1, window - 1)
            # Both surpluses must exist, and the arc must be able to carry the overlap inside the
            # interval the branch stock would otherwise cover.
            branch_surplus = max(0., branch_stock - local_need)
            origin_surplus = max(0., origin_stock - origin_need)
            carriable = arc.capacity * max(0, window - arc.lead_periods)
            overlap = min(branch_surplus, origin_surplus, carriable) if reachable else 0.
            risk_branch = (row["state"]["exit"]["active_risk_source"] or "demand_spread")
            risk_origin = ((origin_row["state"]["exit"]["active_risk_source"] if origin_row else None) or "demand_spread")
            same_risk = risk_branch == risk_origin
            out.append({
                "sku": sku, "branch": branch, "origin": arc.origin, "arc": arc.id,
                "transfer_lead_periods": arc.lead_periods, "arc_capacity": arc.capacity,
                "branch_stock_units": branch_stock, "branch_local_need_units": local_need,
                "origin_stock_units": origin_stock, "origin_need_units": origin_need,
                "risk_source_branch": risk_branch, "risk_source_origin": risk_origin,
                "same_risk_source": same_risk, "arc_reachable_inside_window": bool(reachable),
                "duplicated_buffer_units": overlap if same_risk else 0.,
                "explanation": (
                    f"{overlap:.0f} units cover the same {risk_branch} exposure twice: {branch} holds {branch_stock:.0f} "
                    f"against a local need of {local_need:.0f} it must serve before a transfer could land, while {arc.origin} "
                    f"holds {origin_stock:.0f} against a pooled need of {origin_need:.0f}; arc {arc.id} carries "
                    f"{arc.capacity:.0f} per review at a lead of {arc.lead_periods}"
                    if overlap > 0 and same_risk else
                    f"no duplication: {'different risk sources' if not same_risk else 'no surplus at both echelons' if min(branch_surplus, origin_surplus) <= 0 else 'the arc cannot carry the overlap in time'}")})
    return out


def pooling_split(req: Request, fits: dict, protection: list[dict]) -> list[dict]:
    """Fast-arc pooling (v7). For every transfer-fed branch, the demand that must be met before a
    transfer ordered now could arrive (local immediate stock) and the demand that a shared origin
    can still serve in time (pooled stock), computed period by period rather than as one static
    credit, so a same-review arc leaves almost nothing local and a three-review arc leaves nearly
    everything local."""
    by_pair = {(row["sku"], row["location"]): row for row in protection}
    out: list[dict] = []
    for (sku, branch), row in sorted(by_pair.items()):
        feeders = _feeders(req, sku, branch)
        if not feeders or _cheapest_source(req, sku, branch) is not None:
            continue
        arc = min(feeders, key=lambda a: (a.lead_periods, -a.capacity, a.id))
        services = [s for s in req.services if s.sku == sku and s.location == branch]
        mu = sum(fits[s.id]["mean"] for s in services)
        sd = math.sqrt(sum(fits[s.id]["sd"] ** 2 for s in services))
        z = row["quantile_z"]
        source = _cheapest_source(req, sku, arc.origin)
        window = (dates(req, source, 0)[1] + 1) if source is not None else arc.lead_periods + 1
        # Period by period over the origin's replenishment window: demand in periods before a
        # transfer ordered this review can land must be local; later demand can be pooled, but only
        # as fast as the arc can move it.
        local_units, pooled_units, per_period = 0., 0., []
        for t in range(max(1, window)):
            demand_t = mu
            spread_t = z * sd
            if t < arc.lead_periods:
                local_units += demand_t + spread_t / math.sqrt(max(1, arc.lead_periods))
                per_period.append({"period": t, "servable_from": "branch_only", "units": demand_t})
            else:
                deliverable = min(demand_t, arc.capacity)
                pooled_units += deliverable
                local_units += max(0., demand_t - deliverable)
                per_period.append({"period": t, "servable_from": "origin" if deliverable >= demand_t else "both",
                                   "units": demand_t, "arc_limited_units": max(0., demand_t - deliverable)})
        out.append({"sku": sku, "branch": branch, "origin": arc.origin, "arc": arc.id,
                    "transfer_lead_periods": arc.lead_periods, "arc_capacity": arc.capacity,
                    "window_periods": max(1, window),
                    "local_immediate_units": local_units, "pooled_units": pooled_units,
                    "on_hand_units": row["on_hand_units"],
                    "excess_over_local_immediate": max(0., row["on_hand_units"] - local_units),
                    "per_period": per_period})
    return out
