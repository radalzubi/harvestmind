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


# ── Waste Loss ────────────────────────────────────────────────────────────────

def waste_loss_usd(
    conn: duckdb.DuckDBPyConnection,
    days: int = 365,
) -> dict[str, Any]:
    """Compute dollar value of waste from stg_waste_adjustments.

    Uses estimated_value_lost when present; falls back to
    quantity_lost × avg sales_price for that product.

    Returns:
        total_usd          total waste loss
        by_product         list of {product_name, quantity_lost_kg, loss_usd}
        by_reason          list of {reason, quantity_lost_kg, loss_usd}
        n_rows             rows processed
    """
    since = (_today() - timedelta(days=days)).isoformat()

    # Avg sales price per product from buyer orders (for fallback)
    price_df = conn.execute("""
        SELECT product_name,
               AVG(NULLIF(sales_price, 0)) AS avg_price
        FROM stg_buyer_orders
        WHERE sales_price IS NOT NULL AND sales_price > 0
        GROUP BY product_name
    """).df()
    avg_prices: dict[str, float] = (
        dict(zip(price_df["product_name"], price_df["avg_price"]))
        if not price_df.empty else {}
    )

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
        }

    def _row_value(r) -> float:
        if pd.notna(r["estimated_value_lost"]) and r["estimated_value_lost"] > 0:
            return float(r["estimated_value_lost"])
        qty = float(r["quantity_lost"]) if pd.notna(r["quantity_lost"]) else 0.0
        price = avg_prices.get(r["product_name"], 1.50)  # fallback $1.50/kg
        return qty * float(price)

    waste_df["_loss_usd"] = waste_df.apply(_row_value, axis=1)

    by_product = (
        waste_df.groupby("product_name", dropna=False)
        .agg(quantity_lost_kg=("quantity_lost", "sum"), loss_usd=("_loss_usd", "sum"))
        .reset_index()
        .sort_values("loss_usd", ascending=False)
        .rename(columns={"product_name": "product_name"})
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
    }


# ── Shortage Loss ─────────────────────────────────────────────────────────────

def shortage_loss_usd(
    conn: duckdb.DuckDBPyConnection,
    days: int = 365,
) -> dict[str, Any]:
    """Compute shortage loss from stg_buyer_orders.

    missed_qty = max(requested - fulfilled - substituted, 0)
    loss = missed_qty × sales_price

    Returns:
        total_usd          total shortage loss
        by_product         list of {product_name, missed_kg, loss_usd}
        by_buyer           list of {buyer_name, missed_kg, loss_usd}
        n_at_risk          order lines with any miss
    """
    since = (_today() - timedelta(days=days)).isoformat()

    df = conn.execute(f"""
        SELECT product_name,
               buyer_name,
               requested_quantity,
               COALESCE(fulfilled_quantity, 0)   AS fulfilled_quantity,
               COALESCE(substituted_quantity, 0) AS substituted_quantity,
               COALESCE(sales_price, 0)           AS sales_price
        FROM stg_buyer_orders
        WHERE delivery_date >= '{since}' OR delivery_date IS NULL
    """).df()

    if df.empty:
        return {"total_usd": 0.0, "by_product": [], "by_buyer": [], "n_at_risk": 0}

    df["missed_kg"] = (
        df["requested_quantity"]
        - df["fulfilled_quantity"]
        - df["substituted_quantity"]
    ).clip(lower=0)
    df["loss_usd"] = df["missed_kg"] * df["sales_price"]

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
    }


# ── Supplier Reliability ──────────────────────────────────────────────────────

def supplier_reliability_scores(
    conn: duckdb.DuckDBPyConnection,
) -> dict[str, Any]:
    """Compute per-supplier reliability from stg_supplier_deliveries.

    fill_rate      = accepted / ordered   (or delivered / ordered if accepted missing)
    rejection_rate = rejected / delivered

    Returns:
        suppliers      list of per-supplier dicts
        n_risky        count with fill_rate < threshold
    """
    df = conn.execute("""
        SELECT supplier_id,
               supplier_name,
               COUNT(*)                                          AS n_deliveries,
               COALESCE(SUM(ordered_quantity),  0)              AS total_ordered,
               COALESCE(SUM(delivered_quantity),0)              AS total_delivered,
               COALESCE(SUM(accepted_quantity),
                        SUM(delivered_quantity), 0)             AS total_accepted,
               COALESCE(SUM(rejected_quantity), 0)              AS total_rejected
        FROM stg_supplier_deliveries
        GROUP BY supplier_id, supplier_name
    """).df()

    if df.empty:
        return {"suppliers": [], "n_risky": 0}

    def _fill_rate(row) -> float:
        if row["total_ordered"] > 0:
            return min(float(row["total_accepted"]) / float(row["total_ordered"]), 1.0)
        return 1.0

    def _rejection_rate(row) -> float:
        if row["total_delivered"] > 0:
            return float(row["total_rejected"]) / float(row["total_delivered"])
        return 0.0

    df["fill_rate"] = df.apply(_fill_rate, axis=1)
    df["rejection_rate"] = df.apply(_rejection_rate, axis=1)
    df["risk_level"] = df["fill_rate"].apply(
        lambda v: "High" if v < _HIGH_RISK_FILL_RATE else (
            "Medium" if v < 0.90 else "Low"
        )
    )

    suppliers = df.sort_values("fill_rate").to_dict("records")
    # Round floats for clean JSON
    for row in suppliers:
        for k in ("fill_rate", "rejection_rate", "total_ordered",
                  "total_delivered", "total_accepted", "total_rejected"):
            if isinstance(row.get(k), float):
                row[k] = round(row[k], 4)

    return {
        "suppliers": suppliers,
        "n_risky": int((df["fill_rate"] < _HIGH_RISK_FILL_RATE).sum()),
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

    atp = quantity_on_hand - committed_quantity - expired_quantity

    Near-expiry = expiring within _NEAR_EXPIRY_DAYS days.

    Returns:
        products         list of per-product ATP dicts
        n_risky          products with near_expiry_pct > threshold or atp <= 0
    """
    today = as_of_date or _today()
    near_expiry_cutoff = (today + timedelta(days=_NEAR_EXPIRY_DAYS)).isoformat()
    today_str = today.isoformat()

    df = conn.execute(f"""
        SELECT product_id,
               product_name,
               COALESCE(SUM(quantity_on_hand), 0)                        AS total_on_hand,
               COALESCE(SUM(COALESCE(committed_quantity, 0)), 0)          AS total_committed,
               COALESCE(SUM(
                   CASE WHEN expiration_date < '{today_str}'
                        THEN quantity_on_hand ELSE 0 END
               ), 0)                                                      AS expired_qty,
               COALESCE(SUM(
                   CASE WHEN expiration_date >= '{today_str}'
                        AND expiration_date <= '{near_expiry_cutoff}'
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
        atp = max(usable - committed, 0.0)
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
    reduction_pct: float = 0.30,
) -> dict[str, Any]:
    """Estimate addressable savings if HarvestMind prevented a fraction of losses.

    Default: 30% reduction (conservative, supportable by USDA SR-77 benchmarks).
    """
    addressable = waste["total_usd"] + shortage["total_usd"]
    savings = round(addressable * reduction_pct, 2)
    return {
        "addressable_loss_usd": round(addressable, 2),
        "reduction_pct_assumed": reduction_pct,
        "estimated_annual_savings_usd": savings,
        "waste_loss_usd": waste["total_usd"],
        "shortage_loss_usd": shortage["total_usd"],
    }


# ── Full Diagnostic Summary ───────────────────────────────────────────────────

def diagnostic_summary(
    conn: duckdb.DuckDBPyConnection,
    partner_name: str = "Operator",
    days: int = 365,
) -> dict[str, Any]:
    """Return the full diagnostic payload for the dashboard Overview page
    and the diagnostic report generator.

    This is the single authoritative data pull — all dashboard panels
    and the report generator call this function.
    """
    waste = waste_loss_usd(conn, days=days)
    shortage = shortage_loss_usd(conn, days=days)
    supplier = supplier_reliability_scores(conn)
    buyer = buyer_fulfillment_rates(conn)
    traceability = traceability_coverage(conn)
    atp = atp_by_product(conn)
    recs = recommendations_by_product(conn)
    savings = estimated_annual_savings(waste, shortage)
    row_counts = _staging_row_counts(conn)

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
        "as_of": date.today().isoformat(),
        "period_days": days,
        "row_counts": row_counts,
        "waste": waste,
        "shortage": shortage,
        "supplier": supplier,
        "buyer": buyer,
        "traceability": traceability,
        "atp": atp,
        "recommendations": recs,
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
