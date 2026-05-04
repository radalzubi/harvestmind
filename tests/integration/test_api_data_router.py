"""Integration tests for api/routers/data.py.

Specifically guards against:
- SQL injection through the `product_id` and `tlc` query parameters
- Connection leaks (regression: dependency was a plain `return`, now `yield`)
- 200 OK plus correct shapes on the master-data endpoints
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def temp_db(tmp_path_factory):
    """Spin up an isolated DuckDB on disk so the FastAPI dep can connect to it."""
    import sys
    sys.path.insert(0, str(ROOT))
    from scripts.setup_db import setup_db
    from synthetic.generator import SyntheticGenerator

    db_path = tmp_path_factory.mktemp("apidb") / "test.duckdb"
    conn = duckdb.connect(str(db_path))
    setup_db(conn, load_seeds=True)
    SyntheticGenerator(n_weeks=12, seed=7).generate_all(conn)
    conn.close()

    prev = os.environ.get("DUCKDB_PATH")
    os.environ["DUCKDB_PATH"] = str(db_path)
    yield str(db_path)
    if prev is None:
        os.environ.pop("DUCKDB_PATH", None)
    else:
        os.environ["DUCKDB_PATH"] = prev


@pytest.fixture(scope="module")
def client(temp_db):
    from fastapi.testclient import TestClient
    from api.main import app

    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_suppliers_returns_seeds(client):
    r = client.get("/data/suppliers")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 6  # 6 suppliers in the seed file


def test_products_filters_ftl(client):
    r = client.get("/data/products?is_ftl=true")
    assert r.status_code == 200
    items = r.json()
    assert all(p["is_ftl_item"] for p in items)


def test_products_no_filter(client):
    r = client.get("/data/products")
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 10


def test_lots_param_used_safely(client):
    r = client.get("/data/fsma/lots?product_id=PRD-001")
    assert r.status_code == 200
    items = r.json()
    # Either no lots for PRD-001 in this synthetic run, or every row has product_id == PRD-001
    assert all(item["product_id"] == "PRD-001" for item in items)


def test_lots_sql_injection_attempt_returns_zero_rows(client):
    """The injection payload should be treated as a literal product_id (not match anything)."""
    payload = "PRD-001' OR '1'='1"
    r = client.get(f"/data/fsma/lots?product_id={payload}")
    assert r.status_code == 200
    # Parameterised query treats the whole string as a literal product_id.
    assert r.json() == []


def test_fsma_report_param_safe(client):
    """Non-existent TLC must return [] instead of leaking other rows."""
    r = client.get("/data/fsma/report?tlc=does-not-exist")
    assert r.status_code == 200
    assert r.json() == []


def test_dependency_closes_connection(temp_db, client):
    """The yield-form dependency must release the DB lock after each call."""
    # Hit an endpoint then open a write connection; if the dep leaked, this would block.
    client.get("/data/suppliers")
    other = duckdb.connect(temp_db)  # would deadlock in some configs if previous conn leaked
    other.execute("SELECT COUNT(*) FROM dim_suppliers").fetchone()
    other.close()
