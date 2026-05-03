"""Forecast accuracy metrics: MASE, RMSSE, coverage, winkler score."""

from __future__ import annotations

import numpy as np
import pandas as pd


def mase(actual: np.ndarray, forecast: np.ndarray, seasonal_period: int = 1) -> float:
    """Mean Absolute Scaled Error (Hyndman & Koehler 2006)."""
    actual = np.asarray(actual, dtype=float)
    forecast = np.asarray(forecast, dtype=float)
    n = len(actual)
    if n <= seasonal_period:
        return float("nan")
    naive_errors = np.abs(actual[seasonal_period:] - actual[:-seasonal_period])
    scale = naive_errors.mean()
    if scale == 0:
        return float("nan")
    return float(np.abs(actual - forecast).mean() / scale)


def rmsse(actual: np.ndarray, forecast: np.ndarray, seasonal_period: int = 1) -> float:
    """Root Mean Squared Scaled Error (M5 competition metric)."""
    actual = np.asarray(actual, dtype=float)
    forecast = np.asarray(forecast, dtype=float)
    n = len(actual)
    if n <= seasonal_period:
        return float("nan")
    naive_sq_errors = (actual[seasonal_period:] - actual[:-seasonal_period]) ** 2
    scale = naive_sq_errors.mean()
    if scale == 0:
        return float("nan")
    return float(np.sqrt(((actual - forecast) ** 2).mean() / scale))


def interval_coverage(actual: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> float:
    """Fraction of actuals falling within [lower, upper]."""
    actual = np.asarray(actual, dtype=float)
    lower = np.asarray(lower, dtype=float)
    upper = np.asarray(upper, dtype=float)
    return float(((actual >= lower) & (actual <= upper)).mean())


def winkler_score(actual: np.ndarray, lower: np.ndarray, upper: np.ndarray, alpha: float) -> float:
    """Winkler (1972) interval score. Lower is better."""
    actual = np.asarray(actual, dtype=float)
    lower = np.asarray(lower, dtype=float)
    upper = np.asarray(upper, dtype=float)
    width = upper - lower
    penalty_low = (2 / alpha) * (lower - actual) * (actual < lower)
    penalty_high = (2 / alpha) * (actual - upper) * (actual > upper)
    return float((width + penalty_low + penalty_high).mean())


def evaluate_forecasts(
    actual_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    group_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Compute all metrics grouped by group_cols.

    actual_df  : [product_id, buyer_id, week_start, qty_ordered_kg]
    forecast_df: [product_id, buyer_id, week_start, forecast_kg, lower_80, upper_80, lower_95, upper_95]
    """
    merge_cols = ["product_id", "buyer_id", "week_start"]
    df = actual_df.merge(forecast_df, on=merge_cols, how="inner")

    if group_cols is None:
        group_cols = ["product_id"]

    rows = []
    for keys, grp in df.groupby(group_cols):
        y = grp["qty_ordered_kg"].values
        yhat = grp["forecast_kg"].values
        row = dict(zip(group_cols, keys if isinstance(keys, tuple) else [keys]))
        row["n"] = len(y)
        row["mase"] = mase(y, yhat, seasonal_period=52)
        row["rmsse"] = rmsse(y, yhat, seasonal_period=52)
        if "lower_80" in grp.columns:
            row["coverage_80"] = interval_coverage(y, grp["lower_80"].values, grp["upper_80"].values)
            row["winkler_80"] = winkler_score(y, grp["lower_80"].values, grp["upper_80"].values, alpha=0.20)
        if "lower_95" in grp.columns:
            row["coverage_95"] = interval_coverage(y, grp["lower_95"].values, grp["upper_95"].values)
            row["winkler_95"] = winkler_score(y, grp["lower_95"].values, grp["upper_95"].values, alpha=0.05)
        row["bias_pct"] = float((yhat - y).sum() / (y.sum() + 1e-9) * 100)
        rows.append(row)

    return pd.DataFrame(rows)
