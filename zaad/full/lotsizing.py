"""Ex-ante landed cost of one economic lot, and the P1 terminal valuation derived from it.

Why (P1 benchmark / horizon closure pass, J12). A finite-horizon purchasing plan needs the same number
of shipments inside its window whatever the lot pattern, so the objective is nearly flat in the size of
the first order; with end-of-plan stock credited at the declared salvage the cheapest plan defers the
large lot and covers the gap with a small one, and a rolling operator only ever executes the small one.
On the declared fair benchmark that costs 6-7% against a full-load EOQ buyer on I, G and T. The
correction is the benchmark's own terminal rule applied ex ante: a unit still on hand, or committed and
arriving, at the end of the plan avoids buying that unit later at its LANDED cost (unit price plus the
fixed order, shipment-tariff and receiving cost per unit of one economic lot), less the carrying and
cost of capital until it is consumed, never below salvage. Applied only where the P1 purchasing planner
owns the review (`zaad/full/ownership.py`); a P0-owned review keeps the frozen objective.

Everything here is derived from the declared economics at the review: the supplier's terms, the source's
price and lot rules, the location's holding rate, the declared cost of capital and the fitted mean
demand. There is no fixture constant.
"""
from __future__ import annotations

import math
from collections import defaultdict

from zaad.full.contracts import Request
from zaad.full.model import pallet_units, supplier_orders


def _tier_charge(st, pallets: float) -> float:
    if not st.freight_tiers:
        return 0.
    for tier in st.freight_tiers:
        if pallets <= tier.up_to_pallets + 1e-9:
            return tier.charge
    return st.freight_tiers[-1].charge


def reference_lots(req: Request, fits: dict) -> dict[str, dict]:
    """Per supplier: the economic lot the operator would buy from it and the order-level cost per
    unit of that lot. Lot = min(load limit, max(EOQ on the supplier's fixed costs, minimum order
    quantities, minimum order value, one period of demand)); premium = (fixed order cost + shipment
    tariff at that load + receiving) / lot. Suppliers with no order-level economics get premium 0."""
    skus = {s.id: s for s in req.skus}
    locs = {l.id: l for l in req.locations}
    terms = {x.id: x for x in req.terms}
    mu: dict[tuple[str, str], float] = defaultdict(float)
    for s in req.services:
        mu[s.sku, s.location] += float(fits[s.id]["mean"])
    declared = {st.supplier: st for st in req.supplier_terms}
    by_supplier: dict[str, list] = defaultdict(list)
    for source in req.sources:
        if source.approved and source.compliance == "cleared":
            by_supplier[source.supplier].append(source)
    out: dict[str, dict] = {}
    for supplier, srcs in by_supplier.items():
        st = declared.get(supplier)
        lines = [s for s in srcs if mu[s.sku, s.destination] > 0]
        if not lines:
            continue
        demand = sum(mu[s.sku, s.destination] for s in lines)
        price_of = {s.id: s.unit_price * terms[s.terms].fx_rate_to_currency for s in lines}
        # weighted holding per unit-period across the supplier's lines
        holding = sum(mu[s.sku, s.destination] * price_of[s.id] * (locs[s.destination].holding_per_value_period + req.liquidity.cost_of_capital_per_period) for s in lines) / demand
        fixed = (st.fixed_order_cost if st else 0.) + max(s.fixed_order_fee for s in lines)
        upp = pallet_units(st, lines) if st else None
        top = None
        if st and upp:
            top = st.max_pallets if st.max_pallets is not None else (st.freight_tiers[-1].up_to_pallets if st.freight_tiers else None)
        cap = top * min(upp.values()) if (top and upp) else float("inf")
        eoq = math.sqrt(2. * fixed * demand / holding) if fixed > 0 and holding > 0 else 0.
        moq = max(s.minimum for s in lines)
        mov_units = (st.minimum_order_value / min(price_of.values())) if (st and st.minimum_order_value) else 0.
        lot = min(cap, max(eoq, moq, mov_units, demand))
        pallets = (sum((lot * mu[s.sku, s.destination] / demand) / upp[s.id] for s in lines) if upp else 0.)
        tariff = 0.
        if st:
            tariff = _tier_charge(st, pallets) + st.freight_per_pallet * pallets + st.receiving_fee_per_receipt + st.receiving_per_pallet * pallets
        premium = (fixed + tariff) / lot if lot > 0 else 0.
        out[supplier] = {"lot_units": lot, "premium_per_unit": premium, "eoq": eoq, "load_cap_units": cap if cap < float("inf") else None,
                         "fixed_per_order": fixed, "tariff_at_lot": tariff, "pallets_at_lot": pallets, "demand_per_period": demand,
                         "lines": [s.id for s in lines]}
    return out


def landed_unit_costs(req: Request, fits: dict) -> dict[str, float]:
    """Per SKU: the landed unit cost of a purchase from its cheapest approved source, unit price plus
    per-unit freight and handling plus the reference-lot premium of that source's supplier."""
    lots = reference_lots(req, fits)
    terms = {x.id: x for x in req.terms}
    landed: dict[str, float] = {}
    for source in sorted(req.sources, key=lambda s: (s.unit_price + s.freight_per_unit + s.handling_per_unit, s.id)):
        if not (source.approved and source.compliance == "cleared") or source.sku in landed:
            continue
        premium = lots.get(source.supplier, {}).get("premium_per_unit", 0.)
        landed[source.sku] = source.unit_price * terms[source.terms].fx_rate_to_currency + source.freight_per_unit + source.handling_per_unit + premium
    return landed


def terminal_terms(req: Request, fits: dict) -> dict[tuple[str, str], tuple[float, float]]:
    """Solve terms for `model.solve(continuation=...)`: per SKU / location, the units of end-of-plan
    supply that may earn the landed margin (this line's share of one reference lot) and the margin per
    unit: landed cost less salvage less the carrying and cost of capital over half the lot's consumption
    time, floored at zero. Above one lot the residual earns salvage, as before."""
    skus = {s.id: s for s in req.skus}
    locs = {l.id: l for l in req.locations}
    lots = reference_lots(req, fits)
    landed = landed_unit_costs(req, fits)
    mu: dict[tuple[str, str], float] = defaultdict(float)
    for s in req.services:
        mu[s.sku, s.location] += float(fits[s.id]["mean"])
    out: dict[tuple[str, str], tuple[float, float]] = {}
    for source in req.sources:
        key = (source.sku, source.destination)
        if key in out or mu[key] <= 0 or source.sku not in landed:
            continue
        lot = lots.get(source.supplier)
        if lot is None:
            units = mu[key]
            tau = .5
        else:
            units = lot["lot_units"] * mu[key] / lot["demand_per_period"]
            tau = lot["lot_units"] / (2. * lot["demand_per_period"])
        sku = skus[source.sku]
        rate = locs[source.destination].holding_per_value_period + req.liquidity.cost_of_capital_per_period
        margin = landed[source.sku] - sku.terminal_value - sku.asset_value * rate * tau
        if units > 0 and margin > 0:
            out[key] = (float(units), float(margin))
    return out
