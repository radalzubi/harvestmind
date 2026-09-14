"""Read-only operational projections of the operator's own vault.

Everything here answers a question the compact planning contract cannot: *what do I have, what is
coming, who supplies it, and what does the raw record actually say?* These are the surfaces behind
Inventory, Purchase Orders, Diagnostics and Data.

Three properties hold for every endpoint in this file:

  * **Authenticated and tenant-scoped.** `get_conn` yields the caller's own vault and nothing else;
    an id belonging to another workspace is simply not found here, with no metadata about it.
  * **Bounded.** Page sizes are capped and counts are ceilinged, so no request can pull a
    catalogue through the browser.
  * **Not rate limited by the planner's budget.** These are indexed reads a page makes on every
    view. Sharing the recommendation limiter would let a table scroll spend it and answer 429 for
    a lookup that costs nothing — the same reasoning that keeps job status and the directory off
    it. The configurable per-IP limiter still applies when one is set.
"""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_conn, rate_limiter, require_operator
from api.product import catalog, diagnostics, queries

router = APIRouter(prefix="/api/zaad/workspace", tags=["zaad-workspace"],
                   dependencies=[Depends(rate_limiter)])


def authenticated(operator: str | None = Depends(require_operator)) -> str:
    """Every surface here reads a workspace, so every surface needs to know whose."""
    if operator is None:
        raise HTTPException(401, "Open your workspace to read its data.")
    return operator


Operator = Annotated[str, Depends(authenticated)]


@router.get("/summary")
def summary(operator: Operator, conn=Depends(get_conn), as_of: str | None = Query(None)):
    """Counts and totals for the operating snapshot. Every figure is a count or a sum of rows."""
    return catalog.summary(conn, as_of=as_of)


@router.get("/inventory")
def inventory(
    operator: Operator, conn=Depends(get_conn),
    q: str | None = Query(None, description="matches code, description, brand or category"),
    category: str | None = None, brand: str | None = None, supplier_id: str | None = None,
    abc_class: str | None = None,
    cover: Literal["out", "under2", "under4", "over12", "unknown"] | None = Query(
        None, description="weeks of cover, computed as stock divided by average weekly demand"),
    skus: str | None = Query(None, description="comma-separated selection, e.g. the products the last plan covered"),
    sort: str = "sku", direction: Literal["asc", "desc"] = "asc",
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
):
    try:
        page = catalog.inventory_page(
            conn, search=q, category=category, brand=brand, supplier_id=supplier_id,
            abc_class=abc_class, cover=cover,
            skus=[s.strip() for s in skus.split(",") if s.strip()] if skus else None,
            sort=sort, direction=direction, limit=limit, offset=offset)
    except catalog.CatalogRefused as exc:
        raise HTTPException(400, str(exc)) from exc
    return {
        "rows": page.rows, "total": page.total, "limit": page.limit, "offset": page.offset,
        "sort": page.sort, "direction": page.direction, "snapshot_date": page.snapshot_date,
        "demand_weeks": page.demand_weeks, "served": page.served, "note": page.note,
        "sortable": sorted(catalog.INVENTORY_SORTS),
    }


@router.get("/inventory/{sku}")
def inventory_detail(sku: str, operator: Operator, conn=Depends(get_conn)):
    try:
        return catalog.sku_detail(conn, sku)
    except KeyError as exc:
        raise HTTPException(404, "That product is not in this workspace.") from exc
    except catalog.CatalogRefused as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/purchase-orders")
def purchase_orders(
    operator: Operator, conn=Depends(get_conn),
    q: str | None = None, supplier_id: str | None = None,
    state: Literal["open", "late", "received"] | None = None,
    sort: str = "po_date", direction: Literal["asc", "desc"] = "desc",
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
    as_of: str | None = Query(None, description="the date lateness is measured against"),
):
    try:
        return catalog.purchase_order_page(conn, search=q, supplier_id=supplier_id, state=state,
                                           sort=sort, direction=direction, limit=limit,
                                           offset=offset, as_of=as_of)
    except catalog.CatalogRefused as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/purchase-orders/{po_id}")
def purchase_order(po_id: str, operator: Operator, conn=Depends(get_conn)):
    try:
        return catalog.purchase_order_detail(conn, po_id)
    except KeyError as exc:
        raise HTTPException(404, "That order is not in this workspace.") from exc
    except catalog.CatalogRefused as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/suppliers")
def suppliers(
    operator: Operator, conn=Depends(get_conn), q: str | None = None,
    sort: str = "late_rate", direction: Literal["asc", "desc"] = "desc",
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
    as_of: str | None = None,
):
    try:
        return diagnostics.supplier_page(conn, search=q, sort=sort, direction=direction,
                                         limit=limit, offset=offset, as_of=as_of)
    except diagnostics.DiagnosticsRefused as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/suppliers/{supplier_id}")
def supplier(supplier_id: str, operator: Operator, conn=Depends(get_conn), as_of: str | None = None):
    try:
        return diagnostics.supplier_detail(conn, supplier_id, as_of=as_of)
    except KeyError as exc:
        raise HTTPException(404, "That supplier is not in this workspace.") from exc


@router.get("/sector")
def sector(
    operator: Operator, conn=Depends(get_conn), sector: str | None = None,
    sort: str = "supply_uncertainty", direction: Literal["asc", "desc"] = "desc",
    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
):
    """Per-product physical uncertainty for a produce or meat/seafood workspace."""
    try:
        return diagnostics.sector_page(conn, sector=sector, sort=sort, direction=direction,
                                       limit=limit, offset=offset)
    except diagnostics.DiagnosticsRefused as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/corridors")
def corridors(operator: Operator, conn=Depends(get_conn)):
    """Late arrivals grouped by the route suppliers declare. An association, never a cause."""
    return diagnostics.corridor_lateness(conn)


@router.get("/datasets")
def datasets(operator: Operator, conn=Depends(get_conn)):
    """Every dataset the explorer serves, with how many rows this workspace holds."""
    return {"datasets": queries.catalogue(conn), "max_page": queries.MAX_PAGE}


@router.get("/datasets/{dataset}")
def dataset(
    dataset: str, operator: Operator, conn=Depends(get_conn),
    q: str | None = None, sort: str | None = None,
    direction: Literal["asc", "desc"] = "asc",
    limit: int = Query(queries.DEFAULT_PAGE, ge=1, le=queries.MAX_PAGE), offset: int = Query(0, ge=0),
    where: list[str] = Query(default=[], description="column:value, column drawn from the dataset's declared filters"),
):
    filters: dict[str, str] = {}
    for clause in where:
        name, _, value = str(clause).partition(":")
        if not name or not _:
            raise HTTPException(400, "A filter is written column:value.")
        filters[name] = value
    try:
        page = queries.read_page(conn, dataset, search=q, filters=filters, sort=sort,
                                 direction=direction, limit=limit, offset=offset)
    except queries.QueryRefused as exc:
        raise HTTPException(400, str(exc)) from exc
    return {
        "dataset": page.dataset, "label": page.label, "description": page.description,
        "columns": page.columns, "rows": page.rows, "total": page.total,
        "total_is_floor": page.total_is_floor, "limit": page.limit, "offset": page.offset,
        "sort": page.sort, "direction": page.direction, "served": page.served,
    }


@router.get("/datasets/{dataset}/values/{column}")
def dataset_values(dataset: str, column: str, operator: Operator, conn=Depends(get_conn)):
    """The values a declared filter can take, so a person picks rather than types."""
    try:
        return {"values": queries.distinct_values(conn, dataset, column)}
    except queries.QueryRefused as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/search")
def search(operator: Operator, conn=Depends(get_conn), q: str = Query(..., min_length=1, max_length=120),
           limit: int = Query(8, ge=1, le=20)):
    """Products, suppliers, orders and customers by name or code. Server-side, so it holds at scale."""
    return {"results": catalog.search_everything(conn, q, limit=limit)}
