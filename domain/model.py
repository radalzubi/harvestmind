"""Domain enum and the policy objects the engine consults instead of branching.

A ``DomainPolicy`` answers five questions the optimizer would otherwise have
to ask with an ``if``:

  * does carried stock decay, and how fast (``decay_rate_per_period``)?
  * must orders be whole cases or pallets (``pack_spec_for``)?
  * which cost terms are live (``cost_config``)?
  * how is service promised and measured (``service_target``)?
  * what is the base unit, so a report can name it (``base_unit``)?

Everything else — scenarios, recourse, balance, capacity, settlement — is
domain-blind and shared. That is the architectural claim being tested: two
markets, one engine, no relabelling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from domain.economics import CostConfig, ServiceTarget
from domain.uom import CONTINUOUS, PackSpec, Unit


class Domain(str, Enum):
    AGRICULTURE_PERISHABLE = "agriculture_perishable"
    FMCG = "fmcg"


AGRICULTURE_PERISHABLE = Domain.AGRICULTURE_PERISHABLE
FMCG = Domain.FMCG


@dataclass(frozen=True)
class DomainPolicy:
    """Domain-specific answers, with domain-appropriate validation."""

    domain: Domain
    base_unit: Unit
    cost_config: CostConfig
    service_target: ServiceTarget
    # Fraction of carried stock lost per period. Zero for shelf-stable goods.
    decay_rate_per_period: float = 0.0
    # Per-product pack structure. Products absent from the map are
    # continuous, which is right for produce and wrong for a case-packed
    # SKU, so FMCG validation requires every product to be present.
    pack_specs: dict = field(default_factory=dict)
    # Whether a supplier's delivered quantity is a random YIELD on the
    # commitment (produce) or a random FILL of an order (FMCG). Both are a
    # multiplier in [0, 1] on the quantity committed; the name records the
    # mechanism so a report can say which was assumed.
    supply_uncertainty: str = "fill"
    # Lead time may be uncertain (import distribution) or fixed (harvest
    # week). The optimizer treats both as scenario data.
    lead_time_uncertain: bool = True
    # Whether lots must be consumed oldest-first. Enforced in settlement,
    # not in the LP, because the LP tracks product totals, not lots.
    fefo: bool = False
    review_period: str = "week"
    # Service segmentation: class name -> ServiceTarget, and product -> class.
    # The optimizer enforces a unit-fill floor per product from these; line,
    # order fill and OTIF are measured in settlement, never enforced.
    service_by_class: dict = field(default_factory=dict)
    sku_class: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.decay_rate_per_period < 1.0:
            raise ValueError("decay_rate_per_period must be in [0, 1)")
        if self.supply_uncertainty not in ("yield", "fill"):
            raise ValueError("supply_uncertainty must be 'yield' or 'fill'")
        if self.review_period not in ("day", "week", "month"):
            raise ValueError("review_period must be day, week or month")
        for j, spec in self.pack_specs.items():
            if not isinstance(spec, PackSpec):
                raise TypeError(f"pack_specs[{j!r}] must be a PackSpec")
        if self.domain is Domain.FMCG:
            if self.base_unit not in (Unit.EACH, Unit.CASE):
                raise ValueError("FMCG base unit must be each or case")
            if self.fefo and self.decay_rate_per_period == 0.0 and \
                    self.cost_config.markdown_cost_per_unit == {}:
                # FEFO without any aging cost is inert; say so.
                raise ValueError("fefo=True has no effect without decay or markdown cost")
        if self.domain is Domain.AGRICULTURE_PERISHABLE:
            if self.base_unit not in (Unit.KG, Unit.LB, Unit.CRATE):
                raise ValueError("perishable produce base unit must be kg, lb or crate")

    def service_level_for(self, product_id: str) -> float:
        cls = self.sku_class.get(product_id)
        if cls and cls in self.service_by_class:
            return float(self.service_by_class[cls].level)
        return float(self.service_target.level)

    def service_floors(self, product_ids) -> dict:
        """Per-product unit-fill floors the optimizer can enforce."""
        return {j: self.service_level_for(j) for j in product_ids
                if self.service_target.metric == "unit_fill"}

    def pack_spec_for(self, product_id: str) -> PackSpec:
        return self.pack_specs.get(product_id, CONTINUOUS)

    def validate_products(self, product_ids) -> None:
        """Domain-specific completeness checks before a solve."""
        ids = list(product_ids)
        self.cost_config.validate_for_products(ids)
        if self.domain is Domain.FMCG:
            missing = [j for j in ids if j not in self.pack_specs]
            if missing:
                raise ValueError(
                    f"FMCG run without a PackSpec for {len(missing)} product(s) "
                    f"(e.g. {missing[:3]}); a case-packed SKU with no pack "
                    "structure would be recommended in fractional units")

    def describe(self) -> str:
        return (f"{self.domain.value}: base unit {self.base_unit.value}, "
                f"decay {self.decay_rate_per_period:.1%}/period, "
                f"{len(self.pack_specs)} pack specs, supply uncertainty "
                f"'{self.supply_uncertainty}', service "
                f"{self.service_target.level:.0%} {self.service_target.metric}")


def agriculture_policy(cost_config: CostConfig | None = None,
                       service_level: float = 0.95,
                       decay_rate_per_period: float | None = None,
                       base_unit: Unit = Unit.KG,
                       commodity: str | None = None,
                       category: str | None = None) -> DomainPolicy:
    """Perishable produce: continuous kilograms, decaying stock, yield risk.

    ``decay_rate_per_period`` measured by the operator wins. Otherwise the
    rate comes from ``domain.priors.decay_rate_prior`` (USDA ERS loss share
    for the commodity when cached, else a category table), labelled so.
    """
    cc = cost_config or CostConfig(currency="USD", emergency_cost_multiplier=1.30,
                                   emergency_capacity_factor=0.30)
    if decay_rate_per_period is None:
        from domain.priors import decay_rate_prior
        decay_rate_per_period = decay_rate_prior(commodity, category).value
    return DomainPolicy(
        domain=Domain.AGRICULTURE_PERISHABLE, base_unit=base_unit,
        cost_config=cc,
        service_target=ServiceTarget(service_level, metric="unit_fill"),
        decay_rate_per_period=decay_rate_per_period, pack_specs={},
        supply_uncertainty="yield", lead_time_uncertain=False, fefo=True,
        review_period="week")


def fmcg_policy(pack_specs: dict, cost_config: CostConfig | None = None,
                service_level: float = 0.97, review_period: str = "week",
                base_unit: Unit = Unit.EACH) -> DomainPolicy:
    """Shelf-stable distribution: discrete cases, no decay, fill and lead risk."""
    cc = cost_config or CostConfig(currency="USD", holding_rate_per_period=0.005,
                                   emergency_cost_multiplier=1.0,
                                   emergency_capacity_factor=0.0)
    return DomainPolicy(
        domain=Domain.FMCG, base_unit=base_unit, cost_config=cc,
        service_target=ServiceTarget(service_level, metric="unit_fill"),
        decay_rate_per_period=0.0, pack_specs=dict(pack_specs),
        supply_uncertainty="fill", lead_time_uncertain=True, fefo=False,
        review_period=review_period)


def get_policy(domain: Domain | str, **kwargs) -> DomainPolicy:
    d = Domain(domain) if not isinstance(domain, Domain) else domain
    if d is Domain.AGRICULTURE_PERISHABLE:
        return agriculture_policy(**kwargs)
    if d is Domain.FMCG:
        if "pack_specs" not in kwargs:
            raise ValueError("FMCG policy requires pack_specs")
        return fmcg_policy(**kwargs)
    raise ValueError(f"unknown domain {domain!r}")
