"""Competent baseline purchasing policies (P1), projected over the horizon on the fitted mean demand.

These are the comparators ZAAD P1 is measured against and the declared operator rules it can be
asked to improve on. Each respects the supplier's lot rules (minimum, multiples, minimum order
value) so that it is a policy a buyer could actually execute, not a straw man that fails
settlement. None of them sees the truth; they see the same review snapshot the optimizer sees."""
from __future__ import annotations

import math
from datetime import datetime, timezone

from zaad.full.contracts import Request
from zaad.full.economics import round_up
from zaad.full.model import Solution, supplier_orders
from zaad.full.worlds import dates, forecast_all

EPOCH = datetime(2000, 1, 3, tzinfo=timezone.utc)   # a Monday; periodic cadences count from here
Z_SERVICE = {.90: 1.282, .95: 1.645, .98: 2.054, .99: 2.326}


def _z(target: float) -> float:
    return min(Z_SERVICE.items(), key=lambda kv: abs(kv[0] - target))[1] if target > 0 else 0.


def review_index(req: Request) -> int:
    return (req.as_of - EPOCH).days // req.period_days


def lot_round(source, q: float) -> float:
    if q <= 0:
        return 0.
    q = max(q, source.minimum)
    for m in (source.multiple, source.case_multiple, source.pallet_multiple, source.transport_multiple):
        q = round_up(q, m)
    return min(q, source.maximum)


def apply_mov(req: Request, purchases: dict[tuple[str, int], float]) -> None:
    """Lift each supplier order to its minimum order value, adding units to the cheapest-to-hold
    line (lowest unit price), lot-rounded. A buyer facing an MOV does exactly this."""
    terms = {x.id: x for x in req.terms}
    for supplier, srcs, st in supplier_orders(req):
        if st.minimum_order_value <= 0:
            continue
        for t in range(req.horizon):
            lines = [s for s in srcs if purchases.get((s.id, t), 0.) > 0]
            if not lines:
                continue
            value = sum(purchases[s.id, t] * s.unit_price * terms[s.terms].fx_rate_to_currency for s in lines)
            if value >= st.minimum_order_value - 1e-9:
                continue
            line = min(lines, key=lambda s: s.unit_price)
            price = line.unit_price * terms[line.terms].fx_rate_to_currency
            extra = (st.minimum_order_value - value) / price
            purchases[line.id, t] = lot_round(line, purchases[line.id, t] + extra)


def apply_load_cap(req: Request, purchases: dict[tuple[str, int], float]) -> None:
    """Cap each supplier order at the supplier's maximum load (a full truck), scaling the lines
    down proportionally and lot-rounding down. A buyer facing an FTL cap orders a full load and
    reorders sooner; the reorder rules above pick that up on the next period."""
    from zaad.full.model import pallet_units
    for supplier, srcs, st in supplier_orders(req):
        top = st.max_pallets if st.max_pallets is not None else (st.freight_tiers[-1].up_to_pallets if st.freight_tiers else None)
        upp = pallet_units(st, srcs)
        if top is None or upp is None:
            continue
        for t in range(req.horizon):
            lines = [s for s in srcs if purchases.get((s.id, t), 0.) > 0]
            load = sum(purchases[s.id, t] / upp[s.id] for s in lines)
            if load <= top + 1e-9:
                continue
            scale = top / load
            for s in lines:
                q = purchases[s.id, t] * scale
                pack = max(s.multiple, s.case_multiple, s.pallet_multiple, s.transport_multiple)
                if pack > 0:
                    q = math.floor(q / pack + 1e-9) * pack
                purchases[s.id, t] = max(q, s.minimum) if q > 0 else 0.
            if sum(purchases[s.id, t] / upp[s.id] for s in lines) > top + 1e-9:
                # the minimum alone breaks the cap: drop the smallest line rather than ship an illegal load
                smallest = min(lines, key=lambda s: purchases[s.id, t] * s.unit_price)
                purchases[smallest.id, t] = 0.


def apply_cash_cap(req: Request, purchases: dict[tuple[str, int], float]) -> None:
    """Keep each period's cumulative purchase value inside the cash the request declares: opening
    cash plus dated receivables less other payments to date, plus the credit limit. A buyer who
    cannot pay for a full lot orders what can be paid for and reorders when cash allows."""
    terms = {x.id: x for x in req.terms}
    sources = {s.id: s for s in req.sources}
    available = req.liquidity.opening_cash - req.liquidity.opening_debt + req.liquidity.credit_limit - req.liquidity.minimum_cash
    for t in range(req.horizon):
        available += req.liquidity.known_receivables[t] - req.liquidity.other_payments[t]
        lines = [(sid, q) for (sid, k), q in purchases.items() if k == t and q > 0]
        value = sum(q * sources[sid].unit_price * terms[sources[sid].terms].fx_rate_to_currency for sid, q in lines)
        if value <= available + 1e-9:
            available -= value
            continue
        scale = max(0., available) / value if value > 0 else 0.
        for sid, q in lines:
            src = sources[sid]
            capped = q * scale
            pack = max(src.multiple, src.case_multiple, src.pallet_multiple, src.transport_multiple)
            if pack > 0:
                capped = math.floor(capped / pack + 1e-9) * pack
            purchases[sid, t] = capped if capped >= src.minimum else 0.
        available -= sum(q * sources[sid].unit_price * terms[sources[sid].terms].fx_rate_to_currency for (sid, k), q in purchases.items() if k == t)


def _keep_amendments(req: Request) -> dict[tuple[str, str], float]:
    return {(p.id, next(o.id for o in p.options if o.action == "keep")): p.remaining for p in req.pipeline}


def _projection(req: Request, fits: dict):
    """Per SKU/location: demand rate, opening usable stock, and dated inbound (pipeline + transfers)."""
    sources = {s.id: s for s in req.sources}
    rate: dict[tuple[str, str], float] = {}
    sd2: dict[tuple[str, str], float] = {}
    for s in req.services:
        rate[s.sku, s.location] = rate.get((s.sku, s.location), 0.) + fits[s.id]["mean"]
        sd2[s.sku, s.location] = sd2.get((s.sku, s.location), 0.) + fits[s.id].get("sd", 0.) ** 2
    stock = {(s.id, loc.id): sum(x.usable for x in req.stock if x.sku == s.id and x.location == loc.id) for s in req.skus for loc in req.locations}
    inbound: dict[tuple[str, str, int], float] = {}
    for po in req.pipeline:
        src = sources[po.source]
        due = next(o.due_in for o in po.options if o.action == "keep")
        inbound[src.sku, src.destination, due] = inbound.get((src.sku, src.destination, due), 0.) + po.expected_accepted_remaining
    for row in req.inbound_transfers:
        inbound[row.sku, row.destination, row.due_in] = inbound.get((row.sku, row.destination, row.due_in), 0.) + row.accepted_quantity
    return rate, {k: math.sqrt(v) for k, v in sd2.items()}, stock, inbound


def _primary_source(req: Request, sku: str, location: str):
    options = [s for s in req.sources if s.sku == sku and s.destination == location and s.approved and s.compliance == "cleared"]
    return min(options, key=lambda s: (s.unit_price + s.freight_per_unit + s.handling_per_unit, s.id)) if options else None


def _target_of(req: Request, sku: str, location: str) -> float:
    targets = [s.target for s in req.services if s.sku == sku and s.location == location]
    return max(targets) if targets else 0.


def baseline_plan(req: Request, rule: str) -> Solution:
    """Project a named purchasing rule over the horizon.

    replace_sold      order this period's expected demand every period (what was sold is rebought)
    periodic:k        every k periods, order up to demand over (lead + k) plus z-protection
    reorder_point     when the projected position falls to lead demand + z-protection, order the
                      cover to the next feasible replenishment plus protection (a continuous-review
                      (s, S) rule projected over the horizon)
    economic_lot      reorder point as above, order quantity max(EOQ, cover) where EOQ uses the
                      supplier's fixed order cost and the location's holding rate; without a
                      fixed order cost EOQ is undefined and the rule collapses to reorder_point"""
    if rule.startswith("network:"):
        # Declared network policy (P2): branch reorder points, central echelon replenishment, priority
        # allocation and lane transfers, projected deterministically like the rules below.
        from zaad.meio.baselines import network_rule_plan
        return network_rule_plan(req, rule)
    fits = forecast_all(req)
    rate, sd, stock, inbound = _projection(req, fits)
    purchases: dict[tuple[str, int], float] = {}
    idx = review_index(req)
    kind, _, arg = rule.partition(":")
    k = int(arg) if arg else 1
    locations = {loc.id: loc for loc in req.locations}
    order_costs = {supplier: st.fixed_order_cost for supplier, _, st in supplier_orders(req)}
    for (sku, location), mu in rate.items():
        src = _primary_source(req, sku, location)
        if src is None or mu <= 0:
            continue
        z = _z(_target_of(req, sku, location))
        sigma = sd.get((sku, location), 0.)
        arrivals: dict[int, float] = {}
        for (k_, loc_, due), q in inbound.items():
            if (k_, loc_) == (sku, location):
                arrivals[due] = arrivals.get(due, 0.) + q
        level = stock.get((sku, location), 0.)
        holding = locations[location].holding_per_value_period * src.unit_price + req.liquidity.cost_of_capital_per_period * src.unit_price
        fixed = order_costs.get(src.supplier, 0.) + src.fixed_order_fee
        eoq = math.sqrt(2. * mu * fixed / holding) if kind == "economic_lot" and fixed > 0 and holding > 0 else 0.
        for t in range(req.horizon):
            level += arrivals.get(t, 0.)
            depart, arrival = dates(req, src, t)
            lead = arrival - t
            if kind == "replace_sold":
                q = lot_round(src, mu)
            elif kind == "periodic":
                if (idx + t) % k != 0:
                    q = 0.
                else:
                    horizon_cover = lead + k
                    up_to = mu * horizon_cover + z * sigma * math.sqrt(horizon_cover)
                    position = level + sum(v for d, v in arrivals.items() if d > t)
                    q = lot_round(src, max(0., up_to - position))
            else:   # reorder_point / economic_lot
                position = level + sum(v for d, v in arrivals.items() if d > t)
                reorder_point = mu * lead + z * sigma * math.sqrt(max(lead, 1))
                if position - mu > reorder_point + 1e-9:        # position after this period's demand still above s
                    q = 0.
                else:
                    nxt = next((dates(req, src, u)[1] for u in range(t + 1, req.horizon) if dates(req, src, u)[1] > arrival), None)
                    cover_to = nxt if nxt is not None else req.horizon
                    need = mu * (cover_to - t) + z * sigma * math.sqrt(max(cover_to - t, 1)) - position
                    q = lot_round(src, max(need, eoq, 0.))
            if q > 0 and arrival < req.horizon + 1:
                purchases[src.id, t] = q
                arrivals[arrival] = arrivals.get(arrival, 0.) + q * src.fill_mean
            level -= mu
    apply_mov(req, purchases)
    apply_load_cap(req, purchases)
    apply_cash_cap(req, purchases)
    purchases = {k: v for k, v in purchases.items() if v > 0}
    return Solution("OPTIMAL", purchases, {}, _keep_amendments(req), {}, None, [], 0., 0, 0, None, 0., [f"baseline:{rule}"])
