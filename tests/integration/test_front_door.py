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
