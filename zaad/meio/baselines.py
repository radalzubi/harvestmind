"""P2 network comparators and the declared incumbent network policy.

Three competent network policies, each projected deterministically over the horizon from the same
snapshot the optimizer sees and executed through the frozen common model (`fixed=`), so the same
physics validates them:

  network:rop   INCUMBENT NETWORK POLICY (Baseline C). Every transfer-fed branch runs a continuous
                -review reorder point on its local position: when the position after this period's
                demand falls to demand over the lane lead plus quantile protection, it requests a
                refill to its local base stock (demand over lead + one review, plus protection),
                rounded to the lane pack and capped by lane capacity. The origin allocates what it
                physically holds by customer priority, proportionally among equal priorities. The
                buying location replenishes its ECHELON position (own stock + fed-branch stock +
                everything in transit) with the frozen `reorder_point` / `economic_lot` arithmetic on
                the echelon demand, lot rounded, MOV / load / cash capped like every P1 rule.
  network:pool  SIMPLE CENTRAL POOL (Baseline B). The same, except branches are refilled to their
                local base stock every period (order-up-to, no reorder point), so central stock is
                pooled and pushed as demand consumes it; allocation proportional to request.

  independent branches (Baseline A) is not a rule: it is the frozen optimizer itself run on each
  branch as an isolated single-node problem (`independent_branch_requests`); the benchmark runner
  replays those and sums them, which is exactly a decentralised network with no pooling.

None of these is ZAAD. ZAAD's network decision is the frozen joint solve; these are what it is
measured against, and `network:rop` is the incumbent it must beat or abstain from.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
import math

from zaad.full.contracts import Request, Transfer
from zaad.full.model import Solution, supplier_orders
from zaad.full.policies import _keep_amendments, _z, apply_cash_cap, apply_load_cap, apply_mov, lot_round
from zaad.full.worlds import dates, draw, forecast_all
from zaad.meio.topology import lane_arrival
from zaad.sectors.contracts import resolve as sector_physics
from zaad.sourcing.contracts import resolve as sourcing_view
from zaad.sourcing.incumbent import fit_resources, split_projection


def _round_to(q: float, multiple: float, up: bool) -> float:
    if multiple <= 0 or q <= 0:
        return max(0., q)
    packs = q / multiple
    packs = math.ceil(packs - 1e-9) if up else math.floor(packs + 1e-9)
    return max(0., packs * multiple)


def _apply_weight_cap(req: Request, purchases: dict[tuple[str, int], float], physics) -> None:
    """Sector physics: cap each supplier order at the supplier's maximum shipment weight, scaling the
    lines down and rounding to the pack below (the load-cap rule, on weight)."""
    if physics is None:
        return
    for supplier, srcs, st in supplier_orders(req):
        if st.max_shipment_weight is None:
            continue
        for t in range(req.horizon):
            lines = [s for s in srcs if purchases.get((s.id, t), 0.) > 0]
            weight = sum(purchases[s.id, t] * float(physics.weight(s.sku) or 0.) for s in lines)
            if weight <= st.max_shipment_weight + 1e-9:
                continue
            scale = st.max_shipment_weight / weight
            for s in lines:
                q = purchases[s.id, t] * scale
                for pack in (s.multiple, s.case_multiple, s.pallet_multiple, s.transport_multiple):
                    if pack > 0:
                        q = _round_to(q, pack, up=False)
                purchases[s.id, t] = q


def network_rule_plan(req: Request, rule: str) -> Solution:
    kind = rule.partition(":")[2]
    if kind not in {"rop", "pool"}:
        raise ValueError(f"unknown network policy {rule!r}")
    fits = forecast_all(req)
    customers = {c.id: c for c in req.customers}
    skus = {s.id: s for s in req.skus}
    sources = {s.id: s for s in req.sources}
    H = req.horizon
    # the projection lands supply exactly where the mean world lands it (fitted supply profiles, ETA
    # evidence, signals), so the incumbent solve that pins these transfers sees the stock they need
    mean_world = draw(req, req.seed, 1, deterministic=True)[0]
    # Sector physics (hard feasibility only): the operator's own rule cannot ship a state on a lane or
    # into a location that cannot carry it, receive below the minimum life, or ignore the age at
    # receipt. It stays naive about sellable life - it counts physical units - which is the point of
    # comparing ZAAD against it. None on a legacy request.
    physics = sector_physics(req)
    sourcing = sourcing_view(req)   # incumbent source mix (P3); None on a frozen request
    resource_used: dict[tuple[str, int], float] = {}   # P3: shared resource volume booked by earlier lines, per period

    def lane_legal(arc: Transfer) -> bool:
        return physics is None or (physics.lane_ok(arc.sku, arc.id) and physics.location_ok(arc.sku, arc.destination))

    def receivable(sku: str, expiry: int, arrive: int) -> bool:
        return expiry > arrive and (physics is None or physics.receivable(sku, expiry, arrive))

    def receipt_life(src) -> int:
        return int(skus[src.sku].shelf_life) if physics is None else physics.receipt_life(src.sku, src.id)
    # demand statistics per (sku, location)
    mu: dict[tuple[str, str], float] = defaultdict(float)
    var: dict[tuple[str, str], float] = defaultdict(float)
    target: dict[tuple[str, str], float] = defaultdict(float)
    priority: dict[tuple[str, str], float] = defaultdict(float)
    for s in req.services:
        key = (s.sku, s.location)
        mu[key] += float(fits[s.id]["mean"])
        var[key] += float(fits[s.id].get("sd", 0.)) ** 2
        target[key] = max(target[key], s.target)
        priority[key] = max(priority[key], customers[s.customer].priority)
    # feeders: the fastest approved lane into every fed (sku, destination) whose origin buys or is stocked
    buyers = {(s.sku, s.destination) for s in req.sources if s.approved and s.compliance == "cleared"
              and (physics is None or (physics.location_ok(s.sku, s.destination) and receipt_life(s) > physics.min_receipt(s.sku)))}
    feeder: dict[tuple[str, str], Transfer] = {}
    for arc in sorted(req.transfers, key=lambda a: (lane_arrival(req, a, 0), -a.capacity, a.id)):
        if arc.approved and lane_legal(arc) and (arc.sku, arc.destination) not in buyers:
            feeder.setdefault((arc.sku, arc.destination), arc)
    fed_by_origin: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
    for (sku, dest), arc in feeder.items():
        fed_by_origin[sku, arc.origin].append((sku, dest))
    # cohort state: (sku, location) -> {expiry: units}; pending arrivals (sku, location, expiry, due, units)
    cohorts: dict[tuple[str, str], dict[int, float]] = defaultdict(lambda: defaultdict(float))
    for lot in req.stock:
        if lot.usable > 0 and lot.expires_in > 0:
            cohorts[lot.sku, lot.location][lot.expires_in] += lot.usable
    pending: list[tuple[str, str, int, int, float]] = []
    for po in req.pipeline:
        src = sources[po.source]
        if po.remaining <= 0:
            continue
        due = max(1, int(mean_world.po_due.get(po.id, next(o.due_in for o in po.options if o.action == "keep"))))
        pending.append((src.sku, src.destination, due + skus[src.sku].shelf_life, due, po.expected_accepted_remaining * float(mean_world.po_fill.get(po.id, 1.)) / max(po.expected_accepted_remaining / po.remaining, 1e-9) if po.remaining > 0 else 0.))
    for row in req.inbound_transfers:
        pending.append((row.sku, row.destination, row.expires_in, row.due_in, row.accepted_quantity))
    purchases: dict[tuple[str, int], float] = {}
    transfers: dict[tuple[str, int, int], float] = defaultdict(float)
    order_costs = {supplier: st.fixed_order_cost for supplier, _, st in supplier_orders(req)}
    locations = {loc.id: loc for loc in req.locations}

    def position(sku: str, location: str, t: int, include_transit: bool = True) -> float:
        on_hand = sum(q for e, q in cohorts[sku, location].items() if e > t)
        transit = sum(q for k, loc, _, due, q in pending if k == sku and loc == location and due > t) if include_transit else 0.
        return on_hand + transit

    for t in range(H):
        # land arrivals due now
        rest = []
        for sku, loc, expiry, due, q in pending:
            if due <= t:
                cohorts[sku, loc][expiry] += q
            else:
                rest.append((sku, loc, expiry, due, q))
        pending = rest
        # 1. branch requests and origin allocation
        requests: dict[tuple[str, str], list[tuple[float, tuple[str, str], float]]] = defaultdict(list)
        for (sku, dest), arc in feeder.items():
            m = mu[sku, dest]
            if m <= 0:
                continue
            lead = max(1, lane_arrival(req, arc, t) - t)
            z = _z(target[sku, dest])
            sd = math.sqrt(var[sku, dest])
            base = m * (lead + 1) + z * sd * math.sqrt(lead + 1)
            rop = m * lead + z * sd * math.sqrt(lead)
            pos = position(sku, dest, t)
            if kind == "rop" and pos - m > rop + 1e-9:
                continue
            need = max(0., base - pos)
            if need <= 0:
                continue
            q = _round_to(need, arc.multiple, up=True)
            q = min(q, _round_to(arc.capacity, arc.multiple, up=False) if arc.multiple > 0 else arc.capacity)
            if q > 0:
                requests[sku, arc.origin].append((priority[sku, dest], (sku, dest), q))
        for (sku, origin), rows in requests.items():
            # what the origin can move now: cohorts that survive the lane
            by_priority: dict[float, list[tuple[tuple[str, str], float]]] = defaultdict(list)
            for prio, dest_key, q in rows:
                by_priority[prio].append((dest_key, q))
            for prio in sorted(by_priority, reverse=True):
                group = by_priority[prio]
                arcs = {dest_key: feeder[dest_key] for dest_key, _ in group}
                # available at the origin for this group: cohorts landing before expiry over the slowest lane
                available = 0.
                for e, units in cohorts[sku, origin].items():
                    if units > 0 and all(receivable(sku, e, lane_arrival(req, arcs[d], t)) for d, _ in group):
                        available += units
                total = sum(q for _, q in group)
                share = {d: (q if total <= available + 1e-9 else q * available / total) for d, q in group}
                for dest_key, q in group:
                    lane = arcs[dest_key]
                    alloc = share[dest_key]
                    alloc = _round_to(alloc, lane.multiple, up=False) if lane.multiple > 0 else alloc
                    if alloc <= 0:
                        continue
                    arrive = lane_arrival(req, lane, t)
                    remaining = alloc
                    for e in sorted(cohorts[sku, origin]):
                        if remaining <= 1e-9:
                            break
                        if not receivable(sku, e, arrive) or cohorts[sku, origin][e] <= 0:
                            continue
                        take = min(remaining, cohorts[sku, origin][e])
                        cohorts[sku, origin][e] -= take
                        transfers[lane.id, e, t] += take
                        pending.append((sku, dest_key[1], e, arrive, take * (1 - lane.loss_fraction)))
                        remaining -= take
        # 2. echelon replenishment at every buying location
        for (sku, location) in sorted(buyers):
            downstream = fed_by_origin.get((sku, location), [])
            m = mu[sku, location] + sum(mu[d] for d in downstream)
            sd = math.sqrt(var[sku, location] + sum(var[d] for d in downstream))
            if m <= 0:
                continue
            options = [s for s in req.sources if s.sku == sku and s.destination == location and s.approved and s.compliance == "cleared"
                       and (physics is None or receipt_life(s) > physics.min_receipt(sku))]
            if not options:
                continue
            src = min(options, key=lambda s: (s.unit_price + s.freight_per_unit + s.handling_per_unit, s.id))
            z = _z(max([target[sku, location]] + [target[d] for d in downstream]))
            arrival = int(mean_world.arrival.get((src.id, t), dates(req, src, t)[1]))
            lead = arrival - t
            tail = max((lane_arrival(req, feeder[d], 0) for d in downstream), default=0)
            echelon_pos = position(sku, location, t) + sum(position(*d, t) for d in downstream)
            rop = m * (lead + tail) + z * sd * math.sqrt(max(1, lead + tail))
            if echelon_pos - m > rop + 1e-9:
                continue
            nxt = next((int(mean_world.arrival.get((src.id, u), dates(req, src, u)[1])) for u in range(t + 1, H) if int(mean_world.arrival.get((src.id, u), dates(req, src, u)[1])) > arrival), None)
            cover_to = nxt if nxt is not None else H
            need = m * (cover_to - t + tail) + z * sd * math.sqrt(max(1, cover_to - t + tail)) - echelon_pos
            holding = locations[location].holding_per_value_period * src.unit_price + req.liquidity.cost_of_capital_per_period * src.unit_price
            fixed = order_costs.get(src.supplier, 0.) + src.fixed_order_fee
            eoq = math.sqrt(2. * m * fixed / holding) if fixed > 0 and holding > 0 else 0.
            mix_sources = [s for s in options if s.id in (sourcing.incumbent_mix.get((sku, location), {}) if sourcing is not None else {})]
            if len(mix_sources) > 1:
                # incumbent source mix (P3): the mix's combined capacity caps the period's quantity; each line is
                # capped by its own source in the split below
                q = min(lot_round(src, max(need, eoq, 0.)), sum(min(s.maximum, s.capacity_by_period[t]) for s in mix_sources))
            else:
                q = min(lot_round(src, max(need, eoq, 0.)), src.maximum, src.capacity_by_period[t])
            # a cap that is not itself a legal pack (the frozen lot_round returns min(q, maximum) as is)
            # is brought back to the pack below it, so the projection is always physically legal
            for pack in (src.multiple, src.case_multiple, src.pallet_multiple, src.transport_multiple):
                if pack > 0:
                    q = _round_to(q, pack, up=False)
            if q > 0 and arrival < H + 1:
                # incumbent source mix (P3): the declared shares split the rule's quantity; frozen single line otherwise
                for line_src, line_q in split_projection(sourcing, sku, location, options, src, q, t):
                    if sourcing is not None:
                        # P3: a projected line never exceeds the room left on a resource shared across SKUs
                        line_q = fit_resources(req, resource_used, line_src, line_q, t)
                        if line_q <= 0:
                            continue
                    line_arrival = int(mean_world.arrival.get((line_src.id, t), dates(req, line_src, t)[1]))
                    purchases[line_src.id, t] = purchases.get((line_src.id, t), 0.) + line_q
                    pending.append((sku, location, line_arrival + receipt_life(line_src), line_arrival, line_q * float(mean_world.fills.get((line_src.id, t), line_src.fill_mean))))
        # 3. serve the period's mean demand FEFO at every location
        for (sku, location), m in mu.items():
            remaining = m
            for e in sorted(cohorts[sku, location]):
                if remaining <= 1e-9:
                    break
                if e <= t:
                    cohorts[sku, location][e] = 0.
                    continue
                take = min(remaining, cohorts[sku, location][e])
                cohorts[sku, location][e] -= take
                remaining -= take
    apply_mov(req, purchases)
    apply_load_cap(req, purchases)
    _apply_weight_cap(req, purchases, physics)
    apply_cash_cap(req, purchases)
    purchases = {k: v for k, v in purchases.items() if v > 0}
    return Solution("OPTIMAL", purchases, {k: v for k, v in transfers.items() if v > 1e-9}, _keep_amendments(req), {}, None, [], 0., 0, 0, None, 0.,
                    [f"baseline:{rule}"])


def independent_branch_requests(req: Request) -> dict[str, Request]:
    """Baseline A: every location that serves demand becomes its own isolated supply chain with the
    same physics and no pooling.

    A transfer-fed branch keeps its feeding origin(s) as a private copy: the origin's stock, its
    supplier capacity and maximum, its open orders and shared resources are split by the branch's share
    of the demand the origin serves; the lane into the branch, the supplier lead, the lane cost and the
    order-level economics are unchanged (each branch pays the full order cost: no consolidation is
    exactly what "no pooling" means). A location that buys directly keeps its own sources and stock.
    The union of the parts can never use more stock or capacity than the network holds."""
    from zaad.meio.topology import network_state
    state = network_state(req)
    rate: dict[tuple[str, str], float] = defaultdict(float)
    for p in state.positions.values():
        rate[p.sku, p.location] += p.demand_rate
    served_by_origin: dict[tuple[str, str], float] = defaultdict(float)
    for arc in req.transfers:
        if arc.approved:
            served_by_origin[arc.sku, arc.origin] += rate[arc.sku, arc.destination]
    for (sku, loc), r in rate.items():
        served_by_origin[sku, loc] += r          # an origin's own customers, if any
    data_all = req.model_dump(mode="python")
    out: dict[str, Request] = {}
    serving = sorted({s.location for s in req.services})

    def scaled_po(po: dict, share: float) -> dict:
        row = dict(po)
        for k in ("ordered", "confirmed", "shipped", "received", "rejected", "expected_accepted_remaining"):
            row[k] = po[k] * share
        row["options"] = [{**o, "max_quantity": o["max_quantity"] * share} for o in po["options"]]
        return row

    for location in serving:
        feeders = [a for a in req.transfers if a.approved and a.destination == location]
        origins = sorted({a.origin for a in feeders})
        keep = {location, *origins}
        # share of each origin's served demand that this branch represents (per SKU, then the max over SKUs)
        share_of: dict[str, float] = {}
        for origin in origins:
            skus_here = {a.sku for a in feeders if a.origin == origin}
            shares = [rate[sku, location] / served_by_origin[sku, origin] if served_by_origin[sku, origin] > 0 else 0. for sku in skus_here]
            share_of[origin] = max(shares) if shares else 0.
        data = dict(data_all)
        data["locations"] = [loc for loc in data_all["locations"] if loc["id"] in keep]
        data["services"] = [s for s in data_all["services"] if s["location"] == location]
        keep_services = {s["id"] for s in data["services"]}
        data["history"] = [h for h in data_all["history"] if h["service"] in keep_services]
        data["events"] = [e for e in data_all["events"] if e["service"] in keep_services]
        data["order_lines"] = [line for line in data_all["order_lines"] if line["service"] in keep_services]
        data["customers"] = [c for c in data_all["customers"] if c["id"] in {s["customer"] for s in data["services"]}] or list(data_all["customers"])[:1]
        stock = []
        for x in data_all["stock"]:
            if x["location"] == location:
                stock.append(x)
            elif x["location"] in origins:
                share = share_of[x["location"]]
                stock.append({**x, "id": f"{x['id']}__{location}", "quantity": x["quantity"] * share, "reserved": x["reserved"] * share,
                              "damaged": x["damaged"] * share, "quarantined": x["quarantined"] * share})
        data["stock"] = stock
        data["transfers"] = [a for a in data_all["transfers"] if a["destination"] == location and a["origin"] in keep]
        lane_ids = {a["id"] for a in data["transfers"]}
        data["incumbent_transfers"] = [x for x in data_all["incumbent_transfers"] if x["transfer"] in lane_ids]
        data["inbound_transfers"] = [{**x, "origin": x["origin"] if x["origin"] in keep else location} for x in data_all["inbound_transfers"] if x["destination"] == location]
        sources = []
        for src in data_all["sources"]:
            if src["destination"] == location:
                sources.append(src)
            elif src["destination"] in origins:
                share = share_of[src["destination"]]
                maximum = max(1e-9, src["maximum"] * share)
                sources.append({**src, "capacity_by_period": [c * share for c in src["capacity_by_period"]], "maximum": maximum,
                                "minimum": min(src["minimum"], maximum)})
        data["sources"] = sources
        source_ids = {s["id"] for s in sources}
        share_of_source = {s["id"]: (1. if s["destination"] == location else share_of[s["destination"]]) for s in sources}
        data["pipeline"] = [scaled_po(po, share_of_source[po["source"]]) for po in data_all["pipeline"] if po["source"] in source_ids]
        data["pipeline"] = [po for po in data["pipeline"] if po["ordered"] - po["received"] > 1e-9]
        data["shipment_history"] = [row for row in data_all["shipment_history"] if row["source"] in source_ids]
        data["incumbent_orders"] = [{**row, "quantity": row["quantity"] * share_of_source[row["source"]]} for row in data_all["incumbent_orders"] if row["source"] in source_ids]
        needed = {r for s in sources for r in s["resources"]}
        outside = {r for s in req.sources for r in s.resources if s.id not in source_ids}
        resources = []
        for r in data_all["resources"]:
            if r["id"] not in needed:
                continue
            if r["id"] in outside:
                # shared with sources outside this chain: this chain's share of the network demand it serves
                users = [s for s in req.sources if r["id"] in s.resources]
                served = sum(served_by_origin[s.sku, s.destination] for s in users) or 1.
                mine = sum(rate[s.sku, location] for s in users if s.id in source_ids) or sum(rate[sku, location] for (sku, loc) in rate if loc == location)
                resources.append({**r, "capacity_by_period": [c * min(1., mine / served) for c in r["capacity_by_period"]]})
            else:
                resources.append(r)
        data["resources"] = resources or list(data_all["resources"])[:1]
        data["supplier_terms"] = [st for st in data_all["supplier_terms"] if st["supplier"] in {s["supplier"] for s in sources}]
        data["signals"] = []
        data["inherited_on_hand"] = {k: v for k, v in data_all["inherited_on_hand"].items() if k.split("|")[-1] in keep}
        data["economics_provenance"] = {k: v for k, v in data_all["economics_provenance"].items()
                                        if not k.startswith("location.") or k.split(".")[1] in keep}
        out[location] = Request.model_validate(data)
    return out


def register_replay_methods() -> None:
    """Expose the network policies to `zaad.full.replay` under their method names."""
    from zaad.full.model import solve
    from zaad.full.replay import NETWORK_METHODS
    from zaad.full.worlds import draw

    def make(rule: str):
        def method(req: Request) -> Solution:
            projected = network_rule_plan(req, rule)
            world = draw(req, req.seed, 1, deterministic=True)
            settled = solve(req, world, fixed=replace(projected, status="OPTIMAL"))
            if not settled.usable_plan:
                # the projection itself is the plan: the common model could not reproduce it on the mean world
                return Solution(settled.status, dict(projected.purchases), dict(projected.transfers), dict(projected.amendments), {}, None, [], settled.solve_seconds,
                                settled.variables, settled.constraints, None, None, [f"baseline:{rule}", *settled.warnings])
            return replace(settled, warnings=[f"baseline:{rule}", *settled.warnings])
        return method
    NETWORK_METHODS.setdefault("network_rop", make("network:rop"))
    NETWORK_METHODS.setdefault("central_pool", make("network:pool"))
