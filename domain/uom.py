"""Units of measure and discrete pack structure.

Quantities inside the engine are floats in a product's BASE unit (kg for
produce, each for packaged goods). Nothing here changes that. What this
module adds is the discipline around it: a quantity always knows its unit,
conversion between units is explicit, and the pack hierarchy a supplier
actually sells in (each -> case -> layer -> pallet) is a first-class object
the optimizer can round against.

The alternative, which is what most inventory tools do, is to let a
recommendation of 437.36 units reach a buyer who can only order cases of
12. That number is not an order; it is homework.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class Unit(str, Enum):
    EACH = "each"
    CASE = "case"
    LAYER = "layer"
    PALLET = "pallet"
    KG = "kg"
    LB = "lb"
    CRATE = "crate"


_MASS_TO_KG = {Unit.KG: 1.0, Unit.LB: 0.45359237}


@dataclass(frozen=True)
class Quantity:
    """A number that refuses to forget what it counts."""

    value: float
    unit: Unit

    def __post_init__(self) -> None:
        if not math.isfinite(self.value):
            raise ValueError(f"quantity must be finite, got {self.value}")
        if self.value < 0:
            raise ValueError(f"quantity must be non-negative, got {self.value}")

    def to_kg(self) -> "Quantity":
        if self.unit not in _MASS_TO_KG:
            raise ValueError(f"{self.unit.value} is not a mass unit; use a PackSpec")
        return Quantity(self.value * _MASS_TO_KG[self.unit], Unit.KG)

    def __add__(self, other: "Quantity") -> "Quantity":
        if other.unit != self.unit:
            raise ValueError(
                f"cannot add {self.unit.value} to {other.unit.value} without "
                "an explicit conversion")
        return Quantity(self.value + other.value, self.unit)


@dataclass(frozen=True)
class PackSpec:
    """How a supplier physically sells a SKU.

    ``units_per_case`` is mandatory: a case is the smallest thing a
    distributor orders. Layers and pallets are optional levels above it.
    ``order_multiple`` names the level orders must be a whole number of.
    ``moq_units`` is a minimum in base units, applied only when an order
    is placed at all (zero is always allowed; that is what a binary
    variable is for).
    """

    units_per_case: int = 1
    cases_per_layer: int | None = None
    layers_per_pallet: int | None = None
    order_multiple: Unit = Unit.CASE
    moq_units: float = 0.0
    max_units_per_order: float | None = None

    def __post_init__(self) -> None:
        if self.units_per_case < 1:
            raise ValueError("units_per_case must be >= 1")
        for name in ("cases_per_layer", "layers_per_pallet"):
            v = getattr(self, name)
            if v is not None and v < 1:
                raise ValueError(f"{name} must be >= 1 when given")
        if self.order_multiple == Unit.LAYER and self.cases_per_layer is None:
            raise ValueError("ordering by layer needs cases_per_layer")
        if self.order_multiple == Unit.PALLET and (
                self.cases_per_layer is None or self.layers_per_pallet is None):
            raise ValueError("ordering by pallet needs cases_per_layer and "
                             "layers_per_pallet")
        if self.order_multiple not in (Unit.EACH, Unit.CASE, Unit.LAYER, Unit.PALLET):
            raise ValueError(f"order_multiple must be a pack level, got "
                             f"{self.order_multiple.value}")
        if self.moq_units < 0 or not math.isfinite(self.moq_units):
            raise ValueError("moq_units must be finite and >= 0")
        if self.max_units_per_order is not None:
            if self.max_units_per_order <= 0:
                raise ValueError("max_units_per_order must be positive")
            if self.moq_units > self.max_units_per_order:
                raise ValueError("moq_units exceeds max_units_per_order")
        if self.moq_units and self.lot_units > 0:
            # An MOQ that is not a whole lot cannot be met exactly; round it
            # up now so the optimizer never sees an unsatisfiable minimum.
            object.__setattr__(
                self, "moq_units",
                float(math.ceil(self.moq_units / self.lot_units) * self.lot_units))

    @property
    def units_per_layer(self) -> int | None:
        return None if self.cases_per_layer is None else \
            self.units_per_case * self.cases_per_layer

    @property
    def units_per_pallet(self) -> int | None:
        if self.cases_per_layer is None or self.layers_per_pallet is None:
            return None
        return self.units_per_case * self.cases_per_layer * self.layers_per_pallet

    @property
    def lot_units(self) -> float:
        """Base units in one order multiple. Orders are integer multiples of this."""
        if self.order_multiple == Unit.EACH:
            return 1.0
        if self.order_multiple == Unit.CASE:
            return float(self.units_per_case)
        if self.order_multiple == Unit.LAYER:
            return float(self.units_per_layer or self.units_per_case)
        return float(self.units_per_pallet or self.units_per_case)

    @property
    def is_discrete(self) -> bool:
        return self.lot_units != 1.0 or self.moq_units > 0 \
            or self.max_units_per_order is not None

    def lots(self, units: float) -> int:
        """Whole lots needed to cover ``units``, rounding up."""
        if units <= 0:
            return 0
        return int(math.ceil(units / self.lot_units - 1e-9))

    def describe(self, units: float) -> str:
        lots = self.lots(units)
        return f"{lots} {self.order_multiple.value}(s) = {lots * self.lot_units:g} units"


# Continuous produce: kilograms, no pack structure, no minimum.
CONTINUOUS = PackSpec(units_per_case=1, order_multiple=Unit.EACH)


def round_to_pack(units: float, spec: PackSpec) -> float:
    """Round an order UP to the nearest whole lot and apply the MOQ.

    Up rather than to-nearest: rounding a replenishment quantity down is a
    decision to accept a shortage the optimizer did not price, and a
    ceiling of one extra case is the cheaper mistake almost everywhere a
    case pack exists. A zero order stays zero.
    """
    if units <= 0:
        return 0.0
    q = spec.lots(units) * spec.lot_units
    if spec.moq_units and q < spec.moq_units:
        q = spec.moq_units
    if spec.max_units_per_order is not None:
        q = min(q, spec.max_units_per_order)
    return float(q)
