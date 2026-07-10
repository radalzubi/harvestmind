"""FastAPI dependency injection: database connection and shared state."""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
from fastapi import Depends, Header, HTTPException, Request


ROOT = Path(__file__).resolve().parents[1]


def auth_required() -> bool:
    """Whether the API enforces operator authentication.

    Default OFF (localhost / dev, preserving existing behavior). Set
    HARVESTMIND_AUTH_REQUIRED=true in any networked/pilot deployment: then
    every operator-scoped request MUST carry a valid API token and
    `operator_id` is taken from that token, never from a query/body param.
    Read live (not cached) so tests and deployments can flip it via env.
    """
    return os.getenv("HARVESTMIND_AUTH_REQUIRED", "false").lower() == "true"


def _token_from_headers(authorization: str | None, x_api_key: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    if x_api_key:
        return x_api_key.strip()
    return None


def authenticate_operator(
    authorization: str | None = None,
    x_api_key: str | None = None,
) -> str | None:
    """Core auth logic (plain Python, callable in tests).

    Returns the token's operator_id when a valid token is presented (in any
    mode); returns None when no token is presented and auth is not enforced
    (dev fallback — callers then use their legacy param); raises 401 when a
    token is invalid, or when none is presented and auth IS enforced.
    """
    token = _token_from_headers(authorization, x_api_key)
    if token:
        from infrastructure.operator_registry import OperatorRegistry
        oid = OperatorRegistry().operator_id_for_token(token)
        if oid is None:
            raise HTTPException(status_code=401, detail="Invalid API token")
        return oid
    if auth_required():
        raise HTTPException(status_code=401, detail="Authentication required")
    return None


def require_operator(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str | None:
    """FastAPI dependency wrapper around :func:`authenticate_operator`."""
    return authenticate_operator(authorization, x_api_key)


# ── Rate limiting (heavy/expensive endpoints) ────────────────────────────────
# Minimal per-process fixed-window limiter, no external dependency. Disabled by
# default (HARVESTMIND_RATE_LIMIT_PER_MIN=0) so dev/tests are unaffected; set a
# positive value in production to cap abuse of the CPU/LLM-heavy endpoints.
_RL_BUCKETS: dict = {}


def rate_limiter(request: Request) -> None:
    """FastAPI dependency: cap requests/min per client IP + path.

    No-op unless HARVESTMIND_RATE_LIMIT_PER_MIN > 0, so dev/tests are
    unaffected. 429 when the per-minute cap is exceeded.
    """
    limit = int(os.getenv("HARVESTMIND_RATE_LIMIT_PER_MIN", "0"))
    if limit <= 0:
        return
    import time
    now = time.time()
    client = getattr(request, "client", None)
    ip = client.host if client else "unknown"
    key = (ip, request.url.path)
    bucket = [t for t in _RL_BUCKETS.get(key, []) if now - t < 60.0]
    if len(bucket) >= limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    bucket.append(now)
    _RL_BUCKETS[key] = bucket


def get_db_path() -> str:
    return os.getenv("DUCKDB_PATH", str(ROOT / "harvestmind.duckdb"))


def _resolve_operator(operator_id: str | None, authed: str | None) -> str | None:
    """Authenticated principal wins over a dev-only query param."""
    return authed or operator_id


def get_conn(
    operator_id: str | None = None,
    authed: str | None = Depends(require_operator),
):
    """Yield a per-request DuckDB connection, closed after the response.

    Operator-aware: when an operator is resolved (from the API token, or the
    dev-only ?operator_id= param) the connection is that operator's isolated
    VAULT; otherwise it is the legacy root DB (dev). Test suites that override
    this dependency are unaffected (the override replaces the whole callable).
    """
    op = _resolve_operator(operator_id, authed)
    if op is None:
        conn = duckdb.connect(get_db_path())
        try:
            yield conn
        finally:
            conn.close()
        return
    from infrastructure.db_manager import DBManager
    from infrastructure.operator_registry import (
        OperatorNotFoundError, OperatorRegistry,
    )
    try:
        dbm = DBManager(OperatorRegistry())
        conn = dbm.get_operator_connection(op)
    except (OperatorNotFoundError, FileNotFoundError):
        raise HTTPException(status_code=404, detail=f"Unknown operator {op!r}")
    try:
        yield conn
    finally:
        dbm.close_all()


def get_readonly_conn(
    operator_id: str | None = None,
    authed: str | None = Depends(require_operator),
):
    """Read-only counterpart of get_conn. Operator-aware (vault when an
    operator is resolved, else the root DB)."""
    op = _resolve_operator(operator_id, authed)
    if op is None:
        conn = duckdb.connect(get_db_path(), read_only=True)
        try:
            yield conn
        finally:
            conn.close()
        return
    from infrastructure.db_manager import DBManager
    from infrastructure.operator_registry import (
        OperatorNotFoundError, OperatorRegistry,
    )
    try:
        dbm = DBManager(OperatorRegistry())
        conn = dbm.get_read_only_connection(op)
    except (OperatorNotFoundError, FileNotFoundError):
        raise HTTPException(status_code=404, detail=f"Unknown operator {op!r}")
    try:
        yield conn
    finally:
        dbm.close_all()


def get_request_conn(operator_id: str | None = None, root_conn=None):
    """Resolve the connection for a request.

    - operator_id absent → the legacy single-operator root DB (dev mode;
      all existing flows unchanged).
    - operator_id present → the operator's VAULT database via the
      registry/DBManager. Unknown ids raise 404. This is the only way an
      API request reaches a vault — no endpoint opens vault files itself.
    """
    from fastapi import HTTPException

    if operator_id is None:
        yield from get_conn()
        return

    from infrastructure.db_manager import DBManager
    from infrastructure.operator_registry import (
        OperatorNotFoundError, OperatorRegistry,
    )
    try:
        dbm = DBManager(OperatorRegistry())
        conn = dbm.get_operator_connection(operator_id)
    except (OperatorNotFoundError, FileNotFoundError):
        raise HTTPException(status_code=404,
                            detail=f"Unknown operator {operator_id!r}")
    try:
        yield conn
    finally:
        dbm.close_all()
