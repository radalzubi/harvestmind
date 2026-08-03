"""Tests for the admin token-issuance endpoint.

Fail-closed when HARVESTMIND_ADMIN_KEY is unset; key-gated otherwise; issued
tokens authenticate the operator.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import api.main as api_main
import infrastructure.operator_registry as orm


@pytest.fixture()
def registry(tmp_path, monkeypatch):
    monkeypatch.setattr(orm, "DEFAULT_DATA_ROOT", tmp_path / "data")
    return orm.OperatorRegistry(data_root=tmp_path / "data")


@pytest.fixture()
def client():
    return TestClient(api_main.app)


def test_admin_disabled_when_key_unset(registry, client, monkeypatch):
    monkeypatch.delenv("HARVESTMIND_ADMIN_KEY", raising=False)
    op = registry.create_operator("A")
    r = client.post(f"/admin/operators/{op.operator_id}/token")
    assert r.status_code == 404          # surface hidden when unconfigured


def test_admin_wrong_key_401(registry, client, monkeypatch):
    monkeypatch.setenv("HARVESTMIND_ADMIN_KEY", "s3cret")
    op = registry.create_operator("A")
    r = client.post(f"/admin/operators/{op.operator_id}/token",
                    headers={"X-Admin-Key": "wrong"})
    assert r.status_code == 401


def test_admin_issues_working_token(registry, client, monkeypatch):
    monkeypatch.setenv("HARVESTMIND_ADMIN_KEY", "s3cret")
    op = registry.create_operator("A")
    r = client.post(f"/admin/operators/{op.operator_id}/token",
                    headers={"X-Admin-Key": "s3cret"})
    assert r.status_code == 200
    token = r.json()["token"]
    assert token and r.json()["operator_id"] == op.operator_id
    # the issued token authenticates the operator
    assert registry.operator_id_for_token(token) == op.operator_id


def test_admin_unknown_operator_404(registry, client, monkeypatch):
    monkeypatch.setenv("HARVESTMIND_ADMIN_KEY", "s3cret")
    r = client.post("/admin/operators/op_deadbeef/token",
                    headers={"X-Admin-Key": "s3cret"})
    assert r.status_code == 404


def test_admin_token_rotates(registry, client, monkeypatch):
    monkeypatch.setenv("HARVESTMIND_ADMIN_KEY", "s3cret")
    op = registry.create_operator("A")
    h = {"X-Admin-Key": "s3cret"}
    t1 = client.post(f"/admin/operators/{op.operator_id}/token", headers=h).json()["token"]
    t2 = client.post(f"/admin/operators/{op.operator_id}/token", headers=h).json()["token"]
    assert t1 != t2
    assert registry.operator_id_for_token(t1) is None      # old invalidated
    assert registry.operator_id_for_token(t2) == op.operator_id
