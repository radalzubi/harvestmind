"""P4 persistence and API: migration 019, the recourse adapter, the workspace flag and the interactive caps."""
from __future__ import annotations

import duckdb
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.product.governance import actor_from as _actor_from
from api.dependencies import get_conn, require_actor, require_operator
from api.routers import zaad_full
from scripts.setup_db import setup_db
from tests.unit.test_zaad_sourcing_workspace import make_network_vault
from zaad.full.workspace import build_request
from zaad.recourse.workspace import recourse_block


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
    # the planner routes check a capability (security review 2026-09); this client is the workspace administrator
    app.dependency_overrides[require_actor] = lambda: _actor_from({"operator_id": (lambda: operator)(), "actor_id": "admin", "name": "admin", "role": "ADMIN"})
    from api.routers.zaad import bounded_rate
    app.dependency_overrides[bounded_rate] = lambda: None
    return app


def test_migration_019_is_present_and_nothing_attaches_without_a_row(vault):
    tables = {r[0] for r in vault.execute("SHOW TABLES").fetchall()}
    assert "stg_recourse_spec" in tables
    assert recourse_block(vault, "tenant_n") is None
    req, report = build_request(vault, "tenant_n", recourse=True)
    assert req.recourse is None and report["recourse"]["requested"] and not report["recourse"]["declared"]
    assert any("stg_recourse_spec" in w for w in report["warnings"])
    req0, report0 = build_request(vault, "tenant_n")
    assert req0.recourse is None and not report0["recourse"]["requested"]


def test_declared_row_attaches_the_block_and_the_planner_reports_it(vault):
    vault.execute("INSERT INTO stg_recourse_spec (operator_id, enabled, review_periods, observables, actions, demand_grid, continuations, provenance) "
                  "VALUES ('tenant_n', TRUE, '[3]', '[\"demand\"]', '[\"purchase\", \"transfer\"]', 5.0, 2, 'OPERATOR_DECLARED')")
    block = recourse_block(vault, "tenant_n")
    assert block == {"enabled": True, "review_periods": [3], "observables": ["demand"], "actions": ["purchase", "transfer"], "demand_grid": 5.0, "continuations": 2, "provenance": "OPERATOR_DECLARED"}
    req, report = build_request(vault, "tenant_n", recourse=True, max_solve_seconds=5)
    assert req.recourse is not None and req.recourse.enabled and tuple(req.recourse.review_periods) == (3,)
    assert report["recourse"]["enabled"] and report["recourse"]["review_periods"] == [3]
    client = TestClient(_app(vault))
    r = client.get("/api/zaad/network/request/from-workspace", params={"max_solve_seconds": 5, "recourse": "true"})
    assert r.status_code == 200 and r.json()["request"]["recourse"]["enabled"] is True
    r = client.get("/api/zaad/network/request/from-workspace", params={"max_solve_seconds": 5})
    assert r.status_code == 200 and r.json()["request"]["recourse"] is None


def test_interactive_recourse_bounds_answer_413_and_bad_declarations_422(vault):
    from zaad.meio.fixtures_p2 import p2_request
    p = p2_request(max_solve_seconds=5).model_dump(mode="json")
    p["operator_id"] = "tenant_n"
    p["scenarios"] = 4
    p["recourse"] = {"enabled": True, "review_periods": [3, 6], "observables": ["demand"], "continuations": 3}   # 4 x 3^2 = 36 worlds
    client = TestClient(_app(vault))
    r = client.post("/api/zaad/network/plan", json=p)
    assert r.status_code == 413 and "recourse bounds" in r.text
    p["recourse"] = {"enabled": True, "review_periods": [12], "observables": ["demand"]}
    r = client.post("/api/zaad/network/plan", json=p)
    assert r.status_code == 422
    p["recourse"] = {"enabled": True, "review_periods": [3], "observables": ["demand"], "continuations": 2}
    p["scenarios"] = 4                       # 4 x 2 = 8 tree worlds: the interactive edge
    r = client.post("/api/zaad/network/plan", json=p)
    assert r.status_code == 200
    body = r.json()
    assert body["approval_required"] is True and body["executable_purchase_order"] is False and "recourse" in body
    assert body["recourse"]["verdict"] in ("ADAPTIVE PLAN SELECTED", "NO MATERIAL ADAPTIVE BENEFIT", "ADAPTIVE PLAN NOT SELECTED (a static candidate passed the gates at lower settled cost)")
    # the shared-supplier-order class is batch-only with recourse: 413 on /plan
    from zaad.sourcing.fixtures import build
    q = build("C6_shared_mov_multi_sku", 41001).model_dump(mode="json")
    q["operator_id"] = "tenant_n"
    q["max_solve_seconds"] = 5
    q["recourse"] = {"enabled": True, "review_periods": [3], "observables": ["demand"], "continuations": 2}
    r = client.post("/api/zaad/network/plan", json=q)
    assert r.status_code == 413 and "batch-only" in r.text


def test_batch_path_accepts_what_plan_refuses_and_caps_the_tree(vault, tmp_path, monkeypatch):
    """The asynchronous jobs endpoint accepts the shared-order recourse request (queued, approval
    required, no executable order) and refuses a tree above the batch envelope before any model."""
    monkeypatch.setenv("ZAAD_JOB_STORE", str(tmp_path / "jobs.sqlite"))
    monkeypatch.setenv("ZAAD_JOB_WORKERS", "1")
    monkeypatch.setattr(zaad_full, "_runner", None)
    from zaad.sourcing.fixtures import build
    q = build("C6_shared_mov_multi_sku", 41001).model_dump(mode="json")
    q["operator_id"] = "tenant_n"
    q["max_solve_seconds"] = 5
    q["recourse"] = {"enabled": True, "review_periods": [3], "observables": ["demand"], "continuations": 2}
    client = TestClient(_app(vault))
    r = client.post("/api/zaad/network/jobs", json=q)
    assert r.status_code == 202, r.text
    job = r.json()
    assert job["status"] == "QUEUED" and job["approval_required"] is True and job["executable_purchase_order"] is False
    client.delete(f"/api/zaad/network/jobs/{job['job_id']}")
    q["scenarios"] = 4
    q["recourse"] = {"enabled": True, "review_periods": [3, 6], "observables": ["demand"], "continuations": 3}   # 36 worlds
    r = client.post("/api/zaad/network/jobs", json=q)
    assert r.status_code == 413 and "batch envelope" in r.text
    monkeypatch.setattr(zaad_full, "_runner", None)
