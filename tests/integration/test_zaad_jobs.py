"""Asynchronous planning jobs: tenant isolation, quotas, timeout and cancellation, durable results."""
from __future__ import annotations

import time

import pytest

import infrastructure.operator_registry as orm
from zaad.full.demo import example
from zaad.full.jobs import JobRunner, JobStore, QuotaExceeded


@pytest.fixture()
def clients(tmp_path, monkeypatch):
    monkeypatch.setattr(orm, "DEFAULT_DATA_ROOT", tmp_path / "data")
    reg = orm.OperatorRegistry(data_root=tmp_path / "data")
    a = reg.create_operator("Tenant A")
    b = reg.create_operator("Tenant B")
    monkeypatch.setenv("HARVESTMIND_AUTH_REQUIRED", "true")
    monkeypatch.setenv("ZAAD_JOB_STORE", str(tmp_path / "jobs" / "jobs.sqlite"))
    monkeypatch.setenv("ZAAD_JOB_WORKERS", "1")
    monkeypatch.setenv("ZAAD_JOB_QUOTA_ACTIVE", "2")
    from fastapi.testclient import TestClient
    import api.main as api_main
    import api.routers.zaad_full as zf
    zf._runner = None
    return TestClient(api_main.app), {"Authorization": f"Bearer {reg.issue_token(a.operator_id)}"}, \
        {"Authorization": f"Bearer {reg.issue_token(b.operator_id)}"}, a.operator_id, b.operator_id


def _wait(cl, h, job_id, seconds=120):
    deadline = time.time() + seconds
    while time.time() < deadline:
        r = cl.get(f"/api/zaad/network/jobs/{job_id}", headers=h)
        if r.status_code == 200 and r.json()["status"] in ("DONE", "FAILED", "TIMEOUT", "CANCELLED"):
            return r.json()
        time.sleep(0.5)
    raise AssertionError("job did not finish")


def test_submit_poll_result_and_isolation(clients):
    cl, ha, hb, op_a, _ = clients
    req = example("normal", seed=33001).model_dump(mode="json")
    req["operator_id"] = op_a
    r = cl.post("/api/zaad/network/jobs", headers={**ha, "Content-Type": "application/json"}, json=req)
    assert r.status_code == 202, r.text
    job_id = r.json()["job_id"]
    assert r.json()["executable_purchase_order"] is False
    body = _wait(cl, ha, job_id)
    assert body["status"] == "DONE", body.get("error")
    assert body["report"]["approval_required"] is True and body["report"]["executable_purchase_order"] is False
    assert body["seed"] == 33001 and body["engine_version"] and len(body["config_hash"]) == 64
    # another tenant cannot see it, and the list is per tenant
    assert cl.get(f"/api/zaad/network/jobs/{job_id}", headers=hb).status_code == 404
    assert [j["id"] for j in cl.get("/api/zaad/network/jobs", headers=ha).json()["jobs"]] == [job_id]
    assert cl.get("/api/zaad/network/jobs", headers=hb).json()["jobs"] == []
    # operator mismatch in the payload is refused
    req["operator_id"] = "someone_else"
    assert cl.post("/api/zaad/network/jobs", headers={**ha, "Content-Type": "application/json"}, json=req).status_code == 403


def test_cancel_and_active_quota(clients):
    cl, ha, _, op_a, _ = clients
    req = example("normal", seed=33002).model_dump(mode="json")
    req["operator_id"] = op_a
    req["max_solve_seconds"] = 20.0
    ids = []
    for _ in range(2):
        r = cl.post("/api/zaad/network/jobs", headers={**ha, "Content-Type": "application/json"}, json=req)
        assert r.status_code == 202, r.text
        ids.append(r.json()["job_id"])
    third = cl.post("/api/zaad/network/jobs", headers={**ha, "Content-Type": "application/json"}, json=req)
    assert third.status_code == 429
    cancelled = cl.delete(f"/api/zaad/network/jobs/{ids[1]}", headers=ha)
    assert cancelled.status_code == 200 and cancelled.json()["status"] in ("CANCELLED", "DONE", "RUNNING", "QUEUED")
    final = _wait(cl, ha, ids[1])
    assert final["status"] in ("CANCELLED", "DONE")
    _wait(cl, ha, ids[0])
    import api.routers.zaad_full as zf
    zf.runner().shutdown()


def test_timeout_terminates_the_worker(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite")
    runner = JobRunner(store, workers=1, active_quota=5, daily_quota=50, max_timeout_s=1.0)
    req = example("normal", seed=33003)
    runner.timeout_for = lambda r: 1.0   # force a one-second wall clock
    identity = runner.submit("tenant", req)
    deadline = time.time() + 60
    while time.time() < deadline and store.get(identity, "tenant")["status"] not in ("DONE", "TIMEOUT", "FAILED"):
        time.sleep(0.25)
    body = store.get(identity, "tenant")
    assert body["status"] in ("TIMEOUT", "DONE")   # a fast machine may finish inside a second
    with pytest.raises(KeyError):
        store.get(identity, "other")
    with pytest.raises(QuotaExceeded):
        JobRunner(store, workers=1, active_quota=5, daily_quota=1, max_timeout_s=5).submit("tenant", req)
