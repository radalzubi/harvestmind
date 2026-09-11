"""Sourcing portfolio through the vault (migration 018): declared source options -> request sources and
the sourcing block; legacy vaults and the flag-less path unchanged; malformed declarations refused."""
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


@pytest.fixture()
def vault():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    make_network_vault(conn, seed=7)
    return conn


def _first_sku_and_supplier(conn) -> tuple[str, str]:
    sku, sid = conn.execute("SELECT sku, supplier_id FROM stg_fmcg_purchase_orders WHERE supplier_id IS NOT NULL ORDER BY sku, supplier_id LIMIT 1").fetchone()
    return str(sku), str(sid)


def _declare(conn, sku: str, primary: str, *, alt_min_share: float = .2, primary_incumbent: float = .7, alt_incumbent: float = .3, alt_cost: float | None = None):
    conn.execute("INSERT INTO stg_fmcg_sources (sku, supplier_id, incumbent_share, provenance) VALUES (?, ?, ?, 'OPERATOR_DECLARED')", [sku, primary, primary_incumbent])
    conn.execute("INSERT INTO stg_fmcg_sources (sku, supplier_id, approved, unit_cost, freight_per_unit, moq_units, capacity_per_week, lead_time_promised_weeks, "
                 "minimum_share, incumbent_share, switching_cost, provenance) VALUES (?, 'ALT1', TRUE, ?, 0.15, 24, 900, 2, ?, ?, 350, 'OPERATOR_DECLARED')",
                 [sku, alt_cost, alt_min_share, alt_incumbent])
    conn.execute("INSERT INTO stg_fmcg_suppliers (supplier_id, supplier_name, risk_group, risk_group_kind, risk_group_provenance) VALUES ('ALT1', 'Alternate one', 'plant_9', 'PLANT', 'PHYSICAL_DEPENDENCY')")
    conn.execute("UPDATE stg_fmcg_suppliers SET risk_group = 'plant_9', risk_group_kind = 'PLANT', risk_group_provenance = 'PHYSICAL_DEPENDENCY' WHERE supplier_id = ?", [primary])


def _app(vault, operator: str = "tenant_n") -> FastAPI:
    app = FastAPI()
    app.include_router(zaad_full.router)

    def conn_override():
        yield vault

    app.dependency_overrides[get_conn] = conn_override
    app.dependency_overrides[require_operator] = lambda: operator
    return app


def test_migration_adds_the_source_table_and_the_flagless_path_is_unchanged(vault):
    tables = {r[0] for r in vault.execute("SHOW TABLES").fetchall()}
    assert "stg_fmcg_sources" in tables
    cols = {r[1] for r in vault.execute("PRAGMA table_info('stg_fmcg_suppliers')").fetchall()}
    assert {"risk_group", "risk_group_kind", "risk_group_provenance", "switching_cost"} <= cols
    sku, primary = _first_sku_and_supplier(vault)
    _declare(vault, sku, primary)
    req, build = build_request(vault, "tenant_n", skus=[sku], max_solve_seconds=5.)
    assert req.sourcing is None and len(req.sources) == 1 and build["sourcing"]["requested"] is False


def test_declared_source_options_become_sources_and_the_block(vault):
    sku, primary = _first_sku_and_supplier(vault)
    _declare(vault, sku, primary)
    req, build = build_request(vault, "tenant_n", skus=[sku], max_solve_seconds=5., sourcing=True)
    assert len(req.sources) == 2 and req.sourcing is not None
    alt = next(s for s in req.sources if s.supplier == "ALT1")
    assert alt.approved and alt.minimum == 24 and alt.capacity_by_period[0] == 900 and alt.lead_days == 14 and alt.freight_per_unit == .15
    block = req.sourcing
    assert [c.minimum_share for c in block.share_constraints] == [.2]
    assert sorted(r.share for r in block.incumbent_shares) == [.3, .7]
    assert [c.cost for c in block.switching_costs] == [350.]
    assert len(block.risk_groups) == 1 and set(block.risk_groups[0].members) == {s.id for s in req.sources} and block.risk_groups[0].provenance == "PHYSICAL_DEPENDENCY"
    assert build["sourcing"]["alternate_sources"] == 1 and build["sourcing"]["block"]["risk_groups"] == 1
    assert build["provenance"][f"source.{sku}.ALT1.unit_price"] in ("CONFIGURED_ASSUMPTION", "INFERRED_FROM_HISTORY")


def test_vault_without_migration_018_builds_the_frozen_request_with_a_warning(vault):
    vault.execute("DROP TABLE stg_fmcg_sources")
    sku, _ = _first_sku_and_supplier(vault)
    req, build = build_request(vault, "tenant_n", skus=[sku], max_solve_seconds=5., sourcing=True)
    assert req.sourcing is None and len(req.sources) == 1
    assert any("migration 018" in w for w in build["warnings"]) and build["sourcing"]["source_table_present"] is False


def test_network_adapter_keeps_alternates_at_the_primary_destination(vault):
    sku, primary = _first_sku_and_supplier(vault)
    _declare(vault, sku, primary)
    req, build = build_network_request(vault, "tenant_n", skus=[sku], max_solve_seconds=5., sourcing=True)
    dests = {s.destination for s in req.sources}
    assert len(req.sources) == 2 and len(dests) == 1
    assert all(r.destination in dests for r in req.sourcing.incumbent_shares) and all(c.destination in dests for c in req.sourcing.share_constraints)


def test_inconsistent_declarations_are_refused_and_the_api_reports_them(vault):
    sku, primary = _first_sku_and_supplier(vault)
    _declare(vault, sku, primary, alt_min_share=.9, alt_incumbent=.3)   # the incumbent mix does not meet the declared minimum share
    with pytest.raises(ValueError, match="does not meet"):
        build_request(vault, "tenant_n", skus=[sku], max_solve_seconds=5., sourcing=True)
    client = TestClient(_app(vault))
    r = client.get("/api/zaad/network/request/from-workspace", params={"skus": sku, "sourcing": "true", "max_solve_seconds": 5})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "sourcing_invalid"


def test_api_workspace_plan_carries_the_sourcing_block(vault):
    sku, primary = _first_sku_and_supplier(vault)
    _declare(vault, sku, primary)
    client = TestClient(_app(vault))
    r = client.get("/api/zaad/network/request/from-workspace", params={"skus": sku, "sourcing": "true", "max_solve_seconds": 5})
    assert r.status_code == 200 and r.json()["request"]["sourcing"] is not None and len(r.json()["request"]["sources"]) == 2
    r = client.post("/api/zaad/network/plan/from-workspace", params={"skus": sku, "sourcing": "true", "max_solve_seconds": 5, "shape": "network"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["executable_purchase_order"] is False and body["report"]["approval_required"] is True
    blk = body["report"]["sourcing"]
    assert blk["pairs"] and {o["source"] for o in blk["pairs"][0]["options"]} == {f"src_{sku}", f"src_{sku}__ALT1"}
    assert blk["risk_groups"][0]["id"] == "plant_9"


def test_interactive_sourcing_bounds_answer_413_before_any_model(vault):
    from zaad.meio.fixtures_p2 import p2_request
    p = p2_request(max_solve_seconds=5).model_dump(mode="json")
    p["operator_id"] = "tenant_n"
    a = next(s for s in p["sources"] if s["id"] == "src_A")
    for i in range(9):
        p["sources"].append({**a, "id": f"src_x{i}", "supplier": f"supplier_x{i}", "route": [f"supplier_x{i}", "central"]})
    p["sourcing"] = {"incumbent_shares": [{"sku": "A", "destination": "central", "source": "src_A", "share": 1., "provenance": "OPERATOR_DECLARED"}]}
    client = TestClient(_app(vault))
    r = client.post("/api/zaad/network/plan", json=p)
    assert r.status_code == 413 and "sourcing bounds" in r.text
    p["sources"] = p["sources"][:2]
    p["sourcing"]["risk_groups"] = [{"id": "g", "kind": "PLANT", "members": ["src_A", "src_A"], "provenance": "OPERATOR_DECLARED"}]
    r = client.post("/api/zaad/network/plan", json=p)
    assert r.status_code == 422
