"""Shadow comparison end to end on the SYNTHETIC sample (HARDENING V1, H3b): capture a plan, run ZAAD for the
plan's origin, settle both on the planner's worlds, store the comparison immutably."""
from __future__ import annotations

from datetime import datetime, timezone

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
    assert contract["mode"] == "SHADOW_COMPARISON_MODE" and contract["readiness"] == "READY" and contract["comparator"]["type"] == "ACTUAL_OPERATOR_PLAN"
    assert contract["comparator"]["fidelity"] == "EXACT" and contract["claim_class"] == "SHADOW_COMPARISON"
    assert contract["permissions"]["can_claim_shadow_difference"] is True and contract["permissions"]["can_claim_realized_value"] is False
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
    plan = OP.capture_plan(vault, OPERATOR, as_of=datetime(2025, 9, 1, tzinfo=timezone.utc), lines=[{"sku": SKU, "supplier_id": "SUP-001", "quantity": 10}],
                           provenance="OPERATOR_SUBMITTED", captured_by="b")
    req, _ = build_request(vault, OPERATOR, as_of=datetime(2025, 9, 1, tzinfo=timezone.utc), horizon=8, skus=[SKU])
    mapping = OP.map_plan_to_request(plan, req)
    before = OP.shadow_evidence(plan, mapping, req=req, exposed_at=datetime.fromisoformat(plan["captured_at"]).replace(tzinfo=None) - __import__("datetime").timedelta(seconds=1), latest_version=plan["version"])
    assert C.shadow_readiness(before)["readiness"] == "NOT_READY_FOR_THIS_DECISION"
    after = OP.shadow_evidence(plan, mapping, req=req, exposed_at=datetime.fromisoformat(plan["captured_at"]).replace(tzinfo=None) + __import__("datetime").timedelta(seconds=1), latest_version=plan["version"])
    assert C.shadow_readiness(after)["readiness"] in ("READY", "CONDITIONAL")
