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

from dashboard.components.badges import risk_badge, neutral_badge, info_badge
from dashboard.components.cards import caveat, section
from dashboard.components.empty import db_unavailable, empty_state
from dashboard.lib import db, metrics, theme
from dashboard.lib.formatters import fmt_kg, fmt_percent

theme.apply(page_title="Planning Recommendations")

if not db.is_available():
    db_unavailable()
    st.stop()

conn = db.get_conn()

# ── Sidebar filters ───────────────────────────────────────────────────────
recs = metrics.recommendation_table(conn)

with st.sidebar:
    st.markdown("### Filters")
    if recs.empty:
        st.caption("No data — filters disabled.")
        product_filter = None
        risk_filter = None
        text_filter = ""
    else:
        product_choices = ["All products"] + recs["product"].dropna().tolist()
        product_filter = st.selectbox("Product / SKU", product_choices)
        risk_choices = ["All risk levels", "Low", "Medium", "High", "Critical"]
        risk_filter = st.selectbox(
            "Shortage risk",
            risk_choices,
            help="Filter by recommended shortage-risk classification.",
        )
        text_filter = st.text_input("Search explanations", "")
    st.divider()
    st.caption("Buyer / supplier filters become active when the optimiser writes "
               "scenario-level recommendations to `planning_recommendations`.")

# ── Header ────────────────────────────────────────────────────────────────
theme.page_header(
    eyebrow="Page 2 of 7",
    title="Planning Recommendations",
    subtitle=(
        "Per-SKU commitment guidance for the upcoming planning week. "
        "Recommendations are written in operational language; click any row to "
        "see the underlying reasoning."
    ),
)

if recs.empty:
    empty_state(
        "No recommendations yet",
        "Run the optimiser (`make backtest` or POST /planning/run) or load order "
        "history covering at least 8 weeks. Recommendations will appear here once "
        "the model has enough signal.",
    )
    st.stop()

# Source banner: currently always actuals-derived heuristic
if "source" in recs.columns and recs["source"].iloc[0] == "actuals-derived heuristic":
    st.markdown(
        '<div class="hm-caveat" style="margin-bottom:18px;">'
        "<b>Source:</b> these recommendations are an actuals-derived heuristic "
        "(8-week mean ± standard deviation) computed at page load. They are NOT "
        "the output of the stochastic optimiser. Run a backtest or planning job "
        "to populate <code>planning_recommendations</code> with the optimised plan."
        '</div>',
        unsafe_allow_html=True,
    )

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
for col, (label, val, sub) in zip(
    [c1, c2, c3, c4],
    [
        ("SKUs in plan", n_rows, "Rows after filters"),
        ("High shortage risk", high_short, "Recommend extra reserve"),
        ("High waste risk", high_waste, "Tighten commit; check shelf life"),
        ("Spot-exposed", spot_exposed, "Spot share above 15%"),
    ],
):
    with col:
        st.markdown(
            f'<div class="hm-card"><div class="hm-label">{label}</div>'
            f'<div class="hm-value">{val}</div>'
            f'<div class="hm-sub">{sub}</div></div>',
            unsafe_allow_html=True,
        )

st.write("")

# ── Recommendation table ──────────────────────────────────────────────────
section(
    "Recommended commitments",
    "Sorted by demand. Click a row to see the reasoning.",
)

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

    section(
        "Why these recommendations?",
        "Per-SKU explanation — expand a row for the operational rationale.",
    )
    for _, row in filtered.iterrows():
        with st.expander(
            f"{row['product']} · commit {fmt_kg(row['recommended_commit_kg'])}",
            expanded=False,
        ):
            badges_html = "".join([
                risk_badge(row['shortage_risk']),
                "&nbsp;",
                risk_badge(row['waste_risk']),
                "&nbsp;",
                (info_badge("Spot exposed") if row['spot_exposure'] > 0.15 else ""),
                "&nbsp;",
                (neutral_badge("Heuristic source")
                 if row.get('source') == "actuals-derived heuristic" else ""),
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
            override = st.text_input(
                "Planner override (kg, optional)",
                value="",
                key=f"override_{row['product_id']}",
                placeholder="Leave blank to accept the recommended quantity.",
            )
            if override:
                st.info(
                    f"Override captured: {override} kg. "
                    "(Override persistence requires a wired-up planning store; "
                    "see TODO in `dashboard/pages/02_planning_recommendations.py`.)"
                )

# ── Caveat ────────────────────────────────────────────────────────────────
with st.expander("How shortage / waste risk are scored", expanded=False):
    caveat(
        "<b>Risk classification</b> (heuristic source). "
        "<b>Shortage risk</b>: <i>High</i> if historical spot-exposure on this "
        "SKU exceeds 20% of volume; <i>Medium</i> at 10–20%; <i>Low</i> below 10%. "
        "<b>Waste risk</b>: <i>High</i> if recent waste exceeds 200 kg, "
        "<i>Medium</i> at 50–200 kg, <i>Low</i> below 50 kg. "
        "These thresholds are tunable via the <code>ASSUMPTIONS</code> dict in "
        "<code>dashboard/lib/metrics.py</code> and will be replaced by the "
        "optimiser's per-scenario probability outputs when a planning run is "
        "stored in <code>planning_recommendations</code>."
    )
