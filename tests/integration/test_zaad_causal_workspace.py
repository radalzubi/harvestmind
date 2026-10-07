"""The canonical fingerprint and the causal harness against the production workspace builder (H0).

What is asserted about `zaad.full.workspace.build_request` here is only what holds today and must keep
holding: a stable hash, independence from row order and from import metadata, and a request that does
change when a fact dated before the decision time changes. Since H1a, a receipt dated at or after the
decision time must not change the request, and the harness asserts it on the production builder.
`scripts/demo_causal_attestation.py` prints the same check on the synthetic sample."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import duckdb
import pytest

from synthetic.fmcg.distributor_sim import ARCHETYPES, ArchetypeSpec, build_history
from zaad.full import causal
from zaad.full.workspace import build_request

OPERATOR = "causal_test_operator"
TABLES = ("stg_fmcg_skus", "stg_fmcg_orders", "stg_fmcg_purchase_orders", "stg_fmcg_receipts", "stg_fmcg_inventory",
          "stg_fmcg_promotions", "stg_fmcg_suppliers", "stg_fmcg_economics")      # every table the default build reads


@pytest.fixture(scope="module")
def vault():
    from scripts.setup_db import setup_db
    conn = duckdb.connect()
    setup_db(conn=conn)
    spec = ArchetypeSpec(**{**ARCHETYPES["A_stable"].__dict__, "n_skus": 4, "n_suppliers": 2, "n_customers": 4, "weeks": 70})
    hist = build_history("A_stable", seed=11, spec=spec)
    orders = hist.order_lines.merge(hist.customer_orders[["order_id", "customer_id", "order_date"]], on="order_id")
    frames = {"stg_fmcg_skus": hist.skus[["sku", "supplier_id", "unit_cost", "unit_price", "units_per_case", "moq_units"]],
              "stg_fmcg_orders": orders[["order_id", "customer_id", "order_date", "sku", "qty_ordered"]],
              "stg_fmcg_purchase_orders": hist.purchase_orders[["po_id", "po_date", "supplier_id", "sku", "qty_ordered", "unit_cost"]],
              "stg_fmcg_receipts": hist.receipts[["po_id", "receipt_date", "sku", "qty_received"]],
              "stg_fmcg_inventory": hist.inventory_snapshots.rename(columns={"week_start": "snapshot_date"})[["snapshot_date", "sku", "on_hand", "in_transit"]]}
    for table, frame in frames.items():
        conn.register("frame_", frame)
        conn.execute(f"INSERT INTO {table} ({', '.join(frame.columns)}) SELECT * FROM frame_")
        conn.unregister("frame_")
    last = conn.execute("SELECT MAX(order_date) FROM stg_fmcg_orders").fetchone()[0]
    as_of = datetime(last.year, last.month, last.day, tzinfo=timezone.utc) - timedelta(weeks=14)
    first_rows = {t: row[0] for t in TABLES if (row := conn.execute(f"SELECT * FROM {t} LIMIT 1").fetchone()) is not None}
    yield {"conn": conn, "as_of": as_of, "first_rows": first_rows}
    conn.close()


def _builder(as_of):
    return lambda conn: build_request(conn, OPERATOR, as_of=as_of, horizon=8)[0]


def test_the_same_vault_and_decision_time_give_the_same_hash(vault):
    build = _builder(vault["as_of"])
    first, second = causal.fingerprint(build(vault["conn"])), causal.fingerprint(build(vault["conn"]))
    assert first == second and first.projection_version == causal.PROJECTION_VERSION


def _permute(conn, order_by: str) -> dict[str, int]:
    """Physically reorder every populated source table; returns the row counts of the tables that moved."""
    moved = {}
    for table in TABLES:
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        if n < 2:
            continue
        conn.execute(f"CREATE TEMP TABLE reordered_ AS SELECT * FROM {table} ORDER BY {order_by}")
        conn.execute(f"DELETE FROM {table}")
        conn.execute(f"INSERT INTO {table} SELECT * FROM reordered_")
        conn.execute("DROP TABLE reordered_")
        moved[table] = n
    return moved


@pytest.mark.parametrize("order_by", ["rowid DESC", "md5(CAST(rowid AS VARCHAR))"])
def test_physical_row_order_of_the_source_tables_does_not_reach_the_request(vault, order_by):
    """H1c: the same vault rows in another physical order give the exact same request — the same canonical
    projection, list order included, and therefore the same fingerprint. Nothing is normalised in the
    comparison; the production builder itself emits the canonical order."""
    from zaad.full.worlds import draw
    conn, build = vault["conn"], _builder(vault["as_of"])
    base = build(conn)
    base_projection, base_print = causal.canonical_projection(base), causal.fingerprint(base)
    conn.execute("BEGIN TRANSACTION")
    try:
        moved = _permute(conn, order_by)
        # the permutation is real: a populated table's first row changed
        first_sku_before = vault["first_rows"]["stg_fmcg_purchase_orders"]
        first_sku_after = conn.execute("SELECT po_id FROM stg_fmcg_purchase_orders LIMIT 1").fetchone()[0]
        other = build(conn)
    finally:
        conn.execute("ROLLBACK")
    assert len(moved) >= 4 and first_sku_after != first_sku_before, (moved, first_sku_before, first_sku_after)
    assert causal.canonical_projection(other) == base_projection
    assert causal.fingerprint(other) == base_print
    # and a consumer that reads the request in order gets the same thing: the seeded worlds are identical
    assert [w.demand for w in draw(other, 7, 3)] == [w.demand for w in draw(base, 7, 3)]
    assert causal.fingerprint(build(conn)) == base_print                          # the vault is as it was


def test_import_metadata_is_not_part_of_the_request(vault):
    conn, build = vault["conn"], _builder(vault["as_of"])

    def restamp(c) -> int:
        changed = 0
        for table in TABLES:
            columns = {r[0] for r in c.execute(f"DESCRIBE {table}").fetchall()}
            sets = [f"{col} = {value}" for col, value in (("imported_at", "TIMESTAMP '2031-01-01 12:00:00'"), ("_uploaded_at", "TIMESTAMP '2031-01-01 12:00:00'"),
                                                           ("_upload_session_id", "'another-session'"), ("_source_file", "'another-file.csv'")) if col in columns]
            if sets:
                c.execute(f"UPDATE {table} SET {', '.join(sets)}")
                changed += c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        return changed
    report = causal.run_causal_checks(build, conn, [causal.Perturbation("restamp import time, upload session and source file", "import_metadata", "negative", causal.in_transaction(restamp))])
    assert report["status"] == "PASS" and report["variants_checked"] == 1, report


def test_a_fact_dated_before_the_decision_time_changes_the_request(vault):
    conn, build, day = vault["conn"], _builder(vault["as_of"]), vault["as_of"].date()

    def demand(c) -> int:
        n = c.execute("SELECT COUNT(*) FROM stg_fmcg_orders WHERE order_date < ? AND order_date >= ?", [day, day - timedelta(days=28)]).fetchone()[0]
        c.execute("UPDATE stg_fmcg_orders SET qty_ordered = qty_ordered * 2 WHERE order_date < ? AND order_date >= ?", [day, day - timedelta(days=28)])
        return n
    positives = [p for p in causal.receipt_perturbations(build(conn).as_of, is_available_at=causal.legacy_date_only_receipt_availability) if p.control == "positive"]
    positives.append(causal.Perturbation("double the orders of the four weeks before T", "past_demand", "positive", causal.in_transaction(demand)))
    report = causal.run_causal_checks(build, conn, positives)
    assert report["status"] == "PASS" and report["variants_checked"] == 2 and report["vacuous"] == 0, report


def test_when_a_supplier_observation_became_known_is_part_of_the_request(vault):
    req = _builder(vault["as_of"])(vault["conn"])
    row = req.shipment_history[0]
    earlier = req.model_copy(update={"shipment_history": (row.model_copy(update={"known_at": row.known_at - timedelta(days=1)}), *req.shipment_history[1:])})
    assert causal.fingerprint(earlier).hash != causal.fingerprint(req).hash
    assert causal.first_difference(req, earlier)["path"] == f"shipment_history[id={row.id}].known_at"


def test_the_receipt_family_passes_on_the_production_builder_and_leaves_the_vault_as_it_was(vault):
    """The harness end to end on the real builder (H1a): receipts not available at T, on orders placed
    before T, may be deleted, re-quantified, re-dated or added without changing the request; a receipt
    that was available still changes it; and the vault is exactly as it was. Availability is the labelled
    date-only rule: the vault has no source knowledge time for receipts."""
    conn, build = vault["conn"], _builder(vault["as_of"])
    before_rows = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES}
    before = causal.fingerprint(build(conn))
    report = causal.run_causal_checks(build, conn, causal.receipt_perturbations(build(conn).as_of, is_available_at=causal.legacy_date_only_receipt_availability))
    assert report["status"] == "PASS" and report["all_clean"] is True, report["failures"]
    assert report["failures"] == [] and report["base_request_hash"] == before.hash
    assert report["decision_at"] == build(conn).as_of.isoformat() and report["projection_version"] == causal.PROJECTION_VERSION
    families = {f["family"]: f for f in report["families"]}
    assert families[causal.FUTURE_RECEIPTS]["variants_checked"] == 4 and families[causal.FUTURE_RECEIPTS]["vacuous"] == 0
    assert families[causal.FUTURE_RECEIPTS]["failures"] == 0
    assert families[causal.FUTURE_RECEIPTS]["availability_rules"] == [causal.LEGACY_DATE_ONLY]
    assert families["past_receipts"]["variants_checked"] == 1 and families["past_receipts"]["failures"] == 0
    assert {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES} == before_rows
    assert causal.fingerprint(build(conn)) == before
