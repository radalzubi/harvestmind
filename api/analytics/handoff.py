"""Analytics → optimizer hand-off: a decision context, then the canonical planning path.

"Ask ZAAD what should change" never lets the AI manufacture a recommendation. What travels is a
`DecisionContext` — the products, suppliers and sites an analysis named, the window it looked at,
the observed issue in the requester's words — and the hand-off builds the canonical `Request`
through the existing workspace adapter with the existing defaults, scoped to those products, and
(when asked, by a person with the capability) submits it on the existing jobs path. No parameter
is set by the analysis; no recommendation exists until the plan finishes; nothing is executed.
"""
from __future__ import annotations

import os
from typing import Any

from api.analytics.contracts import AnalyticsRefused, HandoffIn
from api.analytics.validate import validate
from api.product.governance import Actor, record_audit

MAX_SKUS = 50


def decision_context(conn: Any, operator: str, actor: Actor | None, body: HandoffIn) -> dict[str, Any]:
    validated = validate(body.query, actor)
    skus = list(dict.fromkeys(body.skus))
    suppliers = list(dict.fromkeys(body.suppliers))
    locations = list(dict.fromkeys(body.locations))
    for f in validated.filters:
        if f.dimension.id == "sku":
            skus += [v for v in f.values if v not in skus]
        elif f.dimension.id == "supplier":
            suppliers += [v for v in f.values if v not in suppliers]
        elif f.dimension.id == "location":
            locations += [v for v in f.values if v not in locations]
    # a supplier context without named products resolves to the products the master assigns to it
    if suppliers and not skus:
        from api.product.catalog import _rows, has_table
        if has_table(conn, "stg_fmcg_skus"):
            placeholders = ", ".join("?" for _ in suppliers)
            rows = _rows(conn, f"SELECT DISTINCT sku FROM stg_fmcg_skus WHERE supplier_id IN ({placeholders}) ORDER BY sku LIMIT {MAX_SKUS}", suppliers)  # noqa: S608  # nosec B608 - placeholders; values bind
            skus = [str(r["sku"]) for r in rows]
    skus = skus[:MAX_SKUS]
    time = {"grain": validated.grain, "start": (body.query.time.range.start if body.query.time and body.query.time.range else None),
            "end": (body.query.time.range.end if body.query.time and body.query.time.range else None),
            "last": (body.query.time.range.last if body.query.time and body.query.time.range else None),
            "unit": (body.query.time.range.unit if body.query.time and body.query.time.range else None)}
    return {"skus": skus, "suppliers": suppliers, "locations": locations, "time_window": time, "observed_issue": body.observed_issue[:600],
            "metrics": [m.ref for m in validated.metrics], "fact": validated.fact.id, "spec_hash": body.query.spec_hash(),
            "note": "A context for the canonical planner. It sets no parameter and carries no recommendation; the plan decides."}


def handoff(conn: Any, operator: str, actor: Actor | None, body: HandoffIn, *, request_id: str | None = None) -> dict[str, Any]:
    from api.analytics import permissions
    context = decision_context(conn, operator, actor, body)
    if not context["skus"]:
        raise AnalyticsRefused("spec_invalid", "The analysis names no product to plan for. Filter or break down by product or supplier first.")
    permissions.require(actor, "askZaad")
    if body.submit:
        permissions.require(actor, "evaluate") if actor is not None else None
    from api.routers.zaad_full import _workspace_request
    from fastapi import HTTPException
    network = _has_network(conn)
    notes: list[str] = []
    commitments = _has_scoped_rows(conn, "stg_po_commitments", operator)
    try:
        try:
            req, build = _workspace_request(conn, operator, 12, 0.95, ",".join(context["skus"]), 15.0, network=network,
                                            sourcing=_has_rows(conn, "stg_fmcg_sources"), commitments=commitments)
        except HTTPException as exc:
            detail: dict[str, Any] = exc.detail if isinstance(exc.detail, dict) else {}
            if commitments and detail.get("code") == "commitments_invalid":
                # the context leaves out orders that carry declared amendment terms; the plan runs
                # without the P4B block rather than pretending those orders are in scope
                notes.append("Open-order amendment terms were not attached: the context excludes orders that carry them. "
                             "Widen the product selection on Decisions to plan them.")
                req, build = _workspace_request(conn, operator, 12, 0.95, ",".join(context["skus"]), 15.0, network=network,
                                                sourcing=_has_rows(conn, "stg_fmcg_sources"), commitments=False)
            else:
                raise
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {"code": "workspace_not_ready", "message": str(exc.detail)}
        return {"context": context, "request_built": False, "refusal": detail, "job": None, "notes": notes}
    out: dict[str, Any] = {"context": context, "request_built": True, "request_summary": {"skus": len(req.skus), "sources": len(req.sources), "pipeline": len(req.pipeline),
                                                                                             "locations": len(req.locations), "horizon": req.horizon, "as_of": str(req.as_of),
                                                                                             "commitments_attached": bool(req.commitments) if hasattr(req, "commitments") else None},
                           "build_warnings": (build or {}).get("warnings", [])[:8], "notes": notes, "job": None}
    if body.submit:
        from api.routers import zaad_full
        runner = zaad_full.runner()
        try:
            job_id = runner.submit(operator, req, purpose="WORKSPACE_PLAN", reference=f"analytics:{context['spec_hash']}")
        except Exception as exc:  # noqa: BLE001 - quota, lease or store errors are reported, never hidden
            out["job"] = {"submitted": False, "error": type(exc).__name__, "message": str(exc)[:300]}
        else:
            out["job"] = {"submitted": True, "job_id": job_id, "poll": f"/api/zaad/network/jobs/{job_id}"}
            try:
                record_audit(conn, actor, operator=operator, object_type="decision_context", object_id=context["spec_hash"], action="analytics_handoff",
                             request_id=request_id, context={"job_id": job_id, "skus": len(context["skus"]), "suppliers": context["suppliers"][:5]})
            except Exception:  # noqa: BLE001
                pass
    return out


def _has_network(conn: Any) -> bool:
    from api.product.catalog import _one, has_table
    return bool(has_table(conn, "stg_fmcg_locations") and (_one(conn, "SELECT count(*) FROM stg_fmcg_locations") or 0) > 1)


def _has_rows(conn: Any, table: str) -> bool:
    from api.product.catalog import _one, has_table
    return bool(has_table(conn, table) and _one(conn, f"SELECT count(*) FROM {table}"))  # noqa: S608  # nosec B608 - literal


def _has_scoped_rows(conn: Any, table: str, operator: str) -> bool:
    from api.product.catalog import _one, has_table
    return bool(has_table(conn, table) and _one(conn, f"SELECT count(*) FROM {table} WHERE operator_id = ?", [operator]))  # noqa: S608  # nosec B608 - literal


def job_store_configured() -> bool:
    return bool(os.getenv("ZAAD_JOB_STORE"))
