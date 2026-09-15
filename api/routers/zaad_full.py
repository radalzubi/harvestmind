"""Versioned full network API. Authenticated durable shadow workflow; no PO writes."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
import threading
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request as HTTPRequest
from pydantic import Field, ValidationError, model_validator
from starlette.concurrency import run_in_threadpool

from api.dependencies import get_conn, require_operator
from api.routers.zaad import bounded_rate
from zaad.contracts import Record
from zaad.full.contracts import Request
from zaad.full.planner import plan
from zaad.full.jobs import JobRunner, JobStore, QuotaExceeded
from zaad.full.shadow import ShadowConflict, ShadowLedger

router = APIRouter(prefix="/api/zaad/network", tags=["zaad-network-shadow"])
_slots = threading.BoundedSemaphore(1)
_runner: JobRunner | None = None
_runner_lock = threading.Lock()


def runner() -> JobRunner:
    """One bounded runner per process; storage is dedicated, never the training database."""
    global _runner
    path = os.getenv("ZAAD_JOB_STORE")
    if not path:
        raise HTTPException(503, "Configure dedicated ZAAD_JOB_STORE storage for asynchronous planning jobs.")
    with _runner_lock:
        if _runner is None or _runner.store.path != Path(path):
            _runner = JobRunner(JobStore(Path(path)))
        return _runner


LARGE_LIMITS = {"skus": 200, "sources": 400, "services": 200, "horizon": 26, "scenarios": 32, "stresses": 12}


async def large_payload(request: HTTPRequest) -> Request:
    """The asynchronous path accepts what /plan refuses, up to the bounded limits above."""
    if request.headers.get("content-type", "").split(";", 1)[0].strip() != "application/json":
        raise HTTPException(415, "application/json required")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > 16 * 1024 * 1024:
            raise HTTPException(413, "Snapshots over 16 MiB are outside the asynchronous job envelope.")
        body.extend(chunk)
    try:
        result = Request.model_validate_json(body)
    except ValidationError as exc:
        raise HTTPException(422, [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]}
                                 for e in exc.errors(include_input=False, include_context=False)]) from exc
    if result.recourse is not None and result.recourse.enabled:
        # P4 batch bounds: a structural cap on the scenario tree even on the asynchronous path
        from zaad.recourse.contracts import BATCH_LIMITS, tree_worlds
        if tree_worlds(result) > BATCH_LIMITS["tree_worlds"] or len(result.recourse.review_periods) > BATCH_LIMITS["review_epochs"]:
            raise HTTPException(413, f"Recourse scenario tree over the batch envelope: {BATCH_LIMITS} (worlds {tree_worlds(result)}).")
    atp_gate(result, batch=True)
    commitments_gate(result, batch=True)
    if (len(result.skus) > LARGE_LIMITS["skus"] or len(result.sources) > LARGE_LIMITS["sources"]
            or len(result.services) > LARGE_LIMITS["services"] or result.horizon > LARGE_LIMITS["horizon"]
            or result.scenarios > LARGE_LIMITS["scenarios"] or len(result.stresses) > LARGE_LIMITS["stresses"]):
        raise HTTPException(413, f"Asynchronous job limit exceeded: {LARGE_LIMITS}")
    return result


def ledger() -> ShadowLedger:
    path = os.getenv("ZAAD_SHADOW_LEDGER")
    if not path:
        raise HTTPException(503, "Configure dedicated ZAAD_SHADOW_LEDGER storage; training databases are never used.")
    return ShadowLedger(Path(path))


def authenticated(operator: str | None = Depends(require_operator)) -> str:
    if operator is None:
        raise HTTPException(401, "Persistent shadow records require authentication, including in development.")
    return operator


def atp_gate(result: Request, *, batch: bool) -> None:
    """P5 (ATP / scarce-supply allocation) on the planner paths: default off in every environment
    (`ZAAD_ATP_ENABLED=1` switches it on, 422 `atp_disabled` otherwise), and on the interactive path the
    same deterministic bounds as the standalone endpoint (413). Nothing runs before this check."""
    from zaad.atp.contracts import INTERACTIVE_LIMITS as ATP_LIMITS, resolve as resolve_atp
    from zaad.atp.validation import within_interactive_limits
    atp = resolve_atp(result)
    if atp is None:
        return
    if os.getenv("ZAAD_ATP_ENABLED", "0") != "1":
        raise HTTPException(422, {"code": "atp_disabled", "message": "ATP / allocation is not enabled in this environment (ZAAD_ATP_ENABLED); remove the `atp` block or disable it."})
    if not batch:
        ok, why = within_interactive_limits(atp)
        if not ok:
            raise HTTPException(413, f"Interactive ATP bounds exceeded: {why}; limits {ATP_LIMITS}; submit the request to /api/zaad/network/jobs.")


def commitments_gate(result: Request, *, batch: bool) -> None:
    """P4B V1 (release audit K): the declared option set is bounded before any model is built (413), on the
    interactive paths at the module's limits and on the batch path at four times them."""
    from zaad.commitments.contracts import INTERACTIVE_LIMITS as COMMITMENT_LIMITS, over_limits
    why = over_limits(result, factor=4 if batch else 1)
    if why:
        raise HTTPException(413, f"{'Batch' if batch else 'Interactive'} commitment bounds exceeded: {why}; limits {COMMITMENT_LIMITS}"
                                 + ("" if batch else "; submit the request to /api/zaad/network/jobs."))


async def payload(request: HTTPRequest) -> Request:
    if request.headers.get("content-type", "").split(";", 1)[0].strip() != "application/json":
        raise HTTPException(415, "application/json required")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > 2 * 1024 * 1024:
            raise HTTPException(413, "Use offline planning for snapshots over 2 MiB.")
        body.extend(chunk)
    try:
        result = Request.model_validate_json(body)
    except ValidationError as exc:
        raise HTTPException(422, [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]}
                                 for e in exc.errors(include_input=False, include_context=False)]) from exc
    if len(result.skus) > 20 or len(result.sources) > 40 or len(result.services) > 20 or result.horizon > 12 or result.scenarios > 4 or len(result.stresses) > 4:
        raise HTTPException(413, "Interactive network limit exceeded; use offline batch planning.")
    from zaad.meio.topology import NETWORK_LIMITS
    if len(result.locations) > NETWORK_LIMITS["locations"] or len(result.transfers) > NETWORK_LIMITS["transfers"] or len(result.incumbent_transfers) > NETWORK_LIMITS["incumbent_transfers"]:
        raise HTTPException(413, f"Interactive network bounds exceeded (locations, lanes, incumbent transfers): {NETWORK_LIMITS}; use offline batch planning.")
    if result.max_solve_seconds * (10 + len(result.services)) > 180:
        raise HTTPException(422, "Aggregate requested solver time exceeds 180 seconds; lower max_solve_seconds.")
    if result.sourcing is not None:
        # P3 interactive bounds: combinatorial sourcing input is capped before any model is built
        from zaad.sourcing.contracts import INTERACTIVE_LIMITS
        pairs: dict[tuple[str, str], int] = {}
        for s in result.sources:
            pairs[s.sku, s.destination] = pairs.get((s.sku, s.destination), 0) + 1
        if (max(pairs.values(), default=0) > INTERACTIVE_LIMITS["sources_per_pair"] or len(result.sourcing.risk_groups) > INTERACTIVE_LIMITS["risk_groups"]
                or len(result.sourcing.share_constraints) > INTERACTIVE_LIMITS["share_constraints"] or len(result.sourcing.switching_costs) > INTERACTIVE_LIMITS["switching_costs"]
                or len(result.sourcing.incumbent_shares) > INTERACTIVE_LIMITS["incumbent_shares"]):
            raise HTTPException(413, f"Interactive sourcing bounds exceeded: {INTERACTIVE_LIMITS}; use offline batch planning.")
    atp_gate(result, batch=False)
    commitments_gate(result, batch=False)
    if result.recourse is not None and result.recourse.enabled:
        # P4 interactive bounds (deterministic, before any model): the scenario tree at most 8 worlds
        # and never the P3 shared-supplier-order class; both are served by the asynchronous jobs path
        from zaad.full.model import shared_supplier_orders
        from zaad.recourse.contracts import INTERACTIVE_LIMITS as RECOURSE_LIMITS, tree_worlds
        tree = tree_worlds(result)
        if (len(result.recourse.review_periods) > RECOURSE_LIMITS["review_epochs"] or len(result.recourse.observables) > RECOURSE_LIMITS["observables"]
                or len(result.recourse.actions) > RECOURSE_LIMITS["actions"] or tree > RECOURSE_LIMITS["tree_worlds"]):
            raise HTTPException(413, f"Interactive recourse bounds exceeded: {RECOURSE_LIMITS} (scenario-tree worlds {tree}); submit the request to /api/zaad/network/jobs.")
        if shared_supplier_orders(result):
            raise HTTPException(413, "Adaptive recourse on a supplier order shared across SKUs is batch-only in this version; submit the request to /api/zaad/network/jobs.")
    return result


def _take_lease() -> Any:
    """The solver lease for a synchronous plan: the job runner's when a job store is configured,
    so a synchronous solve never runs beside a job or overtakes a queued one; otherwise this
    process's own single slot. Returns the release callable, or None when busy."""
    if os.getenv("ZAAD_JOB_STORE"):
        run = runner()
        return run.release_lease if run.try_lease() else None
    return _slots.release if _slots.acquire(blocking=False) else None


async def compute(req):
    release = _take_lease()
    if release is None:
        raise HTTPException(429, {"code": "planner_busy", "message":
                                  "A planning run is in progress on this service; the planner runs one at a time. "
                                  "Retry shortly, or submit the request to /api/zaad/network/jobs to queue it."})
    try:
        if req.transfers or len(req.locations) > 1:
            # a network request: the frozen decision plus the P2 network block (accounting, explanations)
            from zaad.meio.planner import NetworkRefused, plan_network
            try:
                return await run_in_threadpool(plan_network, req)
            except NetworkRefused as exc:
                raise HTTPException(422, {"code": "network_refused", "message": str(exc)}) from exc
        return await run_in_threadpool(plan, req)
    finally:
        release()


@router.get("/schema")
def schema():
    return Request.model_json_schema()


def _directory_rows(conn, sql: str) -> list[dict]:
    """One staging read, tolerant of a table that has not been created for this operator yet."""
    try:
        cursor = conn.execute(sql)
        columns = [c[0] for c in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception:  # noqa: BLE001 - a workspace without this upload is an empty directory, not an error
        return []


# Not rate limited, for the same reason job status reads are not: this is two indexed reads of
# the caller's own vault, and the product fetches it on every workspace load. Sharing the planner's
# per-minute budget would let a page load spend it and answer 429 for a lookup that costs nothing.
@router.get("/directory")
def directory(operator: str = Depends(authenticated), conn=Depends(get_conn)):
    """Declared supplier and location master data, read straight from the operator's own vault.

    A projection for display only: the compact planning contract identifies a supplier by id and
    carries no name, declared origin country or route tag, so a product surface that wants to name
    or place a supplier has nowhere else to read it from. This endpoint runs no planner, prices
    nothing, infers nothing and writes nothing; every field is a column the operator uploaded.
    """
    suppliers = _directory_rows(conn, "SELECT * FROM stg_fmcg_suppliers")
    locations = _directory_rows(conn, "SELECT * FROM stg_fmcg_locations")
    latest: dict[str, dict] = {}
    for row in suppliers:  # last upload of an id wins, matching the planning adapter's drop_duplicates
        sid = row.get("supplier_id")
        if sid is not None:
            latest[str(sid)] = row
    latest_locations: dict[str, dict] = {}
    for row in locations:
        lid = row.get("location_id")
        if lid is not None:
            latest_locations[str(lid)] = row

    def _text(row: dict, key: str) -> str | None:
        value = row.get(key)
        return None if value is None else str(value)

    def _number(row: dict, key: str) -> float | None:
        value = row.get(key)
        try:
            return None if value is None else float(value)
        except (TypeError, ValueError):
            return None

    return {
        "suppliers": [
            {"id": sid, "name": _text(row, "supplier_name"), "origin_iso3": _text(row, "origin_iso3"),
             "route": _text(row, "route"), "capacity_per_week": _number(row, "capacity_per_week"),
             "lead_time_promised_weeks": _number(row, "lead_time_promised_weeks"),
             "risk_group": _text(row, "risk_group"), "risk_group_kind": _text(row, "risk_group_kind")}
            for sid, row in sorted(latest.items())
        ],
        "locations": [
            {"id": lid, "kind": _text(row, "kind"), "capacity_units": _number(row, "capacity_units")}
            for lid, row in sorted(latest_locations.items())
        ],
        "rows_read": {"stg_fmcg_suppliers": len(suppliers), "stg_fmcg_locations": len(locations)},
        "provenance": "OPERATOR_DECLARED",
    }


@router.get("/fixture", dependencies=[Depends(bounded_rate)])
def fixture(case: Literal["normal", "transfer", "substitution", "recovery", "cash", "understock"] = "normal"):
    from zaad.full.demo import example
    return example(case)


@router.post("/plan", dependencies=[Depends(bounded_rate)])
async def recommend(request: HTTPRequest, operator: str | None = Depends(require_operator)):
    req = await payload(request)
    if operator is not None and req.operator_id != operator:
        raise HTTPException(403, "Operator mismatch")
    return await compute(req)


def _workspace_request(conn, operator: str, horizon: int, service_target: float, skus: str | None, max_solve_seconds: float, network: bool = False,
                       sector_mode: str | None = None, sourcing: bool = False, recourse: bool = False, atp: bool = False, commitments: bool = False):
    from zaad.full.workspace import WorkspaceError, build_request
    subset = [x.strip() for x in skus.split(",") if x.strip()] if skus else None
    try:
        if network:
            # P2: the vault's declared locations and lanes; identical to the frozen adapter below two locations
            from zaad.meio.workspace import build_network_request
            return build_network_request(conn, operator, horizon=horizon, service_target=service_target, skus=subset, max_solve_seconds=max_solve_seconds, sector_mode=sector_mode, sourcing=sourcing, recourse=recourse, atp=atp, commitments=commitments)
        return build_request(conn, operator, horizon=horizon, service_target=service_target, skus=subset, max_solve_seconds=max_solve_seconds, sector_mode=sector_mode, sourcing=sourcing, recourse=recourse, atp=atp, commitments=commitments)
    except WorkspaceError as exc:
        raise HTTPException(422, {"code": "workspace_not_ready", "message": str(exc)}) from exc
    except ValueError as exc:
        # sector physics or sourcing declared inconsistently in the vault (unknown state, threshold above
        # shelf life, share limits the incumbent mix does not meet, unknown supplier in a risk group, ...)
        # A size violation is a validation error like any other, and used to fall through to
        # `sector_physics_invalid` — which sends a reader looking in entirely the wrong place for a
        # workspace that is simply larger than one planning request can carry.
        text = str(exc)
        code = ("commitments_invalid" if "commitments:" in text else "atp_invalid" if "atp:" in text
                else "recourse_invalid" if "recourse:" in text
                else "sourcing_invalid" if "sourcing:" in text
                else "workspace_too_large" if "too_long" in text or "Tuple should have at most" in text
                else "sector_physics_invalid")
        raise HTTPException(422, {"code": code, "message": str(exc)}) from exc


@router.get("/request/from-workspace", dependencies=[Depends(bounded_rate)])
def workspace_request(operator: str = Depends(authenticated), conn=Depends(get_conn), horizon: int = Query(12, ge=4, le=26),
                      service_target: float = Query(.95, gt=.5, le=1.), skus: str | None = Query(None, description="comma-separated subset"),
                      max_solve_seconds: float = Query(15., gt=0, le=120),
                      network: bool = Query(False, description="P2: build the multi-location network from stg_fmcg_locations / lanes / transfers"),
                      sector_mode: Literal["COMMERCIAL", "PRODUCE", "MEAT_SEAFOOD"] | None = Query(None, description="sector physics: the request's default sector (per-SKU columns override it)"),
                      sourcing: bool = Query(False, description="P3: attach the vault's declared source options, shares, incumbent mix and risk groups (stg_fmcg_sources, migration 018)"),
                      recourse: bool = Query(False, description="P4: attach the vault's declared adaptive-recourse specification (stg_recourse_spec, migration 019)"),
                      atp: bool = Query(False, description="P5: attach the vault's declared customer orders, service classes and promising policy (migration 020); needs ZAAD_ATP_ENABLED=1"),
                      commitments: bool = Query(False, description="P4B: attach the vault's declared open-PO commitment terms and amendment options (migration 022); absent declarations keep every order KEEP-only")):
    """The frozen contract built from the operator's own vault (the canonical customer-data path), with
    the build report: rows read, compact dimensions, fitted supplier fill and lead with sample sizes,
    provenance, warnings and the leakage guard. No plan is run."""
    req, build = _workspace_request(conn, operator, horizon, service_target, skus, max_solve_seconds, network, sector_mode, sourcing, recourse, atp, commitments)
    atp_gate(req, batch=False)
    return {"request": req.model_dump(mode="json"), "build": build}


@router.post("/plan/from-workspace", dependencies=[Depends(bounded_rate)])
async def workspace_plan(operator: str = Depends(authenticated), conn=Depends(get_conn), horizon: int = Query(12, ge=4, le=26),
                         service_target: float = Query(.95, gt=.5, le=1.), skus: str | None = Query(None, description="comma-separated subset"),
                         max_solve_seconds: float = Query(15., gt=0, le=120), commit_window_weeks: int = Query(4, ge=1, le=8),
                         shape: Literal["network", "purchase_plan"] = Query("purchase_plan"),
                         network: bool = Query(False, description="P2: plan the declared multi-location network (purchases, transfers, allocation)"),
                         sector_mode: Literal["COMMERCIAL", "PRODUCE", "MEAT_SEAFOOD"] | None = Query(None, description="sector physics: the request's default sector (per-SKU columns override it)"),
                         sourcing: bool = Query(False, description="P3: attach the vault's declared source options, shares, incumbent mix and risk groups (stg_fmcg_sources, migration 018)"),
                      recourse: bool = Query(False, description="P4: attach the vault's declared adaptive-recourse specification (stg_recourse_spec, migration 019)"),
                      atp: bool = Query(False, description="P5: attach the vault's declared customer orders, service classes and promising policy (migration 020); needs ZAAD_ATP_ENABLED=1"),
                      commitments: bool = Query(False, description="P4B: attach the vault's declared open-PO commitment terms and amendment options (migration 022); absent declarations keep every order KEEP-only")):
    """Plan the operator's workspace with the frozen P1 optimizer: vault -> compact Request -> plan.
    `shape=purchase_plan` returns the workspace purchase-plan rows (approval stays with the operator,
    never an executable order); `shape=network` returns the full network report with the build."""
    from zaad.full.workspace import to_purchase_plan
    # P5 release audit (item C): the released call site dropped `recourse` (P4 plumbing defect, recorded in the
    # P5 integration API audit); every phase flag is now passed by keyword, so no flag depends on its position.
    req, build = await run_in_threadpool(_workspace_request, conn, operator, horizon, service_target, skus, max_solve_seconds, network,
                                         sector_mode=sector_mode, sourcing=sourcing, recourse=recourse, atp=atp, commitments=commitments)
    atp_gate(req, batch=False)
    report = await compute(req)
    if shape == "network":
        return {"report": report, "build": build, "executable_purchase_order": False}
    if network and (req.transfers or len(req.locations) > 1):
        from zaad.meio.workspace import to_network_plan
        out = to_network_plan(req, report, build, commit_window_weeks=commit_window_weeks, run_id=str(report.get("input_fingerprint", "")))
    else:
        out = to_purchase_plan(req, report, build, commit_window_weeks=commit_window_weeks, run_id=str(report.get("input_fingerprint", "")))
    if "atp" in report:
        # the P5 promising report travels with the plan shape (approval stays with the operator; no promise executes)
        out["atp"] = report["atp"]
        out["executable_promise"] = False
    if "commitments" in report:
        # the P4B commitment report travels with the plan shape (approval stays with the operator; no amendment executes)
        out["commitments"] = report["commitments"]
        out["executable_amendment"] = False
    return out


@router.post("/shadow", dependencies=[Depends(bounded_rate)])
async def record(request: HTTPRequest, operator: str = Depends(authenticated)):
    req = await payload(request)
    if req.operator_id != operator:
        raise HTTPException(403, "Operator mismatch")
    storage = ledger()  # fail before costly work if durable storage is unavailable
    report = await compute(req)
    identity = await run_in_threadpool(storage.save, req, report, operator)
    return {"decision_id": identity, "report": report, "executable_purchase_order": False}


@router.get("/shadow/{decision_id}", dependencies=[Depends(bounded_rate)])
def read(decision_id: str, operator: str = Depends(authenticated)):
    try:
        return ledger().get(decision_id, operator)
    except KeyError as exc:
        raise HTTPException(404, "Decision not found") from exc


class Review(Record):
    status: Literal["APPROVED", "REJECTED"]
    information_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    version: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=2000)


@router.post("/shadow/{decision_id}/review", dependencies=[Depends(bounded_rate)])
def review(decision_id: str, body: Review, operator: str = Depends(authenticated)):
    try:
        return ledger().review(decision_id, operator, body.status, body.information_hash, body.version, body.reason)
    except KeyError as exc:
        raise HTTPException(404, "Decision not found") from exc
    except ShadowConflict as exc:
        raise HTTPException(409, str(exc)) from exc


class Outcome(Record):
    observed_at: datetime
    service_unit_fill: float = Field(ge=0, le=1)
    realized_cost: float
    evidence_reference: str = Field(min_length=1, max_length=1000)
    note: str = Field(max_length=2000)

    @model_validator(mode="after")
    def observed_clock(self):
        if self.observed_at.tzinfo is None or self.observed_at > datetime.now(timezone.utc):
            raise ValueError("outcome needs an aware, already observed timestamp")
        return self


@router.post("/shadow/{decision_id}/outcome", dependencies=[Depends(bounded_rate)])
def outcome(decision_id: str, body: Outcome, operator: str = Depends(authenticated)):
    try:
        ledger().outcome(decision_id, operator, body.model_dump(mode="json"))
    except KeyError as exc:
        raise HTTPException(404, "Decision not found") from exc
    return {"recorded": True, "used_for_training": False}


@router.post("/jobs", dependencies=[Depends(bounded_rate)], status_code=202)
async def submit_job(request: HTTPRequest, operator: str = Depends(authenticated)):
    """Queue a large planning run. Small requests should use /plan, which answers inline."""
    req = await large_payload(request)
    if req.operator_id != operator:
        raise HTTPException(403, "Operator mismatch")
    run = runner()
    try:
        identity = run.submit(operator, req)
    except QuotaExceeded as exc:
        raise HTTPException(429, str(exc)) from exc
    return {"job_id": identity, "status": "QUEUED", "timeout_s": run.timeout_for(req),
            "executable_purchase_order": False, "approval_required": True}


@router.get("/jobs")
def list_jobs(operator: str = Depends(authenticated),
              purpose: str | None = Query(None, description="WORKSPACE_PLAN | PROPOSAL_BASELINE | PROPOSAL_OVERLAY | …")):
    """Status reads are cheap SQLite lookups scoped to the caller; they are not rate limited so polling works.

    Every job carries a purpose. A surface that wants the workspace's last plan asks for
    `purpose=WORKSPACE_PLAN` and never sees an evaluation's overlay run.
    """
    from zaad.full.jobs import PURPOSES
    if purpose is not None and purpose not in PURPOSES:
        raise HTTPException(400, f"Unknown job purpose {purpose!r}. One of {', '.join(PURPOSES)}.")
    return {"jobs": runner().store.list(operator, purpose=purpose)}


@router.get("/jobs/{job_id}")
def read_job(job_id: str, operator: str = Depends(authenticated)):
    """One job. A QUEUED job also says where it stands: `queue_position` 1 is the next to start
    (the planner runs one solve at a time, in submission order), and `running_now` is how many
    solves hold a lease ahead of the queue."""
    run = runner()
    try:
        job = run.store.get(job_id, operator)
    except KeyError as exc:
        raise HTTPException(404, "Job not found") from exc
    if job["status"] == "QUEUED":
        leases = run.leases()
        job["queue_position"] = run.queue_position(job_id)
        job["running_now"] = leases["held"]
    return job


@router.delete("/jobs/{job_id}", dependencies=[Depends(bounded_rate)])
def cancel_job(job_id: str, operator: str = Depends(authenticated)):
    try:
        return runner().cancel(job_id, operator)
    except KeyError as exc:
        raise HTTPException(404, "Job not found") from exc
