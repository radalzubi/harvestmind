"""Regression (HARDENING V1, H1a): a receipt dated at or after a historical decision time does not change
the request built for that time.

Mechanism it guards, as diagnosed on the pinned demo vault at origin 2026-06-08: three orders placed on
2026-05-18 were received in two parts, one before the origin and one on 2026-06-08 / 2026-06-09. Before
H1a the adapter summed every receipt of an order whatever its date, so the shipment observation dated
before the origin carried `accepted_ratio` 1.0 instead of about 0.6, the supplier fill fitted from
orders closed before the origin used the same sums, and the operating-regime label
`supplier_deterioration` disappeared from the 2026-06-08 snapshot. H1a makes every historical receipt
aggregation read `workspace.receipts_available_before` (`receipt_date < origin`).

The invariant: facts not available at the decision time must not change the shipment observations,
the supplier-fill learning or the regime classification at that time. Fixture preconditions use
`pytest.fail` so that a broken fixture is never mistaken for a regression of the invariant. The positive
control (a receipt that was available does change the request) guards against a builder that ignores
receipts altogether.

The fixture anchor is `DEMO_AS_OF` from test_replay_scale.py: the dataset the defect was diagnosed on.
Availability is judged by receipt date because the vault has no source knowledge time for receipts
(the H1a date-only fallback, not the final temporal contract)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from tests.integration.test_replay_scale import demo_vault

ORIGIN = datetime(2026, 6, 8, tzinfo=timezone.utc)
ORIGIN_DAY = date(2026, 6, 8)
OP = "scale"


@pytest.fixture(scope="module")
def vault():
    conn = demo_vault()
    yield conn
    conn.close()


def _request(conn):
    from zaad.full.workspace import build_request
    return build_request(conn, OP, as_of=ORIGIN, horizon=12)[0]


def _split_orders(conn) -> list[str]:
    """Orders placed before the origin with a receipt before it and another at or after it."""
    rows = conn.execute("SELECT DISTINCT r.po_id FROM stg_fmcg_receipts r JOIN stg_fmcg_receipts q USING (po_id) "
                        "JOIN stg_fmcg_purchase_orders p USING (po_id) WHERE p.po_date < ? AND r.receipt_date < ? AND q.receipt_date >= ? ORDER BY 1",
                        [ORIGIN_DAY, ORIGIN_DAY, ORIGIN_DAY]).fetchall()
    return [r[0] for r in rows]


def _observed(req, po_ids):
    return {r.id: (r.known_at, r.arrived, r.accepted_ratio) for r in req.shipment_history if r.id in {f"ship_{p}" for p in po_ids}}


def _fill(req):
    return {s.id: (s.fill_mean, s.fill_sd, s.lead_days) for s in req.sources}


def _regimes(req):
    import zaad.full.historical as H
    return H._review_regimes(req)


def _in_transaction(conn, statement: str, params: list) -> int:
    """Run one change inside a transaction, rebuild, roll back; returns (request, rows changed)."""
    n = conn.execute("SELECT COUNT(*) FROM stg_fmcg_receipts WHERE " + statement.split(" WHERE ", 1)[1], params).fetchone()[0]
    conn.execute("BEGIN TRANSACTION")
    try:
        conn.execute(statement, params)
        req = _request(conn)
    finally:
        conn.execute("ROLLBACK")
    return req, n


FUTURE = "receipt_date >= ? AND po_id IN (SELECT po_id FROM stg_fmcg_purchase_orders WHERE po_date < ?)"


def _preconditions(conn, before, split):
    """Everything the regression relies on, checked with pytest.fail so that a broken fixture is reported as
    a fixture problem and not as a regression of the invariant."""
    if len(split) != 3:
        pytest.fail(f"expected the three split orders of the pinned demo vault, found {split}")
    seen = _observed(before, split)
    if set(seen) != {f"ship_{p}" for p in split}:
        pytest.fail(f"split orders missing from shipment_history: {set(seen)}")
    if not all(arrived and known_at < ORIGIN for known_at, arrived, _ in seen.values()):
        pytest.fail(f"split orders are not arrived-before-origin observations: {seen}")
    if not before.pipeline or not before.history:
        pytest.fail("the request is empty")


@pytest.mark.parametrize("change, statement", [
    ("delete", f"DELETE FROM stg_fmcg_receipts WHERE {FUTURE}"),
    ("halve", f"UPDATE stg_fmcg_receipts SET qty_received = qty_received * 0.5 WHERE {FUTURE}"),
])
def test_receipts_after_the_origin_do_not_change_fill_observations_learning_or_regimes(vault, change, statement):
    before = _request(vault)
    split = _split_orders(vault)
    _preconditions(vault, before, split)
    after, changed = _in_transaction(vault, statement, [ORIGIN_DAY, ORIGIN_DAY])
    if changed == 0:
        pytest.fail("no receipt dated at or after the origin on an order placed before it: nothing was perturbed")
    # the invariant, reported as one verdict so the failure names every path the later receipts reached
    differences = {
        "accepted_ratio of orders received partly after the origin": (_observed(before, split), _observed(after, split)),
        "supplier fill learning (fill_mean, fill_sd, lead_days per source)": (
            {k: v for k, v in _fill(before).items() if v != _fill(after).get(k)}, {k: v for k, v in _fill(after).items() if v != _fill(before).get(k)}),
        "regime labels": (_regimes(before), _regimes(after)),
    }
    changed_paths = {name: pair for name, pair in differences.items() if pair[0] != pair[1]}
    assert not changed_paths, f"{change} of {changed} receipt row(s) dated at or after the origin changed: {changed_paths}"


def test_a_receipt_available_before_the_origin_changes_the_request(vault):
    """Positive control: the builder does read receipts that were available, so the negative result above is
    not a builder that ignores receipts altogether."""
    before = _request(vault)
    since = ORIGIN_DAY - timedelta(days=56)
    after, changed = _in_transaction(vault, "UPDATE stg_fmcg_receipts SET qty_received = qty_received * 0.5 WHERE receipt_date < ? AND receipt_date >= ?", [ORIGIN_DAY, since])
    assert changed > 0
    assert _observed(after, [p for p in _split_orders(vault)]) != _observed(before, _split_orders(vault)) or _fill(after) != _fill(before)
    assert after.model_dump_json() != before.model_dump_json()
    assert _request(vault).model_dump_json() == before.model_dump_json()           # the rollback restored the vault
