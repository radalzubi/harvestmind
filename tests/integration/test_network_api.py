"""P2 network surface of the canonical API: the workspace endpoints build and plan a declared
network, the interactive bounds refuse oversized networks, an unpriced reverse lane pair is refused,
and the single-location path is unchanged."""
from __future__ import annotations

import duckdb
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dependencies import get_conn, require_operator
from api.routers import zaad_full
from scripts.setup_db import setup_db
from zaad.meio.fixtures_p2 import p2_request


@pytest.fixture(scope="module")
def vault():
    from scripts.zaad_network_workspace_smoke import make_network_vault
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
    # the planner routes check a capability (security review 2026-09); this client is the workspace administrator
    from api.dependencies import require_actor
    from api.product.governance import actor_from
    app.dependency_overrides[require_actor] = lambda: actor_from({"operator_id": operator, "actor_id": operator, "name": operator, "role": "ADMIN"})
    return app


def test_workspace_request_builds_the_network_when_asked_and_the_single_node_otherwise(monkeypatch, vault):
    monkeypatch.setenv("HARVESTMIND_ENV", "pilot")
    client = TestClient(_app(vault))
    single = client.get("/api/zaad/network/request/from-workspace?skus=SKU-0001&max_solve_seconds=5")
    assert single.status_code == 200 and len(single.json()["request"]["locations"]) == 1 and not single.json()["request"]["transfers"]
    net = client.get("/api/zaad/network/request/from-workspace?skus=SKU-0001&max_solve_seconds=5&network=true")
    assert net.status_code == 200, net.text
    body = net.json()
    assert len(body["request"]["locations"]) == 3 and len(body["request"]["transfers"]) == 2 and body["request"]["incumbent_rule"] == "network:rop"
    assert body["build"]["network"]["mode"] == "network" and body["build"]["compact"]["lanes"] == 2


def test_workspace_plan_runs_the_network_layer_and_keeps_approval(monkeypatch, vault):
    monkeypatch.setenv("HARVESTMIND_ENV", "pilot")
    client = TestClient(_app(vault))
    r = client.post("/api/zaad/network/plan/from-workspace?skus=SKU-0001&max_solve_seconds=5&network=true")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mode_run"] == "canonical_p2_network" and body["approval_required"] is True and body["executable_purchase_order"] is False
    assert isinstance(body["transfers"], list) and body["network"]["explanations"]["verdict"]
    assert set(body["network_service"]) == {"svc_SKU-0001@NORTH", "svc_SKU-0001@SOUTH"}
    full = client.post("/api/zaad/network/plan/from-workspace?skus=SKU-0001&max_solve_seconds=5&network=true&shape=network")
    assert full.status_code == 200 and "network" in full.json()["report"] and full.json()["executable_purchase_order"] is False


def test_plan_endpoint_adds_the_network_block_for_a_network_request_and_refuses_free_loops(monkeypatch):
    monkeypatch.setenv("HARVESTMIND_ENV", "dev")
    client = TestClient(_app(duckdb.connect(":memory:"), operator="p2_fixture"))
    req = p2_request(max_solve_seconds=5., opening_central=120., opening_branch=60.)
    r = client.post("/api/zaad/network/plan", json=req.model_dump(mode="json"))
    assert r.status_code == 200, r.text
    assert "network" in r.json() and r.json()["approval_required"] is True and r.json()["executable_purchase_order"] is False
    loop = p2_request(max_solve_seconds=5., lane_cost=0., extra_lanes=[{"id": "back_north", "origin": "north", "destination": "central", "lead_periods": 1, "capacity": 1e6, "cost_per_unit": 0.}])
    r = client.post("/api/zaad/network/plan", json=loop.model_dump(mode="json"))
    assert r.status_code == 422 and r.json()["detail"]["code"] == "network_refused"


def test_interactive_network_bounds_refuse_oversized_networks(monkeypatch):
    monkeypatch.setenv("HARVESTMIND_ENV", "dev")
    client = TestClient(_app(duckdb.connect(":memory:"), operator="p2_fixture"))
    big = p2_request(branches=tuple(f"b{i}" for i in range(13)), max_solve_seconds=5.)
    r = client.post("/api/zaad/network/plan", json=big.model_dump(mode="json"))
    assert r.status_code == 413 and "bounds" in r.json()["detail"]
