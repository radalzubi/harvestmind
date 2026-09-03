"""Distinguishing one bad delivery from a regime shift.

Three small, transparent detectors, all one-pass and leakage-free by
construction (they only ever see the prefix of the series they are given):

  cusum        two-sided CUSUM on standardised deviations from a reference
               mean; flags when accumulated drift exceeds a threshold h.
  page_hinkley the classic drift test for a decrease (or increase) in mean.
  ewma         exponentially weighted level and variance, for "recent vs
               long-run" without a window edge.

Each returns the statistic path so a report can show WHEN evidence
accumulated, not just that it did.
"""

from __future__ import annotations

import math
import statistics as st
from dataclasses import dataclass, field


@dataclass
class Detection:
    detected: bool
    index: int | None                # first index at which the alarm fired
    statistic: float                 # final statistic
    threshold: float
    direction: str                   # "down" | "up" | "none"
    magnitude: float                 # estimated shift in the series' units
    path: list = field(default_factory=list)


def cusum(xs: list, reference_n: int = 8, k: float = 0.5, h: float = 4.0, z_clip: float = 4.0) -> Detection:
    """Two-sided CUSUM. The first ``reference_n`` points set mean and sd;
    k is the allowance (in sd), h the decision interval (in sd).

    Standardised deviations are clipped at ``z_clip`` and the reference sd
    is floored at 2% of the level, so ONE wild observation (a single failed
    delivery against a very steady history) cannot fire the alarm by
    itself: with the defaults a single point contributes at most 3.5 and
    the alarm needs a second consecutive bad one. That is the intended
    semantics: one bad delivery is an event, two in a row are evidence."""
    if len(xs) < reference_n + 2:
        return Detection(False, None, 0.0, h, "none", 0.0, [])
    ref = xs[:reference_n]
    mu = st.mean(ref)
    sd = max(st.pstdev(ref), abs(mu) * 0.02, 1e-9)
    sp = sn = 0.0
    path, first, direction = [], None, "none"
    for i, x in enumerate(xs[reference_n:], start=reference_n):
        z = max(-z_clip, min(z_clip, (x - mu) / sd))
        sp = max(0.0, sp + z - k)
        sn = max(0.0, sn - z - k)
        path.append(max(sp, sn))
        if first is None and (sp > h or sn > h):
            first, direction = i, ("up" if sp > h else "down")
    stat = max(sp, sn)
    post = xs[first:] if first is not None else xs[reference_n:]
    magnitude = (st.mean(post) - mu) if post else 0.0
    return Detection(first is not None, first, stat, h, direction if first is not None else "none",
                     magnitude, path)


def page_hinkley(xs: list, delta: float = 0.005, lam: float = 0.05, direction: str = "down",
                 min_n: int = 6) -> Detection:
    """Page–Hinkley for a mean decrease (direction='down') or increase."""
    if len(xs) < min_n:
        return Detection(False, None, 0.0, lam, "none", 0.0, [])
    mean = 0.0
    cum = 0.0
    ext = 0.0                      # running maximum of the statistic, kept for the path
    path, first = [], None
    for i, x in enumerate(xs):
        mean += (x - mean) / (i + 1)
        if direction == "down":
            cum += (mean - x) - delta          # positive when x falls below the running mean
        else:
            cum += (x - mean) - delta
        ext = max(ext, cum)
        path.append(cum)
        if first is None and i >= min_n - 1 and cum > lam:
            first = i
    magnitude = (st.mean(xs[first:]) - st.mean(xs[:first])) if first not in (None, 0) else 0.0
    return Detection(first is not None, first, path[-1] if path else 0.0, lam,
                     direction if first is not None else "none", magnitude, path)


def ewma(xs: list, alpha: float = 0.3) -> tuple[float, float]:
    """Exponentially weighted mean and sd of the series."""
    if not xs:
        return 0.0, 0.0
    m = xs[0]
    v = 0.0
    for x in xs[1:]:
        d = x - m
        m += alpha * d
        v = (1 - alpha) * (v + alpha * d * d)
    return float(m), float(math.sqrt(max(v, 0.0)))


def recent_vs_longrun(xs: list, recent: int = 4) -> dict:
    """The plainest drift measure: last ``recent`` vs everything before."""
    if len(xs) < recent + 4:
        return {"recent_mean": st.mean(xs) if xs else 0.0, "longrun_mean": st.mean(xs) if xs else 0.0,
                "shift": 0.0, "shift_sd": 0.0}
    rec, lr = xs[-recent:], xs[:-recent]
    sd = st.pstdev(lr) or 1e-9
    return {"recent_mean": st.mean(rec), "longrun_mean": st.mean(lr),
            "shift": st.mean(rec) - st.mean(lr), "shift_sd": (st.mean(rec) - st.mean(lr)) / sd}
