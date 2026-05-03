"""Intermittent demand forecasting: Croston 1972, SBA (Syntetos-Boylan 2005), TSB (Teunter-Syntetos-Babai 2011).

Implemented from scratch using numpy — no statsforecast dependency.
All three models produce a point forecast (expected demand per period) and
an empirical prediction interval via bootstrap.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass


@dataclass
class IntermittentForecast:
    mean: float          # expected demand per period
    std: float           # standard deviation estimate
    lower_80: float
    upper_80: float
    lower_95: float
    upper_95: float
    model: str
    demand_rate: float   # estimated probability of non-zero demand in a period
    demand_size: float   # estimated mean non-zero demand size


# ---------------------------------------------------------------------------
# Croston 1972
# ---------------------------------------------------------------------------

def croston(series: np.ndarray, alpha: float = 0.15, horizon: int = 1) -> IntermittentForecast:
    """Classic Croston method.

    Maintains two exponential smoothers:
      z_t = smoothed non-zero demand sizes
      p_t = smoothed inter-arrival intervals (in periods)
    Forecast = z_t / p_t
    """
    series = np.asarray(series, dtype=float)
    n = len(series)
    if n == 0:
        return _zero_forecast("croston")

    # Initialize
    non_zero = series[series > 0]
    z = float(non_zero[0]) if len(non_zero) > 0 else 1.0
    # Find first inter-arrival interval
    first_nz = np.argmax(series > 0)
    p = float(first_nz + 1) if first_nz < n else float(n)

    for t in range(1, n):
        if series[t] > 0:
            z = alpha * series[t] + (1 - alpha) * z
            p = alpha * 1.0 + (1 - alpha) * p  # inter-arrival = 1 at demand occurrence
        # else: z and p unchanged

    forecast_mean = z / p if p > 0 else 0.0
    std = _bootstrap_std(series, "croston", alpha, horizon)

    return IntermittentForecast(
        mean=max(0.0, forecast_mean * horizon),
        std=std * np.sqrt(horizon),
        lower_80=max(0.0, forecast_mean * horizon - 1.282 * std * np.sqrt(horizon)),
        upper_80=forecast_mean * horizon + 1.282 * std * np.sqrt(horizon),
        lower_95=max(0.0, forecast_mean * horizon - 1.960 * std * np.sqrt(horizon)),
        upper_95=forecast_mean * horizon + 1.960 * std * np.sqrt(horizon),
        model="croston",
        demand_rate=1.0 / p if p > 0 else 0.0,
        demand_size=z,
    )


# ---------------------------------------------------------------------------
# SBA: Syntetos-Boylan Approximation (2005)
# ---------------------------------------------------------------------------

def sba(series: np.ndarray, alpha: float = 0.15, horizon: int = 1) -> IntermittentForecast:
    """Syntetos-Boylan Approximation.

    Corrects Croston's positive bias with a factor (1 - alpha/2).
    Forecast = (1 - alpha/2) * z / p
    """
    series = np.asarray(series, dtype=float)
    n = len(series)
    if n == 0:
        return _zero_forecast("sba")

    non_zero = series[series > 0]
    z = float(non_zero[0]) if len(non_zero) > 0 else 1.0
    first_nz = np.argmax(series > 0)
    p = float(first_nz + 1) if first_nz < n else float(n)

    for t in range(1, n):
        if series[t] > 0:
            z = alpha * series[t] + (1 - alpha) * z
            p = alpha * 1.0 + (1 - alpha) * p

    bias_correction = 1.0 - alpha / 2.0
    forecast_mean = bias_correction * z / p if p > 0 else 0.0
    std = _bootstrap_std(series, "sba", alpha, horizon)

    return IntermittentForecast(
        mean=max(0.0, forecast_mean * horizon),
        std=std * np.sqrt(horizon),
        lower_80=max(0.0, forecast_mean * horizon - 1.282 * std * np.sqrt(horizon)),
        upper_80=forecast_mean * horizon + 1.282 * std * np.sqrt(horizon),
        lower_95=max(0.0, forecast_mean * horizon - 1.960 * std * np.sqrt(horizon)),
        upper_95=forecast_mean * horizon + 1.960 * std * np.sqrt(horizon),
        model="sba",
        demand_rate=1.0 / p if p > 0 else 0.0,
        demand_size=z,
    )


# ---------------------------------------------------------------------------
# TSB: Teunter-Syntetos-Babai (2011)
# ---------------------------------------------------------------------------

def tsb(
    series: np.ndarray,
    alpha: float = 0.15,
    beta: float = 0.10,
    horizon: int = 1,
) -> IntermittentForecast:
    """TSB method: tracks demand probability separately from demand size.

    Allows the demand probability to decay when demand is absent, making it
    better for items that can become obsolete or highly seasonal.

    State:
      p_t = demand probability (updated every period)
      z_t = expected demand size (updated only on non-zero periods)
    Forecast = p_t * z_t
    """
    series = np.asarray(series, dtype=float)
    n = len(series)
    if n == 0:
        return _zero_forecast("tsb")

    non_zero = series[series > 0]
    z = float(non_zero[0]) if len(non_zero) > 0 else 1.0
    n_nz = len(non_zero)
    p = n_nz / n if n > 0 else 0.5  # initial demand probability

    for t in range(1, n):
        if series[t] > 0:
            p = beta * 1.0 + (1 - beta) * p   # demand occurred
            z = alpha * series[t] + (1 - alpha) * z
        else:
            p = beta * 0.0 + (1 - beta) * p   # demand did not occur

    forecast_mean = p * z
    std = _bootstrap_std(series, "tsb", alpha, horizon)

    return IntermittentForecast(
        mean=max(0.0, forecast_mean * horizon),
        std=std * np.sqrt(horizon),
        lower_80=max(0.0, forecast_mean * horizon - 1.282 * std * np.sqrt(horizon)),
        upper_80=forecast_mean * horizon + 1.282 * std * np.sqrt(horizon),
        lower_95=max(0.0, forecast_mean * horizon - 1.960 * std * np.sqrt(horizon)),
        upper_95=forecast_mean * horizon + 1.960 * std * np.sqrt(horizon),
        model="tsb",
        demand_rate=p,
        demand_size=z,
    )


# ---------------------------------------------------------------------------
# Model selection
# ---------------------------------------------------------------------------

def select_and_fit(
    series: np.ndarray,
    alpha: float = 0.15,
    horizon: int = 1,
) -> IntermittentForecast:
    """Auto-select best intermittent model based on CV² and ADI.

    ADI = Average Demand Interval (mean inter-arrival)
    CV² = squared coefficient of variation of non-zero demand sizes

    Syntetos et al. (2005) classification:
      ADI < 1.32, CV² < 0.49 → Croston (smooth)
      ADI ≥ 1.32, CV² < 0.49 → SBA
      ADI < 1.32, CV² ≥ 0.49 → Croston
      ADI ≥ 1.32, CV² ≥ 0.49 → TSB (lumpy)
    """
    series = np.asarray(series, dtype=float)
    non_zero = series[series > 0]

    if len(non_zero) < 3:
        return sba(series, alpha, horizon)

    # ADI: average number of periods between demands
    intervals = []
    last = 0
    for i, v in enumerate(series):
        if v > 0:
            intervals.append(i - last)
            last = i
    adi = float(np.mean(intervals)) if intervals else float(len(series))

    cv2 = float(np.var(non_zero) / np.mean(non_zero) ** 2) if np.mean(non_zero) > 0 else 0.0

    if adi >= 1.32 and cv2 >= 0.49:
        return tsb(series, alpha=alpha, beta=0.10, horizon=horizon)
    elif adi >= 1.32:
        return sba(series, alpha=alpha, horizon=horizon)
    else:
        return croston(series, alpha=alpha, horizon=horizon)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _croston_point(series: np.ndarray, alpha: float) -> float:
    """Croston point estimate without bootstrap (used inside bootstrap loop)."""
    non_zero = series[series > 0]
    z = float(non_zero[0]) if len(non_zero) > 0 else 1.0
    first_nz = np.argmax(series > 0)
    p = float(first_nz + 1) if first_nz < len(series) else float(len(series))
    for t in range(1, len(series)):
        if series[t] > 0:
            z = alpha * series[t] + (1 - alpha) * z
            p = alpha * 1.0 + (1 - alpha) * p
    return max(0.0, z / p if p > 0 else 0.0)


def _sba_point(series: np.ndarray, alpha: float) -> float:
    return _croston_point(series, alpha) * (1.0 - alpha / 2.0)


def _tsb_point(series: np.ndarray, alpha: float, beta: float) -> float:
    non_zero = series[series > 0]
    z = float(non_zero[0]) if len(non_zero) > 0 else 1.0
    n = len(series)
    p = len(non_zero) / n if n > 0 else 0.5
    for t in range(1, n):
        if series[t] > 0:
            p = beta * 1.0 + (1 - beta) * p
            z = alpha * series[t] + (1 - alpha) * z
        else:
            p = beta * 0.0 + (1 - beta) * p
    return max(0.0, p * z)


def _bootstrap_std(
    series: np.ndarray,
    model_name: str,
    alpha: float,
    horizon: int,
    n_boot: int = 200,
    rng_seed: int = 42,
) -> float:
    """Bootstrap forecast standard deviation by re-sampling the series."""
    rng = np.random.default_rng(rng_seed)
    n = len(series)
    if n < 6:
        nz = series[series > 0]
        return float(np.std(nz)) if len(nz) > 1 else 1.0

    boot_means = []
    for _ in range(n_boot):
        sample = rng.choice(series, size=n, replace=True)
        if model_name == "croston":
            val = _croston_point(sample, alpha) * horizon
        elif model_name == "sba":
            val = _sba_point(sample, alpha) * horizon
        else:
            val = _tsb_point(sample, alpha, 0.10) * horizon
        boot_means.append(val)

    return float(np.std(boot_means)) if boot_means else 1.0


def _zero_forecast(model: str) -> IntermittentForecast:
    return IntermittentForecast(
        mean=0.0, std=0.0,
        lower_80=0.0, upper_80=0.0,
        lower_95=0.0, upper_95=0.0,
        model=model,
        demand_rate=0.0, demand_size=0.0,
    )
