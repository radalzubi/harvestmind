"""Competent baseline purchasing policies (P1), projected over the horizon on the fitted mean demand.

These are the comparators ZAAD P1 is measured against and the declared operator rules it can be
asked to improve on. Each respects the supplier's lot rules (minimum, multiples, minimum order
value, pallet load, cash) jointly, so that it is a policy a buyer could actually execute, not a
straw man that fails settlement; an order-week no legal lot can satisfy is cancelled and noted. None of them sees the truth; they see the same review snapshot the optimizer sees."""
from __future__ import annotations

import math
from datetime import datetime, timezone

from zaad.full.contracts import Request
from zaad.full.economics import round_up
from zaad.full.model import Solution, supplier_orders
from zaad.full.worlds import dates, forecast_all
from zaad.sourcing.contracts import resolve as sourcing_view
from zaad.sourcing.incumbent import apply_resource_cap, split_projection

EPOCH = datetime(2000, 1, 3, tzinfo=timezone.utc)   # a Monday; periodic cadences count from here
Z_SERVICE = {.90: 1.282, .95: 1.645, .98: 2.054, .99: 2.326}


def _z(target: float) -> float:
    return min(Z_SERVICE.items(), key=lambda kv: abs(kv[0] - target))[1] if target > 0 else 0.


def review_index(req: Request) -> int:
    return (req.as_of - EPOCH).days // req.period_days


def _pack(source) -> float:
    return max(source.multiple, source.case_multiple, source.pallet_multiple, source.transport_multiple)


def _line_cap(source, t: int | None = None) -> float:
    cap = float(source.maximum)
    if t is not None and t < len(source.capacity_by_period):
        cap = min(cap, float(source.capacity_by_period[t]))
    return cap


def _floor_lot(source, q: float, t: int | None = None) -> float:
    """The largest legal line quantity not above `q` (inside the cap, a whole pack, at least the minimum), or 0 when
    no legal quantity exists below it. A buyer who cannot place a legal lot places none."""
    if q <= 0:
        return 0.
    q = min(q, _line_cap(source, t))
    pack = _pack(source)
    if pack > 0:
        q = math.floor(q / pack + 1e-9) * pack
    return q if q >= source.minimum - 1e-9 else 0.


def lot_round(source, q: float, t: int | None = None) -> float:
    """Round a wanted quantity up to a legal lot; when the lot rounds past the line's cap, the largest legal lot
    inside the cap (a cap that is not itself a pack multiple used to be returned as is and failed settlement with
    "pack violation": M5 coupled run 1, commit 70c10db)."""
    if q <= 0:
        return 0.
    q = max(q, source.minimum)
    for m in (source.multiple, source.case_multiple, source.pallet_multiple, source.transport_multiple):
        q = round_up(q, m)
    cap = _line_cap(source, t)
    return q if q <= cap + 1e-9 else _floor_lot(source, cap, t)


def _max_load(st) -> float | None:
    return st.max_pallets if st.max_pallets is not None else (st.freight_tiers[-1].up_to_pallets if st.freight_tiers else None)


def apply_mov(req: Request, purchases: dict[tuple[str, int], float]) -> None:
    """Lift each supplier order to its minimum order value, adding whole lots to the cheapest-to-hold lines first
    (lowest unit price), never past a line's cap or the supplier's pallet cap. A buyer facing an MOV does exactly
    this; an order the lift cannot bring to the MOV is cancelled by `apply_order_constraints`."""
    from zaad.full.model import pallet_units
    terms = {x.id: x for x in req.terms}
    for supplier, srcs, st in supplier_orders(req):
        if st.minimum_order_value <= 0:
            continue
        top, upp = _max_load(st), pallet_units(st, srcs)
        for t in range(req.horizon):
            lines = [s for s in srcs if purchases.get((s.id, t), 0.) > 0]
            if not lines:
                continue
            value = sum(purchases[s.id, t] * s.unit_price * terms[s.terms].fx_rate_to_currency for s in lines)
            if value >= st.minimum_order_value - 1e-9:
                continue
            for line in sorted(lines, key=lambda s: (s.unit_price, s.id)):
                price = line.unit_price * terms[line.terms].fx_rate_to_currency
                current = purchases[line.id, t]
                lifted = lot_round(line, current + (st.minimum_order_value - value) / price, t)
                if top is not None and upp is not None:
                    room = top - sum(purchases[s.id, t] / upp[s.id] for s in lines if s.id != line.id)
                    if lifted / upp[line.id] > room + 1e-9:
                        lifted = _floor_lot(line, room * upp[line.id], t)       # the largest lot that still fits the load
                if lifted <= current:
                    continue
                purchases[line.id, t] = lifted
                value += (lifted - current) * price
                if value >= st.minimum_order_value - 1e-9:
                    break


def apply_load_cap(req: Request, purchases: dict[tuple[str, int], float], notes: list[str] | None = None) -> None:
    """Cap each supplier order at the supplier's maximum load (a full truck): scale the lines down proportionally to
    legal lots (a line whose scaled lot falls below its minimum waits for a later order rather than being lifted back
    over the cap), then drop the smallest-value lines until the load is legal. A buyer facing an FTL cap ships a full
    legal load and reorders sooner; the reorder rules pick the rest up on the next period. Run 1 of the M5 coupled
    experiment (commit 70c10db) lifted scaled lines back to their minimums and dropped at most one line, so several
    low-volume lines at their minimums still exceeded the cap and settlement rejected the shipment."""
    from zaad.full.model import pallet_units
    for supplier, srcs, st in supplier_orders(req):
        top, upp = _max_load(st), pallet_units(st, srcs)
        if top is None or upp is None:
            continue
        for t in range(req.horizon):
            lines = [s for s in srcs if purchases.get((s.id, t), 0.) > 0]
            load = sum(purchases[s.id, t] / upp[s.id] for s in lines)
            if load <= top + 1e-9:
                continue
            scale = top / load
            for s in lines:
                purchases[s.id, t] = _floor_lot(s, purchases[s.id, t] * scale, t)
            kept = [s for s in lines if purchases[s.id, t] > 0]
            while kept and sum(purchases[s.id, t] / upp[s.id] for s in kept) > top + 1e-9:
                smallest = min(kept, key=lambda s: (purchases[s.id, t] * s.unit_price, s.id))
                purchases[smallest.id, t] = 0.
                kept.remove(smallest)
            if notes is not None:
                notes.append(f"projection:load_cap:{supplier}:{t}:{len(lines)} lines wanted {load:.2f} pallets, {len(kept)} shipped")


def apply_cash_cap(req: Request, purchases: dict[tuple[str, int], float]) -> None:
    """Keep each period's cumulative purchase value inside the cash the request declares: opening
    cash plus dated receivables less other payments to date, plus the credit limit. A buyer who
    cannot pay for a full lot orders what can be paid for and reorders when cash allows."""
    if req.liquidity.opening_cash is None:
        return      # no cash balance declared: capital does not cap the projection (sentinel cleanup)
    terms = {x.id: x for x in req.terms}
    sources = {s.id: s for s in req.sources}
    credit = math.inf if req.liquidity.credit_limit is None else req.liquidity.credit_limit
    available = req.liquidity.opening_cash - req.liquidity.opening_debt + credit - req.liquidity.minimum_cash
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


def _order_breach(req: Request, purchases: dict[tuple[str, int], float], srcs: list, st, t: int) -> str | None:
    """The settlement's own order-level checks (`settlement.settle`), re-derived on the projection: None when the
    supplier's period-`t` order is legal, otherwise the reason settlement would give."""
    from zaad.full.model import pallet_units
    terms = {x.id: x for x in req.terms}
    lines = [(s, purchases.get((s.id, t), 0.)) for s in srcs]
    lines = [(s, q) for s, q in lines if q > 1e-9]
    if not lines:
        return None
    for s, q in lines:
        if q > _line_cap(s, t) + 1e-5 or q < s.minimum - 1e-5:
            return "source capacity / MOQ"
        for multiple in (s.multiple, s.case_multiple, s.pallet_multiple, s.transport_multiple):
            if multiple and abs(q / multiple - round(q / multiple)) > 1e-5:
                return "pack violation"
    value = sum(q * s.unit_price * terms[s.terms].fx_rate_to_currency for s, q in lines)
    if st.minimum_order_value and value < st.minimum_order_value - 1e-6:
        return "supplier minimum order value"
    upp = pallet_units(st, srcs)
    top = _max_load(st)
    if upp is not None and top is not None and math.ceil(sum(q / upp[s.id] for s, q in lines) - 1e-9) > top + 1e-9:
        return "shipment exceeds the supplier's maximum load"
    return None


def apply_order_constraints(req: Request, purchases: dict[tuple[str, int], float], notes: list[str]) -> None:
    """Apply the supplier's order rules jointly: the MOV lift, the load cap and the cash cap interact (a lift can
    break the cap, a cut can break the MOV), so they run to a fixed point, and any supplier order-week that is still
    illegal by the settlement's own checks is cancelled and recorded in `notes` rather than shipped. Without lot,
    MOV, load or cash terms every step is a no-op and the projection is unchanged."""
    for _ in range(4):
        before = dict(purchases)
        apply_mov(req, purchases)
        apply_load_cap(req, purchases, notes)
        apply_cash_cap(req, purchases)
        if purchases == before:
            break
    for supplier, srcs, st in supplier_orders(req):
        for t in range(req.horizon):
            reason = _order_breach(req, purchases, srcs, st, t)
            if reason is not None:
                for s in srcs:
                    purchases.pop((s.id, t), None)
                notes.append(f"projection:cancelled:{supplier}:{t}:{reason}")


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
    sourcing = sourcing_view(req)

    def options_of(sku, location):
        return [s for s in req.sources if s.sku == sku and s.destination == location and s.approved and s.compliance == "cleared"]
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
                q = lot_round(src, mu, t)
            elif kind == "periodic":
                if (idx + t) % k != 0:
                    q = 0.
                else:
                    horizon_cover = lead + k
                    up_to = mu * horizon_cover + z * sigma * math.sqrt(horizon_cover)
                    position = level + sum(v for d, v in arrivals.items() if d > t)
                    q = lot_round(src, max(0., up_to - position), t)
            else:   # reorder_point / economic_lot
                position = level + sum(v for d, v in arrivals.items() if d > t)
                reorder_point = mu * lead + z * sigma * math.sqrt(max(lead, 1))
                if position - mu > reorder_point + 1e-9:        # position after this period's demand still above s
                    q = 0.
                else:
                    nxt = next((dates(req, src, u)[1] for u in range(t + 1, req.horizon) if dates(req, src, u)[1] > arrival), None)
                    cover_to = nxt if nxt is not None else req.horizon
                    need = mu * (cover_to - t) + z * sigma * math.sqrt(max(cover_to - t, 1)) - position
                    q = lot_round(src, max(need, eoq, 0.), t)
            if q > 0 and arrival < req.horizon + 1:
                # incumbent source mix (P3): the declared shares split the rule's quantity; frozen single line otherwise
                for line_src, line_q in split_projection(sourcing, sku, location, options_of(sku, location), src, q, t):
                    purchases[line_src.id, t] = line_q
                    arrivals[dates(req, line_src, t)[1]] = arrivals.get(dates(req, line_src, t)[1], 0.) + line_q * line_src.fill_mean
            level -= mu
    if sourcing is not None:
        apply_resource_cap(req, purchases)   # P3: a projected order never exceeds a shared supplier capacity
    notes: list[str] = []
    apply_order_constraints(req, purchases, notes)
    purchases = {k: v for k, v in purchases.items() if v > 0}
    return Solution("OPTIMAL", purchases, {}, _keep_amendments(req), {}, None, [], 0., 0, 0, None, 0., [f"baseline:{rule}", *notes])
