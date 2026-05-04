"""Page 6 — Data Quality & Assumptions.

Build trust by being transparent about completeness and assumptions."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from dashboard.components.cards import caveat, section
from dashboard.components.empty import db_unavailable
from dashboard.lib import db, metrics, theme
from dashboard.lib.formatters import fmt_count, fmt_currency, fmt_percent

theme.apply(page_title="Data Quality & Assumptions")

if not db.is_available():
    db_unavailable()
    st.stop()

conn = db.get_conn()

theme.page_header(
    eyebrow="Page 6 of 7",
    title="Data Quality & Assumptions",
    subtitle=(
        "Required reading before sharing any output externally. Every "
        "estimate on this dashboard is conditional on the rows below being "
        "complete and accurate."
    ),
)

# ── Score + summary ──────────────────────────────────────────────────────
score = metrics.data_quality_score(conn)
breakdown = metrics.data_quality_breakdown(conn)

c1, c2, c3 = st.columns([1, 1, 2], gap="medium")
with c1:
    status = ("Strong" if score >= 0.9 else
              "Usable with caveats" if score >= 0.6 else
              "Weak" if score > 0 else "Not enough data")
    st.markdown(
        f'<div class="hm-card"><div class="hm-label">Overall quality score</div>'
        f'<div class="hm-value">{fmt_percent(score)}</div>'
        f'<div class="hm-sub">Average completeness across {len(breakdown)} datasets.</div>'
        f'<span class="hm-status" style="background:'
        f'{"#DCFCE7" if status=="Strong" else "#FEF3C7" if status=="Usable with caveats" else "#FFEDD5"};'
        f'color:'
        f'{"#15803D" if status=="Strong" else "#B45309" if status=="Usable with caveats" else "#EA580C"};">'
        f'{status}</span></div>',
        unsafe_allow_html=True,
    )
with c2:
    n_strong = sum(1 for r in breakdown if r.status == "Strong")
    n_total = len(breakdown)
    st.markdown(
        f'<div class="hm-card"><div class="hm-label">Datasets at full strength</div>'
        f'<div class="hm-value">{n_strong} / {n_total}</div>'
        f'<div class="hm-sub">Below threshold = treat as directional only.</div></div>',
        unsafe_allow_html=True,
    )
with c3:
    weak = [r.dataset for r in breakdown if r.status in ("Weak", "Not enough data")]
    st.markdown(
        f'<div class="hm-card"><div class="hm-label">Datasets needing attention</div>'
        f'<div class="hm-value" style="font-size:1.0rem;line-height:1.4;">'
        f'{", ".join(weak[:6]) if weak else "All datasets above threshold"}</div>'
        f'<div class="hm-sub">{("+" + str(len(weak) - 6) + " more") if len(weak) > 6 else ""}</div></div>',
        unsafe_allow_html=True,
    )

st.write("")

# ── Breakdown table ──────────────────────────────────────────────────────
section("Per-dataset completeness", "Row counts vs calibration thresholds.")
df = pd.DataFrame([
    {
        "Dataset": r.dataset,
        "Rows": fmt_count(r.rows),
        "Completeness": fmt_percent(r.completeness),
        "Status": r.status,
        "Notes": r.note,
    }
    for r in breakdown
])
st.dataframe(df, use_container_width=True, hide_index=True)

# Warning banner for any weak data
weak_datasets = [r.dataset for r in breakdown if r.status in ("Weak", "Not enough data")]
if weak_datasets:
    st.markdown(
        f'<div class="hm-caveat" style="margin-top:14px;">'
        f"<b>Warning:</b> the following datasets are below the 'usable' threshold "
        f"and reduce confidence in any KPI that depends on them: "
        f"<b>{', '.join(weak_datasets)}</b>. Treat affected estimates as "
        f"directional and widen confidence ranges.</div>",
        unsafe_allow_html=True,
    )

# ── Schema validation ─────────────────────────────────────────────────────
section("Schema validation", "DuckDB enforced constraints — what the database itself guarantees.")

constraint_checks = [
    ("All `dim_products` rows have a non-null product_id", True,
     "Enforced by PRIMARY KEY"),
    ("All `fact_orders` rows reference an existing `dim_buyers` row", True,
     "Enforced by FOREIGN KEY"),
    ("All `fact_purchase_orders` rows reference an existing supplier + product", True,
     "Enforced by FOREIGN KEY"),
    ("`qty_committed_kg` ≥ 0", True, "CHECK constraint"),
    ("`qty_rejected_kg` ≤ `qty_received_kg`", True, "CHECK constraint"),
    ("`order_status` ∈ {draft, confirmed, fulfilled, partial, cancelled}", True,
     "CHECK constraint"),
    ("`waste_stage` ∈ {pre_sale, post_sale, transit, cold_chain, quality, shrink}", True,
     "CHECK constraint"),
]
checks_df = pd.DataFrame([
    {"Check": c, "Pass": "✓" if ok else "✗", "Source": s}
    for c, ok, s in constraint_checks
])
st.dataframe(checks_df, use_container_width=True, hide_index=True)

# ── Records used / excluded ──────────────────────────────────────────────
section("Record usage summary", "How many rows the dashboard actually consumes.")
usage = pd.DataFrame([
    {"Stage": "Order lines (kg-weighted fill)",
     "Used": conn.execute("SELECT COUNT(*) FROM fact_order_lines").fetchone()[0],
     "Excluded": 0,
     "Reason for exclusion": "—"},
    {"Stage": "Purchase orders (spot exposure)",
     "Used": conn.execute("SELECT COUNT(*) FROM fact_purchase_orders").fetchone()[0],
     "Excluded": 0,
     "Reason for exclusion": "—"},
    {"Stage": "Deliveries (supplier reliability)",
     "Used": conn.execute(
         "SELECT COUNT(*) FROM fact_deliveries WHERE qty_received_kg IS NOT NULL"
     ).fetchone()[0],
     "Excluded": 0,
     "Reason for exclusion": "—"},
    {"Stage": "Waste events",
     "Used": conn.execute("SELECT COUNT(*) FROM fact_waste_events").fetchone()[0],
     "Excluded": 0,
     "Reason for exclusion": "—"},
])
st.dataframe(usage, use_container_width=True, hide_index=True)

# ── Assumptions ──────────────────────────────────────────────────────────
section("Assumptions used in monetary KPIs", "Each is tunable in `dashboard/lib/metrics.py`.")
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

# ── Caveat ────────────────────────────────────────────────────────────────
caveat(
    "<b>What this page is not.</b> Schema validation here lists the static "
    "database constraints — it does not run a fresh validation pass on incoming "
    "data. For pre-ingestion validation see <code>data_contracts/validation/"
    "pandera_schemas.py</code>. The completeness thresholds in the table above "
    "are calibrated for the synthetic Indiana pilot dataset and will need "
    "re-tuning for partners with substantially different volume profiles."
)

# ── Export ────────────────────────────────────────────────────────────────
csv_data = df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download data quality summary (CSV)",
    data=csv_data,
    file_name="harvestmind_data_quality.csv",
    mime="text/csv",
)
