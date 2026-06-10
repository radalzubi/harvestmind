"""Calibration of the supplier fill-rate distributions.

A probabilistic forecaster is honest only if its stated probabilities match
reality. This module checks the hierarchical supplier model two ways:

PIT (probability integral transform)
    For each held-out delivery, PIT = BetaCDF(observed fill rate) under the
    model fit WITHOUT that delivery. If the model's distributions are
    truthful, PITs are uniform on [0, 1] — too many near 0/1 means the
    intervals are too narrow; bunched in the middle means too wide.

Interval coverage
    The fraction of held-out deliveries falling inside the model's 10–90%
    interval should be ≈ 80%.

Leave-one-out protocol: each delivery is removed from its OWN supplier's
statistics before predicting it. The population hyperparameters (m0, σ²,
κ) are estimated once on the full dataset — re-estimating them per
delivery changes nothing measurable at this data volume and would make
the check O(N²); this shortcut is standard for empirical-Bayes
calibration checks and is stated here rather than hidden.

The GATE (Phase 3): coverage of the 10–90 interval within [0.70, 0.90]
AND a PIT-vs-uniform KS statistic below 0.15. Both are reported raw so a
failure cannot hide.
"""

from __future__ import annotations

from typing import Any

import duckdb
import numpy as np
from scipy import stats

from risk.supplier_distribution import (
    _delivery_fill_rates,
    estimate_population,
    supplier_distribution,
)

GATE_COVERAGE_BAND = (0.70, 0.90)   # target 0.80 for the 10–90 interval
GATE_KS_MAX = 0.15


def pit_values(conn: duckdb.DuckDBPyConnection) -> np.ndarray:
    """Leave-one-out PIT for every delivery with a defined fill rate.

    Returns an array of PIT values in [0, 1]; empty when there is not
    enough data (a supplier needs ≥ 2 deliveries to be predictable with
    one held out).
    """
    fills = _delivery_fill_rates(conn)
    if fills.empty:
        return np.array([])

    pop = estimate_population(fills)
    pits: list[float] = []

    for _, g in fills.groupby("supplier_id"):
        fr = g["fill_rate"].to_numpy(dtype=float)
        n = len(fr)
        if n < 2:
            continue  # nothing to hold out against
        for i in range(n):
            rest = np.delete(fr, i)
            m_s = float(rest.mean())
            v_s = float(rest.var(ddof=0)) if len(rest) >= 2 else None
            dist = supplier_distribution(len(rest), m_s, v_s, pop, 0.10)
            pit = float(stats.beta.cdf(fr[i], dist["alpha"], dist["beta"]))
            pits.append(pit)

    return np.asarray(pits)


def calibration_report(conn: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """PIT uniformity + 10–90 interval coverage, with the gate verdict.

    Never hides a failure: the raw histogram, KS statistic, and coverage
    are all in the payload regardless of the verdict.
    """
    pits = pit_values(conn)
    if len(pits) < 20:
        return {
            "status": "insufficient_history",
            "n_held_out": int(len(pits)),
            "note": "calibration needs at least 20 held-out deliveries",
            "gate_passed": None,
        }

    coverage_10_90 = float(((pits >= 0.10) & (pits <= 0.90)).mean())
    ks_stat, ks_p = stats.kstest(pits, "uniform")
    hist, _ = np.histogram(pits, bins=10, range=(0.0, 1.0))

    lo, hi = GATE_COVERAGE_BAND
    coverage_ok = lo <= coverage_10_90 <= hi
    ks_ok = float(ks_stat) <= GATE_KS_MAX

    return {
        "status": "ok",
        "n_held_out": int(len(pits)),
        "coverage_10_90": round(coverage_10_90, 4),
        "coverage_target": 0.80,
        "coverage_band": list(GATE_COVERAGE_BAND),
        "ks_statistic": round(float(ks_stat), 4),
        "ks_pvalue": round(float(ks_p), 6),
        "ks_max_allowed": GATE_KS_MAX,
        "pit_histogram": hist.tolist(),
        "gate_passed": bool(coverage_ok and ks_ok),
        "gate_rule": (
            "10–90 interval must cover 70–90% of held-out deliveries AND "
            "PIT-vs-uniform KS ≤ 0.15; failure means the stated "
            "uncertainties are not truthful and must not be used for "
            "commitments"
        ),
        "protocol": "leave-one-out within supplier; population "
                    "hyperparameters estimated once on the full data",
    }
