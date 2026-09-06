"""One unit-aware zero policy for quantities and obligations.

Solver residuals leave quantities such as 4e-7 units on purchase, transfer
and amendment variables. Extraction, replay and settlement used to apply
three different cut-offs (1e-7, 1e-7 and 1e-6), so a pipeline order could be
created from solver dust and then fail settlement's exclusivity rule because
none of its options carried anything. Every layer now asks this module.

The threshold scales with the smallest physical pack the source declares
(``multiple``, case, pallet or transport multiple): dust is a millionth of a
pack, never less than 1e-9 units. A source with no declared pack is
continuous, and a millionth of a unit is dust. A real order of half a unit,
a tenth of a case, or one carton is never dust.
"""
from __future__ import annotations

from typing import Iterable

DUST_FRACTION = 1e-6
ABSOLUTE_FLOOR = 1e-9


def resolution(multiples: Iterable[float]) -> float:
    """Smallest declared positive pack size, or 1.0 for a continuous quantity."""
    packs = [float(m) for m in multiples if m and m > 0]
    return min(packs) if packs else 1.0


def dust_threshold(pack: float = 1.0) -> float:
    """A millionth of the smallest pack; a continuous quantity (no pack) counts as one unit."""
    unit = pack if pack and pack > 0 else 1.0
    return max(ABSOLUTE_FLOOR, DUST_FRACTION * unit)


def is_dust(quantity: float, pack: float = 1.0) -> bool:
    """True for quantities that are solver residue rather than an order."""
    return abs(quantity) < dust_threshold(pack)


def source_pack(source) -> float:
    return resolution((source.multiple, source.case_multiple, source.pallet_multiple, source.transport_multiple))


def po_closed(po, source) -> bool:
    """An open PO whose remaining units are dust is closed for every layer."""
    return is_dust(po.remaining, source_pack(source))
