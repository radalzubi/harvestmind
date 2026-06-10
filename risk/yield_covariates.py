"""Tier-2 yield covariates: external signals admitted only on measured gain.

The Tier-1 supplier model uses delivery history alone. External signals
(weather, crop type, grower location) can in principle sharpen the yield
distribution — but each one is admitted ONLY if it measurably improves
calibration on held-out deliveries. No signal ships on faith; the
admission test in this module IS the pipeline.

Current signals
---------------
weather_heat_stress
    Shifts a supplier's expected fill rate in weeks flagged as heat-
    stressed (fact_weather_obs, fed by ingestion/noaa_weather_fetcher).
    The shift size is not assumed: it is the observed mean fill-rate
    difference between stressed and unstressed weeks in the operator's
    own history. When no weather observations are loaded, the signal
    reports "no data" and is not admitted — the NOAA fetch only becomes
    worth wiring for an operator whose data admits the signal.

Admission rule
--------------
A signal is admitted when, on leave-one-out held-out deliveries, it moves
the 10–90 interval coverage closer to the 0.80 target AND does not worsen
PIT uniformity (KS statistic). Both numbers are reported either way.
"""

from __future__ import annotations

from typing import Any

import duckdb
import numpy as np
import pandas as pd
from scipy import stats

from risk.calibration import GATE_COVERAGE_BAND
from risk.supplier_distribution import (
    _delivery_fill_rates,
    estimate_population,
    supplier_distribution,
)


def _weather_flags(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Weekly heat-stress flags from fact_weather_obs, if loaded."""
    try:
        df = conn.execute("""
            SELECT DATE_TRUNC('week', obs_date) AS week_start,
                   MAX(CASE WHEN heat_stress_flag THEN 1 ELSE 0 END) AS heat
            FROM fact_weather_obs
            GROUP BY 1
        """).df()
        return df
    except Exception:
        return pd.DataFrame(columns=["week_start", "heat"])


def _deliveries_with_heat(conn) -> pd.DataFrame:
    """Per-delivery fill rates joined to the week's heat-stress flag."""
    fills = conn.execute("""
        SELECT supplier_id,
               supplier_name,
               DATE_TRUNC('week', delivery_date) AS week_start,
               ordered_quantity AS ordered,
               COALESCE(accepted_quantity, delivered_quantity) AS accepted
        FROM stg_supplier_deliveries
        WHERE ordered_quantity IS NOT NULL AND ordered_quantity > 0
          AND delivery_date IS NOT NULL
    """).df()
    if fills.empty:
        return fills
    fills["fill_rate"] = (
        fills["accepted"].fillna(0.0).astype(float)
        / fills["ordered"].astype(float)
    ).clip(0.0, 1.0)
    weather = _weather_flags(conn)
    if weather.empty:
        fills["heat"] = np.nan
        return fills
    fills["week_start"] = pd.to_datetime(fills["week_start"])
    weather["week_start"] = pd.to_datetime(weather["week_start"])
    return fills.merge(weather, on="week_start", how="left")


def _loo_coverage_and_ks(
    fills: pd.DataFrame,
    shift_per_row: np.ndarray | None,
) -> tuple[float, float, int]:
    """Leave-one-out 10–90 coverage and PIT KS, with an optional per-row
    mean shift applied to the predictive distribution."""
    pop = estimate_population(fills)
    pits: list[float] = []
    fills = fills.reset_index(drop=True)
    shifts = (np.zeros(len(fills)) if shift_per_row is None
              else np.asarray(shift_per_row, dtype=float))

    for sid, g in fills.groupby("supplier_id"):
        idx = g.index.to_numpy()
        fr = g["fill_rate"].to_numpy(dtype=float)
        if len(fr) < 2:
            continue
        for j, i in enumerate(idx):
            rest = np.delete(fr, j)
            m_s = float(rest.mean())
            v_s = float(rest.var(ddof=0)) if len(rest) >= 2 else None
            dist = supplier_distribution(len(rest), m_s, v_s, pop, 0.10)
            mu = min(max(dist["mean"] + shifts[i], 1e-6), 1 - 1e-6)
            # re-fit Beta at the shifted mean with the same variance
            var = (dist["alpha"] * dist["beta"]
                   / ((dist["alpha"] + dist["beta"]) ** 2
                      * (dist["alpha"] + dist["beta"] + 1)))
            from risk.supplier_distribution import _beta_from_mean_var
            a, b = _beta_from_mean_var(mu, var)
            pits.append(float(stats.beta.cdf(fr[j], a, b)))

    if len(pits) < 20:
        return float("nan"), float("nan"), len(pits)
    arr = np.asarray(pits)
    coverage = float(((arr >= 0.10) & (arr <= 0.90)).mean())
    ks = float(stats.kstest(arr, "uniform")[0])
    return coverage, ks, len(pits)


def admit_weather_signal(conn: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """Test whether the heat-stress weather signal earns admission.

    Returns the with/without calibration numbers and the verdict. The
    signal is admitted only when it moves coverage closer to 0.80 without
    worsening PIT uniformity.
    """
    df = _deliveries_with_heat(conn)
    if df.empty:
        return {"signal": "weather_heat_stress", "admitted": False,
                "reason": "no delivery data"}
    if df["heat"].isna().all():
        return {"signal": "weather_heat_stress", "admitted": False,
                "reason": "no weather observations loaded "
                          "(fact_weather_obs empty) — signal untestable, "
                          "not admitted on faith"}

    flagged = df[df["heat"] == 1]["fill_rate"]
    clear = df[df["heat"] == 0]["fill_rate"]
    if len(flagged) < 5 or len(clear) < 5:
        return {"signal": "weather_heat_stress", "admitted": False,
                "reason": f"too few stressed weeks to estimate the effect "
                          f"({len(flagged)} stressed deliveries)"}

    # The signal's effect size is measured, not assumed.
    delta = float(flagged.mean() - clear.mean())
    shift = np.where(df["heat"].fillna(0).to_numpy() == 1, delta, 0.0)

    cov0, ks0, n0 = _loo_coverage_and_ks(df, None)
    cov1, ks1, n1 = _loo_coverage_and_ks(df, shift)
    if np.isnan(cov0) or np.isnan(cov1):
        return {"signal": "weather_heat_stress", "admitted": False,
                "reason": "not enough held-out deliveries to evaluate"}

    target = 0.80
    closer = abs(cov1 - target) < abs(cov0 - target)
    not_worse_ks = ks1 <= ks0 + 1e-9
    admitted = bool(closer and not_worse_ks)

    return {
        "signal": "weather_heat_stress",
        "admitted": admitted,
        "measured_effect_delta_fill": round(delta, 4),
        "baseline": {"coverage_10_90": round(cov0, 4), "ks": round(ks0, 4)},
        "with_signal": {"coverage_10_90": round(cov1, 4), "ks": round(ks1, 4)},
        "n_held_out": n0,
        "rule": "admit only if coverage moves closer to 0.80 and PIT "
                "uniformity does not worsen",
    }


def covariate_status(conn: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """Status of every Tier-2 signal: tested, admitted or not, and why."""
    return {
        "signals": [admit_weather_signal(conn)],
        "policy": "external signals are admitted per-operator on measured "
                  "calibration improvement, never by default",
        "coverage_band": list(GATE_COVERAGE_BAND),
    }
