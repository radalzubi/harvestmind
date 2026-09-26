"""FastAPI dependency injection: database connection and shared state."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import Depends, Header, HTTPException, Request


ROOT = Path(__file__).resolve().parents[1]


_ENFORCED_ENVS = ("pilot", "prod", "production", "staging")


def deployment_env() -> str:
    """HARVESTMIND_ENV: dev (default), pilot, staging or prod."""
    return os.getenv("HARVESTMIND_ENV", "dev").strip().lower() or "dev"


def legacy_planners_enabled() -> bool:
    """Whether the superseded planning engines (the first ZAAD engine under /api/zaad and the
    safe-selector purchase plan under /fmcg/plan modes other than canonical) are served.

    FAIL-CLOSED OUTSIDE DEV: the canonical product exposes one planning engine, the frozen P1
    optimizer (/api/zaad/network and /fmcg/plan?mode=canonical). Set ZAAD_LEGACY_PLANNERS=1 to keep
    the legacy engines reachable (dev workspaces, migration of the old pages); ZAAD_LEGACY_PLANNERS=0
    disables them even in dev."""
    raw = os.getenv("ZAAD_LEGACY_PLANNERS")
    if raw is not None and raw.strip() != "":
        return raw.strip().lower() in ("1", "true", "yes")
    return deployment_env() == "dev"


def legacy_planner_gate() -> None:
    """FastAPI dependency: 410 with the canonical replacement when the legacy engines are off."""
    if not legacy_planners_enabled():
        raise HTTPException(status_code=410, detail={
            "code": "legacy_planner_disabled",
            "message": "This planning engine is superseded by the frozen ZAAD P1 optimizer.",
            "canonical": {"workspace_plan": "/api/zaad/network/plan/from-workspace",
                          "purchase_plan": "/fmcg/plan?mode=canonical", "network_plan": "/api/zaad/network/plan"}})


def auth_required() -> bool:
    """Whether the API enforces operator authentication.

    FAIL-CLOSED OUTSIDE DEV. Authentication is enforced when EITHER
    HARVESTMIND_AUTH_REQUIRED=true OR HARVESTMIND_ENV names a deployed
    environment (pilot, staging, prod). An explicit
    HARVESTMIND_AUTH_REQUIRED=false does NOT switch enforcement off in a
    deployed environment: the previous behaviour let a networked pilot ship
    with the dev default, in which any caller could select any operator's
    vault with ?operator_id=. Dev stays permissive so local work and the
    test-suite are unchanged. Read live so tests can flip it via env.
    """
    if deployment_env() in _ENFORCED_ENVS:
        return True
    return os.getenv("HARVESTMIND_AUTH_REQUIRED", "false").lower() == "true"


_LOOPBACK = ("127.0.0.1", "localhost", "::1", "")


def assert_safe_to_serve() -> None:
    """Refuse to start a permissive server on a non-loopback interface.

    The bind host is not visible from inside the app, so the launcher
    declares it in HARVESTMIND_BIND_HOST (the Dockerfile and compose file
    do). A dev-mode process bound to 0.0.0.0 is the configuration that
    would let any network caller pick any operator's vault; it is refused
    at startup rather than logged.
    """
    host = os.getenv("HARVESTMIND_BIND_HOST", "").strip()
    if host and host not in _LOOPBACK and not auth_required():
        raise RuntimeError(
            f"refusing to serve: HARVESTMIND_ENV={deployment_env()!r} is permissive "
            f"but HARVESTMIND_BIND_HOST={host!r} is not loopback. Set "
            "HARVESTMIND_ENV=pilot|staging|prod (or HARVESTMIND_AUTH_REQUIRED=true).")


def auth_posture() -> dict:
    """What /health reports so an operator can see the posture, not guess it."""
    return {"env": deployment_env(), "auth_enforced": auth_required(),
            "rate_limit_per_min": int(os.getenv("HARVESTMIND_RATE_LIMIT_PER_MIN", "0"))}


# ── client address ───────────────────────────────────────────────────────────
# The server runs behind Fly's proxy with proxy headers trusted from any peer (`api/serve.py`), so
# `request.client.host` is whatever the caller wrote into X-Forwarded-For (security review 2026-09,
# SEC-008). The proxy itself stamps `Fly-Client-IP` with the real address and overwrites any value a
# client sends; that header is the address of record whenever it is present, and the socket peer
# otherwise (local runs, the private network). X-Forwarded-For is never read for a limit.

def client_ip(request: Request) -> str:
    stamped = request.headers.get("fly-client-ip")
    if stamped:
        return stamped.strip()[:64]
    client = getattr(request, "client", None)
    return (client.host if client else "unknown")[:64]


# ── failed authentication throttle ──────────────────────────────────────────
# A pilot access code is short and human-typed, so guessing must be expensive: after
# FAILED_AUTH_PER_MIN wrong tokens from one address (or FAILED_AUTH_GLOBAL_PER_MIN across all) the
# API answers 429 with Retry-After for the rest of the minute, before touching the registry.
FAILED_AUTH_PER_MIN = int(os.getenv("HARVESTMIND_FAILED_AUTH_PER_MIN", "10"))
FAILED_AUTH_GLOBAL_PER_MIN = int(os.getenv("HARVESTMIND_FAILED_AUTH_GLOBAL_PER_MIN", "300"))
_FAILED_AUTH: dict[str, list[float]] = {}
_FAILED_AUTH_GLOBAL: list[float] = []
_AUTH_LOCK = __import__("threading").Lock()


def _prune(bucket: list[float], now: float) -> list[float]:
    return [t for t in bucket if now - t < 60.0]


def _auth_throttled(client: str | None) -> bool:
    if client is None:
        return False
    import time
    now = time.time()
    with _AUTH_LOCK:
        global _FAILED_AUTH_GLOBAL
        _FAILED_AUTH_GLOBAL = _prune(_FAILED_AUTH_GLOBAL, now)
        own = _FAILED_AUTH[client] = _prune(_FAILED_AUTH.get(client, []), now)
        for key in [k for k, v in _FAILED_AUTH.items() if not v]:
            del _FAILED_AUTH[key]
        return len(own) >= FAILED_AUTH_PER_MIN or len(_FAILED_AUTH_GLOBAL) >= FAILED_AUTH_GLOBAL_PER_MIN


def _auth_failed(client: str | None) -> None:
    if client is None:
        return
    import time
    now = time.time()
    with _AUTH_LOCK:
        _FAILED_AUTH.setdefault(client, []).append(now)
        _FAILED_AUTH_GLOBAL.append(now)
        if len(_FAILED_AUTH) > 10000:      # bounded memory whatever the address churn
            _FAILED_AUTH.clear()


def _refuse_throttled() -> None:
    raise HTTPException(status_code=429, detail="Too many failed authentication attempts; retry in a minute.",
                        headers={"Retry-After": "60"})


def _token_from_headers(authorization: str | None, x_api_key: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    if x_api_key:
        return x_api_key.strip()
    return None


def authenticate_operator(
    authorization: str | None = None,
    x_api_key: str | None = None,
    client: str | None = None,
) -> str | None:
    """Core auth logic (plain Python, callable in tests).

    Returns the token's operator_id when a valid token is presented (in any
    mode); returns None when no token is presented and auth is not enforced
    (dev fallback — callers then use their legacy param); raises 401 when a
    token is invalid, or when none is presented and auth IS enforced. `client`
    is the address of record for the failed-authentication throttle (429).
    """
    token = _token_from_headers(authorization, x_api_key)
    if token:
        if _auth_throttled(client):
            _refuse_throttled()
        from infrastructure.operator_registry import OperatorRegistry
        oid = OperatorRegistry().operator_id_for_token(token)
        if oid is None:
            _auth_failed(client)
            raise HTTPException(status_code=401, detail="Invalid API token")
        return oid
    if auth_required():
        raise HTTPException(status_code=401, detail="Authentication required")
    return None


def require_operator(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str | None:
    """FastAPI dependency wrapper around :func:`authenticate_operator`."""
    return authenticate_operator(authorization, x_api_key, client_ip(request))


def authenticate_actor(authorization: str | None = None, x_api_key: str | None = None, client: str | None = None):
    """Who is acting: the actor record for the token, or None in permissive dev with no token.

    The workspace's own token is its pilot administrator; a named actor's token carries the
    person's role. Same refusal rules as :func:`authenticate_operator`.
    """
    from api.product.governance import actor_from

    token = _token_from_headers(authorization, x_api_key)
    if token:
        if _auth_throttled(client):
            _refuse_throttled()
        from infrastructure.operator_registry import OperatorRegistry
        record = OperatorRegistry().actor_for_token(token)
        if record is None:
            _auth_failed(client)
            raise HTTPException(status_code=401, detail="Invalid API token")
        return actor_from(record)
    if auth_required():
        raise HTTPException(status_code=401, detail="Authentication required")
    return None


def require_actor(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    """FastAPI dependency: the acting person, with role and capabilities (Operating Product V2)."""
    return authenticate_actor(authorization, x_api_key, client_ip(request))


def capability(name: str):
    """FastAPI dependency factory: the acting person must hold `name` (security review 2026-09, SEC-007).

    Every route that starts a solve, a diagnostic or a model call, records a decision or an outcome, changes
    a workspace-level setting or writes traceability data names the capability its role must grant; the
    role always comes from the token. In permissive dev with no token there is no actor and the route
    behaves as it always has. A refusal is 403 with the governance message, never a 500.
    """
    from api.product.governance import CAPABILITIES, Forbidden, need
    if name not in CAPABILITIES:
        raise ValueError(f"unknown capability {name!r}")

    def dependency(actor=Depends(require_actor)) -> None:
        if actor is None:
            return
        try:
            need(actor, name)
        except Forbidden as exc:
            raise HTTPException(status_code=403, detail={"code": "forbidden", "message": str(exc)}) from exc

    dependency.__name__ = f"capability_{name}"
    return dependency


# ── Rate limiting (heavy/expensive endpoints) ────────────────────────────────
# Minimal per-process fixed-window limiter, no external dependency. Disabled by
# default (HARVESTMIND_RATE_LIMIT_PER_MIN=0) so dev/tests are unaffected; set a
# positive value in production to cap abuse of the CPU/LLM-heavy endpoints.
_RL_BUCKETS: dict = {}


def rate_limiter(request: Request) -> None:
    """FastAPI dependency: cap requests/min per client address + route.

    No-op unless HARVESTMIND_RATE_LIMIT_PER_MIN > 0, so dev/tests are
    unaffected. 429 when the per-minute cap is exceeded. The address is the
    proxy-stamped one (`client_ip`), the key is the route template rather than
    the raw path (an id in the path does not buy a fresh bucket), and empty
    buckets are dropped so the map cannot grow with address churn.
    """
    limit = int(os.getenv("HARVESTMIND_RATE_LIMIT_PER_MIN", "0"))
    if limit <= 0:
        return
    import time
    now = time.time()
    route = request.scope.get("route")
    template = getattr(route, "path", None) or request.url.path
    key = (client_ip(request), template)
    with _AUTH_LOCK:
        for stale in [k for k, v in _RL_BUCKETS.items() if not v or now - v[-1] >= 60.0]:
            del _RL_BUCKETS[stale]
        bucket = [t for t in _RL_BUCKETS.get(key, []) if now - t < 60.0]
        if len(bucket) >= limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded", headers={"Retry-After": "60"})
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
        from infrastructure.db_manager import vault_cursor
        conn = vault_cursor(get_db_path())
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
        # One instance per file for the whole process (see infrastructure/db_manager.py): a
        # read-only open beside a read-write one is refused by DuckDB, so this shares the anchor.
        from infrastructure.db_manager import vault_cursor
        conn = vault_cursor(get_db_path())
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
