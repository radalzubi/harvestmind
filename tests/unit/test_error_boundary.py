"""No traceback, no internal path, no exception text reaches a client."""
from fastapi.testclient import TestClient

import api.main as api_main


def test_unhandled_exception_is_generic_with_request_id(monkeypatch):
    @api_main.app.get("/__boom")
    def boom():
        raise RuntimeError("secret internal path /Users/x/harvestmind.duckdb")
    client = TestClient(api_main.app, raise_server_exceptions=False)
    r = client.get("/__boom")
    assert r.status_code == 500
    assert r.headers.get("X-Request-ID", "").startswith("req-")
    body = r.text
    assert "Traceback" not in body and "harvestmind.duckdb" not in body and "RuntimeError" not in body
    assert r.json()["request_id"] == r.headers["X-Request-ID"]


def test_every_response_carries_a_request_id():
    client = TestClient(api_main.app)
    r = client.get("/health")
    assert r.headers.get("X-Request-ID")
    r2 = client.get("/health", headers={"X-Request-ID": "trace-abc"})
    assert r2.headers["X-Request-ID"] == "trace-abc"
