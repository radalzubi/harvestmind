#!/usr/bin/env python3
"""HarvestMind stress test: degrade the naive baseline, watch optimizer advantage grow.

Real food hubs don't have perfect last-year-same-week spreadsheets. They have
spreadsheets with missing weeks, supplier turnover, and noisy quantities.
This script sweeps the degradation knobs on the naive baseline and reports
the optimizer's advantage at each level.

Output is the table you put on the partner-deck economics slide.

Usage:
  python scripts/stress_test_backtest.py [--db PATH] [--gmv USD]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backtesting.rolling_origin_engine import BacktestConfig, RollingOriginEngine  # noqa: E402  (sys.path set above so the script runs from any cwd)

DEFAULT_DB = ROOT / "harvestmind.duckdb"


SCENARIOS = [
    # (label, missing_rate, noise_cv, supplier_turnover_rate)
    ("Perfect (synthetic)",      0.00, 0.00, 0.00),
    ("Light    (15% missing)",   0.15, 0.10, 0.05),
    ("Medium   (30% missing)",   0.30, 0.20, 0.10),
    ("Heavy    (50% missing)",   0.50, 0.30, 0.20),
]


def load(con: duckdb.DuckDBPyConnection):
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


def run_one(orders, deliveries, scenario, base_cfg) -> dict:
    label, miss, noise, turnover = scenario
    cfg = BacktestConfig(**{**base_cfg.__dict__})
    cfg.naive_missing_rate = miss
    cfg.naive_noise_cv = noise
    cfg.naive_supplier_turnover_rate = turnover

    results = RollingOriginEngine(cfg).run(orders, deliveries)
    if results.empty:
        return {"label": label, "error": "no results"}

    base = results[results["model"] == "naive_lastyear"].set_index("origin_week")
    sp = results[results["model"] == "two_stage_sp"].set_index("origin_week")
    common = base.index.intersection(sp.index)
    if len(common) == 0:
        return {"label": label, "error": "no overlapping origins"}

    base = base.loc[common]
    sp = sp.loc[common]

    n = len(common)
    horizons_per_year = 52 / cfg.horizon_weeks
    scale = horizons_per_year / n

    annual_saved = float((base["total_cost_usd"].sum() - sp["total_cost_usd"].sum()) * scale)
    annual_spot_saved = float((base["spot_cost_usd"].sum() - sp["spot_cost_usd"].sum()) * scale)
    annual_waste_saved_kg = float((base["waste_kg"].sum() - sp["waste_kg"].sum()) * scale)
    fill_lift_pts = float(sp["service_level_pct"].mean() - base["service_level_pct"].mean())
    roi = annual_saved / 18_000.0

    return {
        "label": label,
        "missing_rate": miss,
        "noise_cv": noise,
        "turnover": turnover,
        "annual_saved_usd": round(annual_saved, 0),
        "annual_spot_saved_usd": round(annual_spot_saved, 0),
        "annual_waste_kg_saved": round(annual_waste_saved_kg, 0),
        "fill_lift_pts": round(fill_lift_pts, 2),
        "roi": round(roi, 2),
        "n_origins": n,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--horizon-weeks", type=int, default=4)
    p.add_argument("--step-weeks", type=int, default=8)
    p.add_argument("--n-scenarios", type=int, default=20)
    p.add_argument("--n-train-weeks", type=int, default=26)
    p.add_argument("--spot-capacity-factor", type=float, default=0.30)
    p.add_argument("--lost-sale-per-kg", type=float, default=3.0)
    args = p.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"[ERROR] DB not found: {db_path}", file=sys.stderr)
        sys.exit(2)

    con = duckdb.connect(str(db_path), read_only=True)
    orders, deliveries = load(con)

    base_cfg = BacktestConfig(
        n_train_weeks=args.n_train_weeks,
        horizon_weeks=args.horizon_weeks,
        step_weeks=args.step_weeks,
        n_scenarios=args.n_scenarios,
        gammas=[0],
        run_stochastic=True,
        run_naive_baseline=True,
        spot_capacity_factor=args.spot_capacity_factor,
        lost_sale_per_kg_usd=args.lost_sale_per_kg,
    )

    print("\n" + "═" * 78)
    print(" HarvestMind Baseline Degradation Stress Test")
    print(" Real partners' historical-data quality is rarely 'perfect'. As the")
    print(" naive baseline degrades, the stochastic optimiser's advantage grows.")
    print("═" * 78)

    results = []
    for s in SCENARIOS:
        print(f"\nRunning scenario: {s[0]}")
        r = run_one(orders, deliveries, s, base_cfg)
        results.append(r)
        if "error" in r:
            print(f"  [ERROR] {r['error']}")
            continue
        print(
            f"  saved=${r['annual_saved_usd']:>8,.0f}/yr  "
            f"spot=${r['annual_spot_saved_usd']:>7,.0f}/yr  "
            f"waste={r['annual_waste_kg_saved']:>6,.0f} kg/yr  "
            f"fill {r['fill_lift_pts']:+.1f} pts  "
            f"ROI {r['roi']}×"
        )

    print("\n" + "═" * 78)
    print(f"{'Scenario':<26} {'ROI':>8} {'Fill lift':>10} {'$/yr saved':>14} {'Waste kg/yr':>14}")
    print("─" * 78)
    for r in results:
        if "error" in r:
            print(f"{r['label']:<26} {'ERR':>8}")
            continue
        print(
            f"{r['label']:<26} {r['roi']:>7.2f}× {r['fill_lift_pts']:>+9.1f}p "
            f"${r['annual_saved_usd']:>12,.0f} {r['annual_waste_kg_saved']:>13,.0f}"
        )
    print("═" * 78)

    out_path = Path("/tmp/hm_stress_test.csv")
    pd.DataFrame(results).to_csv(out_path, index=False)
    print(f"\n[OK] saved to {out_path}")


if __name__ == "__main__":
    main()
