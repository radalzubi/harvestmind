"""Paired analysis of two validation runs over IDENTICAL folds.

WHY PAIRING MATTERS HERE. Comparing two medians taken over two different
fold sets is not a comparison of the two methods, it is a comparison of the
two methods plus whatever differed between the sets. The scenario-generator
runs admitted 337 and 342 folds respectively, so five folds separated them
before either method did anything. Everything below matches on (seed,
origin) and reports paired differences only.

Confidence intervals are bootstrapped over folds rather than assumed
normal, because per-fold cost differences are heavily skewed: a handful of
binding months dominate, which is the whole point of the exercise.

FOLDS ARE NOT INDEPENDENT. A 12-month evaluation window advanced one month
at a time overlaps its neighbour by eleven twelfths. A bootstrap over folds
therefore UNDERSTATES the true interval. The moving-block variant reported
alongside resamples contiguous runs of twelve folds to keep that
dependence, and it is the honest number of the two.
"""
from __future__ import annotations

import argparse
import csv
import statistics as st
import sys
from pathlib import Path

import numpy as np


def load(path: Path) -> dict[tuple, dict]:
    out = {}
    with path.open() as fh:
        for r in csv.DictReader(fh):
            out[(r["seed"], r["origin"])] = r
    return out


def boot_ci(x: list[float], n: int, rng, block: int | None = None
            ) -> tuple[float, float]:
    x = np.asarray(x, dtype=float)
    if len(x) < 3:
        return (float("nan"), float("nan"))
    meds = np.empty(n)
    if block and block > 1 and len(x) > block:
        n_blocks = int(np.ceil(len(x) / block))
        starts = len(x) - block
        for i in range(n):
            idx = np.concatenate([
                np.arange(s, s + block)
                for s in rng.integers(0, starts + 1, n_blocks)])[:len(x)]
            meds[i] = np.median(x[idx])
    else:
        for i in range(n):
            meds[i] = np.median(rng.choice(x, len(x), replace=True))
    return float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5))


def sign_test(diffs: list[float]) -> float:
    """Two-sided sign test p-value; exact binomial, no SciPy required."""
    pos = sum(1 for d in diffs if d > 0)
    neg = sum(1 for d in diffs if d < 0)
    n = pos + neg
    if n == 0:
        return 1.0
    k = min(pos, neg)
    from math import comb
    tail = sum(comb(n, i) for i in range(k + 1))
    return min(1.0, 2.0 * tail / (2.0 ** n))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--a", required=True, help="baseline arm CSV")
    p.add_argument("--b", required=True, help="comparison arm CSV")
    p.add_argument("--label-a", default="A")
    p.add_argument("--label-b", default="B")
    p.add_argument("--boot", type=int, default=4000)
    a = p.parse_args()

    A, B = load(Path(a.a)), load(Path(a.b))
    keys = sorted(set(A) & set(B))
    rng = np.random.default_rng(2027)
    print("\n" + "=" * 78)
    print(f"PAIRED COMPARISON   {a.label_a}  vs  {a.label_b}")
    print("=" * 78)
    print(f"  folds in {a.label_a}: {len(A)}   in {a.label_b}: {len(B)}   "
          f"matched: {len(keys)}")
    if not keys:
        print("  no shared folds")
        return 1

    print(f"\n  {'quantity':<34}{'median diff':>13}{'95% CI (block)':>22}"
          f"{'sign p':>9}")
    for field, lab, better in (
            ("sp_total", "SP cost, B minus A", "lower is better for B"),
            ("sp_fill_rate", "SP fill rate, B minus A", "higher is better"),
            ("det_mean_total", "deterministic cost, B - A", "control: expect 0"),
    ):
        d = [float(B[k][field]) - float(A[k][field]) for k in keys]
        if field.endswith("total"):
            base = [float(A[k][field]) for k in keys]
            d = [100.0 * x / b for x, b in zip(d, base) if b > 0]
            unit = "%"
        else:
            d = [100.0 * x for x in d]
            unit = "pt"
        lo, hi = boot_ci(d, a.boot, rng, block=12)
        print(f"  {lab:<34}{st.median(d):>12.2f}{unit}"
              f"{f'[{lo:+.2f}, {hi:+.2f}]':>22}{sign_test(d):>9.4f}")

    print(f"\n  {'edge over deterministic':<34}{'median':>13}{'95% CI (block)':>22}"
          f"{'wins':>9}")
    for tag, src in ((a.label_a, A), (a.label_b, B)):
        e = []
        for k in keys:
            dt, sp = float(src[k]["det_mean_total"]), float(src[k]["sp_total"])
            if dt > 0:
                e.append((dt - sp) / dt * 100)
        lo, hi = boot_ci(e, a.boot, rng, block=12)
        print(f"  {tag:<34}{st.median(e):>12.2f}%"
              f"{f'[{lo:+.2f}, {hi:+.2f}]':>22}"
              f"{f'{sum(1 for x in e if x > 0)}/{len(e)}':>9}")

    print("\n  Block bootstrap, block length 12, because evaluation windows")
    print("  twelve months long advanced one month at a time overlap by 11/12.")
    print("  A naive per-fold bootstrap would give an interval roughly three")
    print("  times too narrow and should not be quoted.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
