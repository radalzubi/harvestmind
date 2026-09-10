"""Bounded, versioned, as-of contracts; no database or external I/O at construction."""
from __future__ import annotations

from datetime import datetime
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import to_jsonable_python


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class Dated(Record):
    known_at: datetime

    @model_validator(mode="after")
    def timezone_required(self):
        if self.known_at.tzinfo is None:
            raise ValueError("known_at must be timezone-aware")
        return self


class Item(Dated):
    id: str = Field(min_length=1, max_length=80)
    location: str = Field(min_length=1, max_length=80)
    unit: str = Field(default="each", min_length=1, max_length=20)
    base_cost: float = Field(gt=0, le=1e6)
    selling_price: float = Field(gt=0, le=1e6)
    holding_per_period: float = Field(gt=0, le=1e5)
    disposal_per_unit: float = Field(default=0, ge=0, le=1e5)
    service_target: float = Field(default=.95, ge=.5, le=1)
    pack: int = Field(default=1, ge=1, le=100000)
    moq: int = Field(default=0, ge=0, le=1000000)
    shelf_life: int = Field(default=104, ge=1, le=520)
    volume: float = Field(default=1, gt=0, le=1e6)
    criticality: float = Field(default=1, gt=0, le=100)
    segment: str = Field(default="B", max_length=30)
    incumbent_cover: float = Field(default=1, ge=0, le=20)

    @model_validator(mode="after")
    def viable_price(self):
        if self.selling_price < self.base_cost:
            raise ValueError("selling price below base cost requires a separate clearance model")
        if self.moq % self.pack:
            raise ValueError("MOQ must be a multiple of the pack size")
        return self


class Node(Dated):
    id: str = Field(min_length=1, max_length=80)
    kind: Literal["supplier", "port", "border", "chokepoint", "hub", "dc"]
    country: str = Field(min_length=2, max_length=3)


class Edge(Dated):
    id: str = Field(min_length=1, max_length=80)
    origin: str = Field(min_length=1, max_length=80)
    destination: str = Field(min_length=1, max_length=80)
    mode: Literal["ocean", "road", "rail", "air"]
    capacity: float = Field(gt=0, le=1e9)
    available: bool = True
    failure_domains: tuple[str, ...] = Field(default=(), max_length=20)


class Route(Dated):
    id: str = Field(min_length=1, max_length=80)
    supplier: str = Field(min_length=1, max_length=80)
    item: str = Field(min_length=1, max_length=80)
    edges: tuple[str, ...] = Field(min_length=1, max_length=12)
    landed_cost: float = Field(gt=0, le=1e6)
    capacity: float = Field(gt=0, le=1e9)
    approved: bool = False
    compliance: Literal["cleared", "blocked", "unreviewed"] = "unreviewed"
    valid_until: datetime
    quote_reference: str = Field(min_length=1, max_length=200)
    cancelable: bool = False


class Demand(Dated):
    item: str = Field(min_length=1, max_length=80)
    period: int = Field(lt=0, ge=-520)
    quantity: float = Field(ge=0, le=1e8)


class Delivery(Dated):
    route: str = Field(min_length=1, max_length=80)
    period: int = Field(lt=0, ge=-520)
    ordered: float = Field(gt=0, le=1e8)
    confirmed: float = Field(ge=0, le=1e8)
    received: float = Field(ge=0, le=1e8)
    accepted: float = Field(ge=0, le=1e8)
    lead_periods: int = Field(ge=1, le=26)

    @model_validator(mode="after")
    def quantity_chain(self):
        if not self.accepted <= self.received <= self.confirmed <= self.ordered:
            raise ValueError("require accepted <= received <= confirmed <= ordered")
        return self


class Lot(Dated):
    id: str = Field(min_length=1, max_length=80)
    item: str = Field(min_length=1, max_length=80)
    quantity: float = Field(ge=0, le=1e8)
    reserved: float = Field(default=0, ge=0, le=1e8)
    damaged: float = Field(default=0, ge=0, le=1e8)
    expires_in: int = Field(ge=0, le=520)

    @model_validator(mode="after")
    def usable(self):
        if self.reserved + self.damaged > self.quantity:
            raise ValueError("reserved and damaged stock exceed the lot")
        return self


class PurchaseOrder(Dated):
    id: str = Field(min_length=1, max_length=80)
    route: str = Field(min_length=1, max_length=80)
    ordered: float = Field(gt=0, le=1e8)
    expected_accepted: float = Field(ge=0, le=1e8)
    due_in: int = Field(ge=0, le=52)
    stage: Literal["placed", "confirmed", "departed", "in_transit", "port", "customs"]
    revision: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def expected_bound(self):
        if self.expected_accepted > self.ordered:
            raise ValueError("expected acceptance exceeds ordered quantity")
        return self


class PlanningRequest(Record):
    schema_version: Literal["zaad.v1"] = "zaad.v1"
    operator_id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    as_of: datetime
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    period_days: int = Field(default=7, ge=1, le=31)
    items: tuple[Item, ...] = Field(min_length=1, max_length=12)
    nodes: tuple[Node, ...] = Field(min_length=2, max_length=100)
    edges: tuple[Edge, ...] = Field(min_length=1, max_length=100)
    routes: tuple[Route, ...] = Field(min_length=1, max_length=24)
    demand: tuple[Demand, ...] = Field(max_length=6240)
    deliveries: tuple[Delivery, ...] = Field(max_length=12480)
    inventory: tuple[Lot, ...] = Field(default=(), max_length=500)
    pipeline: tuple[PurchaseOrder, ...] = Field(default=(), max_length=500)
    # Signals are validated by the dedicated provider contract at the boundary.
    signals: tuple[dict, ...] = Field(default=(), max_length=200)
    warehouse_capacity: float = Field(gt=0, le=1e10)
    review_budget: float = Field(gt=0, le=1e10)
    horizon: int = Field(default=12, ge=4, le=32)
    scenarios: int = Field(default=24, ge=8, le=64)
    seed: int = Field(default=1701, ge=0, le=2147483647)
    force_unit_fills: bool = False
    prior_mode: Literal["LEAN", "PROTECT", "ALLOCATE", "RECOVER"] = "LEAN"
    evidence_label: Literal["SYNTHETIC", "REAL-SIGNAL / SYNTHETIC-OPERATOR", "OPERATOR-SHADOW"] = "OPERATOR-SHADOW"

    @field_validator("signals")
    @classmethod
    def validate_signals(cls, value):
        from zaad.signals import Signal
        return tuple(Signal.model_validate_json(json.dumps(s, default=to_jsonable_python))
                     .model_dump(mode="json") for s in value)

    @model_validator(mode="after")
    def references_and_dates(self):
        if self.as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        for records in (self.items, self.nodes, self.edges, self.routes, self.inventory):
            ids = [r.id for r in records]
            if len(set(ids)) != len(ids):
                raise ValueError("duplicate entity ID")
        item = {x.id: x for x in self.items}
        nodes = {x.id: x for x in self.nodes}
        edges = {x.id: x for x in self.edges}
        routes = {x.id: x for x in self.routes}
        for records in (self.items, self.nodes, self.edges, self.routes, self.demand,
                        self.deliveries, self.inventory, self.pipeline):
            if any(r.known_at > self.as_of for r in records):
                raise ValueError("operator input not known at decision time")
        for edge in self.edges:
            if edge.origin not in nodes or edge.destination not in nodes:
                raise ValueError("unknown edge node")
        for route in self.routes:
            if route.item not in item or route.supplier not in nodes:
                raise ValueError("unknown route item/supplier")
            if route.valid_until.tzinfo is None:
                raise ValueError("route expiry must be timezone-aware")
            if any(e not in edges for e in route.edges):
                raise ValueError("unknown route edge")
            path = [edges[e] for e in route.edges]
            if path[0].origin != route.supplier or path[-1].destination != item[route.item].location:
                raise ValueError("route endpoints do not match supplier and item location")
            if any(a.destination != b.origin for a, b in zip(path, path[1:])):
                raise ValueError("route is not a contiguous itinerary")
            if route.landed_cost < item[route.item].base_cost:
                raise ValueError("base cost must not exceed any landed quote")
        for records in (self.demand, self.inventory):
            if any(x.item not in item for x in records):
                raise ValueError("unknown item")
        for records in (self.deliveries, self.pipeline):
            if any(x.route not in routes for x in records):
                raise ValueError("unknown route")
        if len({(x.item, x.period) for x in self.demand}) != len(self.demand):
            raise ValueError("demand requires one explicitly zero-filled row per item-period")
        if len({(x.id, x.revision) for x in self.pipeline}) != len(self.pipeline):
            raise ValueError("duplicate PO revision")
        # Input is a current as-of snapshot, not an ambiguous revision log.
        if len({x.id for x in self.pipeline}) != len(self.pipeline):
            raise ValueError("select the latest known PO revision before planning")
        return self


class Action(Record):
    route: str
    item: str
    quantity: float
    expected_accepted: float
    expected_due_in: int
    cash: float


class PlanReport(Record):
    brand: str = "ZAAD"
    website: str = "https://zaadsupply.com"
    operator_id: str
    as_of: datetime
    input_fingerprint: str
    evidence_label: str
    status: Literal["RECOMMEND_FOR_REVIEW", "KEEP_INCUMBENT", "ABSTAIN"]
    mode: Literal["LEAN", "PROTECT", "ALLOCATE", "RECOVER"]
    selected_policy: str
    actions: tuple[Action, ...]
    incumbent_actions: tuple[Action, ...]
    reasons: tuple[str, ...]
    frontier: tuple[dict, ...]
    routes: tuple[dict, ...]
    forecasts: tuple[dict, ...]
    economics: dict
    evidence: dict
    limitations: tuple[str, ...]
    approval_required: bool = True
    executable_purchase_order: bool = False
