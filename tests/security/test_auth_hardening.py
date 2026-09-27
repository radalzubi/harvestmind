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
