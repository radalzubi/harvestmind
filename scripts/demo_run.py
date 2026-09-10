"""HarvestMind end-to-end demo run.

Steps:
  1. Initialize schema + seeds
  2. Generate 104 weeks of synthetic data
  3. Fit demand models (LightGBM global + intermittent selectors)
  4. Generate 50 supply scenarios
  5. Solve: deterministic LP, Γ=4 robust LP, two-stage SP (N=50 reduced to 20)
  6. Simulate recourse + compute metrics
  7. Print results table

Target runtime: < 90 seconds on a laptop.
"""

from __future__ import annotations

import sys
import time
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import duckdb  # noqa: E402  (sys.path set above so the script runs from any cwd)
import numpy as np  # noqa: E402  (sys.path set above so the script runs from any cwd)
import pandas as pd  # noqa: E402  (sys.path set above so the script runs from any cwd)


def section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def fmt_row(label: str, value: str, width: int = 42) -> str:
    return f"  {label:<{width}} {value}"


def main() -> None:
    t_start = time.time()
    print("\n" + "═" * 60)
    print("  HarvestMind  ·  End-to-End Demo")
    print("  Purdue University LIFT Lab  ·  v0.1.0")
    print("═" * 60)

    # ── Step 1: Schema + Seeds ────────────────────────────────────────
    section("Step 1 / 7 — Initialize database")
    from scripts.setup_db import setup_db

    conn = duckdb.connect(":memory:")
    setup_db(conn, load_seeds=True)
    n_products = conn.execute("SELECT COUNT(*) FROM dim_products").fetchone()[0]
    n_suppliers = conn.execute("SELECT COUNT(*) FROM dim_suppliers").fetchone()[0]
    print(fmt_row("Products loaded:", str(n_products)))
    print(fmt_row("Suppliers loaded:", str(n_suppliers)))
    print(f"  ✓ Schema ready ({time.time() - t_start:.1f}s)")

    # ── Step 2: Synthetic data ────────────────────────────────────────
    section("Step 2 / 7 — Generate 104-week synthetic dataset")
    from synthetic.generator import SyntheticGenerator

    gen = SyntheticGenerator(n_weeks=104, seed=42)
    counts = gen.generate_all(conn)
    for tbl, n in counts.items():
        print(fmt_row(f"  {tbl}:", f"{n:,} rows"))
    print(f"  ✓ Data generated ({time.time() - t_start:.1f}s)")

    # ── Step 3: Demand forecasting ────────────────────────────────────
    section("Step 3 / 7 — Fit demand models")
    orders_df = conn.execute(
        "SELECT ol.product_id, o.buyer_id, o.week_start, ol.qty_ordered_kg "
        "FROM fact_order_lines ol JOIN fact_orders o ON ol.order_id = o.order_id "
        "ORDER BY o.week_start"
    ).df()
    orders_df["week_start"] = pd.to_datetime(orders_df["week_start"])

    # LightGBM global model
    try:
        from forecasting.demand.lgbm_global_model import LGBMDemandModel

        lgbm = LGBMDemandModel(n_estimators=100, seed=42)
        lgbm.fit(orders_df)
        print(fmt_row("LightGBM global model:", "fitted"))
    except Exception as e:
        print(fmt_row("LightGBM global model:", f"SKIPPED ({e})"))

    # Intermittent model selection per product
    from forecasting.demand.intermittent_model import select_and_fit
    intermittent_products = ["PRD-006", "PRD-007", "PRD-009"]
    for pid in intermittent_products:
        series = orders_df[orders_df["product_id"] == pid].groupby("week_start")["qty_ordered_kg"].sum().values
        if len(series) > 0:
            fc = select_and_fit(series)
            print(fmt_row(f"  {pid} ({fc.model}):", f"{fc.mean:.1f} kg/wk ± {fc.std:.1f}"))

    print(f"  ✓ Forecasts ready ({time.time() - t_start:.1f}s)")

    # ── Step 4: Supply scenarios ──────────────────────────────────────
    section("Step 4 / 7 — Generate supply scenarios (N=50)")
    from forecasting.supply.yield_scenario_generator import YieldScenarioGenerator
    from optimization.scenario_reduction import reduce_scenarios

    yield_df = conn.execute(
        "SELECT supplier_id, product_id, harvest_week, realized_yield_kg_per_ha, "
        "planned_ha, total_kg_harvested FROM fact_yield_obs"
    ).df()

    # Pick a planning week 8 weeks before end of data (to leave room for realized horizon)
    last_week = orders_df["week_start"].max().date()
    planning_week = last_week - timedelta(weeks=8)
    scen_gen = YieldScenarioGenerator(n_scenarios=50, horizon_weeks=4, seed=42)
    scen_df = scen_gen.generate(planning_week=planning_week, yield_history=yield_df)

    reduced_df = reduce_scenarios(scen_df, target_k=20)
    print(fmt_row("Scenarios generated:", f"50 → reduced to {reduced_df['scenario_index'].nunique()}"))
    print(f"  ✓ Scenarios ready ({time.time() - t_start:.1f}s)")

    # ── Step 5: Optimization ──────────────────────────────────────────
    section("Step 5 / 7 — Solve optimization models")

    # Build demand and supply inputs
    mean_demand = (
        orders_df[orders_df["week_start"] < pd.Timestamp(planning_week)]
        .groupby("product_id")["qty_ordered_kg"].mean()
        .reset_index()
        .rename(columns={"qty_ordered_kg": "demand_kg"})
    )
    mean_demand["week_start"] = planning_week

    deliveries_df = conn.execute(
        "SELECT supplier_id, product_id, delivery_date, qty_received_kg FROM fact_deliveries"
    ).df()
    supply_agg = (
        deliveries_df.groupby(["supplier_id","product_id"])
        .agg(capacity_kg=("qty_received_kg","mean"))
        .reset_index()
        .assign(price_per_kg=2.0, week_start=planning_week)
    )

    results: dict[str, dict] = {}

    # Deterministic LP
    t0 = time.time()
    try:
        from optimization.lp_baseline import LPBaseline
        det_result = LPBaseline().solve(mean_demand, supply_agg)
        results["deterministic"] = det_result
        print(fmt_row("  Deterministic LP:", f"{det_result.get('status')} | obj=${det_result.get('objective') or 0:,.0f} | {time.time()-t0:.1f}s"))
    except Exception as e:
        print(fmt_row("  Deterministic LP:", f"FAILED: {e}"))

    # Γ=4 Robust LP
    t0 = time.time()
    try:
        from optimization.gamma_robust_lp import GammaRobustLP
        rob_result = GammaRobustLP(gamma=4.0).solve(mean_demand, supply_agg)
        results["gamma_robust_4"] = rob_result
        print(fmt_row("  Γ=4 Robust LP:", f"{rob_result.get('status')} | obj=${rob_result.get('objective') or 0:,.0f} | {time.time()-t0:.1f}s"))
    except Exception as e:
        print(fmt_row("  Γ=4 Robust LP:", f"FAILED: {e}"))

    # Two-stage SP
    t0 = time.time()
    try:
        from optimization.two_stage_sp import TwoStageStochasticLP

        # Build demand scenarios from yield scenarios
        demand_scen_rows = []
        n_scen_k = reduced_df["scenario_index"].nunique()
        for scen_idx in range(n_scen_k):
            w = 1.0 / n_scen_k
            for _, row in mean_demand.iterrows():
                noise = float(np.random.default_rng(scen_idx).normal(1.0, 0.15))
                demand_scen_rows.append({
                    "scenario_index": scen_idx,
                    "scenario_weight": w,
                    "product_id": row["product_id"],
                    "week_start": None,
                    "demand_kg": max(0.0, row["demand_kg"] * noise),
                })
        demand_scen = pd.DataFrame(demand_scen_rows)

        sp_result = TwoStageStochasticLP(n_scenarios=n_scen_k).solve(demand_scen, supply_agg)
        results["two_stage_sp"] = sp_result
        print(fmt_row("  Two-Stage SP (N=20):", f"{sp_result.get('status')} | obj=${sp_result.get('objective') or 0:,.0f} | {time.time()-t0:.1f}s"))
    except Exception as e:
        print(fmt_row("  Two-Stage SP:", f"FAILED: {e}"))

    print(f"  ✓ Optimization complete ({time.time() - t_start:.1f}s)")

    # ── Step 6: Recourse simulation ───────────────────────────────────
    section("Step 6 / 7 — Simulate recourse (realized demand)")
    from optimization.recourse_simulator import simulate_recourse

    # Realized demand: next 4 weeks post planning_week
    realized_demand = (
        orders_df[
            (orders_df["week_start"] >= pd.Timestamp(planning_week)) &
            (orders_df["week_start"] < pd.Timestamp(planning_week + timedelta(weeks=4)))
        ]
        .groupby("product_id")["qty_ordered_kg"]
        .sum()
        .reset_index()
        .rename(columns={"qty_ordered_kg": "demand_kg"})
    )
    if realized_demand.empty:
        # Fall back to mean demand as realized
        realized_demand = mean_demand[["product_id","demand_kg"]].copy()

    realized_supply = supply_agg[["supplier_id","product_id","capacity_kg"]].rename(
        columns={"capacity_kg": "actual_available_kg"}
    )

    model_metrics: list[dict] = []
    for model_name, result in results.items():
        if not result or result.get("status") not in ("optimal","locallyOptimal"):
            continue
        # Build commitment dataframe
        commit_rows = []
        for k, qty in result.get("x", {}).items():
            if qty is None or float(qty) < 1e-4:
                continue
            sup_id, prod_id = (k[0], k[1]) if isinstance(k, tuple) else (str(k), "?")
            commit_rows.append({
                "supplier_id": sup_id,
                "product_id": prod_id,
                "committed_kg": float(qty),
                "price_per_kg": 2.0,
            })
        if not commit_rows:
            continue
        commit_df = pd.DataFrame(commit_rows)
        recourse = simulate_recourse(commit_df, realized_demand, realized_supply)
        model_metrics.append({
            "Model": model_name,
            "Service Level": f"{recourse['service_level_pct']}%",
            "Spot (kg)": f"{recourse['spot_kg']:,.0f}",
            "Waste (kg)": f"{recourse['waste_kg']:,.0f}",
            "Spot Cost ($)": f"${recourse['spot_cost']:,.0f}",
            "Total Cost ($)": f"${recourse['total_cost']:,.0f}",
        })

    print(f"  ✓ Recourse simulated ({time.time() - t_start:.1f}s)")

    # ── Step 7: Results table ─────────────────────────────────────────
    section("Step 7 / 7 — Results")
    if model_metrics:
        metrics_df = pd.DataFrame(model_metrics)
        col_widths = {c: max(len(c), metrics_df[c].astype(str).str.len().max()) for c in metrics_df.columns}
        header = "  " + "  ".join(c.ljust(col_widths[c]) for c in metrics_df.columns)
        print(header)
        print("  " + "─" * (len(header) - 2))
        for _, row in metrics_df.iterrows():
            print("  " + "  ".join(str(row[c]).ljust(col_widths[c]) for c in metrics_df.columns))
    else:
        print("  No solver results to display (HiGHS may not be installed).")

    # ROI teaser
    from backtesting.roi_calculator import compute_roi

    # Build minimal backtest_df from our results for ROI calc
    bt_rows = []
    for m in model_metrics:
        bt_rows.append({
            "model": m["Model"],
            "origin_week": planning_week,
            "horizon_weeks": 4,
            "service_level_pct": float(m["Service Level"].rstrip("%")),
            "spot_kg": float(m["Spot (kg)"].replace(",","")),
            "waste_kg": float(m["Waste (kg)"].replace(",","")),
            "spot_cost_usd": float(m["Spot Cost ($)"].replace("$","").replace(",","")),
            "total_cost_usd": float(m["Total Cost ($)"].replace("$","").replace(",","")),
        })
    if len(bt_rows) >= 2:
        bt_df = pd.DataFrame(bt_rows)
        roi = compute_roi(bt_df, baseline_model=bt_rows[0]["model"],
                          target_model=bt_rows[-1]["model"])
        if "error" not in roi:
            print(f"\n  Estimated Annual Benefit:  ${roi.get('total_annual_benefit_usd',0):>10,.0f}")
            print(f"  ROI Multiple:              {roi.get('roi_multiple',0):>10.1f}×")
            print(f"  Payback Period:            {roi.get('payback_months',0):>10.1f} months")
    elif bt_rows:
        print("\n  (Only 1 model solved — need ≥2 for ROI comparison)")

    elapsed = time.time() - t_start
    print(f"\n{'═' * 60}")
    print(f"  Demo complete in {elapsed:.1f}s")
    if elapsed > 90:
        print("  ⚠  Target was <90s — consider reducing n_scenarios")
    else:
        print("  ✓ Under 90-second target")
    print(f"{'═' * 60}\n")

    conn.close()


if __name__ == "__main__":
    main()
