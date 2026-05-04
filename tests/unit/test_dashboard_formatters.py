"""Unit tests for dashboard.lib.formatters.

These run without Streamlit — formatters are pure string functions.
"""

from __future__ import annotations

import math
from datetime import date

import pandas as pd
import pytest

from dashboard.lib.formatters import (
    DASH,
    delta_currency,
    delta_pct_points,
    fmt_count,
    fmt_currency,
    fmt_currency_range,
    fmt_date,
    fmt_date_range,
    fmt_kg,
    fmt_multiple,
    fmt_percent,
    fmt_percent_points,
    fmt_quantity,
    fmt_risk,
)


class TestCurrency:
    def test_basic(self):
        assert fmt_currency(1234) == "$1,234"
        assert fmt_currency(1234.56, cents=True) == "$1,234.56"

    def test_compact(self):
        assert fmt_currency(72_400, compact=True) == "$72.4K"
        assert fmt_currency(1_250_000, compact=True) == "$1.2M"

    def test_negative(self):
        assert fmt_currency(-500) == "-$500"
        assert fmt_currency(-15_000, compact=True) == "-$15.0K"

    def test_missing(self):
        assert fmt_currency(None) == DASH
        assert fmt_currency(float("nan")) == DASH
        assert fmt_currency(float("inf")) == DASH


class TestPercent:
    def test_basic(self):
        assert fmt_percent(0.142) == "14.2%"
        assert fmt_percent(0.142, decimals=0) == "14%"

    def test_signed(self):
        assert fmt_percent(0.05, signed=True) == "+5.0%"
        assert fmt_percent(-0.03, signed=True) == "-3.0%"

    def test_missing(self):
        assert fmt_percent(None) == DASH
        assert fmt_percent(math.nan) == DASH


class TestPercentPoints:
    def test_signed(self):
        assert fmt_percent_points(2.3) == "+2.3 pts"
        assert fmt_percent_points(-1.0) == "-1.0 pts"
        assert fmt_percent_points(0) == "0.0 pts"

    def test_missing(self):
        assert fmt_percent_points(None) == DASH


class TestKgQty:
    def test_kg_basic(self):
        assert fmt_kg(1234) == "1,234 kg"

    def test_kg_compact(self):
        assert fmt_kg(125_000, compact=True) == "125.0K kg"
        assert fmt_kg(2_400_000, compact=True) == "2.4M kg"

    def test_missing(self):
        assert fmt_kg(None) == DASH

    def test_quantity_with_unit(self):
        assert fmt_quantity(1234, "lots") == "1,234 lots"
        assert fmt_quantity(0) == "0"

    def test_count(self):
        assert fmt_count(1234) == "1,234"
        assert fmt_count(None) == DASH


class TestMultiple:
    def test_basic(self):
        assert fmt_multiple(27.4) == "27.4×"
        assert fmt_multiple(27.4, decimals=0) == "27×"

    def test_missing(self):
        assert fmt_multiple(None) == DASH


class TestDate:
    def test_pandas_timestamp(self):
        ts = pd.Timestamp("2026-01-15")
        assert fmt_date(ts) == "Jan 15, 2026"

    def test_string_input(self):
        assert fmt_date("2025-12-01") == "Dec 01, 2025"

    def test_missing(self):
        assert fmt_date(None) == DASH
        assert fmt_date(pd.NaT) == DASH

    def test_range(self):
        assert fmt_date_range(date(2025, 1, 1), date(2025, 6, 30)) == "Jan 01, 2025 – Jun 30, 2025"
        assert fmt_date_range(None, None) == DASH


class TestCurrencyRange:
    def test_basic(self):
        assert fmt_currency_range(60_000, 80_000, compact=True) == "$60.0K–$80.0K"

    def test_missing_both(self):
        assert fmt_currency_range(None, None) == DASH


class TestRiskCanonicalisation:
    @pytest.mark.parametrize("input_val,expected", [
        ("low", "Low"),
        ("LOW", "Low"),
        ("Med", "Medium"),
        ("medium", "Medium"),
        ("HIGH", "High"),
        ("critical", "Critical"),
        ("severe", "Critical"),
        (None, DASH),
    ])
    def test_canonical(self, input_val, expected):
        assert fmt_risk(input_val) == expected


class TestDeltaHelpers:
    def test_currency_delta_lower_is_better(self):
        text, good = delta_currency(80, 100, lower_is_better=True)
        assert text == "-20.0% vs baseline"
        assert good is True

    def test_currency_delta_higher_is_better(self):
        text, good = delta_currency(120, 100, lower_is_better=False)
        assert good is True

    def test_currency_delta_missing(self):
        text, good = delta_currency(None, 100)
        assert text is None and good is None

    def test_pct_points_higher_is_better(self):
        text, good = delta_pct_points(95, 92, higher_is_better=True)
        assert text == "+3.0 pts"
        assert good is True
