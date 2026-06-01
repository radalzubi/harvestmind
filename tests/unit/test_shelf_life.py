"""Unit tests for risk/shelf_life.py."""

from __future__ import annotations

from datetime import date

import duckdb
import pytest

from risk.shelf_life import (
    shelf_life_weight, buffer_for_category, weighted_available_by_product,
)

_TODAY = date(2026, 5, 27)


# ── shelf_life_weight: the piecewise function ─────────────────────────────────

def test_expired_before_delivery_is_zero():
    # Remaining shelf life shorter than the lead time -> useless.
    assert shelf_life_weight(remaining_days=2, lead_time_days=5, buffer_days=3) == 0.0


def test_equal_to_lead_time_is_zero():
    assert shelf_life_weight(remaining_days=5, lead_time_days=5, buffer_days=3) == 0.0


def test_beyond_buffer_is_full():
    # 5 days out + 3 day buffer = 8; a lot with 10 days left is fully safe.
    assert shelf_life_weight(remaining_days=10, lead_time_days=5, buffer_days=3) == 1.0


def test_inside_buffer_ramps_linearly():
    # Lead 5, buffer 4, remaining 7 -> (7-5)/4 = 0.5
    assert shelf_life_weight(remaining_days=7, lead_time_days=5, buffer_days=4) == pytest.approx(0.5)


def test_weight_is_monotonic_in_remaining():
    w = [shelf_life_weight(r, lead_time_days=3, buffer_days=5) for r in range(0, 12)]
    assert w == sorted(w)  # non-decreasing in remaining shelf life


def test_zero_buffer_is_hard_step():
    assert shelf_life_weight(remaining_days=4, lead_time_days=3, buffer_days=0) == 1.0
    assert shelf_life_weight(remaining_days=3, lead_time_days=3, buffer_days=0) == 0.0


def test_reduces_to_current_behavior_at_lead_zero_step():
    # The shipped ATP rule is L=0, hard step at 3 days. With buffer 0 and lead 0,
    # anything with remaining > 0 is usable, matching "not yet expired".
    assert shelf_life_weight(remaining_days=1, lead_time_days=0, buffer_days=0) == 1.0
    assert shelf_life_weight(remaining_days=0, lead_time_days=0, buffer_days=0) == 0.0


# ── buffer_for_category ───────────────────────────────────────────────────────

def test_known_category_buffer():
    assert buffer_for_category("Root Vegetables") == 14.0


def test_unknown_category_uses_default():
    assert buffer_for_category("Something Exotic") == 5.0


def test_none_category_uses_default():
    assert buffer_for_category(None) == 5.0


def test_custom_buffer_table():
    assert buffer_for_category("Greens", {"Greens": 2.0}) == 2.0


# ── weighted_available_by_product ─────────────────────────────────────────────

@pytest.fixture()
def lots_db():
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE stg_products (
            product_id VARCHAR, product_name VARCHAR, category VARCHAR,
            unit VARCHAR, default_shelf_life_days INTEGER, traceability_required BOOLEAN
        )
    """)
    conn.execute("""
        CREATE TABLE stg_inventory_lots (
            lot_id VARCHAR, product_id VARCHAR, product_name VARCHAR,
            supplier_id VARCHAR, quantity_on_hand DOUBLE, unit VARCHAR,
            arrival_date DATE, expiration_date DATE, warehouse_location VARCHAR,
            quality_grade VARCHAR, committed_quantity DOUBLE
        )
    """)
    conn.executemany(
        "INSERT INTO stg_products (product_id, product_name, category) VALUES (?, ?, ?)",
        [("P1", "Romaine", "Leafy Greens"), ("P2", "Carrots", "Root Vegetables")],
    )
    # Romaine: one fresh lot (far from expiry), one near-expiry lot.
    # Carrots: one lot well within its long buffer.
    conn.executemany("""
        INSERT INTO stg_inventory_lots
            (lot_id, product_id, product_name, quantity_on_hand, expiration_date, committed_quantity)
        VALUES (?, ?, ?, ?, ?, 0)
    """, [
        ("L1", "P1", "Romaine", 100.0, "2026-06-20"),  # 24 days out, safe
        ("L2", "P1", "Romaine", 100.0, "2026-05-28"),  # 1 day out, near expiry
        ("L3", "P2", "Carrots", 100.0, "2026-06-05"),  # 9 days out
    ])
    yield conn
    conn.close()


def test_near_expiry_lot_is_discounted(lots_db):
    # Delivery 3 days out. Romaine buffer (Leafy Greens) = 4.
    result = weighted_available_by_product(lots_db, _TODAY, lead_time_days=3)
    romaine = result["Romaine"]
    assert romaine["on_hand_kg"] == pytest.approx(200.0)
    # The 1-day-out lot is below lead time (3) -> weight 0; the fresh lot full.
    # So weighted should be ~100, discount ~100.
    assert romaine["weighted_kg"] == pytest.approx(100.0, abs=1.0)
    assert romaine["discount_kg"] == pytest.approx(100.0, abs=1.0)


def test_safe_lot_not_discounted(lots_db):
    result = weighted_available_by_product(lots_db, _TODAY, lead_time_days=1)
    carrots = result["Carrots"]
    # Carrots have a 14-day buffer; 9 days out with lead 1 -> inside buffer,
    # partial weight. Confirm it is discounted but not zeroed.
    assert 0.0 < carrots["weighted_kg"] < carrots["on_hand_kg"]


def test_empty_returns_empty():
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE stg_products (product_id VARCHAR, product_name VARCHAR, category VARCHAR)
    """)
    conn.execute("""
        CREATE TABLE stg_inventory_lots (
            lot_id VARCHAR, product_id VARCHAR, product_name VARCHAR,
            quantity_on_hand DOUBLE, expiration_date DATE, committed_quantity DOUBLE
        )
    """)
    result = weighted_available_by_product(conn, _TODAY, lead_time_days=3)
    assert result == {}
    conn.close()
