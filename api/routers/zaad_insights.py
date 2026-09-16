"""Insights: bounded, tenant-scoped, server-side aggregations of the operator's records and the
latest completed plan. Nothing here starts a solve.

Every endpoint takes the same filters (`bucket`, `start`, `end`, `sku`, `category`, `brand`,
`customer`, `location`, `supplier`), returns a payload sized for a chart rather than a table dump,
and carries a `provenance` block — data, metric, numerator, denominator, filters, coverage, last
updated, and the plan it read if any. `get_conn` yields the caller's own vault; the plan lookup is
filtered by the caller's operator id; identifiers in filters bind as parameters and are never
interpolated.
"""
from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_conn, rate_limiter, require_operator
from api.product import insights

router = APIRouter(prefix="/api/zaad/insights", tags=["zaad-insights"], dependencies=[Depends(rate_limiter)])


def authenticated(operator: str | None = Depends(require_operator)) -> str:
    if operator is None:
        raise HTTPException(401, "Open your workspace to read its data.")
    return operator


Operator = Annotated[str, Depends(authenticated)]


def scope(bucket: str = Query("week"), start: str | None = Query(None), end: str | None = Query(None),
          sku: str | None = Query(None), category: str | None = Query(None), brand: str | None = Query(None),
          customer: str | None = Query(None), location: str | None = Query(None), supplier: str | None = Query(None)) -> insights.Scope:
    try:
        return insights.scope_from(bucket=bucket, start=start, end=end, sku=sku, category=category, brand=brand,
                                   customer=customer, location=location, supplier=supplier)
    except insights.InsightsRefused as exc:
        raise HTTPException(422, {"code": "insights_scope_invalid", "message": str(exc)}) from exc


Filters = Annotated[insights.Scope, Depends(scope)]


@router.get("/summary")
def summary(operator: Operator, filters: Filters, conn=Depends(get_conn)):
    """The headline of every tab: the latest plan and whether the data moved since, demand over the
    last twelve weeks, the inventory position, open supply, and what was decided."""
    plan = insights.latest_plan(conn, operator)
    return insights.overview(conn, filters, operator, plan)


@router.get("/plan")
def plan(operator: Operator, conn=Depends(get_conn)):
    """The latest completed workspace plan as Insights reads it: identity, dates, staleness, scope."""
    return insights.plan_summary(insights.latest_plan(conn, operator))


@router.get("/demand")
def demand(operator: Operator, filters: Filters, conn=Depends(get_conn)):
    """OBSERVED CUSTOMER ORDERS per period (never called demand), with shipped and unfulfilled where recorded."""
    return insights.demand(conn, filters, insights.latest_plan(conn, operator))


@router.get("/demand/period")
def demand_period(operator: Operator, filters: Filters, conn=Depends(get_conn), period: str = Query(..., description="a date inside the bucket to open")):
    """One period opened: products, customers, sites, changes against the period before, the stock
    and inbound behind the products involved, and the latest plan's decisions that touch them."""
    try:
        when = date.fromisoformat(period[:10])
    except ValueError as exc:
        raise HTTPException(422, {"code": "insights_scope_invalid", "message": "period must be a date (YYYY-MM-DD)."}) from exc
    return insights.demand_period(conn, filters, when, insights.latest_plan(conn, operator))


@router.get("/inventory")
def inventory(operator: Operator, filters: Filters, conn=Depends(get_conn)):
    """Inventory over time from the uploaded snapshots, by site and category, with cover and inbound."""
    return insights.inventory(conn, filters, insights.latest_plan(conn, operator))


@router.get("/supply")
def supply(operator: Operator, filters: Filters, conn=Depends(get_conn)):
    """Open purchase orders by expected arrival, receipts per period, aging, by supplier and destination."""
    return insights.supply(conn, filters, insights.latest_plan(conn, operator))


@router.get("/suppliers")
def suppliers(operator: Operator, filters: Filters, conn=Depends(get_conn)):
    """Fill, lead time and lateness per supplier with their denominators; exposure, share, rights, alternatives."""
    return insights.suppliers(conn, filters, operator, insights.latest_plan(conn, operator))


@router.get("/service")
def service(operator: Operator, filters: Filters, conn=Depends(get_conn)):
    """Ordered, shipped, unfulfilled and service level by customer and declared class; the plan's allocation block."""
    return insights.service(conn, filters, operator, insights.latest_plan(conn, operator))


@router.get("/decisions")
def decisions(operator: Operator, conn=Depends(get_conn)):
    """The latest plan's verdicts by verb, and what people did with them."""
    return insights.decisions(conn, operator, insights.latest_plan(conn, operator))


@router.get("/value")
def value(operator: Operator, conn=Depends(get_conn)):
    """Five value registers, each its own number with its own basis, never combined."""
    return insights.value(conn, operator, insights.latest_plan(conn, operator))


@router.get("/connectivity")
def connectivity(operator: Operator, conn=Depends(get_conn)):
    """Every released engine family: source, API, visualization, drilldown, status."""
    return insights.connectivity(conn, operator, insights.latest_plan(conn, operator))
