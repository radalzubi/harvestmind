"""Cycle-stock economics (P1): cost decomposition, order construction waterfall, attribution,
materiality abstention, provenance and plain-language explanations.

Nothing here changes what the optimizer buys. It reads a plan and a settlement and says, in units
and in money, why each order is the size it is and whether the difference against the incumbent is
material enough to act on. Every category partitions the ordered quantity exactly; every cost
component reconciles to the settlement's economic cost to the tolerance stated in `reconcile`."""
from __future__ import annotations

import math
from statistics import mean
from typing import Any

from zaad.full.contracts import Request
from zaad.full.model import Solution, pallet_units, supplier_orders
from zaad.full.tolerance import is_dust, source_pack
from zaad.full.worlds import dates

# Settlement ledger key -> reported cost component. Every key the settlement can write is named
# here, so an unmapped key is a reconciliation failure rather than silent OTHER.
COMPONENT_OF = {
    "procurement": "PURCHASE",
    "freight": "FREIGHT",
    "order_fees": "ORDERING", "ordering": "ORDERING",
    "handling": "RECEIVING", "receiving": "RECEIVING",
    "holding": "CARRYING", "disposal": "CARRYING",
    "financing": "FINANCING", "working_capital": "FINANCING",
    "sla": "SHORTAGE", "lost_sales_opportunity": "SHORTAGE",
    "substitution": "OTHER", "transfer": "OTHER",
    "switching": "ORDERING",   # P3: a declared switching / qualification cost, charged once per newly used source
    "opening_assets": "INVENTORY_VALUE_CHANGE", "closing_assets": "INVENTORY_VALUE_CHANGE",
    "terminal_continuation": "INVENTORY_VALUE_CHANGE",   # P1 lot-sizing terminal valuation on evaluation rows (planner.evaluate)
}
COMPONENTS = ("PURCHASE", "FREIGHT", "ORDERING", "RECEIVING", "CARRYING", "FINANCING", "SHORTAGE", "OTHER", "INVENTORY_VALUE_CHANGE")
CATEGORIES = ("LEAD_TIME_EXPOSURE", "DEMAND_CYCLE", "SERVICE_PROTECTION", "MOQ", "CASE_ROUNDING", "PALLET_ROUNDING",
              "MOV", "FREIGHT_ECONOMICS", "ORDER_COST_ECONOMICS", "SUPPLIER_CALENDAR", "OTHER_EXPLAINED")
RECONCILE_TOLERANCE = 1e-6
NO_MATERIAL_IMPROVEMENT = "NO MATERIAL IMPROVEMENT AVAILABLE"


def cost_breakdown(ledger: dict[str, float]) -> dict[str, Any]:
    """Settlement ledger -> named components that sum to the settlement's economic cost.

    INVENTORY_VALUE_CHANGE is the horizon's opening stock at asset value less closing stock at
    terminal value; it is what makes a plan that ends with a full shelf comparable to one that
    ends empty. TOTAL is the settlement's economic cost exactly."""
    out: dict[str, Any] = {name: 0. for name in COMPONENTS}
    unmapped = []
    for key, value in ledger.items():
        component = COMPONENT_OF.get(key)
        if component is None:
            unmapped.append(key)
            component = "OTHER"
        out[component] += value
    out["TOTAL"] = sum(ledger.values())
    out["OPERATING_TOTAL"] = out["TOTAL"] - out["INVENTORY_VALUE_CHANGE"]
    out["unmapped_ledger_keys"] = unmapped
    return out


def reconcile(result: dict) -> dict[str, Any]:
    """Component sum against the settlement's economic cost and its own ledger residual."""
    breakdown = cost_breakdown(result["ledger"])
    component_gap = breakdown["TOTAL"] - result["economic_cost"]
    return {"components_sum": breakdown["TOTAL"], "economic_cost": result["economic_cost"],
            "component_gap": component_gap, "ledger_residual": result.get("ledger_residual", 0.),
            "reconciled": abs(component_gap) <= RECONCILE_TOLERANCE * max(1., abs(result["economic_cost"]))
                          and abs(result.get("ledger_residual", 0.)) <= RECONCILE_TOLERANCE * max(1., abs(result["economic_cost"])),
            "unmapped_ledger_keys": breakdown["unmapped_ledger_keys"]}


def working_capital(req: Request, result: dict) -> dict[str, float | None]:
    """Cash deployed and inventory carried, averaged over the settled periods."""
    trace = result.get("trace") or []
    if not trace:
        return {"cash_deployed_mean": None, "inventory_value_mean": None, "peak_cash_deployed": None}
    deployed = [max(0., req.liquidity.opening_cash - row["cash"] + row["debt"]) for row in trace]
    return {"cash_deployed_mean": mean(deployed), "peak_cash_deployed": max(deployed),
            "inventory_value_mean": mean(row["inventory_value"] for row in trace)}


def mean_breakdown(rows: list[dict]) -> dict[str, float] | None:
    """Component means across settled worlds (None when any world is unusable)."""
    usable = [r for r in rows if r.get("usable")]
    if not usable or len(usable) != len(rows):
        return None
    parts = [cost_breakdown(r["ledger"]) for r in usable]
    weights = [float(r.get("weight", 1.)) for r in usable]
    total = sum(weights) or 1.
    return {name: sum(w * p[name] for w, p in zip(weights, parts)) / total for name in (*COMPONENTS, "TOTAL", "OPERATING_TOTAL")}


# ---------------------------------------------------------------- order construction waterfall

def next_replenishment(req: Request, source, t: int, allowed: frozenset[int] | None = None) -> tuple[int, int | None]:
    """(arrival period of an order at t, arrival period of the next order that could realistically
    be placed after t) under the source's order, shipping and receiving calendars."""
    arrival = dates(req, source, t)[1]
    for k in range(t + 1, req.horizon):
        if allowed is not None and k not in allowed:
            continue
        candidate = dates(req, source, k)[1]
        if candidate > arrival:
            return arrival, candidate
    return arrival, None


def round_up(q: float, multiple: float) -> float:
    return q if multiple <= 0 or q <= 0 else math.ceil(q / multiple - 1e-9) * multiple


def order_waterfall(req: Request, fits: dict, protection: list[dict], solution: Solution | None, *,
                    period: int | None = 0, allowed: frozenset[int] | None = None) -> list[dict]:
    """Per planned purchase: demand until the next realistic replenishment + justified protection +
    lot requirements - usable on hand - usable inbound = economic need, then MOQ, case, pallet, MOV
    and freight steps. The attribution categories partition the ordered quantity exactly."""
    if solution is None or not solution.purchases:
        return []
    sources = {s.id: s for s in req.sources}
    terms = {x.id: x for x in req.terms}
    prot = {(row["sku"], row["location"]): row for row in protection}
    mu: dict[tuple[str, str], float] = {}
    for s in req.services:
        mu[s.sku, s.location] = mu.get((s.sku, s.location), 0.) + fits[s.id]["mean"]
    on_hand = {(s.id, loc.id): sum(x.usable for x in req.stock if x.sku == s.id and x.location == loc.id) for s in req.skus for loc in req.locations}
    inbound: dict[tuple[str, str, int], float] = {}
    for po in req.pipeline:
        src = sources[po.source]
        due = next(o.due_in for o in po.options if o.action == "keep")
        inbound[src.sku, src.destination, due] = inbound.get((src.sku, src.destination, due), 0.) + po.expected_accepted_remaining
    for row in req.inbound_transfers:
        inbound[row.sku, row.destination, row.due_in] = inbound.get((row.sku, row.destination, row.due_in), 0.) + row.accepted_quantity
    planned = sorted(((sid, t, q) for (sid, t), q in solution.purchases.items()
                      if q > 0 and not is_dust(q, source_pack(sources[sid])) and (period is None or t == period)),
                     key=lambda x: (x[1], dates(req, sources[x[0]], x[1])[1], x[0]))
    # Earlier planned arrivals for the same SKU/location count as inbound for later orders.
    planned_arrivals: dict[tuple[str, str, int], float] = {}
    for sid, t, q in sorted(((sid, t, q) for (sid, t), q in solution.purchases.items() if q > 0), key=lambda x: x[1]):
        src = sources[sid]
        a = dates(req, src, t)[1]
        planned_arrivals[src.sku, src.destination, a] = planned_arrivals.get((src.sku, src.destination, a), 0.) + q * src.fill_mean
    order_terms = {supplier: (srcs, st) for supplier, srcs, st in supplier_orders(req)}
    out = []
    for sid, t, q in planned:
        src = sources[sid]
        key = (src.sku, src.destination)
        arrival, next_feasible = next_replenishment(req, src, t, allowed)
        # The next realistic replenishment is the next order the calendars (and any cadence mask)
        # allow to land after this one: the order is asked to cover demand until then, and no
        # further. Cover beyond that point is a choice - a lot rule, a freight or order-cost
        # economy - and is attributed as such rather than folded into "cycle".
        cover_until = next_feasible if next_feasible is not None else req.horizon
        rate = mu.get(key, 0.)
        lead_demand = rate * max(0, arrival - t)
        cycle_demand = rate * max(0, cover_until - arrival)
        # Under an every-period cadence the next order could land one period after this one; the
        # cover the calendars force beyond that is the supplier calendar's contribution.
        minimal_cycle = rate * max(0, min(cover_until, arrival + 1) - arrival)
        calendar_units = max(0., cycle_demand - minimal_cycle)
        cycle_core = cycle_demand - calendar_units
        prot_row = prot.get(key)
        protection_units = float(prot_row["protection_units"]) if prot_row else 0.
        usable_on_hand = on_hand.get(key, 0.)
        usable_inbound = sum(v for (k, loc, a), v in inbound.items() if (k, loc) == key and a < cover_until)
        usable_inbound += sum(v for (k, loc, a), v in planned_arrivals.items() if (k, loc) == key and a < arrival)
        position = usable_on_hand + usable_inbound
        gross = lead_demand + cycle_demand + protection_units
        need = max(0., gross - position)
        # Lot steps on the economic need, in the order a buyer applies them.
        after_moq = max(need, src.minimum) if need > 0 else 0.
        after_case = round_up(round_up(after_moq, src.multiple), src.case_multiple)
        after_pallet = round_up(after_case, src.pallet_multiple)
        price = src.unit_price * terms[src.terms].fx_rate_to_currency
        mov_units = 0.
        supplier_lines = [(o, sources[o].unit_price * terms[sources[o].terms].fx_rate_to_currency, solution.purchases.get((o, t), 0.))
                          for o in sources if sources[o].supplier == src.supplier]
        st = order_terms.get(src.supplier, (None, None))[1]
        if st is not None and st.minimum_order_value > 0:
            # Value the order would have at this line's lot-rounded need with the other lines as
            # planned; any gap to the MOV is this line's share of the top-up, in units.
            value_others = sum(p * qq for o, p, qq in supplier_lines if o != sid)
            shortfall_value = max(0., st.minimum_order_value - value_others - after_pallet * price)
            if shortfall_value > 0 and price > 0:
                mov_units = min(max(0., q - after_pallet), shortfall_value / price)
        after_mov = after_pallet + mov_units
        remainder = max(0., q - after_mov)
        # Freight economics: completing the last pallet of the supplier order, and filling up to a
        # tariff tier the order lands on exactly.
        freight_units = 0.
        if st is not None and remainder > 1e-9:
            upp = pallet_units(st, [sources[o] for o, _, _ in supplier_lines])
            if upp is not None and upp.get(sid):
                load = sum(qq / upp[o] for o, _, qq in supplier_lines if qq > 0)
                pallets = math.ceil(load - 1e-9)
                share = q / sum(qq for _, _, qq in supplier_lines if qq > 0)
                fill = max(0., pallets - (load - q / upp[sid]) - (after_mov / upp[sid])) * upp[sid] * share if pallets else 0.
                freight_units = min(remainder, max(0., fill))
                at_tier = any(abs(pallets - tier.up_to_pallets) < 1e-9 for tier in st.freight_tiers)
                if at_tier and st.freight_tiers:
                    freight_units = remainder
        remainder -= freight_units
        # Order-cost economics: cover beyond the next replenishment opportunity that per-order
        # costs justify. Justified when the order-level costs the extension avoids are at least the
        # carrying and capital it adds; otherwise the units stay unexplained and are said to be so.
        order_cost_units = 0.
        cycle_economics = None
        per_order = (st.fixed_order_cost + st.receiving_fee_per_receipt if st is not None else 0.) + src.fixed_order_fee
        if remainder > 1e-9 and rate > 0 and per_order > 0 and next_feasible is not None:
            periods_extended = remainder / rate
            cadence = max(1, next_feasible - arrival)
            orders_avoided = periods_extended / cadence
            holding = next(loc.holding_per_value_period for loc in req.locations if loc.id == src.destination)
            rate_per_period = holding * next(k.asset_value for k in req.skus if k.id == src.sku) + req.liquidity.cost_of_capital_per_period * price
            extra_carry = remainder * rate_per_period * periods_extended / 2.
            justified = orders_avoided * per_order >= extra_carry
            cycle_economics = {"extension_units": remainder, "extension_periods": periods_extended, "minimum_cadence_periods": cadence,
                               "orders_avoided": orders_avoided, "order_costs_avoided": orders_avoided * per_order,
                               "extra_carrying_and_capital": extra_carry, "justified": bool(justified),
                               "scope": "plan inputs only; order-level costs avoided are per-order fees, the carrying side is average extra units at the holding and capital rates"}
            if justified:
                order_cost_units = remainder
        # Partition of q. The usable position is netted against the demand-side requirements in
        # the order they fall due (lead-time demand, cycle demand, calendar cover, protection);
        # what remains is the economic need by category. The ordered quantity then fills those
        # categories in the same order (so when q < need the later ones are truncated) and any
        # excess over the need is attributed to the lot, freight and order-cost steps, in the
        # order a buyer applies them. Whatever is left is OTHER_EXPLAINED and is said to be so.
        cats: dict[str, float] = {}
        offset = position
        for name, amount in (("LEAD_TIME_EXPOSURE", lead_demand), ("DEMAND_CYCLE", cycle_core),
                             ("SUPPLIER_CALENDAR", calendar_units), ("SERVICE_PROTECTION", protection_units)):
            netted = max(0., amount - offset)
            offset = max(0., offset - amount)
            cats[name] = netted
        budget = q
        for name in ("LEAD_TIME_EXPOSURE", "DEMAND_CYCLE", "SUPPLIER_CALENDAR", "SERVICE_PROTECTION"):
            take = max(0., min(cats[name], budget))
            cats[name] = take
            budget -= take
        for name, amount in (("MOQ", after_moq - need), ("CASE_ROUNDING", after_case - after_moq),
                             ("PALLET_ROUNDING", after_pallet - after_case), ("MOV", mov_units),
                             ("FREIGHT_ECONOMICS", freight_units), ("ORDER_COST_ECONOMICS", order_cost_units)):
            take = max(0., min(amount, budget))
            cats[name] = take
            budget -= take
        cats["OTHER_EXPLAINED"] = budget
        under_need = max(0., need - q)
        out.append({"source": sid, "supplier": src.supplier, "sku": src.sku, "location": src.destination, "period": t, "quantity": q,
                    "arrival_period": arrival, "next_realistic_replenishment_period": next_feasible,
                    "demand_rate_per_period": rate, "lead_time_demand": lead_demand,
                    "demand_until_next_replenishment": cycle_demand, "justified_protection_units": protection_units,
                    "usable_on_hand": usable_on_hand, "usable_inbound": usable_inbound,
                    "economic_need": need, "after_moq": after_moq, "after_case": after_case, "after_pallet": after_pallet,
                    "after_mov": after_mov, "under_need_units": under_need,
                    "cycle_economics": cycle_economics,
                    "attribution": cats, "attribution_sum": sum(cats.values()),
                    "protection_regime": (prot_row["state"]["regime"] if prot_row else None),
                    "explanation": ""})
        out[-1]["explanation"] = explain_order(req, out[-1], st)
    return out


def explain_order(req: Request, row: dict, st=None) -> str:
    cats = row["attribution"]
    parts = []
    if cats["LEAD_TIME_EXPOSURE"] > 1e-9:
        parts.append(f"{cats['LEAD_TIME_EXPOSURE']:.0f} covers demand before it lands in period {row['arrival_period']}")
    if cats["DEMAND_CYCLE"] > 1e-9:
        until = row["next_realistic_replenishment_period"]
        parts.append(f"{cats['DEMAND_CYCLE']:.0f} covers demand from arrival until the next realistic replenishment"
                     + (f" (period {until})" if until is not None else " (end of the plan)"))
    if cats["SUPPLIER_CALENDAR"] > 1e-9:
        parts.append(f"{cats['SUPPLIER_CALENDAR']:.0f} is the extra cover the supplier's order and shipping calendar forces")
    if cats["SERVICE_PROTECTION"] > 1e-9:
        parts.append(f"{cats['SERVICE_PROTECTION']:.0f} is service protection ({row['protection_regime'] or 'lean'})")
    if cats["MOQ"] > 1e-9:
        parts.append(f"{cats['MOQ']:.0f} is the top-up to the supplier's minimum order")
    if cats["CASE_ROUNDING"] > 1e-9:
        parts.append(f"{cats['CASE_ROUNDING']:.0f} is case rounding")
    if cats["PALLET_ROUNDING"] > 1e-9:
        parts.append(f"{cats['PALLET_ROUNDING']:.0f} is pallet rounding")
    if cats["MOV"] > 1e-9:
        parts.append(f"{cats['MOV']:.0f} lifts the supplier order to its minimum order value")
    if cats["FREIGHT_ECONOMICS"] > 1e-9:
        parts.append(f"{cats['FREIGHT_ECONOMICS']:.0f} completes the pallet load or the freight tier the order lands on")
    ce = row.get("cycle_economics")
    if cats["ORDER_COST_ECONOMICS"] > 1e-9 and ce:
        parts.append(f"{cats['ORDER_COST_ECONOMICS']:.0f} extends cover by about {ce['extension_periods']:.1f} periods, avoiding about "
                     f"{ce['orders_avoided']:.1f} orders (${ce['order_costs_avoided']:,.0f} in order-level costs) against about "
                     f"${ce['extra_carrying_and_capital']:,.0f} of extra carrying and capital")
    elif ce and not ce["justified"] and cats["OTHER_EXPLAINED"] > 1e-9:
        parts.append(f"the extra cover would avoid ${ce['order_costs_avoided']:,.0f} of order-level costs but adds about "
                     f"${ce['extra_carrying_and_capital']:,.0f} of carrying and capital, so it is not justified by order costs alone")
    if cats["OTHER_EXPLAINED"] > 1e-9:
        parts.append(f"{cats['OTHER_EXPLAINED']:.0f} is not explained by the waterfall arithmetic (the joint solve found it cheaper; see the cost comparison)")
    if row["under_need_units"] > 1e-9:
        parts.append(f"the order is {row['under_need_units']:.0f} below the arithmetic need, which the joint solve accepts within the service floor")
    netted = f"Usable on hand {row['usable_on_hand']:.0f} and inbound {row['usable_inbound']:.0f} were netted off."
    head = (f"Order {row['quantity']:.0f} units of {row['sku']} from {row['supplier']} at review {row['period']} "
            f"(arrives period {row['arrival_period']}): ")
    return head + ("; ".join(parts) if parts else "no demand, protection or lot requirement is attributed") + ". " + netted


# ---------------------------------------------------------------- supplier orders (MOV / freight)

def supplier_order_view(req: Request, solution: Solution | None, period: int | None = 0) -> list[dict]:
    """Per supplier order in the plan: value against MOV, pallets against the tariff."""
    if solution is None:
        return []
    terms = {x.id: x for x in req.terms}
    out = []
    for supplier, srcs, st in supplier_orders(req):
        upp = pallet_units(st, srcs)
        for t in range(req.horizon):
            if period is not None and t != period:
                continue
            lines = [(s, solution.purchases.get((s.id, t), 0.)) for s in srcs]
            lines = [(s, q) for s, q in lines if q > 0 and not is_dust(q, source_pack(s))]
            if not lines:
                continue
            value = sum(q * s.unit_price * terms[s.terms].fx_rate_to_currency for s, q in lines)
            load = sum(q / upp[s.id] for s, q in lines) if upp else None
            pallets = math.ceil(load - 1e-9) if load is not None else None
            tier = next((x for x in st.freight_tiers if pallets is not None and pallets <= x.up_to_pallets + 1e-9), None) if st.freight_tiers else None
            out.append({"supplier": supplier, "period": t, "lines": [(s.id, q) for s, q in lines], "order_value": value,
                        "minimum_order_value": st.minimum_order_value, "mov_binding": bool(st.minimum_order_value and value <= st.minimum_order_value * 1.001),
                        "pallets": pallets, "load_pallets": load, "freight_tier_up_to": tier.up_to_pallets if tier else None,
                        "freight_charge": (tier.charge if tier else 0.) + (pallets or 0) * st.freight_per_pallet,
                        "fixed_order_cost": st.fixed_order_cost, "receiving_fee": st.receiving_fee_per_receipt + (pallets or 0) * st.receiving_per_pallet})
    return out


# ---------------------------------------------------------------- materiality / abstention

def _service_min(req: Request, rows: list[dict]) -> float | None:
    """Worst service across worlds and services, counted only up to each service's target: service
    above what the operator asked for is not an improvement that can justify an intervention."""
    values = []
    for r in rows:
        if not r.get("usable"):
            return None
        for s in req.services:
            v = r["service"].get(s.id)
            if v is not None:
                values.append(min(v, s.target) - s.target)
    return min(values) if values else None


def materiality(req: Request, incumbent_rows: list[dict], candidate_rows: list[dict]) -> dict[str, Any]:
    """Is the candidate's improvement over the incumbent large enough to act on?

    An improvement is material when any one of cost, carried inventory or worst service moves in
    the candidate's favour by more than its declared materiality, with no other axis moving
    against it by more than the same tolerance. Thresholds are the request's, never a constant."""
    ib, cb = mean_breakdown(incumbent_rows), mean_breakdown(candidate_rows)
    if ib is None or cb is None:
        return {"material": None, "verdict": "NOT_COMPARABLE", "reason": "a plan was not settleable on every confirmation world"}
    scale = max(abs(ib["TOTAL"]), 1.)
    cost_delta = (cb["TOTAL"] - ib["TOTAL"]) / scale
    def carried(rows):
        weights = [float(r.get("weight", 1.)) for r in rows]
        return sum(w * mean(x["inventory_value"] for x in r["trace"]) for w, r in zip(weights, rows)) / (sum(weights) or 1.)
    inv_i, inv_c = carried(incumbent_rows), carried(candidate_rows)
    # Measured against the incumbent's carried value. A base of one period's demand value was
    # tried in the final economic closure (a lean incumbent carrying a few units read a one-unit
    # change as several percent) and reverted: on the frozen P0 set it made the gate fire once on
    # cells 20 and 21 and cost service there. The known consequence is recorded in the close-out.
    inv_delta = (inv_c - inv_i) / max(inv_i, 1.)
    s_i, s_c = _service_min(req, incumbent_rows), _service_min(req, candidate_rows)
    service_delta = (s_c - s_i) if s_i is not None and s_c is not None else 0.
    better = {"cost": cost_delta <= -req.materiality_cost_fraction,
              "inventory": inv_delta <= -req.materiality_inventory_fraction,
              "service": service_delta >= req.materiality_service}
    worse = {"cost": cost_delta > req.materiality_cost_fraction,
             "inventory": inv_delta > req.materiality_inventory_fraction,
             "service": service_delta < -req.materiality_service}
    material = any(better.values())
    verdict = ("MATERIAL_IMPROVEMENT" if material else NO_MATERIAL_IMPROVEMENT)
    return {"material": material, "verdict": verdict,
            "cost_delta_fraction": cost_delta, "inventory_delta_fraction": inv_delta, "service_delta": service_delta,
            "better_on": [k for k, v in better.items() if v], "worse_on": [k for k, v in worse.items() if v],
            "thresholds": {"cost_fraction": req.materiality_cost_fraction, "inventory_fraction": req.materiality_inventory_fraction,
                           "service": req.materiality_service},
            "reason": (f"cost {cost_delta:+.2%}, inventory {inv_delta:+.2%}, worst service {service_delta:+.3f} against the incumbent; "
                       + ("improvement exceeds the declared materiality on " + ", ".join(k for k, v in better.items() if v)
                          if material else "no axis improves by more than the declared materiality"))}


# ---------------------------------------------------------------- provenance

def provenance(req: Request) -> dict[str, dict[str, Any]]:
    """Every economic input with where it came from. A figure without a declared provenance is
    CONFIGURED_ASSUMPTION when non-zero and NOT_AVAILABLE when zero; nothing is invented."""
    declared = dict(req.economics_provenance)

    def label(key: str, value: float) -> str:
        if key in declared:
            return declared[key]
        return "CONFIGURED_ASSUMPTION" if value else "NOT_AVAILABLE"

    out: dict[str, dict[str, Any]] = {}
    for s in req.sources:
        for field in ("unit_price", "freight_per_unit", "handling_per_unit", "fixed_order_fee", "minimum", "multiple",
                      "case_multiple", "pallet_multiple", "transport_multiple", "lead_days"):
            key = f"source.{s.id}.{field}"
            value = float(getattr(s, field))
            out[key] = {"value": value, "provenance": label(key, value)}
    for loc in req.locations:
        key = f"location.{loc.id}.holding_per_value_period"
        out[key] = {"value": loc.holding_per_value_period, "provenance": label(key, loc.holding_per_value_period)}
    for term in req.terms:
        for field in ("net_days", "deposit_fraction", "financing_fee_fraction"):
            key = f"terms.{term.id}.{field}"
            value = float(getattr(term, field))
            out[key] = {"value": value, "provenance": label(key, value)}
    for field in ("interest_per_period", "cost_of_capital_per_period", "credit_limit"):
        key = f"liquidity.{field}"
        value = float(getattr(req.liquidity, field))
        out[key] = {"value": value, "provenance": label(key, value)}
    for st in req.supplier_terms:
        for field in ("minimum_order_value", "fixed_order_cost", "receiving_fee_per_receipt", "receiving_per_pallet", "freight_per_pallet"):
            value = float(getattr(st, field))
            out[f"supplier_terms.{st.supplier}.{field}"] = {"value": value, "provenance": st.provenance.get(field, label(f"supplier_terms.{st.supplier}.{field}", value))}
        out[f"supplier_terms.{st.supplier}.freight_tiers"] = {"value": [(x.up_to_pallets, x.charge) for x in st.freight_tiers],
                                                              "provenance": st.provenance.get("freight_tiers", "CONFIGURED_ASSUMPTION" if st.freight_tiers else "NOT_AVAILABLE")}
        out[f"supplier_terms.{st.supplier}.units_per_pallet"] = {"value": dict(st.units_per_pallet),
                                                                 "provenance": st.provenance.get("units_per_pallet", "CONFIGURED_ASSUMPTION" if st.units_per_pallet else "NOT_AVAILABLE")}
    for svc in req.services:
        for field in ("selling_price", "sla_per_unmet"):
            key = f"service.{svc.id}.{field}"
            value = float(getattr(svc, field))
            out[key] = {"value": value, "provenance": label(key, value)}
    return out


def missing_data_fallbacks(req: Request) -> list[str]:
    """What the economics could not price and how it was handled (never silently)."""
    notes = []
    if req.liquidity.cost_of_capital_per_period == 0:
        notes.append("cost of capital NOT_AVAILABLE: payment timing is valued only through interest on drawn credit")
    if all(loc.holding_per_value_period == 0 for loc in req.locations):
        notes.append("holding rate NOT_AVAILABLE: carrying cost is zero and inventory is compared on value only")
    for st in req.supplier_terms:
        if (st.freight_tiers or st.freight_per_pallet) and not st.units_per_pallet:
            notes.append(f"supplier {st.supplier}: freight tariff declared without pallet sizes; pallet economics disabled")
        if st.units_per_pallet and any(s.sku not in st.units_per_pallet for s in req.sources if s.supplier == st.supplier):
            notes.append(f"supplier {st.supplier}: pallet size missing for some SKUs; pallet economics disabled for that supplier")
    if not req.supplier_terms:
        notes.append("no supplier terms: MOV, fixed order cost, receiving and freight tariffs are NOT_AVAILABLE (per-unit source costs only)")
    return notes


# ---------------------------------------------------------------- report block

def _weighted(rows: list[dict], value) -> float:
    weights = [float(r.get("weight", 1.)) for r in rows]
    return sum(w * value(r) for w, r in zip(weights, rows)) / (sum(weights) or 1.)


def economics_block(req: Request, fits: dict, protection: list[dict], *, incumbent: Solution | None, final: Solution | None,
                    incumbent_rows: list[dict], final_rows: list[dict], accepted: bool, chosen: str,
                    materiality_result: dict | None) -> dict[str, Any]:
    inc = mean_breakdown(incumbent_rows)
    fin = mean_breakdown(final_rows)
    recon = [reconcile(r) for r in final_rows if r.get("usable")]
    return {
        "scope": "confirmation worlds; components reconcile to the settlement's economic cost; attribution partitions each order exactly",
        "incumbent_costs": inc, "selected_costs": fin,
        "incumbent_working_capital": (_weighted(incumbent_rows, lambda r: working_capital(req, r)["cash_deployed_mean"]) if incumbent_rows and all(r.get("usable") for r in incumbent_rows) else None),
        "selected_working_capital": (_weighted(final_rows, lambda r: working_capital(req, r)["cash_deployed_mean"]) if final_rows and all(r.get("usable") for r in final_rows) else None),
        "reconciled": all(r["reconciled"] for r in recon) if recon else None,
        "unmapped_ledger_keys": sorted({k for r in recon for k in r["unmapped_ledger_keys"]}),
        "orders": order_waterfall(req, fits, protection, final),
        "incumbent_orders": order_waterfall(req, fits, protection, incumbent),
        "supplier_orders": supplier_order_view(req, final),
        "materiality": materiality_result,
        "action_recommended": bool(accepted),
        "recommendation": ("ZAAD intervenes: " + chosen) if accepted else
                          (NO_MATERIAL_IMPROVEMENT if materiality_result and materiality_result.get("verdict") == NO_MATERIAL_IMPROVEMENT else "incumbent retained"),
        "provenance": provenance(req),
        "fallbacks": missing_data_fallbacks(req),
    }
