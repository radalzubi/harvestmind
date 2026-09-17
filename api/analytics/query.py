"""The query pipeline, end to end:

    AnalyticsQuerySpec → semantic validation → permission validation → planning → storage adapter
    → result assembly → provenance

`run` is the one entry point every surface uses — the router, Insights' bridge, Ask ZAAD, the
exports and the signals. It is tenant-scoped by construction (`conn` is the caller's own vault and
`operator` keys everything), it reads the latest completed plan only for plan-sourced measures,
and it caches by the full identity of the answer.
"""
from __future__ import annotations

import time
from datetime import date
from typing import Any

from api.analytics import cache, freshness, permissions, planner, results
from api.analytics.contracts import AnalyticsQuerySpec, AnalyticsRefused
from api.analytics.engines.base import StorageAdapter
from api.analytics.engines.duckdb_adapter import DuckDBAdapter
from api.analytics.semantic import MODEL_VERSION
from api.analytics.validate import ValidatedQuery, validate
from api.product.governance import Actor


def adapter_for(conn: Any, operator: str) -> StorageAdapter:
    """DuckDB today. A different engine is chosen here and nowhere else."""
    return DuckDBAdapter(conn, operator)


def run(conn: Any, operator: str, actor: Actor | None, spec: AnalyticsQuerySpec, *, use_cache: bool = True, timeout_s: float | None = None,
        latest_plan: dict[str, Any] | None = None, currency: str | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    validated: ValidatedQuery = validate(spec, actor)
    version = freshness.current(conn, operator)
    perm = permissions.permissions_hash(actor)
    k = cache.key(operator, version["dataset_version_id"], MODEL_VERSION, perm, spec.spec_hash())
    if use_cache:
        hit = cache.get(k)
        if hit is not None:
            out = dict(hit)
            out["timing"] = {**hit["timing"], "cache": "hit"}
            return out

    plan_rows: list[dict[str, Any]] | None = None
    plan_meta: dict[str, Any] | None = None
    plan_summary: dict[str, Any] | None = None
    needs_plan = validated.fact.source == "plan" or any(m.evidence_class in ("PLAN_SNAPSHOT", "MODELED") for m in validated.metrics)
    if needs_plan:
        from api.product import insights
        plan = latest_plan if latest_plan is not None else insights.latest_plan(conn, operator)
        plan_summary = insights.plan_summary(plan)
        value_payload = insights.value(conn, operator, plan) if validated.fact.id == "plan_value" else None
        plan_rows, plan_meta = planner.plan_snapshot_rows(validated.fact.id, plan, value_payload)
        if currency is None and plan:
            currency = (plan.get("request") or {}).get("currency")
    if currency is None:
        currency = _workspace_currency(conn)

    cutoff = date.fromisoformat(version["data_cutoff"]) if version.get("data_cutoff") else None
    physical = planner.plan(validated, data_cutoff=cutoff, plan_rows=plan_rows, plan_meta=plan_meta, timeout_s=timeout_s)
    planned_ms = (time.perf_counter() - started) * 1000.0
    engine = adapter_for(conn, operator).execute(physical)
    out = results.assemble(validated, physical, engine, operator=operator, dataset_version=version, last_updated=version.get("last_updated"),
                           plan_summary=plan_summary, planned_ms=planned_ms, cache="bypass" if not use_cache else "miss", currency=currency)
    if use_cache:
        cache.put(k, out)
    return out


def members(conn: Any, operator: str, actor: Actor | None, dimension_id: str, *, search: str | None = None, limit: int = 100) -> list[str]:
    from api.analytics import semantic
    try:
        d = semantic.dimension(dimension_id)
    except KeyError as exc:
        raise AnalyticsRefused("semantic_unknown_dimension", f"{dimension_id!r} is not a governed dimension.") from exc
    if not permissions.can_read(actor, d.classification):
        raise AnalyticsRefused("permission_denied", f"Your role may not read the {d.label['en']} dimension.")
    return adapter_for(conn, operator).members(dimension_id, search=search, limit=max(1, min(int(limit), 200)))


def _workspace_currency(conn: Any) -> str | None:
    from api.product.catalog import _one, has_table
    if not has_table(conn, "stg_fmcg_economics"):
        return None
    try:
        value = _one(conn, "SELECT value FROM stg_fmcg_economics WHERE key = 'currency' LIMIT 1")
    except Exception:  # noqa: BLE001
        return None
    return str(value) if value else None
