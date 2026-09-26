"""Diagnostics on a workspace created before later migrations added optional columns.

The NTDCO production workspace was created before migration 018 (`risk_group` on the supplier
master) and its vault was never brought forward, so Diagnostics → Suppliers failed with
``Binder Error: Referenced column "risk_group" not found`` and the page showed "Internal error".
These tests build a vault with the migrations that existed at that time, load rows shaped like that
workspace (a supplier master with ids and names only, purchase orders with an expected date, receipts)
and walk every Diagnostics read through the real router.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.product.governance import actor_from as _actor_from
from api.dependencies import get_conn, require_actor, require_operator
from api.product import diagnostics
from api.routers import zaad_workspace
from scripts.setup_db import MIGRATIONS_DIR, _exec_statements

OPERATOR = "tenant_legacy"
LAST_OLD_MIGRATION = "017"


def legacy_vault(upto: str = LAST_OLD_MIGRATION) -> duckdb.DuckDBPyConnection:
    """A vault migrated only up to `upto`, as a workspace created at that time would be."""
    conn = duckdb.connect(":memory:")
    for mf in sorted(Path(MIGRATIONS_DIR).glob("*.sql")):
        if mf.name[:3] > upto:
            break
        _exec_statements(conn, mf.read_text(), mf.name)
    return conn


def load_ntdco_shaped_rows(conn) -> None:
    conn.executemany("INSERT INTO stg_fmcg_suppliers (supplier_id, supplier_name) VALUES (?, ?)",
                     [("NT-SUP-1", "Northern Trading"), ("NT-SUP-2", "Delta Foods"), ("NT-SUP-3", "No history yet")])
    conn.executemany("INSERT INTO stg_fmcg_skus (sku, sku_name, category, supplier_id, unit_cost) VALUES (?, ?, ?, ?, ?)",
                     [("NT-001", "Rice 5kg", "Staples", "NT-SUP-1", 3.2), ("NT-002", "Oil 1L", "Staples", "NT-SUP-2", 1.1)])
    conn.executemany("INSERT INTO stg_fmcg_purchase_orders (po_id, po_date, supplier_id, sku, qty_ordered, unit_cost, expected_delivery_date) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?)",
                     [("PO-1", "2025-10-01", "NT-SUP-1", "NT-001", 1000, 3.2, "2025-10-20"),
                      ("PO-2", "2025-10-05", "NT-SUP-1", "NT-001", 500, 3.2, "2025-10-25"),
                      ("PO-3", "2025-11-01", "NT-SUP-2", "NT-002", 800, 1.1, None),
                      ("PO-4", "2025-12-10", "NT-SUP-2", "NT-002", 400, 1.1, "2025-12-20")])
    conn.executemany("INSERT INTO stg_fmcg_receipts (receipt_id, po_id, receipt_date, sku, qty_received) VALUES (?, ?, ?, ?, ?)",
                     [("R-1", "PO-1", "2025-10-24", "NT-001", 1000), ("R-2", "PO-2", "2025-10-24", "NT-001", 450),
                      ("R-3", "PO-3", "2025-11-20", "NT-002", 800)])
    conn.executemany("INSERT INTO stg_fmcg_inventory (snapshot_date, sku, location_id, on_hand) VALUES (?, ?, ?, ?)",
                     [("2025-12-28", "NT-001", "MAIN", 300), ("2025-12-28", "NT-002", "MAIN", 120)])
    conn.executemany("INSERT INTO stg_fmcg_orders (order_id, customer_id, order_date, sku, qty_ordered, qty_shipped) VALUES (?, ?, ?, ?, ?, ?)",
                     [("O-1", "C-1", "2025-12-01", "NT-001", 40, 40), ("O-2", "C-2", "2025-12-08", "NT-002", 25, 20)])


@pytest.fixture(scope="module")
def vault():
    conn = legacy_vault()
    load_ntdco_shaped_rows(conn)
    return conn


@pytest.fixture(scope="module")
def client(vault):
    app = FastAPI()
    app.include_router(zaad_workspace.router)

    def conn_override():
        yield vault

    app.dependency_overrides[get_conn] = conn_override
    app.dependency_overrides[require_operator] = lambda: OPERATOR
    # the planner routes check a capability (security review 2026-09); this client is the workspace administrator
    app.dependency_overrides[require_actor] = lambda: _actor_from({"operator_id": (lambda: OPERATOR)(), "actor_id": "admin", "name": "admin", "role": "ADMIN"})
    return TestClient(app)


def test_the_legacy_vault_really_lacks_the_later_columns(vault):
    cols = {r[1] for r in vault.execute("PRAGMA table_info('stg_fmcg_suppliers')").fetchall()}
    assert "risk_group" not in cols and "supplier_id" in cols


def test_suppliers_page_answers_the_production_request_exactly(client):
    # the request the production log recorded as a 500
    r = client.get("/api/zaad/workspace/suppliers?sort=late_rate&direction=desc&limit=50&offset=0&as_of=2025-12-29")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["served"] is True and body["total"] == 3
    by_id = {row["supplier_id"]: row for row in body["rows"]}
    assert by_id["NT-SUP-1"]["name"] == "Northern Trading"
    assert by_id["NT-SUP-1"]["risk_group"] is None and by_id["NT-SUP-1"]["origin"] is None and by_id["NT-SUP-1"]["route"] is None
    assert by_id["NT-SUP-1"]["matched_orders"] == 2
    assert by_id["NT-SUP-1"]["late_rate"] == 0.5             # PO-1 on time, PO-2 late
    assert by_id["NT-SUP-2"]["orders_with_promise"] == 0     # PO-3 carries no promise: lateness unmeasured
    assert by_id["NT-SUP-2"]["late_open_orders"] == 1        # PO-4 open past its date as of 2025-12-29
    assert by_id["NT-SUP-3"]["matched_orders"] is None       # still listed, nothing measured


@pytest.mark.parametrize("sort", sorted(diagnostics.SUPPLIER_SORTS))
def test_every_supplier_sort_works_on_the_legacy_vault(client, sort):
    assert client.get(f"/api/zaad/workspace/suppliers?sort={sort}&as_of=2025-12-29").status_code == 200


def test_supplier_search_and_paging_on_the_legacy_vault(client):
    r = client.get("/api/zaad/workspace/suppliers?q=northern&as_of=2025-12-29").json()
    assert [row["supplier_id"] for row in r["rows"]] == ["NT-SUP-1"]
    r = client.get("/api/zaad/workspace/suppliers?limit=1&offset=1&as_of=2025-12-29").json()
    assert len(r["rows"]) == 1 and r["total"] == 3


def test_supplier_detail_routes_physics_and_value_reads_answer(client):
    detail = client.get("/api/zaad/workspace/suppliers/NT-SUP-1?as_of=2025-12-29")
    assert detail.status_code == 200 and detail.json()["measured"]["supplier_id"] == "NT-SUP-1"
    assert detail.json()["lateness"]["observed"]
    assert client.get("/api/zaad/workspace/suppliers/NOBODY").status_code == 404
    routes = client.get("/api/zaad/workspace/corridors").json()
    # 013's master carries a nullable `route`; every supplier is grouped under "not declared"
    assert routes["served"] is True and all(r["route"] == "not declared" for r in routes["rows"])
    physics = client.get("/api/zaad/workspace/sector").json()
    assert physics["served"] is False and "declares a sector" in physics["note"]
    assert client.get("/api/zaad/workspace/summary?as_of=2025-12-29").status_code == 200


def test_a_vault_without_a_supplier_master_still_lists_suppliers_from_orders():
    conn = legacy_vault()
    load_ntdco_shaped_rows(conn)
    conn.execute("DROP TABLE stg_fmcg_suppliers")
    page = diagnostics.supplier_page(conn, as_of="2025-12-29")
    assert page["total"] == 2 and all(row["name"] is None for row in page["rows"])
