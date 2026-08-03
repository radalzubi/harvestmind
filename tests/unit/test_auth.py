"""Tests for API-token authentication (registry tokens + require_operator).

Auth is OFF by default (dev); these tests exercise the mechanism directly and
in enforced mode. See SECURITY_CHECKLIST.md item A-1.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

import infrastructure.operator_registry as orm
from api.dependencies import authenticate_operator as _auth


@pytest.fixture()
def registry(tmp_path, monkeypatch):
    monkeypatch.setattr(orm, "DEFAULT_DATA_ROOT", tmp_path / "data")
    return orm.OperatorRegistry(data_root=tmp_path / "data")


# ── registry token mechanics ─────────────────────────────────────────────────

def test_issue_token_round_trips(registry):
    op = registry.create_operator("Hub A")
    assert registry.get_operator(op.operator_id).token_hash is None
    raw = registry.issue_token(op.operator_id)
    assert isinstance(raw, str) and len(raw) > 20
    # only the hash is persisted, never the raw token
    stored = registry.get_operator(op.operator_id).token_hash
    assert stored and stored != raw
    assert registry.operator_id_for_token(raw) == op.operator_id


def test_wrong_and_empty_tokens_resolve_to_none(registry):
    op = registry.create_operator("Hub A")
    registry.issue_token(op.operator_id)
    assert registry.operator_id_for_token("not-a-real-token") is None
    assert registry.operator_id_for_token("") is None


def test_token_rotation_invalidates_old(registry):
    op = registry.create_operator("Hub A")
    old = registry.issue_token(op.operator_id)
    new = registry.issue_token(op.operator_id)
    assert old != new
    assert registry.operator_id_for_token(old) is None
    assert registry.operator_id_for_token(new) == op.operator_id


def test_suspended_operator_cannot_authenticate(registry):
    op = registry.create_operator("Hub A")
    raw = registry.issue_token(op.operator_id)
    registry.suspend_operator(op.operator_id)
    assert registry.operator_id_for_token(raw) is None


def test_two_operators_tokens_are_isolated(registry):
    a = registry.create_operator("A")
    b = registry.create_operator("B")
    ta = registry.issue_token(a.operator_id)
    tb = registry.issue_token(b.operator_id)
    assert registry.operator_id_for_token(ta) == a.operator_id
    assert registry.operator_id_for_token(tb) == b.operator_id
    assert a.operator_id != b.operator_id


# ── require_operator dependency ──────────────────────────────────────────────

def test_require_operator_valid_token(registry):
    op = registry.create_operator("A")
    raw = registry.issue_token(op.operator_id)
    assert _auth(authorization=f"Bearer {raw}") == op.operator_id
    assert _auth(x_api_key=raw) == op.operator_id


def test_require_operator_invalid_token_401(registry):
    with pytest.raises(HTTPException) as ei:
        _auth(authorization="Bearer garbage")
    assert ei.value.status_code == 401


def test_require_operator_no_token_dev_returns_none(registry, monkeypatch):
    monkeypatch.delenv("HARVESTMIND_AUTH_REQUIRED", raising=False)
    assert _auth(None, None) is None


def test_require_operator_no_token_enforced_401(registry, monkeypatch):
    monkeypatch.setenv("HARVESTMIND_AUTH_REQUIRED", "true")
    with pytest.raises(HTTPException) as ei:
        _auth(None, None)
    assert ei.value.status_code == 401


def test_require_operator_token_wins_over_missing_env(registry, monkeypatch):
    """A valid token authenticates regardless of the enforcement flag."""
    op = registry.create_operator("A")
    raw = registry.issue_token(op.operator_id)
    monkeypatch.setenv("HARVESTMIND_AUTH_REQUIRED", "true")
    assert _auth(authorization=f"Bearer {raw}") == op.operator_id


# ── end-to-end: the IDOR is closed in enforced mode ──────────────────────────

def test_consent_endpoint_enforced_uses_token_not_query(registry, monkeypatch):
    """With auth enforced, a caller holding A's token cannot flip B's consent
    by passing ?operator_id=B — the token's operator wins."""
    from fastapi.testclient import TestClient
    import api.main as api_main

    a = registry.create_operator("A", pool_consent=False)
    b = registry.create_operator("B", pool_consent=False)
    ta = registry.issue_token(a.operator_id)
    monkeypatch.setenv("HARVESTMIND_AUTH_REQUIRED", "true")
    client = TestClient(api_main.app)

    r = client.post(
        f"/pool/consent?operator_id={b.operator_id}&consented=true",
        headers={"Authorization": f"Bearer {ta}"},
    )
    assert r.status_code == 200
    # acted on A (the token), NOT B (the spoofed query param)
    assert r.json()["operator_id"] == a.operator_id

    # an unauthenticated request is rejected outright in enforced mode
    r2 = client.post(f"/pool/consent?operator_id={a.operator_id}&consented=true")
    assert r2.status_code == 401


def test_read_endpoints_gated_and_vault_routed_in_enforced_mode(registry, monkeypatch):
    """Read endpoints (get_conn-backed) require a token in enforced mode and
    route to the authenticated operator's vault, not the shared root DB."""
    from fastapi.testclient import TestClient
    import api.main as api_main

    op = registry.create_operator("A")
    tok = registry.issue_token(op.operator_id)
    monkeypatch.setenv("HARVESTMIND_AUTH_REQUIRED", "true")
    client = TestClient(api_main.app)

    # no token → 401 (read endpoint is now auth-gated)
    assert client.get("/data/products").status_code == 401
    # invalid token → 401
    assert client.get(
        "/data/products", headers={"Authorization": "Bearer nope"}
    ).status_code == 401
    # valid token → 200, served from A's (empty, migrated) vault
    r = client.get("/data/products", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
