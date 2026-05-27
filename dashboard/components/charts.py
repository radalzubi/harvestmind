"""Plotly chart helpers for the HarvestMind dashboard.

Every chart factory returns a fully-styled :class:`plotly.graph_objects.Figure`.
Pages call ``st.plotly_chart(fig, use_container_width=True)``.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dashboard.lib.theme import (
    ACCENT,
    BAD,
    GOOD,
    INFO,
    INK,
    INK_FAINT,
    INK_MUTED,
    LINE,
    PALETTE,
    SURFACE,
    WARN,
    plotly_layout,
)


# ---------------------------------------------------------------------------
# Page-1 charts
# ---------------------------------------------------------------------------

def baseline_vs_optimised_bar(
    rows: list[dict],
    *,
    title: str = "Baseline vs optimised",
) -> go.Figure:
    """Two-bar comparison. ``rows`` = ``[{label, baseline, optimised}, ...]``."""
    df = pd.DataFrame(rows)
    fig = go.Figure(
        data=[
            go.Bar(
                name="Baseline (actual)", x=df["label"], y=df["baseline"],
                marker_color=INK_FAINT, hovertemplate="%{x}: %{y:$,.0f}<extra>Baseline</extra>",
            ),
            go.Bar(
                name="Optimised", x=df["label"], y=df["optimised"],
                marker_color=ACCENT, hovertemplate="%{x}: %{y:$,.0f}<extra>Optimised</extra>",
            ),
        ]
    )
    fig.update_layout(**plotly_layout(height=300, title=title), barmode="group", bargap=0.35)
    fig.update_yaxes(tickformat="$,.0f")
    return fig


def savings_waterfall(
    *, spot_savings: float, waste_savings: float, fill_recovery: float,
    subscription_cost: float,
) -> go.Figure:
    """Waterfall: spot + waste + fill recovery − subscription = net."""
    measure = ["relative", "relative", "relative", "relative", "total"]
    x = [
        "Spot premium savings", "Waste reduction",
        "Lost-sale recovery", "Subscription cost", "Net annual benefit",
    ]
    y = [spot_savings, waste_savings, fill_recovery, -subscription_cost,
         spot_savings + waste_savings + fill_recovery - subscription_cost]

    fig = go.Figure(
        go.Waterfall(
            name="ROI", orientation="v",
            measure=measure, x=x, y=y,
            text=[f"${v:,.0f}" for v in y], textposition="outside",
            connector={"line": {"color": LINE}},
            increasing={"marker": {"color": GOOD}},
            decreasing={"marker": {"color": BAD}},
            totals={"marker": {"color": INFO}},
            hovertemplate="%{x}: %{y:$,.0f}<extra></extra>",
        )
    )
    fig.update_layout(**plotly_layout(height=320, title="Annual savings waterfall"))
    fig.update_yaxes(tickformat="$,.0f")
    return fig


# ---------------------------------------------------------------------------
# Page-3 charts (backtest)
# ---------------------------------------------------------------------------

def policy_comparison_bar(df: pd.DataFrame) -> go.Figure:
    """``df`` columns: model, avg_total_cost, avg_spot_cost, avg_waste_kg."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Spot cost", x=df["model"], y=df.get("avg_spot_cost", 0),
        marker_color=BAD, hovertemplate="%{x}: %{y:$,.0f}<extra>Spot</extra>",
    ))
    fig.add_trace(go.Bar(
        name="Other cost",
        x=df["model"],
        y=df.get("avg_total_cost", 0) - df.get("avg_spot_cost", 0),
        marker_color=ACCENT,
        hovertemplate="%{x}: %{y:$,.0f}<extra>Other</extra>",
    ))
    fig.update_layout(
        **plotly_layout(height=320, title="Average cost per origin, by policy"),
        barmode="stack",
    )
    fig.update_yaxes(tickformat="$,.0f")
    return fig


def cost_lines_over_time(df: pd.DataFrame, *, x: str, lines: dict[str, str]) -> go.Figure:
    """``lines = {column_name: legend_label}``. ``df`` must contain ``x`` + cols."""
    fig = go.Figure()
    palette = [BAD, ACCENT, INK_FAINT, WARN, INFO]
    for i, (col, label) in enumerate(lines.items()):
        if col not in df.columns:
            continue
        fig.add_trace(go.Scatter(
            x=df[x], y=df[col], mode="lines+markers", name=label,
            line=dict(color=palette[i % len(palette)], width=2),
            hovertemplate="%{x|%b %d, %Y}: %{y:$,.0f}<extra>" + label + "</extra>",
        ))
    fig.update_layout(**plotly_layout(height=320, title="Cost over time"))
    fig.update_yaxes(tickformat="$,.0f")
    return fig


# ---------------------------------------------------------------------------
# Page-4 charts (waste / spot)
# ---------------------------------------------------------------------------

def horizontal_value_bar(df: pd.DataFrame, *, x: str, y: str,
                         title: str, color: str = ACCENT) -> go.Figure:
    df = df.head(15).iloc[::-1]
    fig = go.Figure(
        go.Bar(
            x=df[x], y=df[y], orientation="h",
            marker_color=color,
            text=[f"${v:,.0f}" for v in df[x]] if "usd" in x else [f"{v:,.0f}" for v in df[x]],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}: %{x:,.0f}<extra></extra>",
        )
    )
    layout = plotly_layout(height=max(280, 28 * len(df)), title=title)
    layout["margin"]["r"] = 80  # room for outside text labels
    fig.update_layout(**layout)
    # Extend x-axis 25% past max so the rightmost label isn't clipped
    max_val = df[x].max()
    fig.update_xaxes(range=[0, max_val * 1.25])
    if "usd" in x:
        fig.update_xaxes(tickformat="$,.0f")
    else:
        fig.update_xaxes(tickformat=",.0f")
    return fig


def stacked_bar(df: pd.DataFrame, *, x: str, y: str, color: str,
                title: str) -> go.Figure:
    fig = px.bar(
        df, x=x, y=y, color=color, color_discrete_sequence=PALETTE,
        title=title,
    )
    fig.update_layout(**plotly_layout(height=320, title=title), barmode="stack")
    fig.update_yaxes(tickformat="$,.0f" if "usd" in y.lower() else ",.0f")
    return fig


def risk_heatmap(df: pd.DataFrame) -> go.Figure:
    """Heatmap of risk by product × week.  ``df`` columns: product, week, risk."""
    pv = df.pivot_table(index="product", columns="week", values="risk", aggfunc="mean")
    if pv.empty:
        return go.Figure()
    pv = pv.fillna(0)
    fig = go.Figure(
        go.Heatmap(
            z=pv.values, x=[c.strftime("%b %d") for c in pv.columns], y=pv.index,
            colorscale=[[0, "#DCFCE7"], [0.4, "#FEF3C7"], [0.7, "#FFEDD5"], [1.0, "#FEE2E2"]],
            zmin=0, zmax=1,
            hovertemplate="%{y}<br>%{x}<br>Risk: %{z:.0%}<extra></extra>",
            colorbar=dict(title="Risk", tickformat=".0%", thickness=10, len=0.5),
        )
    )
    fig.update_layout(
        **plotly_layout(height=max(260, 32 * len(pv)), title="Product × week risk heatmap"),
    )
    return fig


def waste_vs_shortage_scatter(df: pd.DataFrame) -> go.Figure:
    """Per-product scatter: waste $ on x, spot $ on y, bubble size by total losses."""
    if df.empty:
        return go.Figure()
    df = df.fillna(0)
    fig = go.Figure(
        go.Scatter(
            x=df["waste_usd"], y=df["spot_cost_usd"],
            mode="markers+text",
            marker=dict(
                size=(df["waste_usd"] + df["spot_cost_usd"]).clip(50, 5000) ** 0.5,
                color=ACCENT, opacity=0.7, line=dict(color=INK, width=0.5),
            ),
            text=df["product"], textposition="top center", textfont=dict(size=10, color=INK_MUTED),
            hovertemplate=(
                "%{text}<br>Waste $%{x:,.0f}<br>Spot $%{y:,.0f}<extra></extra>"
            ),
        )
    )
    fig.update_layout(**plotly_layout(height=380, title="Waste vs spot exposure tradeoff"))
    fig.update_xaxes(tickformat="$,.0f", title_text="Waste cost ($)")
    fig.update_yaxes(tickformat="$,.0f", title_text="Spot premium cost ($)")
    return fig


# ---------------------------------------------------------------------------
# Page-5 charts (supplier / buyer trends)
# ---------------------------------------------------------------------------

def trend_lines(df: pd.DataFrame, *, x: str, y: str, color: str,
                title: str, y_format: str = ",.0f") -> go.Figure:
    fig = px.line(
        df, x=x, y=y, color=color, color_discrete_sequence=PALETTE,
        markers=True, title=title,
    )
    fig.update_layout(**plotly_layout(height=320, title=title))
    fig.update_yaxes(tickformat=y_format)
    return fig


def concentration_donut(df: pd.DataFrame) -> go.Figure:
    """Single donut for supplier concentration. We use this exactly once
    because concentration is genuinely a share-of-whole question."""
    if df.empty:
        return go.Figure()
    fig = go.Figure(
        go.Pie(
            labels=df["supplier"], values=df["committed_kg"], hole=0.55,
            marker=dict(colors=PALETTE, line=dict(color=SURFACE, width=2)),
            textinfo="label+percent",
            hovertemplate="%{label}: %{value:,.0f} kg (%{percent})<extra></extra>",
        )
    )
    fig.update_layout(**plotly_layout(height=340, title="Supplier concentration"))
    return fig
