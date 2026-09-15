"""The amendment counterfactual: one open order rewritten as if the declared right had been used.

The property under test is that nothing is inferred. Every rewrite follows a declared option on
the order; a change the contract does not declare, cannot cover, or no longer allows is refused
with the reason; and the contract's fee is reported beside the engine's figures, never inside.
"""
from __future__ import annotations

from datetime import timedelta

import pytest

from api.product.evaluation import EvaluationRefused, amendment_overlay, compare
from zaad.commitments.fixtures import CANCEL, DEFER, EXPEDITE, KEEP, base, build_request, open_po, option


def _draft(action: str, **over):
    body = {"draft_id": "draft_amend", "origin": "IMPORTED_AMENDMENT", "source_po_id": "po1",
            "amendment_action": action, "supplier_id": None, "destination_id": None,
            "requested_receipt_date": None, "currency": "USD", "lines": [{"sku": "sku", "quantity": 100, "unit_price": 5.3}]}
    body.update(over)
    return body


def _request(*opts, **po_over):
    d = base()
    return build_request(d, open_po(d, [KEEP(d), *[o(d) if callable(o) else o for o in opts]], **po_over))


def _po(request, po_id="po1"):
    return next((p for p in request.pipeline if p.id == po_id), None)


def test_a_deferral_moves_the_arrival_to_the_declared_window_and_uses_up_the_right():
    request = _request(DEFER)
    overlaid, terms = amendment_overlay(request, _draft("DEFER"))
    before, after = _po(request), _po(overlaid)
    assert after.current_eta == request.as_of + timedelta(days=request.period_days * 4)
    assert after.current_eta > before.current_eta
    assert [o.action for o in after.options] == ["keep"], "the right has been used; the overlay is KEEP-only"
    assert after.ordered == before.ordered
    assert terms["engine_action"] == "de_expedite" and terms["units_changed"] == 100
    assert terms["fee_total"] == pytest.approx(0.10 * 100) and terms["credit_total"] == 0
    assert terms["basis"] == "DECLARED_CONTRACT_TERMS"
    # the baseline is untouched: every declared right stays available to the engine there
    assert {o.action for o in before.options} == {"keep", "de_expedite"}


def test_an_expedite_must_actually_be_earlier():
    request = _request(EXPEDITE)
    overlaid, terms = amendment_overlay(request, _draft("EXPEDITE"))
    assert _po(overlaid).current_eta < _po(request).current_eta
    assert terms["fee_total"] == pytest.approx(50.0)
    late = _request(lambda d: option(d, "expedite", "expedite", 6, .5, 5.3))
    with pytest.raises(EvaluationRefused, match="not earlier"):
        amendment_overlay(late, _draft("EXPEDITE"))


def test_a_cancellation_removes_the_open_quantity_and_reports_fee_and_credit():
    request = _request(lambda d: CANCEL(d, credit=.2), prepaid=1., refundable=.5)
    overlaid, terms = amendment_overlay(request, _draft("CANCEL"))
    assert _po(overlaid) is None, "nothing was received, so the order leaves the pipeline"
    assert terms["units_changed"] == 100 and terms["open_after"] == 0
    assert terms["fee_total"] == pytest.approx(25.0) and terms["credit_total"] == pytest.approx(20.0)
    assert [s.id for s in overlaid.sources] == [s.id for s in request.sources], "nothing else changed"


def test_a_reduction_is_a_partial_cancel_within_the_declared_cap():
    request = _request(lambda d: CANCEL(d, max_quantity=40.))
    overlaid, terms = amendment_overlay(request, _draft("REDUCE", lines=[{"sku": "A", "quantity": 70}]))
    after = _po(overlaid)
    assert after.ordered == 70 and after.remaining == 70
    assert after.expected_accepted_remaining == pytest.approx(70)
    assert terms["units_changed"] == 30 and terms["fee_total"] == pytest.approx(7.5)
    with pytest.raises(EvaluationRefused, match="cancels at most 40"):
        amendment_overlay(request, _draft("REDUCE", lines=[{"sku": "A", "quantity": 50}]))
    with pytest.raises(EvaluationRefused, match="not a reduction"):
        amendment_overlay(request, _draft("REDUCE", lines=[{"sku": "A", "quantity": 100}]))


def test_a_full_cancel_beyond_the_declared_cap_is_refused_not_clipped():
    request = _request(lambda d: CANCEL(d, max_quantity=40.))
    with pytest.raises(EvaluationRefused, match="at most 40 of the 100"):
        amendment_overlay(request, _draft("CANCEL"))


def test_no_declared_right_means_no_evaluation():
    request = _request()
    with pytest.raises(EvaluationRefused, match="No right to defer po1 is declared"):
        amendment_overlay(request, _draft("DEFER"))


def test_a_right_the_stage_or_deadline_no_longer_allows_is_refused():
    shipped = _request(DEFER, departed=True, stage="shipped")
    with pytest.raises(EvaluationRefused, match="can be used while the order is confirmed"):
        amendment_overlay(shipped, _draft("DEFER"))
    expired = _request(lambda d: DEFER(d, deadline_days=-1))
    with pytest.raises(EvaluationRefused, match="expired"):
        amendment_overlay(expired, _draft("DEFER"))


def test_a_requested_date_must_be_one_of_the_declared_windows():
    request = _request(lambda d: option(d, "d4", "de_expedite", 4, .1, 5.3), lambda d: option(d, "d5", "reschedule", 5, .2, 5.3))
    with pytest.raises(EvaluationRefused, match="declares 2 windows"):
        amendment_overlay(request, _draft("DEFER"))
    wanted = (request.as_of + timedelta(days=request.period_days * 5)).date().isoformat()
    overlaid, terms = amendment_overlay(request, _draft("DEFER", requested_receipt_date=wanted))
    assert terms["option_id"] == "d5" and terms["fee_per_unit"] == .2
    off = (request.as_of + timedelta(days=request.period_days * 9)).date().isoformat()
    with pytest.raises(EvaluationRefused, match="not one of those windows"):
        amendment_overlay(request, _draft("DEFER", requested_receipt_date=off))


def test_split_and_keep_are_refused_with_the_reason():
    request = _request(DEFER)
    with pytest.raises(EvaluationRefused, match="Splitting"):
        amendment_overlay(request, _draft("SPLIT"))
    with pytest.raises(EvaluationRefused, match="changes nothing"):
        amendment_overlay(request, _draft("KEEP"))
    with pytest.raises(EvaluationRefused, match="not among the open orders"):
        amendment_overlay(request, _draft("DEFER", source_po_id="po-elsewhere"))


def test_the_comparison_shows_the_contract_fee_beside_the_engine_not_inside_it():
    baseline = {"as_of": "2026-01-05", "economics": {"incumbent_costs": {"TOTAL": 1000.0, "PURCHASE": 900.0},
                                                      "selected_costs": {"TOTAL": 990.0, "PURCHASE": 900.0}}}
    proposal = {"as_of": "2026-01-05", "economics": {"incumbent_costs": {"TOTAL": 960.0, "PURCHASE": 900.0}}}
    terms = {"po_id": "po1", "action": "DEFER", "fee_total": 10.0, "credit_total": 0.0, "units_changed": 100,
             "fee_per_unit": .1, "note": "po1: evaluated as if the declared right to defer had been used."}
    out = compare(baseline, proposal, draft=_draft("DEFER"), scope=["sku"], amendment_terms=terms)
    total = next(r for r in out["ledger"] if r["component"] == "TOTAL")
    assert total["proposal_vs_current"] == pytest.approx(-40.0), "the engine's own difference, fee excluded"
    assert out["contract_terms"]["modelled_difference"] == pytest.approx(-40.0)
    assert out["contract_terms"]["net_difference"] == pytest.approx(-30.0)
    assert out["contract_terms"]["basis"] == "DECLARED_CONTRACT_TERMS"
    assert "two stated numbers added" in out["contract_terms"]["net_basis"]
    assert out["amendment"] is True and "as it stands" in out["columns"][0]["source"]
    plain = compare(baseline, proposal, draft={"origin": "MANUAL", "lines": []}, scope=["sku"])
    assert plain["contract_terms"] is None
