#!/usr/bin/env python3
"""Generate a 2-page pilot summary HTML / PDF for a partner.

Usage:
  python scripts/generate_pilot_summary.py \
      --partner "Hoosier Harvest Market" \
      --gmv 3000000 \
      --stress-test \
      --output outputs/hoosier_harvest_pilot_summary.html

Steps:
  1. Pre-flight: count fact_deliveries / fact_orders, fail fast if too sparse.
  2. Run RollingOriginEngine backtest end-to-end.
  3. compute_roi(...) for the headline numbers.
  4. (Optional) --stress-test → run scenarios.SCENARIOS sweep on naive degradation.
  5. Render HTML via reports.pilot_summary_generator.
  6. Print headline KPIs and the file path.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backtesting.roi_calculator import compute_roi  # noqa: E402  (sys.path set above so the script runs from any cwd)
from backtesting.rolling_origin_engine import BacktestConfig, RollingOriginEngine  # noqa: E402  (sys.path set above so the script runs from any cwd)
from dashboard.lib.metrics import data_quality_breakdown  # noqa: E402  (sys.path set above so the script runs from any cwd)
from reports.pilot_summary_generator import (  # noqa: E402  (sys.path set above so the script runs from any cwd)
    PilotSummaryError,
    render_pilot_summary,
)
from scripts.stress_test_backtest import SCENARIOS, run_one as stress_run_one  # noqa: E402  (sys.path set above so the script runs from any cwd)


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return s or "partner"


def _load(con: duckdb.DuckDBPyConnection):
    orders = con.execute("""
        SELECT ol.product_id, o.buyer_id, o.week_start, ol.qty_ordered_kg
        FROM fact_order_lines ol JOIN fact_orders o ON ol.order_id = o.order_id
    """).df()
    deliveries = con.execute("""
        SELECT supplier_id, product_id, delivery_date,
               qty_received_kg, qty_rejected_kg
        FROM fact_deliveries
    """).df()
    return orders, deliveries


def _preflight(con) -> None:
    n_d = con.execute("SELECT COUNT(*) FROM fact_deliveries").fetchone()[0]
    if n_d == 0:
        print("[FAIL] No delivery data. Run scripts/ingest_real_data.py first.", file=sys.stderr)
        sys.exit(2)
    n_w = con.execute("SELECT COUNT(DISTINCT week_start) FROM fact_orders").fetchone()[0]
    if n_w < 13:
        print(f"[FAIL] Need 13+ weeks of order history (have {n_w}).", file=sys.stderr)
        sys.exit(2)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default="harvestmind.duckdb")
    p.add_argument("--partner", required=True)
    p.add_argument("--gmv", type=float, required=True, help="Annual GMV in USD")
    p.add_argument("--output", default=None, help="HTML output path (default: outputs/{slug}_pilot_summary.html)")
    p.add_argument("--as-pdf", action="store_true")
    p.add_argument("--train-weeks", type=int, default=26)
    p.add_argument("--horizon", type=int, default=4)
    p.add_argument("--scenarios", type=int, default=30)
    p.add_argument("--stress-test", action="store_true")
    p.add_argument("--spot-capacity-factor", type=float, default=0.30)
    p.add_argument("--lost-sale-per-kg", type=float, default=3.0)
    args = p.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"[ERROR] DB not found: {db_path}", file=sys.stderr)
        sys.exit(2)

    con = duckdb.connect(str(db_path), read_only=True)
    _preflight(con)
    orders, deliveries = _load(con)

    print(f"\nRunning backtest for '{args.partner}'...")
    cfg = BacktestConfig(
        n_train_weeks=args.train_weeks,
        horizon_weeks=args.horizon,
        step_weeks=8,
        n_scenarios=args.scenarios,
        gammas=[0, 4],
        run_stochastic=True,
        run_naive_baseline=True,
        spot_capacity_factor=args.spot_capacity_factor,
        lost_sale_per_kg_usd=args.lost_sale_per_kg,
    )
    backtest_df = RollingOriginEngine(cfg).run(orders, deliveries)
    if backtest_df.empty:
        print("[ERROR] Backtest produced no results.", file=sys.stderr)
        sys.exit(1)

    print("Computing ROI...")
    roi = compute_roi(
        backtest_df,
        baseline_model="naive_lastyear",
        target_model="two_stage_sp",
        annual_gmv_usd=args.gmv,
    )

    stress_df: pd.DataFrame | None = None
    if args.stress_test:
        print("Running stress test...")
        rows = []
        for s in SCENARIOS:
            r = stress_run_one(orders, deliveries, s, cfg)
            if "error" not in r:
                rows.append(r)
        if rows:
            stress_df = pd.DataFrame(rows)

    dq = [
        {"dataset": d.dataset, "rows": d.rows, "status": d.status}
        for d in data_quality_breakdown(con)
    ]
    con.close()

    output = Path(args.output) if args.output else (
        ROOT / "outputs" / f"{_slug(args.partner)}_pilot_summary.html"
    )

    try:
        _html = render_pilot_summary(
            roi=roi,
            backtest_df=backtest_df,
            partner_name=args.partner,
            output_path=output,
            as_pdf=args.as_pdf,
            stress_test_df=stress_df,
            data_quality=dq,
        )
    except PilotSummaryError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    band_dollar = "$30K – $40K"
    band_roi = "1.5× – 2.0×"
    if stress_df is not None and not stress_df.empty:
        rows = stress_df[stress_df["missing_rate"].isin([0.30, 0.50])]
        if not rows.empty:
            usd_lo = rows["annual_saved_usd"].min()
            usd_hi = rows["annual_saved_usd"].max()
            band_dollar = f"${int(round(usd_lo)):,} – ${int(round(usd_hi)):,}"
            roi_lo = rows["roi"].min()
            roi_hi = rows["roi"].max()
            band_roi = f"{roi_lo:.1f}× – {roi_hi:.1f}×"

    print()
    print("══════════════════════════════════════════════════════════")
    print(f"Pilot Summary — {args.partner}")
    print("──────────────────────────────────────────────────────────")
    print(f"  Annual benefit:   ${int(roi['total_annual_benefit_usd']):,}    (real-world est. {band_dollar})")
    print(f"  ROI multiple:     {roi['roi_multiple']}×    (real-world est. {band_roi})")
    print(f"  Payback period:   {roi['payback_months']} months")
    print(f"  Fill rate lift:   +{roi['service_level_improvement_pts']} pts")
    if roi.get("annual_vss_usd") is not None:
        print(f"  VSS (stochastic): ${int(roi['annual_vss_usd']):,}")
    print("──────────────────────────────────────────────────────────")
    print(f"  Output: {output}")
    if args.as_pdf:
        pdf = output.with_suffix(".pdf")
        if pdf.exists():
            print(f"  PDF:    {pdf}")
        else:
            print("  PDF:    weasyprint not available — HTML only")
    print("══════════════════════════════════════════════════════════")


if __name__ == "__main__":
    main()
