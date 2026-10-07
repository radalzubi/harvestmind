"""Point-in-time receipt reconstruction in the workspace adapter (HARDENING V1, H1a).

At a historical origin T the adapter may read only receipt rows dated before T
(`workspace.receipts_available_before`). A receipt dated at or after T is not opening state: it must not
close an order that was still open at T, not raise what the order had received, not enter a supplier fit.
This is the date-only fallback (receipt rows carry no source knowledge time); a receipt dated on the
origin day counts as not yet known at the start of that day. H1b owns the richer temporal contract.

Cases are inserted into the SYNTHETIC sample vault inside a transaction that is rolled back, so each test
sees its own rows and the shared vault is untouched."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone

import duckdb
import pandas as pd
import pytest

from api.routers.intake import load_fmcg_sample_into
from scripts.setup_db import setup_db
from zaad.full.workspace import build_request, fit_supply, receipts_available_before

OP = "tenant_test"
SKU = "SKU-0001"
ORIGIN = datetime(2024, 9, 2, tzinfo=timezone.utc)          # a Monday inside the sample's history
T = date(2024, 9, 2)


@pytest.fixture(scope="module")
def vault():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    load_fmcg_sample_into(conn, seed=7, archetype="A_stable")
    yield conn
    conn.close()


@contextmanager
def _rows(conn, pos: list[tuple], receipts: list[tuple]):
    """Insert crafted orders / receipts, yield, roll everything back."""
    supplier = conn.execute("SELECT supplier_id FROM stg_fmcg_skus WHERE sku = ?", [SKU]).fetchone()[0]
    conn.execute("BEGIN TRANSACTION")
    try:
        for po_id, po_date, qty in pos:
            conn.execute("INSERT INTO stg_fmcg_purchase_orders (po_id, po_date, supplier_id, sku, qty_ordered, unit_cost) VALUES (?, ?, ?, ?, ?, 1.0)",
                         [po_id, po_date, supplier, SKU, qty])
        for po_id, when, qty in receipts:
            conn.execute("INSERT INTO stg_fmcg_receipts (po_id, receipt_date, sku, qty_received) VALUES (?, ?, ?, ?)", [po_id, when, SKU, qty])
        yield conn
    finally:
        conn.execute("ROLLBACK")


def _build(conn):
    req, build = build_request(conn, OP, as_of=ORIGIN, horizon=8, skus=[SKU])
    return req, build


def _po(req, po_id):
    return next((p for p in req.pipeline if p.id == po_id), None)


def _obs(req, po_id):
    return next((r for r in req.shipment_history if r.id == f"ship_{po_id}"), None)


def test_the_slice_keeps_only_receipts_dated_before_the_origin():
    origin = pd.Timestamp(T)
    frame = pd.DataFrame({"po_id": ["a", "b", "c"], "receipt_date": pd.to_datetime([T - timedelta(days=1), T, T + timedelta(days=1)]), "qty_received": [1., 2., 3.]})
    kept = receipts_available_before(frame, origin)
    assert kept["po_id"].tolist() == ["a"]                                     # the day before: known; the origin day and later: not
    assert receipts_available_before(frame.iloc[0:0], origin).empty


def test_a_receipt_only_after_the_origin_leaves_the_order_open_and_unreceived(vault):
    with _rows(vault, [("H1A-FUTURE", T - timedelta(days=14), 100.)], [("H1A-FUTURE", T + timedelta(days=3), 100.)]) as conn:
        req, build = _build(conn)
    po = _po(req, "H1A-FUTURE")
    assert po is not None, "the order was still open at the origin and must be in the pipeline"
    assert po.received == 0. and po.shipped == 0. and po.remaining == 100.
    obs = _obs(req, "H1A-FUTURE")
    assert obs is not None and obs.arrived is False and obs.accepted_ratio is None     # right-censored, not a fabricated arrival
    assert build["leakage_guard"]["receipts_at_or_after_origin_excluded"] >= 1


def test_a_split_receipt_counts_only_the_part_received_before_the_origin(vault):
    """Received at T is what arrived before T (40 of 100), and the observation says so (accepted_ratio 0.4).

    Note on the pipeline: the adapter has always treated an order's first receipt as its arrival and a
    short total as a short fill (`arrived = first < origin`), so an order partly received before T is
    not carried as open inbound; that is the adapter's partial-receipt semantics, unchanged by H1a, and
    the later 60 units do not change it either way. H1a guarantees the quantities, not that reading."""
    pos = [("H1A-SPLIT", T - timedelta(days=14), 100.)]
    with _rows(vault, pos, [("H1A-SPLIT", T - timedelta(days=5), 40.), ("H1A-SPLIT", T + timedelta(days=2), 60.)]) as conn:
        req, build = _build(conn)
    obs = _obs(req, "H1A-SPLIT")
    assert obs is not None and obs.arrived is True and obs.accepted_ratio == pytest.approx(0.4)   # not 1.0
    assert obs.elapsed_days == 9 and obs.known_at < req.as_of                  # first receipt, 9 days after placement
    assert build["leakage_guard"]["receipts_at_or_after_origin_excluded"] >= 1
    with _rows(vault, pos, [("H1A-SPLIT", T - timedelta(days=5), 40.)]) as conn:
        same_without_future, _ = _build(conn)
    assert (_po(req, "H1A-SPLIT") is None) == (_po(same_without_future, "H1A-SPLIT") is None)   # the later receipt decides nothing


def test_a_receipt_dated_on_the_origin_day_is_not_opening_state_but_the_day_before_is(vault):
    with _rows(vault, [("H1A-SAMEDAY", T - timedelta(days=14), 100.), ("H1A-DAYBEFORE", T - timedelta(days=14), 100.)],
               [("H1A-SAMEDAY", T, 100.), ("H1A-DAYBEFORE", T - timedelta(days=1), 100.)]) as conn:
        req, _ = _build(conn)
    same = _po(req, "H1A-SAMEDAY")
    assert same is not None and same.received == 0. and same.remaining == 100.
    assert _obs(req, "H1A-SAMEDAY").arrived is False
    assert _po(req, "H1A-DAYBEFORE") is None                                  # fully received before the origin: not open
    before = _obs(req, "H1A-DAYBEFORE")
    assert before.arrived is True and before.accepted_ratio == 1.0


def test_future_receipts_do_not_change_the_request_and_past_receipts_do(vault):
    pos = [("H1A-SPLIT", T - timedelta(days=14), 100.)]
    with _rows(vault, pos, [("H1A-SPLIT", T - timedelta(days=5), 40.), ("H1A-SPLIT", T + timedelta(days=2), 60.)]) as conn:
        with_future, _ = _build(conn)
    with _rows(vault, pos, [("H1A-SPLIT", T - timedelta(days=5), 40.)]) as conn:
        without_future, _ = _build(conn)
    with _rows(vault, pos, [("H1A-SPLIT", T - timedelta(days=5), 20.)]) as conn:
        other_past, _ = _build(conn)
    assert with_future.model_dump_json() == without_future.model_dump_json()
    assert other_past.model_dump_json() != without_future.model_dump_json()
    assert _obs(other_past, "H1A-SPLIT").accepted_ratio == pytest.approx(0.2)


def test_supplier_fit_ignores_receipts_dated_at_or_after_the_origin():
    origin = pd.Timestamp(T)
    pos = pd.DataFrame({"po_id": [f"p{i}" for i in range(8)], "po_date": pd.to_datetime([T - timedelta(days=70 - 7 * i) for i in range(8)]),
                        "supplier_id": ["S"] * 8, "sku": [SKU] * 8, "qty_ordered": [100.] * 8})
    before = pd.DataFrame({"po_id": [f"p{i}" for i in range(8)], "receipt_date": pd.to_datetime([T - timedelta(days=56 - 7 * i) for i in range(8)]), "qty_received": [90.] * 8})
    clean = fit_supply(pos, before, origin, {})
    assert clean["S"]["provenance"] == "INFERRED_FROM_HISTORY" and clean["S"]["fill_mean"] == pytest.approx(0.9)
    # a second receipt for the latest order, dated after the origin, and one dated on the origin day
    later = pd.concat([before, pd.DataFrame({"po_id": ["p7", "p6"], "receipt_date": pd.to_datetime([T + timedelta(days=4), T]), "qty_received": [10., 10.]})])
    assert fit_supply(pos, later, origin, {}) == clean
    # a receipt that was known before the origin does change the fit
    earlier = pd.concat([before, pd.DataFrame({"po_id": ["p7"], "receipt_date": pd.to_datetime([T - timedelta(days=1)]), "qty_received": [10.]})])
    assert fit_supply(pos, earlier, origin, {})["S"]["fill_mean"] > clean["S"]["fill_mean"]
