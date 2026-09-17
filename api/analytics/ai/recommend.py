"""Visual recommendation: a chart type from the shape of a validated query, with the reason.

    trend (time grain)                  → line (area when one additive measure)
    ranking (one member dimension)      → horizontal bar
    composition (member × time)         → stacked bar (additive) or multi-line (ratios)
    relationship (two measures, one dim)→ scatter
    two member dimensions               → heatmap (one measure) or pivot
    no dimension                        → KPI (one or two measures) or table
    detail                              → table

Deterministic; the model may name a type, and it is used only when the matrix allows it.
"""
from __future__ import annotations

from typing import Any

from api.analytics.contracts import VisualSpec
from api.analytics.validate import ValidatedQuery

ALLOWED: dict[str, set[str]] = {
    "trend": {"line", "area", "bar", "stacked_bar", "table", "pivot"},
    "trend_series": {"line", "stacked_bar", "area", "table", "pivot", "heatmap"},
    "ranking": {"hbar", "bar", "table", "pivot"},
    "composition": {"stacked_bar", "hbar", "bar", "table", "pivot"},
    "relationship": {"scatter", "table"},
    "matrix": {"heatmap", "pivot", "table"},
    "kpi": {"kpi", "table"},
    "detail": {"table", "pivot"},
}


def shape(validated: ValidatedQuery) -> str:
    time_dim = validated.time_dimension is not None
    members = validated.member_dimensions
    measures = validated.metrics
    if time_dim and not members:
        return "trend"
    if time_dim and len(members) == 1:
        return "trend_series"
    if not time_dim and len(members) == 2:
        return "matrix"
    if not time_dim and len(members) == 1 and len(measures) >= 2 and validated.spec.top_n is None and any(not m.additive for m in measures):
        return "relationship"
    if not time_dim and len(members) == 1:
        return "ranking"
    if not members and not time_dim:
        return "kpi" if len(measures) <= 3 else "detail"
    return "detail"


def recommend(validated: ValidatedQuery, requested: str | None = None) -> tuple[str, str]:
    """(visual_type, reason)."""
    s = shape(validated)
    additive = all(m.additive for m in validated.metrics)
    default = {
        "trend": "area" if (len(validated.metrics) == 1 and additive) else "line",
        "trend_series": "stacked_bar" if (additive and len(validated.metrics) == 1) else "line",
        "ranking": "hbar", "composition": "stacked_bar", "relationship": "scatter",
        "matrix": "heatmap" if len(validated.metrics) == 1 else "pivot",
        "kpi": "kpi", "detail": "table",
    }[s]
    reason = {
        "trend": "a measure over time reads as a line", "trend_series": "several members over time: stacked bars for an additive measure, lines for a ratio",
        "ranking": "members ranked on a measure read as horizontal bars", "composition": "shares of a whole stack", "relationship": "two measures per member read as a scatter",
        "matrix": "two dimensions over one measure read as a heatmap", "kpi": "no breakdown: the figure itself", "detail": "several measures and dimensions: a table",
    }[s]
    if requested and requested in ALLOWED[s]:
        return requested, f"{requested} kept ({reason})"
    return default, reason


def encoding_for(validated: ValidatedQuery, visual_type: str) -> dict[str, Any]:
    time_dim = validated.time_dimension
    members = [d.dimension.id for d in validated.member_dimensions]
    measures = [m.metric_id for m in validated.metrics]
    enc: dict[str, Any] = {"y": measures}
    if visual_type in ("line", "area", "bar", "hbar", "stacked_bar") and len(validated.metrics) > 1:
        # one unit per axis: the chart draws the first measure's unit; the others stay in the table twin
        unit = validated.metrics[0].unit
        enc["y"] = [m.metric_id for m in validated.metrics if m.unit == unit]
    if visual_type in ("line", "area", "bar", "stacked_bar") and time_dim:
        enc["x"] = "date"
        if members:
            enc["series"] = members[0]
    elif visual_type in ("hbar", "bar", "stacked_bar") and members:
        enc["x"] = members[0]
        if len(members) > 1:
            enc["series"] = members[1]
    elif visual_type == "scatter" and members:
        enc["x"] = measures[0]
        enc["y"] = measures[1:2] or measures[:1]
        enc["color"] = members[0]
    elif visual_type == "heatmap" and len(members) >= 2:
        enc["rows"], enc["columns"] = [members[0]], [members[1]]
    elif visual_type == "pivot":
        dims = [d.dimension.id for d in validated.dimensions]
        enc["rows"] = dims[:1]
        enc["columns"] = dims[1:2]
    return enc


def visual_for(validated: ValidatedQuery, visual_type: str, title: dict[str, str], description: dict[str, str]) -> VisualSpec:
    from api.analytics.semantic import DRILL_PATHS
    drill = []
    for d in validated.dimensions:
        key = d.level if d.dimension.kind == "time" else d.dimension.id
        if key in DRILL_PATHS:
            drill.append(DRILL_PATHS[key])
    return VisualSpec.model_validate({"visual_type": visual_type, "title": title, "description": description, "query": validated.spec.model_dump(mode="json"),
                                      "encoding": encoding_for(validated, visual_type), "drill_path": drill[:6]})
