"""Adversarial tenant isolation.

Isolation here is physical: one DuckDB per operator. These tests do what an
attacker would — hold one operator's token and name another operator in
every place the API accepts an id — and assert that the response is served
from the caller's own vault, never the named one. A leak in any of these is
a release blocker; there is no severity below that for tenant data.
"""
from __future__ import annotations

import pytest

import infrastructure.operator_registry as orm


@pytest.fixture()
def two_tenants(tmp_path, monkeypatch):
    monkeypatch.setattr(orm, "DEFAULT_DATA_ROOT", tmp_path / "data")
    reg = orm.OperatorRegistry(data_root=tmp_path / "data")
    a = reg.create_operator("Alpha Foods")
    b = reg.create_operator("Beta Distribution")
    ta, tb = reg.issue_token(a.operator_id), reg.issue_token(b.operator_id)
    # Seed a product ONLY into B's vault, so any appearance of it under A's
    # token is a cross-tenant read.
    from infrastructure.db_manager import DBManager
    dbm = DBManager(reg)
    conn = dbm.get_operator_connection(b.operator_id)
    conn.execute("INSERT INTO dim_products (product_id, crop_name, crop_category, "
                 "shelf_life_days) VALUES ('B-SECRET-001', 'Beta Only Lettuce', "
                 "'leafy_green', 7)")
    dbm.close_all()
    monkeypatch.setenv("HARVESTMIND_AUTH_REQUIRED", "true")
    from fastapi.testclient import TestClient
    import api.main as api_main
    return reg, a, b, ta, tb, TestClient(api_main.app)


def _ids(resp):
    body = resp.json()
    rows = body if isinstance(body, list) else body.get("products", body.get("items", []))
    return {r.get("product_id") for r in rows if isinstance(r, dict)}


class TestBOLA:
    def test_token_a_cannot_read_b_by_naming_b_in_query(self, two_tenants):
        reg, a, b, ta, tb, client = two_tenants
        r = client.get(f"/data/products?operator_id={b.operator_id}",
                       headers={"Authorization": f"Bearer {ta}"})
        assert r.status_code == 200
        assert "B-SECRET-001" not in _ids(r)

    def test_b_sees_its_own_row_with_its_own_token(self, two_tenants):
        reg, a, b, ta, tb, client = two_tenants
        r = client.get("/data/products", headers={"Authorization": f"Bearer {tb}"})
        assert r.status_code == 200
        assert "B-SECRET-001" in _ids(r)

    def test_no_token_cannot_select_a_vault_in_enforced_mode(self, two_tenants):
        reg, a, b, ta, tb, client = two_tenants
        assert client.get(f"/data/products?operator_id={b.operator_id}").status_code == 401

    def test_x_api_key_header_path_is_also_bound_to_its_operator(self, two_tenants):
        reg, a, b, ta, tb, client = two_tenants
        r = client.get(f"/data/products?operator_id={b.operator_id}",
                       headers={"X-API-Key": ta})
        assert r.status_code == 200 and "B-SECRET-001" not in _ids(r)

    def test_forged_and_rotated_tokens_fail(self, two_tenants):
        reg, a, b, ta, tb, client = two_tenants
        assert client.get("/data/products",
                          headers={"Authorization": f"Bearer {ta[:-3]}xyz"}).status_code == 401
        reg.issue_token(b.operator_id)             # rotates B's token
        assert client.get("/data/products",
                          headers={"Authorization": f"Bearer {tb}"}).status_code == 401

    @pytest.mark.parametrize("path", [
        "/data/suppliers", "/data/deliveries/recent", "/data/orders/weekly-demand",
        "/data/quality", "/intake/status", "/planning/recommendations",
    ])
    def test_every_operator_scoped_read_requires_a_token(self, two_tenants, path):
        reg, a, b, ta, tb, client = two_tenants
        r = client.get(path)
        assert r.status_code == 401, (path, r.status_code)

    def test_suspended_operator_loses_access(self, two_tenants):
        reg, a, b, ta, tb, client = two_tenants
        rec = reg.get_operator(b.operator_id)
        rec.status = "suspended"
        reg._update_record(rec)
        assert client.get("/data/products",
                          headers={"Authorization": f"Bearer {tb}"}).status_code == 401


class TestFailClosed:
    def test_deployed_env_enforces_even_when_flag_says_false(self, monkeypatch):
        from api.dependencies import auth_required
        monkeypatch.setenv("HARVESTMIND_ENV", "prod")
        monkeypatch.setenv("HARVESTMIND_AUTH_REQUIRED", "false")
        assert auth_required() is True
        monkeypatch.setenv("HARVESTMIND_ENV", "pilot")
        monkeypatch.delenv("HARVESTMIND_AUTH_REQUIRED", raising=False)
        assert auth_required() is True

    def test_dev_stays_permissive_only_when_named_dev(self, monkeypatch):
        from api.dependencies import auth_required
        monkeypatch.setenv("HARVESTMIND_ENV", "dev")
        monkeypatch.delenv("HARVESTMIND_AUTH_REQUIRED", raising=False)
        assert auth_required() is False

    def test_health_reports_posture_without_secrets(self, monkeypatch):
        from fastapi.testclient import TestClient
        import api.main as api_main
        monkeypatch.setenv("HARVESTMIND_ENV", "prod")
        body = TestClient(api_main.app).get("/health").json()
        assert body["auth_enforced"] is True and body["env"] == "prod"
        assert not any(k.lower() in ("token", "key", "path") for k in body)
