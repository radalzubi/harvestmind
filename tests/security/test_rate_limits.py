"""Limits that an attacker cannot reset by lying about their address (SEC-008), a bounded failed-authentication
budget (SEC-001), bounded self-serve workspace creation (SEC-010) and route-keyed buckets (SEC-021)."""
from __future__ import annotations

import pytest

from tests.security.conftest import Tenants


@pytest.fixture()
def limited(monkeypatch):
    monkeypatch.setenv("HARVESTMIND_RATE_LIMIT_PER_MIN", "3")
    yield
    monkeypatch.setenv("HARVESTMIND_RATE_LIMIT_PER_MIN", "0")


def test_forwarded_for_does_not_reset_the_limit(tenants: Tenants, limited):
    c = tenants.client
    codes = []
    for n in range(5):
        # a different X-Forwarded-For every time: the limiter must not believe it
        r = c.post("/access/request", headers={"X-Forwarded-For": f"203.0.113.{n}"},
                   json={"company": "Probe Co", "contact_name": "Probe", "email": "p@example.com", "country": "JO", "sector": "commercial"})
        codes.append(r.status_code)
    assert codes[:3] == [200, 200, 200] and codes[3] == 429 and codes[4] == 429, codes
    assert "Retry-After" in c.post("/access/request", json={"company": "Probe Co", "contact_name": "Probe", "email": "p@example.com", "country": "JO", "sector": "commercial"}).headers


def test_fly_client_ip_is_the_address_of_record(tenants: Tenants, limited):
    from api.dependencies import client_ip
    from fastapi import Request
    scope = {"type": "http", "headers": [(b"fly-client-ip", b"198.51.100.7"), (b"x-forwarded-for", b"1.1.1.1")], "client": ("10.0.0.1", 1), "method": "GET", "path": "/", "query_string": b"", "scheme": "http", "server": ("x", 80)}
    assert client_ip(Request(scope)) == "198.51.100.7"
    scope["headers"] = [(b"x-forwarded-for", b"1.1.1.1")]
    assert client_ip(Request(scope)) == "10.0.0.1"


def test_the_limit_is_keyed_by_route_not_by_path(tenants: Tenants, limited):
    """An id in the path does not buy a fresh bucket: /jobs/{id}/cancel shares one budget per client."""
    c, a = tenants.client, tenants.a
    from api import dependencies
    seen = set()
    for n in range(4):
        c.post("/access/request", json={"company": f"Co {n}", "contact_name": "Probe", "email": "p@example.com", "country": "JO", "sector": "commercial"})
        seen |= {k[1] for k in dependencies._RL_BUCKETS}
    assert seen == {"/access/request"}
    assert len(dependencies._RL_BUCKETS) == 1
    del a


def test_failed_authentications_are_throttled(tenants: Tenants, monkeypatch):
    from api import dependencies
    monkeypatch.setattr(dependencies, "FAILED_AUTH_PER_MIN", 5)
    c = tenants.client
    codes = [c.get("/me", headers={"Authorization": f"Bearer guess-{n:06d}", "X-Forwarded-For": f"10.9.{n}.1"}).status_code for n in range(8)]
    assert codes[:5] == [401] * 5 and codes[5:] == [429] * 3, codes
    # the throttle answers before the registry is consulted: even the right token waits out the minute
    assert c.get("/me", headers=tenants.a.h()).status_code == 429
    dependencies._FAILED_AUTH.clear()
    assert c.get("/me", headers=tenants.a.h()).status_code == 200


def test_the_global_failed_authentication_budget_holds_across_addresses(tenants: Tenants, monkeypatch):
    from api import dependencies
    monkeypatch.setattr(dependencies, "FAILED_AUTH_GLOBAL_PER_MIN", 6)
    monkeypatch.setattr(dependencies, "FAILED_AUTH_PER_MIN", 100)
    c = tenants.client
    codes = [c.get("/me", headers={"Authorization": f"Bearer guess-{n}", "Fly-Client-IP": f"203.0.113.{n}"}).status_code for n in range(9)]
    assert codes[:6] == [401] * 6 and codes[6:] == [429] * 3, codes


def test_self_serve_daily_cap(tenants: Tenants, monkeypatch):
    from api.routers import access
    monkeypatch.setattr(access, "SELF_SERVE_PER_ADDRESS_PER_DAY", 2)
    monkeypatch.setattr(access, "SELF_SERVE_DAILY_CAP", 3)
    access._SELF_SERVE.clear()
    c = tenants.client
    body = {"sector": "commercial", "company": "Throwaway"}
    first = [c.post("/access/start", json=body, headers={"Fly-Client-IP": "203.0.113.50"}).status_code for _ in range(3)]
    assert first == [200, 200, 429], first
    other = c.post("/access/start", json=body, headers={"Fly-Client-IP": "203.0.113.51"}).status_code
    assert other == 200
    assert c.post("/access/start", json=body, headers={"Fly-Client-IP": "203.0.113.52"}).status_code == 429   # the daily cap
    access._SELF_SERVE.clear()
