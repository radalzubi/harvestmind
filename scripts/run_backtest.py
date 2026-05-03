"""CLI: run rolling-origin backtest and print results summary."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run HarvestMind rolling-origin backtest")
    parser.add_argument("--db", default=str(ROOT / "harvestmind.duckdb"))
    parser.add_argument("--train-weeks", type=int, default=52)
    parser.add_argument("--horizon", type=int, default=4)
    parser.add_argument("--step", type=int, default=4)
    parser.add_argument("--scenarios", type=int, default=30)
    parser.add_argument("--no-stochastic", action="store_true")
    parser.add_argument("--gmv", type=float, default=3_000_000.0)
    args = parser.parse_args()

    import duckdb
    from backtesting.rolling_origin_engine import RollingOriginEngine, BacktestConfig
    from backtesting.roi_calculator import compute_roi
    from backtesting.procurement_metrics import cost_per_kg_by_model

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

    if orders_df.empty:
        print("No order data. Run: python synthetic/generate_pilot_dataset.py")
        sys.exit(1)

    cfg = BacktestConfig(
        n_train_weeks=args.train_weeks,
        horizon_weeks=args.horizon,
        step_weeks=args.step,
        n_scenarios=args.scenarios,
        run_stochastic=not args.no_stochastic,
    )

    print(f"Running backtest ({args.train_weeks}-week train, {args.horizon}-week horizon)…")
    engine = RollingOriginEngine(cfg)
    results_df = engine.run(orders_df, deliveries_df)

    if results_df.empty:
        print("Backtest produced no results.")
        sys.exit(1)

    summary = cost_per_kg_by_model(results_df)
    roi = compute_roi(results_df, annual_gmv_usd=args.gmv)

    print("\n── Model Comparison ──────────────────────────────────────")
    print(summary.to_string(index=False))
    print("\n── ROI Summary ───────────────────────────────────────────")
    for k, v in roi.items():
        if isinstance(v, float):
            print(f"  {k:<40} {v:>12,.1f}")
        else:
            print(f"  {k:<40} {str(v):>12}")


if __name__ == "__main__":
    main()
