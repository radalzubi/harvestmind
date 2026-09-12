"""P5 exact allocation engine: a small MILP over ship / unmet / refused columns.

Isolated from `zaad/full/model.py` on purpose (parallel phase): it consumes the supply state and the
declared orders, and solves with scipy's bundled HiGHS. Columns: one per (line, channel, promise
period) where a channel is (lot, ship-from, lane or none, supplied SKU with its conversion). Rows:
line balance, lot conservation (cumulative by construction: a lot's quantity is shared by every
period), lane capacity per departure period, partial / minimum-ship binaries, contractual floors.
Objective: the shared ledger (economics.py) plus deterministic tie terms.
"""
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

from zaad.atp.contracts import Atp
from zaad.atp.economics import ALTERNATIVE, DIRECT, Allocation, Drivers, Shipment, drivers
from zaad.atp.state import SupplyState

TIE_PERIOD = 1e-6      # earlier promise wins among equal-cost channels
TIE_HOME = 5e-8        # then the service's own location among equal-cost direct channels
TIE_FEFO = 1e-8        # then the earlier-expiring cohort (the frozen model's fefo rule as a tie)
TIE_RANK = 1e-9        # then the documented line rank (order period, line id)
FLOOR_INFEASIBLE = "INFEASIBLE_CONTRACTUAL_FLOORS"


@dataclass(frozen=True)
class Channel:
    line: str
    order: str
    lot: str
    ship_from: str
    lane: str | None
    lead: int
    sku_supplied: str
    substitution: str | None
    ratio: float                 # physical units per requested unit
    sub_penalty: float           # per requested unit
    lane_cost: float             # per physical unit
    promise_period: int
    requested_period: int
    home: bool = True            # shipped from the service's own location


def channels(req, atp: Atp, state: SupplyState) -> tuple[list[Channel], dict[str, Drivers], dict[str, Any]]:
    """Every physically and contractually feasible (line, lot, location, lane, SKU, period)."""
    spec = atp.spec
    services = {(s.customer, s.sku): s for s in req.services}
    customers = {c.id: c for c in req.customers}
    out: list[Channel] = []
    drv: dict[str, Drivers] = {}
    meta: dict[str, Any] = {}
    for order in spec.orders:
        customer = customers[order.customer]
        for line in order.lines:
            drv[line.id] = drivers(req, atp, order, line)
            service = services[order.customer, line.sku]
            home = service.location
            eligible = set(line.ship_from) or {home}
            deadline = line.requested_period + (order.max_backorder_periods if order.backorder_allowed else 0)
            deadline = min(deadline, spec.promise_horizon)
            meta[line.id] = {"order": order.id, "home": home, "eligible": sorted(eligible), "deadline": deadline, "earliest": max(0, order.order_period)}
            # supplied SKUs: the line's own, plus approved substitutes when the order allows them
            supplied = [(line.sku, None, 1., 0.)]
            if order.substitution_allowed:
                for rule in req.substitutions:
                    if rule.approved and rule.requested_sku == line.sku and order.customer in rule.customers and customer.channel in rule.channels:
                        supplied.append((rule.supplied_sku, rule.id, rule.input_per_output / rule.service_equivalence, rule.penalty_per_output / rule.service_equivalence))
            for sku, sub, ratio, pen in supplied:
                for lot in state.lots:
                    if lot.sku != sku or lot.quantity <= 0:
                        continue
                    routes: list[tuple[str | None, int, float, str]] = []
                    if lot.location in eligible and state.location_ok(sku, lot.location):
                        routes.append((None, 0, 0., lot.location))
                    if spec.cross_location and lot.location not in eligible:
                        for lane in state.lanes:
                            if lane.sku == sku and lane.origin == lot.location and lane.destination in eligible and state.location_ok(sku, lane.destination):
                                routes.append((lane.id, lane.lead, lane.cost_per_unit, lane.destination))
                    for lane_id, lead, cost, dest in routes:
                        # a promise is a delivery period: never before the requested period (no unrequested early delivery), never after the deadline
                        for t in range(max(0, order.order_period, line.requested_period), deadline + 1):
                            depart = t - lead
                            if depart < lot.available_from or depart < 0:
                                continue
                            if not state.sellable(lot, depart) or not state.sellable(lot, t):
                                continue
                            out.append(Channel(line=line.id, order=order.id, lot=lot.id, ship_from=lot.location, lane=lane_id, lead=lead, sku_supplied=sku,
                                               substitution=sub, ratio=ratio, sub_penalty=pen, lane_cost=cost, promise_period=t, requested_period=line.requested_period,
                                               home=(dest == home and lane_id is None and lot.location == home)))
    return out, drv, meta


def solve(req, atp: Atp, state: SupplyState, seconds: float = 30.) -> Allocation:
    spec = atp.spec
    chans, drv, meta = channels(req, atp, state)
    lines = [(order, line) for order in spec.orders for line in order.lines]
    rank = {line.id: i for i, (_o, line) in enumerate(sorted(lines, key=lambda ol: (ol[0].order_period, ol[1].requested_period, ol[1].id)))}
    n_ch = len(chans)
    idx_unmet = {line.id: n_ch + i for i, (_o, line) in enumerate(lines)}
    n = n_ch + len(lines)
    idx_full: dict[str, int] = {}
    idx_min: dict[str, int] = {}
    for order, line in lines:
        if not order.partial_fulfillment_allowed:
            idx_full[line.id] = n
            n += 1
        if line.minimum_ship_quantity > 0 and order.partial_fulfillment_allowed:
            idx_min[line.id] = n
            n += 1
    cost = np.zeros(n)
    lower = np.zeros(n)
    upper = np.full(n, np.inf)
    integrality = np.zeros(n)
    refuses = {line.id: (order.late_semantics == "CANCEL_IF_LATE") for order, line in lines}
    expiry_rank = {lot.id: i for i, lot in enumerate(sorted(state.lots, key=lambda lot: (lot.expiry, lot.available_from, lot.id)))}
    for j, c in enumerate(chans):
        d = drv[c.line]
        late = max(0, c.promise_period - c.requested_period)
        cost[j] = (late * d.late_penalty + c.sub_penalty + c.lane_cost * c.ratio + TIE_PERIOD * c.promise_period + TIE_HOME * (0. if c.home else 1.)
                   + TIE_FEFO * expiry_rank[c.lot] / max(1, len(expiry_rank)) + TIE_RANK * rank[c.line])
        upper[j] = next(line.quantity for _o, line in lines if line.id == c.line)
    for order, line in lines:
        d = drv[line.id]
        j = idx_unmet[line.id]
        # a CANCEL_IF_LATE order's shortfall is a refusal (lost sale + declared refusal cost), an
        # ACCEPT_LATE order's shortfall is unmet (lost sale + SLA + declared shortage penalty)
        cost[j] = d.refused_cost if refuses[line.id] else d.unmet_cost
        upper[j] = line.quantity
    for j in list(idx_full.values()) + list(idx_min.values()):
        upper[j] = 1
        integrality[j] = 1
    rows: list[dict[int, float]] = []
    lo: list[float] = []
    hi: list[float] = []
    # line balance: shipped + unmet = quantity
    for order, line in lines:
        row = {j: 1. for j, c in enumerate(chans) if c.line == line.id}
        row[idx_unmet[line.id]] = 1.
        rows.append(row)
        lo.append(line.quantity)
        hi.append(line.quantity)
        if line.id in idx_full:
            # partial forbidden: shipped = quantity x full
            row = {j: 1. for j, c in enumerate(chans) if c.line == line.id}
            row[idx_full[line.id]] = -line.quantity
            rows.append(row)
            lo.append(0.)
            hi.append(0.)
        if line.id in idx_min:
            # minimum ship quantity: shipped in {0} U [minimum, quantity]
            row = {j: 1. for j, c in enumerate(chans) if c.line == line.id}
            row[idx_min[line.id]] = -line.minimum_ship_quantity
            rows.append(dict(row))
            lo.append(0.)
            hi.append(np.inf)
            row2 = {j: 1. for j, c in enumerate(chans) if c.line == line.id}
            row2[idx_min[line.id]] = -line.quantity
            rows.append(row2)
            lo.append(-np.inf)
            hi.append(0.)
    # lot conservation: physical units drawn <= lot quantity (a lot is one dated pool)
    for lot in state.lots:
        row = {j: c.ratio for j, c in enumerate(chans) if c.lot == lot.id}
        if row:
            rows.append(row)
            lo.append(-np.inf)
            hi.append(lot.quantity)
    # lane capacity per departure period
    for lane in state.lanes:
        for t in range(spec.promise_horizon + 1):
            row = {j: c.ratio for j, c in enumerate(chans) if c.lane == lane.id and c.promise_period - c.lead == t}
            if row:
                rows.append(row)
                lo.append(-np.inf)
                hi.append(lane.capacity)
    # contractual floors per class: shipped over the class >= floor x requested over the class
    for cls in spec.service_classes:
        if cls.contractual_service_floor <= 0:
            continue
        members = [line for order, line in lines if order.service_class == cls.id]
        if not members:
            continue
        total = sum(line.quantity for line in members)
        row = {j: 1. for j, c in enumerate(chans) if c.line in {line.id for line in members}}
        rows.append(row)
        lo.append(cls.contractual_service_floor * total - 1e-9)
        hi.append(np.inf)
    rr, cc, vv = [], [], []
    for r, terms in enumerate(rows):
        for c_, v in terms.items():
            rr.append(r)
            cc.append(c_)
            vv.append(v)
    matrix = coo_matrix((vv, (rr, cc)), shape=(len(rows), n)).tocsc()
    t0 = time.perf_counter()
    res = milp(cost, integrality=integrality, bounds=Bounds(lower, upper), constraints=LinearConstraint(matrix, lo, hi),
               options={"time_limit": seconds, "mip_rel_gap": 1e-9})
    dt = time.perf_counter() - t0
    alloc = Allocation(policy="optimised", solve_seconds=round(dt, 4),
                       engine={"columns": int(n), "channels": int(n_ch), "rows": len(rows), "binaries": int(integrality.sum()), "status": int(res.status), "message": str(res.message)[:80]})
    if res.x is None:
        alloc.status = FLOOR_INFEASIBLE if any(c.contractual_service_floor > 0 for c in spec.service_classes) else "INFEASIBLE"
        alloc.notes.append("no feasible allocation: a declared contractual floor or rule cannot be met from the available supply; no recommendation")
        return alloc
    alloc.status = "OPTIMAL" if res.status == 0 else ("FEASIBLE_TIME_LIMIT" if res.status == 1 else "ERROR")
    x = res.x
    for j, c in enumerate(chans):
        q = float(x[j])
        if q > 1e-7:
            alloc.shipments.append(Shipment(order=c.order, line=c.line, customer=next(o.customer for o in spec.orders if o.id == c.order),
                                            service_class=next(o.service_class for o in spec.orders if o.id == c.order), sku_requested=next(line.sku for _o, line in lines if line.id == c.line),
                                            sku_supplied=c.sku_supplied, substitution=c.substitution, lot=c.lot, ship_from=c.ship_from, lane=c.lane,
                                            promise_period=c.promise_period, requested_period=c.requested_period, quantity=q, physical_units=q * c.ratio,
                                            fulfilment=ALTERNATIVE if c.lane is not None else DIRECT))
    for order, line in lines:
        short = float(x[idx_unmet[line.id]])
        if short > 1e-7:
            (alloc.refused if refuses[line.id] else alloc.unmet)[line.id] = short
    alloc.engine["objective"] = float(res.fun)
    alloc.engine["mip_gap"] = float(getattr(res, "mip_gap", 0.) or 0.)
    return alloc


def apply_fairness(alloc: Allocation, req, atp: Atp, state: SupplyState) -> Allocation:
    """The declared fairness rule applied to a recommendation (optimised or incumbent): a tie rule
    among economically indifferent lines, never a redistribution for value (the ledger is unchanged)."""
    if atp.spec.fairness != "PROPORTIONAL_WHEN_INDIFFERENT":
        return alloc
    _chans, drv, meta = channels(req, atp, state)
    lines = [(order, line) for order in atp.spec.orders for line in order.lines]
    proportional_redistribution(alloc, lines, drv, meta)
    return alloc


def proportional_redistribution(alloc: Allocation, lines, drv, meta) -> None:
    """Among lines that are economically indifferent (same drivers, requested period, SKU, eligible
    locations, order period and rules) redistribute the group's shipments pro-rata to quantity. Unit
    costs are identical inside a group, so the ledger total is unchanged (documented fairness rule)."""
    groups: dict[tuple, list] = {}
    for order, line in lines:
        d = drv[line.id]
        # economic indifference is a property of the declared NUMBERS (never of a class id, name or tier)
        key = (d.lost_margin, d.sla, d.shortage_penalty, d.late_penalty, d.refusal_cost, d.floor, line.sku, line.requested_period, order.order_period, tuple(meta[line.id]["eligible"]),
               order.partial_fulfillment_allowed, order.backorder_allowed, order.max_backorder_periods, order.late_semantics, order.substitution_allowed, line.minimum_ship_quantity)
        groups.setdefault(key, []).append((order, line))
    for key, members in groups.items():
        if len(members) < 2 or any(not o.partial_fulfillment_allowed or line.minimum_ship_quantity > 0 for o, line in members):
            continue
        ids = {line.id for _o, line in members}
        ships = [s for s in alloc.shipments if s.line in ids]
        if not ships:
            continue
        total_q = sum(line.quantity for _o, line in members)
        # pool every (lot, location, lane, sku, period) shipment of the group and re-split by quantity share
        pooled: dict[tuple, float] = {}
        template: dict[tuple, Shipment] = {}
        for s in ships:
            k = (s.lot, s.ship_from, s.lane, s.sku_supplied, s.substitution, s.promise_period)
            pooled[k] = pooled.get(k, 0.) + s.quantity
            template[k] = s
        alloc.shipments = [s for s in alloc.shipments if s.line not in ids]
        shipped_total = sum(pooled.values())
        for order, line in members:
            share = line.quantity / total_q
            got = 0.
            for k, q in pooled.items():
                t = template[k]
                part = q * share
                if part > 1e-9:
                    alloc.shipments.append(Shipment(order=order.id, line=line.id, customer=order.customer, service_class=order.service_class, sku_requested=line.sku,
                                                    sku_supplied=t.sku_supplied, substitution=t.substitution, lot=t.lot, ship_from=t.ship_from, lane=t.lane,
                                                    promise_period=t.promise_period, requested_period=line.requested_period, quantity=part, physical_units=part * (t.physical_units / t.quantity),
                                                    fulfilment=t.fulfilment))
                    got += part
            short = line.quantity - got
            target = alloc.refused if order.late_semantics == "CANCEL_IF_LATE" else alloc.unmet
            target.pop(line.id, None)
            if short > 1e-7:
                target[line.id] = short
        alloc.notes.append(f"proportional redistribution among {len(members)} economically indifferent lines ({shipped_total:.1f} units shared pro-rata to quantity; ledger unchanged)")


def blocked_supply(req, atp: Atp, state: SupplyState) -> list[dict[str, Any]]:
    """Supply of a requested SKU that P5 knows about but may not draw on for a line, with the structural
    reason: an ineligible location without an approved eligible lane (an implicit transfer is never
    created), a lane the SKU's storage state may not use, a location the state may not occupy, or a
    non-firm open purchase order. Reporting only; nothing here changes the allocation."""
    spec = atp.spec
    services = {(s.customer, s.sku): s for s in req.services}
    out: list[dict[str, Any]] = []
    approved = {a.id: a for a in req.transfers if a.approved}
    for order in spec.orders:
        for line in order.lines:
            eligible = set(line.ship_from) or {services[order.customer, line.sku].location}
            for lot in state.lots:
                if lot.sku != line.sku or lot.quantity <= 0 or lot.location in eligible:
                    continue
                lanes = {a.id for a in approved.values() if a.sku == lot.sku and a.origin == lot.location and a.destination in eligible}
                usable_lanes = [ln for ln in state.lanes if ln.id in lanes and state.location_ok(lot.sku, ln.destination)]   # state.lanes already passed lane_ok
                if not spec.cross_location:
                    reason = "location not eligible for the line and cross_location is off: no implicit transfer is created"
                elif not lanes:
                    reason = "location not eligible for the line and no approved lane reaches an eligible location: no implicit transfer is created"
                elif not usable_lanes:
                    reason = "the approved lane or its destination is not eligible for the SKU's storage state (sector physics)"
                else:
                    continue   # reachable through an eligible lane: priced as ALTERNATIVE_SHIP_FROM, not blocked
                out.append({"line": line.id, "lot": lot.id, "sku": lot.sku, "location": lot.location, "quantity": round(lot.quantity, 3), "reason": reason})
            for loc in eligible:
                if not state.location_ok(line.sku, loc):
                    out.append({"line": line.id, "lot": None, "sku": line.sku, "location": loc, "quantity": 0., "reason": "eligible location cannot hold the SKU's storage state (sector physics)"})
    for n in state.non_firm:
        out.append({"line": None, "lot": n.id, "sku": n.sku, "location": n.location, "quantity": round(n.quantity, 3), "reason": n.reason, "expected_period": n.expected_period})
    return out
