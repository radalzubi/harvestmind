"""Insights: server-side aggregations that equal the rows, honest nulls, bounded payloads, tenant scope.

Every test runs against the demo company loaded into an in-memory vault, through the router, and
the plan-backed tests write a completed plan into a job store the way the runner does — Insights
only ever reads one.
"""
from __future__ import annotations

import json
from datetime import date

import duckdb
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dependencies import get_conn, require_operator
from api.routers import zaad_insights
from scripts.setup_db import setup_db
from synthetic.fmcg.demo_company import SHORTAGE_SKU, SPIKE_SKUS, load_demo_company_into
from zaad.full.demo import example
from zaad.full.jobs import JobStore

AS_OF = date(2026, 9, 15)
OPERATOR = "tenant_insights"


@pytest.fixture(scope="module")
def vault():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    load_demo_company_into(conn, OPERATOR, as_of=AS_OF)
    return conn


def _client(conn, operator: str | None = OPERATOR) -> TestClient:
    app = FastAPI()
    app.include_router(zaad_insights.router)

    def conn_override():
        yield conn

    app.dependency_overrides[get_conn] = conn_override
    app.dependency_overrides[require_operator] = lambda: operator
    return TestClient(app)


@pytest.fixture(scope="module")
def client(vault):
    return _client(vault)


def _sum(conn, sql, params=None):
    return conn.execute(sql, params or []).fetchone()[0]


# ── demand ─────────────────────────────────────────────────────────────────────

def test_demand_is_observed_orders_and_equals_the_rows(client, vault):
    body = client.get("/api/zaad/insights/demand?bucket=week").json()
    assert body["label"] == "OBSERVED CUSTOMER ORDERS" and body["fulfilment"] == "MEASURED"
    assert sum(r["ordered"] for r in body["series"]) == _sum(vault, "SELECT sum(qty_ordered) FROM stg_fmcg_orders")
    assert sum(r["shipped"] for r in body["series"]) == _sum(vault, "SELECT sum(qty_shipped) FROM stg_fmcg_orders")
    assert all(r["unfulfilled"] == r["ordered_measured"] - r["shipped"] for r in body["series"])
    assert body["provenance"]["numerator"].startswith("sum(qty_ordered)") and body["provenance"]["source_data"]
    assert body["provenance"]["last_updated"]


def test_weekly_and_monthly_buckets_carry_the_same_total(client):
    week = client.get("/api/zaad/insights/demand?bucket=week").json()
    month = client.get("/api/zaad/insights/demand?bucket=month").json()
    day = client.get("/api/zaad/insights/demand?bucket=day&start=2026-08-01&end=2026-09-14").json()
    assert sum(r["ordered"] for r in week["series"]) == sum(r["ordered"] for r in month["series"])
    assert len(month["series"]) < len(week["series"]) and 0 < len(day["series"]) <= 45
    assert client.get("/api/zaad/insights/demand?bucket=year").status_code == 422
    assert client.get("/api/zaad/insights/demand?start=2026-09-01&end=2026-08-01").status_code == 422


def test_filters_narrow_the_rows_and_bind_as_values(client, vault):
    by_sku = client.get(f"/api/zaad/insights/demand?bucket=month&sku={SHORTAGE_SKU}").json()
    assert sum(r["ordered"] for r in by_sku["series"]) == _sum(vault, "SELECT sum(qty_ordered) FROM stg_fmcg_orders WHERE sku = ?", [SHORTAGE_SKU])
    by_cat = client.get("/api/zaad/insights/demand?bucket=month&category=Beverages").json()
    assert sum(r["ordered"] for r in by_cat["series"]) == _sum(vault, "SELECT sum(o.qty_ordered) FROM stg_fmcg_orders o JOIN stg_fmcg_skus m ON m.sku = o.sku WHERE m.category = 'Beverages'")
    by_cust = client.get("/api/zaad/insights/demand?bucket=month&customer=DEMO-CUST-GROW").json()
    assert sum(r["ordered"] for r in by_cust["series"]) == _sum(vault, "SELECT sum(qty_ordered) FROM stg_fmcg_orders WHERE customer_id = 'DEMO-CUST-GROW'")
    by_site = client.get("/api/zaad/insights/demand?bucket=month&location=DEMO-BR-AQABA").json()
    assert sum(r["ordered"] for r in by_site["series"]) == _sum(vault, "SELECT sum(qty_ordered) FROM stg_fmcg_orders WHERE location_id = 'DEMO-BR-AQABA'")
    injected = client.get("/api/zaad/insights/demand?bucket=month&customer=x' OR 1=1 --").json()
    assert injected["series"] == [] and injected["totals"]["lines"] == 0
    assert client.get("/api/zaad/insights/demand?sku=" + "x" * 200).status_code == 422


def test_customer_concentration_and_period_over_period(client, vault):
    body = client.get("/api/zaad/insights/demand?bucket=month").json()
    c = body["concentration"]
    total = _sum(vault, "SELECT sum(qty_ordered) FROM stg_fmcg_orders")
    top = _sum(vault, "SELECT max(q) FROM (SELECT sum(qty_ordered) q FROM stg_fmcg_orders GROUP BY customer_id)")
    assert abs(c["top_1_share"] - top / total) < 1e-9 and 0 < c["top_5_share"] <= 1 and 0 < c["hhi"] <= 1
    assert c["customers"] == 8
    pop = body["period_over_period"]
    assert pop["change"] == pop["ordered"] - pop["previous_ordered"]


def test_a_period_opens_to_the_customers_and_products_behind_it(client, vault):
    week = vault.execute("SELECT date_trunc('week', min(order_date)) FROM stg_fmcg_orders WHERE customer_id = 'DEMO-CUST-GROW' AND sku = ? "
                         "AND qty_ordered = (SELECT max(qty_ordered) FROM stg_fmcg_orders WHERE customer_id = 'DEMO-CUST-GROW' AND sku = ?)",
                         [SPIKE_SKUS[0], SPIKE_SKUS[0]]).fetchone()[0]
    body = client.get(f"/api/zaad/insights/demand/period?bucket=week&period={week.isoformat()}").json()
    assert body["available"] and body["top_customers"][0]["id"] == "DEMO-CUST-GROW"
    assert {r["sku"] for r in body["largest_increases"][:3]} & set(SPIKE_SKUS)
    involved = {r["id"] for r in body["top_skus"]}
    assert {r["sku"] for r in body["affected_inventory"]} <= involved
    assert all(r["open_units"] > 0 for r in body["open_purchase_orders"])
    assert body["related_decisions"] == [], "no plan exists, so no decision is claimed"
    assert body["links"]["data"]["dataset"] == "customer_orders"
    assert client.get("/api/zaad/insights/demand/period?period=notadate").status_code == 422


# ── inventory, supply, suppliers, service ──────────────────────────────────────

def test_inventory_history_comes_from_snapshots_and_sites_sum_to_the_total(client, vault):
    body = client.get("/api/zaad/insights/inventory?bucket=month").json()
    latest = _sum(vault, "SELECT max(snapshot_date) FROM stg_fmcg_inventory")
    assert body["latest_snapshot"] == latest.isoformat()
    assert body["series"][-1]["units"] == _sum(vault, "SELECT sum(on_hand) FROM stg_fmcg_inventory WHERE snapshot_date = ?", [latest])
    assert sum(r["units"] for r in body["by_site"]) == body["series"][-1]["units"]
    assert body["series"][-1]["value"] == pytest.approx(_sum(vault, "SELECT sum(i.on_hand * m.unit_cost) FROM stg_fmcg_inventory i JOIN stg_fmcg_skus m ON m.sku = i.sku WHERE snapshot_date = ?", [latest]))
    assert len(body["series"]) >= 24 and body["position"]["weeks_of_cover"] > 0
    site = client.get("/api/zaad/insights/inventory?bucket=month&location=DEMO-BR-AQABA").json()
    whole = next(r for r in body["by_site"] if r["id"] == "DEMO-BR-AQABA")
    assert site["by_site"][0]["units"] == whole["units"] and site["by_site"][0]["value"] == pytest.approx(whole["value"])
    assert site["position"]["on_hand"] < body["position"]["on_hand"]


def test_supply_open_orders_agree_with_the_purchase_orders_page_rule(client, vault):
    body = client.get(f"/api/zaad/insights/supply?bucket=week&end={AS_OF.isoformat()}").json()
    open_units = _sum(vault, "SELECT sum(qty_ordered) FROM stg_fmcg_purchase_orders WHERE po_id NOT IN (SELECT po_id FROM stg_fmcg_receipts)")
    assert body["totals"]["open_units"] == open_units
    assert sum(r["units"] for r in body["open_by_expected_arrival"]) + body["open_without_expected_date"]["units"] == open_units
    assert body["open_without_expected_date"]["orders"] > 0, "orders without a promised date are counted apart, not dated"
    assert sum(r["units"] for r in body["aging"]) == open_units
    assert sum(r["units"] for r in body["received"]) == _sum(vault, "SELECT sum(qty_received) FROM stg_fmcg_receipts")
    assert {r["id"] for r in body["by_destination"]} == {"DEMO-DC-AMMAN"}


def test_supply_filtered_by_supplier_or_site_still_binds_in_order(client, vault):
    body = client.get(f"/api/zaad/insights/supply?bucket=week&end={AS_OF.isoformat()}&supplier=DEMO-SUP-02").json()
    assert body["available"] and {r["id"] for r in body["by_supplier"]} == {"DEMO-SUP-02"}
    assert sum(r["units"] for r in body["aging"]) == body["totals"]["open_units"] > 0
    site = client.get(f"/api/zaad/insights/supply?bucket=week&end={AS_OF.isoformat()}&location=DEMO-DC-AMMAN&category=Paper").json()
    assert site["available"] and sum(r["units"] for r in site["aging"]) == site["totals"]["open_units"]
    assert client.get("/api/zaad/insights/inventory?bucket=week&location=DEMO-BR-IRBID&category=Paper").json()["available"]


def test_supplier_metrics_carry_their_denominators(client, vault):
    body = client.get("/api/zaad/insights/suppliers?bucket=month").json()
    rows = {r["supplier_id"]: r for r in body["suppliers"]}
    partial = rows["DEMO-SUP-04"]
    assert partial["lateness"]["value"] is not None and partial["lateness"]["denominator"] == partial["orders_with_promise"]
    assert partial["lateness"]["denominator"] < partial["matched_orders"], "orders without a promise are outside the denominator"
    assert 0 < partial["lateness"]["coverage"] < 1
    short = rows["DEMO-SUP-03"]
    assert short["fill"]["value"] < 0.9 and short["fill"]["numerator"] == short["units_received"] and short["fill"]["denominator"] == short["units_ordered"]
    assert short["short_fills"] > rows["DEMO-SUP-01"]["short_fills"]
    for r in rows.values():
        assert r["products_with_declared_alternative"] >= 0 and r["share_of_units_ordered"] is not None
    assert rows["DEMO-SUP-02"]["amendment_rights_on_open_orders"] >= 1
    trend = [t for t in body["trend"] if t["supplier_id"] == "DEMO-SUP-02"]
    early = [t for t in trend if t["period"] < "2025-06"][:6]
    late = [t for t in trend if t["period"] >= "2026-03"][:6]
    assert sum(t["late_orders"] for t in late) > sum(t["late_orders"] for t in early)
    none_promised = client.get("/api/zaad/insights/suppliers?bucket=month&supplier=DEMO-SUP-04&start=2020-01-01&end=2020-02-01").json()
    assert none_promised["suppliers"] == []


def test_lateness_is_not_measured_when_no_order_carries_a_promise(vault):
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    conn.execute("INSERT INTO stg_fmcg_skus (sku, supplier_id, unit_cost) VALUES ('S1', 'SUP', 1.0)")
    conn.execute("INSERT INTO stg_fmcg_suppliers (supplier_id) VALUES ('SUP')")
    for i in range(3):
        conn.execute("INSERT INTO stg_fmcg_purchase_orders (po_id, po_date, supplier_id, sku, qty_ordered) VALUES (?, DATE '2026-01-01', 'SUP', 'S1', 100)", [f"P{i}"])
        conn.execute("INSERT INTO stg_fmcg_receipts (po_id, receipt_date, sku, qty_received) VALUES (?, DATE '2026-01-20', 'S1', 100)", [f"P{i}"])
    body = _client(conn).get("/api/zaad/insights/suppliers").json()
    late = body["suppliers"][0]["lateness"]
    assert late["value"] is None and late["reason"] == "NOT_MEASURED", "never 0 late when no promised date exists"


def test_service_level_is_shipped_over_ordered_on_measured_lines(client, vault):
    body = client.get("/api/zaad/insights/service?bucket=month").json()
    rows = {r["id"]: r for r in body["by_customer"]}
    grow = rows["DEMO-CUST-GROW"]
    ordered, shipped = vault.execute("SELECT sum(qty_ordered), sum(qty_shipped) FROM stg_fmcg_orders WHERE customer_id = 'DEMO-CUST-GROW'").fetchone()
    assert grow["service_level"]["value"] == pytest.approx(shipped / ordered) and grow["service_level"]["denominator"] == ordered
    # the released contract declares open orders against one aggregate customer, so no named customer carries a class
    assert grow["service_class"] is None and grow["service_class_reason"] == "NOT_APPLICABLE"
    assert [c["id"] for c in body["by_service_class"]] == ["not declared"]
    assert body["atp"]["present"] is False and body["atp"]["reason"] == "NOT_IN_PLAN"
    assert body["risk_scores"]["value"] is None and body["risk_scores"]["reason"] == "NOT_APPLICABLE"
    assert {c["class_id"] for c in body["declared_service_classes"]} == {"STRATEGIC", "CONTRACT", "STANDARD"}


# ── decisions, value, connectivity, plan ──────────────────────────────────────

def _fake_plan(store: JobStore, operator: str, *, stale: bool = False) -> str:
    req = example("normal", seed=5)
    identity = store.create(operator, req, 30.0)
    report = {
        "as_of": "2026-09-14T00:00:00", "information_hash": "abc", "status": "RECOMMEND", "schema_version": "x",
        "actions": [{"action": "purchase", "source": "SRC-1", "period": 0, "quantity": 120.0}, {"action": "transfer", "transfer": "DC->B", "period": 1, "quantity": 30.0}],
        "economics": {"incumbent_costs": {"PURCHASE": 1000.0, "TOTAL": 1200.0}, "selected_costs": {"PURCHASE": 950.0, "TOTAL": 1100.0}},
        "commitments": {"orders": [{"po": "DEMO-PO-00364", "recommended_action": "DEFER", "quantity_affected": 500.0},
                                   {"po": "DEMO-PO-00676", "recommended_action": "EXPEDITE", "quantity_affected": 200.0},
                                   {"po": "DEMO-PO-01300", "recommended_action": "KEEP", "quantity_affected": 0.0}]},
        "network_service": [{"service": "svc_A", "location": "DC", "requested": 0.95, "jointly_feasible": 0.95}],
    }
    store.update(identity, status="DONE", finished_at="2000-01-01T00:00:00+00:00" if stale else "2999-01-01T00:00:00+00:00", report_json=json.dumps(report))
    return identity


def test_decisions_and_value_read_the_latest_plan_verbatim(vault, tmp_path, monkeypatch):
    store = JobStore(tmp_path / "jobs.sqlite")
    monkeypatch.setenv("ZAAD_JOB_STORE", str(store.path))
    job = _fake_plan(store, OPERATOR)
    other = _fake_plan(store, "someone_else")
    c = _client(vault)
    plan = c.get("/api/zaad/insights/plan").json()
    assert plan["available"] and plan["job_id"] == job and plan["stale"] is False
    dec = c.get("/api/zaad/insights/decisions").json()
    assert dec["recommended"]["open_po_by_verb"] == {"KEEP": 1, "DEFER": 1, "EXPEDITE": 1, "REDUCE": 0, "CANCEL": 0, "SPLIT": 0}
    assert dec["recommended"]["other"] == {"BUY": 1, "MOVE": 1} and dec["recommended"]["total"] == 5
    val = c.get("/api/zaad/insights/value").json()
    reg = val["registers"]
    assert val["order"] == ["MODELED_DIFFERENCE", "BACKTESTED_OPPORTUNITY", "APPROVED_EXPECTED_DIFFERENCE", "OBSERVED_AFTER_ACTION", "REALIZED_VALUE"]
    assert reg["MODELED_DIFFERENCE"]["difference"] == 100.0 and reg["MODELED_DIFFERENCE"]["plan"]["job_id"] == job
    assert reg["BACKTESTED_OPPORTUNITY"]["available"] is False and reg["BACKTESTED_OPPORTUNITY"]["reason"] == "NOT_MEASURED"
    assert reg["APPROVED_EXPECTED_DIFFERENCE"]["available"] is False and reg["OBSERVED_AFTER_ACTION"]["available"] is False
    assert reg["REALIZED_VALUE"]["available"] is False and reg["REALIZED_VALUE"]["reason"] == "NO_DATA"
    assert "never" in val["never_combined"]
    conn_matrix = c.get("/api/zaad/insights/connectivity").json()
    by = {r["family"]: r["status"] for r in conn_matrix["families"]}
    assert by["P4B"] == "VISUALIZED" and by["P1"] == "VISUALIZED" and by["P5"] == "NOT_IN_PLAN" and by["P4"] == "NOT_DECLARED"
    assert by["P2"] == "VISUALIZED", "a plan with transfer actions or a network service block is a network plan"
    # tenant scope: the other operator's plan is theirs alone
    assert _client(vault, "someone_else").get("/api/zaad/insights/plan").json()["job_id"] == other
    assert _client(vault, "third").get("/api/zaad/insights/plan").json()["available"] is False


def test_a_plan_older_than_the_data_is_said_to_be_stale(vault, tmp_path, monkeypatch):
    store = JobStore(tmp_path / "jobs.sqlite")
    monkeypatch.setenv("ZAAD_JOB_STORE", str(store.path))
    _fake_plan(store, OPERATOR, stale=True)
    body = _client(vault).get("/api/zaad/insights/summary").json()
    assert body["plan"]["stale"] is True and "changed after" in body["plan"]["stale_reason"]
    assert body["demand"]["available"] and body["inventory"]["position"]["on_hand"] > 0 and body["supply"]["totals"]["open_units"] > 0


def test_without_a_plan_nothing_is_claimed(client):
    dec = client.get("/api/zaad/insights/decisions").json()
    assert dec["plan"]["available"] is False and dec["plan"]["reason"] == "NOT_IN_PLAN"
    assert dec["recommended"]["total"] == 0 and dec["decisions"] == []
    val = client.get("/api/zaad/insights/value").json()
    assert val["registers"]["MODELED_DIFFERENCE"]["available"] is False


def test_an_empty_workspace_says_no_data_not_zero():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    c = _client(conn)
    for path in ("demand", "inventory", "supply"):
        body = c.get(f"/api/zaad/insights/{path}").json()
        assert body["available"] is False and body["reason"] == "NO_DATA"
    assert c.get("/api/zaad/insights/summary").json()["demand"]["available"] is False


def test_unauthenticated_reads_are_refused(vault):
    assert _client(vault, None).get("/api/zaad/insights/demand").status_code == 401
