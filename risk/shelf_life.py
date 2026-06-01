"""Shelf-life decay: how much of a lot can be safely promised for a delivery.

The committable value of a lot depends on its remaining shelf life relative to
when the buyer actually needs it. A lot with 10 days left and a lot with 2 days
left are not interchangeable for a delivery five days out: the first is safe,
the second will be expired before it ships.

We weight each lot by a usability factor w(R; L, B):

    R = remaining shelf life in days (expiration_date - as_of_date)
    L = delivery lead time in days  (how far out the commitment is)
    B = safety buffer in days       (category-dependent)

    R <= L           -> 0   (expired before delivery)
    L < R < L + B    -> (R - L) / B   (usable, but inside the buffer; risky)
    R >= L + B       -> 1   (safe)

The current production ATP formula is the special case L = 0, B = 3 with a hard
step (weight 0 below 3 days, 1 above). This generalizes it: the delivery date
becomes explicit, and the cliff becomes a ramp so a lot one day inside the
buffer is not treated identically to one already expired.

Buffers are per product category because shelf life varies widely: leafy greens
need more buffer than roots. Buffers are configurable; the defaults below are
conservative starting points, not claims of precision.
"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

# Conservative default safety buffers in days, by product category. Tunable per
# operator. The default applies to any category not listed.
DEFAULT_BUFFER_DAYS: dict[str, float] = {
    "Leafy Greens": 4.0,
    "Herbs": 3.0,
    "Berries": 3.0,
    "Vegetables": 5.0,
    "Root Vegetables": 14.0,
    "Roots": 14.0,
    "Fruit": 6.0,
}
_DEFAULT_BUFFER = 5.0


def shelf_life_weight(remaining_days: float, lead_time_days: float,
                      buffer_days: float) -> float:
    """Usability weight in [0, 1] for a lot given delivery lead time and buffer.

    See module docstring for the piecewise definition. A non-positive buffer
    collapses to a hard step at the lead time.
    """
    R = float(remaining_days)
    L = float(lead_time_days)
    B = float(buffer_days)

    if R <= L:
        return 0.0
    if B <= 0:
        return 1.0  # past the lead time with no buffer requirement
    if R >= L + B:
        return 1.0
    return (R - L) / B


def buffer_for_category(category: str | None,
                        buffers: dict[str, float] | None = None) -> float:
    """Look up the safety buffer for a product category, with a default."""
    table = buffers if buffers is not None else DEFAULT_BUFFER_DAYS
    if category is None:
        return _DEFAULT_BUFFER
    return float(table.get(category, _DEFAULT_BUFFER))


def weighted_available_by_product(
    conn: duckdb.DuckDBPyConnection,
    as_of_date: date,
    lead_time_days: float,
    buffers: dict[str, float] | None = None,
) -> dict[str, dict[str, float]]:
    """Shelf-life-weighted committable quantity per product.

    Joins inventory lots to product categories, computes each lot's remaining
    shelf life relative to as_of_date, applies the usability weight for the
    given delivery lead time, and sums per product.

    Returns a dict keyed by product_name with:
        on_hand_kg        raw quantity on hand
        weighted_kg       shelf-life-weighted committable quantity
        discount_kg       on_hand_kg - weighted_kg (lost to shelf-life risk)
        lead_time_days    echoed back for transparency
    """
    df = conn.execute("""
        SELECT l.product_id,
               l.product_name,
               l.quantity_on_hand,
               l.expiration_date,
               p.category
        FROM stg_inventory_lots l
        LEFT JOIN stg_products p ON l.product_id = p.product_id
        WHERE l.quantity_on_hand IS NOT NULL
    """).df()

    out: dict[str, dict[str, float]] = {}
    if df.empty:
        return out

    for _, row in df.iterrows():
        name = row["product_name"]
        qty = float(row["quantity_on_hand"]) if pd.notna(row["quantity_on_hand"]) else 0.0
        exp = row["expiration_date"]
        category = row["category"] if pd.notna(row.get("category")) else None
        buf = buffer_for_category(category, buffers)

        if pd.isna(exp):
            # No expiration on record: treat as fully usable but flag nothing.
            weight = 1.0
        else:
            # Normalize to a plain date (handles datetime.date, pandas Timestamp,
            # and strings uniformly; Timestamp subclasses date so test directly).
            exp_date = pd.Timestamp(exp).date()
            remaining = (exp_date - as_of_date).days
            weight = shelf_life_weight(remaining, lead_time_days, buf)

        entry = out.setdefault(name, {"on_hand_kg": 0.0, "weighted_kg": 0.0,
                                      "discount_kg": 0.0,
                                      "lead_time_days": float(lead_time_days)})
        entry["on_hand_kg"] += qty
        entry["weighted_kg"] += qty * weight

    for entry in out.values():
        entry["discount_kg"] = round(entry["on_hand_kg"] - entry["weighted_kg"], 2)
        entry["on_hand_kg"] = round(entry["on_hand_kg"], 2)
        entry["weighted_kg"] = round(entry["weighted_kg"], 2)

    return out
