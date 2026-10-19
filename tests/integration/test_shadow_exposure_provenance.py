"""Workspace provenance and pre-migration exposure coverage (HARDENING V1, H3b final correction).

A workspace that existed before recommendation exposures were recorded may have served recommendations for ANY
planning origin (the raw contract route takes the origin from the caller), so nothing about its data tells which
origins were never exposed. Only a workspace created under the instrumented system, by the registry, can have a
complete history. These tests use the real registry, real vault files, the real migration replay and the real routes."""
from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dependencies import get_conn, require_actor, require_operator
from api.product import operator_plans as OP
from api.product.governance import actor_from
from api.routers import zaad_full, zaad_shadow
from api.routers.intake import load_fmcg_sample_into
from infrastructure.db_manager import DBManager
from infrastructure.operator_registry import OperatorRegistry
from scripts.setup_db import setup_db
from zaad.full.workspace import build_request

SKU = "SKU-0001"
PARAMS = {"horizon": 8, "max_solve_seconds": 5, "skus": SKU}


@pytest.fixture()
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("ZAAD_LEGACY_PLANNERS", "0")
    monkeypatch.setenv("HARVESTMIND_RATE_LIMIT_PER_MIN", "0")
    monkeypatch.setenv("ZAAD_JOB_STORE", str(tmp_path / "jobs.sqlite"))
    monkeypatch.setenv("HARVESTMIND_DATA_ROOT", str(tmp_path / "data"))
    return tmp_path


@pytest.fixture()
def registry(env):
    return OperatorRegistry(data_root=env / "data")


def _vault(registry, name: str):
    """A workspace created the way production creates one, seeded with the synthetic sample; returns (operator, conn)."""
    rec = registry.create_operator(name, sector="commercial")
    conn = DBManager(registry).get_operator_connection(rec.operator_id)
    load_fmcg_sample_into(conn, seed=7, archetype="A_stable")
    return rec.operator_id, conn


def _client(conn, operator: str, role: str = "BUYER") -> TestClient:
    app = FastAPI()
    app.include_router(zaad_full.router)
    app.include_router(zaad_shadow.router)

    def conn_override():
        yield conn
    app.dependency_overrides[get_conn] = conn_override
    app.dependency_overrides[require_operator] = lambda: operator
    app.dependency_overrides[require_actor] = lambda: actor_from({"operator_id": operator, "actor_id": "buyer-1", "name": "Buyer", "role": role})
    # the process-wide recommendation rate cap is keyed by client address, which every TestClient shares: lifted here so a
    # planner call in one test cannot refuse another test's (the cap itself is covered by its own tests)
    from api.routers.zaad import bounded_rate
    app.dependency_overrides[bounded_rate] = lambda: None
    return TestClient(app)


def _supplier(conn) -> str:
    return conn.execute("SELECT supplier_id FROM stg_fmcg_skus WHERE sku = ?", [SKU]).fetchone()[0]


def _capture(cl, conn, origin: datetime, quantity: int = 960, **extra) -> dict:
    body = {"as_of": origin.isoformat(), "provenance": "OPERATOR_SUBMITTED", "lines": [{"sku": SKU, "supplier_id": _supplier(conn), "quantity": quantity}], **extra}
    out = cl.post("/api/zaad/shadow/plans", json=body)
    assert out.status_code == 201, out.text
    return out.json()


def _make_pre_migration(conn) -> None:
    """Turn a vault into what an existing workspace looked like before migration 032: no exposure tables at all."""
    for table in OP.EXPOSURE_TABLES:
        conn.execute(f"DROP TABLE IF EXISTS {table}")  # noqa: S608  # nosec B608 - names are code literals
    assert not any(OP._has_table(conn, t) for t in OP.EXPOSURE_TABLES)


def test_a_pre_migration_recommendation_for_a_future_origin_is_never_excluded(registry, monkeypatch):
    """1. an existing workspace with orders ending at T; 2. before migration 032 the raw route serves a recommendation for an origin
    weeks after T; 3. migration 032 begins recording; 4. the operator captures a plan for that origin; 5. a recommendation is
    recorded; 6. the comparison must NOT be READY: the pre-migration recommendation is not in any record and cannot be excluded."""
    operator, conn = _vault(registry, "Existing distributor")
    cl = _client(conn, operator)
    # the origin the full history plans; then the history is cut three weeks short, as it stood before the pre-migration request
    req, _ = build_request(conn, operator, horizon=8, skus=[SKU], max_solve_seconds=5.)
    origin = req.as_of.astimezone(timezone.utc)
    latest = conn.execute("SELECT max(order_date) FROM stg_fmcg_orders").fetchone()[0]
    cut = latest - timedelta(days=21)
    conn.execute("CREATE TEMP TABLE held AS SELECT * FROM stg_fmcg_orders WHERE order_date > ?", [cut])
    conn.execute("DELETE FROM stg_fmcg_orders WHERE order_date > ?", [cut])
    _make_pre_migration(conn)
    # 2. the pre-032 deployment served the raw contract route without recording anything
    with monkeypatch.context() as pre_032:
        pre_032.setattr(zaad_full, "expose", lambda *a, **k: datetime.now(timezone.utc))
        served = cl.post("/api/zaad/network/plan", json=req.model_dump(mode="json"))
    assert served.status_code == 200, served.text
    # 3. the upgraded deployment opens the vault: migration 032 replays and recording begins; later orders arrive
    setup_db(conn)
    conn.execute("INSERT INTO stg_fmcg_orders SELECT * FROM held")
    cov = OP.coverage(conn)
    assert cov["source"] == "MIGRATION"
    # 4. the operator captures a plan for the origin ZAAD already recommended on, before any recorded exposure
    plan = _capture(cl, conn, origin)
    # 5. a recommendation is recorded (the comparison's own synchronous run)
    body = cl.post(f"/api/zaad/shadow/plans/{plan['plan_id']}/compare", params=PARAMS).json()
    # 6. never READY: an upgraded workspace's pre-recording history is unverifiable for every origin
    assert body["contract"]["readiness"] == "CONDITIONAL", body["contract"]
    assert body["exposure"]["basis"] == "UNVERIFIED" and body["exposure"]["history"]["verified"] is False
    assert body["exposure"]["history"]["coverage"]["provenance"] == "UPGRADED" and "existed before" in body["exposure"]["history"]["note"]
    assert body["contract"]["permissions"]["can_claim_shadow_difference"] is False and body["contract"]["permissions"]["can_claim_realized_value"] is False
    assert any("not established" in c for c in body["contract"]["caveats"])


def test_an_upgraded_workspace_with_no_exposure_records_stays_unverified(registry):
    """An existing vault gains the tables through the replay on open. Recording works from then on; verification never does,
    because nothing records what the vault served before, and the contract route accepted any origin."""
    operator, conn = _vault(registry, "Upgraded distributor")
    _make_pre_migration(conn)
    setup_db(conn)                                                  # the upgraded deployment opens the vault
    cov = OP.coverage(conn)
    assert cov["source"] == "MIGRATION" and cov["provenance"] == "UPGRADED" and cov["bound_vault_path"] is None
    cl = _client(conn, operator)
    req, _ = build_request(conn, operator, horizon=8, skus=[SKU], max_solve_seconds=5.)
    origin = req.as_of.astimezone(timezone.utc)
    plan = _capture(cl, conn, origin)                                # captured before every RECORDED exposure
    served = cl.post("/api/zaad/network/plan/from-workspace", params={**PARAMS, "shape": "network"})
    assert served.status_code == 200 and OP.ledger_exposure(conn, operator, origin)["count"] == 1      # recording is live
    body = cl.post(f"/api/zaad/shadow/plans/{plan['plan_id']}/compare", params=PARAMS).json()
    assert body["contract"]["readiness"] == "CONDITIONAL" and body["exposure"]["basis"] == "UNVERIFIED"
    assert body["exposure"]["history"]["coverage"]["provenance"] == "UPGRADED" and "existed before" in body["exposure"]["history"]["note"]
    assert body["contract"]["permissions"]["can_claim_shadow_difference"] is False and body["contract"]["permissions"]["can_claim_realized_value"] is False
    assert datetime.fromisoformat(body["exposure"]["exposed_at"]) > datetime.fromisoformat(plan["captured_at"]).replace(tzinfo=timezone.utc)


def test_a_workspace_created_under_recording_is_verified_and_ready_only_when_every_gate_passes(registry, env):
    import json
    from zaad.full.planner import plan as run_planner
    operator, conn = _vault(registry, "New distributor")
    cov = OP.coverage(conn)
    assert cov["source"] == "CREATED" and cov["provenance"] == "NEW"
    assert cov["bound_vault_path"] == str(registry.get_db_path(operator).resolve()) == cov["served_from"]
    cl = _client(conn, operator)
    req, _ = build_request(conn, operator, horizon=8, skus=[SKU], max_solve_seconds=5.)
    origin = req.as_of.astimezone(timezone.utc)
    plan = _capture(cl, conn, origin)
    # the synchronous path: this run is the first recorded exposure; a complete job history (none) and a NEW vault verify it
    ready = cl.post(f"/api/zaad/shadow/plans/{plan['plan_id']}/compare", params=PARAMS).json()
    assert ready["contract"]["readiness"] == "READY" and ready["exposure"]["basis"] == "RECOMMENDATION_LEDGER", ready["contract"]
    assert ready["exposure"]["history"]["verified"] is True and ready["exposure"]["history"]["coverage"]["provenance"] == "NEW"
    assert ready["contract"]["permissions"]["can_claim_shadow_difference"] is True and ready["contract"]["permissions"]["can_claim_realized_value"] is False
    # the job path, with a job that finished later: the first exposure stays the synchronous one
    report = run_planner(req)
    store = zaad_full.runner().store
    job = store.create(operator, req, 60.0)
    store.update(job, status="DONE", finished_at=(datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat(), report_json=json.dumps(report))
    again = cl.post(f"/api/zaad/shadow/plans/{plan['plan_id']}/compare", params={**PARAMS, "baseline_job_id": job}).json()
    assert again["contract"]["readiness"] == "READY" and again["exposure"]["exposed_at"] == ready["exposure"]["exposed_at"]
    assert again["exposure"]["history"]["jobs_scanned"] == 1 and again["exposure"]["history"]["ledger_exposures"] >= 1
    # every other gate still applies: a superseded version is CONDITIONAL, a correction captured after the exposure is NOT READY
    later = _capture(cl, conn, origin, quantity=984, supersedes=plan["plan_id"])
    assert later["version"] == 2
    old = cl.post(f"/api/zaad/shadow/plans/{plan['plan_id']}/compare", params=PARAMS).json()
    assert old["contract"]["readiness"] == "CONDITIONAL" and old["contract"]["permissions"]["can_claim_shadow_difference"] is False
    new = cl.post(f"/api/zaad/shadow/plans/{later['plan_id']}/compare", params=PARAMS).json()
    assert new["contract"]["readiness"] == "NOT_READY_FOR_THIS_DECISION"


def test_a_restored_or_copied_vault_is_not_the_vault_it_was_created_as(registry):
    """A CREATED vault file copied over another operator's vault: the stamp names the original file, so the copy is RESTORED."""
    source_op, source_conn = _vault(registry, "Source distributor")
    source_conn.execute("CHECKPOINT")
    target = registry.create_operator("Target distributor", sector="commercial")
    shutil.copyfile(registry.get_db_path(source_op), registry.get_db_path(target.operator_id))
    conn = DBManager(registry).get_operator_connection(target.operator_id)
    cov = OP.coverage(conn)
    assert cov["source"] == "CREATED" and cov["provenance"] == "RESTORED"
    assert cov["bound_vault_path"] == str(registry.get_db_path(source_op).resolve()) and cov["served_from"] == str(registry.get_db_path(target.operator_id).resolve())
    cl = _client(conn, target.operator_id)
    req, _ = build_request(conn, target.operator_id, horizon=8, skus=[SKU], max_solve_seconds=5.)
    plan = _capture(cl, conn, req.as_of.astimezone(timezone.utc))
    body = cl.post(f"/api/zaad/shadow/plans/{plan['plan_id']}/compare", params=PARAMS).json()
    assert body["contract"]["readiness"] == "CONDITIONAL" and body["exposure"]["basis"] == "UNVERIFIED"
    assert body["exposure"]["history"]["coverage"]["provenance"] == "RESTORED" and "served from" in body["exposure"]["history"]["note"]
    assert body["contract"]["permissions"]["can_claim_shadow_difference"] is False
    # replaying the migration on the copy does not launder it into a new vault either
    setup_db(conn)
    assert OP.coverage(conn)["provenance"] == "RESTORED"


def test_repeated_migration_keeps_provenance_coverage_and_ledger_stamps(registry):
    operator, conn = _vault(registry, "Replayed distributor")
    before = OP.coverage(conn)
    req, _ = build_request(conn, operator, horizon=8, skus=[SKU], max_solve_seconds=5.)
    origin = req.as_of.astimezone(timezone.utc)
    first = OP.record_exposure(conn, operator, as_of=origin, route="network_plan_from_workspace", request_hash="h")
    for _ in range(3):                                              # the deployment restarts and reopens the vault: replay, replay, replay
        setup_db(conn)
    after = OP.coverage(conn)
    assert after["source"] == "CREATED" and after["provenance"] == "NEW" and after["since"] == before["since"] and after["bound_vault_path"] == before["bound_vault_path"]
    assert conn.execute("SELECT count(*) FROM zaad_exposure_coverage").fetchone()[0] == 1
    ledger = OP.ledger_exposure(conn, operator, origin)
    assert ledger["earliest"] == first and ledger["count"] == 1                                       # existing entries keep their stamps
    # an upgraded vault stays upgraded through every replay: provenance is never promoted by migration alone
    _make_pre_migration(conn)
    for _ in range(2):
        setup_db(conn)
    assert OP.coverage(conn)["provenance"] == "UPGRADED" and conn.execute("SELECT count(*) FROM zaad_exposure_coverage").fetchone()[0] == 1
