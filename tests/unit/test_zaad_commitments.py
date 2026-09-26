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

from api.product.governance import actor_from as _actor_from
from api.dependencies import get_conn, require_actor, require_operator
from api.routers import zaad_full
from scripts.setup_db import setup_db
from tests.unit.test_zaad_sourcing_workspace import make_network_vault
from zaad.commitments.contracts import resolve
from zaad.commitments.explain import NO_IMPROVEMENT, RECOMMENDED
from zaad.commitments.fixtures import CANCEL, KEEP, _f20_no_options, base, build, build_request, open_po, option, with_stock
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
    # the planner routes check a capability (security review 2026-09); this client is the workspace administrator
    app.dependency_overrides[require_actor] = lambda: _actor_from({"operator_id": (lambda: operator)(), "actor_id": "admin", "name": "admin", "role": "ADMIN"})
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
    # the planner routes check a capability (security review 2026-09); this client is the workspace administrator
    app.dependency_overrides[require_actor] = lambda: _actor_from({"operator_id": (lambda: req.operator_id)(), "actor_id": "admin", "name": "admin", "role": "ADMIN"})
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


# ---------------------------------------------------------------- release audit corrections (P4B V1 release audit)

def test_release_audit_floor_sums_cancel_caps_only_when_split_is_allowed():
    d = with_stock(base(), 100.)
    two = [KEEP(d), option(d, "c1", "cancel", 2, .25, 0., max_quantity=40.), option(d, "c2", "cancel", 2, .10, 0., max_quantity=40.)]
    with pytest.raises(ValidationError, match="together may cancel"):
        build_request(d, open_po(d, two, split=True, minimum=40.))
    exclusive = build_request(d, open_po(d, two, split=False, minimum=40.))      # one option active at a time: each cap inside the floor
    assert exclusive.pipeline[0].minimum_remaining_quantity == 40.
    ok = build_request(d, open_po(d, [KEEP(d), option(d, "c1", "cancel", 2, .25, 0., max_quantity=30.), option(d, "c2", "cancel", 2, .10, 0., max_quantity=30.)], split=True, minimum=40.))
    assert len(ok.pipeline[0].options) == 3


def test_release_audit_settlement_refuses_a_floor_breach_even_when_the_contract_is_bypassed():
    from zaad.full.contracts import OpenPO, POOption
    from zaad.full.settlement import PhysicalViolation, settle
    from zaad.full.worlds import draw
    from zaad.meio.planner import solution_from_actions
    d = with_stock(base(), 100.)
    raw = open_po(d, [KEEP(d), CANCEL(d, max_quantity=100.)], split=True, minimum=40.)
    po = OpenPO.model_construct(**{**raw, "options": tuple(POOption.model_validate(o) for o in raw["options"])})
    req = build_request(d, None).model_copy(update={"pipeline": (po,)})
    forced = solution_from_actions([{"action": "po_option", "po": "po1", "option": "cancel", "period": 0, "quantity": 70.},
                                    {"action": "po_option", "po": "po1", "option": "keep", "period": 0, "quantity": 30.}])
    with pytest.raises(PhysicalViolation, match="below its declared minimum"):
        settle(req, forced, draw(req, req.seed, 1, deterministic=True)[0])


def test_release_audit_credit_is_declared_only_on_cancel():
    d = with_stock(base(), 100.)
    from zaad.commitments.fixtures import DEFER, EXPEDITE
    for opt in (DEFER(d, credit=1.), EXPEDITE(d, credit=1.)):
        with pytest.raises(ValidationError, match="only on a cancel option"):
            build_request(d, open_po(d, [KEEP(d), opt], prepaid=2., refundable=1.))
    assert build_request(d, open_po(d, [KEEP(d), CANCEL(d, credit=1.)], prepaid=2., refundable=1.)).pipeline[0].options[1].credit_per_unit == 1.


def test_release_audit_adapter_normalises_case_and_refuses_everything_else_with_the_commitments_code():
    from datetime import datetime, timezone
    from zaad.commitments.workspace import attach
    d = with_stock(base(), 100.)
    as_of = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def rows():
        return [{**open_po(d, [KEEP(d)]), "id": "po1", "stage": "confirmed"}]

    def opt(**over):
        return {"po_id": "po1", "id": "c", "action": "cancel", "due_offset_periods": 2, "fee_per_unit": .25, "credit_per_unit": None, "remaining_invoice_per_unit": 0.,
                "payment_offset_periods": None, "max_quantity": 100., "deadline": "2030-01-01", "allowed_stages": '["confirmed"]', "contract_reference": "ref", "provenance": "contract", **over}

    r = rows()
    attach(r, ({"po1": {"stage": " Confirmed ", "allow_split_amendments": None, "minimum_remaining_quantity": None, "prepaid_per_remaining_unit": None, "deposit_refundable_fraction": None, "cancellation_status": None}}, {"po1": [opt(action=" Cancel ")]}), as_of=as_of, period_days=7)
    assert r[0]["stage"] == "confirmed" and r[0]["options"][1]["action"] == "cancel" and r[0]["options"][1]["provenance"] == "CONTRACT"
    bad = [({"po1": {"stage": "teleported"}}, {}, "outside the vocabulary"), ({}, {"po1": [opt(action="reroute")]}, "outside"),
           ({}, {"po1": [opt(provenance="guess")]}, "provenance"), ({}, {"po1": [opt(fee_per_unit=-1.)]}, "finite number"),
           ({}, {"po1": [opt(max_quantity=float("inf"))]}, "finite number"), ({"po1": {"deposit_refundable_fraction": 1.5}}, {}, "finite number"),
           ({}, {"po1": [opt(), opt()]}, "more than once"), ({}, {"po1": [opt(id=f"c{i}") for i in range(12)]}, "over the limit"),
           ({}, {"po1": [opt(allowed_stages='["beamed"]')]}, "outside the vocabulary")]
    for terms, options, why in bad:
        with pytest.raises(ValueError, match="commitments: .*" + why):
            attach(rows(), (terms, options), as_of=as_of, period_days=7)


def test_release_audit_api_bounds_the_declared_option_set():
    from zaad.commitments.contracts import INTERACTIVE_LIMITS, over_limits
    d = with_stock(base(), 100.)
    many = [KEEP(d)] + [option(d, f"r{i}", "reschedule", 3 + (i % 3), .1, 5.3) for i in range(INTERACTIVE_LIMITS["options_per_order"])]
    req = build_request(d, open_po(d, many))
    assert "over the limit" in over_limits(req) and over_limits(req, factor=4) == ""
    app = FastAPI()
    app.include_router(zaad_full.router)
    app.dependency_overrides[require_operator] = lambda: req.operator_id
    # the planner routes check a capability (security review 2026-09); this client is the workspace administrator
    app.dependency_overrides[require_actor] = lambda: _actor_from({"operator_id": (lambda: req.operator_id)(), "actor_id": "admin", "name": "admin", "role": "ADMIN"})
    from api.routers.zaad import bounded_rate
    app.dependency_overrides[bounded_rate] = lambda: None
    r = TestClient(app).post("/api/zaad/network/plan", json=req.model_dump(mode="json"))
    assert r.status_code == 413 and "commitment bounds" in r.text
    assert over_limits(build("F20_keep_optimal")) == ""


def test_release_audit_block_separates_the_commitment_verdict_from_the_plan_status():
    rep = plan(build("F14_alternative_source"))
    b = rep["commitments"]
    assert b["commitment_action"] == "KEEP" and b["commitment_verdict"] == NO_IMPROVEMENT and b["commitment_value_vs_keep"] == 0.
    assert b["overall_plan_status"] == rep["status"] and b["plan_changes_outside_commitments"] and "does not recommend amending" in b["reading"]
    rep = plan(build("F01_cancel_optimal"))
    b = rep["commitments"]
    assert b["commitment_action"] == "CANCEL" and b["commitment_verdict"] == RECOMMENDED and b["commitment_value_vs_keep"] == b["material_improvement_vs_keep"]["plan_level_value"] > 0


def test_release_audit_api_shape_without_declaration_carries_no_commitment_keys():
    req = _f20_no_options().model_copy(update={"max_solve_seconds": 5.})
    app = FastAPI()
    app.include_router(zaad_full.router)
    app.dependency_overrides[require_operator] = lambda: req.operator_id
    # the planner routes check a capability (security review 2026-09); this client is the workspace administrator
    app.dependency_overrides[require_actor] = lambda: _actor_from({"operator_id": (lambda: req.operator_id)(), "actor_id": "admin", "name": "admin", "role": "ADMIN"})
    from api.routers.zaad import bounded_rate
    app.dependency_overrides[bounded_rate] = lambda: None
    body = TestClient(app).post("/api/zaad/network/plan", json=req.model_dump(mode="json")).json()
    assert "commitments" not in body and "executable_amendment" not in body and body["executable_purchase_order"] is False
