"""Integration tests for the /fsma router.

A per-test isolated DuckDB is bootstrapped from the migrations and wired
into the FastAPI dependencies via dependency_overrides.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_conn, get_readonly_conn
from api.main import app


def _bootstrap(c) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    for sql in sorted((repo_root / "db" / "migrations").glob("*.sql")):
        c.execute(sql.read_text())
    c.execute(
        "INSERT INTO dim_products (product_id, crop_name, crop_category, "
        "shelf_life_days, is_ftl_item) VALUES "
        "('PRD-FTL-1','Lettuce','leafy_green', 7, TRUE), "
        "('PRD-FTL-2','Tomato', 'tomato',     10, TRUE)"
    )
    c.execute(
        "INSERT INTO dim_suppliers (supplier_id, supplier_name, supplier_type) "
        "VALUES ('SUP-A','Farm A','farm')"
    )


@pytest.fixture
def client():
    db = duckdb.connect(":memory:")
    _bootstrap(db)

    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_conn] = _override
    app.dependency_overrides[get_readonly_conn] = _override
    try:
        yield TestClient(app), db
    finally:
        app.dependency_overrides.clear()
        db.close()


# ── Coverage / FTL / report ──────────────────────────────────────────────────

def test_get_coverage(client):
    c, _ = client
    r = c.get("/fsma/coverage")
    assert r.status_code == 200
    body = r.json()
    assert "coverage_pct" in body
    assert body["status"] in ("Full", "Partial", "Minimal", "None")


def test_get_ftl_products(client):
    c, _ = client
    r = c.get("/fsma/ftl-products")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    # Both seeded FTL products should be present
    assert {row["product_id"] for row in body} >= {"PRD-FTL-1", "PRD-FTL-2"}


def test_get_report_csv_empty_returns_204(client):
    c, _ = client
    r = c.get("/fsma/report")  # default csv, no CTEs yet
    assert r.status_code == 204


def test_get_report_json_empty_returns_list(client):
    c, _ = client
    r = c.get("/fsma/report?format=json")
    assert r.status_code == 200
    assert r.json() == []


# ── Lot creation + duplicate ─────────────────────────────────────────────────

def test_create_lot_success(client):
    c, _ = client
    r = c.post("/fsma/lots/create", json={
        "traceability_lot_code": "TLC-NEW",
        "product_id": "PRD-FTL-1",
        "quantity_kg": 50.0,
        "supplier_id": "SUP-A",
        "tlc_source_reference": "Farm A · GLN-1234567890",
    })
    assert r.status_code == 201
    assert r.json()["traceability_lot_code"] == "TLC-NEW"


def test_create_lot_duplicate_returns_409(client):
    c, _ = client
    payload = {
        "traceability_lot_code": "TLC-DUP",
        "product_id": "PRD-FTL-1",
        "quantity_kg": 50.0,
        "tlc_source_reference": "Farm A",
    }
    assert c.post("/fsma/lots/create", json=payload).status_code == 201
    r = c.post("/fsma/lots/create", json=payload)
    assert r.status_code == 409


# ── CTE recording ────────────────────────────────────────────────────────────

def test_record_cte_valid(client):
    c, db = client
    # Seed a lot we can attach the CTE to
    c.post("/fsma/lots/create", json={
        "traceability_lot_code": "TLC-CTE-TEST",
        "product_id": "PRD-FTL-1",
        "quantity_kg": 30.0,
        "tlc_source_reference": "Farm A",
    })
    lot_id = db.execute(
        "SELECT lot_id FROM fact_lots WHERE traceability_lot_code = ?",
        ["TLC-CTE-TEST"],
    ).fetchone()[0]

    r = c.post("/fsma/cte/record", json={
        "lot_id": lot_id,
        "cte_type": "receiving",
        "event_timestamp": datetime.utcnow().isoformat(),
        "location_description": "Hub Dock 1",
        "business_name": "Test Hub",
        "quantity_kg": 30.0,
    })
    assert r.status_code == 201
    assert r.json()["lot_id"] == lot_id


def test_record_cte_invalid_type_422(client):
    c, db = client
    c.post("/fsma/lots/create", json={
        "traceability_lot_code": "TLC-INV-TYPE",
        "product_id": "PRD-FTL-1",
        "quantity_kg": 5.0,
        "tlc_source_reference": "Farm A",
    })
    lot_id = db.execute(
        "SELECT lot_id FROM fact_lots WHERE traceability_lot_code = ?",
        ["TLC-INV-TYPE"],
    ).fetchone()[0]

    r = c.post("/fsma/cte/record", json={
        "lot_id": lot_id,
        "cte_type": "smuggling",  # not in valid enum
        "event_timestamp": datetime.utcnow().isoformat(),
        "location_description": "Hub Dock 1",
        "business_name": "Test Hub",
    })
    assert r.status_code == 422


def test_record_cte_unknown_lot_404(client):
    c, _ = client
    r = c.post("/fsma/cte/record", json={
        "lot_id": "LOT-DOESNT-EXIST",
        "cte_type": "receiving",
        "event_timestamp": datetime.utcnow().isoformat(),
        "location_description": "Hub Dock 1",
        "business_name": "Test Hub",
    })
    assert r.status_code == 404


# ── SQL injection — query parameter is bound, not interpolated ───────────────

def test_sql_injection_in_lots_query_is_safe(client):
    c, _ = client
    payload = "'; DROP TABLE fact_lots; --"
    r = c.get(f"/fsma/lots?product_id={payload}")
    assert r.status_code == 200
    assert r.json() == []   # literal string, no rows match
