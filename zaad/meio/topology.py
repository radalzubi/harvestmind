"""Network domain model (P2): the frozen `Request` read as a distribution network.

Nothing here decides anything. It is the canonical, read-only view the P2 layer and its
explanations work from:

* nodes with a role and an echelon (0 = buys from a supplier; k = fed by an echelon k-1 node), what
  they buy, what they serve, which lanes feed them and which they feed;
* lanes (the frozen `Transfer` arcs) with their physics: lead, capacity, cost, per-dispatch cost,
  pack, loss, approval, and the earliest period a dispatch made now can land (receiving calendar
  included, exactly as the frozen model computes it);
* positions per SKU / location: usable stock, unusable stock, supplier and transfer units in transit
  with their next due period, fitted demand rate, service targets and customer priority;
* reachability: for every fed SKU / location, the periods that only local stock can serve and the
  lanes that can serve later periods; and stranded stock: units that cannot reach any demand;
* shared resources: suppliers and supplier-side resources whose capacity several destinations draw
  on, and origins whose stock several branches compete for;
* structural issues and the resource bounds a request must respect on the interactive API.

Reachability is the network principle the brief insists on: inventory counts only where and when it
can serve demand. "Network inventory" is never a naive sum here.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import timedelta
import math

from zaad.full.contracts import Request, Transfer
from zaad.full.worlds import dates, next_open

# Bounds for the interactive API (P2). A request beyond these is planned offline, never inline.
NETWORK_LIMITS = {"locations": 12, "transfers": 60, "incumbent_transfers": 600}


def network_solve_seconds(max_solve_seconds: float, scenarios: int, base: int = 3) -> float:
    """Per-solve budget declared with a network scenario count (P2). The frozen adaptive budget scales
    with horizon and breadth but was fitted on three worlds; a stochastic solve with S worlds carries
    S / 3 times the variables, so the declared budget grows with it (capped by the contract's 120 s)."""
    return float(min(120., max_solve_seconds * max(1., scenarios / base)))


def network_scenarios(longest_lane_lead_periods: int, base: int = 3, cap: int = 8) -> int:
    """Scenario count for a network request (P2). Protection at a transfer-fed location covers demand
    over its lane lead plus one review; with S worlds per period the tail of that multi-period sum is
    represented by S strata of each period, which P1 sized at three for a two-period window. The count
    grows with the window (three per two periods of window) and is capped at eight."""
    window = max(2, int(longest_lane_lead_periods) + 1)
    return int(min(cap, max(base, base * math.ceil(window / 2.))))


@dataclass(frozen=True)
class LaneView:
    id: str
    sku: str
    origin: str
    destination: str
    lead_periods: int
    capacity: float
    cost_per_unit: float
    fixed_cost_per_dispatch: float
    multiple: float
    loss_fraction: float
    approved: bool
    # period in which a dispatch made in period 0 lands at the destination (receiving calendar applied)
    earliest_arrival: int


@dataclass
class NodeView:
    id: str
    kind: str
    echelon: int | None
    holding_per_value_period: float
    capacity_volume: float | None
    buys: list[str] = field(default_factory=list)       # approved, cleared source ids
    serves: list[str] = field(default_factory=list)     # service ids
    fed_by: list[str] = field(default_factory=list)     # approved lane ids into this node
    feeds: list[str] = field(default_factory=list)      # approved lane ids out of this node


@dataclass
class PositionView:
    sku: str
    location: str
    on_hand_usable: float
    on_hand_unusable: float
    supplier_transit: float
    supplier_transit_next_due: int | None
    transfer_transit: float
    transfer_transit_next_due: int | None
    demand_rate: float
    targets: dict[str, float]
    priority: float


@dataclass
class Reach:
    sku: str
    location: str
    local_only_periods: int          # demand in periods < this can be served only by stock already here (or already in transit)
    lanes: list[dict]                # feeding lanes: id, origin, earliest_arrival, capacity, cost
    transit_due: list[int]           # periods in which units already in transit land


@dataclass
class NetworkState:
    nodes: dict[str, NodeView]
    lanes: dict[str, LaneView]
    positions: dict[tuple[str, str], PositionView]
    reach: dict[tuple[str, str], Reach]
    stranded: list[dict]
    shared: dict[str, list[dict]]
    correlation_groups: dict[str, list[str]]
    issues: list[str]
    topology: str                     # "single_node", "central_branches", "general"

    def summary(self) -> dict:
        return {"nodes": {k: {"kind": v.kind, "echelon": v.echelon, "buys": v.buys, "serves": v.serves, "fed_by": v.fed_by, "feeds": v.feeds}
                          for k, v in self.nodes.items()},
                "lanes": {k: {"sku": v.sku, "origin": v.origin, "destination": v.destination, "lead_periods": v.lead_periods,
                              "earliest_arrival": v.earliest_arrival, "capacity": v.capacity, "cost_per_unit": v.cost_per_unit,
                              "fixed_cost_per_dispatch": v.fixed_cost_per_dispatch, "multiple": v.multiple,
                              "loss_fraction": v.loss_fraction, "approved": v.approved} for k, v in self.lanes.items()},
                "positions": [{"sku": p.sku, "location": p.location, "on_hand_usable": p.on_hand_usable, "on_hand_unusable": p.on_hand_unusable,
                               "supplier_transit": p.supplier_transit, "supplier_transit_next_due": p.supplier_transit_next_due,
                               "transfer_transit": p.transfer_transit, "transfer_transit_next_due": p.transfer_transit_next_due,
                               "demand_rate": p.demand_rate, "targets": p.targets, "priority": p.priority} for p in self.positions.values()],
                "reachability": [{"sku": r.sku, "location": r.location, "local_only_periods": r.local_only_periods, "lanes": r.lanes,
                                  "transit_due": r.transit_due} for r in self.reach.values()],
                "stranded": self.stranded, "shared_resources": self.shared, "correlation_groups": self.correlation_groups,
                "issues": self.issues, "topology": self.topology,
                "scope": "read-only view of the request; reachability applies the lane lead and the receiving calendar exactly as the frozen model does"}


def lane_arrival(req: Request, arc: Transfer, t: int) -> int:
    """The period a dispatch over `arc` in period t lands, after the destination's receiving calendar
    (identical arithmetic to the frozen model and settlement)."""
    calendars = {c.id: c for c in req.calendars}
    location = next(loc for loc in req.locations if loc.id == arc.destination)
    when = req.as_of + timedelta(days=(t + arc.lead_periods) * req.period_days)
    actual = next_open(when, calendars[location.receiving_calendar])
    return math.ceil((actual - req.as_of).total_seconds() / (86400 * req.period_days))


def _history_rate(req: Request) -> dict[str, float]:
    """Mean of the last 13 observations per service (a reading of the request, not a forecast)."""
    rate: dict[str, float] = {}
    by_service: dict[str, list[tuple[int, float]]] = defaultdict(list)
    for row in req.history:
        by_service[row.service].append((row.period, row.quantity))
    for service in req.services:
        rows = sorted(by_service.get(service.id, []))[-13:]
        rate[service.id] = sum(q for _, q in rows) / len(rows) if rows else 0.
    return rate


def network_state(req: Request, rates: dict[str, float] | None = None) -> NetworkState:
    """Build the read-only network view. `rates` (fitted mean per service) may be supplied by the
    planner; otherwise the recent history mean is used."""
    customers = {c.id: c for c in req.customers}
    rates = rates if rates is not None else _history_rate(req)
    nodes = {loc.id: NodeView(loc.id, loc.kind, None, loc.holding_per_value_period, loc.capacity_volume) for loc in req.locations}
    for source in req.sources:
        if source.approved and source.compliance == "cleared":
            nodes[source.destination].buys.append(source.id)
    for service in req.services:
        nodes[service.location].serves.append(service.id)
    lanes: dict[str, LaneView] = {}
    for arc in req.transfers:
        lanes[arc.id] = LaneView(arc.id, arc.sku, arc.origin, arc.destination, arc.lead_periods, arc.capacity, arc.cost_per_unit,
                                 arc.fixed_cost_per_dispatch, arc.multiple, arc.loss_fraction, arc.approved, lane_arrival(req, arc, 0))
        if arc.approved:
            nodes[arc.destination].fed_by.append(arc.id)
            nodes[arc.origin].feeds.append(arc.id)
    # Echelons: roots buy from a supplier; a node fed by an echelon-k node is at k+1 (shortest path).
    roots = [n for n in nodes.values() if n.buys]
    for node in roots:
        node.echelon = 0
    frontier = [n.id for n in roots]
    while frontier:
        nxt = []
        for origin in frontier:
            for lane_id in nodes[origin].feeds:
                lane = lanes[lane_id]
                dest = nodes[lane.destination]
                if dest.echelon is None or dest.echelon > (nodes[origin].echelon or 0) + 1:
                    dest.echelon = (nodes[origin].echelon or 0) + 1
                    nxt.append(dest.id)
        frontier = nxt
    # Positions per SKU / location.
    positions: dict[tuple[str, str], PositionView] = {}
    pairs = {(s.sku, s.location) for s in req.services} | {(x.sku, x.location) for x in req.stock}
    pairs |= {(s.sku, s.destination) for s in req.sources} | {(a.sku, a.origin) for a in req.transfers} | {(a.sku, a.destination) for a in req.transfers}
    sources = {s.id: s for s in req.sources}
    for sku, location in sorted(pairs):
        usable = sum(x.usable for x in req.stock if x.sku == sku and x.location == location)
        unusable = sum(x.quantity - x.usable for x in req.stock if x.sku == sku and x.location == location)
        pos = [(next(o.due_in for o in po.options if o.action == "keep"), po.expected_accepted_remaining)
               for po in req.pipeline if sources[po.source].sku == sku and sources[po.source].destination == location and po.remaining > 0]
        inbound = [(row.due_in, row.accepted_quantity) for row in req.inbound_transfers if row.sku == sku and row.destination == location]
        services = [s for s in req.services if s.sku == sku and s.location == location]
        positions[sku, location] = PositionView(
            sku, location, usable, unusable, sum(q for _, q in pos), min((d for d, _ in pos), default=None),
            sum(q for _, q in inbound), min((d for d, _ in inbound), default=None),
            sum(rates.get(s.id, 0.) for s in services), {s.id: s.target for s in services},
            max((customers[s.customer].priority for s in services), default=0.))
    # Reachability per fed SKU / location.
    reach: dict[tuple[str, str], Reach] = {}
    for sku, location in sorted(pairs):
        feeders = [lanes[a.id] for a in req.transfers if a.approved and a.sku == sku and a.destination == location]
        if not feeders and not positions[sku, location].targets:
            continue
        earliest = min((lane.earliest_arrival for lane in feeders), default=req.horizon)
        transit_due = sorted({row.due_in for row in req.inbound_transfers if row.sku == sku and row.destination == location}
                             | {next(o.due_in for o in po.options if o.action == "keep") for po in req.pipeline
                                if sources[po.source].sku == sku and sources[po.source].destination == location and po.remaining > 0})
        local_only = min(earliest, req.horizon)
        if nodes[location].buys:
            own = [sources[s] for s in nodes[location].buys if sources[s].sku == sku]
            if own:
                local_only = min(local_only, min(dates(req, s, 0)[1] for s in own))
        reach[sku, location] = Reach(sku, location, local_only,
                                     [{"lane": lane.id, "origin": lane.origin, "earliest_arrival": lane.earliest_arrival, "capacity": lane.capacity,
                                       "cost_per_unit": lane.cost_per_unit, "origin_usable": positions.get((sku, lane.origin), PositionView(sku, lane.origin, 0., 0., 0., None, 0., None, 0., {}, 0.)).on_hand_usable}
                                      for lane in sorted(feeders, key=lambda x: (x.earliest_arrival, -x.capacity, x.id))],
                                     transit_due)
    # Stranded stock: units that cannot reach any demand.
    stranded: list[dict] = []
    for (sku, location), position in positions.items():
        if position.on_hand_usable <= 0:
            continue
        if position.targets:
            continue                       # demand here: the stock serves it
        outbound = [lanes[a.id] for a in req.transfers if a.approved and a.sku == sku and a.origin == location]
        if not outbound:
            stranded.append({"sku": sku, "location": location, "units": position.on_hand_usable, "reason": "no demand at this location and no approved outbound lane"})
            continue
        lots = [x for x in req.stock if x.sku == sku and x.location == location and x.usable > 0]
        dead = 0.
        for lot in lots:
            if all(lane.earliest_arrival >= lot.expires_in for lane in outbound):
                dead += lot.usable
        if dead > 0:
            stranded.append({"sku": sku, "location": location, "units": dead, "reason": "no lane lands before this stock expires"})
    # Shared resources.
    shared: dict[str, list[dict]] = {"supplier": [], "resource": [], "origin": []}
    by_supplier: dict[str, set[str]] = defaultdict(set)
    for source in req.sources:
        if source.approved and source.compliance == "cleared":
            by_supplier[source.supplier].add(source.destination)
    for supplier, dests in sorted(by_supplier.items()):
        if len(dests) > 1:
            shared["supplier"].append({"supplier": supplier, "destinations": sorted(dests)})
    by_resource: dict[str, set[str]] = defaultdict(set)
    for source in req.sources:
        for r in source.resources:
            by_resource[r].add(source.id)
    for resource in req.resources:
        users = by_resource.get(resource.id, set())
        if len(users) > 1:
            shared["resource"].append({"resource": resource.id, "sources": sorted(users), "capacity_period_0": resource.capacity_by_period[0]})
    by_origin: dict[tuple[str, str], set[str]] = defaultdict(set)
    for arc in req.transfers:
        if arc.approved:
            by_origin[arc.sku, arc.origin].add(arc.destination)
    for (sku, origin), dests in sorted(by_origin.items()):
        if len(dests) > 1:
            shared["origin"].append({"sku": sku, "origin": origin, "destinations": sorted(dests),
                                     "usable_now": positions[sku, origin].on_hand_usable if (sku, origin) in positions else 0.})
    groups: dict[str, list[str]] = defaultdict(list)
    for service in req.services:
        groups[service.sku].append(service.id)
    issues = validate_network(req)
    if len(req.locations) == 1:
        topology = "single_node"
    elif all(lanes[a.id].origin in {n.id for n in roots} and not nodes[lanes[a.id].destination].buys for a in req.transfers if a.approved) \
            and all(nodes[a.destination].echelon == 1 for a in req.transfers if a.approved):
        topology = "central_branches"
    else:
        topology = "general"
    return NetworkState(nodes, lanes, positions, reach, stranded, shared, dict(groups), issues, topology)


def validate_network(req: Request, limits: dict[str, int] | None = None) -> list[str]:
    """Structural issues of a network request. Bounds are the interactive API's; a request over them
    is refused there and planned offline. Zero-cost reverse lane pairs are flagged because nothing in
    the economics then separates A->B->A from doing nothing."""
    limits = limits or NETWORK_LIMITS
    issues: list[str] = []
    if len(req.locations) > limits["locations"]:
        issues.append(f"{len(req.locations)} locations exceed the interactive bound of {limits['locations']}")
    if len(req.transfers) > limits["transfers"]:
        issues.append(f"{len(req.transfers)} lanes exceed the interactive bound of {limits['transfers']}")
    if len(req.incumbent_transfers) > limits["incumbent_transfers"]:
        issues.append(f"{len(req.incumbent_transfers)} incumbent transfers exceed the bound of {limits['incumbent_transfers']}")
    approved = [a for a in req.transfers if a.approved]
    seen = {(a.sku, a.origin, a.destination): a for a in approved}
    for a in approved:
        reverse = seen.get((a.sku, a.destination, a.origin))
        if reverse is not None and a.cost_per_unit == 0 and reverse.cost_per_unit == 0 and a.fixed_cost_per_dispatch == 0 and reverse.fixed_cost_per_dispatch == 0:
            issues.append(f"lanes {a.id} and {reverse.id} form a zero-cost reverse pair for {a.sku}: transfer loops are not priced out")
    buyers = {(s.sku, s.destination) for s in req.sources if s.approved and s.compliance == "cleared"}
    fed = {(a.sku, a.destination) for a in approved}
    for service in req.services:
        key = (service.sku, service.location)
        if key not in buyers and key not in fed:
            stock = sum(x.usable for x in req.stock if x.sku == service.sku and x.location == service.location)
            issues.append(f"{service.sku}@{service.location} has demand but no source and no feeding lane (isolated; {stock:.0f} units on hand)")
    for a in approved:
        origin_has = (a.sku, a.origin) in buyers or (a.sku, a.origin) in fed or any(x.sku == a.sku and x.location == a.origin and x.usable > 0 for x in req.stock)
        if not origin_has:
            issues.append(f"lane {a.id}: origin {a.origin} neither buys, is fed, nor holds {a.sku} (dead lane)")
    return issues
