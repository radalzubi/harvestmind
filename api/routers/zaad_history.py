"""The closed loop's record: audit, decision responses, outcomes, settings, people, telemetry.

Everything here is the operator's own record in the operator's own vault. Nothing here
transmits, and nothing here attributes an outcome to ZAAD: an outcome is what was observed after
an action, recorded by a person or matched from the operator's own receipts.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request as HTTPRequest
from fastapi.responses import Response

from api.dependencies import get_conn, rate_limiter, require_actor
from api.product import drafts, governance
from api.product.catalog import _one, _rows
from api.product.governance import Actor, Forbidden, need

router = APIRouter(prefix="/api/zaad", tags=["zaad-history"], dependencies=[Depends(rate_limiter)])

MAX_BODY_BYTES = 256 * 1024


def acting(actor: Actor | None = Depends(require_actor)) -> Actor:
    if actor is None:
        raise HTTPException(401, "Open your workspace first.")
    return actor


Who = Annotated[Actor, Depends(acting)]


def allowed(actor: Actor, capability: str) -> None:
    try:
        need(actor, capability)
    except Forbidden as exc:
        raise HTTPException(403, {"code": "forbidden", "message": str(exc)}) from exc


async def body_of(request: HTTPRequest) -> dict[str, Any]:
    if request.headers.get("content-type", "").split(";", 1)[0].strip() != "application/json":
        raise HTTPException(415, "application/json required")
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > MAX_BODY_BYTES:
            raise HTTPException(413, "That request is larger than ZAAD accepts here.")
        raw.extend(chunk)
    try:
        parsed = json.loads(raw or b"{}")
    except ValueError as exc:
        raise HTTPException(400, "That request body is not valid JSON.") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(400, "A JSON object is expected.")
    return parsed


def _rid(request: HTTPRequest) -> str | None:
    return getattr(request.state, "request_id", None)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── the audit log ─────────────────────────────────────────────────────────────

@router.get("/audit")
def audit(who: Who, conn=Depends(get_conn), object_type: str | None = None, object_id: str | None = None,
          limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    """Append-only. There is no endpoint that deletes from it, by design."""
    drafts.ensure_tables(conn)
    return governance.read_audit(conn, who.operator_id, object_type=object_type, object_id=object_id, limit=limit, offset=offset)


# ── who is here, and the workspace's policy ───────────────────────────────────

@router.get("/workspace/me")
def whoami(who: Who, conn=Depends(get_conn)):
    drafts.ensure_tables(conn)
    return {"actor": {"id": who.actor_id, "name": who.name, "role": who.role}, "capabilities": sorted(who.capabilities),
            "roles": {role: sorted(caps) for role, caps in governance.ROLE_CAPABILITIES.items()},
            "policy": governance.settings(conn, who.operator_id)}


@router.get("/workspace/settings")
def read_settings(who: Who, conn=Depends(get_conn)):
    drafts.ensure_tables(conn)
    return {"settings": governance.settings(conn, who.operator_id), "keys": {k: (list(v) if v else None) for k, v in governance.SETTINGS.items()}}


@router.put("/workspace/settings")
async def write_settings(request: HTTPRequest, who: Who, conn=Depends(get_conn)):
    allowed(who, "manageSettings")
    drafts.ensure_tables(conn)
    body = await body_of(request)
    out: dict[str, Any] = {}
    try:
        for key, value in body.items():
            out = governance.set_setting(conn, who, str(key), value, request_id=_rid(request))
    except governance.SettingRefused as exc:
        raise HTTPException(422, {"code": "setting_refused", "message": str(exc)}) from exc
    return {"settings": out or governance.settings(conn, who.operator_id)}


@router.get("/workspace/actors")
def actors(who: Who, conn=Depends(get_conn)):
    """The people in this workspace, without their tokens. The pilot administrator is the workspace."""
    allowed(who, "manageActors")
    from infrastructure.operator_registry import OperatorRegistry
    return {"actors": OperatorRegistry().list_actors(who.operator_id), "roles": list(governance.ROLES)}


@router.delete("/workspace/actors/{actor_id}", status_code=204)
def revoke_actor(actor_id: str, request: HTTPRequest, who: Who, conn=Depends(get_conn)):
    allowed(who, "manageActors")
    drafts.ensure_tables(conn)
    from infrastructure.operator_registry import OperatorRegistry
    if not OperatorRegistry().revoke_actor(who.operator_id, actor_id):
        raise HTTPException(404, "That person is not in this workspace.")
    governance.record_audit(conn, who, object_type="actor", object_id=actor_id, action="revoked", request_id=_rid(request))
    return Response(status_code=204)


# ── decision responses ───────────────────────────────────────────────────────

RESPONSE_STATUSES = ("REVIEWED", "ACCEPTED", "OVERRIDDEN", "REJECTED")
REASON_CODES = ("supplier_relationship", "contract_not_represented", "cash_constraint", "customer_commitment",
                "promotion", "management_decision", "data_wrong", "capacity_unavailable", "other")


@router.get("/decisions/responses")
def list_responses(who: Who, conn=Depends(get_conn), job_id: str | None = None,
                   limit: int = Query(200, ge=1, le=500), offset: int = Query(0, ge=0)):
    drafts.ensure_tables(conn)
    where = ["operator_id = ?"]
    params: list[Any] = [who.operator_id]
    if job_id:
        where.append("job_id = ?")
        params.append(job_id)
    clause = " WHERE " + " AND ".join(where)
    rows = _rows(conn, f"SELECT * FROM zaad_decision_responses{clause} ORDER BY updated_at DESC LIMIT ? OFFSET ?",  # noqa: S608  # nosec B608 - code literals; values bind
                 [*params, limit, offset])
    total = int(_one(conn, f"SELECT count(*) FROM zaad_decision_responses{clause}", params) or 0)  # noqa: S608  # nosec B608 - code literals; values bind
    return {"rows": rows, "total": total, "reason_codes": list(REASON_CODES), "statuses": list(RESPONSE_STATUSES)}


@router.post("/decisions/responses")
async def respond(request: HTTPRequest, who: Who, conn=Depends(get_conn)):
    """What a person did about a decision ZAAD produced. One row per (job, decision), updated in place.

    The decision itself is reproducible from the job store; this records the response — reviewed,
    accepted, overridden, rejected — with a structured reason when the person has one, free text when
    they want it, and the proposal it turned into when it did. Never a claim that anything executed.
    """
    allowed(who, "respondDecision")
    drafts.ensure_tables(conn)
    body = await body_of(request)
    job_id = drafts._identifier(body.get("job_id"), "Job id")
    decision_id = drafts._identifier(body.get("decision_id"), "Decision id")
    status = str(body.get("status") or "").upper()
    if not job_id or not decision_id:
        raise HTTPException(422, {"code": "response_refused", "message": "A response names the plan (job_id) and the decision (decision_id)."})
    if status not in RESPONSE_STATUSES:
        raise HTTPException(422, {"code": "response_refused", "message": f"status is one of {', '.join(RESPONSE_STATUSES)}."})
    reason_code = body.get("reason_code")
    if reason_code not in (None, "") and reason_code not in REASON_CODES:
        raise HTTPException(422, {"code": "response_refused", "message": f"reason_code is one of {', '.join(REASON_CODES)}, or absent."})
    reason_text = (str(body.get("reason_text"))[:2000] if body.get("reason_text") else None)
    draft_id = drafts._identifier(body.get("draft_id"), "Proposal id")
    # the plan must be this workspace's: a job of another tenant is indistinguishable from a missing one
    from api.routers.zaad_full import runner
    try:
        job = runner().store.get(job_id, who.operator_id)
    except KeyError as exc:
        raise HTTPException(404, "That plan is not in this workspace.") from exc
    except HTTPException:
        job = {}
    report = job.get("report") or {}
    existing = _rows(conn, "SELECT * FROM zaad_decision_responses WHERE operator_id = ? AND job_id = ? AND decision_id = ?",
                     [who.operator_id, job_id, decision_id])
    stamp = _now()
    if existing:
        before = existing[0]["status"]
        conn.execute("UPDATE zaad_decision_responses SET status = ?, reason_code = ?, reason_text = ?, draft_id = coalesce(?, draft_id), "
                     "actor = ?, updated_at = ?, recommended = coalesce(?, recommended), target_type = coalesce(?, target_type), "
                     "target_id = coalesce(?, target_id) WHERE response_id = ? AND operator_id = ?",
                     [status, reason_code or None, reason_text, draft_id, who.actor_id, stamp, body.get("recommended"),
                      body.get("target_type"), body.get("target_id"), existing[0]["response_id"], who.operator_id])
        response_id = existing[0]["response_id"]
    else:
        before = None
        response_id = f"resp_{uuid.uuid4().hex[:12]}"
        conn.execute("INSERT INTO zaad_decision_responses (response_id, operator_id, job_id, decision_id, target_type, target_id, "
                     "recommended, status, reason_code, reason_text, draft_id, information_hash, as_of, actor, created_at, updated_at) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     [response_id, who.operator_id, job_id, decision_id, body.get("target_type"), body.get("target_id"),
                      body.get("recommended"), status, reason_code or None, reason_text, draft_id,
                      report.get("information_hash"), report.get("as_of"), who.actor_id, stamp, stamp])
    governance.record_audit(conn, who, object_type="decision", object_id=f"{job_id}/{decision_id}", action="response_recorded",
                            before_state=before, after_state=status, request_id=_rid(request),
                            context={"reason_code": reason_code or None, "draft_id": draft_id, "has_text": bool(reason_text)})
    return _rows(conn, "SELECT * FROM zaad_decision_responses WHERE response_id = ? AND operator_id = ?", [response_id, who.operator_id])[0]


# ── outcomes and realized value ───────────────────────────────────────────────

OUTCOME_METRICS: dict[str, str] = {
    "received_units": "units", "receipt_date": "date", "purchase_cost": "money", "fill_rate": "fraction",
    "lead_days": "days", "stockout_days": "days", "expedite_cost": "money", "waste_units": "units",
    "working_capital": "money", "customer_allocation_units": "units",
}


def realized_value(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Classify what a draft's outcomes support. Strict: "realized savings" needs a comparator."""
    observed = [r for r in rows if r.get("value") is not None or r.get("observed_at")]
    with_comparator = [r for r in rows if r.get("comparator_value") is not None and r.get("comparator_basis")]
    return {
        "realized_outcome": bool(observed),
        "realized_savings": [
            {"metric": r["metric"], "observed": r["value"], "comparator": r["comparator_value"],
             "basis": r["comparator_basis"], "difference": (r["comparator_value"] - r["value"]) if r.get("value") is not None else None,
             "unit": r.get("unit")}
            for r in with_comparator if r.get("metric") in ("purchase_cost", "expedite_cost", "working_capital")],
        "note": ("Observed after the action; not attributed to ZAAD." if observed else
                 "No outcome has been observed for this action yet."),
    }


@router.get("/outcomes")
def list_outcomes(who: Who, conn=Depends(get_conn), draft_id: str | None = None,
                  limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    drafts.ensure_tables(conn)
    where = ["operator_id = ?"]
    params: list[Any] = [who.operator_id]
    if draft_id:
        where.append("draft_id = ?")
        params.append(draft_id)
    clause = " WHERE " + " AND ".join(where)
    rows = _rows(conn, f"SELECT * FROM zaad_outcomes{clause} ORDER BY observed_at DESC NULLS LAST, recorded_at DESC LIMIT ? OFFSET ?",  # noqa: S608  # nosec B608 - code literals; values bind
                 [*params, limit, offset])
    total = int(_one(conn, f"SELECT count(*) FROM zaad_outcomes{clause}", params) or 0)  # noqa: S608  # nosec B608 - code literals; values bind
    return {"rows": rows, "total": total, "metrics": OUTCOME_METRICS,
            "classification": realized_value(rows) if draft_id else None}


@router.post("/orders/{draft_id}/outcomes", status_code=201)
async def record_outcome(draft_id: str, request: HTTPRequest, who: Who, conn=Depends(get_conn)):
    """Record what was observed after an action. Never what ZAAD caused."""
    allowed(who, "recordOutcome")
    drafts.ensure_tables(conn)
    body = await body_of(request)
    try:
        draft = drafts.read_draft(conn, who.operator_id, draft_id)
    except KeyError as exc:
        raise HTTPException(404, "That proposal is not in this workspace.") from exc
    if draft.get("state") not in ("APPROVED", "EXPORTED"):
        raise HTTPException(422, {"code": "outcome_refused", "message": "An outcome follows an action; this proposal was never approved."})
    metric = str(body.get("metric") or "")
    if metric not in OUTCOME_METRICS:
        raise HTTPException(422, {"code": "outcome_refused", "message": f"metric is one of {', '.join(OUTCOME_METRICS)}."})
    key = request.headers.get("Idempotency-Key")
    if key:
        found = governance.recall(conn, who.operator_id, key, request.url.path)
        if found:
            return Response(found["response"], status_code=int(found["status_code"] or 201), media_type="application/json",
                            headers={"Idempotent-Replay": "true"})
    value = drafts._number(body.get("value"), "value") if OUTCOME_METRICS[metric] != "date" else None
    comparator = drafts._number(body.get("comparator_value"), "comparator value")
    basis = (str(body.get("comparator_basis"))[:500] if body.get("comparator_basis") else None)
    if comparator is not None and not basis:
        raise HTTPException(422, {"code": "outcome_refused", "message":
                                  "A comparator needs its basis stated — what it is and where it comes from — or it is not a comparator."})
    observed = body.get("observed_at")
    when = None
    if observed not in (None, ""):
        try:
            when = datetime.fromisoformat(str(observed)[:19])
        except ValueError as exc:
            raise HTTPException(422, {"code": "outcome_refused", "message": "observed_at is not a date ZAAD can read."}) from exc
        if when > _now():
            raise HTTPException(422, {"code": "outcome_refused", "message": "An observation cannot be in the future."})
    identity = f"outcome_{uuid.uuid4().hex[:12]}"
    conn.execute("INSERT INTO zaad_outcomes (outcome_id, operator_id, draft_id, decision_job_id, decision_id, metric, value, unit, "
                 "observed_at, source, comparator_value, comparator_basis, note, actor, recorded_at) "
                 "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 [identity, who.operator_id, draft_id, body.get("decision_job_id"), body.get("decision_id"), metric, value,
                  OUTCOME_METRICS[metric], when, "recorded", comparator, basis,
                  (str(body.get("note"))[:2000] if body.get("note") else None), who.actor_id, _now()])
    drafts.record_event(conn, who.operator_id, draft_id, "outcome recorded", draft.get("revision"), who.actor_id,
                        f"{metric}: {value if value is not None else (when.date().isoformat() if when else '—')}")
    governance.record_audit(conn, who, object_type="outcome", object_id=identity, action="outcome_recorded", request_id=_rid(request),
                            context={"draft_id": draft_id, "metric": metric, "has_comparator": comparator is not None})
    out = _rows(conn, "SELECT * FROM zaad_outcomes WHERE outcome_id = ? AND operator_id = ?", [identity, who.operator_id])[0]
    if key:
        governance.remember(conn, who.operator_id, key, request.url.path, status_code=201, response=json.dumps(out, default=str))
    return out


@router.get("/orders/{draft_id}/history")
def draft_history(draft_id: str, who: Who, conn=Depends(get_conn)):
    """Everything that happened to a proposal and its predecessors: events, audit, exports, outcomes."""
    drafts.ensure_tables(conn)
    try:
        draft = drafts.read_draft(conn, who.operator_id, draft_id)
    except KeyError as exc:
        raise HTTPException(404, "That proposal is not in this workspace.") from exc
    chain: list[str] = []
    current: str | None = draft_id
    seen: set[str] = set()
    while current and current not in seen and len(chain) < 50:
        chain.append(current)
        seen.add(current)
        parent = _rows(conn, "SELECT supersedes FROM zaad_draft_orders WHERE draft_id = ? AND operator_id = ?", [current, who.operator_id])
        current = parent[0].get("supersedes") if parent else None
    placeholders = ", ".join("?" for _ in chain)
    events = _rows(conn, f"SELECT * FROM zaad_draft_events WHERE operator_id = ? AND draft_id IN ({placeholders}) ORDER BY happened_at",  # noqa: S608  # nosec B608 - bound placeholders; values bind
                   [who.operator_id, *chain])
    audit_rows = _rows(conn, f"SELECT * FROM zaad_audit_log WHERE operator_id = ? AND object_type = 'draft' AND object_id IN ({placeholders}) ORDER BY happened_at",  # noqa: S608  # nosec B608 - bound placeholders; values bind
                       [who.operator_id, *chain])
    for row in audit_rows:
        row["context"] = json.loads(row["context"]) if row.get("context") else None
    exports = _rows(conn, f"SELECT * FROM zaad_export_log WHERE operator_id = ? AND draft_id IN ({placeholders}) ORDER BY happened_at",  # noqa: S608  # nosec B608 - bound placeholders; values bind
                    [who.operator_id, *chain])
    outcomes = _rows(conn, f"SELECT * FROM zaad_outcomes WHERE operator_id = ? AND draft_id IN ({placeholders}) ORDER BY observed_at NULLS LAST",  # noqa: S608  # nosec B608 - bound placeholders; values bind
                     [who.operator_id, *chain])
    evaluations = _rows(conn, f"SELECT evaluation_id, draft_id, revision, status, as_of, created_at, baseline_job_id, proposal_job_id, draft_hash, workspace_version "
                              f"FROM zaad_evaluations WHERE operator_id = ? AND draft_id IN ({placeholders}) ORDER BY created_at",  # noqa: S608  # nosec B608 - bound placeholders; values bind
                        [who.operator_id, *chain])
    responses = _rows(conn, f"SELECT * FROM zaad_decision_responses WHERE operator_id = ? AND draft_id IN ({placeholders})",  # noqa: S608  # nosec B608 - bound placeholders; values bind
                      [who.operator_id, *chain])
    return {"draft_id": draft_id, "revisions": chain, "events": events, "audit": audit_rows, "exports": exports,
            "evaluations": evaluations, "outcomes": outcomes, "decision_responses": responses,
            "external": {"status": draft.get("external_status"), "reference": draft.get("external_reference"),
                         "updated_at": draft.get("external_updated_at"), "updated_by": draft.get("external_updated_by"),
                         "recorded_by_person": True},
            "realized_value": realized_value(outcomes), "executable": False}


# ── the decision history feed ─────────────────────────────────────────────────

@router.get("/history")
def history(who: Who, conn=Depends(get_conn), limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    """Decisions responded to, proposals decided, actions placed, outcomes observed — newest first."""
    drafts.ensure_tables(conn)
    responses = _rows(conn, "SELECT * FROM zaad_decision_responses WHERE operator_id = ? ORDER BY updated_at DESC LIMIT ?",
                      [who.operator_id, limit])
    decided = _rows(conn, "SELECT draft_id, reference, origin, state, revision, supplier_id, approved_by, approved_at, "
                          "decision_reason, approved_evaluation_id, approval_evaluation_state, external_status, external_reference, "
                          "external_updated_at, source_decision_id, source_po_id, updated_at FROM zaad_draft_orders "
                          "WHERE operator_id = ? AND state IN ('APPROVED', 'EXPORTED', 'REJECTED') ORDER BY updated_at DESC LIMIT ?",
                    [who.operator_id, limit])
    outcomes = _rows(conn, "SELECT * FROM zaad_outcomes WHERE operator_id = ? ORDER BY recorded_at DESC LIMIT ?", [who.operator_id, limit])
    counts = {
        "awaiting_approval": int(_one(conn, "SELECT count(*) FROM zaad_draft_orders WHERE operator_id = ? AND state = 'READY_FOR_REVIEW'", [who.operator_id]) or 0),
        "approved_not_placed": int(_one(conn, "SELECT count(*) FROM zaad_draft_orders WHERE operator_id = ? AND state IN ('APPROVED','EXPORTED') AND external_status IS NULL", [who.operator_id]) or 0),
        "placed_not_acknowledged": int(_one(conn, "SELECT count(*) FROM zaad_draft_orders WHERE operator_id = ? AND external_status = 'PLACED_EXTERNALLY'", [who.operator_id]) or 0),
        "outcomes_recorded": int(_one(conn, "SELECT count(*) FROM zaad_outcomes WHERE operator_id = ?", [who.operator_id]) or 0),
        "responses": int(_one(conn, "SELECT count(*) FROM zaad_decision_responses WHERE operator_id = ?", [who.operator_id]) or 0),
    }
    return {"responses": responses, "decided": decided, "outcomes": outcomes, "counts": counts,
            "registers": ["MODELED_DIFFERENCE", "BACKTESTED_OPPORTUNITY", "OPERATOR_APPROVED_EXPECTED_DIFFERENCE",
                          "REALIZED_OUTCOME", "REALIZED_SAVINGS"],
            "backtested": {"available": False, "note": "No held-out replay of your history is wired into this product."}}


# ── telemetry ─────────────────────────────────────────────────────────────────

TELEMETRY_EVENTS = ("workspace_opened", "decision_opened", "sku_opened", "supplier_opened", "po_created", "po_edited",
                    "po_evaluated", "po_approved", "po_rejected", "po_exported", "external_status_recorded",
                    "diagnostic_opened", "data_readiness_opened", "network_object_opened", "history_opened", "outcome_recorded")
TELEMETRY_KEYS = ("draft_id", "decision_id", "job_id", "sku", "supplier_id", "location", "po_id", "surface", "tab",
                  "node", "kind", "count", "locale")
MAX_TELEMETRY_BATCH = 50


@router.post("/telemetry", status_code=202)
async def telemetry(request: HTTPRequest, who: Who, conn=Depends(get_conn)):
    """Allowlisted event names, allowlisted identifier keys, short values. Nothing else is stored."""
    drafts.ensure_tables(conn)
    body = await body_of(request)
    events = body.get("events")
    if not isinstance(events, list) or len(events) > MAX_TELEMETRY_BATCH:
        raise HTTPException(422, {"code": "telemetry_refused", "message": f"events is a list of at most {MAX_TELEMETRY_BATCH}."})
    stored = 0
    dropped: list[str] = []
    stamp = _now()
    for event in events:
        if not isinstance(event, dict):
            continue
        name = str(event.get("name") or "")
        if name not in TELEMETRY_EVENTS:
            dropped.append(name[:40])
            continue
        given = event.get("properties")
        raw: dict[str, Any] = given if isinstance(given, dict) else {}
        props = {k: str(v)[:80] for k, v in raw.items() if k in TELEMETRY_KEYS and isinstance(v, (str, int, float, bool))}
        conn.execute("INSERT INTO zaad_telemetry (event_id, operator_id, actor, name, properties, happened_at) VALUES (?, ?, ?, ?, ?, ?)",
                     [f"ev_{uuid.uuid4().hex[:12]}", who.operator_id, who.actor_id, name, json.dumps(props, sort_keys=True), stamp])
        stored += 1
    return {"stored": stored, "dropped": dropped, "allowed_events": list(TELEMETRY_EVENTS), "allowed_keys": list(TELEMETRY_KEYS)}
