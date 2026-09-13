"""P5 ATP / scarce-supply allocation: isolated, default-off endpoint (parallel phase).

POST /api/zaad/atp/promise runs the P5 engine (shared orchestration, `zaad/atp/integration.py`) on a
frozen `Request` that carries an enabled `atp` block: the operator's incumbent promising rule and the exact allocation on the same
supply state, priced on the shared ledger, the request's materiality standard, the operator report.
It never calls the planner (no P0-P4 decision is made or changed here), never persists a promise,
and always answers `approval_required: true`, `executable_promise: false`. A request without an
enabled block is refused (422 `atp_absent`): this endpoint has no frozen-path behaviour to fall back to.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request as HTTPRequest
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError

from api.dependencies import require_operator
from api.routers.zaad import bounded_rate
from zaad.atp.contracts import INTERACTIVE_LIMITS, resolve
from zaad.atp.integration import atp_block
from zaad.atp.validation import within_interactive_limits
from zaad.full.contracts import Request

router = APIRouter(prefix="/api/zaad/atp", tags=["zaad-atp"])


def enabled() -> None:
    """Feature flag: the endpoint exists only when ZAAD_ATP_ENABLED=1 (default off in every environment)."""
    if os.getenv("ZAAD_ATP_ENABLED", "0") != "1":
        raise HTTPException(404, "ATP / allocation is not enabled in this environment.")


async def payload(request: HTTPRequest) -> Request:
    if request.headers.get("content-type", "").split(";", 1)[0].strip() != "application/json":
        raise HTTPException(415, "application/json required")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > 2 * 1024 * 1024:
            raise HTTPException(413, "Snapshots over 2 MiB are outside the interactive ATP envelope.")
        body.extend(chunk)
    try:
        req = Request.model_validate_json(body)
    except ValidationError as exc:
        errors = exc.errors(include_input=False, include_context=False)
        code = "atp_invalid" if any("atp" in str(e.get("loc", ())) or "atp:" in str(e.get("msg", "")) for e in errors) else "request_invalid"
        raise HTTPException(422, {"code": code, "errors": [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in errors]}) from exc
    atp = resolve(req)
    if atp is None:
        raise HTTPException(422, {"code": "atp_absent", "message": "This endpoint needs an enabled `atp` block; planning without one is /api/zaad/network/plan."})
    ok, why = within_interactive_limits(atp)
    if not ok:
        raise HTTPException(413, f"Interactive ATP bounds exceeded: {why}; limits {INTERACTIVE_LIMITS}.")
    return req


@router.post("/promise", dependencies=[Depends(bounded_rate), Depends(enabled)])
async def promise_endpoint(request: HTTPRequest, operator: str | None = Depends(require_operator)):
    req = await payload(request)
    if operator is not None and req.operator_id != operator:
        raise HTTPException(403, "Operator mismatch")
    atp = resolve(req)
    if atp is None:   # payload() already refused an absent block; defensive, never reached
        raise HTTPException(422, {"code": "atp_absent", "message": "an enabled `atp` block is required"})
    report = await run_in_threadpool(atp_block, req, atp, seconds=min(30., float(req.max_solve_seconds)))
    if report is None or report["verdict"].startswith("REFUSED"):
        raise HTTPException(422, {"code": "atp_refused", "message": (report or {}).get("reason", "refused")})
    return {"atp": report, "approval_required": True, "executable_promise": False, "executable_purchase_order": False}
