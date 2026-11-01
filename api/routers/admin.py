"""Admin API — operator token issuance.

Protected by a shared admin key (`HARVESTMIND_ADMIN_KEY`). The endpoint is
FAIL-CLOSED: if the key is not configured the admin API is disabled entirely,
so it can never become an open token-minting (auth-bypass) hole. Intended for
operator onboarding / key rotation, called by an operator/CLI, not the app UI.
"""

from __future__ import annotations

import hmac
import logging
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
    logging.getLogger("harvestmind.security").info("security event=token_rotated operator=%s", operator_id)
    return {
        "operator_id": operator_id,
        "token": token,
        "note": "Store this token now — it cannot be recovered. "
                "Send it as 'Authorization: Bearer <token>'.",
    }


@router.post("/operators/{operator_id}/actors", dependencies=[Depends(require_admin)])
def issue_actor_token(operator_id: str, body: dict):
    """A token for one named person in a workspace, with a role (Operating Product V2).

    Returns the raw token ONCE. The workspace's own token remains its pilot administrator.
    """
    from infrastructure.operator_registry import OperatorNotFoundError, OperatorRegistry
    from api.product.governance import ROLES
    name = str(body.get("name") or "").strip()
    role = str(body.get("role") or "").upper()
    if role not in ROLES:
        raise HTTPException(status_code=422, detail=f"role is one of {', '.join(ROLES)}")
    registry = OperatorRegistry()
    try:
        actor_id, token = registry.issue_actor_token(operator_id, name, role)
    except OperatorNotFoundError:
        raise HTTPException(status_code=404, detail=f"Unknown operator {operator_id!r}")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    logging.getLogger("harvestmind.security").info("security event=actor_issued operator=%s actor=%s role=%s", operator_id, actor_id, role)
    return {"operator_id": operator_id, "actor_id": actor_id, "name": name, "role": role, "token": token,
            "note": "Store this token now — it cannot be recovered. Send it as 'Authorization: Bearer <token>'."}


@router.post("/operators/{operator_id}/offboard", dependencies=[Depends(require_admin)])
def offboard_operator(operator_id: str, body: dict):
    """Remove one workspace's data from every ZAAD-controlled store (docs/security/TENANT_OFFBOARDING_RUNBOOK.md).

    Dry run unless `execute` is true **and** `confirm_operator_id` repeats the exact operator id. Running inside the
    API also clears this process's caches for the tenant (analytics results, diagnostic job entries) and releases the
    vault's open connection, which the command-line tool cannot reach. The response is counts, ids and paths only.
    """
    from infrastructure.offboarding import Offboarding, Refused
    from infrastructure.operator_registry import OperatorRegistry
    from api.analytics import cache as analytics_cache
    from api.routers import jobs as jobs_router

    def _drop_job_entries(op: str) -> int:
        with jobs_router._LOCK:  # noqa: SLF001
            victims = [k for k, v in jobs_router._JOBS.items() if v.get("operator_id") == op]  # noqa: SLF001
            for k in victims:
                jobs_router._JOBS.pop(k, None)  # noqa: SLF001
        return len(victims)

    execute = bool(body.get("execute"))
    confirm = str(body.get("confirm_operator_id") or "")
    off = Offboarding(OperatorRegistry(), cache_clearers={"analytics_results": analytics_cache.clear, "diagnostic_jobs": _drop_job_entries})
    try:
        res = off.execute(operator_id, confirm, actor="admin") if execute else off.plan(operator_id)
    except Refused as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    logging.getLogger("harvestmind.security").info("security event=offboarding operator=%s mode=%s status=%s", operator_id, res.mode, res.status)
    return res.to_dict()
