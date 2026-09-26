"""P5 shared-core integration: planner hook identity, protection overlay, firm / non-firm supply, ledger
ownership, workspace flag (migration 020), migration idempotency, API gating on the planner paths."""
from __future__ import annotations

import json
import re

import duckdb
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.product.governance import actor_from as _actor_from
from api.dependencies import get_conn, require_actor, require_operator
from api.routers import zaad_atp, zaad_full
from scripts.setup_db import setup_db
from tests.unit.test_zaad_sourcing_workspace import make_network_vault
from zaad.atp.contracts import resolve
from zaad.atp.economics import LEDGER_KEYS
from zaad.atp.fixtures import STD, base, line, order, scene, with_atp
from zaad.atp.fixtures_integration import build
from zaad.atp.integration import atp_block
from zaad.full.contracts import Request
from zaad.full.planner import plan
from zaad.full.workspace import build_request

PAT = (r'"(information_hash|request_hash|fingerprint|input_fingerprint)": "[0-9a-f]+"'
       r'|"(solve_seconds|solver_seconds_total|seconds|elapsed_seconds|wall_seconds|plan_wall_s|partition_seconds|extract_seconds)": [^,}]+')


def _frozen(report: dict) -> str:
    return re.sub(PAT, "", json.dumps({k: v for k, v in report.items() if k != "atp"}, sort_keys=True, default=str))


@pytest.fixture(scope="module")
def planned():
    """One planner run with the block and one without, on the P0-protection fixture (shared by the tests below)."""
    req = build("I01_p0_protection_scarcity")
    return req, plan(req), plan(Request.model_validate({**req.model_dump(), "atp": None}))


def test_planner_hook_changes_no_frozen_decision_and_reports_the_overlay(planned):
    req, with_block, without = planned
    assert "atp" in with_block and "atp" not in without
    assert _frozen(with_block) == _frozen(without)
    rep = with_block["atp"]
    assert rep["path"] == "planner" and rep["protection_overlay_available"] and rep["approval_required"] and not rep["executable_promise"]
    rows = {(r["sku"], r["location"]): r for r in rep["protection_overlay"]}
    assert ("A", "north") in rows and rows["A", "north"]["hard_reservation"] is False
    assert rows["A", "north"]["promised_from_on_hand"] == 150. and rows["A", "north"]["remaining_after_promises"] == 0.
    assert rows["A", "north"]["below_protection_units"] == rows["A", "north"]["protection_units"]


def test_disabled_path_reaches_no_p5_code_inside_the_planner():
    req = base()
    disabled = Request.model_validate({**req.model_dump(), "atp": {"enabled": False}})
    assert resolve(disabled) is None and atp_block(disabled) is None
    a, b = plan(req), plan(disabled)
    assert "atp" not in a and "atp" not in b and _frozen(a) == _frozen(b)


def test_firm_inbound_is_promisable_and_uncertain_inbound_never_is():
    rep = atp_block(build("I08_firm_vs_uncertain_inbound"))
    firm = [p for p in rep["promised"] if p["lot"] == "transfer:firm1"]
    assert sum(p["quantity"] for p in firm) == 40. and all(p["promise_period"] == 2 for p in firm)
    assert rep["non_firm_availability"][0]["record"] == "OpenPO:po_uncertain" and rep["non_firm_availability"][0]["promised"] == 0.
    assert all(p["lot"] != "po:po_uncertain" for p in rep["promised"])
    with pytest.raises(ValueError, match="probabilistic inbound"):
        with_atp(scene(base(), 10.), [order("o", "c1", "std", [line("l", 1.)])], STD, include_inbound=True, inbound_confidence=.9)


def test_ledger_keys_are_owned_and_the_class_penalty_is_not_hidden_in_the_service_sla():
    rep = atp_block(build("I17_ledger_reconciliation"))
    assert set(rep["ledger"]) == set(LEDGER_KEYS) and set(rep["ledger_owner"]) == set(LEDGER_KEYS)
    units, drv = rep["unit_states"], rep["drivers"]
    assert abs(rep["ledger"]["sla"] - sum(u["unmet"] * drv[lid]["sla_per_unmet"] for lid, u in units.items())) < 1e-6
    assert abs(rep["ledger"]["shortage_penalty"] - sum(u["unmet"] * drv[lid]["shortage_penalty_per_unit"] for lid, u in units.items())) < 1e-6
    assert abs(sum(rep["ledger"].values()) - rep["optimised_cost"]) < 1e-6
    assert "transfer" not in rep["ledger"] and rep["fulfilment"]["p2_transfers_created"] == 0
    assert all(d["lost_basis"] == "frozen_contribution" and d["lost_contribution_per_unit"] == d["gross_selling_price"] - 5. for d in drv.values())


def test_no_implicit_transfer_and_direct_ship_from_are_structurally_distinct():
    direct = atp_block(build("I02_network_direct_ship_from"))
    assert all(p["fulfilment"] == "DIRECT" for p in direct["promised"]) and direct["ledger"]["alternative_ship_from"] == 0.
    blocked = atp_block(build("I03_implicit_transfer_rejected"))
    assert {u["quantity"] for u in blocked["unfulfilled"]} == {50.} and any("no implicit transfer" in b["reason"] for b in blocked["blocked_supply"])
    alt = atp_block(build("I17_ledger_reconciliation"))
    assert alt["fulfilment"]["alternative_ship_from_units"] > 0 and all(p["lane"] for p in alt["fulfilment"]["alternative_ship_from"]) and alt["fulfilment"]["p2_transfers_created"] == 0


def test_refused_declaration_fails_closed_inside_the_planner_path():
    req = scene(base(), 10.)
    req = with_atp(req, [order("o1", "c1", "std", [line("l1", 5., requested=7)])], STD, promise_horizon=8)
    # a state-level refusal (the engine must not reinterpret): force it by an impossible promise horizon on the state
    from zaad.atp import integration
    from zaad.atp.validation import AtpRefused
    original = integration.promise_with
    integration.promise_with = lambda *a, **k: (_ for _ in ()).throw(AtpRefused("atp: forced refusal"))
    try:
        rep = atp_block(req)
    finally:
        integration.promise_with = original
    assert rep["verdict"].startswith("REFUSED") and rep["reason"] == "atp: forced refusal" and rep["promised"] == [] and rep["approval_required"]


@pytest.fixture()
def vault():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    make_network_vault(conn, seed=7)
    return conn


def test_migration_020_is_additive_and_idempotent():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    def schema():
        rows = conn.execute("select table_name, column_name, data_type from information_schema.columns order by 1, 2").fetchall()
        return rows
    before = schema()
    setup_db(conn)   # a second run changes nothing
    assert schema() == before
    atp_tables = {"stg_atp_customer_orders", "stg_atp_service_classes", "stg_atp_policy"}
    tables = {r[0] for r in before}
    assert atp_tables <= tables
    # no pre-020 table carries an atp column and no atp table stores an allocation, promise or reservation
    assert not [r for r in before if r[0] not in atp_tables and "atp" in r[1]]
    assert not [r for r in before if r[0] in atp_tables and any(k in r[1] for k in ("promise_period", "allocated", "reserved_qty", "reservation"))]


def _app(vault, operator="tenant_n"):
    app = FastAPI()
    app.include_router(zaad_full.router)
    app.include_router(zaad_atp.router)

    def conn_override():
        yield vault

    app.dependency_overrides[get_conn] = conn_override
    app.dependency_overrides[require_operator] = lambda: operator
    # the planner routes check a capability (security review 2026-09); this client is the workspace administrator
    app.dependency_overrides[require_actor] = lambda: _actor_from({"operator_id": (lambda: operator)(), "actor_id": "admin", "name": "admin", "role": "ADMIN"})
    from api.routers.zaad import bounded_rate
    app.dependency_overrides[bounded_rate] = lambda: None
    return app


def test_workspace_flag_attaches_declared_orders_only_when_asked(vault, monkeypatch):
    req0, rep0 = build_request(vault, "tenant_n")
    assert req0.atp is None and not rep0["atp"]["requested"]
    req1, rep1 = build_request(vault, "tenant_n", atp=True)
    assert req1.atp is None and rep1["atp"]["requested"] and not rep1["atp"]["declared"] and any("stg_atp_customer_orders" in w for w in rep1["warnings"])
    sku = req1.skus[0].id
    customer = req1.customers[0].id
    vault.execute("insert into stg_atp_service_classes (operator_id, class_id, provenance, reference, shortage_penalty_per_unit, shortage_penalty_basis) "
                  "values ('tenant_n', 'hi', 'OPERATOR_DECLARED', 'policy-hi', 20.0, 'ADDITIONAL_TO_SERVICE_SLA')")
    vault.execute("insert into stg_atp_customer_orders (operator_id, order_id, line_id, customer_id, service_class, sku, quantity, requested_period, order_period) "
                  f"values ('tenant_n', 'o1', 'l1', '{customer}', 'hi', '{sku}', 5.0, 0, 0)")
    req2, rep2 = build_request(vault, "tenant_n", atp=True)
    assert req2.atp is not None and req2.atp.enabled and rep2["atp"]["enabled"] and rep2["atp"]["orders"] == 1
    monkeypatch.delenv("ZAAD_ATP_ENABLED", raising=False)
    client = TestClient(_app(vault))
    r = client.get("/api/zaad/network/request/from-workspace", params={"max_solve_seconds": 5, "atp": "true"})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "atp_disabled"
    monkeypatch.setenv("ZAAD_ATP_ENABLED", "1")
    r = client.get("/api/zaad/network/request/from-workspace", params={"max_solve_seconds": 5, "atp": "true"})
    assert r.status_code == 200 and r.json()["request"]["atp"]["enabled"] is True and r.json()["build"]["atp"]["orders"] == 1
    r = client.get("/api/zaad/network/request/from-workspace", params={"max_solve_seconds": 5})
    assert r.status_code == 200 and r.json()["request"]["atp"] is None


def test_planner_api_is_gated_bounded_and_tenant_checked(vault, monkeypatch):
    req = build("I19_tenant_mismatch_api")
    body = req.model_dump(mode="json")
    monkeypatch.delenv("ZAAD_ATP_ENABLED", raising=False)
    client = TestClient(_app(vault, req.operator_id))
    r = client.post("/api/zaad/network/plan", json=body)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "atp_disabled"
    assert client.post("/api/zaad/network/jobs", json=body).status_code == 422
    monkeypatch.setenv("ZAAD_ATP_ENABLED", "1")
    assert TestClient(_app(vault, "tenant_b")).post("/api/zaad/network/plan", json=body).status_code == 403
    big = json.loads(json.dumps(body))
    big["atp"]["orders"] = [{**big["atp"]["orders"][0], "id": f"o{i}", "lines": [{**big["atp"]["orders"][0]["lines"][0], "id": f"l{i}"}]} for i in range(201)]
    assert client.post("/api/zaad/network/plan", json=big).status_code == 413
    # a plannable request (the released P2 request's own customers carry the demand history the planner forecasts from)
    planned = build("I01_p0_protection_scarcity").model_copy(update={"max_solve_seconds": 5.})
    r = TestClient(_app(vault, planned.operator_id)).post("/api/zaad/network/plan", json=planned.model_dump(mode="json"))
    assert r.status_code == 200, r.text
    rep = r.json()
    assert rep["atp"]["path"] == "planner" and rep["atp"]["approval_required"] and rep["executable_purchase_order"] is False
    assert rep["atp"]["reservations"] and all(x["status"] == "PROPOSED" for x in rep["atp"]["reservations"])


def test_workspace_plan_forwards_every_phase_flag_by_keyword(vault, monkeypatch):
    """P5 release audit item C: `plan/from-workspace` forwards `recourse` (P4) and `atp` (P5) to the request
    builder by keyword; `recourse=false` builds the same request as no flag; both flags coexist. The planner
    call is stubbed (the planner-path proof with real solves is R16 / R17 in the release-audit evidence)."""
    from api.routers import zaad_full as router_module
    vault.execute("INSERT INTO stg_recourse_spec (operator_id, enabled, review_periods, observables, actions, demand_grid, continuations, provenance) "
                  "VALUES ('tenant_n', TRUE, '[3]', '[\"demand\"]', '[\"purchase\", \"transfer\"]', 5.0, 2, 'OPERATOR_DECLARED')")
    seen = []

    async def stub(req):
        seen.append(req)
        return {"status": "STUB", "actions": [], "incumbent_actions": [], "input_fingerprint": "0" * 64}

    monkeypatch.setattr(router_module, "compute", stub)
    monkeypatch.setenv("ZAAD_ATP_ENABLED", "1")
    client = TestClient(_app(vault))
    q = {"max_solve_seconds": 5, "shape": "network"}
    assert client.post("/api/zaad/network/plan/from-workspace", params=q).status_code == 200
    assert client.post("/api/zaad/network/plan/from-workspace", params={**q, "recourse": "false"}).status_code == 200
    assert client.post("/api/zaad/network/plan/from-workspace", params={**q, "recourse": "true"}).status_code == 200
    none, false, true = seen
    assert none.recourse is None and false.recourse is None and none.model_dump() == false.model_dump()
    assert true.recourse is not None and true.recourse.enabled and tuple(true.recourse.review_periods) == (3,) and true.atp is None
    sku, customer = none.skus[0].id, none.customers[0].id
    vault.execute("insert into stg_atp_service_classes (operator_id, class_id, provenance, reference, shortage_penalty_per_unit, shortage_penalty_basis) "
                  "values ('tenant_n', 'hi', 'OPERATOR_DECLARED', 'policy-hi', 20.0, 'ADDITIONAL_TO_SERVICE_SLA')")
    vault.execute("insert into stg_atp_customer_orders (operator_id, order_id, line_id, customer_id, service_class, sku, quantity, requested_period, order_period) "
                  f"values ('tenant_n', 'o1', 'l1', '{customer}', 'hi', '{sku}', 5.0, 0, 0)")
    assert client.post("/api/zaad/network/plan/from-workspace", params={**q, "recourse": "true", "atp": "true"}).status_code == 200
    assert client.post("/api/zaad/network/plan/from-workspace", params={**q, "atp": "true"}).status_code == 200
    both, atp_only = seen[3], seen[4]
    assert both.recourse is not None and both.recourse.enabled and both.atp is not None and both.atp.enabled
    assert atp_only.recourse is None and atp_only.atp is not None and atp_only.atp.enabled
