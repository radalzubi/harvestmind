"""Role / capability matrix: every protected mutation as every role, through real actor tokens (SEC-007)."""
from __future__ import annotations

import pytest

from tests.security.conftest import ROLES, Tenants

# (method, path, body, roles that may) — a role not listed must be refused with 403 (or 401 for anonymous)
MUTATIONS = [
    # heavy routes carry a body or query that fails validation right after the role check, so an allowed role
    # answers 4xx in milliseconds instead of starting a solve; the diagnostic dispatcher is stubbed below
    ("POST", "/jobs/diagnostic", None, {"BUYER", "APPROVER", "ADMIN"}),
    ("POST", "/api/zaad/network/jobs", {"operator_id": "{op}"}, {"BUYER", "APPROVER", "ADMIN"}),
    ("POST", "/api/zaad/network/plan/from-workspace?horizon=1", None, {"BUYER", "APPROVER", "ADMIN"}),
    ("POST", "/fmcg/plan?horizon_weeks=1", None, {"BUYER", "APPROVER", "ADMIN"}),
    ("POST", "/planning/run", {"week_start": "not-a-date"}, {"BUYER", "APPROVER", "ADMIN"}),
    ("POST", "/backtest/run", {"n_scenarios": 1}, {"BUYER", "APPROVER", "ADMIN"}),
    ("POST", "/assistant/ask", {"question": "hello"}, {"BUYER", "APPROVER", "ADMIN"}),
    ("POST", "/pool/consent?consented=true", None, {"ADMIN"}),
    ("POST", "/fsma/lots/create", {}, {"BUYER", "ADMIN"}),
    ("POST", "/fsma/cte/record", {}, {"BUYER", "ADMIN"}),
    ("POST", "/api/zaad/network/shadow", {"operator_id": "{op}"}, {"BUYER", "APPROVER", "ADMIN"}),
    ("POST", "/api/zaad/network/shadow/dec_x/review", {"decision": "APPROVE"}, {"APPROVER", "ADMIN"}),
    ("POST", "/api/zaad/network/shadow/dec_x/outcome", {}, {"BUYER", "APPROVER", "ADMIN"}),
    ("POST", "/intake/upload/stg_fmcg_skus", None, {"BUYER", "ADMIN"}),
    ("POST", "/intake/clear/stg_fmcg_skus", None, {"BUYER", "ADMIN"}),
    ("POST", "/api/zaad/orders", {"origin": "MANUAL", "supplier_id": "SUP-001", "lines": [{"sku": "SKU-0001", "quantity": 1, "unit_price": 1.0}]}, {"BUYER", "APPROVER", "ADMIN"}),
    ("POST", "/api/zaad/orders/profiles", {"name": "x", "columns": [{"header": "a", "field": "sku"}]}, {"ADMIN"}),
    ("PUT", "/api/zaad/workspace/settings", {"self_approval": "allowed"}, {"ADMIN"}),
    ("DELETE", "/api/zaad/workspace/actors/act_nobody", None, {"ADMIN"}),
    ("POST", "/api/zaad/analytics/analyses", {"name": "x"}, {"BUYER", "APPROVER", "ADMIN"}),
    ("POST", "/api/zaad/analytics/export", {}, {"BUYER", "APPROVER", "ADMIN"}),
    ("POST", "/api/zaad/analytics/ask", {"question": "x"}, {"BUYER", "APPROVER", "ADMIN"}),
    ("POST", "/api/zaad/analytics/handoff", {}, {"BUYER", "APPROVER", "ADMIN"}),
]


@pytest.fixture(autouse=True)
def _no_real_diagnostic(monkeypatch):
    """The role gate is what is under test; a permitted press must not start a diagnostic thread."""
    from api.routers import jobs as jobs_router
    monkeypatch.setattr(jobs_router, "_dispatch", lambda job, op: None)


def _call(tenants: Tenants, method: str, path: str, body, headers):
    c = tenants.client
    if path.startswith("/intake/upload/"):
        return c.post(path, headers=headers, files={"file": ("x.csv", b"sku,x\n1,2\n", "text/csv")})
    payload = None
    if body is not None:
        payload = {k: (v.replace("{op}", tenants.a.operator_id) if isinstance(v, str) else v) for k, v in body.items()}
    return c.request(method, path, headers=headers, json=payload)


@pytest.mark.parametrize("method,path,body,allowed", MUTATIONS)
@pytest.mark.parametrize("role", ROLES)
def test_role_gate(tenants: Tenants, method, path, body, allowed, role):
    r = _call(tenants, method, path, body, tenants.a.h(role))
    if role in allowed:
        assert r.status_code != 403, (role, method, path, r.status_code, r.text[:200])
        assert r.status_code != 401
    else:
        assert r.status_code == 403, (role, method, path, r.status_code, r.text[:200])


@pytest.mark.parametrize("method,path,body,allowed", MUTATIONS)
def test_anonymous_is_refused(tenants: Tenants, method, path, body, allowed):
    r = _call(tenants, method, path, body, {})
    assert r.status_code == 401, (method, path, r.status_code, r.text[:200])


def test_a_viewer_cannot_read_people_or_change_consent(tenants: Tenants):
    assert tenants.client.get("/api/zaad/workspace/actors", headers=tenants.a.h("VIEWER")).status_code == 403
    assert tenants.client.post("/pool/consent", params={"consented": "true"}, headers=tenants.a.h("VIEWER")).status_code == 403


def test_the_role_comes_from_the_token_never_from_the_request(tenants: Tenants):
    """A viewer naming ADMIN in a body, query or header stays a viewer."""
    r = tenants.client.post("/api/zaad/orders/profiles", headers={**tenants.a.h("VIEWER"), "X-Role": "ADMIN"},
                            params={"role": "ADMIN"}, json={"name": "x", "columns": [{"header": "a", "field": "sku"}], "role": "ADMIN"})
    assert r.status_code == 403


def test_revoked_actor_token_is_dead_everywhere(tenants: Tenants):
    actor_id, token = tenants.registry.issue_actor_token(tenants.a.operator_id, "Temp", "BUYER")
    h = {"Authorization": f"Bearer {token}"}
    assert tenants.client.get("/me", headers=h).status_code == 200
    assert tenants.registry.revoke_actor(tenants.a.operator_id, actor_id)
    assert tenants.client.get("/me", headers=h).status_code == 401
    assert tenants.client.get("/api/zaad/workspace/summary", headers=h).status_code == 401
