"""Unit tests for the leakage guard."""

import pandas as pd
import pytest
from datetime import date

from backtesting.leakage_guard import (
    LeakageGuard,
    LeakageError,
    assert_dates_in_window,
    assert_no_future_data,
)


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "week_start": pd.date_range("2024-01-01", periods=10, freq="W-MON"),
        "value": range(10),
    })


def test_guard_excludes_future(sample_df):
    # Sample dates: Jan 1, 8, 15, 22, 29, ... — cutoff Jan 22 inclusive → 4 rows
    cutoff = date(2024, 1, 22)
    guard = LeakageGuard(sample_df, "week_start", cutoff)
    result = guard.get()
    assert len(result) == 4
    assert all(pd.to_datetime(result["week_start"]).dt.date <= cutoff)


def test_guard_inclusive_cutoff(sample_df):
    # Cutoff Jan 8 inclusive → Jan 1 and Jan 8 = 2 rows
    cutoff = date(2024, 1, 8)
    guard = LeakageGuard(sample_df, "week_start", cutoff, inclusive=True)
    result = guard.get()
    assert len(result) == 2

    # Exclusive variant: only Jan 1 = 1 row
    guard_excl = LeakageGuard(sample_df, "week_start", cutoff, inclusive=False)
    assert len(guard_excl.get()) == 1


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


def test_assert_dates_in_window_passes(sample_df):
    # Sample dates: Jan 1, 8, 15, 22, 29, ...
    # Window Jan 8 → Jan 22 covers 3 rows
    window_df = sample_df[
        (sample_df["week_start"] >= pd.Timestamp("2024-01-08"))
        & (sample_df["week_start"] <= pd.Timestamp("2024-01-22"))
    ]
    assert_dates_in_window(window_df, "week_start", date(2024, 1, 8), date(2024, 1, 22))


def test_assert_dates_in_window_catches_leakage(sample_df):
    # All 10 rows include both pre- and post- dates outside Jan 8–22.
    with pytest.raises(LeakageError):
        assert_dates_in_window(sample_df, "week_start", date(2024, 1, 8), date(2024, 1, 22))


def test_assert_dates_in_window_empty_df_ok():
    empty = pd.DataFrame({"week_start": pd.to_datetime([])})
    # Should not raise
    assert_dates_in_window(empty, "week_start", date(2024, 1, 1), date(2024, 12, 31))
