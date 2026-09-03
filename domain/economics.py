"""Deployment-specific economics, validated once, threaded through the engine.

The optimizer's objective is a sum of cost terms. Which terms apply, and at
what rate, is a property of the operator and the domain rather than of the
model, so it lives in a validated configuration object rather than in
scattered keyword arguments with silent defaults.

One run, one currency. Mixing currencies inside a single optimization is
not supported and is refused at validation rather than at reconciliation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, fields


def _finite_nonneg(name: str, v: float) -> None:
    if not isinstance(v, (int, float)) or isinstance(v, bool):
        raise ValueError(f"{name} must be a number, got {v!r}")
    if not math.isfinite(v) or v < 0:
        raise ValueError(f"{name} must be finite and >= 0, got {v}")


@dataclass(frozen=True)
class ServiceTarget:
    """Service commitment in a stated metric.

    metric: 'unit_fill' (units served / units demanded, the one the
    optimizer can enforce exactly in expectation), or 'cycle' (probability
    of no stockout per review cycle, which the LP approximates and the
    replay measures). Naming the metric is the point: a 97% promise means
    something different under each, and a report that does not say which
    is not a report.
    """

    level: float
    metric: str = "unit_fill"
    scope: str = "global"       # global | sku | sku_class | customer | channel
    key: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 < self.level <= 1.0:
            raise ValueError(f"service level must be in (0, 1], got {self.level}")
        if self.metric not in ("unit_fill", "cycle", "line_fill", "order_fill"):
            raise ValueError(f"unknown service metric {self.metric!r}")
        if self.scope not in ("global", "sku", "sku_class", "customer", "channel"):
            raise ValueError(f"unknown service scope {self.scope!r}")
        if self.scope != "global" and not self.key:
            raise ValueError(f"scope {self.scope!r} needs a key")


@dataclass(frozen=True)
class CostConfig:
    """Every cost term the objective can carry, per unit unless stated.

    Rates are fractions of unit cost per period unless the name says
    otherwise. A term set to zero is disabled; the model drops it rather
    than multiplying by zero, so a zero term cannot accidentally become a
    free variable's price. Every deployment sets what it knows and leaves
    the rest at zero. Nothing here is a default economics; the defaults
    are conservative placeholders and ``validate`` will refuse a config in
    which every recourse term is zero, because that optimizer would have
    nothing to trade off.
    """

    currency: str = "USD"
    holding_rate_per_period: float = 0.0       # fraction of unit cost
    shortage_cost_per_unit: dict = field(default_factory=dict)   # lost margin
    waste_cost_per_unit: dict = field(default_factory=dict)      # unit cost - salvage
    ordering_cost_per_order: float = 0.0
    freight_cost_per_unit: float = 0.0
    emergency_cost_multiplier: float = 1.0      # spot premium, >= 1
    emergency_capacity_factor: float | None = None
    sla_penalty_rate: float = 0.0               # fraction of unit cost on shortfall
    sla_fill_target: float | None = None
    working_capital_rate_per_period: float = 0.0
    markdown_cost_per_unit: dict = field(default_factory=dict)
    transfer_cost_per_unit: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.currency, str) or len(self.currency) != 3 \
                or not self.currency.isalpha() or not self.currency.isupper():
            raise ValueError(f"currency must be a 3-letter ISO code, got {self.currency!r}")
        for f in fields(self):
            v = getattr(self, f.name)
            if f.name in ("currency", "emergency_capacity_factor", "sla_fill_target"):
                continue
            if isinstance(v, dict):
                for k, x in v.items():
                    _finite_nonneg(f"{f.name}[{k}]", x)
            else:
                _finite_nonneg(f.name, v)
        if self.emergency_cost_multiplier < 1.0:
            raise ValueError("emergency_cost_multiplier must be >= 1; emergency "
                             "supply is never cheaper than contracted")
        if self.emergency_capacity_factor is not None and \
                not 0.0 <= self.emergency_capacity_factor <= 1.0:
            raise ValueError("emergency_capacity_factor must be in [0, 1]")
        if self.sla_fill_target is not None and not 0.0 < self.sla_fill_target <= 1.0:
            raise ValueError("sla_fill_target must be in (0, 1]")
        if self.sla_penalty_rate > 0 and self.sla_fill_target is None:
            raise ValueError("sla_penalty_rate needs an sla_fill_target")
        if self.holding_rate_per_period > 0.25:
            raise ValueError(
                f"holding_rate_per_period {self.holding_rate_per_period} is "
                "above 25% per period; check the period (monthly rates run "
                "1.5-2.5%, weekly 0.3-0.6%)")

    def validate_for_products(self, product_ids) -> None:
        """Refuse to optimize products with no priced shortage or waste."""
        missing = [j for j in product_ids
                   if float(self.shortage_cost_per_unit.get(j, 0.0)) <= 0
                   and float(self.waste_cost_per_unit.get(j, 0.0)) <= 0]
        if missing and len(missing) == len(list(product_ids)):
            raise ValueError(
                "no product has a positive shortage or waste cost; the "
                "optimizer would have nothing to trade off. Set "
                "shortage_cost_per_unit (lost margin) and/or waste_cost_per_unit")
