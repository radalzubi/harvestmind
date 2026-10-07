"""Canonical row order of the workspace request (HARDENING V1, H1c).

The vault's physical row order is not business state. Every semantically unordered collection of the
request is emitted in the order of its own identifiers (`workspace.canonical_rows`), so the same facts
give the same request — and, since sequence order is part of the causal identity (H0), the same
fingerprint — whatever order the tables were read in. Positional sequences keep their order.

Crafted rows are inserted into the SYNTHETIC sample vault inside a transaction and rolled back."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone

import duckdb
import pytest

from api.routers.intake import load_fmcg_sample_into
from scripts.setup_db import setup_db
from zaad.full import causal
from zaad.full.workspace import build_request

OP = "tenant_test"
ORIGIN = datetime(2024, 9, 2, tzinfo=timezone.utc)
T = date(2024, 9, 2)
SKUS = ["SKU-0001", "SKU-0002", "SKU-0003", "SKU-0004"]


@pytest.fixture(scope="module")
def vault():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    load_fmcg_sample_into(conn, seed=7, archetype="A_stable")
    yield conn
    conn.close()


@contextmanager
def _transaction(conn):
    conn.execute("BEGIN TRANSACTION")
    try:
        yield conn
    finally:
        conn.execute("ROLLBACK")


def _supplier(conn, sku):
    return conn.execute("SELECT supplier_id FROM stg_fmcg_skus WHERE sku = ?", [sku]).fetchone()[0]


def _build(conn, **kw):
    return build_request(conn, OP, as_of=ORIGIN, horizon=8, skus=SKUS, **kw)[0]


def _reverse_tables(conn, tables):
    for table in tables:
        conn.execute(f"CREATE TEMP TABLE reordered_ AS SELECT * FROM {table} ORDER BY rowid DESC")
        conn.execute(f"DELETE FROM {table}")
        conn.execute(f"INSERT INTO {table} SELECT * FROM reordered_")
        conn.execute("DROP TABLE reordered_")


def test_every_unordered_collection_is_in_its_canonical_order(vault):
    req = _build(vault)
    for name in ("skus", "sources", "services", "terms", "resources", "supplier_terms"):
        ids = [r.id for r in getattr(req, name)]
        assert ids == sorted(ids), name
    assert [(h.service, h.period) for h in req.history] == sorted((h.service, h.period) for h in req.history)
    assert [(s.location, s.sku, s.id) for s in req.stock] == sorted((s.location, s.sku, s.id) for s in req.stock)
    assert [(p.placed_at, p.id) for p in req.pipeline] == sorted((p.placed_at, p.id) for p in req.pipeline)
    assert [(e.start, e.end, e.service, e.id) for e in req.events] == sorted((e.start, e.end, e.service, e.id) for e in req.events)
    # shipment history: grouped by source in source order, each group by (known_at, id)
    assert [(r.source, r.known_at, r.id) for r in req.shipment_history] == sorted((r.source, r.known_at, r.id) for r in req.shipment_history)
    assert len(req.skus) == 4 and len(req.pipeline) >= 1 and len(req.shipment_history) >= 4 and len(req.stock) >= 1
    # positional sequences are not sorted
    src = req.sources[0]
    assert src.route == (src.supplier, src.destination) and len(src.capacity_by_period) == req.horizon


def test_shipment_history_ties_on_known_at_and_the_compaction_are_deterministic(vault):
    """Five orders placed the same day and not yet received share one known_at (the origin). Their order
    and, when only three observations per source are kept, which three survive, follow the id and not
    the insertion order."""
    sup = _supplier(vault, "SKU-0001")
    ids = ["TIE-C", "TIE-A", "TIE-E", "TIE-B", "TIE-D"]

    def build_with(insertion_order, keep):
        with _transaction(vault) as conn:
            for po_id in insertion_order:
                conn.execute("INSERT INTO stg_fmcg_purchase_orders (po_id, po_date, supplier_id, sku, qty_ordered, unit_cost) VALUES (?, ?, ?, 'SKU-0001', 100, 1.0)",
                             [po_id, T - timedelta(days=20), sup])
            req = _build(conn, shipment_observations_per_source=keep)
        return [r for r in req.shipment_history if r.id.startswith("ship_TIE-")], causal.fingerprint(req)

    first, print_first = build_with(ids, keep=200)
    second, print_second = build_with(list(reversed(ids)), keep=200)
    assert [r.id for r in first] == [f"ship_TIE-{x}" for x in "ABCDE"]
    assert len({r.known_at for r in first}) == 1                                 # a genuine tie on known_at
    assert [r.id for r in second] == [r.id for r in first] and print_first == print_second
    kept_a, print_a = build_with(ids, keep=3)
    kept_b, print_b = build_with(list(reversed(ids)), keep=3)
    assert [r.id for r in kept_a] == ["ship_TIE-C", "ship_TIE-D", "ship_TIE-E"]   # the last three by (known_at, id)
    assert [r.id for r in kept_b] == [r.id for r in kept_a] and print_a == print_b


def test_pipeline_order_is_placement_date_then_id_whatever_the_insertion_order(vault):
    sup = _supplier(vault, "SKU-0002")
    rows = [("OPEN-B", T - timedelta(days=10)), ("OPEN-A", T - timedelta(days=10)), ("OPEN-Z", T - timedelta(days=17)), ("OPEN-M", T - timedelta(days=3))]

    def build_with(order):
        with _transaction(vault) as conn:
            for po_id, placed in order:
                conn.execute("INSERT INTO stg_fmcg_purchase_orders (po_id, po_date, supplier_id, sku, qty_ordered, unit_cost) VALUES (?, ?, ?, 'SKU-0002', 50, 1.0)", [po_id, placed, sup])
            req = _build(conn)
        return [p.id for p in req.pipeline if p.id.startswith("OPEN-")], causal.fingerprint(req)
    ids_a, print_a = build_with(rows)
    ids_b, print_b = build_with(list(reversed(rows)))
    assert ids_a == ["OPEN-Z", "OPEN-A", "OPEN-B", "OPEN-M"] == ids_b
    assert print_a == print_b


def test_promotions_suppliers_and_economics_physical_order_does_not_reach_the_request(vault):
    """The tables the small fixtures leave empty: promotions in scrambled order become events in
    (start, end, service, id) order, and reversing these three tables leaves the fingerprint unchanged."""
    promos = [("SKU-0003", T + timedelta(days=14), 1.5), ("SKU-0001", T + timedelta(days=14), 1.2), ("SKU-0002", T, 1.3), ("SKU-0001", T + timedelta(days=7), 1.1)]
    with _transaction(vault) as conn:
        for sku, week, uplift in promos:
            conn.execute("INSERT INTO stg_fmcg_promotions (sku, week_start, uplift) VALUES (?, ?, ?)", [sku, week, uplift])
        conn.execute("INSERT INTO stg_fmcg_economics (key, value, provenance) VALUES ('net_days', '30', 'operator'), ('handling_per_unit', '0.02', 'operator')")
        base = _build(conn)
        base_projection, base_print = causal.canonical_projection(base), causal.fingerprint(base)
        assert [(e.start, e.service) for e in base.events] == [(0, "svc_SKU-0002"), (1, "svc_SKU-0001"), (2, "svc_SKU-0001"), (2, "svc_SKU-0003")]
        assert all(s.terms for s in base.sources) and base.terms[0].net_days == 30
        _reverse_tables(conn, ["stg_fmcg_promotions", "stg_fmcg_suppliers", "stg_fmcg_economics"])
        assert conn.execute("SELECT sku FROM stg_fmcg_promotions LIMIT 1").fetchone()[0] == "SKU-0001"     # the permutation happened
        other = _build(conn)
    assert causal.canonical_projection(other) == base_projection and causal.fingerprint(other) == base_print


def test_the_fingerprint_still_distinguishes_two_orders_of_the_same_rows(vault):
    """H1c canonicalises the producer; it does not make the identity order-blind."""
    req = _build(vault)
    swapped = req.model_copy(update={"skus": (req.skus[1], req.skus[0], *req.skus[2:])})
    assert causal.fingerprint(swapped).hash != causal.fingerprint(req).hash
    assert causal.first_difference(req, swapped)["path"] == "skus<order>[0]"
