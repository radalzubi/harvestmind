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
    cmp = C.historical_comparison(cov, transformed_groups=0, settlement_shares=None, rule_provenance="INFERRED_FROM_HISTORY", reviews_completed=4)
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
    cmp = C.historical_comparison(out.coverage(4), transformed_groups=0, settlement_shares=None, rule_provenance=None, reviews_completed=4)
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
    cmp = C.historical_comparison(cov, transformed_groups=2, settlement_shares=None, rule_provenance="INFERRED_FROM_HISTORY", reviews_completed=4)
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
    # correction C: a bare incumbent order set proves nothing about who wrote it
    orders = C.decision_reference(SimpleNamespace(incumbent_rule=None, incumbent_orders=(1,)))
    assert orders["type"] == C.INCUMBENT_ORDER_SET and orders["fidelity"] == C.NOT_AVAILABLE and orders["provenance"] == C.ORIGIN_NOT_ESTABLISHED
    assert "origin not established" in orders["label"] and "not a captured operator plan" in orders["label"]
    declared = C.decision_reference(SimpleNamespace(incumbent_rule=None, incumbent_orders=(1,)), incumbent_orders_source="stg_operator_plan:plan-7")
    assert declared["fidelity"] == C.DECLARED and declared["provenance"] == "stg_operator_plan:plan-7" and declared["type"] == C.INCUMBENT_ORDER_SET
    shadow_labelled = C.decision_reference(SimpleNamespace(incumbent_rule=None, incumbent_orders=(1,), evidence_label="OPERATOR-SHADOW"))
    assert shadow_labelled["provenance"] == C.ORIGIN_NOT_ESTABLISHED          # the legacy engine label is not evidence of a captured plan


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
    exact = C.historical_comparison(cov, transformed_groups=0, settlement_shares={"zaad_orders": 1}, rule_provenance="INFERRED_FROM_HISTORY", reviews_completed=4)
    assert exact["claim_class"] == C.HISTORICAL_COUNTERFACTUAL_COMPARISON and exact["permissions"]["can_claim_historical_counterfactual_difference"] is True
    assert exact["permissions"]["can_claim_realized_value"] is False and "counterfactual" in exact["caveats"][0]
    transformed = C.historical_comparison(cov, transformed_groups=1, settlement_shares=None, rule_provenance="INFERRED_FROM_HISTORY", reviews_completed=4)
    assert transformed["claim_class"] == C.MODEL_COMPARISON and transformed["permissions"]["can_claim_against_operator"] is False and transformed["comparator"]["transformed"] is True
    none = C.historical_comparison({"lines_observed": 0, "lines_exact": 0, "lines_incomplete": 0}, transformed_groups=0, settlement_shares=None, rule_provenance=None, reviews_completed=4)
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
    assert set(C.COMPARATOR_TYPES) == {"ACTUAL_HISTORICAL_ACTION", "ACTUAL_OPERATOR_PLAN", "RECONSTRUCTED_POLICY", "SYSTEM_BASELINE", "INCUMBENT_ORDER_SET", "NONE"}
    assert set(C.FIDELITIES) == {"EXACT", "DECLARED", "RECONSTRUCTED", "TRANSFORMED", "INCOMPLETE", "NOT_AVAILABLE"}
    assert set(C.CLAIM_CLASSES) == {"PLAN_ONLY", "MODEL_COMPARISON", "HISTORICAL_COUNTERFACTUAL_COMPARISON", "SHADOW_COMPARISON", "REALIZED_VALUE"}
    assert date(2025, 9, 1) == ORIGIN.date()


# ── correction A: supplier-exact historical truth ──
def _truth_vault(order):
    """Two suppliers of one SKU with different behaviour: A delivers 100% in 7 days, B delivers 50% in 28 days.
    Rows are inserted in the given order so the mapping can be proven order-independent."""
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    conn.execute("INSERT INTO stg_fmcg_skus (sku, supplier_id, unit_cost, unit_price, units_per_case, moq_units) VALUES ('X', 'A', 2.0, 4.0, 1, 1)")
    conn.execute("INSERT INTO stg_fmcg_suppliers (supplier_id) VALUES ('A'), ('B')")
    rows = []
    for w in range(60):
        day = date(2025, 1, 6) + pd.Timedelta(weeks=w).to_pytimedelta()
        rows.append(("PO-A-%02d" % w, day, "A", "X", 100.0, 2.0))
        rows.append(("PO-B-%02d" % w, day, "B", "X", 40.0, 2.0))
        conn.execute("INSERT INTO stg_fmcg_orders (order_id, customer_id, order_date, sku, qty_ordered) VALUES (?, 'C1', ?, 'X', 120)", ["SO-%02d" % w, day])
    for po_id, day, sup, sku, qty, cost in (rows if order == "forward" else rows[::-1]):
        conn.execute("INSERT INTO stg_fmcg_purchase_orders (po_id, po_date, supplier_id, sku, qty_ordered, unit_cost) VALUES (?, ?, ?, ?, ?, ?)", [po_id, day, sup, sku, qty, cost])
        received = qty if sup == "A" else qty * 0.5
        lead = 7 if sup == "A" else 28
        conn.execute("INSERT INTO stg_fmcg_receipts (po_id, receipt_date, sku, qty_received) VALUES (?, ?, ?, ?)", [po_id, day + pd.Timedelta(days=lead).to_pytimedelta(), sku, received])
    conn.execute("INSERT INTO stg_fmcg_sources (sku, supplier_id, approved, unit_cost, capacity_per_week, lead_time_promised_weeks, moq_units, units_per_case, provenance) VALUES ('X', 'B', TRUE, 2.0, 100000, 4, 1, 1, 'test')")
    # H2: an opening count that is the state at the origin and knowable before it
    conn.execute("INSERT INTO stg_fmcg_inventory (snapshot_date, sku, location_id, on_hand, in_transit, snapshot_basis, source_known_at) "
                 "VALUES (DATE '2025-08-31', 'X', 'MAIN', 300, 0, 'END_OF_DAY', TIMESTAMP '2025-08-31 23:59:59')")
    return conn


@pytest.mark.parametrize("order", ["forward", "reversed"])
def test_a_truth_uses_each_suppliers_own_observations_only(order):
    conn = _truth_vault(order)
    as_of = datetime(2025, 9, 1, tzinfo=timezone.utc)
    req, _ = build_request(conn, "op", as_of=as_of, horizon=8, skus=["X"], sourcing=True)
    src_a = next(s for s in req.sources if s.supplier == "A")
    src_b = next(s for s in req.sources if s.supplier == "B")
    world, prov = H.build_truth(conn, req, periods=8, seed=1)
    assert prov["source_identity"].startswith("a MEASURED cell is the exact source's own received order")
    for t in range(8):
        assert prov["supply"][f"{src_a.id}|{t}"] == "MEASURED" and prov["supply"][f"{src_b.id}|{t}"] == "MEASURED"
        assert prov["supply_actual_qty"][f"{src_a.id}|{t}"] == 100.0 and prov["supply_actual_qty"][f"{src_b.id}|{t}"] == 40.0
        assert world.fills[src_a.id, t] == 1.0 and world.fills[src_b.id, t] == 0.5
        assert world.arrival[src_a.id, t] == t + 1 and world.arrival[src_b.id, t] == t + 4            # 7 days -> 1 period, 28 days -> 4 periods
    conn.close()


def test_a_a_source_without_its_own_observation_is_never_measured_by_another_supplier():
    conn = _truth_vault("forward")
    conn.execute("DELETE FROM stg_fmcg_receipts WHERE po_id LIKE 'PO-B-%'")
    conn.execute("DELETE FROM stg_fmcg_purchase_orders WHERE po_id LIKE 'PO-B-%'")          # B never delivered anything
    as_of = datetime(2025, 9, 1, tzinfo=timezone.utc)
    req, _ = build_request(conn, "op", as_of=as_of, horizon=8, skus=["X"], sourcing=True)
    src_a = next(s for s in req.sources if s.supplier == "A")
    src_b = next(s for s in req.sources if s.supplier == "B")
    world, prov = H.build_truth(conn, req, periods=8, seed=1)
    assert all(prov["supply"][f"{src_a.id}|{t}"] == "MEASURED" for t in range(8))
    assert all(prov["supply"][f"{src_b.id}|{t}"] == "ASSUMED" for t in range(8)), {k: v for k, v in prov["supply"].items() if src_b.id in k}
    assert not any(k.startswith(src_b.id) for k in prov["supply_actual_qty"])
    assert all(world.fills[src_b.id, t] == src_b.fill_mean for t in range(8))        # the declared or assumed fill, not A's 100%
    conn.close()


def test_a_a_received_order_without_supplier_identity_measures_nothing():
    conn = _truth_vault("forward")
    conn.execute("UPDATE stg_fmcg_purchase_orders SET supplier_id = NULL WHERE po_id LIKE 'PO-A-%'")
    as_of = datetime(2025, 9, 1, tzinfo=timezone.utc)
    req, _ = build_request(conn, "op", as_of=as_of, horizon=8, skus=["X"], sourcing=True)
    src_a = next(s for s in req.sources if s.supplier == "A")
    world, prov = H.build_truth(conn, req, periods=8, seed=1)
    assert all(prov["supply"][f"{src_a.id}|{t}"] != "MEASURED" for t in range(8))
    conn.close()


# ── correction D: identity fidelity is separate from evaluation fidelity ──
def _rows_for(identity_lines, observed, evaluated):
    actions = C.HistoricalActions(lines=identity_lines, by_review={0: {"src_X": observed}})
    methods = SimpleNamespace(actual={0: {"src_X": observed}}, zaad_log=[], actions=actions)
    initial = SimpleNamespace(sources=[_src("src_X", "X", "A")], services=[SimpleNamespace(sku="X", id="svc_X")])
    per = {"actual": [{"purchases": {"src_X": evaluated}, "as_of": "2025-09-01", "service_by_sku": {}, "end_stock_by_sku": {}}],
           "zaad": [{"purchases": {"src_X": 100.0}, "as_of": "2025-09-01", "service_by_sku": {}, "end_stock_by_sku": {}}]}
    return H._decision_rows(initial, per, methods, {"supply": {}, "supply_actual_qty": {}}, 1)[0]


def test_d_quantity_equality_never_proves_action_identity():
    exact = C.ActionLine(po_id="P1", po_date=pd.Timestamp("2025-09-02"), sku="X", supplier="A", destination=None, quantity=103., unit_cost=2., period=0, source="src_X", fidelity=C.EXACT)
    anonymous = C.ActionLine(po_id="P1", po_date=pd.Timestamp("2025-09-02"), sku="X", supplier=None, destination=None, quantity=103., unit_cost=2., period=0, source="src_X", fidelity=C.INCOMPLETE,
                             reason="the record carries no supplier identity")
    row = _rows_for([exact], 103., 103.)
    assert (row["actual_identity_fidelity"], row["actual_evaluation_fidelity"], row["actual_fidelity"]) == (C.EXACT, C.EXACT, C.EXACT)
    row = _rows_for([exact], 103., 96.)
    assert (row["actual_identity_fidelity"], row["actual_evaluation_fidelity"], row["actual_fidelity"]) == (C.EXACT, C.TRANSFORMED, C.TRANSFORMED)
    assert row["actual_observed_qty"] == 103. and row["actual_evaluated_qty"] == 96.
    row = _rows_for([anonymous], 103., 103.)          # sole-source fallback, no rounding: identity stays incomplete
    assert (row["actual_identity_fidelity"], row["actual_evaluation_fidelity"], row["actual_fidelity"]) == (C.INCOMPLETE, C.EXACT, C.INCOMPLETE)
    row = _rows_for([anonymous], 103., 96.)
    assert (row["actual_identity_fidelity"], row["actual_evaluation_fidelity"], row["actual_fidelity"]) == (C.INCOMPLETE, C.TRANSFORMED, C.INCOMPLETE)
    row = _rows_for([exact, anonymous], 206., 206.)   # one anonymous line in the cell makes the cell incomplete
    assert row["actual_identity_fidelity"] == C.INCOMPLETE and row["actual_fidelity"] == C.INCOMPLETE


# ── correction E: transformation is counted per source-review action group ──
def test_e_transformation_coverage_is_labelled_as_action_groups():
    cov = {"lines_observed": 9, "lines_exact": 9, "lines_incomplete": 0, "lines_unmapped": 0, "exact_quantity_share": 1.0, "exact_value_share": 1.0, "value_share_basis": "x", "incomplete_reasons": []}
    cmp = C.historical_comparison(cov, transformed_groups=2, settlement_shares=None, rule_provenance=None, reviews_completed=3)
    assert cmp["coverage"]["transformed_action_groups"] == 2 and "PO-line attribution is not available" in cmp["coverage"]["transformation_unit"]
    assert "2 source-review action group(s)" in " ".join(cmp["caveats"]) and "line(s) were" not in " ".join(cmp["caveats"])
    assert cmp["comparator"]["fidelity"] == C.TRANSFORMED and cmp["permissions"]["can_claim_historical_counterfactual_difference"] is False


# ── final pass, defect 1: receipt observations belong to a PO LINE, not to a PO id ──
def _multiline_vault(order="forward", *, receipts_without_sku=False, duplicate_line=False, shared_po_ids=True, mixed_receipt=False):
    """One PO id carries two SKU lines: X (100 ordered, 100 received after 7 days) and Y (50 ordered, 25 received
    after 28 days). Both SKUs are planned; the two observations must stay distinct.

    `shared_po_ids=False` gives every line its own PO id: the workspace adapter derives shipment-history and pipeline
    identities from the PO id alone (a pre-existing limit outside H3a), so the Request is built from that variant and
    the truth is reconstructed from the shared-id variant, which is the defect under test."""
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    conn.execute("INSERT INTO stg_fmcg_skus (sku, supplier_id, unit_cost, unit_price, units_per_case, moq_units) VALUES ('X', 'A', 2.0, 4.0, 1, 1), ('Y', 'A', 3.0, 6.0, 1, 1)")
    conn.execute("INSERT INTO stg_fmcg_suppliers (supplier_id) VALUES ('A')")
    po_rows, rc_rows = [], []
    for w in range(60):
        day = date(2025, 1, 6) + pd.Timedelta(weeks=w).to_pytimedelta()
        po = "PO-%02d" % w
        pid = (lambda sku: po) if shared_po_ids else (lambda sku: f"{po}-{sku}")
        for sku, q in (("X", 120), ("Y", 60)):
            conn.execute("INSERT INTO stg_fmcg_orders (order_id, customer_id, order_date, sku, qty_ordered) VALUES (?, 'C1', ?, ?, ?)", [f"SO-{sku}-{w:02d}", day, sku, q])
        if 30 <= w <= 33:
            continue          # a multi-line PO still open at the 2025-09-01 origin trips the pipeline's one-id-per-PO contract (pre-existing, outside H3a)
        po_rows += [(pid("X"), day, "A", "X", 100.0, 2.0), (pid("Y"), day, "A", "Y", 50.0, 3.0)]
        if duplicate_line:
            po_rows.append((pid("X"), day, "A", "X", 100.0, 2.0))
        rc_rows += [(pid("X"), day + pd.Timedelta(days=7).to_pytimedelta(), None if receipts_without_sku else "X", 100.0),
                    (pid("Y"), day + pd.Timedelta(days=28).to_pytimedelta(), None if receipts_without_sku else "Y", 25.0)]
        if mixed_receipt:
            rc_rows.append((po, day + pd.Timedelta(days=14).to_pytimedelta(), None, 10.0))      # a receipt on the PO that names no line
    seq = (po_rows, rc_rows) if order == "forward" else (po_rows[::-1], rc_rows[::-1])
    for po, day, sup, sku, qty, cost in seq[0]:
        conn.execute("INSERT INTO stg_fmcg_purchase_orders (po_id, po_date, supplier_id, sku, qty_ordered, unit_cost) VALUES (?, ?, ?, ?, ?, ?)", [po, day, sup, sku, qty, cost])
    for po, day, sku, q in seq[1]:
        conn.execute("INSERT INTO stg_fmcg_receipts (po_id, receipt_date, sku, qty_received) VALUES (?, ?, ?, ?)", [po, day, sku, q])
    for sku in ("X", "Y"):
        conn.execute("INSERT INTO stg_fmcg_inventory (snapshot_date, sku, location_id, on_hand, in_transit, snapshot_basis, source_known_at) "
                     "VALUES (DATE '2025-08-31', ?, 'MAIN', 300, 0, 'END_OF_DAY', TIMESTAMP '2025-08-31 23:59:59')", [sku])
    return conn


def _truth(conn):
    request_vault = _multiline_vault(shared_po_ids=False)
    req, _ = build_request(request_vault, "op", as_of=datetime(2025, 9, 1, tzinfo=timezone.utc), horizon=8, skus=["X", "Y"])
    request_vault.close()
    world, prov = H.build_truth(conn, req, periods=8, seed=1)
    return req, world, prov


@pytest.mark.parametrize("order", ["forward", "reversed"])
def test_f1_two_sku_lines_on_one_po_keep_their_own_receipts(order):
    conn = _multiline_vault(order)
    req, world, prov = _truth(conn)
    sx, sy = next(s.id for s in req.sources if s.sku == "X"), next(s.id for s in req.sources if s.sku == "Y")
    for t in range(8):
        assert prov["supply"][f"{sx}|{t}"] == "MEASURED" and prov["supply"][f"{sy}|{t}"] == "MEASURED"
        assert prov["supply_actual_qty"][f"{sx}|{t}"] == 100.0 and prov["supply_actual_qty"][f"{sy}|{t}"] == 50.0
        assert world.fills[sx, t] == 1.0 and world.fills[sy, t] == 0.5, (world.fills[sx, t], world.fills[sy, t])      # 100/100 and 25/50, not 125/150 for both
        assert world.arrival[sx, t] == t + 1 and world.arrival[sy, t] == t + 4                                       # 7 days and 28 days, not a blend
    assert prov["receipt_line_identity"].startswith("receipts are matched to a purchase-order LINE")
    conn.close()


def test_f1_receipts_without_sku_on_a_multiline_po_are_ambiguous_and_measure_nothing():
    conn = _multiline_vault(receipts_without_sku=True)
    req, world, prov = _truth(conn)
    for s in req.sources:
        assert all(prov["supply"][f"{s.id}|{t}"] != "MEASURED" for t in range(8)), s.id
    assert prov["ambiguous_receipt_lines"] > 0
    conn.close()


def test_f1_a_duplicated_po_line_is_ambiguous_for_that_line_only():
    conn = _multiline_vault(duplicate_line=True)
    req, world, prov = _truth(conn)
    sx, sy = next(s.id for s in req.sources if s.sku == "X"), next(s.id for s in req.sources if s.sku == "Y")
    assert all(prov["supply"][f"{sx}|{t}"] != "MEASURED" for t in range(8))           # X appears twice on the PO: which line was received?
    assert all(prov["supply"][f"{sy}|{t}"] == "MEASURED" for t in range(8)) and all(world.fills[sy, t] == 0.5 for t in range(8))
    conn.close()


def test_f1_two_suppliers_with_distinct_po_ids_are_unchanged():
    conn = _truth_vault("forward")
    req, _ = build_request(conn, "op", as_of=datetime(2025, 9, 1, tzinfo=timezone.utc), horizon=8, skus=["X"], sourcing=True)
    world, prov = H.build_truth(conn, req, periods=8, seed=1)
    a, b = next(s.id for s in req.sources if s.supplier == "A"), next(s.id for s in req.sources if s.supplier == "B")
    assert all(prov["supply"][f"{a}|{t}"] == "MEASURED" and world.fills[a, t] == 1.0 and world.fills[b, t] == 0.5 for t in range(8))
    conn.close()


# ── final pass, defect 2: a zero row is not an exact observation ──
def _serialized_rows(pos_rows, sources, observed_by_source, evaluated_by_source, zaad_by_source=None):
    actions = C.map_historical_actions(_pos(*pos_rows), sources, origin=ORIGIN, period_days=7, reviews=1)
    methods = SimpleNamespace(actual={0: observed_by_source}, zaad_log=[], actions=actions)
    initial = SimpleNamespace(sources=sources, services=[SimpleNamespace(sku=s.sku, id=f"svc_{s.sku}") for s in sources])
    per = {"actual": [{"purchases": evaluated_by_source, "as_of": "2025-09-01", "service_by_sku": {}, "end_stock_by_sku": {}}],
           "zaad": [{"purchases": zaad_by_source or {}, "as_of": "2025-09-01", "service_by_sku": {}, "end_stock_by_sku": {}}]}
    rows = H._decision_rows(initial, per, methods, {"supply": {}, "supply_actual_qty": {}}, 1)
    comparison = C.historical_comparison(actions.coverage(1), transformed_groups=0, settlement_shares=None, rule_provenance="INFERRED_FROM_HISTORY", reviews_completed=1)
    return {r["supplier"]: r for r in rows}, comparison


def test_f2_an_unmapped_po_never_becomes_an_exact_zero_order_for_a_candidate_source():
    two = [_src("src_X", "X", "A"), _src("src_X__B", "X", "B")]
    rows, cmp = _serialized_rows([("PO-1", "2025-09-02", None, "X", 100.)], two, {}, {})
    for supplier in ("A", "B"):
        r = rows[supplier]
        assert r["actual_observed_qty"] == 0.0 and r["actual_evaluated_qty"] == 0.0
        assert r["actual_fidelity"] == C.INCOMPLETE and r["actual_identity_fidelity"] == C.INCOMPLETE and r["actual_evaluation_fidelity"] is None, r
        assert r["actual_unidentified_lines"] == 1 and r["actual_unidentified_qty"] == 100.0
    assert cmp["comparator"]["fidelity"] == C.INCOMPLETE and cmp["permissions"]["can_claim_historical_counterfactual_difference"] is False
    one = [_src("src_X", "X", "A")]
    rows, cmp = _serialized_rows([("PO-1", "2025-09-02", None, "X", 100.)], one, {"src_X": 100.}, {"src_X": 100.})
    r = rows["A"]
    assert r["actual_observed_qty"] == 100.0 and r["actual_identity_fidelity"] == C.INCOMPLETE and r["actual_evaluation_fidelity"] == C.EXACT and r["actual_fidelity"] == C.INCOMPLETE
    assert cmp["permissions"]["can_claim_against_operator"] is False and cmp["claim_class"] == C.MODEL_COMPARISON


def test_f2_exact_identity_rows_and_empty_periods_are_told_apart():
    one = [_src("src_X", "X", "A")]
    rows, cmp = _serialized_rows([("PO-1", "2025-09-02", "A", "X", 100.)], one, {"src_X": 100.}, {"src_X": 100.})
    assert (rows["A"]["actual_identity_fidelity"], rows["A"]["actual_evaluation_fidelity"], rows["A"]["actual_fidelity"]) == (C.EXACT, C.EXACT, C.EXACT)
    assert cmp["claim_class"] == C.HISTORICAL_COUNTERFACTUAL_COMPARISON
    rows, _ = _serialized_rows([("PO-1", "2025-09-02", "A", "X", 103.)], one, {"src_X": 103.}, {"src_X": 96.})
    assert (rows["A"]["actual_identity_fidelity"], rows["A"]["actual_evaluation_fidelity"], rows["A"]["actual_fidelity"]) == (C.EXACT, C.TRANSFORMED, C.TRANSFORMED)
    rows, _ = _serialized_rows([], one, {}, {})
    r = rows["A"]
    assert r["actual_fidelity"] == C.NO_IDENTIFIED_ACTION and r["actual_identity_fidelity"] is None and r["actual_evaluation_fidelity"] is None and r["actual_unidentified_lines"] == 0
    two = [_src("src_X", "X", "A"), _src("src_X__B", "X", "B")]
    rows, cmp = _serialized_rows([("PO-1", "2025-09-02", "A", "X", 100.), ("PO-2", "2025-09-03", None, "X", 40.)], two, {"src_X": 100.}, {"src_X": 100.})
    assert rows["A"]["actual_identity_fidelity"] == C.INCOMPLETE and rows["A"]["actual_fidelity"] == C.INCOMPLETE and rows["A"]["actual_unidentified_lines"] == 1
    assert rows["B"]["actual_fidelity"] == C.INCOMPLETE and rows["B"]["actual_observed_qty"] == 0.0
    assert cmp["comparator"]["fidelity"] == C.INCOMPLETE and cmp["coverage"]["lines_unmapped"] == 1


# ── residual defect 1: an unattributable receipt on a PO taints every line of that PO ──
@pytest.mark.parametrize("order", ["forward", "reversed"])
def test_r1_a_receipt_without_sku_on_a_multiline_po_leaves_no_line_measured(order):
    conn = _multiline_vault(order, mixed_receipt=True)
    req, world, prov = _truth(conn)
    sx, sy = next(s.id for s in req.sources if s.sku == "X"), next(s.id for s in req.sources if s.sku == "Y")
    for t in range(8):
        assert prov["supply"][f"{sx}|{t}"] != "MEASURED" and prov["supply"][f"{sy}|{t}"] != "MEASURED", (t, prov["supply"][f"{sx}|{t}"], prov["supply"][f"{sy}|{t}"])
    assert not any(k.startswith(sx) or k.startswith(sy) for k in prov["supply_actual_qty"])
    assert prov["ambiguous_receipt_lines"] > 0 and prov["pos_with_unplaceable_receipts"] > 0
    conn.close()


def test_r1_fully_placed_pos_stay_measured_beside_tainted_ones():
    conn = _multiline_vault()
    # taint one PO in the window with a receipt that names no line; the others stay independently provable
    conn.execute("INSERT INTO stg_fmcg_receipts (po_id, receipt_date, sku, qty_received) VALUES ('PO-35', DATE '2025-09-22', NULL, 10)")
    req, world, prov = _truth(conn)
    sx, sy = next(s.id for s in req.sources if s.sku == "X"), next(s.id for s in req.sources if s.sku == "Y")
    tainted = 35 - 34                                   # PO-35 is placed in review period 1 (origin 2025-09-01 is week 34)
    assert prov["supply"][f"{sx}|{tainted}"] != "MEASURED" and prov["supply"][f"{sy}|{tainted}"] != "MEASURED"
    for t in range(8):
        if t != tainted:
            assert prov["supply"][f"{sx}|{t}"] == "MEASURED" and prov["supply"][f"{sy}|{t}"] == "MEASURED" and world.fills[sy, t] == 0.5
    conn.close()


# ── residual defect 2: decision summaries follow identity and transformation fidelity ──
def test_r2_an_unattributed_recorded_order_is_not_an_operator_who_placed_none():
    two = [_src("src_X", "X", "A"), _src("src_X__B", "X", "B")]
    rows, cmp = _serialized_rows([("PO-1", "2025-09-02", None, "X", 100.)], two, {}, {}, {"src_X": 20.})
    a = rows["A"]
    assert a["zaad_qty"] == 20. and a["actual_fidelity"] == C.INCOMPLETE and a["actual_unidentified_lines"] == 1
    assert a["comparison_basis"] == "unidentified" and a["zaad_vs_recorded"] is None
    assert a["zaad_action"] == "order" and "could not be attributed" in a["zaad_action_label"] and "no order" not in a["zaad_action_label"]
    assert a["timing"] is None or "not attributable" in a["timing"]
    assert cmp["permissions"]["can_claim_against_operator"] is False


def test_r2_a_transformed_order_is_compared_to_both_quantities_with_the_right_words():
    one = [_src("src_X", "X", "A")]
    rows, _ = _serialized_rows([("PO-1", "2025-09-02", "A", "X", 103.)], one, {"src_X": 103.}, {"src_X": 96.}, {"src_X": 100.})
    a = rows["A"]
    assert (a["actual_observed_qty"], a["actual_evaluated_qty"], a["zaad_qty"]) == (103., 96., 100.)
    assert a["comparison_basis"] == "model-evaluated" and a["zaad_action"] == "more" and a["zaad_vs_recorded"] == "less"
    assert a["zaad_action_label"] == "more than the model-evaluated quantity (96), less than the recorded order (103)"
    assert a["timing"] == "same week"
    rows, _ = _serialized_rows([("PO-1", "2025-09-02", "A", "X", 100.)], one, {"src_X": 100.}, {"src_X": 100.}, {"src_X": 100.})
    assert rows["A"]["comparison_basis"] == "recorded" and rows["A"]["zaad_vs_recorded"] == "same" and rows["A"]["zaad_action_label"] == "same as the recorded order (100)"
