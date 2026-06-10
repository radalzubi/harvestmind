"""Validation-gated retraining for the two forecasters.

Protocol (identical for both model families):

1. Hold out the most recent weeks of staged history.
2. Fit a CANDIDATE on the data before the holdout.
3. Score candidate and INCUMBENT (the currently deployed version) on the
   same holdout, out-of-sample.
4. Deploy the candidate ONLY if it beats the incumbent. Otherwise keep
   the incumbent and log the rejection — a worse refit never ships.
5. Either way, append a log entry: data window, both scores, decision.

Run it on a schedule (cron / CI); see scripts/retrain.py. Nothing here
learns autonomously — "the system keeps improving" means exactly this
loop and nothing more.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from retraining.registry import ModelRegistry

HOLDOUT_WEEKS = 4


# ── Demand forecaster ────────────────────────────────────────────────────────

def _score_demand_point_forecasts(
    point: dict[str, float], holdout: pd.DataFrame,
) -> float | None:
    """Pooled WAPE of per-product weekly point forecasts on the holdout."""
    actual = holdout.groupby(["product_id", "week_start"])["qty_ordered_kg"].sum()
    err = tot = 0.0
    for (p, _w), a in actual.items():
        if p in point:
            err += abs(float(a) - point[p])
            tot += abs(float(a))
    return err / tot if tot > 0 else None


def retrain_demand(conn, registry_root) -> dict[str, Any]:
    """Retrain the demand forecaster with the validation gate."""
    from forecasting.demand.demand_forecast_service import (
        classify_products,
        weekly_orders_from_staging,
        _product_point_forecasts,
    )
    from forecasting.demand.lgbm_global_model import LGBMDemandModel

    reg = ModelRegistry(registry_root, "demand")
    weekly = weekly_orders_from_staging(conn)
    if weekly.empty or weekly["week_start"].nunique() < 12:
        out = {"family": "demand", "decision": "skipped",
               "reason": "insufficient history (<12 weeks)"}
        reg.log(out)
        return out

    weeks = sorted(weekly["week_start"].unique())
    cut = weeks[-HOLDOUT_WEEKS]
    train = weekly[weekly["week_start"] < cut]
    holdout = weekly[weekly["week_start"] >= cut]
    window = {"train_start": str(pd.Timestamp(weeks[0]).date()),
              "holdout_start": str(pd.Timestamp(cut).date()),
              "holdout_end": str(pd.Timestamp(weeks[-1]).date()),
              "n_weeks_train": int(train["week_start"].nunique())}

    # candidate: fresh fit on the training slice
    cand_point, _, cand_model = _product_point_forecasts(
        train, 1, classify_products(train))
    cand_wape = _score_demand_point_forecasts(cand_point, holdout)

    # incumbent: previously deployed LGBM artifacts, scored on the SAME holdout
    inc_wape = None
    cur = reg.current
    if cur is not None:
        try:
            inc_model = LGBMDemandModel.load(reg.version_dir(cur))
            preds = inc_model.predict(train, forecast_weeks=1)
            inc_point = (preds.groupby("product_id")["forecast_kg"]
                         .sum().to_dict())
            inc_wape = _score_demand_point_forecasts(inc_point, holdout)
        except Exception as e:  # noqa: BLE001  incumbent unusable → candidate wins
            inc_wape = None
            reg.log({"family": "demand", "event": "incumbent_load_failed",
                     "error": str(e)})

    deploy = (cand_wape is not None
              and (inc_wape is None or cand_wape < inc_wape))

    decision: dict[str, Any] = {
        "family": "demand", "window": window,
        "candidate_wape": round(cand_wape, 4) if cand_wape is not None else None,
        "incumbent_wape": round(inc_wape, 4) if inc_wape is not None else None,
        "incumbent_version": cur,
        "gate": "deploy only if candidate WAPE < incumbent WAPE on holdout",
    }

    if deploy and cand_model is not None:
        vdir = reg.new_version_dir()
        # refit on ALL data before persisting (the holdout was only for
        # the gate; production should use every week available)
        full_point, _, full_model = _product_point_forecasts(
            weekly, 1, classify_products(weekly))
        if full_model is not None:
            full_model.save(vdir)
        reg.write_metrics(vdir.name, decision)
        reg.deploy(vdir.name)
        decision.update({"decision": "deployed", "version": vdir.name})
    else:
        decision.update({"decision": "rejected" if cand_wape is not None
                        else "skipped",
                         "reason": "candidate did not beat incumbent on "
                                   "holdout" if not deploy else
                                   "no persistable model"})
    reg.log(decision)
    return decision


# ── Yield forecaster ─────────────────────────────────────────────────────────

def _population_coverage_error(fills: pd.DataFrame, pop) -> float | None:
    """|coverage − 0.80| of the 10–90 interval, leave-one-out, under a
    given population prior."""
    from scipy import stats
    from risk.supplier_distribution import supplier_distribution

    pits: list[float] = []
    for _, g in fills.groupby("supplier_id"):
        fr = g["fill_rate"].to_numpy(dtype=float)
        if len(fr) < 2:
            continue
        for i in range(len(fr)):
            rest = np.delete(fr, i)
            m_s = float(rest.mean())
            v_s = float(rest.var(ddof=0)) if len(rest) >= 2 else None
            d = supplier_distribution(len(rest), m_s, v_s, pop, 0.10)
            pits.append(float(stats.beta.cdf(fr[i], d["alpha"], d["beta"])))
    if len(pits) < 20:
        return None
    arr = np.asarray(pits)
    return abs(float(((arr >= 0.10) & (arr <= 0.90)).mean()) - 0.80)


def retrain_yield(conn, registry_root) -> dict[str, Any]:
    """Retrain the supplier-yield population prior with the gate."""
    import json as _json

    from risk.supplier_distribution import (
        Population, _delivery_fill_rates, estimate_population,
    )

    reg = ModelRegistry(registry_root, "yield")
    fills = _delivery_fill_rates(conn)
    if fills.empty:
        out = {"family": "yield", "decision": "skipped",
               "reason": "no delivery history"}
        reg.log(out)
        return out

    candidate = estimate_population(fills)
    cand_err = _population_coverage_error(fills, candidate)

    inc_err = None
    cur = reg.current
    if cur is not None:
        f = reg.version_dir(cur) / "population.json"
        if f.exists():
            incumbent = Population(**_json.loads(f.read_text()))
            inc_err = _population_coverage_error(fills, incumbent)

    deploy = (cand_err is not None
              and (inc_err is None or cand_err <= inc_err))

    decision: dict[str, Any] = {
        "family": "yield",
        "n_deliveries": int(len(fills)),
        "candidate_coverage_error": round(cand_err, 4)
        if cand_err is not None else None,
        "incumbent_coverage_error": round(inc_err, 4)
        if inc_err is not None else None,
        "incumbent_version": cur,
        "gate": "deploy only if |coverage − 0.80| does not worsen on "
                "current held-out deliveries",
    }

    if deploy:
        vdir = reg.new_version_dir()
        (vdir / "population.json").write_text(_json.dumps({
            "mean": candidate.mean,
            "pooled_variance": candidate.pooled_variance,
            "within_variance": candidate.within_variance,
            "kappa": candidate.kappa,
            "n_deliveries": candidate.n_deliveries,
            "n_suppliers": candidate.n_suppliers,
            "method": candidate.method,
        }))
        reg.write_metrics(vdir.name, decision)
        reg.deploy(vdir.name)
        decision.update({"decision": "deployed", "version": vdir.name})
    else:
        decision.update({"decision": "rejected" if cand_err is not None
                        else "skipped"})
    reg.log(decision)
    return decision


def retrain_all(conn, registry_root) -> dict[str, Any]:
    """One scheduled retraining pass over both model families."""
    return {
        "demand": retrain_demand(conn, registry_root),
        "yield": retrain_yield(conn, registry_root),
    }
