"""New canonical API isolation/limits; no operator vault is accessed."""
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from api.dependencies import require_operator
from api.routers import zaad
from zaad.contracts import PlanReport


@pytest.fixture
def payload():
    known = "2026-09-01T00:00:00Z"
    return {
        "operator_id": "tenant_a", "as_of": known, "warehouse_capacity": 10000,
        "review_budget": 10000, "evidence_label": "SYNTHETIC",
        "items": [{"id": "A", "location": "DC", "base_cost": 5, "selling_price": 8,
                   "holding_per_period": .1, "known_at": known}],
        "nodes": [{"id": "S", "kind": "supplier", "country": "JO", "known_at": known},
                  {"id": "DC", "kind": "dc", "country": "JO", "known_at": known}],
        "edges": [{"id": "E", "origin": "S", "destination": "DC", "mode": "road",
                   "capacity": 1000, "known_at": known}],
        "routes": [{"id": "R", "supplier": "S", "item": "A", "edges": ["E"],
                    "landed_cost": 6, "capacity": 1000, "approved": True,
                    "compliance": "cleared", "valid_until": "2026-10-01T00:00:00Z",
                    "quote_reference": "q-test", "known_at": known}],
        "demand": [], "deliveries": [],
    }


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("HARVESTMIND_ENV", "dev")
    monkeypatch.setenv("HARVESTMIND_AUTH_REQUIRED", "false")
    zaad._recent.clear()
    zaad._global_recent.clear()
    app = FastAPI()
    app.include_router(zaad.router)

    async def review(request):
        return PlanReport(operator_id=request.operator_id, as_of=request.as_of,
                          input_fingerprint="test-only", evidence_label=request.evidence_label,
                          status="ABSTAIN", mode="LEAN", selected_policy="incumbent", actions=(),
                          incumbent_actions=(), reasons=("Insufficient history",), frontier=(),
                          routes=(), forecasts=(), economics={}, evidence={}, limitations=("Test fixture",))
    monkeypatch.setattr(zaad, "_plan", review)
    return TestClient(app)


def test_canonical_request_is_recommendation_only(client, payload):
    result = client.post("/api/zaad/plan", json=payload)
    assert result.status_code == 200, result.text
    assert result.json()["approval_required"] is True
    assert result.json()["executable_purchase_order"] is False


def test_principal_mismatch_refused_in_dev(client, payload):
    client.app.dependency_overrides[require_operator] = lambda: "tenant_b"
    assert client.post("/api/zaad/plan", json=payload).status_code == 403


def test_production_requires_auth_even_with_false_override(client, payload, monkeypatch):
    monkeypatch.setenv("HARVESTMIND_ENV", "production")
    monkeypatch.setenv("ZAAD_LEGACY_PLANNERS", "1")     # this engine is superseded; served in production only when enabled explicitly
    assert client.post("/api/zaad/plan", json=payload).status_code == 401


def test_size_limit_without_content_length(client):
    chunks = (b" " * (512 * 1024) for _ in range(5))
    response = client.post("/api/zaad/plan", content=chunks, headers={"Content-Type": "application/json"})
    assert response.status_code == 413


def test_validation_does_not_echo_private_inputs(client, payload):
    payload["private_secret"] = "DO-NOT-ECHO-THIS"
    result = client.post("/api/zaad/plan", json=payload)
    assert result.status_code == 422
    assert "DO-NOT-ECHO-THIS" not in result.text


def test_future_inputs_and_nonfinite_numbers_refused(client, payload):
    payload["items"][0]["known_at"] = datetime(2030, 1, 1, tzinfo=timezone.utc).isoformat()
    assert client.post("/api/zaad/plan", json=payload).status_code == 422
    assert client.post("/api/zaad/plan", content='{"review_budget": NaN}',
                       headers={"Content-Type": "application/json"}).status_code == 422


def test_rate_cap_cannot_be_disabled_by_legacy_setting(client, monkeypatch):
    monkeypatch.setenv("HARVESTMIND_RATE_LIMIT_PER_MIN", "0")
    for _ in range(zaad.REQUESTS_PER_MINUTE):
        assert client.get("/api/zaad/schema").status_code == 200
    assert client.get("/api/zaad/schema").status_code == 429


def test_bad_content_type_and_malformed_json(client):
    assert client.post("/api/zaad/plan", content="{}").status_code == 415
    assert client.post("/api/zaad/plan", content="{", headers={"Content-Type": "application/json"}).status_code == 422


def test_actual_engine_abstains_without_histories(payload, monkeypatch):
    monkeypatch.setenv("HARVESTMIND_ENV", "dev")
    monkeypatch.setenv("HARVESTMIND_AUTH_REQUIRED", "false")
    zaad._recent.clear()
    zaad._global_recent.clear()
    app = FastAPI()
    app.include_router(zaad.router)
    response = TestClient(app).post("/api/zaad/plan", json=payload)
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["status"] == "ABSTAIN"
    assert report["actions"] == []
    assert report["executable_purchase_order"] is False
    assert report["input_fingerprint"]
