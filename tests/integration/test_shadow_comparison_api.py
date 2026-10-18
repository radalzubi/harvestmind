"""Shadow comparison end to end on the SYNTHETIC sample (HARDENING V1, H3b): capture a plan, run ZAAD for the
plan's origin, settle both on the planner's worlds, store the comparison immutably."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import duckdb
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dependencies import get_conn, require_actor, require_operator
from api.product import operator_plans as OP
from api.product.governance import actor_from
from api.routers import zaad_shadow
from api.routers.intake import load_fmcg_sample_into
from scripts.setup_db import setup_db
from zaad.full import comparator as C
from zaad.full.workspace import build_request

OPERATOR = "tenant_shadow"
AS_OF = "2025-09-01T00:00:00Z"
SKU = "SKU-0001"


@pytest.fixture(autouse=True)
def production_engines(monkeypatch, tmp_path):
    """Production settings: the superseded planning engines are unreachable (a reachable one taints a vault's exposure history for
    good) and a job store is configured (without one the operator's job history cannot be examined, so nothing is verified)."""
    monkeypatch.setenv("ZAAD_LEGACY_PLANNERS", "0")
    monkeypatch.setenv("ZAAD_JOB_STORE", str(tmp_path / "jobs.sqlite"))


@pytest.fixture(scope="module")
def vault():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    load_fmcg_sample_into(conn, seed=7, archetype="A_stable")
    yield conn
    conn.close()


def _client(conn, role="BUYER"):
    app = FastAPI()
    app.include_router(zaad_shadow.router)

    def conn_override():
        yield conn
    app.dependency_overrides[get_conn] = conn_override
    app.dependency_overrides[require_operator] = lambda: OPERATOR
    app.dependency_overrides[require_actor] = lambda: actor_from({"operator_id": OPERATOR, "actor_id": "buyer-1", "name": "Buyer", "role": role})
    return TestClient(app)


def test_capture_compare_and_store(vault):
    cl = _client(vault)
    supplier = vault.execute("SELECT supplier_id FROM stg_fmcg_skus WHERE sku = ?", [SKU]).fetchone()[0]
    captured = cl.post("/api/zaad/shadow/plans", json={"as_of": AS_OF, "provenance": "OPERATOR_SUBMITTED", "source_reference": "weekly-sheet-36",
                                                        "lines": [{"sku": SKU, "supplier_id": supplier, "quantity": 1200}]})
    assert captured.status_code == 201, captured.text
    plan = captured.json()
    assert plan["version"] == 1 and plan["integrity"] == "VERIFIED" and plan["created"] is True
    # a retry of the same capture adds nothing
    again = cl.post("/api/zaad/shadow/plans", json={"as_of": AS_OF, "provenance": "OPERATOR_SUBMITTED", "lines": [{"sku": SKU, "supplier_id": supplier, "quantity": 1200}]})
    assert again.status_code == 201 and again.json()["plan_id"] == plan["plan_id"] and again.json()["created"] is False
    # a viewer may not capture
    assert _client(vault, role="VIEWER").post("/api/zaad/shadow/plans", json={"as_of": AS_OF, "provenance": "OPERATOR_SUBMITTED", "lines": [{"sku": SKU, "quantity": 1}]}).status_code == 403

    out = cl.post(f"/api/zaad/shadow/plans/{plan['plan_id']}/compare", params={"horizon": 8, "max_solve_seconds": 5})
    assert out.status_code == 201, out.text
    body = out.json()
    contract = body["contract"]
    # every synchronous recommendation is recorded in the vault's exposure ledger before it is returned, so this run is provably the
    # FIRST exposure for the origin and the plan, captured before it, is the independent baseline: READY (no realized value is ever claimed)
    assert contract["mode"] == "SHADOW_COMPARISON_MODE" and contract["readiness"] == "READY" and contract["comparator"]["type"] == "ACTUAL_OPERATOR_PLAN"
    assert contract["comparator"]["fidelity"] == "EXACT" and contract["claim_class"] == "SHADOW_COMPARISON" and body["exposure"]["basis"] == "RECOMMENDATION_LEDGER"
    assert contract["permissions"]["can_claim_shadow_difference"] is True and contract["permissions"]["can_claim_realized_value"] is False
    assert body["exposure"]["history"]["verified"] is True and body["exposure"]["history"]["ledger_exposures"] == 1
    assert contract["decision_reference"]["provenance"] == "INFERRED_FROM_HISTORY" and body["recommendation"]["decision_reference"]["fidelity"] == "RECONSTRUCTED"
    q = body["quantities"]
    assert q["recorded_plan_units"] == 1200 and q["identified_plan_units"] == 1200 and q["model_evaluated_plan_units"] == 1200 and q["unidentified_lines"] == 0
    m = body["modelled"]
    assert m["operator_plan"]["costs"] and m["zaad"]["costs"] and m["cost_difference_plan_minus_zaad"] is not None and m["worlds"] >= 1
    assert "simulated, not observed" in m["basis"] and body["realized_value"]["available"] is False and body["executable_purchase_order"] is False
    assert body["lines"][0]["fidelity"] == "EXACT" and body["lines"][0]["source"] == f"src_{SKU}"
    stored = cl.get(f"/api/zaad/shadow/comparisons/{body['comparison_id']}").json()
    assert stored["plan_hash"] == plan["content_hash"] and stored["request_hash"] == body["recommendation"]["information_hash"] and stored["status"] == "DONE"
    assert stored["result"]["contract"]["readiness"] == "READY" and stored["recommendation_source"] == "SYNC"
    # the comparison is reproducible: same plan, same request, same modelled figures
    second = cl.post(f"/api/zaad/shadow/plans/{plan['plan_id']}/compare", params={"horizon": 8, "max_solve_seconds": 5}).json()
    assert second["modelled"]["operator_plan"]["costs"] == m["operator_plan"]["costs"] and second["recommendation"]["information_hash"] == body["recommendation"]["information_hash"]


def test_incomplete_identity_and_superseded_versions_are_conditional(vault):
    cl = _client(vault)
    anonymous = cl.post("/api/zaad/shadow/plans", json={"as_of": "2025-09-08T00:00:00Z", "provenance": "OPERATOR_UPLOADED",
                                                         "lines": [{"sku": SKU, "quantity": 500}]}).json()         # no supplier on the line
    out = cl.post(f"/api/zaad/shadow/plans/{anonymous['plan_id']}/compare", params={"horizon": 8, "max_solve_seconds": 5}).json()
    # the sample sources SKU-0001 from one supplier, so the line is evaluated through that sole source but its identity is not established
    assert out["contract"]["readiness"] == "CONDITIONAL" and out["contract"]["comparator"]["fidelity"] == "INCOMPLETE"
    assert out["contract"]["permissions"]["can_claim_shadow_difference"] is False and out["quantities"]["unidentified_lines"] == 1
    corrected = cl.post("/api/zaad/shadow/plans", json={"as_of": "2025-09-08T00:00:00Z", "provenance": "OPERATOR_UPLOADED", "supersedes": anonymous["plan_id"],
                                                         "lines": [{"sku": SKU, "supplier_id": vault.execute("SELECT supplier_id FROM stg_fmcg_skus WHERE sku = ?", [SKU]).fetchone()[0], "quantity": 500}]}).json()
    assert corrected["version"] == 2
    old = cl.post(f"/api/zaad/shadow/plans/{anonymous['plan_id']}/compare", params={"horizon": 8, "max_solve_seconds": 5}).json()
    assert old["contract"]["readiness"] == "CONDITIONAL" and any("supersedes" in r for r in old["contract"]["caveats"])
    # a correction without naming the version it replaces is refused at the API
    refused = cl.post("/api/zaad/shadow/plans", json={"as_of": "2025-09-08T00:00:00Z", "provenance": "OPERATOR_UPLOADED", "lines": [{"sku": SKU, "quantity": 501}]})
    assert refused.status_code == 422 and "supersedes" in refused.text


def test_sync_and_job_reports_carry_the_same_provenance(vault):
    req, build = build_request(vault, OPERATOR, as_of=datetime(2025, 9, 1, tzinfo=timezone.utc), horizon=8, skus=[SKU])
    from_job = {"status": "RETAIN_INCUMBENT", "selected_policy": "operator_rule:replace_sold", "as_of": req.as_of.isoformat(),
                "decision_reference": C.decision_reference(req), "comparison": C.plan_comparison(req, status="RETAIN_INCUMBENT", selected_policy="operator_rule:replace_sold")}
    assert from_job["decision_reference"]["provenance"] == "RULE_IN_REQUEST"                       # what an asynchronous job can know on its own
    refined = zaad_shadow.refine_report(from_job, rule_provenance=build["incumbent_rule"]["provenance"], req=req)
    sync = C.decision_reference(req, rule_provenance=build["incumbent_rule"]["provenance"])
    assert refined["decision_reference"] == sync and refined["decision_reference"]["provenance"] == "INFERRED_FROM_HISTORY"
    assert refined["comparison"]["decision_reference"]["fidelity"] == "RECONSTRUCTED" and refined["comparison"]["mode"] == "PLAN_MODE"


def test_a_plan_captured_after_the_recommendation_cannot_be_its_baseline(vault):
    origin = datetime(2025, 9, 22, tzinfo=timezone.utc)
    plan = OP.capture_plan(vault, OPERATOR, as_of=origin, lines=[{"sku": SKU, "supplier_id": "SUP-001", "quantity": 10}],
                           provenance="OPERATOR_SUBMITTED", captured_by="b")
    req, _ = build_request(vault, OPERATOR, as_of=origin, horizon=8, skus=[SKU])
    mapping = OP.map_plan_to_request(plan, req)
    captured_at = datetime.fromisoformat(plan["captured_at"]).replace(tzinfo=None)
    before = OP.shadow_evidence(plan, mapping, req=req, exposed_at=captured_at - timedelta(seconds=1), latest_version=plan["version"], exposure_basis="JOB_FINISHED")
    assert C.shadow_readiness(before)["readiness"] == "NOT_READY_FOR_THIS_DECISION"
    after = OP.shadow_evidence(plan, mapping, req=req, exposed_at=captured_at + timedelta(seconds=1), latest_version=plan["version"], exposure_basis="JOB_FINISHED")
    assert C.shadow_readiness(after)["readiness"] == "READY"
    unverified = OP.shadow_evidence(plan, mapping, req=req, exposed_at=captured_at + timedelta(seconds=1), latest_version=plan["version"])
    assert C.shadow_readiness(unverified)["readiness"] == "CONDITIONAL"


class FakeStore:
    """A job store with finished planning jobs and their reports, for the baseline_job_id path."""

    def __init__(self, jobs: dict[str, dict]):
        self.jobs = jobs

    def list(self, operator, limit=50, purpose=None):
        return [{"id": k, "status": v["status"], "finished_at": v.get("finished_at")} for k, v in self.jobs.items()]

    def get(self, identity, operator):
        if identity not in self.jobs:
            raise KeyError(identity)
        return self.jobs[identity]

    def earliest_done_for_origin(self, operator, as_of):
        done = [(i, j) for i, j in self.jobs.items() if j.get("status") == "DONE" and j.get("finished_at")]
        hits = sorted((datetime.fromisoformat(j["finished_at"]), i) for i, j in done if j.get("report") and datetime.fromisoformat(j["report"]["as_of"]) == as_of)
        return {"id": hits[0][1] if hits else None, "finished_at": hits[0][0] if hits else None, "scanned": len(done), "unreadable": 0}


def test_job_path_requires_the_same_planning_problem_and_records_first_exposure(vault, monkeypatch):
    from api.routers import zaad_full
    from zaad.full.planner import plan as run_planner
    cl = _client(vault)
    origin = datetime(2025, 9, 15, tzinfo=timezone.utc)
    supplier = vault.execute("SELECT supplier_id FROM stg_fmcg_skus WHERE sku = ?", [SKU]).fetchone()[0]
    # 1. the operator captures first
    captured = cl.post("/api/zaad/shadow/plans", json={"as_of": origin.isoformat(), "provenance": "OPERATOR_SUBMITTED", "lines": [{"sku": SKU, "supplier_id": supplier, "quantity": 960}]}).json()      # a case multiple: scorable as recorded
    # 2. ZAAD's recommendation for the same planning problem finishes afterwards, as a job
    req, _ = build_request(vault, OPERATOR, as_of=origin, horizon=8, skus=[SKU], max_solve_seconds=5.)
    report = run_planner(req)
    finished = datetime.now(timezone.utc)                     # the job finished now: after the capture, before any correction
    jobs = {"job_ok": {"status": "DONE", "report": report, "finished_at": finished.isoformat(), "created_at": finished.isoformat()},
            "job_other_origin": {"status": "DONE", "report": {**report, "as_of": "2025-09-08T00:00:00+00:00"}, "finished_at": finished.isoformat()},
            "job_no_identity": {"status": "DONE", "report": {k: v for k, v in report.items() if k != "information_hash"}, "finished_at": finished.isoformat()},
            "job_running": {"status": "RUNNING", "report": None}}
    monkeypatch.setattr(zaad_full, "runner", lambda: SimpleNamespace(store=FakeStore(jobs), try_lease=lambda: True, release_lease=lambda: None))
    params = {"horizon": 8, "max_solve_seconds": 5, "skus": SKU, "baseline_job_id": "job_ok"}
    ok = cl.post(f"/api/zaad/shadow/plans/{captured['plan_id']}/compare", params=params)
    assert ok.status_code == 201, ok.text
    body = ok.json()
    assert body["exposure"]["basis"] == "JOB_FINISHED" and body["contract"]["readiness"] == "READY" and body["contract"]["permissions"]["can_claim_shadow_difference"] is True, body["contract"]["caveats"]
    assert body["recommendation"]["information_hash"] == report["information_hash"] and body["recommendation"]["decision_reference"]["provenance"] == "INFERRED_FROM_HISTORY"
    # a different planning problem is refused, whatever matched
    for change, code in (({"horizon": 12}, "request_mismatch"), ({"service_target": 0.9}, "request_mismatch"), ({"skus": f"{SKU},SKU-0002"}, "request_mismatch"),
                         ({"max_solve_seconds": 10}, "request_mismatch"), ({"baseline_job_id": "job_other_origin"}, "origin_mismatch"),
                         ({"baseline_job_id": "job_no_identity"}, "request_identity_missing"), ({"baseline_job_id": "job_running"}, "job_not_done")):
        r = cl.post(f"/api/zaad/shadow/plans/{captured['plan_id']}/compare", params={**params, **change})
        assert r.status_code == 409 and r.json()["detail"]["code"] == code, (change, r.text)
    assert cl.post(f"/api/zaad/shadow/plans/{captured['plan_id']}/compare", params={**params, "baseline_job_id": "job_missing"}).status_code == 404
    # a changed workspace state (a new recorded order before the origin) is a different planning problem
    vault.execute("BEGIN")
    vault.execute("INSERT INTO stg_fmcg_purchase_orders (po_id, po_date, supplier_id, sku, qty_ordered, unit_cost) VALUES ('H3B-STATE', DATE '2025-09-08', ?, ?, 10, 1.0)", [supplier, SKU])
    try:
        changed = cl.post(f"/api/zaad/shadow/plans/{captured['plan_id']}/compare", params=params)
        assert changed.status_code == 409 and changed.json()["detail"]["code"] == "request_mismatch"
    finally:
        vault.execute("ROLLBACK")
    # 3. a correction captured AFTER the recommendation was exposed cannot be its baseline, and exposure never moves later
    time.sleep(0.05)
    later = cl.post("/api/zaad/shadow/plans", json={"as_of": origin.isoformat(), "provenance": "OPERATOR_SUBMITTED", "supersedes": captured["plan_id"],
                                                     "lines": [{"sku": SKU, "supplier_id": supplier, "quantity": 984}]}).json()
    assert later["version"] == 2
    after = cl.post(f"/api/zaad/shadow/plans/{later['plan_id']}/compare", params=params).json()
    assert after["contract"]["readiness"] == "NOT_READY_FOR_THIS_DECISION" and any("at or after" in r for r in after["contract"]["caveats"])
    again = cl.post(f"/api/zaad/shadow/plans/{captured['plan_id']}/compare", params=params).json()           # the superseded v1, compared again
    assert again["exposure"]["exposed_at"] == body["exposure"]["exposed_at"] and again["contract"]["readiness"] == "CONDITIONAL"      # superseded, exposure unchanged
    # 4. a synchronous comparison for an origin that already has a finished job takes that job's finish as the exposure
    sync = cl.post(f"/api/zaad/shadow/plans/{later['plan_id']}/compare", params={"horizon": 8, "max_solve_seconds": 5}).json()
    assert sync["exposure"]["basis"] == "JOB_FINISHED" and sync["contract"]["readiness"] == "NOT_READY_FOR_THIS_DECISION"


def test_a_plan_the_settlement_cannot_score_as_recorded_gets_no_claim(vault):
    cl = _client(vault)
    supplier = vault.execute("SELECT supplier_id FROM stg_fmcg_skus WHERE sku = ?", [SKU]).fetchone()[0]
    plan = cl.post("/api/zaad/shadow/plans", json={"as_of": "2025-09-29T00:00:00Z", "provenance": "OPERATOR_SUBMITTED",
                                                    "lines": [{"sku": SKU, "supplier_id": supplier, "quantity": 900}]}).json()    # not a multiple of the declared case (24)
    out = cl.post(f"/api/zaad/shadow/plans/{plan['plan_id']}/compare", params={"horizon": 8, "max_solve_seconds": 5}).json()
    assert out["contract"]["readiness"] == "CONDITIONAL" and out["contract"]["permissions"]["can_claim_shadow_difference"] is False
    assert any("could not score the plan" in r for r in out["contract"]["caveats"]) and out["modelled"]["operator_plan"]["costs"] is None
    assert out["modelled"]["cost_difference_plan_minus_zaad"] is None and out["quantities"]["recorded_plan_units"] == 900
