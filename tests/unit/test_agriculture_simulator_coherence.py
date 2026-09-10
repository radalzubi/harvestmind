"""The agriculture generator must respect physical identities an operator's
books would: nothing is received that was not ordered, nothing is wasted
that was not received, dates run forward, quantities are non-negative."""
from __future__ import annotations

from datetime import date
import duckdb
import pytest

from scripts.setup_db import setup_db
from synthetic.generator import SyntheticGenerator


@pytest.fixture(scope="module")
def conn():
    c = duckdb.connect(":memory:")
    setup_db(c, load_seeds=True)
    SyntheticGenerator(start_date=date(2024, 1, 1), n_weeks=26, seed=7,
                       end_near_today=False).generate_all(c)
    return c


def _cols(conn, table):
    return {r[1] for r in conn.execute(f"PRAGMA table_info('{table}')").fetchall()}  # nosec B608 - constant


def test_tables_populated(conn):
    for t in ("fact_orders", "fact_purchase_orders", "fact_deliveries", "fact_waste_events"):
        assert conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] > 0, t  # nosec B608 - constant


def test_no_negative_quantities(conn):
    checks = [("fact_deliveries", "qty_received_kg"), ("fact_deliveries", "qty_rejected_kg"),
              ("fact_waste_events", "qty_wasted_kg"), ("fact_order_lines", "qty_ordered_kg")]
    for t, c in checks:
        if c in _cols(conn, t):
            n = conn.execute(f"SELECT COUNT(*) FROM {t} WHERE {c} < 0").fetchone()[0]  # nosec B608 - constants
            assert n == 0, (t, c)


def test_received_plus_rejected_never_exceeds_ordered(conn):
    po_cols = _cols(conn, "fact_purchase_orders")
    qty_col = next((c for c in ("qty_ordered_kg", "quantity_kg", "qty_kg") if c in po_cols), None)
    if qty_col is None:
        pytest.skip("purchase order quantity column not found")
    over = conn.execute(f"""
        SELECT COUNT(*) FROM (
            SELECT d.po_id, SUM(d.qty_received_kg + d.qty_rejected_kg) AS got, MAX(p.{qty_col}) AS ordered
            FROM fact_deliveries d JOIN fact_purchase_orders p USING (po_id)
            GROUP BY d.po_id) WHERE got > ordered * 1.0001 + 1e-6""").fetchone()[0]  # nosec B608 - constant
    assert over == 0


def test_waste_never_exceeds_receipts_by_product(conn):
    over = conn.execute("""
        SELECT COUNT(*) FROM (
            SELECT w.product_id, SUM(w.qty_wasted_kg) AS wasted
            FROM fact_waste_events w GROUP BY w.product_id) w
        JOIN (SELECT product_id, SUM(qty_received_kg) AS received
              FROM fact_deliveries GROUP BY product_id) d USING (product_id)
        WHERE wasted > received + 1e-6""").fetchone()[0]
    assert over == 0


def test_waste_dated_at_or_after_delivery(conn):
    if "delivery_id" not in _cols(conn, "fact_waste_events"):
        # linked by product only; check the earliest waste is not before the
        # earliest delivery of that product
        early = conn.execute("""
            SELECT COUNT(*) FROM (SELECT product_id, MIN(event_date) e FROM fact_waste_events GROUP BY 1) w
            JOIN (SELECT product_id, MIN(delivery_date) d FROM fact_deliveries GROUP BY 1) d USING (product_id)
            WHERE e < d""").fetchone()[0]
        assert early == 0
    else:
        early = conn.execute("""
            SELECT COUNT(*) FROM fact_waste_events w JOIN fact_deliveries d USING (delivery_id)
            WHERE w.event_date < d.delivery_date""").fetchone()[0]
        assert early == 0


def test_seed_reproducible():
    a, b = duckdb.connect(":memory:"), duckdb.connect(":memory:")
    for c in (a, b):
        setup_db(c, load_seeds=True)
        SyntheticGenerator(start_date=date(2024, 1, 1), n_weeks=8, seed=3, end_near_today=False).generate_all(c)
    qa = a.execute("SELECT SUM(qty_received_kg), COUNT(*) FROM fact_deliveries").fetchone()
    qb = b.execute("SELECT SUM(qty_received_kg), COUNT(*) FROM fact_deliveries").fetchone()
    assert qa == qb
