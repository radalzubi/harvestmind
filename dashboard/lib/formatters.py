"""Display formatters for the HarvestMind dashboard.

All UI numbers should pass through these helpers so we get one currency
style, one percent style, one quantity style, and one date style across
every page. Formatters never raise on None / NaN — they return a clean
``"—"`` placeholder so the dashboard never displays "nan" or "None".
"""

from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any

import pandas as pd

DASH = "—"  # em-dash, used for missing / not applicable


def _is_missing(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, float):
        return math.isnan(v) or math.isinf(v)
    try:
        if pd.isna(v):  # type: ignore[arg-type]
            return True
    except (TypeError, ValueError):
        pass
    return False


def fmt_currency(
    value: float | int | None,
    *,
    compact: bool = False,
    cents: bool = False,
) -> str:
    """Format USD. ``compact`` switches to $72.4K / $1.2M for big numbers."""
    if _is_missing(value):
        return DASH
    v = float(value)
    sign = "-" if v < 0 else ""
    a = abs(v)
    if compact:
        if a >= 1_000_000:
            return f"{sign}${a / 1_000_000:.1f}M"
        if a >= 1_000:
            return f"{sign}${a / 1_000:.1f}K"
    if cents:
        return f"{sign}${a:,.2f}"
    return f"{sign}${a:,.0f}"


def fmt_currency_range(low: float | None, high: float | None, *, compact: bool = True) -> str:
    """``$65K-$82K`` style confidence intervals."""
    if _is_missing(low) and _is_missing(high):
        return DASH
    return f"{fmt_currency(low, compact=compact)}–{fmt_currency(high, compact=compact)}"


def fmt_percent(value: float | None, *, decimals: int = 1, signed: bool = False) -> str:
    """Format a *fractional* percent (0.142 → ``14.2%``).

    ``signed=True`` prefixes ``+`` for positives — useful for deltas.
    """
    if _is_missing(value):
        return DASH
    v = float(value) * 100
    if signed and v > 0:
        return f"+{v:.{decimals}f}%"
    return f"{v:.{decimals}f}%"


def fmt_percent_points(value: float | None, *, decimals: int = 1) -> str:
    """Format a *whole* point delta (already in percent units).

    ``2.3 → "+2.3 pts"``
    """
    if _is_missing(value):
        return DASH
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{decimals}f} pts"


def fmt_kg(value: float | None, *, compact: bool = False) -> str:
    """Format kilograms with thousand separators."""
    if _is_missing(value):
        return DASH
    v = float(value)
    if compact and abs(v) >= 1_000_000:
        return f"{v / 1_000_000:.1f}M kg"
    if compact and abs(v) >= 10_000:
        return f"{v / 1_000:.1f}K kg"
    return f"{v:,.0f} kg"


def fmt_quantity(value: float | None, unit: str = "") -> str:
    if _is_missing(value):
        return DASH
    base = f"{float(value):,.0f}"
    return f"{base} {unit}".strip() if unit else base


def fmt_count(value: int | None) -> str:
    if _is_missing(value):
        return DASH
    return f"{int(value):,}"


def fmt_multiple(value: float | None, *, decimals: int = 1) -> str:
    """``27.4×`` style multiplier."""
    if _is_missing(value):
        return DASH
    return f"{float(value):.{decimals}f}×"


def fmt_date(value: Any, *, fmt: str = "%b %d, %Y") -> str:
    """Format a date or datetime for display. Empty / NaT → ``—``."""
    if _is_missing(value):
        return DASH
    if isinstance(value, str):
        try:
            value = pd.to_datetime(value)
        except (ValueError, TypeError):
            return value
    if isinstance(value, (date, datetime, pd.Timestamp)):
        return value.strftime(fmt)
    try:
        return pd.to_datetime(value).strftime(fmt)
    except (ValueError, TypeError):
        return str(value)


def fmt_date_range(start: Any, end: Any) -> str:
    if _is_missing(start) and _is_missing(end):
        return DASH
    return f"{fmt_date(start)} – {fmt_date(end)}"


def fmt_risk(level: str | None) -> str:
    """Canonicalise free-text risk into Low / Medium / High / Critical."""
    if _is_missing(level):
        return DASH
    s = str(level).strip().lower()
    canon = {
        "low": "Low", "medium": "Medium", "med": "Medium",
        "high": "High", "critical": "Critical", "severe": "Critical",
    }
    return canon.get(s, str(level).title())


# ---------------------------------------------------------------------------
# Delta formatters — return (text, is_positive_delta) tuples
# ---------------------------------------------------------------------------

def delta_currency(actual: float | None, baseline: float | None,
                   *, lower_is_better: bool = True) -> tuple[str, bool] | tuple[None, None]:
    if _is_missing(actual) or _is_missing(baseline) or baseline == 0:
        return None, None
    diff = actual - baseline
    pct = diff / baseline
    is_good = (diff < 0) if lower_is_better else (diff > 0)
    return f"{fmt_percent(pct, signed=True)} vs baseline", is_good


def delta_pct_points(actual: float | None, baseline: float | None,
                     *, higher_is_better: bool = True) -> tuple[str, bool] | tuple[None, None]:
    if _is_missing(actual) or _is_missing(baseline):
        return None, None
    diff = actual - baseline
    is_good = (diff > 0) if higher_is_better else (diff < 0)
    return fmt_percent_points(diff), is_good
