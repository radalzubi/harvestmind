"""HarvestMind FastAPI application."""
from __future__ import annotations

import logging as _logging
import uuid as _uuid

from fastapi import Request as _Request
from fastapi.responses import JSONResponse as _JSONResponse

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import fmcg, planning, backtest, data, fsma, reports, diagnostics, intake, forecasts, training, pool, admin, access, jobs

app = FastAPI(
    title="HarvestMind API",
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Admin-Key", "Accept"],
)


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
    from api.dependencies import assert_safe_to_serve
    assert_safe_to_serve()


app.include_router(planning.router)
app.include_router(fmcg.router)
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
app.include_router(access.router)
app.include_router(jobs.router)


@app.get("/health")
def health():
    """Liveness plus security posture, so a deployment can be checked from
    outside rather than trusted. Never includes secrets or paths."""
    from api.dependencies import auth_posture
    return {"status": "ok", "service": "harvestmind-api", **auth_posture()}


@app.get("/ready")
def ready():
    """Readiness: the root database opens and the solver is importable."""
    import duckdb
    from api.dependencies import get_db_path
    checks = {}
    try:
        conn = duckdb.connect(get_db_path(), read_only=True)
        conn.execute("SELECT 1").fetchone()
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
        "name": "HarvestMind",
        "version": "0.1.0",
        "docs": "/docs",
    }
