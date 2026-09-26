"""Backtest API router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import capability, get_conn, rate_limiter
from api.models.schemas import BacktestRequest, BacktestResponse

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post("/run", response_model=BacktestResponse,
             dependencies=[Depends(rate_limiter), Depends(capability("runPlanner"))])
def run_backtest(req: BacktestRequest, conn=Depends(get_conn)):
    """Run rolling-origin backtest against historical data in the DB."""
    from backtesting.rolling_origin_engine import RollingOriginEngine, BacktestConfig
    from backtesting.roi_calculator import compute_roi
    from backtesting.procurement_metrics import cost_per_kg_by_model

    orders_df = conn.execute(
        "SELECT ol.product_id, o.buyer_id, o.week_start, ol.qty_ordered_kg "
        "FROM fact_order_lines ol JOIN fact_orders o ON ol.order_id = o.order_id"
    ).df()

    deliveries_df = conn.execute(
        "SELECT supplier_id, product_id, delivery_date, qty_received_kg, qty_rejected_kg "
        "FROM fact_deliveries"
    ).df()
    if orders_df.empty:
        raise HTTPException(status_code=422, detail="No order history in database")

    cfg = BacktestConfig(
        n_train_weeks=req.n_train_weeks,
        horizon_weeks=req.horizon_weeks,
        step_weeks=req.step_weeks,
        n_scenarios=req.n_scenarios,
        gammas=req.gammas,
        run_stochastic=req.run_stochastic,
    )

    engine = RollingOriginEngine(cfg)
    results_df = engine.run(orders_df, deliveries_df)

    if results_df.empty:
        raise HTTPException(status_code=500, detail="Backtest produced no results")

    summary = cost_per_kg_by_model(results_df).to_dict("records")
    roi = compute_roi(results_df)

    return BacktestResponse(
        n_origins=int(results_df["origin_week"].nunique()),
        models_run=list(results_df["model"].unique()),
        results_summary=summary,
        roi=roi,
    )


@router.get("/results")
def get_backtest_results(conn=Depends(get_conn)):
    """Return cached backtest results from DB (if stored)."""
    try:
        df = conn.execute("SELECT * FROM planning_scenarios ORDER BY run_timestamp DESC LIMIT 500").df()
    except Exception:
        df = None
    if df is None or df.empty:
        return {"message": "No cached results. Run POST /backtest/run first."}
    return df.to_dict("records")


@router.post("/benchmark", dependencies=[Depends(capability("runPlanner"))])
def run_benchmark_suite(
    folds: int = 8,
    train_weeks: int = 26,
    spot_cost_multiplier: float = 1.30,
    spot_capacity_factor: float = 0.30,
    conn=Depends(get_conn),
):
    """Rolling-origin benchmark on staged history: two-sided SP vs
    deterministic LP vs order-up-to vs naive, honest penalties, with the
    gate verdict (including the unflattering one)."""
    from backtesting.benchmark_suite import run_benchmark
    return run_benchmark(
        conn, n_folds=folds, train_weeks=train_weeks,
        spot_cost_multiplier=spot_cost_multiplier,
        spot_capacity_factor=spot_capacity_factor,
    )


@router.get("/saa-gap")
def saa_gap(conn=Depends(get_conn)):
    """SAA optimality-gap estimate for the two-sided SP."""
    from backtesting.benchmark_suite import saa_optimality_gap
    return saa_optimality_gap(conn)
