"""P4B V1 open PO / commitment intervention: identity without declarations, contract refusals and credit bounds,
KEEP incumbent and verdicts, the operator block, migration 022 + adapter, the workspace flag and the API."""
from __future__ import annotations

import json
import re

import duckdb
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.dependencies import get_conn, require_operator
from api.routers import zaad_full
from scripts.setup_db import setup_db
from tests.unit.test_zaad_sourcing_workspace import make_network_vault
from zaad.commitments.contracts import resolve
from zaad.commitments.explain import NO_IMPROVEMENT, RECOMMENDED
from zaad.commitments.fixtures import CANCEL, KEEP, _f20_no_options, base, build, build_request, open_po, with_stock
from zaad.commitments.workspace import commitment_declarations
from zaad.full.planner import plan
from zaad.full.workspace import build_request as build_workspace_request

PAT = (r'"(information_hash|request_hash|fingerprint|input_fingerprint)": "[0-9a-f]+"'
       r'|"(solve_seconds|solver_seconds_total|seconds|elapsed_seconds|wall_seconds|plan_wall_s)": [^,}]+')


def _strip(rep: dict) -> str:
    return re.sub(PAT, "", json.dumps({k: v for k, v in rep.items() if k != "commitments"}, sort_keys=True, default=str))


def test_keep_only_orders_reach_no_p4b_code():
    req = _f20_no_options()
    assert resolve(req) is None
    rep = plan(req)
    assert "commitments" not in rep and rep["selected_policy"]


def test_contract_refuses_assumed_rights_and_unbounded_credits():
    d = with_stock(base(), 100.)
    with pytest.raises(ValidationError, match="never assumed"):
        build_request(d, open_po(d, [KEEP(d), CANCEL(d, provenance="CONFIGURED_ASSUMPTION")]))
    with pytest.raises(ValidationError, match="above the refundable deposit"):
        build_request(d, open_po(d, [KEEP(d), CANCEL(d, credit=1.)], prepaid=2., refundable=.25))
    with pytest.raises(ValidationError, match="may not fall below"):
        build_request(d, open_po(d, [KEEP(d), CANCEL(d, max_quantity=80.)], split=True, minimum=40.))
    with pytest.raises(ValidationError, match="unknown stages"):
        build_request(d, open_po(d, [KEEP(d), CANCEL(d, stages=("beamed",))]))
    with pytest.raises(ValidationError):
        build_request(d, open_po(d, [KEEP(d), CANCEL(d)], stage="beamed"))
    ok = build_request(d, open_po(d, [KEEP(d), CANCEL(d, credit=.5)], prepaid=2., refundable=.25))
    assert ok.pipeline[0].options[1].credit_per_unit == .5


def test_cancel_is_recommended_only_when_material_and_keep_is_the_incumbent():
    rep = plan(build("F01_cancel_optimal"))
    block = rep["commitments"]
    assert block["verdict"] == RECOMMENDED and block["orders"][0]["recommended_action"] == "CANCEL"
    assert {r["option"]: r["quantity"] for r in rep["incumbent_actions"] if r["action"] == "po_option"} == {"keep": 100.}
    assert block["approval_required"] and not block["executable_amendment"] and rep["approval_required"]
    rep2 = plan(build("F02_cancel_not_worthwhile"))
    assert rep2["commitments"]["verdict"] == NO_IMPROVEMENT and rep2["commitments"]["orders"][0]["recommended_action"] == "KEEP"


def test_refundable_credit_is_bounded_and_priced_once():
    sunk = plan(build("F11_sunk_deposit"))["commitments"]
    refund = plan(build("F12_refundable_deposit"))["commitments"]
    assert sunk["commitment_ledger_lines"]["commitment_credit"]["selected"] == 0. and refund["commitment_ledger_lines"]["commitment_credit"]["selected"] == -200.
    assert refund["orders"][0]["economic_drivers"]["refundable_credits"] == 200. and refund["orders"][0]["irreversibility"]["sunk_per_unit"] == 0.
    assert sunk["orders"][0]["irreversibility"]["sunk_per_unit"] == 2. and sunk["commitment_ledger_lines"]["opening_assets"]["selected"] >= 200.


def test_block_explains_windows_and_prohibited_orders():
    rep = plan(build("F10_already_shipped"))
    o = rep["commitments"]["orders"][0]
    assert o["recommended_action"] == "KEEP" and o["irreversibility"]["physically_committed"] and o["irreversibility"]["state"].startswith("shipped")
    assert all(not w["eligible"] and w["reasons"] for w in o["amendment_windows"] if w["action"] != "keep")


@pytest.fixture()
def vault():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    make_network_vault(conn, seed=7)
    return conn


def _app(vault, operator="tenant_n"):
    app = FastAPI()
    app.include_router(zaad_full.router)

    def conn_override():
        yield vault

    app.dependency_overrides[get_conn] = conn_override
    app.dependency_overrides[require_operator] = lambda: operator
    from api.routers.zaad import bounded_rate
    app.dependency_overrides[bounded_rate] = lambda: None
    return app


def test_migration_022_is_additive_and_the_flag_attaches_only_declared_options(vault):
    tables = {r[0] for r in vault.execute("select table_name from information_schema.tables").fetchall()}
    assert {"stg_po_options", "stg_po_commitments"} <= tables
    cols = vault.execute("select table_name, column_name from information_schema.columns order by 1,2").fetchall()
    setup_db(vault)
    assert vault.execute("select table_name, column_name from information_schema.columns order by 1,2").fetchall() == cols
    assert commitment_declarations(vault, "tenant_n") is None
    req0, rep0 = build_workspace_request(vault, "tenant_n")
    req1, rep1 = build_workspace_request(vault, "tenant_n", commitments=True)
    assert rep0["commitments"] == {"requested": False, "declared": False, "options_attached": 0}
    assert rep1["commitments"]["requested"] and not rep1["commitments"]["declared"] and req1.model_dump() == req0.model_dump()
    assert all(all(o.action == "keep" for o in po.options) for po in req1.pipeline)
    if req1.pipeline:
        po = req1.pipeline[0]
        vault.execute("insert into stg_po_options (operator_id, po_id, option_id, action, due_offset_periods, fee_per_unit, max_quantity, deadline, allowed_stages, contract_reference, provenance) "
                      f"values ('tenant_n', '{po.id}', 'cancel_{po.id}', 'cancel', 0, 0.25, {po.remaining}, TIMESTAMP '2030-01-01', '[\"{po.stage}\"]', 'MSA-1', 'CONTRACT')")
        req2, rep2 = build_workspace_request(vault, "tenant_n", commitments=True)
        assert rep2["commitments"]["options_attached"] == 1 and resolve(req2) is not None and resolve(req2).ids == (po.id,)
        client = TestClient(_app(vault))
        r = client.get("/api/zaad/network/request/from-workspace", params={"max_solve_seconds": 5, "commitments": "true"})
        assert r.status_code == 200 and any(o["action"] == "cancel" for p in r.json()["request"]["pipeline"] for o in p["options"])
        r = client.get("/api/zaad/network/request/from-workspace", params={"max_solve_seconds": 5})
        assert r.status_code == 200 and all(o["action"] == "keep" for p in r.json()["request"]["pipeline"] for o in p["options"])
        vault.execute("insert into stg_po_options (operator_id, po_id, option_id, action, due_offset_periods, fee_per_unit, max_quantity, deadline, allowed_stages, contract_reference, provenance) "
                      "values ('tenant_n', 'ghost_po', 'c2', 'cancel', 0, 0.25, 1, TIMESTAMP '2030-01-01', '[\"ordered\"]', 'MSA-1', 'CONTRACT')")
        r = client.get("/api/zaad/network/request/from-workspace", params={"max_solve_seconds": 5, "commitments": "true"})
        assert r.status_code == 422 and r.json()["detail"]["code"] == "commitments_invalid"


def test_planner_api_carries_the_block_and_the_plan_shape():
    req = build("F06_defer_reduces_excess").model_copy(update={"max_solve_seconds": 5.})
    app = FastAPI()
    app.include_router(zaad_full.router)
    app.dependency_overrides[require_operator] = lambda: req.operator_id
    from api.routers.zaad import bounded_rate
    app.dependency_overrides[bounded_rate] = lambda: None
    r = TestClient(app).post("/api/zaad/network/plan", json=req.model_dump(mode="json"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["commitments"]["orders"][0]["recommended_action"] == "DEFER" and body["executable_purchase_order"] is False
    assert TestClient(app).post("/api/zaad/network/plan", json={**req.model_dump(mode="json"), "operator_id": "someone_else"}).status_code == 403


def test_defer_prices_only_through_existing_terms():
    rep = plan(build("F06_defer_reduces_excess"))
    lines = rep["commitments"]["commitment_ledger_lines"]
    assert lines["de_expedite_fee"]["selected"] == 10. and lines["holding"]["selected"] < lines["holding"]["incumbent"]
    assert "defer_cost" not in json.dumps(rep) and rep["commitments"]["commitment_component"]["mapped_to"].startswith("ORDERING")
