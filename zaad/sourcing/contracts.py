"""Sourcing portfolio contract (P3): explicit, default-off, provenance-aware.

A source option is the frozen `zaad.full.contracts.Source` record (supplier, SKU, destination,
itinerary, capacity, price, freight, MOQ, packs, payment terms, calendars, lead and fill
uncertainty, approval and compliance). This module declares what the frozen record cannot carry:

* `SourceRiskGroup`   - sources that share a physical dependency (plant, port, route, carrier ...)
                        and therefore a common supply shock, with a correlation strength and provenance;
* `SourceShareConstraint` - operator-declared minimum / maximum share or committed units of one source
                        in the SKU / destination commitment (horizon or period scope);
* `SourceSwitchingCost` - a declared switching, qualification or set-up cost charged once when a source
                        outside the incumbent mix receives any quantity;
* `IncumbentSourceShare` - the operator's current source mix, so the incumbent projection buys the way
                        the operator buys and "switching" has a meaning.

`SourcingPortfolio` bundles them. A request without it (`Request.sourcing is None`) is the frozen
request: no hook below reads anything. Nothing here is an optimizer, a supplier score or an objective
of its own."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import Field, model_validator

from zaad.contracts import Record

SourcingProvenance = Literal["OPERATOR_DECLARED", "DERIVED_FROM_OPERATOR_HISTORY", "PHYSICAL_DEPENDENCY", "PUBLIC_PRIOR", "FALLBACK", "UNKNOWN"]
RiskKind = Literal["MANUFACTURER", "PLANT", "PACKAGING", "PORT", "ROUTE", "CARRIER", "3PL", "UPSTREAM_FACILITY", "OTHER"]
SwitchKind = Literal["SWITCHING", "QUALIFICATION", "SETUP"]
ShareScope = Literal["horizon", "period"]
WEAK_PROVENANCE: frozenset[str] = frozenset({"PUBLIC_PRIOR", "FALLBACK"})

# Resource bounds (contract level; the interactive API applies tighter caps before a model is built).
MAX_RISK_GROUPS = 200
MAX_GROUP_MEMBERS = 50
MAX_SHARE_CONSTRAINTS = 2000
MAX_SWITCHING_COSTS = 2000
MAX_INCUMBENT_SHARES = 2000
MAX_SOURCES_PER_PAIR = 64
INTERACTIVE_LIMITS = {"sources_per_pair": 8, "risk_groups": 50, "share_constraints": 200, "switching_costs": 100, "incumbent_shares": 200}


class SourceRiskGroup(Record):
    """Sources that fail together. `correlation` is the share of each member's supply shock that is
    common to the group (1 = the members move as one); the frozen shared-domain machinery (declared
    resource failure domains, itinerary nodes) stays underneath. A declared group is a claim, so its
    provenance cannot be UNKNOWN; PUBLIC_PRIOR and FALLBACK are reported as weak evidence."""
    id: str = Field(min_length=1, max_length=80)
    kind: RiskKind
    members: tuple[str, ...] = Field(min_length=2, max_length=MAX_GROUP_MEMBERS)
    correlation: float = Field(default=1., gt=0, le=1, allow_inf_nan=False)
    provenance: SourcingProvenance
    evidence: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def shape(self):
        if len(set(self.members)) != len(self.members):
            raise ValueError(f"risk group {self.id}: duplicate member")
        if self.provenance == "UNKNOWN":
            raise ValueError(f"risk group {self.id}: a declared dependency needs a provenance other than UNKNOWN")
        return self


class SourceShareConstraint(Record):
    """Declared share limits of one source in the commitment of its SKU / destination pair. Shares are
    fractions of purchased units; `committed_units` is a floor in units over the plan window. Scope
    "horizon": on the plan's cumulative commitment; "period": in every period with a purchase."""
    sku: str
    destination: str
    source: str
    minimum_share: float = Field(default=0., ge=0, le=1, allow_inf_nan=False)
    maximum_share: float = Field(default=1., ge=0, le=1, allow_inf_nan=False)
    committed_units: float = Field(default=0., ge=0, allow_inf_nan=False)
    scope: ShareScope = "horizon"
    provenance: SourcingProvenance
    reference: str = Field(default="", max_length=200)

    @model_validator(mode="after")
    def ordered(self):
        if self.minimum_share > self.maximum_share:
            raise ValueError(f"share constraint {self.source}: minimum share above maximum share")
        if self.provenance == "UNKNOWN":
            raise ValueError(f"share constraint {self.source}: a declared limit needs a provenance other than UNKNOWN")
        return self


class SourceSwitchingCost(Record):
    """A cost the operator actually pays to start buying from a source that is not in the incumbent
    mix (qualification, set-up, switching). Charged once in the plan, only when the source receives
    quantity. Never assumed: absent means zero."""
    source: str
    cost: float = Field(ge=0, allow_inf_nan=False)
    kind: SwitchKind = "SWITCHING"
    provenance: SourcingProvenance

    @model_validator(mode="after")
    def declared(self):
        if self.provenance == "UNKNOWN":
            raise ValueError(f"switching cost {self.source}: needs a provenance other than UNKNOWN")
        return self


class IncumbentSourceShare(Record):
    """The operator's current mix: the share of the SKU / destination commitment bought from `source`."""
    sku: str
    destination: str
    source: str
    share: float = Field(gt=0, le=1, allow_inf_nan=False)
    provenance: SourcingProvenance


class SourcingPortfolio(Record):
    mode: Literal["PORTFOLIO"] = "PORTFOLIO"
    risk_groups: tuple[SourceRiskGroup, ...] = Field(default=(), max_length=MAX_RISK_GROUPS)
    share_constraints: tuple[SourceShareConstraint, ...] = Field(default=(), max_length=MAX_SHARE_CONSTRAINTS)
    switching_costs: tuple[SourceSwitchingCost, ...] = Field(default=(), max_length=MAX_SWITCHING_COSTS)
    incumbent_shares: tuple[IncumbentSourceShare, ...] = Field(default=(), max_length=MAX_INCUMBENT_SHARES)
    # Exact pruning: a source with no eligible period (unapproved, blocked, expired quote, zero capacity,
    # physics-ineligible) gets no pack / activation binaries. Off for equivalence runs.
    prune_zero_capability: bool = True


@dataclass(frozen=True)
class Sourcing:
    """Resolved, read-only sourcing view of one request."""
    portfolio: SourcingPortfolio
    groups_of: dict[str, tuple[SourceRiskGroup, ...]]     # source id -> groups it belongs to (>= 2 members)
    shares: dict[tuple[str, str], tuple[SourceShareConstraint, ...]]   # (sku, destination) -> constraints
    switching: dict[str, SourceSwitchingCost]              # source id -> declared cost
    incumbent_mix: dict[tuple[str, str], dict[str, float]]  # (sku, destination) -> {source: share}
    incumbent_sources: frozenset[str]                      # sources in the incumbent mix (declared or dated orders)

    def switching_cost(self, source: str) -> float:
        row = self.switching.get(source)
        return float(row.cost) if row is not None and source not in self.incumbent_sources else 0.

    def weak_evidence(self, source: str) -> bool:
        return any(g.provenance in WEAK_PROVENANCE for g in self.groups_of.get(source, ()))


def resolve(req) -> Sourcing | None:
    """The request's sourcing view, or None for a frozen request."""
    portfolio = getattr(req, "sourcing", None)
    if portfolio is None:
        return None
    groups_of: dict[str, list[SourceRiskGroup]] = {}
    for g in portfolio.risk_groups:
        for member in g.members:
            groups_of.setdefault(member, []).append(g)
    shares: dict[tuple[str, str], list[SourceShareConstraint]] = {}
    for c in portfolio.share_constraints:
        shares.setdefault((c.sku, c.destination), []).append(c)
    mix: dict[tuple[str, str], dict[str, float]] = {}
    for row in portfolio.incumbent_shares:
        mix.setdefault((row.sku, row.destination), {})[row.source] = float(row.share)
    if mix:
        incumbent_sources = frozenset(s for pair in mix.values() for s in pair)
    elif getattr(req, "incumbent_orders", ()):
        incumbent_sources = frozenset(x.source for x in req.incumbent_orders if x.quantity > 0)
    else:
        # the frozen rule projections buy from the cheapest landed source of each pair
        incumbent_sources = frozenset(_primary_sources(req))
    return Sourcing(portfolio, {k: tuple(v) for k, v in groups_of.items()}, {k: tuple(v) for k, v in shares.items()},
                    {c.source: c for c in portfolio.switching_costs}, mix, incumbent_sources)


def _primary_sources(req) -> list[str]:
    best: dict[tuple[str, str], tuple[float, str]] = {}
    for s in req.sources:
        if s.approved and s.compliance == "cleared":
            key = (s.unit_price + s.freight_per_unit + s.handling_per_unit, s.id)
            pair = (s.sku, s.destination)
            if pair not in best or key < best[pair]:
                best[pair] = key
    return [v[1] for v in best.values()]
