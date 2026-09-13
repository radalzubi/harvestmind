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
from zaad.sectors.contracts import resolve as sector_physics
from zaad.sourcing.contracts import resolve as sourcing_view
from zaad.full.model import pallet_units, supplier_orders


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
    # Sector operating physics, re-derived from the executed plan exactly as the model applied them
    # (receipt life, storage-state eligibility, sellable life, shipment weight). None on a legacy request.
    physics = sector_physics(req)
    # Sourcing portfolio (P3): the declared switching cost is a real payment; it enters the ledger once
    # per source outside the incumbent mix that the plan actually buys from. None on a frozen request.
    sourcing = sourcing_view(req)
    switched: set[str] = set()
    stock: dict[tuple[str, str, int], float] = defaultdict(float)
    locked: dict[str, float] = defaultdict(float)
    ledger: dict[str, float] = defaultdict(float)
    shipments: list[dict] = []
    pending, trace = [], []
    payments: dict[int, float] = defaultdict(float)
    lc = []
    demand_total: dict[str, float] = defaultdict(float)
    served_total: dict[str, float] = defaultdict(float)
    substitute_total: dict[str, float] = defaultdict(float)
    initial_units, received_units, served_inputs, expired_units, transit_loss = 0., 0., 0., 0., 0.
    # Per SKU / location / period flow telemetry (P2 network accounting). Read from the same state the
    # settlement itself evolves; it changes nothing about the economics or the validation.
    flows: list[dict] = []
    transfer_events: list[dict] = []
    flow_in: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
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
            if option.credit_per_unit > 0:
                # P4B V1: the declared refund / credit note (bounded by the refundable deposit at the contract)
                ledger["commitment_credit"] -= q * option.credit_per_unit
                payments[0] -= q * option.credit_per_unit
            if option.action != "cancel":
                due = world.po_due[po.id]
                if option.action != "keep":
                    keep = next(o for o in po.options if o.action == "keep")
                    due = option.due_in + max(0, due - keep.due_in)
                quantity = q * world.po_fill[po.id]
                life = skus[source.sku].shelf_life if physics is None else physics.receipt_life(source.sku, source.id)
                pending.append((source.sku, source.destination, due + life, due, quantity, "external"))
        if abs(total - po.remaining) > 1e-5 or (not po.allow_split_amendments and active != 1):
            raise PhysicalViolation("PO amendment conservation or exclusivity")
        if po.minimum_remaining_quantity > 0:
            # P4B V1 (release audit G): a declared floor is physical for the settlement as well as the contract
            cancelled = sum(plan.amendments.get((po.id, o.id), 0.) for o in po.options if o.action == "cancel")
            if po.remaining - cancelled < po.minimum_remaining_quantity - 1e-6:
                raise PhysicalViolation("PO reduced below its declared minimum remaining quantity")
        ledger["opening_assets"] += po.prepaid_per_remaining_unit * po.remaining
    cash, debt = req.liquidity.opening_cash, req.liquidity.opening_debt
    service_by_period: list[dict] = []
    for t in range(end):
        period_start = req.as_of + timedelta(days=t * req.period_days)
        expired_at_start: dict[tuple[str, str], float] = defaultdict(float)
        for key in list(stock):
            sku, location_of_lot, expiry = key
            if expiry <= t:
                q = stock.pop(key)
                ledger["disposal"] += q * skus[sku].disposal_fee
                expired_units += q
                expired_at_start[sku, location_of_lot] += q
        rest = []
        opening_units_at: dict[tuple[str, str], float] = defaultdict(float)
        for (sku, location, expiry), q in stock.items():
            opening_units_at[sku, location] += q
        flow_in.clear()
        for sku, location, expiry, due, quantity, kind in pending:
            if due <= t:
                stock[sku, location, expiry] += quantity
                if kind == "external":
                    received_units += quantity
                flow_in[sku, location]["external" if kind == "external" else "transfer"] += quantity
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
            if physics is not None:
                if not physics.location_ok(source.sku, source.destination):
                    raise PhysicalViolation(f"{source.destination} cannot store {physics.state(source.sku)} ({source.sku})")
                if physics.receipt_life(source.sku, source.id) <= physics.min_receipt(source.sku):
                    raise PhysicalViolation(f"receipt from {source.id} arrives below the minimum remaining life at receipt ({source.sku})")
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
            life = skus[source.sku].shelf_life if physics is None else physics.receipt_life(source.sku, source.id)
            pending.append((source.sku, source.destination, due + life, due, quantity, "external"))
        # Supplier-order economics (P1): the same rows the model carries, re-derived from the plan.
        for supplier, srcs, st in supplier_orders(req):
            lines = [(s, plan.purchases.get((s.id, t), 0.)) for s in srcs]
            lines = [(s, q) for s, q in lines if not is_dust(q, source_pack(s))]
            if not lines:
                continue
            value = sum(q * s.unit_price * terms[s.terms].fx_rate_to_currency for s, q in lines)
            if st.minimum_order_value and value < st.minimum_order_value - 1e-6:
                raise PhysicalViolation("supplier minimum order value")
            if st.max_shipment_weight is not None and physics is not None:
                weight = sum(q * float(physics.weight(s.sku) or 0.) for s, q in lines)
                if weight > st.max_shipment_weight + 1e-6:
                    raise PhysicalViolation("shipment exceeds the supplier's maximum weight")
            departure = min(dates(req, s, t)[0] for s, _ in lines)
            arrival = min(world.arrival[s.id, t] for s, _ in lines)
            ledger["ordering"] += st.fixed_order_cost
            payments[t] += st.fixed_order_cost
            ledger["receiving"] += st.receiving_fee_per_receipt
            payments[arrival] += st.receiving_fee_per_receipt
            shipment = {"period": t, "supplier": supplier, "order_value": value, "lines": [(s.id, q) for s, q in lines]}
            upp = pallet_units(st, srcs)
            if upp is not None:                      # pallet economics only when every line has a pallet size
                load = sum(q / upp[s.id] for s, q in lines)
                pallets = math.ceil(load - 1e-9)
                top = st.max_pallets if st.max_pallets is not None else (st.freight_tiers[-1].up_to_pallets if st.freight_tiers else None)
                if top is not None and pallets > top + 1e-9:
                    raise PhysicalViolation("shipment exceeds the supplier's maximum load")
                if st.freight_tiers:
                    tier = next(tier for tier in st.freight_tiers if pallets <= tier.up_to_pallets + 1e-9)
                    ledger["freight"] += tier.charge
                    payments[departure] += tier.charge
                ledger["freight"] += pallets * st.freight_per_pallet
                payments[departure] += pallets * st.freight_per_pallet
                ledger["receiving"] += pallets * st.receiving_per_pallet
                payments[arrival] += pallets * st.receiving_per_pallet
                shipment.update(pallets=pallets, load_pallets=load)
            shipments.append(shipment)
        if sourcing is not None:
            for source in req.sources:
                q = plan.purchases.get((source.id, t), 0.)
                if source.id not in switched and not is_dust(q, source_pack(source)) and sourcing.switching_cost(source.id) > 0:
                    switched.add(source.id)
                    ledger["switching"] += sourcing.switching_cost(source.id)
                    payments[t] += sourcing.switching_cost(source.id)
        for capacity_resource in req.resources:
            if usage[capacity_resource.id] > capacity_resource.capacity_by_period[t] + 1e-5:
                raise PhysicalViolation("shared supplier/route capacity breach")
        transfer_usage: dict[str, float] = defaultdict(float)
        expired_now = expired_at_start
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
            if physics is not None:
                if not physics.lane_ok(arc.sku, arc_id) or not physics.location_ok(arc.sku, arc.destination):
                    raise PhysicalViolation(f"lane {arc_id} or {arc.destination} cannot carry / hold {physics.state(arc.sku)} ({arc.sku})")
                if not physics.receivable(arc.sku, expiry, due):
                    raise PhysicalViolation(f"transfer on {arc_id} would arrive with {expiry - due} periods of life, below the minimum at receipt ({arc.sku})")
            stock[key] -= q
            transfer_usage[arc_id] += q
            pending.append((arc.sku, arc.destination, expiry, due, q * (1 - arc.loss_fraction), "transfer"))
            transit_loss += q * arc.loss_fraction
            ledger["transfer"] += q * arc.cost_per_unit
            payments[t] += q * arc.cost_per_unit
            flow_in[arc.sku, arc.origin]["transfer_out"] += q
            transfer_events.append({"period": t, "transfer": arc_id, "sku": arc.sku, "origin": arc.origin, "destination": arc.destination,
                                    "expiry": expiry, "quantity": q, "arrives": due, "received": q * (1 - arc.loss_fraction)})
        if any(q > arcs[a].capacity + 1e-5 for a, q in transfer_usage.items()):
            raise PhysicalViolation("transfer capacity breach")
        for arc_id, moved in transfer_usage.items():
            arc = arcs[arc_id]
            if is_dust(moved):
                continue
            # Packs are checked on the executable period-zero movement; later transfers are replanning
            # guidance that this evaluator may already have reduced to the stock a world actually holds.
            if t == 0 and arc.multiple > 0 and abs(moved / arc.multiple - round(moved / arc.multiple)) * arc.multiple > 1e-6 * max(1., arc.multiple):
                raise PhysicalViolation("transfer pack violation")
            if arc.fixed_cost_per_dispatch > 0:
                ledger["transfer"] += arc.fixed_cost_per_dispatch
                payments[t] += arc.fixed_cost_per_dispatch
        # Real allocation is work conserving and uses only this review's revealed demand.
        # Contract priority first, then contribution, then stable ID. No future demand input.
        for service in sorted(req.services, key=lambda s: (-customers[s.customer].priority,
                              -(s.selling_price - skus[s.sku].asset_value), s.id)):
            demand = world.demand[service.id][t]
            need = demand
            substitutions = 0.
            for sku, ratio, fee in compatible(req, service):
                for key in sorted([k for k in stock if k[0] == sku and k[1] == service.location
                                   and (physics is None or physics.sellable(sku, k[2], t))], key=lambda k: k[2]):
                    quantity = min(need, max(0., stock[key]) / ratio)
                    stock[key] -= quantity * ratio
                    served_inputs += quantity * ratio
                    flow_in[sku, service.location]["served"] += quantity * ratio
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
        closing_units_at: dict[tuple[str, str], float] = defaultdict(float)
        for (sku, location, expiry), q in stock.items():
            closing_units_at[sku, location] += q
        for pair in sorted(set(opening_units_at) | set(closing_units_at) | set(flow_in)):
            pair_sku, pair_location = pair
            f = flow_in.get(pair, {})
            flows.append({"period": t, "sku": pair_sku, "location": pair_location, "opening": opening_units_at.get(pair, 0.),
                          "external_receipts": f.get("external", 0.), "transfer_receipts": f.get("transfer", 0.),
                          "served": f.get("served", 0.), "transfer_out": f.get("transfer_out", 0.), "expired": expired_now.get(pair, 0.),
                          "closing": closing_units_at.get(pair, 0.),
                          "holding_cost": sum(q * skus[s].asset_value * locations[pair_location].holding_per_value_period
                                              for (s, loc_, _), q in stock.items() if s == pair_sku and loc_ == pair_location)})
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
        # Working capital (P1): own cash deployed below the opening balance earns the cost of
        # capital elsewhere. Charged after borrowing, so the part financed by drawn credit carries
        # interest above and never a second capital charge; idle cash above opening earns nothing.
        ledger["working_capital"] += req.liquidity.cost_of_capital_per_period * max(0., req.liquidity.opening_cash - cash)
        trace.append({"period": t, "inventory_value": sum(q * skus[s].asset_value for (s, _, _), q in stock.items()),
                      "cash": cash, "debt": debt, "payments": payments[t], "lc_reserve": reserve,
                      "pending_units": sum(p[4] for p in pending), "expired_units": expired_units})
    # Financial tail: every payment this plan committed after the horizon must be financeable from
    # closing cash above the floor plus unused credit. Forecast receipts are not counted; dated
    # known receivables and other payments declared inside the request horizon are (P1): they are
    # the same declared cash flows the model's own liquidity rows use, so model and settlement agree.
    terminal_liability = sum(v for due, v in payments.items() if due >= end)
    declared_tail = sum(req.liquidity.known_receivables[k] - req.liquidity.other_payments[k] for k in range(end, req.horizon))
    terminal_headroom = (cash - req.liquidity.minimum_cash) + (req.liquidity.credit_limit - debt) + declared_tail
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
        open_lines = [line for line in req.order_lines if line.service == rule.id and line.due_in < end and line.open_quantity > 0]
        available = {r["period"]: r["served"] for r in service_by_period if r["service"] == rule.id}
        full, on_time, orders = [], [], defaultdict(list)
        open_units, filled_units, late, partial = 0., 0., 0, 0
        for line in sorted(open_lines, key=lambda x: (x.promised_at, x.id)):
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
            "shipments": shipments,
            "unpaid_contractual_payments": terminal_liability,
            "terminal_liability_reserve": terminal_liability, "terminal_financing_headroom": terminal_headroom,
            "end_stock": [{"sku": s, "location": location_key, "expiry": e, "quantity": q,
                           **({"sellable": physics.sellable(s, e, end)} if physics is not None else {})} for (s, location_key, e), q in stock.items()],
            "future_payments": {t: v for t, v in payments.items() if t >= end},
            "pending": pending,
            "flows": flows, "transfer_events": transfer_events,
            "metric_note": "unit fill is not OTIF; zero-demand service is unobserved",
            "initial_units": initial_units, "received_units": received_units}
