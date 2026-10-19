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

DECLARATION_VERSION = "frn-declaration-2"
DAYS_PER_YEAR = 365.0
#: frn-declaration-1 (PR #114 original run) differs from this version only by the fields marked "v2" below; the original
#: results and their manifest are kept unchanged under docs/remodel/evidence/frn/ and data/public/freshretailnet/results/fifty.


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
    #: v2. Line capacity and maximum order per period as a multiple of mean history demand (v1 used 1,000,000 as "unbounded",
    #: which the model's undeclared-storage big-M summed into coefficients of order 1e7 against quantities of order 1 and the
    #: solver reported false INFEASIBLE: the root cause of the v1 base-stock/order-up-to infeasibility and of ZAAD's
    #: proxy-incumbent abstentions). A finite declared cap is still far above any plan's need.
    line_capacity_multiple: float = 50.0
    line_capacity_floor: float = 10.0

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
        SupplyScenario("uncertain_lead_only", lead_days=2, lead_sd_days=1.0, fill_mean=1.0, fill_sd=0.0,
                       rationale="v2. two-day lead with one-day spread and full deliveries: isolates lead variability from fill variability"),
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

    #: v2. The declared operator rule ZAAD treats as its incumbent (retained on every review it cannot improve on, exactly as
    #: production retains the operator's rule). None reproduces v1 (the engine's projected base-stock proxy, which ends the run
    #: when its own solve is unusable). The decision provenance (own candidate / retained incumbent / abstention) is recorded
    #: per review so a retained-incumbent review is never reported as an optimization success.
    zaad_incumbent_rule: str | None = "reorder_point"

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
#: the PR #114 reference configuration, byte-for-byte the v1 inputs except that line caps are finite (the v1 value is a
#: solver-conditioning defect, not an assumption worth preserving) and the engine's E1 correction applies
REFERENCE_V1 = Declaration(zaad_incumbent_rule=None)


def variant(name: str, **changes) -> Declaration:
    """A predeclared variant of the default declaration; `name` is recorded with the hash in every result row."""
    from dataclasses import replace as _replace
    d = _replace(DEFAULT, economics=_replace(DEFAULT.economics, **{k: v for k, v in changes.items() if hasattr(DEFAULT.economics, k)}),
                 **{k: v for k, v in changes.items() if not hasattr(DEFAULT.economics, k)})
    return d


VARIANTS: dict[str, Declaration] = {
    "reference_v1": REFERENCE_V1,                                   # original inputs + finite caps + E1; no incumbent rule
    "corrected": DEFAULT,                                           # + declared incumbent rule (reorder_point)
    "target_90": variant("target_90", service_target=0.90),
    "target_85": variant("target_85", service_target=0.85),
    "holding_x4": variant("holding_x4", holding_annual=0.32, cost_of_capital_annual=0.40),   # 72 %/yr: cheap goods, expensive capital
    "margin_x2": variant("margin_x2", selling_price=2.0),                                      # shortage twice as costly as v1
}
