"""Admin API — operator token issuance.

Protected by a shared admin key (`HARVESTMIND_ADMIN_KEY`). The endpoint is
FAIL-CLOSED: if the key is not configured the admin API is disabled entirely,
so it can never become an open token-minting (auth-bypass) hole. Intended for
operator onboarding / key rotation, called by an operator/CLI, not the app UI.
"""

from __future__ import annotations

import hmac
import os

from fastapi import APIRouter, Depends, Header, HTTPException

router = APIRouter(prefix="/admin", tags=["admin"])


def _admin_key() -> str | None:
    return os.getenv("HARVESTMIND_ADMIN_KEY") or None


def require_admin(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> bool:
    key = _admin_key()
    if not key:
        # Unconfigured → disabled. 404 avoids advertising the surface.
        raise HTTPException(status_code=404, detail="Not found")
    if not x_admin_key or not hmac.compare_digest(x_admin_key, key):
        raise HTTPException(status_code=401, detail="Invalid admin key")
    return True


@router.post("/operators/{operator_id}/token",
             dependencies=[Depends(require_admin)])
def issue_operator_token(operator_id: str):
    """Issue (or rotate) an operator's API token. Returns the raw token ONCE —
    it is stored only as a hash and cannot be recovered later."""
    from infrastructure.operator_registry import (
        OperatorNotFoundError, OperatorRegistry,
    )

    registry = OperatorRegistry()
    try:
        registry.get_operator(operator_id)
    except OperatorNotFoundError:
        raise HTTPException(status_code=404,
                            detail=f"Unknown operator {operator_id!r}")
    token = registry.issue_token(operator_id)
    return {
        "operator_id": operator_id,
        "token": token,
        "note": "Store this token now — it cannot be recovered. "
                "Send it as 'Authorization: Bearer <token>'.",
    }
