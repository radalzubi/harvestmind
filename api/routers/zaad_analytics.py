"""Enterprise Analytics V1: the semantic model, the typed query API, saved analyses, dashboards,
exports, Ask ZAAD, signals and the optimizer hand-off.

Every endpoint is authenticated and tenant-scoped (`get_conn` is the caller's own vault, the actor
carries the role), every write checks an analytics capability, every query goes through the one
validator, and nothing here accepts SQL or an expression. Errors carry a code from the taxonomy.
"""
from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request as HTTPRequest
from fastapi.responses import Response

from api.analytics import exports, freshness, handoff as handoff_module, permissions, query as query_module, saved, semantic, signals
from api.analytics.ai import service as ask_service
from api.analytics.contracts import AnalyticsQuerySpec, AnalyticsRefused, AskIn, DashboardIn, HandoffIn, SavedAnalysisIn
from api.analytics.validate import allowed_dimensions_for, validate
from api.dependencies import get_conn, rate_limiter, require_actor, require_operator
from api.product.governance import Actor, Forbidden, need, record_audit

router = APIRouter(prefix="/api/zaad/analytics", tags=["zaad-analytics"], dependencies=[Depends(rate_limiter)])

MAX_BODY_BYTES = 256 * 1024


def authenticated(operator: str | None = Depends(require_operator)) -> str:
    if operator is None:
        raise HTTPException(401, "Open your workspace to read its data.")
    return operator


Operator = Annotated[str, Depends(authenticated)]
Who = Annotated[Actor | None, Depends(require_actor)]


def allowed(actor: Actor | None, capability: str) -> None:
    if actor is None:
        return
    try:
        need(actor, capability)
    except Forbidden as exc:
        raise HTTPException(403, {"code": "forbidden", "message": str(exc)}) from exc


def _refused(exc: AnalyticsRefused) -> HTTPException:
    status = {"permission_denied": 403, "query_timeout": 504, "engine_unavailable": 503, "dataset_unavailable": 503}.get(exc.code, 422)
    return HTTPException(status, exc.as_dict())


def _rid(request: HTTPRequest) -> str | None:
    return getattr(request.state, "request_id", None)


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
    except (ValueError, RecursionError) as exc:      # a document nested past the interpreter's limit is not valid input either
        raise HTTPException(400, "That request body is not valid JSON.") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(400, "A JSON object is expected.")
    return parsed


def _parse(model: Any, data: dict[str, Any]) -> Any:
    try:
        return model.model_validate(data)
    except Exception as exc:  # noqa: BLE001 - pydantic's message names the field
        raise HTTPException(422, {"code": "spec_invalid", "message": str(exc)[:600]}) from exc


# ── the semantic model ──

@router.get("/model")
def model(operator: Operator, who: Who, locale: str = Query("en")):
    """The whole governed model, machine-readable, filtered to what this role may read."""
    allowed(who, "viewAnalytics")
    doc = semantic.model_document(locale)
    classes = permissions.readable_classes(who)
    doc["metrics"] = [m for m in doc["metrics"] if m["security_classification"] in classes]
    doc["dimensions"] = [d for d in doc["dimensions"] if d["classification"] in classes]
    doc["permissions"] = permissions.describe(who)
    doc["capabilities"] = {c: permissions.check(who, c) for c in ("viewAnalytics", "createAnalysis", "editOwnAnalysis", "shareAnalysis", "exportAnalytics", "askZaad", "manageAnalytics")}
    return doc


@router.get("/metrics")
def metrics(operator: Operator, who: Who):
    allowed(who, "viewAnalytics")
    classes = permissions.readable_classes(who)
    return {"metrics": [m.as_dict() for m in semantic.METRICS.values() if m.security_classification in classes], "semantic_model_version": semantic.MODEL_VERSION}


@router.get("/metrics/{metric_id}")
def metric(metric_id: str, operator: Operator, who: Who):
    allowed(who, "viewAnalytics")
    try:
        m = semantic.metric(metric_id)
    except KeyError as exc:
        raise HTTPException(404, {"code": "semantic_unknown_metric", "message": f"{metric_id!r} is not a governed metric."}) from exc
    if not permissions.can_read(who, m.security_classification):
        raise HTTPException(403, {"code": "permission_denied", "message": "Your role may not read this measure."})
    return m.as_dict()


@router.get("/dimensions/{dimension_id}/members")
def members(dimension_id: str, operator: Operator, who: Who, conn=Depends(get_conn), q: str | None = Query(None, max_length=120), limit: int = Query(100, ge=1, le=200)):
    allowed(who, "viewAnalytics")
    try:
        return {"dimension_id": dimension_id, "members": query_module.members(conn, operator, who, dimension_id, search=q, limit=limit)}
    except AnalyticsRefused as exc:
        raise _refused(exc) from exc


@router.get("/allowed-dimensions")
def allowed_dimensions(operator: Operator, who: Who, metrics: str = Query(..., description="comma-separated metric ids")):
    allowed(who, "viewAnalytics")
    ids = [x.strip() for x in metrics.split(",") if x.strip()][:6]
    return {"metrics": ids, "dimensions": allowed_dimensions_for(ids)}


@router.get("/dataset-version")
def dataset_version(operator: Operator, who: Who, conn=Depends(get_conn), recorded: str | None = Query(None, max_length=40)):
    allowed(who, "viewAnalytics")
    out = freshness.current(conn, operator)
    if recorded:
        out["moved"] = freshness.moved_since(conn, operator, recorded)
    return out


# ── queries ──

@router.post("/query")
async def run_query(request: HTTPRequest, operator: Operator, who: Who, conn=Depends(get_conn)):
    """The only way a surface reads analytics: a typed spec in, a ResultSet out."""
    allowed(who, "viewAnalytics")
    spec = _parse(AnalyticsQuerySpec, await body_of(request))
    try:
        return query_module.run(conn, operator, who, spec, use_cache=request.headers.get("cache-control", "").lower() != "no-cache")
    except AnalyticsRefused as exc:
        raise _refused(exc) from exc


@router.post("/validate")
async def validate_query(request: HTTPRequest, operator: Operator, who: Who):
    """Validate without running: the builder asks before it draws."""
    allowed(who, "viewAnalytics")
    spec = _parse(AnalyticsQuerySpec, await body_of(request))
    try:
        v = validate(spec, who)
    except AnalyticsRefused as exc:
        return {"valid": False, **exc.as_dict()}
    from api.analytics.ai import recommend
    visual_type, why = recommend.recommend(v)
    return {"valid": True, **v.as_dict(), "recommended_visual": visual_type, "visual_reason": why,
            "allowed_dimensions": allowed_dimensions_for([m.metric_id for m in v.metrics])}


@router.post("/export")
async def export(request: HTTPRequest, operator: Operator, who: Who, conn=Depends(get_conn),
                 fmt: str = Query("csv", pattern="^(csv|xlsx)$"), name: str = Query("analysis", max_length=120), locale: str = Query("en", pattern="^(en|ar)$")):
    """The result of a spec as CSV or XLSX with its provenance. Exporting is not transmitting."""
    allowed(who, "exportAnalytics")
    spec = _parse(AnalyticsQuerySpec, await body_of(request))
    try:
        result = query_module.run(conn, operator, who, spec.model_copy(update={"purpose": "export"}))
    except AnalyticsRefused as exc:
        raise _refused(exc) from exc
    if fmt == "csv":
        payload, media = exports.to_csv(result, locale=locale), "text/csv; charset=utf-8"
    else:
        payload, media = exports.to_xlsx(result, locale=locale, title=name), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    try:
        record_audit(conn, who, operator=operator, object_type="analysis_export", object_id=result["query_id"], action="analytics_exported", request_id=_rid(request),
                     context={"format": fmt, "rows": result["bounds"]["rows"], "metrics": [d["ref"] for d in result["provenance"]["definitions"]], "dataset_version": result["dataset_version"]["dataset_version_id"]})
    except Exception:  # noqa: BLE001 - a vault without the audit table still exports
        pass
    return Response(content=payload, media_type=media, headers={"Content-Disposition": f'attachment; filename="{exports.filename(name, fmt)}"', "X-ZAAD-Transmitted": "false"})


# ── saved analyses ──

@router.get("/analyses")
def list_analyses(operator: Operator, who: Who, conn=Depends(get_conn), q: str | None = Query(None, max_length=120), origin: str | None = Query(None, pattern="^(user|ask_zaad|zaad_curated)$"),
                  limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    allowed(who, "viewAnalytics")
    return saved.list_analyses(conn, operator, who, q=q, origin=origin, limit=limit, offset=offset)


@router.post("/analyses", status_code=201)
async def create_analysis(request: HTTPRequest, operator: Operator, who: Who, conn=Depends(get_conn)):
    allowed(who, "createAnalysis")
    body = _parse(SavedAnalysisIn, await body_of(request))
    try:
        return saved.create_analysis(conn, operator, who, body, request_id=_rid(request))
    except (AnalyticsRefused, Forbidden) as exc:
        raise (_refused(exc) if isinstance(exc, AnalyticsRefused) else HTTPException(403, {"code": "forbidden", "message": str(exc)})) from exc


@router.get("/analyses/{analysis_id}")
def get_analysis(analysis_id: str, operator: Operator, who: Who, conn=Depends(get_conn)):
    allowed(who, "viewAnalytics")
    try:
        return saved.get_analysis(conn, operator, who, analysis_id)
    except saved.NotFound as exc:
        raise HTTPException(404, {"code": "not_found", "message": "That analysis is not in this workspace."}) from exc


@router.patch("/analyses/{analysis_id}")
async def update_analysis(analysis_id: str, request: HTTPRequest, operator: Operator, who: Who, conn=Depends(get_conn)):
    allowed(who, "editOwnAnalysis")
    changes = await body_of(request)
    try:
        return saved.update_analysis(conn, operator, who, analysis_id, changes, request_id=_rid(request))
    except saved.NotFound as exc:
        raise HTTPException(404, {"code": "not_found", "message": "That analysis is not in this workspace."}) from exc
    except AnalyticsRefused as exc:
        raise _refused(exc) from exc
    except Forbidden as exc:
        raise HTTPException(403, {"code": "forbidden", "message": str(exc)}) from exc


@router.delete("/analyses/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: str, request: HTTPRequest, operator: Operator, who: Who, conn=Depends(get_conn)):
    allowed(who, "editOwnAnalysis")
    try:
        saved.delete_analysis(conn, operator, who, analysis_id, request_id=_rid(request))
    except saved.NotFound as exc:
        raise HTTPException(404, {"code": "not_found", "message": "That analysis is not in this workspace."}) from exc
    except AnalyticsRefused as exc:
        raise _refused(exc) from exc
    return Response(status_code=204)


@router.post("/analyses/{analysis_id}/run")
def run_analysis(analysis_id: str, operator: Operator, who: Who, conn=Depends(get_conn)):
    """Run a saved analysis against the current data; says whether the data moved since it was saved."""
    allowed(who, "viewAnalytics")
    try:
        analysis = saved.get_analysis(conn, operator, who, analysis_id)
    except saved.NotFound as exc:
        raise HTTPException(404, {"code": "not_found", "message": "That analysis is not in this workspace."}) from exc
    if not analysis["compatibility"]["compatible"]:
        raise HTTPException(422, {"code": analysis["compatibility"]["codes"][0], "message": analysis["compatibility"].get("message", "This analysis no longer matches the semantic model.")})
    spec = AnalyticsQuerySpec.model_validate(analysis["visual"]["query"])
    try:
        result = query_module.run(conn, operator, who, spec)
    except AnalyticsRefused as exc:
        raise _refused(exc) from exc
    moved = freshness.moved_since(conn, operator, analysis.get("dataset_version_id"))
    return {"analysis": analysis, "result": result, "moved": moved}


# ── dashboards ──

@router.get("/dashboards")
def list_dashboards(operator: Operator, who: Who, conn=Depends(get_conn), limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    allowed(who, "viewAnalytics")
    return saved.list_dashboards(conn, operator, who, limit=limit, offset=offset)


@router.post("/dashboards", status_code=201)
async def create_dashboard(request: HTTPRequest, operator: Operator, who: Who, conn=Depends(get_conn)):
    allowed(who, "createAnalysis")
    body = _parse(DashboardIn, await body_of(request))
    try:
        return saved.create_dashboard(conn, operator, who, body, request_id=_rid(request))
    except AnalyticsRefused as exc:
        raise _refused(exc) from exc
    except Forbidden as exc:
        raise HTTPException(403, {"code": "forbidden", "message": str(exc)}) from exc


@router.get("/dashboards/{dashboard_id}")
def get_dashboard(dashboard_id: str, operator: Operator, who: Who, conn=Depends(get_conn)):
    allowed(who, "viewAnalytics")
    try:
        return saved.get_dashboard(conn, operator, who, dashboard_id)
    except saved.NotFound as exc:
        raise HTTPException(404, {"code": "not_found", "message": "That dashboard is not in this workspace."}) from exc


@router.patch("/dashboards/{dashboard_id}")
async def update_dashboard(dashboard_id: str, request: HTTPRequest, operator: Operator, who: Who, conn=Depends(get_conn)):
    allowed(who, "editOwnAnalysis")
    changes = await body_of(request)
    try:
        return saved.update_dashboard(conn, operator, who, dashboard_id, changes, request_id=_rid(request))
    except saved.NotFound as exc:
        raise HTTPException(404, {"code": "not_found", "message": "That dashboard is not in this workspace."}) from exc
    except AnalyticsRefused as exc:
        raise _refused(exc) from exc
    except Forbidden as exc:
        raise HTTPException(403, {"code": "forbidden", "message": str(exc)}) from exc


@router.post("/dashboards/{dashboard_id}/duplicate", status_code=201)
def duplicate_dashboard(dashboard_id: str, request: HTTPRequest, operator: Operator, who: Who, conn=Depends(get_conn)):
    allowed(who, "createAnalysis")
    try:
        return saved.duplicate_dashboard(conn, operator, who, dashboard_id, request_id=_rid(request))
    except saved.NotFound as exc:
        raise HTTPException(404, {"code": "not_found", "message": "That dashboard is not in this workspace."}) from exc


@router.delete("/dashboards/{dashboard_id}", status_code=204)
def delete_dashboard(dashboard_id: str, request: HTTPRequest, operator: Operator, who: Who, conn=Depends(get_conn)):
    allowed(who, "editOwnAnalysis")
    try:
        saved.delete_dashboard(conn, operator, who, dashboard_id, request_id=_rid(request))
    except saved.NotFound as exc:
        raise HTTPException(404, {"code": "not_found", "message": "That dashboard is not in this workspace."}) from exc
    except AnalyticsRefused as exc:
        raise _refused(exc) from exc
    return Response(status_code=204)


# ── Ask ZAAD ──

@router.post("/ask")
async def ask(request: HTTPRequest, operator: Operator, who: Who, conn=Depends(get_conn)):
    """A question in, a governed analysis out. The model proposes; the validator decides; the engine runs."""
    allowed(who, "askZaad")
    body = _parse(AskIn, await body_of(request))
    try:
        out = ask_service.ask(conn, operator, who, body)
    except AnalyticsRefused as exc:
        raise _refused(exc) from exc
    try:
        import hashlib
        record_audit(conn, who, operator=operator, object_type="ask_zaad", object_id=hashlib.sha256(body.question.encode()).hexdigest()[:16], action="ai_query",
                     request_id=_rid(request), context={"answered": out.get("answered"), "planner": out.get("planner"), "intent": out.get("intent"),
                                                        "spec_hash": (out.get("result") or {}).get("spec_hash"), "conversation": body.conversation_id,
                                                        "visual_type": (out.get("visual") or {}).get("visual_type")})
    except Exception:  # noqa: BLE001
        pass
    return out


@router.get("/ask/status")
def ask_status(operator: Operator, who: Who):
    from api.analytics.ai.provider import default_provider
    provider = default_provider()
    return {"model_available": provider is not None, "provider": provider.name if provider else None, "fallback": "rules"}


# ── signals ──

@router.get("/signals/supplier-deterioration")
def supplier_deterioration(operator: Operator, who: Who, conn=Depends(get_conn), months: int = Query(12, ge=4, le=36)):
    allowed(who, "viewAnalytics")
    try:
        return signals.supplier_deterioration(conn, operator, who, months=months)
    except AnalyticsRefused as exc:
        raise _refused(exc) from exc


@router.get("/signals/cover-exposure")
def cover_exposure(operator: Operator, who: Who, conn=Depends(get_conn)):
    allowed(who, "viewAnalytics")
    try:
        return signals.cover_exposure(conn, operator, who)
    except AnalyticsRefused as exc:
        raise _refused(exc) from exc


# ── the optimizer hand-off ──

@router.post("/handoff")
async def handoff(request: HTTPRequest, operator: Operator, who: Who, conn=Depends(get_conn)):
    """From an analysis to the canonical planner: a decision context, the request it builds, and —
    only when asked by someone who may evaluate — a job on the ordered lease."""
    allowed(who, "askZaad")
    body = _parse(HandoffIn, await body_of(request))
    if body.submit:
        allowed(who, "evaluate")
    try:
        return handoff_module.handoff(conn, operator, who, body, request_id=_rid(request))
    except AnalyticsRefused as exc:
        raise _refused(exc) from exc
    except Forbidden as exc:
        raise HTTPException(403, {"code": "forbidden", "message": str(exc)}) from exc
