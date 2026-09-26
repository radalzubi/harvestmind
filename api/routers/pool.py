"""Data pool API: status, consent toggle, plain-English explanation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import capability, require_operator

router = APIRouter(prefix="/pool", tags=["pool"])


@router.get("/status")
def pool_status(operator_id: str | None = None,
                authed: str | None = Depends(require_operator)):
    """Pool size + (when operator_id given) this operator's status.

    In enforced-auth mode the operator is taken from the API token; the
    query param is a dev-only fallback and never overrides the token.
    """
    from pool.pool_reader import PoolReader

    operator_id = authed or operator_id
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


@router.post("/consent", dependencies=[Depends(capability("manageSettings"))])
def set_pool_consent(consented: bool, operator_id: str | None = None,
                     authed: str | None = Depends(require_operator)):
    """Dashboard toggle. Withdrawal stops future contributions
    immediately; anonymized prior contributions remain (irreversible by
    design — see docs/POOL_PRIVACY.md).

    In enforced-auth mode the operator is taken from the API token, so a
    caller can only toggle their OWN consent (closes the cross-operator
    consent-flip IDOR)."""
    from infrastructure.consent_manager import ConsentManager
    from infrastructure.operator_registry import (
        OperatorNotFoundError, OperatorRegistry,
    )
    operator_id = authed or operator_id
    if operator_id is None:
        raise HTTPException(status_code=400, detail="operator_id required")
    try:
        registry = OperatorRegistry()
        rec = ConsentManager(registry).record_consent(
            operator_id, consented, method="dashboard_toggle")
    except OperatorNotFoundError:
        raise HTTPException(status_code=404,
                            detail=f"Unknown operator {operator_id!r}")
    return {"operator_id": operator_id, "pool_consent": rec.consented,
            "note": rec.withdrawal_note}
