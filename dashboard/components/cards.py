"""KPI / metric cards rendered as raw HTML for full typographic control."""

from __future__ import annotations

from html import escape

import streamlit as st


def metric_card(
    label: str,
    value: str,
    *,
    delta: str | None = None,
    delta_direction: str | None = None,   # "up" | "down" | "flat"
    subtitle: str | None = None,
    status: str | None = None,            # "Strong" | "Usable with caveats" | "Weak" | …
) -> None:
    """Render a single KPI tile.

    Direction semantics: "up" = green (improvement), "down" = red (regression),
    "flat" = neutral grey. Caller decides the meaning since some metrics
    improve when going down (waste, spot) and others when going up (fill).
    """
    delta_html = ""
    if delta:
        cls = delta_direction if delta_direction in ("up", "down", "flat") else "flat"
        arrow = {"up": "▲", "down": "▼", "flat": "•"}.get(cls, "•")
        delta_html = (
            f'<div class="hm-delta {cls}">{arrow}&nbsp;{escape(delta)}</div>'
        )
    sub_html = (
        f'<div class="hm-sub">{escape(subtitle)}</div>' if subtitle else ""
    )
    status_html = ""
    if status:
        status_color = {
            "Strong":              ("#DCFCE7", "#15803D"),
            "Usable with caveats": ("#FEF3C7", "#B45309"),
            "Weak":                ("#FFEDD5", "#EA580C"),
            "Not enough data":     ("#FEE2E2", "#B91C1C"),
        }.get(status, ("#F1F5F9", "#475569"))
        status_html = (
            f'<span class="hm-status" style="background:{status_color[0]};'
            f'color:{status_color[1]};">{escape(status)}</span>'
        )

    # NB: no indentation — Streamlit's markdown otherwise treats leading
    # whitespace as a code fence and prints the raw HTML as code.
    html = (
        '<div class="hm-card">'
        f'<div class="hm-label">{escape(label)}</div>'
        f'<div class="hm-value">{escape(value)}</div>'
        f'{delta_html}{sub_html}{status_html}'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def metric_grid(metrics: list[dict], *, columns: int = 3) -> None:
    """Render a responsive grid of metric cards."""
    cols = st.columns(columns, gap="medium")
    for i, m in enumerate(metrics):
        with cols[i % columns]:
            metric_card(**m)


def section(title: str, subtitle: str | None = None) -> None:
    """Section header inside a page."""
    st.markdown(f'<h2>{escape(title)}</h2>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(
            f'<div style="color:#475569;font-size:0.85rem;margin:-0.4rem 0 0.6rem;">'
            f'{escape(subtitle)}</div>',
            unsafe_allow_html=True,
        )


def insight(text: str) -> None:
    """Plain-English executive insight callout."""
    st.markdown(f'<div class="hm-insight">{text}</div>', unsafe_allow_html=True)


def caveat(text: str) -> None:
    """Assumption / caveat banner."""
    st.markdown(f'<div class="hm-caveat">{text}</div>', unsafe_allow_html=True)
