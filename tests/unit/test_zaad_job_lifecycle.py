"""The job store's lifecycle: leases, reconciliation, purposes, resumption.

These hold the fix for a defect reproduced in the V1 audit: a job orphaned by a process restart
stayed RUNNING for ever, counted against the active quota, and a queued job never ran. Nothing here
touches the planner; the one test that executes a job replaces the executor with a stub.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from zaad.full import jobs as jobs_module
from zaad.full.demo import example
from zaad.full.jobs import ACTIVE, PURPOSES, TERMINAL, JobRunner, JobStore


def _iso(delta_s: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=delta_s)).isoformat()


def _old_schema_store(path) -> None:
    """A store as the previous release wrote it: no purpose, owner or lease columns."""
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE jobs (
            id TEXT PRIMARY KEY, operator TEXT NOT NULL, status TEXT NOT NULL,
            created_at TEXT NOT NULL, started_at TEXT, finished_at TEXT,
            seed INTEGER NOT NULL, config_hash TEXT NOT NULL, engine_version TEXT NOT NULL,
            timeout_s REAL NOT NULL, request_json TEXT NOT NULL, report_json TEXT, error TEXT);""")
    db.commit()
    db.close()


def _insert(store: JobStore, identity: str, status: str, *, owner=None, lease=None, operator="tenant",
            purpose="WORKSPACE_PLAN") -> None:
    req = example("normal", seed=1).model_dump_json()
    with store.connect() as db:
        db.execute("INSERT INTO jobs (id, operator, status, created_at, started_at, finished_at, seed, config_hash, "
                   "engine_version, timeout_s, request_json, report_json, error, purpose, reference, owner, heartbeat_at, "
                   "lease_until) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (identity, operator, status, _iso(-100), _iso(-90) if status == "RUNNING" else None, None, 1, "x" * 64,
                    "test", 30.0, req, None, None, purpose, None, owner, None, lease))


def test_terminal_statuses_include_abandoned_and_active_is_the_rest():
    assert "ABANDONED" in TERMINAL
    assert set(ACTIVE) == {"QUEUED", "RUNNING"}
    assert not set(ACTIVE) & set(TERMINAL)


def test_a_store_written_before_leases_existed_is_upgraded_and_its_orphans_are_reconciled(tmp_path):
    path = tmp_path / "jobs.sqlite"
    _old_schema_store(path)
    db = sqlite3.connect(path)
    req = example("normal", seed=1).model_dump_json()
    db.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
               ("job_running_orphan", "tenant", "RUNNING", _iso(-100), _iso(-90), None, 1, "x" * 64, "test", 30.0, req, None, None))
    db.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
               ("job_done", "tenant", "DONE", _iso(-200), _iso(-190), _iso(-100), 1, "x" * 64, "test", 30.0, req, "{}", None))
    db.commit()
    db.close()

    db = sqlite3.connect(path)
    db.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
               ("job_old_overlay", "tenant", "DONE", _iso(-300), _iso(-290), _iso(-200), 1, "x" * 64, "test", 30.0,
                '{"seed":1,"pipeline":[{"id":"proposal_draft_1_1","source":"s"}]}', "{}", None))
    db.commit()
    db.close()

    store = JobStore(path)
    present = {row[1] for row in sqlite3.connect(path).execute("PRAGMA table_info(jobs)").fetchall()}
    assert {"purpose", "reference", "owner", "heartbeat_at", "lease_until"} <= present

    # Every read reconciles, so the explicit call comes first to observe what it changes.
    changed = store.reconcile()
    assert [c["id"] for c in changed] == ["job_running_orphan"]
    assert store.get("job_old_overlay", "tenant")["purpose"] == "PROPOSAL_OVERLAY", \
        "an old overlay run is recognised from its request and never listed as a workspace plan"
    assert store.get("job_done", "tenant")["purpose"] == "WORKSPACE_PLAN", "old rows default to a workspace plan"
    orphan = store.get("job_running_orphan", "tenant")
    assert orphan["status"] == "ABANDONED"
    assert orphan["finished_at"] is not None
    assert "stopped before it finished" in orphan["error"]
    assert store.get("job_done", "tenant")["status"] == "DONE", "a terminal row is never touched"
    assert store.active("tenant") == 0, "an abandoned job no longer spends the active quota"
    assert store.reconcile() == [], "reconciliation is idempotent"


def test_a_running_job_with_a_live_lease_is_never_reaped_by_a_reader(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite")
    _insert(store, "job_live", "RUNNING", owner="host:1:abcd", lease=_iso(+30))
    _insert(store, "job_lapsed", "RUNNING", owner="host:2:dead", lease=_iso(-1))
    for _ in range(5):   # however often and slowly a reader polls
        assert store.reconcile() in ([], [{"id": "job_lapsed", "operator": "tenant", "was": "RUNNING"}])
    assert store.get("job_live", "tenant")["status"] == "RUNNING"
    assert store.get("job_lapsed", "tenant")["status"] == "ABANDONED"
    assert store.active("tenant") == 1


def test_a_heartbeat_renews_only_the_owners_own_non_terminal_jobs(tmp_path):
    store = JobStore(tmp_path / "jobs.sqlite")
    _insert(store, "job_mine", "RUNNING", owner="me", lease=_iso(+1))
    _insert(store, "job_theirs", "RUNNING", owner="them", lease=_iso(+1))
    _insert(store, "job_mine_done", "DONE", owner="me", lease=_iso(+1))
    assert store.heartbeat("me") == 1
    mine = store.get("job_mine", "tenant")["lease_until"]
    theirs = store.get("job_theirs", "tenant")["lease_until"]
    assert datetime.fromisoformat(mine) > datetime.now(timezone.utc) + timedelta(seconds=jobs_module.LEASE_S - 5)
    assert datetime.fromisoformat(theirs) < datetime.now(timezone.utc) + timedelta(seconds=5)


def test_a_new_runner_abandons_lapsed_running_jobs_and_resumes_lapsed_queued_ones(tmp_path, monkeypatch):
    store = JobStore(tmp_path / "jobs.sqlite")
    _insert(store, "job_was_running", "RUNNING", owner="host:9:gone", lease=_iso(-5))
    _insert(store, "job_was_queued", "QUEUED", owner="host:9:gone", lease=_iso(-5))
    _insert(store, "job_someone_elses_queue", "QUEUED", owner="host:3:alive", lease=_iso(+30))
    executed: list[str] = []

    def stub(self, identity):
        executed.append(identity)
        self.store.update(identity, status="DONE", finished_at=jobs_module._now())

    monkeypatch.setattr(JobRunner, "_execute", stub)
    runner = JobRunner(store, workers=1, active_quota=5, daily_quota=50, max_timeout_s=5)
    try:
        assert [c["id"] for c in runner.abandoned_at_start] == ["job_was_running"]
        assert runner.resumed_at_start == ["job_was_queued"]
        deadline = datetime.now(timezone.utc) + timedelta(seconds=5)
        while datetime.now(timezone.utc) < deadline and store.get("job_was_queued", "tenant")["status"] != "DONE":
            pass
        assert executed == ["job_was_queued"]
        assert store.get("job_was_queued", "tenant")["owner"] == runner.instance
        assert store.get("job_was_running", "tenant")["status"] == "ABANDONED"
        assert store.get("job_someone_elses_queue", "tenant")["status"] == "QUEUED", "a live owner's queue is not stolen"
    finally:
        runner.shutdown()


def test_cancelling_an_orphan_reports_what_happened_not_before_start(tmp_path, monkeypatch):
    store = JobStore(tmp_path / "jobs.sqlite")
    _insert(store, "job_orphan", "RUNNING", owner="host:9:gone", lease=_iso(-5))
    monkeypatch.setattr(JobRunner, "_execute", lambda self, identity: None)
    runner = JobRunner(store, workers=1, active_quota=5, daily_quota=50, max_timeout_s=5, resume=False)
    try:
        out = runner.cancel("job_orphan", "tenant")
        assert out["status"] == "ABANDONED"
        assert "before start" not in (out["error"] or "")
        with pytest.raises(KeyError):
            runner.cancel("job_orphan", "another-tenant")
    finally:
        runner.shutdown()


def test_purpose_and_reference_are_persisted_and_filterable(tmp_path, monkeypatch):
    store = JobStore(tmp_path / "jobs.sqlite")
    req = example("normal", seed=1)
    with pytest.raises(ValueError):
        store.create("tenant", req, 30.0, purpose="SOMETHING_ELSE")
    plan_id = store.create("tenant", req, 30.0)
    base_id = store.create("tenant", req, 30.0, purpose="PROPOSAL_BASELINE", reference="eval_1")
    over_id = store.create("tenant", req, 30.0, purpose="PROPOSAL_OVERLAY", reference="eval_1")
    assert store.get(plan_id, "tenant")["purpose"] == "WORKSPACE_PLAN"
    assert store.get(base_id, "tenant")["reference"] == "eval_1"
    assert {j["id"] for j in store.list("tenant", purpose="WORKSPACE_PLAN")} == {plan_id}
    assert {j["id"] for j in store.list("tenant", purpose="PROPOSAL_OVERLAY")} == {over_id}
    assert len(store.list("tenant")) == 3
    with pytest.raises(ValueError):
        store.list("tenant", purpose="nope")
    assert set(PURPOSES) >= {"WORKSPACE_PLAN", "PROPOSAL_BASELINE", "PROPOSAL_OVERLAY"}


def test_submit_stamps_the_runner_as_owner_with_a_fresh_lease(tmp_path, monkeypatch):
    store = JobStore(tmp_path / "jobs.sqlite")
    monkeypatch.setattr(JobRunner, "_execute", lambda self, identity: None)
    runner = JobRunner(store, workers=1, active_quota=5, daily_quota=50, max_timeout_s=5, resume=False)
    try:
        identity = runner.submit("tenant", example("normal", seed=2), purpose="PROPOSAL_BASELINE", reference="eval_x")
        row = store.get(identity, "tenant")
        assert row["owner"] == runner.instance
        assert row["purpose"] == "PROPOSAL_BASELINE" and row["reference"] == "eval_x"
        assert datetime.fromisoformat(row["lease_until"]) > datetime.now(timezone.utc)
        assert store.reconcile() == [], "a freshly submitted job is not reaped"
    finally:
        runner.shutdown()
