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

from api.dependencies import get_conn, rate_limiter, require_operator
from api.product import drafts, evaluation, exporting
from api.product.catalog import _one, _rows, has_table
from api.routers.zaad import bounded_rate

router = APIRouter(prefix="/api/zaad/orders", tags=["zaad-orders"],
                   dependencies=[Depends(rate_limiter)])

MAX_BODY_BYTES = 1 * 1024 * 1024
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


def authenticated(operator: str | None = Depends(require_operator)) -> str:
    if operator is None:
        raise HTTPException(401, "Open your workspace to work with proposed orders.")
    return operator


Operator = Annotated[str, Depends(authenticated)]


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
    operator: Operator, conn=Depends(get_conn), state: str | None = None, origin: str | None = None,
    supplier_id: str | None = None, source_po_id: str | None = None, q: str | None = None,
    sort: str = "updated_at", direction: Literal["asc", "desc"] = "desc",
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
):
    try:
        return drafts.list_drafts(conn, operator, state=state, origin=origin, supplier_id=supplier_id,
                                  source_po_id=source_po_id, search=q, sort=sort, direction=direction,
                                  limit=limit, offset=offset)
    except drafts.DraftRefused as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("", status_code=201)
async def create_order(request: HTTPRequest, operator: Operator, conn=Depends(get_conn)):
    """Create a proposal. Every origin — recommendation, current policy, manual, upload, amendment."""
    body = await body_of(request)
    try:
        identity = drafts.create_draft(conn, operator, body, actor=operator)
    except drafts.DraftRefused as exc:
        raise _refused(exc) from exc
    return {**drafts.read_draft(conn, operator, identity), "executable": False, "transmitted": False}


@router.get("/profiles")
def profiles(operator: Operator, conn=Depends(get_conn)):
    """The workspace's own output formats, plus the built-in one it starts with."""
    return {"profiles": [exporting.default_profile(), *drafts.list_profiles(conn, operator)],
            "fields": exporting.EXPORT_FIELDS, "formats": list(exporting.FORMATS),
            "import_fields": exporting.IMPORT_FIELDS}


@router.post("/profiles", status_code=201)
async def create_profile(request: HTTPRequest, operator: Operator, conn=Depends(get_conn)):
    body = await body_of(request)
    try:
        identity = drafts.save_profile(conn, operator, body)
    except drafts.DraftRefused as exc:
        raise _refused(exc) from exc
    return {"profile_id": identity}


@router.put("/profiles/{profile_id}")
async def update_profile(profile_id: str, request: HTTPRequest, operator: Operator, conn=Depends(get_conn)):
    body = await body_of(request)
    try:
        drafts.save_profile(conn, operator, body, profile_id=profile_id)
    except drafts.DraftRefused as exc:
        raise _refused(exc) from exc
    return {"profile_id": profile_id}


@router.delete("/profiles/{profile_id}", status_code=204)
def remove_profile(profile_id: str, operator: Operator, conn=Depends(get_conn)):
    try:
        drafts.delete_profile(conn, operator, profile_id)
    except KeyError as exc:
        raise HTTPException(404, "That format is not in this workspace.") from exc
    return Response(status_code=204)


@router.post("/profiles/read-template")
async def read_template(operator: Operator, file: UploadFile = File(...)):
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
    operator: Operator,
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
def evaluation_jobs(operator: Operator, conn=Depends(get_conn)):
    """Job ids that belong to a proposal evaluation rather than to the workspace's own plan.

    An evaluation runs the released jobs path twice, and one of those runs carries a proposed order
    overlaid on the pipeline. Nothing in the job record distinguishes it from a plan, so a surface
    that shows "the last completed plan" would otherwise show a plan of a workspace *plus an order
    nobody has placed* and present it as the operator's position. This is the list to exclude.
    """
    drafts.ensure_tables(conn)
    rows = _rows(conn, "SELECT baseline_job_id, proposal_job_id FROM zaad_evaluations WHERE operator_id = ?",
                 [operator])
    identities = sorted({str(value) for row in rows for value in row.values() if value})
    return {"evaluation_job_ids": identities}


@router.get("/{draft_id}")
def read_order(draft_id: str, operator: Operator, conn=Depends(get_conn)):
    try:
        return drafts.read_draft(conn, operator, draft_id)
    except KeyError as exc:
        raise HTTPException(404, "That proposal is not in this workspace.") from exc


@router.patch("/{draft_id}")
async def edit_order(draft_id: str, request: HTTPRequest, operator: Operator, conn=Depends(get_conn)):
    body = await body_of(request)
    try:
        return drafts.update_draft(conn, operator, draft_id, body, actor=operator)
    except KeyError as exc:
        raise HTTPException(404, "That proposal is not in this workspace.") from exc
    except drafts.DraftRefused as exc:
        raise _refused(exc) from exc


@router.delete("/{draft_id}", status_code=204)
def remove_order(draft_id: str, operator: Operator, conn=Depends(get_conn)):
    try:
        drafts.delete_draft(conn, operator, draft_id, actor=operator)
    except KeyError as exc:
        raise HTTPException(404, "That proposal is not in this workspace.") from exc
    except drafts.DraftRefused as exc:
        raise _refused(exc) from exc
    return Response(status_code=204)


@router.post("/{draft_id}/actions/{action}")
async def act(draft_id: str, action: Literal["submit", "reopen", "approve", "reject"],
              request: HTTPRequest, operator: Operator, conn=Depends(get_conn)):
    body = await body_of(request)
    try:
        return drafts.transition(conn, operator, draft_id, action, actor=operator,
                                 reason=body.get("reason"))
    except KeyError as exc:
        raise HTTPException(404, "That proposal is not in this workspace.") from exc
    except drafts.DraftRefused as exc:
        raise _refused(exc) from exc


@router.post("/{draft_id}/revise", status_code=201)
def revise_order(draft_id: str, operator: Operator, conn=Depends(get_conn)):
    """The next revision of a proposal that is already part of the record."""
    try:
        identity = drafts.revise(conn, operator, draft_id, actor=operator)
    except KeyError as exc:
        raise HTTPException(404, "That proposal is not in this workspace.") from exc
    except drafts.DraftRefused as exc:
        raise _refused(exc) from exc
    return drafts.read_draft(conn, operator, identity)


# ── export ────────────────────────────────────────────────────────────────────

def _profile_for(conn: Any, operator: str, profile_id: str | None) -> dict[str, Any]:
    if not profile_id:
        return exporting.default_profile()
    for profile in drafts.list_profiles(conn, operator):
        if profile["profile_id"] == profile_id:
            return profile
    raise HTTPException(404, "That output format is not in this workspace.")


@router.post("/{draft_id}/export")
def export_order(draft_id: str, operator: Operator, conn=Depends(get_conn),
                 profile_id: str | None = Query(None),
                 fmt: Literal["csv", "xlsx", "print"] | None = Query(None, alias="format")):
    """Produce the file. **This does not send anything to a supplier or an ERP.**"""
    try:
        draft = drafts.read_draft(conn, operator, draft_id)
    except KeyError as exc:
        raise HTTPException(404, "That proposal is not in this workspace.") from exc
    if not draft.get("lines"):
        raise HTTPException(422, {"code": "proposal_refused", "message": "This proposal has no lines to export."})
    profile = dict(_profile_for(conn, operator, profile_id))
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
                                   WHERE sku IN ({', '.join('?' for _ in draft['lines'])}) GROUP BY sku""",
                         [str(line["sku"]) for line in draft["lines"]]):
            if row.get("n"):
                descriptions[str(row["sku"])] = str(row["n"])
    for line in draft["lines"]:
        line["sku_name"] = descriptions.get(str(line["sku"]), "")

    try:
        payload, media, filename = exporting.render(draft, profile, supplier_names=names, workspace=operator)
    except exporting.ExportRefused as exc:
        raise HTTPException(422, str(exc)) from exc
    drafts.record_export(conn, operator, draft_id, revision=draft.get("revision"),
                         profile_id=profile.get("profile_id"), profile_name=str(profile.get("name")),
                         fmt=str(profile.get("format")), filename=filename, actor=operator)
    return Response(payload, media_type=media, headers={
        "Content-Disposition": f'attachment; filename="{filename}"',
        "X-ZAAD-Transmitted": "false",
    })


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
async def evaluate(draft_id: str, operator: Operator, conn=Depends(get_conn),
                   horizon: int = Query(12, ge=4, le=26),
                   service_target: float = Query(.95, gt=.5, le=1.),
                   max_solve_seconds: float = Query(15., gt=0, le=120)):
    """Run the workspace twice — without this proposal and with it — on the released jobs path.

    Both runs share an as-of, a seed and a set of products, so the difference between them is the
    proposal. Each evaluation uses two of the workspace's daily job allowance.
    """
    from zaad.full.jobs import QuotaExceeded
    from api.routers.zaad_full import _workspace_request, runner

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
    try:
        baseline_job = run.submit(operator, request)
        proposal_job = run.submit(operator, overlaid)
    except QuotaExceeded as exc:
        raise HTTPException(429, {"code": "job_quota", "message":
                                  f"{exc} An evaluation runs the engine twice, so it needs two."}) from exc

    identity = evaluation.store_evaluation(
        conn, operator, draft_id=draft_id, revision=draft.get("revision"),
        baseline_job_id=baseline_job, proposal_job_id=proposal_job,
        as_of=request.as_of.isoformat(), scope=scope, status="QUEUED",
        note="; ".join(notes) if notes else None)
    return {"evaluation_id": identity, "status": "QUEUED", "baseline_job_id": baseline_job,
            "proposal_job_id": proposal_job, "scope": scope, "commitments_included": commitments,
            "notes": notes, "executable": False}


@router.get("/{draft_id}/evaluation")
def read_evaluation(draft_id: str, operator: Operator, conn=Depends(get_conn),
                    evaluation_id: str | None = Query(None)):
    """The state of an evaluation, and the comparison once both runs have finished."""
    from api.routers.zaad_full import runner

    drafts.ensure_tables(conn)
    try:
        draft = drafts.read_draft(conn, operator, draft_id)
    except KeyError as exc:
        raise HTTPException(404, "That proposal is not in this workspace.") from exc
    rows = _rows(conn, "SELECT * FROM zaad_evaluations WHERE draft_id = ? AND operator_id = ? "
                       + ("AND evaluation_id = ? " if evaluation_id else "")
                       + "ORDER BY created_at DESC LIMIT 1",
                 [draft_id, operator, *([evaluation_id] if evaluation_id else [])])
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

    status = "DONE" if len(reports) == 2 else (
        "FAILED" if any(s.get("status") in ("FAILED", "TIMEOUT", "CANCELLED", "MISSING") for s in states.values())
        else "RUNNING" if any(s.get("status") == "RUNNING" for s in states.values()) else "QUEUED")
    if status != record.get("status"):
        conn.execute("UPDATE zaad_evaluations SET status = ?, finished_at = ? WHERE evaluation_id = ? AND operator_id = ?",
                     [status, datetime.now(timezone.utc).replace(tzinfo=None) if status in ("DONE", "FAILED") else None,
                      record["evaluation_id"], operator])

    comparison = evaluation.compare(
        reports.get("baseline"), reports.get("proposal"), draft=draft, scope=scope,
        currency=str(draft.get("currency") or "USD"),
        notes=[record["note"]] if record.get("note") else None) if reports else None
    return {"evaluation_id": record["evaluation_id"], "draft_id": draft_id, "status": status,
            "runs": states, "scope": scope, "as_of": record.get("as_of"),
            "comparison": comparison, "executable": False}


@router.get("/{draft_id}/amendment")
def amendment(draft_id: str, operator: Operator, conn=Depends(get_conn)):
    """For a proposed change to an existing order: what the engine's own commitment block says."""
    from api.routers.zaad_full import runner

    try:
        draft = drafts.read_draft(conn, operator, draft_id)
    except KeyError as exc:
        raise HTTPException(404, "That proposal is not in this workspace.") from exc
    po_id = draft.get("source_po_id")
    if not po_id:
        raise HTTPException(422, {"code": "not_an_amendment",
                                  "message": "This proposal is a new order, not a change to an existing one."})
    report = None
    for job in runner().store.list(operator):
        if job.get("status") != "DONE":
            continue
        detail = runner().store.get(job["id"], operator)
        report = detail.get("report")
        break
    return {"draft_id": draft_id, "po_id": po_id, **evaluation.amendment_view(report, str(po_id))}
