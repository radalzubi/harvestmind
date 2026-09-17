"""Query planning: a validated query becomes an engine-neutral `PhysicalPlan`.

The planner resolves the time range (absolute, or relative to the data's last date), attaches the
bounds, the sort, the top-N and the timeout, and — for plan-snapshot facts — supplies the rows read
from the latest completed plan so the engine groups them without recomputing anything. It never
renders SQL.
"""
from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any

from api.analytics.engines.base import PhysicalPlan, PlanDimension, PlanFilter
from api.analytics.validate import ValidatedQuery

DEFAULT_TIMEOUT_S = float(os.getenv("ZAAD_ANALYTICS_QUERY_TIMEOUT_S", "20"))


def _relative_start(last: int, unit: str, end: date) -> date:
    if unit == "day":
        return end - timedelta(days=last)
    if unit == "week":
        return end - timedelta(weeks=last)
    if unit == "month":
        m = end.month - last
        y = end.year + (m - 1) // 12
        return end.replace(year=y, month=(m - 1) % 12 + 1, day=1)
    if unit == "quarter":
        m = end.month - 3 * last
        y = end.year + (m - 1) // 12
        return end.replace(year=y, month=(m - 1) % 12 + 1, day=1)
    return end.replace(year=end.year - last, month=1, day=1)


def plan(validated: ValidatedQuery, *, data_cutoff: date | None = None, plan_rows: list[dict[str, Any]] | None = None,
         plan_meta: dict[str, Any] | None = None, timeout_s: float | None = None) -> PhysicalPlan:
    spec = validated.spec
    start = end = None
    if spec.time and spec.time.range:
        r = spec.time.range
        start, end = r.start, r.end
        if r.last and r.unit:
            anchor_end = date.fromisoformat(end) if end else (data_cutoff or date.today())
            start = _relative_start(r.last, r.unit, anchor_end).isoformat()
            end = end or anchor_end.isoformat()
    dims = tuple(PlanDimension(d.dimension.id, d.route, d.level, d.dimension.kind) for d in validated.dimensions)
    filters = tuple(PlanFilter(f.dimension.id, f.route, f.op, f.values) for f in validated.filters)
    top_n = None
    if spec.top_n:
        top_n = {"dimension_id": spec.top_n.dimension_id, "n": spec.top_n.n, "others": spec.top_n.others, "by": spec.top_n.by}
    sort = tuple((s.field, s.dir) for s in spec.sort)
    return PhysicalPlan(
        fact=validated.fact.id, fact_source=validated.fact.source, metrics=tuple(validated.metrics), dimensions=dims, filters=filters,
        grain=validated.grain, anchor=validated.anchor, range_start=start, range_end=end, limit=validated.limit, top_n=top_n, sort=sort,
        comparison_lag=spec.comparison.lag if spec.comparison else None, timeout_s=timeout_s or DEFAULT_TIMEOUT_S,
        supplied_rows=tuple(plan_rows or ()), parameters=dict(plan_meta or {}),
    )


def plan_snapshot_rows(fact_id: str, latest_plan: dict[str, Any] | None, value_payload: dict[str, Any] | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Rows for a plan-sourced fact, read from the stored plan. Never recomputed."""
    from api.product.insights import decisions_of_plan
    meta: dict[str, Any] = {"plan_present": latest_plan is not None}
    if latest_plan:
        meta.update({"plan_job_id": latest_plan.get("job_id"), "plan_as_of": latest_plan.get("as_of"), "plan_finished_at": latest_plan.get("finished_at"),
                     "plan_stale": latest_plan.get("stale"), "plan_information_hash": latest_plan.get("information_hash")})
    if fact_id == "decision":
        if not latest_plan:
            return [], meta
        sources = {s.get("id"): s for s in ((latest_plan.get("request") or {}).get("sources") or [])}
        pipeline = {p.get("id"): p for p in ((latest_plan.get("request") or {}).get("pipeline") or [])}
        rows = []
        for d in decisions_of_plan(latest_plan):
            supplier = None
            if d["kind"] == "purchase":
                supplier = (sources.get(d["target"]) or {}).get("supplier")
            elif d["kind"] == "open_po":
                src = (pipeline.get(d["target"]) or {}).get("source")
                supplier = (sources.get(src) or {}).get("supplier")
            rows.append({"decision_verb": d["verb"], "sku": d.get("sku"), "supplier": supplier, "decision_id": d["id"], "kind": d["kind"]})
        return rows, meta
    if fact_id == "plan_value":
        rows = []
        registers = (value_payload or {}).get("registers") or {}
        md = registers.get("MODELED_DIFFERENCE") or {}
        if md.get("available"):
            rows.append({"register": "MODELED_DIFFERENCE", "value_register": "MODELED_DIFFERENCE", "value": md.get("difference"), "currency": md.get("currency")})
        ae = registers.get("APPROVED_EXPECTED_DIFFERENCE") or {}
        for p in ae.get("proposals") or []:
            if p.get("available") and p.get("proposal_vs_current") is not None:
                rows.append({"register": "APPROVED_EXPECTED_DIFFERENCE", "value_register": "APPROVED_EXPECTED_DIFFERENCE", "value": p["proposal_vs_current"],
                             "currency": p.get("currency"), "draft_id": p.get("draft_id")})
        meta["plan_present"] = True
        return rows, meta
    return [], meta
