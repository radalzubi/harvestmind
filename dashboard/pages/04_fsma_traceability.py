"""FSMA-204 Traceability page: lot lookup and FDA report export."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import streamlit as st
import duckdb


@st.cache_resource
def get_conn():
    db_path = os.getenv("DUCKDB_PATH", str(ROOT / "harvestmind.duckdb"))
    return duckdb.connect(db_path, read_only=True)


conn = get_conn()
st.header("FSMA-204 Traceability")
st.caption("Traceback lookup · FDA 24-hour sortable spreadsheet · Lot audit trail")

# ── TLC lookup ────────────────────────────────────────────────────────────────
st.subheader("Lot Lookup by Traceability Lot Code (TLC)")
col1, col2 = st.columns([3, 1])
with col1:
    tlc_input = st.text_input("Enter TLC (or partial match)", placeholder="TLC-SUP-001-PRD-001-20240601")
with col2:
    st.write("")
    search_btn = st.button("Search", type="primary")

if search_btn and tlc_input:
    try:
        lot_df = conn.execute(
            "SELECT l.*, p.crop_name, s.supplier_name "
            "FROM fact_lots l "
            "JOIN dim_products p ON l.product_id = p.product_id "
            "JOIN dim_suppliers s ON l.supplier_id = s.supplier_id "
            "WHERE l.traceability_lot_code LIKE ?",
            [f"%{tlc_input}%"],
        ).df()
        if not lot_df.empty:
            st.success(f"Found {len(lot_df)} lot(s)")
            st.dataframe(lot_df[["traceability_lot_code","crop_name","supplier_name",
                                  "quantity_kg","harvest_date","pack_date","best_by_date",
                                  "lot_status"]], use_container_width=True, hide_index=True)

            # CTE event chain
            tlcs = lot_df["traceability_lot_code"].tolist()
            cte_df = conn.execute(
                "SELECT * FROM v_fsma_204_report WHERE traceability_lot_code = ANY(?)",
                [tlcs],
            ).df()
            if not cte_df.empty:
                st.subheader("Critical Tracking Events")
                st.dataframe(cte_df, use_container_width=True, hide_index=True)

                # Export button
                csv = cte_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Download FDA Spreadsheet (CSV)",
                    data=csv,
                    file_name=f"fsma_204_traceback_{tlc_input}.csv",
                    mime="text/csv",
                )
        else:
            st.warning("No lots found matching that TLC.")
    except Exception as e:
        st.error(f"Lookup failed: {e}")

st.divider()

# ── Recent lots ───────────────────────────────────────────────────────────────
st.subheader("Recent Active Lots (FTL Products)")
try:
    recent = conn.execute(
        "SELECT l.traceability_lot_code, p.crop_name, s.supplier_name, "
        "l.quantity_kg, l.harvest_date, l.best_by_date, l.lot_status "
        "FROM fact_lots l "
        "JOIN dim_products p ON l.product_id = p.product_id "
        "JOIN dim_suppliers s ON l.supplier_id = s.supplier_id "
        "WHERE l.lot_status = 'active' "
        "ORDER BY l.created_at DESC LIMIT 100"
    ).df()
    if not recent.empty:
        st.dataframe(recent, use_container_width=True, hide_index=True)
    else:
        st.info("No active lots. Load synthetic data or connect your system.")
except Exception as e:
    st.warning(f"Lot data unavailable: {e}")

# ── Compliance status ─────────────────────────────────────────────────────────
st.subheader("Compliance Status")
try:
    ftl_count = conn.execute("SELECT COUNT(*) FROM dim_products WHERE is_ftl_item = TRUE").fetchone()[0]
    lot_count = conn.execute("SELECT COUNT(*) FROM fact_lots").fetchone()[0]
    cte_count = conn.execute("SELECT COUNT(*) FROM fact_cte_events").fetchone()[0]

    col1, col2, col3 = st.columns(3)
    col1.metric("FTL Products Tracked", str(ftl_count))
    col2.metric("Active Lot Records", str(lot_count))
    col3.metric("CTE Events Logged", str(cte_count))

    st.caption(
        "FSMA Section 204 compliance date: July 20, 2028 (extended). "
        "Major buyers (Sysco, US Foods, Walmart) are requesting KDE data now."
    )
except Exception as e:
    st.warning(f"Compliance stats unavailable: {e}")
