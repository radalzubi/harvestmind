"""Versioned full network API. Authenticated durable shadow workflow; no PO writes."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
import threading
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request as HTTPRequest
from pydantic import Field, ValidationError, model_validator
from starlette.concurrency import run_in_threadpool

from api.dependencies import require_operator
from api.routers.zaad import bounded_rate
from zaad.contracts import Record
from zaad.full.contracts import Request
from zaad.full.planner import plan
from zaad.full.shadow import ShadowConflict, ShadowLedger

router = APIRouter(prefix="/api/zaad/network", tags=["zaad-network-shadow"])
_slots = threading.BoundedSemaphore(1)


def ledger() -> ShadowLedger:
    path = os.getenv("ZAAD_SHADOW_LEDGER")
    if not path:
        raise HTTPException(503, "Configure dedicated ZAAD_SHADOW_LEDGER storage; training databases are never used.")
    return ShadowLedger(Path(path))


def authenticated(operator: str | None = Depends(require_operator)) -> str:
    if operator is None:
        raise HTTPException(401, "Persistent shadow records require authentication, including in development.")
    return operator


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
    if result.max_solve_seconds * (10 + len(result.services)) > 180:
        raise HTTPException(422, "Aggregate requested solver time exceeds 180 seconds; lower max_solve_seconds.")
    return result


async def compute(req):
    if not _slots.acquire(blocking=False):
        raise HTTPException(429, "Network planner busy; retry shortly.")
    try:
        return await run_in_threadpool(plan, req)
    finally:
        _slots.release()


@router.get("/schema")
def schema():
    return Request.model_json_schema()


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
