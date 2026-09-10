#!/usr/bin/env python3
"""Run the rolling-origin backtest on real data, compute headline KPIs,
and emit a JSON file the Next.js dashboard imports.

Output schema (web/src/lib/backtest_summary.json):
  generated_at:               ISO timestamp
  config:                     {n_origins, horizon_weeks, step_weeks, n_scenarios}
  baseline_model:             "naive_lastyear"
  optimised_model:            "two_stage_sp"
  kpis:
    annual_savings_usd:       opt vs baseline, scaled to 52 weeks
    spot_premium_savings_usd
    waste_reduction_usd
    fill_rate_baseline
    fill_rate_optimised
    fill_rate_lift_pts
    cost_per_kg_baseline
    cost_per_kg_optimised
    roi_multiple              (annual_savings / annual_subscription)
    annual_subscription_usd
    confidence_low_usd / confidence_high_usd
  per_origin:                 list[{origin, naive_*, opt_*, saved_*}]
  cost_trend:                 [{week, baseline_$, optimised_$}] for the chart
  raw_n_origins:              count actually run

Usage:
  python scripts/build_dashboard_summary.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backtesting.rolling_origin_engine import BacktestConfig, RollingOriginEngine  # noqa: E402  (sys.path set above so the script runs from any cwd)

DEFAULT_DB = ROOT / "harvestmind.duckdb"
DEFAULT_OUT = ROOT / "web" / "src" / "lib" / "backtest_summary.json"
ANNUAL_SUBSCRIPTION_USD = 18_000
HORIZON_PERIODS_PER_YEAR = 52 / 4   # 4-week horizons


def load_orders_deliveries(con: duckdb.DuckDBPyConnection) -> tuple[pd.DataFrame, pd.DataFrame]:
    orders = con.execute("""
        SELECT
            ol.product_id,
            o.buyer_id,
            o.week_start,
            ol.qty_ordered_kg
        FROM fact_order_lines ol
        JOIN fact_orders o ON ol.order_id = o.order_id
    """).df()
    deliveries = con.execute("""
        SELECT supplier_id, product_id, delivery_date,
               qty_received_kg, qty_rejected_kg
        FROM fact_deliveries
    """).df()
    return orders, deliveries


def aggregate_kpis(
    results: pd.DataFrame,
    baseline_model: str,
    optimised_model: str,
    n_origins: int,
    horizon_weeks: int,
) -> dict:
    """Compute headline KPIs by joining baseline & optimised rows on origin_week."""
    base = results[results["model"] == baseline_model].set_index("origin_week")
    opt = results[results["model"] == optimised_model].set_index("origin_week")
    common = base.index.intersection(opt.index)
    if len(common) == 0:
        raise RuntimeError(
            f"No overlapping origins between {baseline_model} and {optimised_model}"
        )
    base = base.loc[common]
    opt = opt.loc[common]

    # Period totals
    base_total = base["total_cost_usd"].sum()
    opt_total = opt["total_cost_usd"].sum()
    base_spot = base["spot_cost_usd"].sum()
    opt_spot = opt["spot_cost_usd"].sum()
    base_waste = base["waste_cost_usd"].sum()
    opt_waste = opt["waste_cost_usd"].sum()

    base_fill = float(base["service_level_pct"].mean())
    opt_fill = float(opt["service_level_pct"].mean())

    period_saved = base_total - opt_total
    spot_saved = base_spot - opt_spot
    waste_saved = base_waste - opt_waste

    # Annualize
    n = len(common)
    horizons_per_year = 52 / horizon_weeks
    scale = horizons_per_year / n
    annual_saved = period_saved * scale
    annual_spot_saved = spot_saved * scale
    annual_waste_saved = waste_saved * scale

    # Cost per kg (committed cost / committed kg, taken from results)
    # We approximate "kg moved" via demand_kg implied by service-level math; but
    # the engine doesn't store demand_kg in BacktestResult, so we report cost/kg
    # using committed kg (= sum of received under realized supply). For a safer
    # proxy here we use total_cost_usd ÷ (waste_kg + spot_kg + serviced_kg).
    # When unavailable, fall back to None.
    base_cost_per_kg = None
    opt_cost_per_kg = None

    # Confidence interval from per-origin variance
    saved_per_origin = (base["total_cost_usd"] - opt["total_cost_usd"]).values
    if n > 1:
        std = float(np.std(saved_per_origin, ddof=1)) * float(np.sqrt(horizons_per_year))
    else:
        std = 0.0
    ci_low = annual_saved - 1.96 * std
    ci_high = annual_saved + 1.96 * std

    roi = annual_saved / ANNUAL_SUBSCRIPTION_USD if ANNUAL_SUBSCRIPTION_USD else 0.0

    # Value of Stochastic Solution (per origin: deterministic_cost - sp_cost)
    annual_vss_usd: float | None = None
    if "deterministic" in results["model"].unique() and "two_stage_sp" in results["model"].unique():
        det = results[results["model"] == "deterministic"].set_index("origin_week")
        sp = results[results["model"] == "two_stage_sp"].set_index("origin_week")
        common = det.index.intersection(sp.index)
        if len(common) > 0:
            vss_per_origin = det.loc[common, "total_cost_usd"] - sp.loc[common, "total_cost_usd"]
            annual_vss_usd = round(float(vss_per_origin.mean() * scale), 0)

    return {
        "annual_savings_usd": round(annual_saved, 0),
        "annual_spot_premium_savings_usd": round(annual_spot_saved, 0),
        "annual_waste_reduction_usd": round(annual_waste_saved, 0),
        "fill_rate_baseline": round(base_fill, 2),
        "fill_rate_optimised": round(opt_fill, 2),
        "fill_rate_lift_pts": round(opt_fill - base_fill, 2),
        "cost_per_kg_baseline": base_cost_per_kg,
        "cost_per_kg_optimised": opt_cost_per_kg,
        "roi_multiple": round(roi, 2),
        "annual_subscription_usd": ANNUAL_SUBSCRIPTION_USD,
        "confidence_low_usd": round(ci_low, 0),
        "confidence_high_usd": round(ci_high, 0),
        "period_saved_usd": round(period_saved, 0),
        "period_spot_saved_usd": round(spot_saved, 0),
        "period_waste_saved_usd": round(waste_saved, 0),
        "spot_kg_avoided_period": round(float(base["spot_kg"].sum() - opt["spot_kg"].sum()), 0),
        "waste_kg_avoided_period": round(float(base["waste_kg"].sum() - opt["waste_kg"].sum()), 0),
        "lost_sale_kg_baseline": round(float(base["lost_sale_kg"].fillna(0).sum()), 0),
        "lost_sale_kg_optimised": round(float(opt["lost_sale_kg"].fillna(0).sum()), 0),
        "annual_vss_usd": annual_vss_usd,
    }


def build_per_origin(
    results: pd.DataFrame, baseline_model: str, optimised_model: str
) -> list[dict]:
    base = results[results["model"] == baseline_model].set_index("origin_week")
    opt = results[results["model"] == optimised_model].set_index("origin_week")
    common = sorted(base.index.intersection(opt.index))
    rows = []
    for o in common:
        b, p = base.loc[o], opt.loc[o]
        rows.append({
            "origin": str(o),
            "baseline_total_cost": round(float(b["total_cost_usd"]), 0),
            "optimised_total_cost": round(float(p["total_cost_usd"]), 0),
            "saved": round(float(b["total_cost_usd"] - p["total_cost_usd"]), 0),
            "baseline_fill_pct": round(float(b["service_level_pct"]), 1),
            "optimised_fill_pct": round(float(p["service_level_pct"]), 1),
            "baseline_waste_kg": round(float(b["waste_kg"]), 0),
            "optimised_waste_kg": round(float(p["waste_kg"]), 0),
            "baseline_spot_kg": round(float(b["spot_kg"]), 0),
            "optimised_spot_kg": round(float(p["spot_kg"]), 0),
            "baseline_lost_kg": round(float(b["lost_sale_kg"] or 0), 0),
            "optimised_lost_kg": round(float(p["lost_sale_kg"] or 0), 0),
        })
    return rows


def build_cost_trend(
    results: pd.DataFrame, baseline_model: str, optimised_model: str
) -> list[dict]:
    """One row per origin → drives the dashboard's cost-trend chart."""
    base = results[results["model"] == baseline_model].set_index("origin_week")
    opt = results[results["model"] == optimised_model].set_index("origin_week")
    common = sorted(base.index.intersection(opt.index))
    out = []
    for o in common:
        date_str = pd.Timestamp(o).strftime("%b %d")
        out.append({
            "label": date_str,
            "baseline": round(float(base.loc[o, "total_cost_usd"]), 0),
            "optimised": round(float(opt.loc[o, "total_cost_usd"]), 0),
        })
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--out", default=str(DEFAULT_OUT))
    p.add_argument("--n-train-weeks", type=int, default=26)
    p.add_argument("--horizon-weeks", type=int, default=4)
    p.add_argument("--step-weeks", type=int, default=8)
    p.add_argument("--n-scenarios", type=int, default=20)
    p.add_argument("--spot-capacity-factor", type=float, default=0.30,
                   help="Cap spot procurement at this fraction of demand "
                        "(default 0.30 = 30%% of demand can be spot-sourced).")
    p.add_argument("--lost-sale-per-kg", type=float, default=1.50)
    args = p.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"[ERROR] DB not found: {db_path}", file=sys.stderr)
        sys.exit(2)

    con = duckdb.connect(str(db_path), read_only=True)
    orders, deliveries = load_orders_deliveries(con)
    print(f"[INFO] orders={len(orders):,}  deliveries={len(deliveries):,}")

    cfg = BacktestConfig(
        n_train_weeks=args.n_train_weeks,
        horizon_weeks=args.horizon_weeks,
        step_weeks=args.step_weeks,
        n_scenarios=args.n_scenarios,
        gammas=[0],   # cheap; we don't surface robust on the dashboard
        run_stochastic=True,
        run_naive_baseline=True,
        spot_capacity_factor=args.spot_capacity_factor,
        lost_sale_per_kg_usd=args.lost_sale_per_kg,
    )
    print(f"[INFO] config: {cfg}")

    results = RollingOriginEngine(cfg).run(orders, deliveries)
    if results.empty:
        print("[ERROR] backtest produced no results.", file=sys.stderr)
        sys.exit(1)

    baseline_model = "naive_lastyear"
    optimised_model = "two_stage_sp"

    if baseline_model not in results["model"].unique():
        print(f"[WARN] {baseline_model} not in results — falling back to deterministic.")
        baseline_model = "deterministic"

    n_origins_kept = results["origin_week"].nunique()
    kpis = aggregate_kpis(results, baseline_model, optimised_model,
                          n_origins=n_origins_kept,
                          horizon_weeks=args.horizon_weeks)

    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "config": {
            "n_origins": n_origins_kept,
            "n_train_weeks": args.n_train_weeks,
            "horizon_weeks": args.horizon_weeks,
            "step_weeks": args.step_weeks,
            "n_scenarios": args.n_scenarios,
            "spot_capacity_factor": args.spot_capacity_factor,
        },
        "baseline_model": baseline_model,
        "optimised_model": optimised_model,
        "kpis": kpis,
        "per_origin": build_per_origin(results, baseline_model, optimised_model),
        "cost_trend": build_cost_trend(results, baseline_model, optimised_model),
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str))
    print(f"[OK] wrote {out_path}")
    print(f"[OK] KPIs: annual_savings ${kpis['annual_savings_usd']:,.0f} | "
          f"spot saved ${kpis['annual_spot_premium_savings_usd']:,.0f} | "
          f"waste saved ${kpis['annual_waste_reduction_usd']:,.0f} | "
          f"fill {kpis['fill_rate_baseline']:.1f}% → {kpis['fill_rate_optimised']:.1f}% | "
          f"ROI {kpis['roi_multiple']}×")


if __name__ == "__main__":
    main()
