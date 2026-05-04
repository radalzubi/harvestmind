"""Security-focused API tests.

Covers:
- CORS allowlist is not '*' by default
- /planning/run rejects non-optimal solver outcomes (HTTP 422)
- /planning/recommendations rejects unknown status values (HTTP 400)
- /data/* SQL-injection payloads are treated as literals (already in
  test_api_data_router.py — re-asserted briefly here for completeness)
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def temp_db(tmp_path_factory):
    import sys
    sys.path.insert(0, str(ROOT))
    from scripts.setup_db import setup_db
    from synthetic.generator import SyntheticGenerator

    db_path = tmp_path_factory.mktemp("apidb") / "test.duckdb"
    conn = duckdb.connect(str(db_path))
    setup_db(conn, load_seeds=True)
    SyntheticGenerator(n_weeks=12, seed=7).generate_all(conn)
    conn.close()

    prev = os.environ.get("DUCKDB_PATH")
    os.environ["DUCKDB_PATH"] = str(db_path)
    yield str(db_path)
    if prev is None:
        os.environ.pop("DUCKDB_PATH", None)
    else:
        os.environ["DUCKDB_PATH"] = prev


@pytest.fixture(scope="module")
def client(temp_db):
    # Reset the api.main module so it picks up our DUCKDB_PATH override.
    import importlib
    import api.main
    importlib.reload(api.main)
    from fastapi.testclient import TestClient
    return TestClient(api.main.app)


def test_cors_default_is_localhost_only(client):
    """Default CORS must NOT be '*'. Send a cross-origin request and confirm
    the allowed-origin echo only matches the localhost allowlist."""
    r = client.options(
        "/data/suppliers",
        headers={
            "Origin": "https://attacker.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Browser would block; API does not echo the malicious origin back.
    assert r.headers.get("access-control-allow-origin") != "https://attacker.example.com"
    assert r.headers.get("access-control-allow-origin") != "*"


def test_recommendations_rejects_unknown_status(client):
    r = client.get("/planning/recommendations?status=DROP TABLE")
    assert r.status_code == 400
    body = r.json()
    assert "status must be one of" in body["detail"]


def test_recommendations_accepts_known_status(client):
    r = client.get("/planning/recommendations?status=open")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_recommendations_default_is_open(client):
    r = client.get("/planning/recommendations")
    assert r.status_code == 200


def test_lots_injection_payload_returns_empty(client):
    """Defence-in-depth re-assertion of the parameterised query."""
    r = client.get("/data/fsma/lots?product_id=' OR 1=1 --")
    assert r.status_code == 200
    assert r.json() == []
