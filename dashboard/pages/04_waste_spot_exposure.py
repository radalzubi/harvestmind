"""Page 4 — Waste & Spot Exposure.

Where the losses are coming from."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from dashboard.components.cards import section
from dashboard.components.charts import (
    horizontal_value_bar, risk_heatmap, stacked_bar, waste_vs_shortage_scatter,
)
from dashboard.components.empty import db_unavailable, empty_state
from dashboard.lib import db, metrics, theme
from dashboard.lib.formatters import fmt_currency

theme.apply(page_title="Loss exposure")

if not db.is_available():
    db_unavailable()
    st.stop()

conn = db.get_conn()

with st.sidebar:
    weeks = st.slider("Trailing window (weeks)", 4, 52, 12)

theme.page_header(title="Loss exposure")

# ── Pull data ─────────────────────────────────────────────────────────────
waste_p = metrics.waste_by_product(conn)
waste_r = metrics.waste_by_reason(conn)
spot_p = metrics.spot_by_product(conn)
spot_t = metrics.spot_premium_trend(conn)
heat = metrics.product_risk_heatmap(conn, weeks=weeks)
attrib = metrics.loss_attribution(conn)

# ── Top KPIs ──────────────────────────────────────────────────────────────
total_waste = float(waste_p["waste_usd"].sum())
total_spot = float(spot_p["spot_cost_usd"].sum())

c1, c2, c3 = st.columns(3, gap="medium")
with c1:
    st.markdown(
        f'<div class="hm-card"><div class="hm-label">Waste cost</div>'
        f'<div class="hm-value">{fmt_currency(total_waste, compact=True)}</div>'
        f'<div class="hm-sub">{int(waste_p["events"].sum())} events</div></div>',
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f'<div class="hm-card"><div class="hm-label">Spot premium</div>'
        f'<div class="hm-value">{fmt_currency(total_spot, compact=True)}</div>'
        f'<div class="hm-sub">Above-contract emergency spend</div></div>',
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        f'<div class="hm-card"><div class="hm-label">Combined loss</div>'
        f'<div class="hm-value">{fmt_currency(total_waste + total_spot, compact=True)}</div>'
        f'<div class="hm-sub">Across loaded period</div></div>',
        unsafe_allow_html=True,
    )

st.write("")

# ── Waste by product / reason ─────────────────────────────────────────────
section("Waste")
col1, col2 = st.columns(2, gap="medium")

with col1:
    if waste_p.empty or waste_p["waste_usd"].sum() == 0:
        empty_state("No waste events", "Once waste events are logged they will appear here.")
    else:
        st.plotly_chart(
            horizontal_value_bar(
                waste_p[waste_p["waste_usd"] > 0],
                x="waste_usd", y="product",
                title="Waste cost by product",
                color="#B45309",
            ),
            use_container_width=True,
        )

with col2:
    if waste_r.empty:
        empty_state("No waste reasons", "Reason codes will populate here once waste events exist.")
    else:
        # Aggregate to top reasons, mapping snake_case codes to readable labels
        _reason_labels = {
            "quality_rejection":  "Quality rejection",
            "quality_reject":     "Quality rejection",
            "shelf_life":         "Shelf life",
            "cold_chain_failure": "Cold chain failure",
            "cold_chain":         "Cold chain failure",
            "demand_miss":        "Demand miss",
            "over_commitment":    "Over-commitment",
            "over_commit":        "Over-commitment",
            "transit_damage":     "Transit damage",
            "packaging":          "Packaging",
            "other":              "Other",
        }
        agg = waste_r.groupby("reason_code", as_index=False)["waste_usd"].sum()
        agg["reason_code"] = agg["reason_code"].map(_reason_labels).fillna(
            agg["reason_code"].str.replace("_", " ").str.capitalize()
        )
        agg = agg.sort_values("waste_usd", ascending=False)
        st.plotly_chart(
            horizontal_value_bar(
                agg, x="waste_usd", y="reason_code",
                title="Waste cost by reason",
                color="#B91C1C",
            ),
            use_container_width=True,
        )

# ── Spot premium ──────────────────────────────────────────────────────────
section("Spot premium")
col3, col4 = st.columns(2, gap="medium")

with col3:
    if spot_p.empty or spot_p["spot_cost_usd"].sum() == 0:
        empty_state("No spot purchases yet", "Will populate as emergency POs are recorded.")
    else:
        st.plotly_chart(
            horizontal_value_bar(
                spot_p[spot_p["spot_cost_usd"] > 0],
                x="spot_cost_usd", y="product",
                title="Spot premium cost by product",
                color="#0F766E",
            ),
            use_container_width=True,
        )

with col4:
    if spot_t.empty:
        empty_state("No spot trend data", "")
    else:
        spot_t_df = spot_t.copy()
        spot_t_df["spot_share"] = spot_t_df["spot_kg"] / spot_t_df["total_kg"].replace(0, pd.NA)
        st.plotly_chart(
            stacked_bar(
                spot_t_df.assign(category="Spot premium ($)"),
                x="week_start", y="spot_cost_usd", color="category",
                title="Spot premium $ over time",
            ),
            use_container_width=True,
        )

# ── Tradeoff scatter ──────────────────────────────────────────────────────
section("Waste vs spot tradeoff")
trade = spot_p.merge(
    waste_p[["product_id", "waste_usd", "waste_kg"]], on="product_id", how="outer",
).fillna(0)
trade["product"] = trade["product_x"].fillna(trade.get("product_y", ""))
if trade["spot_cost_usd"].sum() == 0 and trade["waste_usd"].sum() == 0:
    empty_state("No loss data", "Load order/PO/waste history to populate.")
else:
    st.plotly_chart(waste_vs_shortage_scatter(trade), use_container_width=True)

# ── Heatmap ───────────────────────────────────────────────────────────────
section("Risk heatmap by week")
if heat.empty:
    empty_state("Not enough weekly data", "Need at least a few weeks of POs and waste events.")
else:
    st.plotly_chart(risk_heatmap(heat), use_container_width=True)

# ── Loss attribution table ────────────────────────────────────────────────
section("Loss attribution")

if attrib.empty:
    empty_state("No products with loss data", "")
else:
    tbl = attrib.copy()
    tbl["spot_cost_usd"] = tbl["spot_cost_usd"].apply(fmt_currency)
    tbl["waste_usd"] = tbl["waste_usd"].apply(fmt_currency)
    tbl["top_waste_reason"] = tbl["top_waste_reason"].fillna("—")
    tbl = tbl.rename(columns={
        "product": "Product",
        "product_id": "SKU",
        "spot_cost_usd": "Spot premium",
        "waste_usd": "Waste cost",
        "top_waste_reason": "Top waste reason",
        "recommended_action": "Recommended action",
    })
    st.dataframe(
        tbl[["Product", "SKU", "Spot premium", "Waste cost",
             "Top waste reason", "Recommended action"]],
        use_container_width=True, hide_index=True,
    )

