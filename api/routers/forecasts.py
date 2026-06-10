"""Demand forecast API.

GET /forecasts/demand
  Per-product forecast distribution (median + quantiles), the model used
  per product, and plain-language drivers.

GET /forecasts/demand/evaluation
  Rolling-origin out-of-sample evaluation vs seasonal-naive, including the
  honest gate verdict. If gate_passed is false, the model does NOT beat
  the naive on this operator's data and the UI must say so.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.dependencies import get_conn

router = APIRouter(prefix="/forecasts", tags=["forecasts"])


@router.get("/demand")
def demand_forecast(
    weeks: int = Query(default=4, ge=1, le=13),
    conn=Depends(get_conn),
):
    from forecasting.demand.demand_forecast_service import forecast_demand
    return forecast_demand(conn, horizon_weeks=weeks).to_dict()


@router.get("/demand/evaluation")
def demand_forecast_evaluation(
    folds: int = Query(default=4, ge=2, le=8),
    conn=Depends(get_conn),
):
    from forecasting.demand.demand_forecast_service import (
        evaluate_demand_forecaster,
    )
    return evaluate_demand_forecaster(conn, n_folds=folds)


@router.get("/supply")
def supply_risk(conn=Depends(get_conn)):
    """Per-supplier predictive fill-rate distributions (Tier 1) with the
    calibration verdict and Tier-2 covariate admission status."""
    from risk.calibration import calibration_report
    from risk.supplier_distribution import supplier_fill_distributions
    from risk.yield_covariates import covariate_status

    dists = supplier_fill_distributions(conn)  # service-linked quantile
    prior = dists.pop("_prior", {})
    suppliers = [
        {"supplier_id": sid, **d}
        for sid, d in sorted(dists.items(),
                             key=lambda kv: kv[1]["downside"])
    ]
    return {
        "suppliers": suppliers,
        "prior": prior,
        "calibration": calibration_report(conn),
        "covariates": covariate_status(conn),
    }
