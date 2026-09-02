"""HarvestMind FastAPI application."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import planning, backtest, data, fsma, reports, diagnostics, intake, forecasts, training, pool, admin

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

app.include_router(planning.router)
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


@app.get("/health")
def health():
    return {"status": "ok", "service": "harvestmind-api"}


@app.get("/")
def root():
    return {
        "name": "HarvestMind",
        "version": "0.1.0",
        "docs": "/docs",
    }
