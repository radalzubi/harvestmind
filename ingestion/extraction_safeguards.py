"""Post-extraction safeguards. Every one has a direct unit test.

These run on EVERY ExtractionResult — mock, real, or fallback — after the
confidence policy. They are pure functions over the result so each rule
can be tested in isolation and none can be skipped by a code path.

S1  no silent inference: every field carries inference_source
S2  consistency checks: outliers, impossible dates, negative quantities,
    margin inversion, expiry-before-arrival, fulfilled ≫ ordered
S3  schema sufficiency: warn before confirmation when required-field
    coverage is too thin for the optimizer
S4  confidence floor (applied in the policy; re-checked here)
S6  PII scrubbing (in extraction_sessions, used before any logging)
S8  multi-file reconciliation: orders vs deliveries product/date overlap
(S5 audit log, S7 snapshots, S9 cost logging live in
extraction_sessions.py and the engine.)
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from ingestion.llm_extractor import (
    REQUIRED_FIELDS,
    ExtractionResult,
)

OUTLIER_MULTIPLIER = 10.0
FUTURE_LIMIT_DAYS = 365 * 2
PAST_LIMIT_DAYS = 365 * 10
FULFILLED_OVER_ORDERED_FACTOR = 1.20
SUFFICIENCY_REQUIRED_COVERAGE = 0.60

_QTY_FIELDS = {
    "ordered_quantity", "delivered_quantity", "accepted_quantity",
    "rejected_quantity", "requested_quantity", "fulfilled_quantity",
    "substituted_quantity", "quantity_on_hand", "committed_quantity",
    "quantity_lost", "unit_cost", "sales_price", "estimated_value_lost",
}
_DATE_FIELDS = {"delivery_date", "order_date", "arrival_date",
                "expiration_date", "date"}


def _num(v) -> float | None:
    try:
        f = float(v)
        return f if not np.isnan(f) else None
    except (TypeError, ValueError):
        return None


def _parse_date(v) -> date | None:
    if v is None:
        return None
    try:
        d = pd.to_datetime(v, errors="coerce")
        return None if pd.isna(d) else d.date()
    except Exception:  # noqa: BLE001
        return None


# ── S1 — no silent inference ─────────────────────────────────────────────────

def assert_no_silent_inference(result: ExtractionResult) -> ExtractionResult:
    """Any populated field missing inference_source gets flagged for
    confirmation — a value with no provenance never auto-passes."""
    for row in result.extracted_rows:
        for fname, val in row.fields.items():
            if val is None:
                continue
            meta = row.field_metadata.get(fname)
            if meta is None or not meta.inference_source.strip():
                row.flags.append(
                    f"{fname}: value has no recorded provenance — "
                    f"flagged for confirmation")
                row.requires_confirmation = True
                if meta is not None:
                    meta.requires_confirmation = True
    return result


# ── S2 — consistency checks ──────────────────────────────────────────────────

def consistency_checks(
    result: ExtractionResult,
    today: date | None = None,
) -> ExtractionResult:
    ref = today or date.today()
    future_limit = ref + timedelta(days=FUTURE_LIMIT_DAYS)
    past_limit = ref - timedelta(days=PAST_LIMIT_DAYS)

    # per-product medians for the outlier check (across all rows)
    by_product: dict[str, list[float]] = {}
    for row in result.extracted_rows:
        p = row.fields.get("product_name")
        for f in ("ordered_quantity", "requested_quantity",
                  "quantity_on_hand", "quantity_lost"):
            v = _num(row.fields.get(f))
            if p and v is not None and v > 0:
                by_product.setdefault(str(p), []).append(v)
    medians = {p: float(np.median(vs)) for p, vs in by_product.items()
               if len(vs) >= 3}

    # cost/price medians per product for margin-inversion (cross-table)
    costs: dict[str, list[float]] = {}
    prices: dict[str, list[float]] = {}
    for row in result.extracted_rows:
        p = str(row.fields.get("product_name") or "")
        c = _num(row.fields.get("unit_cost"))
        s = _num(row.fields.get("sales_price"))
        if p and c is not None and c > 0:
            costs.setdefault(p, []).append(c)
        if p and s is not None and s > 0:
            prices.setdefault(p, []).append(s)

    for row in result.extracted_rows:
        if row.rejected:
            continue
        p = str(row.fields.get("product_name") or "")

        # negative quantities → reject the row
        for f in _QTY_FIELDS:
            v = _num(row.fields.get(f))
            if v is not None and v < 0:
                row.rejected = True
                row.rejection_reason = (
                    f"{f} is negative ({v:g}) — quantities and prices "
                    f"must be ≥ 0; if this is a correction, record it as "
                    f"a waste adjustment")
                break
        if row.rejected:
            continue

        # expiration before arrival → reject
        exp = _parse_date(row.fields.get("expiration_date"))
        arr = _parse_date(row.fields.get("arrival_date"))
        if exp and arr and exp < arr:
            row.rejected = True
            row.rejection_reason = (
                f"expiration_date {exp} precedes arrival_date {arr} — "
                f"dates appear swapped or misparsed")
            continue

        # implausible dates → flag
        for f in _DATE_FIELDS:
            d = _parse_date(row.fields.get(f))
            if d and (d > future_limit or d < past_limit):
                row.flags.append(
                    f"{f}={d}: more than "
                    f"{'2 years in the future' if d > future_limit else '10 years in the past'}"
                    f" — likely date-format error")
                row.requires_confirmation = True

        # quantity outlier vs product median → flag
        if p in medians:
            for f in ("ordered_quantity", "requested_quantity",
                      "quantity_on_hand", "quantity_lost"):
                v = _num(row.fields.get(f))
                if v is not None and v > OUTLIER_MULTIPLIER * medians[p]:
                    row.flags.append(
                        f"{f}={v:g} is >{OUTLIER_MULTIPLIER:g}× the median "
                        f"for {p} ({medians[p]:g}) — check the unit of "
                        f"measure")
                    row.requires_confirmation = True

        # margin inversion: cost above price for the same product → flag
        if p in costs and p in prices:
            med_p = float(np.median(prices[p]))
            c = _num(row.fields.get("unit_cost"))
            if c is not None and c > med_p:
                row.flags.append(
                    f"unit_cost {c:g} exceeds the median sales_price "
                    f"{med_p:g} for {p} — cost and price may be swapped")
                row.requires_confirmation = True

        # fulfilled ≫ ordered → flag possible unit mismatch
        req = _num(row.fields.get("requested_quantity"))
        ful = _num(row.fields.get("fulfilled_quantity"))
        if req and ful and ful > req * FULFILLED_OVER_ORDERED_FACTOR:
            row.flags.append(
                f"fulfilled_quantity {ful:g} exceeds requested "
                f"{req:g}×{FULFILLED_OVER_ORDERED_FACTOR} — possible unit "
                f"mismatch")
            row.requires_confirmation = True
        o = _num(row.fields.get("ordered_quantity"))
        dlv = _num(row.fields.get("delivered_quantity"))
        if o and dlv and dlv > o * FULFILLED_OVER_ORDERED_FACTOR:
            row.flags.append(
                f"delivered_quantity {dlv:g} exceeds ordered "
                f"{o:g}×{FULFILLED_OVER_ORDERED_FACTOR} — possible unit "
                f"mismatch")
            row.requires_confirmation = True

    return result


# ── S3 — schema sufficiency ──────────────────────────────────────────────────

def schema_sufficiency(result: ExtractionResult) -> ExtractionResult:
    """Warn (before confirmation) when a present table is too thin for
    downstream math. The optimizer must never run on a dataset missing
    more than 40% of its required fields — the warning is carried on the
    result and the confirm endpoint surfaces it."""
    for table in {r.table for r in result.extracted_rows if not r.rejected}:
        required = REQUIRED_FIELDS.get(table, [])
        if not required:
            continue
        rows = [r for r in result.extracted_rows
                if r.table == table and not r.rejected]
        if not rows:
            continue
        covered = 0
        for f in required:
            non_null = sum(1 for r in rows if r.fields.get(f) is not None)
            if non_null / len(rows) >= 0.5:
                covered += 1
        coverage = covered / len(required)
        if coverage < SUFFICIENCY_REQUIRED_COVERAGE:
            missing = [f for f in required
                       if sum(1 for r in rows
                              if r.fields.get(f) is not None)
                       / len(rows) < 0.5]
            result.sufficiency_warnings.append(
                f"{table}: only {coverage:.0%} of required fields are "
                f"populated (need ≥{SUFFICIENCY_REQUIRED_COVERAGE:.0%}). "
                f"Missing/thin: {', '.join(missing)}. The diagnostic can "
                f"run; the optimizer should NOT until these fields are "
                f"supplied.")
    return result


# ── S8 — multi-file reconciliation ───────────────────────────────────────────

def reconcile_files(result: ExtractionResult) -> ExtractionResult:
    """When the upload contains both orders and deliveries, compare
    product × week coverage and flag what does not line up."""
    def keys(table: str, date_field: str) -> set[tuple[str, str]]:
        out = set()
        for r in result.extracted_rows:
            if r.table != table or r.rejected:
                continue
            p = r.fields.get("product_name")
            d = _parse_date(r.fields.get(date_field))
            if p and d:
                week = (d - timedelta(days=d.weekday())).isoformat()
                out.add((str(p).lower(), week))
        return out

    orders = keys("stg_buyer_orders", "delivery_date")
    deliveries = keys("stg_supplier_deliveries", "delivery_date")
    if not orders or not deliveries:
        return result

    only_orders = orders - deliveries
    only_deliv = deliveries - orders
    for p, w in sorted(only_orders)[:10]:
        result.schema_gaps.append(
            f"reconciliation: orders for '{p}' in week {w} have no "
            f"matching supplier deliveries in the upload")
    for p, w in sorted(only_deliv)[:10]:
        result.schema_gaps.append(
            f"reconciliation: deliveries of '{p}' in week {w} have no "
            f"matching buyer orders in the upload")
    return result


# ── Orchestrator ─────────────────────────────────────────────────────────────

def run_post_extraction_safeguards(
    result: ExtractionResult,
    today: date | None = None,
) -> ExtractionResult:
    result = assert_no_silent_inference(result)
    result = consistency_checks(result, today=today)
    result = schema_sufficiency(result)
    result = reconcile_files(result)
    from ingestion.llm_unstructured import enforce_unstructured_floor
    result = enforce_unstructured_floor(result)
    return result
