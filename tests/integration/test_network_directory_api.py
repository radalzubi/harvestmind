"""`/api/zaad/network/directory`: the read-only master-data projection the product uses to name and
place suppliers. It reads the operator's own vault, runs no planner, and answers an empty directory
rather than an error when the optional uploads are absent."""
from __future__ import annotations

import duckdb
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dependencies import get_conn, require_operator
from api.routers import zaad_full
from scripts.setup_db import setup_db


@pytest.fixture(scope="module")
def vault():
    from scripts.zaad_network_workspace_smoke import make_network_vault
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    make_network_vault(conn, seed=7)
    return conn


def _app(conn, operator: str | None = "tenant_n") -> FastAPI:
    app = FastAPI()
    app.include_router(zaad_full.router)

    def conn_override():
        yield conn

    app.dependency_overrides[get_conn] = conn_override
    app.dependency_overrides[require_operator] = lambda: operator
    return app


def test_directory_returns_declared_suppliers_and_locations(monkeypatch, vault):
    monkeypatch.setenv("HARVESTMIND_ENV", "pilot")
    client = TestClient(_app(vault))
    r = client.get("/api/zaad/network/directory")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["provenance"] == "OPERATOR_DECLARED"
    assert set(body["rows_read"]) == {"stg_fmcg_suppliers", "stg_fmcg_locations"}
    ids = [s["id"] for s in body["suppliers"]]
    assert ids == sorted(ids), "suppliers are returned in a stable order"
    for supplier in body["suppliers"]:
        assert set(supplier) == {"id", "name", "origin_iso3", "route", "capacity_per_week",
                                 "lead_time_promised_weeks", "risk_group", "risk_group_kind"}
    for location in body["locations"]:
        assert set(location) == {"id", "kind", "capacity_units"}
    # the network vault declares three locations; the projection must not lose or duplicate one
    assert len(body["locations"]) == len({loc["id"] for loc in body["locations"]})


def test_directory_never_plans_and_needs_no_optional_upload(monkeypatch):
    monkeypatch.setenv("HARVESTMIND_ENV", "pilot")
    empty = duckdb.connect(":memory:")
    setup_db(empty)
    client = TestClient(_app(empty))
    r = client.get("/api/zaad/network/directory")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["suppliers"] == [] and body["locations"] == []
    assert body["rows_read"] == {"stg_fmcg_suppliers": 0, "stg_fmcg_locations": 0}


def test_directory_requires_an_operator(monkeypatch, vault):
    monkeypatch.setenv("HARVESTMIND_ENV", "pilot")
    client = TestClient(_app(vault, operator=None))
    assert client.get("/api/zaad/network/directory").status_code == 401


def test_directory_reads_only_the_callers_vault(monkeypatch):
    """Two operators, two connections: the projection returns what its own connection holds. The
    per-request connection is the tenant boundary, exactly as every other workspace endpoint."""
    monkeypatch.setenv("HARVESTMIND_ENV", "pilot")
    mine = duckdb.connect(":memory:")
    setup_db(mine)
    mine.execute("INSERT INTO stg_fmcg_suppliers (supplier_id, supplier_name, origin_iso3, route) VALUES ('S1', 'Mine', 'CHN', 'red_sea')")
    theirs = duckdb.connect(":memory:")
    setup_db(theirs)
    theirs.execute("INSERT INTO stg_fmcg_suppliers (supplier_id, supplier_name, origin_iso3, route) VALUES ('S9', 'Theirs', 'IND', 'hormuz')")

    got_mine = TestClient(_app(mine, operator="a")).get("/api/zaad/network/directory").json()
    got_theirs = TestClient(_app(theirs, operator="b")).get("/api/zaad/network/directory").json()
    assert [s["name"] for s in got_mine["suppliers"]] == ["Mine"]
    assert [s["name"] for s in got_theirs["suppliers"]] == ["Theirs"]
    assert got_mine["suppliers"][0]["origin_iso3"] == "CHN" and got_mine["suppliers"][0]["route"] == "red_sea"
