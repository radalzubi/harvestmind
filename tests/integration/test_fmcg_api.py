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

    ready = cl.get("/fmcg/readiness", headers=h).json()
    assert ready["verdict"] in ("READY", "READY_WITH_CAVEATS") and "weakened_conclusions" in ready

    stt = cl.get("/fmcg/state?train_weeks=40", headers=h)
    assert stt.status_code == 200, stt.text
    body = stt.json()
    assert abs(sum(body["portfolio"]["probabilities"].values()) - 1.0) < 1e-6
    assert set(body["sku"]) and set(body["supplier"]) and "posture" in body and body["replan_triggers"]
    assert body["signal_sources"]["provenance"] in ("REAL_PUBLIC", None)
    # a route with no port signal is reported UNAVAILABLE, never assumed normal
    assert all(("available" in v) for v in body["signals"].values())

    r = cl.post("/fmcg/plan?mode=safe&horizon_weeks=12&commit_window_weeks=4&train_weeks=40&scenarios=10", headers=h)
    assert r.status_code == 200, r.text
    plan = r.json()
    assert plan["mode_run"] in ("incumbent", "order_up_to", "deterministic_sp", "stochastic_sp", "anchored_sp", "adaptive_sp")
    assert plan["baseline_policy"].startswith("client policy") and plan["reason"]
    # the posture decides which candidates are even evaluated
    assert set(plan["candidate_evidence"]) <= set(plan["candidates_admitted"])
    assert set(plan["candidate_evidence"]) >= {"order_up_to", "deterministic_sp"}
    assert abs(sum(plan["state"]["portfolio"]["probabilities"].values()) - 1.0) < 1e-6
    assert 0.0 <= plan["autonomy"]["score"] <= 1.0 and plan["narrative"].startswith("Current regime")
    assert plan["posture"]["commit_window"] >= 1
    assert plan["unit"] == "each" and plan["currency"] == "USD" and plan["run_id"].startswith("run-")
    assert plan["economics_provenance"]["unit_cost"] == "operator"
    assert plan["economics_provenance"]["supplier_fill"] == "measured"
    assert plan["supply_model"]["method"] == "moving_block_bootstrap"
    assert plan["regime"]["dominant"] and plan["carrying_cost_sensitivity"]
    assert 1 <= plan["executable_until_week"] <= 4 == plan["commit_window_requested"]
    assert plan["advisory_horizon_weeks"] == 12
    assert plan["orders"], "no orders recommended"
    statuses = {o["status"] for o in plan["orders"]}
    assert statuses <= {"EXECUTABLE", "ADVISORY"}
    cw = plan["executable_until_week"]
    assert all(o["status"] == ("EXECUTABLE" if o["week_offset"] < cw else "ADVISORY") for o in plan["orders"])
    for o in plan["orders"]:
        assert abs(o["order_units"] / o["units_per_lot"] - round(o["order_units"] / o["units_per_lot"])) < 1e-6
        assert "incumbent_units" in o and "deviation_from_incumbent" in o and o["regime"]
        assert "amount" in o["purchase_value"] and o["purchase_value"]["currency"] == "USD"
    assert "amount" in plan["purchase_value_executable"]
    if plan["vss_evpi"]:
        assert plan["vss_evpi"]["vss"] >= 0 and plan["vss_evpi"]["evpi"] >= 0
    # a plan that keeps the incumbent is a successful outcome and says why
    if plan["mode_run"] == "incumbent":
        assert "threshold" in plan["reason"] or "held-out" in plan["reason"] or "insufficient" in plan["reason"]


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


def test_missing_margin_is_unknown_and_anchors_rather_than_inventing(client, history):
    cl, h = client
    skus = history.skus[["sku", "supplier_id", "unit_cost", "units_per_case", "moq_units"]]   # no price, no margin
    _upload(cl, h, "stg_fmcg_skus", skus)
    ol = history.order_lines.merge(history.customer_orders[["order_id", "customer_id", "order_date"]], on="order_id")
    _upload(cl, h, "stg_fmcg_orders", ol[["order_id", "customer_id", "order_date", "sku", "qty_ordered"]])
    r = cl.post("/fmcg/plan?mode=safe&train_weeks=40&scenarios=10", headers=h)
    assert r.status_code == 200, r.text
    plan = r.json()
    assert plan["economics_provenance"]["shortage_cost_per_unit"] == "unknown"
    assert any("UNKNOWN" in w for w in plan["warnings"])
    assert plan["economics_provenance"]["supplier_capacity"] in ("assumed", "measured")
    assert any("capacity" in w.lower() for w in plan["warnings"])
    assert plan["mode_run"] == "incumbent"       # nothing priced can justify a departure
