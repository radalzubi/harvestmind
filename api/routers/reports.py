"""Reports API router: generate and return partner reports."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse

from api.dependencies import get_conn, rate_limiter

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/roi", response_class=HTMLResponse,
            dependencies=[Depends(rate_limiter)])
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
        raise HTTPException(status_code=422, detail=f"Report inputs invalid ({type(e).__name__})") from e
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
        raise HTTPException(status_code=422, detail=f"Report inputs invalid ({type(e).__name__})") from e
    return HTMLResponse(content=html)


@router.get("/roi-cards")
def roi_cards(conn=Depends(get_conn)):
    """Two-card ROI: the assumed opportunity ceiling and the measured
    backtest result — SEPARATE cards, never summed, never interchanged.

    Card 1 (ceiling) is an assumption-based benchmark applied to the
    operator's measured losses. Card 2 (measured) exists only when the
    rolling-origin benchmark has actually run on enough history; until
    then it says "not yet measured" rather than borrowing the ceiling.
    """
    from dashboard.lib.diagnostic_metrics import (
        _period_days_from_data, estimated_annual_savings,
        shortage_loss_usd, waste_loss_usd,
    )

    period = _period_days_from_data(conn)
    waste = waste_loss_usd(conn, days=period)
    shortage = shortage_loss_usd(conn, days=period)
    ceiling = estimated_annual_savings(waste, shortage, period_days=period)

    from backtesting.benchmark_suite import run_benchmark
    bench = run_benchmark(conn)
    if bench.get("status") == "ok":
        edge = bench["sp_vs_deterministic_lp"]
        measured = {
            "status": "measured",
            "basis": "rolling-origin backtest on your own history",
            "sp_vs_lp_edge_pct": edge["edge_pct"],
            "wins": edge["wins"],
            "n_origins": edge["n"],
            "paired_t": edge["paired_t"],
            "gate_passed": bench["gate_passed"],
            "verdict": bench["verdict"],
            "spot_assumption": bench["spot_economics"],
        }
    else:
        measured = {
            "status": "not_measured",
            "note": "the measured card requires enough order history for "
                    "a rolling-origin backtest; nothing is borrowed from "
                    "the ceiling card in the meantime",
            "weeks_available": bench.get("weeks_available"),
            "weeks_required": bench.get("weeks_required"),
        }

    return {
        "ceiling_card": {
            "status": "assumed",
            "basis": ceiling["basis"],
            "note": ceiling["basis_note"],
            "annual_low_usd": ceiling["estimated_annual_savings_usd_low"],
            "annual_high_usd": ceiling["estimated_annual_savings_usd_high"],
            "addressable_loss_usd": ceiling["addressable_loss_usd"],
        },
        "measured_card": measured,
        "do_not_sum": "these two cards answer different questions and "
                      "must never be added or averaged together",
    }


@router.get("/confidence")
def confidence(conn=Depends(get_conn)):
    """Recommendation confidence index (internal index, not a probability)."""
    from risk.confidence import recommendation_confidence
    return recommendation_confidence(conn)
