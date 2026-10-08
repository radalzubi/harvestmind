"""A commercial workspace with synthetic history runs the diagnostic to
completion and hands back a PDF. Slow (real solves), so kept to a small
book."""
from __future__ import annotations

import io
import time

import pytest

import infrastructure.operator_registry as orm
from synthetic.fmcg.distributor_sim import ARCHETYPES, ArchetypeSpec, build_history, closing_inventory_rows


@pytest.fixture(scope="module")
def history():
    spec = ArchetypeSpec(**{**ARCHETYPES["A_stable"].__dict__, "n_skus": 8, "n_suppliers": 2, "n_customers": 5, "weeks": 70})
    return build_history("A_stable", seed=5, spec=spec)


def _upload(client, headers, table, df):
    r = client.post(f"/intake/upload/{table}", headers=headers,
                    files={"file": (f"{table}.csv", io.BytesIO(df.to_csv(index=False).encode()), "text/csv")})
    assert r.status_code == 200, r.text
    assert r.json()["rows_inserted"] == len(df), r.json()
    return r.json()


def test_commercial_diagnostic_end_to_end(tmp_path, monkeypatch, history):
    monkeypatch.setattr(orm, "DEFAULT_DATA_ROOT", tmp_path / "data")
    reg = orm.OperatorRegistry(data_root=tmp_path / "data")
    op = reg.create_operator("Small Distributor", sector="commercial")
    tok = reg.issue_token(op.operator_id)
    monkeypatch.setenv("HARVESTMIND_AUTH_REQUIRED", "true")
    monkeypatch.setenv("HARVESTMIND_SOLVER_THREADS", "1")
    from fastapi.testclient import TestClient
    import api.main as api_main
    import api.routers.jobs as jobs
    # the end-to-end test bounds the optimizer replay (its own suites cover it): two products, three decision
    # dates, a short budget - the real planner still runs at every date, inside this test's deadline
    monkeypatch.setattr(jobs, "REPLAY_SKUS", 2)
    monkeypatch.setattr(jobs, "REPLAY_REVIEWS", 3)
    monkeypatch.setattr(jobs, "REPLAY_BUDGET_S", 120.0)
    cl, h = TestClient(api_main.app), {"Authorization": f"Bearer {tok}"}

    skus = history.skus[["sku", "supplier_id", "unit_cost", "unit_price", "units_per_case", "moq_units"]]
    orders = history.order_lines.merge(history.customer_orders[["order_id", "customer_id", "order_date"]], on="order_id")
    pos = history.purchase_orders[["po_id", "po_date", "supplier_id", "sku", "qty_ordered", "unit_cost"]]
    rec = history.receipts[["po_id", "receipt_date", "sku", "qty_received"]]
    inv = closing_inventory_rows(history.inventory_snapshots)
    inv = inv[inv["snapshot_date"] == inv["snapshot_date"].max()]
    for table, df in (("stg_fmcg_skus", skus), ("stg_fmcg_orders", orders[["order_id", "customer_id", "order_date", "sku", "qty_ordered"]]),
                      ("stg_fmcg_purchase_orders", pos), ("stg_fmcg_receipts", rec), ("stg_fmcg_inventory", inv)):
        _upload(cl, h, table, df)

    j = cl.post("/jobs/diagnostic", headers=h)
    assert j.status_code == 200, j.text
    jid = j.json()["id"]
    assert cl.get(f"/jobs/{jid}/report.pdf", headers=h).status_code in (409, 200)
    deadline = time.time() + 600
    while time.time() < deadline:
        st = cl.get(f"/jobs/{jid}", headers=h).json()
        if st["status"] in ("done", "failed"):
            break
        time.sleep(2)
    assert st["status"] == "done", st
    s = st["summary"]
    assert s["sector"] == "commercial" and s["decision"] and s["reason"]
    assert s["products"] == 8 and s["suppliers"] == 2
    assert "state" in s and "lanes" in s and "readiness" in s
    pdf = cl.get(f"/jobs/{jid}/report.pdf", headers=h)
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF" and len(pdf.content) > 2000
    # a second start while nothing is running creates a new job; the old one is still readable
    assert cl.get(f"/jobs/{jid}", headers=h).json()["status"] == "done"
