"""Integration test: synthetic data generation into in-memory DB."""

import pytest
import duckdb

from scripts.setup_db import setup_db
from synthetic.generator import SyntheticGenerator


@pytest.fixture
def db_with_seeds():
    conn = duckdb.connect(":memory:")
    setup_db(conn, load_seeds=True)
    yield conn
    conn.close()


def test_generator_produces_data(db_with_seeds):
    gen = SyntheticGenerator(n_weeks=8, seed=42)
    counts = gen.generate_all(db_with_seeds)

    assert counts["fact_orders"] > 0
    assert counts["fact_order_lines"] > 0
    assert counts["fact_deliveries"] > 0
    assert counts["fact_yield_obs"] > 0
    assert counts["fact_weather_obs"] == 8  # one per week
    assert counts["fact_market_prices"] > 0


def test_generator_no_duplicate_primary_keys(db_with_seeds):
    gen = SyntheticGenerator(n_weeks=8, seed=42)
    gen.generate_all(db_with_seeds)

    # Running again should not raise on OR IGNORE
    gen2 = SyntheticGenerator(n_weeks=8, seed=42)
    gen2.generate_all(db_with_seeds)  # should not raise

    n_orders = db_with_seeds.execute("SELECT COUNT(*) FROM fact_orders").fetchone()[0]
    assert n_orders > 0


def test_fsma_lots_reference_valid_products(db_with_seeds):
    gen = SyntheticGenerator(n_weeks=8, seed=42)
    gen.generate_all(db_with_seeds)

    orphans = db_with_seeds.execute(
        "SELECT COUNT(*) FROM fact_lots l "
        "LEFT JOIN dim_products p ON l.product_id = p.product_id "
        "WHERE p.product_id IS NULL"
    ).fetchone()[0]
    assert orphans == 0
