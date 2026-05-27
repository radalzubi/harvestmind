"""Page 6 — Data Quality & Assumptions.

Build trust by being transparent about completeness and assumptions."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from dashboard.components.cards import section
from dashboard.components.empty import db_unavailable
from dashboard.lib import db, metrics, theme
from dashboard.lib.formatters import fmt_count, fmt_currency, fmt_percent

theme.apply(page_title="Data quality")

if not db.is_available():
    db_unavailable()
    st.stop()

conn = db.get_conn()

theme.page_header(title="Data quality")

# ── Score + summary ──────────────────────────────────────────────────────
score = metrics.data_quality_score(conn)
breakdown = metrics.data_quality_breakdown(conn)
n_strong = sum(1 for r in breakdown if r.status == "Strong")
n_total = len(breakdown)
weak = [r.dataset for r in breakdown if r.status in ("Weak", "Not enough data")]

c1, c2, c3 = st.columns(3, gap="medium")
with c1:
    status = ("Strong" if score >= 0.9 else
              "Usable with caveats" if score >= 0.6 else
              "Weak" if score > 0 else "Not enough data")
    st.markdown(
        f'<div class="hm-card"><div class="hm-label">Quality score</div>'
        f'<div class="hm-value">{fmt_percent(score)}</div>'
        f'<span class="hm-status" style="background:'
        f'{"#DCFCE7" if status=="Strong" else "#FEF3C7" if status=="Usable with caveats" else "#FFEDD5"};'
        f'color:'
        f'{"#15803D" if status=="Strong" else "#B45309" if status=="Usable with caveats" else "#EA580C"};">'
        f'{status}</span></div>',
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f'<div class="hm-card"><div class="hm-label">Datasets ready</div>'
        f'<div class="hm-value">{n_strong} / {n_total}</div></div>',
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        f'<div class="hm-card"><div class="hm-label">Need attention</div>'
        f'<div class="hm-value">{len(weak)}</div></div>',
        unsafe_allow_html=True,
    )

st.write("")

# ── Breakdown table ──────────────────────────────────────────────────────
_TABLE_LABELS = {
    "dim_products":        "Products",
    "dim_suppliers":       "Suppliers",
    "dim_buyers":          "Buyers",
    "dim_locations":       "Locations",
    "fact_orders":         "Orders",
    "fact_order_lines":    "Order Lines",
    "fact_purchase_orders":"Purchase Orders",
    "fact_deliveries":     "Deliveries",
    "fact_waste_events":   "Waste Events",
    "fact_spot_purchases": "Spot Purchases",
    "planning_recommendations": "Planning Recommendations",
    "backtest_results":    "Backtest Results",
}

section("Dataset completeness")
df = pd.DataFrame([
    {
        "Dataset": _TABLE_LABELS.get(r.dataset, r.dataset.replace("_", " ").title()),
        "Rows": fmt_count(r.rows),
        "Completeness": fmt_percent(r.completeness),
        "Status": r.status,
        "Notes": r.note,
    }
    for r in breakdown
])
st.dataframe(df, use_container_width=True, hide_index=True)

# Warning banner for any weak data
if weak:
    st.markdown(
        f'<div class="hm-caveat" style="margin-top:14px;">'
        f"<b>{len(weak)} dataset{'s' if len(weak) > 1 else ''} below threshold:</b> "
        f"{', '.join(_TABLE_LABELS.get(d, d) for d in weak)}. "
        f"Treat dependent estimates as directional.</div>",
        unsafe_allow_html=True,
    )

# ── Assumptions ──────────────────────────────────────────────────────────
section("Modelling assumptions")
asm = metrics.ASSUMPTIONS
asm_table = pd.DataFrame([
    {
        "Assumption": "Spot premium multiplier",
        "Value": f"{asm['spot_premium_multiplier']:.2f}×",
        "Used in": "Spot premium savings calculation",
        "Rationale": "Historical USDA AMS data shows emergency purchases pay ≈30% above contract.",
    },
    {
        "Assumption": "Recoverable spot share",
        "Value": "90%",
        "Used in": "Annual spot premium savings",
        "Rationale": "Backtest pattern: ~10% of spot exposure remains even with optimal planning (true demand surprises).",
    },
    {
        "Assumption": "Avoidable waste share",
        "Value": "40%",
        "Used in": "Waste cost reduction",
        "Rationale": "USDA studies place 30–50% of fresh-produce waste as avoidable through demand planning.",
    },
    {
        "Assumption": "Waste $ / kg fallback",
        "Value": fmt_currency(asm['waste_value_per_kg_usd']),
        "Used in": "Loss attribution when value field is null",
        "Rationale": "Average farm-gate price across the modelled SKU mix.",
    },
    {
        "Assumption": "Service-level target",
        "Value": fmt_percent(asm['service_level_target']),
        "Used in": "Fill-rate KPI",
        "Rationale": "Standard food-hub commitment threshold.",
    },
    {
        "Assumption": "Confidence range",
        "Value": "± 25%",
        "Used in": "Annual savings band",
        "Rationale": "Reflects rolling-origin backtest variance on similar synthetic datasets.",
    },
    {
        "Assumption": "Subscription cost (Tier A)",
        "Value": fmt_currency(asm['subscription_tier_a_monthly_usd']) + " / month",
        "Used in": "ROI multiple, payback period",
        "Rationale": "Initial Tier-A pricing for sub-$10M GMV food hubs.",
    },
])
st.dataframe(asm_table, use_container_width=True, hide_index=True)

# ── Export ────────────────────────────────────────────────────────────────
csv_data = df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download CSV",
    data=csv_data,
    file_name="data_quality.csv",
    mime="text/csv",
)
