"""Backtest & ROI page."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
import duckdb

from dashboard.components.charts import spot_buy_waterfall
from dashboard.components.kpi_cards import kpi_strip


@st.cache_resource
def get_conn():
    db_path = os.getenv("DUCKDB_PATH", str(ROOT / "harvestmind.duckdb"))
    return duckdb.connect(db_path, read_only=True)


conn = get_conn()
st.header("Backtest & ROI")
st.caption("Rolling-origin backtest results and partner ROI analysis")

with st.sidebar:
    st.subheader("Backtest Config")
    n_train = st.slider("Training weeks", 26, 78, 52, 4)
    horizon = st.selectbox("Horizon (weeks)", [1, 2, 4, 8], index=2)
    n_scen = st.slider("SAA Scenarios", 10, 100, 30, 10)
    annual_gmv = st.number_input("Partner Annual GMV ($)", value=3_000_000, step=100_000)
    run_btn = st.button("Run Backtest", type="primary")

if run_btn:
    with st.spinner("Running rolling-origin backtest (this may take 1–3 minutes)…"):
        try:
            orders_df = conn.execute(
                "SELECT ol.product_id, o.buyer_id, o.week_start, ol.qty_ordered_kg "
                "FROM fact_order_lines ol JOIN fact_orders o ON ol.order_id = o.order_id"
            ).df()
            deliveries_df = conn.execute(
                "SELECT supplier_id, product_id, delivery_date, qty_received_kg, qty_rejected_kg "
                "FROM fact_deliveries"
            ).df()

            from backtesting.rolling_origin_engine import RollingOriginEngine, BacktestConfig
            from backtesting.roi_calculator import compute_roi
            from backtesting.procurement_metrics import cost_per_kg_by_model

            cfg = BacktestConfig(n_train_weeks=n_train, horizon_weeks=horizon,
                                 step_weeks=horizon, n_scenarios=n_scen, run_stochastic=True)
            engine = RollingOriginEngine(cfg)
            results_df = engine.run(orders_df, deliveries_df)

            if results_df.empty:
                st.error("Backtest produced no results. Check that enough data is loaded.")
            else:
                st.session_state["backtest_df"] = results_df
                st.session_state["roi"] = compute_roi(results_df, annual_gmv_usd=annual_gmv)
                st.success(f"Backtest complete: {results_df['origin_week'].nunique()} origins evaluated")
        except Exception as e:
            st.error(f"Backtest failed: {e}")

# ── Display results ───────────────────────────────────────────────────────────
if "roi" in st.session_state:
    roi = st.session_state["roi"]
    results_df = st.session_state["backtest_df"]

    if "error" in roi:
        st.warning(f"ROI calc unavailable: {roi['error']}. Showing raw backtest results below.")
    else:
        kpi_strip([
            {"label": "Annual Benefit", "value": f"${roi['total_annual_benefit_usd']:,.0f}", "delta_positive": True},
            {"label": "ROI Multiple", "value": f"{roi['roi_multiple']}×", "delta_positive": True},
            {"label": "Payback", "value": f"{roi['payback_months']} mo", "delta_positive": True},
            {"label": "Service Level Lift", "value": f"+{roi['service_level_improvement_pts']}pts", "delta_positive": True},
            {"label": "Spot Savings", "value": f"{roi['spot_savings_pct']}%", "delta_positive": True},
        ])

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if "error" not in roi:
            st.plotly_chart(spot_buy_waterfall(roi), use_container_width=True)
    with col2:
        st.subheader("Model Comparison")
        from backtesting.procurement_metrics import cost_per_kg_by_model
        summary = cost_per_kg_by_model(results_df)
        st.dataframe(summary, use_container_width=True, hide_index=True)

    st.subheader("Backtest Results (All Origins)")
    st.dataframe(results_df.sort_values("origin_week"), use_container_width=True, hide_index=True)
else:
    st.info("Configure parameters and click **Run Backtest** to see results.")
