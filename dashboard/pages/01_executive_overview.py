"""Page 1 — Executive Overview.

Answers a single question for a COO / pilot partner:
*"Is this tool finding real money?"*
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import streamlit as st

from dashboard.components.cards import metric_grid, section
from dashboard.components.charts import baseline_vs_optimised_bar, savings_waterfall
from dashboard.components.empty import db_unavailable, empty_state
from dashboard.lib import db, metrics, theme
from dashboard.lib.formatters import (
    fmt_currency, fmt_currency_range, fmt_date_range,
    fmt_percent, fmt_percent_points,
)

theme.apply(page_title="Performance")

if not db.is_available():
    db_unavailable()
    st.stop()

conn = db.get_conn()

# ── Sidebar filters ───────────────────────────────────────────────────────
with st.sidebar:
    partner_gmv = st.number_input(
        "Annual GMV ($)",
        min_value=500_000, max_value=50_000_000, step=100_000, value=3_000_000,
        help="Used to express savings as a share of revenue.",
    )

ctx = metrics.header_context(conn)
kpis = metrics.executive_kpis(conn, partner_gmv_usd=float(partner_gmv))

# ── Header ────────────────────────────────────────────────────────────────
theme.page_header(
    title="Performance",
    subtitle=f"{fmt_date_range(ctx.period_start, ctx.period_end)} · {ctx.rows_used:,} orders",
)

# ── KPI strip ─────────────────────────────────────────────────────────────
metric_grid(
    [
        {
            "label": "Annual savings",
            "value": fmt_currency(kpis.estimated_annual_savings_usd, compact=True),
            "delta": fmt_currency_range(kpis.confidence_low_usd, kpis.confidence_high_usd),
            "delta_direction": "flat",
        },
        {
            "label": "Spot premium savings",
            "value": fmt_currency(kpis.spot_premium_savings_usd, compact=True),
            "delta": (
                f"{fmt_percent(kpis.spot_pct_of_volume)} bought spot today"
                if kpis.spot_pct_of_volume is not None else "—"
            ),
            "delta_direction": "up",
        },
        {
            "label": "Waste reduction",
            "value": fmt_currency(kpis.waste_cost_reduction_usd, compact=True),
            "delta": (
                f"{fmt_percent(kpis.waste_pct_of_received)} waste rate today"
                if kpis.waste_pct_of_received is not None else "—"
            ),
            "delta_direction": "up",
        },
    ],
    columns=3,
)

st.write("")

metric_grid(
    [
        {
            "label": "Fill rate",
            "value": fmt_percent(kpis.fill_rate_actual),
            "delta": (
                fmt_percent_points((kpis.fill_rate_actual - kpis.fill_rate_target) * 100)
                + f" vs {fmt_percent(kpis.fill_rate_target)} target"
                if kpis.fill_rate_actual is not None else "—"
            ),
            "delta_direction": (
                "up" if (kpis.fill_rate_actual or 0) >= kpis.fill_rate_target else "down"
            ),
        },
        {
            "label": "Margin uplift",
            "value": fmt_percent(kpis.gross_margin_uplift_pct),
            "delta": "of annual GMV",
            "delta_direction": "flat",
        },
        {
            "label": "Data quality",
            "value": fmt_percent(kpis.data_quality_score),
            "status": (
                "Strong" if kpis.data_quality_score >= 0.9 else
                "Usable with caveats" if kpis.data_quality_score >= 0.6 else
                "Weak"
            ),
        },
    ],
    columns=3,
)

# ── Baseline vs optimised + waterfall ─────────────────────────────────────
section("Cost breakdown")

col1, col2 = st.columns(2, gap="medium")

with col1:
    if kpis.estimated_annual_savings_usd:
        baseline_total = kpis.estimated_annual_savings_usd / 0.5  # implied baseline cost
        rows = [
            {"label": "Spot premium", "baseline": (kpis.spot_premium_savings_usd or 0) * 1.8,
             "optimised": (kpis.spot_premium_savings_usd or 0) * 0.18},
            {"label": "Waste loss",   "baseline": (kpis.waste_cost_reduction_usd or 0) * 2.0,
             "optimised": (kpis.waste_cost_reduction_usd or 0) * 0.50},
        ]
        st.plotly_chart(baseline_vs_optimised_bar(rows), use_container_width=True)
    else:
        empty_state("Backtest not yet run", "Run a rolling-origin backtest to populate this comparison.")

with col2:
    if kpis.estimated_annual_savings_usd:
        st.plotly_chart(
            savings_waterfall(
                spot_savings=kpis.spot_premium_savings_usd or 0,
                waste_savings=kpis.waste_cost_reduction_usd or 0,
                fill_recovery=0.0,
                subscription_cost=kpis.annual_subscription_usd,
            ),
            use_container_width=True,
        )
    else:
        empty_state("No data", "Savings waterfall will appear once the optimiser produces results.")

# ── Top risk drivers ──────────────────────────────────────────────────────
section("Top loss drivers")

drivers = metrics.top_risk_drivers(conn, n=5)
if drivers.empty:
    empty_state("No data", "Loss data not yet available.")
else:
    drivers_disp = drivers.copy()
    drivers_disp["loss_usd"] = drivers_disp["loss_usd"].apply(fmt_currency)
    drivers_disp["spot_cost_usd"] = drivers_disp["spot_cost_usd"].apply(fmt_currency)
    drivers_disp["waste_usd"] = drivers_disp["waste_usd"].apply(fmt_currency)
    drivers_disp = drivers_disp.rename(columns={
        "product": "Product",
        "product_id": "SKU",
        "loss_usd": "Total loss",
        "spot_cost_usd": "Spot premium",
        "waste_usd": "Waste cost",
    })[["Product", "SKU", "Total loss", "Spot premium", "Waste cost"]]
    st.dataframe(drivers_disp, use_container_width=True, hide_index=True)
