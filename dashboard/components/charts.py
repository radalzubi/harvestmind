"""Plotly chart helpers for the HarvestMind dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


BRAND_GREEN = "#2d6a4f"
BRAND_AMBER = "#e76f51"
PALETTE = [BRAND_GREEN, BRAND_AMBER, "#74c69d", "#f4a261", "#457b9d", "#a8dadc"]


def demand_forecast_chart(
    actual_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    product_id: str,
) -> go.Figure:
    """Line chart: actual demand vs forecast with 80% CI band."""
    act = actual_df[actual_df["product_id"] == product_id].sort_values("week_start")
    if not forecast_df.empty and "product_id" in forecast_df.columns:
        fct = forecast_df[forecast_df["product_id"] == product_id].sort_values("week_start")
    else:
        fct = pd.DataFrame(columns=["week_start", "forecast_kg", "lower_80", "upper_80"])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=act["week_start"], y=act["qty_ordered_kg"],
        name="Actual", line=dict(color=BRAND_GREEN, width=2),
        mode="lines+markers",
    ))
    if not fct.empty and "forecast_kg" in fct.columns:
        fig.add_trace(go.Scatter(
            x=fct["week_start"], y=fct["forecast_kg"],
            name="Forecast", line=dict(color=BRAND_AMBER, width=2, dash="dash"),
        ))
        if "upper_80" in fct.columns and "lower_80" in fct.columns:
            fig.add_trace(go.Scatter(
                x=pd.concat([fct["week_start"], fct["week_start"][::-1]]),
                y=pd.concat([fct["upper_80"], fct["lower_80"][::-1]]),
                fill="toself",
                fillcolor="rgba(231,111,81,0.15)",
                line=dict(color="rgba(255,255,255,0)"),
                name="80% CI",
                showlegend=True,
            ))

    fig.update_layout(
        title=f"Demand Forecast — {product_id}",
        xaxis_title="Week",
        yaxis_title="kg",
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def spot_buy_waterfall(roi: dict) -> go.Figure:
    """Waterfall chart: cost savings breakdown."""
    categories = [
        "Spot Premium Savings",
        "Waste Reduction",
        "Lost Sale Recovery",
        "Subscription Cost",
        "Net Benefit",
    ]
    values = [
        roi.get("annual_spot_savings_usd", 0),
        roi.get("annual_waste_value_savings_usd", 0),
        roi.get("annual_lost_sale_recovery_usd", 0),
        -roi.get("annual_subscription_usd", 0),
        roi.get("net_annual_benefit_usd", 0),
    ]
    measure = ["relative", "relative", "relative", "relative", "total"]
    colors = [BRAND_GREEN, BRAND_GREEN, BRAND_GREEN, BRAND_AMBER, "#457b9d"]

    fig = go.Figure(go.Waterfall(
        name="ROI", orientation="v",
        measure=measure,
        x=categories,
        y=values,
        text=[f"${v:,.0f}" for v in values],
        textposition="outside",
        connector=dict(line=dict(color="#ccc")),
        increasing=dict(marker=dict(color=BRAND_GREEN)),
        decreasing=dict(marker=dict(color=BRAND_AMBER)),
        totals=dict(marker=dict(color="#457b9d")),
    ))
    fig.update_layout(
        title="Annual ROI Waterfall",
        plot_bgcolor="white",
        paper_bgcolor="white",
        yaxis_title="USD",
        showlegend=False,
    )
    return fig


def gamma_frontier_chart(frontier_df: pd.DataFrame) -> go.Figure:
    """Scatter: Γ robustness frontier (cost vs service level)."""
    fig = px.scatter(
        frontier_df,
        x="avg_total_cost",
        y="avg_service_level",
        color="model",
        text="model",
        title="Model Comparison: Cost vs Service Level",
        labels={"avg_total_cost": "Avg Cost / Origin ($)", "avg_service_level": "Avg Service Level (%)"},
        color_discrete_sequence=PALETTE,
    )
    fig.update_traces(textposition="top center", marker_size=12)
    fig.update_layout(plot_bgcolor="white", paper_bgcolor="white")
    return fig


def weekly_waste_bar(waste_df: pd.DataFrame) -> go.Figure:
    """Stacked bar: weekly waste by reason code."""
    if waste_df.empty:
        return go.Figure()
    fig = px.bar(
        waste_df,
        x="event_date",
        y="qty_wasted_kg",
        color="reason_code",
        title="Weekly Waste by Reason Code",
        labels={"qty_wasted_kg": "Waste (kg)", "event_date": "Week"},
        color_discrete_sequence=PALETTE,
    )
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        barmode="stack",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig
