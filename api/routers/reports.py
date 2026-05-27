"""Reports API router: generate and return partner reports."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse

from api.dependencies import get_conn

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/roi", response_class=HTMLResponse)
def roi_report_html(
    partner_name: str = "Hoosier Harvest Market",
    annual_gmv: float = 3_000_000.0,
    conn=Depends(get_conn),
):
    """Generate and return the ROI report as HTML."""
    from backtesting.rolling_origin_engine import RollingOriginEngine, BacktestConfig
    from backtesting.roi_calculator import compute_roi
    from reports.roi_report_generator import render_roi_report, ROIReportError

    orders_df = conn.execute(
        "SELECT ol.product_id, o.buyer_id, o.week_start, ol.qty_ordered_kg "
        "FROM fact_order_lines ol JOIN fact_orders o ON ol.order_id = o.order_id"
    ).df()
    deliveries_df = conn.execute(
        "SELECT supplier_id, product_id, delivery_date, qty_received_kg, qty_rejected_kg "
        "FROM fact_deliveries"
    ).df()

    if orders_df.empty or deliveries_df.empty:
        raise HTTPException(
            status_code=422,
            detail="No order or delivery data in database — cannot compute ROI.",
        )

    cfg = BacktestConfig(
        n_train_weeks=26, horizon_weeks=4, step_weeks=4,
        n_scenarios=30, run_stochastic=True,  # stochastic must be on for ROI vs det
    )
    engine = RollingOriginEngine(cfg)
    results_df = engine.run(orders_df, deliveries_df)

    if results_df.empty:
        raise HTTPException(
            status_code=422,
            detail="Backtest produced no rolling-origin results.",
        )

    roi = compute_roi(results_df, annual_gmv_usd=annual_gmv)
    try:
        html = render_roi_report(roi, results_df, partner_name=partner_name)
    except ROIReportError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return HTMLResponse(content=html)


@router.get("/diagnostic", response_class=HTMLResponse)
def diagnostic_report_html(
    partner_name: str = Query(default="Operator"),
    days: int = Query(default=365, ge=1, le=3650),
    conn=Depends(get_conn),
):
    """Generate and return the diagnostic report as HTML.

    Reads from the staging tables (stg_*). Load data via POST /intake/upload
    before calling this endpoint.
    """
    from dashboard.lib.diagnostic_metrics import diagnostic_summary
    from reports.diagnostic_report_generator import (
        render_diagnostic_report,
        DiagnosticReportError,
    )

    summary = diagnostic_summary(conn, partner_name=partner_name, days=days)
    try:
        html = render_diagnostic_report(summary, partner_name=partner_name)
    except DiagnosticReportError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return HTMLResponse(content=html)
