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
    # Optional contract class label ("strategic", "wholesale", "spot", ...) used for reporting
    # service by customer class. Targets stay on the Service record; the class never sets them.
    service_class: str | None = None


class Service(Dated):
    id: str
    sku: str
    location: str
    customer: str
    target: float = Field(ge=0, le=1)
    selling_price: float = Field(gt=0)
    sla_per_unmet: float = Field(ge=0)
    metric: Literal["unit_fill", "line_fill", "order_fill", "otif", "order_otif"] = "unit_fill"


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
    # Revisions: a superseded line is history, never demand or a service obligation.
    revision: int = Field(default=1, ge=1)
    superseded_by: str | None = None

    @property
    def open_quantity(self) -> float:
        return 0. if self.superseded_by else max(0., self.quantity - self.filled - self.cancelled)

    @model_validator(mode="after")
    def line_chain(self):
        if self.filled + self.cancelled > self.quantity + 1e-9:
            raise ValueError("filled plus cancelled exceeds the line quantity")
        if self.superseded_by == self.id:
            raise ValueError("a line cannot supersede itself")
        return self


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
    solver: Literal["highs", "highspy", "cbc", "glpk", "gurobi", "cplex"] = "highs"
    downside_cost_tolerance: float = Field(ge=0, le=1)
    service_tolerance: float = Field(ge=0, le=.1)
    force_unit_fills: bool = False
    # How review-by-review demand refits treat a detected level change. "symmetric" is the frozen
    # PR23 behaviour; the others are evaluated on new development/validation seeds only.
    demand_adaptation: Literal["symmetric", "asymmetric", "soft", "ensemble", "page_hinkley", "bocpd"] = "symmetric"
    # "pr24" is the frozen PR23/PR24 engine (expected-value service floors, declared supply
    # parameters only, universal 1.645 proxy buffer, cost-first acceptance). "reliability" adds
    # calibrated demand/supply uncertainty, route-derived failure domains, quantile (CVaR) service
    # protection, uncertainty-responsive proxy protection and service-first acceptance. Both are
    # evaluated side by side on new seeds; nothing about the frozen profile is retuned.
    engine_profile: Literal["pr24", "reliability"] = "reliability"
    # CVaR level for the quantile service constraint: the mean service over the worst
    # (1 - level) share of scenarios must still meet the target. 0 reduces to the expected floor.
    service_risk_level: float = Field(default=.5, ge=0, lt=1)
    # Probability weight the reliability profile gives the declared stress envelopes when it ranks
    # feasible candidates by cost and confirms benefit: protection is bought when the stress
    # downside is expensive enough at this weight, and not otherwise. Zero reproduces cost-first
    # ranking on fitted worlds only.
    stress_weight: float = Field(default=.2, ge=0, le=.5)
    # State-dependent protection decay (reliability profile only). True: robust residual spread,
    # calibration dead band, bounded young-regime level mixture, evidence-conditioned stress floor
    # and quantile protection scaled by the SKU/location risk state. False reproduces the PR30
    # reliability profile exactly, for paired comparison.
    protection_decay: bool = True
    # The incumbent at the next review is the plan the operator is executing: when a candidate was
    # accepted, its remaining schedule (shifted one period) becomes the declared incumbent instead
    # of re-deriving the base-stock proxy every review. Stops the selector chattering between a
    # network plan and the proxy, which front-loads purchases and inflates average inventory.
    # Default off: on development4 the carried schedule anchored the next review to a lumpy
    # horizon plan and raised quiet-cell inventory (evidence/v4/diag_quiet_carry_29001.json).
    carry_incumbent: bool = False
    # Stability cost (reliability profile): a fraction of landed unit cost charged per unit of
    # period-to-period change in each source's order quantity, so a plan that is otherwise
    # indifferent to timing does not lurch between large and zero orders. A genuine reason to
    # change (shortage at 11 per unit, a stress) still dominates a 2% smoothing charge.
    order_smoothing: float = Field(default=.02, ge=0, le=.5)
    # v5 network/recovery rules: recency-weighted supply state (risk-source half-life), alternates
    # earn flexibility credit only inside the service window, feasible candidates within a cost
    # band are ranked by inventory burden, echelon accounting and transition reasons in the
    # report. False reproduces the v4 (PR 33) profile for paired comparison.
    protection_v5: bool = True
    # v6 multi-echelon / recovery rules: duplicated-buffer detection, per-driver recovery exit,
    # recovery excess penalty (orderly run-down of temporary protection), bounded terminal
    # continuation, procurement-timing audit. False reproduces the V5 engine exactly.
    protection_v6: bool = True
    # v7 capital-efficiency rules: protection state for transfer origins that carry no customers of
    # their own (a central DC held half the network inventory outside the recovery machinery),
    # symmetric confirmation when the incumbent itself misses a target, an inventory tie-break the
    # finite horizon cannot see, confirmed demand-decline liquidation, source-specific recovery
    # confidence and the procurement-timing preference. False reproduces the V6 engine exactly.
    protection_v7: bool = True
    # Solver optimality gap for the MILP (v8). The engine has always asked HiGHS for 1e-6, which on
    # a 30-review network cell is not reachable inside the wall-clock cap: six of ten candidate
    # solves hit the cap and return whatever incumbent the solver happened to hold. A bounded gap
    # is the honest setting for an operational recommendation; evidence runs may keep the strict
    # one. Changing it changes which solution is returned, so it is recorded in the manifest.
    solver_mip_gap: float = Field(default=1e-6, gt=0, le=.5)
    # Solve-quality threshold (v8). A candidate whose achieved optimality gap exceeds this is a
    # feasible point the solver never optimised, not an economic proposal: on a 30-review cell six
    # of ten candidate solves hit the wall-clock cap with achieved gaps of 0.89 and 1.00, while the
    # selector was ranking them against each other on cost differences of tens of units. Such a
    # candidate still counts as evidence about feasibility and service; it is excluded from
    # cost-based ranking and from cost-based acceptance, and it downgrades confidence if selected.
    # Set above 1 to disable the gate and reproduce V7 comparison behaviour exactly.
    comparable_gap: float = Field(default=.02, gt=0)
    # Inherited stock still on hand per "sku|location" (v8), supplied by the causal replay, which is
    # the only place that knows a lot's provenance. Empty in a single-shot request, where every unit
    # is by definition inherited from the operator's current position.
    inherited_on_hand: dict[str, float] = Field(default_factory=dict)
    # Adaptive escalation (v8). Off reproduces the V7 architecture exactly: every candidate policy
    # is solved for every review regardless of whether it could change the decision. On, a cheap
    # deterministic screen classifies the operating state, a minimum safe candidate set for that
    # state is solved first, and the optional planners run only when materiality or uncertainty
    # warrants the compute. The screen never prunes on a heuristic score alone.
    adaptive_escalation: bool = True
    # joint_recovery requiredness (v8, P0-E). The service-first joint plan is load-bearing only when
    # the current plan is projected to miss service materially; measured on the P0 set, the closure
    # cell whose service collapsed without it showed incumbent deficits of 0.27-0.55 while cells
    # where it changed nothing stayed inside 0.11. "v8": on-demand only (built when no candidate
    # meets every target). "deficit": also REQUIRED whenever the incumbent's projected service on
    # the selection worlds is at least `joint_recovery_deficit` below any target. "deficit_cover":
    # additionally REQUIRED when a served location holds under half a period of demand while a
    # supply or inbound driver is active.
    joint_recovery_rule: Literal["v8", "deficit", "deficit_cover"] = "deficit"
    joint_recovery_deficit: float = Field(default=.2, ge=0., le=1.)
    # Solve budget scaling (v8). The 5-second per-solve cap is not a considered figure - it is a
    # historical default - and measurement shows it lands in the worst possible place. On these
    # models HiGHS returns nothing at all until branching completes and then returns a proved
    # optimum: cell 72 needs 5.4 s, cell 21 needs 10.1 s and cell 108 needs 38.0 s, and below those
    # thresholds every one of them yields NO_FEASIBLE_SOLUTION. A flat 5 s therefore buys nothing
    # on exactly the cells that matter. The budget is scaled by model size instead, which the
    # measured solve times track closely, and the compute is paid for by the candidates adaptive
    # escalation no longer builds. Set to 1.0 to reproduce the flat cap.
    adaptive_solve_budget: bool = True
    # Margin over the fitted size curve. The worst measured case needed 38.0 s against a fitted
    # 31.25 s, a ratio of 1.22, so 1.3 is the smallest round margin that covers every cell measured.
    solve_budget_margin: float = Field(default=1.3, ge=1., le=5.)
    solve_budget_ceiling_seconds: float = Field(default=90., gt=0)
    # Warm start (v8, P0-W). On the largest models HiGHS finds no incumbent at all inside the
    # budget - cell 108 review 1 returns nothing at 40, 80 or 160 s - although the incumbent plan
    # itself meets the service target, so a feasible point is known. The incumbent's controls are
    # mapped into each candidate's own formulation, completed by that formulation's constraints
    # (a plan that fails a candidate's floors or packs is rejected, never asserted feasible) and
    # handed to HiGHS through highspy as the starting incumbent. Search only; the problem, the
    # physical validation and the gap policy are unchanged. Small models are not seeded.
    warm_start: bool = True
    warm_start_min_variables: int = Field(default=3000, ge=0)
    warm_start_completion_seconds: float = Field(default=30., gt=0)
    # Share of the solve budget the completion may spend. The completion is itself the search for
    # a first incumbent, so when the formulation has to repair the seed it is the best use of the
    # budget; it stops at its first feasible point and the main solve continues from there.
    warm_start_completion_share: float = Field(default=.6, gt=0., le=1.)
    # Bounded terminal continuation (v6, investigated): end-of-horizon stock and committed arrivals may
    # serve post-horizon demand over one lead at the service margin. Off by default: on development6 it
    # deferred buying into closures and severe delays (cells 21, 49, 91) in both of its forms.
    terminal_continuation: bool = False
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
