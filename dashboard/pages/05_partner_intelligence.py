"""Page 5 — Supplier & Buyer Intelligence.

Which partners are creating planning risk?"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from dashboard.components.cards import section
from dashboard.components.charts import concentration_donut, trend_lines
from dashboard.components.empty import db_unavailable, empty_state
from dashboard.lib import db, metrics, theme
from dashboard.lib.formatters import fmt_kg, fmt_percent

theme.apply(page_title="Partners")

if not db.is_available():
    db_unavailable()
    st.stop()

conn = db.get_conn()

theme.page_header(title="Partners")

tabs = st.tabs(["Suppliers", "Buyers"])

# ── Suppliers ─────────────────────────────────────────────────────────────
with tabs[0]:
    sup = metrics.supplier_reliability(conn)
    conc = metrics.supplier_concentration(conn)

    if sup.empty:
        empty_state("No supplier data", "Load delivery + PO history to populate this tab.")
    else:
        # Header KPIs
        n_critical = (sup["risk_tier"] == "Critical").sum()
        n_high = (sup["risk_tier"] == "High").sum()
        avg_fill = sup["fill_reliability"].mean()
        avg_rej = sup["rejection_rate"].mean()

        c1, c2, c3, c4 = st.columns(4, gap="medium")
        for col, (label, val) in zip(
            [c1, c2, c3, c4],
            [
                ("Critical tier", n_critical),
                ("High tier", n_high),
                ("Avg fill rel.", fmt_percent(avg_fill)),
                ("Avg rejection", fmt_percent(avg_rej)),
            ],
        ):
            with col:
                val_str = f"{val}" if isinstance(val, int) else val
                st.markdown(
                    f'<div class="hm-card"><div class="hm-label">{label}</div>'
                    f'<div class="hm-value">{val_str}</div></div>',
                    unsafe_allow_html=True,
                )
        st.write("")

        # Reliability table
        section("Reliability by supplier × product")
        disp = sup.copy()
        disp["committed_kg"] = disp["committed_kg"].apply(fmt_kg)
        disp["received_kg"] = disp["received_kg"].apply(fmt_kg)
        disp["rejected_kg"] = disp["rejected_kg"].apply(fmt_kg)
        disp["fill_reliability"] = disp["fill_reliability"].apply(fmt_percent)
        disp["rejection_rate"] = disp["rejection_rate"].apply(fmt_percent)
        disp["late_rate"] = disp["late_rate"].apply(fmt_percent)
        disp["spot_replacement_rate"] = disp["spot_replacement_rate"].apply(fmt_percent)
        disp = disp.rename(columns={
            "supplier": "Supplier",
            "product": "Product",
            "committed_kg": "Committed",
            "received_kg": "Received",
            "rejected_kg": "Rejected",
            "fill_reliability": "Fill rel.",
            "rejection_rate": "Rejection",
            "late_rate": "Late rate",
            "spot_replacement_rate": "Spot replace",
            "deliveries": "# del.",
            "risk_tier": "Risk",
        })
        cols = ["Supplier", "Product", "Committed", "Received", "Fill rel.",
                "Rejection", "Late rate", "Spot replace", "# del.", "Risk"]
        st.dataframe(disp[cols], use_container_width=True, hide_index=True)

        # Concentration donut
        col_a, col_b = st.columns([1, 1], gap="medium")
        with col_a:
            section("Concentration")
            if not conc.empty:
                st.plotly_chart(concentration_donut(conc), use_container_width=True)

        # Trend
        with col_b:
            section("Rejection rate trend")
            tr = metrics.supplier_trend(conn)
            if tr.empty:
                empty_state("Not enough monthly history", "")
            else:
                fig = trend_lines(
                    tr.assign(rejection_rate_pct=tr["rejection_rate"] * 100),
                    x="month", y="rejection_rate_pct", color="supplier",
                    title="Rejection rate (%) by month",
                    y_format=".1f",
                )
                st.plotly_chart(fig, use_container_width=True)

# ── Buyers ────────────────────────────────────────────────────────────────
with tabs[1]:
    buyers = metrics.buyer_demand_variability(conn)
    trend = metrics.buyer_demand_trend(conn)

    if buyers.empty:
        empty_state("No buyer data", "Load order history to populate this tab.")
    else:
        n_crit = (buyers["risk_tier"] == "Critical").sum()
        avg_cv = buyers["coef_of_variation"].mean()
        avg_lost = buyers["lost_sale_rate"].mean()
        avg_fill = buyers["fill_rate"].mean()

        c1, c2, c3, c4 = st.columns(4, gap="medium")
        for col, (label, val) in zip(
            [c1, c2, c3, c4],
            [
                ("Critical tier", n_crit),
                ("Avg demand CV", fmt_percent(avg_cv)),
                ("Lost-sale rate", fmt_percent(avg_lost)),
                ("Fill rate", fmt_percent(avg_fill)),
            ],
        ):
            with col:
                val_str = f"{val}" if isinstance(val, int) else val
                st.markdown(
                    f'<div class="hm-card"><div class="hm-label">{label}</div>'
                    f'<div class="hm-value">{val_str}</div></div>',
                    unsafe_allow_html=True,
                )
        st.write("")

        section("Demand variability by buyer × product")
        disp = buyers.copy()
        disp["avg_order_kg"] = disp["avg_order_kg"].apply(fmt_kg)
        disp["coef_of_variation"] = disp["coef_of_variation"].apply(fmt_percent)
        disp["lost_sale_rate"] = disp["lost_sale_rate"].apply(fmt_percent)
        disp["fill_rate"] = disp["fill_rate"].apply(fmt_percent)
        disp = disp.rename(columns={
            "buyer": "Buyer",
            "product": "Product",
            "lines": "# lines",
            "avg_order_kg": "Avg order",
            "coef_of_variation": "Demand CV",
            "lost_sale_rate": "Lost-sale rate",
            "fill_rate": "Fill rate",
            "risk_tier": "Risk",
        })
        cols = ["Buyer", "Product", "# lines", "Avg order", "Demand CV",
                "Lost-sale rate", "Fill rate", "Risk"]
        st.dataframe(disp[cols], use_container_width=True, hide_index=True)

        section("Weekly demand by buyer")
        trend_agg = trend.groupby(["week_start", "buyer"], as_index=False)["demand_kg"].sum()
        st.plotly_chart(
            trend_lines(trend_agg, x="week_start", y="demand_kg", color="buyer",
                        title="Weekly demand by buyer (kg)", y_format=",.0f"),
            use_container_width=True,
        )
