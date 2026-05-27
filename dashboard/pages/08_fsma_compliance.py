"""Page 8 — FSMA-204 Traceability.

FDA Food Traceability Rule (21 CFR Part 1, Subpart S).
Compliance date: July 20, 2028. Major retailers require KDE data NOW.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from dashboard.components.cards import section
from dashboard.components.empty import db_unavailable, empty_state
from dashboard.lib import db, theme
from dashboard.lib.fsma_metrics import (
    fsma_coverage_score,
    ftl_product_list,
    fsma_lot_chain,
    generate_fda_report_csv,
    recent_cte_events,
)

theme.apply(page_title="FSMA-204")

if not db.is_available():
    db_unavailable()
    st.stop()

conn = db.get_conn()

theme.page_header(
    title="FSMA-204 Traceability",
    subtitle="FDA Food Traceability Rule · enforcement July 2028",
)

# ── Score + summary tiles ────────────────────────────────────────────────────
score = fsma_coverage_score(conn)

c1, c2, c3, c4 = st.columns(4, gap="medium")
status_bg = {
    "Full":    ("#DCFCE7", "#15803D"),
    "Partial": ("#FEF3C7", "#B45309"),
    "Minimal": ("#FFEDD5", "#EA580C"),
    "None":    ("#FEE2E2", "#B91C1C"),
}
bg, fg = status_bg[score["status"]]

with c1:
    st.markdown(
        f'<div class="hm-card"><div class="hm-label">Coverage score</div>'
        f'<div class="hm-value">{score["coverage_pct"] * 100:.0f}%</div>'
        f'<span class="hm-status" style="background:{bg};color:{fg};">{score["status"]}</span></div>',
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f'<div class="hm-card"><div class="hm-label">Covered volume</div>'
        f'<div class="hm-value">{int(score["covered_kg"]):,} kg</div></div>',
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        f'<div class="hm-card"><div class="hm-label">Missing volume</div>'
        f'<div class="hm-value">{int(score["missing_kg"]):,} kg</div></div>',
        unsafe_allow_html=True,
    )
with c4:
    st.markdown(
        f'<div class="hm-card"><div class="hm-label">FTL products</div>'
        f'<div class="hm-value">{score["n_ftl_products_covered"]} / {score["n_ftl_products_total"]}</div></div>',
        unsafe_allow_html=True,
    )

st.write("")

# ── FTL product table ────────────────────────────────────────────────────────
section("FTL products")

products = ftl_product_list(conn)
if products.empty:
    empty_state("No FTL items configured", "Mark Food Traceability List items via dim_products.is_ftl_item.")
else:
    disp = products.copy()

    def _color(v: float) -> str:
        return "#15803D" if v >= 0.95 else ("#B45309" if v >= 0.5 else "#B91C1C")

    disp["Coverage"] = disp["coverage_pct"].apply(lambda v: f"{v * 100:.0f}%")
    disp["Action"] = disp["coverage_pct"].apply(
        lambda v: "✓ Complete" if v >= 0.95 else "⚠ Upload receiving logs"
    )
    disp["Received kg"] = disp["received_kg"].apply(lambda v: f"{int(v):,}")
    disp["Covered kg"] = disp["covered_kg"].apply(lambda v: f"{int(v):,}")
    disp = disp.rename(columns={
        "crop_name": "Product",
        "crop_category": "FTL Category",
        "status": "Status",
    })
    cols = ["Product", "FTL Category", "Received kg", "Covered kg", "Coverage", "Status", "Action"]
    st.dataframe(disp[cols], use_container_width=True, hide_index=True)

# ── Recent CTE activity ──────────────────────────────────────────────────────
section("Recent CTE activity")
recent = recent_cte_events(conn, limit=20)
if recent.empty:
    empty_state(
        "No CTE records yet",
        "Records appear automatically when receiving workflows tag deliveries with a Traceability Lot Code.",
    )
else:
    show_cols = [
        "traceability_lot_code", "product_description", "cte_type",
        "location_description", "event_timestamp", "recorded_by",
    ]
    have_cols = [c for c in show_cols if c in recent.columns]
    rename_map = {
        "traceability_lot_code": "TLC",
        "product_description":   "Product",
        "cte_type":              "Event",
        "location_description":  "Location",
        "event_timestamp":       "When",
        "recorded_by":           "Recorded by",
    }
    st.dataframe(
        recent[have_cols].rename(columns=rename_map),
        use_container_width=True, hide_index=True,
    )

# ── FDA report download ──────────────────────────────────────────────────────
section("FDA 24-hour report")

tlc_input = st.text_input(
    "Traceability Lot Code (leave blank for all CTEs in last 30 days)",
    value="",
).strip() or None

col_a, col_b = st.columns([1, 1], gap="medium")
with col_a:
    csv_str = generate_fda_report_csv(conn, tlc=tlc_input)
    st.download_button(
        "Download FDA Report (CSV)",
        data=csv_str.encode("utf-8"),
        file_name="fsma_report.csv",
        mime="text/csv",
        use_container_width=True,
        disabled=not csv_str.strip(),
    )

with col_b:
    if tlc_input:
        chain = fsma_lot_chain(conn, tlc_input)
        chain_csv = chain.to_csv(index=False) if not chain.empty else ""
        st.download_button(
            "Download lot chain (CSV)",
            data=chain_csv.encode("utf-8"),
            file_name=f"fsma_chain_{tlc_input}.csv",
            mime="text/csv",
            use_container_width=True,
            disabled=chain.empty,
        )
    else:
        st.caption("Enter a TLC above to download its full chain.")

# ── Compliance guidance ──────────────────────────────────────────────────────
with st.expander("What FSMA-204 requires"):
    st.markdown(
        """
**FSMA Section 204** (21 CFR Part 1, Subpart S) requires hubs handling Food
Traceability List items to capture **Key Data Elements** at six **Critical
Tracking Events**: harvesting, cooling, initial packing, shipping, receiving,
and transformation.

**FDA enforcement:** July 20, 2028 (extended November 2025).

**Major buyers requiring it now:** Walmart, Sysco, US Foods.

**For each CTE, the FDA requires:**
- A Traceability Lot Code (TLC) for every shipment of FTL product
- The quantity and unit of measure
- Location description, business name, point of contact
- Date and time of the event
- For *transformations*: the input TLC(s) and the new output TLC

**24-hour rule:** on FDA request, the hub must produce a sortable spreadsheet
with all CTEs for the affected TLC chain within 24 hours.
        """
    )
