"""Generic CSV ingestor: maps flat CSV files to DuckDB tables.

Supports order history, purchase orders, deliveries, and inventory exports
from common food hub systems (Local Line, QuickBooks exports, etc.).
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

# Tables that ingest_csv is allowed to write to. Any other value is rejected
# before the SQL is constructed — prevents identifier injection through the
# `table` argument when called from automated pipelines.
ALLOWED_TABLES: frozenset[str] = frozenset({
    "stg_fmcg_skus", "stg_fmcg_orders", "stg_fmcg_purchase_orders",
    "stg_fmcg_receipts", "stg_fmcg_inventory", "stg_fmcg_promotions",
    "fact_orders",
    "fact_order_lines",
    "fact_purchase_orders",
    "fact_deliveries",
    "fact_inventory_snapshot",
    "fact_market_prices",
    "fact_weather_obs",
    "fact_yield_obs",
    "fact_waste_events",
    "fact_lots",
    "fact_cte_events",
    "dim_products",
    "dim_suppliers",
    "dim_buyers",
    "dim_locations",
    "dim_logistics_lanes",
    "dim_contracts",
    # ── Diagnostic staging tables (migration 010) ──────────────────────────
    "stg_products",
    "stg_supplier_deliveries",
    "stg_inventory_lots",
    "stg_buyer_orders",
    "stg_waste_adjustments",
})

ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".csv"})

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


COLUMN_MAPS: dict[str, dict[str, str]] = {
    "stg_fmcg_skus": {"SKU": "sku", "Item": "sku", "Item Code": "sku", "Description": "sku_name",
                      "Supplier": "supplier_id", "Cost": "unit_cost", "Unit Cost": "unit_cost",
                      "Price": "unit_price", "Units per Case": "units_per_case", "Case Pack": "units_per_case",
                      "MOQ": "moq_units", "Shelf Life (days)": "shelf_life_days"},
    "stg_fmcg_orders": {"Order ID": "order_id", "Customer": "customer_id", "Customer ID": "customer_id",
                        "Order Date": "order_date", "Requested Delivery": "requested_delivery_date",
                        "SKU": "sku", "Item": "sku", "Qty": "qty_ordered", "Quantity": "qty_ordered",
                        "Qty Ordered": "qty_ordered", "Qty Shipped": "qty_shipped", "Channel": "channel"},
    "stg_fmcg_purchase_orders": {"PO": "po_id", "PO Number": "po_id", "PO Date": "po_date",
                                 "Supplier": "supplier_id", "SKU": "sku", "Item": "sku",
                                 "Qty": "qty_ordered", "Qty Ordered": "qty_ordered", "Unit Cost": "unit_cost",
                                 "Expected Delivery": "expected_delivery_date"},
    "stg_fmcg_receipts": {"Receipt": "receipt_id", "PO": "po_id", "PO Number": "po_id",
                          "Receipt Date": "receipt_date", "Received Date": "receipt_date",
                          "SKU": "sku", "Qty Received": "qty_received", "Received": "qty_received",
                          "Qty Rejected": "qty_rejected"},
    "stg_fmcg_inventory": {"Date": "snapshot_date", "Snapshot Date": "snapshot_date", "SKU": "sku",
                           "Location": "location_id", "Warehouse": "location_id", "On Hand": "on_hand",
                           "In Transit": "in_transit"},
    "stg_fmcg_promotions": {"SKU": "sku", "Week": "week_start", "Week Start": "week_start",
                            "Uplift": "uplift", "Multiplier": "uplift"},
    "orders": {
        "Order ID": "order_id",
        "Buyer": "buyer_id",
        "Order Date": "order_date",
        "Week Start": "week_start",
        "Status": "status",
    },
    "order_lines": {
        "Line ID": "line_id",
        "Order ID": "order_id",
        "Product": "product_id",
        "Qty Ordered (kg)": "qty_ordered_kg",
        "Qty Delivered (kg)": "qty_delivered_kg",
        "Price/kg": "price_per_kg",
    },
    "deliveries": {
        "Delivery ID": "delivery_id",
        "Supplier": "supplier_id",
        "Product": "product_id",
        "Delivery Date": "delivery_date",
        "Qty Received (kg)": "qty_received_kg",
        "Qty Rejected (kg)": "qty_rejected_kg",
        "Rejection Reason": "rejection_reason",
    },
    # ── Diagnostic staging table column maps (migration 010) ───────────────
    # Column names in these maps are common human-readable aliases that
    # operators may use; the values are the staging-table column names.
    "stg_products": {
        "Product ID": "product_id",
        "Product Name": "product_name",
        "Category": "category",
        "Unit": "unit",
        "Shelf Life (days)": "default_shelf_life_days",
        "Default Shelf Life Days": "default_shelf_life_days",
        "Traceability Required": "traceability_required",
        "FTL Item": "traceability_required",
    },
    "stg_supplier_deliveries": {
        "Delivery ID": "delivery_id",
        "Supplier ID": "supplier_id",
        "Supplier Name": "supplier_name",
        "Product ID": "product_id",
        "Product Name": "product_name",
        "Delivery Date": "delivery_date",
        "Ordered Quantity": "ordered_quantity",
        "Delivered Quantity": "delivered_quantity",
        "Accepted Quantity": "accepted_quantity",
        "Rejected Quantity": "rejected_quantity",
        "Unit Cost": "unit_cost",
        "Quality Grade": "quality_grade",
        "Lot ID": "lot_id",
    },
    "stg_inventory_lots": {
        "Lot ID": "lot_id",
        "Product ID": "product_id",
        "Product Name": "product_name",
        "Supplier ID": "supplier_id",
        "Quantity On Hand": "quantity_on_hand",
        "Qty On Hand": "quantity_on_hand",
        "Unit": "unit",
        "Arrival Date": "arrival_date",
        "Expiration Date": "expiration_date",
        "Expiry Date": "expiration_date",
        "Warehouse Location": "warehouse_location",
        "Location": "warehouse_location",
        "Quality Grade": "quality_grade",
        "Committed Quantity": "committed_quantity",
        "Qty Committed": "committed_quantity",
    },
    "stg_buyer_orders": {
        "Order ID": "order_id",
        "Buyer ID": "buyer_id",
        "Buyer Name": "buyer_name",
        "Product ID": "product_id",
        "Product Name": "product_name",
        "Order Date": "order_date",
        "Delivery Date": "delivery_date",
        "Requested Quantity": "requested_quantity",
        "Qty Requested": "requested_quantity",
        "Fulfilled Quantity": "fulfilled_quantity",
        "Qty Fulfilled": "fulfilled_quantity",
        "Qty Delivered": "fulfilled_quantity",
        "Substituted Quantity": "substituted_quantity",
        "Sales Price": "sales_price",
        "Price/kg": "sales_price",
        "Required Quality Grade": "required_quality_grade",
        "Grade": "required_quality_grade",
    },
    "stg_waste_adjustments": {
        "Adjustment ID": "adjustment_id",
        "Date": "date",
        "Event Date": "date",
        "Product ID": "product_id",
        "Product Name": "product_name",
        "Lot ID": "lot_id",
        "Quantity Lost": "quantity_lost",
        "Qty Lost": "quantity_lost",
        "Reason": "reason",
        "Reason Code": "reason",
        "Estimated Value Lost": "estimated_value_lost",
        "Value Lost ($)": "estimated_value_lost",
    },
}


def ingest_csv(
    path: str | Path,
    table: str,
    conn,
    column_map: dict[str, str] | None = None,
    date_cols: list[str] | None = None,
    if_exists: str = "ignore",  # 'ignore' (INSERT OR IGNORE) or 'replace'
) -> int:
    """Load a CSV file into a DuckDB table. Returns rows inserted.

    Security
    --------
    - ``table`` must be in :data:`ALLOWED_TABLES`. SQL identifiers cannot be
      bound via DuckDB parameters, so we allowlist instead of interpolating
      arbitrary user input.
    - ``path`` must exist, be a regular file, and end in ``.csv``.
    - ``if_exists`` must be ``"ignore"`` or ``"replace"``.
    """
    # ── validate `table` (used in raw SQL — must be safe) ───────────────
    if table not in ALLOWED_TABLES:
        raise ValueError(
            f"table {table!r} is not in the ingestion allowlist. "
            f"Allowed: {sorted(ALLOWED_TABLES)}"
        )
    # Defence in depth: even allowlisted entries must be plain identifiers.
    if not _IDENT_RE.match(table):
        raise ValueError(f"table {table!r} is not a valid SQL identifier")

    # ── validate `path` ──────────────────────────────────────────────────
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CSV file not found: {p}")
    if not p.is_file():
        raise ValueError(f"CSV path is not a regular file: {p}")
    if p.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"unsupported file extension {p.suffix!r}; expected one of "
            f"{sorted(ALLOWED_EXTENSIONS)}"
        )

    if if_exists not in ("ignore", "replace", "append"):
        raise ValueError(
            f"if_exists must be 'ignore', 'replace', or 'append', got {if_exists!r}"
        )

    # ── read + transform ────────────────────────────────────────────────
    try:
        df = pd.read_csv(p)
    except pd.errors.EmptyDataError:
        return 0  # well-formed empty file → nothing to insert

    # Apply column mapping
    if column_map is None:
        column_map = COLUMN_MAPS.get(table, {})
    if column_map:
        df = df.rename(columns=column_map)

    # Parse date columns
    if date_cols:
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col]).dt.date

    n = len(df)
    if n == 0:
        return 0

    if if_exists == "replace":
        conn.execute(f"DELETE FROM {table}")  # noqa: S608  table is allowlisted  # nosec B608 - table allowlisted

    if if_exists == "ignore":
        # Position-based insert — requires UNIQUE/PK constraints on the table.
        # SELECT * passes all DataFrame columns by position; DuckDB raises if
        # column counts mismatch, which is the correct behaviour for normalized tables.
        conn.execute(f"INSERT OR IGNORE INTO {table} SELECT * FROM df")  # noqa: S608  # nosec B608 - table allowlisted
    else:
        # For "append" and "replace" (after DELETE): use explicit column names so
        # that schema columns with DEFAULT values (e.g. imported_at) are not
        # required in the CSV and receive their defaults automatically.
        cols = ", ".join(f'"{c}"' for c in df.columns)
        conn.execute(f'INSERT INTO {table} ({cols}) SELECT {cols} FROM df')  # noqa: S608  # nosec B608 - table allowlisted
    return n


def ingest_directory(
    directory: str | Path,
    table_map: dict[str, str],
    conn,
    pattern: str = "*.csv",
) -> dict[str, int]:
    """Ingest all CSV files matching table_map {filename_prefix: table_name}."""
    counts: dict[str, int] = {}
    dir_path = Path(directory)
    for csv_file in dir_path.glob(pattern):
        stem = csv_file.stem.lower()
        for prefix, table in table_map.items():
            if stem.startswith(prefix.lower()):
                n = ingest_csv(csv_file, table, conn)
                counts[table] = counts.get(table, 0) + n
                break
    return counts
