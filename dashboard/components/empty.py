"""Empty / loading / error states."""

from __future__ import annotations

from html import escape

import streamlit as st


def empty_state(title: str, body: str, *, action: str | None = None) -> None:
    """Friendly empty-state block — used when a query returns no rows."""
    action_html = (
        f'<div style="margin-top:0.75rem;color:#0F766E;font-weight:500;">{escape(action)}</div>'
        if action else ""
    )
    html = (
        '<div class="hm-empty">'
        f'<div class="hm-empty-title">{escape(title)}</div>'
        f'<div class="hm-empty-body">{escape(body)}</div>'
        f'{action_html}'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def error_state(title: str, body: str) -> None:
    html = (
        '<div class="hm-empty" style="border-color:#FECACA;background:#FEF2F2;">'
        f'<div class="hm-empty-title" style="color:#B91C1C;">{escape(title)}</div>'
        f'<div class="hm-empty-body">{escape(body)}</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def db_unavailable() -> None:
    """Shown when the DuckDB file isn't on disk yet."""
    error_state(
        title="Database not initialised",
        body=(
            "Run `make setup` from the project root to create the schema and load "
            "the synthetic pilot dataset, then refresh this page."
        ),
    )
