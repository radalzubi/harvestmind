"""First exposure across every recommendation route (HARDENING V1, H3b cross-route correction).

A ZAAD recommendation can reach an operator through several routes. Whichever route makes it accessible, the
shadow comparison must know that it did, so a plan captured afterwards can never pose as the independent baseline.
These tests drive the real routes, the operator's DuckDB vault (exposure ledger) and the real SQLite job store."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone

import duckdb
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dependencies import get_conn, require_actor, require_operator
from api.product import operator_plans as OP
from api.product.governance import actor_from
from api.routers import fmcg, zaad_full, zaad_shadow
from api.routers.intake import load_fmcg_sample_into
from scripts.setup_db import setup_db
from zaad.full.planner import plan as run_planner
from zaad.full.workspace import build_request

SKU = "SKU-0001"
PARAMS = {"horizon": 8, "max_solve_seconds": 5, "skus": SKU}


@pytest.fixture()
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("ZAAD_LEGACY_PLANNERS", "0")                 # production setting: superseded engines unreachable
    monkeypatch.setenv("HARVESTMIND_RATE_LIMIT_PER_MIN", "0")
    monkeypatch.setenv("ZAAD_JOB_STORE", str(tmp_path / "jobs.sqlite"))
    monkeypatch.setenv("ZAAD_SHADOW_LEDGER", str(tmp_path / "decisions.sqlite"))
    return tmp_path


@pytest.fixture()
def vault():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    OP.stamp_vault_creation(conn, None)                              # the registry's creation stamp: a vault whose whole life is recorded
    load_fmcg_sample_into(conn, seed=7, archetype="A_stable")
    yield conn
    conn.close()


def _client(conn, operator: str, role: str = "BUYER") -> TestClient:
    app = FastAPI()
    for r in (zaad_full.router, zaad_shadow.router, fmcg.router):
        app.include_router(r)

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


def _origin(cl) -> datetime:
    """The planning origin the workspace derives for a synchronous recommendation (the Monday after its latest order)."""
    out = cl.post("/api/zaad/network/plan/from-workspace", params={**PARAMS, "shape": "network"})
    assert out.status_code == 200, out.text
    return datetime.fromisoformat(out.json()["report"]["as_of"]).astimezone(timezone.utc)


def _finished_job(conn, operator: str, origin: datetime, finished: datetime) -> str:
    """A planning job for the origin finished at `finished`, written through the real job store."""
    req, _ = build_request(conn, operator, as_of=origin, horizon=8, skus=[SKU], max_solve_seconds=5.)
    report = run_planner(req)
    store = zaad_full.runner().store
    identity = store.create(operator, req, 60.0)
    store.update(identity, status="DONE", finished_at=finished.isoformat(), report_json=json.dumps(report))
    return identity


def _capture(cl, origin: datetime, quantity: int = 960, **extra) -> dict:
    supplier = extra.pop("supplier")
    body = {"as_of": origin.isoformat(), "provenance": "OPERATOR_SUBMITTED", "lines": [{"sku": SKU, "supplier_id": supplier, "quantity": quantity}], **extra}
    out = cl.post("/api/zaad/shadow/plans", json=body)
    assert out.status_code == 201, out.text
    return out.json()


def _supplier(conn) -> str:
    return conn.execute("SELECT supplier_id FROM stg_fmcg_skus WHERE sku = ?", [SKU]).fetchone()[0]


def test_a_synchronous_recommendation_before_capture_is_an_exposure(env, vault):
    """The mixed-route defect: a synchronous recommendation, then a capture, then a finished job after the capture.
    The job history alone says the recommendation was first exposed after the capture; the synchronous run says otherwise."""
    operator = "tenant_mixed"
    cl = _client(vault, operator)
    origin = _origin(cl)                                             # 1. the operator receives a synchronous recommendation
    seen_at = datetime.now(timezone.utc)
    plan = _capture(cl, origin, supplier=_supplier(vault))           # 2. then captures a plan for the same origin
    captured_at = datetime.fromisoformat(plan["captured_at"]).replace(tzinfo=timezone.utc)
    assert captured_at > seen_at - timedelta(seconds=1)
    job = _finished_job(vault, operator, origin, captured_at + timedelta(minutes=5))   # 3. a job finishes after the capture
    body = cl.post(f"/api/zaad/shadow/plans/{plan['plan_id']}/compare", params={**PARAMS, "baseline_job_id": job}).json()   # 4.
    # 5. the recommendation was accessible BEFORE the capture: never READY
    assert body["contract"]["readiness"] == "NOT_READY_FOR_THIS_DECISION", body["contract"]
    assert body["contract"]["permissions"]["can_claim_shadow_difference"] is False
    assert body["exposure"]["basis"] == "RECOMMENDATION_LEDGER"
    assert datetime.fromisoformat(body["exposure"]["exposed_at"]) < captured_at
    assert body["exposure"]["history"]["ledger_exposures"] >= 1 and body["exposure"]["history"]["record_loss_detected"] is False


def _workspace_origin(conn, operator: str) -> datetime:
    """The origin the workspace derives, computed without serving a recommendation (no exposure)."""
    req, _ = build_request(conn, operator, horizon=8, skus=[SKU], max_solve_seconds=5.)
    return req.as_of.astimezone(timezone.utc)


def _no_realized_claim(body: dict) -> None:
    assert body["contract"]["permissions"]["can_claim_realized_value"] is False and body["realized_value"]["available"] is False
    assert body["executable_purchase_order"] is False


def test_a_plan_captured_before_every_exposure_is_ready_on_both_paths(env, vault):
    operator = "tenant_clean"
    cl = _client(vault, operator)
    origin = _workspace_origin(vault, operator)
    plan = _capture(cl, origin, supplier=_supplier(vault))                    # captured first: nothing has been exposed for this origin
    captured_at = datetime.fromisoformat(plan["captured_at"]).replace(tzinfo=timezone.utc)
    first = cl.post(f"/api/zaad/shadow/plans/{plan['plan_id']}/compare", params=PARAMS).json()      # synchronous: its own run is the first exposure
    assert first["contract"]["readiness"] == "READY" and first["exposure"]["basis"] == "RECOMMENDATION_LEDGER", first["contract"]
    assert first["contract"]["permissions"]["can_claim_shadow_difference"] is True and first["exposure"]["history"]["verified"] is True
    first_exposure = datetime.fromisoformat(first["exposure"]["exposed_at"])
    assert captured_at < first_exposure
    _no_realized_claim(first)
    # later recommendations through other routes, and a job finishing later still, do not move the first exposure
    assert _origin(cl) == origin
    job = _finished_job(vault, operator, origin, datetime.now(timezone.utc) + timedelta(minutes=1))
    again = cl.post(f"/api/zaad/shadow/plans/{plan['plan_id']}/compare", params={**PARAMS, "baseline_job_id": job}).json()
    assert again["contract"]["readiness"] == "READY" and datetime.fromisoformat(again["exposure"]["exposed_at"]) == first_exposure
    assert again["exposure"]["basis"] == "RECOMMENDATION_LEDGER" and again["exposure"]["history"]["ledger_exposures"] >= 2
    _no_realized_claim(again)


def test_two_synchronous_recommendations_keep_the_first_exposure(env, vault):
    operator = "tenant_twice"
    cl = _client(vault, operator)
    origin = _origin(cl)
    first = OP.ledger_exposure(vault, operator, origin)["earliest"]
    assert _origin(cl) == origin
    assert OP.ledger_exposure(vault, operator, origin)["earliest"] == first and OP.ledger_exposure(vault, operator, origin)["count"] == 2
    plan = _capture(cl, origin, supplier=_supplier(vault))
    body = cl.post(f"/api/zaad/shadow/plans/{plan['plan_id']}/compare", params=PARAMS).json()
    assert body["contract"]["readiness"] == "NOT_READY_FOR_THIS_DECISION" and datetime.fromisoformat(body["exposure"]["exposed_at"]) == first


def test_concurrent_synchronous_and_asynchronous_exposures_keep_the_earliest(env, vault):
    operator = "tenant_concurrent"
    cl = _client(vault, operator)
    origin = _workspace_origin(vault, operator)
    plan = _capture(cl, origin, supplier=_supplier(vault))
    req, _ = build_request(vault, operator, as_of=origin, horizon=8, skus=[SKU], max_solve_seconds=5.)
    report = run_planner(req)
    store = zaad_full.runner().store
    stamps: list[datetime] = []
    barrier = threading.Barrier(4)
    lock = threading.Lock()

    def sync_route(route):
        cursor = vault.cursor()
        barrier.wait()
        t = OP.record_exposure(cursor, operator, as_of=origin, route=route, request_hash=report["information_hash"])
        with lock:
            stamps.append(t)

    def async_job():
        identity = store.create(operator, req, 60.0)
        barrier.wait()
        t = datetime.now(timezone.utc)
        store.update(identity, status="DONE", finished_at=t.isoformat(), report_json=json.dumps(report))
        with lock:
            stamps.append(t)
    threads = [threading.Thread(target=sync_route, args=(f"route_{i}",)) for i in range(3)] + [threading.Thread(target=async_job)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(stamps) == 4
    body = cl.post(f"/api/zaad/shadow/plans/{plan['plan_id']}/compare", params=PARAMS).json()
    assert datetime.fromisoformat(body["exposure"]["exposed_at"]) == min(stamps)
    assert body["exposure"]["history"]["verified"] is True and body["exposure"]["history"]["jobs_scanned"] == 1 and body["exposure"]["history"]["ledger_exposures"] >= 4
    assert body["contract"]["readiness"] == "READY"      # the capture preceded all four


def test_capture_and_exposure_races_never_certify_a_post_exposure_plan(env, vault):
    operator = "tenant_race"
    cl = _client(vault, operator)
    supplier = _supplier(vault)
    for round_ in range(3):
        origin = datetime(2025, 9, 1, tzinfo=timezone.utc) + timedelta(days=7 * round_)
        barrier = threading.Barrier(2)
        out: dict = {}

        def capture():
            cursor = vault.cursor()
            barrier.wait()
            out["plan"] = OP.capture_plan(cursor, operator, as_of=origin, lines=[{"sku": SKU, "supplier_id": supplier, "quantity": 960}],
                                          provenance="OPERATOR_SUBMITTED", captured_by="buyer-1", source_reference=None, note=None, supersedes=None)

        def expose():
            cursor = vault.cursor()
            barrier.wait()
            out["exposed"] = OP.record_exposure(cursor, operator, as_of=origin, route="network_plan_from_workspace")
        pair = [threading.Thread(target=capture), threading.Thread(target=expose)]
        for t in pair:
            t.start()
        for t in pair:
            t.join()
        plan_id, exposed = out["plan"]["plan_id"], out["exposed"]
        body = cl.post(f"/api/zaad/shadow/plans/{plan_id}/compare", params=PARAMS).json()
        captured_at = datetime.fromisoformat(body["evidence"]["captured_at"]).replace(tzinfo=timezone.utc)
        first = datetime.fromisoformat(body["exposure"]["exposed_at"])
        assert first <= exposed
        if body["contract"]["readiness"] == "READY":
            assert captured_at < first                                  # READY only when the capture strictly precedes the first exposure
        else:
            assert body["contract"]["readiness"] == "NOT_READY_FOR_THIS_DECISION" and captured_at >= first


def test_a_failed_exposure_write_withholds_the_recommendation(env, vault, monkeypatch):
    operator = "tenant_failed_write"
    cl = _client(vault, operator)
    origin = _workspace_origin(vault, operator)

    def broken(*a, **k):
        raise RuntimeError("ledger offline")
    monkeypatch.setattr(OP, "record_exposure", broken)
    out = cl.post("/api/zaad/network/plan/from-workspace", params={**PARAMS, "shape": "network"})
    assert out.status_code == 503 and out.json()["detail"]["code"] == "exposure_not_recorded" and "withheld" in out.json()["detail"]["message"]
    assert "report" not in out.json()
    canonical = cl.post("/fmcg/plan", params={"mode": "canonical", "skus": SKU, "horizon_weeks": 8, "max_solve_seconds": 5})
    assert canonical.status_code == 503 and canonical.json()["detail"]["code"] == "exposure_not_recorded"
    monkeypatch.undo()
    monkeypatch.setenv("ZAAD_LEGACY_PLANNERS", "0")
    assert OP.ledger_exposure(vault, operator, origin)["count"] == 0        # nothing was recorded, and nothing was served


def test_every_synchronous_route_records_before_answering(env, vault):
    operator = "tenant_routes"
    cl = _client(vault, operator)
    origin = _origin(cl)
    rows = vault.execute("SELECT route, request_hash FROM zaad_recommendation_exposures WHERE operator_id = ? AND as_of = ?",
                         [operator, origin.replace(tzinfo=None)]).fetchall()
    assert [r[0] for r in rows] == ["network_plan_from_workspace"] and rows[0][1]
    canonical = cl.post("/fmcg/plan", params={"mode": "canonical", "skus": SKU, "horizon_weeks": 8, "max_solve_seconds": 5})
    assert canonical.status_code == 200, canonical.text
    # the raw contract route and the decision ledger route, with a request the operator supplies
    req, _ = build_request(vault, operator, as_of=origin, horizon=8, skus=[SKU], max_solve_seconds=5.)
    raw = cl.post("/api/zaad/network/plan", json=req.model_dump(mode="json"))
    assert raw.status_code == 200, raw.text
    decision = cl.post("/api/zaad/network/shadow", json=req.model_dump(mode="json"))
    assert decision.status_code == 200, decision.text
    routes = vault.execute("SELECT route, reference FROM zaad_recommendation_exposures WHERE operator_id = ? ORDER BY created_at", [operator]).fetchall()
    assert [r[0] for r in routes] == ["network_plan_from_workspace", "fmcg_plan_canonical", "network_plan", "network_shadow_decision"]
    assert routes[-1][1] == decision.json()["decision_id"]
    assert OP.ledger_exposure(vault, operator, origin)["route"] == "network_plan_from_workspace"


def test_legacy_history_and_unrecorded_engines_are_never_treated_as_complete(env, vault, monkeypatch):
    supplier = _supplier(vault)
    origin = _workspace_origin(vault, "tenant_before_coverage")
    # (a) a plan captured before the vault began recording (the coverage instant moved after the capture)
    cl = _client(vault, "tenant_before_coverage")
    plan = _capture(cl, origin, supplier=supplier)
    since = vault.execute("SELECT coverage_since_ms FROM zaad_exposure_coverage").fetchone()[0]
    vault.execute("UPDATE zaad_exposure_coverage SET coverage_since_ms = ?", [int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp() * 1000)])
    try:
        body = cl.post(f"/api/zaad/shadow/plans/{plan['plan_id']}/compare", params=PARAMS).json()
        assert body["contract"]["readiness"] == "CONDITIONAL" and body["exposure"]["basis"] == "UNVERIFIED"
        assert "before this workspace began recording" in body["exposure"]["history"]["note"] and any("not established" in c for c in body["contract"]["caveats"])
    finally:
        vault.execute("UPDATE zaad_exposure_coverage SET coverage_since_ms = ?", [since])
    # (b) superseded engines reachable: unverifiable now, and still unverifiable after they are switched off (the taint is durable)
    operator = "tenant_legacy"
    cl = _client(vault, operator)
    plan = _capture(cl, origin, supplier=supplier)
    monkeypatch.setenv("ZAAD_LEGACY_PLANNERS", "1")
    first = cl.post(f"/api/zaad/shadow/plans/{plan['plan_id']}/compare", params=PARAMS).json()
    second = cl.post(f"/api/zaad/shadow/plans/{plan['plan_id']}/compare", params=PARAMS).json()
    assert first["contract"]["readiness"] == "CONDITIONAL" and first["exposure"]["basis"] == "UNVERIFIED" and "superseded planning engines" in first["exposure"]["history"]["note"]
    assert second["contract"]["readiness"] == "CONDITIONAL" and second["exposure"]["exposed_at"] == first["exposure"]["exposed_at"]
    monkeypatch.setenv("ZAAD_LEGACY_PLANNERS", "0")
    third = cl.post(f"/api/zaad/shadow/plans/{plan['plan_id']}/compare", params=PARAMS).json()
    assert third["contract"]["readiness"] == "CONDITIONAL" and third["exposure"]["basis"] == "UNVERIFIED" and third["exposure"]["exposed_at"] == first["exposure"]["exposed_at"]
    assert "were reachable" in third["exposure"]["history"]["note"] and third["contract"]["permissions"]["can_claim_shadow_difference"] is False
    for b in (first, second, third):
        _no_realized_claim(b)
    # (c) an upgraded workspace: the exposure tables arrive through the migration's replay on open, not through creation.
    # Its data says nothing about which origins were exposed before, so no origin is verified (see test_shadow_exposure_provenance.py)
    for table in OP.EXPOSURE_TABLES:
        vault.execute(f"DROP TABLE IF EXISTS {table}")  # noqa: S608  # nosec B608 - names are code literals
    setup_db(vault)
    cov = OP.coverage(vault)
    assert cov["source"] == "MIGRATION" and cov["provenance"] == "UPGRADED"
    cl = _client(vault, "tenant_upgraded")
    plan = _capture(cl, origin, supplier=supplier)
    body = cl.post(f"/api/zaad/shadow/plans/{plan['plan_id']}/compare", params=PARAMS).json()
    assert body["contract"]["readiness"] == "CONDITIONAL" and body["exposure"]["basis"] == "UNVERIFIED" and "existed before" in body["exposure"]["history"]["note"]
    assert body["exposure"]["history"]["coverage"]["provenance"] == "UPGRADED" and body["exposure"]["history"]["ledger_exposures"] == 1   # recording still works
    _no_realized_claim(body)


def test_other_operators_exposures_never_count(env, vault):
    origin = _workspace_origin(vault, "tenant_a")
    assert _origin(_client(vault, "tenant_b")) == origin                   # tenant B received a recommendation for the same origin, earlier
    cl = _client(vault, "tenant_a")
    plan = _capture(cl, origin, supplier=_supplier(vault))
    body = cl.post(f"/api/zaad/shadow/plans/{plan['plan_id']}/compare", params=PARAMS).json()
    assert body["contract"]["readiness"] == "READY" and body["exposure"]["history"]["ledger_exposures"] == 1      # only tenant A's own run
    assert datetime.fromisoformat(body["exposure"]["exposed_at"]) > datetime.fromisoformat(plan["captured_at"]).replace(tzinfo=timezone.utc)
