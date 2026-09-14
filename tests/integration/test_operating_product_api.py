"""The operating product's API: inventory, orders, suppliers, the data explorer and the proposal
lifecycle, against a real vault.

These tests exist to hold three properties that matter more than any single feature:

  * **Tenancy.** Another workspace's proposal is *absent*, not forbidden-with-detail.
  * **The allowlist.** No name from a request reaches SQL. A sort, a filter or a dataset the
    product does not declare is a 400 before anything runs.
  * **Nothing executes.** Every write path answers `executable: false`, and export produces a file
    rather than contacting anything.
"""
from __future__ import annotations

import io
import json

import duckdb
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dependencies import get_conn, require_operator
from api.routers import zaad_orders, zaad_workspace
from scripts.setup_db import setup_db

OPERATOR = "tenant_product"


@pytest.fixture(scope="module")
def vault():
    from scripts.zaad_network_workspace_smoke import make_network_vault
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    make_network_vault(conn, seed=7)
    # a promised delivery date on part of the history, so lateness is measurable on this fixture
    conn.execute("""UPDATE stg_fmcg_purchase_orders
                    SET expected_delivery_date = po_date + INTERVAL 14 DAY
                    WHERE abs(hash(po_id)) % 2 = 0""")
    return conn


def _client(conn, operator: str | None = OPERATOR) -> TestClient:
    app = FastAPI()
    app.include_router(zaad_workspace.router)
    app.include_router(zaad_orders.router)

    def conn_override():
        yield conn

    app.dependency_overrides[get_conn] = conn_override
    app.dependency_overrides[require_operator] = lambda: operator
    return TestClient(app)


@pytest.fixture(scope="module")
def client(vault):
    return _client(vault)


@pytest.fixture(scope="module")
def skus(vault):
    return [r[0] for r in vault.execute("SELECT sku FROM stg_fmcg_skus ORDER BY sku LIMIT 3").fetchall()]


# ── reading the business ──────────────────────────────────────────────────────

def test_inventory_is_paged_sorted_and_searchable(client):
    r = client.get("/api/zaad/workspace/inventory?limit=5&sort=inventory_value&direction=desc")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["served"] and body["total"] == 150 and len(body["rows"]) == 5
    values = [row["inventory_value"] for row in body["rows"] if row["inventory_value"] is not None]
    assert values == sorted(values, reverse=True), "the server sorted, not the browser"
    assert body["snapshot_date"], "the stock date is stated, never implied"
    first = body["rows"][0]
    assert {"sku", "on_hand", "inbound_units", "weekly_demand", "cover_weeks"} <= set(first)


def test_inventory_never_returns_more_than_the_cap(client):
    r = client.get("/api/zaad/workspace/inventory?limit=100000")
    assert r.status_code == 422, "a page size outside the contract is refused, not clamped silently"


def test_inventory_refuses_a_sort_it_does_not_declare(client):
    r = client.get("/api/zaad/workspace/inventory?sort=unit_cost%3B%20DROP%20TABLE%20stg_fmcg_skus")
    assert r.status_code == 400
    assert "sort" in r.json()["detail"].lower()


def test_cover_is_arithmetic_and_filterable(client):
    everything = client.get("/api/zaad/workspace/inventory?limit=1").json()["total"]
    thin = client.get("/api/zaad/workspace/inventory?cover=under2&limit=1").json()["total"]
    assert 0 <= thin <= everything


def test_sku_detail_carries_the_record_and_says_what_is_missing(client, skus):
    r = client.get(f"/api/zaad/workspace/inventory/{skus[0]}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["sku"] == skus[0]
    assert body["provenance"] == "OPERATOR_UPLOADED"
    assert isinstance(body["purchase_orders"], list) and isinstance(body["demand_by_week"], list)
    assert isinstance(body["missing"], list)


def test_an_unknown_product_is_not_found(client):
    assert client.get("/api/zaad/workspace/inventory/NOT-A-SKU").status_code == 404


def test_open_orders_follow_the_planner_rule(client, vault):
    """An order is open until its first receipt lands — the planning adapter's own rule.

    Counting "ordered minus received" instead would leave a permanent sliver open on every order a
    supplier ever under-shipped, and the number would never match the plan's inbound units.
    """
    open_orders = client.get("/api/zaad/workspace/purchase-orders?state=open&limit=1").json()["total"]
    without_receipt = vault.execute(
        "SELECT count(*) FROM (SELECT DISTINCT po_id FROM stg_fmcg_purchase_orders "
        "WHERE po_id NOT IN (SELECT DISTINCT po_id FROM stg_fmcg_receipts))").fetchone()[0]
    assert open_orders == without_receipt


def test_purchase_order_detail_shows_declared_rights_only(client, vault):
    po = vault.execute("SELECT po_id FROM stg_fmcg_purchase_orders LIMIT 1").fetchone()[0]
    body = client.get(f"/api/zaad/workspace/purchase-orders/{po}").json()
    assert body["po_id"] == po
    assert body["amendment_rights_declared"] is False, "no right is invented from history"
    assert body["declared_options"] == []


def test_supplier_diagnostics_separate_fact_from_association_from_unknown(client, vault):
    listing = client.get("/api/zaad/workspace/suppliers?limit=10").json()
    assert listing["served"] and listing["total"] >= 1
    supplier = listing["rows"][0]["supplier_id"]
    body = client.get(f"/api/zaad/workspace/suppliers/{supplier}").json()
    lateness = body["lateness"]
    assert lateness["drivers"] == [], "no stage of the journey is claimed without an event timestamp"
    assert lateness["unknown"]["missing_fields"], "the fields that would settle it are named"
    for statement in lateness["observed"]:
        assert statement["sample"] is not None, "every observed fact carries its sample size"
    assert body["alternatives"]["declared"] is False
    assert body["exposure"]["skus"] is not None


def test_a_supplier_from_another_workspace_is_not_found(client):
    assert client.get("/api/zaad/workspace/suppliers/SUP-NOT-HERE").status_code == 404


def test_sector_diagnostics_say_so_when_nothing_is_declared(client):
    body = client.get("/api/zaad/workspace/sector").json()
    assert body["served"] is False
    assert "declare" in body["note"].lower()


# ── the data explorer ─────────────────────────────────────────────────────────

def test_the_explorer_lists_only_datasets_it_declares(client):
    body = client.get("/api/zaad/workspace/datasets").json()
    keys = {d["key"] for d in body["datasets"]}
    assert {"products", "purchase_orders", "receipts", "customer_orders", "suppliers"} <= keys
    counts = {d["key"]: d["rows"] for d in body["datasets"]}
    assert counts["products"] == 150 and counts["customer_orders"] > 100_000


def test_the_explorer_serves_real_records(client):
    body = client.get("/api/zaad/workspace/datasets/customer_orders?limit=3").json()
    assert body["served"] and len(body["rows"]) == 3
    assert any(c["name"] == "qty_ordered" for c in body["columns"])


@pytest.mark.parametrize("url", [
    "/api/zaad/workspace/datasets/secrets",
    "/api/zaad/workspace/datasets/products?sort=1%3B%20DROP%20TABLE%20stg_fmcg_skus",
    "/api/zaad/workspace/datasets/products?where=unit_cost:1",
    "/api/zaad/workspace/datasets/products/values/unit_cost",
])
def test_the_explorer_refuses_any_name_it_did_not_declare(client, url):
    assert client.get(url).status_code == 400


def test_the_explorer_binds_values_rather_than_interpolating_them(client, vault):
    hostile = "'; DROP TABLE stg_fmcg_skus; --"
    r = client.get("/api/zaad/workspace/datasets/products", params={"q": hostile})
    assert r.status_code == 200 and r.json()["rows"] == []
    assert vault.execute("SELECT count(*) FROM stg_fmcg_skus").fetchone()[0] == 150


def test_search_is_server_side_and_lands_in_context(client, skus):
    body = client.get(f"/api/zaad/workspace/search?q={skus[0]}").json()
    assert body["results"], "a product a person types is found"
    assert all(result["href"].startswith("/") for result in body["results"])


def test_summary_counts_only_what_exists(client):
    body = client.get("/api/zaad/workspace/summary").json()
    assert body["products"] == 150
    assert body["provenance"] == "OPERATOR_UPLOADED"
    assert body["inventory_value"] is not None


# ── proposed orders ───────────────────────────────────────────────────────────

def _create(client, skus, **over):
    body = {"origin": "MANUAL", "supplier_id": "SUP-001", "destination_id": "DC", "currency": "USD",
            "reference": "PO-LIFECYCLE", "requested_order_date": "2026-01-05",
            "requested_receipt_date": "2026-02-02",
            "lines": [{"sku": skus[0], "quantity": 1200, "unit_price": 4.5}]}
    body.update(over)
    r = client.post("/api/zaad/orders", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_a_proposal_is_created_read_edited_and_deleted(client, skus):
    draft = _create(client, skus)
    identity = draft["draft_id"]
    assert draft["state"] == "DRAFT" and draft["executable"] is False and draft["transmitted"] is False

    edited = client.patch(f"/api/zaad/orders/{identity}", json={"notes": "buyer note",
                                                               "lines": [{"sku": skus[0], "quantity": 2400}]})
    assert edited.status_code == 200 and edited.json()["lines"][0]["quantity"] == 2400

    assert client.delete(f"/api/zaad/orders/{identity}").status_code == 204
    assert client.get(f"/api/zaad/orders/{identity}").status_code == 404


def test_a_refused_edit_changes_nothing(client, skus):
    """A validation failure part-way through an edit must not leave the proposal without lines."""
    draft = _create(client, skus)
    identity = draft["draft_id"]
    bad = client.patch(f"/api/zaad/orders/{identity}",
                       json={"lines": [{"sku": skus[0], "quantity": 10}, {"sku": skus[1], "quantity": -5}]})
    assert bad.status_code == 422
    after = client.get(f"/api/zaad/orders/{identity}").json()
    assert len(after["lines"]) == 1 and after["lines"][0]["quantity"] == 1200


def test_validation_warns_and_does_not_forbid(client, skus, vault):
    pack = vault.execute("SELECT any_value(units_per_case) FROM stg_fmcg_skus WHERE sku = ?", [skus[0]]).fetchone()[0]
    draft = _create(client, skus, lines=[{"sku": skus[0], "quantity": float(pack) + 1}])
    messages = " ".join(w["message"] for w in draft["warnings"])
    assert "whole number of cases" in messages
    assert draft["state"] == "DRAFT", "a warning never blocks the document"


def test_the_lifecycle_is_enforced(client, skus):
    draft = _create(client, skus)
    identity = draft["draft_id"]
    assert client.post(f"/api/zaad/orders/{identity}/actions/submit", json={}).status_code == 200
    assert client.patch(f"/api/zaad/orders/{identity}", json={"notes": "x"}).status_code == 422
    assert client.post(f"/api/zaad/orders/{identity}/actions/approve", json={}).status_code == 422, \
        "an approval needs a reason"
    approved = client.post(f"/api/zaad/orders/{identity}/actions/approve", json={"reason": "cover is thin"})
    assert approved.status_code == 200 and approved.json()["state"] == "APPROVED"
    assert client.delete(f"/api/zaad/orders/{identity}").status_code == 422
    assert client.patch(f"/api/zaad/orders/{identity}", json={"notes": "x"}).status_code == 422

    revised = client.post(f"/api/zaad/orders/{identity}/revise")
    assert revised.status_code == 201 and revised.json()["revision"] == 2
    assert revised.json()["supersedes"] == identity
    assert client.get(f"/api/zaad/orders/{identity}").json()["state"] == "SUPERSEDED"


def test_an_amendment_points_at_the_imported_order_and_never_edits_it(client, skus, vault):
    po = vault.execute("SELECT po_id FROM stg_fmcg_purchase_orders LIMIT 1").fetchone()[0]
    before = vault.execute("SELECT * FROM stg_fmcg_purchase_orders WHERE po_id = ?", [po]).fetchall()
    draft = _create(client, skus, origin="IMPORTED_AMENDMENT", source_po_id=po, amendment_action="DEFER")
    assert draft["source_po_id"] == po and draft["amendment_action"] == "DEFER"
    after = vault.execute("SELECT * FROM stg_fmcg_purchase_orders WHERE po_id = ?", [po]).fetchall()
    assert before == after, "imported evidence is never rewritten by a proposal against it"


def test_an_amendment_is_not_priced_without_a_declared_right(client, skus, vault):
    po = vault.execute("SELECT po_id FROM stg_fmcg_purchase_orders LIMIT 1").fetchone()[0]
    draft = _create(client, skus, origin="IMPORTED_AMENDMENT", source_po_id=po, amendment_action="CANCEL")
    r = client.post(f"/api/zaad/orders/{draft['draft_id']}/evaluate")
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "amendment_not_evaluated"


def test_an_amendment_needs_an_action_and_an_order(client, skus):
    assert client.post("/api/zaad/orders", json={"origin": "IMPORTED_AMENDMENT",
                                                 "lines": [{"sku": skus[0], "quantity": 1}]}).status_code == 422


# ── export ────────────────────────────────────────────────────────────────────

def test_export_produces_a_file_and_records_that_it_did(client, skus):
    draft = _create(client, skus)
    identity = draft["draft_id"]
    client.post(f"/api/zaad/orders/{identity}/actions/approve", json={"reason": "agreed"})
    for fmt, media in (("csv", "text/csv"), ("xlsx", "spreadsheetml"), ("print", "application/pdf")):
        r = client.post(f"/api/zaad/orders/{identity}/export?format={fmt}")
        assert r.status_code == 200, r.text
        assert media in r.headers["content-type"]
        assert r.headers["x-zaad-transmitted"] == "false"
        assert "attachment" in r.headers["content-disposition"]
    after = client.get(f"/api/zaad/orders/{identity}").json()
    assert after["state"] == "EXPORTED"
    assert len(after["exports"]) == 3, "every file that left is in the record"


def test_a_profile_can_only_name_fields_zaad_holds(client):
    bad = client.post("/api/zaad/orders/profiles", json={
        "name": "Bad", "format": "csv", "columns": [{"header": "X", "field": "secret_margin"}]})
    assert bad.status_code == 422 and "does not hold" in bad.json()["detail"]["message"]


def test_a_company_format_maps_columns_and_constants(client, skus):
    made = client.post("/api/zaad/orders/profiles", json={
        "name": "Oracle PO Import", "format": "csv", "date_format": "dmy",
        "columns": [{"header": "PO_NUM", "field": "po_number"}, {"header": "ITEM", "field": "sku"},
                    {"header": "QTY", "field": "quantity"}, {"header": "NEED_BY", "field": "need_by_date"},
                    {"header": "ORG", "constant": "JOR01"}]})
    assert made.status_code == 201
    profile_id = made.json()["profile_id"]
    draft = _create(client, skus)
    r = client.post(f"/api/zaad/orders/{draft['draft_id']}/export?profile_id={profile_id}")
    assert r.status_code == 200
    text = r.content.decode("utf-8-sig")
    assert text.splitlines()[0] == "PO_NUM,ITEM,QTY,NEED_BY,ORG"
    assert "02/02/2026" in text and "JOR01" in text


def test_a_formula_never_leaves_in_an_export(client, skus):
    draft = _create(client, skus, reference="=cmd|'/c calc'!A1")
    r = client.post(f"/api/zaad/orders/{draft['draft_id']}/export")
    body = r.content.decode("utf-8-sig")
    assert "\n'=cmd" in body or body.splitlines()[1].startswith("'="), body.splitlines()[:2]


# ── uploading a proposed order ────────────────────────────────────────────────

def test_an_uploaded_order_is_mapped_then_confirmed(client, skus):
    content = (f"Item Code,Order Qty,Unit Price,Required Date\n"
               f"{skus[0]},600,4.10,2026-02-10\n{skus[1]},not-a-number,,\n").encode()
    first = client.post("/api/zaad/orders/read-proposal",
                        files={"file": ("proposal.csv", io.BytesIO(content), "text/csv")})
    assert first.status_code == 200
    suggested = first.json()["suggested_mapping"]
    assert suggested["sku"] == "Item Code" and suggested["quantity"] == "Order Qty"

    second = client.post("/api/zaad/orders/read-proposal",
                         files={"file": ("proposal.csv", io.BytesIO(content), "text/csv")},
                         data={"mapping": json.dumps(suggested)})
    body = second.json()
    assert len(body["lines"]) == 1, "a row ZAAD cannot read is reported, not guessed"
    assert any("not-a-number" in problem for problem in body["problems"])
    assert "Row 3" in body["problems"][0], "the problem names the row in the file"


def test_an_export_template_is_read_for_its_headings_only(client):
    template = b"PO Number,Vendor,Item,Quantity,Need By Date,Plant\n=DANGEROUS(),1,2,3,4,5\n"
    r = client.post("/api/zaad/orders/profiles/read-template",
                    files={"file": ("template.csv", io.BytesIO(template), "text/csv")})
    assert r.status_code == 200
    body = r.json()
    assert body["headers"] == ["PO Number", "Vendor", "Item", "Quantity", "Need By Date", "Plant"]
    suggested = {c["header"]: c["field"] for c in body["suggested_columns"]}
    assert suggested["Vendor"] == "supplier_id" and suggested["Plant"] is None


# ── tenancy ───────────────────────────────────────────────────────────────────

def test_another_workspace_sees_nothing_of_this_one(vault, skus):
    mine = _client(vault, OPERATOR)
    draft = _create(mine, skus)
    theirs = _client(vault, "someone_else")
    assert theirs.get(f"/api/zaad/orders/{draft['draft_id']}").status_code == 404, \
        "absent, not forbidden-with-detail"
    assert theirs.get("/api/zaad/orders").json()["rows"] == []
    assert theirs.patch(f"/api/zaad/orders/{draft['draft_id']}", json={"notes": "x"}).status_code == 404
    assert theirs.delete(f"/api/zaad/orders/{draft['draft_id']}").status_code == 404
    assert mine.get(f"/api/zaad/orders/{draft['draft_id']}").status_code == 200, "and mine is untouched"


def test_every_surface_needs_a_workspace(vault):
    anonymous = _client(vault, None)
    for url in ("/api/zaad/workspace/inventory", "/api/zaad/workspace/summary",
                "/api/zaad/workspace/datasets", "/api/zaad/orders"):
        assert anonymous.get(url).status_code == 401, url


def test_evaluation_runs_are_distinguishable_from_the_workspace_plan(client, vault, skus):
    """An evaluation uses the released jobs path twice, and one of its runs carries a proposed
    order overlaid on the pipeline. Nothing in the job record says so, so a surface showing "the
    last completed plan" would present a plan of the workspace *plus an order nobody has placed*
    as the operator's own position. This is the list that prevents it."""
    empty = client.get("/api/zaad/orders/evaluation-jobs")
    assert empty.status_code == 200
    assert empty.json()["evaluation_job_ids"] == []

    draft = _create(client, skus)
    from api.product import evaluation
    evaluation.store_evaluation(
        vault, OPERATOR, draft_id=draft["draft_id"], revision=1,
        baseline_job_id="job_base", proposal_job_id="job_proposal",
        as_of="2026-01-05T00:00:00Z", scope=[skus[0]], status="QUEUED")

    listed = client.get("/api/zaad/orders/evaluation-jobs").json()["evaluation_job_ids"]
    assert listed == ["job_base", "job_proposal"]
    assert _client(vault, "someone_else").get("/api/zaad/orders/evaluation-jobs").json()["evaluation_job_ids"] == [], \
        "and another workspace's evaluation runs are not listed here"
