"""Shared pytest fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture
def sample_demand_df() -> pd.DataFrame:
    """Weekly demand for 2 products × 2 buyers over 52 weeks."""
    rng = np.random.default_rng(42)
    weeks = pd.date_range("2023-06-05", periods=52, freq="W-MON")
    rows = []
    for prod in ["PRD-001", "PRD-003"]:
        for buyer in ["BUY-001", "BUY-002"]:
            for week in weeks:
                rows.append({
                    "product_id": prod,
                    "buyer_id": buyer,
                    "week_start": week,
                    "qty_ordered_kg": max(0.0, float(rng.normal(200, 40))),
                })
    return pd.DataFrame(rows)


@pytest.fixture
def sample_deliveries_df() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    weeks = pd.date_range("2023-06-05", periods=52, freq="W-MON")
    rows = []
    for sup in ["SUP-001", "SUP-004"]:
        for prod in ["PRD-001", "PRD-003"]:
            for week in weeks:
                qty = float(rng.uniform(100, 500))
                rej = qty * rng.uniform(0, 0.08)
                rows.append({
                    "supplier_id": sup,
                    "product_id": prod,
                    "delivery_date": week,
                    "qty_received_kg": round(qty, 1),
                    "qty_rejected_kg": round(rej, 1),
                })
    return pd.DataFrame(rows)


@pytest.fixture
def in_memory_db():
    """DuckDB in-memory database with full schema."""
    import duckdb
    from scripts.setup_db import setup_db

    conn = duckdb.connect(":memory:")
    setup_db(conn, load_seeds=False)
    yield conn
    conn.close()
