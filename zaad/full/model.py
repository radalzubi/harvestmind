"""Sparse continuous/mixed-integer, age-indexed network MPC.

All order/transfer/amendment schedules are scenario invariant. Only inventory,
customer fulfillment and borrowing react to a scenario. Future schedules are
guidance, not commitments. No service-floor relaxation is hidden in this model.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
import math
import time

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

from zaad.full.contracts import Request
from zaad.full.tolerance import is_dust, po_closed, source_pack
from zaad.full.worlds import World, dates, next_open


class Linear:
    def __init__(self):
        self.names, self.cost, self.lower, self.upper, self.integer = [], [], [], [], []
        self.rows, self.lo, self.hi = [], [], []

    def var(self, name, cost=0., upper=np.inf, integer=False, lower=0.):
        n = len(self.names)
        self.names.append(name)
        self.cost.append(cost)
        self.lower.append(lower)
        self.upper.append(upper)
        self.integer.append(int(integer))
        return n

    def row(self, coefficients, lower=-np.inf, upper=np.inf):
        self.rows.append(dict(coefficients))
        self.lo.append(lower)
        self.hi.append(upper)

    def solve(self, seconds, objective=None, solver="highs"):
        rr, cc, vv = [], [], []
        for r, terms in enumerate(self.rows):
            for c, v in terms.items():
                if v:
                    rr.append(r)
                    cc.append(c)
                    vv.append(v)
        matrix = coo_matrix((vv, (rr, cc)), shape=(len(self.rows), len(self.names))).tocsc()
        if solver != "highs":
            from zaad.full.solvers import pyomo_solve
            result = pyomo_solve(self, seconds, objective, solver)
        else:
            result = milp(np.asarray(self.cost if objective is None else objective),
                      integrality=np.asarray(self.integer),
                      bounds=Bounds(self.lower, self.upper),
                      constraints=LinearConstraint(matrix, self.lo, self.hi),
                      options={"time_limit": seconds, "mip_rel_gap": 1e-6})
        if result.x is not None:
            activity = matrix @ result.x
            residual = max(float(np.max(np.asarray(self.lo) - activity, initial=0)),
                           float(np.max(activity - np.asarray(self.hi), initial=0)),
                           float(np.max(np.asarray(self.lower) - result.x, initial=0)),
                           float(np.max(result.x - np.asarray(self.upper), initial=0)))
            ints = np.asarray(self.integer, dtype=bool)
            residual = max(residual, float(np.max(abs(result.x[ints] - np.rint(result.x[ints])), initial=0)))
        else:
            residual = math.inf
        return result, residual


@dataclass
class Solution:
    status: str
    purchases: dict[tuple[str, int], float]
    transfers: dict[tuple[str, int, int], float]
    amendments: dict[tuple[str, str], float]
    projected_service: dict[str, float]
    projected_cost: float | None
    cash: list[dict]
    solve_seconds: float
    variables: int
    constraints: int
    gap: float | None
    residual: float | None
    warnings: list[str]


def compatible(req, service):
    """(supplied SKU, physical input per service-equivalent unit, penalty)."""
    rows = [(service.sku, 1., 0.)]
    customer = next(c for c in req.customers if c.id == service.customer)
    for rule in req.substitutions:
        if (rule.approved and rule.requested_sku == service.sku
                and service.customer in rule.customers and customer.channel in rule.channels):
            rows.append((rule.supplied_sku, rule.input_per_output / rule.service_equivalence,
                         rule.penalty_per_output / rule.service_equivalence))
    return rows


def solve(req: Request, worlds: list[World], *, service_floor: bool = False,
          service_first: str | None = None, cvar_weight: float = 0.,
          fixed: Solution | None = None, disabled: frozenset[str] = frozenset(),
          targets: dict[tuple[str, int], float] | None = None,
          per_world_service: bool = False, service_risk: str = "expected",
          service_risk_levels: dict[str, float] | None = None) -> Solution:
    started = time.monotonic()
    if not worlds or abs(sum(w.weight for w in worlds) - 1) > 1e-8 or any(w.weight <= 0 for w in worlds):
        raise ValueError("positive scenario weights must sum to one")
    H = req.horizon
    if any(len(w.demand[s.id]) != H for w in worlds for s in req.services):
        raise ValueError("world dimensions do not match request")
    skus = {s.id: s for s in req.skus}
    locs = {location_key.id: location_key for location_key in req.locations}
    sources = {s.id: s for s in req.sources}
    terms = {p.id: p for p in req.terms}
    customers = {c.id: c for c in req.customers}
    calendars = {c.id: c for c in req.calendars}
    m = Linear()
    x, tr, po, inv, use, unmet, cash, debt = {}, {}, {}, {}, {}, {}, {}, {}
    use_by_stock = defaultdict(list)
    stock_indices = defaultdict(list)
    use_for_service: dict[tuple, dict[int, float]] = defaultdict(dict)
    ordered_services = sorted(req.services, key=lambda s: (-customers[s.customer].priority,
        -(s.selling_price - skus[s.sku].asset_value), s.id))
    service_rank = {s.id: n for n, s in enumerate(ordered_services)}
    service_for_stock = defaultdict(list)
    for service in ordered_services:
        for sku, _, _ in compatible(req, service):
            service_for_stock[sku, service.location].append(service)
    costs: list[dict[int, float]] = [defaultdict(float) for _ in worlds]
    payments: list[list[dict[int, float]]] = [[defaultdict(float) for _ in range(H)] for _ in worlds]
    arrivals: list[dict[tuple, dict[int, float]]] = [defaultdict(lambda: defaultdict(float)) for _ in worlds]
    outbound: dict[tuple, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    cohorts = defaultdict(set)
    locked: dict[str, float] = defaultdict(float)
    initial: dict[tuple, float] = defaultdict(float)
    constant = req.liquidity.opening_debt * req.liquidity.interest_per_period
    quote_groups = defaultdict(list)
    for lot in req.stock:
        cohorts[lot.sku].add(lot.expires_in)
        initial[lot.sku, lot.location, lot.expires_in] += lot.usable
        locked[lot.location] += (lot.quantity - lot.usable) * skus[lot.sku].volume
        constant += lot.usable * skus[lot.sku].asset_value
        if lot.expires_in == 0:
            constant += lot.usable * skus[lot.sku].disposal_fee
    for inbound in req.inbound_transfers:
        cohorts[inbound.sku].add(inbound.expires_in)
        q = m.var(("inbound_transfer", inbound.id), lower=inbound.accepted_quantity, upper=inbound.accepted_quantity)
        constant += inbound.accepted_quantity * skus[inbound.sku].asset_value
        for w in range(len(worlds)):
            arrivals[w][inbound.sku, inbound.destination, inbound.expires_in, inbound.due_in][q] += 1
            if inbound.due_in >= H:
                costs[w][q] -= skus[inbound.sku].terminal_value
    tail: list[dict[int, float]] = [defaultdict(float) for _ in worlds]

    def expense(index, amount, w, when):
        costs[w][index] += amount
        if 0 <= when < H:
            payments[w][when][index] += amount
        elif when >= H:
            # Committed after the horizon: not paid inside the plan, but it must be financeable at the end.
            tail[w][index] += amount
    # "alternates" disabled keeps only the cheapest approved source per SKU and destination, so the
    # value of the other approved suppliers and routes can be measured rather than assumed.
    cheapest: dict[tuple[str, str], tuple[float, str]] = {}
    for source in req.sources:
        if source.approved and source.compliance == "cleared":
            term = terms[source.terms]
            landed = source.unit_price * term.fx_rate_to_currency + source.freight_per_unit + source.handling_per_unit
            pair = (source.sku, source.destination)
            if pair not in cheapest or (landed, source.id) < cheapest[pair]:
                cheapest[pair] = (landed, source.id)
    primary_id = {key: value[1] for key, value in cheapest.items()}
    # Purchase variables and fixed costs, continuous unless actual pack/MOQ needs MILP.
    for source in req.sources:
        term = terms[source.terms]
        price = source.unit_price * term.fx_rate_to_currency
        landed = price + source.freight_per_unit + source.handling_per_unit
        for t in range(H):
            origin = req.as_of + timedelta(days=req.period_days * t)
            order_date = next_open(origin, calendars[source.order_calendar])
            eligible = source.approved and source.compliance == "cleared" and order_date <= source.quote_expires
            if "alternates" in disabled and primary_id.get((source.sku, source.destination)) != source.id:
                eligible = False
            cap = min(source.maximum, source.capacity_by_period[t]) if eligible else 0.
            q = m.var(("purchase", source.id, t), upper=cap)
            x[source.id, t] = q
            multiple = source.multiple if "continuous" not in disabled else max(source.multiple, 10.)
            if multiple > 0:
                units = m.var(("packs", source.id, t), upper=math.floor(cap / multiple), integer=True)
                m.row({q: 1, units: -multiple}, 0, 0)
            for label, increment in (("case", source.case_multiple), ("pallet", source.pallet_multiple), ("transport", source.transport_multiple)):
                if increment:
                    units = m.var((label, source.id, t), upper=math.floor(cap / increment), integer=True)
                    m.row({q: 1, units: -increment}, 0, 0)
            if source.minimum or source.fixed_order_fee or source.exclusive_quote_group:
                active = m.var(("active", source.id, t), upper=1, integer=True)
                m.row({q: 1, active: -cap}, upper=0)
                m.row({q: 1, active: -source.minimum}, lower=0)
                for w in range(len(worlds)):
                    expense(active, source.fixed_order_fee, w, t)
                if source.exclusive_quote_group:
                    quote_groups[source.exclusive_quote_group, t].append(active)
            if fixed is not None:
                quantity = fixed.purchases.get((source.id, t), 0.)
                m.row({q: 1}, quantity, quantity)
            departure = dates(req, source, t)[0]
            for w, world in enumerate(worlds):
                due, fill = world.arrival[source.id, t], world.fills[source.id, t]
                if not 0 <= fill <= 1 or due <= t:
                    raise ValueError("invalid physical fill or arrival chronology")
                expiry = due + skus[source.sku].shelf_life
                cohorts[source.sku].add(expiry)
                arrivals[w][source.sku, source.destination, expiry, due][q] += fill
                trigger = {"order": t, "shipment": departure, "arrival": due}[term.balance_trigger]
                net = math.ceil(term.net_days / req.period_days)
                # Total contract invoice is cost regardless of whether payment is beyond horizon.
                costs[w][q] += landed + price * term.financing_fee_fraction
                payments[w][t][q] += price * term.deposit_fraction
                payment_t = trigger + net
                if payment_t < H:
                    payments[w][payment_t][q] += price * (1 - term.deposit_fraction)
                if departure < H:
                    payments[w][departure][q] += source.freight_per_unit + source.handling_per_unit
                payments[w][t][q] += price * term.financing_fee_fraction
                if due >= H:
                    costs[w][q] -= fill * skus[source.sku].terminal_value
    for group in quote_groups.values():
        m.row({v: 1 for v in group}, upper=1)
    # Outstanding PO amendments: only explicit contractual options, no invented permission.
    for order in req.pipeline:
        source = sources[order.source]
        if po_closed(order, source):
            # Residue from an earlier solve, not an obligation: no variables, no exclusivity row.
            continue
        constant += order.prepaid_per_remaining_unit * order.remaining
        quantities, switches = [], []
        for option in order.options:
            allowed = (option.action == "keep" or (option.deadline >= req.as_of and order.stage in option.allowed_stages))
            if option.action in disabled:
                allowed = False
            capacity = min(order.remaining, option.max_quantity) if allowed else 0.
            q = m.var(("amend", order.id, option.id), upper=capacity)
            po[order.id, option.id] = q
            quantities.append(q)
            if not order.allow_split_amendments:
                flag = m.var(("po_option", order.id, option.id), upper=1, integer=True)
                m.row({q: 1, flag: -order.remaining}, 0, 0)
                switches.append(flag)
            if fixed is not None:
                amount = fixed.amendments.get((order.id, option.id), 0.)
                m.row({q: 1}, amount, amount)
            for w, world in enumerate(worlds):
                expense(q, option.fee_per_unit, w, 0)
                expense(q, option.remaining_invoice_per_unit, w, option.payment_due_in)
                if option.action == "cancel":
                    continue
                due = world.po_due[order.id] if option.action == "keep" else option.due_in
                # Changed ETA is a contractual target, subject to the world's PO ETA error.
                if option.action != "keep":
                    keep = next(o for o in order.options if o.action == "keep")
                    due += max(0, world.po_due[order.id] - keep.due_in)
                expiry = due + skus[source.sku].shelf_life
                cohorts[source.sku].add(expiry)
                arrivals[w][source.sku, source.destination, expiry, due][q] += world.po_fill[order.id]
                if due >= H:
                    costs[w][q] -= world.po_fill[order.id] * skus[source.sku].terminal_value
        m.row({q: 1 for q in quantities}, order.remaining, order.remaining)
        if switches:
            m.row({q: 1 for q in switches}, 1, 1)
    # Reachable SKU/location pairs only, not a dense Cartesian network.
    pairs = {(location_key.sku, location_key.location) for location_key in req.stock} | {(s.sku, s.destination) for s in req.sources}
    pairs |= {(s.sku, s.location) for s in req.services}
    for arc in req.transfers:
        pairs.update(((arc.sku, arc.origin), (arc.sku, arc.destination)))
    for service in req.services:
        for sku, _, _ in compatible(req, service):
            pairs.add((sku, service.location))
    for arc in req.transfers:
        for t in range(H):
            ids = []
            for expiry in sorted(cohorts[arc.sku]):
                if expiry <= t + arc.lead_periods:
                    continue
                cap = arc.capacity if arc.approved and "transfers" not in disabled else 0.
                # Receiving calendar, rather than silently unloading on closed days.
                when = req.as_of + timedelta(days=(t + arc.lead_periods) * req.period_days)
                actual = next_open(when, calendars[locs[arc.destination].receiving_calendar])
                due = math.ceil((actual - req.as_of).total_seconds() / (86400 * req.period_days))
                if due >= expiry:
                    cap = 0.
                q = m.var(("transfer", arc.id, expiry, t), upper=cap)
                tr[arc.id, expiry, t] = q
                ids.append(q)
                outbound[arc.sku, arc.origin, expiry, t][q] += 1
                if fixed is not None:
                    amount = fixed.transfers.get((arc.id, expiry, t), 0.)
                    m.row({q: 1}, amount, amount)
                for w in range(len(worlds)):
                    arrivals[w][arc.sku, arc.destination, expiry, due][q] += 1 - arc.loss_fraction
                    expense(q, arc.cost_per_unit, w, t)
                    if due >= H:
                        costs[w][q] -= (1 - arc.loss_fraction) * skus[arc.sku].terminal_value
            if ids:
                m.row({q: 1 for q in ids}, upper=arc.capacity)
    # Executable transfers share observed opening inventory across all arcs.
    # Expected PO receipts, including overdue ones, cannot fund today's action.
    confirmed: dict[tuple[str, str, int], float] = defaultdict(float)
    for inbound in req.inbound_transfers:
        if inbound.due_in == 0:
            confirmed[inbound.sku, inbound.destination, inbound.expires_in] += inbound.accepted_quantity
    for (sku, origin, expiry, t), transfer_terms in outbound.items():
        if t == 0:
            m.row(transfer_terms, upper=initial[sku, origin, expiry] + confirmed[sku, origin, expiry])
    for resource in req.resources:
        for t in range(H):
            row = {x[s.id, t]: skus[s.sku].volume for s in req.sources if resource.id in s.resources}
            if row:
                m.row(row, upper=resource.capacity_by_period[t])
    for w, world in enumerate(worlds):
        for t in range(H):
            for sku, location in sorted(pairs):
                for expiry in sorted(cohorts[sku]):
                    if expiry <= t:
                        continue
                    index = m.var(("inventory", sku, location, expiry, t, w),
                                  upper=max(0., (locs[location].capacity_volume - locked[location]) / skus[sku].volume))
                    inv[sku, location, expiry, t, w] = index
                    stock_indices[sku, location, t, w].append(index)
                    costs[w][index] += skus[sku].asset_value * locs[location].holding_per_value_period
                    if expiry == t + 1 and t < H - 1:
                        costs[w][index] += skus[sku].disposal_fee
                    if t == H - 1:
                        costs[w][index] -= skus[sku].terminal_value if expiry > H else 0.
            for service in req.services:
                d = world.demand[service.id][t]
                if d < 0 or not math.isfinite(d):
                    raise ValueError("invalid world demand")
                u = m.var(("unmet", service.id, t, w), upper=d)
                unmet[service.id, t, w] = u
                costs[w][u] += service.selling_price + service.sla_per_unmet
                payments[w][t][u] += service.sla_per_unmet
                balance = {u: 1.}
                for sku, conversion, fee in compatible(req, service):
                    if "substitutions" in disabled and sku != service.sku:
                        continue
                    consumptions = []
                    stocks = []
                    for expiry in sorted(cohorts[sku]):
                        key = (sku, service.location, expiry, t, w)
                        if key not in inv:
                            continue
                        q = m.var(("allocate", sku, service.id, expiry, t, w), upper=d)
                        use[sku, service.id, expiry, t, w] = (q, conversion)
                        use_by_stock[sku, service.location, expiry, t, w].append((q, conversion))
                        use_for_service[service.id, sku, t, w][q] = conversion
                        balance[q] = 1.
                        costs[w][q] += fee
                        if fee:
                            payments[w][t][q] += fee
                        consumptions.append((expiry, q))
                        stocks.append(inv[key])
                    if d > 0 and stocks:
                        # Available compatible stock cannot be hoarded while demand is lost.
                        empty = m.var(("depleted", sku, service.id, t, w), upper=1, integer=True)
                        m.row({u: 1, empty: -d}, upper=0)
                        cap = locs[service.location].capacity_volume / skus[sku].volume
                        m.row({**{i: 1 for i in stocks}, empty: cap}, upper=cap)
                        # FEFO: consumption of younger cohorts requires older remaining stock zero.
                        for expiry, q in consumptions:
                            older = [inv[sku, service.location, e, t, w] for e in cohorts[sku]
                                     if t < e < expiry and (sku, service.location, e, t, w) in inv]
                            if older:
                                active = m.var(("fefo", sku, service.id, expiry, t, w), upper=1, integer=True)
                                m.row({q: 1, active: -d}, upper=0)
                                m.row({**{i: 1 for i in older}, active: cap}, upper=cap)
                m.row(balance, d, d)
            # Same current-review customer priority and direct-before-substitution
            # semantics as settlement; later demand cannot steal today's stock.
            for rank, high in enumerate(ordered_services):
                high_demand = world.demand[high.id][t]
                if not high_demand:
                    continue
                eligible_skus = {sku for sku, _, _ in compatible(req, high)}
                lower_candidates = {s.id: s for sku in eligible_skus for s in service_for_stock[sku, high.location]
                                    if service_rank[s.id] > rank}
                for low in lower_candidates.values():
                    for sku, ratio, _ in compatible(req, low):
                        if sku not in eligible_skus:
                            continue
                        lower_units = use_for_service[low.id, sku, t, w]
                        if lower_units:
                            active = m.var(("priority", high.id, low.id, sku, t, w), upper=1, integer=True)
                            m.row({unmet[high.id, t, w]: 1, active: -high_demand}, upper=0)
                            cap = locs[high.location].capacity_volume / skus[sku].volume
                            m.row({**lower_units, active: cap}, upper=cap)
                direct_remaining = stock_indices[high.sku, high.location, t, w]
                substitute_units = {q: 1 for sku in eligible_skus if sku != high.sku
                                    for q in use_for_service[high.id, sku, t, w]}
                if direct_remaining and substitute_units:
                    active = m.var(("direct_first", high.id, t, w), upper=1, integer=True)
                    cap = locs[high.location].capacity_volume / skus[high.sku].volume
                    m.row({**substitute_units, active: -high_demand}, upper=0)
                    m.row({**{i: 1 for i in direct_remaining}, active: cap}, upper=cap)
            for sku, location in sorted(pairs):
                for expiry in sorted(cohorts[sku]):
                    key = (sku, location, expiry, t, w)
                    if key not in inv:
                        continue
                    row = defaultdict(float, {inv[key]: 1})
                    prior = inv.get((sku, location, expiry, t - 1, w))
                    if prior is not None:
                        row[prior] -= 1
                    for q, coefficient in arrivals[w][sku, location, expiry, t].items():
                        row[q] -= coefficient
                    for q, coefficient in outbound[sku, location, expiry, t].items():
                        row[q] += coefficient
                    for used_q, used_conversion in use_by_stock[key]:
                        row[used_q] += used_conversion
                    opening = initial[sku, location, expiry] if t == 0 else 0.
                    m.row(row, opening, opening)
            for warehouse in req.locations:
                row = {index: skus[sku].volume for (sku, location_key, _, period, scenario), index in inv.items()
                       if location_key == warehouse.id and period == t and scenario == w}
                if row:
                    m.row(row, upper=warehouse.capacity_volume - locked[warehouse.id])
                # Capacity applies before serving demand too, not just end-of-period stock.
                before: dict[int, float] = defaultdict(float)
                for (sku, location_key, expiry, period, scenario), index in inv.items():
                    if location_key == warehouse.id and period == t - 1 and scenario == w and expiry > t:
                        before[index] += skus[sku].volume
                for (sku, location_key, _, period), flows in arrivals[w].items():
                    if location_key == warehouse.id and period == t:
                        for index, factor in flows.items():
                            before[index] += factor * skus[sku].volume
                initial_volume = sum(v * skus[k].volume for (k, location_key, e), v in initial.items()
                                     if location_key == warehouse.id and e > 0) if t == 0 else 0.
                if before or initial_volume + locked[warehouse.id] > warehouse.capacity_volume:
                    m.row(before, upper=warehouse.capacity_volume - locked[warehouse.id] - initial_volume)
            # Cash balance: contractual payments, explicit debt and interest, no forecast sales receipts.
            liquidity = req.liquidity
            c = m.var(("cash", t, w), lower=liquidity.minimum_cash)
            b = m.var(("debt", t, w), upper=liquidity.credit_limit)
            cash[t, w], debt[t, w] = c, b
            row = defaultdict(float, {c: 1, b: -1})
            prior_cash, prior_debt = cash.get((t - 1, w)), debt.get((t - 1, w))
            rhs = liquidity.known_receivables[t] - liquidity.other_payments[t]
            if prior_cash is not None:
                assert prior_debt is not None
                row[prior_cash] -= 1
                row[prior_debt] += 1 + liquidity.interest_per_period
                costs[w][prior_debt] += liquidity.interest_per_period
            else:
                rhs += liquidity.opening_cash - liquidity.opening_debt * (1 + liquidity.interest_per_period)
            for q, amount in payments[w][t].items():
                row[q] += amount
            m.row(row, rhs, rhs)
            # Letters of credit reserve liquidity until receipt, separately from expense.
            reserve = defaultdict(float, {c: -1})
            for source in req.sources:
                term = terms[source.terms]
                for placed in range(t + 1):
                    if world.arrival[source.id, placed] > t:
                        reserve[x[source.id, placed]] += source.unit_price * term.fx_rate_to_currency * term.letter_of_credit_fraction
            m.row(reserve, upper=-liquidity.minimum_cash)
            if t == H - 1 and tail[w]:
                # Terminal solvency: closing cash above the floor plus unused credit must cover every
                # invoice this plan commits to after the horizon. No forecast receipts are counted.
                terminal = defaultdict(float, {c: -1, b: 1})
                for q, amount in tail[w].items():
                    terminal[q] += amount
                m.row(terminal, upper=liquidity.credit_limit - liquidity.minimum_cash)
    order_vars: dict = {}
    counted_orders: set = set()
    if service_floor:
        for service in req.services:
            if service.metric != "unit_fill":
                lines = [line for line in req.order_lines if line.service == service.id
                         and line.due_in < H and line.open_quantity > 0]
                if not lines:
                    raise ValueError("order-level service requires outstanding lines in the horizon")
                metric_terms = {}
                denominator = 0.
                for w, world in enumerate(worlds):
                    complete: dict = {}
                    for line in lines:
                        qty = line.open_quantity
                        full = m.var(("line_full", line.id, w), upper=1, integer=True)
                        complete[line.id] = full
                        allocated = m.var(("line_units", line.id, w), upper=qty)
                        m.row({allocated: 1, full: -qty}, lower=0)
                        complete[(line.id, "units")] = allocated
                        if service.metric in ("otif", "order_otif"):
                            delivery = req.as_of + timedelta(days=line.due_in * req.period_days)
                            if delivery > line.promised_at:
                                m.row({full: 1}, 0, 0)
                    for t in {line.due_in for line in lines}:
                        row = {complete[line.id, "units"]: 1 for line in lines if line.due_in == t}
                        row[unmet[service.id, t, w]] = 1
                        m.row(row, upper=world.demand[service.id][t])
                    if service.metric in ("order_fill", "order_otif"):
                        # One completeness variable per order and world, shared by every service the
                        # order touches: a multi-SKU order is complete only when all its lines are.
                        for order_id in {line.order_id for line in lines}:
                            order_key = ("order_full", order_id, w)
                            full = order_vars.get(order_key)
                            if full is None:
                                full = order_vars[order_key] = m.var(order_key, upper=1, integer=True)
                            for line in lines:
                                if line.order_id == order_id:
                                    m.row({full: 1, complete[line.id]: -1}, upper=0)
                            if order_key not in counted_orders:
                                counted_orders.add(order_key)
                                metric_terms[full] = world.weight
                                denominator += world.weight
                    else:
                        for line in lines:
                            metric_terms[complete[line.id]] = world.weight
                            denominator += world.weight
                m.row(metric_terms, lower=service.target * denominator)
                continue
            row, demand = {}, 0.
            for w, world in enumerate(worlds):
                for t in range(H):
                    row[unmet[service.id, t, w]] = world.weight
                    demand += world.weight * world.demand[service.id][t]
            m.row(row, upper=(1 - service.target) * demand)
            risk_level = (service_risk_levels or {}).get(service.id, req.service_risk_level)
            if service_risk == "cvar" and len(worlds) > 1 and risk_level > 0:
                # Quantile protection (Rockafellar-Uryasev): the mean unmet fraction over the worst
                # (1 - level) share of scenarios must also respect the target. Protection then scales
                # with the spread of the scenarios and vanishes when they are tight, or when the
                # SKU/location risk state is calm (level scaled by protection activity).
                eta = m.var(("service_eta", service.id))
                tail_terms: dict[int, float] = {eta: 1.}
                for w, world in enumerate(worlds):
                    total_w = sum(world.demand[service.id])
                    if total_w <= 0:
                        continue
                    zeta = m.var(("service_tail", service.id, w))
                    tail_terms[zeta] = world.weight / (1 - risk_level)
                    m.row({**{unmet[service.id, t, w]: 1 / total_w for t in range(H)}, eta: -1, zeta: -1}, upper=0)
                m.row(tail_terms, upper=1 - service.target)
            if per_world_service:
                for w, world in enumerate(worlds):
                    m.row({unmet[service.id, t, w]: 1 for t in range(H)},
                          upper=(1 - service.target) * sum(world.demand[service.id]))
    for w, world in enumerate(worlds):
        for q, amount in costs[w].items():
            m.cost[q] += world.weight * amount
    if cvar_weight:
        threshold = m.var(("cvar_threshold",), cost=cvar_weight, lower=-np.inf)
        for w, world in enumerate(worlds):
            tail = m.var(("cvar_tail", w), cost=cvar_weight * world.weight / .1)
            row = dict(costs[w])
            row[threshold], row[tail] = -1, -1
            m.row(row, upper=0)
    if targets is not None:
        # Operational projection of a heuristic target into COMMON constraints.
        # It remains labelled a projected baseline, not an unconstrained strawman.
        penalty = 1000 * max(s.selling_price + s.sla_per_unmet for s in req.services)
        for target_key, quantity in targets.items():
            plus, minus = m.var(("target_above", *target_key), cost=penalty), m.var(("target_below", *target_key), cost=penalty)
            m.row({x[target_key]: 1, plus: -1, minus: 1}, quantity, quantity)
    objective = None
    if service_first:
        objective = np.zeros(len(m.names))
        for service in req.services:
            if service_first not in {"all", service.id}:
                continue
            for w, world in enumerate(worlds):
                for t in range(H):
                    objective[unmet[service.id, t, w]] = world.weight * customers[service.customer].priority
    result, residual = m.solve(req.max_solve_seconds, objective, req.solver)
    if objective is not None and result.status == 0 and result.x is not None:
        optimum = float(np.dot(objective, result.x))
        m.row({i: float(v) for i, v in enumerate(objective) if v}, upper=optimum + 1e-7)
        remaining = req.max_solve_seconds - (time.monotonic() - started)
        if remaining > 0:
            result, residual = m.solve(remaining, solver=req.solver)
    usable = result.status == 0 and result.x is not None and residual <= 1e-5
    elapsed = time.monotonic() - started
    gap = getattr(result, "mip_gap", None)
    if not usable:
        return Solution({1: "TIME_LIMIT", 2: "INFEASIBLE", 3: "UNBOUNDED"}.get(result.status, "SOLVER_ERROR"), {}, {}, {}, {}, None, [], elapsed,
                        len(m.names), len(m.rows), gap, residual if math.isfinite(residual) else None, [str(result.message)])
    values = result.x
    service_result = {}
    for service in req.services:
        total = sum(world.weight * sum(world.demand[service.id]) for world in worlds)
        loss = sum(world.weight * values[unmet[service.id, t, w]] for w, world in enumerate(worlds) for t in range(H))
        service_result[service.id] = 1 - loss / total if total else 1.
    economic = constant + sum(world.weight * sum(values[q] * v for q, v in costs[w].items()) for w, world in enumerate(worlds))
    pack_of = {source.id: source_pack(source) for source in req.sources}
    po_pack = {order.id: pack_of[order.source] for order in req.pipeline}
    return Solution("OPTIMAL", {k: float(max(0, values[q])) for k, q in x.items() if not is_dust(values[q], pack_of[k[0]])},
                    {k: float(max(0, values[q])) for k, q in tr.items() if not is_dust(values[q])},
                    {k: float(max(0, values[q])) for k, q in po.items() if not is_dust(values[q], po_pack[k[0]])},
                    service_result, float(economic),
                    [{"period": t, "scenario": w, "cash": float(values[cash[t, w]]), "debt": float(values[debt[t, w]])} for w in range(len(worlds)) for t in range(H)],
                    elapsed, len(m.names), len(m.rows), gap, residual, [])
