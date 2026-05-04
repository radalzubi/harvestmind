"""Planning API router: run optimization and fetch recommendations."""

from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_conn
from api.models.schemas import PlanningRequest, PlanningResponse, CommitmentResponse

router = APIRouter(prefix="/planning", tags=["planning"])


@router.post("/run", response_model=PlanningResponse)
def run_planning(req: PlanningRequest, conn=Depends(get_conn)):
    """Run the optimization model for a given week and return commitments."""
    from optimization.lp_baseline import LPBaseline
    from optimization.gamma_robust_lp import GammaRobustLP
    from optimization.two_stage_sp import TwoStageStochasticLP
    from optimization.cvar_extension import CVaRStochasticLP
    from forecasting.supply.yield_scenario_generator import YieldScenarioGenerator

    run_id = str(uuid.uuid4())[:8]
    t0 = time.time()

    # Fetch data from DB
    orders_df = conn.execute(
        "SELECT product_id, week_start, SUM(qty_ordered_kg) AS demand_kg "
        "FROM fact_order_lines ol JOIN fact_orders o ON ol.order_id = o.order_id "
        "WHERE o.week_start >= ? - INTERVAL 52 WEEKS GROUP BY 1,2",
        [req.week_start],
    ).df()

    supply_df = conn.execute(
        "SELECT supplier_id, product_id, delivery_date AS week_start, "
        "AVG(qty_received_kg) AS capacity_kg, 2.0 AS price_per_kg "
        "FROM fact_deliveries WHERE delivery_date >= ? - INTERVAL 52 WEEKS "
        "GROUP BY 1,2,3",
        [req.week_start],
    ).df()

    if orders_df.empty:
        raise HTTPException(status_code=422, detail="No demand data available for planning")

    # Build a simple current-week demand
    mean_demand = orders_df.groupby("product_id")["demand_kg"].mean().reset_index()
    mean_demand["week_start"] = req.week_start

    supply_agg = supply_df.groupby(["supplier_id","product_id"]).agg(
        capacity_kg=("capacity_kg","mean"),
        price_per_kg=("price_per_kg","mean"),
    ).reset_index().assign(week_start=req.week_start)

    result: dict = {}
    if req.model_type == "deterministic":
        result = LPBaseline().solve(mean_demand, supply_agg)
    elif req.model_type == "gamma_robust":
        result = GammaRobustLP(gamma=req.gamma).solve(mean_demand, supply_agg)
    elif req.model_type == "two_stage_sp":
        from datetime import timedelta
        scen_gen = YieldScenarioGenerator(n_scenarios=req.n_scenarios)
        scen_df = scen_gen.generate(req.week_start + timedelta(weeks=1))
        # Simple demand scenarios: perturb mean by yield factor
        from optimization.two_stage_sp import TwoStageStochasticLP
        demand_scen = _build_demand_scenarios(mean_demand, scen_df, req.n_scenarios)
        result = TwoStageStochasticLP(n_scenarios=req.n_scenarios).solve(demand_scen, supply_agg)
    elif req.model_type == "cvar":
        from datetime import timedelta
        scen_gen = YieldScenarioGenerator(n_scenarios=req.n_scenarios)
        scen_df = scen_gen.generate(req.week_start + timedelta(weeks=1))
        demand_scen = _build_demand_scenarios(mean_demand, scen_df, req.n_scenarios)
        result = CVaRStochasticLP(lambda_weight=req.lambda_cvar, alpha=req.alpha_cvar).solve(demand_scen, supply_agg)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown model_type: {req.model_type}")

    solve_time = round(time.time() - t0, 2)

    # Parse commitments
    commitments = []
    for k, qty in result.get("x", {}).items():
        if qty is None or float(qty) < 1e-4:
            continue
        sup_id, prod_id = (k[0], k[1]) if isinstance(k, tuple) else (str(k), "?")
        commitments.append(CommitmentResponse(
            supplier_id=sup_id,
            product_id=prod_id,
            week_start=req.week_start,
            committed_kg=round(float(qty), 2),
            spot_kg=0.0,
            price_per_kg=None,
            decision_stage="first",
        ))

    total_spot = sum(
        float(v) for v in result.get("spot", {}).values() if v and float(v) > 0
    )
    total_waste = sum(
        float(v) for v in result.get("waste", {}).values() if v and float(v) > 0
    )
    return PlanningResponse(
        run_id=run_id,
        model_type=req.model_type,
        week_start=req.week_start,
        objective=result.get("objective"),
        solver_status=result.get("status", "unknown"),
        solve_time_s=solve_time,
        expected_spot_kg=round(total_spot, 2),
        expected_waste_kg=round(total_waste, 2),
        commitments=commitments,
        recommendations=[],
    )


def _build_demand_scenarios(mean_demand, yield_scen_df, n_scenarios):
    import pandas as pd
    import numpy as np
    rows = []
    for scen_idx in range(n_scenarios):
        scen = yield_scen_df[yield_scen_df["scenario_index"] == scen_idx]
        weight = 1.0 / n_scenarios
        for _, row in mean_demand.iterrows():
            noise = float(np.random.default_rng(scen_idx).normal(1.0, 0.15))
            rows.append({
                "scenario_index": scen_idx,
                "scenario_weight": weight,
                "product_id": row["product_id"],
                "week_start": None,
                "demand_kg": max(0.0, row["demand_kg"] * noise),
            })
    return pd.DataFrame(rows)


@router.get("/recommendations")
def get_recommendations(status: str = "open", conn=Depends(get_conn)):
    """Fetch open recommendations from the planning output table."""
    df = conn.execute(
        "SELECT * FROM planning_recommendations WHERE status = ? ORDER BY priority, generated_at DESC",
        [status],
    ).df()
    return df.to_dict("records")
