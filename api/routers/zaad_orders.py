"""Proposed purchase orders: create, edit, evaluate, approve, export.

This is the first place in ZAAD where an operator *writes*. Everything it writes is the operator's
own document, in the operator's own vault, and none of it is ever transmitted: `executable` is
false on every response and the last mile of this release is a file a person downloads.

The evaluation endpoints submit work to the released asynchronous jobs path — the same runner,
quotas and honest states as a plan — because comparing a proposal means solving twice, and a solve
takes minutes.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request as HTTPRequest, UploadFile
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from api.dependencies import get_conn, rate_limiter, require_actor
from api.product import drafts, evaluation, exporting, governance
from api.product.catalog import _one, _rows, has_table
from api.product.governance import Actor, Forbidden, need
from api.routers.zaad import bounded_rate

router = APIRouter(prefix="/api/zaad/orders", tags=["zaad-orders"],
                   dependencies=[Depends(rate_limiter)])

MAX_BODY_BYTES = 1 * 1024 * 1024
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


def acting(actor: Actor | None = Depends(require_actor)) -> Actor:
    """The acting person. Every write below checks one of their capabilities."""
    if actor is None:
        raise HTTPException(401, "Open your workspace to work with proposed orders.")
    return actor


Who = Annotated[Actor, Depends(acting)]


def allowed(actor: Actor, capability: str) -> None:
    try:
        need(actor, capability)
    except Forbidden as exc:
        raise HTTPException(403, {"code": "forbidden", "message": str(exc)}) from exc


def request_id_of(request: HTTPRequest) -> str | None:
    return getattr(request.state, "request_id", None)


def _idempotent(conn: Any, actor: Actor, request: HTTPRequest):
    """The recorded response for a retried request, when the caller sent an Idempotency-Key."""
    key = request.headers.get("Idempotency-Key")
    if not key:
        return None, None
    found = governance.recall(conn, actor.operator_id, key, request.url.path)
    if found is None:
        return key, None
    if (found.get("media_type") or "application/json") == "application/json":
        return key, _JSONReplay(int(found.get("status_code") or 200), json.loads(found.get("response") or "{}"))
    import base64
    return key, Response(base64.b64decode(found.get("response") or ""), status_code=int(found.get("status_code") or 200),
                         media_type=found.get("media_type"), headers={**json.loads(found.get("headers") or "{}"),
                                                                       "Idempotent-Replay": "true"})


class _JSONReplay(Response):
    def __init__(self, status_code: int, body: Any):
        super().__init__(json.dumps(body), status_code=status_code, media_type="application/json",
                         headers={"Idempotent-Replay": "true"})


def _remember_json(conn: Any, actor: Actor, key: str | None, request: HTTPRequest, status_code: int, body: Any) -> None:
    if key:
        governance.remember(conn, actor.operator_id, key, request.url.path, status_code=status_code,
                            response=json.dumps(body, default=str))


async def body_of(request: HTTPRequest) -> dict[str, Any]:
    """A bounded JSON object. A proposal is a document, not a bulk upload."""
    if request.headers.get("content-type", "").split(";", 1)[0].strip() != "application/json":
        raise HTTPException(415, "application/json required")
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > MAX_BODY_BYTES:
            raise HTTPException(413, "That proposal is larger than ZAAD accepts in one document.")
        raw.extend(chunk)
    try:
        parsed = json.loads(raw or b"{}")
    except ValueError as exc:
        raise HTTPException(400, "That request body is not valid JSON.") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(400, "A proposal is a JSON object.")
    return parsed


def _refused(exc: Exception) -> HTTPException:
    return HTTPException(422, {"code": "proposal_refused", "message": str(exc)})


# ── the list and one proposal ─────────────────────────────────────────────────

@router.get("")
def list_orders(
    who: Who, conn=Depends(get_conn), state: str | None = None, origin: str | None = None,
    supplier_id: str | None = None, source_po_id: str | None = None, q: str | None = None,
    external_status: str | None = None,
    sort: str = "updated_at", direction: Literal["asc", "desc"] = "desc",
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
):
    try:
        return drafts.list_drafts(conn, who.operator_id, state=state, origin=origin, supplier_id=supplier_id,
                                  source_po_id=source_po_id, search=q, sort=sort, direction=direction,
                                  limit=limit, offset=offset, external_status=external_status)
    except drafts.DraftRefused as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("", status_code=201)
async def create_order(request: HTTPRequest, who: Who, conn=Depends(get_conn)):
    """Create a proposal. Every origin — recommendation, current policy, manual, upload, amendment."""
    allowed(who, "createProposal")
    body = await body_of(request)
    key, replay = _idempotent(conn, who, request)
    if replay is not None:
        return replay
    try:
        identity = drafts.create_draft(conn, who.operator_id, body, actor=who.actor_id, who=who,
                                       request_id=request_id_of(request))
    except drafts.DraftRefused as exc:
        raise _refused(exc) from exc
    out = {**drafts.read_draft(conn, who.operator_id, identity), "executable": False, "transmitted": False}
    _remember_json(conn, who, key, request, 201, out)
    return out


@router.post("/bulk", status_code=201)
async def create_orders_bulk(request: HTTPRequest, who: Who, conn=Depends(get_conn)):
    """Create several proposals as one unit — all or none.

    The body is `{"drafts": [<same shape as POST /api/zaad/orders>, ...]}`, at most 50. Used for
    bulk creation from selected recommendations; the grouping (one proposal per supplier and
    destination) is done deterministically by the caller and every group is created here in one
    transaction, so a refused line in one group creates nothing anywhere.
    """
    allowed(who, "createProposal")
    body = await body_of(request)
    key, replay = _idempotent(conn, who, request)
    if replay is not None:
        return replay
    bodies = body.get("drafts")
    if not isinstance(bodies, list):
        raise HTTPException(400, {"code": "proposal_refused", "message": "Send the proposals as a list under \"drafts\"."})
    try:
        identities = drafts.create_drafts(conn, who.operator_id, bodies, actor=who.actor_id, who=who,
                                          request_id=request_id_of(request))
    except drafts.DraftRefused as exc:
        raise _refused(exc) from exc
    out = {"drafts": [drafts.read_draft(conn, who.operator_id, i) for i in identities],
           "created": len(identities), "executable": False, "transmitted": False}
    _remember_json(conn, who, key, request, 201, out)
    return out


@router.get("/profiles")
def profiles(who: Who, conn=Depends(get_conn)):
    """The workspace's own output formats, plus the built-in one it starts with."""
    return {"profiles": [exporting.default_profile(), *drafts.list_profiles(conn, who.operator_id)],
            "fields": exporting.EXPORT_FIELDS, "formats": list(exporting.FORMATS),
            "import_fields": exporting.IMPORT_FIELDS,
            "default_profile_id": governance.settings(conn, who.operator_id).get("default_export_profile")}


@router.post("/profiles", status_code=201)
async def create_profile(request: HTTPRequest, who: Who, conn=Depends(get_conn)):
    allowed(who, "manageProfiles")
    body = await body_of(request)
    try:
        identity = drafts.save_profile(conn, who.operator_id, body, who=who, request_id=request_id_of(request))
    except drafts.DraftRefused as exc:
        raise _refused(exc) from exc
    return {"profile_id": identity}


@router.put("/profiles/{profile_id}")
async def update_profile(profile_id: str, request: HTTPRequest, who: Who, conn=Depends(get_conn)):
    allowed(who, "manageProfiles")
    body = await body_of(request)
    try:
        drafts.save_profile(conn, who.operator_id, body, profile_id=profile_id, who=who, request_id=request_id_of(request))
    except KeyError as exc:
        raise HTTPException(404, "That format is not in this workspace.") from exc
    except drafts.DraftRefused as exc:
        raise _refused(exc) from exc
    return {"profile_id": profile_id}


@router.delete("/profiles/{profile_id}", status_code=204)
def remove_profile(profile_id: str, request: HTTPRequest, who: Who, conn=Depends(get_conn)):
    allowed(who, "manageProfiles")
    try:
        drafts.delete_profile(conn, who.operator_id, profile_id, who=who, request_id=request_id_of(request))
    except KeyError as exc:
        raise HTTPException(404, "That format is not in this workspace.") from exc
    return Response(status_code=204)


@router.post("/profiles/read-template")
async def read_template(who: Who, file: UploadFile = File(...)):
    """Read the column headings of a template the operator already uses, so they can be mapped.

    Only the heading row is read. Nothing in the file is evaluated and nothing is sent anywhere:
    the mapping the buyer confirms is stored as data and applied deterministically at export.
    """
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "That file is larger than ZAAD reads for a template.")
    try:
        found = exporting.read_template_headers(content, file.filename or "")
    except exporting.ExportRefused as exc:
        raise HTTPException(422, str(exc)) from exc
    return {**found, "suggested_columns": exporting.suggest_mapping(found["headers"]),
            "fields": exporting.EXPORT_FIELDS}


@router.post("/read-proposal")
async def read_proposal(
    who: Who,
    file: UploadFile = File(...),
    mapping: str | None = Form(None, description="JSON object of {field: column heading}; omit for a suggestion"),
):
    """Read a proposed order out of a buyer's spreadsheet.

    Two steps on purpose: without a mapping this returns the headings and ZAAD's guess at each one,
    and the buyer confirms or changes it; with a mapping it returns the lines that mapping produces,
    along with every row it could not read. Nothing is stored until the buyer creates the proposal.
    """
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "That file is larger than ZAAD reads in one upload.")
    try:
        table = exporting.read_table(content, file.filename or "")
    except exporting.ExportRefused as exc:
        raise HTTPException(422, str(exc)) from exc
    if not mapping:
        return {"headers": table["headers"], "preview": table["rows"][:10], "rows": len(table["rows"]),
                "truncated": table["truncated"], "suggested_mapping": exporting.suggest_import_mapping(table["headers"]),
                "fields": exporting.IMPORT_FIELDS}
    try:
        chosen = json.loads(mapping)
        if not isinstance(chosen, dict):
            raise ValueError("a mapping is an object of field to column heading")
        lines, order, problems = exporting.rows_to_lines(table["headers"], table["rows"],
                                                         {str(k): str(v) for k, v in chosen.items()})
    except (ValueError, exporting.ExportRefused) as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"lines": lines, "order": order, "problems": problems, "rows": len(table["rows"]),
            "truncated": table["truncated"]}


@router.get("/evaluation-jobs")
def evaluation_jobs(who: Who, conn=Depends(get_conn)):
    operator = who.operator_id
    """Job ids that belong to a proposal evaluation rather than to the workspace's own plan.

    An evaluation runs the released jobs path twice, and one of those runs carries a proposed order
    overlaid on the pipeline. Nothing in the job record distinguishes it from a plan, so a surface
    that shows "the last completed plan" would otherwise show a plan of a workspace *plus an order
    nobody has placed* and present it as the operator's position. This is the list to exclude.
    """
    from api.routers.zaad_full import runner

    drafts.ensure_tables(conn)
    rows = _rows(conn, "SELECT baseline_job_id, proposal_job_id FROM zaad_evaluations WHERE operator_id = ?",
                 [operator])
    identities = {str(value) for row in rows for value in row.values() if value}

    # The job's own purpose is the authoritative answer since the V1 audit: every evaluation run is
    # submitted as PROPOSAL_BASELINE or PROPOSAL_OVERLAY and a reader selects plans by purpose. The
    # vault record above and the request-shape guard below remain for runs written before purposes
    # existed, and for a vault that was replaced while the job store kept its runs.
    try:
        store = runner().store
        for job in store.list(operator):
            identity = str(job.get("id"))
            if identity in identities:
                continue
            if str(job.get("purpose") or "").startswith("PROPOSAL_"):
                identities.add(identity)
                continue
            try:
                if '"proposal_' in store.request_json(identity):
                    identities.add(identity)
            except Exception:  # noqa: BLE001 - a job whose request has been pruned is simply not one
                continue
    except HTTPException:
        pass  # no job store configured in this environment; the vault record is the whole answer
    return {"evaluation_job_ids": sorted(identities)}


@router.get("/{draft_id}")
def read_order(draft_id: str, who: Who, conn=Depends(get_conn)):
    try:
        return drafts.read_draft(conn, who.operator_id, draft_id)
    except KeyError as exc:
        raise HTTPException(404, "That proposal is not in this workspace.") from exc


def _version_of(body: dict[str, Any]) -> int | None:
    raw = body.get("expected_version")
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(422, {"code": "proposal_refused", "message": "expected_version is a whole number."}) from exc


def _write_refused(exc: drafts.DraftRefused) -> HTTPException:
    if isinstance(exc, drafts.StaleWrite):
        return HTTPException(409, {"code": "stale_write", "message": str(exc)})
    if isinstance(exc, drafts.SelfApprovalNotAllowed):
        return HTTPException(422, {"code": "self_approval_not_allowed", "message": str(exc)})
    if isinstance(exc, drafts.EvaluationStale):
        return HTTPException(422, {"code": "evaluation_stale", "message": str(exc)})
    return _refused(exc)


@router.patch("/{draft_id}")
async def edit_order(draft_id: str, request: HTTPRequest, who: Who, conn=Depends(get_conn)):
    allowed(who, "editDraft")
    body = await body_of(request)
    try:
        return drafts.update_draft(conn, who.operator_id, draft_id, body, actor=who.actor_id, who=who,
                                   request_id=request_id_of(request), expected_version=_version_of(body))
    except KeyError as exc:
        raise HTTPException(404, "That proposal is not in this workspace.") from exc
    except drafts.DraftRefused as exc:
        raise _write_refused(exc) from exc


@router.delete("/{draft_id}", status_code=204)
def remove_order(draft_id: str, request: HTTPRequest, who: Who, conn=Depends(get_conn)):
    allowed(who, "editDraft")
    try:
        drafts.delete_draft(conn, who.operator_id, draft_id, actor=who.actor_id, who=who, request_id=request_id_of(request))
    except KeyError as exc:
        raise HTTPException(404, "That proposal is not in this workspace.") from exc
    except drafts.DraftRefused as exc:
        raise _refused(exc) from exc
    return Response(status_code=204)


@router.post("/{draft_id}/actions/{action}")
async def act(draft_id: str, action: Literal["submit", "reopen", "approve", "reject"],
              request: HTTPRequest, who: Who, conn=Depends(get_conn)):
    allowed(who, "approve" if action in ("approve", "reject") else "review")
    body = await body_of(request)
    key, replay = _idempotent(conn, who, request)
    if replay is not None:
        return replay
    try:
        out = drafts.transition(conn, who.operator_id, draft_id, action, actor=who.actor_id,
                                reason=body.get("reason"), acknowledge_stale=bool(body.get("acknowledge_stale")),
                                who=who, request_id=request_id_of(request), expected_version=_version_of(body))
    except KeyError as exc:
        raise HTTPException(404, "That proposal is not in this workspace.") from exc
    except drafts.DraftRefused as exc:
        # A stale evaluation is refused, not silently: the approver may say "I know" —
        # `acknowledge_stale: true` — and that is then part of the record the next reader sees.
        raise _write_refused(exc) from exc
    _remember_json(conn, who, key, request, 200, out)
    return out


@router.post("/{draft_id}/external-status")
async def external_status(draft_id: str, request: HTTPRequest, who: Who, conn=Depends(get_conn)):
    """A person records what happened to this order outside ZAAD: placed, acknowledged, delivered.

    ZAAD does not place, send or receive orders. This is the operator's statement, with who, when
    and the reference their system or supplier gave; it is an event and an audit row.
    """
    allowed(who, "recordExternal")
    body = await body_of(request)
    key, replay = _idempotent(conn, who, request)
    if replay is not None:
        return replay
    try:
        out = drafts.record_external_status(
            conn, who.operator_id, draft_id, status=str(body.get("status") or ""),
            external_reference=body.get("external_reference"), note=body.get("note"), observed_at=body.get("observed_at"),
            actor=who.actor_id, who=who, request_id=request_id_of(request), expected_version=_version_of(body))
    except KeyError as exc:
        raise HTTPException(404, "That proposal is not in this workspace.") from exc
    except drafts.DraftRefused as exc:
        raise _write_refused(exc) from exc
    _remember_json(conn, who, key, request, 200, out)
    return out


@router.post("/{draft_id}/revise", status_code=201)
def revise_order(draft_id: str, request: HTTPRequest, who: Who, conn=Depends(get_conn)):
    """The next revision of a proposal that is already part of the record."""
    allowed(who, "editDraft")
    try:
        identity = drafts.revise(conn, who.operator_id, draft_id, actor=who.actor_id, who=who, request_id=request_id_of(request))
    except KeyError as exc:
        raise HTTPException(404, "That proposal is not in this workspace.") from exc
    except drafts.DraftRefused as exc:
        raise _refused(exc) from exc
    return drafts.read_draft(conn, who.operator_id, identity)


# ── export ────────────────────────────────────────────────────────────────────

@router.get("/{draft_id}/export/preview")
def export_preview(draft_id: str, who: Who, conn=Depends(get_conn), profile_id: str | None = Query(None)):
    """Which format an export would use, and why, before anything is produced (V2 §53)."""
    try:
        draft = drafts.read_draft(conn, who.operator_id, draft_id)
        choice = drafts.profile_choice(conn, who.operator_id, draft, profile_id)
    except KeyError as exc:
        raise HTTPException(404, "That proposal or format is not in this workspace.") from exc
    from api.product.outbound import FileExportAdapter
    adapter = FileExportAdapter()
    return {"draft_id": draft_id, "profile": {k: v for k, v in choice["profile"].items() if k != "columns"},
            "columns": choice["profile"].get("columns"), "reason": choice["reason"], "detail": choice["detail"],
            "exportable": draft.get("exportable", False), "adapter": adapter.describe(),
            "validation": adapter.validate(draft, choice["profile"])}


@router.post("/{draft_id}/export")
def export_order(draft_id: str, request: HTTPRequest, who: Who, conn=Depends(get_conn),
                 profile_id: str | None = Query(None),
                 fmt: Literal["csv", "xlsx", "print"] | None = Query(None, alias="format")):
    """Produce the file. **This does not send anything to a supplier or an ERP.**

    The last mile goes through the outbound adapter seam: today the one real adapter writes a
    file; a connector would take the same approved canonical action object. The format is chosen
    by the declared hierarchy (chosen → supplier default → workspace default → standard) and the
    choice is recorded with the export.
    """
    allowed(who, "export")
    key, replay = _idempotent(conn, who, request)
    if replay is not None:
        return replay
    try:
        draft = drafts.read_draft(conn, who.operator_id, draft_id)
    except KeyError as exc:
        raise HTTPException(404, "That proposal is not in this workspace.") from exc
    if not draft.get("lines"):
        raise HTTPException(422, {"code": "proposal_refused", "message": "This proposal has no lines to export."})
    if draft.get("state") not in drafts.EXPORTABLE:
        # A file that reads as a purchase order leaves only for a decided one. Before this check an
        # unapproved draft produced a file with nothing on it saying it was unapproved.
        raise HTTPException(422, {"code": "not_approved", "message":
                                  "Only an approved proposal is exported. Approve it first — or reject it, and "
                                  "nothing leaves."})
    try:
        choice = drafts.profile_choice(conn, who.operator_id, draft, profile_id)
    except KeyError as exc:
        raise HTTPException(404, "That output format is not in this workspace.") from exc
    profile = dict(choice["profile"])
    if fmt:
        profile["format"] = fmt

    names: dict[str, str] = {}
    descriptions: dict[str, str] = {}
    if has_table(conn, "stg_fmcg_suppliers") and draft.get("supplier_id"):
        found = _one(conn, "SELECT any_value(supplier_name) FROM stg_fmcg_suppliers WHERE supplier_id = ?",
                     [draft["supplier_id"]])
        if found:
            names[str(draft["supplier_id"])] = str(found)
    if has_table(conn, "stg_fmcg_skus") and draft["lines"]:
        for row in _rows(conn, f"""SELECT sku, any_value(sku_name) AS n FROM stg_fmcg_skus
                                   WHERE sku IN ({', '.join('?' for _ in draft['lines'])}) GROUP BY sku""",  # nosec B608 - bound placeholders only; values bind
                         [str(line["sku"]) for line in draft["lines"]]):
            if row.get("n"):
                descriptions[str(row["sku"])] = str(row["n"])
    for line in draft["lines"]:
        line["sku_name"] = descriptions.get(str(line["sku"]), "")

    from api.product.outbound import FileExportAdapter, OutboundRefused
    adapter = FileExportAdapter()
    try:
        result = adapter.submit(draft, profile, supplier_names=names, workspace=who.operator_id)
    except OutboundRefused as exc:
        raise HTTPException(422, str(exc)) from exc
    drafts.record_export(conn, who.operator_id, draft_id, revision=draft.get("revision"),
                         profile_id=profile.get("profile_id"), profile_name=str(profile.get("name")),
                         fmt=str(profile.get("format")), filename=result.filename, actor=who.actor_id, who=who,
                         request_id=request_id_of(request), adapter=adapter.name)
    headers = {"Content-Disposition": f'attachment; filename="{result.filename}"',
               "X-ZAAD-Transmitted": "false", "X-ZAAD-Export-Profile": str(profile.get("profile_id") or "standard"),
               "X-ZAAD-Export-Choice": choice["reason"]}
    if key:
        import base64
        governance.remember(conn, who.operator_id, key, request.url.path, status_code=200,
                            response=base64.b64encode(result.payload).decode(), media_type=result.media_type, headers=headers)
    return Response(result.payload, media_type=result.media_type, headers=headers)


# ── evaluation ────────────────────────────────────────────────────────────────

def _amendment_skus(conn: Any) -> set[str]:
    """Products whose open orders carry a declared amendment right.

    A scoped build that leaves one of these out points the declaration at an order the request no
    longer carries, and the workspace adapter rightly refuses it. They travel together or not at all.
    """
    if not (has_table(conn, "stg_po_options") and has_table(conn, "stg_fmcg_purchase_orders")):
        return set()
    rows = _rows(conn, """
        SELECT DISTINCT p.sku AS sku FROM stg_po_options o
        JOIN stg_fmcg_purchase_orders p ON p.po_id = o.po_id WHERE p.sku IS NOT NULL""")
    return {str(r["sku"]) for r in rows}


@router.post("/{draft_id}/evaluate", status_code=202, dependencies=[Depends(bounded_rate)])
async def evaluate(draft_id: str, http: HTTPRequest, who: Who, conn=Depends(get_conn),
                   horizon: int = Query(12, ge=4, le=26),
                   service_target: float = Query(.95, gt=.5, le=1.),
                   max_solve_seconds: float = Query(15., gt=0, le=120)):
    """Run the workspace twice — without this proposal and with it — on the released jobs path.

    Both runs share an as-of, a seed and a set of products, so the difference between them is the
    proposal. Each evaluation uses two of the workspace's daily job allowance.
    """
    from zaad.full.jobs import QuotaExceeded
    from api.routers.zaad_full import _workspace_request, runner

    allowed(who, "evaluate")
    operator = who.operator_id
    key, replay = _idempotent(conn, who, http)
    if replay is not None:
        return replay
    try:
        draft = drafts.read_draft(conn, operator, draft_id)
    except KeyError as exc:
        raise HTTPException(404, "That proposal is not in this workspace.") from exc

    if draft.get("origin") == "IMPORTED_AMENDMENT":
        raise HTTPException(422, {"code": "amendment_not_evaluated", "message":
                                  "A change to an existing order is worth what your contract says it is worth. "
                                  "ZAAD prices the amendment rights you have declared for that order, in the "
                                  "plan itself — open the order to see them."})

    amendment = _amendment_skus(conn)
    try:
        scope = evaluation.scope_for(draft, amendment_skus=amendment)
    except evaluation.EvaluationRefused as exc:
        raise HTTPException(422, {"code": "proposal_refused", "message": str(exc)}) from exc
    commitments = amendment.issubset(set(scope))

    try:
        request, _build = await run_in_threadpool(
            _workspace_request, conn, operator, horizon, service_target, ",".join(scope),
            max_solve_seconds, True, sector_mode=None, sourcing=True, recourse=False,
            atp=False, commitments=commitments)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - a build failure is an operator-facing message
        raise HTTPException(422, {"code": "workspace_not_ready", "message": str(exc)}) from exc

    try:
        overlaid, notes = evaluation.overlay(request, draft)
    except evaluation.EvaluationRefused as exc:
        raise HTTPException(422, {"code": "proposal_refused", "message": str(exc)}) from exc

    run = runner()
    # The quota is checked before anything is written, so a refused evaluation leaves no record.
    if run.store.active(operator) + 2 > run.active_quota:
        raise HTTPException(429, {"code": "job_quota", "message":
                                  f"at most {run.active_quota} queued or running jobs per workspace. "
                                  "An evaluation runs the engine twice, so it needs two."})

    # Record first, then submit against the record. A reader that lands between the steps finds
    # two jobs whose purpose says what they are and a record that names them; before this the jobs
    # existed for a moment with nothing marking them, and a workspace read in that moment adopted
    # the baseline run as the operator's plan.
    identity = evaluation.store_evaluation(
        conn, operator, draft_id=draft_id, revision=draft.get("revision"),
        baseline_job_id=None, proposal_job_id=None,
        as_of=request.as_of.isoformat(), scope=scope, status="QUEUED",
        note="; ".join(notes) if notes else None,
        draft_hash=evaluation.content_hash(draft), workspace_version=evaluation.workspace_version(conn))
    drafts.record_event(conn, operator, draft_id, "evaluation requested", draft.get("revision"), who.actor_id,
                        f"{identity} over {len(scope)} product{'' if len(scope) == 1 else 's'}")
    governance.record_audit(conn, who, object_type="evaluation", object_id=identity, action="evaluation_requested",
                            request_id=request_id_of(http),
                            context={"draft_id": draft_id, "revision": draft.get("revision"), "scope": len(scope),
                                     "commitments_included": commitments})
    baseline_job: str | None = None
    try:
        baseline_job = run.submit(operator, request, purpose="PROPOSAL_BASELINE", reference=identity)
        proposal_job = run.submit(operator, overlaid, purpose="PROPOSAL_OVERLAY", reference=identity)
    except QuotaExceeded as exc:
        if baseline_job:
            run.cancel(baseline_job, operator)
        evaluation.fail_evaluation(conn, operator, identity, f"not submitted: {exc}")
        raise HTTPException(429, {"code": "job_quota", "message":
                                  f"{exc} An evaluation runs the engine twice, so it needs two."}) from exc
    except Exception as exc:  # noqa: BLE001 - a failed submission is a failed evaluation, never a silent one
        if baseline_job:
            run.cancel(baseline_job, operator)
        evaluation.fail_evaluation(conn, operator, identity, f"not submitted: {type(exc).__name__}: {exc}"[:2000])
        raise HTTPException(503, {"code": "evaluation_not_submitted", "message":
                                  "The evaluation could not be started. Nothing was changed; try again."}) from exc
    evaluation.link_jobs(conn, operator, identity, baseline_job_id=baseline_job, proposal_job_id=proposal_job)
    out = {"evaluation_id": identity, "status": "QUEUED", "baseline_job_id": baseline_job,
           "proposal_job_id": proposal_job, "scope": scope, "commitments_included": commitments,
           "notes": notes, "executable": False}
    _remember_json(conn, who, key, http, 202, out)
    return out


@router.get("/{draft_id}/evaluation")
def read_evaluation(draft_id: str, who: Who, conn=Depends(get_conn),
                    evaluation_id: str | None = Query(None)):
    """The state of an evaluation, and the comparison once both runs have finished."""
    from api.routers.zaad_full import runner

    operator = who.operator_id
    drafts.ensure_tables(conn)
    try:
        draft = drafts.read_draft(conn, operator, draft_id)
    except KeyError as exc:
        raise HTTPException(404, "That proposal is not in this workspace.") from exc
    # Two literal statements rather than one built by concatenation: the only difference is a bound
    # placeholder, and a reader should not have to prove that to themselves.
    newest = ("SELECT * FROM zaad_evaluations WHERE draft_id = ? AND operator_id = ? "
              "AND evaluation_id = ? ORDER BY created_at DESC LIMIT 1") if evaluation_id else (
              "SELECT * FROM zaad_evaluations WHERE draft_id = ? AND operator_id = ? "
              "ORDER BY created_at DESC LIMIT 1")
    rows = _rows(conn, newest, [draft_id, operator, *([evaluation_id] if evaluation_id else [])])
    if not rows:
        return {"status": "NONE", "draft_id": draft_id,
                "message": "This proposal has not been evaluated yet."}
    record = rows[0]
    scope = json.loads(record["scope_skus"]) if record.get("scope_skus") else []
    store = runner().store
    states: dict[str, Any] = {}
    reports: dict[str, Any] = {}
    for key, job_id in (("baseline", record.get("baseline_job_id")), ("proposal", record.get("proposal_job_id"))):
        if not job_id:
            continue
        try:
            job = store.get(str(job_id), operator)
        except KeyError:
            states[key] = {"status": "MISSING"}
            continue
        states[key] = {"status": job.get("status"), "job_id": job_id, "error": job.get("error"),
                       "finished_at": job.get("finished_at")}
        if job.get("status") == "DONE":
            reports[key] = job.get("report")

    if record.get("status") == "FAILED" and not states:
        # Refused before its runs were submitted (a quota, a storage fault): the note says why.
        return {"evaluation_id": record["evaluation_id"], "draft_id": draft_id, "status": "FAILED",
                "runs": {}, "scope": scope, "as_of": record.get("as_of"), "evaluated_at": record.get("created_at"),
                "stale": False, "stale_reason": None, "comparison": None, "executable": False,
                "message": record.get("note")}
    status = "DONE" if len(reports) == 2 else (
        "FAILED" if any(s.get("status") in ("FAILED", "TIMEOUT", "CANCELLED", "ABANDONED", "MISSING") for s in states.values())
        else "RUNNING" if any(s.get("status") == "RUNNING" for s in states.values()) else "QUEUED")
    if status != record.get("status"):
        conn.execute("UPDATE zaad_evaluations SET status = ?, finished_at = ? WHERE evaluation_id = ? AND operator_id = ?",
                     [status, datetime.now(timezone.utc).replace(tzinfo=None) if status in ("DONE", "FAILED") else None,
                      record["evaluation_id"], operator])

    comparison = evaluation.compare(
        reports.get("baseline"), reports.get("proposal"), draft=draft, scope=scope,
        currency=str(draft.get("currency") or "USD"),
        notes=[record["note"]] if record.get("note") else None) if reports else None

    # An evaluation describes the lines as they were when it was submitted. A draft stays editable,
    # and an edit does not start a new revision — so without this the page would keep showing an
    # engine answer for an order that no longer exists on the screen above it. Decided by content
    # hash, not by timestamp: approving or exporting a proposal is not a change to what it says.
    stale, stale_reason = drafts.evaluation_freshness(conn, operator, draft, record)

    return {"evaluation_id": record["evaluation_id"], "draft_id": draft_id, "status": status,
            "runs": states, "scope": scope, "as_of": record.get("as_of"),
            "evaluated_at": record.get("created_at"), "stale": stale, "stale_reason": stale_reason,
            "draft_hash": record.get("draft_hash"), "workspace_version": record.get("workspace_version"),
            "comparison": comparison, "executable": False}


@router.get("/{draft_id}/amendment")
def amendment(draft_id: str, who: Who, conn=Depends(get_conn)):
    """For a proposed change to an existing order: what the engine's own commitment block says."""
    from api.routers.zaad_full import runner

    operator = who.operator_id
    try:
        draft = drafts.read_draft(conn, operator, draft_id)
    except KeyError as exc:
        raise HTTPException(404, "That proposal is not in this workspace.") from exc
    po_id = draft.get("source_po_id")
    if not po_id:
        raise HTTPException(422, {"code": "not_an_amendment",
                                  "message": "This proposal is a new order, not a change to an existing one."})
    report = None
    # The last *workspace* plan. Selecting the first DONE job of any kind read an evaluation's
    # overlay run — the workspace plus an order nobody placed — as "ZAAD's last plan".
    store = runner().store
    for job in store.list(operator, purpose="WORKSPACE_PLAN"):
        if job.get("status") != "DONE":
            continue
        report = store.get(job["id"], operator).get("report")
        break
    return {"draft_id": draft_id, "po_id": po_id,
            **evaluation.amendment_view(report, str(po_id), draft.get("amendment_action"))}
