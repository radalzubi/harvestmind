"""P5 economics: the price of an allocation on the shared ledger.

A unit of a line ends in exactly one state: shipped on time, shipped late (backordered), shipped as
a declared substitute (on time or late), unmet (lost), or refused (CANCEL_IF_LATE shortfall). Every
charge lands on one settlement ledger key; the only keys P5 adds are `backorder_carry` and
`refusal`. Nothing is charged twice, and the ledger total equals the engine objective.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from zaad.atp.contracts import Atp, CustomerOrder, PromiseLine

TOL = 1e-9
LEDGER_KEYS = ("lost_sales_opportunity", "sla", "backorder_carry", "substitution", "transfer", "refusal")


@dataclass(frozen=True)
class Shipment:
    order: str
    line: str
    customer: str
    service_class: str
    sku_requested: str
    sku_supplied: str
    substitution: str | None        # frozen Substitute id when a substitute is shipped
    lot: str
    ship_from: str
    lane: str | None                # lane id when shipped from an alternative location
    promise_period: int
    requested_period: int
    quantity: float                 # requested (service-equivalent) units
    physical_units: float           # units drawn from the lot (conversion applied)


@dataclass
class Allocation:
    policy: str
    shipments: list[Shipment] = field(default_factory=list)
    unmet: dict[str, float] = field(default_factory=dict)
    refused: dict[str, float] = field(default_factory=dict)
    status: str = "OPTIMAL"
    notes: list[str] = field(default_factory=list)
    solve_seconds: float = 0.
    engine: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Drivers:
    """The declared numbers that rank a line; every one of them can be cited by the report."""
    lost_margin: float               # per unmet or refused unit (declared class value, else the Service selling price - the settlement basis)
    sla: float                       # Service.sla_per_unmet (stream-level, frozen)
    shortage_penalty: float          # class
    late_penalty: float              # class, per unit per period late
    refusal_cost: float              # class
    floor: float                     # class contractual floor
    strategic: bool
    reference: str
    customer_priority: float         # frozen Customer.priority (declared weight)
    tier: str | None
    provenance: str

    @property
    def unmet_cost(self) -> float:
        return self.lost_margin + self.sla + self.shortage_penalty

    @property
    def refused_cost(self) -> float:
        return self.lost_margin + self.refusal_cost


def drivers(req, atp: Atp, order: CustomerOrder, line: PromiseLine) -> Drivers:
    cls = atp.classes[order.service_class]
    service = next(s for s in req.services if s.customer == order.customer and s.sku == line.sku)
    customer = next(c for c in req.customers if c.id == order.customer)
    lost = line.unit_margin if line.unit_margin is not None else (cls.lost_margin_per_unit if cls.lost_margin_per_unit is not None else float(service.selling_price))
    return Drivers(lost_margin=float(lost), sla=float(service.sla_per_unmet), shortage_penalty=cls.shortage_penalty_per_unit,
                   late_penalty=cls.late_penalty_per_unit_period, refusal_cost=cls.refusal_cost_per_unit, floor=cls.contractual_service_floor,
                   strategic=cls.strategic, reference=cls.reference, customer_priority=float(customer.priority), tier=cls.tier, provenance=cls.provenance)


def price(alloc: Allocation, req, atp: Atp, state) -> dict[str, Any]:
    """Ledger by key, total, and the unit-state table per line (reconciliation invariant 3 / 13)."""
    ledger = {k: 0. for k in LEDGER_KEYS}
    units: dict[str, dict[str, float]] = {}
    subs = {s.id: s for s in req.substitutions}
    lanes = {lane.id: lane for lane in state.lanes}
    for order in atp.spec.orders:
        for line in order.lines:
            d = drivers(req, atp, order, line)
            row = {"requested": line.quantity, "on_time": 0., "late": 0., "substituted": 0., "unmet": alloc.unmet.get(line.id, 0.), "refused": alloc.refused.get(line.id, 0.), "late_unit_periods": 0.}
            for s in alloc.shipments:
                if s.line != line.id:
                    continue
                late = max(0, s.promise_period - s.requested_period)
                if late:
                    row["late"] += s.quantity
                    row["late_unit_periods"] += s.quantity * late
                    ledger["backorder_carry"] += s.quantity * late * d.late_penalty
                else:
                    row["on_time"] += s.quantity
                if s.substitution is not None:
                    row["substituted"] += s.quantity
                    rule = subs[s.substitution]
                    ledger["substitution"] += s.quantity * rule.penalty_per_output / rule.service_equivalence
                if s.lane is not None:
                    ledger["transfer"] += s.physical_units * lanes[s.lane].cost_per_unit
            ledger["lost_sales_opportunity"] += (row["unmet"] + row["refused"]) * d.lost_margin
            ledger["sla"] += row["unmet"] * (d.sla + d.shortage_penalty)
            ledger["refusal"] += row["refused"] * d.refusal_cost
            row["balance_residual"] = row["on_time"] + row["late"] + row["unmet"] + row["refused"] - line.quantity
            units[line.id] = row
    return {"ledger": ledger, "total": sum(ledger.values()), "units": units}
