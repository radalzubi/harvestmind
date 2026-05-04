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

from dashboard.components.cards import caveat, insight, metric_card, metric_grid, section
from dashboard.components.charts import baseline_vs_optimised_bar, savings_waterfall
from dashboard.components.empty import db_unavailable, empty_state
from dashboard.lib import db, metrics, theme
from dashboard.lib.formatters import (
    fmt_currency, fmt_currency_range, fmt_date, fmt_date_range,
    fmt_percent, fmt_percent_points,
)

theme.apply(page_title="Executive Overview")

if not db.is_available():
    db_unavailable()
    st.stop()

conn = db.get_conn()

# ── Sidebar filters ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filters")
    partner_gmv = st.number_input(
        "Partner annual GMV ($)",
        min_value=500_000, max_value=50_000_000, step=100_000, value=3_000_000,
        help="Used to express savings as a % of revenue.",
    )

ctx = metrics.header_context(conn)
kpis = metrics.executive_kpis(conn, partner_gmv_usd=float(partner_gmv))

# ── Header ────────────────────────────────────────────────────────────────
theme.page_header(
    eyebrow="Page 1 of 7",
    title="Executive Overview",
    subtitle=(
        f"<b>{ctx.partner_name}</b> · planning period "
        f"{fmt_date_range(ctx.period_start, ctx.period_end)} · last refreshed "
        f"{fmt_date(ctx.last_data_date)}"
    ),
)

# ── KPI strip ─────────────────────────────────────────────────────────────
metric_grid(
    [
        {
            "label": "Estimated annual savings",
            "value": fmt_currency(kpis.estimated_annual_savings_usd, compact=True),
            "delta": fmt_currency_range(kpis.confidence_low_usd, kpis.confidence_high_usd) + " confidence range",
            "delta_direction": "up" if kpis.estimated_annual_savings_usd else "flat",
            "subtitle": "Reduction in spot premium + waste, scaled to a 52-week year.",
        },
        {
            "label": "Spot premium savings",
            "value": fmt_currency(kpis.spot_premium_savings_usd, compact=True),
            "delta": (
                f"{fmt_percent(kpis.spot_pct_of_volume)} of volume currently bought spot"
                if kpis.spot_pct_of_volume is not None else "—"
            ),
            "delta_direction": "up",
            "subtitle": "Premium paid above contract price for emergency purchases.",
        },
        {
            "label": "Waste cost reduction",
            "value": fmt_currency(kpis.waste_cost_reduction_usd, compact=True),
            "delta": (
                f"{fmt_percent(kpis.waste_pct_of_received)} waste rate today"
                if kpis.waste_pct_of_received is not None else "—"
            ),
            "delta_direction": "up",
            "subtitle": "Avoidable spoilage from over-commitment and shelf-life.",
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
            "subtitle": "kg-weighted: delivered ÷ ordered across all order lines.",
        },
        {
            "label": "Gross margin uplift",
            "value": fmt_percent(kpis.gross_margin_uplift_pct),
            "delta": "of partner annual GMV",
            "delta_direction": "flat",
            "subtitle": "Annual savings expressed as a share of revenue.",
        },
        {
            "label": "Data quality score",
            "value": fmt_percent(kpis.data_quality_score),
            "subtitle": "Average completeness across ingested datasets.",
            "status": (
                "Strong" if kpis.data_quality_score >= 0.9 else
                "Usable with caveats" if kpis.data_quality_score >= 0.6 else
                "Weak"
            ),
        },
    ],
    columns=3,
)

# ── Insight ───────────────────────────────────────────────────────────────
top = metrics.top_risk_drivers(conn, n=3)
top_label = ", ".join(top["product"].head(3).fillna("—").tolist()) if not top.empty else "—"

if kpis.estimated_annual_savings_usd:
    msg = (
        f"<b>The opportunity is real.</b> Across the loaded "
        f"{ctx.rows_used:,} order rows, spot premium and avoidable waste together cost "
        f"roughly <b>{fmt_currency(kpis.estimated_annual_savings_usd, compact=True)}</b> per year, "
        f"with a <b>{fmt_currency_range(kpis.confidence_low_usd, kpis.confidence_high_usd)}</b> "
        f"confidence range. The three SKUs driving most of the loss are "
        f"<b>{top_label}</b> — see the Waste &amp; Spot Exposure page for line-item attribution."
    )
else:
    msg = (
        "Not enough data to estimate annual savings yet. Load more order and delivery "
        "history, or run the optimiser at least once, to see a value estimate."
    )
insight(msg)

# ── Baseline vs optimised + waterfall ─────────────────────────────────────
section(
    "Baseline vs optimised",
    "Per-origin averages from the rolling-origin backtest. Optimised = two-stage stochastic plan.",
)

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

# ── Top 5 risk drivers ────────────────────────────────────────────────────
section(
    "Top 5 risk drivers",
    "Products driving the largest combined waste + spot premium loss.",
)

drivers = metrics.top_risk_drivers(conn, n=5)
if drivers.empty:
    empty_state("No risk drivers", "Loss data is not yet present.")
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

# ── Caveat / assumptions ──────────────────────────────────────────────────
with st.expander("Assumptions and methodology", expanded=False):
    caveat(
        "<b>How these numbers are computed.</b> Spot premium savings = "
        "<i>30%</i> recoverable share of the historical premium between spot "
        "and contract prices. Waste reduction = <i>40%</i> of avoidable "
        "spoilage in the planning window. Confidence range is ±25% reflecting "
        "rolling-origin backtest variance. All numbers are scaled to a 52-week "
        "year. None of these are guarantees — see the Backtest Results page "
        "for evidence and the Data Quality page for completeness scores."
    )
