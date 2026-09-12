"""P5 ATP / scarce-supply allocation: declared contracts.

A request without an `atp` block, or with `enabled` false, reaches no P5 code path
(`resolve()` returns None); every frozen P0-P4 semantic is bit-identical. A declared block is
validated aggressively (422 `atp_invalid` at the API) and bounded before any engine runs (413).

Every priority driver is a declared, provenance-carrying number. Names, labels and inferred scores
never rank a customer; `Customer.service_class` (frozen contract) stays a reporting label.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import Field, model_validator

from zaad.contracts import Record

Provenance = Literal["OPERATOR_DECLARED", "CONTRACT", "CONFIGURED_ASSUMPTION"]
IncumbentPolicy = Literal["FIFO_PROMISE", "FCFS_ORDER_DATE", "TIER_PRIORITY", "PROPORTIONAL", "CONTRACTUAL_THEN_PRIORITY", "DECLARED_MANUAL"]
Fairness = Literal["NONE", "PROPORTIONAL_WHEN_INDIFFERENT"]
LateSemantics = Literal["ACCEPT_LATE", "CANCEL_IF_LATE"]

INTERACTIVE_LIMITS = {"orders": 200, "lines": 500, "promise_horizon": 26, "service_classes": 50}


class ServiceClass(Record):
    """Declared economic / contractual class. Every number is a driver the report can cite."""
    id: str = Field(min_length=1, max_length=80)
    provenance: Provenance = "OPERATOR_DECLARED"
    reference: str = ""                       # contract id / policy id; required for CONTRACT and for strategic
    contractual_service_floor: float = Field(default=0., ge=0, le=1)
    shortage_penalty_per_unit: float = Field(default=0., ge=0)
    late_penalty_per_unit_period: float = Field(default=0., ge=0)
    refusal_cost_per_unit: float = Field(default=0., ge=0)
    lost_margin_per_unit: float | None = Field(default=None, ge=0)   # None -> frozen Service economics
    strategic: bool = False
    tier: str | None = None                   # declared label; used only by the TIER_PRIORITY incumbent

    @model_validator(mode="after")
    def provenance_rules(self):
        if self.provenance == "CONTRACT" and not self.reference:
            raise ValueError("atp: a CONTRACT service class needs a reference")
        if self.strategic and (self.provenance != "OPERATOR_DECLARED" or not self.reference):
            raise ValueError("atp: a strategic flag needs OPERATOR_DECLARED provenance and a reference (undeclared strategic flag)")
        return self


class PromiseLine(Record):
    id: str = Field(min_length=1, max_length=80)
    sku: str
    quantity: float = Field(gt=0)
    minimum_ship_quantity: float = Field(default=0., ge=0)
    requested_period: int = Field(ge=0)
    ship_from: tuple[str, ...] = ()           # eligible locations; empty = the service's own location
    unit_margin: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def coherent(self):
        if self.minimum_ship_quantity > self.quantity:
            raise ValueError("atp: minimum_ship_quantity exceeds the line quantity")
        return self


class CustomerOrder(Record):
    id: str = Field(min_length=1, max_length=80)
    customer: str
    service_class: str
    order_period: int = Field(default=0, le=0)          # 0 = placed now; negative = placed earlier
    lines: tuple[PromiseLine, ...] = Field(min_length=1)
    partial_fulfillment_allowed: bool = True
    backorder_allowed: bool = False
    max_backorder_periods: int = Field(default=0, ge=0)
    substitution_allowed: bool = False
    late_semantics: LateSemantics = "ACCEPT_LATE"
    priority_provenance: Provenance = "OPERATOR_DECLARED"

    @model_validator(mode="after")
    def coherent(self):
        if len({line.id for line in self.lines}) != len(self.lines):
            raise ValueError("atp: duplicate line id inside an order")
        if not self.backorder_allowed and self.max_backorder_periods:
            raise ValueError("atp: max_backorder_periods needs backorder_allowed")
        if self.backorder_allowed and self.max_backorder_periods < 1:
            raise ValueError("atp: backorder_allowed needs max_backorder_periods >= 1")
        return self


class AtpSpec(Record):
    """The request-level declaration (`Request.atp`)."""
    enabled: bool = False
    orders: tuple[CustomerOrder, ...] = ()
    service_classes: tuple[ServiceClass, ...] = ()
    incumbent_policy: IncumbentPolicy = "FIFO_PROMISE"
    manual_sequence: tuple[str, ...] = ()
    fairness: Fairness = "NONE"
    include_inbound: bool = False                 # count FIRM inbound (accepted in-flight transfers) by arrival period
    # Kept for schema compatibility (migration 020). Only 1 is accepted: a probabilistic inbound is never
    # converted into a firm promise by a confidence factor; open purchase orders are classified as
    # non-firm availability and never promised (state.py). Any other value is refused (fail closed).
    inbound_confidence: float = Field(default=1., ge=0, le=1)
    promise_horizon: int = Field(default=8, ge=1, le=52)
    cross_location: bool = False
    provenance: Provenance = "OPERATOR_DECLARED"

    @model_validator(mode="after")
    def coherent(self):
        ids = [o.id for o in self.orders]
        if len(set(ids)) != len(ids):
            raise ValueError("atp: duplicate customer order id")
        if abs(self.inbound_confidence - 1.) > 1e-12:
            raise ValueError("atp: inbound_confidence must be 1: probabilistic inbound is never promised (open purchase orders are classified as non-firm availability; "
                             "only accepted in-flight transfers are firm)")
        line_ids = [line.id for o in self.orders for line in o.lines]
        if len(set(line_ids)) != len(line_ids):
            raise ValueError("atp: duplicate line id across orders")
        classes = {c.id for c in self.service_classes}
        if len(classes) != len(self.service_classes):
            raise ValueError("atp: duplicate service class id")
        for o in self.orders:
            if o.service_class not in classes:
                raise ValueError(f"atp: order {o.id} references an undeclared service class {o.service_class} (invalid priority class)")
            for line in o.lines:
                if line.requested_period < o.order_period:
                    raise ValueError(f"atp: line {line.id} requests delivery before its order period (impossible requested date)")
                if line.requested_period > self.promise_horizon:
                    raise ValueError(f"atp: line {line.id} requests delivery beyond the promise horizon (impossible requested date)")
        if self.incumbent_policy == "DECLARED_MANUAL":
            if not self.manual_sequence:
                raise ValueError("atp: DECLARED_MANUAL needs a manual_sequence (conflicting service policies)")
            unknown = set(self.manual_sequence) - set(ids)
            if unknown or len(set(self.manual_sequence)) != len(self.manual_sequence):
                raise ValueError("atp: manual_sequence must name every order once and only declared orders (conflicting service policies)")
        elif self.manual_sequence:
            raise ValueError("atp: manual_sequence only applies to DECLARED_MANUAL (conflicting service policies)")
        return self


@dataclass(frozen=True)
class Atp:
    """The resolved view: the spec plus the request's own economics standard."""
    spec: AtpSpec
    materiality_cost_fraction: float

    @property
    def classes(self) -> dict[str, ServiceClass]:
        return {c.id: c for c in self.spec.service_classes}


def resolve(req) -> Atp | None:
    """The request's P5 view, or None for a frozen request (absent or disabled)."""
    spec = getattr(req, "atp", None)
    if spec is None or not spec.enabled:
        return None
    return Atp(spec=spec, materiality_cost_fraction=float(req.materiality_cost_fraction))


def validate_request(req) -> None:
    """Request-level checks (called from the Request model validator): every referenced customer,
    SKU, location, and service exists; substitution only through the frozen approved contract."""
    spec = getattr(req, "atp", None)
    if spec is None or not spec.enabled:
        return
    customers = {c.id for c in req.customers}
    skus = {s.id for s in req.skus}
    locations = {loc.id for loc in req.locations}
    services = {(s.customer, s.sku): s for s in req.services}
    for order in spec.orders:
        if order.customer not in customers:
            raise ValueError(f"atp: order {order.id} names an unknown customer {order.customer}")
        for line in order.lines:
            if line.sku not in skus:
                raise ValueError(f"atp: line {line.id} names an unknown SKU {line.sku}")
            for loc in line.ship_from:
                if loc not in locations:
                    raise ValueError(f"atp: line {line.id} names an unknown location {loc}")
            if (order.customer, line.sku) not in services:
                raise ValueError(f"atp: no service (demand stream) declares customer {order.customer} for SKU {line.sku}; P5 prices with the frozen Service economics")
    if len(spec.orders) > INTERACTIVE_LIMITS["orders"] * 4 or sum(len(o.lines) for o in spec.orders) > INTERACTIVE_LIMITS["lines"] * 4:
        raise ValueError("atp: order count beyond the contract envelope (resource abuse)")
