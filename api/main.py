"""ZAAD API application (repository name harvestmind is the internal, historical name)."""
from __future__ import annotations

import logging

import logging as _logging
import uuid as _uuid

from fastapi import Request as _Request
from fastapi.responses import JSONResponse as _JSONResponse

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from api.product.drafts import DraftRefused
from api.routers import zaad_insights, zaad_analytics
from api.routers import assistant, fmcg, planning, backtest, data, fsma, reports, diagnostics, intake, forecasts, training, pool, admin, access, jobs, zaad, zaad_full, zaad_atp, zaad_workspace, zaad_orders, zaad_history

app = FastAPI(
    title="Zaad Supply API",
    description="Available-to-promise and traceability diagnostics for perishable produce operators",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allowlist driven by env var. Defaults to local development origins
# only; production deployments must set CORS_ALLOWED_ORIGINS explicitly.
# Set CORS_ALLOWED_ORIGINS="*" only for local pilots — never for shared
# environments handling partner data.
_cors_env = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost,http://localhost:3000,http://localhost:5173,"
    "http://localhost:8000,http://localhost:8501,"
    "http://127.0.0.1,http://127.0.0.1:8000,http://127.0.0.1:8501",
)
_cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()]
# Never honor a wildcard origin for a partner-data API — drop "*" if present.
# Production must set an explicit CORS_ALLOWED_ORIGINS allowlist.
_cors_origins = [o for o in _cors_origins if o != "*"]
if not _cors_origins:
    # Enforced-auth (production) deployments must configure origins explicitly;
    # fall back to the localhost allowlist only for dev.
    _cors_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]



@app.middleware("http")
async def security_headers(request, call_next):
    """Baseline security response headers.

    Behaviour-preserving (headers only). The report endpoints return
    operator-branded HTML, so framing/MIME-sniff protection matters even
    in a localhost pilot. HSTS is harmless over plain HTTP and takes
    effect once the deployment is fronted by TLS.
    """
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Strict-Transport-Security", "max-age=63072000; includeSubDomains"
    )
    return response

# ── Request ids, structured error boundary ───────────────────────────────────
# Every response carries X-Request-ID. An unhandled exception is logged
# server-side WITH its traceback under that id and answered with a generic
# message carrying only the id, so an operator can quote it to support and a
# stack trace never reaches a browser. Validation and HTTP errors keep their
# curated `detail`.
_log = _logging.getLogger("harvestmind.api")


@app.middleware("http")
async def _request_id_middleware(request: _Request, call_next):
    rid = request.headers.get("X-Request-ID") or f"req-{_uuid.uuid4().hex[:12]}"
    request.state.request_id = rid
    try:
        response = await call_next(request)
    except Exception:  # noqa: BLE001  boundary: log with traceback, answer generically
        _log.exception("unhandled error request_id=%s path=%s", rid, request.url.path)
        return _JSONResponse(status_code=500, headers={"X-Request-ID": rid},
                             content={"detail": "Internal error. Quote this request id to support.",
                                      "request_id": rid})
    response.headers["X-Request-ID"] = rid
    return response


@app.on_event("startup")
async def _refuse_permissive_public_bind() -> None:
    try:
        from infrastructure.seed_workspaces import seed_workspaces_from_env
        seed_workspaces_from_env()
    except Exception:  # noqa: BLE001  seeding must never block startup
        logging.getLogger("harvestmind.api").exception("workspace seeding failed")
    from api.dependencies import assert_safe_to_serve
    assert_safe_to_serve()


@app.on_event("shutdown")
async def _checkpoint_vaults() -> None:
    """A clean stop folds every idle vault's write-ahead log into its file."""
    try:
        from infrastructure.db_manager import checkpoint_all
        checkpoint_all()
    except Exception:  # noqa: BLE001  shutdown must never fail on this
        logging.getLogger("harvestmind.api").exception("vault checkpoint on shutdown failed")


@app.exception_handler(DraftRefused)
async def _draft_refused(request: _Request, exc: DraftRefused) -> _JSONResponse:
    """A refused proposal is a message to the buyer, never a 500.

    Most order endpoints catch this themselves; a few read-only ones (the export formats, one
    proposal, an evaluation) reach it only through `ensure_tables`, which refuses when a vault has
    not been migrated for proposed orders. Handling it here means an endpoint added later cannot
    turn the same refusal back into an internal error.
    """
    return _JSONResponse(status_code=422,
                         content={"detail": {"code": "proposal_refused", "message": str(exc)}})


# The methods this API actually serves. It was GET/POST/OPTIONS, which was true until the operating
# product declared PATCH (edit a proposal), PUT (update an export format) and DELETE (remove
# either) — and a browser's preflight for an unlisted method is answered 400, so those three write
# paths could not work from the interface at all. Server-side tests never see it: a test client
# does not preflight. Still an allowlist, still no wildcard, still no credentials.
#
# CORS is added LAST so that it is the OUTERMOST middleware. Starlette wraps middleware in the
# reverse order of registration, and the error boundary below must sit *inside* CORS: a 500 it
# produces then passes back out through CORS and carries `Access-Control-Allow-Origin`. When CORS
# was innermost, an unhandled error reached the browser with no CORS headers at all, so the page
# saw only "Failed to fetch" and could not read the request id the error copy tells people to
# quote. `tests/integration/test_api_error_boundary.py` holds this.
# Response compression (performance pass, SERIALIZATION). The workspace read the web makes on every
# open (`/api/zaad/network/request/from-workspace`) is 3.6 MB of JSON for the 150-product sample
# and a completed plan's report is 50-330 KB; both are text that compresses about ten to one.
# Registered before CORS so that CORS stays the outermost middleware (see below). The security-
# header middleware streams every response, so the 1 KB floor does not apply and small bodies are
# compressed too (microseconds); nothing about the JSON itself changes.
app.add_middleware(GZipMiddleware, minimum_size=1024)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Admin-Key", "Accept"],
    # Cross-origin JavaScript can read only the six "simple" response headers unless the server
    # says otherwise — and the web app is on a different origin from this API in every deployment.
    # `Content-Disposition` carries the filename the operator's own export profile produced, so
    # without it every exported file downloaded as "purchase-order" with no extension; the request
    # id is what the error copy tells a person to quote to support; and `X-ZAAD-Transmitted` is an
    # assertion this product makes, which a reviewer should be able to check from the browser.
    expose_headers=["Content-Disposition", "X-Request-ID", "X-ZAAD-Transmitted"],
)


app.include_router(planning.router)
app.include_router(fmcg.router)
app.include_router(zaad.router)
app.include_router(zaad_full.router)
app.include_router(zaad_atp.router)   # P5 ATP (default off: ZAAD_ATP_ENABLED=1)
app.include_router(zaad_workspace.router)  # operating product: read-only projections of the vault
app.include_router(zaad_orders.router)     # operating product: proposed orders, evaluation, export
app.include_router(zaad_history.router)    # operating product V2: audit, responses, outcomes, settings, telemetry
app.include_router(zaad_insights.router)   # operating product V2.1A: server-side aggregations, latest plan read back
app.include_router(zaad_analytics.router)  # enterprise analytics V1: semantic model, typed queries, saved analyses, dashboards, Ask ZAAD, hand-off
app.include_router(backtest.router)
app.include_router(data.router)
app.include_router(fsma.router)
app.include_router(reports.router)
app.include_router(diagnostics.router)
app.include_router(intake.router)
app.include_router(forecasts.router)
app.include_router(training.router)
app.include_router(pool.router)
app.include_router(admin.router)
app.include_router(assistant.router)
app.include_router(access.router)
app.include_router(jobs.router)


@app.get("/health")
def health():
    """Liveness plus security posture, so a deployment can be checked from
    outside rather than trusted. Never includes secrets or paths."""
    from api.dependencies import auth_posture
    return {"status": "ok", "service": "zaad-api", **auth_posture()}


@app.get("/ready")
def ready():
    """Readiness: the root database opens and the solver is importable."""
    from api.dependencies import get_db_path
    from infrastructure.db_manager import vault_cursor
    checks = {}
    try:
        conn = vault_cursor(get_db_path())
        try:
            conn.execute("SELECT 1").fetchone()
        finally:
            conn.close()
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["database"] = f"unavailable: {type(exc).__name__}"
    try:
        import highspy  # noqa: F401
        checks["solver"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["solver"] = f"unavailable: {type(exc).__name__}"
    ok = all(v == "ok" for v in checks.values())
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=200 if ok else 503,
                        content={"status": "ready" if ok else "not_ready", **checks})


@app.get("/")
def root():
    return {
        "name": "Zaad Supply",
        "version": "0.1.0",
        "docs": "/docs",
    }
