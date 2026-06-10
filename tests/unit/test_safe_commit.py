"""Unit tests for risk/safe_commit.py."""

from __future__ import annotations

from datetime import date

import duckdb
import pytest

from risk.safe_commit import safe_commit_recommendations

_TODAY = date(2026, 5, 27)


@pytest.fixture()
def db():
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE stg_products (product_id VARCHAR, product_name VARCHAR, category VARCHAR, unit VARCHAR, default_shelf_life_days INTEGER, traceability_required BOOLEAN)")
    conn.execute("CREATE TABLE stg_supplier_deliveries (delivery_id VARCHAR, supplier_id VARCHAR, supplier_name VARCHAR, product_id VARCHAR, product_name VARCHAR, delivery_date DATE, ordered_quantity DOUBLE, delivered_quantity DOUBLE, accepted_quantity DOUBLE, rejected_quantity DOUBLE, unit_cost DOUBLE, quality_grade VARCHAR, lot_id VARCHAR)")
    conn.execute("CREATE TABLE stg_inventory_lots (lot_id VARCHAR, product_id VARCHAR, product_name VARCHAR, supplier_id VARCHAR, quantity_on_hand DOUBLE, unit VARCHAR, arrival_date DATE, expiration_date DATE, warehouse_location VARCHAR, quality_grade VARCHAR, committed_quantity DOUBLE)")
    conn.execute("CREATE TABLE stg_buyer_orders (order_id VARCHAR, buyer_id VARCHAR, buyer_name VARCHAR, product_id VARCHAR, product_name VARCHAR, order_date DATE, delivery_date DATE, requested_quantity DOUBLE, fulfilled_quantity DOUBLE, substituted_quantity DOUBLE, sales_price DOUBLE, required_quality_grade VARCHAR)")

    conn.executemany("INSERT INTO stg_products (product_id, product_name, category) VALUES (?, ?, ?)",
                     [("P1", "Tomatoes", "Vegetables"), ("P2", "Lettuce", "Leafy Greens")])

    # Tomatoes supplier: reliable, high downside. Lettuce supplier: volatile, low downside.
    rows = []
    for i, acc in enumerate([97, 96, 98, 97, 96]):
        rows.append((f"T{i}", "S-GOOD", "Good Farms", "P1", "Tomatoes", "2026-05-01", 100.0, acc, acc, 0.0, 1.0, "A", f"LT{i}"))
    for i, acc in enumerate([55, 95, 58, 96, 60]):  # mean ~0.73, swingy, low downside
        rows.append((f"V{i}", "S-VOL", "Swingy Co", "P2", "Lettuce", "2026-05-01", 100.0, acc, acc, 0.0, 1.0, "B", f"LV{i}"))
    conn.executemany("""INSERT INTO stg_supplier_deliveries
        (delivery_id, supplier_id, supplier_name, product_id, product_name, delivery_date,
         ordered_quantity, delivered_quantity, accepted_quantity, rejected_quantity, unit_cost, quality_grade, lot_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", rows)

    # Inventory: Tomatoes fresh + committed; Lettuce has a near-expiry lot.
    conn.executemany("""INSERT INTO stg_inventory_lots
        (lot_id, product_id, product_name, supplier_id, quantity_on_hand, unit, arrival_date, expiration_date, committed_quantity)
        VALUES (?, ?, ?, ?, ?, 'kg', ?, ?, ?)""", [
        ("L1", "P1", "Tomatoes", "S-GOOD", 200.0, "2026-05-10", "2026-06-20", 50.0),  # fresh, 50 committed
        ("L2", "P2", "Lettuce", "S-VOL", 100.0, "2026-05-20", "2026-06-15", 0.0),     # fresh
        ("L3", "P2", "Lettuce", "S-VOL", 100.0, "2026-05-22", "2026-05-28", 0.0),     # 1 day out
    ])

    conn.executemany("""INSERT INTO stg_buyer_orders
        (order_id, buyer_name, product_name, delivery_date, requested_quantity, fulfilled_quantity, substituted_quantity, sales_price)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?)""", [
        ("O1", "Buyer A", "Tomatoes", "2026-05-15", 100, 98, 2.5),
        ("O2", "Buyer B", "Lettuce", "2026-05-15", 100, 70, 3.0),
    ])
    yield conn
    conn.close()


def test_returns_one_record_per_product(db):
    recs = safe_commit_recommendations(db, as_of_date=_TODAY, lead_time_days=3)
    names = {r["product_name"] for r in recs}
    assert names == {"Tomatoes", "Lettuce"}


def test_committed_subtracted_from_available(db):
    recs = {r["product_name"]: r for r in safe_commit_recommendations(db, as_of_date=_TODAY, lead_time_days=3)}
    tom = recs["Tomatoes"]
    # 200 on hand, fresh (full weight), 50 committed -> net 150 available.
    assert tom["net_available_kg"] == pytest.approx(150.0, abs=1.0)


def test_near_expiry_lot_discounted(db):
    recs = {r["product_name"]: r for r in safe_commit_recommendations(db, as_of_date=_TODAY, lead_time_days=3)}
    let = recs["Lettuce"]
    # One of two 100kg lots expires in 1 day (< 3 day lead) -> weight 0.
    assert let["shelf_life_discount_kg"] >= 90.0
    assert let["weighted_available_kg"] <= 110.0


def test_volatile_supplier_triggers_holdback(db):
    recs = {r["product_name"]: r for r in safe_commit_recommendations(db, as_of_date=_TODAY, lead_time_days=3)}
    let = recs["Lettuce"]
    # Swingy low-downside supplier -> holdback applied, flagged High or Medium.
    assert let["holdback_kg"] > 0
    assert let["risk_level"] in ("High", "Medium")
    assert any("downside" in f or "volatile" in f for f in let["risk_flags"])


def test_reliable_fresh_product_is_low_risk(db):
    recs = {r["product_name"]: r for r in safe_commit_recommendations(db, as_of_date=_TODAY, lead_time_days=3)}
    tom = recs["Tomatoes"]
    let = recs["Lettuce"]
    # Reliable supplier, fresh stock -> low risk. Under continuous variance
    # shrinkage a 5-delivery supplier keeps a SMALL precautionary holdback
    # (partial pooling: n=5 cannot fully rule out volatility) — the old
    # zero-holdback expectation encoded the n>=3 variance cliff.
    assert tom["risk_level"] == "Low"
    total = tom["safe_commit_kg"] + tom["holdback_kg"]
    assert tom["holdback_kg"] <= 0.15 * total
    # and far smaller than the volatile supplier's product
    assert tom["holdback_kg"] < let["holdback_kg"]


def test_high_risk_sorted_first(db):
    recs = safe_commit_recommendations(db, as_of_date=_TODAY, lead_time_days=3)
    levels = [r["risk_level"] for r in recs]
    order = {"High": 0, "Medium": 1, "Low": 2}
    assert [order[l] for l in levels] == sorted(order[l] for l in levels)
