"""HarvestMind Streamlit dashboard entry point.

Streamlit auto-discovers pages under dashboard/pages/. This file is the landing page.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(
    page_title="HarvestMind",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title("HarvestMind")
st.sidebar.caption("Stochastic Supply Planning")
st.sidebar.divider()
st.sidebar.caption("Purdue University LIFT Lab · v0.1.0")

st.title("HarvestMind")
st.caption("AI-driven supply planning for Midwest fresh produce distributors")

st.markdown("""
### Navigation

Use the sidebar to access:

- **Control Tower** — live operational KPIs and waste/delivery overview
- **Supply Planning** — run optimizer, view demand forecasts, recommended commitments
- **Backtest & ROI** — rolling-origin backtest results and partner ROI analysis
- **FSMA-204 Traceability** — lot lookup, FDA-ready 24-hour spreadsheet export

### Quick Stats
""")

import os
import duckdb

db_path = os.getenv("DUCKDB_PATH", str(ROOT / "harvestmind.duckdb"))

try:
    conn = duckdb.connect(db_path, read_only=True)
    n_orders = conn.execute("SELECT COUNT(*) FROM fact_orders").fetchone()[0]
    n_deliveries = conn.execute("SELECT COUNT(*) FROM fact_deliveries").fetchone()[0]
    n_lots = conn.execute("SELECT COUNT(*) FROM fact_lots").fetchone()[0]
    n_suppliers = conn.execute("SELECT COUNT(*) FROM dim_suppliers").fetchone()[0]
    conn.close()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Orders", f"{n_orders:,}")
    col2.metric("Deliveries", f"{n_deliveries:,}")
    col3.metric("FSMA-204 Lots", f"{n_lots:,}")
    col4.metric("Suppliers", str(n_suppliers))
except Exception as e:
    st.warning(f"Database not initialized. Run `python3 synthetic/generate_pilot_dataset.py` first. ({e})")
