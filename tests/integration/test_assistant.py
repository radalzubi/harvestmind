"""Assistant endpoints without a model key: the plain reading, never a guess."""
from __future__ import annotations

import pytest

import infrastructure.operator_registry as orm


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(orm, "DEFAULT_DATA_ROOT", tmp_path / "data")
    reg = orm.OperatorRegistry(data_root=tmp_path / "data")
    op = reg.create_operator("Ask Co", sector="commercial")
    tok = reg.issue_token(op.operator_id)
    monkeypatch.setenv("HARVESTMIND_AUTH_REQUIRED", "true")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from fastapi.testclient import TestClient
    import api.main as api_main
    return TestClient(api_main.app), {"Authorization": f"Bearer {tok}"}


def test_summary_and_ask_without_data(client):
    cl, h = client
    r = cl.get("/assistant/summary", headers=h)
    assert r.status_code == 200 and r.json()["source"] == "none" and "upload" in r.json()["summary"].lower()
    r = cl.get("/assistant/summary?lang=ar", headers=h)
    assert "حمّل" in r.json()["summary"]
    r = cl.post("/assistant/ask", headers=h, json={"question": "why?"})
    assert r.status_code == 200 and r.json()["source"] == "rules"
    assert cl.post("/assistant/ask", headers=h, json={"question": ""}).status_code == 422
    assert cl.get("/assistant/summary").status_code == 401


def test_summary_with_sample_data_is_plain(client):
    cl, h = client
    r = cl.post("/intake/load-sample-fmcg", headers=h)
    assert r.status_code == 200, r.text
    r = cl.get("/assistant/summary", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"] == "rules"
    # H3a: the fallback names the incumbent as the reconstructed rule, never as "your current policy"
    assert "reconstructed historical rule" in body["summary"] or "optimizer" in body["summary"]
    assert "current policy" not in body["summary"]
    assert "cvar" not in body["summary"].lower()
    st = cl.get("/fmcg/state", headers=h).json()
    assert st["plain"]["headline"] and st["plain"]["posture"]
