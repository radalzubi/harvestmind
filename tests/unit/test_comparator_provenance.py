"""Comparator provenance and claim gating (HARDENING V1, H3a).

A decision reference is what the planner compares against internally; an evidence comparator is what ZAAD may
compare itself against in front of the operator. The tests prove the vocabulary, the exact mapping of recorded
historical actions to request sources by business key, the transformation / coverage rules, and the claim
permissions each mode grants."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from types import SimpleNamespace

import duckdb
import pandas as pd
import pytest

from api.routers.intake import load_fmcg_sample_into
from api.routers.zaad_history import realized_value
from scripts.setup_db import setup_db
from zaad.full import comparator as C
from zaad.full import historical as H
from zaad.full.workspace import build_request

ORIGIN = pd.Timestamp("2025-09-01")


def _src(id_: str, sku: str, supplier: str, destination: str = "main"):
    return SimpleNamespace(id=id_, sku=sku, supplier=supplier, destination=destination)


def _pos(*rows):
    return pd.DataFrame([{"po_id": r[0], "po_date": r[1], "supplier_id": r[2], "sku": r[3], "qty_ordered": r[4], "unit_cost": r[5] if len(r) > 5 else 2.0,
                          "destination_id": r[6] if len(r) > 6 else "MAIN"} for r in rows])


def _map(pos, sources, network=False, reviews=4):
    return C.map_historical_actions(pos, sources, origin=ORIGIN, period_days=7, reviews=reviews, network=network)


# ── A: an exact historical action ──
def test_a_exact_historical_action_maps_by_business_key():
    out = _map(_pos(("PO-1", "2025-09-02", "A", "X", 100.)), [_src("src_X", "X", "A")])
    line = out.lines[0]
    assert line.source == "src_X" and line.fidelity == C.EXACT and out.by_review[0] == {"src_X": 100.}
    cov = out.coverage(4)
    assert cov["lines_observed"] == cov["lines_exact"] == 1 and cov["exact_quantity_share"] == 1.0 and cov["exact_value_share"] == 1.0
    cmp = C.historical_comparison(cov, transformed_lines=0, settlement_shares=None, rule_provenance="INFERRED_FROM_HISTORY", reviews_completed=4)
    assert cmp["comparator"]["type"] == C.ACTUAL_HISTORICAL_ACTION and cmp["comparator"]["fidelity"] == C.EXACT and cmp["claim_class"] == C.HISTORICAL_COUNTERFACTUAL_COMPARISON


# ── B: the wrong-supplier trap ──
def test_b_a_po_from_supplier_b_never_maps_to_supplier_a():
    sources = [_src("src_X", "X", "A"), _src("src_X__B", "X", "B")]
    out = _map(_pos(("PO-1", "2025-09-02", "B", "X", 100.), ("PO-2", "2025-09-03", "A", "X", 40.)), sources)
    assert {ln.po_id: ln.source for ln in out.lines} == {"PO-1": "src_X__B", "PO-2": "src_X"} and all(ln.fidelity == C.EXACT for ln in out.lines)
    assert out.by_review[0] == {"src_X__B": 100., "src_X": 40.}
    # a supplier the request does not source the SKU from is never mapped to another approved supplier
    out = _map(_pos(("PO-3", "2025-09-02", "Z", "X", 100.)), sources)
    assert out.lines[0].source is None and out.lines[0].fidelity == C.INCOMPLETE and "no source of X is supplied by Z" in out.lines[0].reason
    assert out.by_review[0] == {}


def test_b_sample_vault_po_from_an_alternate_supplier_lands_on_that_supplier_only():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    load_fmcg_sample_into(conn, seed=7, archetype="A_stable")
    sku = "SKU-0001"
    conn.execute("INSERT INTO stg_fmcg_suppliers (supplier_id) VALUES ('SUP-ALT')")
    conn.execute("INSERT INTO stg_fmcg_sources (sku, supplier_id, approved, unit_cost, capacity_per_week, lead_time_promised_weeks, moq_units, units_per_case, provenance) "
                 "VALUES (?, 'SUP-ALT', TRUE, 1.0, 100000, 2, 1, 1, 'test')", [sku])
    conn.execute("INSERT INTO stg_fmcg_purchase_orders (po_id, po_date, supplier_id, sku, qty_ordered, unit_cost) VALUES ('H3A-B', DATE '2025-09-03', 'SUP-ALT', ?, 103, 1.0)", [sku])
    req, _ = build_request(conn, "op", as_of=datetime(2025, 9, 1, tzinfo=timezone.utc), horizon=8, skus=[sku], sourcing=True)
    actions = H.historical_actions(conn, req, 1)
    by_po = {ln.po_id: ln for ln in actions.lines}
    assert by_po["H3A-B"].source == f"src_{sku}__SUP-ALT" and by_po["H3A-B"].fidelity == C.EXACT
    primary_lines = [ln for ln in actions.lines if ln.po_id != "H3A-B"]
    assert primary_lines and all(ln.source == f"src_{sku}" and ln.sku == sku for ln in primary_lines)       # the primary supplier's own orders stay on the primary source
    assert actions.out_of_scope > 0 and actions.coverage(1)["lines_incomplete"] == 0            # other SKUs' orders are out of scope, not incomplete comparators
    assert actions.by_review[0][f"src_{sku}__SUP-ALT"] == 103.
    conn.close()


# ── C: an ambiguous source ──
def test_c_a_line_without_supplier_identity_is_incomplete_and_cannot_claim():
    two = [_src("src_X", "X", "A"), _src("src_X__B", "X", "B")]
    out = _map(_pos(("PO-1", "2025-09-02", None, "X", 100.)), two)
    assert out.lines[0].source is None and out.lines[0].fidelity == C.INCOMPLETE and "no supplier identity" in out.lines[0].reason and out.by_review[0] == {}
    one = [_src("src_X", "X", "A")]
    out = _map(_pos(("PO-1", "2025-09-02", None, "X", 100.)), one)
    assert out.lines[0].source == "src_X" and out.lines[0].fidelity == C.INCOMPLETE              # evaluated through the only source, but not exact
    cmp = C.historical_comparison(out.coverage(4), transformed_lines=0, settlement_shares=None, rule_provenance=None, reviews_completed=4)
    assert cmp["comparator"]["fidelity"] == C.INCOMPLETE and cmp["readiness"] == C.CONDITIONAL and cmp["claim_class"] == C.MODEL_COMPARISON
    assert cmp["permissions"]["can_claim_against_operator"] is False and cmp["permissions"]["can_claim_historical_counterfactual_difference"] is False
    # a network request needs the destination too
    net = [_src("src_X@DC", "X", "A", "DC"), _src("src_X@NORTH", "X", "A", "NORTH")]
    out = _map(_pos(("PO-1", "2025-09-02", "A", "X", 100., 2.0, "NORTH"), ("PO-2", "2025-09-02", "A", "X", 50., 2.0, None)), net, network=True)
    assert {ln.po_id: (ln.source, ln.fidelity) for ln in out.lines} == {"PO-1": ("src_X@NORTH", C.EXACT), "PO-2": (None, C.INCOMPLETE)}


# ── D / E: conformance (quantity rounding, capacity) is a transformation ──
def test_d_e_a_transformed_quantity_keeps_the_observed_one_and_loses_exactness():
    source = SimpleNamespace(multiple=0.0, case_multiple=24.0, pallet_multiple=0.0, transport_multiple=0.0, maximum=10_000., capacity_by_period=[10_000.], minimum=0.)
    settled, note = H._conform(source, 103.)
    assert settled == 96. and "rounded" in note
    capped = SimpleNamespace(multiple=0.0, case_multiple=0.0, pallet_multiple=0.0, transport_multiple=0.0, maximum=80., capacity_by_period=[80.], minimum=0.)
    settled, note = H._conform(capped, 103.)
    assert settled == 80. and "capped" in note
    cov = {"lines_observed": 2, "lines_exact": 2, "lines_incomplete": 0, "lines_unmapped": 0, "exact_quantity_share": 1.0, "exact_value_share": 1.0, "value_share_basis": "x", "incomplete_reasons": []}
    cmp = C.historical_comparison(cov, transformed_lines=2, settlement_shares=None, rule_provenance="INFERRED_FROM_HISTORY", reviews_completed=4)
    assert cmp["comparator"]["fidelity"] == C.TRANSFORMED and cmp["comparator"]["transformed"] is True and cmp["claim_class"] == C.MODEL_COMPARISON
    assert cmp["permissions"]["can_claim_against_operator"] is False and "model-adjusted" in cmp["comparator"]["label"]
    assert C.actual_action_label(cmp) == "a model-adjusted version of the recorded historical orders"


# ── F / G: a rule is a policy, declared or reconstructed, never a plan ──
def test_f_g_rules_are_reconstructed_policy_whether_inferred_or_declared():
    inferred = C.decision_reference(SimpleNamespace(incumbent_rule="replace_sold", incumbent_orders=()), rule_provenance="INFERRED_FROM_HISTORY")
    declared = C.decision_reference(SimpleNamespace(incumbent_rule="reorder_point", incumbent_orders=()), rule_provenance="CUSTOMER_PROVIDED")
    assert inferred["type"] == declared["type"] == C.RECONSTRUCTED_POLICY and inferred["fidelity"] == C.RECONSTRUCTED and declared["fidelity"] == C.DECLARED
    assert inferred["label"] == "the reconstructed historical rule" and declared["label"] == "the operator-declared rule"
    assert C.ACTUAL_OPERATOR_PLAN not in (inferred["type"], declared["type"])
    for ref in (inferred, declared):
        assert "current policy" not in json.dumps(ref).lower() and "would have" not in json.dumps(ref).lower()
    unknown = C.decision_reference(SimpleNamespace(incumbent_rule="replace_sold", incumbent_orders=()))
    assert unknown["fidelity"] == C.RECONSTRUCTED and unknown["provenance"] == "RULE_IN_REQUEST" and "build report" in unknown["provenance_note"]
    orders = C.decision_reference(SimpleNamespace(incumbent_rule=None, incumbent_orders=(1,)))
    assert orders["type"] == C.RECONSTRUCTED_POLICY and orders["fidelity"] == C.DECLARED and "not a captured operator plan" in orders["label"]


# ── H / I: PLAN_MODE ──
def test_h_i_plan_mode_recommends_and_compares_against_the_model_only():
    proxy = SimpleNamespace(incumbent_rule=None, incumbent_orders=())
    cmp = C.plan_comparison(proxy, status="PENDING_REVIEW", selected_policy="joint_recovery")
    assert cmp["mode"] == C.PLAN_MODE and cmp["permissions"]["can_recommend"] is True and cmp["decision_reference"]["type"] == C.SYSTEM_BASELINE
    assert cmp["permissions"]["can_claim_against_operator"] is False and cmp["permissions"]["can_claim_realized_value"] is False
    rule = SimpleNamespace(incumbent_rule="replace_sold", incumbent_orders=())
    cmp = C.plan_comparison(rule, status="RETAIN_INCUMBENT", selected_policy="operator_rule:replace_sold", rule_provenance="INFERRED_FROM_HISTORY")
    assert cmp["claim_class"] == C.MODEL_COMPARISON and cmp["permissions"]["can_compare"] is True and cmp["permissions"]["can_claim_against_operator"] is False
    assert cmp["meaning"] == "ZAAD retained its decision reference" and cmp["comparator"]["type"] == C.RECONSTRUCTED_POLICY
    text = json.dumps(cmp).lower()
    assert "keep your current plan" not in text and "saves" not in text and "what you would have done" not in text.replace("better than what you would have done", "")
    abstain = C.plan_comparison(rule, status="ABSTAIN", selected_policy=None)
    assert abstain["readiness"] == C.CANNOT_COMPARE and abstain["permissions"]["can_compare"] is False and abstain["comparator"]["type"] == C.NONE


# ── J: shadow comparison without an operator plan ──
def test_j_shadow_comparison_is_not_ready_without_a_captured_operator_plan():
    shadow = C.shadow_readiness(None)
    assert shadow["readiness"] == C.NOT_READY_FOR_THIS_DECISION and shadow["requires"] == C.ACTUAL_OPERATOR_PLAN and shadow["claim_class"] is None
    with pytest.raises(NotImplementedError):
        C.plan_comparison(SimpleNamespace(incumbent_rule="x", incumbent_orders=()), status="PENDING_REVIEW", selected_policy="p", actual_operator_plan={"orders": []})
    with pytest.raises(NotImplementedError):
        C.shadow_readiness({"orders": []})


# ── K / L / M: historical exact vs transformed, and the system baseline ──
def test_k_l_m_claim_classes_follow_fidelity_and_baselines_stay_generic():
    cov = {"lines_observed": 5, "lines_exact": 5, "lines_incomplete": 0, "lines_unmapped": 0, "exact_quantity_share": 1.0, "exact_value_share": 1.0, "value_share_basis": "x", "incomplete_reasons": []}
    exact = C.historical_comparison(cov, transformed_lines=0, settlement_shares={"zaad_orders": 1}, rule_provenance="INFERRED_FROM_HISTORY", reviews_completed=4)
    assert exact["claim_class"] == C.HISTORICAL_COUNTERFACTUAL_COMPARISON and exact["permissions"]["can_claim_historical_counterfactual_difference"] is True
    assert exact["permissions"]["can_claim_realized_value"] is False and "counterfactual" in exact["caveats"][0]
    transformed = C.historical_comparison(cov, transformed_lines=1, settlement_shares=None, rule_provenance="INFERRED_FROM_HISTORY", reviews_completed=4)
    assert transformed["claim_class"] == C.MODEL_COMPARISON and transformed["permissions"]["can_claim_against_operator"] is False and transformed["comparator"]["transformed"] is True
    none = C.historical_comparison({"lines_observed": 0, "lines_exact": 0, "lines_incomplete": 0}, transformed_lines=0, settlement_shares=None, rule_provenance=None, reviews_completed=4)
    assert none["comparator"]["type"] == C.NONE and none["readiness"] == C.CANNOT_COMPARE and none["permissions"]["can_compare"] is False
    baseline = C.decision_reference(SimpleNamespace(incumbent_rule=None, incumbent_orders=()))
    assert baseline["type"] == C.SYSTEM_BASELINE and "operator" not in baseline["label"] and "plan" not in baseline["label"] and "engineering benchmark" in baseline["description"]
    assert exact["legs"]["rule"]["comparator_type"] == C.RECONSTRUCTED_POLICY and exact["legs"]["actual"]["fidelity"] == C.EXACT


# ── N: the realized-value contract is untouched ──
def test_n_realized_value_contract_is_unchanged():
    none = realized_value([])
    assert none == {"realized_outcome": False, "realized_savings": [], "note": "No outcome has been observed for this action yet."}
    observed = realized_value([{"metric": "purchase_cost", "value": 90., "observed_at": "2026-01-01", "comparator_value": None, "comparator_basis": None}])
    assert observed["realized_outcome"] is True and observed["realized_savings"] == [] and "not attributed to ZAAD" in observed["note"]
    with_comparator = realized_value([{"metric": "purchase_cost", "value": 90., "observed_at": "2026-01-01", "comparator_value": 100., "comparator_basis": "quoted price", "unit": "money"}])
    assert with_comparator["realized_savings"][0]["difference"] == 10. and with_comparator["realized_savings"][0]["basis"] == "quoted price"
    assert C.REALIZED_VALUE in C.CLAIM_CLASSES


# ── O: physical row order never changes the mapping ──
def test_o_mapping_is_deterministic_under_physical_reorder():
    sources = [_src("src_X", "X", "A"), _src("src_X__B", "X", "B"), _src("src_Y", "Y", "A")]
    rows = [("PO-3", "2025-09-02", "B", "X", 10.), ("PO-1", "2025-09-02", "A", "X", 20.), ("PO-2", "2025-09-09", "A", "Y", 30.), ("PO-4", "2025-09-02", None, "Y", 5.)]
    a = _map(_pos(*rows), sources)
    b = _map(_pos(*rows[::-1]), sources[::-1])
    assert [ln.as_dict() for ln in a.lines] == [ln.as_dict() for ln in b.lines] and a.by_review == b.by_review and a.coverage(4) == b.coverage(4)
    assert [ln.po_id for ln in a.lines] == ["PO-1", "PO-3", "PO-4", "PO-2"]              # canonical (po_date, po_id) order, not physical order


def test_vocabulary_is_closed():
    assert set(C.COMPARATOR_TYPES) == {"ACTUAL_HISTORICAL_ACTION", "ACTUAL_OPERATOR_PLAN", "RECONSTRUCTED_POLICY", "SYSTEM_BASELINE", "NONE"}
    assert set(C.FIDELITIES) == {"EXACT", "DECLARED", "RECONSTRUCTED", "TRANSFORMED", "INCOMPLETE", "NOT_AVAILABLE"}
    assert set(C.CLAIM_CLASSES) == {"PLAN_ONLY", "MODEL_COMPARISON", "HISTORICAL_COUNTERFACTUAL_COMPARISON", "SHADOW_COMPARISON", "REALIZED_VALUE"}
    assert date(2025, 9, 1) == ORIGIN.date()
