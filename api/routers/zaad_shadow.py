"""Operator-plan capture and shadow comparison (HARDENING V1, H3b).

POST /api/zaad/shadow/plans                capture an operator's intended purchasing plan (append-only version)
GET  /api/zaad/shadow/plans                list captured plans
GET  /api/zaad/shadow/plans/{plan_id}      one version with its lines and hash integrity
POST /api/zaad/shadow/plans/{plan_id}/compare
                                           compare ZAAD's recommendation for the plan's origin against the plan:
                                           the recommendation comes from a synchronous planner run, or from a
                                           finished planning job (`baseline_job_id`) whose request is for the same
                                           origin; both plans are then settled on the planner's own worlds
GET  /api/zaad/shadow/comparisons/{id}     a stored comparison

Every write checks the acting person's capability. The comparison is stored once, immutably, with the plan
version, hash and request fingerprint it used; nothing here writes a purchase order.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from api.dependencies import get_conn, require_actor
from api.product import governance, operator_plans
from api.product.governance import Actor
from zaad.full import comparator
from zaad.full import shadow_plan as shadow

router = APIRouter(prefix="/api/zaad/shadow", tags=["zaad-shadow"])


def acting(actor: Actor | None = Depends(require_actor)) -> Actor:
    if actor is None:
        raise HTTPException(401, "Open your workspace to capture a purchasing plan.")
    return actor


Who = Annotated[Actor, Depends(acting)]


class PlanLine(BaseModel):
    sku: str = Field(min_length=1, max_length=120)
    supplier_id: str | None = Field(default=None, max_length=120)
    destination_id: str | None = Field(default=None, max_length=120)
    quantity: float = Field(ge=0)
    period: int = Field(default=0, ge=0, le=52)
    line_reference: str | None = Field(default=None, max_length=200)


class PlanCapture(BaseModel):
    as_of: datetime
    lines: list[PlanLine] = Field(min_length=1, max_length=5000)
    provenance: Literal["OPERATOR_SUBMITTED", "OPERATOR_UPLOADED", "OPERATOR_CONFIRMED_DRAFT"]
    source_reference: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=2000)
    supersedes: str | None = Field(default=None, max_length=64)


def _require(who: Actor, capability: str) -> None:
    if not who.can(capability):
        raise HTTPException(403, {"code": "forbidden", "message": f"your role cannot {capability.replace('_', ' ')}"})


@router.post("/plans", status_code=201)
def capture_plan(body: PlanCapture, who: Who, conn=Depends(get_conn)):
    """Record the operator's intended plan for a planning origin as a new immutable version."""
    _require(who, "createProposal")
    try:
        plan = operator_plans.capture_plan(conn, who.operator_id, as_of=body.as_of, lines=[ln.model_dump() for ln in body.lines],
                                           provenance=body.provenance, captured_by=who.actor_id, source_reference=body.source_reference,
                                           note=body.note, supersedes=body.supersedes)
    except operator_plans.PlanRefused as exc:
        raise HTTPException(422, {"code": "plan_refused", "message": str(exc)}) from exc
    if plan.get("created"):
        governance.record_audit(conn, who, object_type="operator_plan", object_id=plan["plan_id"], action="operator_plan_captured",
                                context={"version": plan["version"], "lines": plan["line_count"], "provenance": plan["provenance"], "hash": plan["content_hash"]})
    return plan


@router.get("/plans")
def list_plans(who: Who, conn=Depends(get_conn), as_of: datetime | None = Query(None), limit: int = Query(50, ge=1, le=200)):
    return {"plans": operator_plans.list_plans(conn, who.operator_id, as_of=as_of, limit=limit)}


@router.get("/plans/{plan_id}")
def read_plan(plan_id: str, who: Who, conn=Depends(get_conn)):
    try:
        return operator_plans.read_plan(conn, who.operator_id, plan_id)
    except KeyError as exc:
        raise HTTPException(404, "That plan is not in this workspace.") from exc


def _utc(value: Any) -> datetime:
    stamp = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    return stamp.astimezone(timezone.utc) if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


def refine_report(report: dict[str, Any], *, rule_provenance: str | None, req: Any) -> dict[str, Any]:
    """A planner report (from a synchronous run or a finished job) with its decision reference and PLAN_MODE
    comparison refined from the workspace build's rule provenance, so synchronous and asynchronous results
    carry the same provenance."""
    out = dict(report)
    out["decision_reference"] = comparator.decision_reference(req, rule_provenance=rule_provenance)
    out["comparison"] = comparator.plan_comparison(req, status=report.get("status"), selected_policy=report.get("selected_policy"), rule_provenance=rule_provenance)
    return out


def shadow_result(req: Any, build: dict[str, Any], report: dict[str, Any], plan: dict[str, Any], *, latest_version: int, exposed_at: datetime,
                  recommendation_source: str, max_solve_seconds: float) -> dict[str, Any]:
    """The comparison of ZAAD's recommendation (already produced, without the plan) against the captured plan,
    both settled on the planner's own worlds. Pure: no persistence."""
    mapping = operator_plans.map_plan_to_request(plan, req)
    evidence = operator_plans.shadow_evidence(plan, mapping, req=req, exposed_at=exposed_at, latest_version=latest_version)
    rule_prov = ((build or {}).get("incumbent_rule") or {}).get("provenance")
    recommended: dict[tuple[str, int], float] = {}
    for a in report.get("actions") or []:
        if a.get("action") == "buy" and a.get("source") and float(a.get("quantity") or 0) > 0:
            recommended[a["source"], int(a.get("period") or 0)] = recommended.get((a["source"], int(a.get("period") or 0)), 0.0) + float(a["quantity"])
    scored = shadow.evaluate_plans(req, {"operator_plan": mapping["purchases"], "zaad": recommended}) if evidence["identity_fidelity"] != comparator.NOT_AVAILABLE else None
    plan_eval = (scored or {}).get("plans", {}).get("operator_plan") or {}
    zaad_eval = (scored or {}).get("plans", {}).get("zaad") or {}
    recorded_units = float(sum(float(ln["quantity"]) for ln in plan["lines"]))
    identified_units = float(sum(mapping["purchases"].values()))
    evaluated_units = float(plan_eval.get("units") or 0.0)
    transformed = abs(identified_units - evaluated_units) > 1e-6
    contract = comparator.shadow_comparison(evidence, status=report.get("status"), selected_policy=report.get("selected_policy"),
                                            rule_provenance=rule_prov, transformed=transformed)
    costs_plan, costs_zaad = plan_eval.get("costs"), zaad_eval.get("costs")
    difference = None
    if costs_plan and costs_zaad:
        difference = {k: costs_plan[k] - costs_zaad[k] for k in costs_zaad}          # positive = ZAAD's plan modelled cheaper
    return {"contract": contract, "evidence": {**{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in evidence.items()}},
            "quantities": {"recorded_plan_units": recorded_units, "identified_plan_units": identified_units, "model_evaluated_plan_units": evaluated_units,
                           "zaad_units": float(sum(recommended.values())), "unidentified_lines": mapping["coverage"].get("lines_incomplete"),
                           "out_of_scope_lines": mapping["out_of_scope_lines"]},
            "lines": mapping["lines"],
            "modelled": {"basis": (scored or {}).get("basis"), "worlds": (scored or {}).get("worlds"), "seed": (scored or {}).get("seed"),
                         "operator_plan": plan_eval, "zaad": zaad_eval,
                         "cost_difference_plan_minus_zaad": difference,
                         "note": "a modelled difference on simulated worlds; not a realized outcome and not operator savings"},
            "recommendation": {"source": recommendation_source, "status": report.get("status"), "selected_policy": report.get("selected_policy"),
                               "information_hash": report.get("information_hash"), "decision_reference": report.get("decision_reference"),
                               "max_solve_seconds": max_solve_seconds},
            "realized_value": {"available": False, "note": "no observed outcome is attached to this comparison; see the V2 outcome contract"}}


@router.post("/plans/{plan_id}/compare", status_code=201)
async def compare_plan(plan_id: str, who: Who, conn=Depends(get_conn), horizon: int = Query(12, ge=4, le=26),
                       service_target: float = Query(.95, gt=.5, le=1.), skus: str | None = Query(None), max_solve_seconds: float = Query(15., gt=0, le=120),
                       baseline_job_id: str | None = Query(None, description="a finished planning job whose request has the plan's origin; otherwise the planner runs now")):
    """Compare ZAAD's recommendation for the plan's planning origin against the captured plan."""
    from api.routers.zaad_full import _workspace_request, compute, runner
    _require(who, "runPlanner")
    operator = who.operator_id
    try:
        plan = operator_plans.read_plan(conn, operator, plan_id)
    except KeyError as exc:
        raise HTTPException(404, "That plan is not in this workspace.") from exc
    family = operator_plans.list_plans(conn, operator, as_of=_utc(plan["as_of"]))
    latest_version = max(int(p["version"]) for p in family) if family else int(plan["version"])
    as_of = _utc(plan["as_of"])
    subset = skus or ",".join(sorted({ln["sku"] for ln in plan["lines"]}))
    req, build = await run_in_threadpool(_workspace_request_at, conn, operator, horizon, service_target, subset, max_solve_seconds, as_of, _workspace_request)
    rule_prov = ((build or {}).get("incumbent_rule") or {}).get("provenance")
    if baseline_job_id:
        try:
            job = runner().store.get(baseline_job_id, operator)
        except KeyError as exc:
            raise HTTPException(404, "That planning job is not in this workspace.") from exc
        if job.get("status") != "DONE" or not job.get("report"):
            raise HTTPException(409, {"code": "job_not_done", "message": f"job {baseline_job_id} is {job.get('status')}; the comparison needs a finished recommendation"})
        report = job["report"]
        if _utc(report.get("as_of")) != as_of:
            raise HTTPException(409, {"code": "origin_mismatch", "message": "that job planned a different origin than the captured plan"})
        exposed_at = _utc(job.get("finished_at") or job.get("created_at") or datetime.now(timezone.utc))
        source = f"JOB:{baseline_job_id}"
    else:
        report = await compute(req)
        exposed_at = datetime.now(timezone.utc)
        source = "SYNC"
    report = refine_report(report, rule_provenance=rule_prov, req=req)
    result = await run_in_threadpool(shadow_result, req, build, report, plan, latest_version=latest_version, exposed_at=exposed_at,
                                     recommendation_source=source, max_solve_seconds=max_solve_seconds)
    identity = operator_plans.store_comparison(conn, operator, plan=plan, as_of=as_of, request_hash=report.get("information_hash"),
                                               recommendation_source=source, exposed_at=exposed_at, status="DONE", result=result)
    governance.record_audit(conn, who, object_type="shadow_comparison", object_id=identity, action="shadow_comparison_recorded",
                            context={"plan_id": plan_id, "version": plan["version"], "readiness": result["contract"]["readiness"], "source": source})
    return {"comparison_id": identity, "plan_id": plan_id, "plan_version": plan["version"], "as_of": as_of.isoformat(), "recommendation_source": source,
            **result, "executable_purchase_order": False}


def _workspace_request_at(conn, operator, horizon, service_target, skus, max_solve_seconds, as_of, _workspace_request):
    """The workspace request for the plan's own origin (the shared builder plans 'now'; a shadow comparison plans the captured origin)."""
    from zaad.full.workspace import WorkspaceError, build_request
    subset = [x.strip() for x in skus.split(",") if x.strip()] if skus else None
    try:
        return build_request(conn, operator, horizon=horizon, service_target=service_target, skus=subset, max_solve_seconds=max_solve_seconds, as_of=as_of)
    except WorkspaceError as exc:
        raise HTTPException(422, {"code": "workspace_not_ready", "message": str(exc)}) from exc


@router.get("/comparisons/{comparison_id}")
def read_comparison(comparison_id: str, who: Who, conn=Depends(get_conn)):
    try:
        return operator_plans.read_comparison(conn, who.operator_id, comparison_id)
    except KeyError as exc:
        raise HTTPException(404, "That comparison is not in this workspace.") from exc


__all__ = ["router", "refine_report", "shadow_result", "json"]
