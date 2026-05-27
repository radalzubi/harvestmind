"""HarvestMind FastAPI application."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import planning, backtest, data, fsma, reports, diagnostics, intake

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

app.include_router(planning.router)
app.include_router(backtest.router)
app.include_router(data.router)
app.include_router(fsma.router)
app.include_router(reports.router)
app.include_router(diagnostics.router)
app.include_router(intake.router)


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
