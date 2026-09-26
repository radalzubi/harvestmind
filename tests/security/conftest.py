"""Security regression suite fixtures (security review 2026-09).

Two real tenants through the real application: the registry issues their workspace tokens and one actor token per
role, both vaults hold the synthetic FMCG sample (the same SKU, supplier and purchase-order identifiers in each, so a
cross-tenant read cannot hide behind a different id), authentication is enforced, the rate limiter is off (the rate-limit
tests switch it on themselves), the planning job store and the extraction-session root live under the test directory.
Every request goes through the real `Authorization: Bearer` chain — no dependency override anywhere in this suite.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import pytest

ROLES = ("VIEWER", "BUYER", "APPROVER", "ADMIN")


@dataclass
class Tenant:
    operator_id: str
    token: str                                  # the workspace (pilot administrator) token
    actors: dict[str, str] = field(default_factory=dict)   # role -> actor token
    actor_ids: dict[str, str] = field(default_factory=dict)

    def h(self, role: str | None = None) -> dict[str, str]:
        """Authorization header: the workspace token, or the actor token of a role."""
        return {"Authorization": f"Bearer {self.token if role is None else self.actors[role]}"}


@dataclass
class Tenants:
    a: Tenant
    b: Tenant
    client: object
    registry: object
    data_root: Path
    sessions_root: Path


def _seed(registry, operator_id: str, seed: int) -> None:
    from api.routers.intake import load_fmcg_sample_into
    from infrastructure.db_manager import DBManager
    dbm = DBManager(registry)
    conn = dbm.get_operator_connection(operator_id)
    try:
        load_fmcg_sample_into(conn, seed=seed)
    finally:
        dbm.close_all()


@pytest.fixture(scope="module")
def tenants(tmp_path_factory) -> Tenants:
    """Two seeded tenants and a TestClient over the whole app with enforced authentication."""
    import infrastructure.operator_registry as orm
    import ingestion.extraction_sessions as es
    root = tmp_path_factory.mktemp("security")
    data_root = root / "data"
    env = {"HARVESTMIND_AUTH_REQUIRED": "true", "HARVESTMIND_RATE_LIMIT_PER_MIN": "0",
           "ZAAD_JOB_STORE": str(root / "jobs.sqlite"), "ZAAD_SHADOW_LEDGER": str(root / "shadow.sqlite"),
           "HARVESTMIND_DATA_ROOT": str(data_root), "HARVESTMIND_SELF_SERVE": "true"}
    saved = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    saved_root, saved_audit = orm.DEFAULT_DATA_ROOT, es.AUDIT_ROOT
    orm.DEFAULT_DATA_ROOT = data_root
    es.AUDIT_ROOT = root / "audit"
    registry = orm.OperatorRegistry(data_root=data_root)
    made = []
    for name, seed in (("Tenant A", 7), ("Tenant B", 7)):
        rec = registry.create_operator(name, region="test", sector="commercial")
        t = Tenant(rec.operator_id, registry.issue_token(rec.operator_id))
        for role in ROLES:
            actor_id, token = registry.issue_actor_token(rec.operator_id, f"{role.title()} of {name}", role)
            t.actors[role], t.actor_ids[role] = token, actor_id
        _seed(registry, rec.operator_id, seed)
        made.append(t)
    from fastapi.testclient import TestClient
    import api.main as api_main
    client = TestClient(api_main.app)
    yield Tenants(a=made[0], b=made[1], client=client, registry=registry, data_root=data_root, sessions_root=root / "audit")
    orm.DEFAULT_DATA_ROOT, es.AUDIT_ROOT = saved_root, saved_audit
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


@pytest.fixture(autouse=True)
def _fresh_limits():
    """Every test starts with empty rate-limit state (the limiter is process-global)."""
    from api import dependencies
    from api.routers import zaad as zaad_router
    dependencies._RL_BUCKETS.clear()
    dependencies._FAILED_AUTH.clear()
    dependencies._FAILED_AUTH_GLOBAL = []
    from api.routers import access
    access._SELF_SERVE.clear()
    with zaad_router._lock:
        zaad_router._recent.clear()
        zaad_router._global_recent.clear()
    yield
