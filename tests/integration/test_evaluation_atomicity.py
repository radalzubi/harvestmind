"""Evaluation submission is record-first and every job says what it is for.

Audit H3: `POST /orders/{id}/evaluate` used to submit two runs and only then write the record that
marked them as an evaluation, so a workspace read landing in between adopted the baseline run as
the operator's plan. Now the record is written first, the jobs carry PROPOSAL_* purposes and the
record's id, and a failure between the steps leaves a FAILED record and no plan-looking job.
These tests run against the real app with a job store, and replace the solver with a stub.
"""
from __future__ import annotations

import duckdb
import pytest

import infrastructure.operator_registry as orm
from zaad.full.jobs import JobRunner


@pytest.fixture()
def workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(orm, "DEFAULT_DATA_ROOT", tmp_path / "data")
    reg = orm.OperatorRegistry(data_root=tmp_path / "data")
    op = reg.create_operator("Atomic Importer")
    from scripts.setup_db import setup_db
    from scripts.zaad_network_workspace_smoke import make_network_vault
    conn = duckdb.connect(str(reg.get_db_path(op.operator_id)))
    setup_db(conn)
    make_network_vault(conn, seed=11)
    conn.close()
    monkeypatch.setenv("HARVESTMIND_AUTH_REQUIRED", "true")
    monkeypatch.setenv("ZAAD_JOB_STORE", str(tmp_path / "jobs" / "jobs.sqlite"))
    monkeypatch.setenv("ZAAD_JOB_QUOTA_ACTIVE", "2")
    # No real solve: the executor marks the job DONE with an empty report.
    monkeypatch.setattr(JobRunner, "_execute", lambda self, identity: self.store.update(identity, status="DONE", report_json="{}"))
    from fastapi.testclient import TestClient
    import api.main as api_main
    import api.routers.zaad_full as zf
    zf._runner = None
    from api.routers import zaad as zaad_router
    with zaad_router._lock:
        zaad_router._recent.clear()
        zaad_router._global_recent.clear()
    client = TestClient(api_main.app)
    headers = {"Authorization": f"Bearer {reg.issue_token(op.operator_id)}", "Content-Type": "application/json"}
    yield client, headers, op.operator_id, zf
    if zf._runner is not None:
        zf._runner.shutdown()


def _draft(client, headers) -> str:
    sku = client.get("/api/zaad/workspace/inventory?limit=1", headers=headers).json()["rows"][0]["sku"]
    supplier = client.get(f"/api/zaad/workspace/inventory/{sku}", headers=headers).json()["master"]["supplier_id"]
    r = client.post("/api/zaad/orders", headers=headers,
                    json={"origin": "MANUAL", "supplier_id": supplier, "lines": [{"sku": sku, "quantity": 120, "unit_price": 2.0}]})
    assert r.status_code == 201, r.text
    return r.json()["draft_id"]


def test_every_evaluation_job_carries_its_purpose_and_the_record_names_them(workspace):
    client, headers, op, zf = workspace
    draft_id = _draft(client, headers)
    r = client.post(f"/api/zaad/orders/{draft_id}/evaluate", headers=headers)
    assert r.status_code == 202, r.text
    body = r.json()
    store = zf.runner().store
    baseline = store.get(body["baseline_job_id"], op)
    overlay = store.get(body["proposal_job_id"], op)
    assert baseline["purpose"] == "PROPOSAL_BASELINE" and overlay["purpose"] == "PROPOSAL_OVERLAY"
    assert baseline["reference"] == overlay["reference"] == body["evaluation_id"]
    # a reader asking for the workspace's plans sees neither run
    plans = client.get("/api/zaad/network/jobs?purpose=WORKSPACE_PLAN", headers=headers).json()["jobs"]
    assert plans == []
    assert set(client.get("/api/zaad/orders/evaluation-jobs", headers=headers).json()["evaluation_job_ids"]) \
        == {body["baseline_job_id"], body["proposal_job_id"]}
    events = client.get(f"/api/zaad/orders/{draft_id}", headers=headers).json()["events"]
    assert any(e["event"] == "evaluation requested" for e in events), "the history records that an evaluation was asked for"


def test_a_failure_between_the_two_submissions_leaves_a_failed_record_and_no_plan(workspace, monkeypatch):
    client, headers, op, zf = workspace
    draft_id = _draft(client, headers)
    runner = zf.runner()
    real_submit = runner.submit
    calls = {"n": 0}

    def flaky(operator, req, **kw):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("storage went away")
        return real_submit(operator, req, **kw)

    monkeypatch.setattr(runner, "submit", flaky)
    r = client.post(f"/api/zaad/orders/{draft_id}/evaluate", headers=headers)
    assert r.status_code == 503 and r.json()["detail"]["code"] == "evaluation_not_submitted"
    state = client.get(f"/api/zaad/orders/{draft_id}/evaluation", headers=headers).json()
    assert state["status"] == "FAILED" and "not submitted" in (state.get("message") or "")
    jobs = client.get("/api/zaad/network/jobs", headers=headers).json()["jobs"]
    assert all(j["status"] in ("CANCELLED", "DONE") and j["purpose"] == "PROPOSAL_BASELINE" for j in jobs), jobs
    assert client.get("/api/zaad/network/jobs?purpose=WORKSPACE_PLAN", headers=headers).json()["jobs"] == []


def test_a_quota_refusal_writes_no_evaluation_record(workspace):
    client, headers, op, zf = workspace
    store = zf.runner().store
    from zaad.full.demo import example
    for _ in range(2):   # fill the active quota with plans that never finish
        store.create(op, example("normal", seed=5), 30.0, owner=zf.runner().instance)
    draft_id = _draft(client, headers)
    r = client.post(f"/api/zaad/orders/{draft_id}/evaluate", headers=headers)
    assert r.status_code == 429, r.text
    state = client.get(f"/api/zaad/orders/{draft_id}/evaluation", headers=headers).json()
    assert state["status"] == "NONE"


def test_the_amendment_view_reads_only_workspace_plans(workspace):
    client, headers, op, zf = workspace
    store = zf.runner().store
    from zaad.full.demo import example
    # an evaluation's overlay run finished most recently; it must not be read as "the last plan"
    identity = store.create(op, example("normal", seed=6), 30.0, purpose="PROPOSAL_OVERLAY", reference="eval_z")
    store.update(identity, status="DONE", report_json='{"commitments": {"orders": [{"po": "PO-X", "recommended_action": "CANCEL"}]}}')
    po = client.get("/api/zaad/workspace/purchase-orders?limit=1", headers=headers).json()["rows"][0]["po_id"]
    r = client.post("/api/zaad/orders", headers=headers, json={"origin": "IMPORTED_AMENDMENT", "source_po_id": po,
                                                               "amendment_action": "DEFER", "supplier_id": "SUP-001",
                                                               "lines": [{"sku": "SKU-0001", "quantity": 1}]})
    assert r.status_code == 201, r.text
    view = client.get(f"/api/zaad/orders/{r.json()['draft_id']}/amendment", headers=headers).json()
    assert view["priced"] is False and "not in the last plan" in view["reason"]
