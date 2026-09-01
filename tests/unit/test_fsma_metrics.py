"""Unit tests for dashboard.lib.fsma_metrics."""

from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path

import duckdb
import pytest

from dashboard.lib.fsma_metrics import (
    fsma_coverage_score,
    ftl_product_list,
    fsma_lot_chain,
    generate_fda_report_csv,
)


def _bootstrap(conn) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    for sql in sorted((repo_root / "db" / "migrations").glob("*.sql")):
        conn.execute(sql.read_text())


def _seed_dims(conn) -> None:
    conn.execute(
        "INSERT INTO dim_products (product_id, crop_name, crop_category, "
        "shelf_life_days, is_ftl_item) VALUES "
        "(?, 'Lettuce', 'leafy_green', 7, TRUE), "
        "(?, 'Tomato',  'tomato',       10, TRUE), "
        "(?, 'Onion',   'allium',       60, FALSE)",
        ["PRD-FTL-1", "PRD-FTL-2", "PRD-NONFTL"],
    )
    conn.execute(
        "INSERT INTO dim_suppliers (supplier_id, supplier_name, supplier_type) VALUES "
        "(?, 'Farm A', 'farm'), (?, 'Farm B', 'farm')",
        ["SUP-A", "SUP-B"],
    )


@pytest.fixture
def conn():
    c = duckdb.connect(":memory:")
    _bootstrap(c)
    _seed_dims(c)
    return c


# ── Coverage ─────────────────────────────────────────────────────────────────

def test_full_coverage(conn):
    """All FTL deliveries have a matching lot record → 100% coverage."""
    conn.execute(
        "INSERT INTO fact_deliveries (delivery_id, supplier_id, product_id, "
        "delivery_date, qty_received_kg) VALUES "
        "('D1','SUP-A','PRD-FTL-1','2025-06-04', 100.0), "
        "('D2','SUP-B','PRD-FTL-2','2025-06-05',  80.0)"
    )
    conn.execute(
        "INSERT INTO fact_lots (lot_id, traceability_lot_code, "
        "tlc_source_reference, product_id, quantity_kg, supplier_id) VALUES "
        "('L1','TLC-1','Farm A', 'PRD-FTL-1', 100.0, 'SUP-A'), "
        "('L2','TLC-2','Farm B', 'PRD-FTL-2',  80.0, 'SUP-B')"
    )
    score = fsma_coverage_score(conn)
    assert score["coverage_pct"] == 1.0
    assert score["status"] == "Full"


def test_partial_coverage(conn):
    """Two FTL deliveries; only one has a lot record → between 0 and 1."""
    conn.execute(
        "INSERT INTO fact_deliveries (delivery_id, supplier_id, product_id, "
        "delivery_date, qty_received_kg) VALUES "
        "('D1','SUP-A','PRD-FTL-1','2025-06-04', 100.0), "
        "('D2','SUP-B','PRD-FTL-2','2025-06-05',  80.0)"
    )
    conn.execute(
        "INSERT INTO fact_lots (lot_id, traceability_lot_code, "
        "tlc_source_reference, product_id, quantity_kg, supplier_id) VALUES "
        "('L1','TLC-1','Farm A', 'PRD-FTL-1', 100.0, 'SUP-A')"
    )
    score = fsma_coverage_score(conn)
    assert 0 < score["coverage_pct"] < 1
    assert score["status"] in ("Partial", "Minimal")


def test_no_lots_zero_coverage(conn):
    conn.execute(
        "INSERT INTO fact_deliveries (delivery_id, supplier_id, product_id, "
        "delivery_date, qty_received_kg) VALUES "
        "('D1','SUP-A','PRD-FTL-1','2025-06-04', 100.0)"
    )
    score = fsma_coverage_score(conn)
    assert score["coverage_pct"] == 0.0
    assert score["status"] == "None"


def test_no_ftl_deliveries(conn):
    """No FTL deliveries at all → n_ftl_products_total > 0 but covered=0."""
    score = fsma_coverage_score(conn)
    # n_ftl_products_total counts dim_products rows, regardless of deliveries
    assert score["n_ftl_products_total"] >= 2
    assert score["covered_kg"] == 0.0


# ── Per-product list ─────────────────────────────────────────────────────────

def test_ftl_product_list_only_ftl(conn):
    df = ftl_product_list(conn)
    # PRD-NONFTL must be excluded
    assert "PRD-NONFTL" not in df["product_id"].tolist()
    assert "PRD-FTL-1" in df["product_id"].tolist()


# ── FDA report ───────────────────────────────────────────────────────────────

def _seed_lot_with_cte(conn, lot_id, tlc, product_id, supplier_id, when):
    conn.execute(
        "INSERT INTO fact_lots (lot_id, traceability_lot_code, "
        "tlc_source_reference, product_id, quantity_kg, supplier_id) "
        "VALUES (?, ?, ?, ?, 100.0, ?)",
        [lot_id, tlc, "Farm", product_id, supplier_id],
    )
    conn.execute(
        "INSERT INTO fact_cte_events (cte_id, lot_id, traceability_lot_code, "
        "cte_type, event_timestamp, location_description, business_name, "
        "quantity_kg) VALUES "
        "(?, ?, ?, 'receiving', ?, 'Hub Dock 1', 'Test Hub', 100.0)",
        [f"CTE-{tlc}", lot_id, tlc, when],
    )


def test_generate_fda_report_csv_valid(conn):
    _seed_lot_with_cte(
        conn, "L1", "TLC-X", "PRD-FTL-1", "SUP-A", datetime.now(timezone.utc)
    )
    csv_str = generate_fda_report_csv(conn)
    assert csv_str.strip(), "CSV should not be empty"
    parsed = list(csv.reader(StringIO(csv_str)))
    assert "traceability_lot_code" in parsed[0]
    # At least the header + 1 data row
    assert len(parsed) >= 2


# ── Lot chain ────────────────────────────────────────────────────────────────

def test_fsma_lot_chain_three_hops(conn):
    # Build a 3-step chain: TLC-A → TLC-B → TLC-C (each refs the prior)
    now = datetime.now(timezone.utc)
    _seed_lot_with_cte(conn, "L-A", "TLC-A", "PRD-FTL-1", "SUP-A", now - timedelta(hours=2))
    _seed_lot_with_cte(conn, "L-B", "TLC-B", "PRD-FTL-1", "SUP-A", now - timedelta(hours=1))
    _seed_lot_with_cte(conn, "L-C", "TLC-C", "PRD-FTL-1", "SUP-A", now)

    # Wire B → A and C → B via referenced_tlc_codes
    conn.execute(
        "UPDATE fact_cte_events SET referenced_tlc_codes = ? WHERE traceability_lot_code = ?",
        [["TLC-A"], "TLC-B"],
    )
    conn.execute(
        "UPDATE fact_cte_events SET referenced_tlc_codes = ? WHERE traceability_lot_code = ?",
        [["TLC-B"], "TLC-C"],
    )

    chain = fsma_lot_chain(conn, "TLC-C")
    tlcs = sorted(chain["traceability_lot_code"].unique().tolist())
    assert tlcs == ["TLC-A", "TLC-B", "TLC-C"]
