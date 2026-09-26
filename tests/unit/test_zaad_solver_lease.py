"""The solver lease: one solve at a time, in submission order, with an honest queue.

Measured on the production machine class, two solves at once starve the API process
(docs/zaad_full/PRODUCTION_SOLVE_PERFORMANCE_RECOVERY.md). These tests pin the orchestration that
prevents it. No planner runs: the solver process is replaced by a fake whose completion the test
controls, so every ordering below is deterministic.
"""
from __future__ import annotations

import threading
import time

import pytest

from zaad.full.demo import example
from zaad.full.jobs import JobRunner, JobStore


class FakeProcess:
    def __init__(self, done: threading.Event) -> None:
        self.done = done
        self.terminated = False

    def is_alive(self) -> bool:
        return not self.done.is_set()

    def terminate(self) -> None:
        self.terminated = True
        self.done.set()

    def join(self, timeout=None) -> None:
        return None


class FakePipe:
    def __init__(self, done: threading.Event, result) -> None:
        self.done = done
        self.result = result

    def poll(self, timeout: float = 0.) -> bool:
        return self.done.wait(timeout)

    def recv(self):
        return self.result


class FakeSolves:
    """Each launch hands back a process the test finishes by name."""

    def __init__(self) -> None:
        self.launched: list[str] = []
        self.events: dict[str, threading.Event] = {}
        self.lock = threading.Lock()

    def launch(self, runner: JobRunner, request_json: str):
        done = threading.Event()
        with self.lock:
            # the runner writes RUNNING before it launches, so the launched job is the newest RUNNING row
            with runner.store.connect() as db:
                identity = db.execute("SELECT id FROM jobs WHERE status = 'RUNNING' ORDER BY started_at DESC LIMIT 1").fetchone()[0]
            self.launched.append(identity)
            self.events[identity] = done
        return FakeProcess(done), FakePipe(done, ("DONE", "{}", None))

    def finish(self, identity: str) -> None:
        # the runner marks a job RUNNING before it launches the process, so a test that saw RUNNING may
        # finish the job before this fake has registered it: wait for the launch, then finish it
        _until(lambda: identity in self.events)
        self.events[identity].set()


def _until(predicate, seconds: float = 5.) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("condition not reached")


@pytest.fixture()
def runner(tmp_path, monkeypatch):
    fakes = FakeSolves()
    monkeypatch.setattr(JobRunner, "_launch", lambda self, request_json: fakes.launch(self, request_json))
    run = JobRunner(JobStore(tmp_path / "jobs.sqlite"), workers=1, active_quota=10, daily_quota=100, max_timeout_s=30, resume=False)
    try:
        yield run, fakes
    finally:
        run.shutdown()


def test_one_solve_at_a_time_in_submission_order(runner):
    run, fakes = runner
    req = example("normal", seed=1)
    first = run.submit("tenant-a", req)
    second = run.submit("tenant-b", req, purpose="PROPOSAL_BASELINE", reference="eval_1")
    third = run.submit("tenant-b", req, purpose="PROPOSAL_OVERLAY", reference="eval_1")
    _until(lambda: run.store.get(first, "tenant-a")["status"] == "RUNNING")
    _until(lambda: run.queue_position(third) == 2)
    assert run.store.get(second, "tenant-b")["status"] == "QUEUED"
    assert run.store.get(third, "tenant-b")["status"] == "QUEUED"
    assert run.queue_position(second) == 1 and run.queue_position(third) == 2
    assert run.queue_position(first) is None, "a running job is not in the queue"
    assert run.leases() == {"workers": 1, "held": 1, "waiting": 2}
    assert fakes.launched == [first], "nothing else was launched while the lease was held"
    fakes.finish(first)
    _until(lambda: run.store.get(second, "tenant-b")["status"] == "RUNNING")
    assert run.store.get(first, "tenant-a")["status"] == "DONE"
    assert run.store.get(third, "tenant-b")["status"] == "QUEUED" and run.queue_position(third) == 1
    fakes.finish(second)
    _until(lambda: run.store.get(third, "tenant-b")["status"] == "RUNNING")
    fakes.finish(third)
    _until(lambda: run.store.get(third, "tenant-b")["status"] == "DONE")
    assert fakes.launched == [first, second, third]
    assert run.leases() == {"workers": 1, "held": 0, "waiting": 0}


def test_a_queued_job_cancels_immediately_and_never_runs(runner):
    run, fakes = runner
    req = example("normal", seed=2)
    first = run.submit("tenant", req)
    second = run.submit("tenant", req)
    third = run.submit("tenant", req)
    _until(lambda: run.queue_position(third) == 2)
    out = run.cancel(second, "tenant")
    assert out["status"] == "CANCELLED" and out["error"] == "cancelled before start"
    assert run.store.get(second, "tenant")["started_at"] is None
    fakes.finish(first)
    _until(lambda: run.store.get(third, "tenant")["status"] == "RUNNING")
    assert fakes.launched == [first, third], "the cancelled job was skipped, the next one took its turn"
    assert run.store.get(second, "tenant")["status"] == "CANCELLED", "the queued cancel is not overwritten"
    fakes.finish(third)
    _until(lambda: run.store.get(third, "tenant")["status"] == "DONE")


def test_cancelling_a_running_job_terminates_its_process(runner):
    run, fakes = runner
    first = run.submit("tenant", example("normal", seed=3))
    _until(lambda: fakes.launched == [first])
    out = run.cancel(first, "tenant")
    _until(lambda: run.store.get(first, "tenant")["status"] == "CANCELLED")
    assert out["status"] in ("RUNNING", "CANCELLED")
    assert run.store.get(first, "tenant")["error"] == "cancelled by the workspace"
    assert run.leases()["held"] == 0


def test_a_synchronous_solve_takes_the_same_lease_and_never_overtakes_the_queue(runner):
    run, fakes = runner
    assert run.try_lease() is True, "idle: a synchronous solve may run"
    assert run.leases()["held"] == 1
    first = run.submit("tenant", example("normal", seed=4))
    time.sleep(0.2)
    assert run.store.get(first, "tenant")["status"] == "QUEUED", "the job waits behind the synchronous solve"
    assert run.queue_position(first) == 1
    assert run.try_lease() is False, "no second lease while one is held"
    run.release_lease()
    _until(lambda: run.store.get(first, "tenant")["status"] == "RUNNING")
    assert run.try_lease() is False, "a job holds the lease"
    second = run.submit("tenant", example("normal", seed=5))
    fakes.finish(first)
    _until(lambda: run.store.get(second, "tenant")["status"] == "RUNNING")
    fakes.finish(second)
    _until(lambda: run.store.get(second, "tenant")["status"] == "DONE")
    assert run.try_lease() is True and run.leases()["held"] == 1
    run.release_lease()


def test_a_timed_out_solve_releases_the_lease_for_the_next_job(runner):
    run, fakes = runner
    run.timeout_for = lambda r: 0.5
    first = run.submit("tenant", example("normal", seed=6))
    second = run.submit("tenant", example("normal", seed=6))
    _until(lambda: run.store.get(first, "tenant")["status"] == "TIMEOUT", seconds=5)
    assert run.store.get(first, "tenant")["error"] == "exceeded 0s wall clock" or "wall clock" in run.store.get(first, "tenant")["error"]
    _until(lambda: run.store.get(second, "tenant")["status"] == "TIMEOUT", seconds=5)
    assert fakes.launched == [first, second]
    assert run.leases()["held"] == 0


def test_queued_work_adopted_at_start_runs_in_creation_order(tmp_path, monkeypatch):
    store = JobStore(tmp_path / "jobs.sqlite")
    req = example("normal", seed=7)
    older = store.create("tenant", req, 30.)
    time.sleep(0.01)
    newer = store.create("tenant", req, 30.)
    fakes = FakeSolves()
    monkeypatch.setattr(JobRunner, "_launch", lambda self, request_json: fakes.launch(self, request_json))
    run = JobRunner(store, workers=1, active_quota=10, daily_quota=100, max_timeout_s=30)
    try:
        assert run.resumed_at_start == [older, newer]
        _until(lambda: fakes.launched == [older])
        assert run.queue_position(newer) == 1
        fakes.finish(older)
        _until(lambda: fakes.launched == [older, newer])
        fakes.finish(newer)
        _until(lambda: store.get(newer, "tenant")["status"] == "DONE")
    finally:
        run.shutdown()
