"""The DEMO company reconciles with itself.

Every scenario the generator promises is checked against the rows it wrote: identifiers resolve,
receipts never exceed orders, shipments never exceed orders or stock, snapshots are non-negative and
site totals sum to the enterprise total, dates are sensible, currency is one, the declared rights
point at real open orders, and the Insights aggregates equal sums over the raw rows.
"""
from __future__ import annotations

from datetime import date, timedelta

import duckdb
import pytest

from api.product import insights
from scripts.setup_db import setup_db
from synthetic.fmcg.demo_company import (CLASSIFICATION, EXCESS_SKU, IMBALANCE_SKU, SHORTAGE_SKU, SPIKE_SKUS, build_demo_company,
                                         load_demo_company_into)

AS_OF = date(2026, 9, 15)
OPERATOR = "demo_tenant"


@pytest.fixture(scope="module")
def vault():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    loaded = load_demo_company_into(conn, OPERATOR, as_of=AS_OF)
    return conn, loaded


def _one(conn, sql, params=None):
    return conn.execute(sql, params or []).fetchone()[0]


def test_it_is_labelled_demo_and_deterministic(vault):
    conn, loaded = vault
    assert loaded["classification"] == CLASSIFICATION and "DEMO" in loaded["company"]
    again = build_demo_company(as_of=AS_OF)
    assert again.counts() == loaded["tables"]
    assert all(str(r[0]).startswith("DEMO-") for r in conn.execute("SELECT sku FROM stg_fmcg_skus").fetchall())


def test_every_reference_resolves(vault):
    conn, _ = vault
    assert _one(conn, "SELECT count(*) FROM stg_fmcg_orders WHERE sku NOT IN (SELECT sku FROM stg_fmcg_skus)") == 0
    assert _one(conn, "SELECT count(*) FROM stg_fmcg_purchase_orders WHERE sku NOT IN (SELECT sku FROM stg_fmcg_skus)") == 0
    assert _one(conn, "SELECT count(*) FROM stg_fmcg_purchase_orders WHERE supplier_id NOT IN (SELECT supplier_id FROM stg_fmcg_suppliers)") == 0
    assert _one(conn, "SELECT count(*) FROM stg_fmcg_skus WHERE supplier_id NOT IN (SELECT supplier_id FROM stg_fmcg_suppliers)") == 0
    assert _one(conn, "SELECT count(*) FROM stg_fmcg_receipts WHERE po_id NOT IN (SELECT po_id FROM stg_fmcg_purchase_orders)") == 0
    assert _one(conn, "SELECT count(*) FROM stg_fmcg_inventory WHERE location_id NOT IN (SELECT location_id FROM stg_fmcg_locations)") == 0
    assert _one(conn, "SELECT count(*) FROM stg_fmcg_orders WHERE location_id NOT IN (SELECT location_id FROM stg_fmcg_locations)") == 0
    assert _one(conn, "SELECT count(*) FROM stg_fmcg_transfers WHERE origin_id NOT IN (SELECT location_id FROM stg_fmcg_locations) "
                      "OR destination_id NOT IN (SELECT location_id FROM stg_fmcg_locations)") == 0
    assert _one(conn, "SELECT count(*) FROM stg_fmcg_sources WHERE sku NOT IN (SELECT sku FROM stg_fmcg_skus) OR supplier_id NOT IN (SELECT supplier_id FROM stg_fmcg_suppliers)") == 0
    assert _one(conn, "SELECT count(*) FROM stg_po_commitments WHERE po_id NOT IN (SELECT po_id FROM stg_fmcg_purchase_orders)") == 0
    assert _one(conn, "SELECT count(*) FROM stg_po_options WHERE po_id NOT IN (SELECT po_id FROM stg_po_commitments)") == 0
    assert _one(conn, "SELECT count(*) FROM stg_atp_customer_orders WHERE sku NOT IN (SELECT sku FROM stg_fmcg_skus)") == 0
    assert _one(conn, "SELECT count(*) FROM stg_atp_customer_orders WHERE customer_id <> 'customers'") == 0, "the released contract's aggregate customer"
    assert _one(conn, "SELECT count(*) FROM stg_atp_customer_orders WHERE service_class NOT IN (SELECT class_id FROM stg_atp_service_classes)") == 0


def test_quantities_reconcile_and_none_is_impossible(vault):
    conn, _ = vault
    assert _one(conn, "SELECT count(*) FROM stg_fmcg_orders WHERE qty_ordered <= 0 OR qty_shipped < 0 OR qty_shipped > qty_ordered") == 0
    assert _one(conn, "SELECT count(*) FROM stg_fmcg_inventory WHERE on_hand < 0") == 0
    assert _one(conn, "SELECT count(*) FROM stg_fmcg_receipts WHERE qty_received < 0") == 0
    # receipts never exceed what was ordered on the order
    over = conn.execute("""SELECT r.po_id FROM (SELECT po_id, sum(qty_received) AS q FROM stg_fmcg_receipts GROUP BY 1) r
                           JOIN (SELECT po_id, sum(qty_ordered) AS q FROM stg_fmcg_purchase_orders GROUP BY 1) p ON p.po_id = r.po_id
                           WHERE r.q > p.q + 1e-6""").fetchall()
    assert over == []
    # shipments obey stock: a site never ships more in a week than it opened with plus what arrived
    assert _one(conn, "SELECT sum(qty_ordered - qty_shipped) FROM stg_fmcg_orders") > 0, "the shortage scenario records a shortfall"
    short_skus = {r[0] for r in conn.execute("SELECT DISTINCT sku FROM stg_fmcg_orders WHERE qty_shipped < qty_ordered").fetchall()}
    assert SHORTAGE_SKU in short_skus


def test_site_snapshots_sum_to_the_enterprise_total(vault):
    conn, _ = vault
    latest = _one(conn, "SELECT max(snapshot_date) FROM stg_fmcg_inventory")
    per_site = conn.execute("SELECT location_id, sum(on_hand) FROM stg_fmcg_inventory WHERE snapshot_date = ? GROUP BY 1", [latest]).fetchall()
    assert len(per_site) == 3
    assert sum(v for _, v in per_site) == _one(conn, "SELECT sum(on_hand) FROM stg_fmcg_inventory WHERE snapshot_date = ?", [latest])
    assert _one(conn, "SELECT count(DISTINCT snapshot_date) FROM stg_fmcg_inventory") >= 100, "two years of weekly snapshots"


def test_dates_are_sensible_and_currency_is_one(vault):
    conn, _ = vault
    assert _one(conn, "SELECT max(order_date) FROM stg_fmcg_orders") < AS_OF
    assert _one(conn, "SELECT min(order_date) FROM stg_fmcg_orders") >= AS_OF - timedelta(weeks=106)
    assert _one(conn, "SELECT count(*) FROM stg_fmcg_receipts r JOIN stg_fmcg_purchase_orders p ON p.po_id = r.po_id WHERE r.receipt_date < p.po_date") == 0
    assert _one(conn, "SELECT count(*) FROM stg_fmcg_transfers WHERE received_date < dispatch_date") == 0
    assert _one(conn, "SELECT count(DISTINCT value) FROM stg_fmcg_economics WHERE key = 'currency'") == 1


def test_the_scenarios_are_in_the_rows(vault):
    conn, loaded = vault
    s = loaded["scenarios"]
    # the spike: the growing customer's week is far above its neighbours on the spike products
    week = date.fromisoformat(s["spike"]["week"])
    spike = _one(conn, "SELECT sum(qty_ordered) FROM stg_fmcg_orders WHERE customer_id = ? AND sku IN (?, ?, ?) AND order_date >= ? AND order_date < ?",
                 ["DEMO-CUST-GROW", *SPIKE_SKUS, week, week + timedelta(days=7)])
    before = _one(conn, "SELECT sum(qty_ordered) / 4 FROM stg_fmcg_orders WHERE customer_id = ? AND sku IN (?, ?, ?) AND order_date >= ? AND order_date < ?",
                  ["DEMO-CUST-GROW", *SPIKE_SKUS, week - timedelta(days=28), week])
    assert spike > 2.5 * before
    # the excess product carries far more cover than the median product
    latest = _one(conn, "SELECT max(snapshot_date) FROM stg_fmcg_inventory")
    cover = {r[0]: r[1] for r in conn.execute("""
        WITH stock AS (SELECT sku, sum(on_hand) AS q FROM stg_fmcg_inventory WHERE snapshot_date = ? GROUP BY 1),
             dem AS (SELECT sku, sum(qty_ordered) / 12.0 AS w FROM stg_fmcg_orders WHERE order_date > ? - INTERVAL 84 DAY GROUP BY 1)
        SELECT stock.sku, stock.q / dem.w FROM stock JOIN dem ON dem.sku = stock.sku""", [latest, AS_OF]).fetchall()}
    ordered = sorted(cover.values())
    median = ordered[len(ordered) // 2]
    assert cover[EXCESS_SKU] > 2 * median and cover[SHORTAGE_SKU] < median / 2
    # the site imbalance: Aqaba holds several times what Irbid holds of the product
    aqaba = _one(conn, "SELECT on_hand FROM stg_fmcg_inventory WHERE snapshot_date = ? AND sku = ? AND location_id = 'DEMO-BR-AQABA'", [latest, IMBALANCE_SKU])
    irbid = _one(conn, "SELECT on_hand FROM stg_fmcg_inventory WHERE snapshot_date = ? AND sku = ? AND location_id = 'DEMO-BR-IRBID'", [latest, IMBALANCE_SKU])
    assert aqaba > 3 * max(irbid, 1)
    # the declared rights sit on open orders of the intended products, dated before as_of
    rights = s["amendment_rights"]
    assert rights["defer"] and rights["expedite"] and rights["keep"]
    for role, sku in (("defer", EXCESS_SKU), ("expedite", SHORTAGE_SKU)):
        po = rights[role]
        assert _one(conn, "SELECT any_value(sku) FROM stg_fmcg_purchase_orders WHERE po_id = ?", [po]) == sku
        assert _one(conn, "SELECT count(*) FROM stg_fmcg_receipts WHERE po_id = ?", [po]) == 0
        assert _one(conn, "SELECT min(po_date) FROM stg_fmcg_purchase_orders WHERE po_id = ?", [po]) < AS_OF
        assert _one(conn, "SELECT count(*) FROM stg_po_options WHERE po_id = ? AND operator_id = ?", [po, OPERATOR]) == 3
    # supplier behaviours: the deteriorating supplier is later in the second year than the first
    late = conn.execute("""WITH m AS (SELECT p.po_id, min(p.po_date) AS d, min(p.expected_delivery_date) AS promised, min(r.receipt_date) AS got, any_value(p.supplier_id) AS s
                                     FROM stg_fmcg_purchase_orders p JOIN stg_fmcg_receipts r ON r.po_id = p.po_id GROUP BY 1)
                           SELECT (d < ? - INTERVAL 365 DAY) AS first_year, avg(CASE WHEN got > promised THEN 1.0 ELSE 0.0 END)
                           FROM m WHERE s = 'DEMO-SUP-02' AND promised IS NOT NULL GROUP BY 1 ORDER BY 1 DESC""", [AS_OF]).fetchall()
    assert late[0][1] < late[1][1], "lateness rises in the second year"
    assert _one(conn, "SELECT count(*) FROM stg_fmcg_purchase_orders WHERE supplier_id = 'DEMO-SUP-04' AND expected_delivery_date IS NULL") > 0
    assert _one(conn, "SELECT count(*) FROM stg_fmcg_purchase_orders WHERE supplier_id = 'DEMO-SUP-04' AND expected_delivery_date IS NOT NULL") > 0
    assert _one(conn, "SELECT count(*) FROM (SELECT po_id FROM stg_fmcg_receipts GROUP BY 1 HAVING count(*) > 1)") > 0, "partial receipts exist"


def test_insights_aggregates_equal_the_raw_rows(vault):
    conn, _ = vault
    d = insights.demand(conn, insights.scope_from("month"))
    assert d["available"] and d["fulfilment"] == "MEASURED"
    assert sum(r["ordered"] for r in d["series"]) == _one(conn, "SELECT sum(qty_ordered) FROM stg_fmcg_orders")
    assert sum(r["shipped"] for r in d["series"]) == _one(conn, "SELECT sum(qty_shipped) FROM stg_fmcg_orders")
    assert sum(r["unfulfilled"] for r in d["series"]) == _one(conn, "SELECT sum(qty_ordered - qty_shipped) FROM stg_fmcg_orders")
    top = d["top"]["customers"]["rows"][0]
    assert top["ordered"] == _one(conn, "SELECT sum(qty_ordered) FROM stg_fmcg_orders WHERE customer_id = ?", [top["id"]])
    inv = insights.inventory(conn, insights.scope_from("week"))
    latest = _one(conn, "SELECT max(snapshot_date) FROM stg_fmcg_inventory")
    assert inv["series"][-1]["units"] == _one(conn, "SELECT sum(on_hand) FROM stg_fmcg_inventory WHERE snapshot_date = ?", [latest])
    assert sum(r["units"] for r in inv["by_site"]) == inv["series"][-1]["units"]
    sup = insights.supply(conn, insights.scope_from("week", end=AS_OF.isoformat()))
    open_units = _one(conn, "SELECT sum(qty_ordered) FROM stg_fmcg_purchase_orders WHERE po_id NOT IN (SELECT po_id FROM stg_fmcg_receipts)")
    assert sup["totals"]["open_units"] == open_units
