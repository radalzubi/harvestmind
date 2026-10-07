"""Canonical request fingerprint and the causal perturbation harness (HARDENING V1, H0).

The harness is proved on a test double: the same toy builder in a clean form (reads only facts the
operator could have known before the decision time) and in a contaminated form that reproduces the defect
class found in the audit (an open order's remaining quantity is computed from receipts of every date, so
an order received in full after the decision time disappears from the pipeline). The production builder
is not asserted on here; its own invariant arrives with the fix (H1a).

The double keeps three things apart on every receipt row: `day` (when the receipt happens, relative to T),
`known_day` (when the operator could have known it) and nothing about ingestion. One row is a delivery
scheduled after T that was already known before T."""
from __future__ import annotations

import math
from datetime import timedelta, timezone

import pytest

from zaad.full import causal
from zaad.full.contracts import Request
from zaad.full.demo import example
from zaad.full.economics import provenance


# ── the test double ──────────────────────────────────────────────────────────
def _source() -> dict:
    """Two orders placed before T. PO-A is received in full after T and nobody knew before T. PO-B was half
    received before T; its second half is scheduled for day 4, a commitment known two days before T."""
    return {"pos": [{"id": "PO-A", "ordered": 40.0, "placed_days_before": 10}, {"id": "PO-B", "ordered": 60.0, "placed_days_before": 20}],
            "receipts": [{"po": "PO-A", "day": 2, "known_day": 2, "qty": 40.0},
                         {"po": "PO-B", "day": -5, "known_day": -5, "qty": 30.0},
                         {"po": "PO-B", "day": 4, "known_day": -2, "qty": 30.0}]}


def known_before(fact, decision_at=None) -> bool:
    """The double's knowledge rule: source_known_at < T."""
    return fact["known_day"] < 0


def happened_before(fact, decision_at=None) -> bool:
    """The date-only stand-in: a fact is taken to be known from the day it happens."""
    return fact["day"] < 0


def _build(source: dict, *, contaminated: bool) -> Request:
    base = example()
    t, src = base.as_of, base.sources[0]
    known = t - timedelta(seconds=1)
    rows = []
    for po in source["pos"]:
        mine = [r for r in source["receipts"] if r["po"] == po["id"]]
        # contaminated: every receipt row counts as received, whenever it happens and whoever knew
        received = sum(r["qty"] for r in mine if contaminated or (known_before(r) and r["day"] < 0))
        remaining = po["ordered"] - received
        if remaining <= 0:
            continue
        promised = [r["day"] for r in mine if known_before(r) and r["day"] >= 0]      # a future delivery the buyer already knows
        eta = min(promised) if promised else 7
        rows.append({"known_at": known, "id": po["id"], "source": src.id, "revision": 1, "ordered": po["ordered"], "confirmed": po["ordered"],
                     "shipped": received, "received": received, "rejected": 0., "expected_accepted_remaining": remaining,
                     "placed_at": t - timedelta(days=po["placed_days_before"]), "confirmed_at": None, "departed_at": None,
                     "current_eta": t + timedelta(days=eta), "stage": "ordered", "carrier": "unknown", "cancellation_status": "none",
                     "prepaid_per_remaining_unit": 0., "allow_split_amendments": False,
                     "options": [{"known_at": known, "id": "keep_" + po["id"], "action": "keep", "due_in": 1, "fee_per_unit": 0.,
                                  "remaining_invoice_per_unit": src.unit_price, "payment_due_in": 1, "max_quantity": remaining,
                                  "deadline": t + timedelta(days=28), "allowed_stages": ["ordered"], "contract_reference": po["id"]}]})
    return Request.model_validate({**base.model_dump(), "pipeline": rows})


def clean(source: dict) -> Request:
    return _build(source, contaminated=False)


def contaminated(source: dict) -> Request:
    return _build(source, contaminated=True)


def _receipts(change):
    def apply(source: dict):
        before = source["receipts"]
        after = change([dict(r) for r in before])
        return {**source, "receipts": after}, sum(1 for r in before if r not in after) + sum(1 for r in after if r not in before)
    return causal.pure(apply)


def family(is_available_at, rule: str) -> list[causal.Perturbation]:
    """Receipt perturbations for the double. Availability comes from the predicate and from nothing else."""
    def unavailable(r):
        return not is_available_at(r, None)

    def make(name, fam, control, change):
        return causal.Perturbation(name, fam, control, _receipts(change), availability=rule)
    return [make("delete unavailable receipts", causal.FUTURE_RECEIPTS, "negative", lambda rs: [r for r in rs if not unavailable(r)]),
            make("halve unavailable receipts", causal.FUTURE_RECEIPTS, "negative", lambda rs: [{**r, "qty": r["qty"] / 2} if unavailable(r) else r for r in rs]),
            make("move unavailable receipts later", causal.FUTURE_RECEIPTS, "negative",
                 lambda rs: [{**r, "day": r["day"] + 7, "known_day": r["known_day"] + 7} if unavailable(r) else r for r in rs]),
            make("add an unavailable receipt", causal.FUTURE_RECEIPTS, "negative", lambda rs: rs + [{"po": "PO-B", "day": 3, "known_day": 3, "qty": 30.0}]),
            make("halve available receipts that already happened", "known_facts", "positive",
                 lambda rs: [{**r, "qty": r["qty"] / 2} if not unavailable(r) and r["day"] < 0 else r for r in rs]),
            make("move an available future delivery", "known_facts", "positive",
                 lambda rs: [{**r, "day": r["day"] + 2} if not unavailable(r) and r["day"] >= 0 else r for r in rs])]


BY_KNOWLEDGE = family(known_before, "source_known_at < T")
BY_EVENT_DATE = family(happened_before, causal.LEGACY_DATE_ONLY)
NEGATIVE = [p for p in BY_KNOWLEDGE if p.control == "negative"]


# ── the fingerprint ──────────────────────────────────────────────────────────
def test_the_same_request_built_twice_has_the_same_hash():
    a, b = causal.fingerprint(clean(_source())), causal.fingerprint(clean(_source()))
    assert a == b and len(a.hash) == 64


def test_the_hash_records_its_projection_version_and_covers_it(monkeypatch):
    req = clean(_source())
    first = causal.fingerprint(req)
    assert first.projection_version == causal.PROJECTION_VERSION == "zaad.causal.request.v1"
    assert first.schema_version == req.schema_version
    assert first.as_dict() == {"hash": first.hash, "projection_version": first.projection_version, "schema_version": first.schema_version}
    monkeypatch.setattr(causal, "PROJECTION_VERSION", "zaad.causal.request.v2-test")
    second = causal.fingerprint(req)
    assert second.projection_version == "zaad.causal.request.v2-test" and second.hash != first.hash


def test_row_order_is_part_of_the_identity_of_every_collection():
    """No row collection is sorted: consumers draw random numbers and create solver variables in collection
    order, so two orders of the same rows are two requests until shown otherwise."""
    req = clean(_source())
    base = causal.fingerprint(req).hash
    checked = []
    for name, field in type(req).model_fields.items():
        rows = getattr(req, name)
        if not isinstance(rows, tuple) or len(rows) < 2:
            continue
        other = req.model_copy(update={name: rows[::-1]})
        assert causal.fingerprint(other).hash != base, name
        assert causal.first_difference(req, other)["path"].startswith(name), name
        checked.append(name)
    assert {"history", "pipeline"} <= set(checked)
    swapped = req.model_copy(update={"pipeline": req.pipeline[::-1]})
    assert causal.first_difference(req, swapped) == {"path": "pipeline<order>[0]", "base": "id=PO-A", "variant": "id=PO-B"}


def test_a_positional_sequence_inside_a_row_keeps_its_order():
    req = clean(_source())
    src = req.sources[0]
    ramp = tuple(float(src.capacity_by_period[0] + i) for i in range(len(src.capacity_by_period)))
    up = req.model_copy(update={"sources": (src.model_copy(update={"capacity_by_period": ramp}), *req.sources[1:])})
    down = req.model_copy(update={"sources": (src.model_copy(update={"capacity_by_period": ramp[::-1]}), *req.sources[1:])})
    assert causal.fingerprint(up).hash != causal.fingerprint(down).hash


def test_the_one_order_free_mapping_is_order_free_in_behaviour():
    """`economics_provenance` is the only mapping whose key order is left out of the identity. The evidence
    is behavioural: the function that reads it returns the same thing for either order."""
    assert set(causal.ORDER_FREE_MAPPINGS) == {"economics_provenance"}
    req = clean(_source())
    src, loc = req.sources[0], req.locations[0]
    labels = {f"source.{src.id}.unit_price": "CUSTOMER_PROVIDED", f"source.{src.id}.lead_days": "INFERRED_FROM_HISTORY",
              f"location.{loc.id}.holding_per_value_period": "CONFIGURED_ASSUMPTION"}
    forward = req.model_copy(update={"economics_provenance": dict(labels)})
    backward = req.model_copy(update={"economics_provenance": dict(reversed(list(labels.items())))})
    assert list(forward.economics_provenance) != list(backward.economics_provenance)
    assert causal.fingerprint(forward) == causal.fingerprint(backward)
    assert provenance(forward) == provenance(backward)
    assert list(provenance(forward)) == list(provenance(backward))                   # same content in the same order
    assert provenance(forward) != provenance(req)                                    # and the labels are read at all
    assert causal.fingerprint(forward).hash != causal.fingerprint(req).hash


def test_every_other_mapping_keeps_its_insertion_order():
    req = clean(_source())
    one = req.model_copy(update={"inherited_on_hand": {"A|branch": 1.0, "B|branch": 2.0}})
    two = req.model_copy(update={"inherited_on_hand": {"B|branch": 2.0, "A|branch": 1.0}})
    assert causal.fingerprint(one).hash != causal.fingerprint(two).hash
    assert causal.first_difference(one, two) == {"path": "inherited_on_hand<order>[0]", "base": "A|branch", "variant": "B|branch"}
    signal = req.model_copy(update={"signals": ({"a": 1, "b": 2},)})
    flipped = req.model_copy(update={"signals": ({"b": 2, "a": 1},)})
    assert causal.fingerprint(signal).hash != causal.fingerprint(flipped).hash


def test_any_decision_relevant_change_changes_the_hash_without_rounding():
    req = clean(_source())
    base = causal.fingerprint(req).hash
    lot = req.stock[0]
    nudged = req.model_copy(update={"stock": (lot.model_copy(update={"quantity": math.nextafter(lot.quantity, math.inf)}), *req.stock[1:])})
    assert causal.fingerprint(nudged).hash != base                                   # the next representable number is a different request
    diff = causal.first_difference(req, nudged)
    assert diff["path"] == f"stock[id={lot.id}].quantity" and diff["base"] == lot.quantity
    for change in ({"seed": req.seed + 1}, {"scenarios": req.scenarios + 1}, {"evidence_label": "OPERATOR-SHADOW" if req.evidence_label == "SYNTHETIC" else "SYNTHETIC"},
                   {"incumbent_rule": "periodic:2"}, {"operator_id": req.operator_id + "-other"}):
        assert causal.fingerprint(req.model_copy(update=change)).hash != base, change
    po = req.pipeline[0]                                                             # when a row became known is identity
    earlier = req.model_copy(update={"pipeline": (po.model_copy(update={"known_at": po.known_at - timedelta(days=1)}), *req.pipeline[1:])})
    assert causal.first_difference(req, earlier)["path"] == f"pipeline[id={po.id}].known_at"


def test_one_instant_written_in_two_timezones_is_one_request():
    req = clean(_source())
    amman = timezone(timedelta(hours=3))
    same = req.model_copy(update={"as_of": req.as_of.astimezone(amman)})
    assert same.as_of.utcoffset() != req.as_of.utcoffset()
    assert causal.fingerprint(same) == causal.fingerprint(req)
    assert causal.fingerprint(req.model_copy(update={"as_of": req.as_of + timedelta(microseconds=1)})).hash != causal.fingerprint(req).hash


def test_negative_zero_is_zero_and_nothing_else_is_normalised():
    assert causal._bytes(causal._canon([-0.0], "")) == causal._bytes(causal._canon([0.0], ""))
    assert causal._bytes(causal._canon([0.1 + 0.2], "")) != causal._bytes(causal._canon([0.3], ""))
    assert causal._bytes(causal._canon([1], "")) != causal._bytes(causal._canon([1.0], ""))


def test_a_value_without_an_exact_form_is_refused():
    req = clean(_source())
    for bad in ({"note": object()}, {"level": float("nan")}, {"level": float("inf")}, {"tags": {"a", "b"}}, {1: "numeric key"}):
        with pytest.raises(causal.CanonicalizationError):
            causal.fingerprint(req.model_copy(update={"signals": (bad,)}))
    with pytest.raises(causal.CanonicalizationError):
        causal.fingerprint(req.model_copy(update={"as_of": req.as_of.replace(tzinfo=None)}))


def test_nothing_in_the_request_is_excluded_and_an_exclusion_would_have_to_be_declared(monkeypatch):
    assert causal.EXCLUDED_PATHS == {}
    req = clean(_source())
    assert set(causal.canonical_projection(req)["request"]) == set(type(req).model_fields)
    other = req.model_copy(update={"seed": req.seed + 1})
    assert causal.fingerprint(other).hash != causal.fingerprint(req).hash
    monkeypatch.setattr(causal, "EXCLUDED_PATHS", {"seed": "test only: shows that an excluded path leaves the hash alone"})
    assert causal.fingerprint(other) == causal.fingerprint(req)
    assert causal.first_difference(req, other) is None


# ── the harness ──────────────────────────────────────────────────────────────
def test_a_builder_that_reads_an_unavailable_receipt_is_caught_and_the_field_is_named():
    report = causal.run_causal_checks(contaminated, _source(), BY_KNOWLEDGE)
    assert report["status"] == "FAIL" and report["all_clean"] is False
    assert report["meaning"] == causal.CAUSAL_STATUS_MEANING["FAIL"]
    assert report["projection_version"] == causal.PROJECTION_VERSION
    assert report["base_request_hash"] == causal.fingerprint(contaminated(_source())).hash
    assert report["decision_at"] == example().as_of.isoformat()
    group = next(f for f in report["families"] if f["family"] == causal.FUTURE_RECEIPTS)
    assert group["control"] == "negative" and group["variants_checked"] == 4 and group["failures"] >= 2
    assert group["availability_rules"] == ["source_known_at < T"]
    failed = {f["perturbation"]: f for f in report["failures"]}
    deleted = failed["delete unavailable receipts"]
    assert deleted["expected"] == "request unchanged" and deleted["observed"] == "request changed" and deleted["source_facts_changed"] == 1
    assert deleted["availability"] == "source_known_at < T"
    # the order that the unavailable receipt had removed from the pipeline is the first difference
    assert deleted["first_difference"]["path"] == "pipeline[id=PO-A]" and deleted["first_difference"]["base"] == "<absent>"
    assert failed["halve unavailable receipts"]["first_difference"]["path"].startswith("pipeline[id=PO-A]")
    assert all(f["first_difference"]["path"].startswith("pipeline") for f in report["failures"] if f["control"] == "negative")


def test_a_builder_that_reads_only_what_was_known_passes_both_controls():
    report = causal.run_causal_checks(clean, _source(), BY_KNOWLEDGE)
    assert report["status"] == "PASS" and report["all_clean"] is True and report["failures"] == []
    assert report["meaning"] == causal.CAUSAL_STATUS_MEANING["PASS"]
    assert report["variants_checked"] == 6 and report["vacuous"] == 0
    assert {(f["family"], f["control"], f["variants_checked"]) for f in report["families"]} == {(causal.FUTURE_RECEIPTS, "negative", 4), ("known_facts", "positive", 2)}


def test_a_future_event_that_was_already_known_is_an_input_not_a_leak():
    """event_at >= T does not imply source_known_at >= T. The delivery scheduled for day 4 was known before
    T, the clean builder uses it, and that is correct: under the knowledge rule it is a positive control."""
    moved = next(p for p in BY_KNOWLEDGE if p.name == "move an available future delivery")
    report = causal.run_causal_checks(clean, _source(), [moved])
    assert report["status"] == "PASS" and report["variants_checked"] == 1
    with moved.variant(_source()) as (perturbed, changed):
        assert changed > 0
        assert causal.first_difference(clean(_source()), clean(perturbed))["path"] == "pipeline[id=PO-B].current_eta"


def test_judging_availability_by_event_date_condemns_a_correct_builder():
    """The same clean builder under the date-only stand-in: the known future delivery is classed as
    unavailable, perturbing it changes the request, and the harness reports a failure that is not one.
    The stand-in is therefore a labelled assumption for date-only rows and never the harness's rule."""
    report = causal.run_causal_checks(clean, _source(), BY_EVENT_DATE)
    assert report["status"] == "FAIL"
    assert {f["availability"] for f in report["failures"]} == {causal.LEGACY_DATE_ONLY}
    assert all(f["first_difference"]["path"].startswith("pipeline[id=PO-B]") for f in report["failures"] if f["control"] == "negative")
    assert causal.run_causal_checks(clean, _source(), BY_KNOWLEDGE)["status"] == "PASS"


def test_the_harness_has_no_availability_rule_of_its_own():
    import inspect
    assert inspect.signature(causal.receipt_perturbations).parameters["is_available_at"].default is inspect.Parameter.empty
    with pytest.raises(TypeError):
        causal.receipt_perturbations(example().as_of)                                # the caller must state the rule
    family_ = causal.receipt_perturbations(example().as_of, is_available_at=causal.legacy_date_only_receipt_availability)
    assert {p.availability for p in family_} == {causal.LEGACY_DATE_ONLY} and causal.LEGACY_DATE_ONLY.startswith("LEGACY_DATE_ONLY_TEST_ASSUMPTION")
    named = causal.receipt_perturbations(example().as_of, is_available_at=known_before)
    assert {p.availability for p in named} == {"known_before"}
    t = example().as_of
    assert causal.legacy_date_only_receipt_availability({"receipt_date": (t - timedelta(days=1)).date()}, t) is True
    assert causal.legacy_date_only_receipt_availability({"receipt_date": t.date()}, t) is False


def test_a_builder_that_ignores_its_data_fails_the_positive_control():
    report = causal.run_causal_checks(lambda source: clean(_source()), _source(), BY_KNOWLEDGE)
    assert report["status"] == "FAIL"
    assert {f["control"] for f in report["failures"]} == {"positive"} and len(report["failures"]) == 2
    assert all(f["expected"] == "request changed" and f["observed"] == "request unchanged" and f["first_difference"] is None for f in report["failures"])


def test_a_perturbation_that_touches_nothing_is_not_a_pass():
    nothing = causal.Perturbation("delete unavailable receipts", causal.FUTURE_RECEIPTS, "negative", _receipts(lambda rs: rs))
    report = causal.run_causal_checks(clean, _source(), [nothing])
    assert report["status"] == "NOT_RUN" and report["all_clean"] is False and report["variants_checked"] == 0 and report["vacuous"] == 1
    assert report["meaning"] == causal.CAUSAL_STATUS_MEANING["NOT_RUN"]
    assert causal.run_causal_checks(clean, _source(), [])["status"] == "NOT_RUN"


# ── the composite attestation ────────────────────────────────────────────────
def _legacy(clean_: bool) -> dict:
    return {"snapshots": 1, "all_clean": clean_, "per_review": [{"as_of": "2026-09-01T00:00:00+00:00", "history_before_decision": clean_}]}


PASSED = causal.run_causal_checks(clean, _source(), NEGATIVE)
FAILED = causal.run_causal_checks(contaminated, _source(), NEGATIVE)


@pytest.mark.parametrize("legacy_clean, causal_report, expected", [
    (True, PASSED, True),          # legacy pass + causal PASS
    (False, PASSED, False),        # legacy fail + causal PASS
    (True, FAILED, False),         # legacy pass + causal FAIL
    (True, None, False),           # legacy pass + causal NOT_RUN (never ran)
    (True, causal.not_run(), False),
    (False, FAILED, False),
])
def test_all_clean_needs_the_field_checks_and_a_causal_pass(legacy_clean, causal_report, expected):
    legacy = _legacy(legacy_clean)
    out = causal.composite_attestation(legacy, causal_report)
    status = "NOT_RUN" if causal_report is None else causal_report["status"]
    assert out["all_clean"] is expected
    assert out["legacy_all_clean"] is legacy_clean
    assert out["causal_status"] == status and out["causal"]["status"] == status
    assert out["causal_all_clean"] is (status == "PASS")
    assert out["all_clean"] is (out["legacy_all_clean"] and out["causal_status"] == "PASS" and out["causal_all_clean"])
    assert out["snapshots"] == 1 and out["per_review"] == legacy["per_review"]          # the field checks are kept as they were
    assert legacy["all_clean"] is legacy_clean                                          # and the input is not edited


def test_a_report_that_only_claims_to_be_clean_is_not_clean():
    forged = {**causal.not_run(), "all_clean": True}
    assert causal.composite_attestation(_legacy(True), forged)["all_clean"] is False
    odd = {**PASSED, "all_clean": False}
    assert causal.composite_attestation(_legacy(True), odd)["all_clean"] is False
    assert causal.not_run() == causal.not_run() and causal.not_run() is not causal.not_run()


def test_the_three_causal_statuses_say_what_they_allow():
    assert set(causal.CAUSAL_STATUS_MEANING) == {"PASS", "FAIL", "NOT_RUN"}
    assert "causally attested" in causal.CAUSAL_STATUS_MEANING["PASS"] and "subject to the other evidence gates" in causal.CAUSAL_STATUS_MEANING["PASS"]
    assert "not valid for causal evidence claims" in causal.CAUSAL_STATUS_MEANING["FAIL"]
    assert "not causally attested" in causal.CAUSAL_STATUS_MEANING["NOT_RUN"] and "savings claim" in causal.CAUSAL_STATUS_MEANING["NOT_RUN"]
