"""Landing page — quick-glance health summary."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import streamlit as st

from dashboard.components.cards import metric_card
from dashboard.components.empty import db_unavailable
from dashboard.lib import db, metrics, theme
from dashboard.lib.formatters import fmt_currency, fmt_date, fmt_percent

theme.apply(page_title="Overview", page_icon="🌾")

if not db.is_available():
    theme.page_header(title="Overview")
    db_unavailable()
    st.stop()

conn = db.get_conn()
ctx = metrics.header_context(conn)
kpis = metrics.executive_kpis(conn, partner_gmv_usd=3_000_000)
score = metrics.data_quality_score(conn)

theme.page_header(
    title="Overview",
    subtitle=f"Last refreshed {fmt_date(ctx.last_data_date)}",
)

c1, c2, c3, c4 = st.columns(4, gap="medium")
with c1:
    metric_card(
        label="Annual savings",
        value=fmt_currency(kpis.estimated_annual_savings_usd, compact=True),
        delta=f"±{fmt_currency((kpis.confidence_high_usd - kpis.confidence_low_usd) / 2, compact=True)}",
        delta_direction="flat",
    )
with c2:
    metric_card(
        label="Fill rate",
        value=fmt_percent(kpis.fill_rate_actual),
        delta=f"target {fmt_percent(kpis.fill_rate_target)}",
        delta_direction="up" if (kpis.fill_rate_actual or 0) >= kpis.fill_rate_target else "down",
    )
with c3:
    metric_card(
        label="Spot exposure",
        value=fmt_percent(kpis.spot_pct_of_volume),
        delta=fmt_currency(kpis.spot_premium_savings_usd, compact=True) + " recoverable",
        delta_direction="flat",
    )
with c4:
    metric_card(
        label="Data quality",
        value=fmt_percent(score),
        status=("Strong" if score >= 0.9 else "Usable with caveats" if score >= 0.6 else "Weak"),
    )
