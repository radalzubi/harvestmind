"""What Ask ZAAD may know: the semantic schema, bounded member lists, coverage warnings.

Never a database, never raw rows, never another tenant. The schema is the registry's queryable
part (ids, definitions, allowed dimensions, evidence classes); the members are the top values of
the bounded dimensions the question mentions, capped; the warnings are the data-quality facts the
result would carry anyway (no shipped quantities, no promised dates, no sites on orders).
"""
from __future__ import annotations

from typing import Any

from api.analytics import query, semantic
from api.product.governance import Actor

MEMBER_DIMENSIONS = ("category", "brand", "supplier", "customer", "location", "channel", "sector", "route", "origin", "abc_class")
MAX_MEMBERS = 60


def schema(actor: Actor | None) -> dict[str, Any]:
    from api.analytics import permissions
    metrics = []
    for m in semantic.queryable_metrics():
        if not permissions.can_read(actor, m.security_classification):
            continue
        metrics.append({"metric_id": m.metric_id, "name": m.display_name["en"], "domain": m.domain, "fact": m.fact, "definition": m.description["en"],
                        "aggregation": m.aggregation_rule, "unit": m.unit, "evidence": m.evidence_class, "register": m.register,
                        "allowed_dimensions": list(m.allowed_dimensions), "time": bool(m.time_anchor)})
    dims = [{"dimension_id": d.id, "name": d.label["en"], "kind": d.kind, "description": d.description}
            for d in semantic.DIMENSIONS.values() if d.status in ("EXISTS", "DERIVABLE") and permissions.can_read(actor, d.classification)]
    return {"semantic_model_version": semantic.MODEL_VERSION, "metrics": metrics, "dimensions": dims, "time_grains": list(semantic.TIME_GRAINS),
            "filter_ops": ["in", "eq", "ne", "contains"], "null_reasons": list(semantic.NULL_REASONS)}


def members(conn: Any, operator: str, actor: Actor | None, question: str, *, dimensions: tuple[str, ...] = MEMBER_DIMENSIONS) -> dict[str, list[str]]:
    """Bounded value lists so the planner can resolve "only seafood" to a member of `category`."""
    out: dict[str, list[str]] = {}
    for dimension_id in dimensions:
        try:
            values = query.members(conn, operator, actor, dimension_id, limit=MAX_MEMBERS)
        except Exception:  # noqa: BLE001 - a dimension the workspace cannot answer is simply absent
            continue
        if values:
            out[dimension_id] = [str(v)[:80] for v in values][:MAX_MEMBERS]
    return out


def warnings(conn: Any) -> list[str]:
    from api.product.catalog import _columns, has_table, site_column_usable
    out: list[str] = []
    if has_table(conn, "stg_fmcg_orders"):
        if "qty_shipped" not in _columns(conn, "stg_fmcg_orders"):
            out.append("Customer orders carry no shipped quantity: fill rate, shipped and unfulfilled units are NOT_MEASURED.")
        if not site_column_usable(conn, "stg_fmcg_orders", "location_id"):
            out.append("Customer orders carry no site: demand by site is BLOCKED_BY_DATA.")
    else:
        out.append("No customer orders uploaded: demand and service measures are NO_DATA.")
    if not has_table(conn, "stg_fmcg_receipts"):
        out.append("No receipts uploaded: supplier fill, lead time and lateness are NO_DATA.")
    if not has_table(conn, "stg_fmcg_inventory"):
        out.append("No inventory snapshots uploaded: stock measures are NO_DATA.")
    return out


def build(conn: Any, operator: str, actor: Actor | None, question: str) -> dict[str, Any]:
    from api.analytics import freshness
    version = freshness.current(conn, operator, record=False)
    return {"schema": schema(actor), "members": members(conn, operator, actor, question), "warnings": warnings(conn),
            "data_cutoff": version.get("data_cutoff"), "last_updated": version.get("last_updated"), "dataset_version": version.get("dataset_version_id")}
