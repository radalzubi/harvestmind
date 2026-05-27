"""Page 2 — Planning Recommendations.

Operational view for the planner: what to commit this week, why, and which
items are flagged. Recommendations are written in operational language."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from dashboard.components.badges import risk_badge, info_badge
from dashboard.components.cards import section
from dashboard.components.empty import db_unavailable, empty_state
from dashboard.lib import db, metrics, theme
from dashboard.lib.formatters import fmt_kg, fmt_percent

theme.apply(page_title="Recommendations")

if not db.is_available():
    db_unavailable()
    st.stop()

conn = db.get_conn()

# ── Sidebar filters ───────────────────────────────────────────────────────
recs = metrics.recommendation_table(conn)

with st.sidebar:
    if recs.empty:
        product_filter = None
        risk_filter = None
        text_filter = ""
    else:
        product_choices = ["All products"] + recs["product"].dropna().tolist()
        product_filter = st.selectbox("Product", product_choices)
        risk_filter = st.selectbox(
            "Shortage risk",
            ["All risk levels", "Low", "Medium", "High", "Critical"],
        )
        text_filter = st.text_input("Search", "")

# ── Header ────────────────────────────────────────────────────────────────
theme.page_header(title="Recommendations")

if recs.empty:
    empty_state(
        "No recommendations available",
        "Recommendations appear once at least 8 weeks of order history are loaded.",
    )
    st.stop()

# Apply filters
filtered = recs.copy()
if product_filter and product_filter != "All products":
    filtered = filtered[filtered["product"] == product_filter]
if risk_filter and risk_filter != "All risk levels":
    filtered = filtered[filtered["shortage_risk"] == risk_filter]
if text_filter:
    filtered = filtered[filtered["explanation"].str.contains(text_filter, case=False, na=False)]

# ── Summary tiles ─────────────────────────────────────────────────────────
n_rows = len(filtered)
high_short = (filtered["shortage_risk"].isin(["High", "Critical"])).sum()
high_waste = (filtered["waste_risk"].isin(["High", "Critical"])).sum()
spot_exposed = (filtered["spot_exposure"] > 0.15).sum()

c1, c2, c3, c4 = st.columns(4, gap="medium")
for col, (label, val) in zip(
    [c1, c2, c3, c4],
    [
        ("SKUs in plan", n_rows),
        ("Shortage risk", high_short),
        ("Waste risk", high_waste),
        ("Spot exposed", spot_exposed),
    ],
):
    with col:
        st.markdown(
            f'<div class="hm-card"><div class="hm-label">{label}</div>'
            f'<div class="hm-value">{val}</div></div>',
            unsafe_allow_html=True,
        )

st.write("")

# ── Recommendation table ──────────────────────────────────────────────────
section("Recommended commitments")

if filtered.empty:
    empty_state("No rows match filters", "Adjust filters in the sidebar.")
else:
    # Build display copy with formatting + badges
    disp = filtered.copy()
    disp["Recommended commit"] = disp["recommended_commit_kg"].apply(
        lambda v: fmt_kg(v))
    disp["Historical avg"] = disp["historical_avg_kg"].apply(fmt_kg)
    disp["Forecast"] = disp["demand_forecast_kg"].apply(fmt_kg)
    disp["Spot exposure"] = disp["spot_exposure"].apply(fmt_percent)
    disp["Shortage risk"] = disp["shortage_risk"]
    disp["Waste risk"] = disp["waste_risk"]
    disp["Status"] = disp["status"]
    disp["Product"] = disp["product"]

    cols = ["Product", "Recommended commit", "Historical avg", "Forecast",
            "Spot exposure", "Shortage risk", "Waste risk", "Status"]

    st.dataframe(
        disp[cols],
        use_container_width=True, hide_index=True,
        column_config={
            "Recommended commit": st.column_config.TextColumn(width="medium"),
            "Shortage risk": st.column_config.TextColumn(width="small"),
            "Waste risk": st.column_config.TextColumn(width="small"),
        },
    )

    section("Reasoning")
    for _, row in filtered.iterrows():
        with st.expander(
            f"{row['product']} · {fmt_kg(row['recommended_commit_kg'])}",
            expanded=False,
        ):
            badges_html = "".join([
                risk_badge(row['shortage_risk']),
                "&nbsp;",
                risk_badge(row['waste_risk']),
                "&nbsp;",
                (info_badge("Spot exposed") if row['spot_exposure'] > 0.15 else ""),
            ])
            st.markdown(
                f"<div style='margin-bottom:0.6rem;'>{badges_html}</div>"
                f"<div style='color:#0F172A;font-size:0.92rem;line-height:1.55;'>{row['explanation']}</div>"
                f"<div style='color:#475569;font-size:0.8rem;margin-top:0.6rem;'>"
                f"Forecast {fmt_kg(row['demand_forecast_kg'])} "
                f"· stdev {fmt_kg(row.get('demand_std_kg'))}"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.text_input(
                "Override (kg)",
                value="",
                key=f"override_{row['product_id']}",
                placeholder="Accept recommended quantity by leaving blank",
            )
