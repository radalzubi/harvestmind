"""Online change detectors for review-by-review demand adaptation.

Every detector answers one question with the same contract as the frozen CUSUM: given the
history so far, at which index does the current demand regime start? Zero means no change.
A single abnormal observation never moves the origin; a genuine level shift should move it
within two or three observations. The detectors are compared on synthetic surge patterns by
scripts/study_zaad_surge.py; the winner is chosen on development seeds and confirmed on
validation seeds, never on the frozen benchmark evidence.
"""
from __future__ import annotations

from collections.abc import Callable
import math

import numpy as np

MIN_HISTORY = 16
BASE_WINDOW = 26


def _scale(base: np.ndarray) -> float:
    return max(float(np.std(base)), abs(float(np.mean(base))) * .1, 1.)


def page_hinkley_origin(y: np.ndarray, delta: float = .5, threshold: float = 4.5) -> int:
    """Two-sided Page-Hinkley test on standardized residuals with the drift point as origin.

    Unlike the CUSUM's fixed "one observation before the alarm" origin, Page-Hinkley dates the
    change from the start of the run of positive evidence after the cumulative deviation last
    touched its extreme. The alarm still needs at least two observations of accumulated
    evidence, so one spike cannot trigger it.
    """
    origin = 0
    up_sum, up_min, up_start = 0., 0., 0
    down_sum, down_min, down_start = 0., 0., 0
    for t in range(MIN_HISTORY, len(y)):
        base = y[max(origin, t - BASE_WINDOW):t]
        if len(base) < 8:
            continue
        z = float(np.clip((y[t] - np.mean(base)) / _scale(base), -3, 3))
        up_sum += z - delta
        if z - delta <= 0:
            up_start = t + 1          # evidence run for an upward shift begins after this point
        if up_sum < up_min:
            up_min = up_sum
        down_sum += -z - delta
        if -z - delta <= 0:
            down_start = t + 1
        if down_sum < down_min:
            down_min = down_sum
        if up_sum - up_min > threshold and t - up_start >= 1:
            origin = max(0, up_start)
            up_sum = up_min = down_sum = down_min = 0.
            up_start = down_start = t + 1
        elif down_sum - down_min > threshold and t - down_start >= 1:
            origin = max(0, down_start)
            up_sum = up_min = down_sum = down_min = 0.
            up_start = down_start = t + 1
    return origin


def bocpd_origin(y: np.ndarray, hazard: float = 1 / 40, mass: float = .6, min_run: int = 2) -> int:
    """Bayesian online change-point detection (Adams and MacKay) with a Gaussian mean model.

    The observation variance is taken from the pre-change base window, the mean has a Normal
    prior centred on that base. The origin moves to the maximum-a-posteriori run length only
    when that run is at least min_run observations old and carries more than the required
    posterior mass, which is what stops a single outlier from resetting the level.
    """
    n = len(y)
    if n <= MIN_HISTORY:
        return 0
    origin = 0
    base = y[:MIN_HISTORY]
    # Count-like demand: the variance is at least the mean, so a Poisson-noisy series measured
    # against a tighter history does not read as a change every other week.
    var = max(float(np.var(base)), abs(float(np.mean(base))), (abs(float(np.mean(base))) * .1) ** 2, 1.)
    mu0, kappa0 = float(np.mean(base)), 1.
    # Run-length posterior; sufficient statistics per run length.
    r = np.array([1.])
    sums = np.array([0.])
    counts = np.array([0.])
    for t in range(MIN_HISTORY, n):
        x = float(y[t])
        # Predictive for each run length: mean of prior updated by that run's observations.
        post_kappa = kappa0 + counts
        post_mu = (kappa0 * mu0 + sums) / post_kappa
        pred_var = var * (1 + 1 / post_kappa)
        like = np.exp(-.5 * (x - post_mu) ** 2 / pred_var) / np.sqrt(2 * math.pi * pred_var)
        growth = r * like * (1 - hazard)
        change = float(np.sum(r * like * hazard))
        r = np.concatenate(([change], growth))
        total = float(np.sum(r))
        r = r / total if total > 0 else np.concatenate(([1.], np.zeros(len(r) - 1)))
        sums = np.concatenate(([0.], sums + x))
        counts = np.concatenate(([0.], counts + 1))
        best = int(np.argmax(r))
        recent = float(np.sum(r[:best + 1]))
        full = len(r) - 1   # run length covering every observation after the base window
        # A MAP run shorter than the full run means a change happened inside the window.
        if min_run <= best < full and recent >= mass:
            candidate = t - best + 1   # run length k covers the last k observations including y[t]
            # A new run whose level is not materially different from the base is an outlier's
            # aftermath, not a regime change; leave the origin alone.
            reference = y[max(origin, candidate - BASE_WINDOW):candidate]
            threshold = max(_scale(reference), math.sqrt(abs(float(np.mean(reference))))) if len(reference) else 0.
            material = abs(float(np.mean(y[candidate:t + 1])) - float(np.mean(reference))) > threshold
            if candidate > origin and material:
                origin = candidate
    return origin


DETECTORS: dict[str, Callable[[np.ndarray], int]] = {"page_hinkley": page_hinkley_origin, "bocpd": bocpd_origin}
