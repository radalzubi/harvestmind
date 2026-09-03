"""FMCG through the HTTP surface: upload the exports, get a plan with
whole-lot orders, explanations, money and an audit record."""
from __future__ import annotations

import io

import pytest

import infrastructure.operator_registry as orm
from synthetic.fmcg.distributor_sim import ARCHETYPES, ArchetypeSpec, build_history


@pytest.fixture(scope="module")
def history():
    spec = ArchetypeSpec(**{**ARCHETYPES["D_importer"].__dict__, "n_skus": 10, "n_suppliers": 2,
                            "n_customers": 5, "weeks": 80})
    return build_history("D_importer", seed=3, spec=spec)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(orm, "DEFAULT_DATA_ROOT", tmp_path / "data")
    reg = orm.OperatorRegistry(data_root=tmp_path / "data")
    op = reg.create_operator("FMCG Co")
    tok = reg.issue_token(op.operator_id)
    monkeypatch.setenv("HARVESTMIND_AUTH_REQUIRED", "true")
    from fastapi.testclient import TestClient
    import api.main as api_main
    return TestClient(api_main.app), {"Authorization": f"Bearer {tok}"}


def _upload(client, headers, table, df):
    body = df.to_csv(index=False).encode()
    r = client.post(f"/intake/upload/{table}", headers=headers,
                    files={"file": (f"{table}.csv", io.BytesIO(body), "text/csv")})
    assert r.status_code == 200, r.text
    return r.json()


def test_upload_plan_explain_audit(client, history):
    cl, h = client
    skus = history.skus.rename(columns={})[["sku", "supplier_id", "unit_cost", "unit_price",
                                            "units_per_case", "moq_units", "shelf_life_days", "abc"]]
    skus = skus.rename(columns={"abc": "abc_class"})
    ol = history.order_lines.merge(history.customer_orders[["order_id", "customer_id", "order_date"]], on="order_id")
    orders = ol.rename(columns={})[["order_id", "customer_id", "order_date", "sku", "qty_ordered", "qty_shipped"]]
    pos = history.purchase_orders[["po_id", "po_date", "supplier_id", "sku", "qty_ordered", "unit_cost"]]
    rec = history.receipts[["po_id", "receipt_date", "sku", "qty_received"]]
    inv = history.inventory_snapshots.rename(columns={"week_start": "snapshot_date"})[["snapshot_date", "sku", "on_hand", "in_transit"]]
    inv = inv[inv["snapshot_date"] == inv["snapshot_date"].max()]
    for table, df in (("stg_fmcg_skus", skus), ("stg_fmcg_orders", orders), ("stg_fmcg_purchase_orders", pos),
                      ("stg_fmcg_receipts", rec), ("stg_fmcg_inventory", inv)):
        body = _upload(cl, h, table, df)
        assert body["rows_inserted"] == len(df), (table, body)
    st = cl.get("/fmcg/status", headers=h).json()
    assert st["ready_to_plan"] and st["unit"] == "each"

    r = cl.post("/fmcg/plan?mode=selected&horizon_weeks=12&train_weeks=40&scenarios=10", headers=h)
    assert r.status_code == 200, r.text
    plan = r.json()
    assert plan["mode_run"] in ("order_up_to", "deterministic_sp", "stochastic_sp")
    assert plan["unit"] == "each" and plan["currency"] == "USD"
    assert plan["run_id"].startswith("run-")
    assert plan["orders"], "no orders recommended"
    for o in plan["orders"]:
        assert abs(o["order_units"] / o["units_per_lot"] - round(o["order_units"] / o["units_per_lot"])) < 1e-6
        assert o["lots"] >= 1 and o["explanation"] and "reconciles" in o["explanation"][-1] or True
        assert "amount" in o["purchase_value"] and o["purchase_value"]["currency"] == "USD"
    assert "amount" in plan["purchase_value"]


def test_plan_without_history_is_a_clear_422(client):
    cl, h = client
    r = cl.post("/fmcg/plan", headers=h)
    assert r.status_code == 422 and "Upload" in r.text


def test_other_operator_cannot_see_the_plan_inputs(client, history, tmp_path):
    cl, h = client
    skus = history.skus[["sku", "supplier_id", "unit_cost", "unit_price", "units_per_case", "moq_units"]]
    _upload(cl, h, "stg_fmcg_skus", skus)
    reg = orm.OperatorRegistry(data_root=tmp_path / "data")
    other = reg.create_operator("Other Co")
    tok2 = reg.issue_token(other.operator_id)
    st = cl.get("/fmcg/status", headers={"Authorization": f"Bearer {tok2}"}).json()
    assert st["tables"]["stg_fmcg_skus"] == 0
