"""Post-P1 integration: one canonical planning engine on the product API.

* the superseded engines (/api/zaad plan and demo, /fmcg/plan legacy modes) are served only while
  legacy planners are enabled: dev by default, never in a deployed environment unless
  ZAAD_LEGACY_PLANNERS=1;
* the canonical workspace endpoints build the frozen contract from the operator's own vault and run
  the frozen P1 planner; approval stays with the operator.
"""
from __future__ import annotations

import duckdb
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dependencies import get_conn, legacy_planners_enabled, require_operator
from api.routers import fmcg, zaad, zaad_full
from api.routers.intake import load_fmcg_sample_into
from scripts.setup_db import setup_db

SUBSET = "SKU-0001,SKU-0002"


@pytest.fixture(scope="module")
def vault():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    load_fmcg_sample_into(conn, seed=7, archetype="A_stable")
    return conn


def _app(vault, operator: str = "tenant_a") -> FastAPI:
    app = FastAPI()
    app.include_router(zaad.router)
    app.include_router(zaad_full.router)
    app.include_router(fmcg.router)

    def conn_override():
        yield vault

    app.dependency_overrides[get_conn] = conn_override
    app.dependency_overrides[require_operator] = lambda: operator
    return app


def test_legacy_planners_are_off_outside_dev_and_on_in_dev(monkeypatch):
    monkeypatch.delenv("ZAAD_LEGACY_PLANNERS", raising=False)
    monkeypatch.setenv("HARVESTMIND_ENV", "dev")
    assert legacy_planners_enabled()
    for env in ("pilot", "staging", "prod"):
        monkeypatch.setenv("HARVESTMIND_ENV", env)
        assert not legacy_planners_enabled()
    monkeypatch.setenv("ZAAD_LEGACY_PLANNERS", "1")
    assert legacy_planners_enabled()
    monkeypatch.setenv("HARVESTMIND_ENV", "dev")
    monkeypatch.setenv("ZAAD_LEGACY_PLANNERS", "0")
    assert not legacy_planners_enabled()


def test_superseded_engines_answer_410_with_the_canonical_pointer_when_disabled(monkeypatch, vault):
    monkeypatch.setenv("HARVESTMIND_ENV", "pilot")
    monkeypatch.delenv("ZAAD_LEGACY_PLANNERS", raising=False)
    monkeypatch.setenv("HARVESTMIND_AUTH_REQUIRED", "false")
    client = TestClient(_app(vault))
    demo = client.get("/api/zaad/demo?case=balanced")
    assert demo.status_code == 410 and demo.json()["detail"]["canonical"]["workspace_plan"] == "/api/zaad/network/plan/from-workspace"
    legacy_plan = client.post("/fmcg/plan?mode=incumbent")
    assert legacy_plan.status_code == 410
    old_engine = client.post("/api/zaad/plan", json={})
    assert old_engine.status_code == 410


def test_workspace_request_endpoint_builds_the_frozen_contract_with_provenance(monkeypatch, vault):
    monkeypatch.setenv("HARVESTMIND_ENV", "dev")
    client = TestClient(_app(vault))
    r = client.get(f"/api/zaad/network/request/from-workspace?skus={SUBSET}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["request"]["schema_version"] == "zaad.network.v2" and body["request"]["operator_id"] == "tenant_a"
    assert body["build"]["compact"]["skus"] == 2 and body["build"]["leakage_guard"]["fits_use_closed_orders_before_origin_only"]
    assert all(v["provenance"] in ("INFERRED_FROM_HISTORY", "CONFIGURED_ASSUMPTION") for v in body["build"]["fits"].values())


def test_workspace_plan_endpoint_runs_the_frozen_planner_and_keeps_approval(monkeypatch, vault):
    monkeypatch.setenv("HARVESTMIND_ENV", "pilot")     # legacy engines off; the canonical path must still serve
    monkeypatch.delenv("ZAAD_LEGACY_PLANNERS", raising=False)
    client = TestClient(_app(vault))
    r = client.post(f"/api/zaad/network/plan/from-workspace?skus={SUBSET}&max_solve_seconds=5")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mode_run"] == "canonical_p1" and body["approval_required"] is True and body["executable_purchase_order"] is False
    assert body["engine"] == "zaad.full frozen P1" and isinstance(body["orders"], list)
    page = client.post("/fmcg/plan?mode=canonical&horizon_weeks=12")
    assert page.status_code == 200, page.text
    assert page.json()["mode_run"] == "canonical_p1" and page.json()["approval_required"] is True


def test_workspace_plan_refuses_an_empty_workspace_with_an_operator_message(monkeypatch):
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    client = TestClient(_app(conn))
    r = client.get("/api/zaad/network/request/from-workspace")
    assert r.status_code == 422 and r.json()["detail"]["code"] == "workspace_not_ready"
