"""Reports API router: generate and return partner reports."""

from __future__ import annotations

from fastapi import APIRouter, Depends
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
    import pandas as pd
    from backtesting.rolling_origin_engine import RollingOriginEngine, BacktestConfig
    from backtesting.roi_calculator import compute_roi
    from reports.roi_report_generator import render_roi_report

    orders_df = conn.execute(
        "SELECT ol.product_id, o.buyer_id, o.week_start, ol.qty_ordered_kg "
        "FROM fact_order_lines ol JOIN fact_orders o ON ol.order_id = o.order_id"
    ).df()
    deliveries_df = conn.execute(
        "SELECT supplier_id, product_id, delivery_date, qty_received_kg, qty_rejected_kg "
        "FROM fact_deliveries"
    ).df()
    conn.close()

    cfg = BacktestConfig(n_train_weeks=26, horizon_weeks=4, step_weeks=4, n_scenarios=30, run_stochastic=False)
    engine = RollingOriginEngine(cfg)
    results_df = engine.run(orders_df, deliveries_df)

    roi = compute_roi(results_df, annual_gmv_usd=annual_gmv)
    html = render_roi_report(roi, results_df, partner_name=partner_name)
    return HTMLResponse(content=html)
