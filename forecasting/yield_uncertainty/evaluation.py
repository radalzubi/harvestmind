"""Proper scoring rules for probabilistic forecasts.

A probabilistic forecast cannot be judged by accuracy of its median. The
governing principle is Gneiting & Raftery's: maximise SHARPNESS SUBJECT TO
CALIBRATION. A narrow interval is worthless if it misses; a wide interval
is not virtuous merely because it contains the outcome. Only a *proper*
scoring rule rewards both correctly — one that is optimised by reporting
your true belief, so a forecaster cannot game it by hedging.

References
----------
Gneiting, T. & Raftery, A.E. (2007). "Strictly Proper Scoring Rules,
    Prediction, and Estimation." *JASA* 102(477):359-378.
    doi:10.1198/016214506000001437
Gneiting, T., Balabdaoui, F. & Raftery, A.E. (2007). "Probabilistic
    forecasts, calibration and sharpness." *JRSS-B* 69(2):243-268.
    doi:10.1111/j.1467-9868.2007.00587.x
Bracher, J., Ray, E.L., Gneiting, T. & Reich, N.G. (2021). "Evaluating
    epidemic forecasts in an interval format." *PLOS Computational
    Biology* 17(2):e1008618. doi:10.1371/journal.pcbi.1008618
    — the Weighted Interval Score, a quantile-format CRPS approximation.

Implemented here: pinball loss, interval score, WIS, sample CRPS, PIT,
coverage, and sharpness.
"""

from __future__ import annotations

import numpy as np


def pinball_loss(y: np.ndarray, q_pred: np.ndarray, level: float) -> float:
    """Quantile (pinball) loss at one level.

        L = mean( max( tau*(y - q), (tau-1)*(y - q) ) )

    Proper for the quantile: minimised in expectation by the true
    ``level``-quantile, and asymmetric so under- and over-prediction are
    penalised in the ratio the level implies.
    """
    y = np.asarray(y, dtype=float)
    q = np.asarray(q_pred, dtype=float)
    d = y - q
    return float(np.mean(np.maximum(level * d, (level - 1.0) * d)))


def mean_pinball(
    y: np.ndarray, quantile_preds: dict[float, np.ndarray],
) -> float:
    """Average pinball loss across a quantile grid."""
    if not quantile_preds:
        return float("nan")
    return float(np.mean([pinball_loss(y, p, lv)
                          for lv, p in quantile_preds.items()]))


def interval_score(
    y: np.ndarray, lo: np.ndarray, hi: np.ndarray, alpha: float,
) -> float:
    """Interval score for a central (1-alpha) interval.

        IS = (hi - lo)
             + (2/alpha)*(lo - y)*1{y < lo}
             + (2/alpha)*(y - hi)*1{y > hi}

    Width is penalised always; misses are penalised in proportion to how
    far outside they fall and how confident the interval claimed to be.
    Lower is better.
    """
    y = np.asarray(y, dtype=float)
    lo = np.asarray(lo, dtype=float)
    hi = np.asarray(hi, dtype=float)
    width = hi - lo
    below = (2.0 / alpha) * np.maximum(lo - y, 0.0)
    above = (2.0 / alpha) * np.maximum(y - hi, 0.0)
    return float(np.mean(width + below + above))


def weighted_interval_score(
    y: np.ndarray, quantile_preds: dict[float, np.ndarray],
) -> float:
    """Weighted Interval Score (Bracher et al. 2021).

        WIS = 1/(K + 1/2) * [ 1/2*|y - median| + sum_k (alpha_k/2)*IS_k ]

    A quantile-format approximation to CRPS that converges to it as the
    grid densifies — the right headline score when a model emits quantiles
    rather than a full distribution.
    """
    levels = sorted(quantile_preds)
    if not levels:
        return float("nan")
    y = np.asarray(y, dtype=float)

    median = quantile_preds.get(0.50)
    if median is None:
        median = quantile_preds[min(levels, key=lambda q: abs(q - 0.5))]
    total = 0.5 * np.abs(y - np.asarray(median, dtype=float))

    pairs = [(lo, hi) for lo in levels for hi in levels
             if lo < 0.5 < hi and abs((lo + hi) - 1.0) < 1e-9]
    k = 0
    for lo_lv, hi_lv in pairs:
        alpha = 2.0 * lo_lv
        lo = np.asarray(quantile_preds[lo_lv], dtype=float)
        hi = np.asarray(quantile_preds[hi_lv], dtype=float)
        width = hi - lo
        below = (2.0 / alpha) * np.maximum(lo - y, 0.0)
        above = (2.0 / alpha) * np.maximum(y - hi, 0.0)
        total = total + (alpha / 2.0) * (width + below + above)
        k += 1

    return float(np.mean(total / (k + 0.5)))


def crps_sample(y: float, samples: np.ndarray, fair: bool = True) -> float:
    """CRPS from an ensemble.

        CRPS = mean|X - y| - 0.5 * E|X - X'|

    The second term is computed in O(n log n) from the sorted sample via

        sum_i sum_j |x_i - x_j| = 2 * sum_i (2i - n - 1) * x_(i)

    rather than an O(n^2) double loop, so it stays usable at operational
    ensemble sizes.

    ``fair=True`` (default) uses the 2*M*(M-1) normalisation, excluding the
    self-distance terms. The naive 2*M^2 form is BIASED by ensemble size —
    a small ensemble scores better than it deserves, which would make an
    under-sampled scenario set look artificially good. Since we compare
    across configurations with different draw counts, the fair estimator is
    the correct default (Ferro 2014; discussed in the ensemble-verification
    literature).
    """
    x = np.sort(np.asarray(samples, dtype=float))
    n = x.size
    if n == 0:
        return float("nan")
    term1 = float(np.mean(np.abs(x - y)))
    if n == 1:
        return term1
    i = np.arange(1, n + 1)
    pair_sum = float(np.sum((2 * i - n - 1) * x) * 2.0)   # sum_i sum_j |xi-xj|
    denom = (n * (n - 1)) if fair else (n * n)
    return term1 - 0.5 * (pair_sum / denom)


def crps_ensemble(y: np.ndarray, samples: np.ndarray, fair: bool = True) -> float:
    """Mean CRPS over observations. ``samples`` is (n_obs, n_draws)."""
    y = np.asarray(y, dtype=float)
    s = np.asarray(samples, dtype=float)
    if s.ndim == 1:
        s = s.reshape(1, -1)
    return float(np.mean([crps_sample(float(y[i]), s[i], fair=fair)
                          for i in range(len(y))]))


def coverage_by_level(
    y: np.ndarray, quantile_preds: dict[float, np.ndarray],
) -> dict[str, float]:
    """Empirical coverage of each central interval, versus nominal."""
    y = np.asarray(y, dtype=float)
    levels = sorted(quantile_preds)
    out: dict[str, float] = {}
    for lo_lv in [lv for lv in levels if lv < 0.5]:
        hi_lv = 1.0 - lo_lv
        if hi_lv not in quantile_preds:
            continue
        lo = np.asarray(quantile_preds[lo_lv], dtype=float)
        hi = np.asarray(quantile_preds[hi_lv], dtype=float)
        nominal = hi_lv - lo_lv
        emp = float(((y >= lo) & (y <= hi)).mean()) if y.size else float("nan")
        key = f"{int(round(nominal * 100))}%"
        out[key] = round(emp, 4)
        out[f"{key}_nominal"] = round(nominal, 4)
        out[f"{key}_error"] = round(emp - nominal, 4)
    return out


def tail_coverage(
    y: np.ndarray, quantile_preds: dict[float, np.ndarray], level: float = 0.05,
) -> float:
    """Fraction of outcomes at or below the lower quantile.

    Should equal ``level``. Reported separately because the optimizer is
    asymmetrically exposed to supply coming in BELOW forecast: a p05 that
    is really a p15 causes shortfalls the plan never priced.
    """
    if level not in quantile_preds:
        return float("nan")
    y = np.asarray(y, dtype=float)
    q = np.asarray(quantile_preds[level], dtype=float)
    return float((y <= q).mean()) if y.size else float("nan")


def sharpness(quantile_preds: dict[float, np.ndarray], level: float = 0.80) -> float:
    """Mean central-interval width. Only meaningful alongside coverage."""
    tail = (1.0 - level) / 2.0
    levels = sorted(quantile_preds)
    lo_lv = min(levels, key=lambda q: abs(q - tail))
    hi_lv = min(levels, key=lambda q: abs(q - (1.0 - tail)))
    lo = np.asarray(quantile_preds[lo_lv], dtype=float)
    hi = np.asarray(quantile_preds[hi_lv], dtype=float)
    return float(np.mean(hi - lo))


def pit_values(y: np.ndarray, samples: np.ndarray) -> np.ndarray:
    """Probability Integral Transform values from an ensemble.

    PIT_i = F_i(y_i), estimated as the fraction of draws at or below the
    observation. Under a perfectly calibrated forecast these are Uniform
    on [0,1]. The histogram shape diagnoses the failure:

        U-shaped   -> too narrow (over-confident); outcomes keep landing
                      in the tails
        hump-shaped-> too wide (under-confident)
        sloped     -> biased
    """
    y = np.asarray(y, dtype=float)
    s = np.asarray(samples, dtype=float)
    if s.ndim == 1:
        s = s.reshape(1, -1)
    return np.array([float((s[i] <= y[i]).mean()) for i in range(len(y))])


def pit_uniformity(pit: np.ndarray, n_bins: int = 10) -> dict[str, float]:
    """Summarise PIT uniformity, with a plain reading of the shape."""
    p = np.asarray(pit, dtype=float)
    p = p[np.isfinite(p)]
    if p.size == 0:
        return {"status": "no_data"}
    counts, _ = np.histogram(p, bins=n_bins, range=(0.0, 1.0))
    expected = p.size / n_bins
    chi2 = float(np.sum((counts - expected) ** 2 / max(expected, 1e-9)))
    edge = float(((p < 0.1) | (p > 0.9)).mean())
    middle = float(((p > 0.4) & (p < 0.6)).mean())
    if edge > 0.30:
        shape = "U-shaped: intervals too narrow (over-confident)"
    elif middle > 0.35:
        shape = "hump-shaped: intervals too wide (under-confident)"
    elif abs(float(p.mean()) - 0.5) > 0.15:
        shape = "sloped: forecast is biased"
    else:
        shape = "approximately uniform: well calibrated"
    return {"chi2": round(chi2, 3), "mean": round(float(p.mean()), 4),
            "edge_mass": round(edge, 4), "middle_mass": round(middle, 4),
            "shape": shape}


def evaluate_forecasts(
    y: np.ndarray,
    quantile_preds: dict[float, np.ndarray],
    samples: np.ndarray | None = None,
) -> dict:
    """Full scorecard. Probabilistic metrics lead; point metrics follow."""
    y = np.asarray(y, dtype=float)
    med = quantile_preds.get(0.50)
    out: dict = {
        "n": int(y.size),
        "wis": round(weighted_interval_score(y, quantile_preds), 5),
        "mean_pinball": round(mean_pinball(y, quantile_preds), 5),
        "sharpness_80": round(sharpness(quantile_preds, 0.80), 5),
        "coverage": coverage_by_level(y, quantile_preds),
        "lower_tail_coverage_p05": round(tail_coverage(y, quantile_preds, 0.05), 4),
    }
    if med is not None:
        m = np.asarray(med, dtype=float)
        out["mae"] = round(float(np.mean(np.abs(y - m))), 5)
        out["rmse"] = round(float(np.sqrt(np.mean((y - m) ** 2))), 5)
        denom = float(np.mean(np.abs(y)))
        out["bias"] = round(float(np.mean(m - y)), 5)
        out["nrmse"] = (round(out["rmse"] / denom, 5) if denom > 1e-9 else None)
    if samples is not None:
        out["crps"] = round(crps_ensemble(y, samples), 5)
        out["pit"] = pit_uniformity(pit_values(y, samples))
    return out
