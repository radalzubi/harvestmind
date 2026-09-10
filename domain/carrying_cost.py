"""Carrying-cost calculator: annual components in, planning-period rate out.

The carrying rate is the single number the validation showed can reverse
the policy ranking, and it is the one most operators do not actually
know. This makes it a sum of named parts, each with a provenance, and
converts to the optimizer's period (week or month) explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

PERIODS_PER_YEAR = {"week": 52.0, "month": 12.0, "day": 365.0}


@dataclass
class CarryingCostComponents:
    cost_of_capital_annual: float = 0.0        # WACC or borrowing rate
    storage_handling_annual: float = 0.0       # as a fraction of inventory value
    insurance_annual: float = 0.0
    shrink_obsolescence_annual: float = 0.0
    other_annual: float = 0.0
    provenance: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        for k, v in self.__dict__.items():
            if k.endswith("_annual") and not (0.0 <= float(v) <= 2.0):
                raise ValueError(f"{k} must be a fraction of value per year in [0, 2], got {v}")

    @property
    def annual_rate(self) -> float:
        return (self.cost_of_capital_annual + self.storage_handling_annual + self.insurance_annual
                + self.shrink_obsolescence_annual + self.other_annual)

    def per_period(self, period: str = "week") -> float:
        if period not in PERIODS_PER_YEAR:
            raise ValueError(f"period must be one of {sorted(PERIODS_PER_YEAR)}")
        return self.annual_rate / PERIODS_PER_YEAR[period]

    def breakdown(self, period: str = "week") -> dict:
        n = PERIODS_PER_YEAR[period]
        parts = {k: float(v) for k, v in self.__dict__.items() if k.endswith("_annual")}
        return {"annual_rate": self.annual_rate, "period": period, "per_period_rate": self.per_period(period),
                "components_annual": parts, "components_per_period": {k: v / n for k, v in parts.items()},
                "provenance": dict(self.provenance),
                "unknown_components": [k for k in parts if self.provenance.get(k, "assumed") in ("unknown",)]}


def sensitivity_grid(base: CarryingCostComponents, period: str = "week",
                     multipliers=(0.5, 1.0, 2.0, 4.0, 10.0)) -> list:
    """Rates to sweep, because the ranking of policies can flip with them."""
    r = base.per_period(period)
    return [{"multiplier": m, "per_period_rate": r * m, "annual_rate": base.annual_rate * m} for m in multipliers]
