"""Page 3 — Backtest Results.

Evidence the model could have improved historical decisions.
Critical: perfect hindsight is labeled as theoretical upper bound."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from dashboard.components.cards import section
from dashboard.components.charts import (
    cost_lines_over_time, policy_comparison_bar,
)
from dashboard.components.empty import db_unavailable, empty_state
from dashboard.lib import db, theme
from dashboard.lib.formatters import fmt_currency

theme.apply(page_title="Backtest")

if not db.is_available():
    db_unavailable()
    st.stop()

conn = db.get_conn()

# ── sidebar filters ───────────────────────────────────────────────────────
with st.sidebar:
    train_weeks = st.slider("Training window (weeks)", 26, 78, 52, 4)
    horizon = st.selectbox("Planning horizon (weeks)", [1, 2, 4, 8], index=2)
    n_scen = st.slider("SAA scenarios", 10, 100, 30, 10)
    annual_gmv = st.number_input("Annual GMV ($)", 500_000, 50_000_000,
                                 3_000_000, 100_000)
    st.divider()
    run_btn = st.button("Run backtest", type="primary", use_container_width=True)

# ── Header ────────────────────────────────────────────────────────────────
theme.page_header(title="Backtest")

# ── Run on click ──────────────────────────────────────────────────────────
results_df: pd.DataFrame | None = st.session_state.get("backtest_results")
roi_dict = st.session_state.get("backtest_roi")

if run_btn:
    with st.spinner("Running rolling-origin backtest — this can take 1–3 minutes…"):
        try:
            orders_df = conn.execute(
                "SELECT ol.product_id, o.buyer_id, o.week_start, ol.qty_ordered_kg "
                "FROM fact_order_lines ol JOIN fact_orders o ON ol.order_id = o.order_id"
            ).df()
            deliveries_df = conn.execute(
                "SELECT supplier_id, product_id, delivery_date, qty_received_kg, qty_rejected_kg "
                "FROM fact_deliveries"
            ).df()

            from backtesting.rolling_origin_engine import (
                BacktestConfig, RollingOriginEngine,
            )
            from backtesting.roi_calculator import compute_roi

            cfg = BacktestConfig(
                n_train_weeks=train_weeks, horizon_weeks=horizon,
                step_weeks=horizon, n_scenarios=n_scen,
                run_stochastic=True,
            )
            results_df = RollingOriginEngine(cfg).run(orders_df, deliveries_df)

            if not results_df.empty:
                roi_dict = compute_roi(results_df, annual_gmv_usd=annual_gmv)
                st.session_state["backtest_results"] = results_df
                st.session_state["backtest_roi"] = roi_dict
                st.success(
                    f"Backtest complete: {results_df['origin_week'].nunique()} origins evaluated."
                )
            else:
                st.error("Backtest produced no rows. Check that enough order history is loaded.")
        except Exception as e:
            st.error(f"Backtest failed ({type(e).__name__}). See the server log.")

# ── Display ───────────────────────────────────────────────────────────────
if results_df is None or results_df.empty:
    empty_state(
        "Run a backtest to see results",
        "Configure parameters in the sidebar and click Run backtest.",
    )
    st.stop()

# Summary KPIs from ROI
section(f"Results across {results_df['origin_week'].nunique()} origins")

if roi_dict and "error" not in roi_dict:
    kpis = [
        ("Annual benefit",  fmt_currency(roi_dict.get("total_annual_benefit_usd"), compact=True),
         f"vs ${roi_dict['annual_subscription_usd']:,.0f} subscription"),
        ("ROI multiple",    f"{roi_dict.get('roi_multiple', 0):.1f}×",
         f"Payback: {roi_dict.get('payback_months', 0):.1f} mo"),
        ("Service-level lift", f"+{roi_dict.get('service_level_improvement_pts', 0):.1f} pts",
         f"{roi_dict.get('baseline_service_level_pct', 0):.1f}% → "
         f"{roi_dict.get('target_service_level_pct', 0):.1f}%"),
        ("Spot reduction",  f"{roi_dict.get('spot_savings_pct', 0):.1f}%",
         f"Spot kg: -{roi_dict.get('annual_spot_savings_usd', 0):,.0f}/yr"),
    ]
    cols = st.columns(4, gap="medium")
    for col, (label, val, sub) in zip(cols, kpis):
        with col:
            st.markdown(
                f'<div class="hm-card"><div class="hm-label">{label}</div>'
                f'<div class="hm-value">{val}</div>'
                f'<div class="hm-sub">{sub}</div></div>',
                unsafe_allow_html=True,
            )

# Policy comparison bar
section("Cost by policy")
from backtesting.procurement_metrics import cost_per_kg_by_model
summary = cost_per_kg_by_model(results_df)
st.plotly_chart(policy_comparison_bar(summary), use_container_width=True)

# Origin-by-origin table
section("Per-origin detail")
detail = results_df.copy()
detail["spot_cost_usd"] = detail["spot_cost_usd"].fillna(0)
detail["total_cost_usd"] = detail["total_cost_usd"].fillna(0)
detail["service_level_pct"] = detail["service_level_pct"].fillna(0)

# Pivot: one row per origin, one column per policy
pivot = detail.pivot_table(
    index="origin_week",
    columns="model",
    values=["total_cost_usd", "spot_kg", "service_level_pct"],
    aggfunc="mean",
).round(2).sort_index()
pivot.columns = [f"{a} ({b})" for a, b in pivot.columns]
st.dataframe(pivot, use_container_width=True)

# Cost lines over time
if not detail.empty:
    section("Cost trend across origins")
    line_df = detail.pivot_table(
        index="origin_week", columns="model", values="total_cost_usd", aggfunc="mean"
    ).reset_index()
    fig = cost_lines_over_time(
        line_df, x="origin_week",
        lines={c: c.replace("_", " ").title()
               for c in line_df.columns if c != "origin_week"},
    )
    st.plotly_chart(fig, use_container_width=True)
