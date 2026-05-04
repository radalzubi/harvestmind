"""Page 3 — Backtest Results.

Evidence the model could have improved historical decisions.
Critical: perfect hindsight is labeled as theoretical upper bound."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from dashboard.components.cards import caveat, insight, section
from dashboard.components.charts import (
    cost_lines_over_time, policy_comparison_bar,
)
from dashboard.components.empty import db_unavailable, empty_state
from dashboard.lib import db, theme
from dashboard.lib.formatters import fmt_currency, fmt_percent

theme.apply(page_title="Backtest Results")

if not db.is_available():
    db_unavailable()
    st.stop()

conn = db.get_conn()

# ── sidebar filters ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Backtest configuration")
    train_weeks = st.slider("Training window (weeks)", 26, 78, 52, 4)
    horizon = st.selectbox("Planning horizon (weeks)", [1, 2, 4, 8], index=2)
    n_scen = st.slider("SAA scenarios", 10, 100, 30, 10)
    annual_gmv = st.number_input("Partner annual GMV ($)", 500_000, 50_000_000,
                                 3_000_000, 100_000)
    st.divider()
    run_btn = st.button("Run backtest", type="primary")

# ── Header ────────────────────────────────────────────────────────────────
theme.page_header(
    eyebrow="Page 3 of 7",
    title="Backtest Results",
    subtitle=(
        "Rolling-origin evidence that the model could have outperformed the "
        "historical baseline. Each origin is a planning week we 'replay' on "
        "training data only — strict information cutoff at the origin date."
    ),
)

# ── Methodology panel (always visible at top) ─────────────────────────────
section(
    "Methodology",
    "Three policies evaluated on the same rolling-origin splits.",
)
m1, m2, m3, m4 = st.columns(4, gap="medium")
with m1:
    st.markdown(
        '<div class="hm-card">'
        '<div class="hm-label">Actual baseline</div>'
        '<div class="hm-value" style="font-size:1.0rem;line-height:1.3;">Historical decisions</div>'
        '<div class="hm-sub">What the partner actually did each week. '
        'Includes the realised spot premium and waste cost.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
with m2:
    st.markdown(
        '<div class="hm-card">'
        '<div class="hm-label">Heuristic baseline</div>'
        '<div class="hm-value" style="font-size:1.0rem;line-height:1.3;">Deterministic LP</div>'
        '<div class="hm-sub">Last-week mean demand, no uncertainty. '
        'Comparable to spreadsheet planning.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
with m3:
    st.markdown(
        '<div class="hm-card">'
        '<div class="hm-label">Optimised policy</div>'
        '<div class="hm-value" style="font-size:1.0rem;line-height:1.3;">Two-stage stochastic + Γ-robust</div>'
        '<div class="hm-sub">SAA over 30 demand scenarios; commits absorb '
        'demand-band uncertainty.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
with m4:
    st.markdown(
        '<div class="hm-card" style="border-color:#FED7AA;">'
        '<div class="hm-label">Theoretical upper bound</div>'
        '<div class="hm-value" style="font-size:1.0rem;line-height:1.3;">Perfect hindsight</div>'
        '<div class="hm-sub" style="color:#B45309;"><b>Not achievable.</b> '
        'Solved with realised demand revealed; quoted only as a ceiling on '
        'recoverable savings.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

st.write("")

# ── Run on click ──────────────────────────────────────────────────────────
results_df: pd.DataFrame | None = st.session_state.get("backtest_results")
roi_dict = st.session_state.get("backtest_roi")

if run_btn:
    with st.spinner("Running rolling-origin backtest — this can take 1–3 minutes…"):
        try:
            orders_df = conn.execute(
                "SELECT ol.product_id, o.buyer_id, o.week_start, ol.qty_ordered_kg "
                "FROM fact_order_lines ol JOIN fact_orders o ON ol.order_id = o.order_id"
            ).df()
            deliveries_df = conn.execute(
                "SELECT supplier_id, product_id, delivery_date, qty_received_kg, qty_rejected_kg "
                "FROM fact_deliveries"
            ).df()

            from backtesting.rolling_origin_engine import (
                BacktestConfig, RollingOriginEngine,
            )
            from backtesting.roi_calculator import compute_roi

            cfg = BacktestConfig(
                n_train_weeks=train_weeks, horizon_weeks=horizon,
                step_weeks=horizon, n_scenarios=n_scen,
                run_stochastic=True,
            )
            results_df = RollingOriginEngine(cfg).run(orders_df, deliveries_df)

            if not results_df.empty:
                roi_dict = compute_roi(results_df, annual_gmv_usd=annual_gmv)
                st.session_state["backtest_results"] = results_df
                st.session_state["backtest_roi"] = roi_dict
                st.success(
                    f"Backtest complete: {results_df['origin_week'].nunique()} origins evaluated."
                )
            else:
                st.error("Backtest produced no rows. Check that enough order history is loaded.")
        except Exception as e:
            st.error(f"Backtest failed: {type(e).__name__}: {e}")

# ── Display ───────────────────────────────────────────────────────────────
if results_df is None or results_df.empty:
    empty_state(
        "No backtest results yet",
        "Configure parameters in the sidebar and click 'Run backtest' to evaluate.",
        action="A run takes 1–3 minutes on the included synthetic dataset.",
    )
    st.stop()

# Summary KPIs from ROI
section(
    "Headline results",
    f"Aggregated across {results_df['origin_week'].nunique()} rolling origins.",
)

if roi_dict and "error" not in roi_dict:
    kpis = [
        ("Annual benefit",  fmt_currency(roi_dict.get("total_annual_benefit_usd"), compact=True),
         f"vs ${roi_dict['annual_subscription_usd']:,.0f} subscription"),
        ("ROI multiple",    f"{roi_dict.get('roi_multiple', 0):.1f}×",
         f"Payback: {roi_dict.get('payback_months', 0):.1f} mo"),
        ("Service-level lift", f"+{roi_dict.get('service_level_improvement_pts', 0):.1f} pts",
         f"{roi_dict.get('baseline_service_level_pct', 0):.1f}% → "
         f"{roi_dict.get('target_service_level_pct', 0):.1f}%"),
        ("Spot reduction",  f"{roi_dict.get('spot_savings_pct', 0):.1f}%",
         f"Spot kg: -{roi_dict.get('annual_spot_savings_usd', 0):,.0f}/yr"),
    ]
    cols = st.columns(4, gap="medium")
    for col, (label, val, sub) in zip(cols, kpis):
        with col:
            st.markdown(
                f'<div class="hm-card"><div class="hm-label">{label}</div>'
                f'<div class="hm-value">{val}</div>'
                f'<div class="hm-sub">{sub}</div></div>',
                unsafe_allow_html=True,
            )

# Policy comparison bar
section("Cost by policy", "Lower is better.")
from backtesting.procurement_metrics import cost_per_kg_by_model
summary = cost_per_kg_by_model(results_df)
st.plotly_chart(policy_comparison_bar(summary), use_container_width=True)

# Origin-by-origin table
section("Per-origin detail", "Each row is one rolling planning week.")
detail = results_df.copy()
detail["spot_cost_usd"] = detail["spot_cost_usd"].fillna(0)
detail["total_cost_usd"] = detail["total_cost_usd"].fillna(0)
detail["service_level_pct"] = detail["service_level_pct"].fillna(0)

# Pivot: one row per origin, one column per policy
pivot = detail.pivot_table(
    index="origin_week",
    columns="model",
    values=["total_cost_usd", "spot_kg", "service_level_pct"],
    aggfunc="mean",
).round(2).sort_index()
pivot.columns = [f"{a} ({b})" for a, b in pivot.columns]
st.dataframe(pivot, use_container_width=True)

# Cost lines over time
if not detail.empty:
    section("Cost over time, by policy", "Track how each policy's cost evolves across origins.")
    line_df = detail.pivot_table(
        index="origin_week", columns="model", values="total_cost_usd", aggfunc="mean"
    ).reset_index()
    fig = cost_lines_over_time(
        line_df, x="origin_week",
        lines={c: c.replace("_", " ").title()
               for c in line_df.columns if c != "origin_week"},
    )
    st.plotly_chart(fig, use_container_width=True)

# Insight
if roi_dict and "error" not in roi_dict:
    insight(
        f"<b>Backtest verdict.</b> Across "
        f"{results_df['origin_week'].nunique()} rolling origins, the optimised "
        f"policy reduced average per-origin cost by "
        f"<b>{(1 - summary.iloc[0]['avg_total_cost'] / summary.iloc[-1]['avg_total_cost'])*100:.1f}%</b> "
        f"versus the deterministic heuristic baseline. The full annual benefit "
        f"estimate of <b>{fmt_currency(roi_dict['total_annual_benefit_usd'], compact=True)}</b> "
        f"is the per-origin saving scaled to a 52-week year, with the assumptions "
        f"listed below."
    )

# Methodology + caveats
with st.expander("Backtest assumptions and limitations", expanded=False):
    caveat(
        "<b>Strict no-lookahead rule.</b> All training data is sliced at the "
        "origin date by <code>backtesting.leakage_guard.LeakageGuard</code>. The "
        "two-stage SP base is the historical-mean per-product demand — not "
        "realised demand. <br><br>"
        "<b>Limitations.</b> The synthetic dataset's per-week supply capacity "
        "is mean-of-historical-deliveries, which is sometimes tight relative to "
        "demand and forces the LP to choose 'all spot'. This makes deterministic "
        "and Γ-robust converge to the same recourse outcome on this data. The "
        "two-stage SP differentiates because it aggregates capacity across the "
        "horizon. Real partner data with explicit contract bounds will produce "
        "more separation across policies. <br><br>"
        "<b>Theoretical upper bound</b> (perfect hindsight) is not implemented "
        "in this build. When added, it must be labelled as an unattainable "
        "ceiling — never as an achievable savings number."
    )
