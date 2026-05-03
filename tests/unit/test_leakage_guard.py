"""Unit tests for the leakage guard."""

import pandas as pd
import pytest
from datetime import date

from backtesting.leakage_guard import LeakageGuard, LeakageError, assert_no_future_data


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "week_start": pd.date_range("2024-01-01", periods=10, freq="W-MON"),
        "value": range(10),
    })


def test_guard_excludes_future(sample_df):
    cutoff = date(2024, 1, 22)  # includes first 3 weeks
    guard = LeakageGuard(sample_df, "week_start", cutoff)
    result = guard.get()
    assert len(result) == 3
    assert all(pd.to_datetime(result["week_start"]).dt.date <= cutoff)


def test_guard_inclusive_cutoff(sample_df):
    cutoff = date(2024, 1, 8)
    guard = LeakageGuard(sample_df, "week_start", cutoff, inclusive=True)
    result = guard.get()
    assert len(result) == 1


def test_assert_no_future_data_raises(sample_df):
    cutoff = date(2024, 1, 8)
    with pytest.raises(LeakageError):
        assert_no_future_data(sample_df, "week_start", cutoff)


def test_assert_no_future_data_passes(sample_df):
    cutoff = date(2025, 1, 1)
    assert_no_future_data(sample_df, "week_start", cutoff)  # should not raise


def test_validate_no_leakage(sample_df):
    cutoff = date(2024, 1, 8)
    guard = LeakageGuard(sample_df, "week_start", cutoff)
    future_df = sample_df[sample_df["week_start"] > pd.Timestamp(cutoff)]
    with pytest.raises(LeakageError):
        guard.validate_no_leakage(future_df, "week_start")
