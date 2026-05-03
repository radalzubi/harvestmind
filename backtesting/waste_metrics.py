"""Waste and spoilage metrics for backtest reporting."""

from __future__ import annotations

import pandas as pd
import numpy as np


def summarize_waste(
    waste_df: pd.DataFrame,
    deliveries_df: pd.DataFrame | None = None,
) -> dict:
    """Compute waste KPIs from fact_waste_events and optional delivery data."""
    if waste_df.empty:
        return {"total_waste_kg": 0.0, "total_waste_value_usd": 0.0}

    total_kg = float(waste_df["qty_wasted_kg"].sum())
    total_value = float(waste_df.get("estimated_value_usd", pd.Series([0])).sum())

    by_reason = (
        waste_df.groupby("reason_code")["qty_wasted_kg"]
        .sum()
        .sort_values(ascending=False)
        .to_dict()
    )
    by_stage = (
        waste_df.groupby("waste_stage")["qty_wasted_kg"]
        .sum()
        .sort_values(ascending=False)
        .to_dict()
    )

    # Waste rate as % of received volume
    waste_rate_pct = None
    if deliveries_df is not None and not deliveries_df.empty:
        total_received = float(deliveries_df["qty_received_kg"].sum())
        waste_rate_pct = round(total_kg / total_received * 100, 2) if total_received > 0 else None

    return {
        "total_waste_kg": round(total_kg, 1),
        "total_waste_value_usd": round(total_value, 2),
        "waste_rate_pct": waste_rate_pct,
        "by_reason_code": by_reason,
        "by_stage": by_stage,
        "n_events": len(waste_df),
    }


def waste_attribution(waste_df: pd.DataFrame) -> pd.DataFrame:
    """Classify waste by planning-caused vs execution-caused.

    Planning-caused: over_commitment, demand_miss
    Execution-caused: quality_reject, cold_chain_failure, supplier_error, transport_damage
    """
    if waste_df.empty:
        return pd.DataFrame()

    planning_codes = {"over_commitment", "demand_miss"}
    df = waste_df.copy()
    df["attribution"] = df["reason_code"].apply(
        lambda r: "planning" if r in planning_codes else "execution"
    )
    return (
        df.groupby(["attribution", "reason_code"])["qty_wasted_kg"]
        .agg(["sum","count"])
        .rename(columns={"sum":"total_kg","count":"n_events"})
        .reset_index()
        .sort_values("total_kg", ascending=False)
    )
