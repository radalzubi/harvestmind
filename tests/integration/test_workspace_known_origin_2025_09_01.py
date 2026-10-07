"""The known synthetic state at origin 2025-09-01 (audit Tasks 7, 11, 13-16; HARDENING V1, H1a).

On the SYNTHETIC sample (seed 7, E_mixed_portfolio) three orders were in flight at 2025-09-01 and were
received in full afterwards. Before H1a the adapter read those later receipts and dropped the orders, so
the request carried 0 / 120 / 6 units inbound for SKU-0009 / SKU-0030 / SKU-0143 instead of
3000 / 3888 / 72. Nothing here is hard-coded in production: the numbers are the sample's own rows, and
the test derives them from the vault beside the request so a regenerated sample fails loudly rather than
silently."""
from __future__ import annotations

from datetime import datetime, timezone

import duckdb
import pytest

from api.routers.intake import load_fmcg_sample_into
from scripts.setup_db import setup_db
from zaad.full.workspace import build_request

SKUS = ["SKU-0009", "SKU-0030", "SKU-0143"]
EXPECTED_INBOUND = {"SKU-0009": 3000., "SKU-0030": 3888., "SKU-0143": 72.}
ORIGIN = datetime(2025, 9, 1, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def vault():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    load_fmcg_sample_into(conn, seed=7, archetype="E_mixed_portfolio")
    yield conn
    conn.close()


def test_open_inbound_at_2025_09_01_is_what_was_in_flight_by_receipts_before_that_day(vault):
    # what the vault says: orders placed before the origin with no receipt dated before it (the adapter's open
    # order: its first receipt is its arrival), summed per product
    rows = vault.execute("""
        SELECT p.sku, SUM(p.qty_ordered) AS inbound
        FROM stg_fmcg_purchase_orders p
        WHERE p.po_date < DATE '2025-09-01' AND p.sku IN ('SKU-0009', 'SKU-0030', 'SKU-0143')
          AND NOT EXISTS (SELECT 1 FROM stg_fmcg_receipts r WHERE r.po_id = p.po_id AND r.receipt_date < DATE '2025-09-01')
        GROUP BY p.sku""").fetchall()
    from_vault = {sku: float(q) for sku, q in rows}
    if from_vault != EXPECTED_INBOUND:
        pytest.fail(f"the synthetic sample changed: in-flight by vault rows {from_vault}, the audited state was {EXPECTED_INBOUND}")
    req, build = build_request(vault, "tenant_test", as_of=ORIGIN, horizon=12, skus=SKUS)
    sku_of = {s.id: s.sku for s in req.sources}
    inbound: dict[str, float] = {}
    for po in req.pipeline:
        inbound[sku_of[po.source]] = inbound.get(sku_of[po.source], 0.) + po.remaining
    assert inbound == EXPECTED_INBOUND
    assert {p.id for p in req.pipeline} >= {"PO-014747", "PO-014856", "PO-014768", "PO-014877", "PO-014951"}
    assert build["leakage_guard"]["receipts_at_or_after_origin_excluded"] > 0
