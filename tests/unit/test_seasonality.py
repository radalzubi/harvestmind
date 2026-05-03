"""Unit tests for seasonality curves."""

import pytest
import numpy as np

from synthetic.seasonality import seasonal_index, enso_yield_adjustment


def test_seasonal_index_returns_positive():
    for week in range(1, 53):
        assert seasonal_index("summer_peak", week) >= 0


def test_seasonal_index_mean_near_one():
    """Mean of all weekly indices should be ≈ 1.0 (normalized)."""
    for stype in ("summer_peak", "spring_fall", "year_round", "winter_dip"):
        values = [seasonal_index(stype, w) for w in range(1, 53)]
        assert abs(np.mean(values) - 1.0) < 0.05, f"{stype} mean = {np.mean(values)}"


def test_summer_peak_peaks_in_summer():
    summer_avg = np.mean([seasonal_index("summer_peak", w) for w in range(24, 36)])
    winter_avg = np.mean([seasonal_index("summer_peak", w) for w in [1, 2, 51, 52]])
    assert summer_avg > winter_avg


def test_enso_leafy_green_la_nina():
    adj = enso_yield_adjustment("la_nina", "leafy_green")
    assert adj < 1.0  # La Niña hurts leafy greens


def test_enso_allium_la_nina():
    adj = enso_yield_adjustment("la_nina", "allium")
    assert adj > 1.0  # La Niña helps alliums


def test_enso_neutral_is_one():
    for cat in ("leafy_green", "tomato", "pepper", "allium", "other"):
        assert enso_yield_adjustment("neutral", cat) == 1.0


def test_enso_unknown_returns_one():
    assert enso_yield_adjustment(None, "leafy_green") == 1.0
    assert enso_yield_adjustment("moderate_el_nino", "other") == 1.0
