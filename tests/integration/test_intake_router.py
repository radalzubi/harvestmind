"""Integration tests for api/routers/intake.py.

Tests the full CSV upload → DuckDB round-trip through the FastAPI layer:
  POST /intake/upload/{table}  — success, missing columns, empty file
  GET  /intake/status          — row counts after upload
  POST /intake/clear/{table}   — truncation

Uses a temp DuckDB on disk with migration 010 applied.
DUCKDB_PATH env var is set to point to that temp DB.
"""

from __future__ import annotations

import io
import os
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[2]
MIGRATION_010 = ROOT / "db" / "migrations" / "010_diagnostic_staging.sql"


# ── DB fixture ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def intake_db(tmp_path_factory):
    """Temp DuckDB with staging tables from migration 010."""
    db_path = tmp_path_factory.mktemp("intakedb") / "intake_test.duckdb"
    conn = duckdb.connect(str(db_path))

    # Apply migration 010 to create staging tables
    sql = MIGRATION_010.read_text()
    for statement in sql.split(";"):
        stmt = statement.strip()
        if stmt:
            try:
                conn.execute(stmt)
            except Exception:
                pass  # COMMENT ON TABLE is not supported in all DuckDB versions

    conn.close()

    prev = os.environ.get("DUCKDB_PATH")
    os.environ["DUCKDB_PATH"] = str(db_path)
    yield str(db_path)
    if prev is None:
        os.environ.pop("DUCKDB_PATH", None)
    else:
        os.environ["DUCKDB_PATH"] = prev


@pytest.fixture(scope="module")
def client(intake_db):
    import sys
    sys.path.insert(0, str(ROOT))
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)


# ── Helper ────────────────────────────────────────────────────────────────────

def _csv_file(content: str, filename: str = "upload.csv"):
    return ("file", (filename, io.BytesIO(content.encode()), "text/csv"))


# ── Status endpoint ───────────────────────────────────────────────────────────

def test_intake_status_returns_all_tables(client):
    r = client.get("/intake/status")
    assert r.status_code == 200
    data = r.json()
    assert "tables" in data
    expected_tables = {
        "stg_products", "stg_supplier_deliveries", "stg_inventory_lots",
        "stg_buyer_orders", "stg_waste_adjustments",
    }
    assert expected_tables.issubset(set(data["tables"].keys()))


def test_intake_status_starts_empty(client):
    r = client.get("/intake/status")
    data = r.json()
    # Fresh DB — all tables should be empty
    for table_info in data["tables"].values():
        assert table_info["row_count"] == 0
    assert data["any_data_loaded"] is False
    assert data["all_tables_loaded"] is False


# ── Upload: products ──────────────────────────────────────────────────────────

PRODUCTS_CSV = """\
product_id,product_name,category,unit,default_shelf_life_days,traceability_required
P001,Tomatoes,Vegetables,kg,7,True
P002,Cucumbers,Vegetables,kg,10,True
P003,Romaine Lettuce,Leafy Greens,kg,5,True
"""


def test_upload_products_success(client):
    r = client.post(
        "/intake/upload/stg_products",
        files=[_csv_file(PRODUCTS_CSV)],
    )
    assert r.status_code == 200
    data = r.json()
    assert data["rows_inserted"] == 3
    assert data["errors"] == []


def test_upload_products_status_updated(client):
    r = client.get("/intake/status")
    data = r.json()
    assert data["tables"]["stg_products"]["row_count"] == 3
    assert data["tables"]["stg_products"]["loaded"] is True


# ── Upload: supplier deliveries ───────────────────────────────────────────────

DELIVERIES_CSV = """\
delivery_id,supplier_id,supplier_name,product_name,delivery_date,ordered_quantity,delivered_quantity,accepted_quantity,rejected_quantity,unit_cost,quality_grade,lot_id
D1,S001,Good Farms,Tomatoes,2026-05-01,500,490,485,5,1.20,A,LOT-001
D2,S002,Risky Produce,Tomatoes,2026-05-03,400,250,248,2,1.15,B,LOT-002
D3,S001,Good Farms,Cucumbers,2026-05-05,200,198,195,3,0.80,A,LOT-003
"""


def test_upload_deliveries_success(client):
    r = client.post(
        "/intake/upload/stg_supplier_deliveries",
        files=[_csv_file(DELIVERIES_CSV)],
    )
    assert r.status_code == 200
    assert r.json()["rows_inserted"] == 3
    assert r.json()["errors"] == []


# ── Upload: inventory lots ────────────────────────────────────────────────────

INVENTORY_CSV = """\
lot_id,product_id,product_name,supplier_id,quantity_on_hand,unit,arrival_date,expiration_date,committed_quantity
LOT-A,P001,Tomatoes,S001,200,kg,2026-05-01,2026-06-10,50
LOT-B,P001,Tomatoes,S002,80,kg,2026-05-10,2026-05-28,0
LOT-C,P004,Strawberries,S002,30,kg,2026-05-05,2026-05-22,0
"""


def test_upload_inventory_success(client):
    r = client.post(
        "/intake/upload/stg_inventory_lots",
        files=[_csv_file(INVENTORY_CSV)],
    )
    assert r.status_code == 200
    assert r.json()["rows_inserted"] == 3
    assert r.json()["errors"] == []


# ── Upload: buyer orders ──────────────────────────────────────────────────────

ORDERS_CSV = """\
order_id,buyer_id,buyer_name,product_name,delivery_date,requested_quantity,fulfilled_quantity,substituted_quantity,sales_price
O1,B001,Good Buyer,Tomatoes,2026-05-10,100,97,3,2.50
O2,B002,Risky Buyer,Tomatoes,2026-05-10,150,90,5,2.50
O3,B002,Risky Buyer,Tomatoes,2026-05-15,120,80,0,2.50
"""


def test_upload_orders_success(client):
    r = client.post(
        "/intake/upload/stg_buyer_orders",
        files=[_csv_file(ORDERS_CSV)],
    )
    assert r.status_code == 200
    assert r.json()["rows_inserted"] == 3
    assert r.json()["errors"] == []


# ── Upload: waste adjustments ─────────────────────────────────────────────────

WASTE_CSV = """\
adjustment_id,date,product_name,lot_id,quantity_lost,reason,estimated_value_lost
A1,2026-05-10,Strawberries,LOT-C,20,Spoilage,140.00
A2,2026-05-12,Tomatoes,,15,Overripe,37.50
"""


def test_upload_waste_success(client):
    r = client.post(
        "/intake/upload/stg_waste_adjustments",
        files=[_csv_file(WASTE_CSV)],
    )
    assert r.status_code == 200
    assert r.json()["rows_inserted"] == 2
    assert r.json()["errors"] == []


# ── Status: all tables now loaded ─────────────────────────────────────────────

def test_intake_status_all_tables_loaded(client):
    r = client.get("/intake/status")
    data = r.json()
    assert data["any_data_loaded"] is True
    assert data["all_tables_loaded"] is True


# ── Diagnostics endpoint fires after upload ───────────────────────────────────

def test_diagnostics_summary_after_upload(client):
    """Full round-trip: upload CSVs → diagnostics/summary returns real metrics."""
    r = client.get("/diagnostics/summary")
    assert r.status_code == 200
    data = r.json()
    # Waste loss from the uploaded CSVs
    assert data["waste"]["total_usd"] >= 0
    # Supplier data loaded
    assert len(data["supplier"]["suppliers"]) >= 2
    # Buyer data loaded
    assert len(data["buyer"]["buyers"]) >= 2
    # Traceability data loaded
    assert data["traceability"]["total_lots"] == 3


# ── Error cases ───────────────────────────────────────────────────────────────

def test_upload_unknown_table_returns_400(client):
    r = client.post(
        "/intake/upload/fact_orders",  # not in allowlist
        files=[_csv_file(PRODUCTS_CSV)],
    )
    assert r.status_code == 400


def test_upload_non_csv_returns_400(client):
    r = client.post(
        "/intake/upload/stg_products",
        files=[("file", ("data.xlsx", b"fake excel data", "application/vnd.ms-excel"))],
    )
    assert r.status_code == 400


def test_upload_missing_required_column_returns_error(client):
    # products CSV without product_name column
    bad_csv = "product_id,category\nP001,Vegetables\n"
    r = client.post(
        "/intake/upload/stg_products",
        files=[_csv_file(bad_csv)],
    )
    assert r.status_code == 200  # endpoint returns 200 with errors list
    data = r.json()
    assert len(data["errors"]) > 0
    assert "product_name" in data["errors"][0].lower() or "missing" in data["errors"][0].lower()


# ── Clear ─────────────────────────────────────────────────────────────────────

def test_clear_staging_table(client):
    r = client.post("/intake/clear/stg_waste_adjustments")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "cleared"


def test_clear_removes_rows(client):
    r = client.get("/intake/status")
    data = r.json()
    assert data["tables"]["stg_waste_adjustments"]["row_count"] == 0
    assert data["tables"]["stg_waste_adjustments"]["loaded"] is False


def test_clear_unknown_table_returns_400(client):
    r = client.post("/intake/clear/not_a_real_table")
    assert r.status_code == 400


# ── Load sample data ──────────────────────────────────────────────────────────
#
# Uses an isolated DB fixture so these tests are independent of the upload
# tests above (which share the module-scoped `intake_db`).

@pytest.fixture(scope="module")
def sample_client(tmp_path_factory):
    """Fresh DuckDB + TestClient for load-sample-data tests."""
    import sys
    db_path = tmp_path_factory.mktemp("sampledb") / "sample_test.duckdb"
    conn = duckdb.connect(str(db_path))
    sql = MIGRATION_010.read_text()
    for statement in sql.split(";"):
        stmt = statement.strip()
        if stmt:
            try:
                conn.execute(stmt)
            except Exception:
                pass
    conn.close()

    prev = os.environ.get("DUCKDB_PATH")
    os.environ["DUCKDB_PATH"] = str(db_path)

    sys.path.insert(0, str(ROOT))
    from fastapi.testclient import TestClient
    from api.main import app
    tc = TestClient(app)

    yield tc

    if prev is None:
        os.environ.pop("DUCKDB_PATH", None)
    else:
        os.environ["DUCKDB_PATH"] = prev


def test_load_sample_data_succeeds(sample_client):
    r = sample_client.post("/intake/load-sample-data")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "loaded"
    assert data["tables_loaded"] == 5
    assert data["total_rows"] > 0
    assert data["errors"] == []


def test_load_sample_data_row_counts(sample_client):
    """Each staging table should have rows after loading sample data."""
    r = sample_client.post("/intake/load-sample-data")
    data = r.json()
    for table in ("stg_products", "stg_supplier_deliveries", "stg_inventory_lots",
                  "stg_buyer_orders", "stg_waste_adjustments"):
        assert data["rows_by_table"][table] > 0, f"{table} has 0 rows after sample load"


def test_load_sample_data_is_idempotent(sample_client):
    """Calling load-sample-data twice should produce the same row counts."""
    r1 = sample_client.post("/intake/load-sample-data")
    r2 = sample_client.post("/intake/load-sample-data")
    assert r1.json()["total_rows"] == r2.json()["total_rows"]


def test_load_sample_data_status_reflects_loaded_tables(sample_client):
    """After loading, intake/status should report all tables loaded."""
    sample_client.post("/intake/load-sample-data")
    r = sample_client.get("/intake/status")
    data = r.json()
    assert data["all_tables_loaded"] is True
    for table_info in data["tables"].values():
        assert table_info["loaded"] is True


def test_load_sample_data_diagnostics_computes(sample_client):
    """After loading sample data, diagnostics/summary should return real numbers."""
    sample_client.post("/intake/load-sample-data")
    r = sample_client.get("/diagnostics/summary")
    assert r.status_code == 200
    data = r.json()
    # Sample data has waste events — total should be positive
    assert data["waste"]["total_usd"] > 0
    # Traceability: sample data has some lots with missing lot_ids
    assert data["traceability"]["total_lots"] > 0
