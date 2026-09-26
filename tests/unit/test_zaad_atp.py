"""P5 ATP / scarce-supply allocation: isolated engine, contracts, neutrality, determinism, adapter, API."""
from __future__ import annotations

import json
import re

import duckdb
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.product.governance import actor_from as _actor_from
from api.dependencies import require_actor, require_operator
from api.routers import zaad_atp
from scripts.setup_db import setup_db
from zaad.atp.contracts import resolve
from zaad.atp.fixtures import STD, base, build, cls, line, order, scene, with_atp
from zaad.atp.promise import promise
from zaad.atp.workspace import atp_block
from zaad.full.contracts import Request
from zaad.full.planner import plan, report_json


PAT = (r'\\?"(information_hash|request_hash|fingerprint)\\?": \\?"[0-9a-f]+\\?"'
       r'|\\?"(solve_seconds|solver_seconds_total|seconds|elapsed_seconds|wall_seconds|plan_wall_s|partition_seconds|extract_seconds)\\?": [0-9.e-]+'
       r'|\\?"atp\\?": (null|\{[^{}]*\})')   # timing, hashes (also inside embedded JSON strings) and the request echo of the block itself


def _strip(s: str) -> str:
    return re.sub(PAT, "", s)


def test_disabled_path_is_frozen():
    """Invariant 20: no `atp` block, or `enabled` false, reaches no P5 code and leaves the planner report identical."""
    req = base()   # the released P2 request as is (its services carry the demand history the planner forecasts from)
    assert req.atp is None and resolve(req) is None and promise(req) is None
    disabled = Request.model_validate({**req.model_dump(), "atp": {"enabled": False}})
    assert resolve(disabled) is None and promise(disabled) is None
    a = _strip(json.dumps(report_json(plan(req)), sort_keys=True, default=str))
    b = _strip(json.dumps(report_json(plan(disabled)), sort_keys=True, default=str))
    assert a == b and '"atp"' not in a


def test_contract_refuses_malformed_declarations():
    req = scene(base(), 100.)
    with pytest.raises(ValidationError, match="undeclared strategic flag"):
        cls("k", strategic=True)
    with pytest.raises(ValidationError, match="unknown customer"):
        with_atp(req, [order("o", "ghost", "std", [line("l", 1.)])], STD)
    with pytest.raises(ValidationError, match="impossible requested date"):
        with_atp(req, [order("o", "c1", "std", [line("l", 1., requested=30)])], STD, promise_horizon=8)
    with pytest.raises(ValidationError, match="conflicting service policies"):
        with_atp(req, [order("o", "c1", "std", [line("l", 1.)])], STD, incumbent_policy="DECLARED_MANUAL")


def test_scarcity_follows_declared_economics_and_reconciles():
    rep = promise(build("B_true_scarcity"))
    assert rep["verdict"] == "ALLOCATION CHANGE RECOMMENDED"
    got = {}
    for p in rep["promised"]:
        got[p["line"]] = got.get(p["line"], 0.) + p["quantity"]
    assert got == {"lX": 50., "lY": 10.} and rep["unfulfilled"][0]["quantity"] == 40.
    assert "shortage penalty per unit 20.00 against 0.00" in rep["why"][0]
    assert abs(sum(rep["ledger"].values()) - rep["optimised_cost"]) < 1e-6
    assert all(abs(u["balance_residual"]) < 1e-9 for u in rep["unit_states"].values())
    assert rep["approval_required"] is True and rep["executable_promise"] is False
    assert "priority_score" not in json.dumps(rep)


def test_no_unit_promised_twice_and_reserved_never_promised():
    rep = promise(build("T_double_reservation"))
    assert abs(sum(p["quantity"] for p in rep["promised"]) - 40.) < 1e-9
    assert all(r["reserved_before"] == 60. and r["remaining_unreserved"] >= -1e-9 for r in rep["remaining_supply"])


def test_time_and_physics_are_respected():
    f = promise(build("F_backorder_allowed"))
    late = [p for p in f["promised"] if p["periods_late"]]
    assert sum(p["quantity"] for p in late) == 50. and all(p["promise_period"] == 2 for p in late) and f["ledger"]["backorder_carry"] == 100.
    j = promise(build("J_inbound_too_late"))
    assert not j["promised"] and j["next_promise"]["l1"]["earliest_period_with_firm_supply"] == 4
    m = promise(build("M_produce_remaining_life"))
    assert all(p["lot"] != "stock:north_lot" for p in m["promised"]) and sum(p["quantity"] for p in m["promised"]) == 100.
    k = promise(build("K_multiple_locations"))
    assert abs(k["ledger"]["alternative_ship_from"] - 10.) < 1e-9 and all(p["lane"] for p in k["promised"] if p["ship_from"] == "central")


def test_incumbent_first_and_deterministic_ties():
    q = promise(build("Q_optimal_incumbent"))
    assert q["verdict"].startswith("NO MATERIAL") and q["recommended_policy"] == "TIER_PRIORITY" and abs(q["value_of_allocation"]) < 1e-9
    p1 = [promise(build("P1_indifferent_lexical"))["promised"] for _ in range(3)]
    assert p1[0] == p1[1] == p1[2] and p1[0][0]["line"] == "l1" and p1[0][0]["quantity"] == 50.
    p2 = promise(build("P2_indifferent_proportional"))
    assert sorted((p["line"], p["quantity"]) for p in p2["promised"]) == [("l1", 25.), ("l2", 25.)]
    assert p2["incumbent_cost"] == promise(build("P1_indifferent_lexical"))["incumbent_cost"]   # the fairness rule never changes the ledger


def test_strategic_flag_only_acts_through_declared_economics():
    from zaad.atp.fixtures import _R_flag_only
    with_pen = promise(build("R_strategic_declared"))
    flag_only = promise(_R_flag_only())
    assert with_pen["verdict"].startswith("ALLOCATION CHANGE") and flag_only["verdict"].startswith("NO MATERIAL")
    assert "board-2026-09" in json.dumps(with_pen["service_classes"])


@pytest.fixture()
def vault():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    return conn


def test_migration_020_and_adapter(vault):
    tables = {r[0] for r in vault.execute("select table_name from information_schema.tables").fetchall()}
    assert {"stg_atp_customer_orders", "stg_atp_service_classes", "stg_atp_policy"} <= tables
    assert atp_block(vault, "op_x") is None
    vault.execute("insert into stg_atp_service_classes (operator_id, class_id, provenance, shortage_penalty_per_unit) values ('op_x', 'hi', 'OPERATOR_DECLARED', 20.0)")
    vault.execute("insert into stg_atp_customer_orders (operator_id, order_id, line_id, customer_id, service_class, sku, quantity, requested_period, order_period) values ('op_x', 'o1', 'l1', 'c1', 'hi', 'A', 50.0, 0, 0)")
    vault.execute("insert into stg_atp_policy (operator_id, incumbent_policy, fairness, promise_horizon) values ('op_x', 'FCFS_ORDER_DATE', 'NONE', 6)")
    block = atp_block(vault, "op_x")
    assert block["enabled"] and block["orders"][0]["lines"][0]["quantity"] == 50. and block["service_classes"][0]["shortage_penalty_per_unit"] == 20. and block["promise_horizon"] == 6
    assert atp_block(vault, "op_other") is None


def _app(operator="tenant_a"):
    app = FastAPI()
    app.include_router(zaad_atp.router)
    app.dependency_overrides[require_operator] = lambda: operator
    # the planner routes check a capability (security review 2026-09); this client is the workspace administrator
    app.dependency_overrides[require_actor] = lambda: _actor_from({"operator_id": (lambda: operator)(), "actor_id": "admin", "name": "admin", "role": "ADMIN"})
    from api.routers.zaad import bounded_rate
    app.dependency_overrides[bounded_rate] = lambda: None
    return app


def test_api_is_off_by_default_and_fails_closed(monkeypatch):
    req = build("B_true_scarcity").model_dump(mode="json")
    monkeypatch.delenv("ZAAD_ATP_ENABLED", raising=False)
    client = TestClient(_app(req["operator_id"]))
    assert client.post("/api/zaad/atp/promise", json=req).status_code == 404
    monkeypatch.setenv("ZAAD_ATP_ENABLED", "1")
    r = client.post("/api/zaad/atp/promise", json=req)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["approval_required"] is True and body["executable_promise"] is False and body["atp"]["verdict"] == "ALLOCATION CHANGE RECOMMENDED"
    # absent block -> 422 atp_absent; malformed -> 422 atp_invalid; other tenant -> 403; over bounds -> 413
    absent = {**req, "atp": None}
    assert client.post("/api/zaad/atp/promise", json=absent).json()["detail"]["code"] == "atp_absent"
    bad = json.loads(json.dumps(req))
    bad["atp"]["orders"][0]["customer"] = "ghost"
    r = client.post("/api/zaad/atp/promise", json=bad)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "atp_invalid"
    assert TestClient(_app("tenant_b")).post("/api/zaad/atp/promise", json=req).status_code == 403
    big = json.loads(json.dumps(req))
    big["atp"]["orders"] = [{**big["atp"]["orders"][0], "id": f"o{i}", "lines": [{**big["atp"]["orders"][0]["lines"][0], "id": f"l{i}"}]} for i in range(201)]
    assert client.post("/api/zaad/atp/promise", json=big).status_code == 413
