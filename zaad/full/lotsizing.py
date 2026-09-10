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

from zaad.full.contracts import Request, Source
from zaad.full.model import pallet_units


def _tier_charge(st, pallets: float) -> float:
    if not st.freight_tiers:
        return 0.
    for tier in st.freight_tiers:
        if pallets <= tier.up_to_pallets + 1e-9:
            return tier.charge
    return st.freight_tiers[-1].charge


def echelon_demand(req: Request, mu: dict[tuple[str, str], float]) -> dict[tuple[str, str], float]:
    """Demand each (SKU, location) ultimately serves: its own plus that of every location its approved
    lanes feed, transitively (P2). A source delivering to a central DC without customers of its own
    still buys for the branches the DC feeds, so its economic lot is sized on that demand. Without
    lanes this is `mu` unchanged."""
    out: dict[tuple[str, str], float] = defaultdict(float, mu)
    if not any(a.approved for a in req.transfers):
        return out
    downstream: dict[tuple[str, str], set[str]] = defaultdict(set)
    for arc in req.transfers:
        if arc.approved:
            downstream[arc.sku, arc.origin].add(arc.destination)
    for (sku, origin), dests in downstream.items():
        seen: set[str] = set()
        frontier = list(dests)
        while frontier:
            dest = frontier.pop()
            if dest in seen or dest == origin:
                continue
            seen.add(dest)
            frontier.extend(downstream.get((sku, dest), ()))
        out[sku, origin] = mu.get((sku, origin), 0.) + sum(mu.get((sku, d), 0.) for d in seen)
    return out


def reference_lots(req: Request, fits: dict) -> dict[str, dict]:
    """Per supplier: the economic lot the operator would buy from it and the order-level cost per
    unit of that lot. Lot = min(load limit, max(EOQ on the supplier's fixed costs, minimum order
    quantities, minimum order value, one period of demand)); premium = (fixed order cost + shipment
    tariff at that load + receiving) / lot. Suppliers with no order-level economics get premium 0."""
    locs = {loc.id: loc for loc in req.locations}
    terms = {x.id: x for x in req.terms}
    mu: dict[tuple[str, str], float] = defaultdict(float)
    for s in req.services:
        mu[s.sku, s.location] += float(fits[s.id]["mean"])
    mu = echelon_demand(req, mu)
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


def _continuation_sources(req: Request, mu: dict) -> list[tuple[tuple[str, str], Source]]:
    """(SKU, location) pairs that carry continuation slabs, each with the source whose supplier lot
    sets the cycle: a source destination keeps the first source declared for it (the frozen P1 rule,
    unchanged); a served location that buys nothing itself - a transfer-fed branch (P2) - uses the
    cheapest approved source of the SKU anywhere in the network, since that is the purchase its
    residual lets the operator avoid. Order: source destinations in declaration order, then the
    other served locations sorted."""
    out: list[tuple[tuple[str, str], Source]] = []
    seen: set[tuple[str, str]] = set()
    for source in req.sources:
        key = (source.sku, source.destination)
        if key not in seen:
            seen.add(key)
            out.append((key, source))
    cheapest: dict[str, Source] = {}
    for source in sorted(req.sources, key=lambda s: (s.unit_price + s.freight_per_unit + s.handling_per_unit, s.id)):
        if source.approved and source.compliance == "cleared":
            cheapest.setdefault(source.sku, source)
    for key in sorted(mu):
        if key not in seen and mu[key] > 0 and key[0] in cheapest:
            seen.add(key)
            out.append((key, cheapest[key[0]]))
    return out


def terminal_terms(req: Request, fits: dict) -> dict[tuple[str, str], tuple[float, float]]:
    """Solve terms for `model.solve(continuation=...)`: per SKU / location, the units of end-of-plan
    supply that may earn the landed margin (this line's share of one reference lot) and the margin per
    unit: landed cost less salvage less the carrying and cost of capital over half the lot's consumption
    time, floored at zero. Above one lot the residual earns salvage, as before."""
    skus = {s.id: s for s in req.skus}
    locs = {loc.id: loc for loc in req.locations}
    lots = reference_lots(req, fits)
    landed = landed_unit_costs(req, fits)
    mu: dict[tuple[str, str], float] = defaultdict(float)
    for s in req.services:
        mu[s.sku, s.location] += float(fits[s.id]["mean"])
    out: dict[tuple[str, str], tuple[float, float]] = {}
    for key, source in _continuation_sources(req, mu):
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
        rate = locs[key[1]].holding_per_value_period + req.liquidity.cost_of_capital_per_period
        margin = landed[source.sku] - sku.terminal_value - sku.asset_value * rate * tau
        if units > 0 and margin > 0:
            out[key] = (float(units), float(margin))
    return out


def steady_state_unit_costs(req: Request, fits: dict) -> dict[str, float]:
    """Per SKU: the long-run average cost of one RECEIVED unit of demand under the economic lot, c* / mu:
    the replacement cost of a received unit (price, per-unit freight and handling, and the order and
    shipment cost per unit of one reference lot, each divided by the source's declared fill ratio,
    because the ledger charges an order on the ordered quantity and stock receives the filled part) plus
    the holding and cost of capital that unit would incur while it waits its turn in a steady-state lot,
    on average half the lot's consumption time. It is what a unit still on hand at the end of a plan
    lets the operator avoid buying, ordering and holding later. (The pass-J `landed_unit_costs` basis is
    kept as recorded: per ordered unit, no fill correction.)"""
    skus = {s.id: s for s in req.skus}
    locs = {loc.id: loc for loc in req.locations}
    terms = {x.id: x for x in req.terms}
    lots = reference_lots(req, fits)
    out: dict[str, float] = {}
    for source in sorted(req.sources, key=lambda s: (s.unit_price + s.freight_per_unit + s.handling_per_unit, s.id)):
        if not (source.approved and source.compliance == "cleared") or source.sku in out:
            continue
        lot = lots.get(source.supplier)
        fill = max(float(source.fill_mean), 1e-6)
        premium = lot["premium_per_unit"] if lot else 0.
        replacement = (source.unit_price * terms[source.terms].fx_rate_to_currency + source.freight_per_unit + source.handling_per_unit + premium) / fill
        rate = locs[source.destination].holding_per_value_period + req.liquidity.cost_of_capital_per_period
        tau = (lot["lot_units"] * fill / (2. * lot["demand_per_period"])) if lot and lot["demand_per_period"] > 0 else .5
        out[source.sku] = replacement + skus[source.sku].asset_value * rate * tau
    return out


def economic_cycle(req: Request, fits: dict) -> dict[str, dict]:
    """Per supplier: the reference lot, the demand it serves per period and the cycle length in periods
    (lot / demand), for reporting and for the continuation's period slabs."""
    return {supplier: {"lot_units": lot["lot_units"], "demand_per_period": lot["demand_per_period"],
                       "cycle_periods": lot["lot_units"] / lot["demand_per_period"] if lot["demand_per_period"] > 0 else None}
            for supplier, lot in reference_lots(req, fits).items()}


def cycle_continuation_terms(req: Request, fits: dict) -> dict[tuple[str, str], list[tuple[float, float]]]:
    """Solve terms for `model.solve(continuation=...)`, the steady-state relative value of end-of-plan
    stock (P1 final closure). Per SKU / location, one slab per post-window period j = 0, 1, ... up to one
    economic cycle: the units the fitted demand consumes in that period (mu) and the margin above
    salvage each of them earns, c* / mu less the holding and cost of capital it incurs itself until that
    period, (j + 1/2) periods after the plan ends. The solver fills the highest-margin slabs first, so
    the credit is concave in the residual: the k-th residual unit is worth c* / mu - rate * price * k / mu,
    which falls to the purchase price at exactly one economic lot and to salvage far beyond it. Slabs
    with a non-positive margin are dropped; beyond one cycle the residual earns salvage, as before."""
    skus = {s.id: s for s in req.skus}
    locs = {loc.id: loc for loc in req.locations}
    lots = reference_lots(req, fits)
    unit_cost = steady_state_unit_costs(req, fits)
    mu: dict[tuple[str, str], float] = defaultdict(float)
    for s in req.services:
        mu[s.sku, s.location] += float(fits[s.id]["mean"])
    out: dict[tuple[str, str], list[tuple[float, float]]] = {}
    for key, source in _continuation_sources(req, mu):
        if key in out or mu[key] <= 0 or source.sku not in unit_cost:
            continue
        lot = lots.get(source.supplier)
        periods = max(1, math.ceil(lot["lot_units"] / lot["demand_per_period"])) if lot and lot["demand_per_period"] > 0 else 1
        sku = skus[source.sku]
        # stock bought in the window expires shelf_life periods after arrival: a unit landed in period
        # 0 cannot serve a post-window period at or beyond shelf_life - horizon, so no slab is credited
        # there (the selection rows apply each lot's own expiry; this is the solve-side bound)
        periods = min(periods, max(0, int(sku.shelf_life) - int(req.horizon)))
        rate = locs[key[1]].holding_per_value_period + req.liquidity.cost_of_capital_per_period
        slabs = []
        for j in range(periods):
            margin = unit_cost[source.sku] - sku.terminal_value - sku.asset_value * rate * (j + .5)
            if margin <= 0:
                break
            slabs.append((float(mu[key]), float(margin)))
        if slabs:
            out[key] = slabs
    return out


def continuation_feeds(req: Request, fits: dict) -> dict[tuple[str, str], list[dict]]:
    """Post-window outlets for the residual stock of an origin that serves no customers of its own (P2
    network continuation). Per SKU / origin with no fitted demand and approved lanes to locations that
    carry continuation slabs: the fed locations, each with its lane lead (periods) and cost per unit.
    The model lets origin residual earn a fed location's slab margin less the lane cost, from slab
    `lead` onward, SHARING that location's post-window demand with the location's own residual, so no
    unit of post-window demand is credited twice. A single-location request, or an origin with its own
    customers, yields nothing here and the frozen continuation is unchanged."""
    mu: dict[tuple[str, str], float] = defaultdict(float)
    for s in req.services:
        mu[s.sku, s.location] += float(fits[s.id]["mean"])
    slabs = cycle_continuation_terms(req, fits) if req.terminal_economic_basis == "cycle" else {k: [v] for k, v in terminal_terms(req, fits).items()}
    out: dict[tuple[str, str], list[dict]] = {}
    for arc in sorted(req.transfers, key=lambda a: (a.lead_periods, a.cost_per_unit, a.id)):
        if not arc.approved or mu.get((arc.sku, arc.origin), 0.) > 0 or (arc.sku, arc.destination) not in slabs:
            continue
        feeds = out.setdefault((arc.sku, arc.origin), [])
        if any(f["branch"] == arc.destination for f in feeds):
            continue          # the fastest, then cheapest, lane to each fed location
        feeds.append({"branch": arc.destination, "lead": int(arc.lead_periods), "cost": float(arc.cost_per_unit)})
    return out


def continuation_caps(req: Request, fits: dict) -> dict[str, float]:
    """Per SKU: the residual units the continuation credits above salvage, one economic cycle of the
    SKU's share of the supplier's demand (the same bound the solve's slabs carry)."""
    lots = reference_lots(req, fits)
    mu: dict[str, float] = defaultdict(float)
    for s in req.services:
        mu[s.sku] += float(fits[s.id]["mean"])
    caps: dict[str, float] = {}
    for source in req.sources:
        if source.sku in caps or not (source.approved and source.compliance == "cleared"):
            continue
        lot = lots.get(source.supplier)
        if lot and lot["demand_per_period"] > 0 and mu[source.sku] > 0:
            caps[source.sku] = lot["lot_units"] * mu[source.sku] / lot["demand_per_period"]
        else:
            caps[source.sku] = mu[source.sku]
    return caps
