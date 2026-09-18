"""The diagnostic job lifecycle as the UI sees it: queued with a position,
running with real stages, done with a structured report, failed with a
reference, timed out, cancelled, stale machine jobs reaped, reconnect after
a refresh or a process restart, and no duplicate work from repeated
presses. The diagnostic itself is replaced by a controllable stand-in so
these tests exercise the lifecycle, not the solver."""
from __future__ import annotations

import json
import threading
import time

import pytest

import infrastructure.operator_registry as orm
from api.routers import jobs as J


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setattr(orm, "DEFAULT_DATA_ROOT", tmp_path / "data")
    monkeypatch.setenv("HARVESTMIND_AUTH_REQUIRED", "true")
    monkeypatch.setenv("HARVESTMIND_WORKER_MACHINES", "false")
    monkeypatch.setattr(J, "_GATE", J._Gate(1))
    J._JOBS.clear()
    reg = orm.OperatorRegistry(data_root=tmp_path / "data")
    from fastapi.testclient import TestClient
    import api.main as api_main
    cl = TestClient(api_main.app)

    def operator(name="Distributor A"):
        op = reg.create_operator(name, sector="commercial")
        tok = reg.issue_token(op.operator_id)
        return op.operator_id, {"Authorization": f"Bearer {tok}"}
    yield cl, operator
    J._JOBS.clear()


class FakeDiagnostic:
    """A diagnostic that walks the real stages and waits where told."""

    def __init__(self, hold_at: str | None = None, fail: bool = False):
        self.hold_at, self.fail = hold_at, fail
        self.release = threading.Event()
        self.reached = threading.Event()

    def __call__(self, conn, job):
        for key in ("preparing", "reconstructing", "lanes", "testing"):
            J._stage(job, key)
            if key == self.hold_at:
                self.reached.set()
                self.release.wait(90)     # long enough that a loaded CI runner never sees the hold expire mid-assertion
        if self.fail:
            raise RuntimeError("solver exploded")
        J._stage(job, "reporting")
        return {"sector": "commercial", "readiness": {"verdict": "READY", "score": 1.0, "missing": []},
                "incumbent": "client policy (INFERRED from PO history)", "incumbent_notes": [], "history_periods": 60,
                "products": 8, "suppliers": 2, "decision": "incumbent",
                "reason": "No candidate cleared the conservative improvement threshold; incumbent retained",
                "improvement": None, "candidates": {"order_up_to": {"mean": 0.01, "lower_bound": -0.02, "passed": False}},
                "state": {"mode": "normal", "dominant": "NORMAL", "p_disruptive": 0.1, "stress": 0.2, "reasons": []},
                "lanes": {}, "signal_sources": {}, "priors_in_use": {}, "provenance": {"holding_rate_per_period": "operator"}, "warnings": []}


def _wait(cl, h, jid, until, timeout=10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        j = cl.get(f"/jobs/{jid}", headers=h).json()
        if until(j):
            return j
        time.sleep(0.05)
    raise AssertionError(f"job did not reach the expected state: {j}")


def test_queued_running_stages_done_with_report(api, monkeypatch):
    cl, operator = api
    _, h = operator()
    fake = FakeDiagnostic(hold_at="testing")
    monkeypatch.setattr(J, "_run_commercial", fake)
    j = cl.post("/jobs/diagnostic", headers=h).json()
    assert j["status"] in ("queued", "running") and j["reference"] == j["id"]
    assert [s["key"] for s in j["stages"]] == ["preparing", "reconstructing", "lanes", "testing", "replaying", "reporting"]
    assert fake.reached.wait(5)
    running = cl.get(f"/jobs/{j['id']}", headers=h).json()
    assert running["status"] == "running" and running["stage"] == "testing" and running["started_at"]
    assert "percent" not in json.dumps(running)
    # the report is not ready while running
    assert cl.get(f"/jobs/{j['id']}/report.pdf", headers=h).status_code == 409
    assert cl.get(f"/jobs/{j['id']}/report.json", headers=h).status_code == 409
    fake.release.set()
    done = _wait(cl, h, j["id"], lambda x: x["status"] == "done")
    assert done["stage"] == "reporting" and done["summary"]["decision"] == "incumbent"
    assert done["report"]["conclusion"]["kind"] == "keep_current"
    assert done["report"]["run_id"] == j["id"] and done["report"]["company"] == "Distributor A"
    assert done["timing"]["run_s"] >= 0 and "queue_wait_s" in done["timing"]
    rep = cl.get(f"/jobs/{j['id']}/report.json", headers=h)
    assert rep.status_code == 200 and rep.json()["conclusion"] == done["report"]["conclusion"]
    pdf = cl.get(f"/jobs/{j['id']}/report.pdf", headers=h)
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    assert "zaad-diagnostic-" in pdf.headers["content-disposition"]


def test_repeated_press_returns_the_same_job(api, monkeypatch):
    cl, operator = api
    _, h = operator()
    fake = FakeDiagnostic(hold_at="preparing")
    monkeypatch.setattr(J, "_run_commercial", fake)
    a = cl.post("/jobs/diagnostic", headers=h).json()
    b = cl.post("/jobs/diagnostic", headers=h).json()
    c = cl.post("/jobs/diagnostic", headers=h).json()
    assert a["id"] == b["id"] == c["id"]
    assert sum(1 for j in J._JOBS.values() if j["status"] in J.ACTIVE) == 1
    fake.release.set()
    _wait(cl, h, a["id"], lambda x: x["status"] == "done")
    # once finished, a new press starts a new job and the old one stays readable
    d = cl.post("/jobs/diagnostic", headers=h).json()
    assert d["id"] != a["id"]
    assert cl.get(f"/jobs/{a['id']}", headers=h).json()["status"] == "done"


def test_queue_position_with_one_slot(api, monkeypatch):
    cl, operator = api
    _, h1 = operator("One")
    _, h2 = operator("Two")
    fake = FakeDiagnostic(hold_at="lanes")
    monkeypatch.setattr(J, "_run_commercial", fake)
    a = cl.post("/jobs/diagnostic", headers=h1).json()
    assert fake.reached.wait(5)
    b = cl.post("/jobs/diagnostic", headers=h2).json()
    queued = _wait(cl, h2, b["id"], lambda x: x["queue_position"] == 1)
    assert queued["status"] == "queued" and queued["queue_position"] == 1
    fake.release.set()
    _wait(cl, h1, a["id"], lambda x: x["status"] == "done")
    _wait(cl, h2, b["id"], lambda x: x["status"] == "done")


def test_failed_carries_a_reference(api, monkeypatch):
    cl, operator = api
    _, h = operator()
    monkeypatch.setattr(J, "_run_commercial", FakeDiagnostic(fail=True))
    j = cl.post("/jobs/diagnostic", headers=h).json()
    failed = _wait(cl, h, j["id"], lambda x: x["status"] == "failed")
    assert "solver exploded" in failed["error"] and failed["reference"] == j["id"]
    assert cl.get(f"/jobs/{j['id']}/report.pdf", headers=h).status_code == 409


def test_cancel_while_running_is_terminal_and_not_overwritten(api, monkeypatch):
    cl, operator = api
    _, h = operator()
    fake = FakeDiagnostic(hold_at="testing")
    monkeypatch.setattr(J, "_run_commercial", fake)
    j = cl.post("/jobs/diagnostic", headers=h).json()
    assert fake.reached.wait(5)
    c = cl.post(f"/jobs/{j['id']}/cancel", headers=h).json()
    assert c["status"] == "cancelled"
    fake.release.set()
    time.sleep(0.3)   # the worker wakes, hits the next stage boundary and stops
    after = cl.get(f"/jobs/{j['id']}", headers=h).json()
    assert after["status"] == "cancelled" and after["summary"] is None
    # cancel is idempotent, and a new run can start
    assert cl.post(f"/jobs/{j['id']}/cancel", headers=h).json()["status"] == "cancelled"
    n = cl.post("/jobs/diagnostic", headers=h).json()
    assert n["id"] != j["id"]


def test_cancel_while_queued(api, monkeypatch):
    cl, operator = api
    _, h1 = operator("One")
    _, h2 = operator("Two")
    fake = FakeDiagnostic(hold_at="lanes")
    monkeypatch.setattr(J, "_run_commercial", fake)
    a = cl.post("/jobs/diagnostic", headers=h1).json()
    assert fake.reached.wait(5)
    b = cl.post("/jobs/diagnostic", headers=h2).json()
    _wait(cl, h2, b["id"], lambda x: x["queue_position"] == 1)
    assert cl.post(f"/jobs/{b['id']}/cancel", headers=h2).json()["status"] == "cancelled"
    fake.release.set()
    _wait(cl, h1, a["id"], lambda x: x["status"] == "done")
    assert cl.get(f"/jobs/{b['id']}", headers=h2).json()["status"] == "cancelled"


def test_timed_out_after_max_run(api, monkeypatch):
    cl, operator = api
    _, h = operator()
    fake = FakeDiagnostic(hold_at="testing")
    monkeypatch.setattr(J, "_run_commercial", fake)
    j = cl.post("/jobs/diagnostic", headers=h).json()
    assert fake.reached.wait(5)
    monkeypatch.setattr(J, "MAX_RUN_S", 0)   # the wall clock is checked on every read
    time.sleep(0.05)
    t = cl.get(f"/jobs/{j['id']}", headers=h).json()
    assert t["status"] == "timed_out" and "run it again" in t["error"] and j["id"] in t["error"]
    fake.release.set()
    time.sleep(0.3)
    assert cl.get(f"/jobs/{j['id']}", headers=h).json()["status"] == "timed_out"
    # the retry path: a new job can be started
    assert cl.post("/jobs/diagnostic", headers=h).json()["id"] != j["id"]


def test_stale_machine_job_is_reaped_and_machine_destroyed(api, monkeypatch):
    cl, operator = api
    op, h = operator()
    destroyed = []
    monkeypatch.setattr(J.fly_machines, "destroy_machine", lambda mid: destroyed.append(mid))
    job = {"id": "job_stale00001", "operator_id": op, "kind": "diagnostic", "sector": "commercial", "status": "running",
           "stage": "testing", "progress": "solving", "queue_position": None, "runner": "machine", "machine_id": "m-1",
           "created_at": "2026-01-01T00:00:00+00:00", "started_at": "2026-01-01T00:00:00+00:00",
           "updated_at": "2026-01-01T00:00:00+00:00", "finished_at": None, "error": None, "summary": None, "report": None,
           "timing": {}, "_cancel": threading.Event()}
    J._JOBS[job["id"]] = job
    monkeypatch.setattr(J, "MAX_RUN_S", 10 ** 9)   # only the stale rule applies
    got = cl.get(f"/jobs/{job['id']}", headers=h).json()
    assert got["status"] == "timed_out" and "no progress from the solver machine" in got["error"]
    assert destroyed == ["m-1"]
    # a worker that reports late is told to stop and does not resurrect the job
    monkeypatch.setenv("HARVESTMIND_WORKER_TOKEN", "wt")
    late = cl.post(f"/jobs/internal/{job['id']}/progress", headers={"X-Worker-Token": "wt"}, json={"progress": "still here", "stage": "testing"})
    assert late.json()["ok"] is False
    assert cl.get(f"/jobs/{job['id']}", headers=h).json()["status"] == "timed_out"


def test_latest_reconnects_after_refresh_and_after_restart(api, monkeypatch):
    cl, operator = api
    _, h = operator()
    assert cl.get("/jobs/latest", headers=h).json() == {"job": None}
    fake = FakeDiagnostic(hold_at="reconstructing")
    monkeypatch.setattr(J, "_run_commercial", fake)
    j = cl.post("/jobs/diagnostic", headers=h).json()
    assert fake.reached.wait(5)
    latest = cl.get("/jobs/latest", headers=h).json()["job"]
    assert latest["id"] == j["id"] and latest["status"] == "running"
    fake.release.set()
    _wait(cl, h, j["id"], lambda x: x["status"] == "done")
    # process restart: memory gone, the persisted job is found by id and by /latest
    J._JOBS.clear()
    assert cl.get(f"/jobs/{j['id']}", headers=h).json()["status"] == "done"
    latest = cl.get("/jobs/latest", headers=h).json()["job"]
    assert latest["id"] == j["id"] and latest["report"]["run_id"] == j["id"]
    assert cl.get(f"/jobs/{j['id']}/report.pdf", headers=h).status_code == 200


def test_terminal_states_are_persisted(api, monkeypatch, tmp_path):
    cl, operator = api
    op, h = operator()
    monkeypatch.setattr(J, "_run_commercial", FakeDiagnostic(fail=True))
    j = cl.post("/jobs/diagnostic", headers=h).json()
    _wait(cl, h, j["id"], lambda x: x["status"] == "failed")
    stored = list((tmp_path / "data").rglob(f"{j['id']}.json"))
    assert len(stored) == 1 and json.loads(stored[0].read_text())["status"] == "failed"


def test_tenant_isolation_and_anonymous_rejection(api, monkeypatch):
    cl, operator = api
    _, h1 = operator("One")
    _, h2 = operator("Two")
    fake = FakeDiagnostic()
    monkeypatch.setattr(J, "_run_commercial", fake)
    j = cl.post("/jobs/diagnostic", headers=h1).json()
    _wait(cl, h1, j["id"], lambda x: x["status"] == "done")
    for path in (f"/jobs/{j['id']}", f"/jobs/{j['id']}/report.json", f"/jobs/{j['id']}/report.pdf"):
        assert cl.get(path, headers=h2).status_code == 404
        assert cl.get(path).status_code == 401
    assert cl.post(f"/jobs/{j['id']}/cancel", headers=h2).status_code == 404
    assert cl.post(f"/jobs/{j['id']}/cancel").status_code == 401
    assert cl.post("/jobs/diagnostic").status_code == 401
    assert cl.get("/jobs/latest").status_code == 401
    assert cl.get("/jobs/latest", headers=h2).json() == {"job": None}
    # the public payload never carries the operator id
    assert "operator_id" not in cl.get(f"/jobs/{j['id']}", headers=h1).json()


def test_worker_progress_accepts_stage_and_rejects_unknown_stage(api, monkeypatch):
    cl, operator = api
    op, h = operator()
    monkeypatch.setenv("HARVESTMIND_WORKER_TOKEN", "wt")
    job = {"id": "job_machine0001", "operator_id": op, "kind": "diagnostic", "sector": "commercial", "status": "queued",
           "stage": None, "progress": J.BOOT_PROGRESS, "queue_position": None, "runner": "machine", "machine_id": "m-2",
           "created_at": J._now(), "started_at": None, "updated_at": J._now(), "finished_at": None, "error": None,
           "summary": None, "report": None, "timing": {}, "_cancel": threading.Event()}
    J._JOBS[job["id"]] = job
    assert cl.get(f"/jobs/{job['id']}", headers=h).json()["status"] == "queued"
    assert cl.post(f"/jobs/internal/{job['id']}/progress", headers={"X-Worker-Token": "wt"}, json={"progress": "x", "stage": "bogus"}).json()["ok"]
    assert cl.get(f"/jobs/{job['id']}", headers=h).json()["stage"] is None
    assert cl.post(f"/jobs/internal/{job['id']}/progress", headers={"X-Worker-Token": "wt"}, json={"progress": "y", "stage": "testing"}).json()["ok"]
    assert cl.get(f"/jobs/{job['id']}", headers=h).json()["stage"] == "testing"
    assert cl.post(f"/jobs/internal/{job['id']}/progress", headers={"X-Worker-Token": "nope"}, json={"progress": "z"}).status_code == 401
    # result completes the job with a structured report
    summary = FakeDiagnostic()(None, {"id": job["id"], "status": "running"})
    r = cl.post(f"/jobs/internal/{job['id']}/result", headers={"X-Worker-Token": "wt"}, json={"status": "done", "summary": summary})
    assert r.json()["ok"]
    done = cl.get(f"/jobs/{job['id']}", headers=h).json()
    assert done["status"] == "done" and done["report"]["conclusion"]["kind"] == "keep_current"
