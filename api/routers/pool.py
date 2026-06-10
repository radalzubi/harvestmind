"""Data pool API: status, consent toggle, plain-English explanation."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/pool", tags=["pool"])


@router.get("/status")
def pool_status(operator_id: str | None = None):
    """Pool size + (when operator_id given) this operator's status."""
    from pool.pool_reader import PoolReader

    stats = PoolReader().get_pool_stats().model_dump()
    out = {"pool": stats}
    if operator_id is not None:
        from infrastructure.operator_registry import (
            OperatorNotFoundError, OperatorRegistry,
        )
        try:
            rec = OperatorRegistry().get_operator(operator_id)
        except OperatorNotFoundError:
            raise HTTPException(status_code=404,
                                detail=f"Unknown operator {operator_id!r}")
        out["operator"] = {
            "operator_id": rec.operator_id,
            "pool_consent": rec.pool_consent,
            "pool_contribution_count": rec.pool_contribution_count,
        }
    return out


@router.post("/consent")
def set_pool_consent(operator_id: str, consented: bool):
    """Dashboard toggle. Withdrawal stops future contributions
    immediately; anonymized prior contributions remain (irreversible by
    design — see docs/POOL_PRIVACY.md)."""
    from infrastructure.consent_manager import ConsentManager
    from infrastructure.operator_registry import (
        OperatorNotFoundError, OperatorRegistry,
    )
    try:
        registry = OperatorRegistry()
        rec = ConsentManager(registry).record_consent(
            operator_id, consented, method="dashboard_toggle")
    except OperatorNotFoundError:
        raise HTTPException(status_code=404,
                            detail=f"Unknown operator {operator_id!r}")
    return {"operator_id": operator_id, "pool_consent": rec.consented,
            "note": rec.withdrawal_note}
