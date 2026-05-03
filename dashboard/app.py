"""HarvestMind Streamlit dashboard entry point."""

import os
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

# Sidebar navigation
st.sidebar.image("", width=40)
st.sidebar.title("HarvestMind")
st.sidebar.caption("Stochastic Supply Planning")
st.sidebar.divider()

pages = {
    "Control Tower": "dashboard/pages/01_control_tower.py",
    "Supply Planning": "dashboard/pages/02_supply_planning.py",
    "Backtest & ROI": "dashboard/pages/03_backtest_roi.py",
    "FSMA-204 Traceability": "dashboard/pages/04_fsma_traceability.py",
}

page = st.sidebar.radio("Navigation", list(pages.keys()))
st.sidebar.divider()
st.sidebar.caption("Purdue University LIFT Lab · v0.1.0")

# Route to page
if page == "Control Tower":
    import importlib.util
    spec = importlib.util.spec_from_file_location("ct", ROOT / "dashboard/pages/01_control_tower.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
elif page == "Supply Planning":
    spec = importlib.util.spec_from_file_location("sp", ROOT / "dashboard/pages/02_supply_planning.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
elif page == "Backtest & ROI":
    spec = importlib.util.spec_from_file_location("bt", ROOT / "dashboard/pages/03_backtest_roi.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
elif page == "FSMA-204 Traceability":
    spec = importlib.util.spec_from_file_location("fsma", ROOT / "dashboard/pages/04_fsma_traceability.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
