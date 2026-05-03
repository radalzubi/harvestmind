"""Reusable KPI card components for the Streamlit dashboard."""

from __future__ import annotations

import streamlit as st


def kpi_card(label: str, value: str, delta: str | None = None, delta_positive: bool = True) -> None:
    """Render a single KPI metric tile."""
    delta_color = "normal" if delta_positive else "inverse"
    st.metric(label=label, value=value, delta=delta, delta_color=delta_color)


def kpi_strip(metrics: list[dict]) -> None:
    """Render a horizontal strip of KPI cards.

    Each dict: {label, value, delta (optional), delta_positive (optional)}
    """
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        with col:
            kpi_card(
                label=m["label"],
                value=m["value"],
                delta=m.get("delta"),
                delta_positive=m.get("delta_positive", True),
            )
