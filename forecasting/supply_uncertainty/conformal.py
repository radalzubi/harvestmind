"""Conformalized Quantile Regression — turning asserted intervals into
intervals with a coverage guarantee.

THE PROBLEM
-----------
A quantile model trained to predict the 5th and 95th percentiles will
generally not cover 90% of future outcomes. It covers whatever its
training data and its own misspecification permit — often 70-80% when
sold as 90%. An optimizer fed those intervals commits as though it faces
less risk than it does, and the error is systematically in the dangerous
direction.

THE METHOD
----------
Romano, Y., Patterson, E. & Candès, E. (2019). "Conformalized Quantile
Regression." *Advances in Neural Information Processing Systems* 32.
https://arxiv.org/abs/1905.03222

Split the data. Fit quantile regressors q_lo, q_hi on the training part.
On a held-out calibration set compute the conformity score

    E_i = max{ q_lo(x_i) - y_i ,  y_i - q_hi(x_i) }

which is positive when the true value fell outside the predicted interval
and negative when it fell comfortably inside. Take

    Q = the ceil((n+1)(1-alpha)) / n empirical quantile of {E_i}

and return the widened interval [q_lo(x) - Q, q_hi(x) + Q].

The guarantee is finite-sample and distribution-free:

    P( Y in C(X) ) >= 1 - alpha

requiring only that calibration and test points be EXCHANGEABLE. Note
what it does not require: no assumption that the quantile model is any
good. A poor model yields wide intervals; it does not yield wrong
coverage. That property is what makes this worth the extra machinery.

Note also that Q may be NEGATIVE, which tightens an over-wide interval.
That is correct behaviour, not a bug to clamp away.

WHERE THE GUARANTEE BREAKS, AND WHAT WE DO ABOUT IT
---------------------------------------------------
Exchangeability fails under temporal drift, and crop-yield data drifts:
climate trends, cultivar turnover, changed practice. A random calibration
split would also leak the future into calibration.

Two mitigations, both implemented here:

* ``split_time_aware`` calibrates on the most recent block, never a random
  subset, so calibration reflects the period nearest the forecast.
* ``MondrianConformalCalibrator`` calibrates per group (crop, region,
  horizon bucket), giving approximate group-conditional coverage rather
  than only marginal coverage. Marginal coverage can be met while a
  specific crop is badly under-covered, and an operator only ever
  experiences one group at a time.

Neither restores the theorem under drift. Coverage is therefore always
MEASURED on held-out data and reported, never asserted from the theory
alone.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np


def conformity_scores(
    y: np.ndarray, q_lo: np.ndarray, q_hi: np.ndarray,
) -> np.ndarray:
    """CQR score E_i = max{q_lo - y, y - q_hi}."""
    y = np.asarray(y, dtype=float)
    lo = np.asarray(q_lo, dtype=float)
    hi = np.asarray(q_hi, dtype=float)
    return np.maximum(lo - y, y - hi)


def conformal_quantile(scores: np.ndarray, alpha: float) -> float:
    """The finite-sample-corrected score quantile.

    Uses the ceil((n+1)(1-alpha))/n empirical quantile — the (n+1)
    correction is what makes the coverage guarantee exact rather than
    asymptotic. With too few points the required order statistic exceeds
    the sample and the method cannot guarantee the level; we return
    +inf so the caller must fall back rather than quietly under-cover.
    """
    s = np.asarray(scores, dtype=float)
    s = s[np.isfinite(s)]
    n = s.size
    if n == 0:
        return float("inf")
    k = math.ceil((n + 1) * (1.0 - alpha))
    if k > n:
        # e.g. alpha=0.1 needs n >= 9. Honest failure, not silent.
        return float("inf")
    return float(np.sort(s)[k - 1])


def min_calibration_size(alpha: float) -> int:
    """Smallest calibration set that can support level ``alpha``.

    Requires ceil((n+1)(1-alpha)) <= n, i.e. n >= ceil(1/alpha) - 1.
    """
    return max(1, math.ceil(1.0 / alpha) - 1)


def split_time_aware(
    n: int, calibration_fraction: float = 0.3,
) -> tuple[np.ndarray, np.ndarray]:
    """Chronological split: earliest rows train, most recent calibrate.

    Assumes the input is already sorted oldest-first. A random split would
    both leak future information into calibration and calibrate against a
    period the forecast will never face.
    """
    if n < 2:
        return np.arange(n), np.array([], dtype=int)
    n_cal = max(1, int(round(n * calibration_fraction)))
    n_cal = min(n_cal, n - 1)
    idx = np.arange(n)
    return idx[: n - n_cal], idx[n - n_cal:]


@dataclass
class ConformalCalibrator:
    """Marginal split-conformal calibration of a predicted interval."""

    alpha: float = 0.10
    correction: float = float("nan")
    n_calibration: int = 0
    fitted: bool = False
    insufficient_data: bool = False

    def fit(self, y: np.ndarray, q_lo: np.ndarray, q_hi: np.ndarray) -> "ConformalCalibrator":
        scores = conformity_scores(y, q_lo, q_hi)
        self.n_calibration = int(np.isfinite(scores).sum())
        q = conformal_quantile(scores, self.alpha)
        if not math.isfinite(q):
            self.insufficient_data = True
            self.correction = float("nan")
            self.fitted = False
            return self
        self.correction = q
        self.fitted = True
        self.insufficient_data = False
        return self

    def apply(self, q_lo: np.ndarray, q_hi: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Widen (or tighten) an interval by the calibrated correction.

        Lower bounds are floored at zero: a negative supply quantity is
        meaningless. This does mean the guarantee is one-sided-conservative
        for groups whose lower bound would have gone negative.
        """
        lo = np.asarray(q_lo, dtype=float)
        hi = np.asarray(q_hi, dtype=float)
        if not self.fitted:
            return lo, hi
        return np.maximum(lo - self.correction, 0.0), hi + self.correction


@dataclass
class MondrianConformalCalibrator:
    """Group-conditional (Mondrian) conformal calibration.

    Calibrates a separate correction per group — crop, region, horizon
    bucket, data tier. Marginal coverage can look healthy while one crop
    is badly under-covered; an operator planning a single crop experiences
    that group's coverage, not the average.

    Groups too small to support the level fall back to the pooled marginal
    correction, and that fallback is recorded per group rather than hidden.
    """

    alpha: float = 0.10
    min_group_size: int = 0
    group_corrections: dict = field(default_factory=dict)
    pooled: ConformalCalibrator | None = None
    fallback_groups: set = field(default_factory=set)

    def __post_init__(self):
        if self.min_group_size <= 0:
            self.min_group_size = min_calibration_size(self.alpha)

    def fit(
        self, y: np.ndarray, q_lo: np.ndarray, q_hi: np.ndarray, groups: np.ndarray,
    ) -> "MondrianConformalCalibrator":
        y = np.asarray(y, dtype=float)
        q_lo = np.asarray(q_lo, dtype=float)
        q_hi = np.asarray(q_hi, dtype=float)
        groups = np.asarray(groups)

        self.pooled = ConformalCalibrator(alpha=self.alpha).fit(y, q_lo, q_hi)
        self.group_corrections = {}
        self.fallback_groups = set()

        for g in np.unique(groups):
            m = groups == g
            if int(m.sum()) < self.min_group_size:
                self.fallback_groups.add(g)
                continue
            cal = ConformalCalibrator(alpha=self.alpha).fit(y[m], q_lo[m], q_hi[m])
            if cal.fitted:
                self.group_corrections[g] = cal
            else:
                self.fallback_groups.add(g)
        return self

    def correction_for(self, group) -> float:
        cal = self.group_corrections.get(group)
        if cal is not None and cal.fitted:
            return cal.correction
        if self.pooled is not None and self.pooled.fitted:
            return self.pooled.correction
        return float("nan")

    def apply(
        self, q_lo: np.ndarray, q_hi: np.ndarray, groups: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        lo = np.asarray(q_lo, dtype=float).copy()
        hi = np.asarray(q_hi, dtype=float).copy()
        groups = np.asarray(groups)
        for i, g in enumerate(groups):
            c = self.correction_for(g)
            if math.isfinite(c):
                lo[i] = max(lo[i] - c, 0.0)
                hi[i] = hi[i] + c
        return lo, hi

    @property
    def is_usable(self) -> bool:
        return bool(self.group_corrections) or bool(
            self.pooled and self.pooled.fitted)


def empirical_coverage(
    y: np.ndarray, lo: np.ndarray, hi: np.ndarray,
) -> float:
    """Fraction of outcomes inside the interval — the number that matters.

    Coverage is always measured, never inferred from the theorem, because
    the theorem's exchangeability assumption is exactly what crop data
    violates.
    """
    y = np.asarray(y, dtype=float)
    lo = np.asarray(lo, dtype=float)
    hi = np.asarray(hi, dtype=float)
    if y.size == 0:
        return float("nan")
    return float(((y >= lo) & (y <= hi)).mean())
