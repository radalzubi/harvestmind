"""Are the optimizer's demand scenarios calibrated against real history?

WHY THIS IS A SEPARATE TEST. A stochastic program is only as good as the
distribution it integrates over. If the scenario set is miscalibrated the
optimizer solves the wrong problem precisely, and a cost comparison will
not reveal it: both the SP and its deterministic twin can look reasonable
while the SP's claimed advantage rests on a distribution that never
matched the world.

WHAT IS SCORED. The exact generator used inside
``scripts/validate_commercial_real_data.py``: bootstrap month-over-month
growth rates from the training window, compound them into forward paths,
and treat the resulting spread as the predictive distribution. It is scored
on the real US Census grocery-wholesale series, 1992-2026, at every rolling
origin, against three references:

  seasonal_naive   the value twelve months earlier. On a not-seasonally-
                   adjusted series this is a genuinely strong baseline and
                   the standard one in the forecasting literature.
  random_walk      last observed value carried forward.
  seasonal_boot    the same bootstrap, but resampling growth rates from the
                   SAME CALENDAR MONTH only, so seasonality survives.

The third exists because the generator in the loop samples growth rates
without regard to calendar month, which on an NSA series throws away the
strongest signal present. Whether that costs anything is exactly what this
measures.

SCORING RULES. Pinball loss on deciles, the Weighted Interval Score
(Bracher et al. 2021), PIT coverage of the central 80% interval, and the
share of realizations falling below the median. A calibrated distribution
puts 80% inside the 80% interval and 50% below the median; a distribution
that is sharp but wrong scores well on neither.
"""
from __future__ import annotations

import argparse
import statistics as st
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from validation.commercial.real_data import demand_index, regime_of  # noqa: E402

QUANTILES = [round(0.1 * k, 1) for k in range(1, 10)]


def pinball(y: float, q: float, tau: float) -> float:
    return (tau * (y - q)) if y >= q else ((1 - tau) * (q - y))


def wis(y: float, qs: dict[float, float]) -> float:
    """Weighted Interval Score: the interval form of the pinball average."""
    return 2.0 * st.mean(pinball(y, qs[t], t) for t in qs)


def boot_paths(hist: list[float], months: list[str], horizon: int,
               n: int, rng, seasonal: bool) -> np.ndarray:
    """Forward paths by compounding resampled month-over-month growth."""
    growth: dict[int, list[float]] = {}
    allg: list[float] = []
    for i in range(len(hist) - 1):
        if hist[i] <= 0:
            continue
        g = hist[i + 1] / hist[i]
        allg.append(g)
        growth.setdefault(int(months[i + 1][5:7]), []).append(g)
    if not allg:
        return np.full((n, horizon), hist[-1])
    last_m = int(months[-1][5:7])
    out = np.empty((n, horizon))
    for w in range(n):
        cur = hist[-1]
        for h in range(horizon):
            m = (last_m + h) % 12 + 1
            pool = growth.get(m) or allg if seasonal else allg
            cur *= float(rng.choice(pool))
            out[w, h] = cur
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--train-months", type=int, default=36)
    p.add_argument("--horizon", type=int, default=12)
    p.add_argument("--paths", type=int, default=400)
    p.add_argument("--seed", type=int, default=17)
    a = p.parse_args()

    idx = demand_index()
    months = sorted(idx)
    vals = [idx[m] for m in months]
    rng = np.random.default_rng(a.seed)

    METHODS = ("bootstrap", "seasonal_boot", "seasonal_naive", "random_walk")
    score: dict[str, list[float]] = {m: [] for m in METHODS}
    cov80: dict[str, list[int]] = {m: [] for m in METHODS}
    below: dict[str, list[int]] = {m: [] for m in METHODS}
    by_regime: dict[str, dict[str, list[float]]] = {}
    n_obs = 0

    for oi in range(max(a.train_months, 13), len(months) - a.horizon + 1):
        hist = vals[oi - a.train_months:oi]
        hmon = months[oi - a.train_months:oi]
        paths = {
            "bootstrap": boot_paths(hist, hmon, a.horizon, a.paths, rng, False),
            "seasonal_boot": boot_paths(hist, hmon, a.horizon, a.paths, rng, True),
        }
        for h in range(a.horizon):
            t = oi + h
            y = vals[t]
            reg = regime_of(months[t]) or "unclassified"
            n_obs += 1
            for name in METHODS:
                if name in paths:
                    draws = paths[name][:, h]
                    qs = {q: float(np.quantile(draws, q)) for q in QUANTILES}
                    lo = float(np.quantile(draws, 0.10))
                    hi = float(np.quantile(draws, 0.90))
                    med = qs[0.5]
                elif name == "seasonal_naive":
                    base = vals[t - 12]
                    resid = [vals[k] - vals[k - 12]
                             for k in range(oi - a.train_months + 12, oi)]
                    sd = st.pstdev(resid) if len(resid) > 1 else 0.0
                    qs = {q: base + sd * float(
                        np.sqrt(2) * _erfinv(2 * q - 1)) for q in QUANTILES}
                    lo, hi, med = qs[0.1], qs[0.9], qs[0.5]
                else:
                    base = vals[oi - 1]
                    resid = [vals[k] - vals[k - 1]
                             for k in range(oi - a.train_months + 1, oi)]
                    sd = (st.pstdev(resid) * np.sqrt(h + 1)
                          if len(resid) > 1 else 0.0)
                    qs = {q: base + sd * float(
                        np.sqrt(2) * _erfinv(2 * q - 1)) for q in QUANTILES}
                    lo, hi, med = qs[0.1], qs[0.9], qs[0.5]
                s = wis(y, qs)
                score[name].append(s)
                cov80[name].append(1 if lo <= y <= hi else 0)
                below[name].append(1 if y < med else 0)
                by_regime.setdefault(reg, {m: [] for m in METHODS})[name].append(s)

    print("\n" + "=" * 78)
    print("DEMAND SCENARIO CALIBRATION ON REAL HISTORY")
    print("=" * 78)
    print("  series   US Census MWTS NAICS 4244, NSA, via FRED")
    print(f"  window   {months[0]} .. {months[-1]}   "
          f"{n_obs:,} origin-horizon pairs")
    print(f"  horizon  {a.horizon} months   train {a.train_months} months\n")
    print(f"  {'method':<16}{'WIS':>10}{'vs best':>10}"
          f"{'80% cover':>12}{'below med':>12}")
    best = min(st.mean(score[m]) for m in METHODS)
    for m in METHODS:
        w = st.mean(score[m])
        print(f"  {m:<16}{w:>10.4f}{w / best:>10.2f}"
              f"{st.mean(cov80[m]):>11.1%}{st.mean(below[m]):>12.1%}")
    print("\n  A calibrated set covers 80% and puts 50% below the median.")

    print("\n  WIS BY REGIME (lower is better)")
    hdr = "".join(f"{m[:13]:>15}" for m in METHODS)
    print(f"  {'regime':<16}{hdr}")
    for reg, d in sorted(by_regime.items()):
        if len(d["bootstrap"]) < 12:
            continue
        print(f"  {reg:<16}" + "".join(f"{st.mean(d[m]):>15.4f}" for m in METHODS))
    print()
    return 0


def _erfinv(x: float) -> float:
    """Inverse error function; avoids a SciPy dependency for nine calls."""
    a = 0.147
    ln = np.log(1 - x * x) if abs(x) < 1 else -700.0
    t = 2 / (np.pi * a) + ln / 2
    return float(np.sign(x) * np.sqrt(max(np.sqrt(t * t - ln / a) - t, 0.0)))


if __name__ == "__main__":
    raise SystemExit(main())
