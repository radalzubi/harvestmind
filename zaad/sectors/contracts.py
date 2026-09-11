"""Sector operating physics: one typed, default-off contract attached to the frozen request.

Three sectors share one ZAAD engine (P0 protection / recovery, P1 purchasing economics, P2 network
placement); what differs between them is the physical reality the engine optimises over. This module
declares that reality per SKU - storage state, life at receipt, sellable life, shipment weight - and
resolves it, together with the optional location / lane eligibility of the frozen records, into one
read-only `Physics` view the model, the settlement, the continuation valuation and the explanations
consult. `resolve(req)` returns None for a request that declares no sector and no profile, and every
consumer then takes the frozen path untouched: the physics code is unreachable on a legacy request.

Nothing here is an optimizer, an ownership class or an objective term.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import Field, model_validator

from zaad.contracts import Record

SectorMode = Literal["COMMERCIAL", "PRODUCE", "MEAT_SEAFOOD"]
StorageState = Literal["AMBIENT", "CHILLED", "FROZEN"]
STORAGE_STATES: tuple[str, ...] = ("AMBIENT", "CHILLED", "FROZEN")
SECTOR_MODES: tuple[str, ...] = ("COMMERCIAL", "PRODUCE", "MEAT_SEAFOOD")
PhysicsProvenance = Literal["OPERATOR_OBSERVED", "OPERATOR_DECLARED", "DERIVED_FROM_OPERATOR_HISTORY", "PUBLIC_PRIOR", "FALLBACK", "UNKNOWN"]

# Fields whose declared value must carry a provenance other than UNKNOWN (a declared number is a claim).
DECLARABLE = ("storage_state", "age_at_receipt_periods", "age_at_receipt_by_source",
              "minimum_remaining_life_at_receipt", "minimum_remaining_life_at_sale", "weight_per_unit")


class SkuPhysics(Record):
    """Operating physics of one SKU. Units: periods of the request (`period_days`) for every life
    field; the operator's mass unit for weight. Every declared field affects feasibility, cost,
    uncertainty or settlement; none is decorative."""
    sku: str
    sector: SectorMode
    # The state the SKU must be kept in. There are no thaw / freeze transitions: a chilled SKU and a
    # frozen SKU are different SKUs with different lives. AMBIENT is the neutral (legacy) state.
    storage_state: StorageState = "AMBIENT"
    # Life already elapsed when a purchase arrives (imports), per SKU with optional per-source values;
    # remaining life at receipt = shelf_life - age. 0 (default) is the frozen behaviour.
    age_at_receipt_periods: int = Field(default=0, ge=0, le=519)
    age_at_receipt_by_source: dict[str, int] = {}
    # An arrival (purchase or transfer) with less remaining life than this is not usable: the source
    # or the cohort's lane is capped at zero and the settlement refuses the receipt.
    minimum_remaining_life_at_receipt: int = Field(default=0, ge=0, le=519)
    # A cohort is sellable at period t only while expiry - t > this; unsellable stock stays physical
    # (holding, disposal) but cannot serve and earns salvage only in continuation.
    minimum_remaining_life_at_sale: int = Field(default=0, ge=0, le=519)
    # Shipment weight cap with SupplierTerms.max_shipment_weight; None = no weight physics.
    weight_per_unit: float | None = Field(default=None, gt=0)
    provenance: dict[str, PhysicsProvenance] = {}

    @model_validator(mode="after")
    def declared_values_carry_provenance(self):
        defaults = {"storage_state": "AMBIENT", "age_at_receipt_periods": 0, "age_at_receipt_by_source": {},
                    "minimum_remaining_life_at_receipt": 0, "minimum_remaining_life_at_sale": 0, "weight_per_unit": None}
        for field in DECLARABLE:
            value = getattr(self, field)
            if value != defaults[field] and self.provenance.get(field, "UNKNOWN") == "UNKNOWN":
                raise ValueError(f"sku physics {self.sku}: {field} is declared without a provenance other than UNKNOWN")
        for source, age in self.age_at_receipt_by_source.items():
            if not isinstance(age, int) or age < 0 or age > 519:
                raise ValueError(f"sku physics {self.sku}: age at receipt for source {source} must be an integer number of periods in [0, 519]")
        return self


def neutral(sku: str, sector: str) -> SkuPhysics:
    """The sector's neutral profile: declaring a sector alone changes nothing about a SKU."""
    return SkuPhysics(sku=sku, sector=sector)  # type: ignore[arg-type]


@dataclass(frozen=True)
class Physics:
    """Resolved, read-only physics of one request."""
    sector_default: str | None
    sku: dict[str, SkuPhysics]
    shelf_life: dict[str, int]
    location_states: dict[str, frozenset[str]]     # empty = unrestricted
    lane_states: dict[str, frozenset[str]]         # empty = unrestricted
    lane_of_source: dict[str, str]                 # source id -> destination location
    declared: frozenset[str]                       # SKUs with a declared (non-neutral) profile

    def state(self, sku: str) -> str:
        return self.sku[sku].storage_state

    def location_ok(self, sku: str, location: str) -> bool:
        allowed = self.location_states.get(location, frozenset())
        return not allowed or self.state(sku) in allowed

    def lane_ok(self, sku: str, lane: str) -> bool:
        allowed = self.lane_states.get(lane, frozenset())
        return not allowed or self.state(sku) in allowed

    def age_at_receipt(self, sku: str, source: str) -> int:
        p = self.sku[sku]
        return int(p.age_at_receipt_by_source.get(source, p.age_at_receipt_periods))

    def receipt_life(self, sku: str, source: str) -> int:
        """Remaining life (periods) of a purchase from `source` on arrival."""
        return int(self.shelf_life[sku]) - self.age_at_receipt(sku, source)

    def min_receipt(self, sku: str) -> int:
        return int(self.sku[sku].minimum_remaining_life_at_receipt)

    def min_sale(self, sku: str) -> int:
        return int(self.sku[sku].minimum_remaining_life_at_sale)

    def sellable(self, sku: str, expiry: int, t: int) -> bool:
        """A cohort with the given expiry period is sellable at period t."""
        return expiry - t > self.min_sale(sku)

    def receivable(self, sku: str, expiry: int, due: int) -> bool:
        """A cohort arriving at `due` with the given expiry has enough life to be received."""
        return expiry - due > self.min_receipt(sku)

    def weight(self, sku: str) -> float | None:
        return self.sku[sku].weight_per_unit

    def any_life_rule(self) -> bool:
        return any(p.minimum_remaining_life_at_sale or p.minimum_remaining_life_at_receipt or p.age_at_receipt_periods or p.age_at_receipt_by_source
                   for p in self.sku.values())


def resolve(req) -> Physics | None:
    """The request's physics, or None for a legacy request (no sector mode, no profile)."""
    mode = getattr(req, "sector_mode", None)
    profiles = tuple(getattr(req, "sku_physics", ()) or ())
    if mode is None and not profiles:
        return None
    by_sku: dict[str, SkuPhysics] = {p.sku: p for p in profiles}
    declared = frozenset(by_sku)
    for s in req.skus:
        if s.id not in by_sku:
            by_sku[s.id] = neutral(s.id, mode or "COMMERCIAL")
    return Physics(sector_default=mode, sku=by_sku, shelf_life={s.id: int(s.shelf_life) for s in req.skus},
                   location_states={loc.id: frozenset(getattr(loc, "storage_states", ()) or ()) for loc in req.locations},
                   lane_states={a.id: frozenset(getattr(a, "storage_states", ()) or ()) for a in req.transfers},
                   lane_of_source={s.id: s.destination for s in req.sources}, declared=declared)
