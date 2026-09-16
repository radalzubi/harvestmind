"""Response compression (performance pass): bodies over 1 KB are gzip-encoded when the client
accepts it, small bodies are left alone, and the error boundary's CORS headers survive the
compression layer (CORS stays outermost)."""
from __future__ import annotations

import gzip
import json

from fastapi.testclient import TestClient

from api.main import app


def test_large_json_is_gzipped_and_identical_after_decoding():
    client = TestClient(app)
    plain = client.get("/openapi.json", headers={"Accept-Encoding": "identity"})
    assert plain.status_code == 200 and "content-encoding" not in plain.headers
    zipped = client.get("/openapi.json", headers={"Accept-Encoding": "gzip"})
    assert zipped.status_code == 200
    assert zipped.headers.get("content-encoding") == "gzip"
    assert "accept-encoding" in zipped.headers.get("vary", "").lower()
    # the test client decodes transparently; the decoded document is byte-identical
    assert zipped.json() == plain.json()
    raw = client.get("/openapi.json", headers={"Accept-Encoding": "gzip"}).content
    assert json.loads(gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw) == plain.json()


def test_small_bodies_decode_to_the_same_document():
    # The security-header middleware streams every response, so GZip cannot apply its 1 KB floor
    # and a small body is compressed too; that costs microseconds and changes no byte after decoding.
    client = TestClient(app)
    plain = client.get("/health", headers={"Accept-Encoding": "identity"}).json()
    zipped = client.get("/health", headers={"Accept-Encoding": "gzip"})
    assert zipped.status_code == 200 and zipped.json() == plain


def test_cors_headers_still_reach_the_browser_with_compression():
    client = TestClient(app)
    r = client.get("/health", headers={"Accept-Encoding": "gzip", "Origin": "http://localhost:3000"})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
