"""The canonical temporal contract (HARDENING V1, H1b): a fact enters a decision only if the operator
could have known it before the decision — `source_known_at < decision_at` — whatever the event time and
whatever the import time.

    event_at          when it happened / becomes effective
    source_known_at   when the operator could have known it
    imported_at       when ZAAD received the row: never causality

Rows without a knowledge time use the labelled date-only fallback (known from the start of their date),
which keeps the H1a receipt rule exactly. Future-effective rows (promotions) without one have no
knowledge time: a historical build leaves them out, a live build keeps them and says so.

`decision_at` (the causal cutoff) is distinct from the planning period origin (`Request.as_of`, the
Monday). The temporal helper takes any exact cutoff; the weekly workspace reconstructs its physical state
at the period origin and therefore accepts a decision at that boundary only (`decision_at ==
period_origin`), refusing anything else rather than pairing Monday's state with Wednesday's knowledge.

Crafted rows go into the SYNTHETIC sample vault inside a transaction that is rolled back."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone

import duckdb
import pandas as pd
import pytest

from api.routers.intake import load_fmcg_sample_into
from scripts.setup_db import setup_db
from zaad.full import causal, temporal
from zaad.full.workspace import build_request, receipts_available_before

OP = "tenant_test"
SKU = "SKU-0001"
T = date(2024, 9, 2)                                          # a Monday inside the sample's history
ORIGIN = datetime(2024, 9, 2, tzinfo=timezone.utc)
UTC = timezone.utc


@pytest.fixture(scope="module")
def vault():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    load_fmcg_sample_into(conn, seed=7, archetype="A_stable")
    yield conn
    conn.close()


@contextmanager
def _rows(conn, pos=(), receipts=(), promotions=(), orders=()):
    """Insert crafted facts (po_id, po_date, qty[, event_at, source_known_at]) etc., yield, roll back."""
    supplier = conn.execute("SELECT supplier_id FROM stg_fmcg_skus WHERE sku = ?", [SKU]).fetchone()[0]
    conn.execute("BEGIN TRANSACTION")
    try:
        for po_id, po_date, qty, *ts in pos:
            event, known = (ts + [None, None])[:2]
            conn.execute("INSERT INTO stg_fmcg_purchase_orders (po_id, po_date, supplier_id, sku, qty_ordered, unit_cost, event_at, source_known_at) VALUES (?, ?, ?, ?, ?, 1.0, ?, ?)",
                         [po_id, po_date, supplier, SKU, qty, event, known])
        for po_id, when, qty, *ts in receipts:
            event, known = (ts + [None, None])[:2]
            conn.execute("INSERT INTO stg_fmcg_receipts (po_id, receipt_date, sku, qty_received, event_at, source_known_at) VALUES (?, ?, ?, ?, ?, ?)", [po_id, when, SKU, qty, event, known])
        for sku, week, uplift, known in promotions:
            conn.execute("INSERT INTO stg_fmcg_promotions (sku, week_start, uplift, source_known_at) VALUES (?, ?, ?, ?)", [sku, week, uplift, known])
        for order_id, when, qty, known in orders:
            conn.execute("INSERT INTO stg_fmcg_orders (order_id, customer_id, order_date, sku, qty_ordered, source_known_at) VALUES (?, 'c', ?, ?, ?, ?)", [order_id, when, SKU, qty, known])
        yield conn
    finally:
        conn.execute("ROLLBACK")


def _build(conn, decision_at=None, as_of=ORIGIN, **kw):
    return build_request(conn, OP, as_of=as_of, horizon=8, skus=[SKU], decision_at=decision_at, **kw)


def _po(req, po_id):
    return next((p for p in req.pipeline if p.id == po_id), None)


def _obs(req, po_id):
    return next((r for r in req.shipment_history if r.id == f"ship_{po_id}"), None)


# ── the rule itself ──────────────────────────────────────────────────────────
def test_the_three_times_are_distinct_and_only_knowledge_decides():
    cutoff = datetime(2026, 10, 1, 9, 0)
    frame = pd.DataFrame({"event_date": [date(2026, 9, 20), date(2026, 9, 20), date(2026, 10, 12), date(2026, 10, 12), date(2026, 9, 30)],
                          "source_known_at": [datetime(2026, 9, 21), datetime(2026, 10, 2), datetime(2026, 9, 25, 12), datetime(2026, 10, 3), None],
                          "imported_at": [datetime(2027, 1, 1)] * 5, "id": ["past_known", "past_late", "future_known", "future_unknown", "date_only"]})
    kept, counts = temporal.available(frame, cutoff, date_col="event_date")
    assert kept["id"].tolist() == ["past_known", "future_known", "date_only"]          # a known future event is in; a late-known past one is out
    assert kept.set_index("id")[temporal.BASIS].to_dict() == {"past_known": temporal.EXPLICIT_SOURCE_KNOWN, "future_known": temporal.EXPLICIT_SOURCE_KNOWN, "date_only": temporal.DATE_ONLY_FALLBACK}
    assert counts == {"explicit_source_known": 2, "date_only_fallback": 1, "excluded_not_known": 2, "knowledge_time_unavailable": 0}
    # without the fallback, a row with no knowledge time is simply not known
    kept2, counts2 = temporal.available(frame, cutoff, date_col="event_date", fallback=False)
    assert kept2["id"].tolist() == ["past_known", "future_known"] and counts2["knowledge_time_unavailable"] == 1 and counts2["excluded_not_known"] == 2
    # the date-only fallback is the start of the date: a date equal to the decision day is not known at a start-of-day decision
    same_day = pd.DataFrame({"event_date": [date(2026, 10, 1), date(2026, 9, 30)], "source_known_at": [None, None]})
    assert temporal.available(same_day, datetime(2026, 10, 1), date_col="event_date")[0]["event_date"].tolist() == [date(2026, 9, 30)]
    assert temporal.available(same_day, datetime(2026, 10, 1, 9), date_col="event_date")[0]["event_date"].tolist() == [date(2026, 10, 1), date(2026, 9, 30)]


def test_the_causal_harness_has_the_canonical_rule_beside_the_legacy_one():
    noon = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
    fact = {"receipt_date": date(2026, 10, 7), "source_known_at": datetime(2026, 10, 7, 10, 5)}
    assert causal.canonical_receipt_availability(fact, noon) is True
    assert causal.canonical_receipt_availability({**fact, "source_known_at": datetime(2026, 10, 7, 13, 0)}, noon) is False
    assert causal.canonical_receipt_availability({"receipt_date": date(2026, 10, 7), "source_known_at": None}, noon) is True     # date-only: known from 00:00
    assert causal.canonical_receipt_availability({"receipt_date": date(2026, 10, 7)}, datetime(2026, 10, 7, tzinfo=UTC)) is False
    assert causal.legacy_date_only_receipt_availability({"receipt_date": date(2026, 10, 7)}, noon) is False                    # the legacy rule looks at the date only
    assert causal.canonical_receipt_availability.label.startswith("CANONICAL") and causal.legacy_date_only_receipt_availability.label.startswith("LEGACY")


# ── receipts: exact knowledge time, date-only fallback, legacy compatibility ──
def test_a_past_receipt_known_before_the_decision_is_in_and_one_known_after_is_out(vault):
    pos = [("H1B-KNOWN", T - timedelta(days=14), 100.), ("H1B-LATE", T - timedelta(days=14), 100.)]
    receipts = [("H1B-KNOWN", T - timedelta(days=3), 100., datetime(2024, 8, 30, 10), datetime(2024, 8, 30, 10, 5)),
                ("H1B-LATE", T - timedelta(days=3), 100., datetime(2024, 8, 30, 10), datetime(2024, 9, 3, 8))]      # happened before T, posted after
    with _rows(vault, pos, receipts) as conn:
        req, build = _build(conn)
    assert _po(req, "H1B-KNOWN") is None and _obs(req, "H1B-KNOWN").arrived is True and _obs(req, "H1B-KNOWN").accepted_ratio == 1.0
    assert _obs(req, "H1B-KNOWN").known_at == datetime(2024, 8, 30, 10, 5, tzinfo=UTC)                 # the observation is known when the receipt was
    late = _po(req, "H1B-LATE")
    assert late is not None and late.received == 0. and late.remaining == 100. and _obs(req, "H1B-LATE").arrived is False
    assert build["temporal"]["receipts"]["explicit_source_known"] >= 1 and build["temporal"]["receipts"]["excluded_not_known"] >= 1
    # the late-known receipt row has no effect at all: the request equals one built without it
    with _rows(vault, pos, receipts[:1]) as conn:
        without, _ = _build(conn)
    assert req.model_dump_json() == without.model_dump_json()


def test_exact_knowledge_timestamps_are_judged_against_the_period_boundary(vault):
    """Decision at Monday 00:00:00Z (the only decision the weekly workspace builds). The same receipt, same
    event time, three knowledge times: Sunday 22:05 is in; Monday 00:00:00 and 00:00:01 are out - the
    inequality is strict, and the calendar date of the receipt plays no part once a knowledge time exists."""
    event = datetime(2024, 9, 1, 22, 0)
    cases = {"A": datetime(2024, 9, 1, 22, 5), "B": datetime(2024, 9, 2, 0, 0, 0), "C": datetime(2024, 9, 2, 0, 0, 1)}
    built = {}
    for name, known in cases.items():
        with _rows(vault, [(f"H1B-{name}", T - timedelta(days=14), 100.)], [(f"H1B-{name}", T - timedelta(days=1), 100., event, known)]) as conn:
            built[name] = _build(conn)[0]
    assert _po(built["A"], "H1B-A") is None and _obs(built["A"], "H1B-A").accepted_ratio == 1.0
    assert _obs(built["A"], "H1B-A").known_at == datetime(2024, 9, 1, 22, 5, tzinfo=UTC)
    for name in ("B", "C"):
        assert _po(built[name], f"H1B-{name}") is not None and _po(built[name], f"H1B-{name}").received == 0.
        assert _obs(built[name], f"H1B-{name}").arrived is False
    assert built["A"].model_dump_json() != built["B"].model_dump_json()           # the receipt date is Sunday in all three


def test_the_temporal_helper_takes_any_exact_cutoff_but_the_workspace_builds_period_boundaries_only():
    """The engine is general (a noon cutoff works on the pure helper); the weekly workspace is not yet, and
    says so instead of building a Monday physical state with a Wednesday's knowledge."""
    noon = datetime(2026, 10, 7, 12, 0)
    frame = pd.DataFrame({"receipt_date": [date(2026, 10, 7)] * 2, "source_known_at": [datetime(2026, 10, 7, 10, 5), datetime(2026, 10, 7, 13, 0)], "id": ["known_1005", "known_1300"]})
    kept, counts = temporal.available(frame, noon, date_col="receipt_date")
    assert kept["id"].tolist() == ["known_1005"] and counts["excluded_not_known"] == 1


def test_the_date_only_fallback_keeps_the_h1a_boundary(vault):
    pos = [("H1B-BEFORE", T - timedelta(days=14), 100.), ("H1B-ON", T - timedelta(days=14), 100.), ("H1B-AFTER", T - timedelta(days=14), 100.)]
    with _rows(vault, pos, [("H1B-BEFORE", T - timedelta(days=1), 100.), ("H1B-ON", T, 100.), ("H1B-AFTER", T + timedelta(days=1), 100.)]) as conn:
        req, build = _build(conn)
    assert _po(req, "H1B-BEFORE") is None and _obs(req, "H1B-BEFORE").accepted_ratio == 1.0
    assert _po(req, "H1B-ON") is not None and _po(req, "H1B-ON").received == 0.
    assert _po(req, "H1B-AFTER") is not None and _po(req, "H1B-AFTER").received == 0.
    assert build["temporal"]["receipts"]["date_only_fallback"] >= 1 and build["temporal"]["ingestion_time_used"] is False
    frame = pd.DataFrame({"po_id": ["a", "b", "c"], "receipt_date": pd.to_datetime([T - timedelta(days=1), T, T + timedelta(days=1)]), "qty_received": [1., 2., 3.]})
    assert receipts_available_before(frame, pd.Timestamp(T))["po_id"].tolist() == ["a"]


def test_ingestion_time_is_never_causality(vault):
    pos = [("H1B-ING", T - timedelta(days=14), 100.)]
    with _rows(vault, pos, [("H1B-ING", T - timedelta(days=3), 100.)]) as conn:
        base = causal.fingerprint(_build(conn)[0])
        conn.execute("UPDATE stg_fmcg_receipts SET imported_at = TIMESTAMP '2024-09-30 00:00:00' WHERE po_id = 'H1B-ING'")   # imported long after T
        conn.execute("UPDATE stg_fmcg_purchase_orders SET imported_at = TIMESTAMP '2024-09-30 00:00:00' WHERE po_id = 'H1B-ING'")
        assert causal.fingerprint(_build(conn)[0]) == base
        conn.execute("UPDATE stg_fmcg_receipts SET imported_at = TIMESTAMP '2024-01-01 00:00:00' WHERE po_id = 'H1B-ING'")   # or long before
        assert causal.fingerprint(_build(conn)[0]) == base


def test_moving_only_the_knowledge_time_across_the_cutoff_changes_the_request_and_only_the_event_time_changes_the_lead(vault):
    pos = [("H1B-J", T - timedelta(days=14), 100.)]
    before = (T - timedelta(days=3), 100., datetime(2024, 8, 30, 10), datetime(2024, 9, 1, 23, 59, 59))
    after = (T - timedelta(days=3), 100., datetime(2024, 8, 30, 10), datetime(2024, 9, 2, 0, 0, 1))
    with _rows(vault, pos, [("H1B-J", *before)]) as conn:
        known, _ = _build(conn)
    with _rows(vault, pos, [("H1B-J", *after)]) as conn:
        unknown, _ = _build(conn)
    assert _po(known, "H1B-J") is None and _po(unknown, "H1B-J") is not None                     # J: the knowledge time moved across T
    # K: the event time moves (the receipt day), the knowledge time does not: the observation changes only where the event is decision-relevant (the lead)
    with _rows(vault, pos, [("H1B-J", T - timedelta(days=5), 100., datetime(2024, 8, 28, 10), datetime(2024, 9, 1, 23, 59, 59))]) as conn:
        earlier_event, _ = _build(conn)
    a, b = _obs(known, "H1B-J"), _obs(earlier_event, "H1B-J")
    assert a.known_at == b.known_at and a.elapsed_days == 11 and b.elapsed_days == 9 and a.accepted_ratio == b.accepted_ratio


# ── future-effective facts: promotions ───────────────────────────────────────
def test_a_promotion_is_available_when_it_was_known_before_the_decision_whatever_its_date(vault):
    week = T + timedelta(days=14)
    with _rows(vault, promotions=[(SKU, week, 1.4, datetime(2024, 8, 26, 9))]) as conn:          # announced a week before T, effective two weeks after
        req, build = _build(conn)
    assert [(e.start, e.multiplier, e.known_at) for e in req.events] == [(2, 1.4, datetime(2024, 8, 26, 9, tzinfo=UTC))]
    assert build["temporal"]["promotions"]["explicit_source_known"] == 1
    with _rows(vault, promotions=[(SKU, week, 1.4, datetime(2024, 9, 2, 9))]) as conn:           # announced after the decision
        later, build2 = _build(conn)
    assert later.events == () and build2["temporal"]["promotions"]["excluded_not_known"] == 1


def test_a_promotion_without_a_knowledge_time_is_not_historical_evidence_but_still_plans_live(vault):
    week = T + timedelta(days=14)
    with _rows(vault, promotions=[(SKU, week, 1.4, None)]) as conn:
        historical, build = _build(conn)
    assert historical.events == ()
    assert build["temporal"]["promotions"] == {"explicit_source_known": 0, "date_only_fallback": 0, "excluded_not_known": 0, "knowledge_time_unavailable": 1, "included_live_unproven": 0}
    # a live build (no decision date given) keeps it, labelled as unproven knowledge
    live_origin = vault.execute("SELECT MAX(order_date) FROM stg_fmcg_orders").fetchone()[0]
    live_origin = pd.Timestamp(live_origin) + pd.Timedelta(days=7)
    live_origin = (live_origin - pd.Timedelta(days=live_origin.weekday())).normalize()
    with _rows(vault, promotions=[(SKU, (live_origin + pd.Timedelta(days=7)).date(), 1.4, None)]) as conn:
        live, build_live = build_request(conn, OP, horizon=8, skus=[SKU])
    assert build_live["temporal"]["mode"] == "live" and build_live["temporal"]["promotions"]["included_live_unproven"] == 1
    assert [(e.start, e.multiplier) for e in live.events] == [(1, 1.4)]


# ── orders: late-known demand ───────────────────────────────────────────────
def test_a_customer_order_posted_after_the_decision_is_not_in_the_history(vault):
    with _rows(vault, orders=[("H1B-O1", T - timedelta(days=3), 5000., datetime(2024, 8, 30, 9)), ("H1B-O2", T - timedelta(days=3), 5000., datetime(2024, 9, 5, 9))]) as conn:
        req, build = _build(conn)
    with _rows(vault, orders=[("H1B-O1", T - timedelta(days=3), 5000., datetime(2024, 8, 30, 9))]) as conn:
        only_known, _ = _build(conn)
    assert req.model_dump_json() == only_known.model_dump_json()
    assert build["temporal"]["orders"]["explicit_source_known"] == 1 and build["temporal"]["orders"]["excluded_not_known"] >= 1


# ── decision_at vs period origin ─────────────────────────────────────────────
def test_decision_at_must_be_the_period_origin(vault):
    from zaad.full.workspace import WorkspaceError
    req, build = _build(vault)
    assert build["temporal"]["decision_at"] == "2024-09-02T00:00:00+00:00" and build["temporal"]["decision_basis"] == "start_of_planning_period"
    assert build["temporal"]["supported_mode"] == "PERIOD_BOUNDARY" and build["temporal"]["period_origin"] == "2024-09-02" and req.as_of == ORIGIN
    explicit, build2 = _build(vault, decision_at=ORIGIN)                                            # A: explicit, equal to the origin
    assert build2["temporal"]["decision_basis"] == "explicit" and explicit.model_dump_json() == req.model_dump_json()
    for bad in (ORIGIN + timedelta(seconds=1), ORIGIN - timedelta(seconds=1), ORIGIN + timedelta(days=7), datetime(2024, 9, 4, 9, 0, tzinfo=UTC)):
        with pytest.raises(WorkspaceError, match="period boundary"):                                 # B, C, D: refused, not rounded
            _build(vault, decision_at=bad)


def test_included_facts_keep_their_real_knowledge_time_in_the_request(vault):
    """No backdating: every fact-derived record carries the fact's own source_known_at (or, for date-only
    rows, the start of the fact's date), never a value moved earlier to fit the request."""
    pos = [("H1B-NB1", T - timedelta(days=20), 100., datetime(2024, 8, 13, 14, 30), datetime(2024, 8, 13, 14, 31)),
           ("H1B-NB2", T - timedelta(days=9), 100.)]
    receipts = [("H1B-NB1", T - timedelta(days=4), 100., datetime(2024, 8, 29, 7), datetime(2024, 8, 29, 7, 30)),
                ("H1B-NB2", T - timedelta(days=2), 60.)]
    with _rows(vault, pos, receipts) as conn:
        req, _ = _build(conn)
    nb1, nb2 = _obs(req, "H1B-NB1"), _obs(req, "H1B-NB2")
    assert nb1.known_at == datetime(2024, 8, 29, 7, 30, tzinfo=UTC) and nb2.known_at == datetime(2024, 8, 31, tzinfo=UTC)
    with _rows(vault, [("H1B-NB3", T - timedelta(days=5), 100., datetime(2024, 8, 28, 16, 0), datetime(2024, 8, 28, 16, 2))]) as conn:
        req2, _ = _build(conn)
    open_po = _po(req2, "H1B-NB3")
    assert open_po.known_at == datetime(2024, 8, 28, 16, 2, tzinfo=UTC) and open_po.placed_at == datetime(2024, 8, 28, 16, 0, tzinfo=UTC)
    # derived records keep the derived convention and are not given invented precision; nothing is capped to fit
    assert all(s.known_at == ORIGIN - timedelta(seconds=1) for s in req.skus) and all(h.known_at == ORIGIN - timedelta(seconds=1) for h in req.history)
    assert all(r.known_at < req.as_of for r in (*req.pipeline, *req.shipment_history, *req.events))


def test_same_day_receipt_at_a_period_boundary_decision(vault):
    """What the weekly workspace states today, at a Monday 00:00 decision: a date-only Monday receipt is
    not opening state; a knowledge time before Monday 00:00 may make it available; one at or after is
    not. Whether that receipt arrives physically during period 0 is not represented yet (deferred)."""
    pos = [("H1B-SD1", T - timedelta(days=14), 100.), ("H1B-SD2", T - timedelta(days=14), 100.), ("H1B-SD3", T - timedelta(days=14), 100.)]
    receipts = [("H1B-SD1", T, 100.), ("H1B-SD2", T, 100., datetime(2024, 9, 1, 23, 0), datetime(2024, 9, 1, 23, 10)), ("H1B-SD3", T, 100., datetime(2024, 9, 2, 8, 0), datetime(2024, 9, 2, 8, 5))]
    with _rows(vault, pos, receipts) as conn:
        req, _ = _build(conn)
    assert _po(req, "H1B-SD1") is not None and _po(req, "H1B-SD1").received == 0.
    assert _po(req, "H1B-SD2") is None and _obs(req, "H1B-SD2").known_at == datetime(2024, 9, 1, 23, 10, tzinfo=UTC)
    assert _po(req, "H1B-SD3") is not None and _po(req, "H1B-SD3").received == 0.


# ── the harness on the production builder: legacy and canonical families both pass ──
def test_both_receipt_families_pass_on_the_production_builder(vault):
    build = lambda conn: _build(conn)[0]   # noqa: E731
    for rule in (causal.legacy_date_only_receipt_availability, causal.canonical_receipt_availability):
        report = causal.run_causal_checks(build, vault, causal.receipt_perturbations(ORIGIN, is_available_at=rule))
        assert report["status"] == "PASS" and report["failures"] == [], (rule.label, report["failures"])
        assert {f["family"]: f["variants_checked"] for f in report["families"]} == {causal.FUTURE_RECEIPTS: 4, "past_receipts": 1}
