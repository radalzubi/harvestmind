"""Procurement metrics: spot premium, contract compliance, cost attribution."""

from __future__ import annotations

import pandas as pd


def compute_spot_premium(
    po_df: pd.DataFrame,
    price_df: pd.DataFrame | None = None,
) -> dict:
    """Compute spot buy KPIs from fact_purchase_orders.

    Returns dict with spot_pct_of_volume, spot_premium_avg_pct, annual_spot_cost_usd.
    """
    if po_df.empty:
        return {}

    total_vol = po_df["qty_committed_kg"].sum()
    spot = po_df[po_df["is_spot_purchase"] == True]
    spot_vol = spot["qty_committed_kg"].sum()
    spot_pct = round(spot_vol / total_vol * 100, 2) if total_vol > 0 else 0.0

    spot_cost = (spot["qty_committed_kg"] * spot["price_per_kg"]).sum()
    avg_spot_premium = float(spot["spot_premium_pct"].mean()) if len(spot) > 0 else 0.0

    contract = po_df[po_df["is_spot_purchase"] == False]
    contract_cost = (contract["qty_committed_kg"] * contract["price_per_kg"].fillna(2.0)).sum()

    return {
        "spot_volume_pct": spot_pct,
        "spot_volume_kg": round(float(spot_vol), 1),
        "contract_volume_kg": round(float(total_vol - spot_vol), 1),
        "avg_spot_premium_pct": round(avg_spot_premium, 1),
        "total_spot_cost_usd": round(float(spot_cost), 2),
        "total_contract_cost_usd": round(float(contract_cost), 2),
        "n_spot_orders": len(spot),
        "n_contract_orders": len(contract),
    }


def cost_per_kg_by_model(backtest_df: pd.DataFrame) -> pd.DataFrame:
    """Average cost-per-kg by optimization model from backtest results."""
    if backtest_df.empty:
        return pd.DataFrame()

    return (
        backtest_df.groupby("model")
        .agg(
            avg_total_cost=("total_cost_usd","mean"),
            avg_spot_cost=("spot_cost_usd","mean"),
            avg_waste_kg=("waste_kg","mean"),
            avg_spot_kg=("spot_kg","mean"),
            avg_service_level=("service_level_pct","mean"),
            n_origins=("origin_week","count"),
        )
        .reset_index()
        .sort_values("avg_total_cost")
    )
