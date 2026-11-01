"""Token lifecycle hardening (SEC-001, SEC-016): short access codes refused, the registry private and atomic,
tokens hashed and mutated tokens dead."""
from __future__ import annotations

import os
import stat

import pytest

from tests.security.conftest import Tenants


def test_short_access_codes_are_refused(tenants: Tenants):
    reg, op = tenants.registry, tenants.a.operator_id
    for short in ("short1", "abcdef", "12345678901"):
        with pytest.raises(ValueError):
            reg.set_access_code(op, short)
    reg.set_access_code(op, "long-enough-code-2026")
    assert tenants.client.get("/me", headers={"Authorization": "Bearer long-enough-code-2026"}).status_code == 200
    reg.clear_access_code(op)
    assert tenants.client.get("/me", headers={"Authorization": "Bearer long-enough-code-2026"}).status_code == 401


def test_registry_file_is_private_and_atomic(tenants: Tenants):
    reg = tenants.registry
    mode = stat.S_IMODE(os.stat(reg.registry_file).st_mode)
    assert mode == 0o600, oct(mode)
    leftovers = [p for p in reg.registry_dir.iterdir() if p.name.startswith(".operators.") and p.suffix == ".json"]
    assert leftovers == []                      # no temp file survives a save
    raw = reg.registry_file.read_text()
    assert tenants.a.token not in raw and tenants.b.token not in raw and all(t not in raw for t in tenants.a.actors.values())


@pytest.mark.parametrize("mutate", [lambda t: t.upper(), lambda t: t[:-1], lambda t: t + "x", lambda t: " " + t, lambda t: t.swapcase(), lambda t: "", lambda t: "Bearer " + t])
def test_mutated_tokens_never_authenticate(tenants: Tenants, mutate):
    token = tenants.a.token
    bad = mutate(token)
    if bad.strip() == token:
        pytest.skip("whitespace is trimmed by design")
    r = tenants.client.get("/me", headers={"Authorization": f"Bearer {bad}"})
    assert r.status_code == 401, (bad[:8], r.status_code)


def test_token_in_query_string_is_ignored(tenants: Tenants):
    assert tenants.client.get("/me", params={"token": tenants.a.token}).status_code == 401
    assert tenants.client.get("/me", params={"api_key": tenants.a.token}).status_code == 401
    assert tenants.client.get("/me", headers={"Authorization": f"Basic {tenants.a.token}"}).status_code == 401


def test_worker_token_and_admin_key_are_not_workspace_credentials(tenants: Tenants, monkeypatch):
    monkeypatch.setenv("HARVESTMIND_WORKER_TOKEN", "worker-secret-value")
    monkeypatch.setenv("HARVESTMIND_ADMIN_KEY", "admin-secret-value")
    c = tenants.client
    assert c.get("/me", headers={"Authorization": "Bearer worker-secret-value"}).status_code == 401
    assert c.get("/me", headers={"Authorization": "Bearer admin-secret-value"}).status_code == 401
    assert c.get("/api/zaad/workspace/summary", headers={"X-Admin-Key": "admin-secret-value"}).status_code == 401
    # the admin key opens the admin surface only, and never a vault
    assert c.get("/admin/workspaces", headers={"X-Admin-Key": "admin-secret-value"}).status_code == 200
    assert c.get("/admin/workspaces", headers={"X-Admin-Key": "wrong"}).status_code == 401


def test_rotation_invalidates_the_previous_credential(tenants: Tenants):
    """Rotating the token or the access code kills the old value at once (closure 2026-09, SEC-001)."""
    reg, c = tenants.registry, tenants.client
    rec = reg.create_operator("Rotation Tenant", region="test", sector="commercial")
    first = reg.issue_token(rec.operator_id)
    assert c.get("/me", headers={"Authorization": f"Bearer {first}"}).status_code == 200
    second = reg.issue_token(rec.operator_id)
    assert first != second
    assert c.get("/me", headers={"Authorization": f"Bearer {first}"}).status_code == 401
    assert c.get("/me", headers={"Authorization": f"Bearer {second}"}).status_code == 200
    reg.set_access_code(rec.operator_id, "synthetic-code-one-2026")
    assert c.get("/me", headers={"Authorization": "Bearer synthetic-code-one-2026"}).status_code == 200
    reg.set_access_code(rec.operator_id, "synthetic-code-two-2026")
    assert c.get("/me", headers={"Authorization": "Bearer synthetic-code-one-2026"}).status_code == 401
    assert c.get("/me", headers={"Authorization": "Bearer synthetic-code-two-2026"}).status_code == 200
    raw = reg.registry_file.read_text()
    for secret in (first, second, "synthetic-code-one-2026", "synthetic-code-two-2026"):
        assert secret not in raw, "the registry holds hashes only"


def test_seed_replaces_the_code_and_a_short_seed_leaves_it_alone(tenants: Tenants, monkeypatch):
    """The seed secret is the controlling copy of a seeded workspace's access code (closure 2026-09)."""
    from infrastructure.seed_workspaces import seed_workspaces_from_env
    reg, c = tenants.registry, tenants.client
    monkeypatch.setenv("HARVESTMIND_SEED_WORKSPACES", "Seeded Tenant|commercial|seeded-code-first-2026|")
    (op,) = seed_workspaces_from_env(reg)
    assert c.get("/me", headers={"Authorization": "Bearer seeded-code-first-2026"}).status_code == 200
    monkeypatch.setenv("HARVESTMIND_SEED_WORKSPACES", "Seeded Tenant|commercial|seeded-code-second-2026|")
    assert seed_workspaces_from_env(reg) == [op], "the same workspace, not a new one"
    assert c.get("/me", headers={"Authorization": "Bearer seeded-code-first-2026"}).status_code == 401
    assert c.get("/me", headers={"Authorization": "Bearer seeded-code-second-2026"}).status_code == 200
    # a short code in the secret cannot become the credential, and does not disturb the long one
    monkeypatch.setenv("HARVESTMIND_SEED_WORKSPACES", "Seeded Tenant|commercial|short1|")
    assert seed_workspaces_from_env(reg) == [op]
    assert c.get("/me", headers={"Authorization": "Bearer short1"}).status_code == 401
    assert c.get("/me", headers={"Authorization": "Bearer seeded-code-second-2026"}).status_code == 200


def test_admin_rotation_response_carries_the_token_once_and_the_log_never(tenants: Tenants, monkeypatch, caplog):
    import logging
    monkeypatch.setenv("HARVESTMIND_ADMIN_KEY", "admin-test-key")
    c = tenants.client
    rec = tenants.registry.create_operator("Logged Tenant", region="test", sector="commercial")
    with caplog.at_level(logging.INFO, logger="harvestmind.security"):
        r = c.post(f"/admin/operators/{rec.operator_id}/token", headers={"X-Admin-Key": "admin-test-key"})
    assert r.status_code == 200
    token = r.json()["token"]
    assert token and token not in caplog.text and rec.operator_id in caplog.text
    assert c.get("/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200
