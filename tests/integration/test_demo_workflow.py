"""Smoke test: the full HarvestMind workflow runs end-to-end on synthetic data.

This is a thinner version of scripts/demo_run.py — it exercises every layer
(schema setup → synthetic generator → forecasting → optimization → recourse)
in-memory so CI can catch wiring breakage without writing files or waiting
the full 90-second demo.
"""

from __future__ import annotations

from datetime import timedelta

import duckdb
import numpy as np
import pandas as pd
import pytest

from optimization.gamma_robust_lp import GammaRobustLP
from optimization.lp_baseline import LPBaseline
from optimization.recourse_simulator import simulate_recourse
from optimization.two_stage_sp import TwoStageStochasticLP
from scripts.setup_db import setup_db
from synthetic.generator import SyntheticGenerator


@pytest.fixture(scope="module")
def populated_db():
    conn = duckdb.connect(":memory:")
    setup_db(conn, load_seeds=True)
    SyntheticGenerator(n_weeks=20, seed=11).generate_all(conn)
    yield conn
    conn.close()


def test_end_to_end_demo(populated_db):
    conn = populated_db

    # ── pull data the way the real demo does ──────────────────────────
    orders_df = conn.execute(
        "SELECT ol.product_id, o.buyer_id, o.week_start, ol.qty_ordered_kg "
        "FROM fact_order_lines ol JOIN fact_orders o ON ol.order_id = o.order_id"
    ).df()
    assert not orders_df.empty
    orders_df["week_start"] = pd.to_datetime(orders_df["week_start"])

    deliveries_df = conn.execute(
        "SELECT supplier_id, product_id, delivery_date, qty_received_kg "
        "FROM fact_deliveries"
    ).df()
    assert not deliveries_df.empty

    # ── pick a planning week with realised data after it ──────────────
    planning_week = orders_df["week_start"].max().date() - timedelta(weeks=4)

    mean_demand = (
        orders_df[orders_df["week_start"] < pd.Timestamp(planning_week)]
        .groupby("product_id")["qty_ordered_kg"]
        .mean()
        .reset_index()
        .rename(columns={"qty_ordered_kg": "demand_kg"})
    )
    mean_demand["week_start"] = planning_week

    supply_agg = (
        deliveries_df.groupby(["supplier_id", "product_id"])
        .agg(capacity_kg=("qty_received_kg", "mean"))
        .reset_index()
        .assign(price_per_kg=2.0, week_start=planning_week)
    )

    # ── solve all three optimisers ────────────────────────────────────
    det = LPBaseline().solve(mean_demand, supply_agg)
    rob = GammaRobustLP(gamma=4.0).solve(mean_demand, supply_agg)

    # build minimal demand scenarios for the SP
    rng = np.random.default_rng(0)
    n_scen = 5
    rows = []
    for s in range(n_scen):
        for _, row in mean_demand.iterrows():
            rows.append({
                "scenario_index": s,
                "scenario_weight": 1.0 / n_scen,
                "product_id": row["product_id"],
                "week_start": planning_week,
                "demand_kg": max(0.0, row["demand_kg"] * float(rng.normal(1.0, 0.1))),
            })
    demand_scen = pd.DataFrame(rows)

    sp = TwoStageStochasticLP(n_scenarios=n_scen).solve(demand_scen, supply_agg)

    for name, result in [("det", det), ("rob", rob), ("sp", sp)]:
        assert result.get("status") in ("optimal", "locallyOptimal"), \
            f"{name} did not solve: {result.get('status')}"
        assert result.get("objective") is not None
        assert result["objective"] >= 0

    # gamma_robust must not undercut deterministic (regression: arbitrage bug)
    assert rob["objective"] >= det["objective"] - 1e-6

    # ── simulate recourse on the deterministic result ─────────────────
    realized_demand = mean_demand[["product_id", "demand_kg"]].copy()
    realized_supply = supply_agg.rename(columns={"capacity_kg": "actual_available_kg"})

    commit_rows = []
    for (i, j, t), qty in det["x"].items():
        if qty and qty > 1e-4:
            commit_rows.append({
                "supplier_id": i, "product_id": j,
                "committed_kg": float(qty), "price_per_kg": 2.0,
            })
    commitments = pd.DataFrame(commit_rows) if commit_rows else pd.DataFrame(
        columns=["supplier_id", "product_id", "committed_kg", "price_per_kg"]
    )
    rec = simulate_recourse(commitments, realized_demand, realized_supply)
    assert rec["service_level_pct"] == 100.0
    assert rec["total_cost"] >= 0
