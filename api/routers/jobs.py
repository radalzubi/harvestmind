"""Background diagnostic jobs.

A diagnostic is the thing the front door promises: the operator's inferred
policy, a backtested comparison with a conservative lower bound, the lane
risk today, and a report that says all of it including "no material
improvement" when that is the answer. Solves can take minutes, so the job
runs off the request thread and the UI polls. When Fly machine launching
is configured (infrastructure/fly_machines.py) the job runs on a dedicated
ephemeral machine that fetches a data bundle over the private network and
posts the result back; otherwise it runs on a worker thread in this process.

Lifecycle (what the UI shows is exactly this, nothing invented):

  queued      created; waiting for a solver slot in this process (with a
              queue position) or for the dedicated machine to boot
  running     the diagnostic is executing; `stage` names the real step
  done        summary and structured report are attached
  failed      an error with the job id as the reference
  timed_out   exceeded HARVESTMIND_JOB_MAX_S, or a machine job went quiet
              for HARVESTMIND_JOB_STALE_S; the operator may run it again
  cancelled   the operator cancelled it

Every terminal state is persisted under the operator's vault so a refreshed
browser or a restarted process still finds the result.

  POST /jobs/diagnostic          operator: start (returns the active job if one exists)
  GET  /jobs/latest              operator: the newest job (for reconnect after a refresh)
  GET  /jobs/{id}                operator: status, stage, progress, summary, report
  GET  /jobs/{id}/report.json    operator: the structured report
  GET  /jobs/{id}/report.pdf     operator: the report as a PDF
  POST /jobs/{id}/cancel         operator: cancel

  GET  /jobs/internal/{id}/bundle    worker: staging tables as parquet, zipped
  POST /jobs/internal/{id}/progress  worker: progress text and stage
  POST /jobs/internal/{id}/result    worker: done/failed + summary
"""
from __future__ import annotations

import hashlib
import hmac
import io
import json
import logging
import os
import tempfile
import threading
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request
from fastapi.responses import Response

from api.dependencies import capability, rate_limiter, require_operator
from infrastructure import fly_machines
from infrastructure.db_manager import DBManager
from infrastructure.operator_registry import OperatorNotFoundError, OperatorRegistry

router = APIRouter(prefix="/jobs", tags=["jobs"])
log = logging.getLogger("harvestmind.jobs")
_JOBS: dict[str, dict] = {}
_LOCK = threading.Lock()

ACTIVE = ("queued", "running")
TERMINAL = ("done", "failed", "timed_out", "cancelled")
# The real steps of a commercial diagnostic, in order. Shown to the operator
# as stages; never as a percentage, because the solver has no meaningful one.
STAGES: list[dict] = [
    {"key": "preparing", "label": "Preparing your historical data"},
    {"key": "reconstructing", "label": "Reconstructing your purchasing behaviour"},
    {"key": "lanes", "label": "Reading supply conditions on your lanes"},
    {"key": "testing", "label": "Testing simple policies on your own history"},
    {"key": "replaying", "label": "Replaying ZAAD's own decisions at each historical date"},
    {"key": "reporting", "label": "Building your report"},
]
REPLAY_ENABLED = os.environ.get("HARVESTMIND_REPLAY", "1").lower() not in ("0", "false", "no")
REPLAY_SKUS = int(os.environ.get("HARVESTMIND_REPLAY_SKUS", "5"))
REPLAY_REVIEWS = int(os.environ.get("HARVESTMIND_REPLAY_REVIEWS", "26"))
REPLAY_BUDGET_S = float(os.environ.get("HARVESTMIND_REPLAY_BUDGET_S", "1200"))
# the replay's engine: "network" (the released formulation, default), "certified" (symmetry-reduced under an exact
# tie certificate, otherwise released) or "all" (symmetry-reduced, an owner option); and the study-selection
# rule for the replayed products ("window_value" or "d0_value")
REPLAY_FEFO = os.environ.get("HARVESTMIND_REPLAY_FEFO", "network").strip().lower() or "network"
REPLAY_SCOPE_RULE = os.environ.get("HARVESTMIND_REPLAY_SCOPE_RULE", "window_value").strip().lower() or "window_value"
STALE_AFTER_S = int(os.environ.get("HARVESTMIND_JOB_STALE_S", "1800"))
BOOT_STALE_S = int(os.environ.get("HARVESTMIND_JOB_BOOT_STALE_S", "300"))
MAX_RUN_S = int(os.environ.get("HARVESTMIND_JOB_MAX_S", "3600"))
BOOT_PROGRESS = "starting a dedicated solver machine"


class JobCancelled(Exception):
    """Raised inside the worker when the job was cancelled or timed out."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reports_dir(registry: OperatorRegistry, op: str) -> Path:
    d = registry.vault_dir(op) / "reports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _set(job: dict, **kw: Any) -> None:
    """Update a job; the machine worker's hook forwards progress and stage."""
    with _LOCK:
        job.update(kw)
        job["updated_at"] = _now()
    hook = job.get("_hook")
    if hook is not None:
        hook(kw)


def _stage(job: dict, key: str, progress: str | None = None) -> None:
    """Enter a real stage. Stops the worker cooperatively when the job was
    cancelled or timed out while it was busy."""
    cancel = job.get("_cancel")
    if cancel is not None and cancel.is_set():
        raise JobCancelled()
    with _LOCK:
        if job.get("status") in TERMINAL:
            raise JobCancelled()
    label = next((s["label"] for s in STAGES if s["key"] == key), key)
    _set(job, stage=key, progress=progress or label)


def _finish(job: dict, **kw: Any) -> bool:
    """Move to a terminal state once. A worker that finishes after a
    cancel or timeout does not overwrite the state the operator saw."""
    with _LOCK:
        if job.get("status") in TERMINAL:
            return False
        job.update(kw)
        job["updated_at"] = _now()
        job["finished_at"] = _now()
    _persist(job)
    return True


# ── the solver slot: one diagnostic at a time in this process ────────────────
class _Gate:
    """FIFO slots for in-process diagnostics. A job waiting here is QUEUED
    and knows its position; the API thread never solves."""

    def __init__(self, workers: int) -> None:
        self.cv = threading.Condition()
        self.free = max(1, workers)
        self.waiting: list[str] = []

    def acquire(self, ident: str, cancel: threading.Event) -> bool:
        with self.cv:
            self.waiting.append(ident)
            while not (self.free > 0 and self.waiting[0] == ident):
                if cancel.is_set():
                    self.waiting.remove(ident)
                    self.cv.notify_all()
                    return False
                self.cv.wait(0.5)
            self.waiting.pop(0)
            self.free -= 1
            self.cv.notify_all()
            return True

    def release(self) -> None:
        with self.cv:
            self.free += 1
            self.cv.notify_all()

    def position(self, ident: str) -> int | None:
        with self.cv:
            return self.waiting.index(ident) + 1 if ident in self.waiting else None


_GATE = _Gate(int(os.environ.get("HARVESTMIND_DIAG_WORKERS", "1")))


# ── the diagnostic itself (unchanged optimizer path, real stages) ────────────
def _run_commercial(conn, job: dict) -> dict:
    from api.routers.fmcg import _state_for, build_inputs
    from backtesting.counterfactual import EXTRA_CANDIDATES
    from backtesting.safe_selector import SafeSelectionConfig, safe_select
    from ingestion.pilot_readiness import assess
    from reports.diagnostic_summary import enrich
    import numpy as np
    _stage(job, "preparing", "checking what your history can support")
    ready = assess(conn)
    _stage(job, "reconstructing", "reading your history and inferring your current policy")
    fi, report = build_inputs(conn, horizon=12, train_weeks=52, service_level=0.97, holding_rate_per_week=None,
                              currency="USD", incumbent_cover_weeks=None)
    _stage(job, "lanes", "estimating the operating state and lane risk")
    est, src = _state_for(fi)
    fi.posture = est.posture
    # Scenario count for the fold candidates. Validation ran at 20; the pilot
    # machine (shared CPU) can be set lower via env to trade fidelity of the
    # candidates' own decisions for wall time. The truth folds are unaffected.
    n_scen = int(os.environ.get("HARVESTMIND_GATE_SCENARIOS", "20"))
    _stage(job, "testing", f"backtesting candidates on your own history at {n_scen} scenarios per fold, then re-testing the winner on unseen periods (this is the slow part)")
    decision = safe_select(fi, None, np.random.default_rng(0), SafeSelectionConfig(n_scen=n_scen), posture=est.posture,
                           extra_candidates={"anchored_sp": EXTRA_CANDIDATES["anchored_sp"],
                                             "adaptive_sp": EXTRA_CANDIDATES["adaptive_sp"]})
    replay_result = _run_replay(conn, job)
    _stage(job, "reporting", "assembling the evidence for your report")
    ev = decision.evidence.get(decision.mode_run)
    stats = ev.stats if ev is not None else {}
    summary = {
        "sector": "commercial",
        "readiness": {"verdict": getattr(ready, "verdict", None), "score": getattr(ready, "score", None),
                      "missing": list(getattr(ready, "required_missing", []) or [])[:12]},
        "incumbent": report.get("incumbent"), "incumbent_notes": report.get("incumbent_notes", []),
        "history_periods": decision.history_periods, "products": len(fi.products),
        "suppliers": len(set(fi.supplier_of.values())),
        "decision": decision.mode_run, "reason": decision.reason,
        "improvement": {"mean": stats.get("mean"), "lower_bound": stats.get("lower_bound"),
                        "worst": stats.get("worst"), "n_folds": getattr(ev, "n_folds", 0)} if stats else None,
        "candidates": {k: {"mean": v.stats.get("mean"), "lower_bound": v.stats.get("lower_bound"), "passed": v.passed}
                       for k, v in decision.evidence.items() if v.stats},
        "state": {"mode": est.posture.mode, "dominant": est.portfolio.dominant,
                  "p_disruptive": est.portfolio.p_disruptive(), "stress": est.portfolio.stress,
                  "reasons": est.portfolio.reasons[:5]},
        "lanes": {r: {"risk": o.risk, "quality": o.quality, "reasons": o.reasons[:3], "missing": o.missing}
                  for r, o in est.outlooks.items()},
        "signal_sources": src,
        "priors_in_use": report.get("priors", {}),
        "provenance": report.get("provenance", {}),
        "warnings": list(report.get("warnings", [])) + list(decision.warnings),
    }
    summary["optimizer_replay"] = replay_result
    return enrich(summary, ready=ready, fi=fi, est=est, decision=decision, report=report, conn=conn)


def _run_replay(conn, job: dict) -> dict:
    """The rolling replay of the production optimizer (zaad/full/historical.py). Its own stage with
    progress per decision date; a failure or an unavailable replay never fails the diagnostic."""
    if not REPLAY_ENABLED:
        return {"status": "unavailable", "reason": "disabled by configuration (HARVESTMIND_REPLAY=0)"}
    _stage(job, "replaying", "reconstructing the historical state at the first decision date")
    from zaad.full.historical import run_historical_replay

    def progress(stage: str, info: dict) -> None:
        leg = info.get("leg")
        if leg == "zaad":
            _stage(job, "replaying", f"ZAAD re-solved decision date {info.get('review')} of {info.get('reviews')} "
                                     f"(last solve {info.get('solve_seconds')} s)")
        else:
            what = "the operator's actual orders" if leg == "actual" else "the reconstructed purchasing rule"
            _stage(job, "replaying", f"replaying {what} through the same settlement")
    try:
        return run_historical_replay(conn, job.get("operator_id") or job["id"], skus=REPLAY_SKUS, reviews=REPLAY_REVIEWS,
                                     budget_s=REPLAY_BUDGET_S, progress=progress, scope_rule=REPLAY_SCOPE_RULE, fefo=REPLAY_FEFO)
    except JobCancelled:
        raise
    except Exception as exc:  # noqa: BLE001  the replay is reported as unavailable, the diagnostic stands
        log.exception("historical replay failed for %s", job.get("id"))
        return {"status": "unavailable", "reason": f"the replay failed ({type(exc).__name__}); the request id is in the server log"}


def _run_produce(conn, job: dict) -> dict:
    from backtesting.benchmark_suite import run_benchmark
    from ingestion.pilot_readiness import assess
    _stage(job, "preparing", "checking what your history can support")
    ready = assess(conn)
    _stage(job, "testing", "rolling-origin benchmark on your own history (this is the slow part)")
    bench = run_benchmark(conn)
    _stage(job, "reporting")
    return {
        "sector": "produce",
        "readiness": {"verdict": getattr(ready, "verdict", None), "score": getattr(ready, "score", None),
                      "missing": list(getattr(ready, "required_missing", []) or [])[:12]},
        "benchmark": {k: v for k, v in bench.items() if k in ("status", "gate_passed", "verdict", "weeks_available",
                                                               "weeks_required", "summary", "policies", "edge")},
        "decision": "stochastic two-sided plan" if bench.get("gate_passed") else "baseline retained",
        "reason": bench.get("verdict"),
        "warnings": [],
    }


def _company_name(op: str) -> str:
    try:
        return OperatorRegistry().get_operator(op).name
    except Exception:  # noqa: BLE001
        return "your workspace"


def _build_report(job: dict, summary: dict) -> dict | None:
    from reports.diagnostic_findings import build_report
    try:
        return build_report(summary, job_id=job["id"], company=_company_name(job["operator_id"]),
                            generated_at=job.get("finished_at") or _now())
    except Exception:  # noqa: BLE001  the summary stands on its own; the report is rebuilt on read
        log.exception("report build failed for %s", job.get("id"))
        return None


def _complete(job: dict, summary: dict) -> None:
    finished = _now()
    with _LOCK:
        job["finished_at"] = finished
    t0 = datetime.now(timezone.utc)
    report = _build_report(job, summary)
    report_s = (datetime.now(timezone.utc) - t0).total_seconds()
    created, started = job.get("created_at"), job.get("started_at")
    timing = {**(job.get("timing") or {}), "finished_at": finished, "report_build_s": round(report_s, 3)}
    try:
        if created and started:
            timing["queue_wait_s"] = round((datetime.fromisoformat(started) - datetime.fromisoformat(created)).total_seconds(), 1)
        if started:
            timing["run_s"] = round((datetime.fromisoformat(finished) - datetime.fromisoformat(started)).total_seconds(), 1)
    except (TypeError, ValueError):
        pass
    _finish(job, status="done", stage="reporting", progress="report ready", summary=summary, report=report, timing=timing)


def _worker(job: dict, op: str, sector: str) -> None:
    # The backtest is CPU-bound and shares the process with the web server.
    # On Linux, nice() applies to the calling thread only, so this keeps the
    # request loop (and the platform health check) responsive on a small VM.
    try:
        os.nice(10)
    except (AttributeError, OSError):
        pass
    cancel: threading.Event = job["_cancel"]
    if not _GATE.acquire(job["id"], cancel):
        return                                  # cancelled or timed out while queued; state already recorded
    registry = OperatorRegistry()
    dbm = DBManager(registry)
    try:
        with _LOCK:
            if job.get("status") != "queued":
                return
            job["status"] = "running"
            job["started_at"] = _now()
            job["queue_position"] = None
            job["updated_at"] = job["started_at"]
        conn = dbm.get_operator_connection(op)
        summary = _run_commercial(conn, job) if sector == "commercial" else _run_produce(conn, job)
        _complete(job, summary)
    except JobCancelled:
        pass
    except Exception as exc:  # noqa: BLE001
        log.exception("diagnostic failed for %s", op)
        _finish(job, status="failed", progress="failed", error=f"the diagnostic failed ({type(exc).__name__})")
    finally:
        _GATE.release()
        try:
            dbm.close_all()
        except Exception:  # noqa: BLE001
            pass


# ── operator-facing endpoints ────────────────────────────────────────────────
def _active_for(op: str) -> dict | None:
    with _LOCK:
        active = [j for j in _JOBS.values() if j["operator_id"] == op and j["status"] in ACTIVE]
    for j in active:
        _check_stale(j)
    active = [j for j in active if j["status"] in ACTIVE]
    active.sort(key=lambda j: j["created_at"])
    return active[0] if active else None


@router.post("/diagnostic", dependencies=[Depends(rate_limiter), Depends(capability("runDiagnostic"))])
def start_diagnostic(authed: str | None = Depends(require_operator)):
    """Start a diagnostic. Idempotent while one is active: a second press
    or a second tab gets the same job back, never a duplicate run."""
    if not authed:
        raise HTTPException(401, "operator token required")
    registry = OperatorRegistry()
    try:
        rec = registry.get_operator(authed)
    except OperatorNotFoundError:
        raise HTTPException(404, "unknown operator")
    with _LOCK:
        active = _active_locked(authed)
        if active is None:
            job_id = f"job_{uuid.uuid4().hex[:10]}"
            job: dict = {"id": job_id, "operator_id": authed, "kind": "diagnostic",
                         "sector": getattr(rec, "sector", "produce"), "status": "queued", "stage": None,
                         "progress": "waiting for a solver slot", "queue_position": None,
                         "created_at": _now(), "started_at": None, "finished_at": None, "error": None,
                         "summary": None, "report": None, "timing": {}, "_cancel": threading.Event()}
            job["updated_at"] = job["created_at"]
            _JOBS[job_id] = job
            created = True
        else:
            job, created = active, False
    if created:
        _dispatch(job, authed)
    else:
        _check_stale(job)
        if job["status"] not in ACTIVE:           # it just ended: start a fresh one
            return start_diagnostic(authed)
    return _public(job)


def _active_locked(op: str) -> dict | None:
    active = [j for j in _JOBS.values() if j["operator_id"] == op and j["status"] in ACTIVE]
    active.sort(key=lambda j: j["created_at"])
    return active[0] if active else None


def _dispatch(job: dict, op: str) -> None:
    """Dedicated machine when configured, otherwise a thread in this process."""
    if fly_machines.enabled():
        api = f"http://[{os.environ.get('FLY_PRIVATE_IP', '::1')}]:8000"
        try:
            mid = fly_machines.launch_worker(job["id"], {"ZAAD_JOB_ID": job["id"], "ZAAD_INTERNAL_API": api})
            _set(job, runner="machine", machine_id=mid, progress=BOOT_PROGRESS)
            return
        except Exception as exc:  # noqa: BLE001  fall back to the in-process thread
            log.warning("machine launch failed, running in-process: %s", exc)
            _set(job, warnings_runner=f"machine launch failed ({type(exc).__name__}); ran in-process")
    _set(job, runner="thread")
    threading.Thread(target=_worker, args=(job, op, job["sector"]), daemon=True).start()


def _persist(job: dict) -> None:
    try:
        registry = OperatorRegistry()
        path = _reports_dir(registry, job["operator_id"]) / f"{job['id']}.json"
        path.write_text(json.dumps({k: v for k, v in job.items() if not k.startswith("_")}, indent=1, default=str))
    except Exception:  # noqa: BLE001  the in-memory state is still served; persistence is best effort
        log.exception("could not persist job %s", job.get("id"))


def _age_s(stamp: Any) -> float | None:
    try:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(str(stamp))).total_seconds()
    except (TypeError, ValueError):
        return None


def _check_stale(job: dict) -> None:
    """Timeouts are applied on read so no background sweeper is needed:
    a job that ran too long is TIMED_OUT (the worker stops at its next
    stage; a machine is destroyed); a machine job that stopped reporting
    is TIMED_OUT rather than spinning forever in the UI."""
    if job.get("status") not in ACTIVE:
        return
    started = _age_s(job.get("started_at") or job.get("created_at"))
    if started is not None and started > MAX_RUN_S:
        _time_out(job, f"the diagnostic exceeded {MAX_RUN_S // 60} minutes; run it again or contact ZAAD with reference {job['id']}")
        return
    if job.get("runner") != "machine":
        return
    age = _age_s(job.get("updated_at") or job.get("created_at"))
    if age is None:
        return
    # a machine that never fetched the data (boot or network failure) frees
    # the workspace quickly; one that went quiet mid-solve gets the long limit
    limit = BOOT_STALE_S if job.get("progress") == BOOT_PROGRESS else STALE_AFTER_S
    if age > limit:
        _time_out(job, f"no progress from the solver machine for {int(age // 60)} minutes; run it again or contact ZAAD with reference {job['id']}")


def _time_out(job: dict, message: str) -> None:
    cancel = job.get("_cancel")
    if cancel is not None:
        cancel.set()
    if _finish(job, status="timed_out", progress="timed out", error=message) and job.get("machine_id"):
        fly_machines.destroy_machine(job["machine_id"])


@router.get("/latest")
def latest_job(authed: str | None = Depends(require_operator)):
    """The operator's newest job, active or finished, so a refreshed
    browser reconnects to a run instead of starting another."""
    if not authed:
        raise HTTPException(401, "operator token required")
    with _LOCK:
        mine = [j for j in _JOBS.values() if j["operator_id"] == authed]
    for j in mine:
        _check_stale(j)
    if not mine:
        registry = OperatorRegistry()
        stored = sorted(_reports_dir(registry, authed).glob("job_*.json"), key=lambda p: p.stat().st_mtime)
        if not stored:
            return {"job": None}
        try:
            job = json.loads(stored[-1].read_text())
        except (OSError, ValueError):
            return {"job": None}
        return {"job": _public(job) if job.get("operator_id") == authed else None}
    newest = max(mine, key=lambda j: j["created_at"])
    return {"job": _public(newest)}


def _public(job: dict) -> dict:
    _check_stale(job)
    out = {k: v for k, v in job.items() if k != "operator_id" and not k.startswith("_")}
    out["stages"] = STAGES if job.get("sector") == "commercial" else [s for s in STAGES if s["key"] in ("preparing", "testing", "reporting")]
    out["reference"] = job["id"]
    if job.get("status") == "queued" and job.get("runner") != "machine":
        out["queue_position"] = _GATE.position(job["id"])
    if job.get("status") == "done" and job.get("summary") and not out.get("report"):
        out["report"] = _build_report(job, job["summary"])   # a job persisted before structured reports existed
    return out


def _get(job_id: str, authed: str | None) -> dict:
    if not authed:
        raise HTTPException(401, "operator token required")
    with _LOCK:
        job = _JOBS.get(job_id)
    if job is None:
        # process may have restarted: fall back to the stored report
        registry = OperatorRegistry()
        p = _reports_dir(registry, authed) / f"{job_id}.json"
        if not p.exists():
            raise HTTPException(404, "unknown job")
        job = json.loads(p.read_text())
    if job["operator_id"] != authed:
        raise HTTPException(404, "unknown job")
    return job


@router.get("/{job_id}")
def get_job(job_id: str, authed: str | None = Depends(require_operator)):
    return _public(_get(job_id, authed))


@router.post("/{job_id}/cancel", dependencies=[Depends(capability("runDiagnostic"))])
def cancel_job(job_id: str, authed: str | None = Depends(require_operator)):
    job = _get(job_id, authed)
    if job.get("status") in TERMINAL:
        return _public(job)
    cancel = job.get("_cancel")
    if cancel is not None:
        cancel.set()
    if _finish(job, status="cancelled", progress="cancelled", error=None) and job.get("machine_id"):
        fly_machines.destroy_machine(job["machine_id"])
    return _public(job)


@router.get("/{job_id}/report.json")
def report_json(job_id: str, authed: str | None = Depends(require_operator)):
    job = _get(job_id, authed)
    if job["status"] != "done" or not job.get("summary"):
        raise HTTPException(409, "report not ready")
    report = job.get("report") or _build_report(job, job["summary"])
    if report is None:
        raise HTTPException(500, "report could not be built")
    return report


@router.get("/{job_id}/report.pdf")
def report_pdf(job_id: str, authed: str | None = Depends(require_operator)):
    job = _get(job_id, authed)
    if job["status"] != "done" or not job.get("summary"):
        raise HTTPException(409, "report not ready")
    registry = OperatorRegistry()
    rec = registry.get_operator(authed)  # type: ignore[arg-type]
    pdf = render_report_pdf(rec.name, job)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="zaad-diagnostic-{job_id}.pdf"'})


def render_report_pdf(company: str, job: dict) -> bytes:
    """The PDF for a finished job: the structured report rendered by
    reports/diagnostic_pdf. Built from the stored report when there is
    one, else from the summary (older jobs)."""
    from reports.diagnostic_findings import build_report
    from reports.diagnostic_pdf import render_pdf
    report = job.get("report")
    if not report or report.get("company") != company:
        report = build_report(job["summary"], job_id=job["id"], company=company,
                              generated_at=job.get("finished_at") or _now())
    return render_pdf(report)


# ── worker-facing endpoints (private network + job-scoped token) ────────────
# Security review 2026-09 (SEC-006): a worker machine holds a token for its own job only — the HMAC of
# the job id under the worker secret — so a token cannot read another job's bundle or write another
# job's result; and the routes serve the private network only: a request that came through Fly's public
# proxy carries `Fly-Client-IP`, and is answered 404 whatever token it presents.

def job_token(job_id: str) -> str:
    secret = os.environ.get("HARVESTMIND_WORKER_TOKEN", "")
    if not secret:
        return ""
    return hmac.new(secret.encode(), job_id.encode(), hashlib.sha256).hexdigest()


def worker_token_ok(job_id: str, presented: str | None) -> bool:
    expected = job_token(job_id)
    return bool(expected) and bool(presented) and hmac.compare_digest(expected, presented or "")


def require_worker(job_id: str, request: Request, x_worker_token: str | None = Header(default=None)) -> None:
    if request.headers.get("fly-client-ip"):
        raise HTTPException(404, "unknown job")
    if not worker_token_ok(job_id, x_worker_token):
        raise HTTPException(401, "worker token required")


def _job_for_worker(job_id: str) -> dict:
    with _LOCK:
        job = _JOBS.get(job_id)
    if job is None or job.get("runner") != "machine":
        raise HTTPException(404, "unknown job")
    return job


@router.get("/internal/{job_id}/bundle", dependencies=[Depends(require_worker)])
def worker_bundle(job_id: str):
    """The workspace's non-empty staging tables as parquet in a zip, plus job meta."""
    from api.routers.intake import STAGING_TABLES
    job = _job_for_worker(job_id)
    if job.get("status") in TERMINAL:
        raise HTTPException(409, "job is no longer active")
    registry = OperatorRegistry()
    rec = registry.get_operator(job["operator_id"])
    dbm = DBManager(registry)
    buf = io.BytesIO()
    try:
        conn = dbm.get_operator_connection(job["operator_id"])
        with tempfile.TemporaryDirectory() as td, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("job.json", json.dumps({"id": job_id, "sector": job["sector"], "name": rec.name}))
            for table in STAGING_TABLES:
                row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # noqa: S608  # nosec B608 - allowlisted names
                if not row or not row[0]:
                    continue
                path = Path(td) / f"{table}.parquet"
                conn.execute(f"COPY (SELECT * FROM {table}) TO '{path}' (FORMAT PARQUET)")  # noqa: S608  # nosec B608
                zf.write(path, f"{table}.parquet")
    finally:
        try:
            dbm.close_all()
        except Exception:  # noqa: BLE001
            pass
    with _LOCK:
        if job.get("status") == "queued":
            job["status"] = "running"
            job["started_at"] = _now()
    _set(job, stage="preparing", progress="solver machine fetched the data")
    return Response(content=buf.getvalue(), media_type="application/zip")


@router.post("/internal/{job_id}/progress", dependencies=[Depends(require_worker)])
def worker_progress(job_id: str, body: dict = Body(...)):
    job = _job_for_worker(job_id)
    if job.get("status") in TERMINAL:
        return {"ok": False, "status": job["status"]}   # tells the machine to stop
    kw: dict = {"progress": str(body.get("progress", ""))[:200]}
    stage = body.get("stage")
    if isinstance(stage, str) and any(s["key"] == stage for s in STAGES):
        kw["stage"] = stage
    _set(job, **kw)
    return {"ok": True}


@router.post("/internal/{job_id}/result", dependencies=[Depends(require_worker)])
def worker_result(job_id: str, body: dict = Body(...)):
    job = _job_for_worker(job_id)
    if body.get("status") == "done" and body.get("summary"):
        _complete(job, body["summary"])
    else:
        _finish(job, status="failed", progress="failed", error=str(body.get("error", "worker failed"))[:300])
    return {"ok": True}
