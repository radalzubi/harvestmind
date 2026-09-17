"""Insights on the governed layer: the representative Insights series served by the query engine.

One definition, three consumers. The demand series, the inventory series and the supplier trend
that Insights draws are re-expressed here as `AnalyticsQuerySpec`s over the registry's metrics and
proven identical to the released SQL by `tests/integration/test_analytics_insights_identity.py`.
Insights' composite payloads keep their assembler; the numbers inside them are the contract's.
"""
from __future__ import annotations

from typing import Any

from api.analytics import query
from api.analytics.contracts import AnalyticsQuerySpec
from api.product.governance import Actor
from api.product.insights import Scope

_GRAIN = {"day": "day", "week": "week", "month": "month"}


def _filters(scope: Scope) -> list[dict[str, Any]]:
    out = []
    for dim, value in (("sku", scope.sku), ("category", scope.category), ("brand", scope.brand), ("customer", scope.customer),
                       ("location", scope.location), ("supplier", scope.supplier)):
        if value:
            out.append({"dimension_id": dim, "op": "eq", "values": [value]})
    return out


def _time(scope: Scope, grain: str | None) -> dict[str, Any]:
    t: dict[str, Any] = {}
    if grain:
        t["grain"] = grain
    if scope.start or scope.end:
        t["range"] = {"start": scope.start.isoformat() if scope.start else None, "end": scope.end.isoformat() if scope.end else None}
    return t


def demand_series_spec(scope: Scope) -> AnalyticsQuerySpec:
    return AnalyticsQuerySpec.model_validate({"measures": [{"metric_id": "ordered_units"}, {"metric_id": "shipped_units"}, {"metric_id": "unfulfilled_units"}, {"metric_id": "ordered_lines"}],
                                              "time": _time(scope, _GRAIN[scope.bucket]), "filters": _filters(scope), "purpose": "insights", "limit": 400})


def inventory_series_spec(scope: Scope) -> AnalyticsQuerySpec:
    filters = [f for f in _filters(scope) if f["dimension_id"] != "customer"]
    return AnalyticsQuerySpec.model_validate({"measures": [{"metric_id": "inventory_units"}, {"metric_id": "inventory_value"}, {"metric_id": "in_transit_units"}],
                                              "time": _time(scope, _GRAIN[scope.bucket]), "filters": filters, "purpose": "insights", "limit": 400})


def supplier_trend_spec(scope: Scope) -> AnalyticsQuerySpec:
    filters = [f for f in _filters(scope) if f["dimension_id"] in ("supplier", "sku")]
    return AnalyticsQuerySpec.model_validate({"measures": [{"metric_id": "supplier_fill_rate"}, {"metric_id": "supplier_late_rate"}, {"metric_id": "matched_orders"}],
                                              "dimensions": [{"dimension_id": "supplier"}], "time": _time(scope, "month"), "filters": filters, "purpose": "insights", "limit": 400})


def demand_series(conn: Any, operator: str, actor: Actor | None, scope: Scope) -> list[dict[str, Any]]:
    """`insights.demand`'s series, from the engine: period, ordered, shipped, unfulfilled, lines."""
    result = query.run(conn, operator, actor, demand_series_spec(scope))
    if result.get("empty"):
        return []
    cols = [c["id"] for c in result["columns"]]
    out = []
    for row in result["rows"]:
        r = dict(zip(cols, row))
        out.append({"period": r["date"], "ordered": _v(r["ordered_units"]), "shipped": _v(r["shipped_units"]), "unfulfilled": _v(r["unfulfilled_units"]), "lines": _v(r["ordered_lines"])})
    return out


def inventory_series(conn: Any, operator: str, actor: Actor | None, scope: Scope) -> list[dict[str, Any]]:
    result = query.run(conn, operator, actor, inventory_series_spec(scope))
    if result.get("empty"):
        return []
    cols = [c["id"] for c in result["columns"]]
    return [{"period": r["date"], "units": _v(r["inventory_units"]), "value": _v(r["inventory_value"]), "in_transit": _v(r["in_transit_units"])}
            for r in (dict(zip(cols, row)) for row in result["rows"])]


def supplier_trend(conn: Any, operator: str, actor: Actor | None, scope: Scope) -> list[dict[str, Any]]:
    result = query.run(conn, operator, actor, supplier_trend_spec(scope))
    if result.get("empty"):
        return []
    cols = [c["id"] for c in result["columns"]]
    return [{"supplier_id": r["supplier"], "period": r["date"], "fill_rate": _v(r["supplier_fill_rate"]), "late_rate": _v(r["supplier_late_rate"]), "matched_orders": _v(r["matched_orders"])}
            for r in (dict(zip(cols, row)) for row in result["rows"])]


def _v(cell: Any) -> Any:
    return cell.get("value") if isinstance(cell, dict) else cell


#: Insights payload → the governed definition it now references (one definition, three consumers)
INSIGHTS_DEFINITIONS: dict[str, list[str]] = {
    "demand": ["ordered_units@1", "shipped_units@1", "unfulfilled_units@1", "ordered_lines@1", "customers_ordering@1"],
    "inventory": ["inventory_units@1", "inventory_value@1", "in_transit_units@1", "weeks_of_cover@1"],
    "supply": ["open_po_units@1", "open_po_value@1", "open_po_count@1", "received_units@1"],
    "suppliers": ["supplier_fill_rate@1", "supplier_late_rate@1", "short_fill_rate@1", "lead_time_p50@1", "lead_time_p90@1", "mean_late_days@1", "matched_orders@1"],
    "service": ["fill_rate@1", "shipped_units@1", "unfulfilled_units@1", "ordered_units@1"],
    "decisions": ["decision_count@1", "decision_response_count@1", "proposal_count@1"],
    "value": ["modeled_difference@1", "backtested_opportunity@1", "approved_expected_difference@1", "observed_after_action@1", "realized_value@1"],
}
