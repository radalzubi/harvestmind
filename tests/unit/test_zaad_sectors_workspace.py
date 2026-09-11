"""Sector physics through the vault: migration 017 columns -> request profiles, lot expiry, storage
states on locations and lanes, shipment weight; legacy vaults unchanged; malformed physics refused."""
from __future__ import annotations

import duckdb
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dependencies import get_conn, require_operator
from api.routers import zaad_full
from scripts.setup_db import setup_db
from scripts.zaad_network_workspace_smoke import make_network_vault
from zaad.full.workspace import build_request
from zaad.meio.workspace import build_network_request
from zaad.sectors.contracts import resolve


@pytest.fixture()
def vault():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    make_network_vault(conn, seed=7)
    return conn


def _app(vault, operator: str = "tenant_n") -> FastAPI:
    app = FastAPI()
    app.include_router(zaad_full.router)

    def conn_override():
        yield vault

    app.dependency_overrides[get_conn] = conn_override
    app.dependency_overrides[require_operator] = lambda: operator
    return app


def test_migration_adds_the_physics_columns_and_a_legacy_vault_plans_without_physics(vault):
    cols = {r[1] for r in vault.execute("PRAGMA table_info('stg_fmcg_skus')").fetchall()}
    assert {"sector", "storage_state", "age_at_receipt_days", "min_remaining_life_receipt_days", "min_remaining_life_sale_days", "weight_per_unit"} <= cols
    assert "expiry_date" in {r[1] for r in vault.execute("PRAGMA table_info('stg_fmcg_inventory')").fetchall()}
    assert "storage_states" in {r[1] for r in vault.execute("PRAGMA table_info('stg_fmcg_locations')").fetchall()}
    req, report = build_request(vault, "tenant_n", skus=["SKU-0001"], max_solve_seconds=5.)
    assert req.sector_mode is None and req.sku_physics == () and resolve(req) is None
    assert report["provenance"].get("sku.physics") in (None, "NOT_AVAILABLE")


def test_physics_columns_become_profiles_with_provenance_and_lot_expiry(vault):
    vault.execute("UPDATE stg_fmcg_skus SET sector='PRODUCE', storage_state='CHILLED', min_remaining_life_sale_days=7, age_at_receipt_days=14, physics_provenance='OPERATOR_DECLARED' WHERE sku='SKU-0001'")
    vault.execute("UPDATE stg_fmcg_inventory SET expiry_date = snapshot_date + INTERVAL 21 DAY WHERE sku='SKU-0001'")
    vault.execute("UPDATE stg_fmcg_locations SET storage_states='CHILLED,FROZEN'")
    vault.execute("UPDATE stg_fmcg_lanes SET storage_states='CHILLED'")
    req, report = build_network_request(vault, "tenant_n", skus=["SKU-0001"], max_solve_seconds=5.)
    physics = resolve(req)
    assert physics is not None and req.sector_mode == "PRODUCE"
    p = physics.sku["SKU-0001"]
    assert p.storage_state == "CHILLED" and p.minimum_remaining_life_at_sale == 1 and p.age_at_receipt_periods == 2
    assert p.provenance["minimum_remaining_life_at_sale"] == "OPERATOR_DECLARED"
    assert report["provenance"]["sku.physics"] == "CUSTOMER_PROVIDED" and report["provenance"]["stock.expiry"] == "CUSTOMER_PROVIDED"
    assert all(lot.expires_in <= 3 for lot in req.stock)            # 21 days -> 3 periods, capped by the shelf life
    assert all(set(loc.storage_states) == {"CHILLED", "FROZEN"} for loc in req.locations)
    assert all(a.storage_states == ("CHILLED",) for a in req.transfers)


def test_request_level_sector_mode_and_malformed_physics_answer_422(monkeypatch, vault):
    monkeypatch.setenv("HARVESTMIND_ENV", "pilot")
    client = TestClient(_app(vault))
    r = client.get("/api/zaad/network/request/from-workspace?skus=SKU-0001&max_solve_seconds=5&sector_mode=COMMERCIAL")
    assert r.status_code == 200 and r.json()["request"]["sector_mode"] == "COMMERCIAL"
    r = client.get("/api/zaad/network/request/from-workspace?skus=SKU-0001&max_solve_seconds=5&sector_mode=DAIRY")
    assert r.status_code == 422
    vault.execute("UPDATE stg_fmcg_skus SET sector='MEAT_SEAFOOD', storage_state='FROZEN', physics_provenance='OPERATOR_DECLARED' WHERE sku='SKU-0001'")
    vault.execute("UPDATE stg_fmcg_locations SET storage_states='CHILLED'")
    r = client.get("/api/zaad/network/request/from-workspace?skus=SKU-0001&max_solve_seconds=5&network=true")
    assert r.status_code == 422 and r.json()["detail"]["code"] == "sector_physics_invalid"
    vault.execute("UPDATE stg_fmcg_locations SET storage_states='FROZEN,CHILLED'")
    vault.execute("UPDATE stg_fmcg_skus SET min_remaining_life_sale_days=700 WHERE sku='SKU-0001'")
    r = client.get("/api/zaad/network/request/from-workspace?skus=SKU-0001&max_solve_seconds=5&network=true")
    assert r.status_code == 422 and "shelf life" in r.json()["detail"]["message"]


def test_workspace_plan_carries_the_physics_block_and_keeps_approval(monkeypatch, vault):
    monkeypatch.setenv("HARVESTMIND_ENV", "pilot")
    vault.execute("UPDATE stg_fmcg_skus SET sector='PRODUCE', min_remaining_life_sale_days=7, physics_provenance='OPERATOR_DECLARED' WHERE sku='SKU-0001'")
    client = TestClient(_app(vault))
    r = client.post("/api/zaad/network/plan/from-workspace?skus=SKU-0001&max_solve_seconds=5&network=true&shape=network")
    assert r.status_code == 200, r.text
    report = r.json()["report"]
    assert report["approval_required"] is True and r.json()["executable_purchase_order"] is False
    assert report["physics"]["sector_default"] == "PRODUCE" and report["physics"]["profiles"][0]["minimum_remaining_life_at_sale"] == 1
    assert {"physical_on_hand", "sellable_on_hand"} <= set(report["physics"]["stock"][0])


def test_payload_path_validates_physics_and_bounds(monkeypatch):
    from zaad.sectors.fixtures import build
    monkeypatch.setenv("HARVESTMIND_ENV", "dev")
    client = TestClient(_app(duckdb.connect(":memory:"), operator="p2_fixture"))
    req = build("M4_cold_chain_lane", 41001)
    payload = req.model_dump(mode="json")
    payload["max_solve_seconds"] = 5.
    r = client.post("/api/zaad/network/plan", json=payload)
    assert r.status_code == 200, r.text
    assert "physics" in r.json() and r.json()["physics"]["storage"]["lanes"]["lane_south"] == ["AMBIENT"]
    bad = dict(payload)
    bad["sku_physics"] = [{**payload["sku_physics"][0], "minimum_remaining_life_at_sale": 500}]
    r = client.post("/api/zaad/network/plan", json=bad)
    assert r.status_code == 422
    bad = dict(payload)
    bad["sku_physics"] = [{**payload["sku_physics"][0], "storage_state": "TEPID"}]
    r = client.post("/api/zaad/network/plan", json=bad)
    assert r.status_code == 422
    bad = dict(payload)
    bad["sku_physics"] = [{**payload["sku_physics"][0], "weight_per_unit": -1}]
    r = client.post("/api/zaad/network/plan", json=bad)
    assert r.status_code == 422
