"""Exposure history must be complete, never a bounded sample (HARDENING V1, H3b final correction).

The earliest finished planning job for an operator and origin is the first moment ZAAD's recommendation was
accessible. A search that looks at a fixed number of recent jobs can miss an older finished job and let a plan
captured after that exposure qualify as a pre-exposure baseline. These tests use the real job store."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import duckdb
import pytest

from api.routers import zaad_shadow
from api.routers.intake import load_fmcg_sample_into
from scripts.setup_db import setup_db
from zaad.full.jobs import JobStore
from zaad.full.workspace import build_request

OPERATOR, OTHER = "tenant_exposure", "tenant_other"
ORIGIN = datetime(2025, 9, 1, tzinfo=timezone.utc)
T0 = datetime(2025, 9, 1, 6, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def req():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    load_fmcg_sample_into(conn, seed=7, archetype="A_stable")
    request, _ = build_request(conn, OPERATOR, as_of=ORIGIN, horizon=8, skus=["SKU-0001"])
    conn.close()
    return request


def _done(store: JobStore, operator: str, req, finished: datetime, as_of: str | None = None, status: str = "DONE") -> str:
    identity = store.create(operator, req, 60.0)
    report = {"as_of": as_of or req.as_of.isoformat(), "information_hash": "h", "status": "PENDING_REVIEW"}
    store.update(identity, status=status, finished_at=finished.isoformat(), report_json=json.dumps(report) if status == "DONE" else None)
    return identity


def test_the_earliest_exposure_is_found_beyond_any_bounded_window(tmp_path, req):
    store = JobStore(tmp_path / "jobs.sqlite")
    # the OLDEST created job carries the EARLIEST exposure; 249 newer jobs finished later push it out of any "newest 200" view
    first = _done(store, OPERATOR, req, T0)
    for i in range(1, 250):
        _done(store, OPERATOR, req, T0 + timedelta(minutes=i))
    # another tenant exposed something earlier still: it must not count
    _done(store, OTHER, req, T0 - timedelta(days=1))
    # an unfinished and a failed job for the origin do not expose a recommendation
    store.create(OPERATOR, req, 60.0)
    _done(store, OPERATOR, req, T0 - timedelta(hours=2), status="FAILED")
    # a finished job for another origin does not count either
    _done(store, OPERATOR, req, T0 - timedelta(hours=3), as_of="2025-08-25T00:00:00+00:00")
    exposure = zaad_shadow.earliest_job_exposure(store, OPERATOR, ORIGIN)
    assert exposure.basis == "JOB_FINISHED" and exposure.job_id == first and exposure.exposed_at == T0, exposure
    assert exposure.history_complete is True and exposure.jobs_scanned >= 250


def test_an_unverifiable_history_is_never_read_as_no_exposure(tmp_path, req):
    store = JobStore(tmp_path / "jobs.sqlite")
    _done(store, OPERATOR, req, T0)

    class Broken(JobStore):
        def earliest_done_for_origin(self, operator, as_of_iso):
            raise RuntimeError("storage offline")
    broken = Broken(tmp_path / "jobs.sqlite")
    exposure = zaad_shadow.earliest_job_exposure(broken, OPERATOR, ORIGIN)
    assert exposure.basis == "UNVERIFIED" and exposure.exposed_at is None and exposure.history_complete is False
    # a store object without the complete query (an older interface) is unverifiable, not clean
    class NoQuery:
        def list(self, *a, **k):
            return []
    exposure = zaad_shadow.earliest_job_exposure(NoQuery(), OPERATOR, ORIGIN)
    assert exposure.basis == "UNVERIFIED" and exposure.history_complete is False
    # nothing finished for the origin, with a complete scan: no job exposure, but the history is known complete
    empty = JobStore(tmp_path / "empty.sqlite")
    exposure = zaad_shadow.earliest_job_exposure(empty, OPERATOR, ORIGIN)
    assert exposure.exposed_at is None and exposure.history_complete is True and exposure.basis == "NONE_RECORDED"


def test_unreadable_finished_records_leave_the_history_unverified(tmp_path, req):
    import sqlite3
    store = JobStore(tmp_path / "jobs.sqlite")
    later = _done(store, OPERATOR, req, T0 + timedelta(hours=1))
    broken = _done(store, OPERATOR, req, T0)
    with sqlite3.connect(store.path) as db:                       # a finished row whose report cannot be read any more
        db.execute("UPDATE jobs SET report_json = '{not json' WHERE id = ?", (broken,))
    exposure = zaad_shadow.earliest_job_exposure(store, OPERATOR, ORIGIN)
    # the readable job IS an exposure (it can make a later plan NOT READY) but the history is not complete, so never READY
    assert exposure.exposed_at == T0 + timedelta(hours=1) and exposure.job_id == later
    assert exposure.basis == "UNVERIFIED" and exposure.history_complete is False and exposure.jobs_scanned == 2
    with sqlite3.connect(store.path) as db:                       # a finished row with no report at all is equally unassessable
        db.execute("UPDATE jobs SET report_json = NULL WHERE id = ?", (broken,))
    assert zaad_shadow.earliest_job_exposure(store, OPERATOR, ORIGIN).history_complete is False


def _client(conn, operator):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from api.dependencies import get_conn, require_actor, require_operator
    from api.product.governance import actor_from
    app = FastAPI()
    app.include_router(zaad_shadow.router)

    def conn_override():
        yield conn
    app.dependency_overrides[get_conn] = conn_override
    app.dependency_overrides[require_operator] = lambda: operator
    app.dependency_overrides[require_actor] = lambda: actor_from({"operator_id": operator, "actor_id": "buyer-1", "name": "Buyer", "role": "BUYER"})
    return TestClient(app)


def test_a_hidden_early_exposure_blocks_ready_end_to_end(tmp_path, monkeypatch):
    """The end-to-end regression on the real job store: a plan captured AFTER the operator's earliest finished job for the
    origin, where that job is older than 200 newer finished jobs. The bounded search missed it and granted READY."""
    import sqlite3
    from types import SimpleNamespace
    from api.routers import zaad_full
    from zaad.full.planner import plan as run_planner
    operator, sku = "tenant_e2e", "SKU-0001"
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    load_fmcg_sample_into(conn, seed=7, archetype="A_stable")
    cl = _client(conn, operator)
    origin = datetime(2025, 9, 15, tzinfo=timezone.utc)
    supplier = conn.execute("SELECT supplier_id FROM stg_fmcg_skus WHERE sku = ?", [sku]).fetchone()[0]
    req, _ = build_request(conn, operator, as_of=origin, horizon=8, skus=[sku], max_solve_seconds=5.)
    report = run_planner(req)
    plan_body = {"as_of": origin.isoformat(), "provenance": "OPERATOR_SUBMITTED", "lines": [{"sku": sku, "supplier_id": supplier, "quantity": 960}]}

    def fill(store, *, first_finished, baseline_finished, tenant=operator, request=req, result=report):
        """250 finished jobs for the origin: the OLDEST created finishes at `first_finished`; 249 newer ones finish after `baseline_finished`."""
        oldest = store.create(tenant, request, 60.0)
        store.update(oldest, status="DONE", finished_at=first_finished.isoformat(), report_json=json.dumps(result))
        baseline = None
        for i in range(249):
            identity = store.create(tenant, request, 60.0)
            store.update(identity, status="DONE", finished_at=(baseline_finished + timedelta(minutes=i)).isoformat(), report_json=json.dumps(result))
            baseline = baseline or identity
        return oldest, baseline

    params = {"horizon": 8, "max_solve_seconds": 5, "skus": sku}
    # A. the operator captures; one finished job for the origin predates the capture, hidden behind 249 later ones
    captured = cl.post("/api/zaad/shadow/plans", json=plan_body).json()
    captured_at = datetime.fromisoformat(captured["captured_at"]).replace(tzinfo=timezone.utc)
    store_a = JobStore(tmp_path / "a.sqlite")
    hidden, baseline = fill(store_a, first_finished=captured_at - timedelta(hours=1), baseline_finished=captured_at + timedelta(seconds=1))
    monkeypatch.setattr(zaad_full, "runner", lambda: SimpleNamespace(store=store_a))
    body = cl.post(f"/api/zaad/shadow/plans/{captured['plan_id']}/compare", params={**params, "baseline_job_id": baseline}).json()
    assert body["contract"]["readiness"] == "NOT_READY_FOR_THIS_DECISION", body["contract"]
    assert body["exposure"]["basis"] == "JOB_FINISHED" and body["exposure"]["history"] == {**body["exposure"]["history"], "complete": True, "jobs_scanned": 250, "earliest_job_id": hidden}
    assert datetime.fromisoformat(body["exposure"]["exposed_at"]) == captured_at - timedelta(hours=1)
    assert body["contract"]["permissions"]["can_claim_shadow_difference"] is False
    # B. the same plan against a history whose EVERY finished job follows the capture: READY, on a complete verified history
    store_b = JobStore(tmp_path / "b.sqlite")
    first_b, baseline_b = fill(store_b, first_finished=captured_at + timedelta(seconds=1), baseline_finished=captured_at + timedelta(minutes=5))
    monkeypatch.setattr(zaad_full, "runner", lambda: SimpleNamespace(store=store_b))
    ready = cl.post(f"/api/zaad/shadow/plans/{captured['plan_id']}/compare", params={**params, "baseline_job_id": baseline_b}).json()
    # the earlier stored comparison (A) recorded the hidden exposure for this plan family, so it still rules: exposure never moves forward;
    # and because A's exposure was a finished job this complete scan no longer finds, the store has lost records: nothing is verified
    assert ready["contract"]["readiness"] == "NOT_READY_FOR_THIS_DECISION" and ready["exposure"]["basis"] == "UNVERIFIED"
    assert ready["exposure"]["history"]["record_loss_detected"] is True and "no longer finds" in ready["exposure"]["history"]["note"]
    assert datetime.fromisoformat(ready["exposure"]["exposed_at"]) == captured_at - timedelta(hours=1)
    # a correction (v2) shares the family and its recorded first exposure, so it is gated the same way
    fresh = cl.post("/api/zaad/shadow/plans", json={**plan_body, "lines": [{"sku": sku, "supplier_id": supplier, "quantity": 984}], "supersedes": captured["plan_id"]}).json()
    assert fresh["version"] == 2
    v2 = cl.post(f"/api/zaad/shadow/plans/{fresh['plan_id']}/compare", params={**params, "baseline_job_id": baseline_b}).json()
    assert v2["contract"]["readiness"] == "NOT_READY_FOR_THIS_DECISION" and v2["exposure"]["basis"] == "UNVERIFIED"
    assert datetime.fromisoformat(v2["exposure"]["exposed_at"]) == captured_at - timedelta(hours=1)
    # C. a separate tenant's plan with no prior comparison: READY only with a complete history, and store B's earliest job is the exposure
    other = "tenant_e2e_clean"
    cl2 = _client(conn, other)
    req2, _ = build_request(conn, other, as_of=origin, horizon=8, skus=[sku], max_solve_seconds=5.)   # the Request carries the tenant: its own identity
    report2 = run_planner(req2)
    captured2 = cl2.post("/api/zaad/shadow/plans", json=plan_body).json()
    captured2_at = datetime.fromisoformat(captured2["captured_at"]).replace(tzinfo=timezone.utc)
    store_c = JobStore(tmp_path / "c.sqlite")
    first_c, baseline_c = fill(store_c, first_finished=captured2_at + timedelta(seconds=1), baseline_finished=captured2_at + timedelta(minutes=5),
                               tenant=other, request=req2, result=report2)
    store_c.create(operator, req, 60.0)                              # the first tenant's jobs, in the same store, are not this tenant's exposures
    store_c.update(store_c.create(operator, req, 60.0), status="DONE", finished_at=(captured2_at - timedelta(days=1)).isoformat(), report_json=json.dumps(report))
    monkeypatch.setattr(zaad_full, "runner", lambda: SimpleNamespace(store=store_c))
    ok = cl2.post(f"/api/zaad/shadow/plans/{captured2['plan_id']}/compare", params={**params, "baseline_job_id": baseline_c}).json()
    assert ok["contract"]["readiness"] == "READY" and ok["exposure"]["basis"] == "JOB_FINISHED", ok["contract"]
    assert ok["exposure"]["history"]["complete"] is True and ok["exposure"]["history"]["jobs_scanned"] == 250 and ok["exposure"]["history"]["earliest_job_id"] == first_c
    assert datetime.fromisoformat(ok["exposure"]["exposed_at"]) == captured2_at + timedelta(seconds=1)
    # repeated: exposure identical, never later
    again = cl2.post(f"/api/zaad/shadow/plans/{captured2['plan_id']}/compare", params={**params, "baseline_job_id": baseline_c}).json()
    assert again["exposure"]["exposed_at"] == ok["exposure"]["exposed_at"] and again["contract"]["readiness"] == "READY"
    # D. one finished record of this tenant becomes unreadable: the history is no longer verified, READY is withdrawn (CONDITIONAL), exposure unchanged
    with sqlite3.connect(store_c.path) as db:
        db.execute("UPDATE jobs SET report_json = '{broken' WHERE id = ?", (baseline_c,))
    store_c.update(baseline_c, report_json=json.dumps(report2))      # keep the baseline job readable; break a different one instead
    with sqlite3.connect(store_c.path) as db:
        victim = db.execute("SELECT id FROM jobs WHERE operator = ? AND id NOT IN (?, ?) AND status = 'DONE' LIMIT 1", (other, baseline_c, first_c)).fetchone()[0]
        db.execute("UPDATE jobs SET report_json = '{broken' WHERE id = ?", (victim,))
    partial = cl2.post(f"/api/zaad/shadow/plans/{captured2['plan_id']}/compare", params={**params, "baseline_job_id": baseline_c}).json()
    assert partial["contract"]["readiness"] == "CONDITIONAL" and partial["exposure"]["basis"] == "UNVERIFIED" and partial["exposure"]["history"]["complete"] is False, partial["exposure"]
    assert partial["exposure"]["exposed_at"] == ok["exposure"]["exposed_at"] and partial["contract"]["permissions"]["can_claim_shadow_difference"] is False
    # E. a store that cannot be read: CONDITIONAL, never READY, with the reason in the response
    class Offline(JobStore):
        def earliest_done_for_origin(self, operator, as_of):
            raise RuntimeError("storage offline")
    monkeypatch.setattr(zaad_full, "runner", lambda: SimpleNamespace(store=Offline(tmp_path / "c.sqlite")))
    offline = cl2.post(f"/api/zaad/shadow/plans/{captured2['plan_id']}/compare", params={**params, "baseline_job_id": baseline_c}).json()
    assert offline["contract"]["readiness"] == "CONDITIONAL" and offline["exposure"]["basis"] == "UNVERIFIED" and "could not be read" in offline["exposure"]["history"]["note"]
    # F. a synchronous comparison against a store that holds none of the jobs an earlier comparison verified: record loss, never READY
    monkeypatch.setattr(zaad_full, "runner", lambda: SimpleNamespace(store=JobStore(tmp_path / "empty.sqlite")))
    sync = cl2.post(f"/api/zaad/shadow/plans/{captured2['plan_id']}/compare", params=params).json()
    assert sync["contract"]["readiness"] == "CONDITIONAL" and sync["exposure"]["basis"] == "UNVERIFIED" and sync["exposure"]["history"]["record_loss_detected"] is True
    assert sync["exposure"]["exposed_at"] == ok["exposure"]["exposed_at"]                      # the recorded first exposure still rules
    # G. a plan with no job history at all, compared synchronously twice: the first run's clock is recorded as an exposure (the second
    # cannot move it later) but it is never laundered into a verified pre-exposure basis
    plan3 = cl2.post("/api/zaad/shadow/plans", json={**plan_body, "as_of": "2025-09-08T00:00:00+00:00"}).json()
    first = cl2.post(f"/api/zaad/shadow/plans/{plan3['plan_id']}/compare", params=params).json()
    second = cl2.post(f"/api/zaad/shadow/plans/{plan3['plan_id']}/compare", params=params).json()
    assert first["contract"]["readiness"] == "CONDITIONAL" and first["exposure"]["basis"] == "UNVERIFIED" and first["exposure"]["history"]["complete"] is True
    assert second["contract"]["readiness"] == "CONDITIONAL" and second["exposure"]["basis"] == "UNVERIFIED"
    assert second["exposure"]["exposed_at"] == first["exposure"]["exposed_at"] and second["contract"]["permissions"]["can_claim_shadow_difference"] is False
    conn.close()
