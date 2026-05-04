"""CLI: generate partner ROI report as HTML + PDF."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate HarvestMind ROI report")
    parser.add_argument("--db", default=str(ROOT / "harvestmind.duckdb"))
    parser.add_argument("--partner", default="Hoosier Harvest Market")
    parser.add_argument("--gmv", type=float, default=3_000_000.0)
    parser.add_argument("--output", default=str(ROOT / "outputs" / "roi_report.html"))
    parser.add_argument("--pdf", action="store_true")
    args = parser.parse_args()

    import duckdb
    from backtesting.rolling_origin_engine import RollingOriginEngine, BacktestConfig
    from backtesting.roi_calculator import compute_roi
    from reports.roi_report_generator import render_roi_report

    conn = duckdb.connect(args.db)
    orders_df = conn.execute(
        "SELECT ol.product_id, o.buyer_id, o.week_start, ol.qty_ordered_kg "
        "FROM fact_order_lines ol JOIN fact_orders o ON ol.order_id = o.order_id"
    ).df()
    deliveries_df = conn.execute(
        "SELECT supplier_id, product_id, delivery_date, qty_received_kg, qty_rejected_kg "
        "FROM fact_deliveries"
    ).df()
    conn.close()

    cfg = BacktestConfig(n_train_weeks=26, horizon_weeks=4, step_weeks=4,
                         n_scenarios=20, run_stochastic=True)
    engine = RollingOriginEngine(cfg)
    print("Running backtest for ROI calculation…")
    results_df = engine.run(orders_df, deliveries_df)
    roi = compute_roi(results_df, annual_gmv_usd=args.gmv)

    html = render_roi_report(roi, results_df, partner_name=args.partner,
                              output_path=args.output, as_pdf=args.pdf)
    print(f"Report written to: {args.output}")
    if args.pdf:
        print(f"PDF written to: {Path(args.output).with_suffix('.pdf')}")


if __name__ == "__main__":
    main()
