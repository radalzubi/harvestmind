"""Integration test: schema setup and seed data load."""

import pytest
import duckdb

from scripts.setup_db import setup_db


def test_schema_creates_all_tables():
    conn = duckdb.connect(":memory:")
    setup_db(conn, load_seeds=False)

    expected_tables = {
        "dim_products", "dim_suppliers", "dim_locations", "dim_buyers",
        "fact_orders", "fact_order_lines", "fact_purchase_orders", "dim_contracts",
        "fact_deliveries", "fact_inventory_snapshot", "fact_waste_events", "dim_logistics_lanes",
        "fact_market_prices", "fact_spot_purchases", "fact_weather_obs", "fact_yield_obs",
        "fact_lots", "fact_cte_events",
        "planning_scenarios", "planning_commitments", "planning_recommendations",
        "optimization_run_log",
    }

    existing = set(
        row[0] for row in conn.execute("SHOW TABLES").fetchall()
    )
    missing = expected_tables - existing
    assert not missing, f"Missing tables: {missing}"
    conn.close()


def test_seeds_load_correctly():
    conn = duckdb.connect(":memory:")
    setup_db(conn, load_seeds=True)

    n_products = conn.execute("SELECT COUNT(*) FROM dim_products").fetchone()[0]
    n_suppliers = conn.execute("SELECT COUNT(*) FROM dim_suppliers").fetchone()[0]
    n_buyers = conn.execute("SELECT COUNT(*) FROM dim_buyers").fetchone()[0]

    assert n_products >= 10
    assert n_suppliers >= 6
    assert n_buyers >= 5
    conn.close()
