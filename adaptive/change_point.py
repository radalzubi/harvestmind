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
    onset: int | None = None         # start of the CURRENT excursion (last reset before the final statistic)
    active: bool = False             # statistic above threshold at the end of the series


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
    reset_p = reset_n = reference_n - 1           # last index at which each side was zero
    for i, x in enumerate(xs[reference_n:], start=reference_n):
        z = max(-z_clip, min(z_clip, (x - mu) / sd))
        sp = max(0.0, sp + z - k)
        sn = max(0.0, sn - z - k)
        if sp == 0.0:
            reset_p = i
        if sn == 0.0:
            reset_n = i
        path.append(max(sp, sn))
        if first is None and (sp > h or sn > h):
            first, direction = i, ("up" if sp > h else "down")
    stat = max(sp, sn)
    active = stat > h
    # The change-point estimate is the start of the excursion that is
    # currently above threshold (the classic CUSUM onset estimator), not the
    # first index the alarm ever fired: a noise excursion months ago must
    # not date a shift that started last month.
    if active:
        onset = (reset_p if sp >= sn else reset_n) + 1
        cur_dir = "up" if sp >= sn else "down"
    else:
        onset, cur_dir = None, "none"
    post = xs[onset:] if onset is not None else (xs[first:] if first is not None else xs[reference_n:])
    magnitude = (st.mean(post) - mu) if post else 0.0
    return Detection(first is not None, first, stat, h, cur_dir if active else (direction if first is not None else "none"),
                     magnitude, path, onset, active)


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


def recent_shift_onset(xs: list, window: int = 16, min_post: int = 3, t_threshold: float = 3.0,
                       ref_len: int = 26) -> dict:
    """Date the MOST RECENT change in mean. Scanning from the newest
    candidate onset tau backwards (leaving at least ``min_post`` points
    after it), compare the mean after tau with the mean of the ``ref_len``
    points before it by a two-sample t statistic, and take the first
    (newest) tau that clears ``t_threshold``. Newest-first matters: the
    maximal statistic favours older onsets simply because they have more
    post points, and a shock that ended two weeks ago must read as a
    recent downward shift, not as the older upward one. Unlike the CUSUM
    alarm index this is not fooled by a slow drift either."""
    n = len(xs)
    if n < ref_len // 2 + min_post + 2:
        return {"onset": None, "age": None, "t": 0.0, "shift": 0.0}
    strongest = (0.0, None, 0.0)
    for tau in range(n - min_post, max(ref_len // 2, n - window) - 1, -1):
        post = xs[tau:]
        pre = xs[max(0, tau - ref_len):tau]
        if len(post) < min_post or len(pre) < 4:
            continue
        mp, mq = st.mean(post), st.mean(pre)
        sp = st.pstdev(pre) or (abs(mq) * 0.02 + 1e-9)
        t = (mp - mq) / (sp * math.sqrt(1.0 / len(post) + 1.0 / len(pre)))
        if abs(t) >= t_threshold:
            return {"onset": tau, "age": n - tau, "t": float(t), "shift": float(mp - mq)}
        if abs(t) > abs(strongest[0]):
            strongest = (t, tau, mp - mq)
    return {"onset": None, "age": None, "t": float(strongest[0]), "shift": float(strongest[2])}
