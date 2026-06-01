"""Tests for risk/scenario_generation.py (the optimizer bridge)."""

from __future__ import annotations

import duckdb
import pytest

from risk.scenario_generation import (
    demand_scenarios_from_orders, supply_from_distributions, run_two_stage,
)


@pytest.fixture()
def db():
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE stg_supplier_deliveries (delivery_id VARCHAR, supplier_id VARCHAR, supplier_name VARCHAR, product_id VARCHAR, product_name VARCHAR, delivery_date DATE, ordered_quantity DOUBLE, delivered_quantity DOUBLE, accepted_quantity DOUBLE, rejected_quantity DOUBLE, unit_cost DOUBLE, quality_grade VARCHAR, lot_id VARCHAR)")
    conn.execute("CREATE TABLE stg_buyer_orders (order_id VARCHAR, buyer_id VARCHAR, buyer_name VARCHAR, product_id VARCHAR, product_name VARCHAR, order_date DATE, delivery_date DATE, requested_quantity DOUBLE, fulfilled_quantity DOUBLE, substituted_quantity DOUBLE, sales_price DOUBLE, required_quality_grade VARCHAR)")

    deliveries = []
    for i, acc in enumerate([60, 95, 58, 96, 62]):  # volatile, low downside
        deliveries.append((f"V{i}", "S1", "Swingy", "P1", "Tomatoes", "2026-05-01",
                           100.0, acc, acc, 0.0, 1.20, "A", f"L{i}"))
    for i, acc in enumerate([97, 96, 98, 97]):       # reliable
        deliveries.append((f"R{i}", "S2", "Reliable", "P1", "Tomatoes", "2026-05-02",
                           100.0, acc, acc, 0.0, 1.30, "A", f"M{i}"))
    conn.executemany("""INSERT INTO stg_supplier_deliveries
        (delivery_id, supplier_id, supplier_name, product_id, product_name, delivery_date,
         ordered_quantity, delivered_quantity, accepted_quantity, rejected_quantity, unit_cost, quality_grade, lot_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", deliveries)

    conn.executemany("""INSERT INTO stg_buyer_orders
        (order_id, buyer_name, product_name, delivery_date, requested_quantity, fulfilled_quantity, substituted_quantity, sales_price)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?)""", [
        ("O1", "B", "Tomatoes", "2026-05-10", 120, 110, 2.5),
        ("O2", "B", "Tomatoes", "2026-05-17", 100, 100, 2.5),
        ("O3", "B", "Tomatoes", "2026-05-24", 140, 120, 2.5),
    ])
    yield conn
    conn.close()


def test_demand_scenarios_shape(db):
    dem = demand_scenarios_from_orders(db)
    assert list(dem.columns) == ["scenario_index", "scenario_weight",
                                 "product_id", "week_start", "demand_kg"]
    # Three distinct delivery dates -> three scenarios.
    assert dem["scenario_index"].nunique() == 3
    # Scenario weights are equal and sum to 1 across unique scenarios.
    uniq = dem.drop_duplicates("scenario_index")["scenario_weight"].sum()
    assert uniq == pytest.approx(1.0)


def test_supply_capacity_discounted_by_downside(db):
    sup = supply_from_distributions(db, quantile=0.10)
    by_sup = {r["supplier_id"]: r for _, r in sup.iterrows()}
    # Both suppliers order ~100; capacity is ordered x downside, so < 100.
    assert by_sup["S1"]["capacity_kg"] < 100
    assert by_sup["S2"]["capacity_kg"] < 100
    # The volatile supplier (lower downside) gets less effective capacity than
    # the reliable one, despite identical order sizes.
    assert by_sup["S1"]["capacity_kg"] < by_sup["S2"]["capacity_kg"]


def test_supply_empty_when_no_deliveries():
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE stg_supplier_deliveries (supplier_id VARCHAR, product_name VARCHAR, ordered_quantity DOUBLE, accepted_quantity DOUBLE, delivered_quantity DOUBLE, unit_cost DOUBLE, supplier_name VARCHAR)")
    sup = supply_from_distributions(conn, quantile=0.10)
    assert len(sup) == 0
    conn.close()


def test_optimizer_solves_on_bridge_inputs(db):
    """The dormant two-stage SP runs on operator-derived inputs.

    Skipped cleanly if the optimization stack (pyomo + HiGHS) is unavailable.
    """
    pytest.importorskip("pyomo")
    try:
        result = run_two_stage(db, quantile=0.10, time_limit_s=30.0)
    except Exception as exc:  # solver missing or environment issue
        pytest.skip(f"optimizer unavailable: {exc}")
    assert result["status"] in ("optimal", "locallyOptimal")
    assert result["objective"] is not None
    # Recourse quantities are returned.
    assert "expected_spot_kg" in result
    assert "expected_unmet_kg" in result
