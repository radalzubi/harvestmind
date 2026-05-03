"""HarvestMind FastAPI application."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import planning, backtest, data, reports

app = FastAPI(
    title="HarvestMind API",
    description="Stochastic supply planning for Midwest fresh produce distributors",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(planning.router)
app.include_router(backtest.router)
app.include_router(data.router)
app.include_router(reports.router)


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
