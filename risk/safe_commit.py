"""Unified safe-commit recommendation, distribution and shelf-life aware.

This is the upgrade of the deterministic recommendations_by_product. It changes
two things:

1. Availability is shelf-life-weighted, not a binary near-expiry cut. A lot that
   will still be good at the delivery date counts; one that won't, does not.

2. The holdback is driven by the supplier's downside fill-rate quantile, not its
   mean. A volatile supplier has a low downside even when its mean looks fine,
   so it triggers a larger holdback automatically. The deterministic model could
   not tell a steady supplier from a swingy one at equal mean; this one can.

    net_available = max(shelf_life_weighted_on_hand - committed, 0)
    safe_commit   = net_available * (1 - holdback_fraction)

The deterministic recommendations_by_product stays in place unchanged so the
backtest can run old policy against new and report the dollar difference.
"""

from __future__ import annotations

from datetime import date
from typing import cast, Any

import duckdb

from risk.shelf_life import weighted_available_by_product
from risk.supplier_distribution import supplier_fill_distributions

_HIGH_RISK = 0.80
_MEDIUM_RISK = 0.90
_BUYER_RISK = 0.90


def _committed_by_product(conn: duckdb.DuckDBPyConnection) -> dict[str, float]:
    df = conn.execute("""
        SELECT product_name,
               COALESCE(SUM(COALESCE(committed_quantity, 0)), 0) AS committed
        FROM stg_inventory_lots
        GROUP BY product_name
    """).df()
    return {r["product_name"]: float(r["committed"]) for _, r in df.iterrows()}


def _product_supplier_signal(
    conn: duckdb.DuckDBPyConnection,
    dists: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """For each product, the worst (lowest downside) supplier that supplies it.

    Mirrors the deterministic model's "worst supplier per product" logic, but
    uses the downside quantile so volatility is reflected.
    """
    pairs = conn.execute("""
        SELECT DISTINCT supplier_id, product_name
        FROM stg_supplier_deliveries
        WHERE product_name IS NOT NULL
    """).df()

    by_product: dict[str, dict[str, Any]] = {}
    for _, row in pairs.iterrows():
        sid = row["supplier_id"]
        pname = row["product_name"]
        info = dists.get(sid)
        if not info:
            continue
        cur = by_product.get(pname)
        if cur is None or info["downside"] < cur["downside"]:
            by_product[pname] = {
                "downside": info["downside"],
                "mean": info["posterior_mean"],
                "supplier_name": info["supplier_name"],
                "spread": info["spread"],
            }
    return by_product


def _buyer_fulfillment_by_product(conn: duckdb.DuckDBPyConnection) -> dict[str, float]:
    df = conn.execute("""
        SELECT product_name,
               CASE WHEN SUM(requested_quantity) > 0
                    THEN SUM(COALESCE(fulfilled_quantity, 0)) / SUM(requested_quantity)
                    ELSE 1.0 END AS fulfillment
        FROM stg_buyer_orders
        WHERE product_name IS NOT NULL
        GROUP BY product_name
    """).df()
    return {r["product_name"]: float(r["fulfillment"]) for _, r in df.iterrows()}


def safe_commit_recommendations(
    conn: duckdb.DuckDBPyConnection,
    as_of_date: date | None = None,
    lead_time_days: float = 3.0,
    quantile: float = 0.10,
    buffers: dict[str, float] | None = None,
    weather_aware: bool = True,
) -> list[dict[str, Any]]:
    """Distribution and shelf-life aware commitment recommendations per product.

    Returns one record per product, sorted High risk first, with the same core
    fields as the deterministic recommendations plus the new signals
    (shelf-life discount, supplier downside vs mean, volatility spread).

    When ``weather_aware`` (default), the Tier-2 heat-stress covariate is
    applied IF it passed admission on this operator's history AND the
    delivery window is heat-flagged in loaded weather data: every
    supplier's fill distribution shifts by the measured delta before the
    downside feeds the holdback. Inactive (with a stated reason) in every
    other case — the recommendation then matches the weather-blind one
    exactly.
    """
    today = as_of_date or date.today()

    weighted = weighted_available_by_product(conn, today, lead_time_days, buffers)
    dists = supplier_fill_distributions(conn, quantile=quantile)

    weather = {"active": False, "reason": "weather_aware disabled"}
    if weather_aware:
        from datetime import timedelta

        from risk.yield_covariates import (
            apply_shift_to_distributions,
            weather_shift_for_window,
        )
        # The delivery window sits lead_time_days ahead, so that IS the
        # forecast lead the weather effect must be attenuated to.
        weather = weather_shift_for_window(
            conn, today, today + timedelta(days=lead_time_days),
            lead_days=lead_time_days)
        if weather["active"]:
            dists = apply_shift_to_distributions(
                dists, cast(float, weather["delta"]), quantile)

    supplier_sig = _product_supplier_signal(conn, dists)
    committed = _committed_by_product(conn)
    buyer_fill = _buyer_fulfillment_by_product(conn)

    recs: list[dict[str, Any]] = []
    for pname, w in weighted.items():
        on_hand = w["on_hand_kg"]
        weighted_avail = w["weighted_kg"]
        shelf_discount = w["discount_kg"]
        com = committed.get(pname, 0.0)

        sig = supplier_sig.get(pname)
        s_downside = sig["downside"] if sig else 1.0
        s_mean = sig["mean"] if sig else 1.0
        s_spread = sig["spread"] if sig else 0.0
        b_fill = buyer_fill.get(pname, 1.0)

        net_available = max(weighted_avail - com, 0.0)

        holdback_frac = 0.0
        if s_downside < _HIGH_RISK:
            holdback_frac += 0.15
        elif s_downside < _MEDIUM_RISK:
            holdback_frac += 0.08
        if b_fill < _BUYER_RISK:
            holdback_frac += 0.05

        safe_commit = round(net_available * (1 - holdback_frac), 1)
        holdback_kg = round(net_available - safe_commit, 1)

        flags: list[str] = []
        if weather["active"] and sig:
            rho = weather.get("forecast_skill_rho")
            measured = weather.get("delta_measured", weather["delta"])
            detail = (f" (measured {measured:+.1%}, forecast skill "
                      f"{rho:.2f} at {weather.get('lead_days', 0):.0f}-day lead)"
                      if rho is not None and cast(float, rho) < 0.999 else
                      " (measured on your history)")
            flags.append(
                f"heat-stress window: supplier fills shifted "
                f"{weather['delta']:+.1%}{detail}")
        if s_downside < _HIGH_RISK:
            flags.append(f"supplier downside fill {s_downside:.0%}")
        if s_spread >= 0.15:
            flags.append(f"volatile supplier (mean {s_mean:.0%}, downside {s_downside:.0%})")
        if shelf_discount > 0.10 * on_hand and on_hand > 0:
            flags.append(f"{shelf_discount:.0f} kg at shelf-life risk for {lead_time_days:.0f}-day delivery")
        if b_fill < _BUYER_RISK:
            flags.append(f"buyer fulfillment {b_fill:.0%}")
        if net_available <= 0:
            flags.append("no committable inventory after shelf-life and commitments")

        if net_available <= 0:
            risk_level = "High"
        elif len(flags) >= 2:
            risk_level = "High"
        elif len(flags) == 1:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        if net_available <= 0:
            text = (f"Do not commit {pname}. No committable inventory once shelf life "
                    f"and existing commitments are accounted for. Source or notify buyers.")
        elif flags:
            text = (f"Commit up to {safe_commit:.0f} kg of {pname} for a "
                    f"{lead_time_days:.0f}-day delivery. {'; '.join(flags)}. "
                    f"Hold back {holdback_kg:.0f} kg.")
        else:
            text = (f"{pname} is low risk. Up to {safe_commit:.0f} kg can be "
                    f"committed for a {lead_time_days:.0f}-day delivery.")

        recs.append({
            "product_name": pname,
            "on_hand_kg": round(on_hand, 1),
            "weighted_available_kg": round(weighted_avail, 1),
            "shelf_life_discount_kg": round(shelf_discount, 1),
            "committed_kg": round(com, 1),
            "net_available_kg": round(net_available, 1),
            "safe_commit_kg": safe_commit,
            "holdback_kg": holdback_kg,
            "supplier_downside_fill": round(s_downside, 4),
            "supplier_mean_fill": round(s_mean, 4),
            "supplier_spread": round(s_spread, 4),
            "buyer_fulfillment_rate": round(b_fill, 4),
            "risk_level": risk_level,
            "risk_flags": flags,
            "recommendation_text": text,
        })

    return sorted(recs, key=lambda r: (r["risk_level"] != "High",
                                       r["risk_level"] != "Medium",
                                       r["product_name"]))
