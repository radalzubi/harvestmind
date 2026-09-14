"""The data explorer's safety model, and the paging it shares with every other table.

The product lets an operator read the records ZAAD actually holds. That is a real need — a row
count is not evidence — and it is also the single most dangerous thing in this release, because it
is a query surface over a tenant's own database. So the rule here is narrow and absolute:

  * **Only names from this file reach SQL.** Dataset, column, sort column and direction are looked
    up in the tables below; a name that is not there is a 400 before anything is executed. No
    string from a request is ever concatenated into a statement.
  * **Only values are bound.** Search text and filter values travel as DuckDB parameters.
  * **Every answer is bounded.** Page size is capped, and the row count is capped too, so a
    50,000-row table cannot be pulled through the browser by asking nicely.
  * **Nothing is writable.** This module reads. Writes live in `drafts.py`, which touches only the
    product's own tables and never a staging table.

A dataset that a workspace has not uploaded is an empty dataset, not an error: a vault created
before a migration simply has no such table.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

MAX_PAGE = 200
DEFAULT_PAGE = 50
# A page count over this is reported as "more than", not counted exactly: counting every row of a
# very large table on every keystroke costs more than the number is worth.
COUNT_CEILING = 100_000

ColumnKind = Literal["text", "number", "date", "timestamp"]


@dataclass(frozen=True)
class Column:
    name: str
    label: str
    kind: ColumnKind = "text"
    #: shown by default in a narrow table; the rest are available through column visibility
    primary: bool = False


@dataclass(frozen=True)
class Dataset:
    key: str
    table: str
    label: str
    description: str
    columns: tuple[Column, ...]
    #: columns a free-text search matches against (text columns only)
    search: tuple[str, ...] = ()
    #: columns that may be filtered on exactly
    filters: tuple[str, ...] = ()
    default_sort: str = ""
    default_dir: Literal["asc", "desc"] = "asc"
    #: lineage columns are real, useful for audit, and noisy; they are available, never default
    hidden: tuple[str, ...] = field(default=("_upload_session_id", "_uploaded_at", "_source_file", "_operator_id"))

    def column(self, name: str) -> Column | None:
        return next((c for c in self.columns if c.name == name), None)


def _lineage() -> tuple[Column, ...]:
    return (
        Column("_source_file", "Source file"),
        Column("_uploaded_at", "Uploaded at", "timestamp"),
        Column("_upload_session_id", "Upload session"),
    )


DATASETS: dict[str, Dataset] = {
    "products": Dataset(
        key="products", table="stg_fmcg_skus", label="Products",
        description="The product master: pack structure, economics and the supplier each product is bought from.",
        columns=(
            Column("sku", "SKU", "text", True),
            Column("sku_name", "Description", "text", True),
            Column("brand", "Brand", "text", True),
            Column("category", "Category", "text", True),
            Column("sub_category", "Sub-category"),
            Column("supplier_id", "Supplier", "text", True),
            Column("unit_cost", "Unit cost", "number", True),
            Column("unit_price", "Unit price", "number"),
            Column("units_per_case", "Units per case", "number"),
            Column("cases_per_layer", "Cases per layer", "number"),
            Column("layers_per_pallet", "Layers per pallet", "number"),
            Column("order_multiple", "Order multiple"),
            Column("moq_units", "MOQ (units)", "number"),
            Column("shelf_life_days", "Shelf life (days)", "number"),
            Column("abc_class", "ABC class"),
            *_lineage(),
        ),
        search=("sku", "sku_name", "brand", "category", "sub_category", "supplier_id"),
        filters=("category", "brand", "sub_category", "supplier_id", "abc_class"),
        default_sort="sku",
    ),
    "inventory": Dataset(
        key="inventory", table="stg_fmcg_inventory", label="Inventory snapshots",
        description="Every stock snapshot uploaded, per product and site, in eaches.",
        columns=(
            Column("snapshot_date", "Snapshot date", "date", True),
            Column("sku", "SKU", "text", True),
            Column("location_id", "Site", "text", True),
            Column("on_hand", "On hand", "number", True),
            Column("in_transit", "In transit", "number", True),
            *_lineage(),
        ),
        search=("sku", "location_id"),
        filters=("location_id", "snapshot_date"),
        default_sort="snapshot_date", default_dir="desc",
    ),
    "purchase_orders": Dataset(
        key="purchase_orders", table="stg_fmcg_purchase_orders", label="Purchase orders",
        description="Purchase orders as uploaded from your system. Read-only evidence: proposed changes are stored separately.",
        columns=(
            Column("po_id", "PO", "text", True),
            Column("po_date", "Ordered", "date", True),
            Column("supplier_id", "Supplier", "text", True),
            Column("sku", "SKU", "text", True),
            Column("qty_ordered", "Quantity", "number", True),
            Column("unit_cost", "Unit cost", "number", True),
            Column("expected_delivery_date", "Expected", "date", True),
            Column("destination_id", "Destination"),
            *_lineage(),
        ),
        search=("po_id", "supplier_id", "sku"),
        filters=("supplier_id", "destination_id"),
        default_sort="po_date", default_dir="desc",
    ),
    "receipts": Dataset(
        key="receipts", table="stg_fmcg_receipts", label="Receipts",
        description="What actually arrived against each purchase order. Fill rate and observed lead time are measured from these.",
        columns=(
            Column("receipt_date", "Received", "date", True),
            Column("po_id", "PO", "text", True),
            Column("sku", "SKU", "text", True),
            Column("qty_received", "Quantity received", "number", True),
            Column("qty_rejected", "Rejected", "number", True),
            Column("receipt_id", "Receipt"),
            *_lineage(),
        ),
        search=("po_id", "sku", "receipt_id"),
        filters=("sku",),
        default_sort="receipt_date", default_dir="desc",
    ),
    "customer_orders": Dataset(
        key="customer_orders", table="stg_fmcg_orders", label="Customer orders",
        description="Customer order lines. A shipped quantity below the ordered quantity is a recorded shortfall.",
        columns=(
            Column("order_date", "Order date", "date", True),
            Column("order_id", "Order", "text", True),
            Column("customer_id", "Customer", "text", True),
            Column("sku", "SKU", "text", True),
            Column("qty_ordered", "Quantity ordered", "number", True),
            Column("qty_shipped", "Quantity shipped", "number", True),
            Column("requested_delivery_date", "Requested delivery", "date"),
            Column("channel", "Channel"),
            Column("location_id", "Site"),
            *_lineage(),
        ),
        search=("order_id", "customer_id", "sku"),
        filters=("customer_id", "channel", "location_id"),
        default_sort="order_date", default_dir="desc",
    ),
    "suppliers": Dataset(
        key="suppliers", table="stg_fmcg_suppliers", label="Suppliers",
        description="The supplier master, including declared origin, route and shared risk group.",
        columns=(
            Column("supplier_id", "Supplier", "text", True),
            Column("supplier_name", "Name", "text", True),
            Column("origin_iso3", "Origin", "text", True),
            Column("route", "Route", "text", True),
            Column("lead_time_promised_weeks", "Promised lead (weeks)", "number", True),
            Column("capacity_per_week", "Capacity per week", "number", True),
            Column("risk_group", "Shared risk group"),
            Column("risk_group_kind", "Risk group kind"),
            Column("switching_cost", "Switching cost", "number"),
            *_lineage(),
        ),
        search=("supplier_id", "supplier_name", "origin_iso3", "route"),
        filters=("origin_iso3", "route", "risk_group"),
        default_sort="supplier_id",
    ),
    "locations": Dataset(
        key="locations", table="stg_fmcg_locations", label="Sites",
        description="Warehouses, distribution centres and branches the network is planned over.",
        columns=(
            Column("location_id", "Site", "text", True),
            Column("kind", "Kind", "text", True),
            Column("capacity_units", "Capacity (units)", "number", True),
            Column("holding_annual", "Holding rate (annual)", "number"),
        ),
        search=("location_id", "kind"),
        filters=("kind",),
        default_sort="location_id",
    ),
    "sources": Dataset(
        key="sources", table="stg_fmcg_sources", label="Alternative sources",
        description="Approved product × supplier source options beyond the primary supplier, with their declared economics and contractual shares.",
        columns=(
            Column("sku", "SKU", "text", True),
            Column("supplier_id", "Supplier", "text", True),
            Column("approved", "Approved", "text", True),
            Column("compliance", "Compliance", "text", True),
            Column("unit_cost", "Unit cost", "number", True),
            Column("lead_time_promised_weeks", "Promised lead (weeks)", "number", True),
            Column("capacity_per_week", "Capacity per week", "number"),
            Column("moq_units", "MOQ (units)", "number"),
            Column("units_per_case", "Units per case", "number"),
            Column("freight_per_unit", "Freight per unit", "number"),
            Column("handling_per_unit", "Handling per unit", "number"),
            Column("minimum_share", "Minimum share", "number"),
            Column("maximum_share", "Maximum share", "number"),
            Column("incumbent_share", "Current share", "number"),
            Column("switching_cost", "Switching cost", "number"),
            Column("provenance", "Provenance"),
            *_lineage(),
        ),
        search=("sku", "supplier_id"),
        filters=("supplier_id", "approved", "compliance"),
        default_sort="sku",
    ),
    "transfers": Dataset(
        key="transfers", table="stg_fmcg_transfers", label="Transfers",
        description="Stock movements between your own sites, historical and open.",
        columns=(
            Column("dispatch_date", "Dispatched", "date", True),
            Column("transfer_id", "Transfer", "text", True),
            Column("origin_id", "From", "text", True),
            Column("destination_id", "To", "text", True),
            Column("sku", "SKU", "text", True),
            Column("qty", "Quantity", "number", True),
            Column("expected_arrival_date", "Expected", "date"),
            Column("received_date", "Received", "date"),
            Column("lane_id", "Lane"),
        ),
        search=("transfer_id", "sku", "origin_id", "destination_id"),
        filters=("origin_id", "destination_id"),
        default_sort="dispatch_date", default_dir="desc",
    ),
    "lanes": Dataset(
        key="lanes", table="stg_fmcg_lanes", label="Transfer lanes",
        description="Declared lanes between your sites and their physics.",
        columns=(
            Column("lane_id", "Lane", "text", True),
            Column("origin_id", "From", "text", True),
            Column("destination_id", "To", "text", True),
            Column("sku", "SKU"),
            Column("lead_days", "Lead (days)", "number", True),
            Column("cost_per_unit", "Cost per unit", "number", True),
            Column("capacity_per_week", "Capacity per week", "number"),
            Column("approved", "Approved", "text"),
        ),
        search=("lane_id", "origin_id", "destination_id"),
        filters=("origin_id", "destination_id"),
        default_sort="lane_id",
    ),
    "po_options": Dataset(
        key="po_options", table="stg_po_options", label="Order amendment rights",
        description="Declared contractual rights to change an open order. ZAAD never infers one of these.",
        columns=(
            Column("po_id", "PO", "text", True),
            Column("option_id", "Option", "text", True),
            Column("action", "Action", "text", True),
            Column("due_offset_periods", "New arrival period", "number", True),
            Column("fee_per_unit", "Fee per unit", "number", True),
            Column("credit_per_unit", "Credit per unit", "number"),
            Column("max_quantity", "Maximum quantity", "number"),
            Column("deadline", "Change deadline", "timestamp", True),
            Column("contract_reference", "Contract"),
            Column("provenance", "Provenance"),
        ),
        search=("po_id", "option_id", "contract_reference"),
        filters=("action", "provenance"),
        default_sort="po_id",
    ),
    "customer_order_promises": Dataset(
        key="customer_order_promises", table="stg_atp_customer_orders", label="Customer commitments",
        description="Customer orders declared for availability and allocation.",
        columns=(
            Column("order_id", "Order", "text", True),
            Column("customer_id", "Customer", "text", True),
            Column("sku", "SKU", "text", True),
            Column("quantity", "Quantity", "number", True),
            Column("requested_period", "Requested period", "number", True),
            Column("service_class", "Service class", "text", True),
        ),
        search=("order_id", "customer_id", "sku"),
        filters=("customer_id", "service_class"),
        default_sort="order_id",
    ),
}


class QueryRefused(ValueError):
    """A name in the request is not in the allowlist. Never carries the offending SQL."""


@dataclass(frozen=True)
class Page:
    rows: list[dict[str, Any]]
    total: int
    #: True when `total` is the ceiling rather than the real count
    total_is_floor: bool
    limit: int
    offset: int
    columns: list[dict[str, Any]]
    dataset: str
    label: str
    description: str
    sort: str
    direction: str
    served: bool


def _columns_for(ds: Dataset, present: set[str]) -> list[Column]:
    """Declared columns the vault actually has, in declared order.

    A vault created before a later migration has fewer columns than the dataset declares. Selecting
    a column that is not there would fail the whole query; leaving it out shows what exists.
    """
    return [c for c in ds.columns if c.name in present]


def _table_columns(conn: Any, table: str) -> set[str]:
    try:
        return {row[1] for row in conn.execute(f"PRAGMA table_info('{table}')").fetchall()}  # noqa: S608
    except Exception:  # noqa: BLE001 - absent table: an empty dataset, not an error
        return set()


def read_page(
    conn: Any,
    dataset: str,
    *,
    search: str | None = None,
    filters: dict[str, str] | None = None,
    sort: str | None = None,
    direction: str = "asc",
    limit: int = DEFAULT_PAGE,
    offset: int = 0,
) -> Page:
    """One page of one dataset. Every identifier below comes from `DATASETS`, never from the caller."""
    ds = DATASETS.get(dataset)
    if ds is None:
        raise QueryRefused(f"Unknown dataset {dataset!r}")
    limit = max(1, min(int(limit), MAX_PAGE))
    offset = max(0, int(offset))
    direction_sql = "DESC" if str(direction).lower() == "desc" else "ASC"

    present = _table_columns(conn, ds.table)
    columns = _columns_for(ds, present)
    if not columns:
        return Page([], 0, False, limit, offset, [], ds.key, ds.label, ds.description,
                    ds.default_sort, direction_sql.lower(), served=False)

    sort_column = sort if sort and ds.column(sort) and sort in present else (
        ds.default_sort if ds.default_sort in present else columns[0].name)
    if sort and sort != sort_column and (ds.column(sort) is None):
        raise QueryRefused(f"{dataset}: cannot sort on {sort!r}")
    if not sort:
        direction_sql = "DESC" if ds.default_dir == "desc" else "ASC"

    where: list[str] = []
    params: list[Any] = []
    for name, value in (filters or {}).items():
        if name not in ds.filters:
            raise QueryRefused(f"{dataset}: cannot filter on {name!r}")
        if name not in present:
            continue
        where.append(f'CAST("{name}" AS VARCHAR) = ?')
        params.append(str(value))
    if search and search.strip():
        searchable = [c for c in ds.search if c in present]
        if searchable:
            needle = f"%{search.strip()}%"
            where.append("(" + " OR ".join(f'CAST("{c}" AS VARCHAR) ILIKE ?' for c in searchable) + ")")
            params.extend([needle] * len(searchable))
    clause = f" WHERE {' AND '.join(where)}" if where else ""

    selected = ", ".join(f'"{c.name}"' for c in columns)
    # nosec B608 - every identifier interpolated here is a literal from DATASETS above; values bind
    sql = (f'SELECT {selected} FROM "{ds.table}"{clause} '  # noqa: S608
           f'ORDER BY "{sort_column}" {direction_sql} NULLS LAST LIMIT ? OFFSET ?')  # nosec B608 - identifiers come from DATASETS; values bind
    cursor = conn.execute(sql, [*params, limit, offset])
    names = [c[0] for c in cursor.description]
    rows = [dict(zip(names, row)) for row in cursor.fetchall()]

    counted = conn.execute(
        f'SELECT count(*) FROM (SELECT 1 FROM "{ds.table}"{clause} LIMIT {COUNT_CEILING + 1})',  # noqa: S608  # nosec B608 - identifiers come from DATASETS; values bind
        params).fetchone()
    total = int(counted[0]) if counted else 0
    return Page(rows, min(total, COUNT_CEILING), total > COUNT_CEILING, limit, offset,
                [{"name": c.name, "label": c.label, "kind": c.kind, "primary": c.primary} for c in columns],
                ds.key, ds.label, ds.description, sort_column, direction_sql.lower(), served=True)


def catalogue(conn: Any) -> list[dict[str, Any]]:
    """Every dataset, with how many rows the vault holds. An absent table reports zero, not an error."""
    out: list[dict[str, Any]] = []
    for ds in DATASETS.values():
        present = _table_columns(conn, ds.table)
        rows: int | None = None
        if present:
            try:
                got = conn.execute(f'SELECT count(*) FROM "{ds.table}"').fetchone()  # noqa: S608  # nosec B608 - identifiers come from DATASETS; values bind
                rows = int(got[0]) if got else 0
            except Exception:  # noqa: BLE001
                rows = None
        out.append({
            "key": ds.key, "label": ds.label, "table": ds.table, "description": ds.description,
            "rows": rows, "available": bool(present),
            "filters": [c for c in ds.filters if c in present],
        })
    return out


def distinct_values(conn: Any, dataset: str, column: str, limit: int = 200) -> list[str]:
    """The values a filter can take. Only a declared filter column, only from the allowlist."""
    ds = DATASETS.get(dataset)
    if ds is None:
        raise QueryRefused(f"Unknown dataset {dataset!r}")
    if column not in ds.filters:
        raise QueryRefused(f"{dataset}: {column!r} is not a filter")
    if column not in _table_columns(conn, ds.table):
        return []
    rows = conn.execute(
        f'SELECT DISTINCT CAST("{column}" AS VARCHAR) AS v FROM "{ds.table}" '  # noqa: S608
        f'WHERE "{column}" IS NOT NULL ORDER BY v LIMIT ?', [max(1, min(limit, 500))]).fetchall()  # nosec B608 - identifiers come from DATASETS; values bind
    return [str(r[0]) for r in rows]
