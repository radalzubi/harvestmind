"""Declared (SYNTHETIC) supply conditions and normalized-unit economics for the FreshRetailNet pilot.

FreshRetailNet carries no supplier, purchase order, receipt, inventory, price or cost. Every value in this module is a
modelling assumption, held identical across every evaluated policy, versioned, hashed into every result row and
reported as a sensitivity axis. Quantities are the dataset's normalized units; costs are indices per normalized unit,
never currency. Nothing here is an observed procurement record and no simulated purchase order is ever an actual one.

Daily periods. The pilot plans in one-day periods (`Request.period_days = 1`), so every per-period rate below is a
DAILY rate derived explicitly from an annual assumption (divided by 365), never a weekly rate reinterpreted.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any

DECLARATION_VERSION = "frn-declaration-1"
DAYS_PER_YEAR = 365.0


@dataclass(frozen=True)
class SupplyScenario:
    name: str
    lead_days: int                 # order-to-arrival, calendar days (period_days = 1, so one day is one period)
    lead_sd_days: float            # declared lead spread; the truth draws delays with it
    fill_mean: float               # declared fraction of an order that arrives
    fill_sd: float
    rationale: str


@dataclass(frozen=True)
class Economics:
    unit_cost: float = 1.0                     # purchase cost index per normalized unit (asset value)
    selling_price: float = 1.5                 # revenue index per normalized unit served; shortage cost rate = price + sla
    sla_per_unmet: float = 0.0
    salvage_fraction: float = 0.8              # terminal value of unsold, unexpired stock at the window end (ZAAD's default)
    disposal_fee: float = 0.05                 # per normalized unit expired
    holding_annual: float = 0.08               # storage and handling, fraction of value per year (ZAAD's public default)
    cost_of_capital_annual: float = 0.10       # ZAAD's default
    service_target: float = 0.95
    shelf_life_days: int = 7                   # declared for every SKU: fresh goods, numbers not in the dataset
    opening_cover_days: float = 2.0            # opening stock = cover × mean training demand before the first origin

    @property
    def holding_per_value_day(self) -> float:
        return (self.holding_annual + self.cost_of_capital_annual) / DAYS_PER_YEAR

    @property
    def terminal_value(self) -> float:
        return self.unit_cost * self.salvage_fraction


@dataclass(frozen=True)
class Declaration:
    version: str = DECLARATION_VERSION
    period_days: int = 1
    horizon_days: int = 7
    scenarios: int = 3                          # planner selection worlds (ZAAD's default)
    max_solve_seconds: float = 20.0
    #: the planner's history window in days. Capped below 68 so the frozen estimator's 52-lag "seasonal_naive" candidate (annual
    #: on weekly data, 52 DAYS on daily data) can never be enabled; the estimator's other windows are observation counts tuned on
    #: weekly data (16 / 26 / 12 / 4 observations) and are left as they are: they act on days here, identically for every policy.
    history_days: int = 63
    economics: Economics = field(default_factory=Economics)
    supply: tuple[SupplyScenario, ...] = (
        SupplyScenario("stable", lead_days=1, lead_sd_days=0.0, fill_mean=1.0, fill_sd=0.0,
                       rationale="next-morning replenishment as the paper describes (06:00 restock); every order arrives in full"),
        SupplyScenario("uncertain", lead_days=2, lead_sd_days=1.0, fill_mean=0.9, fill_sd=0.1,
                       rationale="two-day lead with one-day spread and short deliveries; a declared stress, not an observed supplier. "
                                 "NOTE: on daily periods a one-day lead spread exceeds the engine's half-period lateness slack, so the "
                                 "planner's supply-risk state activates (audit finding W1); this scenario therefore also exercises the "
                                 "protection regime, and the fill-only variant below separates the two effects"),
        SupplyScenario("uncertain_fill_only", lead_days=2, lead_sd_days=0.0, fill_mean=0.9, fill_sd=0.1,
                       rationale="two-day lead, no lead spread, short deliveries: isolates fill uncertainty from the lateness state"),
    )
    stress: dict[str, Any] = field(default_factory=lambda: {
        "name": "declared_tail", "fill_multiplier": 0.9, "extra_lead_days": 1, "demand_multiplier": 1.1,
        "recovery_period": 7, "shared_failure": True})
    knowledge_rule: str = "END_OF_DAY_UTC: a day's sales and stock flags are knowable at 23:59:59 UTC of that day"
    evidence: dict[str, str] = field(default_factory=lambda: {
        "demand_history": "OBSERVED (track A) or DERIVED (track B, recovered)",
        "stockout_flags": "OBSERVED; strata and recovery input only, never a policy outcome",
        "calendar_and_promotions": "OBSERVED; not supplied to the planner in the main runs (sensitivity only)",
        "opening_stock": "SYNTHETIC: declared cover times DERIVED mean training demand",
        "supply": "SYNTHETIC", "economics": "SYNTHETIC normalized-unit indices", "purchase_orders": "SIMULATED by the replay, never observed",
        "prices_costs_units": "UNAVAILABLE in the dataset"})

    def supply_named(self, name: str) -> SupplyScenario:
        for s in self.supply:
            if s.name == name:
                return s
        raise KeyError(name)

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["economics"]["holding_per_value_day"] = self.economics.holding_per_value_day
        out["economics"]["terminal_value"] = self.economics.terminal_value
        out["hash"] = self.hash()
        return out

    def hash(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()


DEFAULT = Declaration()
