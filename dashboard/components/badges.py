"""Risk / status badges for use inline in tables and recommendations."""

from __future__ import annotations

from html import escape


def risk_badge(level: str | None) -> str:
    """Return inline HTML for a Low/Medium/High/Critical badge."""
    if not level:
        return ""
    s = str(level).strip().lower()
    cls = s if s in ("low", "medium", "high", "critical", "info", "neutral") else "neutral"
    label = level if isinstance(level, str) else "—"
    return f'<span class="hm-badge {cls}">{escape(label)}</span>'


def info_badge(text: str) -> str:
    return f'<span class="hm-badge info">{escape(text)}</span>'


def neutral_badge(text: str) -> str:
    return f'<span class="hm-badge neutral">{escape(text)}</span>'


# Multiple badges joined with a small gap, for risk-driver columns
def badge_row(items: list[str | None]) -> str:
    out = []
    for item in items:
        if not item:
            continue
        if item in ("Low", "Medium", "High", "Critical"):
            out.append(risk_badge(item))
        else:
            out.append(neutral_badge(item))
    return '<span style="display:inline-flex;gap:4px;flex-wrap:wrap;">' + "".join(out) + "</span>"
