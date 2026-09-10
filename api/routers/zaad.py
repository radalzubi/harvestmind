"""The first ZAAD engine's bounded recommendation API (SUPERSEDED by the frozen P1 optimizer under
/api/zaad/network). Served only while legacy planners are enabled (see api.dependencies.legacy_planners_enabled);
no vault writes or PO execution."""
from __future__ import annotations

import json
import threading
import time
from collections import deque
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from api.dependencies import legacy_planner_gate, require_operator
from zaad.contracts import PlanningRequest, PlanReport

router = APIRouter(prefix="/api/zaad", tags=["zaad-experimental"])
MAX_BODY_BYTES = 2 * 1024 * 1024
REQUESTS_PER_MINUTE = 12
_recent: dict[str, deque] = {}
_global_recent: deque = deque()
_lock = threading.Lock()
_slots = threading.BoundedSemaphore(2)


def bounded_rate(request: Request) -> None:
    """Mandatory per-process cap, never disabled by legacy dev settings."""
    now = time.monotonic()
    client = request.client.host if request.client else "unknown"
    with _lock:
        for key in list(_recent):
            bucket = _recent[key]
            while bucket and bucket[0] <= now - 60:
                bucket.popleft()
            if not bucket:
                del _recent[key]
        while _global_recent and _global_recent[0] <= now - 60:
            _global_recent.popleft()
        current_bucket = _recent.get(client)
        if len(_global_recent) >= 60 or (current_bucket is not None and len(current_bucket) >= REQUESTS_PER_MINUTE):
            raise HTTPException(429, "Recommendation rate limit reached; retry in one minute.",
                                headers={"Retry-After": "60"})
        _recent.setdefault(client, deque()).append(now)
        _global_recent.append(now)


async def _plan(payload: PlanningRequest) -> PlanReport:
    from zaad.engine import plan
    if not _slots.acquire(blocking=False):
        raise HTTPException(429, "Both planning slots are busy; retry shortly.")
    try:
        return await run_in_threadpool(plan, payload)
    finally:
        _slots.release()


@router.get("/demo", dependencies=[Depends(bounded_rate), Depends(legacy_planner_gate)], deprecated=True)
async def demo(
    case: Literal["balanced", "overstock", "understock", "disruption", "false_alarm", "recovery"] = "balanced",
    authed: str | None = Depends(require_operator),
):
    from zaad.demo import demo_request
    payload = demo_request(case=case)
    if authed:
        payload = payload.model_copy(update={"operator_id": authed})
    return {"request": payload, "report": await _plan(payload),
            "classification": "SYNTHETIC demonstration; not customer validation or live risk intelligence"}


@router.post("/plan", response_model=PlanReport, dependencies=[Depends(bounded_rate), Depends(legacy_planner_gate)], deprecated=True)
async def recommend(request: Request, authed: str | None = Depends(require_operator)):
    if request.headers.get("content-type", "").split(";", 1)[0].strip() != "application/json":
        raise HTTPException(415, "Send a canonical application/json planning request.")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_BODY_BYTES:
            raise HTTPException(413, "Canonical planning request exceeds 2 MiB.")
        body.extend(chunk)
    try:
        payload = PlanningRequest.model_validate_json(body)
    except ValidationError as exc:
        # Pydantic errors can include the complete sensitive input; return
        # only locations and rule messages, never the input or context.
        raise HTTPException(422, [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]}
                                 for e in exc.errors(include_input=False, include_context=False)]) from exc
    if authed is not None and payload.operator_id != authed:
        raise HTTPException(403, "Request operator does not match the authenticated workspace.")
    return await _plan(payload)


@router.get("/schema", dependencies=[Depends(bounded_rate)])
def schema():
    """Public format only; no customer data or credentials."""
    return json.loads(json.dumps(PlanningRequest.model_json_schema()))
