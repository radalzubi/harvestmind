"""Page 7 — Report Export / Partner Memo.

Generate the partner ROI HTML/PDF and preview the executive summary.
Buttons that aren't fully wired show a clear disabled state, never a fake
'success' confirmation.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from dashboard.components.cards import section
from dashboard.components.empty import db_unavailable
from dashboard.lib import db, metrics, theme
from dashboard.lib.formatters import fmt_currency, fmt_currency_range, fmt_date_range, fmt_percent

theme.apply(page_title="Report Export")

if not db.is_available():
    db_unavailable()
    st.stop()

conn = db.get_conn()

theme.page_header(title="Reports")

# ── Sidebar config ────────────────────────────────────────────────────────
with st.sidebar:
    partner_name = st.text_input("Partner name", value="")
    annual_gmv = st.number_input("Annual GMV ($)",
                                 min_value=500_000, max_value=50_000_000,
                                 value=3_000_000, step=100_000)
    today = dt.date.today().isoformat()
    filename_base = st.text_input(
        "Filename",
        value=f"roi_{(partner_name or 'partner').lower().replace(' ', '_')}_{today}",
    )

# ── Compute ROI for preview ──────────────────────────────────────────────
_display_partner = partner_name or "Partner"
ctx = metrics.header_context(conn, partner_name=_display_partner)
kpis = metrics.executive_kpis(conn, partner_gmv_usd=float(annual_gmv))

section("Memo preview")

_memo_html = (
    '<div class="hm-card" style="padding:24px 28px;">'
    '<div style="font-size:0.78rem;color:#475569;text-transform:uppercase;'
    'letter-spacing:0.06em;">Partner ROI Memo</div>'
    f'<h2 style="margin:0.5rem 0 0.4rem;">{_display_partner}</h2>'
    '<div style="color:#475569;font-size:0.85rem;margin-bottom:1.2rem;">'
    f'Planning period {fmt_date_range(ctx.period_start, ctx.period_end)}. '
    f'Generated {today}.'
    '</div>'
    '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;">'
    '<div>'
    '<div style="font-size:0.75rem;color:#475569;text-transform:uppercase;">Estimated annual benefit</div>'
    f'<div style="font-size:1.6rem;font-weight:700;color:#0F172A;">'
    f'{fmt_currency(kpis.estimated_annual_savings_usd, compact=True)}</div>'
    f'<div style="font-size:0.78rem;color:#475569;">'
    f'{fmt_currency_range(kpis.confidence_low_usd, kpis.confidence_high_usd)} confidence</div>'
    '</div>'
    '<div>'
    '<div style="font-size:0.75rem;color:#475569;text-transform:uppercase;">Spot premium savings</div>'
    f'<div style="font-size:1.6rem;font-weight:700;color:#0F172A;">'
    f'{fmt_currency(kpis.spot_premium_savings_usd, compact=True)}</div>'
    f'<div style="font-size:0.78rem;color:#475569;">'
    f'{fmt_percent(kpis.spot_pct_of_volume)} spot share today</div>'
    '</div>'
    '<div>'
    '<div style="font-size:0.75rem;color:#475569;text-transform:uppercase;">Waste reduction</div>'
    f'<div style="font-size:1.6rem;font-weight:700;color:#0F172A;">'
    f'{fmt_currency(kpis.waste_cost_reduction_usd, compact=True)}</div>'
    f'<div style="font-size:0.78rem;color:#475569;">'
    f'{fmt_percent(kpis.waste_pct_of_received)} waste rate today</div>'
    '</div>'
    '</div>'
    '</div>'
)
st.markdown(_memo_html, unsafe_allow_html=True)

st.write("")

# ── Export buttons ───────────────────────────────────────────────────────
section("Export")

c1, c2, c3 = st.columns(3, gap="medium")

# 1. Executive summary CSV
with c1:
    st.markdown('<div class="hm-card">'
                '<div class="hm-label">Summary CSV</div>'
                '<div class="hm-sub" style="margin-top:4px;margin-bottom:14px;">'
                'Headline KPIs and assumptions.</div>',
                unsafe_allow_html=True)
    summary_csv = pd.DataFrame([
        ["Partner", _display_partner],
        ["Planning period start", ctx.period_start],
        ["Planning period end", ctx.period_end],
        ["Annual savings (low)", kpis.confidence_low_usd],
        ["Annual savings (point)", kpis.estimated_annual_savings_usd],
        ["Annual savings (high)", kpis.confidence_high_usd],
        ["Spot premium savings", kpis.spot_premium_savings_usd],
        ["Waste reduction", kpis.waste_cost_reduction_usd],
        ["Fill rate", kpis.fill_rate_actual],
        ["Data quality score", kpis.data_quality_score],
        ["Subscription cost (annual)", kpis.annual_subscription_usd],
    ], columns=["Metric", "Value"]).to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV", data=summary_csv,
        file_name=f"{filename_base}_summary.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

# 2. Backtest report HTML — wired through reports/roi_report_generator
with c2:
    st.markdown('<div class="hm-card">'
                '<div class="hm-label">ROI memo (HTML)</div>'
                '<div class="hm-sub" style="margin-top:4px;margin-bottom:14px;">'
                'Branded one-pager, runs a fresh backtest.</div>',
                unsafe_allow_html=True)
    if st.button("Generate HTML", key="gen_html", use_container_width=True):
        with st.spinner("Running backtest + rendering..."):
            try:
                from backtesting.rolling_origin_engine import (
                    BacktestConfig, RollingOriginEngine,
                )
                from backtesting.roi_calculator import compute_roi
                from reports.roi_report_generator import (
                    ROIReportError, render_roi_report,
                )

                orders_df = conn.execute(
                    "SELECT ol.product_id, o.buyer_id, o.week_start, ol.qty_ordered_kg "
                    "FROM fact_order_lines ol JOIN fact_orders o ON ol.order_id = o.order_id"
                ).df()
                deliveries_df = conn.execute(
                    "SELECT supplier_id, product_id, delivery_date, qty_received_kg, qty_rejected_kg "
                    "FROM fact_deliveries"
                ).df()

                cfg = BacktestConfig(
                    n_train_weeks=26, horizon_weeks=4, step_weeks=4,
                    n_scenarios=20, run_stochastic=True,
                )
                results_df = RollingOriginEngine(cfg).run(orders_df, deliveries_df)

                if results_df.empty:
                    st.error("Backtest produced no results — cannot render report.")
                else:
                    roi = compute_roi(results_df, annual_gmv_usd=annual_gmv)
                    html = render_roi_report(roi, results_df, partner_name=_display_partner)
                    st.session_state["report_html"] = html
                    st.session_state["report_filename"] = f"{filename_base}_report.html"
                    st.success("Report generated.")
            except ROIReportError as e:
                st.error(f"Report not generated ({type(e).__name__}). See the server log.")
            except Exception as e:
                st.error(f"Failed ({type(e).__name__}). See the server log.")
    if "report_html" in st.session_state:
        st.download_button(
            "Download HTML",
            data=st.session_state["report_html"].encode("utf-8"),
            file_name=st.session_state["report_filename"],
            mime="text/html",
            use_container_width=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

# 3. KPI table CSV
with c3:
    st.markdown('<div class="hm-card">'
                '<div class="hm-label">Loss table (CSV)</div>'
                '<div class="hm-sub" style="margin-top:4px;margin-bottom:14px;">'
                'Per-product loss attribution.</div>',
                unsafe_allow_html=True)
    kpi_df = metrics.loss_attribution(conn).copy()
    csv = kpi_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV", data=csv,
        file_name=f"{filename_base}_kpi_table.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

