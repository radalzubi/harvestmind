"""Unit tests for the tier abstraction, audit package, carbon, recall, and grant export."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from backtesting.roi_calculator import (
    SUBSCRIPTION_TIERS,
    _resolve_tier_pricing,
)
from dashboard.lib.carbon_metrics import (
    EMISSION_FACTORS_KG_PER_TON_MILE,
    backfill_estimated_co2e,
    carbon_summary,
    emission_factor,
    estimate_co2e_kg,
)
from dashboard.lib.fsma_metrics import recall_forward_trace
from reports.audit_package import (
    AUDIT_TYPES,
    AuditPackageError,
    generate_audit_package,
)
from reports.grant_export import generate_grant_csv, generate_grant_metrics


def _bootstrap(c) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    for sql in sorted((repo_root / "db" / "migrations").glob("*.sql")):
        c.execute(sql.read_text())


def _seed_min(c) -> None:
    c.execute(
        "INSERT INTO dim_products (product_id, crop_name, crop_category, "
        "shelf_life_days, is_ftl_item, cold_chain_required) VALUES "
        "('P-FTL', 'Lettuce', 'leafy_green', 7, TRUE, TRUE), "
        "('P-NON', 'Onions', 'allium', 60, FALSE, FALSE)"
    )
    c.execute(
        "INSERT INTO dim_suppliers (supplier_id, supplier_name, supplier_type, "
        "audit_evidence_status, gfsi_certification, sqf_level) VALUES "
        "('S-A', 'Farm A', 'farm', 'verified', 'BRC', 2), "
        "('S-B', 'Farm B', 'farm', 'unverified', NULL, NULL)"
    )
    c.execute(
        "INSERT INTO dim_buyers (buyer_id, buyer_name, buyer_type) VALUES "
        "('B-1', 'School District', 'school')"
    )


@pytest.fixture
def conn():
    c = duckdb.connect(":memory:")
    _bootstrap(c)
    _seed_min(c)
    yield c
    c.close()


# ── SUBSCRIPTION_TIERS / pricing resolution ─────────────────────────────────

def test_subscription_tiers_have_all_five_tiers():
    expected = {"A", "A_HIGH", "B", "C", "D"}
    assert set(SUBSCRIPTION_TIERS) == expected


def test_tier_pricing_strictly_increasing():
    """Annual price must increase A → A_HIGH → B → C → D."""
    order = ["A", "A_HIGH", "B", "C", "D"]
    prices = [SUBSCRIPTION_TIERS[t]["annual"] for t in order]
    assert prices == sorted(prices)
    assert prices[0] < prices[-1]


def test_resolve_tier_pricing_offline_fallback():
    """When no DB conn given, falls back to the SUBSCRIPTION_TIERS constant."""
    p = _resolve_tier_pricing("A", conn=None)
    assert p["annual"] == SUBSCRIPTION_TIERS["A"]["annual"]


def test_resolve_tier_pricing_uses_db_when_available(conn):
    """When DB has dim_customer_segments (from migration 009),
    resolver pulls from it."""
    p = _resolve_tier_pricing("C", conn=conn)
    assert p["annual"] > 0
    assert "distributor" in p["label"].lower()


def test_resolve_tier_pricing_unknown_tier_falls_back():
    """Unknown tier → returns Tier A pricing as safe default."""
    p = _resolve_tier_pricing("Z_DOES_NOT_EXIST", conn=None)
    assert p["annual"] == SUBSCRIPTION_TIERS["A"]["annual"]


# ── Carbon metrics ──────────────────────────────────────────────────────────

def test_emission_factor_known_class():
    """Refrigerated truckload should be > class 8 truckload (reefer adds ~25%)."""
    reef = EMISSION_FACTORS_KG_PER_TON_MILE["refrigerated_truckload"]
    cl8 = EMISSION_FACTORS_KG_PER_TON_MILE["class_8_truckload"]
    assert reef > cl8


def test_emission_factor_unknown_class_uses_default():
    f = emission_factor("unknown_class")
    default = EMISSION_FACTORS_KG_PER_TON_MILE["default"] / 907.185
    assert f == pytest.approx(default)


def test_estimate_co2e_kg_zero_for_zero_inputs():
    assert estimate_co2e_kg(0, 100, "class_8_truckload") == 0.0
    assert estimate_co2e_kg(100, 0, "class_8_truckload") == 0.0


def test_estimate_co2e_kg_positive_for_real_inputs():
    co2 = estimate_co2e_kg(1000, 500, "class_8_truckload")  # 1 ton × 500 mi
    assert co2 > 0
    # Should be roughly 0.130 × 1 ton × 500 mi = 65 kg CO2e
    assert 50 < co2 < 80


def test_backfill_estimated_co2e_skips_rows_without_miles(conn):
    conn.execute(
        "INSERT INTO fact_deliveries (delivery_id, supplier_id, product_id, "
        "delivery_date, qty_received_kg, transport_miles, truck_class) VALUES "
        "('D-A', 'S-A', 'P-FTL', '2025-06-04', 500, 200, 'class_8_truckload'), "
        "('D-B', 'S-B', 'P-FTL', '2025-06-04', 500, NULL, NULL)"
    )
    n = backfill_estimated_co2e(conn)
    assert n == 1
    val = conn.execute(
        "SELECT estimated_co2e_kg FROM fact_deliveries WHERE delivery_id = 'D-A'"
    ).fetchone()[0]
    assert val is not None and val > 0


def test_carbon_summary_empty_db_returns_zeros(conn):
    s = carbon_summary(conn)
    assert s["total_co2e_kg"] == 0.0
    assert s["coverage_pct"] == 0.0


# ── Audit package ───────────────────────────────────────────────────────────

def test_audit_types_include_walmart_and_gfsi():
    assert "walmart" in AUDIT_TYPES
    assert "gfsi" in AUDIT_TYPES
    assert "sqf_2" in AUDIT_TYPES
    assert "sqf_3" in AUDIT_TYPES


def test_generate_audit_package_unknown_type_raises(conn):
    with pytest.raises(AuditPackageError, match="Unknown audit"):
        generate_audit_package(conn, "Test", audit_type="not_real")


def test_generate_audit_package_creates_zip(conn, tmp_path):
    zip_path = generate_audit_package(
        conn, "Test Hub", audit_type="sqf_2",
        output_dir=tmp_path, create_zip=True,
    )
    assert zip_path.exists()
    assert zip_path.suffix == ".zip"


def test_generate_audit_package_directory_mode(conn, tmp_path):
    pkg_dir = generate_audit_package(
        conn, "Test Hub", audit_type="sqf_2",
        output_dir=tmp_path, create_zip=False,
    )
    assert pkg_dir.is_dir()
    # Must contain at least the 4 SQF Level 2 sections + summary
    files = sorted(p.name for p in pkg_dir.iterdir())
    assert any("supplier_reliability" in f for f in files)
    assert any("audit_summary.html" in f for f in files)


def test_audit_package_walmart_includes_fsma(conn, tmp_path):
    pkg_dir = generate_audit_package(
        conn, "Acme", audit_type="walmart",
        output_dir=tmp_path, create_zip=False,
    )
    files = sorted(p.name for p in pkg_dir.iterdir())
    assert any("fsma_204_coverage" in f for f in files)


# ── Recall forward-chain ────────────────────────────────────────────────────

def test_recall_forward_trace_no_chain(conn):
    """TLC with no events returns empty recall set."""
    r = recall_forward_trace(conn, "TLC-NONE")
    assert r["affected_lots"] == []
    assert r["receiving_businesses"] == []
    assert r["n_shipping_events"] == 0


def test_recall_forward_trace_one_shipment(conn):
    """One lot with one shipping CTE → forward trace finds the recipient."""
    conn.execute(
        "INSERT INTO fact_lots (lot_id, traceability_lot_code, tlc_source_reference, "
        "product_id, quantity_kg, supplier_id) VALUES "
        "('L-1', 'TLC-1', 'Farm A', 'P-FTL', 500, 'S-A')"
    )
    conn.execute(
        "INSERT INTO fact_cte_events (cte_id, lot_id, traceability_lot_code, "
        "cte_type, event_timestamp, location_description, business_name, quantity_kg) "
        "VALUES "
        "('CTE-1', 'L-1', 'TLC-1', 'shipping', CURRENT_TIMESTAMP, "
        "'Hub Dock 1', 'Indianapolis Schools', 500)"
    )
    r = recall_forward_trace(conn, "TLC-1")
    assert r["affected_lots"] == ["TLC-1"]
    assert "Indianapolis Schools" in r["receiving_businesses"]
    assert r["n_shipping_events"] == 1
    assert r["total_quantity_kg"] == 500.0


# ── Grant export ────────────────────────────────────────────────────────────

def test_generate_grant_metrics_returns_required_fields(conn):
    metrics = generate_grant_metrics(conn, partner_name="Test")
    names = {m.name for m in metrics}
    for required in ("annual_revenue_usd", "annual_volume_kg",
                     "buyers_served", "local_suppliers_engaged",
                     "schools_served", "fsma_204_coverage_pct"):
        assert required in names


def test_generate_grant_csv_writes_valid_csv(conn, tmp_path):
    out = tmp_path / "grant.csv"
    p = generate_grant_csv(conn, output_path=out, partner_name="Test")
    assert p.exists()
    content = p.read_text()
    assert "metric" in content.splitlines()[0]
    assert "annual_revenue_usd" in content


def test_grant_csv_wrong_extension_raises(conn, tmp_path):
    with pytest.raises(ValueError, match="must end in"):
        generate_grant_csv(conn, output_path=tmp_path / "bad.txt")
