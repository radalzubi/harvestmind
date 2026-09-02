"""Training control and corpus metadata are administrative surfaces."""

from fastapi.testclient import TestClient

import api.main as api_main


def test_training_rejects_wrong_admin_key(monkeypatch):
    monkeypatch.setenv("HARVESTMIND_ADMIN_KEY", "correct-key")
    client = TestClient(api_main.app)
    response = client.get(
        "/training/corpus/stats", headers={"X-Admin-Key": "wrong-key"}
    )
    assert response.status_code == 401


def test_training_corpus_stats_accepts_admin_key(monkeypatch):
    monkeypatch.setenv("HARVESTMIND_ADMIN_KEY", "correct-key")
    client = TestClient(api_main.app)
    response = client.get(
        "/training/corpus/stats", headers={"X-Admin-Key": "correct-key"}
    )
    assert response.status_code == 200
    assert {"stats", "quality"} <= set(response.json())
