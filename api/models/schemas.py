"""Pydantic request/response models for the HarvestMind API."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PlanningRequest(BaseModel):
    week_start: date = Field(..., description="ISO week Monday for the planning horizon")
    horizon_weeks: int = Field(default=4, ge=1, le=26)
    model_type: str = Field(
        default="gamma_robust",
        description=(
            "deterministic|gamma_robust on the legacy route; stochastic "
            "values are accepted only to return a migration error pointing "
            "to /planning/two-sided"
        ),
    )
    gamma: float = Field(default=4.0, ge=0, le=20)
    lambda_cvar: float = Field(default=0.5, ge=0, le=1)
    alpha_cvar: float = Field(default=0.95, ge=0.5, le=0.999)
    n_scenarios: int = Field(default=100, ge=10, le=500)

    @field_validator("model_type")
    @classmethod
    def valid_model(cls, v: str) -> str:
        allowed = {"deterministic", "gamma_robust", "two_stage_sp", "cvar", "robust_cvar"}
        if v not in allowed:
            raise ValueError(f"model_type must be one of {allowed}")
        return v


class CommitmentResponse(BaseModel):
    supplier_id: str
    product_id: str
    week_start: date
    committed_kg: float
    spot_kg: float
    price_per_kg: Optional[float]
    decision_stage: str
    # Unit-neutral aliases. The engine works in the product's base unit and
    # the domain names it; ``_kg`` fields are kept for compatibility.
    quantity: Optional[float] = None
    unit: str = "kg"
    explanation: Optional[list[str]] = None


class PlanningResponse(BaseModel):
    run_id: str
    audit_record: Optional[dict] = None
    unit: str = "kg"
    model_type: str
    week_start: date
    objective: Optional[float]
    solver_status: str
    solve_time_s: float
    expected_spot_kg: float
    expected_waste_kg: float
    commitments: list[CommitmentResponse]
    recommendations: list[dict]


class BacktestRequest(BaseModel):
    n_train_weeks: int = Field(default=52, ge=12, le=104)
    horizon_weeks: int = Field(default=4, ge=1, le=13)
    step_weeks: int = Field(default=4, ge=1, le=13)
    n_scenarios: int = Field(default=50, ge=10, le=200)
    gammas: list[float] = Field(default=[0, 2, 4, 6])
    run_stochastic: bool = Field(default=True)


class BacktestResponse(BaseModel):
    n_origins: int
    models_run: list[str]
    results_summary: list[dict]
    roi: Optional[dict]


class RecommendationResponse(BaseModel):
    rec_id: str
    rec_type: str
    priority: int
    headline: str
    detail: Optional[str]
    recommended_action: Optional[str]
    expected_impact_usd: Optional[float]
    status: str
