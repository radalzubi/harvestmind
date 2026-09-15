"""Data readiness: not whether a file exists, but whether the fields ZAAD needs are there and usable.

V1 knew that a source was uploaded. That let a workspace say "nothing needs your attention" while
every one of its 16,751 purchase-order lines carried no promised delivery date and three
diagnostics said lateness could not be measured. This module answers the real question, per
capability:

    PURCHASING            Ready
    SUPPLIER_LATENESS     Blocked — promised delivery date missing
    SUPPLIER_ROOT_CAUSE   Unavailable — dispatch / port event timestamps are not part of the upload
    PERISHABILITY         Partial — shelf life present for 62 % of products
    ...

and, per source, which fields are present, how complete each important one is, how valid, what
date range it spans, how many rows, when it was last uploaded. Every number here is counted from
the vault; nothing is inferred. A capability's status names the field that decides it, so the
path back is always the same: which source, which column, what to upload.

Quality checks (duplicates, orphan keys, impossible dates, negative quantities, extremes,
unknown products and suppliers, unmatched receipts) are classified BLOCKING, MATERIAL or
INFORMATIONAL by whether ZAAD can plan at all, plans differently, or merely notices.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from api.product.catalog import _columns, _one, has_table, site_column_usable

#: A field ZAAD reads, on a source, and what it is for. `required` sources cannot plan without it.
@dataclass(frozen=True)
class Field:
    name: str
    label: str
    required: bool = False
    #: the capabilities this field feeds; a missing optional field blocks only these
    feeds: tuple[str, ...] = ()
    kind: str = "text"   # text | number | date


@dataclass(frozen=True)
class Source:
    key: str
    table: str
    label: str
    required: bool
    fields: tuple[Field, ...]
    date_column: str | None = None
    hint: str = ""


SOURCES: tuple[Source, ...] = (
    Source("products", "stg_fmcg_skus", "Product list", True, (
        Field("sku", "Product code", True, ("PURCHASING",)),
        Field("unit_cost", "Unit cost", True, ("PURCHASING", "INVENTORY_VALUE"), "number"),
        Field("supplier_id", "Supplier", False, ("PURCHASING", "SUPPLIER_LATENESS")),
        Field("units_per_case", "Units per case", False, ("PURCHASING",), "number"),
        Field("moq_units", "Minimum order quantity", False, ("PURCHASING",), "number"),
        Field("shelf_life_days", "Shelf life (days)", False, ("PERISHABILITY",), "number"),
        Field("unit_price", "Unit price", False, ("SHORTAGE_ECONOMICS",), "number"),
    )),
    Source("customer_orders", "stg_fmcg_orders", "Customer orders", True, (
        Field("sku", "Product code", True, ("PURCHASING",)),
        Field("qty_ordered", "Quantity ordered", True, ("PURCHASING",), "number"),
        Field("order_date", "Order date", True, ("PURCHASING",), "date"),
        Field("qty_shipped", "Quantity shipped", False, ("SERVICE_HISTORY",), "number"),
        Field("location_id", "Site", False, ("MULTI_SITE",)),
        Field("customer_id", "Customer", False, ("CUSTOMER_ALLOCATION",)),
    ), "order_date"),
    Source("purchase_orders", "stg_fmcg_purchase_orders", "Purchase orders", False, (
        Field("po_id", "Order number", True, ("OPEN_PO_INTERVENTION", "SUPPLIER_LATENESS")),
        Field("sku", "Product code", True, ("OPEN_PO_INTERVENTION",)),
        Field("qty_ordered", "Quantity ordered", True, ("OPEN_PO_INTERVENTION",), "number"),
        Field("po_date", "Order date", True, ("SUPPLIER_LATENESS",), "date"),
        Field("expected_delivery_date", "Promised delivery date", False, ("SUPPLIER_LATENESS", "OPEN_PO_INTERVENTION"), "date"),
        Field("supplier_id", "Supplier", False, ("SUPPLIER_LATENESS",)),
        Field("unit_cost", "Unit cost", False, ("OPEN_PO_INTERVENTION",), "number"),
        Field("destination_id", "Destination site", False, ("MULTI_SITE",)),
    ), "po_date", "What you have on order and when it is due"),
    Source("receipts", "stg_fmcg_receipts", "Goods received", False, (
        Field("po_id", "Order number", True, ("SUPPLIER_LATENESS", "REALIZED_VALUE")),
        Field("qty_received", "Quantity received", True, ("SUPPLIER_LATENESS", "REALIZED_VALUE"), "number"),
        Field("receipt_date", "Receipt date", True, ("SUPPLIER_LATENESS", "REALIZED_VALUE"), "date"),
        Field("sku", "Product code", False, ("SUPPLIER_LATENESS",)),
    ), "receipt_date"),
    Source("inventory", "stg_fmcg_inventory", "Stock counts", False, (
        Field("sku", "Product code", True, ("INVENTORY_VALUE",)),
        Field("on_hand", "On hand", True, ("INVENTORY_VALUE",), "number"),
        Field("snapshot_date", "Count date", True, ("INVENTORY_VALUE",), "date"),
        Field("location_id", "Site", False, ("MULTI_SITE",)),
        Field("in_transit", "In transit", False, ("MULTI_SITE",), "number"),
    ), "snapshot_date"),
    Source("suppliers", "stg_fmcg_suppliers", "Supplier list", False, (
        Field("supplier_id", "Supplier", True, ("SUPPLIER_LATENESS",)),
        Field("supplier_name", "Name", False, ()),
        Field("origin_iso3", "Origin country", False, ("NETWORK",)),
        Field("route", "Route", False, ("NETWORK",)),
        Field("capacity_per_week", "Weekly capacity", False, ("PURCHASING",), "number"),
        Field("lead_time_promised_weeks", "Promised lead time", False, ("SUPPLIER_LATENESS",), "number"),
    )),
    Source("locations", "stg_fmcg_locations", "Sites", False, (
        Field("location_id", "Site", True, ("MULTI_SITE",)),
        Field("kind", "Kind", False, ("MULTI_SITE",)),
    )),
    Source("lanes", "stg_fmcg_lanes", "Transfer lanes", False, (
        Field("origin_id", "From", True, ("MULTI_SITE",)),
        Field("destination_id", "To", True, ("MULTI_SITE",)),
        Field("lead_days", "Lead (days)", False, ("MULTI_SITE",), "number"),
    )),
    Source("sources", "stg_fmcg_sources", "Alternative sources", False, (
        Field("sku", "Product code", True, ("ALTERNATIVE_SOURCING",)),
        Field("supplier_id", "Supplier", True, ("ALTERNATIVE_SOURCING",)),
        Field("unit_cost", "Unit cost", False, ("ALTERNATIVE_SOURCING",), "number"),
    )),
    Source("po_options", "stg_po_options", "Order amendment rights", False, (
        Field("po_id", "Order number", True, ("OPEN_PO_INTERVENTION",)),
        Field("action", "Right", True, ("OPEN_PO_INTERVENTION",)),
        Field("fee_per_unit", "Fee per unit", False, ("OPEN_PO_INTERVENTION",), "number"),
        Field("deadline", "Change deadline", False, ("OPEN_PO_INTERVENTION",), "date"),
    )),
    Source("customer_order_promises", "stg_atp_customer_orders", "Customer commitments", False, (
        Field("order_id", "Order", True, ("CUSTOMER_ALLOCATION",)),
        Field("sku", "Product code", True, ("CUSTOMER_ALLOCATION",)),
        Field("quantity", "Quantity", True, ("CUSTOMER_ALLOCATION",), "number"),
    )),
)

#: The fields a capability would need that the canonical upload does not carry at all.
NOT_IN_UPLOAD: dict[str, tuple[str, ...]] = {
    "SUPPLIER_ROOT_CAUSE": ("supplier dispatch date", "vessel departure", "port arrival", "customs clearance", "inland delivery"),
    "WASTE": ("waste or spoilage adjustments", "cold-chain excursions"),
}

CAPABILITIES: dict[str, str] = {
    "PURCHASING": "Purchasing recommendations",
    "INVENTORY_VALUE": "Stock value and cover",
    "SUPPLIER_LATENESS": "Supplier lateness",
    "SUPPLIER_ROOT_CAUSE": "Where a delay happened",
    "PERISHABILITY": "Shelf life and remaining life",
    "OPEN_PO_INTERVENTION": "Changing open orders",
    "MULTI_SITE": "Stock by site and transfers",
    "ALTERNATIVE_SOURCING": "Alternative suppliers",
    "CUSTOMER_ALLOCATION": "Allocating scarce supply to customers",
    "SERVICE_HISTORY": "Service measured from shipments",
    "SHORTAGE_ECONOMICS": "The cost of running short",
    "NETWORK": "The network picture",
    "REALIZED_VALUE": "Outcomes matched from receipts",
    "WASTE": "Waste and spoilage",
}


@dataclass
class FieldReadiness:
    name: str
    label: str
    required: bool
    present: bool
    coverage: float | None          # share of rows with a value, None when the column is absent
    valid: float | None             # share of present values that pass the kind's check
    feeds: tuple[str, ...]
    kind: str


@dataclass
class SourceReadiness:
    key: str
    table: str
    label: str
    required: bool
    present: bool
    rows: int
    fields: list[FieldReadiness] = field(default_factory=list)
    date_range: tuple[str | None, str | None] = (None, None)
    last_uploaded: str | None = None
    hint: str = ""


def _coverage(conn: Any, table: str, column: str, kind: str, rows: int) -> tuple[float | None, float | None]:
    if rows == 0:
        return None, None
    non_null = int(_one(conn, f'SELECT count("{column}") FROM "{table}"') or 0)  # noqa: S608  # nosec B608 - names from SOURCES; no values
    coverage = non_null / rows
    valid: float | None = None
    if non_null:
        if kind == "number":
            ok = int(_one(conn, f'SELECT count(*) FROM "{table}" WHERE TRY_CAST("{column}" AS DOUBLE) IS NOT NULL AND TRY_CAST("{column}" AS DOUBLE) >= 0') or 0)  # noqa: S608  # nosec B608 - names from SOURCES
        elif kind == "date":
            ok = int(_one(conn, f'SELECT count(*) FROM "{table}" WHERE TRY_CAST("{column}" AS DATE) IS NOT NULL AND TRY_CAST("{column}" AS DATE) BETWEEN DATE \'1990-01-01\' AND DATE \'2100-01-01\'') or 0)  # noqa: S608  # nosec B608 - names from SOURCES
        else:
            ok = int(_one(conn, f'SELECT count(*) FROM "{table}" WHERE length(trim(CAST("{column}" AS VARCHAR))) > 0') or 0)  # noqa: S608  # nosec B608 - names from SOURCES
        valid = ok / non_null
    return coverage, valid


def source_readiness(conn: Any) -> list[SourceReadiness]:
    out: list[SourceReadiness] = []
    for src in SOURCES:
        present = has_table(conn, src.table)
        columns = _columns(conn, src.table) if present else set()
        rows = int(_one(conn, f'SELECT count(*) FROM "{src.table}"') or 0) if present else 0  # noqa: S608  # nosec B608 - names from SOURCES
        item = SourceReadiness(src.key, src.table, src.label, src.required, present and rows > 0, rows, hint=src.hint)
        for f in src.fields:
            has = f.name in columns
            coverage, valid = _coverage(conn, src.table, f.name, f.kind, rows) if has else (None, None)
            item.fields.append(FieldReadiness(f.name, f.label, f.required, has, coverage, valid, f.feeds, f.kind))
        if present and rows and src.date_column and src.date_column in columns:
            lo, hi = conn.execute(f'SELECT min("{src.date_column}"), max("{src.date_column}") FROM "{src.table}"').fetchone()  # noqa: S608  # nosec B608 - names from SOURCES
            item.date_range = (str(lo)[:10] if lo else None, str(hi)[:10] if hi else None)
        stamp_col = next((c for c in ("_uploaded_at", "imported_at") if c in columns), None)
        if present and rows and stamp_col:
            stamp = _one(conn, f'SELECT max("{stamp_col}") FROM "{src.table}"')  # noqa: S608  # nosec B608 - names from SOURCES
            item.last_uploaded = str(stamp)[:19] if stamp else None
        out.append(item)
    return out


def _field(sources: list[SourceReadiness], key: str, name: str) -> FieldReadiness | None:
    for s in sources:
        if s.key == key:
            for f in s.fields:
                if f.name == name:
                    return f
    return None


def _source(sources: list[SourceReadiness], key: str) -> SourceReadiness | None:
    return next((s for s in sources if s.key == key), None)


def _pct(x: float | None) -> str:
    return "—" if x is None else f"{round(x * 100)} %"


def capability_readiness(sources: list[SourceReadiness], conn: Any | None = None) -> list[dict[str, Any]]:
    """One line per capability: READY | PARTIAL | BLOCKED | UNAVAILABLE, and the field that decides it.

    `conn` lets the site checks ask the vault whether a site column names real sites: the
    staging schema defaults it to 'MAIN', so presence alone proves nothing.
    """
    def loaded(key: str) -> bool:
        s = _source(sources, key)
        return bool(s and s.present)

    def cov(key: str, name: str) -> float | None:
        f = _field(sources, key, name)
        return f.coverage if f and f.present else None

    out: list[dict[str, Any]] = []

    def add(cap: str, status: str, reason: str, *, source: str | None = None, column: str | None = None, coverage: float | None = None):
        out.append({"capability": cap, "label": CAPABILITIES[cap], "status": status, "reason": reason,
                    "source": source, "column": column, "coverage": coverage})

    # purchasing: products + customer orders with the required fields
    if not loaded("products") or not loaded("customer_orders"):
        add("PURCHASING", "BLOCKED", "Needs the product list and customer orders.",
            source="products" if not loaded("products") else "customer_orders")
    else:
        c = cov("products", "unit_cost")
        if c is None or c < 0.999:
            add("PURCHASING", "PARTIAL" if (c or 0) > 0 else "BLOCKED",
                f"Unit cost is present for {_pct(c)} of products; a product without one cannot be priced.",
                source="products", column="unit_cost", coverage=c)
        else:
            add("PURCHASING", "READY", "Product list and customer orders carry what a plan needs.")

    c = cov("inventory", "on_hand")
    if not loaded("inventory"):
        add("INVENTORY_VALUE", "BLOCKED", "No stock count has been uploaded.", source="inventory", column="on_hand")
    else:
        add("INVENTORY_VALUE", "READY" if (c or 0) >= 0.999 else "PARTIAL",
            f"Stock counts cover {_pct(c)} of rows." if (c or 0) < 0.999 else "Stock counts are complete.",
            source="inventory", column="on_hand", coverage=c)

    if not loaded("purchase_orders") or not loaded("receipts"):
        add("SUPPLIER_LATENESS", "BLOCKED", "Needs purchase orders and goods received.",
            source="purchase_orders" if not loaded("purchase_orders") else "receipts")
    else:
        c = cov("purchase_orders", "expected_delivery_date")
        if not c:
            add("SUPPLIER_LATENESS", "BLOCKED", "Promised delivery date is missing on every purchase order, so lateness cannot be measured — only how long delivery took.",
                source="purchase_orders", column="expected_delivery_date", coverage=c or 0.0)
        elif c < 0.9:
            add("SUPPLIER_LATENESS", "PARTIAL", f"Promised delivery date is present on {_pct(c)} of purchase orders; lateness is measured on those.",
                source="purchase_orders", column="expected_delivery_date", coverage=c)
        else:
            add("SUPPLIER_LATENESS", "READY", f"Promised delivery date is present on {_pct(c)} of purchase orders.",
                source="purchase_orders", column="expected_delivery_date", coverage=c)

    add("SUPPLIER_ROOT_CAUSE", "UNAVAILABLE",
        "The upload carries the order date, the promised date and the receipt date and nothing between them: "
        + ", ".join(NOT_IN_UPLOAD["SUPPLIER_ROOT_CAUSE"]) + " are not part of it, so ZAAD can measure a delay but not say where it happened.")

    c = cov("products", "shelf_life_days")
    if not loaded("products"):
        add("PERISHABILITY", "BLOCKED", "Needs the product list.", source="products")
    elif not c:
        add("PERISHABILITY", "BLOCKED", "No product declares a shelf life.", source="products", column="shelf_life_days", coverage=0.0)
    elif c < 0.999:
        add("PERISHABILITY", "PARTIAL", f"Shelf life is present for {_pct(c)} of products.", source="products", column="shelf_life_days", coverage=c)
    else:
        add("PERISHABILITY", "READY", "Every product declares a shelf life.", source="products", column="shelf_life_days", coverage=c)

    if not loaded("purchase_orders"):
        add("OPEN_PO_INTERVENTION", "BLOCKED", "Needs purchase orders.", source="purchase_orders")
    elif not loaded("po_options"):
        add("OPEN_PO_INTERVENTION", "PARTIAL", "Open orders are read; no contractual right to change one is declared, so every order is KEEP-only.",
            source="po_options", column="action")
    else:
        add("OPEN_PO_INTERVENTION", "READY", "Open orders and declared amendment rights are present.")

    if not loaded("locations") and not loaded("inventory"):
        add("MULTI_SITE", "BLOCKED", "Needs sites and stock counts by site.", source="locations")
    else:
        inv_site = cov("inventory", "location_id")
        ord_site = cov("customer_orders", "location_id")
        po_dest = cov("purchase_orders", "destination_id")
        if conn is not None:
            if ord_site and not site_column_usable(conn, "stg_fmcg_orders", "location_id"):
                ord_site = None
            if po_dest and not site_column_usable(conn, "stg_fmcg_purchase_orders", "destination_id"):
                po_dest = None
        gaps = []
        if not inv_site:
            gaps.append("stock counts carry no site")
        if not ord_site:
            gaps.append("customer orders carry no site")
        if loaded("purchase_orders") and not po_dest:
            gaps.append("purchase orders carry no destination")
        if not gaps and loaded("lanes"):
            add("MULTI_SITE", "READY", "Sites, per-site stock, per-site demand and transfer lanes are present.")
        elif not gaps:
            add("MULTI_SITE", "PARTIAL", "Per-site stock and demand are present; no transfer lanes are declared.", source="lanes")
        else:
            add("MULTI_SITE", "PARTIAL", "Per-site figures are limited: " + "; ".join(gaps) + ".",
                source="inventory" if not inv_site else ("customer_orders" if not ord_site else "purchase_orders"),
                column="location_id" if not inv_site or not ord_site else "destination_id")

    add("ALTERNATIVE_SOURCING", "READY" if loaded("sources") else "BLOCKED",
        "Alternative sources are declared." if loaded("sources") else "No alternative source is declared, so ZAAD cannot consider moving volume between suppliers.",
        source="sources", column="supplier_id")
    add("CUSTOMER_ALLOCATION", "READY" if loaded("customer_order_promises") else "BLOCKED",
        "Customer commitments are declared." if loaded("customer_order_promises") else "No customer commitments are declared for allocation.",
        source="customer_order_promises")

    c = cov("customer_orders", "qty_shipped")
    add("SERVICE_HISTORY", "READY" if (c or 0) >= 0.9 else ("PARTIAL" if c else "BLOCKED"),
        f"Quantity shipped is present on {_pct(c)} of order lines." if c else "Customer orders carry no shipped quantity, so service history cannot be measured.",
        source="customer_orders", column="qty_shipped", coverage=c)

    c = cov("products", "unit_price")
    add("SHORTAGE_ECONOMICS", "READY" if (c or 0) >= 0.999 else ("PARTIAL" if c else "BLOCKED"),
        f"Unit price is present for {_pct(c)} of products; the cost of running short is priced on those." if c else "No product declares a selling price, so the cost of running short cannot be priced.",
        source="products", column="unit_price", coverage=c)

    if not loaded("suppliers"):
        add("NETWORK", "PARTIAL", "No supplier list: suppliers appear by code, without origin or route.", source="suppliers")
    else:
        origin = cov("suppliers", "origin_iso3")
        add("NETWORK", "READY" if (origin or 0) >= 0.999 else "PARTIAL",
            "Suppliers carry an origin and a route." if (origin or 0) >= 0.999 else f"Origin is declared for {_pct(origin)} of suppliers.",
            source="suppliers", column="origin_iso3", coverage=origin)

    add("REALIZED_VALUE", "PARTIAL" if loaded("receipts") else "BLOCKED",
        "Receipts can be matched to exported orders by reference once orders carry the exported reference; outcomes are otherwise recorded by a person."
        if loaded("receipts") else "No goods received have been uploaded, so no outcome can be matched.",
        source="receipts", column="po_id")
    add("WASTE", "UNAVAILABLE", ", ".join(NOT_IN_UPLOAD["WASTE"]).capitalize() + " are not part of the canonical upload.")
    return out


def quality_checks(conn: Any) -> list[dict[str, Any]]:
    """Counted from the vault, each with what it blocks. Nothing here changes a row."""
    out: list[dict[str, Any]] = []

    def add(check: str, severity: str, count: int, message: str, *, source: str, column: str | None = None):
        if count:
            out.append({"check": check, "severity": severity, "count": int(count), "message": message, "source": source, "column": column})

    if has_table(conn, "stg_fmcg_skus"):
        dup = _one(conn, "SELECT count(*) FROM (SELECT sku FROM stg_fmcg_skus GROUP BY sku HAVING count(*) > 1)")
        add("duplicate_products", "INFORMATIONAL", dup, "Products appearing more than once in the product list; the latest upload of each is used.", source="products", column="sku")
        neg = _one(conn, "SELECT count(*) FROM stg_fmcg_skus WHERE TRY_CAST(unit_cost AS DOUBLE) < 0")
        add("negative_unit_cost", "MATERIAL", neg, "Products with a negative unit cost.", source="products", column="unit_cost")
    if has_table(conn, "stg_fmcg_purchase_orders"):
        if has_table(conn, "stg_fmcg_skus"):
            orphan = _one(conn, "SELECT count(*) FROM stg_fmcg_purchase_orders p WHERE p.sku IS NOT NULL AND NOT EXISTS (SELECT 1 FROM stg_fmcg_skus s WHERE s.sku = p.sku)")
            add("orders_for_unknown_products", "MATERIAL", orphan, "Purchase-order lines for products not in the product list; they are not planned.", source="purchase_orders", column="sku")
        if has_table(conn, "stg_fmcg_suppliers"):
            unknown = _one(conn, "SELECT count(DISTINCT supplier_id) FROM stg_fmcg_purchase_orders p WHERE p.supplier_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM stg_fmcg_suppliers s WHERE s.supplier_id = p.supplier_id)")
            add("unknown_suppliers", "INFORMATIONAL", unknown, "Suppliers on purchase orders that are not in the supplier list; they appear by code only.", source="purchase_orders", column="supplier_id")
        neg = _one(conn, "SELECT count(*) FROM stg_fmcg_purchase_orders WHERE TRY_CAST(qty_ordered AS DOUBLE) < 0")
        add("negative_order_quantity", "MATERIAL", neg, "Purchase-order lines with a negative quantity.", source="purchase_orders", column="qty_ordered")
        extreme = _one(conn, "SELECT count(*) FROM stg_fmcg_purchase_orders WHERE TRY_CAST(qty_ordered AS DOUBLE) > 1000000")
        add("extreme_order_quantity", "MATERIAL", extreme, "Purchase-order lines over a million units — likely a unit or paste error.", source="purchase_orders", column="qty_ordered")
        dup = _one(conn, "SELECT count(*) FROM (SELECT po_id, sku FROM stg_fmcg_purchase_orders GROUP BY po_id, sku HAVING count(*) > 1)")
        add("duplicate_order_lines", "MATERIAL", dup, "The same product appears more than once on one purchase order; quantities are summed.", source="purchase_orders", column="po_id")
        if "expected_delivery_date" in _columns(conn, "stg_fmcg_purchase_orders"):
            impossible = _one(conn, "SELECT count(*) FROM stg_fmcg_purchase_orders WHERE expected_delivery_date IS NOT NULL AND expected_delivery_date < po_date")
            add("promised_before_ordered", "MATERIAL", impossible, "Purchase orders promised before they were ordered; lateness is not measured on them.", source="purchase_orders", column="expected_delivery_date")
    if has_table(conn, "stg_fmcg_receipts"):
        if has_table(conn, "stg_fmcg_purchase_orders"):
            unmatched = _one(conn, "SELECT count(*) FROM stg_fmcg_receipts r WHERE NOT EXISTS (SELECT 1 FROM stg_fmcg_purchase_orders p WHERE p.po_id = r.po_id)")
            add("unmatched_receipts", "MATERIAL", unmatched, "Receipts naming an order that is not in the purchase orders; they measure nothing.", source="receipts", column="po_id")
            early = _one(conn, """SELECT count(*) FROM stg_fmcg_receipts r JOIN (SELECT po_id, min(po_date) d FROM stg_fmcg_purchase_orders GROUP BY po_id) p
                                  ON p.po_id = r.po_id WHERE r.receipt_date < p.d""")
            add("received_before_ordered", "MATERIAL", early, "Receipts dated before the order they belong to.", source="receipts", column="receipt_date")
        neg = _one(conn, "SELECT count(*) FROM stg_fmcg_receipts WHERE TRY_CAST(qty_received AS DOUBLE) < 0")
        add("negative_receipt_quantity", "MATERIAL", neg, "Receipts with a negative quantity.", source="receipts", column="qty_received")
    if has_table(conn, "stg_fmcg_orders"):
        if has_table(conn, "stg_fmcg_skus"):
            orphan = _one(conn, "SELECT count(*) FROM stg_fmcg_orders o WHERE o.sku IS NOT NULL AND NOT EXISTS (SELECT 1 FROM stg_fmcg_skus s WHERE s.sku = o.sku)")
            add("demand_for_unknown_products", "MATERIAL", orphan, "Customer-order lines for products not in the product list; their demand is not planned.", source="customer_orders", column="sku")
        neg = _one(conn, "SELECT count(*) FROM stg_fmcg_orders WHERE TRY_CAST(qty_ordered AS DOUBLE) < 0")
        add("negative_demand", "MATERIAL", neg, "Customer-order lines with a negative quantity.", source="customer_orders", column="qty_ordered")
        if "qty_shipped" in _columns(conn, "stg_fmcg_orders"):
            over = _one(conn, "SELECT count(*) FROM stg_fmcg_orders WHERE qty_shipped IS NOT NULL AND qty_shipped > qty_ordered * 1.001")
            add("shipped_more_than_ordered", "INFORMATIONAL", over, "Customer-order lines shipped above the quantity ordered.", source="customer_orders", column="qty_shipped")
    if has_table(conn, "stg_fmcg_inventory"):
        if has_table(conn, "stg_fmcg_skus"):
            orphan = _one(conn, "SELECT count(*) FROM stg_fmcg_inventory i WHERE i.sku IS NOT NULL AND NOT EXISTS (SELECT 1 FROM stg_fmcg_skus s WHERE s.sku = i.sku)")
            add("stock_for_unknown_products", "MATERIAL", orphan, "Stock rows for products not in the product list.", source="inventory", column="sku")
        neg = _one(conn, "SELECT count(*) FROM stg_fmcg_inventory WHERE TRY_CAST(on_hand AS DOUBLE) < 0")
        add("negative_stock", "MATERIAL", neg, "Stock rows with a negative on-hand quantity.", source="inventory", column="on_hand")
    # currency consistency across the product's own tables
    for table, key in (("zaad_draft_orders", "currency"),):
        if has_table(conn, table):
            n = _one(conn, f'SELECT count(DISTINCT "{key}") FROM "{table}" WHERE "{key}" IS NOT NULL')  # noqa: S608  # nosec B608 - names are code literals
            if n and int(n) > 1:
                add("mixed_currencies", "INFORMATIONAL", int(n), "Proposals in more than one currency; each is exported in its own.", source="proposals", column="currency")
    order = {"BLOCKING": 0, "MATERIAL": 1, "INFORMATIONAL": 2}
    out.sort(key=lambda r: (order.get(r["severity"], 9), -r["count"]))
    return out


def readiness(conn: Any) -> dict[str, Any]:
    sources = source_readiness(conn)
    capabilities = capability_readiness(sources, conn)
    checks = quality_checks(conn)
    blocked = [c for c in capabilities if c["status"] == "BLOCKED" and c["capability"] in ("PURCHASING", "INVENTORY_VALUE")]
    return {
        "sources": [{
            "key": s.key, "table": s.table, "label": s.label, "required": s.required, "present": s.present, "rows": s.rows,
            "date_range": {"from": s.date_range[0], "to": s.date_range[1]}, "last_uploaded": s.last_uploaded, "hint": s.hint,
            "fields": [{"name": f.name, "label": f.label, "required": f.required, "present": f.present, "coverage": f.coverage,
                        "valid": f.valid, "feeds": list(f.feeds), "kind": f.kind} for f in s.fields],
        } for s in sources],
        "capabilities": capabilities,
        "quality": checks,
        "summary": {
            "can_plan": not blocked,
            "ready": sum(1 for c in capabilities if c["status"] == "READY"),
            "partial": sum(1 for c in capabilities if c["status"] == "PARTIAL"),
            "blocked": sum(1 for c in capabilities if c["status"] == "BLOCKED"),
            "unavailable": sum(1 for c in capabilities if c["status"] == "UNAVAILABLE"),
            "material_issues": sum(1 for q in checks if q["severity"] in ("BLOCKING", "MATERIAL")),
        },
        "provenance": "COUNTED_FROM_THE_VAULT",
    }
