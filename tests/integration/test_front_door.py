"""Front door: a company requests access, the admin approves, the token
connects the workspace, /me reports the sector, and a diagnostic job can be
started and reports its status."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import api.main as api_main
from infrastructure import operator_registry as reg_mod
from infrastructure.operator_registry import OperatorRegistry


@pytest.fixture()
def registry(tmp_path, monkeypatch):
    reg = OperatorRegistry(data_root=tmp_path / "data")
    monkeypatch.setattr(reg_mod, "DEFAULT_DATA_ROOT", tmp_path / "data")
    monkeypatch.setenv("HARVESTMIND_ADMIN_KEY", "test-admin-key-not-a-secret")
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    return reg


def test_request_approve_connect_and_me(registry):
    cl = TestClient(api_main.app)
    r = cl.post("/access/request", json={"company": "NTDCO", "contact_name": "Buyer", "email": "buyer@example.com",
                                        "country": "Jordan", "sector": "commercial", "erp": "SAP B1", "sku_count": 800})
    assert r.status_code == 200, r.text
    rid = r.json()["id"]
    assert r.json()["status"] == "pending"

    # invalid sector and email are refused
    assert cl.post("/access/request", json={"company": "X Co", "contact_name": "A B", "email": "nope",
                                            "country": "JO", "sector": "commercial"}).status_code == 422
    assert cl.post("/access/request", json={"company": "X Co", "contact_name": "A B", "email": "a@b.co",
                                            "country": "JO", "sector": "mining"}).status_code == 422

    # admin only
    assert cl.get("/admin/access-requests").status_code == 401
    h = {"X-Admin-Key": "test-admin-key-not-a-secret"}
    pending = cl.get("/admin/access-requests", headers=h).json()
    assert [p["id"] for p in pending] == [rid]

    a = cl.post(f"/admin/access-requests/{rid}/approve", headers=h)
    assert a.status_code == 200, a.text
    body = a.json()
    assert body["sector"] == "commercial" and body["email_sent"] is False and "token=" in body["access_link"]
    token = body["access_link"].split("token=")[1]
    assert cl.post(f"/admin/access-requests/{rid}/approve", headers=h).status_code == 409

    me = cl.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["sector"] == "commercial" and me.json()["name"] == "NTDCO"
    assert cl.get("/me").status_code == 401

    # a diagnostic on an empty vault starts, then fails honestly rather than hanging
    j = cl.post("/jobs/diagnostic", headers={"Authorization": f"Bearer {token}"})
    assert j.status_code == 200, j.text
    jid = j.json()["id"]
    import time
    for _ in range(100):
        st = cl.get(f"/jobs/{jid}", headers={"Authorization": f"Bearer {token}"}).json()
        if st["status"] in ("done", "failed"):
            break
        time.sleep(0.2)
    assert st["status"] in ("done", "failed")
    assert "operator_id" not in st
    # another operator cannot see it
    other = registry.create_operator("Other", sector="produce")
    t2 = registry.issue_token(other.operator_id)
    assert cl.get(f"/jobs/{jid}", headers={"Authorization": f"Bearer {t2}"}).status_code == 404


def test_self_serve_start_creates_isolated_workspace(registry):
    cl = TestClient(api_main.app)
    a = cl.post("/access/start", json={"sector": "produce", "company": "Green Hub"})
    b = cl.post("/access/start", json={"sector": "commercial"})
    assert a.status_code == 200 and b.status_code == 200, (a.text, b.text)
    ta, tb = a.json()["token"], b.json()["token"]
    assert a.json()["operator_id"] != b.json()["operator_id"]
    assert cl.get("/me", headers={"Authorization": f"Bearer {ta}"}).json()["sector"] == "produce"
    assert cl.get("/me", headers={"Authorization": f"Bearer {tb}"}).json()["name"].startswith("Workspace")
    assert cl.post("/access/start", json={"sector": "banking"}).status_code == 422


def test_key_only_mode(registry, monkeypatch):
    monkeypatch.setenv("HARVESTMIND_SELF_SERVE", "false")
    cl = TestClient(api_main.app)
    assert cl.get("/access/config").json()["self_serve"] is False
    assert cl.post("/access/start", json={"sector": "commercial"}).status_code == 404
    h = {"X-Admin-Key": "test-admin-key-not-a-secret"}
    w = cl.post("/admin/workspaces", json={"name": "NTDCO", "sector": "commercial", "region": "Jordan"}, headers=h)
    assert w.status_code == 200, w.text
    tok = w.json()["token"]
    assert cl.get("/me", headers={"Authorization": f"Bearer {tok}"}).json()["name"] == "NTDCO"
    listing = cl.get("/admin/workspaces", headers=h).json()
    assert [x["name"] for x in listing] == ["NTDCO"] and "token" not in listing[0]


def test_short_key_opens_seeded_workspace_and_greets_the_company(registry, monkeypatch):
    monkeypatch.setenv("HARVESTMIND_SEED_WORKSPACES", "NTDCO|commercial|839285|/logos/ntdco.svg")
    from infrastructure.seed_workspaces import seed_workspaces_from_env
    ids = seed_workspaces_from_env(registry)
    assert len(ids) == 1
    # idempotent: a second seeding keeps the same workspace
    assert seed_workspaces_from_env(registry) == ids
    cl = TestClient(api_main.app)
    me = cl.get("/me", headers={"Authorization": "Bearer 839285"})
    assert me.status_code == 200, me.text
    assert me.json()["display_name"] == "NTDCO" and me.json()["logo_url"] == "/logos/ntdco.svg"
    assert me.json()["sector"] == "commercial"
    assert cl.get("/me", headers={"Authorization": "Bearer 839286"}).status_code == 401
    # the code is stored hashed, never in clear
    import json as _json
    raw = _json.dumps(_json.loads((registry.registry_dir / "operators.json").read_text()))
    assert "839285" not in raw
