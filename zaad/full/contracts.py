"""Explicit financial, physical and causal contracts. No critical cost imputation."""
from __future__ import annotations

from datetime import datetime
import json
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_core import to_jsonable_python

from zaad.contracts import Dated, Record


class SKU(Dated):
    id: str
    volume: float = Field(gt=0)
    asset_value: float = Field(gt=0)
    terminal_value: float = Field(ge=0)
    shelf_life: int = Field(ge=1, le=520)
    disposal_fee: float = Field(ge=0)

    @model_validator(mode="after")
    def value_bound(self):
        if self.terminal_value > self.asset_value:
            raise ValueError("terminal value cannot exceed asset value")
        return self


class Calendar(Dated):
    id: str
    weekdays: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6)
    blackout_dates: tuple[str, ...] = ()
    cutoff_hour_utc: int = Field(default=24, ge=0, le=24)

    @model_validator(mode="after")
    def valid_calendar(self):
        from datetime import date
        if not self.weekdays or any(d not in range(7) for d in self.weekdays):
            raise ValueError("calendar requires valid weekdays")
        for d in self.blackout_dates:
            date.fromisoformat(d)
        return self


class Location(Dated):
    id: str
    kind: Literal["central_dc", "regional_dc", "branch", "warehouse"]
    capacity_volume: float = Field(gt=0)
    holding_per_value_period: float = Field(ge=0)
    receiving_calendar: str


class Stock(Dated):
    id: str
    sku: str
    location: str
    quantity: float = Field(ge=0)
    reserved: float = Field(ge=0)
    damaged: float = Field(ge=0)
    quarantined: float = Field(ge=0)
    expires_in: int = Field(ge=0)
    age_periods: int = Field(ge=0)

    @model_validator(mode="after")
    def usable_bound(self):
        if self.reserved + self.damaged + self.quarantined > self.quantity:
            raise ValueError("unusable quantities exceed physical lot")
        return self

    @property
    def usable(self) -> float:
        return self.quantity - self.reserved - self.damaged - self.quarantined


class Terms(Dated):
    id: str
    deposit_fraction: float = Field(ge=0, le=1)
    balance_trigger: Literal["order", "shipment", "arrival"]
    net_days: int = Field(ge=0, le=365)
    financing_fee_fraction: float = Field(ge=0, le=1)
    fx_rate_to_currency: float = Field(gt=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    fx_basis: Literal["same_currency", "contracted_hedge"]
    letter_of_credit_fraction: float = Field(ge=0, le=1)


class Resource(Dated):
    id: str
    capacity_by_period: tuple[float, ...]
    failure_domains: tuple[str, ...] = ()

    @model_validator(mode="after")
    def capacity(self):
        if not self.capacity_by_period or min(self.capacity_by_period) < 0:
            raise ValueError("resource requires nonnegative dated capacity")
        return self


class Source(Dated):
    """One operator-approved supplier/SKU/destination/itinerary/price-tier option."""
    id: str
    supplier: str
    sku: str
    destination: str
    route: tuple[str, ...]
    resources: tuple[str, ...]
    capacity_by_period: tuple[float, ...]
    unit_price: float = Field(gt=0)
    freight_per_unit: float = Field(ge=0)
    handling_per_unit: float = Field(ge=0)
    minimum: float = Field(ge=0)
    multiple: float = Field(ge=0)  # zero means physically continuous
    case_multiple: float = Field(default=0, ge=0)
    pallet_multiple: float = Field(default=0, ge=0)
    transport_multiple: float = Field(default=0, ge=0)
    maximum: float = Field(gt=0)
    fixed_order_fee: float = Field(ge=0)
    terms: str
    order_calendar: str
    shipping_calendar: str
    lead_days: int = Field(ge=1, le=730)
    dispatch_days: int = Field(ge=0, le=365)
    production_calendar: str | None = None
    production_workdays: int = Field(default=0, ge=0, le=365)
    leg_transit_days: tuple[int, ...] = ()
    leg_arrival_calendars: tuple[str, ...] = ()
    fill_mean: float = Field(gt=0, le=1)
    fill_sd: float = Field(ge=0, le=.5)
    lead_sd_days: float = Field(ge=0, le=365)
    approved: bool
    compliance: Literal["cleared", "blocked", "unreviewed"]
    quote_expires: datetime
    quote_reference: str
    exclusive_quote_group: str | None = None

    @model_validator(mode="after")
    def quote(self):
        if self.quote_expires.tzinfo is None or not self.route or not self.resources:
            raise ValueError("source requires dated quote, itinerary and capacity resources")
        if not self.capacity_by_period or min(self.capacity_by_period) < 0:
            raise ValueError("invalid source capacity")
        if self.minimum > self.maximum:
            raise ValueError("MOQ above maximum")
        if self.leg_transit_days and (len(self.leg_transit_days) != len(self.route) - 1 or len(self.leg_arrival_calendars) != len(self.leg_transit_days) or min(self.leg_transit_days) < 0):
            raise ValueError("leg calendars and travel days must match itinerary")
        return self


class Transfer(Dated):
    id: str
    sku: str
    origin: str
    destination: str
    lead_periods: int = Field(ge=1, le=104)
    capacity: float = Field(ge=0)
    cost_per_unit: float = Field(ge=0)
    loss_fraction: float = Field(ge=0, le=1)
    approved: bool


class Substitute(Dated):
    id: str
    supplied_sku: str
    requested_sku: str
    customers: tuple[str, ...]
    channels: tuple[str, ...]
    input_per_output: float = Field(gt=0)
    penalty_per_output: float = Field(ge=0)
    service_equivalence: float = Field(gt=0, le=1)
    approved: bool
    brand_approval_reference: str
    cannibalization_assumption: str


class Customer(Dated):
    id: str
    channel: str
    priority: float = Field(gt=0)


class Service(Dated):
    id: str
    sku: str
    location: str
    customer: str
    target: float = Field(ge=0, le=1)
    selling_price: float = Field(gt=0)
    sla_per_unmet: float = Field(ge=0)
    metric: Literal["unit_fill", "line_fill", "order_fill", "otif"] = "unit_fill"


class DemandObservation(Dated):
    service: str
    period: int = Field(lt=0)
    quantity: float = Field(ge=0)


class OrderLine(Dated):
    id: str
    order_id: str
    service: str
    quantity: float = Field(ge=0)
    due_in: int = Field(ge=0)
    ordered_at: datetime
    requested_at: datetime
    promised_at: datetime
    delivered_at: datetime | None = None
    filled: float = Field(ge=0)
    cancelled: float = Field(ge=0)


class Event(Dated):
    id: str
    service: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    multiplier: float = Field(ge=0)
    label: str


class ShipmentObservation(Dated):
    id: str
    source: str
    elapsed_days: int = Field(ge=0)
    arrived: bool  # False is right censored, not a fabricated completed lead
    stage: str
    carrier: str
    accepted_ratio: float | None = Field(default=None, ge=0, le=1)


class POOption(Dated):
    id: str
    action: Literal["keep", "cancel", "expedite", "de_expedite", "reschedule"]
    due_in: int = Field(ge=0)
    fee_per_unit: float = Field(ge=0)
    remaining_invoice_per_unit: float = Field(ge=0)
    payment_due_in: int = Field(ge=0)
    max_quantity: float = Field(ge=0)
    deadline: datetime
    allowed_stages: tuple[str, ...]
    contract_reference: str


class OpenPO(Dated):
    id: str
    source: str
    revision: int = Field(ge=1)
    ordered: float = Field(gt=0)
    confirmed: float = Field(ge=0)
    shipped: float = Field(ge=0)
    received: float = Field(ge=0)
    rejected: float = Field(ge=0)
    expected_accepted_remaining: float = Field(ge=0)
    placed_at: datetime
    confirmed_at: datetime | None
    departed_at: datetime | None
    current_eta: datetime
    stage: str
    carrier: str
    cancellation_status: str
    prepaid_per_remaining_unit: float = Field(ge=0)
    allow_split_amendments: bool
    options: tuple[POOption, ...]

    @property
    def remaining(self) -> float:
        return self.ordered - self.received

    @model_validator(mode="after")
    def quantities(self):
        if not 0 <= self.rejected <= self.received <= self.shipped <= self.confirmed <= self.ordered:
            raise ValueError("PO quantity chain invalid")
        if self.expected_accepted_remaining > self.remaining:
            raise ValueError("expected remaining receipt exceeds open units")
        if sum(o.action == "keep" for o in self.options) != 1:
            raise ValueError("exactly one keep option required")
        return self


class Liquidity(Dated):
    opening_cash: float
    minimum_cash: float
    credit_limit: float = Field(ge=0)
    opening_debt: float = Field(ge=0)
    interest_per_period: float = Field(ge=0, le=1)
    known_receivables: tuple[float, ...]
    other_payments: tuple[float, ...]


class Stress(Record):
    name: str
    fill_multiplier: float = Field(gt=0, le=1)
    extra_lead_days: int = Field(ge=0, le=365)
    demand_multiplier: float = Field(gt=0, le=3)
    recovery_period: int = Field(ge=0)
    shared_failure: bool
    affected_resources: tuple[str, ...] = ()


class IncumbentOrder(Dated):
    source: str
    period: int = Field(ge=0)
    quantity: float = Field(ge=0)


class InboundTransfer(Dated):
    id: str
    sku: str
    origin: str
    destination: str
    accepted_quantity: float = Field(ge=0)
    due_in: int = Field(ge=0)
    expires_in: int = Field(ge=0)


class Request(Record):
    schema_version: Literal["zaad.network.v2"] = "zaad.network.v2"
    operator_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    as_of: datetime
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    period_days: int = Field(ge=1, le=31)
    horizon: int = Field(ge=1, le=52)
    skus: tuple[SKU, ...] = Field(min_length=1, max_length=5000)
    locations: tuple[Location, ...] = Field(min_length=1, max_length=100)
    calendars: tuple[Calendar, ...]
    terms: tuple[Terms, ...]
    resources: tuple[Resource, ...]
    sources: tuple[Source, ...]
    stock: tuple[Stock, ...]
    transfers: tuple[Transfer, ...]
    substitutions: tuple[Substitute, ...]
    customers: tuple[Customer, ...]
    services: tuple[Service, ...]
    history: tuple[DemandObservation, ...]
    order_lines: tuple[OrderLine, ...] = ()
    events: tuple[Event, ...] = ()
    shipment_history: tuple[ShipmentObservation, ...] = ()
    signals: tuple[dict, ...] = Field(default=(), max_length=200)
    pipeline: tuple[OpenPO, ...]
    inbound_transfers: tuple[InboundTransfer, ...] = ()
    incumbent_orders: tuple[IncumbentOrder, ...] = ()
    liquidity: Liquidity
    stresses: tuple[Stress, ...] = Field(min_length=1, max_length=12)
    seed: int = Field(ge=0)
    scenarios: int = Field(ge=1, le=32)
    max_solve_seconds: float = Field(gt=0, le=120)
    solver: Literal["highs", "cbc", "glpk", "gurobi", "cplex"] = "highs"
    downside_cost_tolerance: float = Field(ge=0, le=1)
    service_tolerance: float = Field(ge=0, le=.1)
    force_unit_fills: bool = False
    mode: Literal["LEAN", "PROTECT", "ALLOCATE", "RECOVER"] = "LEAN"
    evidence_label: Literal["SYNTHETIC", "OPERATOR-SHADOW"]

    @field_validator("signals")
    @classmethod
    def normalized_signals(cls, values):
        from zaad.signals import Signal
        return tuple(Signal.model_validate_json(json.dumps(v, default=to_jsonable_python)).model_dump(mode="json") for v in values)

    @model_validator(mode="after")
    def integrity(self):
        if self.as_of.tzinfo is None:
            raise ValueError("aware decision time required")
        tables = (self.skus, self.locations, self.calendars, self.terms, self.resources,
                  self.sources, self.stock, self.transfers, self.substitutions,
                  self.customers, self.services, self.events, self.shipment_history,
                  self.pipeline, self.order_lines, self.inbound_transfers)
        for records in tables:
            if len({r.id for r in records}) != len(records):
                raise ValueError("duplicate entity ID / unresolved PO revisions")
        def causal(record):
            for key, value in record.__dict__.items():
                if isinstance(value, datetime):
                    if value.tzinfo is None:
                        raise ValueError("all timestamps require timezone")
                    if key in {"known_at", "placed_at", "confirmed_at", "departed_at", "ordered_at", "delivered_at"} and value > self.as_of:
                        raise ValueError("future information at decision origin")
        for records in (*tables, self.history, self.incumbent_orders, (self.liquidity,)):
            for record in records:
                causal(record)
        maps = [{r.id: r for r in rows} for rows in (self.skus, self.locations, self.calendars, self.terms, self.resources, self.sources, self.customers, self.services)]
        sk, loc, cal, terms, res, src, customers, svc = maps
        def require(ok):
            if not ok:
                raise ValueError("invalid reference or incompatible planning dimensions")
        for location_key in self.locations:
            require(location_key.receiving_calendar in cal)
        for s in self.sources:
            require(s.sku in sk and s.destination in loc and s.terms in terms and s.order_calendar in cal and s.shipping_calendar in cal and all(r in res for r in s.resources))
            require(s.route[0] == s.supplier and s.route[-1] == s.destination)
            require(len(s.capacity_by_period) >= self.horizon)
            require((s.production_calendar is None or s.production_calendar in cal) and all(c in cal for c in s.leg_arrival_calendars))
            require(s.production_workdays == 0 or s.production_calendar is not None)
            require(s.unit_price * terms[s.terms].fx_rate_to_currency >= sk[s.sku].terminal_value)
        for r in self.resources:
            require(len(r.capacity_by_period) >= self.horizon)
        for row in self.stock:
            require(row.sku in sk and row.location in loc)
        for row in self.inbound_transfers:
            require(row.sku in sk and row.origin in loc and row.destination in loc and row.expires_in > row.due_in)
        for row in self.transfers:
            require(row.sku in sk and row.origin in loc and row.destination in loc and row.origin != row.destination)
        for row in self.services:
            require(row.sku in sk and row.location in loc and row.customer in customers)
            require(row.selling_price >= sk[row.sku].asset_value)
            if row.metric != "unit_fill":
                require(any(line.service == row.id for line in self.order_lines))
        for row in self.substitutions:
            require(row.supplied_sku in sk and row.requested_sku in sk and row.supplied_sku != row.requested_sku and all(c in customers for c in row.customers))
        require(len({(r.service, r.period) for r in self.history}) == len(self.history))
        for row in (*self.history, *self.events, *self.order_lines):
            require(row.service in svc)
        for event in self.events:
            require(event.end >= event.start)
        for line in self.order_lines:
            require(line.ordered_at <= self.as_of and line.filled + line.cancelled <= line.quantity)
        for row in self.shipment_history:
            require(row.source in src)
        for row in self.incumbent_orders:
            require(row.source in src and row.period < self.horizon)
        require(len({(r.source, r.period) for r in self.incumbent_orders}) == len(self.incumbent_orders))
        for po in self.pipeline:
            require(po.source in src and po.remaining > 0)
            for option in po.options:
                causal(option)
            require(len({o.id for o in po.options}) == len(po.options))
        for term in self.terms:
            require(term.currency == self.currency or term.fx_basis == "contracted_hedge")
            require(term.currency != self.currency or term.fx_rate_to_currency == 1)
        require(len(self.liquidity.known_receivables) >= self.horizon and len(self.liquidity.other_payments) >= self.horizon)
        require(self.liquidity.opening_debt <= self.liquidity.credit_limit)
        require(min(self.liquidity.known_receivables) >= 0 and min(self.liquidity.other_payments) >= 0)
        return self
