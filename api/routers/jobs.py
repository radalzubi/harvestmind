"""Background diagnostic jobs.

A diagnostic is the thing the front door promises: the operator's inferred
policy, a backtested comparison with a conservative lower bound, the lane
risk today, and a PDF that says all of it including "no material
improvement" when that is the answer. Solves can take minutes, so the job
runs in a worker thread against the operator's own vault and the UI polls.

  POST /jobs/diagnostic          operator: start (one at a time per operator)
  GET  /jobs/{id}                operator: status, progress, summary
  GET  /jobs/{id}/report.pdf     operator: the report
"""
from __future__ import annotations

import io
import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from api.dependencies import rate_limiter, require_operator
from infrastructure.db_manager import DBManager
from infrastructure.operator_registry import OperatorNotFoundError, OperatorRegistry

router = APIRouter(prefix="/jobs", tags=["jobs"])
log = logging.getLogger("harvestmind.jobs")
_JOBS: dict[str, dict] = {}
_LOCK = threading.Lock()


def _reports_dir(registry: OperatorRegistry, op: str) -> Path:
    d = registry.vault_dir(op) / "reports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _set(job: dict, **kw: Any) -> None:
    with _LOCK:
        job.update(kw)


def _run_commercial(conn, job: dict) -> dict:
    from api.routers.fmcg import _state_for, build_inputs
    from backtesting.counterfactual import EXTRA_CANDIDATES
    from backtesting.safe_selector import SafeSelectionConfig, safe_select
    from ingestion.pilot_readiness import assess
    import numpy as np
    _set(job, progress="checking readiness")
    ready = assess(conn)
    _set(job, progress="reading your history and inferring your current policy")
    fi, report = build_inputs(conn, horizon=12, train_weeks=52, service_level=0.97, holding_rate_per_week=None,
                              currency="USD", incumbent_cover_weeks=None)
    _set(job, progress="estimating the operating state and lane risk")
    est, src = _state_for(fi)
    fi.posture = est.posture
    _set(job, progress="backtesting candidates on your own history (this is the slow part)")
    decision = safe_select(fi, None, np.random.default_rng(0), SafeSelectionConfig(n_scen=20), posture=est.posture,
                           extra_candidates={"anchored_sp": EXTRA_CANDIDATES["anchored_sp"],
                                             "adaptive_sp": EXTRA_CANDIDATES["adaptive_sp"]})
    ev = decision.evidence.get(decision.mode_run)
    stats = ev.stats if ev is not None else {}
    summary = {
        "sector": "commercial",
        "readiness": {"verdict": getattr(ready, "verdict", None), "score": getattr(ready, "score", None),
                      "missing": list(getattr(ready, "missing_required", []) or [])[:12]},
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
    return summary


def _run_produce(conn, job: dict) -> dict:
    from backtesting.benchmark_suite import run_benchmark
    from ingestion.pilot_readiness import assess
    _set(job, progress="checking readiness")
    ready = assess(conn)
    _set(job, progress="rolling-origin benchmark on your own history (this is the slow part)")
    bench = run_benchmark(conn)
    return {
        "sector": "produce",
        "readiness": {"verdict": getattr(ready, "verdict", None), "score": getattr(ready, "score", None),
                      "missing": list(getattr(ready, "missing_required", []) or [])[:12]},
        "benchmark": {k: v for k, v in bench.items() if k in ("status", "gate_passed", "verdict", "weeks_available",
                                                               "weeks_required", "summary", "policies", "edge")},
        "decision": "stochastic two-sided plan" if bench.get("gate_passed") else "baseline retained",
        "reason": bench.get("verdict"),
        "warnings": [],
    }


def _worker(job: dict, op: str, sector: str) -> None:
    registry = OperatorRegistry()
    dbm = DBManager(registry)
    try:
        conn = dbm.get_operator_connection(op)
        summary = _run_commercial(conn, job) if sector == "commercial" else _run_produce(conn, job)
        path = _reports_dir(registry, op) / f"{job['id']}.json"
        path.write_text(json.dumps({**job, "summary": summary}, indent=1, default=str))
        _set(job, status="done", progress="report ready", summary=summary,
             finished_at=datetime.now(timezone.utc).isoformat())
    except Exception as exc:  # noqa: BLE001
        log.exception("diagnostic failed for %s", op)
        _set(job, status="failed", progress="failed", error=f"{type(exc).__name__}: {exc}"[:300],
             finished_at=datetime.now(timezone.utc).isoformat())
    finally:
        try:
            dbm.close_all()
        except Exception:  # noqa: BLE001
            pass


@router.post("/diagnostic", dependencies=[Depends(rate_limiter)])
def start_diagnostic(authed: str | None = Depends(require_operator)):
    if not authed:
        raise HTTPException(401, "operator token required")
    registry = OperatorRegistry()
    try:
        rec = registry.get_operator(authed)
    except OperatorNotFoundError:
        raise HTTPException(404, "unknown operator")
    with _LOCK:
        running = [j for j in _JOBS.values() if j["operator_id"] == authed and j["status"] in ("queued", "running")]
    if running:
        return _public(running[0])
    job_id = f"job_{uuid.uuid4().hex[:10]}"
    job: dict = {"id": job_id, "operator_id": authed, "kind": "diagnostic",
           "sector": getattr(rec, "sector", "produce"), "status": "running", "progress": "starting",
           "created_at": datetime.now(timezone.utc).isoformat(), "finished_at": None, "error": None, "summary": None}
    with _LOCK:
        _JOBS[job_id] = job
    threading.Thread(target=_worker, args=(job, authed, job["sector"]), daemon=True).start()
    return _public(job)


def _public(job: dict) -> dict:
    return {k: v for k, v in job.items() if k != "operator_id"}


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


@router.get("/{job_id}/report.pdf")
def report_pdf(job_id: str, authed: str | None = Depends(require_operator)):
    job = _get(job_id, authed)
    if job["status"] != "done" or not job.get("summary"):
        raise HTTPException(409, "report not ready")
    registry = OperatorRegistry()
    rec = registry.get_operator(authed)  # type: ignore[arg-type]
    pdf = render_report_pdf(rec.name, job)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="harvestmind-diagnostic-{job_id}.pdf"'})


def _pct(x: Any) -> str:
    return "n/a" if x is None else f"{float(x):+.1%}"


def render_report_pdf(company: str, job: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    s = job["summary"]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm,
                            title=f"Zaad Supply diagnostic: {company}")
    ink = colors.HexColor("#111111")
    grey = colors.HexColor("#555555")
    rule = colors.HexColor("#CCCCCC")
    H1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=ink, spaceAfter=4)
    H2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12.5, leading=16, textColor=ink, spaceBefore=14, spaceAfter=6)
    P = ParagraphStyle("p", fontName="Helvetica", fontSize=10, leading=14, textColor=ink)
    S = ParagraphStyle("s", parent=P, textColor=grey, fontSize=9, leading=12)
    el: list = [Paragraph(f"Zaad Supply diagnostic: {company}", H1),
                Paragraph(f"Sector {s.get('sector')} · run {job['id']} · {str(job.get('finished_at') or '')[:10]} · "
                          "a backtest on your own history against your own policy, not a forecast of savings", S)]

    def table(rows, widths):
        t = Table(rows, colWidths=widths)
        t.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), "Helvetica", 9.5), ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9.5),
                               ("LINEBELOW", (0, 0), (-1, 0), 0.8, ink), ("LINEBELOW", (0, 1), (-1, -1), 0.4, rule),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
        return t

    r = s.get("readiness") or {}
    el += [Paragraph("1. Data readiness", H2),
           Paragraph(f"Verdict: <b>{r.get('verdict')}</b>. " + (f"Missing: {', '.join(r['missing'])}." if r.get("missing") else "Nothing required is missing."), P)]
    if s.get("sector") == "commercial":
        el += [Paragraph("2. How you order today", H2),
               Paragraph(f"{s.get('incumbent')} · {s.get('history_periods')} weeks of history · {s.get('products')} products · {s.get('suppliers')} suppliers", P)]
        for n in (s.get("incumbent_notes") or [])[:4]:
            el.append(Paragraph(f"• {n}", S))
        imp = s.get("improvement") or {}
        el += [Paragraph("3. What a safe optimizer would have done on your history", H2),
               Paragraph(f"Decision: <b>{s.get('decision')}</b>. {s.get('reason')}", P)]
        if imp:
            el.append(Paragraph(f"Mean cost change vs your policy {_pct(imp.get('mean'))}; conservative lower bound "
                                f"{_pct(imp.get('lower_bound'))}; worst fold {_pct(imp.get('worst'))} over {imp.get('n_folds')} folds. "
                                "Positive is a cost reduction.", P))
        cands = s.get("candidates") or {}
        if cands:
            rows = [["Candidate", "Mean vs your policy", "Lower bound", "Cleared the gate"]]
            for k, v in cands.items():
                rows.append([k, _pct(v.get("mean")), _pct(v.get("lower_bound")), "yes" if v.get("passed") else "no"])
            el.append(table(rows, [55*mm, 40*mm, 35*mm, 35*mm]))
        st = s.get("state") or {}
        el += [Paragraph("4. Your operating state and supply lanes today", H2),
               Paragraph(f"Mode <b>{st.get('mode')}</b>, dominant regime {st.get('dominant')}, probability of a disruptive regime "
                         f"{float(st.get('p_disruptive') or 0):.0%}, stress {float(st.get('stress') or 0):.2f}.", P)]
        for n in (st.get("reasons") or [])[:5]:
            el.append(Paragraph(f"• {n}", S))
        lanes = s.get("lanes") or {}
        if lanes:
            rows = [["Lane", "Risk", "Evidence quality", "Why"]]
            for k, v in lanes.items():
                rows.append([k, f"{float(v.get('risk') or 0):.0%}", f"{float(v.get('quality') or 0):.2f}", "; ".join(v.get("reasons") or [])[:110]])
            el.append(table(rows, [25*mm, 18*mm, 28*mm, 100*mm]))
        pri = s.get("priors_in_use") or {}
        el += [Paragraph("5. Assumptions and priors used", H2)]
        if pri:
            for k, v in list(pri.items())[:10]:
                el.append(Paragraph(f"• {k}: {v.get('source')} ({v.get('provenance')}); {v.get('note')}", S))
        else:
            el.append(Paragraph("No public priors were needed; every supplier had enough receipts.", S))
        for k, v in (s.get("provenance") or {}).items():
            el.append(Paragraph(f"• {k}: {v}", S))
    else:
        b = s.get("benchmark") or {}
        el += [Paragraph("2. Rolling-origin benchmark on your history", H2),
               Paragraph(f"Decision: <b>{s.get('decision')}</b>. {s.get('reason')}", P),
               Paragraph(f"Status {b.get('status')} · gate passed {b.get('gate_passed')} · weeks available {b.get('weeks_available')} of {b.get('weeks_required')} required", S)]
        summ = b.get("summary")
        if isinstance(summ, dict):
            for k, v in list(summ.items())[:12]:
                el.append(Paragraph(f"• {k}: {v}", S))
    if s.get("warnings"):
        el += [Paragraph("Notes", H2)] + [Paragraph(f"• {w}", S) for w in s["warnings"][:10]]
    el += [Spacer(1, 10), Paragraph("Every number above is measured on your own uploaded history with identifiers pseudonymised. "
                                     "It is not a promise about the future.", S)]
    doc.build(el)
    return buf.getvalue()
