"""V2: location-aware inventory and capability-based data readiness.

A figure under a site's name is that site's figure. What the vault cannot fill for one site is
null with a stated reason, never the all-sites total wearing a site label. Readiness is per
capability and names the field that decides it, counted from the vault.
"""
from __future__ import annotations

import duckdb
import pytest

from api.product import catalog, readiness
from scripts.setup_db import setup_db
from tests.integration.test_operating_product_api import _client


@pytest.fixture(scope="module")
def vault():
    from scripts.zaad_network_workspace_smoke import make_network_vault
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    make_network_vault(conn, seed=11)
    return conn


@pytest.fixture(scope="module")
def sku(vault):
    return vault.execute("SELECT sku FROM stg_fmcg_inventory GROUP BY sku ORDER BY sum(on_hand) DESC LIMIT 1").fetchone()[0]


def test_sites_are_listed_with_their_declared_kind(vault):
    sites = {s["id"]: s for s in catalog.locations(vault)}
    assert set(sites) == {"DC", "NORTH", "SOUTH"}
    assert sites["DC"]["kind"] == "central_dc" and sites["NORTH"]["kind"] == "branch"
    assert all(s["products"] > 0 for s in sites.values())


def test_a_site_page_shows_that_sites_stock_and_the_sites_sum_to_the_total(vault, sku):
    every = catalog.inventory_page(vault, skus=[sku], limit=1).rows[0]
    by_site = {loc: catalog.inventory_page(vault, skus=[sku], limit=1, location=loc).rows[0]
               for loc in ("DC", "NORTH", "SOUTH")}
    assert every["sites"] == 3
    for loc, row in by_site.items():
        assert row["sites"] == 1
        assert row["on_hand"] < every["on_hand"], f"{loc} must show its own stock, not the total"
    assert abs(sum(r["on_hand"] for r in by_site.values()) - every["on_hand"]) < 1e-6


def test_inbound_follows_the_orders_destination_and_transfers_follow_theirs(vault, sku):
    every = catalog.inventory_page(vault, skus=[sku], limit=1).rows[0]
    dc = catalog.inventory_page(vault, skus=[sku], limit=1, location="DC").rows[0]
    north = catalog.inventory_page(vault, skus=[sku], limit=1, location="NORTH").rows[0]
    # every purchase order in this vault is delivered to the DC
    assert dc["inbound_units"] == every["inbound_units"]
    assert north["inbound_units"] is None, "no purchase order is due at a branch, and nothing pretends one is"
    assert every["transfer_units"] is None, "across all sites a transfer is a move, not an arrival"


def test_demand_and_cover_are_the_sites_own(vault, sku):
    every = catalog.inventory_page(vault, skus=[sku], limit=1).rows[0]
    dc = catalog.inventory_page(vault, skus=[sku], limit=1, location="DC").rows[0]
    north = catalog.inventory_page(vault, skus=[sku], limit=1, location="NORTH").rows[0]
    south = catalog.inventory_page(vault, skus=[sku], limit=1, location="SOUTH").rows[0]
    # customer orders name the branches; the DC serves no customer directly
    assert dc["weekly_demand"] is None and dc["cover_weeks"] is None
    assert north["weekly_demand"] is not None and south["weekly_demand"] is not None
    assert abs(north["weekly_demand"] + south["weekly_demand"] - every["weekly_demand"]) < 1e-6
    assert north["cover_weeks"] == pytest.approx(north["on_hand"] / north["weekly_demand"])


def test_a_site_column_that_only_carries_the_schema_default_is_not_declared():
    from scripts.zaad_network_workspace_smoke import make_network_vault
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    make_network_vault(conn, seed=3)
    conn.execute("UPDATE stg_fmcg_orders SET location_id = 'MAIN'")
    assert not catalog.site_column_usable(conn, "stg_fmcg_orders", "location_id")
    page = catalog.inventory_page(conn, limit=1, location="NORTH")
    assert page.rows[0]["weekly_demand"] is None
    assert any("customer orders carry no site" in n for n in page.location_notes)
    caps = {c["capability"]: c for c in readiness.readiness(conn)["capabilities"]}
    assert caps["MULTI_SITE"]["status"] == "PARTIAL" and "customer orders carry no site" in caps["MULTI_SITE"]["reason"]


def test_an_unknown_site_is_an_empty_page_not_the_total(vault):
    page = catalog.inventory_page(vault, limit=5, location="NOWHERE")
    assert page.location == "NOWHERE"
    assert all(r["on_hand"] is None for r in page.rows)


def test_sku_detail_reconciles_the_total_with_the_site_positions(vault, sku):
    detail = catalog.sku_detail(vault, sku)
    rec = detail["reconciliation"]
    assert rec["agree"] is True
    assert rec["sites_on_latest_snapshot"] == 3 and rec["sites_with_older_rows"] == []
    assert rec["sum_of_sites"] == pytest.approx(rec["all_sites_total"])


def test_sku_detail_states_a_stale_site_row_instead_of_hiding_it(sku):
    from scripts.zaad_network_workspace_smoke import make_network_vault
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    make_network_vault(conn, seed=11)
    # SOUTH's row for this product was last counted a week before the others
    conn.execute("UPDATE stg_fmcg_inventory SET snapshot_date = snapshot_date - INTERVAL 7 DAY WHERE sku = ? AND location_id = 'SOUTH'", [sku])
    rec = catalog.sku_detail(conn, sku)["reconciliation"]
    assert rec["agree"] is False and rec["sites_with_older_rows"] == ["SOUTH"]
    assert "SOUTH" in rec["note"]


def test_inventory_route_carries_the_site_and_its_notes(vault):
    client = _client(vault)
    got = client.get("/api/zaad/workspace/inventory", params={"location": "NORTH", "limit": 3}).json()
    assert got["location"] == "NORTH" and got["rows"]
    assert got["location_notes"] == []
    assert client.get("/api/zaad/workspace/locations").json()["locations"][0]["id"] == "DC"
    assert client.get("/api/zaad/workspace/inventory", params={"location": "x" * 201}).status_code == 422


def test_readiness_is_per_capability_and_names_the_deciding_field(vault):
    got = _client(vault).get("/api/zaad/workspace/readiness").json()
    caps = {c["capability"]: c for c in got["capabilities"]}
    assert caps["PURCHASING"]["status"] == "READY"
    # this fixture carries no promised date at all: lateness is BLOCKED and says which column
    assert caps["SUPPLIER_LATENESS"]["status"] == "BLOCKED"
    assert caps["SUPPLIER_LATENESS"]["column"] == "expected_delivery_date"
    assert caps["SUPPLIER_ROOT_CAUSE"]["status"] == "UNAVAILABLE"
    assert caps["MULTI_SITE"]["status"] == "READY"
    assert caps["ALTERNATIVE_SOURCING"]["status"] == "BLOCKED"
    srcs = {s["key"]: s for s in got["sources"]}
    po = {f["name"]: f for f in srcs["purchase_orders"]["fields"]}
    assert po["expected_delivery_date"]["present"] is True and po["expected_delivery_date"]["coverage"] == 0.0
    assert po["po_id"]["coverage"] == 1.0 and po["po_id"]["valid"] == 1.0
    assert srcs["purchase_orders"]["date_range"]["from"] < srcs["purchase_orders"]["date_range"]["to"]
    assert got["summary"]["can_plan"] is True
    assert got["provenance"] == "COUNTED_FROM_THE_VAULT"


def test_readiness_becomes_partial_when_the_field_is_partly_filled(vault):
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    from scripts.zaad_network_workspace_smoke import make_network_vault
    make_network_vault(conn, seed=5)
    conn.execute("UPDATE stg_fmcg_purchase_orders SET expected_delivery_date = po_date + INTERVAL 14 DAY WHERE abs(hash(po_id)) % 2 = 0")
    caps = {c["capability"]: c for c in readiness.readiness(conn)["capabilities"]}
    assert caps["SUPPLIER_LATENESS"]["status"] == "PARTIAL"
    assert 0.3 < caps["SUPPLIER_LATENESS"]["coverage"] < 0.7


def test_quality_checks_count_what_would_change_a_plan():
    from scripts.zaad_network_workspace_smoke import make_network_vault
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    make_network_vault(conn, seed=5)
    conn.execute("INSERT INTO stg_fmcg_purchase_orders (po_id, sku, qty_ordered, po_date, supplier_id) VALUES ('PO-GHOST', 'NOT-A-SKU', 10, DATE '2025-01-01', 'S1')")
    conn.execute("INSERT INTO stg_fmcg_purchase_orders (po_id, sku, qty_ordered, po_date, supplier_id) SELECT 'PO-NEG', sku, -5, DATE '2025-01-01', 'S1' FROM stg_fmcg_skus LIMIT 1")
    conn.execute("INSERT INTO stg_fmcg_receipts (po_id, sku, qty_received, receipt_date) VALUES ('PO-NOBODY', NULL, 3, DATE '2025-01-02')")
    checks = {q["check"]: q for q in readiness.quality_checks(conn)}
    assert checks["orders_for_unknown_products"]["count"] == 1 and checks["orders_for_unknown_products"]["severity"] == "MATERIAL"
    assert checks["negative_order_quantity"]["count"] == 1
    assert checks["unmatched_receipts"]["count"] >= 1
    summary = readiness.readiness(conn)["summary"]
    assert summary["material_issues"] >= 3


def test_an_empty_workspace_is_blocked_not_broken():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    got = readiness.readiness(conn)
    caps = {c["capability"]: c["status"] for c in got["capabilities"]}
    assert caps["PURCHASING"] == "BLOCKED" and got["summary"]["can_plan"] is False
    assert catalog.locations(conn) == []
