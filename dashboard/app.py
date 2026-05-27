"""HarvestMind dashboard — navigation shell."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import streamlit as st

_here = Path(__file__).parent

pages = st.navigation(
    [
        st.Page(str(_here / "overview.py"),                            title="Overview",          icon=":material/dashboard:", default=True),
        st.Page(str(_here / "pages/01_executive_overview.py"),         title="Performance",       icon=":material/insights:"),
        st.Page(str(_here / "pages/02_planning_recommendations.py"),   title="Recommendations",   icon=":material/playlist_add_check:"),
        st.Page(str(_here / "pages/03_backtest_results.py"),           title="Backtest",          icon=":material/science:"),
        st.Page(str(_here / "pages/04_waste_spot_exposure.py"),        title="Loss exposure",     icon=":material/warning:"),
        st.Page(str(_here / "pages/05_partner_intelligence.py"),       title="Partners",          icon=":material/handshake:"),
        st.Page(str(_here / "pages/06_data_quality.py"),               title="Data quality",      icon=":material/verified:"),
        st.Page(str(_here / "pages/07_report_export.py"),              title="Reports",           icon=":material/description:"),
    ],
    position="sidebar",
)
pages.run()
