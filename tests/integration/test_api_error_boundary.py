"""An unhandled error must still be readable from the browser.

The request-id boundary answers a 500 with a generic message and the id to quote to support. When
it sat outside the CORS middleware, that response carried no ``Access-Control-Allow-Origin``, so a
cross-origin page could not read it at all: the operator saw "Failed to fetch" and had no id to
quote. The boundary now sits inside CORS. This test raises from a route on the real app and reads
the headers the way a browser would.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

import api.main as api_main


def test_a_500_carries_cors_headers_and_a_request_id(monkeypatch):
    app = api_main.app

    async def boom():
        raise RuntimeError("deliberate")

    app.add_api_route("/__audit_boom", boom, methods=["GET"])
    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/__audit_boom", headers={"Origin": "http://localhost:3000"})
    finally:
        app.router.routes[:] = [r for r in app.router.routes if getattr(r, "path", "") != "/__audit_boom"]
    assert response.status_code == 500
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert response.headers.get("x-request-id", "").startswith("req-")
    assert "X-Request-ID" in response.headers.get("access-control-expose-headers", "")
    body = response.json()
    assert body["request_id"] == response.headers["x-request-id"]
    assert "deliberate" not in response.text, "a stack trace or exception text must never reach a browser"


def test_a_refused_origin_still_gets_no_cors_header_on_a_500():
    app = api_main.app

    async def boom():
        raise RuntimeError("deliberate")

    app.add_api_route("/__audit_boom2", boom, methods=["GET"])
    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/__audit_boom2", headers={"Origin": "https://evil.example"})
    finally:
        app.router.routes[:] = [r for r in app.router.routes if getattr(r, "path", "") != "/__audit_boom2"]
    assert response.status_code == 500
    assert "access-control-allow-origin" not in response.headers
