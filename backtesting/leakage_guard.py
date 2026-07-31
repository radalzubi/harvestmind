"""Leakage guard: enforces strict information cutoff in rolling-origin backtests.

All data access must go through LeakageGuard.get_data(cutoff_date).
Any attempt to access data past the cutoff raises LeakageError.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Union

import pandas as pd


class LeakageError(Exception):
    """Raised when backtesting code accesses data past the cutoff date."""


DateLike = Union[date, datetime, str, pd.Timestamp]


def _to_date(d: DateLike) -> date:
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    return pd.to_datetime(d).date()


class LeakageGuard:
    """Wraps a DataFrame and enforces a temporal cutoff on all reads.

    Usage:
        guard = LeakageGuard(df, date_col="week_start", cutoff=origin_date)
        safe_df = guard.get()
    """

    def __init__(
        self,
        df: pd.DataFrame,
        date_col: str,
        cutoff: DateLike,
        inclusive: bool = True,  # include rows on the cutoff date itself
    ) -> None:
        self._df = df
        self._date_col = date_col
        self._cutoff = _to_date(cutoff)
        self._inclusive = inclusive

    def get(self) -> pd.DataFrame:
        """Return DataFrame rows on or before the cutoff."""
        dates = pd.to_datetime(self._df[self._date_col]).dt.date
        if self._inclusive:
            mask = dates <= self._cutoff
        else:
            mask = dates < self._cutoff
        return self._df[mask].copy()

    def validate_no_leakage(self, result_df: pd.DataFrame, date_col: str) -> None:
        """Raise LeakageError if result_df contains any dates past the cutoff.

        Fails CLOSED: a missing date column is treated as a caller error, not a
        pass. Silently returning would disable the guard exactly when it should
        catch a differently-named/renamed date column carrying leaked dates.
        """
        if date_col not in result_df.columns:
            raise LeakageError(
                f"validate_no_leakage: date column {date_col!r} not in result "
                f"(columns={list(result_df.columns)}); cannot verify cutoff "
                f"{self._cutoff}."
            )
        future_mask = pd.to_datetime(result_df[date_col]).dt.date > self._cutoff
        if future_mask.any():
            bad_dates = result_df.loc[future_mask, date_col].unique()[:3]
            raise LeakageError(
                f"Leakage detected: result contains dates past cutoff {self._cutoff}: {bad_dates}"
            )

    @property
    def cutoff(self) -> date:
        return self._cutoff


def assert_no_future_data(df: pd.DataFrame, date_col: str, cutoff: DateLike) -> None:
    """Standalone check — raises LeakageError if any row is past the cutoff."""
    cutoff_date = _to_date(cutoff)
    dates = pd.to_datetime(df[date_col]).dt.date
    bad = dates[dates > cutoff_date]
    if len(bad) > 0:
        raise LeakageError(
            f"Future data detected past cutoff {cutoff_date}: "
            f"{sorted(bad.unique())[:5]}"
        )


def assert_dates_in_window(
    df: pd.DataFrame,
    date_col: str,
    window_start: DateLike,
    window_end: DateLike,
) -> None:
    """Raise LeakageError if any row falls outside [window_start, window_end].

    Symmetric counterpart to assert_no_future_data: catches both training-window
    leakage (date < window_start) AND post-horizon leakage (date > window_end).
    Use this on horizon-window slices like realized supply/demand to confirm
    the recourse simulator only sees data from the evaluation period.
    """
    if df.empty or date_col not in df.columns:
        return
    start_d = _to_date(window_start)
    end_d = _to_date(window_end)
    dates = pd.to_datetime(df[date_col]).dt.date
    pre = dates[dates < start_d]
    post = dates[dates > end_d]
    if len(pre) > 0 or len(post) > 0:
        raise LeakageError(
            f"Date leakage outside [{start_d}, {end_d}]: "
            f"pre={sorted(pre.unique())[:3]} post={sorted(post.unique())[:3]}"
        )
