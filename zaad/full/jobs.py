"""Bounded asynchronous network-planning jobs.

Small requests stay synchronous on /plan. Anything larger is submitted here:
one process per job (so a timeout or a cancel terminates real work), a
process-wide worker cap, per-operator quotas, a hard wall clock, and a
durable SQLite record of the request, its seed and engine version, the
result and every failure. Nothing here places orders.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import sqlite3
from typing import Any
import threading
import time
import uuid

from zaad.full import VERSION
from zaad.full.contracts import Request
from zaad.full.planner import plan, report_json

TERMINAL = ("DONE", "FAILED", "TIMEOUT", "CANCELLED")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(request_json: str, conn) -> None:  # child process entry
    try:
        req = Request.model_validate_json(request_json)
        report = plan(req)
        conn.send(("DONE", report_json(report), None))
    except Exception as exc:  # noqa: BLE001  the parent records the failure verbatim
        conn.send(("FAILED", None, f"{type(exc).__name__}: {exc}"[:2000]))
    finally:
        conn.close()


class JobStore:
    def __init__(self, path: Path):
        self.path = path
        if path.is_symlink() or path.parent.is_symlink():
            raise ValueError("job storage cannot use symlinks")
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, operator TEXT NOT NULL, status TEXT NOT NULL,
                    created_at TEXT NOT NULL, started_at TEXT, finished_at TEXT,
                    seed INTEGER NOT NULL, config_hash TEXT NOT NULL, engine_version TEXT NOT NULL,
                    timeout_s REAL NOT NULL, request_json TEXT NOT NULL, report_json TEXT, error TEXT);
                CREATE INDEX IF NOT EXISTS jobs_operator ON jobs(operator, created_at);""")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        try:
            yield db
            db.commit()
        finally:
            db.close()

    def create(self, operator: str, req: Request, timeout_s: float) -> str:
        identity = f"job_{uuid.uuid4().hex}"
        request_json = req.model_dump_json()
        with self.connect() as db:
            db.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (identity, operator, "QUEUED", _now(), None, None, req.seed,
                        hashlib.sha256(request_json.encode()).hexdigest(), VERSION, timeout_s, request_json, None, None))
        return identity

    def update(self, identity: str, **fields) -> None:
        keys = ", ".join(f"{k} = ?" for k in fields)
        with self.connect() as db:
            db.execute(f"UPDATE jobs SET {keys} WHERE id = ?", (*fields.values(), identity))  # noqa: S608  # nosec B608 - column names are code literals

    def get(self, identity: str, operator: str) -> dict:
        with self.connect() as db:
            row = db.execute("SELECT id, operator, status, created_at, started_at, finished_at, seed, config_hash, engine_version, timeout_s, report_json, error "
                             "FROM jobs WHERE id = ? AND operator = ?", (identity, operator)).fetchone()
        if row is None:
            raise KeyError(identity)   # another tenant's job is indistinguishable from a missing one
        keys = ["id", "operator", "status", "created_at", "started_at", "finished_at", "seed", "config_hash", "engine_version", "timeout_s", "report", "error"]
        out = dict(zip(keys, row))
        out["report"] = json.loads(out["report"]) if out["report"] else None
        return out

    def list(self, operator: str, limit: int = 50) -> list[dict]:
        with self.connect() as db:
            rows = db.execute("SELECT id, status, created_at, started_at, finished_at, seed, config_hash, engine_version FROM jobs "
                              "WHERE operator = ? ORDER BY created_at DESC LIMIT ?", (operator, limit)).fetchall()
        return [dict(zip(["id", "status", "created_at", "started_at", "finished_at", "seed", "config_hash", "engine_version"], r)) for r in rows]

    def active(self, operator: str) -> int:
        with self.connect() as db:
            return db.execute("SELECT COUNT(*) FROM jobs WHERE operator = ? AND status IN ('QUEUED','RUNNING')", (operator,)).fetchone()[0]

    def created_since(self, operator: str, since: datetime) -> int:
        with self.connect() as db:
            return db.execute("SELECT COUNT(*) FROM jobs WHERE operator = ? AND created_at >= ?", (operator, since.isoformat())).fetchone()[0]

    def request_json(self, identity: str) -> str:
        with self.connect() as db:
            return db.execute("SELECT request_json FROM jobs WHERE id = ?", (identity,)).fetchone()[0]


class QuotaExceeded(ValueError):
    pass


class JobRunner:
    """One process per job, a global worker cap, per-operator quotas, cancellation and timeouts."""

    def __init__(self, store: JobStore, workers: int | None = None, active_quota: int | None = None,
                 daily_quota: int | None = None, max_timeout_s: float | None = None):
        self.store = store
        self.workers = workers or int(os.environ.get("ZAAD_JOB_WORKERS", "1"))
        self.active_quota = active_quota or int(os.environ.get("ZAAD_JOB_QUOTA_ACTIVE", "2"))
        self.daily_quota = daily_quota or int(os.environ.get("ZAAD_JOB_QUOTA_DAILY", "24"))
        self.max_timeout_s = max_timeout_s or float(os.environ.get("ZAAD_JOB_MAX_SECONDS", "1800"))
        self._slots = threading.BoundedSemaphore(self.workers)
        self._lock = threading.Lock()
        self._cancel: set[str] = set()
        self._procs: dict[str, Any] = {}   # spawn-context Process objects

    def timeout_for(self, req: Request) -> float:
        # every candidate/confirmation solve shares max_solve_seconds; 10 solves per service is the planner's shape
        return min(self.max_timeout_s, max(30.0, req.max_solve_seconds * (10 + len(req.services)) * 1.5))

    def submit(self, operator: str, req: Request) -> str:
        if self.store.active(operator) >= self.active_quota:
            raise QuotaExceeded(f"at most {self.active_quota} queued or running jobs per workspace")
        if self.store.created_since(operator, datetime.now(timezone.utc) - timedelta(days=1)) >= self.daily_quota:
            raise QuotaExceeded(f"at most {self.daily_quota} jobs per workspace per day")
        identity = self.store.create(operator, req, self.timeout_for(req))
        threading.Thread(target=self._execute, args=(identity,), daemon=True, name=identity).start()
        return identity

    def cancel(self, identity: str, operator: str) -> dict:
        job = self.store.get(identity, operator)   # raises KeyError for other tenants
        if job["status"] in TERMINAL:
            return job
        with self._lock:
            self._cancel.add(identity)
            proc = self._procs.get(identity)
        if proc is not None and proc.is_alive():
            proc.terminate()
        else:
            self.store.update(identity, status="CANCELLED", finished_at=_now(), error="cancelled before start")
        return self.store.get(identity, operator)

    def _execute(self, identity: str) -> None:
        try:
            self._execute_guarded(identity)
        except Exception as exc:  # noqa: BLE001  a runner fault is a recorded failure, not a hung job
            try:
                self.store.update(identity, status="FAILED", finished_at=_now(), error=f"runner: {type(exc).__name__}: {exc}"[:2000])
            except Exception:  # noqa: BLE001  storage gone (e.g. test teardown): nothing left to record into
                pass

    def shutdown(self) -> None:
        with self._lock:
            procs = list(self._procs.values())
        for proc in procs:
            if proc.is_alive():
                proc.terminate()

    def _execute_guarded(self, identity: str) -> None:
        with self._slots:
            with self._lock:
                if identity in self._cancel:
                    self.store.update(identity, status="CANCELLED", finished_at=_now(), error="cancelled while queued")
                    return
            request_json = self.store.request_json(identity)
            timeout = float(json.loads(request_json).get("max_solve_seconds", 5.0))
            with self.store.connect() as db:
                timeout = db.execute("SELECT timeout_s FROM jobs WHERE id = ?", (identity,)).fetchone()[0]
            parent, child = mp.get_context("spawn").Pipe(duplex=False)
            proc = mp.get_context("spawn").Process(target=_run, args=(request_json, child), daemon=True)
            with self._lock:
                self._procs[identity] = proc
            self.store.update(identity, status="RUNNING", started_at=_now())
            proc.start()
            child.close()
            deadline = time.monotonic() + timeout
            status, report, error = "TIMEOUT", None, f"exceeded {timeout:.0f}s wall clock"
            while time.monotonic() < deadline:
                if parent.poll(0.25):
                    status, report, error = parent.recv()
                    break
                if not proc.is_alive():
                    if parent.poll(0.5):
                        status, report, error = parent.recv()
                    else:
                        status, error = "FAILED", "worker exited without a result"
                    break
            with self._lock:
                cancelled = identity in self._cancel
                self._procs.pop(identity, None)
                self._cancel.discard(identity)
            if proc.is_alive():
                proc.terminate()
            proc.join(5)
            if cancelled:
                status, report, error = "CANCELLED", None, "cancelled by the workspace"
            self.store.update(identity, status=status, finished_at=_now(), report_json=report, error=error)
