"""Visual theme + global stylesheet for the HarvestMind dashboard.

A single stylesheet injected via ``st.markdown(...,unsafe_allow_html=True)``
on every page so cards / typography / spacing stay consistent.
"""

from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------

INK = "#0F172A"          # primary text
INK_MUTED = "#475569"    # secondary text
INK_FAINT = "#94A3B8"    # tertiary / placeholder
LINE = "#E2E8F0"         # card / table borders
SURFACE = "#FFFFFF"      # card background
SURFACE_ALT = "#F8FAFC"  # page background, table stripe
ACCENT = "#0F766E"       # primary brand (deep teal — credible, neutral)
ACCENT_SOFT = "#CCFBF1"
GOOD = "#15803D"         # delta improving
GOOD_SOFT = "#DCFCE7"
WARN = "#B45309"         # caution
WARN_SOFT = "#FEF3C7"
BAD = "#B91C1C"          # delta worsening / critical
BAD_SOFT = "#FEE2E2"
INFO = "#1D4ED8"
INFO_SOFT = "#DBEAFE"

# Plotly-friendly palette (categorical)
PALETTE = [
    "#0F766E",  # accent
    "#1D4ED8",  # info
    "#B45309",  # warn
    "#7C3AED",  # purple
    "#0891B2",  # cyan
    "#94A3B8",  # neutral
]

# Risk → palette token
RISK_COLORS: dict[str, str] = {
    "Low":      GOOD,
    "Medium":   WARN,
    "High":     "#EA580C",
    "Critical": BAD,
}
RISK_BG: dict[str, str] = {
    "Low":      GOOD_SOFT,
    "Medium":   WARN_SOFT,
    "High":     "#FFEDD5",
    "Critical": BAD_SOFT,
}


# ---------------------------------------------------------------------------
# Stylesheet
# ---------------------------------------------------------------------------

_GLOBAL_CSS = """
<style>
:root {
    --hm-ink: #0F172A;
    --hm-ink-muted: #475569;
    --hm-ink-faint: #94A3B8;
    --hm-line: #E2E8F0;
    --hm-surface: #FFFFFF;
    --hm-surface-alt: #F8FAFC;
    --hm-accent: #0F766E;
    --hm-good: #15803D;
    --hm-warn: #B45309;
    --hm-bad: #B91C1C;
}

/* Page chrome */
html, body, [class*="css"], .stApp {
    background-color: var(--hm-surface-alt) !important;
    color: var(--hm-ink) !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", Roboto, "Helvetica Neue", Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
}
.stApp > header { background: transparent; }

/* Constrain main column for readability */
.block-container {
    padding-top: 2.0rem !important;
    padding-bottom: 4rem !important;
    max-width: 1240px;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: var(--hm-surface) !important;
    border-right: 1px solid var(--hm-line);
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: var(--hm-ink) !important;
}
section[data-testid="stSidebar"] .stRadio label,
section[data-testid="stSidebar"] .stMarkdown {
    color: var(--hm-ink) !important;
}

/* Headings */
h1, h2, h3, h4 {
    color: var(--hm-ink) !important;
    letter-spacing: -0.01em;
}
h1 { font-weight: 700 !important; font-size: 1.6rem !important; margin-bottom: 0.25rem !important; }
h2 { font-weight: 600 !important; font-size: 1.15rem !important; margin: 1.25rem 0 0.5rem !important; }
h3 { font-weight: 600 !important; font-size: 1.0rem !important; margin: 1rem 0 0.4rem !important; }

/* Page header subtitle */
.hm-subtitle {
    color: var(--hm-ink-muted);
    font-size: 0.9rem;
    margin-bottom: 1.5rem;
}

/* Metric (KPI) card */
.hm-card {
    background: var(--hm-surface);
    border: 1px solid var(--hm-line);
    border-radius: 10px;
    padding: 16px 18px;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    height: 100%;
}
.hm-card .hm-label {
    color: var(--hm-ink-muted);
    font-size: 0.78rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 0.4rem;
}
.hm-card .hm-value {
    color: var(--hm-ink);
    font-size: 1.8rem;
    font-weight: 700;
    line-height: 1.1;
    margin: 0.05rem 0;
}
.hm-card .hm-delta {
    font-size: 0.82rem;
    font-weight: 500;
    margin-top: 0.25rem;
}
.hm-card .hm-delta.up    { color: var(--hm-good); }
.hm-card .hm-delta.down  { color: var(--hm-bad); }
.hm-card .hm-delta.flat  { color: var(--hm-ink-muted); }
.hm-card .hm-sub {
    color: var(--hm-ink-muted);
    font-size: 0.78rem;
    margin-top: 0.55rem;
    line-height: 1.35;
}
.hm-card .hm-status {
    display: inline-block;
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 100px;
    font-weight: 600;
    margin-top: 0.45rem;
}

/* Risk badge */
.hm-badge {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 100px;
    font-size: 0.75rem;
    font-weight: 600;
    line-height: 1.4;
    border: 1px solid transparent;
}
.hm-badge.low      { background: #DCFCE7; color: #15803D; border-color: #BBF7D0; }
.hm-badge.medium   { background: #FEF3C7; color: #B45309; border-color: #FDE68A; }
.hm-badge.high     { background: #FFEDD5; color: #EA580C; border-color: #FED7AA; }
.hm-badge.critical { background: #FEE2E2; color: #B91C1C; border-color: #FECACA; }
.hm-badge.info     { background: #DBEAFE; color: #1D4ED8; border-color: #BFDBFE; }
.hm-badge.neutral  { background: #F1F5F9; color: #475569; border-color: #E2E8F0; }

/* Section */
.hm-section {
    background: var(--hm-surface);
    border: 1px solid var(--hm-line);
    border-radius: 10px;
    padding: 18px 22px;
    margin-bottom: 18px;
}
.hm-section .hm-section-title {
    font-size: 0.92rem;
    font-weight: 600;
    color: var(--hm-ink);
    margin-bottom: 0.15rem;
}
.hm-section .hm-section-sub {
    font-size: 0.8rem;
    color: var(--hm-ink-muted);
    margin-bottom: 0.85rem;
}

/* Insight box (executive callout) */
.hm-insight {
    background: #F0FDFA;
    border-left: 3px solid var(--hm-accent);
    padding: 14px 18px;
    border-radius: 6px;
    color: var(--hm-ink);
    font-size: 0.92rem;
    line-height: 1.55;
    margin: 12px 0 18px;
}

/* Caveat / assumption */
.hm-caveat {
    background: #FFFBEB;
    border-left: 3px solid var(--hm-warn);
    padding: 12px 16px;
    border-radius: 6px;
    color: var(--hm-ink-muted);
    font-size: 0.84rem;
    line-height: 1.5;
}

/* Empty state */
.hm-empty {
    border: 1px dashed var(--hm-line);
    border-radius: 10px;
    padding: 36px 24px;
    background: var(--hm-surface);
    color: var(--hm-ink-muted);
    text-align: center;
}
.hm-empty .hm-empty-title {
    color: var(--hm-ink);
    font-weight: 600;
    margin-bottom: 0.4rem;
}
.hm-empty .hm-empty-body {
    font-size: 0.88rem;
    line-height: 1.5;
}

/* Streamlit dataframe table polish */
[data-testid="stDataFrame"] div[role="grid"] {
    border: 1px solid var(--hm-line) !important;
    border-radius: 8px !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    border-bottom: 1px solid var(--hm-line);
}
.stTabs [data-baseweb="tab"] {
    padding: 8px 14px;
    color: var(--hm-ink-muted);
    font-weight: 500;
}
.stTabs [aria-selected="true"] {
    color: var(--hm-accent) !important;
}

/* Buttons */
.stButton > button {
    background: var(--hm-accent);
    color: white;
    border: 0;
    font-weight: 500;
    border-radius: 6px;
}
.stButton > button:hover { background: #115E59; color: white; }
.stButton > button:disabled { background: var(--hm-ink-faint); }

/* Native st.metric polish */
[data-testid="stMetric"] {
    background: var(--hm-surface);
    border: 1px solid var(--hm-line);
    border-radius: 10px;
    padding: 14px 16px;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
[data-testid="stMetricLabel"] p {
    color: var(--hm-ink-muted) !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
[data-testid="stMetricValue"] {
    color: var(--hm-ink) !important;
    font-weight: 700 !important;
}
</style>
"""


def apply(*, page_title: str, page_icon: str = "🌾") -> None:
    """Set the Streamlit page config + inject the theme CSS once.

    Call once at the top of every page module.
    """
    st.set_page_config(
        page_title=f"HarvestMind — {page_title}",
        page_icon=page_icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str, *, eyebrow: str | None = None) -> None:
    """Render the consistent page title block."""
    if eyebrow:
        st.markdown(
            f'<div style="color:{INK_MUTED};font-size:0.75rem;letter-spacing:0.06em;'
            f'text-transform:uppercase;margin-bottom:0.25rem;">{eyebrow}</div>',
            unsafe_allow_html=True,
        )
    st.markdown(f'<h1 style="margin-top:0;">{title}</h1>', unsafe_allow_html=True)
    st.markdown(f'<div class="hm-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def plotly_layout(*, height: int = 320, title: str | None = None) -> dict:
    """Default plotly layout — applied on top of any chart."""
    return {
        "title": (
            {"text": title, "font": {"size": 14, "color": INK}, "x": 0, "xanchor": "left"}
            if title else None
        ),
        "height": height,
        "margin": {"l": 50, "r": 16, "t": 40 if title else 16, "b": 40},
        "plot_bgcolor": SURFACE,
        "paper_bgcolor": SURFACE,
        "font": {"family": "-apple-system, BlinkMacSystemFont, Inter, sans-serif",
                 "color": INK, "size": 12},
        "xaxis": {"gridcolor": LINE, "linecolor": LINE, "zerolinecolor": LINE},
        "yaxis": {"gridcolor": LINE, "linecolor": LINE, "zerolinecolor": LINE},
        "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02,
                   "xanchor": "left", "x": 0, "bgcolor": "rgba(0,0,0,0)"},
        "hoverlabel": {"bgcolor": SURFACE, "bordercolor": LINE,
                       "font": {"family": "Inter, sans-serif", "color": INK, "size": 12}},
    }
