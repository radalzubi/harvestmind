"""Data ingestion pipeline: orchestrates all data source connectors."""

from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path

import duckdb


def run_ingestion_pipeline(
    conn: duckdb.DuckDBPyConnection,
    data_dir: str | Path | None = None,
    days_back: int = 30,
    verbose: bool = True,
) -> dict[str, int]:
    """Run all available ingestion connectors. Returns row counts per source."""
    counts: dict[str, int] = {}

    # --- CSV directory ingestion ---
    if data_dir is not None:
        from ingestion.csv_ingestor import ingest_directory
        csv_counts = ingest_directory(
            directory=data_dir,
            table_map={
                "orders": "fact_orders",
                "order_lines": "fact_order_lines",
                "deliveries": "fact_deliveries",
                "purchase_orders": "fact_purchase_orders",
            },
            conn=conn,
        )
        counts.update(csv_counts)
        if verbose and csv_counts:
            print(f"  CSV ingestion: {csv_counts}")

    # --- USDA AMS prices ---
    try:
        from ingestion.usda_ams_connector import fetch_and_store
        n = fetch_and_store(conn, days_back=days_back)
        counts["fact_market_prices"] = counts.get("fact_market_prices", 0) + n
        if verbose and n > 0:
            print(f"  USDA AMS: {n} price records")
    except Exception as e:
        if verbose:
            print(f"  USDA AMS skipped: {e}")

    # --- NOAA weather ---
    try:
        from ingestion.noaa_weather_fetcher import fetch_and_store as wx_fetch
        n = wx_fetch(conn, days_back=days_back)
        counts["fact_weather_obs"] = counts.get("fact_weather_obs", 0) + n
        if verbose and n > 0:
            print(f"  NOAA weather: {n} observations")
    except Exception as e:
        if verbose:
            print(f"  NOAA weather skipped: {e}")

    return counts
