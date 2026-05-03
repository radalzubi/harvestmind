"""Supply Planning page: run optimizer and review commitments."""

import os
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
import duckdb

from dashboard.components.charts import demand_forecast_chart, gamma_frontier_chart


@st.cache_resource
def get_conn():
    db_path = os.getenv("DUCKDB_PATH", str(ROOT / "harvestmind.duckdb"))
    return duckdb.connect(db_path, read_only=True)


conn = get_conn()

st.header("Supply Planning")
st.caption("Configure and run the optimization model for the upcoming week")

# ── Sidebar controls ──────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("Planning Parameters")
    week_start = st.date_input("Planning Week", value=date.today() + timedelta(days=(7 - date.today().weekday())))
    model_type = st.selectbox("Model", ["gamma_robust", "deterministic", "two_stage_sp", "cvar"])
    gamma = st.slider("Γ (robustness)", 0.0, 12.0, 4.0, 0.5) if model_type in ("gamma_robust",) else None
    n_scenarios = st.slider("SAA Scenarios", 10, 200, 50, 10) if model_type in ("two_stage_sp","cvar") else None
    run_btn = st.button("Run Optimizer", type="primary")

# ── Demand forecast ───────────────────────────────────────────────────────────
st.subheader("Demand Forecast")
try:
    orders_df = conn.execute(
        "SELECT ol.product_id, o.week_start, SUM(ol.qty_ordered_kg) AS qty_ordered_kg "
        "FROM fact_order_lines ol JOIN fact_orders o ON ol.order_id = o.order_id "
        "WHERE o.week_start >= CURRENT_DATE - INTERVAL 182 DAYS "
        "GROUP BY 1, 2 ORDER BY 1, 2"
    ).df()

    if not orders_df.empty:
        products = sorted(orders_df["product_id"].unique())
        sel_product = st.selectbox("Product", products)
        st.plotly_chart(
            demand_forecast_chart(orders_df, pd.DataFrame(), sel_product),
            use_container_width=True,
        )
    else:
        st.info("No order history found. Run the synthetic data generator first.")
except Exception as e:
    st.warning(f"Demand chart unavailable: {e}")

# ── Run optimizer ─────────────────────────────────────────────────────────────
if run_btn:
    with st.spinner("Running optimizer…"):
        try:
            orders_full = conn.execute(
                "SELECT ol.product_id, o.week_start, SUM(ol.qty_ordered_kg) AS demand_kg "
                "FROM fact_order_lines ol JOIN fact_orders o ON ol.order_id = o.order_id "
                "GROUP BY 1, 2"
            ).df()
            supply_df = conn.execute(
                "SELECT supplier_id, product_id, delivery_date AS week_start, "
                "AVG(qty_received_kg) AS capacity_kg, 2.0 AS price_per_kg "
                "FROM fact_deliveries GROUP BY 1, 2, 3"
            ).df()

            mean_demand = orders_full.groupby("product_id")["demand_kg"].mean().reset_index()
            mean_demand["week_start"] = week_start
            supply_agg = supply_df.groupby(["supplier_id","product_id"]).agg(
                capacity_kg=("capacity_kg","mean"), price_per_kg=("price_per_kg","mean")
            ).reset_index().assign(week_start=week_start)

            if model_type == "deterministic":
                from optimization.lp_baseline import LPBaseline
                result = LPBaseline().solve(mean_demand, supply_agg)
            elif model_type == "gamma_robust":
                from optimization.gamma_robust_lp import GammaRobustLP
                result = GammaRobustLP(gamma=gamma).solve(mean_demand, supply_agg)
            else:
                st.info(f"Model '{model_type}' requires the API server. Run `make serve` and use the API.")
                result = None

            if result and result.get("status") in ("optimal","locallyOptimal"):
                st.success(f"Solver: {result['status']} · Objective: ${result['objective']:,.2f}")

                # Build commitments table
                rows = []
                for (i,j,t), qty in result.get("x",{}).items():
                    if qty and float(qty) > 0.01:
                        rows.append({"Supplier": i, "Product": j, "Committed (kg)": round(float(qty),1)})
                if rows:
                    st.subheader("Recommended Commitments")
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            elif result:
                st.error(f"Solver status: {result.get('status')}")
        except Exception as e:
            st.error(f"Optimization failed: {e}")

# ── Γ frontier ────────────────────────────────────────────────────────────────
st.subheader("Robustness Frontier")
st.caption("Run backtest to populate model comparison data")
try:
    bt_df = conn.execute(
        "SELECT model, AVG(service_level_pct) AS avg_service_level, "
        "AVG(total_cost_usd) AS avg_total_cost, AVG(spot_kg) AS avg_spot_kg, "
        "AVG(waste_kg) AS avg_waste_kg "
        "FROM planning_scenarios WHERE solver_status IN ('optimal','locallyOptimal') "
        "GROUP BY 1"
    ).df()
    if not bt_df.empty:
        st.plotly_chart(gamma_frontier_chart(bt_df), use_container_width=True)
    else:
        st.info("No backtest results yet. Go to Backtest & ROI to run.")
except Exception:
    st.info("Run a backtest to see the cost vs service level frontier.")
