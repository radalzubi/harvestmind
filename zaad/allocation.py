"""Auditable shortage allocation helper; no involuntary contractual overrides."""
from __future__ import annotations

from pydantic import Field

from zaad.contracts import Record


class CustomerLine(Record):
    id: str = Field(min_length=1, max_length=80)
    quantity: float = Field(ge=0)
    contractual_minimum: float = Field(default=0, ge=0)
    priority: int = Field(default=0, ge=0, le=100)
    unit_margin: float = Field(ge=0)


def allocate(available: float, lines: tuple[CustomerLine, ...]) -> dict:
    """Minimum obligations then explicit priority/margin; ties pro-rata, no customer IDs as rank.

    Infeasible minima produce no recommended allocation. This standalone helper
    is not yet an order-line OTIF optimizer or part of product-total simulation.
    """
    import math
    if not math.isfinite(available) or available < 0:
        raise ValueError("available quantity must be finite and nonnegative")
    if len({x.id for x in lines}) != len(lines):
        raise ValueError("duplicate customer line")
    if any(x.contractual_minimum > x.quantity for x in lines):
        raise ValueError("contractual minimum exceeds requested quantity")
    minimum = sum(x.contractual_minimum for x in lines)
    if available < minimum:
        return {"status": "INFEASIBLE_MINIMA", "allocation": {},
                "unavoidable_shortage": sum(x.quantity for x in lines)-available}
    result = {x.id:x.contractual_minimum for x in lines}
    left = available-minimum
    for key in sorted({(x.priority,x.unit_margin) for x in lines}, reverse=True):
        group = [x for x in lines if (x.priority,x.unit_margin) == key]
        gap = sum(x.quantity-result[x.id] for x in group)
        fraction = min(1.,left/gap) if gap else 0.
        for line in group:
            qty = fraction*(line.quantity-result[line.id])
            result[line.id] += qty
            left -= qty
    return {"status": "REVIEW_REQUIRED", "allocation": result,
            "unavoidable_shortage": max(0.,sum(x.quantity for x in lines)-available)}
