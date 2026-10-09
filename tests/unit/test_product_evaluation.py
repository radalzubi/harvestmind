"""Proposal evaluation: the overlay that puts a proposed order into the request, and the
three-column comparison that reads the two reports back out.

The property under test is that **nothing is modelled here**. Every cell of the comparison is a
number one of the two engine reports produced under a named ledger key, and a key one report
carries and the other does not is reported as unavailable rather than treated as zero.
"""
from __future__ import annotations

import pytest

from api.product.evaluation import (
    LEDGER_ORDER, MAX_EVALUATION_SKUS, EvaluationRefused, amendment_view, compare, overlay, scope_for,
)


@pytest.fixture(scope="module")
def workspace():
    """A small real request built from a real vault, so the overlay is validated by the contract."""
    import duckdb
    from scripts.setup_db import setup_db
    from scripts.zaad_network_workspace_smoke import make_network_vault
    from zaad.meio.workspace import build_network_request

    conn = duckdb.connect(":memory:")
    setup_db(conn)
    make_network_vault(conn, seed=7)
    skus = [r[0] for r in conn.execute("SELECT sku FROM stg_fmcg_skus ORDER BY sku LIMIT 2").fetchall()]
    request, _build = build_network_request(conn, "tenant_eval", horizon=12, service_target=.95,
                                            skus=skus, max_solve_seconds=15., sourcing=True)
    return request, skus


def _draft(skus, **over):
    body = {"draft_id": "draft_eval", "supplier_id": None, "destination_id": None,
            "requested_receipt_date": None, "origin": "MANUAL",
            "lines": [{"sku": skus[0], "quantity": 1200, "unit_price": 4.5}]}
    body.update(over)
    return body


def test_the_overlay_adds_the_proposal_as_an_order_already_placed(workspace):
    request, skus = workspace
    overlaid, notes = overlay(request, _draft(skus))
    assert len(overlaid.pipeline) == len(request.pipeline) + 1
    added = next(po for po in overlaid.pipeline if po.id.startswith("proposal_"))
    assert added.ordered == 1200 and added.received == 0 and added.stage == "placed"
    assert sum(option.action == "keep" for option in added.options) == 1
    assert notes == [], "a declared price needs no note"


def test_the_overlay_changes_nothing_else_about_the_request(workspace):
    request, skus = workspace
    overlaid, _notes = overlay(request, _draft(skus))
    assert overlaid.as_of == request.as_of and overlaid.seed == request.seed
    assert overlaid.skus == request.skus and overlaid.sources == request.sources
    assert overlaid.stock == request.stock and overlaid.services == request.services
    assert request.pipeline == tuple(po for po in overlaid.pipeline if not po.id.startswith("proposal_"))


def test_a_line_with_no_declared_price_says_which_price_was_used(workspace):
    request, skus = workspace
    _overlaid, notes = overlay(request, _draft(skus, lines=[{"sku": skus[0], "quantity": 100}]))
    assert notes and "declared unit price" in notes[0]


def test_a_product_with_no_approved_source_is_refused_not_invented(workspace):
    request, skus = workspace
    with pytest.raises(EvaluationRefused, match="no approved source"):
        overlay(request, _draft(skus, supplier_id="SUP-NOT-APPROVED"))


def test_an_empty_proposal_has_nothing_to_evaluate(workspace):
    request, skus = workspace
    with pytest.raises(EvaluationRefused):
        overlay(request, _draft(skus, lines=[]))


def test_the_scope_is_the_proposal_and_is_bounded(workspace):
    _request, skus = workspace
    assert scope_for(_draft(skus)) == [skus[0]]
    many = _draft(skus, lines=[{"sku": f"SKU-{i:04d}", "quantity": 1} for i in range(MAX_EVALUATION_SKUS + 1)])
    with pytest.raises(EvaluationRefused, match="Split it"):
        scope_for(many)


def test_products_with_a_declared_amendment_right_travel_with_a_small_scope(workspace):
    _request, skus = workspace
    assert scope_for(_draft(skus), amendment_skus={"SKU-0099"}) == [skus[0], "SKU-0099"]
    # once the scope would exceed the bound, the extras are dropped rather than the proposal refused
    crowded = scope_for(_draft(skus), amendment_skus={f"SKU-{i:04d}" for i in range(200, 200 + MAX_EVALUATION_SKUS)})
    assert crowded == [skus[0]]


# ── the comparison ────────────────────────────────────────────────────────────

BASELINE = {
    "as_of": "2026-01-05T00:00:00Z", "information_hash": "a" * 64, "status": "PENDING_REVIEW",
    "limitations": ["one supplier's lead time is a public prior"],
    "economics": {
        "incumbent_costs": {"PURCHASE": 100.0, "CARRYING": 10.0, "OPERATING_TOTAL": 110.0, "TOTAL": 115.0},
        "selected_costs": {"PURCHASE": 90.0, "CARRYING": 12.0, "OPERATING_TOTAL": 102.0, "TOTAL": 108.0},
        "incumbent_working_capital": 500.0, "selected_working_capital": 460.0,
    },
    "network_service": [{"service": "svc_a", "location": "DC", "requested": 0.95,
                         "incumbent_achieved": 0.93, "selected_achieved": 0.96,
                         "expected_achieved": 0.96, "jointly_feasible": 0.97}],
}
PROPOSAL = {
    "as_of": "2026-01-05T00:00:00Z", "status": "PENDING_REVIEW", "limitations": [],
    "economics": {"incumbent_costs": {"PURCHASE": 140.0, "CARRYING": 16.0, "OPERATING_TOTAL": 156.0},
                  "incumbent_working_capital": 620.0},
    "network_service": [{"service": "svc_a", "location": "DC", "requested": 0.95,
                         "incumbent_achieved": 0.97, "selected_achieved": 0.97,
                         "expected_achieved": 0.97, "jointly_feasible": 0.98}],
}


def test_three_columns_come_from_the_two_reports():
    out = compare(BASELINE, PROPOSAL, draft=_draft(["SKU-0001"]), scope=["SKU-0001"])
    assert [c["key"] for c in out["columns"]] == ["current", "zaad", "proposal"]
    purchase = next(row for row in out["ledger"] if row["component"] == "PURCHASE")
    assert (purchase["current"], purchase["zaad"], purchase["proposal"]) == (100.0, 90.0, 140.0)
    assert purchase["proposal_vs_current"] == 40.0
    assert purchase["zaad_vs_current"] == -10.0


def test_the_ledger_keeps_the_engines_order_and_drops_nothing_it_has():
    out = compare(BASELINE, PROPOSAL, draft=_draft(["SKU-0001"]), scope=["SKU-0001"])
    shown = [row["component"] for row in out["ledger"]]
    assert shown == [c for c in LEDGER_ORDER if c in shown]
    assert "TOTAL" in shown


def test_a_line_one_report_does_not_carry_is_unavailable_not_zero():
    out = compare(BASELINE, PROPOSAL, draft=_draft(["SKU-0001"]), scope=["SKU-0001"])
    total = next(row for row in out["ledger"] if row["component"] == "TOTAL")
    assert total["current"] == 115.0 and total["proposal"] is None
    assert total["proposal_vs_current"] is None, "a missing figure is never differenced against zero"


def test_service_is_reported_per_service_against_the_target():
    out = compare(BASELINE, PROPOSAL, draft=_draft(["SKU-0001"]), scope=["SKU-0001"])
    row = out["service"][0]
    assert row["requested"] == 0.95 and row["current"] == 0.93 and row["proposal"] == 0.97


def test_the_scope_limitation_is_always_stated():
    out = compare(BASELINE, PROPOSAL, draft=_draft(["SKU-0001"]), scope=["SKU-0001"])
    assert any("covers the 1 product" in limitation for limitation in out["limitations"])
    assert any("public prior" in limitation for limitation in out["limitations"]), \
        "the engine's own limitations travel with the comparison"
    assert out["executable"] is False


def test_runs_that_do_not_share_an_information_set_are_not_compared():
    out = compare(BASELINE, {**PROPOSAL, "as_of": "2026-02-05T00:00:00Z"},
                  draft=_draft(["SKU-0001"]), scope=["SKU-0001"])
    assert any("as-of" in note for note in out["unavailable"])


def test_a_run_still_in_flight_says_so():
    out = compare(BASELINE, None, draft=_draft(["SKU-0001"]), scope=["SKU-0001"])
    assert out["unavailable"] == ["The run with your proposal has not produced a plan yet."]


# ── amendments ────────────────────────────────────────────────────────────────

def test_an_amendment_with_no_declared_right_is_not_priced():
    report = {"commitments": {"reading": "x", "orders": [
        {"po": "PO-1", "recommended_action": "KEEP", "contractual_basis": []}]}}
    view = amendment_view(report, "PO-1")
    assert view["priced"] is False and "declared" in view["reason"]


def test_an_amendment_with_a_declared_right_reads_the_engines_own_block():
    report = {"commitments": {"reading": "deferring saves financing", "orders": [
        {"po": "PO-1", "recommended_action": "DEFER",
         "contractual_basis": [{"option": "opt_defer", "provenance": "CONTRACT"}]}]}}
    view = amendment_view(report, "PO-1")
    assert view["priced"] is True and view["recommended_action"] == "DEFER"
    assert view["declared_options"] == ["opt_defer"]
    assert view["executable"] is False


def test_an_order_outside_the_last_plan_says_so_rather_than_guessing():
    view = amendment_view({"commitments": {"orders": []}}, "PO-2")
    assert view["priced"] is False and "not in the last plan" in view["reason"]


# ── what the comparison says it covered ───────────────────────────────────────

def test_the_scope_sentence_separates_the_proposals_products_from_the_rights_it_carries():
    """The scope is the proposal's products PLUS every product with a declared order-change right.

    Calling all of them "the products on this proposal" was false whenever the second group was not
    empty — a one-line proposal was reported as covering six products "on this proposal".
    """
    out = compare(BASELINE, PROPOSAL, draft=_draft(["SKU-0001"]),
                  scope=["SKU-0001", "SKU-0002", "SKU-0003"])
    said = out["limitations"][0]
    assert "covers 3 products" in said
    assert "1 product on this proposal" in said
    assert "2 more that carry a declared order-change right" in said


def test_a_proposal_whose_scope_is_only_its_own_products_keeps_the_short_sentence():
    out = compare(BASELINE, PROPOSAL, draft=_draft(["SKU-0001"]), scope=["SKU-0001"])
    assert out["limitations"][0].startswith("The comparison covers the 1 product on this proposal.")


def test_one_carried_product_is_singular():
    out = compare(BASELINE, PROPOSAL, draft=_draft(["SKU-0001"]), scope=["SKU-0001", "SKU-0002"])
    assert "1 more that carries a declared order-change right" in out["limitations"][0]


# ── declared rights are not the same thing as a chosen amendment ──────────────

def _window(action, **over):
    base = {"option": f"opt_{action}", "action": action, "label": action.upper(), "eligible": True,
            "provenance": "OPERATOR_DECLARED", "fee_per_unit": 0.2, "credit_per_unit": 0.0,
            "capacity_units": 1776.0, "deadline": "2026-10-05T00:00:00+00:00"}
    base.update(over)
    return base


def _keep_order(windows):
    """What P4B reports for an order it decided to KEEP: no basis, but the windows are still there."""
    return {"commitments": {"reading": "KEEP every declared order.", "orders": [
        {"po": "PO-1", "recommended_action": "KEEP", "contractual_basis": [],
         "amendment_windows": [_window("keep", provenance="CONTRACT", label="KEEP"), *windows]}]}}


def test_a_keep_does_not_mean_the_contract_declares_nothing():
    """`contractual_basis` is what the engine CHOSE. It is empty on every KEEP.

    Reading it as "no right is declared" told a buyer their contract gave them nothing while the
    order drawer beside it listed three declared rights.
    """
    view = amendment_view(_keep_order([_window("de_expedite"), _window("expedite"), _window("cancel")]),
                          "PO-1", "DEFER")
    assert view["priced"] is False                      # the engine priced no change, and says so
    assert len(view["declared_windows"]) == 3           # but the rights are reported
    assert "a right to defer, expedite or cancel" in view["reason"]
    assert "keeping it as it is" in view["reason"]
    assert view["proposed_window"]["action"] == "de_expedite"


def test_the_built_in_keep_window_is_not_evidence_of_a_declared_right():
    view = amendment_view(_keep_order([]), "PO-1", "DEFER")
    assert view["declared_windows"] == []
    assert "No contractual right" in view["reason"]


def test_an_ineligible_window_is_not_offered_as_a_right():
    view = amendment_view(_keep_order([_window("cancel", eligible=False)]), "PO-1", "CANCEL")
    assert view["declared_windows"] == []
    assert view["proposed_window"] is None


def test_a_change_the_contract_does_not_cover_says_which_ones_it_does():
    view = amendment_view(_keep_order([_window("cancel")]), "PO-1", "EXPEDITE")
    assert view["proposed_window"] is None
    assert "a right to cancel" in view["reason"]
    assert "not this change" in view["reason"]


def test_a_change_p4b_has_no_option_type_for_is_named_as_such():
    view = amendment_view(_keep_order([_window("cancel")]), "PO-1", "SPLIT")
    assert "not a change of this kind" in view["reason"]


def test_reschedule_is_a_defer_too():
    view = amendment_view(_keep_order([_window("reschedule")]), "PO-1", "DEFER")
    assert view["proposed_window"]["action"] == "reschedule"
    assert "a right to defer" in view["reason"]


# ── H3a: the left column is the decision reference, labelled by its provenance ──
def test_left_column_is_the_decision_reference_not_your_current_plan():
    out = compare(BASELINE, PROPOSAL, draft=_draft(["SKU-0001"]), scope=["SKU-0001"])
    current = out["columns"][0]
    # a baseline report from before the contract never recorded what its incumbent was
    assert current["label"] == "Decision reference (provenance not recorded)" and current["comparator_type"] == "NOT_RECORDED"
    reconstructed = {**BASELINE, "decision_reference": {"type": "RECONSTRUCTED_POLICY", "fidelity": "RECONSTRUCTED", "label": "the reconstructed historical rule", "rule": "replace_sold"}}
    out = compare(reconstructed, PROPOSAL, draft=_draft(["SKU-0001"]), scope=["SKU-0001"])
    current = out["columns"][0]
    assert current["label"] == "Reconstructed policy baseline" and current["comparator_type"] == "RECONSTRUCTED_POLICY" and current["fidelity"] == "RECONSTRUCTED"
    assert out["comparison"]["claim_class"] == "MODEL_COMPARISON" and out["comparison"]["permissions"]["can_claim_against_operator"] is False
    assert out["comparison"]["permissions"]["can_claim_realized_value"] is False
    text = " ".join([c["label"] + " " + c["source"] for c in out["columns"]] + out["limitations"]).lower()
    assert "your current plan" not in text and "what you would have done" not in text.replace("not a claim against what you would have done", "")
    declared = {**BASELINE, "decision_reference": {"type": "RECONSTRUCTED_POLICY", "fidelity": "DECLARED", "label": "the operator-declared rule"}}
    assert compare(declared, PROPOSAL, draft=_draft(["SKU-0001"]), scope=["SKU-0001"])["columns"][0]["label"] == "Operator-declared rule baseline"
    proxy = {**BASELINE, "decision_reference": {"type": "SYSTEM_BASELINE", "fidelity": "NOT_AVAILABLE", "label": "the system base-stock baseline"}}
    assert compare(proxy, PROPOSAL, draft=_draft(["SKU-0001"]), scope=["SKU-0001"])["columns"][0]["label"] == "Model baseline"
    # the ledger arithmetic is untouched by the labelling
    purchase = next(r for r in out["ledger"] if r["component"] == "PURCHASE")
    assert (purchase["current"], purchase["zaad"], purchase["proposal"]) == (100.0, 90.0, 140.0)
