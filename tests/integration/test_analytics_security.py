"""Adversarial: cross-tenant ids, forged ids, SQL attempts, oversized inputs, role escalation."""
from __future__ import annotations

from datetime import date

import duckdb
import pytest

from api.analytics import cache
from scripts.setup_db import setup_db
from synthetic.fmcg.demo_company import load_demo_company_into
from tests.integration.test_analytics_api import DEMAND, FILL, client_for, visual

AS_OF = date(2026, 9, 15)


@pytest.fixture(scope="module")
def vault():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    load_demo_company_into(conn, "tenant_a", as_of=AS_OF)
    return conn


@pytest.fixture(scope="module")
def a(vault):
    return client_for(vault, operator="tenant_a", role="ADMIN")


@pytest.fixture(scope="module")
def b(vault):
    return client_for(vault, operator="tenant_b", role="ADMIN")


def test_cross_tenant_analysis_and_dashboard_ids_are_not_found(a, b):
    an = a.post("/api/zaad/analytics/analyses", json={"name": "A's", "visual": visual(DEMAND), "visibility": "workspace"}).json()
    db = a.post("/api/zaad/analytics/dashboards", json={"name": "A's board", "spec": {"tiles": [{"tile_id": "t", "analysis_id": an["analysis_id"]}]}, "visibility": "workspace"}).json()
    for path in (f"/api/zaad/analytics/analyses/{an['analysis_id']}", f"/api/zaad/analytics/dashboards/{db['dashboard_id']}"):
        assert b.get(path).status_code == 404
        assert b.patch(path, json={"name": "mine now"}).status_code == 404
        assert b.delete(path).status_code == 404
    assert b.post(f"/api/zaad/analytics/analyses/{an['analysis_id']}/run").status_code == 404
    assert b.post(f"/api/zaad/analytics/dashboards/{db['dashboard_id']}/duplicate").status_code == 404
    # B cannot compose A's analysis into a dashboard
    r = b.post("/api/zaad/analytics/dashboards", json={"name": "steal", "spec": {"tiles": [{"tile_id": "t", "analysis_id": an["analysis_id"]}]}})
    assert r.status_code == 422
    assert b.get("/api/zaad/analytics/analyses").json()["total"] == 0


def test_cross_tenant_cache_never_serves_another_tenants_result(a, b):
    cache.clear()
    first = a.post("/api/zaad/analytics/query", json=DEMAND).json()
    assert first["timing"]["cache"] == "miss"
    assert a.post("/api/zaad/analytics/query", json=DEMAND).json()["timing"]["cache"] == "hit"
    other = b.post("/api/zaad/analytics/query", json=DEMAND).json()
    assert other["timing"]["cache"] == "miss"
    assert cache.stats()["entries"] >= 2


def test_forged_metric_and_dimension_ids_and_sql_are_refused(a):
    for payload in ({"measures": [{"metric_id": "ordered_units; DROP TABLE stg_fmcg_orders"}]},
                    {"measures": [{"metric_id": "ordered_units"}], "dimensions": [{"dimension_id": "sku) UNION SELECT token FROM registry --"}]},
                    {"measures": [{"metric_id": "ordered_units"}], "filters": [{"dimension_id": "sku", "op": "raw", "values": ["1=1"]}]},
                    {"measures": [{"metric_id": "ordered_units"}], "sort": [{"field": "1; SELECT 1", "dir": "desc"}]},
                    {"measures": [{"metric_id": "ordered_units"}], "time": {"grain": "decade"}},
                    {"measures": [{"metric_id": "ordered_units"}], "time": {"anchor": "(SELECT 1)"}},
                    {"measures": [], "dimensions": []}):
        r = a.post("/api/zaad/analytics/query", json=payload)
        assert r.status_code == 422, payload
        assert r.json()["detail"]["code"] in ("spec_invalid", "semantic_unknown_metric", "semantic_unknown_dimension", "semantic_invalid_time", "semantic_invalid_filter")


def test_filter_values_bind_and_never_widen(a):
    r = a.post("/api/zaad/analytics/query", json={"measures": [{"metric_id": "ordered_units"}], "filters": [{"dimension_id": "category", "op": "eq", "values": ["Beverages' OR '1'='1"]}]})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "spec_invalid"     # `=` is outside the value alphabet
    r = a.post("/api/zaad/analytics/query", json={"measures": [{"metric_id": "ordered_units"}], "filters": [{"dimension_id": "category", "op": "eq", "values": ["Beverages' OR 'x"]}]})
    assert r.status_code == 200 and r.json()["empty"] is True                          # a legal odd value binds and matches nothing
    r = a.post("/api/zaad/analytics/query", json={"measures": [{"metric_id": "ordered_units"}], "filters": [{"dimension_id": "category", "op": "contains", "values": ["%"]}]})
    assert r.status_code == 422                                                         # `%` is outside the value alphabet
    r = a.post("/api/zaad/analytics/query", json={"measures": [{"metric_id": "ordered_units"}], "filters": [{"dimension_id": "category", "op": "contains", "values": ["_"]}]})
    assert r.status_code == 200 and r.json()["empty"] is True                          # a literal underscore, not a wildcard


def test_oversized_inputs_are_bounded(a):
    too_many = {"measures": [{"metric_id": "ordered_units"}], "filters": [{"dimension_id": "sku", "op": "in", "values": [f"S{i}" for i in range(201)]}]}
    assert a.post("/api/zaad/analytics/query", json=too_many).status_code == 422
    assert a.post("/api/zaad/analytics/query", json={"measures": [{"metric_id": "ordered_units"}], "limit": 100000}).status_code == 422
    assert a.post("/api/zaad/analytics/query", json={"measures": [{"metric_id": m} for m in ("ordered_units", "shipped_units", "unfulfilled_units", "fill_rate", "ordered_lines", "customers_ordering", "customer_order_units")]}).status_code == 422
    explosion = {"measures": [{"metric_id": "ordered_units"}], "dimensions": [{"dimension_id": "sku"}, {"dimension_id": "customer"}], "time": {"grain": "day"}}
    out = a.post("/api/zaad/analytics/query", json=explosion).json()
    assert out["bounds"]["truncated"] is True and len(out["rows"]) <= 400
    assert a.post("/api/zaad/analytics/ask", json={"question": "x" * 2000}).status_code == 422
    big = a.post("/api/zaad/analytics/query", content="{" + '"a":' * 200000 + "1}", headers={"Content-Type": "application/json"})
    assert big.status_code in (400, 413)


def test_role_escalation_is_refused_at_every_write(vault):
    viewer = client_for(vault, operator="tenant_a", role="VIEWER")
    buyer = client_for(vault, operator="tenant_a", role="BUYER")
    assert viewer.post("/api/zaad/analytics/analyses", json={"name": "x", "visual": visual(DEMAND)}).status_code == 403
    assert viewer.post("/api/zaad/analytics/dashboards", json={"name": "x"}).status_code == 403
    assert viewer.post("/api/zaad/analytics/export?fmt=csv", json=DEMAND).status_code == 403
    assert viewer.post("/api/zaad/analytics/ask", json={"question": "demand"}).status_code == 403
    assert viewer.post("/api/zaad/analytics/handoff", json={"query": FILL, "suppliers": ["DEMO-SUP-02"]}).status_code == 403
    # a buyer cannot share, and cannot submit a plan without the evaluate capability being checked
    own = buyer.post("/api/zaad/analytics/analyses", json={"name": "mine", "visual": visual(DEMAND), "visibility": "workspace"})
    assert own.status_code == 403
    # a viewer reads OPERATIONAL only
    r = viewer.post("/api/zaad/analytics/query", json={"measures": [{"metric_id": "inventory_value"}]})
    assert r.status_code == 403 and r.json()["detail"]["code"] == "permission_denied"
    r = viewer.post("/api/zaad/analytics/query", json={"measures": [{"metric_id": "ordered_units"}]})
    assert r.status_code == 200
    # another actor in the same workspace cannot edit a private analysis they do not own
    mine = buyer.post("/api/zaad/analytics/analyses", json={"name": "mine", "visual": visual(DEMAND)}).json()
    other_buyer = client_for(vault, operator="tenant_a", role="BUYER", actor_id="someone_else")
    assert other_buyer.get(f"/api/zaad/analytics/analyses/{mine['analysis_id']}").status_code == 404
    assert other_buyer.patch(f"/api/zaad/analytics/analyses/{mine['analysis_id']}", json={"name": "x"}).status_code == 404


def test_ai_output_with_sql_or_expressions_never_reaches_the_engine(vault, monkeypatch):
    from api.analytics.ai import service
    from api.analytics.ai.provider import PlanCandidate
    from tests.integration.test_analytics_api import FakeProvider
    executed: list = []
    from api.analytics import query as query_module
    real = query_module.run

    def spy(conn, operator, actor, spec, **kw):
        executed.append(spec.canonical())
        return real(conn, operator, actor, spec, **kw)

    monkeypatch.setattr(service.query, "run", spy)
    fake = FakeProvider([PlanCandidate(intent="detail", query_spec={"measures": [{"metric_id": "ordered_units"}], "filters": [{"dimension_id": "sku", "op": "eq", "values": ["' OR 1=1 --"]}]}, source="model"),
                         PlanCandidate(intent="detail", query_spec={"measures": [{"metric_id": "ordered_units"}], "raw_sql": "DROP TABLE stg_fmcg_orders"}, source="model")])
    monkeypatch.setattr(service, "default_provider", lambda: fake)
    c = client_for(vault, operator="tenant_a", role="BUYER")
    body = c.post("/api/zaad/analytics/ask", json={"question": "demand"}).json()
    assert body["answered"]
    assert all("raw_sql" not in e and all("OR 1=1" not in str(f) for f in e.get("filters", [])) for e in executed)
    assert vault.execute("SELECT count(*) FROM stg_fmcg_orders").fetchone()[0] > 0
