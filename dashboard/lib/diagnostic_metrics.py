"""Diagnostic metrics engine — available-to-promise, inventory risk,
supplier reliability, buyer fulfillment, waste loss, shortage loss,
and traceability readiness.

All functions read from the diagnostic staging tables (migration 010):
  stg_products, stg_supplier_deliveries, stg_inventory_lots,
  stg_buyer_orders, stg_waste_adjustments

These staging tables accept messy operator CSV data with no FK constraints.
The main normalized schema (fact_*, dim_*) is not touched by this module.

All monetary outputs are in USD.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import duckdb
import pandas as pd


# ── Helpers ──────────────────────────────────────────────────────────────────

_NEAR_EXPIRY_DAYS = 3   # flag lots expiring within this many days
_HIGH_RISK_FILL_RATE = 0.80   # supplier fill rate below this → High risk
_HIGH_RISK_FULFILLMENT = 0.90  # buyer fulfillment below this → High risk
_HIGH_RISK_NEAR_EXPIRY = 0.20  # near-expiry > 20% of inventory → High risk
_HIGH_RISK_TRACEABILITY = 0.90  # traceability completeness below this → High risk


def _today() -> date:
    return date.today()


def _staging_row_counts(conn: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Return row counts for all 5 staging tables."""
    tables = [
        "stg_products",
        "stg_supplier_deliveries",
        "stg_inventory_lots",
        "stg_buyer_orders",
        "stg_waste_adjustments",
    ]
    counts: dict[str, int] = {}
    for t in tables:
        try:
            row = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()
            counts[t] = int(row[0]) if row else 0
        except Exception:
            counts[t] = 0
    return counts


def _period_days_from_data(
    conn: duckdb.DuckDBPyConnection,
    default: int = 90,
    min_days: int = 7,
) -> int:
    """Auto-detect the period spanned by the operator's data.

    Looks at the widest date range across orders, deliveries, and waste events
    and returns the integer number of days. Falls back to ``default`` when no
    date data exists. Clamps to at least ``min_days`` to avoid divide-by-near-
    zero in annualization for very small samples.
    """
    try:
        row = conn.execute("""
            WITH all_dates AS (
              SELECT delivery_date AS d FROM stg_buyer_orders          WHERE delivery_date IS NOT NULL
              UNION ALL
              SELECT delivery_date AS d FROM stg_supplier_deliveries   WHERE delivery_date IS NOT NULL
              UNION ALL
              SELECT date          AS d FROM stg_waste_adjustments     WHERE date          IS NOT NULL
            )
            SELECT MIN(d) AS min_d, MAX(d) AS max_d FROM all_dates
        """).fetchone()
    except Exception:
        return default
    if not row or row[0] is None or row[1] is None:
        return default
    span = (row[1] - row[0]).days + 1  # inclusive
    return max(int(span), min_days)


def _avg_unit_cost_by_product(
    conn: duckdb.DuckDBPyConnection,
) -> dict[str, float]:
    """Average unit_cost from supplier deliveries, keyed by product_name.

    Used as the cost basis for valuing waste when ``estimated_value_lost``
    is missing on a row. Drops zero/null prices to avoid pulling the
    average down.
    """
    try:
        df = conn.execute("""
            SELECT product_name,
                   AVG(NULLIF(unit_cost, 0)) AS avg_cost
            FROM stg_supplier_deliveries
            WHERE unit_cost IS NOT NULL AND unit_cost > 0
            GROUP BY product_name
        """).df()
    except Exception:
        return {}
    if df.empty:
        return {}
    return dict(zip(df["product_name"], df["avg_cost"].astype(float)))


def _avg_sales_price_by_product(
    conn: duckdb.DuckDBPyConnection,
) -> dict[str, float]:
    """Average sales_price from buyer orders, keyed by product_name.

    Used as the price basis for valuing shortage when an order row has a
    missing ``sales_price``.
    """
    try:
        df = conn.execute("""
            SELECT product_name,
                   AVG(NULLIF(sales_price, 0)) AS avg_price
            FROM stg_buyer_orders
            WHERE sales_price IS NOT NULL AND sales_price > 0
            GROUP BY product_name
        """).df()
    except Exception:
        return {}
    if df.empty:
        return {}
    return dict(zip(df["product_name"], df["avg_price"].astype(float)))


# ── Waste Loss ────────────────────────────────────────────────────────────────

def waste_loss_usd(
    conn: duckdb.DuckDBPyConnection,
    days: int = 365,
) -> dict[str, Any]:
    """Compute dollar value of waste from stg_waste_adjustments.

    Valuation order, applied row-by-row:
      1. Use ``estimated_value_lost`` when present and > 0.
      2. Else use ``quantity_lost × avg unit_cost`` for that product
         (cost basis from ``stg_supplier_deliveries``).
      3. Else the row is "unvalued" — contributes $0 to total but is
         counted in ``n_rows_unvalued`` so the operator knows the
         total understates true waste.

    Note: cost (not sales price) is the right basis for waste loss.
    Sales price would conflate margin with cost-of-goods written off.

    Returns:
        total_usd          total waste loss (cost basis)
        by_product         list of {product_name, quantity_lost_kg, loss_usd}
        by_reason          list of {reason, quantity_lost_kg, loss_usd}
        n_rows             total rows processed
        n_rows_unvalued    rows with no estimated_value_lost AND no
                           product-level unit cost available
    """
    since = (_today() - timedelta(days=days)).isoformat()

    avg_costs = _avg_unit_cost_by_product(conn)

    waste_df = conn.execute(f"""
        SELECT product_name,
               reason,
               quantity_lost,
               estimated_value_lost
        FROM stg_waste_adjustments
        WHERE date >= '{since}' OR date IS NULL
    """).df()

    if waste_df.empty:
        return {
            "total_usd": 0.0,
            "by_product": [],
            "by_reason": [],
            "n_rows": 0,
            "n_rows_unvalued": 0,
        }

    n_unvalued = 0

    def _row_value(r) -> float:
        nonlocal n_unvalued
        if pd.notna(r["estimated_value_lost"]) and r["estimated_value_lost"] > 0:
            return float(r["estimated_value_lost"])
        qty = float(r["quantity_lost"]) if pd.notna(r["quantity_lost"]) else 0.0
        cost = avg_costs.get(r["product_name"])
        if cost is None or cost <= 0:
            n_unvalued += 1
            return 0.0
        return qty * float(cost)

    waste_df["_loss_usd"] = waste_df.apply(_row_value, axis=1)

    by_product = (
        waste_df.groupby("product_name", dropna=False)
        .agg(quantity_lost_kg=("quantity_lost", "sum"), loss_usd=("_loss_usd", "sum"))
        .reset_index()
        .sort_values("loss_usd", ascending=False)
        .to_dict("records")
    )

    by_reason = (
        waste_df.groupby("reason", dropna=False)
        .agg(quantity_lost_kg=("quantity_lost", "sum"), loss_usd=("_loss_usd", "sum"))
        .reset_index()
        .sort_values("loss_usd", ascending=False)
        .to_dict("records")
    )

    return {
        "total_usd": round(float(waste_df["_loss_usd"].sum()), 2),
        "by_product": [{k: (round(v, 2) if isinstance(v, float) else v)
                        for k, v in row.items()} for row in by_product],
        "by_reason": [{k: (round(v, 2) if isinstance(v, float) else v)
                       for k, v in row.items()} for row in by_reason],
        "n_rows": len(waste_df),
        "n_rows_unvalued": n_unvalued,
    }


# ── Shortage Loss ─────────────────────────────────────────────────────────────

def shortage_loss_usd(
    conn: duckdb.DuckDBPyConnection,
    days: int = 365,
) -> dict[str, Any]:
    """Compute shortage loss from stg_buyer_orders.

    For each order line:
        missed_qty = max(requested - fulfilled - substituted, 0)
        price      = row's sales_price, or avg sales_price for that
                     product across all orders (if the row is missing)
        loss       = missed_qty × price

    Rows with missed_qty > 0 but no usable price (no row price AND no
    product-level average) contribute $0 and are counted in
    ``n_at_risk_unvalued`` so the operator knows the total understates
    true shortage.

    Returns:
        total_usd                total shortage loss
        by_product               list of {product_name, missed_kg, loss_usd}
        by_buyer                 list of {buyer_name, missed_kg, loss_usd}
        n_at_risk                order lines with missed_qty > 0
        n_at_risk_unvalued       at-risk lines we couldn't price
    """
    since = (_today() - timedelta(days=days)).isoformat()

    avg_prices = _avg_sales_price_by_product(conn)

    df = conn.execute(f"""
        SELECT product_name,
               buyer_name,
               requested_quantity,
               COALESCE(fulfilled_quantity, 0)   AS fulfilled_quantity,
               COALESCE(substituted_quantity, 0) AS substituted_quantity,
               sales_price
        FROM stg_buyer_orders
        WHERE delivery_date >= '{since}' OR delivery_date IS NULL
    """).df()

    if df.empty:
        return {
            "total_usd": 0.0, "by_product": [], "by_buyer": [],
            "n_at_risk": 0, "n_at_risk_unvalued": 0,
        }

    df["missed_kg"] = (
        df["requested_quantity"]
        - df["fulfilled_quantity"]
        - df["substituted_quantity"]
    ).clip(lower=0)

    n_unvalued = 0

    def _price_for_row(r) -> float:
        nonlocal n_unvalued
        if pd.notna(r["sales_price"]) and r["sales_price"] > 0:
            return float(r["sales_price"])
        avg = avg_prices.get(r["product_name"])
        if avg is None or avg <= 0:
            # Only count as unvalued if this line actually has a miss
            if r["missed_kg"] > 0:
                n_unvalued += 1
            return 0.0
        return float(avg)

    df["_price"] = df.apply(_price_for_row, axis=1)
    df["loss_usd"] = df["missed_kg"] * df["_price"]

    n_at_risk = int((df["missed_kg"] > 0).sum())

    by_product = (
        df.groupby("product_name", dropna=False)
        .agg(missed_kg=("missed_kg", "sum"), loss_usd=("loss_usd", "sum"))
        .reset_index()
        .sort_values("loss_usd", ascending=False)
        .to_dict("records")
    )

    by_buyer = (
        df.groupby("buyer_name", dropna=False)
        .agg(missed_kg=("missed_kg", "sum"), loss_usd=("loss_usd", "sum"))
        .reset_index()
        .sort_values("loss_usd", ascending=False)
        .to_dict("records")
    )

    return {
        "total_usd": round(float(df["loss_usd"].sum()), 2),
        "by_product": [{k: (round(v, 2) if isinstance(v, float) else v)
                        for k, v in row.items()} for row in by_product],
        "by_buyer": [{k: (round(v, 2) if isinstance(v, float) else v)
                      for k, v in row.items()} for row in by_buyer],
        "n_at_risk": n_at_risk,
        "n_at_risk_unvalued": n_unvalued,
    }


# ── Supplier Reliability ──────────────────────────────────────────────────────

def supplier_reliability_scores(
    conn: duckdb.DuckDBPyConnection,
) -> dict[str, Any]:
    """Compute per-supplier reliability from stg_supplier_deliveries.

    Definitions:
        fill_rate      = accepted / ordered
                         (falls back to delivered / ordered when no
                          accepted_quantity recorded on any row)
        rejection_rate = rejected / delivered

    Suppliers with no ordered_quantity data are returned with
    ``fill_rate = None`` and ``risk_level = "Unknown"``. They are
    excluded from the ``n_risky`` count because we cannot judge
    a supplier whose data we don't have.

    Returns:
        suppliers      list of per-supplier dicts
        n_risky        count with fill_rate < High threshold (excludes Unknown)
        n_unknown      count of suppliers with no orderable history
    """
    # NOTE: SUM(accepted_quantity) returns NULL only when *every* row's
    # accepted_quantity is NULL. We pick the right basis at the row level
    # in pandas, not in SQL, to avoid COALESCE(SUM(.), SUM(.)) confusion
    # when both have data but one happens to sum to zero.
    df = conn.execute("""
        SELECT supplier_id,
               supplier_name,
               COUNT(*)                                AS n_deliveries,
               SUM(ordered_quantity)                   AS total_ordered,
               SUM(delivered_quantity)                 AS total_delivered,
               SUM(accepted_quantity)                  AS total_accepted_raw,
               SUM(rejected_quantity)                  AS total_rejected
        FROM stg_supplier_deliveries
        GROUP BY supplier_id, supplier_name
    """).df()

    if df.empty:
        return {"suppliers": [], "n_risky": 0, "n_unknown": 0}

    def _accepted(row) -> float:
        """Prefer accepted, fall back to delivered when accepted has no data."""
        a = row["total_accepted_raw"]
        d = row["total_delivered"]
        if pd.notna(a):
            return float(a)
        return float(d) if pd.notna(d) else 0.0

    def _fill_rate(row):
        ordered = row["total_ordered"]
        if not pd.notna(ordered) or ordered <= 0:
            return None  # unknown — we can't judge
        accepted = _accepted(row)
        return min(accepted / float(ordered), 1.0)

    def _rejection_rate(row) -> float:
        d = row["total_delivered"]
        r = row["total_rejected"]
        if pd.notna(d) and d > 0 and pd.notna(r):
            return float(r) / float(d)
        return 0.0

    df["total_accepted"] = df.apply(_accepted, axis=1)
    df["fill_rate"] = df.apply(_fill_rate, axis=1)
    df["rejection_rate"] = df.apply(_rejection_rate, axis=1)

    def _risk(v) -> str:
        if v is None:
            return "Unknown"
        if v < _HIGH_RISK_FILL_RATE:
            return "High"
        if v < 0.90:
            return "Medium"
        return "Low"

    df["risk_level"] = df["fill_rate"].apply(_risk)

    # Sort: knowns first (lowest fill rate first), then Unknowns
    df["_sort_fill"] = df["fill_rate"].fillna(2.0)  # push Unknowns to bottom
    df = df.sort_values("_sort_fill").drop(columns=["_sort_fill", "total_accepted_raw"])

    suppliers = df.to_dict("records")
    for row in suppliers:
        # Round numerics. Leave fill_rate=None alone.
        for k in ("rejection_rate", "total_ordered", "total_delivered",
                  "total_accepted", "total_rejected"):
            v = row.get(k)
            if isinstance(v, float) and pd.notna(v):
                row[k] = round(v, 4)
            elif pd.isna(v):
                row[k] = 0.0
        if row.get("fill_rate") is not None and pd.notna(row.get("fill_rate")):
            row["fill_rate"] = round(float(row["fill_rate"]), 4)
        elif pd.isna(row.get("fill_rate")):
            row["fill_rate"] = None

    n_risky = sum(
        1 for s in suppliers
        if s["fill_rate"] is not None and s["fill_rate"] < _HIGH_RISK_FILL_RATE
    )
    n_unknown = sum(1 for s in suppliers if s["fill_rate"] is None)

    return {
        "suppliers": suppliers,
        "n_risky": n_risky,
        "n_unknown": n_unknown,
    }


# ── Buyer Fulfillment ─────────────────────────────────────────────────────────

def buyer_fulfillment_rates(
    conn: duckdb.DuckDBPyConnection,
) -> dict[str, Any]:
    """Compute per-buyer fulfillment from stg_buyer_orders.

    fulfillment_rate = fulfilled / requested
    substitution_rate = substituted / requested
    missed_rate = missed / requested

    Returns:
        buyers         list of per-buyer dicts
        n_risky        count with fulfillment_rate < threshold
    """
    df = conn.execute("""
        SELECT buyer_id,
               buyer_name,
               COUNT(*)                                              AS n_orders,
               COALESCE(SUM(requested_quantity), 0)                 AS total_requested,
               COALESCE(SUM(fulfilled_quantity), 0)                 AS total_fulfilled,
               COALESCE(SUM(substituted_quantity), 0)               AS total_substituted,
               COALESCE(SUM(
                   GREATEST(requested_quantity
                     - COALESCE(fulfilled_quantity, 0)
                     - COALESCE(substituted_quantity, 0), 0)
               ), 0)                                                 AS total_missed
        FROM stg_buyer_orders
        GROUP BY buyer_id, buyer_name
    """).df()

    if df.empty:
        return {"buyers": [], "n_risky": 0}

    def _rate(num, denom):
        return round(float(num) / float(denom), 4) if float(denom) > 0 else 0.0

    df["fulfillment_rate"] = df.apply(
        lambda r: _rate(r["total_fulfilled"], r["total_requested"]), axis=1
    )
    df["substitution_rate"] = df.apply(
        lambda r: _rate(r["total_substituted"], r["total_requested"]), axis=1
    )
    df["missed_rate"] = df.apply(
        lambda r: _rate(r["total_missed"], r["total_requested"]), axis=1
    )
    df["risk_level"] = df["fulfillment_rate"].apply(
        lambda v: "High" if v < _HIGH_RISK_FULFILLMENT else (
            "Medium" if v < 0.95 else "Low"
        )
    )

    buyers = df.sort_values("fulfillment_rate").to_dict("records")
    for row in buyers:
        for k in ("fulfillment_rate", "substitution_rate", "missed_rate"):
            if isinstance(row.get(k), float):
                row[k] = round(row[k], 4)

    return {
        "buyers": buyers,
        "n_risky": int((df["fulfillment_rate"] < _HIGH_RISK_FULFILLMENT).sum()),
    }


# ── Traceability Coverage ─────────────────────────────────────────────────────

def traceability_coverage(
    conn: duckdb.DuckDBPyConnection,
) -> dict[str, Any]:
    """Compute lot-level traceability completeness from stg_inventory_lots.

    A lot is complete if it has: lot_id, product_id, supplier_id,
    arrival_date, quantity_on_hand, unit.

    Returns:
        completeness_pct   fraction of lots that are complete
        total_lots
        complete_lots
        incomplete_lots    list of {lot_id, product_name, missing_fields}
        missing_breakdown  dict of field → count missing
    """
    df = conn.execute("""
        SELECT lot_id,
               product_id,
               product_name,
               supplier_id,
               quantity_on_hand,
               unit,
               arrival_date,
               expiration_date
        FROM stg_inventory_lots
    """).df()

    if df.empty:
        return {
            "completeness_pct": 0.0,
            "total_lots": 0,
            "complete_lots": 0,
            "incomplete_lots": [],
            "missing_breakdown": {},
        }

    required_fields = [
        "lot_id", "product_id", "supplier_id",
        "arrival_date", "quantity_on_hand", "unit",
    ]

    missing_breakdown: dict[str, int] = {}
    incomplete_lots = []

    for _, row in df.iterrows():
        missing = [
            f for f in required_fields
            if pd.isna(row.get(f)) or str(row.get(f, "")).strip() == ""
        ]
        if missing:
            incomplete_lots.append({
                "lot_id": row.get("lot_id"),
                "product_name": row.get("product_name"),
                "missing_fields": missing,
            })
            for f in missing:
                missing_breakdown[f] = missing_breakdown.get(f, 0) + 1

    total = len(df)
    complete = total - len(incomplete_lots)
    completeness = round(complete / total, 4) if total > 0 else 0.0

    return {
        "completeness_pct": completeness,
        "total_lots": total,
        "complete_lots": complete,
        "incomplete_lots": incomplete_lots[:50],  # cap for API response size
        "missing_breakdown": missing_breakdown,
    }


# ── Available-to-Promise ──────────────────────────────────────────────────────

def atp_by_product(
    conn: duckdb.DuckDBPyConnection,
    as_of_date: date | None = None,
) -> dict[str, Any]:
    """Compute available-to-promise per product from stg_inventory_lots.

    Formula (matches the customer-facing field definitions):
        usable_kg = on_hand - expired_kg
        atp_kg    = max(usable_kg - committed_kg - near_expiry_kg, 0)

    Near-expiry inventory IS subtracted from ATP because committing
    near-expiry stock to a delivery 3+ days out is a known cause of
    missed-order risk. Operators should source replenishment, not
    promise near-expiry product.

    Each lot is classified into at most one of {expired, near_expiry,
    healthy} based on its expiration_date relative to ``as_of_date`` —
    a lot cannot count in both buckets.

    Returns:
        products         list of per-product ATP dicts, sorted by ATP ascending
        n_risky          products with near_expiry_pct > threshold OR atp <= 0
    """
    today = as_of_date or _today()
    near_expiry_cutoff = (today + timedelta(days=_NEAR_EXPIRY_DAYS)).isoformat()
    today_str = today.isoformat()

    # CASE order matters: expired check first, then near-expiry, so a lot
    # is never counted in both buckets.
    df = conn.execute(f"""
        SELECT product_id,
               product_name,
               COALESCE(SUM(quantity_on_hand), 0)                        AS total_on_hand,
               COALESCE(SUM(COALESCE(committed_quantity, 0)), 0)         AS total_committed,
               COALESCE(SUM(
                   CASE WHEN expiration_date IS NOT NULL
                        AND  expiration_date < '{today_str}'
                        THEN quantity_on_hand ELSE 0 END
               ), 0)                                                      AS expired_qty,
               COALESCE(SUM(
                   CASE WHEN expiration_date IS NOT NULL
                        AND  expiration_date >= '{today_str}'
                        AND  expiration_date <= '{near_expiry_cutoff}'
                        THEN quantity_on_hand ELSE 0 END
               ), 0)                                                      AS near_expiry_qty
        FROM stg_inventory_lots
        GROUP BY product_id, product_name
    """).df()

    if df.empty:
        return {"products": [], "n_risky": 0}

    products = []
    n_risky = 0

    for _, row in df.iterrows():
        on_hand = float(row["total_on_hand"])
        committed = float(row["total_committed"])
        expired = float(row["expired_qty"])
        near_expiry = float(row["near_expiry_qty"])

        usable = max(on_hand - expired, 0.0)
        # ATP subtracts near_expiry too — this is the contractually safe
        # quantity to promise for delivery beyond the near-expiry window.
        atp = max(usable - committed - near_expiry, 0.0)
        near_expiry_pct = (near_expiry / on_hand) if on_hand > 0 else 0.0

        is_risky = (
            atp <= 0
            or near_expiry_pct > _HIGH_RISK_NEAR_EXPIRY
        )
        if is_risky:
            n_risky += 1

        products.append({
            "product_id": row["product_id"],
            "product_name": row["product_name"],
            "total_on_hand_kg": round(on_hand, 1),
            "committed_kg": round(committed, 1),
            "expired_kg": round(expired, 1),
            "near_expiry_kg": round(near_expiry, 1),
            "usable_kg": round(usable, 1),
            "atp_kg": round(atp, 1),
            "near_expiry_pct": round(near_expiry_pct, 4),
            "risk_level": "High" if is_risky else (
                "Medium" if near_expiry_pct > 0.10 else "Low"
            ),
        })

    products.sort(key=lambda p: p["atp_kg"])

    return {"products": products, "n_risky": n_risky}


# ── Per-Product Recommendations ───────────────────────────────────────────────

def recommendations_by_product(
    conn: duckdb.DuckDBPyConnection,
    as_of_date: date | None = None,
) -> list[dict[str, Any]]:
    """Generate plain-English commitment recommendations per product.

    Combines ATP, supplier fill rates, and buyer fulfillment data.
    """
    today = as_of_date or _today()
    atp_data = atp_by_product(conn, as_of_date=today)
    supplier_data = supplier_reliability_scores(conn)
    buyer_data = buyer_fulfillment_rates(conn)

    # Build lookup: product_name → worst supplier fill rate
    supplier_fill: dict[str, float] = {}
    for s in supplier_data["suppliers"]:
        # Join by product via stg_supplier_deliveries
        try:
            prod_rows = conn.execute("""
                SELECT DISTINCT product_name
                FROM stg_supplier_deliveries
                WHERE supplier_id = ?
            """, [s["supplier_id"]]).fetchall()
        except Exception:
            prod_rows = []
        for (pname,) in prod_rows:
            if pname:
                current = supplier_fill.get(pname, 1.0)
                supplier_fill[pname] = min(current, float(s["fill_rate"]))

    # Build lookup: product_name → worst buyer fulfillment rate
    buyer_fill: dict[str, float] = {}
    try:
        bf_df = conn.execute("""
            SELECT product_name,
                   MIN(CASE WHEN requested_quantity > 0
                       THEN fulfilled_quantity / requested_quantity
                       ELSE 1.0 END) AS worst_fill
            FROM stg_buyer_orders
            GROUP BY product_name
        """).df()
        buyer_fill = dict(zip(bf_df["product_name"], bf_df["worst_fill"]))
    except Exception:
        pass

    recs = []
    for p in atp_data["products"]:
        pname = p["product_name"]
        atp = p["atp_kg"]
        near_exp = p["near_expiry_kg"]
        near_exp_pct = p["near_expiry_pct"]
        s_fill = supplier_fill.get(pname, 1.0)
        b_fill = float(buyer_fill.get(pname, 1.0) or 1.0)

        # Holdback = buffer for supply uncertainty
        holdback_pct = 0.0
        if s_fill < _HIGH_RISK_FILL_RATE:
            holdback_pct += 0.15
        elif s_fill < 0.90:
            holdback_pct += 0.08
        if b_fill < _HIGH_RISK_FULFILLMENT:
            holdback_pct += 0.05

        holdback_kg = round(atp * holdback_pct, 1)
        safe_commit = round(max(atp - holdback_kg, 0.0), 1)

        # Risk level
        risk_flags = []
        if s_fill < _HIGH_RISK_FILL_RATE:
            risk_flags.append(f"supplier fill rate {s_fill:.0%}")
        if near_exp_pct > _HIGH_RISK_NEAR_EXPIRY:
            risk_flags.append(f"{near_exp:.0f} kg near expiry")
        if b_fill < _HIGH_RISK_FULFILLMENT:
            risk_flags.append(f"buyer fulfillment {b_fill:.0%}")
        if atp <= 0:
            risk_flags.append("no available inventory")

        if len(risk_flags) >= 2 or atp <= 0:
            risk_level = "High"
        elif len(risk_flags) == 1:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        # Plain-English recommendation
        if atp <= 0:
            text = (
                f"Do not commit {pname} — no usable inventory available. "
                f"Source immediately or notify buyers."
            )
        elif risk_flags:
            flags_str = "; ".join(risk_flags)
            text = (
                f"Commit no more than {safe_commit:.0f} kg of {pname}. "
                f"Risk factors: {flags_str}. "
                f"Hold back {holdback_kg:.0f} kg as buffer."
            )
        else:
            text = (
                f"{pname} is low risk. Up to {safe_commit:.0f} kg can be safely committed."
            )

        recs.append({
            "product_name": pname,
            "product_id": p.get("product_id"),
            "atp_kg": atp,
            "safe_commit_kg": safe_commit,
            "holdback_kg": holdback_kg,
            "near_expiry_kg": near_exp,
            "supplier_fill_rate": round(s_fill, 4),
            "buyer_fulfillment_rate": round(b_fill, 4),
            "risk_level": risk_level,
            "risk_flags": risk_flags,
            "recommendation_text": text,
        })

    return sorted(recs, key=lambda r: (r["risk_level"] != "High",
                                        r["risk_level"] != "Medium",
                                        r["product_name"]))


# ── Estimated Annual Savings ──────────────────────────────────────────────────

def estimated_annual_savings(
    waste: dict[str, Any],
    shortage: dict[str, Any],
    period_days: int = 90,
    reduction_pct_low: float = 0.15,
    reduction_pct_high: float = 0.30,
) -> dict[str, Any]:
    """Estimate addressable savings if HarvestMind prevented a fraction of losses.

    Takes the period loss (from the analyzed window), scales to a full
    year using ``365 / period_days``, then applies a reduction range
    (default 15%–30%) sourced from USDA SR-77 benchmarks for produce
    hubs adopting improved inventory and fulfillment practices.

    The output includes both raw period values and annualized values so
    the operator can see exactly what the math did.

    Returns:
        addressable_loss_usd_period      raw waste + shortage over the period
        addressable_loss_usd             ANNUALIZED addressable loss
        period_days                      window of data the period figure covers
        annualization_factor             365 / period_days
        reduction_pct_low / _high        the assumed reduction range
        reduction_pct_assumed            kept for backward compatibility (= high)
        estimated_annual_savings_usd_low   addressable × low %
        estimated_annual_savings_usd_high  addressable × high %
        estimated_annual_savings_usd     headline figure (= high, conservative-side)
        waste_loss_usd                   raw period waste loss
        shortage_loss_usd                raw period shortage loss
    """
    # Defensive: clamp period_days to a sane minimum so a 1-day sample
    # doesn't extrapolate by 365× and produce absurd headline figures.
    pd_days = max(int(period_days or 90), 7)
    factor = 365.0 / pd_days

    period_loss = float(waste["total_usd"]) + float(shortage["total_usd"])
    annual_loss = period_loss * factor

    savings_low  = annual_loss * float(reduction_pct_low)
    savings_high = annual_loss * float(reduction_pct_high)

    return {
        "addressable_loss_usd_period": round(period_loss, 2),
        "addressable_loss_usd": round(annual_loss, 2),
        "period_days": pd_days,
        "annualization_factor": round(factor, 4),
        "reduction_pct_low": reduction_pct_low,
        "reduction_pct_high": reduction_pct_high,
        "reduction_pct_assumed": reduction_pct_high,  # backward-compat
        "estimated_annual_savings_usd_low": round(savings_low, 2),
        "estimated_annual_savings_usd_high": round(savings_high, 2),
        "estimated_annual_savings_usd": round(savings_high, 2),  # backward-compat
        "waste_loss_usd": float(waste["total_usd"]),
        "shortage_loss_usd": float(shortage["total_usd"]),
    }


# ── Full Diagnostic Summary ───────────────────────────────────────────────────

def diagnostic_summary(
    conn: duckdb.DuckDBPyConnection,
    partner_name: str = "Operator",
    days: int | None = None,
    as_of_date: date | None = None,
) -> dict[str, Any]:
    """Return the full diagnostic payload for the dashboard Overview page
    and the diagnostic report generator.

    This is the single authoritative data pull — all dashboard panels
    and the report generator call this function.

    ``days`` is the lookback window for waste and shortage. When ``None``
    (the recommended default for a real diagnostic) HarvestMind detects
    the actual data span from min(date)..max(date) across orders,
    deliveries, and waste events. The detected value is used for both
    filtering and for annualization in the savings module.

    ``as_of_date`` controls the date used for near-expiry / expired
    classification. Defaults to today. Tests pass a fixed date for
    determinism.
    """
    detected_period = _period_days_from_data(conn)
    effective_days = int(days) if days is not None else detected_period

    waste = waste_loss_usd(conn, days=effective_days)
    shortage = shortage_loss_usd(conn, days=effective_days)
    supplier = supplier_reliability_scores(conn)
    buyer = buyer_fulfillment_rates(conn)
    traceability = traceability_coverage(conn)
    atp = atp_by_product(conn, as_of_date=as_of_date)
    recs = recommendations_by_product(conn, as_of_date=as_of_date)
    savings = estimated_annual_savings(waste, shortage, period_days=effective_days)
    row_counts = _staging_row_counts(conn)

    # Distribution + shelf-life aware commitment plan (the upgraded model).
    # Kept alongside the deterministic `recommendations` so the two can be
    # compared directly in the backtest. Guarded so a risk-layer issue can
    # never take down the diagnostic summary.
    try:
        from risk.safe_commit import safe_commit_recommendations
        commitment_plan = safe_commit_recommendations(conn, as_of_date=as_of_date)
    except Exception:  # noqa: BLE001  defensive: never break the summary
        commitment_plan = []

    # Top 5 operational risks (highest-loss items across waste + shortage)
    all_risks: list[dict[str, Any]] = []
    for item in waste["by_product"][:5]:
        all_risks.append({
            "category": "Waste",
            "item": item.get("product_name", "—"),
            "loss_usd": item.get("loss_usd", 0.0),
        })
    for item in shortage["by_product"][:5]:
        all_risks.append({
            "category": "Shortage",
            "item": item.get("product_name", "—"),
            "loss_usd": item.get("loss_usd", 0.0),
        })
    top_risks = sorted(all_risks, key=lambda x: x["loss_usd"], reverse=True)[:5]

    return {
        "partner_name": partner_name,
        "as_of": (as_of_date or date.today()).isoformat(),
        "period_days": effective_days,
        "period_days_detected": detected_period,
        "row_counts": row_counts,
        "waste": waste,
        "shortage": shortage,
        "supplier": supplier,
        "buyer": buyer,
        "traceability": traceability,
        "atp": atp,
        "recommendations": recs,
        "commitment_plan": commitment_plan,
        "savings": savings,
        "top_risks": top_risks,
        # Convenience top-line scalars for Overview cards
        "total_waste_loss_usd": waste["total_usd"],
        "total_shortage_loss_usd": shortage["total_usd"],
        "total_addressable_loss_usd": savings["addressable_loss_usd"],
        "n_risky_suppliers": supplier["n_risky"],
        "n_risky_products": atp["n_risky"],
        "n_risky_buyers": buyer["n_risky"],
        "traceability_completeness_pct": traceability["completeness_pct"],
    }
