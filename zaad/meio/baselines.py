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
from zaad.full.worlds import dates, forecast_all
from zaad.meio.topology import lane_arrival


def _round_to(q: float, multiple: float, up: bool) -> float:
    if multiple <= 0 or q <= 0:
        return max(0., q)
    packs = q / multiple
    packs = math.ceil(packs - 1e-9) if up else math.floor(packs + 1e-9)
    return max(0., packs * multiple)


def network_rule_plan(req: Request, rule: str) -> Solution:
    kind = rule.partition(":")[2]
    if kind not in {"rop", "pool"}:
        raise ValueError(f"unknown network policy {rule!r}")
    fits = forecast_all(req)
    customers = {c.id: c for c in req.customers}
    skus = {s.id: s for s in req.skus}
    sources = {s.id: s for s in req.sources}
    H = req.horizon
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
    buyers = {(s.sku, s.destination) for s in req.sources if s.approved and s.compliance == "cleared"}
    feeder: dict[tuple[str, str], Transfer] = {}
    for arc in sorted(req.transfers, key=lambda a: (lane_arrival(req, a, 0), -a.capacity, a.id)):
        if arc.approved and (arc.sku, arc.destination) not in buyers:
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
        due = max(1, next(o.due_in for o in po.options if o.action == "keep"))
        pending.append((src.sku, src.destination, due + skus[src.sku].shelf_life, due, po.expected_accepted_remaining))
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
                    if units > 0 and all(lane_arrival(req, arcs[d], t) < e for d, _ in group):
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
                        if e <= arrive or cohorts[sku, origin][e] <= 0:
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
            options = [s for s in req.sources if s.sku == sku and s.destination == location and s.approved and s.compliance == "cleared"]
            src = min(options, key=lambda s: (s.unit_price + s.freight_per_unit + s.handling_per_unit, s.id))
            z = _z(max([target[sku, location]] + [target[d] for d in downstream]))
            _, arrival = dates(req, src, t)
            lead = arrival - t
            tail = max((lane_arrival(req, feeder[d], 0) for d in downstream), default=0)
            echelon_pos = position(sku, location, t) + sum(position(*d, t) for d in downstream)
            rop = m * (lead + tail) + z * sd * math.sqrt(max(1, lead + tail))
            if echelon_pos - m > rop + 1e-9:
                continue
            nxt = next((dates(req, src, u)[1] for u in range(t + 1, H) if dates(req, src, u)[1] > arrival), None)
            cover_to = nxt if nxt is not None else H
            need = m * (cover_to - t + tail) + z * sd * math.sqrt(max(1, cover_to - t + tail)) - echelon_pos
            holding = locations[location].holding_per_value_period * src.unit_price + req.liquidity.cost_of_capital_per_period * src.unit_price
            fixed = order_costs.get(src.supplier, 0.) + src.fixed_order_fee
            eoq = math.sqrt(2. * m * fixed / holding) if fixed > 0 and holding > 0 else 0.
            q = lot_round(src, max(need, eoq, 0.))
            q = min(q, src.maximum, src.capacity_by_period[t])
            if q > 0 and arrival < H + 1:
                purchases[src.id, t] = purchases.get((src.id, t), 0.) + q
                pending.append((sku, location, arrival + skus[sku].shelf_life, arrival, q * src.fill_mean))
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
    apply_cash_cap(req, purchases)
    purchases = {k: v for k, v in purchases.items() if v > 0}
    return Solution("OPTIMAL", purchases, {k: v for k, v in transfers.items() if v > 1e-9}, _keep_amendments(req), {}, None, [], 0., 0, 0, None, 0.,
                    [f"baseline:{rule}"])


def independent_branch_requests(req: Request) -> dict[str, Request]:
    """Baseline A: every location that serves demand becomes an isolated single-node request.

    A branch fed only by lanes gets a virtual supplier relationship for each SKU: the origin's cheapest
    source with the lane appended (lead = supplier lead + lane lead, landed cost + lane cost, fill x
    (1 - loss), capacity = min(source, lane) split by the branch's share of the origin's fed demand),
    and its share of the origin's current stock as an inbound transfer landing after the lane lead.
    A location that buys directly keeps its own sources and stock. No lanes, no shared stock: what a
    decentralised network is. Shared supplier / resource capacity is split by demand share, so the
    decomposition can never use more than the network could."""
    rates = {s.id: 0. for s in req.services}
    from zaad.meio.topology import network_state
    state = network_state(req)
    for p in state.positions.values():
        for sid in p.targets:
            rates[sid] = p.demand_rate / max(1, len(p.targets))
    demand_at: dict[tuple[str, str], float] = defaultdict(float)
    for s in req.services:
        demand_at[s.sku, s.location] += rates[s.id]
    data_all = req.model_dump(mode="python")
    known_at = req.as_of
    out: dict[str, Request] = {}
    serving = sorted({s.location for s in req.services})
    for location in serving:
        data = dict(data_all)
        data["locations"] = [loc for loc in data_all["locations"] if loc["id"] == location]
        data["services"] = [s for s in data_all["services"] if s["location"] == location]
        keep_services = {s["id"] for s in data["services"]}
        data["history"] = [h for h in data_all["history"] if h["service"] in keep_services]
        data["events"] = [e for e in data_all["events"] if e["service"] in keep_services]
        data["order_lines"] = [line for line in data_all["order_lines"] if line["service"] in keep_services]
        data["stock"] = [x for x in data_all["stock"] if x["location"] == location]
        data["transfers"] = []
        data["incumbent_transfers"] = []
        data["inbound_transfers"] = [x for x in data_all["inbound_transfers"] if x["destination"] == location]
        own_sources = [s for s in data_all["sources"] if s["destination"] == location]
        own_ids = {s["id"] for s in own_sources}
        data["pipeline"] = [po for po in data_all["pipeline"] if po["source"] in own_ids]
        data["shipment_history"] = [row for row in data_all["shipment_history"] if row["source"] in own_ids]
        data["incumbent_orders"] = [row for row in data_all["incumbent_orders"] if row["source"] in own_ids]
        new_sources = list(own_sources)
        resources_needed: set[str] = {r for s in own_sources for r in s["resources"]}
        extra_inbound: list[dict] = []
        for sku_id in {s["sku"] for s in data["services"]}:
            if any(s["sku"] == sku_id for s in own_sources):
                continue
            feeders = [a for a in req.transfers if a.approved and a.sku == sku_id and a.destination == location]
            if not feeders:
                continue
            arc = min(feeders, key=lambda a: (lane_arrival(req, a, 0), -a.capacity, a.id))
            origin_sources = [s for s in req.sources if s.sku == sku_id and s.destination == arc.origin and s.approved and s.compliance == "cleared"]
            if not origin_sources:
                continue
            base = min(origin_sources, key=lambda s: (s.unit_price + s.freight_per_unit + s.handling_per_unit, s.id))
            fed = [d for a in req.transfers if a.approved and a.sku == sku_id and a.origin == arc.origin for d in [a.destination]]
            total = sum(demand_at[sku_id, d] for d in set(fed)) + demand_at[sku_id, arc.origin]
            share = demand_at[sku_id, location] / total if total > 0 else 1. / max(1, len(set(fed)))
            virtual = base.model_dump(mode="python")
            virtual.update({"id": f"{base.id}__via__{arc.id}", "destination": location, "route": [*base.route, location],
                            "lead_days": base.lead_days + arc.lead_periods * req.period_days,
                            "freight_per_unit": base.freight_per_unit + arc.cost_per_unit,
                            "fill_mean": max(1e-6, min(1., base.fill_mean * (1 - arc.loss_fraction))),
                            "capacity_by_period": [min(c, arc.capacity) * share for c in base.capacity_by_period],
                            "maximum": max(1e-9, min(base.maximum, arc.capacity) * share),
                            "minimum": min(base.minimum, max(1e-9, min(base.maximum, arc.capacity) * share)),
                            "resources": list(base.resources), "leg_transit_days": [], "leg_arrival_calendars": []})
            new_sources.append(virtual)
            resources_needed |= set(base.resources)
            origin_stock = sum(x.usable for x in req.stock if x.sku == sku_id and x.location == arc.origin)
            if origin_stock > 0:
                oldest = min((x.expires_in for x in req.stock if x.sku == sku_id and x.location == arc.origin and x.usable > 0), default=1)
                due = lane_arrival(req, arc, 0)
                if oldest > due:
                    # the origin no longer exists in this isolated request: the share is stock already on its way here
                    extra_inbound.append({"id": f"share_{sku_id}_{location}", "known_at": known_at, "sku": sku_id, "origin": location,
                                          "destination": location, "accepted_quantity": origin_stock * share * (1 - arc.loss_fraction),
                                          "due_in": due, "expires_in": oldest})
        data["sources"] = new_sources
        data["inbound_transfers"] = data["inbound_transfers"] + extra_inbound
        data["resources"] = [r for r in data_all["resources"] if r["id"] in resources_needed] or data_all["resources"][:1]
        # shared capacity: this branch's demand share of every shared resource
        total_demand = sum(demand_at.values()) or 1.
        my_share = sum(v for (k, loc), v in demand_at.items() if loc == location) / total_demand
        data["resources"] = [{**r, "capacity_by_period": [c * my_share for c in r["capacity_by_period"]]} if len([s for s in req.sources if r["id"] in s.resources and s.destination != location]) else r
                             for r in data["resources"]]
        data["supplier_terms"] = [st for st in data_all["supplier_terms"] if st["supplier"] in {s["supplier"] for s in new_sources}]
        data["stresses"] = data_all["stresses"]
        data["signals"] = []
        data["operator_id"] = f"{req.operator_id}"
        data["inherited_on_hand"] = {k: v for k, v in data_all["inherited_on_hand"].items() if k.endswith("|" + location)}
        if data["incumbent_rule"] and str(data["incumbent_rule"]).startswith("network:"):
            data["incumbent_rule"] = "reorder_point"
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
