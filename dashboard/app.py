"""HarvestMind dashboard — entry page.

Streamlit auto-discovers everything under ``dashboard/pages/`` and lists
the pages in the sidebar in lexical order. This file is just the landing
page that runs when a user opens the app at the root URL.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import streamlit as st

from dashboard.components.cards import insight, metric_card
from dashboard.components.empty import db_unavailable
from dashboard.lib import db, metrics, theme
from dashboard.lib.formatters import fmt_count, fmt_date, fmt_percent

theme.apply(page_title="Overview", page_icon="🌾")

# ── sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div style="padding:14px 6px 18px;">'
        '<div style="font-size:1rem;font-weight:700;color:#0F172A;">HarvestMind</div>'
        '<div style="font-size:0.78rem;color:#475569;margin-top:4px;">'
        'Stochastic supply planning</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.divider()
    st.caption("Indiana pilot · v0.1.0")

# ── header ─────────────────────────────────────────────────────────────────
theme.page_header(
    eyebrow="HarvestMind",
    title="Pre-production planning & allocation",
    subtitle=(
        "Reduce waste, cut emergency spot purchases, and lift fill-rate for fresh "
        "produce hubs and regional distributors. Use the sidebar to navigate the "
        "executive overview, planning recommendations, backtest evidence, exposure "
        "analysis, supplier/buyer intelligence, and data quality."
    ),
)

if not db.is_available():
    db_unavailable()
    st.stop()

conn = db.get_conn()
ctx = metrics.header_context(conn)

# ── three quick stats ──────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3, gap="medium")
with c1:
    metric_card(
        label="Partner",
        value=ctx.partner_name,
        subtitle=f"Last data refreshed {fmt_date(ctx.last_data_date)}",
    )
with c2:
    metric_card(
        label="Records loaded",
        value=fmt_count(ctx.rows_used),
        subtitle="Rows of order history powering KPIs across the dashboard.",
    )
with c3:
    score = metrics.data_quality_score(conn)
    metric_card(
        label="Data quality",
        value=fmt_percent(score),
        subtitle="See Data Quality page for per-dataset breakdown.",
        status=("Strong" if score >= 0.9 else "Usable with caveats" if score >= 0.6 else "Weak"),
    )

st.write("")

# ── executive insight ─────────────────────────────────────────────────────
insight(
    "<b>How to use this dashboard:</b> start with the Executive Overview to see "
    "the top-line opportunity, then use Planning Recommendations for the next "
    "operational decision. Backtest Results explains how the savings are derived; "
    "Waste &amp; Spot Exposure shows where losses are concentrated. The Supplier "
    "and Buyer Intelligence page surfaces the partners driving planning risk. "
    "Data Quality &amp; Assumptions is required reading before sharing any output "
    "externally."
)
