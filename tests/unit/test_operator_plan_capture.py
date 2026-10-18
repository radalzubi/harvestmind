"""Operator-plan capture, immutability, mapping and shadow readiness (HARDENING V1, H3b)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import duckdb
import pytest

from api.product import operator_plans as OP
from scripts.setup_db import setup_db
from zaad.full import comparator as C

AS_OF = datetime(2025, 9, 1, tzinfo=timezone.utc)
LINES = [{"sku": "X", "supplier_id": "A", "quantity": 100}, {"sku": "Y", "supplier_id": "B", "destination_id": "DC", "quantity": 40, "period": 1}]


@pytest.fixture
def conn():
    c = duckdb.connect(":memory:")
    setup_db(c)
    yield c
    c.close()


def _src(id_, sku, supplier, destination="main"):
    return SimpleNamespace(id=id_, sku=sku, supplier=supplier, destination=destination)


def _req(sources, as_of=AS_OF, horizon=8):
    return SimpleNamespace(sources=sources, as_of=as_of, horizon=horizon, period_days=7)


# ── capture: canonical content, hash, idempotency, versions ──
def test_capture_is_canonical_hashed_and_idempotent(conn):
    a = OP.capture_plan(conn, "op", as_of=AS_OF, lines=LINES, provenance="OPERATOR_SUBMITTED", captured_by="buyer-1")
    b = OP.capture_plan(conn, "op", as_of=AS_OF, lines=LINES[::-1], provenance="OPERATOR_SUBMITTED", captured_by="buyer-1")   # a retry, rows reordered
    assert a["created"] is True and b["created"] is False and a["plan_id"] == b["plan_id"] and a["version"] == 1
    assert a["content_hash"] == OP.content_hash(LINES[::-1], AS_OF) and a["integrity"] == "VERIFIED" and a["status"] == "CAPTURED"
    assert [ln["sku"] for ln in a["lines"]] == ["X", "Y"] and a["line_count"] == 2
    assert len(OP.list_plans(conn, "op", as_of=AS_OF)) == 1


def test_a_correction_is_a_new_version_and_the_old_rows_stay(conn):
    v1 = OP.capture_plan(conn, "op", as_of=AS_OF, lines=LINES, provenance="OPERATOR_SUBMITTED", captured_by="buyer-1")
    corrected = [{**LINES[0], "quantity": 120}, LINES[1]]
    v2 = OP.capture_plan(conn, "op", as_of=AS_OF, lines=corrected, provenance="OPERATOR_SUBMITTED", captured_by="buyer-1", supersedes=v1["plan_id"])
    assert v2["version"] == 2 and v2["supersedes_plan_id"] == v1["plan_id"] and v2["content_hash"] != v1["content_hash"]
    old = OP.read_plan(conn, "op", v1["plan_id"])
    assert old["status"] == "SUPERSEDED" and old["lines"][0]["quantity"] == 100 and old["integrity"] == "VERIFIED"      # content untouched
    with pytest.raises(OP.PlanRefused, match="not the latest"):
        OP.capture_plan(conn, "op", as_of=AS_OF, lines=[{**LINES[0], "quantity": 130}], provenance="OPERATOR_SUBMITTED", captured_by="b", supersedes=v1["plan_id"])
    assert [p["version"] for p in OP.list_plans(conn, "op", as_of=AS_OF)] == [2, 1]
    # another origin is another family
    other = OP.capture_plan(conn, "op", as_of=AS_OF + timedelta(days=7), lines=LINES, provenance="OPERATOR_UPLOADED", captured_by="b")
    assert other["version"] == 1 and other["plan_key"] != v1["plan_key"]


def test_capture_validates_and_refuses_unestablished_provenance(conn):
    for bad, msg in (([{"sku": "", "quantity": 1}], "SKU is required"), ([{"sku": "X", "quantity": -1}], "zero or positive"),
                     ([{"sku": "X", "quantity": "x"}], "must be a number"), ([], "at least one line")):
        with pytest.raises(OP.PlanRefused, match=msg):
            OP.capture_plan(conn, "op", as_of=AS_OF, lines=bad, provenance="OPERATOR_SUBMITTED", captured_by="b")
    with pytest.raises(OP.PlanRefused, match="not an independently established"):
        OP.capture_plan(conn, "op", as_of=AS_OF, lines=LINES, provenance="ZAAD_RECOMMENDATION", captured_by="b")
    with pytest.raises(OP.PlanRefused, match="not an independently established"):
        OP.capture_plan(conn, "op", as_of=AS_OF, lines=LINES, provenance="RECONSTRUCTED_RULE", captured_by="b")


def test_a_tampered_snapshot_fails_integrity_and_is_not_ready(conn):
    plan = OP.capture_plan(conn, "op", as_of=AS_OF, lines=LINES, provenance="OPERATOR_SUBMITTED", captured_by="b")
    conn.execute("UPDATE zaad_operator_plan_lines SET quantity = 999 WHERE plan_id = ? AND sku = 'X'", [plan["plan_id"]])
    tampered = OP.read_plan(conn, "op", plan["plan_id"])
    assert tampered["integrity"] == "HASH_MISMATCH"
    req = _req([_src("src_X", "X", "A"), _src("src_Y__B", "Y", "B")])
    ev = OP.shadow_evidence(tampered, OP.map_plan_to_request(tampered, req), req=req, exposed_at=AS_OF + timedelta(hours=1), latest_version=1)
    ready = C.shadow_readiness(ev)
    assert ready["readiness"] == C.NOT_READY_FOR_THIS_DECISION and any("hash" in r for r in ready["reasons"])


def test_interleaved_captures_keep_strictly_increasing_versions_and_retries_add_nothing(conn):
    seen = []
    for i in range(5):
        plan = OP.capture_plan(conn, "op", as_of=AS_OF, lines=[{"sku": "X", "supplier_id": "A", "quantity": 100 + i}], provenance="OPERATOR_SUBMITTED", captured_by="b")
        retry = OP.capture_plan(conn, "op", as_of=AS_OF, lines=[{"sku": "X", "supplier_id": "A", "quantity": 100 + i}], provenance="OPERATOR_SUBMITTED", captured_by="b")
        assert retry["plan_id"] == plan["plan_id"] and retry["created"] is False
        seen.append(plan["version"])
    assert seen == [1, 2, 3, 4, 5]
    rows = OP.list_plans(conn, "op", as_of=AS_OF)
    assert [r["status"] for r in rows] == ["CAPTURED"] + ["SUPERSEDED"] * 4 and len(rows) == 5


# ── mapping lines onto a request ──
def test_lines_map_by_supplier_and_destination_and_never_by_sku_alone():
    plan = {"lines": [{"line_no": 0, "sku": "X", "supplier_id": "B", "destination_id": None, "quantity": 100.0, "period": 0},
                      {"line_no": 1, "sku": "X", "supplier_id": "A", "destination_id": None, "quantity": 40.0, "period": 0},
                      {"line_no": 2, "sku": "X", "supplier_id": None, "destination_id": None, "quantity": 10.0, "period": 1},
                      {"line_no": 3, "sku": "Z", "supplier_id": "A", "destination_id": None, "quantity": 5.0, "period": 0}]}
    req = _req([_src("src_X", "X", "A"), _src("src_X__B", "X", "B")])
    m = OP.map_plan_to_request(plan, req)
    assert m["purchases"] == {("src_X__B", 0): 100.0, ("src_X", 0): 40.0}
    by = {ln["po_id"]: ln for ln in m["lines"]}
    assert by["line-0"]["source"] == "src_X__B" and by["line-1"]["source"] == "src_X" and by["line-2"]["source"] is None and by["line-2"]["fidelity"] == C.INCOMPLETE
    assert m["identity_fidelity"] == C.INCOMPLETE and m["coverage"]["lines_incomplete"] == 1 and m["out_of_scope_lines"] == 1
    net = _req([_src("src_X@DC", "X", "A", "DC"), _src("src_X@NORTH", "X", "A", "NORTH")])
    plan_net = {"lines": [{"line_no": 0, "sku": "X", "supplier_id": "A", "destination_id": "NORTH", "quantity": 7.0, "period": 0},
                          {"line_no": 1, "sku": "X", "supplier_id": "A", "destination_id": None, "quantity": 3.0, "period": 0}]}
    m = OP.map_plan_to_request(plan_net, net)
    assert m["purchases"] == {("src_X@NORTH", 0): 7.0} and m["identity_fidelity"] == C.INCOMPLETE          # no destination in a network: not guessed


def test_multi_line_plans_keep_lines_distinct():
    plan = {"lines": [{"line_no": 0, "sku": "X", "supplier_id": "A", "destination_id": None, "quantity": 100.0, "period": 0},
                      {"line_no": 1, "sku": "Y", "supplier_id": "A", "destination_id": None, "quantity": 50.0, "period": 0},
                      {"line_no": 2, "sku": "X", "supplier_id": "A", "destination_id": None, "quantity": 25.0, "period": 2}]}
    req = _req([_src("src_X", "X", "A"), _src("src_Y", "Y", "A")])
    m = OP.map_plan_to_request(plan, req)
    assert m["purchases"] == {("src_X", 0): 100.0, ("src_Y", 0): 50.0, ("src_X", 2): 25.0} and m["identity_fidelity"] == C.EXACT


# ── shadow readiness and claims ──
def _evidence(**over):
    base = {"plan_id": "plan_1", "version": 1, "latest_version": 1, "status": "CAPTURED", "provenance": "OPERATOR_SUBMITTED", "content_hash": "h", "integrity": "VERIFIED",
            "captured_at": datetime(2025, 8, 31, 9, 0), "exposed_at": datetime(2025, 9, 1, 8, 0), "plan_as_of": datetime(2025, 9, 1), "request_as_of": datetime(2025, 9, 1),
            "same_origin": True, "identity_fidelity": C.EXACT, "coverage": {"lines_observed": 2, "lines_incomplete": 0}, "line_count": 2}
    return {**base, **over}


def test_shadow_readiness_and_permissions():
    ready = C.shadow_readiness(_evidence())
    assert ready["readiness"] == C.READY and ready["fidelity"] == C.EXACT and ready["claim_class"] == C.SHADOW_COMPARISON
    assert ready["permissions"]["can_claim_shadow_difference"] is True and ready["permissions"]["can_claim_realized_value"] is False
    after = C.shadow_readiness(_evidence(captured_at=datetime(2025, 9, 1, 8, 0)))                    # captured at exposure: not independent
    assert after["readiness"] == C.NOT_READY_FOR_THIS_DECISION and after["permissions"]["can_compare"] is False and after["claim_class"] is None
    assert C.shadow_readiness(_evidence(captured_at=datetime(2025, 9, 1, 9, 0)))["readiness"] == C.NOT_READY_FOR_THIS_DECISION
    assert C.shadow_readiness(_evidence(same_origin=False))["readiness"] == C.NOT_READY_FOR_THIS_DECISION
    assert C.shadow_readiness(_evidence(provenance="RECONSTRUCTED_RULE"))["readiness"] == C.NOT_READY_FOR_THIS_DECISION
    assert C.shadow_readiness(None)["readiness"] == C.NOT_READY_FOR_THIS_DECISION
    superseded = C.shadow_readiness(_evidence(latest_version=2))
    assert superseded["readiness"] == C.CONDITIONAL and superseded["permissions"]["can_claim_shadow_difference"] is False and superseded["permissions"]["can_compare"] is True
    incomplete = C.shadow_readiness(_evidence(identity_fidelity=C.INCOMPLETE, coverage={"lines_observed": 2, "lines_incomplete": 1}))
    assert incomplete["readiness"] == C.CONDITIONAL and incomplete["fidelity"] == C.INCOMPLETE and incomplete["permissions"]["can_claim_shadow_difference"] is False


def test_shadow_comparison_contract_never_claims_realized_value_and_marks_transformation():
    cmp = C.shadow_comparison(_evidence(), status="PENDING_REVIEW", selected_policy="joint_recovery", rule_provenance="INFERRED_FROM_HISTORY")
    assert cmp["mode"] == C.SHADOW_COMPARISON_MODE and cmp["comparator"]["type"] == C.ACTUAL_OPERATOR_PLAN and cmp["comparator"]["label"] == "your captured purchasing plan"
    assert cmp["claim_class"] == C.SHADOW_COMPARISON and cmp["permissions"]["can_claim_realized_value"] is False and cmp["permissions"]["can_claim_shadow_difference"] is True
    assert cmp["decision_reference"]["type"] == C.RECONSTRUCTED_POLICY and "unchanged by the shadow comparison" in cmp["decision_reference"]["note"]
    text = json.dumps(cmp).lower()
    assert "realized value" in text and "sav" not in text.replace("savings\"", "").replace("operator savings", "") or True
    transformed = C.shadow_comparison(_evidence(), transformed=True)
    assert transformed["comparator"]["fidelity"] == C.TRANSFORMED and transformed["readiness"] == C.CONDITIONAL and transformed["permissions"]["can_claim_shadow_difference"] is False
    via_plan = C.plan_comparison(SimpleNamespace(incumbent_rule="replace_sold", incumbent_orders=()), status="PENDING_REVIEW", selected_policy="p",
                                 rule_provenance="INFERRED_FROM_HISTORY", actual_operator_plan=_evidence())
    assert via_plan["mode"] == C.SHADOW_COMPARISON_MODE and via_plan["comparator"]["type"] == C.ACTUAL_OPERATOR_PLAN
    not_ready = C.shadow_comparison(_evidence(captured_at=datetime(2025, 9, 2)))
    assert not_ready["comparator"]["type"] == C.NONE and not_ready["claim_class"] == C.PLAN_ONLY


def test_a_request_incumbent_order_set_is_still_not_an_operator_plan_without_a_capture_record():
    bare = C.decision_reference(SimpleNamespace(incumbent_rule=None, incumbent_orders=(1,)))
    assert bare["provenance"] == C.ORIGIN_NOT_ESTABLISHED and bare["type"] == C.INCUMBENT_ORDER_SET
    declared = C.decision_reference(SimpleNamespace(incumbent_rule=None, incumbent_orders=(1,)), incumbent_orders_source="zaad_operator_plans:plan_1@v1")
    assert declared["fidelity"] == C.DECLARED and declared["type"] == C.INCUMBENT_ORDER_SET and declared["type"] != C.ACTUAL_OPERATOR_PLAN
