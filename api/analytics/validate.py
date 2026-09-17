"""Semantic and permission validation: deterministic, before any SQL exists.

A spec is refused with one code from the taxonomy the moment it names a metric or a dimension the
registry does not know, asks a metric for a dimension it does not allow, combines measures that
live on different facts (one fact per query in V1), combines two value registers, requests a grain
or a comparison the fact cannot carry, or reaches a classification the actor's role may not read.
What comes out is a `ValidatedQuery`: resolved contracts, the fact, the dimensions with their
join routes, filters with resolved dimensions, the time grain and anchor, and the clamps applied.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from api.analytics import permissions, semantic
from api.analytics.contracts import (
    MAX_LIMIT, AnalyticsQuerySpec, AnalyticsRefused, Filter,
)
from api.analytics.semantic import (
    DIMENSIONS, DRILL_PATHS, FACTS, MODEL_VERSION, TIME_GRAINS, VALUE_REGISTERS, Dimension, MetricContract,
)
from api.product.governance import Actor

_LEVELS = set(TIME_GRAINS)


@dataclass(frozen=True)
class ResolvedDimension:
    dimension: Dimension
    route: str           # row | product | supplier | derived
    level: str | None    # time grain for the time dimension


@dataclass(frozen=True)
class ResolvedFilter:
    dimension: Dimension
    route: str
    op: str
    values: tuple[str, ...]


@dataclass
class ValidatedQuery:
    spec: AnalyticsQuerySpec
    metrics: list[MetricContract]
    fact: semantic.Fact
    dimensions: list[ResolvedDimension]
    filters: list[ResolvedFilter]
    grain: str | None
    anchor: str
    limit: int
    notes: list[str] = field(default_factory=list)

    @property
    def time_dimension(self) -> ResolvedDimension | None:
        return next((d for d in self.dimensions if d.dimension.kind == "time"), None)

    @property
    def member_dimensions(self) -> list[ResolvedDimension]:
        return [d for d in self.dimensions if d.dimension.kind != "time"]

    def as_dict(self) -> dict[str, Any]:
        return {"fact": self.fact.id, "metrics": [m.ref for m in self.metrics],
                "dimensions": [{"id": d.dimension.id, "route": d.route, "level": d.level} for d in self.dimensions],
                "filters": [{"id": f.dimension.id, "op": f.op, "values": list(f.values)} for f in self.filters],
                "grain": self.grain, "anchor": self.anchor, "limit": self.limit, "notes": list(self.notes)}


def _resolve_metric(ref: str) -> MetricContract:
    try:
        return semantic.metric(ref)
    except KeyError as exc:
        metric_id = ref.partition("@")[0]
        if metric_id in semantic.METRICS:
            raise AnalyticsRefused("semantic_version_deprecated", f"{ref} is not a version of {metric_id} this model serves "
                                   f"(current: {semantic.METRICS[metric_id].ref}).") from exc
        raise AnalyticsRefused("semantic_unknown_metric", f"{metric_id!r} is not a governed metric. Only metrics in the semantic model can be queried.") from exc


def _resolve_dimension(dimension_id: str) -> Dimension:
    try:
        return semantic.dimension(dimension_id)
    except KeyError as exc:
        raise AnalyticsRefused("semantic_unknown_dimension", f"{dimension_id!r} is not a governed dimension.") from exc


def validate(spec: AnalyticsQuerySpec, actor: Actor | None) -> ValidatedQuery:
    if spec.semantic_model_version != MODEL_VERSION:
        raise AnalyticsRefused("semantic_version_deprecated", f"This query was built against model {spec.semantic_model_version}; the current model is {MODEL_VERSION}.")

    metrics = [_resolve_metric(m.ref) for m in spec.measures]
    for m in metrics:
        if m.status not in ("EXISTS", "DERIVABLE"):
            raise AnalyticsRefused("semantic_metric_not_queryable", f"{m.display_name['en']} is classified {m.status} and cannot be queried yet: {m.business_definition}",
                                   {"metric_id": m.metric_id, "status": m.status})
        if not permissions.can_read(actor, m.security_classification):
            raise AnalyticsRefused("permission_denied", f"Your role may not read {m.security_classification.lower()} measures such as {m.display_name['en']}.",
                                   {"metric_id": m.metric_id, "classification": m.security_classification})
    facts = {m.fact for m in metrics}
    if len(facts) > 1:
        raise AnalyticsRefused("semantic_no_join_path", "These measures are defined on different records and cannot be combined in one query: "
                               + ", ".join(f"{m.display_name['en']} ({m.fact})" for m in metrics) + ". Put them on separate visuals of one dashboard.",
                               {"facts": sorted(facts)})
    registers = {m.register for m in metrics if m.register}
    if len(registers) > 1:
        raise AnalyticsRefused("semantic_registers_combined", "Two value registers are never combined in one query: " + ", ".join(sorted(registers)) + ".",
                               {"registers": sorted(registers)})
    fact = FACTS[metrics[0].fact]

    # dimensions: known, allowed by every measure, reachable from the fact, readable
    dims: list[ResolvedDimension] = []
    grain: str | None = spec.time.grain if spec.time else None
    for ref in spec.dimensions:
        d = _resolve_dimension(ref.dimension_id)
        if d.status not in ("EXISTS", "DERIVABLE"):
            raise AnalyticsRefused("semantic_unknown_dimension", f"{d.label['en']} is classified {d.status}; the vault does not hold it.", {"dimension_id": d.id})
        if not permissions.can_read(actor, d.classification):
            raise AnalyticsRefused("permission_denied", f"Your role may not read the {d.label['en']} dimension.", {"dimension_id": d.id})
        for m in metrics:
            if d.id not in m.allowed_dimensions or d.id in m.disallowed_dimensions:
                raise AnalyticsRefused("semantic_dimension_not_allowed", f"{m.display_name['en']} cannot be broken down by {d.label['en']}. Allowed: "
                                       + ", ".join(m.allowed_dimensions) + ".", {"metric_id": m.metric_id, "dimension_id": d.id, "allowed": list(m.allowed_dimensions)})
        route = semantic.join_path(fact.id, d.id)
        if route is None:
            raise AnalyticsRefused("semantic_no_join_path", f"There is no governed path from {fact.entity} to {d.label['en']}.", {"fact": fact.id, "dimension_id": d.id})
        level = None
        if d.kind == "time":
            level = ref.level or grain or "week"
            if level not in _LEVELS:
                raise AnalyticsRefused("semantic_invalid_time", f"{level!r} is not a time grain; one of {', '.join(TIME_GRAINS)}.")
            if grain and ref.level and ref.level != grain:
                raise AnalyticsRefused("semantic_invalid_time", "The time dimension's level and time.grain disagree.")
            grain = level
        dims.append(ResolvedDimension(d, route, level))
    if grain and not any(d.dimension.kind == "time" for d in dims):
        # a grain without the date dimension: add it, so "monthly" always means a monthly series
        if "date" not in metrics[0].allowed_dimensions:
            raise AnalyticsRefused("semantic_invalid_time", f"{metrics[0].display_name['en']} has no time dimension.")
        if len(dims) >= 3:
            raise AnalyticsRefused("limit_exceeded", "At most three dimensions, the time dimension included.")
        dims.append(ResolvedDimension(DIMENSIONS["date"], "row", grain))
    if any(m.aggregation_rule == "snapshot" for m in metrics) and any(d.dimension.kind == "time" for d in dims):
        raise AnalyticsRefused("semantic_aggregation_forbidden", "A plan snapshot has no time series; it is read once from the plan.")
    if spec.comparison and grain is None:
        raise AnalyticsRefused("semantic_invalid_time", "A period-over-period comparison needs a time grain.")

    # time anchor
    anchor = fact.time_anchor
    if spec.time and spec.time.anchor:
        if spec.time.anchor not in (fact.time_anchors or (fact.time_anchor,)):
            raise AnalyticsRefused("semantic_invalid_time", f"{spec.time.anchor!r} is not a date on {fact.entity}; one of {', '.join(fact.time_anchors or (fact.time_anchor,))}.")
        anchor = spec.time.anchor
    if spec.time and spec.time.range and not anchor:
        raise AnalyticsRefused("semantic_invalid_time", f"{fact.entity} rows carry no date to bound.")

    # filters: known, reachable from the fact, on a dimension at least one measure allows
    filters: list[ResolvedFilter] = []
    for f in spec.filters:
        d = _resolve_dimension(f.dimension_id)
        if d.kind == "time":
            raise AnalyticsRefused("semantic_invalid_filter", "Bound the time range with time.range, not a filter on date.")
        if not permissions.can_read(actor, d.classification):
            raise AnalyticsRefused("permission_denied", f"Your role may not filter on {d.label['en']}.", {"dimension_id": d.id})
        route = semantic.join_path(fact.id, d.id)
        if route is None:
            raise AnalyticsRefused("semantic_no_join_path", f"{fact.entity} rows cannot be filtered by {d.label['en']}: no governed path.", {"fact": fact.id, "dimension_id": d.id})
        if not any(d.id in m.allowed_dimensions for m in metrics):
            raise AnalyticsRefused("semantic_dimension_not_allowed", f"No measure in this query allows a filter on {d.label['en']}.", {"dimension_id": d.id})
        filters.append(ResolvedFilter(d, route, f.op, tuple(f.values)))

    # top-N: on a member dimension of the query; "others" only where every measure is additive
    if spec.top_n:
        member_ids = [d.dimension.id for d in dims if d.dimension.kind != "time"]
        if spec.top_n.dimension_id not in member_ids:
            raise AnalyticsRefused("spec_invalid", "top_n names a dimension that is not in the query.", {"dimension_id": spec.top_n.dimension_id})
        if spec.top_n.others and not all(m.additive for m in metrics):
            raise AnalyticsRefused("semantic_aggregation_forbidden", "\"Others\" folds rows together, which is only meaningful for additive measures; "
                                   + ", ".join(m.display_name["en"] for m in metrics if not m.additive) + " cannot be summed across members.")
        if spec.top_n.by and spec.top_n.by not in {m.metric_id for m in metrics}:
            raise AnalyticsRefused("spec_invalid", "top_n.by names a measure that is not in the query.")
    for s in spec.sort:
        known = {m.metric_id for m in metrics} | {d.dimension.id for d in dims}
        if s.field not in known:
            raise AnalyticsRefused("spec_invalid", f"sort names {s.field!r}, which is neither a measure nor a dimension of this query.")
    if spec.drilldown:
        d = _resolve_dimension(spec.drilldown.dimension_id)
        if d.id not in DRILL_PATHS and d.id not in ("sku", "product", "customer", "supplier", "location"):
            raise AnalyticsRefused("spec_invalid", f"{d.label['en']} has no drill path.")

    limit = min(spec.limit, MAX_LIMIT)
    notes: list[str] = []
    if spec.limit > MAX_LIMIT:
        notes.append(f"limit clamped to {MAX_LIMIT}")
    return ValidatedQuery(spec=spec, metrics=metrics, fact=fact, dimensions=dims, filters=filters, grain=grain, anchor=anchor, limit=limit, notes=notes)


def registers_in(metrics: list[MetricContract]) -> list[str]:
    return [r for r in VALUE_REGISTERS if any(m.register == r for m in metrics)]


def allowed_dimensions_for(metric_ids: list[str]) -> list[str]:
    """The intersection of what every named metric allows — what the builder may offer next."""
    sets = []
    for ref in metric_ids:
        m = semantic.METRICS.get(ref.partition("@")[0])
        if m is None:
            return []
        sets.append(set(m.allowed_dimensions))
    if not sets:
        return []
    out = set.intersection(*sets)
    return [d for d in DIMENSIONS if d in out]


def filter_to_dict(f: Filter) -> dict[str, Any]:
    return {"dimension_id": f.dimension_id, "op": f.op, "values": list(f.values)}
