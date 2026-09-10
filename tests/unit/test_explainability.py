"""Phase 6 tests: shadow prices, confidence labeling, two-card ROI."""

from __future__ import annotations

from datetime import date, timedelta

import duckdb
import numpy as np
import pandas as pd

from optimization.two_stage_sp import TwoStageStochasticLP

_TODAY = date(2026, 5, 25)


# ── Shadow prices ─────────────────────────────────────────────────────────────

def test_shadow_price_on_binding_capacity():
    """Capacity 50 against demand 100 with expensive unmet: the capacity
    binds and its shadow price (value of one more kg) must be positive."""
    scen = pd.DataFrame([
        {"scenario_index": 0, "scenario_weight": 1.0, "product_id": "A",
         "week_start": "2026-06-01", "demand_kg": 100.0},
    ])
    sup = pd.DataFrame([
        {"supplier_id": "s1", "product_id": "A", "week_start": "2026-06-01",
         "capacity_kg": 50.0, "price_per_kg": 2.0},
    ])
    res = TwoStageStochasticLP(
        newsvendor_objective=True,
        waste_cost_by_product={"A": 0.5},
        unmet_cost_by_product={"A": 5.0},
        spot_capacity_factor=0.0,
        n_scenarios=1,
    ).solve(scen, sup)
    assert "shadow_prices" in res
    assert res["shadow_prices"].get(("s1", "A"), 0.0) > 0


def test_no_shadow_price_when_capacity_slack():
    """Ample capacity → the constraint does not bind → no shadow price."""
    scen = pd.DataFrame([
        {"scenario_index": 0, "scenario_weight": 1.0, "product_id": "A",
         "week_start": "2026-06-01", "demand_kg": 100.0},
    ])
    sup = pd.DataFrame([
        {"supplier_id": "s1", "product_id": "A", "week_start": "2026-06-01",
         "capacity_kg": 10_000.0, "price_per_kg": 2.0},
    ])
    res = TwoStageStochasticLP(
        newsvendor_objective=True,
        waste_cost_by_product={"A": 0.5},
        unmet_cost_by_product={"A": 5.0},
        spot_capacity_factor=0.0,
        n_scenarios=1,
    ).solve(scen, sup)
    assert ("s1", "A") not in res["shadow_prices"]


# ── Confidence index ──────────────────────────────────────────────────────────

def _staging_db(weeks=30, seed=9):
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE stg_buyer_orders (
            buyer_id VARCHAR, buyer_name VARCHAR, product_name VARCHAR,
            order_date DATE, delivery_date DATE,
            requested_quantity DOUBLE, fulfilled_quantity DOUBLE,
            substituted_quantity DOUBLE, sales_price DOUBLE
        )
    """)
    conn.execute("""
        CREATE TABLE stg_supplier_deliveries (
            supplier_id VARCHAR, supplier_name VARCHAR, product_name VARCHAR,
            delivery_date DATE, ordered_quantity DOUBLE,
            delivered_quantity DOUBLE, accepted_quantity DOUBLE,
            unit_cost DOUBLE
        )
    """)
    conn.execute("""
        CREATE TABLE stg_waste_adjustments (
            adjustment_id VARCHAR, date DATE, product_id VARCHAR,
            product_name VARCHAR, lot_id VARCHAR, quantity_lost DOUBLE,
            reason VARCHAR, estimated_value_lost DOUBLE
        )
    """)
    rng = np.random.default_rng(seed)
    start = _TODAY - timedelta(weeks=weeks)
    o, d = [], []
    for w in range(weeks):
        day = start + timedelta(weeks=w)
        qty = max(400 + rng.normal(0, 30), 10)
        o.append(("B1", "Buyer", "Tomatoes", str(day), str(day), qty, qty, 0.0, 3.0))
        for s in ("S1", "S2", "S3"):
            ordered = qty / 2
            fill = float(np.clip(rng.beta(16, 3), 0, 1))
            d.append((s, s, "Tomatoes", str(day), ordered, ordered * fill,
                      ordered * fill, 2.0))
    conn.executemany("INSERT INTO stg_buyer_orders VALUES (?,?,?,?,?,?,?,?,?)", o)
    conn.executemany(
        "INSERT INTO stg_supplier_deliveries VALUES (?,?,?,?,?,?,?,?)", d)
    return conn


def test_confidence_is_labeled_internal_index():
    from risk.confidence import recommendation_confidence

    conn = _staging_db()
    c = recommendation_confidence(conn)
    assert c["label"] == "internal index — not a probability"
    assert c["index"] is not None
    assert 0 <= c["index"] <= 100
    # arithmetic is stated, components are measured quantities
    assert "arithmetic" in c
    assert c["components"]["demand_oos_wape"] > 0


def test_confidence_honest_when_unmeasurable():
    from risk.confidence import recommendation_confidence

    conn = _staging_db(weeks=6)
    c = recommendation_confidence(conn)
    assert c["index"] is None
    assert "reason" in c
    assert c["label"] == "internal index — not a probability"


# ── Two-card ROI ──────────────────────────────────────────────────────────────

def test_roi_cards_separate_and_never_summed():
    """The endpoint payload must keep ceiling and measured as separate
    cards with an explicit do-not-sum statement, and the measured card
    must say 'not_measured' rather than borrowing the ceiling when the
    benchmark cannot run."""
    from fastapi.testclient import TestClient
    import api.main as api_main
    from api.dependencies import get_conn

    conn = _staging_db(weeks=10)  # too short for the benchmark

    app = api_main.app
    app.dependency_overrides[get_conn] = lambda: conn
    try:
        client = TestClient(app)
        r = client.get("/reports/roi-cards")
        assert r.status_code == 200
        body = r.json()
        assert body["ceiling_card"]["status"] == "assumed"
        assert body["measured_card"]["status"] == "not_measured"
        assert "never be added" in body["do_not_sum"]
        # the ceiling numbers exist independently of measurement
        assert "annual_high_usd" in body["ceiling_card"]
    finally:
        app.dependency_overrides.pop(get_conn, None)
