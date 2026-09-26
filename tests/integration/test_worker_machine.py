"""The dedicated-machine path: bundle out, run on a scratch vault, result back."""
from __future__ import annotations

import io
import json

import pytest

import infrastructure.operator_registry as orm
from api.routers import jobs as jobs_router
from synthetic.fmcg.distributor_sim import ARCHETYPES, ArchetypeSpec, build_history


@pytest.fixture(scope="module")
def history():
    spec = ArchetypeSpec(**{**ARCHETYPES["D_importer"].__dict__, "n_skus": 8, "n_suppliers": 2, "weeks": 60})
    return build_history("D_importer", seed=5, spec=spec)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(orm, "DEFAULT_DATA_ROOT", tmp_path / "data")
    reg = orm.OperatorRegistry(data_root=tmp_path / "data")
    op = reg.create_operator("Bundle Co", sector="commercial")
    tok = reg.issue_token(op.operator_id)
    monkeypatch.setenv("HARVESTMIND_AUTH_REQUIRED", "true")
    monkeypatch.setenv("HARVESTMIND_WORKER_TOKEN", "wt-test")
    monkeypatch.setenv("HARVESTMIND_WORKER_MACHINES", "false")
    monkeypatch.setenv("HARVESTMIND_GATE_SCENARIOS", "6")
    from fastapi.testclient import TestClient
    import api.main as api_main
    return TestClient(api_main.app), {"Authorization": f"Bearer {tok}"}, op.operator_id


def _upload(cl, h, table, df):
    r = cl.post(f"/intake/upload/{table}", headers=h, files={"file": (f"{table}.csv", io.BytesIO(df.to_csv(index=False).encode()), "text/csv")})
    assert r.status_code == 200, r.text


def _load(cl, h, history):
    skus = history.skus[["sku", "supplier_id", "unit_cost", "unit_price", "units_per_case", "moq_units"]]
    ol = history.order_lines.merge(history.customer_orders[["order_id", "customer_id", "order_date"]], on="order_id")
    orders = ol[["order_id", "customer_id", "order_date", "sku", "qty_ordered", "qty_shipped"]]
    pos = history.purchase_orders[["po_id", "po_date", "supplier_id", "sku", "qty_ordered", "unit_cost"]]
    rec = history.receipts[["po_id", "receipt_date", "sku", "qty_received"]]
    inv = history.inventory_snapshots.rename(columns={"week_start": "snapshot_date"})[["snapshot_date", "sku", "on_hand", "in_transit"]]
    inv = inv[inv["snapshot_date"] == inv["snapshot_date"].max()]
    for table, df in (("stg_fmcg_skus", skus), ("stg_fmcg_orders", orders), ("stg_fmcg_purchase_orders", pos),
                      ("stg_fmcg_receipts", rec), ("stg_fmcg_inventory", inv)):
        _upload(cl, h, table, df)


def test_worker_round_trip(client, history, tmp_path, monkeypatch):
    cl, h, op = client
    _load(cl, h, history)
    from api.routers import jobs as J
    from api import worker as W

    # a job the API believes is running on a machine (no in-process thread:
    # two HiGHS solves in one process would fight over its global scheduler)
    monkeypatch.setattr(J, "_dispatch", lambda job, op: J._set(job, runner="machine", progress="starting a dedicated solver machine"))
    r = cl.post("/jobs/diagnostic", headers=h)
    assert r.status_code == 200
    job_id = r.json()["id"]
    assert r.json()["runner"] == "machine"

    # bundle needs the worker token, and the operator token does not open it
    assert cl.get(f"/jobs/internal/{job_id}/bundle", headers=h).status_code == 401
    blob = cl.get(f"/jobs/internal/{job_id}/bundle", headers={"X-Worker-Token": jobs_router.job_token(job_id)}).content
    conn, meta = W.restore_bundle(blob, tmp_path / "scratch")
    assert meta["sector"] == "commercial"
    n_orders = conn.execute("SELECT COUNT(*) FROM stg_fmcg_orders").fetchone()[0]
    assert n_orders == len(history.order_lines)

    # the worker's HTTP calls routed through the test client
    def fake_call(method, path, body=None, raw=False, tries=5):
        hdr = {"X-Worker-Token": jobs_router.job_token(job_id)}
        resp = cl.get(path, headers=hdr) if method == "GET" else cl.post(path, headers=hdr, json=body)
        assert resp.status_code == 200, resp.text
        return resp.content if raw else resp.json()
    monkeypatch.setattr(W, "_call", fake_call)
    monkeypatch.setenv("ZAAD_INTERNAL_API", "http://test")
    assert W.run_job(job_id) == 0

    j = cl.get(f"/jobs/{job_id}", headers=h).json()
    assert j["status"] == "done" and j["summary"]["decision"] and j["progress"] == "report ready"
    assert "_hook" not in j and "operator_id" not in j
    saved = json.loads((orm.OperatorRegistry().vault_dir(op) / "reports" / f"{job_id}.json").read_text())
    assert saved["status"] == "done" and saved["summary"]["decision"] == j["summary"]["decision"]


def test_stale_machine_job_is_timed_out(client, monkeypatch):
    """A machine job that stopped reporting ends as TIMED_OUT (a retryable terminal state), never a spinner."""
    cl, h, _ = client
    from api.routers import jobs as J
    monkeypatch.setenv("HARVESTMIND_JOB_STALE_S", "0")
    monkeypatch.setattr(J, "STALE_AFTER_S", 0)
    monkeypatch.setattr(J, "MAX_RUN_S", 10 ** 9)   # exercise the stale rule, not the wall clock
    monkeypatch.setattr(J.fly_machines, "destroy_machine", lambda mid: None)
    with J._LOCK:
        J._JOBS["job_stale"] = {"id": "job_stale", "operator_id": cl.get("/me", headers=h).json()["operator_id"], "kind": "diagnostic",
                                "sector": "commercial", "status": "running", "progress": "x", "runner": "machine",
                                "created_at": "2020-01-01T00:00:00+00:00", "updated_at": "2020-01-01T00:00:00+00:00",
                                "finished_at": None, "error": None, "summary": None}
    j = cl.get("/jobs/job_stale", headers=h).json()
    assert j["status"] == "timed_out" and "no progress" in j["error"] and "run it again" in j["error"]
