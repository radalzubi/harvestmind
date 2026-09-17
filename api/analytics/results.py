"""Result assembly: engine rows become a `ResultSet` with typed cells, coverage and provenance.

Every cell is a value or `{"value": null, "reason", "why"}`. The contract decides which reason a
missing case maps to; a ratio whose denominator is zero is NOT_APPLICABLE, a measure the vault
cannot carry is NOT_MEASURED or BLOCKED_BY_DATA, an empty fact is NO_DATA, a plan-sourced measure
without a plan is NOT_IN_PLAN, and a ratio whose coverage is below the contract's floor is flagged
INSUFFICIENT_COVERAGE with the value still shown. Zero is a number.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from api.analytics.engines.base import EngineResult, PhysicalPlan
from api.analytics.semantic import DIMENSIONS, MODEL_VERSION, MetricContract
from api.analytics.validate import ValidatedQuery

_WHY = {
    "NO_DATA": "No rows of this kind have been uploaded for this scope.",
    "NOT_MEASURED": "The rows exist but do not carry the field this measure needs.",
    "NOT_APPLICABLE": "The denominator is zero, so no ratio exists.",
    "BLOCKED_BY_DATA": "The upload does not carry a column this needs.",
    "NOT_IN_PLAN": "No completed plan carries this.",
    "INSUFFICIENT_COVERAGE": "Too few rows carry the field for the ratio to be trusted.",
    "UNKNOWN": "Not available.",
}


def null_cell(reason: str, why: str | None = None) -> dict[str, Any]:
    return {"value": None, "reason": reason, "why": why or _WHY.get(reason, _WHY["UNKNOWN"])}


def _empty_reason(m: MetricContract, engine: EngineResult) -> tuple[str, str]:
    if "__fact__" in engine.blocked:
        reason, why = engine.blocked["__fact__"]
        if reason == "NOT_IN_PLAN" or m.evidence_class == "PLAN_SNAPSHOT":
            return "NOT_IN_PLAN", why
        return reason, why
    first = next(iter(m.null_behavior.values()), "NO_DATA")
    return (first if first != "0" else "NO_DATA"), _WHY.get(first, _WHY["NO_DATA"])


def _measure_cell(m: MetricContract, row: dict[str, Any], engine: EngineResult) -> Any:
    n = row.get(f"{m.metric_id}__n")
    if m.aggregation_rule in ("ratio_of_sums", "ratio_of_counts"):
        num, den = row.get(f"{m.metric_id}__num"), row.get(f"{m.metric_id}__den")
        if den is None or num is None:
            if m.metric_id == "weeks_of_cover":
                return null_cell("NOT_MEASURED", "No product in this group has an order in the trailing 12 weeks, so weekly demand is not measured.")
            if m.metric_id in ("supplier_late_rate",):
                return null_cell("BLOCKED_BY_DATA", "No matched order in this group carries a promised date, so lateness cannot be measured.")
            return null_cell("NOT_MEASURED", f"No row in this group records the field {m.display_name['en']} needs.")
        if float(den) == 0:
            if m.metric_id == "supplier_late_rate":
                return null_cell("BLOCKED_BY_DATA", "No matched order in this group carries a promised date, so lateness cannot be measured.")
            if m.metric_id == "weeks_of_cover":
                return null_cell("NOT_APPLICABLE", "Weekly demand is zero for this group, so cover is not a number.")
            return null_cell("NOT_APPLICABLE", "The denominator is zero here.")
        value = float(num) / float(den)
        cov_num, cov_den = row.get(f"{m.metric_id}__cov_num"), row.get(f"{m.metric_id}__cov_den")
        floor = m.coverage_rule.insufficient_below
        if floor is not None and cov_num is not None and cov_den not in (None, 0) and float(cov_num) / float(cov_den) < floor:
            return {"value": value, "reason": "INSUFFICIENT_COVERAGE", "why": f"Only {float(cov_num) / float(cov_den):.0%} of rows carry the field; the ratio is shown but not trusted.",
                    "numerator": num, "denominator": den}
        return {"value": value, "numerator": num, "denominator": den,
                **({"thin": True} if (m.coverage_rule.thin_sample_below and n is not None and float(n) < m.coverage_rule.thin_sample_below) else {})}
    raw_value: Any = row.get(m.metric_id)
    if raw_value is None:
        if m.evidence_class == "PLAN_SNAPSHOT" or m.aggregation_rule == "snapshot":
            return null_cell("NOT_IN_PLAN")
        if m.metric_id in ("shipped_units", "unfulfilled_units"):
            return null_cell("NOT_MEASURED", "No line in this group records a shipped quantity.")
        if m.metric_id in ("inventory_value", "open_po_value"):
            return null_cell("NOT_MEASURED", "No row in this group carries a unit cost.")
        if m.metric_id == "mean_late_days":
            return null_cell("NOT_APPLICABLE", "No late order in this group.")
        if n is not None and float(n) == 0:
            return null_cell("NO_DATA")
        return null_cell("NOT_MEASURED")
    return raw_value


def _dimension_value(dimension_id: str, value: Any) -> Any:
    if value is None:
        return {"value": None, "reason": "UNKNOWN", "why": f"{DIMENSIONS[dimension_id].label['en']} is not set on these rows."}
    return value


def assemble(validated: ValidatedQuery, physical: PhysicalPlan, engine: EngineResult, *, operator: str, dataset_version: dict[str, Any],
             last_updated: str | None, plan_summary: dict[str, Any] | None, planned_ms: float, cache: str = "miss", currency: str | None = None) -> dict[str, Any]:
    spec = validated.spec
    columns: list[dict[str, Any]] = []
    for d in validated.dimensions:
        columns.append({"id": d.dimension.id, "kind": "dimension", "label": d.dimension.label, "level": d.level, "dimension_kind": d.dimension.kind,
                        "blocked": engine.blocked.get(d.dimension.id)})
    for m in validated.metrics:
        columns.append({"id": m.metric_id, "kind": "measure", "metric_id": m.metric_id, "ref": m.ref, "label": m.display_name, "unit": m.unit,
                        "currency": currency if m.currency_behavior == "workspace_currency" else None, "aggregation_rule": m.aggregation_rule,
                        "additive": m.additive, "evidence_class": m.evidence_class, "register": m.register})
    if spec.comparison:
        for m in validated.metrics:
            columns.append({"id": f"{m.metric_id}__previous", "kind": "comparison", "metric_id": m.metric_id, "label": {k: f"{v} (previous)" for k, v in m.display_name.items()},
                            "unit": m.unit, "lag": spec.comparison.lag})

    rows: list[list[Any]] = []
    previous: dict[tuple, dict[str, Any]] = {}
    if spec.comparison and engine.comparison_rows is not None:
        shift = _period_shift(validated.grain or "week", spec.comparison.lag)
        keys = [d.dimension.id for d in validated.dimensions]
        source = engine.comparison_rows if engine.comparison_rows else engine.rows
        for r in source:
            key = tuple(shift(r.get(k)) if k == "date" else r.get(k) for k in keys)
            previous[key] = r
    for r in engine.rows:
        out: list[Any] = []
        for d in validated.dimensions:
            if d.dimension.id in engine.blocked:
                out.append(null_cell(*engine.blocked[d.dimension.id]))
            else:
                out.append(_dimension_value(d.dimension.id, r.get(d.dimension.id)))
        for m in validated.metrics:
            out.append(_measure_cell(m, r, engine))
        if spec.comparison:
            key = tuple(r.get(d.dimension.id) for d in validated.dimensions)
            prev = previous.get(key)
            for m in validated.metrics:
                out.append(_measure_cell(m, prev, engine) if prev else null_cell("NO_DATA", "No earlier period to compare against."))
        rows.append(out)
    if not rows:
        # one row of reasons so a KPI or a table can say why, in the contract's words
        reasons = [null_cell(*_empty_reason(m, engine)) for m in validated.metrics]
        head = _empty_reason(validated.metrics[0], engine)
        empty_row = [null_cell(*head) for _ in validated.dimensions] + reasons
        if spec.comparison:
            empty_row += [null_cell("NO_DATA") for _ in validated.metrics]
        rows.append(empty_row)
        empty = True
    else:
        empty = False

    coverage: dict[str, Any] = {}
    for m in validated.metrics:
        cov = engine.coverage.get(m.metric_id) or {}
        num, den = cov.get("numerator"), cov.get("denominator")
        share = (num / den) if (num is not None and den) else None
        coverage[m.metric_id] = {
            "measure": m.coverage_rule.measure, "rows": cov.get("n"), "measured_share": share,
            "insufficient": bool(m.coverage_rule.insufficient_below is not None and share is not None and share < m.coverage_rule.insufficient_below),
            "thin_sample": bool(m.coverage_rule.thin_sample_below is not None and cov.get("n") is not None and float(cov["n"] or 0) < m.coverage_rule.thin_sample_below),
            "total": _total_cell(m, cov, engine, time_series=validated.time_dimension is not None),
        }
    blocked = {k: {"reason": v[0], "why": v[1]} for k, v in engine.blocked.items() if k != "__fact__"}
    filters = [{"dimension_id": f.dimension.id, "label": f.dimension.label, "op": f.op, "values": list(f.values)} for f in validated.filters]
    provenance = {
        "definitions": [{"ref": m.ref, "metric_id": m.metric_id, "display_name": m.display_name, "business_definition": m.business_definition,
                         "numerator": m.numerator, "denominator": m.denominator, "aggregation_rule": m.aggregation_rule, "evidence_class": m.evidence_class,
                         "register": m.register, "unit": m.unit, "parameters": m.parameters, "lineage": list(m.lineage)} for m in validated.metrics],
        "source_entities": sorted({e for m in validated.metrics for e in m.source_entities}),
        "source_data": sorted({t for m in validated.metrics for t in m.lineage}),
        "fact": validated.fact.id, "filters": filters, "blocked": blocked,
        "time": {"grain": validated.grain, "anchor": validated.anchor, "start": physical.range_start, "end": physical.range_end},
        "date_range": {"start": physical.range_start, "end": physical.range_end}, "bucket": validated.grain or "all",
        "last_updated": last_updated, "data_cutoff": engine.data_cutoff,
        "dataset_version": dataset_version.get("dataset_version_id"),
        "plan": ({k: plan_summary.get(k) for k in ("job_id", "finished_at", "as_of", "information_hash", "stale", "stale_reason")} if plan_summary and any(m.evidence_class in ("PLAN_SNAPSHOT", "MODELED") for m in validated.metrics) else None),
        "scope_filtered": [], "notes": list(validated.notes), "engine": "duckdb" if physical.fact_source == "sql" else "plan snapshot",
        "metric": "; ".join(f"{m.display_name['en']} = {m.numerator} / {m.denominator}" if m.denominator != "—" else f"{m.display_name['en']} = {m.numerator}" for m in validated.metrics),
        "numerator": "; ".join(m.numerator for m in validated.metrics), "denominator": "; ".join(m.denominator for m in validated.metrics),
        "coverage": {m.metric_id: coverage[m.metric_id]["rows"] for m in validated.metrics},
    }
    return {
        "query_id": f"q_{uuid.uuid4().hex[:16]}", "semantic_model_version": MODEL_VERSION, "dataset_version": dataset_version,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "columns": columns, "rows": rows, "empty": empty,
        "coverage": coverage, "provenance": provenance,
        "bounds": {"truncated": engine.truncated, "limit_applied": validated.limit, "top_n_applied": physical.top_n, "rows": len(rows)},
        "timing": {"planned_ms": round(planned_ms, 2), "executed_ms": round(engine.executed_ms, 2), "cache": cache},
        "spec": spec.canonical(), "spec_hash": spec.spec_hash(),
    }


def _total_cell(m: MetricContract, cov: dict[str, Any], engine: EngineResult, time_series: bool = False) -> Any:
    """The whole-result figure for the measure: a ratio of sums for ratios, the sum for additive
    measures, and nothing (with the reason) for a measure that must not be summed across rows."""
    if "__fact__" in engine.blocked:
        return null_cell(*_empty_reason(m, engine))
    if m.aggregation_rule in ("ratio_of_sums", "ratio_of_counts"):
        num, den = cov.get("value_num"), cov.get("value_den")
        if num is None or den is None:
            return null_cell("NOT_MEASURED")
        if float(den) == 0:
            return null_cell("NOT_APPLICABLE")
        return {"value": float(num) / float(den), "numerator": num, "denominator": den}
    value = cov.get("value")
    if m.additive:
        return value if value is not None else null_cell("NO_DATA")
    if m.aggregation_rule in ("count_distinct", "quantile", "mean") or (m.aggregation_rule == "latest_snapshot" and not time_series):
        # computed once over the whole result, never by adding the rows
        return {"value": value, "basis": "overall"} if value is not None else null_cell("NO_DATA")
    if m.aggregation_rule == "latest_snapshot":
        return null_cell("NOT_APPLICABLE", f"{m.display_name['en']} is a level per period; the latest period is the current figure, and periods are never added.")
    return null_cell("NOT_APPLICABLE", f"{m.display_name['en']} is not additive across rows; no total is shown.")


def _period_shift(grain: str, lag: int):
    from datetime import date, timedelta

    def go(period: Any) -> Any:
        if not isinstance(period, str) or len(period) < 10:
            return period
        d = date.fromisoformat(period[:10])
        if grain == "day":
            n = d + timedelta(days=lag)
        elif grain == "week":
            n = d + timedelta(weeks=lag)
        elif grain in ("month", "quarter"):
            step = lag if grain == "month" else 3 * lag
            m = d.month + step
            y = d.year + (m - 1) // 12
            n = d.replace(year=y, month=(m - 1) % 12 + 1, day=1)
        else:
            n = d.replace(year=d.year + lag)
        return n.isoformat() + period[10:]
    return go
