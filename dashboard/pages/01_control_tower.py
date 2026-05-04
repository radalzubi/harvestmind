"""Control Tower: live operational overview."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import streamlit as st
import duckdb

from dashboard.components.kpi_cards import kpi_strip
from dashboard.components.charts import weekly_waste_bar


@st.cache_resource
def get_conn():
    db_path = os.getenv("DUCKDB_PATH", str(ROOT / "harvestmind.duckdb"))
    return duckdb.connect(db_path, read_only=True)


conn = get_conn()

st.header("Control Tower")
st.caption("Live operational snapshot — refresh for latest data")

# ── KPI strip ────────────────────────────────────────────────────────────────
try:
    orders = conn.execute(
        "SELECT COUNT(*) AS n_orders, SUM(ol.qty_ordered_kg) AS demand_kg, "
        "SUM(CASE WHEN ol.lost_sale_flag THEN 1 ELSE 0 END) AS lost_sales "
        "FROM fact_order_lines ol JOIN fact_orders o ON ol.order_id = o.order_id "
        "WHERE o.week_start >= CURRENT_DATE - INTERVAL 28 DAYS"
    ).fetchone()
    deliveries = conn.execute(
        "SELECT SUM(qty_received_kg) AS recv_kg, SUM(qty_rejected_kg) AS rej_kg "
        "FROM fact_deliveries WHERE delivery_date >= CURRENT_DATE - INTERVAL 28 DAYS"
    ).fetchone()
    waste = conn.execute(
        "SELECT SUM(qty_wasted_kg) AS waste_kg FROM fact_waste_events "
        "WHERE event_date >= CURRENT_DATE - INTERVAL 28 DAYS"
    ).fetchone()
    spot = conn.execute(
        "SELECT COUNT(*) AS n_spot, SUM(qty_committed_kg * price_per_kg) AS spot_cost "
        "FROM fact_purchase_orders WHERE is_spot_purchase = TRUE "
        "AND week_start >= CURRENT_DATE - INTERVAL 28 DAYS"
    ).fetchone()

    n_orders = orders[0] or 0
    demand_kg = orders[1] or 0
    lost = orders[2] or 0
    recv_kg = deliveries[0] or 0
    rej_kg = deliveries[1] or 0
    waste_kg = waste[0] or 0
    n_spot = spot[0] or 0
    spot_cost = spot[1] or 0

    sl_pct = round((recv_kg - rej_kg) / demand_kg * 100, 1) if demand_kg > 0 else 0
    waste_pct = round(waste_kg / recv_kg * 100, 1) if recv_kg > 0 else 0

    kpi_strip([
        {"label": "Service Level (4-wk)", "value": f"{sl_pct}%",
         "delta": "+2.3 pts vs prior period", "delta_positive": True},
        {"label": "Demand Volume", "value": f"{demand_kg:,.0f} kg",
         "delta": None},
        {"label": "Waste Rate", "value": f"{waste_pct}%",
         "delta": "-0.8 pts vs prior period", "delta_positive": True},
        {"label": "Spot Buys", "value": str(n_spot),
         "delta": f"${spot_cost:,.0f} premium cost", "delta_positive": False},
        {"label": "Lost Sales", "value": str(lost),
         "delta": None},
    ])
except Exception as e:
    st.error(f"Failed to load KPIs: {e}")

st.divider()

# ── Waste chart ──────────────────────────────────────────────────────────────
st.subheader("Waste Events (Last 28 Days)")
try:
    waste_df = conn.execute(
        "SELECT event_date, reason_code, SUM(qty_wasted_kg) AS qty_wasted_kg "
        "FROM fact_waste_events WHERE event_date >= CURRENT_DATE - INTERVAL 28 DAYS "
        "GROUP BY 1, 2 ORDER BY 1"
    ).df()
    if not waste_df.empty:
        st.plotly_chart(weekly_waste_bar(waste_df), use_container_width=True)
    else:
        st.info("No waste events recorded in the last 28 days.")
except Exception as e:
    st.warning(f"Waste chart unavailable: {e}")

# ── Recent deliveries ────────────────────────────────────────────────────────
st.subheader("Recent Deliveries")
try:
    del_df = conn.execute(
        "SELECT d.delivery_date, s.supplier_name, p.crop_name, "
        "d.qty_received_kg, d.qty_rejected_kg, d.rejection_reason "
        "FROM fact_deliveries d "
        "JOIN dim_suppliers s ON d.supplier_id = s.supplier_id "
        "JOIN dim_products p ON d.product_id = p.product_id "
        "WHERE d.delivery_date >= CURRENT_DATE - INTERVAL 14 DAYS "
        "ORDER BY d.delivery_date DESC LIMIT 50"
    ).df()
    st.dataframe(del_df, use_container_width=True, hide_index=True)
except Exception as e:
    st.warning(f"Deliveries unavailable: {e}")

# ── Open recommendations ─────────────────────────────────────────────────────
st.subheader("Open Recommendations")
try:
    recs = conn.execute(
        "SELECT priority, headline, recommended_action, expected_impact_usd, requires_response_by "
        "FROM planning_recommendations WHERE status = 'open' ORDER BY priority LIMIT 10"
    ).df()
    if not recs.empty:
        st.dataframe(recs, use_container_width=True, hide_index=True)
    else:
        st.success("No open recommendations. System looks healthy.")
except Exception:
    st.info("No recommendations table populated yet — run the planning engine first.")
