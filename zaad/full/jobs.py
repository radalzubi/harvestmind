"""Bounded asynchronous network-planning jobs.

Small requests stay synchronous on /plan. Anything larger is submitted here:
one process per job (so a timeout or a cancel terminates real work), a
process-wide worker cap, per-operator quotas, a hard wall clock, and a
durable SQLite record of the request, its seed and engine version, the
result and every failure. Nothing here places orders.

Lifecycle, and what survives a restart
--------------------------------------
A job is QUEUED when it is accepted, RUNNING while its solver process is
alive, and ends in exactly one terminal status:

    DONE        the planner returned a report
    FAILED      the planner or the runner raised
    TIMEOUT     the wall clock the job was given ran out
    CANCELLED   the workspace asked for it to stop
    ABANDONED   the service that owned it stopped before it finished

The last one is the reason this module carries an *owner* and a *lease*.
Before it did, a job orphaned by a process restart stayed RUNNING for
ever: its solver child was a daemon and died with the parent, but nothing
was left to update the row, the active quota kept counting it, and two of
them blocked a workspace from planning until someone cancelled them by
hand. Now every runner instance stamps the jobs it owns with a lease that
it renews on a heartbeat while it is alive, and every read reconciles: a
non-terminal job whose lease has lapsed is ABANDONED with a reason. A
genuinely running solve is never reaped by a slow reader, because its
owner keeps renewing the lease regardless of who is polling. Queued work
that nobody owns when a runner starts is adopted and run — a queued
request is durable and has no side effects to repeat.

Every job also carries a *purpose*. The operating product runs the same
planner for a workspace plan and for the two runs of a proposal evaluation,
and a reader that wants "the workspace's last plan" must not adopt an
evaluation's overlay run — a plan of the workspace plus an order nobody
placed — as the operator's position. The purpose is persisted with the job
so no reader has to infer it by joining other tables.

The solver lease
----------------
A solve is minutes of one CPU. On the machine class ZAAD runs on, two of
them at once do not finish twice as slowly: they starve the API process
too, and every read the operator makes waits behind them (measured in
`docs/zaad_full/PRODUCTION_SOLVE_PERFORMANCE_RECOVERY.md`). So the runner
holds `workers` solver leases (one, by default) and grants them in
submission order: the earliest queued job runs first, an evaluation's
baseline and overlay run one after the other, and no workspace can jump
another's queue. A job is RUNNING only once its solver process exists;
while it waits it is QUEUED, and `queue_position` says how many are ahead
of it. The synchronous planning routes take the same lease (`try_lease`)
and answer "busy" instead of solving beside a job, so the cap is one
place, not an accident of defaults.

This is infrastructure. It calls the frozen planner and changes nothing
about what the planner computes.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import multiprocessing as mp
import logging
import os
from pathlib import Path
import socket
import sqlite3
from typing import Any
import threading
import time
import uuid

from zaad.full import VERSION
from zaad.full.contracts import Request
from zaad.full.planner import plan, report_json

TERMINAL = ("DONE", "FAILED", "TIMEOUT", "CANCELLED", "ABANDONED")
ACTIVE = ("QUEUED", "RUNNING")

#: What a job is for. Persisted with the job so a reader never has to infer it.
PURPOSES = ("WORKSPACE_PLAN", "PROPOSAL_BASELINE", "PROPOSAL_OVERLAY", "DIAGNOSTIC_REPLAY", "SYSTEM_TEST")
DEFAULT_PURPOSE = "WORKSPACE_PLAN"

#: A runner renews the lease on every job it owns this often, and a lease lasts this long. A
#: lease that lapses means the owner is gone: a reader polling slowly cannot cause it, because the
#: owner renews on its own clock, not the reader's.
HEARTBEAT_S = float(os.environ.get("ZAAD_JOB_HEARTBEAT_SECONDS", "5"))
LEASE_S = float(os.environ.get("ZAAD_JOB_LEASE_SECONDS", "60"))

ABANDONED_REASON = ("the service that was running this stopped before it finished; nothing was "
                    "changed — run it again")
ABANDONED_QUEUED_REASON = "the service restarted before this run started; run it again"

_COLUMNS = ("id", "operator", "status", "created_at", "started_at", "finished_at", "seed", "config_hash",
            "engine_version", "timeout_s", "purpose", "reference", "owner", "heartbeat_at", "lease_until")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_utc(stamp: datetime) -> datetime:
    return stamp.astimezone(timezone.utc) if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


def _origin_of(report_json: str | None) -> tuple[int, str | None]:
    """(json_valid, report.as_of) for one stored report, as the SQL path would report them."""
    if not report_json:
        return 0, None
    try:
        report = json.loads(report_json)
    except ValueError:
        return 0, None
    origin = report.get("as_of") if isinstance(report, dict) else None
    return 1, (str(origin) if origin else None)


def _plus(seconds: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def _run(request_json: str, conn) -> None:  # child process entry
    try:
        req = Request.model_validate_json(request_json)
        report = plan(req)
        conn.send(("DONE", report_json(report), None))
    except Exception as exc:  # noqa: BLE001  the parent records the failure's class; the text stays in the worker log
        logging.getLogger("zaad.full.jobs").exception("planning job failed")
        conn.send(("FAILED", None, f"the planner failed ({type(exc).__name__})"))
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
            # Additive columns for a store created before leases and purposes existed. SQLite has
            # no ADD COLUMN IF NOT EXISTS, so the existing columns are read first.
            present = {row[1] for row in db.execute("PRAGMA table_info(jobs)").fetchall()}
            for column, decl in (("purpose", f"TEXT NOT NULL DEFAULT '{DEFAULT_PURPOSE}'"), ("reference", "TEXT"),
                                 ("owner", "TEXT"), ("heartbeat_at", "TEXT"), ("lease_until", "TEXT")):
                if column not in present:
                    db.execute(f"ALTER TABLE jobs ADD COLUMN {column} {decl}")  # noqa: S608  # nosec B608 - names are code literals
            if "purpose" not in present:
                # Rows written before purposes existed default to a workspace plan. The one kind
                # that can be told apart from the store alone is an evaluation's overlay run: its
                # request carries the proposal's pipeline entries, which nothing else ever writes.
                # (Its baseline run is a plain request; the product's vault record still excludes it.)
                db.execute("UPDATE jobs SET purpose = 'PROPOSAL_OVERLAY' WHERE purpose = ? "
                           "AND request_json LIKE '%\"id\":\"proposal_%'", (DEFAULT_PURPOSE,))

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        try:
            yield db
            db.commit()
        finally:
            db.close()

    # ── writing ──────────────────────────────────────────────────────────────

    def create(self, operator: str, req: Request, timeout_s: float, *, purpose: str = DEFAULT_PURPOSE,
               reference: str | None = None, owner: str | None = None) -> str:
        if purpose not in PURPOSES:
            raise ValueError(f"unknown job purpose {purpose!r}; one of {', '.join(PURPOSES)}")
        identity = f"job_{uuid.uuid4().hex}"
        request_json = req.model_dump_json()
        now = _now()
        with self.connect() as db:
            db.execute("INSERT INTO jobs (id, operator, status, created_at, started_at, finished_at, seed, config_hash, "
                       "engine_version, timeout_s, request_json, report_json, error, purpose, reference, owner, "
                       "heartbeat_at, lease_until) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (identity, operator, "QUEUED", now, None, None, req.seed,
                        hashlib.sha256(request_json.encode()).hexdigest(), VERSION, timeout_s, request_json, None, None,
                        purpose, reference, owner, now, _plus(LEASE_S)))
        return identity

    def claim(self, identity: str, owner: str) -> float | None:
        """QUEUED -> RUNNING for one job, atomically; its wall clock, or None when it is no longer
        queued (cancelled, or reconciled away) so the caller must not start it."""
        now = _now()
        with self.connect() as db:
            cur = db.execute("UPDATE jobs SET status = 'RUNNING', started_at = ?, owner = ?, heartbeat_at = ?, lease_until = ? "
                             "WHERE id = ? AND status = 'QUEUED'", (now, owner, now, _plus(LEASE_S), identity))
            if cur.rowcount != 1:
                return None
            row = db.execute("SELECT timeout_s FROM jobs WHERE id = ?", (identity,)).fetchone()
        return float(row[0])

    def update(self, identity: str, **fields) -> None:
        keys = ", ".join(f"{k} = ?" for k in fields)
        with self.connect() as db:
            db.execute(f"UPDATE jobs SET {keys} WHERE id = ?", (*fields.values(), identity))  # noqa: S608  # nosec B608 - column names are code literals

    def heartbeat(self, owner: str) -> int:
        """Renew the lease on every non-terminal job this owner holds. Returns how many."""
        with self.connect() as db:
            cur = db.execute("UPDATE jobs SET heartbeat_at = ?, lease_until = ? WHERE owner = ? AND status IN ('QUEUED','RUNNING')",
                             (_now(), _plus(LEASE_S), owner))
            return cur.rowcount

    def reconcile(self, now: str | None = None) -> list[dict]:
        """Turn every non-terminal job whose lease has lapsed into an explicit terminal state.

        Deterministic and idempotent: the same clock gives the same answer, and a row is only ever
        moved once. A job with no lease at all was written before leases existed and is treated as
        lapsed — nothing can be renewing it. Returns the rows it changed, for logging.
        """
        stamp = now or _now()
        with self.connect() as db:
            rows = db.execute("SELECT id, operator, status, started_at FROM jobs WHERE status IN ('QUEUED','RUNNING') "
                              "AND (lease_until IS NULL OR lease_until < ?)", (stamp,)).fetchall()
            for identity, operator, status, _started in rows:
                reason = ABANDONED_REASON if status == "RUNNING" else ABANDONED_QUEUED_REASON
                db.execute("UPDATE jobs SET status = 'ABANDONED', finished_at = ?, error = ? "
                           "WHERE id = ? AND status IN ('QUEUED','RUNNING')", (stamp, reason, identity))
        return [{"id": r[0], "operator": r[1], "was": r[2]} for r in rows]

    def adopt_queued(self, owner: str, now: str | None = None) -> list[str]:
        """Take ownership of queued jobs nobody is renewing, so they run instead of rotting.

        A queued job with no owner at all — created straight into the store rather than through a
        runner — is adopted whatever its lease says: nobody else will ever run it.
        """
        stamp = now or _now()
        with self.connect() as db:
            rows = db.execute("SELECT id FROM jobs WHERE status = 'QUEUED' AND (owner IS NULL OR lease_until IS NULL OR lease_until < ?) "
                              "ORDER BY created_at, rowid", (stamp,)).fetchall()
            ids = [r[0] for r in rows]
            for identity in ids:
                db.execute("UPDATE jobs SET owner = ?, heartbeat_at = ?, lease_until = ? WHERE id = ? AND status = 'QUEUED'",
                           (owner, stamp, _plus(LEASE_S), identity))
        return ids

    # ── reading ──────────────────────────────────────────────────────────────

    def get(self, identity: str, operator: str) -> dict:
        self.reconcile()
        with self.connect() as db:
            row = db.execute("SELECT id, operator, status, created_at, started_at, finished_at, seed, config_hash, "
                             "engine_version, timeout_s, purpose, reference, owner, heartbeat_at, lease_until, "
                             "report_json, error FROM jobs WHERE id = ? AND operator = ?", (identity, operator)).fetchone()
        if row is None:
            raise KeyError(identity)   # another tenant's job is indistinguishable from a missing one
        out = dict(zip([*_COLUMNS, "report", "error"], row))
        out["report"] = json.loads(out["report"]) if out["report"] else None
        return out

    def list(self, operator: str, limit: int = 50, purpose: str | None = None) -> list[dict]:
        self.reconcile()
        if purpose is not None and purpose not in PURPOSES:
            raise ValueError(f"unknown job purpose {purpose!r}")
        with self.connect() as db:
            if purpose is None:
                rows = db.execute("SELECT id, status, created_at, started_at, finished_at, seed, config_hash, engine_version, "
                                  "purpose, reference FROM jobs WHERE operator = ? ORDER BY created_at DESC LIMIT ?",
                                  (operator, limit)).fetchall()
            else:
                rows = db.execute("SELECT id, status, created_at, started_at, finished_at, seed, config_hash, engine_version, "
                                  "purpose, reference FROM jobs WHERE operator = ? AND purpose = ? ORDER BY created_at DESC LIMIT ?",
                                  (operator, purpose, limit)).fetchall()
        keys = ["id", "status", "created_at", "started_at", "finished_at", "seed", "config_hash", "engine_version", "purpose", "reference"]
        return [dict(zip(keys, r)) for r in rows]

    def active(self, operator: str) -> int:
        self.reconcile()
        with self.connect() as db:
            return db.execute("SELECT COUNT(*) FROM jobs WHERE operator = ? AND status IN ('QUEUED','RUNNING')", (operator,)).fetchone()[0]

    def created_since(self, operator: str, since: datetime) -> int:
        with self.connect() as db:
            return db.execute("SELECT COUNT(*) FROM jobs WHERE operator = ? AND created_at >= ?", (operator, since.isoformat())).fetchone()[0]

    def earliest_done_for_origin(self, operator: str, as_of: datetime) -> dict:
        """The earliest finished job of ONE operator whose report was for the planning origin `as_of`, from a
        complete scan of that operator's finished jobs: one SELECT over the operator's rows with no window and
        no page, so it examines every row that exists and terminates with the table. Returns the match (or
        none) together with the scan's own accounting, so a caller can tell a verified history from a doubtful
        one: `scanned` finished rows were examined, `unreadable` of them could not be assessed (no report, a
        report whose origin cannot be read, or a finish stamp that cannot be read). Any unreadable row may be an
        earlier exposure for the origin, so `unreadable > 0` means the history is NOT established as complete.

        `finished_at` is the exposure stamp: it is written together with the report in the one update that
        makes a job DONE, so it is the first moment the recommendation was readable. Rows of other operators are
        never read (the WHERE clause is the tenant boundary, as in `get` and `list`)."""
        self.reconcile()
        target = _as_utc(as_of)
        earliest: datetime | None = None
        which: str | None = None
        scanned = unreadable = 0
        with self.connect() as db:
            try:
                rows = db.execute("SELECT id, finished_at, json_valid(report_json), "
                                  "CASE WHEN json_valid(report_json) THEN json_extract(report_json, '$.as_of') END "
                                  "FROM jobs WHERE operator = ? AND status = 'DONE' ORDER BY finished_at", (operator,)).fetchall()
            except sqlite3.OperationalError:          # a SQLite without the JSON functions: read the reports in Python
                rows = [(identity, finished, *_origin_of(report)) for identity, finished, report in
                        db.execute("SELECT id, finished_at, report_json FROM jobs WHERE operator = ? AND status = 'DONE' ORDER BY finished_at",
                                   (operator,)).fetchall()]
        for identity, finished_at, valid, origin in rows:
            scanned += 1
            if not valid or not origin or not finished_at:
                unreadable += 1
                continue
            try:
                when, origin_at = _as_utc(datetime.fromisoformat(str(finished_at))), _as_utc(datetime.fromisoformat(str(origin)))
            except ValueError:
                unreadable += 1
                continue
            if origin_at == target and (earliest is None or when < earliest):
                earliest, which = when, str(identity)
        return {"id": which, "finished_at": earliest, "scanned": scanned, "unreadable": unreadable}

    def request_json(self, identity: str) -> str:
        with self.connect() as db:
            return db.execute("SELECT request_json FROM jobs WHERE id = ?", (identity,)).fetchone()[0]


class QuotaExceeded(ValueError):
    pass


class JobRunner:
    """One process per job, a global worker cap, per-operator quotas, cancellation and timeouts."""

    def __init__(self, store: JobStore, workers: int | None = None, active_quota: int | None = None,
                 daily_quota: int | None = None, max_timeout_s: float | None = None, resume: bool = True):
        self.store = store
        self.workers = workers or int(os.environ.get("ZAAD_JOB_WORKERS", "1"))
        self.active_quota = active_quota or int(os.environ.get("ZAAD_JOB_QUOTA_ACTIVE", "2"))
        self.daily_quota = daily_quota or int(os.environ.get("ZAAD_JOB_QUOTA_DAILY", "24"))
        self.max_timeout_s = max_timeout_s or float(os.environ.get("ZAAD_JOB_MAX_SECONDS", "1800"))
        self.instance = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"
        self._lock = threading.Lock()
        # The solver lease: `_free` leases, handed out in submission order to the jobs waiting in
        # `_waiting` (sequence number, identity). A synchronous plan may take a lease only when
        # nothing is waiting, so it never overtakes queued work.
        self._turn = threading.Condition(self._lock)
        self._free = self.workers
        self._waiting: list[tuple[int, str]] = []
        self._sequence = 0
        self._order: dict[str, int] = {}   # each job's place in submission order, given in _start
        self._cancel: set[str] = set()
        self._procs: dict[str, Any] = {}   # spawn-context Process objects
        self._stopped = threading.Event()
        # Take over what the previous owner of this store left behind — queued work first, so it
        # is resumed rather than reaped — then keep our own leases fresh for as long as this
        # process lives.
        self.resumed_at_start = self.store.adopt_queued(self.instance) if resume else []
        self.abandoned_at_start = self.store.reconcile() if resume else []
        threading.Thread(target=self._heartbeat_loop, daemon=True, name="zaad-job-heartbeat").start()
        for identity in self.resumed_at_start:   # adopted in creation order, so they queue in it
            self._start(identity)

    def _start(self, identity: str) -> None:
        """Give the job its place in the queue, then execute it on its own thread."""
        with self._lock:
            self._sequence += 1
            self._order[identity] = self._sequence
        threading.Thread(target=self._execute, args=(identity,), daemon=True, name=identity).start()

    # ── the solver lease ─────────────────────────────────────────────────────

    def _acquire_slot(self, identity: str, sequence: int) -> None:
        """Block until a lease is free and every job submitted earlier has taken its turn."""
        with self._turn:
            self._waiting.append((sequence, identity))
            self._waiting.sort()
            while not (self._free > 0 and self._waiting[0][1] == identity):
                self._turn.wait()
            self._waiting.pop(0)
            self._free -= 1

    def _release_slot(self) -> None:
        with self._turn:
            self._free += 1
            self._turn.notify_all()

    def try_lease(self) -> bool:
        """A lease for a synchronous solve, granted only when one is free and no job is waiting.
        The caller releases it with `release_lease`. Never blocks."""
        with self._turn:
            if self._free > 0 and not self._waiting:
                self._free -= 1
                return True
            return False

    def release_lease(self) -> None:
        self._release_slot()

    def queue_position(self, identity: str) -> int | None:
        """1 when this job is the next to start; None when it is not waiting for a lease here."""
        with self._lock:
            for position, (_, waiting) in enumerate(self._waiting, start=1):
                if waiting == identity:
                    return position
        return None

    def leases(self) -> dict[str, int]:
        """What the lease looks like now: how many are held, how many jobs wait."""
        with self._lock:
            return {"workers": self.workers, "held": self.workers - self._free, "waiting": len(self._waiting)}

    def timeout_for(self, req: Request) -> float:
        # every candidate/confirmation solve shares max_solve_seconds; 10 solves per service is the planner's shape
        return min(self.max_timeout_s, max(30.0, req.max_solve_seconds * (10 + len(req.services)) * 1.5))

    def submit(self, operator: str, req: Request, *, purpose: str = DEFAULT_PURPOSE, reference: str | None = None) -> str:
        if self.store.active(operator) >= self.active_quota:
            raise QuotaExceeded(f"at most {self.active_quota} queued or running jobs per workspace")
        if self.store.created_since(operator, datetime.now(timezone.utc) - timedelta(days=1)) >= self.daily_quota:
            raise QuotaExceeded(f"at most {self.daily_quota} jobs per workspace per day")
        identity = self.store.create(operator, req, self.timeout_for(req), purpose=purpose, reference=reference,
                                     owner=self.instance)
        self._start(identity)
        return identity

    def cancel(self, identity: str, operator: str) -> dict:
        job = self.store.get(identity, operator)   # raises KeyError for other tenants; reconciles first
        if job["status"] in TERMINAL:
            return job
        with self._lock:
            self._cancel.add(identity)
            proc = self._procs.get(identity)
        if proc is not None and proc.is_alive():
            proc.terminate()
        elif job["status"] == "QUEUED":
            self.store.update(identity, status="CANCELLED", finished_at=_now(), error="cancelled before start")
        else:
            # RUNNING with a live lease but no process here: another instance owns it, or it is
            # between claiming and starting. Say what happened rather than "before start".
            self.store.update(identity, status="CANCELLED", finished_at=_now(),
                              error="cancelled by the workspace; the run was not being executed by this service")
        return self.store.get(identity, operator)

    def _heartbeat_loop(self) -> None:
        while not self._stopped.wait(HEARTBEAT_S):
            try:
                self.store.heartbeat(self.instance)
            except Exception:  # noqa: BLE001  storage gone (e.g. test teardown): nothing to renew
                return

    def _execute(self, identity: str) -> None:
        try:
            self._execute_guarded(identity)
        except Exception as exc:  # noqa: BLE001  a runner fault is a recorded failure, not a hung job
            try:
                logging.getLogger("zaad.full.jobs").exception("planning runner failed for %s", identity)
                self.store.update(identity, status="FAILED", finished_at=_now(), error=f"the planning runner failed ({type(exc).__name__})")
            except Exception:  # noqa: BLE001  storage gone (e.g. test teardown): nothing left to record into
                pass

    def shutdown(self) -> None:
        self._stopped.set()
        with self._lock:
            procs = list(self._procs.values())
        for proc in procs:
            if proc.is_alive():
                proc.terminate()

    def _launch(self, request_json: str) -> tuple[Any, Any]:
        """Start the solver process for one request; returns (process, the parent's end of its pipe)."""
        parent, child = mp.get_context("spawn").Pipe(duplex=False)
        proc = mp.get_context("spawn").Process(target=_run, args=(request_json, child), daemon=True)
        proc.start()
        child.close()
        return proc, parent

    def _execute_guarded(self, identity: str) -> None:
        with self._lock:
            sequence = self._order.pop(identity, None)
        if sequence is None:   # started outside _start: last in line
            with self._lock:
                self._sequence += 1
                sequence = self._sequence
        self._acquire_slot(identity, sequence)
        try:
            with self._lock:
                # a cancel that landed while the job waited is already recorded in the store
                # ("cancelled before start"); the conditional claim below finds no QUEUED row
                self._cancel.discard(identity)
            request_json = self.store.request_json(identity)
            timeout = self.store.claim(identity, self.instance)
            if timeout is None:
                return   # cancelled or reconciled away while it waited for a lease
            # RUNNING is written before the process exists, so a cancel that lands in between finds a
            # RUNNING row and a live lease; `cancel` then records that the run was not being executed
            # rather than "before start", which would be untrue by a few milliseconds.
            proc, parent = self._launch(request_json)
            with self._lock:
                self._procs[identity] = proc
            self._watch(identity, proc, parent, timeout)
        finally:
            self._release_slot()

    def _watch(self, identity: str, proc: Any, parent: Any, timeout: float) -> None:
        """Wait for the solver process: its result, its death, the wall clock, or a cancel."""
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
