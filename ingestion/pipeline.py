"""Data ingestion pipeline: orchestrates all data source connectors."""

from __future__ import annotations

from pathlib import Path

import duckdb


def run_ingestion_pipeline(
    conn: duckdb.DuckDBPyConnection,
    data_dir: str | Path | None = None,
    days_back: int = 30,
    verbose: bool = True,
    weather_counties: tuple[str, ...] = ("18157",),
) -> dict[str, int]:
    """Run all available ingestion connectors. Returns row counts per source.

    weather_counties: FIPS codes to fetch Open-Meteo / Drought Monitor
    data for — extend per operator as supplier locations are learned.
    """
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

    # --- Open-Meteo historical weather (keyless, deep history) ---
    try:
        from datetime import date, timedelta

        from ingestion.open_meteo_fetcher import fetch_and_store as om_fetch
        start = date.today() - timedelta(days=days_back)
        for fips in weather_counties:
            n = om_fetch(conn, county_fips=fips, start_date=start)
            counts["fact_weather_obs"] = counts.get("fact_weather_obs", 0) + n
            if verbose and n > 0:
                print(f"  Open-Meteo weather ({fips}): {n} observations")
    except Exception as e:
        if verbose:
            print(f"  Open-Meteo weather skipped: {e}")

    # --- Drought Monitor categories onto stored weather (keyless) ---
    try:
        from datetime import date, timedelta

        from ingestion.drought_monitor_fetcher import (
            fetch_and_store as usdm_fetch,
        )
        start = date.today() - timedelta(days=days_back)
        for fips in weather_counties:
            n = usdm_fetch(conn, county_fips=fips, start_date=start)
            if verbose and n > 0:
                print(f"  Drought Monitor ({fips}): {n} weeks stamped")
    except Exception as e:
        if verbose:
            print(f"  Drought Monitor skipped: {e}")

    # --- ENSO ONI index onto stored weather (keyless) ---
    try:
        from ingestion.enso_oni_fetcher import apply_to_weather as oni_apply
        n = oni_apply(conn)
        if verbose and n > 0:
            print(f"  ENSO ONI: {n} monthly values stamped")
    except Exception as e:
        if verbose:
            print(f"  ENSO ONI skipped: {e}")

    # --- USDA NASS county reference yields (key-gated) ---
    try:
        from ingestion.nass_quickstats_fetcher import (
            fetch_and_store as nass_fetch,
        )
        n = nass_fetch(conn)
        counts["fact_county_yields"] = counts.get("fact_county_yields", 0) + n
        if verbose and n > 0:
            print(f"  NASS county yields: {n} records")
    except Exception as e:
        if verbose:
            print(f"  NASS county yields skipped: {e}")

    return counts
