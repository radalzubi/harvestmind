"""Saved analyses and dashboards: validated on save, validated on open, owned, audited, tenant-scoped.

A saved object stores a `VisualSpec` (which carries its `AnalyticsQuerySpec`) or a `DashboardSpec`
as JSON the server produced from a validated model — never raw frontend state. Opening one runs
the validator again against the current semantic model, so a definition that has moved since is
reported (`compatible: false`, with the codes) rather than silently re-interpreted.

Visibility is `private` (the owner) or `workspace` (everyone in the tenant). There are no public
links. Deleting hides (`deleted_at`); nothing is hard-deleted while a dashboard may reference it,
and the audit log records every create, update, share, delete and export with identifiers only.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from api.analytics import freshness, permissions
from api.analytics.contracts import AnalyticsRefused, DashboardIn, DashboardSpec, SavedAnalysisIn, VisualSpec
from api.analytics.semantic import MODEL_VERSION
from api.analytics.validate import validate
from api.product.catalog import _one, _rows
from api.product.governance import Actor, record_audit

MAX_LIST = 200


class NotFound(KeyError):
    """Another tenant's object and a missing one are the same thing here."""


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def ensure_tables(conn: Any) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS zaad_analytics_analyses (analysis_id VARCHAR NOT NULL, operator_id VARCHAR NOT NULL, name VARCHAR NOT NULL, "
                 "description VARCHAR, owner VARCHAR NOT NULL, visibility VARCHAR NOT NULL, origin VARCHAR NOT NULL, visual_json VARCHAR NOT NULL, "
                 "semantic_model_version VARCHAR NOT NULL, dataset_version_id VARCHAR, notes VARCHAR, version INTEGER NOT NULL DEFAULT 1, "
                 "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, deleted_at TIMESTAMP)")
    conn.execute("CREATE TABLE IF NOT EXISTS zaad_analytics_dashboards (dashboard_id VARCHAR NOT NULL, operator_id VARCHAR NOT NULL, name VARCHAR NOT NULL, "
                 "description VARCHAR, owner VARCHAR NOT NULL, visibility VARCHAR NOT NULL, spec_json VARCHAR NOT NULL, semantic_model_version VARCHAR NOT NULL, "
                 "version INTEGER NOT NULL DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, deleted_at TIMESTAMP)")
    freshness.ensure_table(conn)


def _actor_id(actor: Actor | None, operator: str) -> str:
    return actor.actor_id if actor else operator


def _is_admin(actor: Actor | None) -> bool:
    return actor is None or permissions.check(actor, "manageAnalytics")


def _visible(actor: Actor | None, operator: str) -> tuple[str, list[Any]]:
    """The rows this person may see: their own, and the workspace's shared ones."""
    if _is_admin(actor):
        return "", []
    return " AND (visibility = 'workspace' OR owner = ?)", [_actor_id(actor, operator)]


def _may_edit(row: dict[str, Any], actor: Actor | None, operator: str) -> None:
    if _is_admin(actor):
        return
    if row["owner"] != _actor_id(actor, operator):
        raise AnalyticsRefused("permission_denied", "Only the owner (or a workspace administrator) can change this.")
    permissions.require(actor, "editOwnAnalysis")


def _check_visual(visual: VisualSpec, actor: Actor | None) -> dict[str, Any]:
    """Validate the visual's query against the current model; report rather than raise."""
    try:
        validated = validate(visual.query, actor)
        return {"compatible": True, "fact": validated.fact.id, "metrics": [m.ref for m in validated.metrics], "codes": []}
    except AnalyticsRefused as exc:
        return {"compatible": False, "codes": [exc.code], "message": str(exc)}


# ── analyses ──

def _analysis_row(row: dict[str, Any], actor: Actor | None) -> dict[str, Any]:
    visual = VisualSpec.model_validate(json.loads(row["visual_json"]))
    return {"analysis_id": row["analysis_id"], "name": row["name"], "description": row["description"], "owner": row["owner"],
            "visibility": row["visibility"], "origin": row["origin"], "visual": visual.model_dump(mode="json"),
            "semantic_model_version": row["semantic_model_version"], "dataset_version_id": row.get("dataset_version_id"), "notes": row.get("notes"),
            "version": row["version"], "created_at": _iso(row["created_at"]), "updated_at": _iso(row["updated_at"]),
            "compatibility": _check_visual(visual, actor)}


def _iso(value: Any) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else (str(value) if value is not None else None)


def list_analyses(conn: Any, operator: str, actor: Actor | None, *, q: str | None = None, origin: str | None = None, limit: int = 50, offset: int = 0) -> dict[str, Any]:
    ensure_tables(conn)
    vis, vp = _visible(actor, operator)
    where, params = "operator_id = ? AND deleted_at IS NULL" + vis, [operator, *vp]
    if q:
        from api.product import queries
        where += f" AND (name ILIKE ? ESCAPE '{queries.LIKE_ESCAPE}' OR coalesce(description, '') ILIKE ? ESCAPE '{queries.LIKE_ESCAPE}')"
        params += [queries.like_contains(q), queries.like_contains(q)]
    if origin:
        where += " AND origin = ?"
        params.append(origin)
    limit = max(1, min(int(limit), MAX_LIST))
    rows = _rows(conn, f"SELECT * FROM zaad_analytics_analyses WHERE {where} ORDER BY updated_at DESC LIMIT ? OFFSET ?", [*params, limit, max(0, int(offset))])  # noqa: S608  # nosec B608 - literals; values bind
    total = int(_one(conn, f"SELECT count(*) FROM zaad_analytics_analyses WHERE {where}", params) or 0)  # noqa: S608  # nosec B608
    return {"rows": [_analysis_row(r, actor) for r in rows], "total": total, "limit": limit, "offset": int(offset)}


def get_analysis(conn: Any, operator: str, actor: Actor | None, analysis_id: str) -> dict[str, Any]:
    ensure_tables(conn)
    vis, vp = _visible(actor, operator)
    rows = _rows(conn, f"SELECT * FROM zaad_analytics_analyses WHERE operator_id = ? AND analysis_id = ? AND deleted_at IS NULL{vis} LIMIT 1", [operator, analysis_id, *vp])  # noqa: S608  # nosec B608
    if not rows:
        raise NotFound(analysis_id)
    return _analysis_row(rows[0], actor)


def create_analysis(conn: Any, operator: str, actor: Actor | None, body: SavedAnalysisIn, *, request_id: str | None = None) -> dict[str, Any]:
    ensure_tables(conn)
    permissions.require(actor, "createAnalysis")
    if body.visibility == "workspace":
        permissions.require(actor, "shareAnalysis")
    validated = validate(body.visual.query, actor)      # refuses before anything is stored
    visual = body.visual.model_copy(update={"semantic_model_version": MODEL_VERSION, "visual_id": body.visual.visual_id or f"v_{uuid.uuid4().hex[:10]}"})
    identity = f"an_{uuid.uuid4().hex[:12]}"
    version = freshness.current(conn, operator)
    now = _now()
    conn.execute("INSERT INTO zaad_analytics_analyses (analysis_id, operator_id, name, description, owner, visibility, origin, visual_json, semantic_model_version, "
                 "dataset_version_id, notes, version, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
                 [identity, operator, body.name, body.description, _actor_id(actor, operator), body.visibility, body.origin, json.dumps(visual.model_dump(mode="json")),
                  MODEL_VERSION, version["dataset_version_id"], body.notes, now, now])
    record_audit(conn, actor, operator=operator, object_type="analysis", object_id=identity, action="analysis_created", after_revision=1, after_state=body.visibility,
                 request_id=request_id, context={"origin": body.origin, "fact": validated.fact.id, "metrics": [m.ref for m in validated.metrics], "visual_type": visual.visual_type})
    return get_analysis(conn, operator, actor, identity)


def update_analysis(conn: Any, operator: str, actor: Actor | None, analysis_id: str, changes: dict[str, Any], *, request_id: str | None = None) -> dict[str, Any]:
    ensure_tables(conn)
    vis, vp = _visible(actor, operator)
    rows = _rows(conn, f"SELECT * FROM zaad_analytics_analyses WHERE operator_id = ? AND analysis_id = ? AND deleted_at IS NULL{vis} LIMIT 1", [operator, analysis_id, *vp])  # noqa: S608  # nosec B608
    if not rows:
        raise NotFound(analysis_id)
    row = rows[0]
    _may_edit(row, actor, operator)
    allowed = {"name", "description", "visual", "visibility", "notes"}
    unknown = set(changes) - allowed
    if unknown:
        raise AnalyticsRefused("spec_invalid", f"Cannot change {', '.join(sorted(unknown))}.")
    name = str(changes.get("name", row["name"]))[:160]
    description = changes.get("description", row["description"])
    visibility = str(changes.get("visibility", row["visibility"]))
    if visibility not in ("private", "workspace"):
        raise AnalyticsRefused("spec_invalid", "visibility is private or workspace.")
    if visibility == "workspace" and row["visibility"] != "workspace":
        permissions.require(actor, "shareAnalysis")
    visual_json = row["visual_json"]
    context: dict[str, Any] = {}
    if "visual" in changes:
        visual = VisualSpec.model_validate(changes["visual"])
        validated = validate(visual.query, actor)
        visual = visual.model_copy(update={"semantic_model_version": MODEL_VERSION, "visual_id": visual.visual_id or f"v_{uuid.uuid4().hex[:10]}"})
        visual_json = json.dumps(visual.model_dump(mode="json"))
        context = {"fact": validated.fact.id, "metrics": [m.ref for m in validated.metrics], "visual_type": visual.visual_type}
    conn.execute("UPDATE zaad_analytics_analyses SET name = ?, description = ?, visibility = ?, visual_json = ?, notes = ?, semantic_model_version = ?, "
                 "version = version + 1, updated_at = ? WHERE operator_id = ? AND analysis_id = ?",
                 [name, description, visibility, visual_json, changes.get("notes", row.get("notes")), MODEL_VERSION, _now(), operator, analysis_id])
    action = "analysis_shared" if visibility != row["visibility"] else "analysis_updated"
    record_audit(conn, actor, operator=operator, object_type="analysis", object_id=analysis_id, action=action, before_revision=int(row["version"]),
                 after_revision=int(row["version"]) + 1, before_state=row["visibility"], after_state=visibility, request_id=request_id, context=context or None)
    return get_analysis(conn, operator, actor, analysis_id)


def delete_analysis(conn: Any, operator: str, actor: Actor | None, analysis_id: str, *, request_id: str | None = None) -> None:
    ensure_tables(conn)
    vis, vp = _visible(actor, operator)
    rows = _rows(conn, f"SELECT * FROM zaad_analytics_analyses WHERE operator_id = ? AND analysis_id = ? AND deleted_at IS NULL{vis} LIMIT 1", [operator, analysis_id, *vp])  # noqa: S608  # nosec B608
    if not rows:
        raise NotFound(analysis_id)
    _may_edit(rows[0], actor, operator)
    conn.execute("UPDATE zaad_analytics_analyses SET deleted_at = ?, updated_at = ? WHERE operator_id = ? AND analysis_id = ?", [_now(), _now(), operator, analysis_id])
    record_audit(conn, actor, operator=operator, object_type="analysis", object_id=analysis_id, action="analysis_deleted", before_revision=int(rows[0]["version"]),
                 before_state=rows[0]["visibility"], request_id=request_id)


# ── dashboards ──

def _dashboard_row(conn: Any, row: dict[str, Any], actor: Actor | None, operator: str, *, with_analyses: bool) -> dict[str, Any]:
    spec = DashboardSpec.model_validate(json.loads(row["spec_json"]))
    out = {"dashboard_id": row["dashboard_id"], "name": row["name"], "description": row["description"], "owner": row["owner"], "visibility": row["visibility"],
           "spec": spec.model_dump(mode="json"), "semantic_model_version": row["semantic_model_version"], "version": row["version"],
           "created_at": _iso(row["created_at"]), "updated_at": _iso(row["updated_at"]), "tiles": len(spec.tiles)}
    if with_analyses:
        analyses: dict[str, Any] = {}
        missing: list[str] = []
        for tile in spec.tiles:
            try:
                analyses[tile.analysis_id] = get_analysis(conn, operator, actor, tile.analysis_id)
            except NotFound:
                missing.append(tile.analysis_id)
        out["analyses"] = analyses
        out["missing"] = missing
    return out


def list_dashboards(conn: Any, operator: str, actor: Actor | None, *, limit: int = 50, offset: int = 0) -> dict[str, Any]:
    ensure_tables(conn)
    vis, vp = _visible(actor, operator)
    where, params = "operator_id = ? AND deleted_at IS NULL" + vis, [operator, *vp]
    limit = max(1, min(int(limit), MAX_LIST))
    rows = _rows(conn, f"SELECT * FROM zaad_analytics_dashboards WHERE {where} ORDER BY updated_at DESC LIMIT ? OFFSET ?", [*params, limit, max(0, int(offset))])  # noqa: S608  # nosec B608
    total = int(_one(conn, f"SELECT count(*) FROM zaad_analytics_dashboards WHERE {where}", params) or 0)  # noqa: S608  # nosec B608
    return {"rows": [_dashboard_row(conn, r, actor, operator, with_analyses=False) for r in rows], "total": total, "limit": limit, "offset": int(offset)}


def get_dashboard(conn: Any, operator: str, actor: Actor | None, dashboard_id: str) -> dict[str, Any]:
    ensure_tables(conn)
    vis, vp = _visible(actor, operator)
    rows = _rows(conn, f"SELECT * FROM zaad_analytics_dashboards WHERE operator_id = ? AND dashboard_id = ? AND deleted_at IS NULL{vis} LIMIT 1", [operator, dashboard_id, *vp])  # noqa: S608  # nosec B608
    if not rows:
        raise NotFound(dashboard_id)
    return _dashboard_row(conn, rows[0], actor, operator, with_analyses=True)


def _check_tiles(conn: Any, operator: str, actor: Actor | None, spec: DashboardSpec) -> None:
    for tile in spec.tiles:
        try:
            get_analysis(conn, operator, actor, tile.analysis_id)
        except NotFound as exc:
            raise AnalyticsRefused("spec_invalid", f"Tile {tile.tile_id} references an analysis that is not in this workspace.", {"analysis_id": tile.analysis_id}) from exc
    for f in spec.shared_filters:
        from api.analytics import semantic
        try:
            semantic.dimension(f.dimension_id)
        except KeyError as exc:
            raise AnalyticsRefused("semantic_unknown_dimension", f"{f.dimension_id!r} is not a governed dimension.") from exc


def create_dashboard(conn: Any, operator: str, actor: Actor | None, body: DashboardIn, *, request_id: str | None = None) -> dict[str, Any]:
    ensure_tables(conn)
    permissions.require(actor, "createAnalysis")
    if body.visibility == "workspace":
        permissions.require(actor, "shareAnalysis")
    _check_tiles(conn, operator, actor, body.spec)
    identity = f"db_{uuid.uuid4().hex[:12]}"
    now = _now()
    spec = body.spec.model_copy(update={"semantic_model_version": MODEL_VERSION})
    conn.execute("INSERT INTO zaad_analytics_dashboards (dashboard_id, operator_id, name, description, owner, visibility, spec_json, semantic_model_version, version, created_at, updated_at) "
                 "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
                 [identity, operator, body.name, body.description, _actor_id(actor, operator), body.visibility, json.dumps(spec.model_dump(mode="json")), MODEL_VERSION, now, now])
    record_audit(conn, actor, operator=operator, object_type="dashboard", object_id=identity, action="dashboard_created", after_revision=1, after_state=body.visibility,
                 request_id=request_id, context={"tiles": len(spec.tiles)})
    return get_dashboard(conn, operator, actor, identity)


def update_dashboard(conn: Any, operator: str, actor: Actor | None, dashboard_id: str, changes: dict[str, Any], *, request_id: str | None = None) -> dict[str, Any]:
    ensure_tables(conn)
    vis, vp = _visible(actor, operator)
    rows = _rows(conn, f"SELECT * FROM zaad_analytics_dashboards WHERE operator_id = ? AND dashboard_id = ? AND deleted_at IS NULL{vis} LIMIT 1", [operator, dashboard_id, *vp])  # noqa: S608  # nosec B608
    if not rows:
        raise NotFound(dashboard_id)
    row = rows[0]
    _may_edit(row, actor, operator)
    unknown = set(changes) - {"name", "description", "spec", "visibility"}
    if unknown:
        raise AnalyticsRefused("spec_invalid", f"Cannot change {', '.join(sorted(unknown))}.")
    visibility = str(changes.get("visibility", row["visibility"]))
    if visibility not in ("private", "workspace"):
        raise AnalyticsRefused("spec_invalid", "visibility is private or workspace.")
    if visibility == "workspace" and row["visibility"] != "workspace":
        permissions.require(actor, "shareAnalysis")
    spec_json = row["spec_json"]
    if "spec" in changes:
        spec = DashboardSpec.model_validate(changes["spec"]).model_copy(update={"semantic_model_version": MODEL_VERSION})
        _check_tiles(conn, operator, actor, spec)
        spec_json = json.dumps(spec.model_dump(mode="json"))
    conn.execute("UPDATE zaad_analytics_dashboards SET name = ?, description = ?, visibility = ?, spec_json = ?, semantic_model_version = ?, version = version + 1, updated_at = ? "
                 "WHERE operator_id = ? AND dashboard_id = ?",
                 [str(changes.get("name", row["name"]))[:160], changes.get("description", row["description"]), visibility, spec_json, MODEL_VERSION, _now(), operator, dashboard_id])
    action = "dashboard_shared" if visibility != row["visibility"] else "dashboard_updated"
    record_audit(conn, actor, operator=operator, object_type="dashboard", object_id=dashboard_id, action=action, before_revision=int(row["version"]),
                 after_revision=int(row["version"]) + 1, before_state=row["visibility"], after_state=visibility, request_id=request_id)
    return get_dashboard(conn, operator, actor, dashboard_id)


def duplicate_dashboard(conn: Any, operator: str, actor: Actor | None, dashboard_id: str, *, request_id: str | None = None) -> dict[str, Any]:
    source = get_dashboard(conn, operator, actor, dashboard_id)
    body = DashboardIn(name=f"{source['name']} (copy)"[:160], description=source["description"], spec=DashboardSpec.model_validate(source["spec"]), visibility="private")
    return create_dashboard(conn, operator, actor, body, request_id=request_id)


def delete_dashboard(conn: Any, operator: str, actor: Actor | None, dashboard_id: str, *, request_id: str | None = None) -> None:
    ensure_tables(conn)
    vis, vp = _visible(actor, operator)
    rows = _rows(conn, f"SELECT * FROM zaad_analytics_dashboards WHERE operator_id = ? AND dashboard_id = ? AND deleted_at IS NULL{vis} LIMIT 1", [operator, dashboard_id, *vp])  # noqa: S608  # nosec B608
    if not rows:
        raise NotFound(dashboard_id)
    _may_edit(rows[0], actor, operator)
    conn.execute("UPDATE zaad_analytics_dashboards SET deleted_at = ?, updated_at = ? WHERE operator_id = ? AND dashboard_id = ?", [_now(), _now(), operator, dashboard_id])
    record_audit(conn, actor, operator=operator, object_type="dashboard", object_id=dashboard_id, action="dashboard_deleted", before_revision=int(rows[0]["version"]), request_id=request_id)
