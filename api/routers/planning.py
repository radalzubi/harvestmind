"""Planning API router: run optimization and fetch recommendations."""

from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_conn, rate_limiter
from api.models.schemas import PlanningRequest, PlanningResponse, CommitmentResponse

router = APIRouter(prefix="/planning", tags=["planning"])


@router.post("/run", response_model=PlanningResponse, deprecated=True)
def run_planning(req: PlanningRequest, conn=Depends(get_conn)):
    """Run a legacy fact-table deterministic or gamma-robust plan.

    Stochastic planning is deliberately unavailable here. The production
    candidate is the staging-first ``/planning/two-sided`` path, which fits
    demand and supplier-yield uncertainty from the same operator history and
    applies honest product economics. Maintaining two stochastic paths made it
    possible to surface materially different commitments for the same data.
    """
    from optimization.lp_baseline import LPBaseline
    from optimization.gamma_robust_lp import GammaRobustLP

    if req.model_type not in {"deterministic", "gamma_robust"}:
        raise HTTPException(
            status_code=422,
            detail=(
                f"model_type {req.model_type!r} is not available on the legacy "
                "/planning/run route. Use POST /planning/two-sided for the "
                "canonical stochastic, staging-first plan."
            ),
        )

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
    else:
        raise HTTPException(status_code=400, detail=f"Unknown model_type: {req.model_type}")

    solve_time = round(time.time() - t0, 2)

    # Refuse to surface non-optimal solver outputs as recommendations.
    # `infeasible`, `unbounded`, `timeout`, etc. → 422, not silent success.
    solver_status = result.get("status", "unknown")
    if solver_status not in ("optimal", "locallyOptimal"):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Solver returned non-optimal status {solver_status!r}; "
                "no commitments produced."
            ),
        )

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
            quantity=round(float(qty), 2),
            unit="kg",
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

_REC_STATUS_VALUES = {"open", "actioned", "dismissed", "expired"}


@router.get("/recommendations")
def get_recommendations(status: str = "open", conn=Depends(get_conn)):
    """Fetch recommendations from the planning output table.

    ``status`` must be one of: open, actioned, dismissed, expired.
    """
    if status not in _REC_STATUS_VALUES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"status must be one of {sorted(_REC_STATUS_VALUES)}, "
                f"got {status!r}"
            ),
        )
    df = conn.execute(
        "SELECT * FROM planning_recommendations WHERE status = ? "
        "ORDER BY priority, generated_at DESC",
        [status],
    ).df()
    return df.to_dict("records")


@router.post("/two-sided", dependencies=[Depends(rate_limiter)])
def two_sided_plan(
    service_level_floor: float | None = Query(default=None, ge=0.0, le=1.0),
    diversification_cap: float | None = Query(default=None, gt=0.0, le=1.0),
    spot_cost_multiplier: float | None = Query(default=None, ge=1.0, le=5.0),
    spot_capacity_factor: float | None = Query(default=None, ge=0.0, le=1.0),
    enforce_backtest_gate: bool = True,
    conn=Depends(get_conn),
):
    """Two-sided stochastic plan (demand AND supplier yield uncertain),
    newsvendor objective, honest per-product penalties. When spot
    economics are not supplied, returns a sensitivity band across a
    plausible grid instead of silently assuming cheap spot."""
    from backtesting.benchmark_suite import run_benchmark
    from risk.scenario_generation import run_two_stage_two_sided

    # A complex policy is not allowed to graduate into commitments merely
    # because the solver found an optimum. It must first beat the deterministic
    # and run-rate baselines on held-out operator history. Diagnostic users can
    # still inspect an un-gated plan explicitly, but the default pilot path is
    # fail-closed.
    benchmark = run_benchmark(
        conn,
        spot_cost_multiplier=(
            spot_cost_multiplier if spot_cost_multiplier is not None else 1.30
        ),
        spot_capacity_factor=(
            spot_capacity_factor if spot_capacity_factor is not None else 0.30
        ),
    )
    if enforce_backtest_gate and benchmark.get("gate_passed") is not True:
        raise HTTPException(
            status_code=422,
            detail={
                "message": (
                    "Stochastic commitments are blocked until the rolling-origin "
                    "benchmark beats both the deterministic LP and run-rate baseline."
                ),
                "benchmark_status": benchmark.get("status"),
                "gate_passed": benchmark.get("gate_passed"),
                "weeks_available": benchmark.get("weeks_available"),
                "weeks_required": benchmark.get("weeks_required"),
                "verdict": benchmark.get("verdict"),
                "inspection_override": "set enforce_backtest_gate=false for diagnostic inspection only",
            },
        )

    spot = None
    if spot_cost_multiplier is not None and spot_capacity_factor is not None:
        spot = {"spot_cost_multiplier": spot_cost_multiplier,
                "spot_capacity_factor": spot_capacity_factor}
    result = run_two_stage_two_sided(
        conn,
        spot_economics=spot,
        service_level_floor=service_level_floor,
        diversification_cap=diversification_cap,
    )
    result["backtest_gate"] = {
        "enforced": enforce_backtest_gate,
        "passed": benchmark.get("gate_passed"),
        "verdict": benchmark.get("verdict"),
    }
    result["unit"] = "kg"
    # Commercial explanation per commitment and the audit record, built from
    # the same history the plan used. Solver internals stay out of it.
    plan = result.get("plan", result)
    x = plan.get("x", {}) if isinstance(plan, dict) else {}
    if x:
        try:
            from backtesting.benchmark_suite import _deliveries, _weekly_demand
            from optimization.explain import explain_order
            wd = _weekly_demand(conn)
            hist = {j: [float(v) for v in g["demand_kg"]] for j, g in wd.groupby("product_id")} if len(wd) else {}
            dl = _deliveries(conn)
            fills = {}
            if len(dl) and "supplier_id" in dl.columns:
                num = "qty_received_kg" if "qty_received_kg" in dl.columns else None
                if num:
                    fills = dl.groupby("supplier_id")[num].apply(lambda g: 0.9).to_dict()
            expl = []
            for key, qty in x.items():
                sup, prod = (key.split("|", 1) if isinstance(key, str) and "|" in key else (str(key), "?"))
                if not qty or float(qty) <= 0:
                    continue
                e = explain_order(prod, sup, 0, float(qty), demand_history=hist.get(prod, []),
                                  on_hand=0.0, inbound=0.0, expected_fill=float(fills.get(sup, 0.9)),
                                  lead_periods=0, service_target=float(service_level_floor or 0.95),
                                  solver_status=str(plan.get("status", "optimal")))
                expl.append({"supplier_id": sup, "product_id": prod, "quantity": float(qty), "unit": "kg",
                             "explanation": e.reasons})
            result["explanations"] = expl
        except Exception as exc:  # noqa: BLE001  explanation is additive, never blocking
            result["explanations_error"] = type(exc).__name__
        from optimization.audit_trail import record_run
        rec = record_run(domain="agriculture_perishable",
                         config={"service_level_floor": service_level_floor,
                                 "diversification_cap": diversification_cap,
                                 "spot_cost_multiplier": spot_cost_multiplier,
                                 "spot_capacity_factor": spot_capacity_factor},
                         inputs={"commitments": x},
                         result={"status": plan.get("status") if isinstance(plan, dict) else result.get("status"),
                                 "usable": True, "objective": plan.get("objective") if isinstance(plan, dict) else None,
                                 "warnings": []})
        result["audit_record"] = {"run_id": rec.run_id, "timestamp": rec.timestamp,
                                  "model_version": rec.model_version, "solver_version": rec.solver_version,
                                  "input_hashes": rec.input_hashes}
    return result
