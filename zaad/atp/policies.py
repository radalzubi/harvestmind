"""P5 incumbent policies: deterministic greedy allocators on the same supply state, priced by the
same economics, so the comparison with the optimiser is like for like. None of them reads a name.

FIFO_PROMISE            earliest requested period, then order period, then line id (today's settlement rule)
FCFS_ORDER_DATE         earliest order period, then requested period, then line id
TIER_PRIORITY           Customer.priority desc, then declared margin desc, then requested period, then id
PROPORTIONAL            lines requesting the same period share scarce supply pro-rata to quantity
CONTRACTUAL_THEN_PRIORITY  contractual floors first, then priority / margin groups pro-rata (zaad/allocation.py's rule)
DECLARED_MANUAL         the operator's own sequence of orders
"""
from __future__ import annotations

from typing import Any, Callable

from zaad.atp.allocation import Channel, channels
from zaad.atp.contracts import Atp
from zaad.atp.economics import Allocation, Shipment
from zaad.atp.state import SupplyState

POLICIES = ("FIFO_PROMISE", "FCFS_ORDER_DATE", "TIER_PRIORITY", "PROPORTIONAL", "CONTRACTUAL_THEN_PRIORITY", "DECLARED_MANUAL")


def _ordered_lines(req, atp: Atp, drv) -> list[tuple[Any, Any]]:
    spec = atp.spec
    lines = [(o, line) for o in spec.orders for line in o.lines]
    pol = spec.incumbent_policy
    key: Callable[[Any], tuple]
    if pol == "FIFO_PROMISE":
        key = lambda ol: (ol[1].requested_period, ol[0].order_period, ol[1].id)  # noqa: E731
    elif pol == "FCFS_ORDER_DATE":
        key = lambda ol: (ol[0].order_period, ol[1].requested_period, ol[1].id)  # noqa: E731
    elif pol == "TIER_PRIORITY":
        key = lambda ol: (-drv[ol[1].id].customer_priority, -drv[ol[1].id].lost_margin, ol[1].requested_period, ol[1].id)  # noqa: E731
    elif pol == "DECLARED_MANUAL":
        seq = {oid: i for i, oid in enumerate(spec.manual_sequence)}
        key = lambda ol: (seq[ol[0].id], ol[1].requested_period, ol[1].id)  # noqa: E731
    else:  # PROPORTIONAL and CONTRACTUAL_THEN_PRIORITY iterate in requested-period order and share inside groups
        key = lambda ol: (ol[1].requested_period, ol[0].order_period, ol[1].id)  # noqa: E731
    return sorted(lines, key=key)


def _take(alloc: Allocation, order, line, chans: list[Channel], remaining: dict[str, float], lane_left: dict[tuple, float], want: float) -> float:
    """Greedy fill of `want` units for one line: own SKU before substitutes, earliest promise period,
    then earliest-expiring lot (FEFO), then cheapest route. Returns the quantity shipped."""
    mine = [c for c in chans if c.line == line.id]
    lots_expiry = {c.lot: getattr(c, "expiry", 0) for c in mine}
    mine.sort(key=lambda c: (c.substitution is not None, c.promise_period, lots_expiry.get(c.lot, 0), c.lane_cost + c.sub_penalty, c.lot, c.lane or ""))
    got = 0.
    for c in mine:
        if want - got <= 1e-9:
            break
        room = remaining.get(c.lot, 0.) / c.ratio
        if c.lane is not None:
            room = min(room, lane_left.get((c.lane, c.promise_period - c.lead), 0.) / c.ratio)
        q = min(want - got, room)
        if q <= 1e-9:
            continue
        remaining[c.lot] -= q * c.ratio
        if c.lane is not None:
            lane_left[c.lane, c.promise_period - c.lead] -= q * c.ratio
        alloc.shipments.append(Shipment(order=order.id, line=line.id, customer=order.customer, service_class=order.service_class, sku_requested=line.sku,
                                        sku_supplied=c.sku_supplied, substitution=c.substitution, lot=c.lot, ship_from=c.ship_from, lane=c.lane,
                                        promise_period=c.promise_period, requested_period=line.requested_period, quantity=q, physical_units=q * c.ratio))
        got += q
    return got


def _fillable(line, order, chans, remaining, lane_left) -> float:
    """How much the line could receive right now under its rules (dry run)."""
    trial = Allocation(policy="trial")
    rem = dict(remaining)
    ll = dict(lane_left)
    return _take(trial, order, line, chans, rem, ll, line.quantity)


def _commit(alloc, order, line, chans, remaining, lane_left, want) -> None:
    """Apply the order's partial / minimum rules, then take."""
    can = _fillable(line, order, chans, remaining, lane_left)
    target = min(want, can)
    if not order.partial_fulfillment_allowed and target < line.quantity - 1e-9:
        target = 0.
    if line.minimum_ship_quantity > 0 and 0 < target < line.minimum_ship_quantity - 1e-9:
        target = 0.
    got = _take(alloc, order, line, chans, remaining, lane_left, target) if target > 0 else 0.
    short = line.quantity - got
    if short > 1e-7:
        (alloc.refused if order.late_semantics == "CANCEL_IF_LATE" else alloc.unmet)[line.id] = short


def incumbent(req, atp: Atp, state: SupplyState) -> Allocation:
    spec = atp.spec
    chans, drv, meta = channels(req, atp, state)
    # attach lot expiry for the FEFO tie inside _take
    expiry = {lot.id: lot.expiry for lot in state.lots}
    chans = [Channel(**{**c.__dict__}) for c in chans]
    for c in chans:
        object.__setattr__(c, "expiry", expiry[c.lot])  # noqa: B010  dataclass is frozen; the attribute is auxiliary
    remaining = {lot.id: lot.quantity for lot in state.lots}
    lane_left = {(lane.id, t): lane.capacity for lane in state.lanes for t in range(spec.promise_horizon + 1)}
    alloc = Allocation(policy=spec.incumbent_policy)
    ordered = _ordered_lines(req, atp, drv)
    if spec.incumbent_policy in ("PROPORTIONAL", "CONTRACTUAL_THEN_PRIORITY"):
        _shared(alloc, ordered, chans, drv, remaining, lane_left, atp)
    else:
        for order, line in ordered:
            _commit(alloc, order, line, chans, remaining, lane_left, line.quantity)
    for order, line in ordered:
        if line.id not in alloc.unmet and line.id not in alloc.refused:
            got = sum(s.quantity for s in alloc.shipments if s.line == line.id)
            if line.quantity - got > 1e-7:
                (alloc.refused if order.late_semantics == "CANCEL_IF_LATE" else alloc.unmet)[line.id] = line.quantity - got
    alloc.engine = {"channels": len(chans), "rule": spec.incumbent_policy}
    return alloc


def _shared(alloc, ordered, chans, drv, remaining, lane_left, atp: Atp) -> None:
    """Pro-rata sharing: groups of lines share what all of them together could take. For
    CONTRACTUAL_THEN_PRIORITY the first pass gives every class its floor share, the next passes go
    by (customer priority, margin) groups; for PROPORTIONAL one pass by requested period."""
    spec = atp.spec
    passes: dict[Any, list] = {}
    if spec.incumbent_policy == "CONTRACTUAL_THEN_PRIORITY":
        # floors first: each line receives floor x quantity (its class's floor), if it can
        for order, line in ordered:
            floor = drv[line.id].floor
            if floor > 0:
                _commit(alloc, order, line, chans, remaining, lane_left, floor * line.quantity)
                alloc.unmet.pop(line.id, None)
                alloc.refused.pop(line.id, None)
        for order, line in ordered:
            passes.setdefault((-drv[line.id].customer_priority, -drv[line.id].lost_margin), []).append((order, line))
        groups = [passes[k] for k in sorted(passes)]
    else:
        for order, line in ordered:
            passes.setdefault(line.requested_period, []).append((order, line))
        groups = [passes[k] for k in sorted(passes)]
    for group in groups:
        wants = {}
        for order, line in group:
            got = sum(s.quantity for s in alloc.shipments if s.line == line.id)
            wants[line.id] = max(0., line.quantity - got)
        # what the group could take together, then each member's pro-rata share of it
        trial = Allocation(policy="trial")
        rem = dict(remaining)
        ll = dict(lane_left)
        capacity = sum(_take(trial, order, line, chans, rem, ll, wants[line.id]) for order, line in group)
        total_want = sum(wants.values())
        share = min(1., capacity / total_want) if total_want > 1e-9 else 0.
        for order, line in group:
            _commit(alloc, order, line, chans, remaining, lane_left, wants[line.id] * share)
            got = sum(s.quantity for s in alloc.shipments if s.line == line.id)
            alloc.unmet.pop(line.id, None)
            alloc.refused.pop(line.id, None)
            if line.quantity - got > 1e-7:
                (alloc.refused if order.late_semantics == "CANCEL_IF_LATE" else alloc.unmet)[line.id] = line.quantity - got
