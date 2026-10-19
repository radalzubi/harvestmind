"""Declared (SYNTHETIC) supply, economics and windows for the M5 weekly evaluation (Experiment A: single-SKU,
multiweek replenishment with declared lead times and an optional working-capital budget).

M5 carries unit sales and shelf prices; it carries no supplier, lead time, order, receipt, inventory or cost. Every
value here is an assumption held identical across all policies, versioned and hashed into every result row. Prices are
OBSERVED (the shelf price of the origin's Walmart week, knowable at the start of that week); the purchase cost is the
observed price times a declared margin, so purchase and shortage costs are in dollars of shelf price, not Walmart's
procurement cost. Weekly periods: every per-period rate is an annual assumption divided by 52.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import date
import hashlib
import json
from typing import Any

DECLARATION_VERSION = "m5-declaration-1"
WEEKS_PER_YEAR = 52.0


@dataclass(frozen=True)
class SupplyScenario:
    name: str
    lead_days: int
    lead_sd_days: float
    fill_mean: float
    fill_sd: float
    rationale: str


@dataclass(frozen=True)
class Economics:
    margin_fraction: float = 0.30              # unit cost = observed shelf price x (1 - margin); SYNTHETIC
    holding_annual: float = 0.25               # storage, handling, shrink: fraction of value per year
    cost_of_capital_annual: float = 0.10
    salvage_fraction: float = 0.80             # terminal value of unsold stock at the window end
    disposal_fee_fraction: float = 0.0
    shelf_life_weeks: int = 26                 # no expiry pressure in Experiment A (general merchandise and ambient food)
    opening_cover_weeks: float = 2.0
    service_target: float = 0.95
    sla_per_unmet: float = 0.0
    line_capacity_multiple: float = 20.0       # finite line cap per week as a multiple of mean weekly demand (never a sentinel)
    line_capacity_floor: float = 20.0
    order_multiple: float = 0.0                # 0 = continuous quantities in Experiment A (orders are in units but not lot-sized)
    cash_weeks: float | None = None            # None = no cash rows; k = opening cash of k weeks of purchases at mean demand, credit 0

    @property
    def holding_per_value_week(self) -> float:
        return (self.holding_annual + self.cost_of_capital_annual) / WEEKS_PER_YEAR


@dataclass(frozen=True)
class Declaration:
    version: str = DECLARATION_VERSION
    period_days: int = 7
    horizon_weeks: int = 8
    history_weeks: int = 52
    scenarios: int = 3
    max_solve_seconds: float = 20.0
    zaad_incumbent_rule: str | None = "reorder_point"
    economics: Economics = field(default_factory=Economics)
    supply: tuple[SupplyScenario, ...] = (
        SupplyScenario("stable", lead_days=14, lead_sd_days=0.0, fill_mean=1.0, fill_sd=0.0, rationale="two-week lead, on time, in full"),
        SupplyScenario("uncertain", lead_days=14, lead_sd_days=7.0, fill_mean=0.9, fill_sd=0.1, rationale="two-week lead with a one-week spread and short deliveries"),
        SupplyScenario("lead_only", lead_days=14, lead_sd_days=7.0, fill_mean=1.0, fill_sd=0.0, rationale="lead variability alone"),
        SupplyScenario("fill_only", lead_days=14, lead_sd_days=0.0, fill_mean=0.9, fill_sd=0.1, rationale="fill variability alone"),
        SupplyScenario("mild_lead", lead_days=14, lead_sd_days=3.0, fill_mean=1.0, fill_sd=0.0,
                       rationale="three-day spread: below the engine's half-period lateness slack on weekly periods (3.5 days)"),
    )
    stress: dict[str, Any] = field(default_factory=lambda: {"name": "declared_tail", "fill_multiplier": 0.9, "extra_lead_days": 7, "demand_multiplier": 1.1,
                                                            "recovery_period": 8, "shared_failure": True})
    knowledge_rule: str = "sales knowable at 23:59:59 UTC of their day; the origin week's shelf price knowable at the week start"
    evidence: dict[str, str] = field(default_factory=lambda: {
        "demand_history": "OBSERVED weekly unit sales (not demand: stockouts are not annotated in M5)", "prices": "OBSERVED weekly shelf price",
        "unit_cost": "DERIVED from the observed price by a SYNTHETIC margin", "opening_stock": "SYNTHETIC cover x DERIVED mean",
        "supply": "SYNTHETIC", "holding_capital_salvage_shelf_life_service": "SYNTHETIC", "purchase_orders": "SIMULATED by the replay",
        "supplier_relationships_at_walmart": "UNAVAILABLE; nothing here was observed at Walmart"})

    def supply_named(self, name: str) -> SupplyScenario:
        for s in self.supply:
            if s.name == name:
                return s
        raise KeyError(name)

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["economics"]["holding_per_value_week"] = self.economics.holding_per_value_week
        out["hash"] = self.hash()
        return out

    def hash(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()


DEFAULT = Declaration()


def variant(**changes) -> Declaration:
    eco = {k: v for k, v in changes.items() if hasattr(DEFAULT.economics, k)}
    top = {k: v for k, v in changes.items() if not hasattr(DEFAULT.economics, k)}
    return replace(DEFAULT, economics=replace(DEFAULT.economics, **eco), **top)


#: predeclared configurations (frozen before the holdout run); the holdout is run once per configuration listed in the
#: evidence note's freeze record, and no configuration is chosen on holdout results
VARIANTS: dict[str, Declaration] = {
    "corrected": DEFAULT,
    "no_incumbent": variant(zaad_incumbent_rule=None),
    "target_90": variant(service_target=0.90),
    "cash_4w": variant(cash_weeks=4.0),                       # working-capital budget: four weeks of purchases, no credit
    "holding_x2": variant(holding_annual=0.50, cost_of_capital_annual=0.20),
}

#: windows (Saturday origins on Walmart weeks); rolling mode, 13 weekly reviews, 8-week horizon: 20 truth weeks each
WINDOWS: dict[str, dict[str, Any]] = {
    "val1": {"origin": date(2014, 8, 2), "reviews": 13, "rolling": True, "role": "internal validation"},
    "val2": {"origin": date(2015, 1, 31), "reviews": 13, "rolling": True, "role": "internal validation"},
    "final": {"origin": date(2016, 1, 30), "reviews": 13, "rolling": True, "role": "chronological holdout; truth runs to 2016-06-17 (d_1939)"},
}
