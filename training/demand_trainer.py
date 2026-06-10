"""Demand forecaster training with pool priors — the thin-data bootstrap.

Where the pool helps, precisely: an operator with a few weeks of history
cannot estimate trend or variability from their own data. The pool
carries the cross-operator consensus per category — trend direction and
demand CV. The bootstrap blends the operator's run-rate with the pool's
trend, weighted by how much own history exists:

    w_own  = n_weeks / (n_weeks + POOL_PSEUDO_WEEKS)
    trend_factor (pool)  = +8% (increasing) / −8% (decreasing) / 0
    forecast = runrate × (1 + (1 − w_own) × trend_factor)
    quantiles: own residuals when estimable, else pool CV

With a season of history the pool's influence washes out and the full
LGBM forecaster (which beats seasonal-naive behind its MASE gate) takes
over. Retrained models still pass the incumbent-beating holdout gate
(retraining/pipeline.retrain_demand) — pool priors shape cold starts,
never bypass validation.
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd

from pool.pool_reader import DemandPrior, PoolReader

POOL_PSEUDO_WEEKS = 8
TREND_FACTOR = {"increasing": 0.08, "decreasing": -0.08, "stable": 0.0}
THIN_HISTORY_WEEKS = 12


def pool_informed_point_forecast(
    weekly: pd.DataFrame,             # [product_id, week_start, demand_kg]
    category_of: dict[str, str],      # product_id -> pool category
    pool_reader: PoolReader | None = None,
) -> dict[str, dict[str, Any]]:
    """Per-product next-week forecast for thin-history operators.

    Returns {product: {forecast_kg, lo, hi, basis}}. With no pool prior
    for a product's category, the plain run-rate is returned and labeled
    as such — the pool never silently invents an adjustment.
    """
    reader = pool_reader or PoolReader()
    out: dict[str, dict[str, Any]] = {}
    for product, g in weekly.groupby("product_id"):
        series = g.groupby("week_start")["demand_kg"].sum().sort_index()
        vals = series.to_numpy(dtype=float)
        n = len(vals)
        if n == 0:
            continue
        runrate = float(vals[-4:].mean())
        prior: Optional[DemandPrior] = reader.get_demand_prior(
            category_of.get(str(product), "uncategorized"))

        if prior is None:
            out[str(product)] = {
                "forecast_kg": round(runrate, 1),
                "lo": round(runrate * 0.8, 1), "hi": round(runrate * 1.2, 1),
                "basis": "runrate (no pool prior for this category)",
            }
            continue

        w_own = n / (n + POOL_PSEUDO_WEEKS)
        factor = TREND_FACTOR.get(prior.trend_consensus, 0.0)
        forecast = runrate * (1.0 + (1.0 - w_own) * factor)

        cv = (float(np.std(vals, ddof=0) / vals.mean())
              if n >= THIN_HISTORY_WEEKS and vals.mean() > 0
              else prior.demand_cv)
        out[str(product)] = {
            "forecast_kg": round(forecast, 1),
            "lo": round(max(forecast * (1 - 1.28 * cv), 0.0), 1),
            "hi": round(forecast * (1 + 1.28 * cv), 1),
            "basis": (f"runrate × pool trend ({prior.trend_consensus}, "
                      f"{prior.n_operators} operators) — own weight "
                      f"{w_own:.2f}"),
        }
    return out


def evaluate_pool_bootstrap(
    weekly: pd.DataFrame,
    category_of: dict[str, str],
    pool_reader: PoolReader,
    holdout_weeks: int = 2,
) -> dict[str, Any]:
    """Out-of-sample comparison: pool-informed vs plain run-rate on the
    last weeks of a thin history. Returns both WAPEs so the claim 'the
    pool helps thin-data operators' is measured, never asserted."""
    weeks = sorted(weekly["week_start"].unique())
    if len(weeks) <= holdout_weeks + 2:
        return {"status": "insufficient_history"}
    cut = weeks[-holdout_weeks]
    train = weekly[weekly["week_start"] < cut]
    test = weekly[weekly["week_start"] >= cut]

    with_pool = pool_informed_point_forecast(train, category_of, pool_reader)
    plain = {p: float(g.groupby("week_start")["demand_kg"].sum()
                      .sort_index().to_numpy()[-4:].mean())
             for p, g in train.groupby("product_id")}

    actual = test.groupby(["product_id", "week_start"])["demand_kg"].sum()
    err_pool = err_plain = tot = 0.0
    for (p, _w), a in actual.items():
        p = str(p)
        if p not in with_pool:
            continue
        err_pool += abs(float(a) - with_pool[p]["forecast_kg"])
        err_plain += abs(float(a) - plain[p])
        tot += abs(float(a))
    if tot == 0:
        return {"status": "insufficient_history"}
    return {
        "status": "ok",
        "wape_pool_informed": round(err_pool / tot, 4),
        "wape_plain_runrate": round(err_plain / tot, 4),
        "pool_helps": bool(err_pool < err_plain),
    }
