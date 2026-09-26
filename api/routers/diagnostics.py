"""Diagnostics API router.

Single endpoint: GET /diagnostics/summary
Returns the full diagnostic payload from diagnostic_metrics.py.
This is the primary data source for the Overview page and Report Export.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.dependencies import get_conn
from dashboard.lib.diagnostic_metrics import (
    atp_by_product,
    buyer_fulfillment_rates,
    diagnostic_summary,
    recommendations_by_product,
    shortage_loss_usd,
    supplier_reliability_scores,
    traceability_coverage,
    waste_loss_usd,
)

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


@router.get("/summary")
def get_diagnostic_summary(
    partner_name: str = Query(default="Operator", description="Hub or operator name"),
    days: int = Query(default=365, ge=1, le=3650, description="Lookback window in days"),
    conn=Depends(get_conn),
):
    """Full diagnostic payload: waste loss, shortage loss, supplier reliability,
    buyer fulfillment, traceability coverage, ATP, recommendations, and savings.

    This is the single authoritative data pull for all dashboard panels.
    """
    return json_safe(diagnostic_summary(conn, partner_name=partner_name, days=days))


def json_safe(value):
    """NaN and infinities are not JSON; a metric that could not be computed is null, never a 500
    (security review 2026-09, SEC-037)."""
    import math
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


@router.get("/waste")
def get_waste_loss(
    days: int = Query(default=365, ge=1, le=3650),
    conn=Depends(get_conn),
):
    """Waste loss detail: total USD, by product, by reason."""
    return waste_loss_usd(conn, days=days)


@router.get("/shortage")
def get_shortage_loss(
    days: int = Query(default=365, ge=1, le=3650),
    conn=Depends(get_conn),
):
    """Shortage loss detail: total USD, by product, by buyer."""
    return shortage_loss_usd(conn, days=days)


@router.get("/suppliers")
def get_supplier_reliability(conn=Depends(get_conn)):
    """Per-supplier fill rate, rejection rate, and risk level."""
    return supplier_reliability_scores(conn)


@router.get("/buyers")
def get_buyer_fulfillment(conn=Depends(get_conn)):
    """Per-buyer fulfillment rate, substitution rate, missed rate."""
    return buyer_fulfillment_rates(conn)


@router.get("/traceability")
def get_traceability_coverage(conn=Depends(get_conn)):
    """Lot-level traceability completeness score and missing-field breakdown."""
    return traceability_coverage(conn)


@router.get("/atp")
def get_atp(conn=Depends(get_conn)):
    """Available-to-promise per product: usable stock, committed, near-expiry."""
    return atp_by_product(conn)


@router.get("/recommendations")
def get_recommendations(conn=Depends(get_conn)):
    """Per-product commitment recommendations with plain-English text."""
    return recommendations_by_product(conn)
