"""Generic CSV ingestor: maps flat CSV files to DuckDB tables.

Supports order history, purchase orders, deliveries, and inventory exports
from common food hub systems (Local Line, QuickBooks exports, etc.).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


COLUMN_MAPS: dict[str, dict[str, str]] = {
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
}


def ingest_csv(
    path: str | Path,
    table: str,
    conn,
    column_map: dict[str, str] | None = None,
    date_cols: list[str] | None = None,
    if_exists: str = "ignore",  # 'ignore' (INSERT OR IGNORE) or 'replace'
) -> int:
    """Load a CSV file into a DuckDB table. Returns rows inserted."""
    df = pd.read_csv(path)

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

    if if_exists not in ("ignore", "replace"):
        raise ValueError(f"if_exists must be 'ignore' or 'replace', got {if_exists!r}")
    if if_exists == "replace":
        conn.execute(f"DELETE FROM {table}")

    # Let duckdb errors propagate — silently falling back to a different INSERT
    # form would mask real schema/parser problems.
    conn.execute(f"INSERT OR IGNORE INTO {table} SELECT * FROM df")
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
