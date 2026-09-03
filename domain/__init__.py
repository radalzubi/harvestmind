"""Operating-domain layer: what is shared, what is domain-specific.

HarvestMind runs in two operating environments that share an optimization
core and differ in physics and commerce:

    AGRICULTURE_PERISHABLE   the product carries a clock; supply is a yield
                             realised after commitment; waste is the cost of
                             over-committing.
    FMCG                     the product is shelf-stable or semi-perishable;
                             supply arrives in discrete cases and pallets
                             after an uncertain lead time; capital tied up
                             in stock is the cost of over-ordering.

The engine does not branch on the domain. It consumes a ``DomainPolicy``
that answers the questions where the two genuinely differ (does stock
decay, must orders be rounded, which cost terms apply, what a service
target means) and treats everything else identically. Anything that would
need ``if domain == ...`` in the optimizer belongs on the policy instead.
"""

from domain.economics import CostConfig, ServiceTarget
from domain.model import (
    AGRICULTURE_PERISHABLE, FMCG, Domain, DomainPolicy, get_policy,
)
from domain.uom import PackSpec, Quantity, Unit, round_to_pack

__all__ = [
    "AGRICULTURE_PERISHABLE", "FMCG", "CostConfig", "Domain", "DomainPolicy",
    "PackSpec", "Quantity", "ServiceTarget", "Unit", "get_policy",
    "round_to_pack",
]
