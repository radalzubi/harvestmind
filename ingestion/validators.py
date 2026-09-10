"""Hard validation for staging-table uploads.

Run BEFORE rows are inserted. Errors are blocking: the upload is rejected
with a message naming the column, the rule violated, and example rows so the
operator can fix the file. Warnings are non-blocking: the rows load, but the
issue is surfaced in the data-quality scorecard.

Rules (per table, applied to the post-column-mapping DataFrame):

  errors (reject the file)
    - negative values in any quantity / price / cost / value column
    - reversed date pairs: expiration_date < arrival_date (lots),
      delivery_date < order_date (buyer orders)
    - unparseable values in a required date column

  warnings (load, but report)
    - unparseable values in an optional date column
    - unrecognized unit values (units are names, not facts to reject on)
    - implausible magnitudes: quantity > 1e6 per row, price/cost > 1e4 per kg
    - dates more than 2 years in the future (except expiration dates)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import pandas as pd

# The only tables this validator knows how to vet. Anything else must be
# rejected (fail-closed) rather than silently passing with zero rules — a
# write to an unrecognized table is never legitimate on the intake path.
KNOWN_STAGING_TABLES: frozenset[str] = frozenset({
    "stg_fmcg_suppliers", "stg_fmcg_economics",
    "stg_fmcg_skus", "stg_fmcg_orders", "stg_fmcg_purchase_orders",
    "stg_fmcg_receipts", "stg_fmcg_inventory", "stg_fmcg_promotions",
    "stg_products",
    "stg_supplier_deliveries",
    "stg_inventory_lots",
    "stg_buyer_orders",
    "stg_waste_adjustments",
})

# Columns subject to the non-negativity rule, per staging table.
_REQUIRED_QUANTITY_COLUMNS: dict[str, list[str]] = {
    "stg_fmcg_orders": ["qty_ordered"], "stg_fmcg_purchase_orders": ["qty_ordered"],
    "stg_fmcg_receipts": ["qty_received"], "stg_fmcg_inventory": ["on_hand"],
    "stg_inventory_lots": ["quantity_on_hand"],
    "stg_buyer_orders": ["requested_quantity"],
    "stg_waste_adjustments": ["quantity_lost"],
}

QUANTITY_COLUMNS: dict[str, list[str]] = {
    "stg_products": [],
    "stg_supplier_deliveries": [
        "ordered_quantity", "delivered_quantity",
        "accepted_quantity", "rejected_quantity", "unit_cost",
    ],
    "stg_inventory_lots": ["quantity_on_hand", "committed_quantity"],
    "stg_buyer_orders": [
        "requested_quantity", "fulfilled_quantity",
        "substituted_quantity", "sales_price",
    ],
    "stg_waste_adjustments": ["quantity_lost", "estimated_value_lost"],
}

# (earlier_col, later_col) pairs that must not be reversed.
DATE_ORDER_RULES: dict[str, list[tuple[str, str]]] = {
    "stg_inventory_lots": [("arrival_date", "expiration_date")],
    "stg_buyer_orders": [("order_date", "delivery_date")],
}

# Date columns whose values must parse for the row to be usable at all.
REQUIRED_DATE_COLUMNS: dict[str, list[str]] = {
    "stg_fmcg_orders": ["order_date"], "stg_fmcg_purchase_orders": ["po_date"],
    "stg_fmcg_receipts": ["receipt_date"], "stg_fmcg_inventory": ["snapshot_date"],
    "stg_fmcg_promotions": ["week_start"],
    "stg_supplier_deliveries": ["delivery_date"],
    "stg_buyer_orders": [],
    "stg_inventory_lots": [],
    "stg_waste_adjustments": [],
    "stg_products": [],
}

OPTIONAL_DATE_COLUMNS: dict[str, list[str]] = {
    "stg_supplier_deliveries": [],
    "stg_buyer_orders": ["order_date", "delivery_date"],
    "stg_inventory_lots": ["arrival_date", "expiration_date"],
    "stg_waste_adjustments": ["date"],
    "stg_products": [],
}

KNOWN_UNITS: frozenset[str] = frozenset({
    "kg", "lb", "lbs", "case", "cases", "each", "box", "boxes",
    "bunch", "bunches", "pint", "pints", "flat", "flats", "dozen",
})

_MAX_PLAUSIBLE_QTY = 1_000_000.0      # kg per row
_MAX_PLAUSIBLE_PRICE = 10_000.0       # $ per kg
_FUTURE_HORIZON_DAYS = 730            # dates beyond this are suspicious

# Future-date plausibility applies to these (expiration dates legitimately
# sit in the future, but not years out for fresh produce either — still,
# only warn, never block, on dates).
_FUTURE_CHECK_COLUMNS: dict[str, list[str]] = {
    "stg_supplier_deliveries": ["delivery_date"],
    "stg_buyer_orders": ["order_date", "delivery_date"],
    "stg_inventory_lots": ["arrival_date"],
    "stg_waste_adjustments": ["date"],
    "stg_products": [],
}


@dataclass
class StagingValidation:
    """Result of validating one staging-table DataFrame."""
    table: str
    n_rows: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return {
            "table": self.table,
            "n_rows": self.n_rows,
            "ok": self.ok,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


def _example_rows(mask: pd.Series, limit: int = 3) -> str:
    """Human-readable 1-based row numbers for the first few offenders."""
    idx = [str(i + 2) for i in mask[mask].index[:limit]]  # +2: header + 1-base
    suffix = "…" if int(mask.sum()) > limit else ""
    return f"rows {', '.join(idx)}{suffix}"


def validate_staging_df(
    table: str,
    df: pd.DataFrame,
    today: date | None = None,
) -> StagingValidation:
    """Validate a post-column-mapping DataFrame bound for a staging table.

    Returns a StagingValidation; ``result.ok is False`` means the file must
    be rejected (do not insert).
    """
    result = StagingValidation(table=table, n_rows=len(df))
    # Fail closed: an unrecognized table has no rules, which previously meant
    # it passed validation vacuously. Reject it so callers cannot smuggle a
    # write into a non-staging table through a validation no-op.
    if table not in KNOWN_STAGING_TABLES:
        result.errors.append(
            f"Unknown staging table {table!r}. Valid tables: "
            f"{sorted(KNOWN_STAGING_TABLES)}."
        )
        return result
    if df.empty:
        return result
    ref_today = today or date.today()

    # ── exact duplicate rows → warning ───────────────────────────────────
    # A duplicated line in an export usually means a re-run export or a
    # double-keyed entry. Loading it doubles a quantity silently, so it is
    # surfaced with row numbers; the operator decides whether it is real.
    dup_mask = df.duplicated(keep="first")
    if dup_mask.any():
        result.warnings.append(
            f"{int(dup_mask.sum())} exact duplicate row(s) "
            f"({_example_rows(dup_mask)}) — loaded as-is; remove them if "
            f"they are a re-export rather than repeated transactions."
        )

    # ── required quantities that are missing → error ─────────────────────
    # A blank quantity is not zero. Treating it as zero would understate
    # demand or stock without any trace, so the file is rejected with the
    # rows named.
    for col in _REQUIRED_QUANTITY_COLUMNS.get(table, []):
        if col in df.columns:
            missing = pd.to_numeric(df[col], errors="coerce").isna()
            if missing.any():
                result.errors.append(
                    f"{col}: {int(missing.sum())} missing or non-numeric "
                    f"value(s) ({_example_rows(missing)}). A blank quantity "
                    f"is not zero; fill it in or drop the row."
                )

    # ── negatives in quantity / price columns → error ────────────────────
    for col in QUANTITY_COLUMNS.get(table, []):
        if col not in df.columns:
            continue
        vals = pd.to_numeric(df[col], errors="coerce")
        neg = vals < 0
        if neg.any():
            result.errors.append(
                f"{col}: {int(neg.sum())} negative value(s) "
                f"({_example_rows(neg)}). Quantities and prices must be ≥ 0 — "
                f"if these are corrections, record them as waste adjustments "
                f"or remove the sign."
            )
        # implausible magnitude → warning
        limit = _MAX_PLAUSIBLE_PRICE if ("price" in col or "cost" in col or "value" in col) \
            else _MAX_PLAUSIBLE_QTY
        big = vals > limit
        if big.any():
            result.warnings.append(
                f"{col}: {int(big.sum())} value(s) above {limit:,.0f} "
                f"({_example_rows(big)}) — check the unit of measure."
            )

    # ── date parseability ────────────────────────────────────────────────
    parsed_dates: dict[str, pd.Series] = {}
    for col in (REQUIRED_DATE_COLUMNS.get(table, [])
                + OPTIONAL_DATE_COLUMNS.get(table, [])):
        if col not in df.columns:
            continue
        parsed = pd.to_datetime(df[col], errors="coerce")
        parsed_dates[col] = parsed
        bad = parsed.isna() & df[col].notna()
        if bad.any():
            msg = (
                f"{col}: {int(bad.sum())} unparseable date(s) "
                f"({_example_rows(bad)}). Use an unambiguous format like "
                f"YYYY-MM-DD."
            )
            if col in REQUIRED_DATE_COLUMNS.get(table, []):
                result.errors.append(msg)
            else:
                result.warnings.append(msg)

    # ── reversed date pairs → error ──────────────────────────────────────
    for earlier, later in DATE_ORDER_RULES.get(table, []):
        if earlier in parsed_dates and later in parsed_dates:
            a, b = parsed_dates[earlier], parsed_dates[later]
            reversed_mask = a.notna() & b.notna() & (b < a)
            if reversed_mask.any():
                result.errors.append(
                    f"{later} before {earlier}: {int(reversed_mask.sum())} "
                    f"row(s) ({_example_rows(reversed_mask)}). "
                    f"Dates appear reversed — check for swapped columns or "
                    f"day/month ambiguity."
                )

    # ── implausibly distant future dates → warning ───────────────────────
    horizon = pd.Timestamp(ref_today + timedelta(days=_FUTURE_HORIZON_DAYS))
    for col in _FUTURE_CHECK_COLUMNS.get(table, []):
        if col in parsed_dates:
            far = parsed_dates[col] > horizon
            if far.any():
                result.warnings.append(
                    f"{col}: {int(far.sum())} date(s) more than 2 years in "
                    f"the future ({_example_rows(far)}) — check for typos."
                )

    # ── unit sanity → warning ────────────────────────────────────────────
    if "unit" in df.columns:
        units = df["unit"].dropna().astype(str).str.strip().str.lower()
        unknown = sorted(set(units) - KNOWN_UNITS - {""})
        if unknown:
            result.warnings.append(
                f"unit: unrecognized value(s) {unknown[:5]} — quantities are "
                f"interpreted as recorded; mixed units within a product will "
                f"distort totals."
            )

    return result


def validate_loaded_tables(conn) -> dict[str, dict]:
    """Run the validators over already-loaded staging tables.

    Used by the data-quality scorecard so violations that pre-date the
    validator (or arrived through other paths) are still surfaced.
    """
    out: dict[str, dict] = {}
    for table in QUANTITY_COLUMNS:
        try:
            df = conn.execute(f"SELECT * FROM {table}").df()  # noqa: S608  # nosec B608 - table from allowlist iteration
        except Exception:
            continue
        out[table] = validate_staging_df(table, df).to_dict()
    return out
