"""One independent work-conserving physical/economic evaluator for every policy.

Does not use the optimizer's inventory, allocation, cash, or objective values.
Rejects illegal actions; never creates phantom stock by silently clipping them.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
import math

from zaad.full.contracts import Request
from zaad.full.model import Solution, compatible
from zaad.full.tolerance import is_dust, po_closed, source_pack
from zaad.full.worlds import World, dates, next_open


class PhysicalViolation(ValueError):
    pass


def settle(req: Request, plan: Solution, world: World, steps: int | None = None, future_guidance: bool = False) -> dict:
    """Work-conserving settlement of a plan on one world.

    Period-zero actions are the only ones an operator executes; later purchases and transfers
    are replanning guidance. With future_guidance=True a transfer planned for a later period
    that exceeds the stock actually on hand in this world is reduced to what is there and the
    shortfall is recorded as guidance_truncated_units, instead of failing the whole plan for a
    receipt that landed later in this world than in the planning worlds. Period zero stays
    strict, and nothing is ever clipped upward.
    """
    # A plan is settled on what it does, not on whether the solver proved it optimal. A
    # FEASIBLE_TIME_LIMIT plan is a real incumbent and must pass every physical check below like any
    # other; the status gate that lived here rejected it before any of them ran (P0-D1).
    if not plan.usable_plan:
        raise PhysicalViolation("unusable solve is not a zero-order plan")
    guidance_truncated = 0.
    skus = {s.id: s for s in req.skus}
    end = req.horizon if steps is None else steps
    if not 1 <= end <= req.horizon:
        raise ValueError("invalid settlement prefix")
    locations = {location_key.id: location_key for location_key in req.locations}
    sources = {s.id: s for s in req.sources}
    terms = {s.id: s for s in req.terms}
    calendars = {c.id: c for c in req.calendars}
    customers = {c.id: c for c in req.customers}
    arcs = {a.id: a for a in req.transfers}
    stock: dict[tuple[str, str, int], float] = defaultdict(float)
    locked: dict[str, float] = defaultdict(float)
    ledger: dict[str, float] = defaultdict(float)
    pending, trace = [], []
    payments: dict[int, float] = defaultdict(float)
    lc = []
    demand_total: dict[str, float] = defaultdict(float)
    served_total: dict[str, float] = defaultdict(float)
    substitute_total: dict[str, float] = defaultdict(float)
    initial_units, received_units, served_inputs, expired_units, transit_loss = 0., 0., 0., 0., 0.
    for lot in req.stock:
        stock[lot.sku, lot.location, lot.expires_in] += lot.usable
        locked[lot.location] += (lot.quantity - lot.usable) * skus[lot.sku].volume
        ledger["opening_assets"] += lot.usable * skus[lot.sku].asset_value
        initial_units += lot.usable
    for inbound in req.inbound_transfers:
        pending.append((inbound.sku, inbound.destination, inbound.expires_in, inbound.due_in, inbound.accepted_quantity, "transfer"))
        ledger["opening_assets"] += inbound.accepted_quantity * skus[inbound.sku].asset_value
        initial_units += inbound.accepted_quantity
    for po in req.pipeline:
        source = sources[po.source]
        if po_closed(po, source):
            # Dust remaining from an earlier solve is closed, never an obligation nor a receipt.
            continue
        pack = source_pack(source)
        total = 0.
        active = 0
        for option in po.options:
            q = plan.amendments.get((po.id, option.id), 0.)
            if q < -1e-6 or q > option.max_quantity + 1e-6:
                raise PhysicalViolation("amendment quantity outside contract")
            if is_dust(q, pack):
                continue
            total += q
            active += 1
            if option.action != "keep" and (option.deadline < req.as_of or po.stage not in option.allowed_stages):
                raise PhysicalViolation("expired or stage-ineligible amendment")
            ledger[option.action + "_fee"] += q * option.fee_per_unit
            ledger["procurement"] += q * option.remaining_invoice_per_unit
            payments[0] += q * option.fee_per_unit
            payments[option.payment_due_in] += q * option.remaining_invoice_per_unit
            if option.action != "cancel":
                due = world.po_due[po.id]
                if option.action != "keep":
                    keep = next(o for o in po.options if o.action == "keep")
                    due = option.due_in + max(0, due - keep.due_in)
                quantity = q * world.po_fill[po.id]
                pending.append((source.sku, source.destination, due + skus[source.sku].shelf_life, due, quantity, "external"))
        if abs(total - po.remaining) > 1e-5 or (not po.allow_split_amendments and active != 1):
            raise PhysicalViolation("PO amendment conservation or exclusivity")
        ledger["opening_assets"] += po.prepaid_per_remaining_unit * po.remaining
    cash, debt = req.liquidity.opening_cash, req.liquidity.opening_debt
    service_by_period: list[dict] = []
    for t in range(end):
        period_start = req.as_of + timedelta(days=t * req.period_days)
        for key in list(stock):
            sku, _, expiry = key
            if expiry <= t:
                q = stock.pop(key)
                ledger["disposal"] += q * skus[sku].disposal_fee
                expired_units += q
        rest = []
        for sku, location, expiry, due, quantity, kind in pending:
            if due <= t:
                stock[sku, location, expiry] += quantity
                if kind == "external":
                    received_units += quantity
            else:
                rest.append((sku, location, expiry, due, quantity, kind))
        pending = rest
        for warehouse in req.locations:
            volume = locked[warehouse.id] + sum(q * skus[s].volume for (s, location_key, _), q in stock.items() if location_key == warehouse.id)
            if volume > warehouse.capacity_volume + 1e-5:
                raise PhysicalViolation("receiving capacity breach")
        usage: dict[str, float] = defaultdict(float)
        for source in req.sources:
            q = plan.purchases.get((source.id, t), 0.)
            if q < -1e-6:
                raise PhysicalViolation("negative purchase")
            if is_dust(q, source_pack(source)):
                continue
            order_date = next_open(period_start, calendars[source.order_calendar])
            if not source.approved or source.compliance != "cleared" or order_date > source.quote_expires:
                raise PhysicalViolation("ineligible source or expired quote")
            if q > min(source.maximum, source.capacity_by_period[t]) + 1e-5 or q < source.minimum - 1e-5:
                raise PhysicalViolation("source capacity / MOQ")
            if source.multiple and abs(q / source.multiple - round(q / source.multiple)) > 1e-5:
                raise PhysicalViolation("pack violation")
            for multiple in (source.case_multiple, source.pallet_multiple, source.transport_multiple):
                if multiple and abs(q / multiple - round(q / multiple)) > 1e-5:
                    raise PhysicalViolation("case/pallet/transport multiple violation")
            for resource in source.resources:
                usage[resource] += q * skus[source.sku].volume
            term = terms[source.terms]
            price = source.unit_price * term.fx_rate_to_currency
            ledger["procurement"] += q * price
            ledger["freight"] += q * source.freight_per_unit
            ledger["handling"] += q * source.handling_per_unit
            ledger["order_fees"] += source.fixed_order_fee
            ledger["financing"] += q * price * term.financing_fee_fraction
            departure = dates(req, source, t)[0]
            due = world.arrival[source.id, t]
            trigger = {"order": t, "shipment": departure, "arrival": due}[term.balance_trigger]
            payments[t] += q * price * (term.deposit_fraction + term.financing_fee_fraction) + source.fixed_order_fee
            payments[trigger + math.ceil(term.net_days / req.period_days)] += q * price * (1 - term.deposit_fraction)
            payments[departure] += q * (source.freight_per_unit + source.handling_per_unit)
            lc.append((due, q * price * term.letter_of_credit_fraction))
            quantity = q * world.fills[source.id, t]
            pending.append((source.sku, source.destination, due + skus[source.sku].shelf_life, due, quantity, "external"))
        for capacity_resource in req.resources:
            if usage[capacity_resource.id] > capacity_resource.capacity_by_period[t] + 1e-5:
                raise PhysicalViolation("shared supplier/route capacity breach")
        transfer_usage: dict[str, float] = defaultdict(float)
        for (arc_id, expiry, period), q in plan.transfers.items():
            if period != t or is_dust(q):
                continue
            arc = arcs[arc_id]
            when = period_start + timedelta(days=arc.lead_periods * req.period_days)
            receive = next_open(when, calendars[locations[arc.destination].receiving_calendar])
            due = math.ceil((receive - req.as_of).total_seconds() / (req.period_days * 86400))
            key = (arc.sku, arc.origin, expiry)
            if future_guidance and t >= 1 and arc.approved and due < expiry and 0 <= q and q > stock[key] + 1e-5:
                guidance_truncated += q - max(0., stock[key])
                q = max(0., stock[key])
                if is_dust(q):
                    continue
            if not arc.approved or due >= expiry or q > stock[key] + 1e-5 or q < 0:
                raise PhysicalViolation("transfer lacks usable source stock or approval")
            stock[key] -= q
            transfer_usage[arc_id] += q
            pending.append((arc.sku, arc.destination, expiry, due, q * (1 - arc.loss_fraction), "transfer"))
            transit_loss += q * arc.loss_fraction
            ledger["transfer"] += q * arc.cost_per_unit
            payments[t] += q * arc.cost_per_unit
        if any(q > arcs[a].capacity + 1e-5 for a, q in transfer_usage.items()):
            raise PhysicalViolation("transfer capacity breach")
        # Real allocation is work conserving and uses only this review's revealed demand.
        # Contract priority first, then contribution, then stable ID. No future demand input.
        for service in sorted(req.services, key=lambda s: (-customers[s.customer].priority,
                              -(s.selling_price - skus[s.sku].asset_value), s.id)):
            demand = world.demand[service.id][t]
            need = demand
            substitutions = 0.
            for sku, ratio, fee in compatible(req, service):
                for key in sorted([k for k in stock if k[0] == sku and k[1] == service.location], key=lambda k: k[2]):
                    quantity = min(need, max(0., stock[key]) / ratio)
                    stock[key] -= quantity * ratio
                    served_inputs += quantity * ratio
                    need -= quantity
                    ledger["substitution"] += quantity * fee
                    payments[t] += quantity * fee
                    if sku != service.sku:
                        substitutions += quantity
            served = demand - need
            demand_total[service.id] += demand
            served_total[service.id] += served
            substitute_total[service.id] += substitutions
            ledger["lost_sales_opportunity"] += need * service.selling_price
            ledger["sla"] += need * service.sla_per_unmet
            payments[t] += need * service.sla_per_unmet
            service_by_period.append({"service": service.id, "period": t, "demand": demand, "served": served})
        holding = sum(q * skus[s].asset_value * locations[location_key].holding_per_value_period for (s, location_key, _), q in stock.items())
        ledger["holding"] += holding
        # Holding is an economic accrual, NOT a second cash-financing charge.
        interest = debt * req.liquidity.interest_per_period
        ledger["financing"] += interest
        cash += req.liquidity.known_receivables[t] - req.liquidity.other_payments[t] - payments[t] - interest
        reserve = sum(value for due, value in lc if due > t)
        required = req.liquidity.minimum_cash + reserve
        borrow = max(0., required - cash)
        debt += borrow
        cash += borrow
        if debt > req.liquidity.credit_limit + 1e-5:
            raise PhysicalViolation("insufficient dated liquidity")
        repay = min(debt, max(0., cash - required))
        cash -= repay
        debt -= repay
        trace.append({"period": t, "inventory_value": sum(q * skus[s].asset_value for (s, _, _), q in stock.items()),
                      "cash": cash, "debt": debt, "payments": payments[t], "lc_reserve": reserve,
                      "pending_units": sum(p[4] for p in pending), "expired_units": expired_units})
    # Financial tail: every payment this plan committed after the horizon must be financeable from
    # closing cash above the floor plus unused credit. Forecast receipts are not counted.
    terminal_liability = sum(v for due, v in payments.items() if due >= end)
    terminal_headroom = (cash - req.liquidity.minimum_cash) + (req.liquidity.credit_limit - debt)
    if terminal_liability > terminal_headroom + 1e-5:
        raise PhysicalViolation(f"post-horizon obligations {terminal_liability:.2f} exceed terminal financing headroom {terminal_headroom:.2f}")
    closing_units = sum(stock.values()) + sum(p[4] for p in pending if p[5] == "transfer")
    # External quantities still in transit have not yet entered the conservation equation.
    conservation = initial_units + received_units - served_inputs - expired_units - transit_loss - closing_units
    if abs(conservation) > 1e-4:
        raise PhysicalViolation(f"inventory conservation residual {conservation}")
    ledger["closing_assets"] = -sum(q * skus[s].terminal_value for (s, _, e), q in stock.items() if e > end)
    ledger["closing_assets"] -= sum(q * skus[s].terminal_value for s, _, e, _, q, _ in pending if e > end)
    total_cost = sum(ledger.values())
    service_summary = {s.id: served_total[s.id] / demand_total[s.id] if demand_total[s.id] else None for s in req.services}
    order_metrics = {}
    # Order-level reconciliation across every service: an order is complete only when all of its
    # open lines (any SKU, any service) are complete, and on time only when every line is on time.
    order_state: dict[str, dict] = defaultdict(lambda: {"lines": 0, "complete": 0, "on_time": 0, "partial": 0, "late": 0})
    superseded = sum(1 for line in req.order_lines if line.superseded_by)
    cancelled_lines = sum(1 for line in req.order_lines if not line.superseded_by and line.cancelled >= line.quantity - line.filled - 1e-9 and line.quantity > 0)
    for rule in req.services:
        lines = [line for line in req.order_lines if line.service == rule.id and line.due_in < end and line.open_quantity > 0]
        available = {r["period"]: r["served"] for r in service_by_period if r["service"] == rule.id}
        full, on_time, orders = [], [], defaultdict(list)
        open_units, filled_units, late, partial = 0., 0., 0, 0
        for line in sorted(lines, key=lambda x: (x.promised_at, x.id)):
            quantity = line.open_quantity
            filled = min(quantity, max(0., available.get(line.due_in, 0.)))
            available[line.due_in] = available.get(line.due_in, 0.) - filled
            complete = filled >= quantity - 1e-6
            when = req.as_of + timedelta(days=line.due_in * req.period_days)
            timely = when <= line.promised_at
            full.append(complete)
            on_time.append(complete and timely)
            orders[line.order_id].append(complete and timely)
            open_units += quantity
            filled_units += filled
            late += int(complete and not timely)
            partial += int(0 < filled < quantity - 1e-6)
            state = order_state[line.order_id]
            state["lines"] += 1
            state["complete"] += int(complete)
            state["on_time"] += int(complete and timely)
            state["partial"] += int(0 < filled < quantity - 1e-6)
            state["late"] += int(complete and not timely)
        order_metrics[rule.id] = {"line_fill": sum(full) / len(full) if full else None,
                                  "order_fill": sum(all(v) for v in orders.values()) / len(orders) if orders else None,
                                  "otif": sum(on_time) / len(on_time) if on_time else None,
                                  "order_otif": None,   # filled after every service is reconciled
                                  "quantity_fill": filled_units / open_units if open_units else None,
                                  "lines": len(full), "partial_lines": partial, "late_complete_lines": late,
                                  "scope": "declared open lines only; line metrics per service, order metrics across services"}
    orders_summary = {"orders": len(order_state),
                      "complete_order_rate": sum(v["complete"] == v["lines"] for v in order_state.values()) / len(order_state) if order_state else None,
                      "order_otif_rate": sum(v["on_time"] == v["lines"] for v in order_state.values()) / len(order_state) if order_state else None,
                      "orders_with_partial_lines": sum(v["partial"] > 0 for v in order_state.values()),
                      "orders_with_late_lines": sum(v["late"] > 0 for v in order_state.values()),
                      "superseded_lines_ignored": superseded, "fully_cancelled_lines_ignored": cancelled_lines,
                      "unobserved_lines_after_horizon": sum(1 for line in req.order_lines if line.open_quantity > 0 and line.due_in >= end)}
    for rule in req.services:
        touched = {line.order_id for line in req.order_lines if line.service == rule.id and line.due_in < end and line.open_quantity > 0}
        if touched:
            order_metrics[rule.id]["order_otif"] = sum(order_state[o]["on_time"] == order_state[o]["lines"] for o in touched) / len(touched)
    return {"economic_cost": total_cost, "ledger": dict(ledger), "service": service_summary,
            "guidance_truncated_units": guidance_truncated,
            "order_metrics": order_metrics, "orders": orders_summary,
            "substituted": dict(substitute_total), "trace": trace, "service_by_period": service_by_period,
            "conservation_residual": conservation, "ledger_residual": total_cost - sum(ledger.values()),
            "unpaid_contractual_payments": terminal_liability,
            "terminal_liability_reserve": terminal_liability, "terminal_financing_headroom": terminal_headroom,
            "end_stock": [{"sku": s, "location": location_key, "expiry": e, "quantity": q} for (s, location_key, e), q in stock.items()],
            "future_payments": {t: v for t, v in payments.items() if t >= end},
            "pending": pending,
            "metric_note": "unit fill is not OTIF; zero-demand service is unobserved",
            "initial_units": initial_units, "received_units": received_units}
