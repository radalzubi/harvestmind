"""Unit tests for forecasting/demand/demand_forecast_service.py.

Covers: staging aggregation, metric math (WAPE/bias — never MAPE),
model routing, leakage protection, the evaluation gate contract, and
forecast-driven scenario generation.
"""

from __future__ import annotations

from datetime import date, timedelta

import duckdb
import numpy as np
import pandas as pd
import pytest

from forecasting.demand.demand_forecast_service import (
    bias_pct,
    classify_products,
    evaluate_demand_forecaster,
    forecast_demand,
    seasonal_naive_forecast,
    wape,
    weekly_orders_from_staging,
    _product_point_forecasts,
)

_TODAY = date(2026, 5, 25)


def _make_db(weeks: int = 30, products=("Tomatoes", "Kale")) -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE stg_buyer_orders (
            order_id VARCHAR, buyer_id VARCHAR, buyer_name VARCHAR,
            product_id VARCHAR, product_name VARCHAR,
            order_date DATE, delivery_date DATE,
            requested_quantity DOUBLE, fulfilled_quantity DOUBLE,
            substituted_quantity DOUBLE, sales_price DOUBLE,
            required_quality_grade VARCHAR
        )
    """)
    rng = np.random.default_rng(7)
    rows = []
    start = _TODAY - timedelta(weeks=weeks)
    for w in range(weeks):
        d = start + timedelta(weeks=w)
        for p in products:
            base = 500 if p == "Tomatoes" else 120
            qty = max(base + 30 * np.sin(2 * np.pi * w / 26) + rng.normal(0, 20), 0)
            rows.append((f"O{w}{p[0]}", "B1", "Buyer One", p, p,
                         str(d), str(d), float(qty), float(qty), 0.0, 2.5, None))
    conn.executemany(
        "INSERT INTO stg_buyer_orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return conn


# ── Aggregation ───────────────────────────────────────────────────────────────

def test_weekly_aggregation_shape():
    conn = _make_db(weeks=20)
    weekly = weekly_orders_from_staging(conn)
    assert set(weekly.columns) == {"product_id", "buyer_id", "week_start",
                                   "qty_ordered_kg"}
    assert weekly["week_start"].nunique() == 20
    assert weekly["product_id"].nunique() == 2
    # Mondays only
    assert (pd.to_datetime(weekly["week_start"]).dt.dayofweek == 0).all()


def test_weekly_aggregation_empty():
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE stg_buyer_orders (product_name VARCHAR, "
                 "buyer_id VARCHAR, buyer_name VARCHAR, order_date DATE, "
                 "delivery_date DATE, requested_quantity DOUBLE)")
    assert weekly_orders_from_staging(conn).empty


# ── Metrics ───────────────────────────────────────────────────────────────────

def test_wape_basic():
    assert wape([100, 100], [90, 110]) == pytest.approx(0.10)


def test_wape_zero_actuals_nan():
    assert np.isnan(wape([0, 0], [5, 5]))


def test_bias_pct_signs():
    assert bias_pct([100], [110]) == pytest.approx(10.0)
    assert bias_pct([100], [90]) == pytest.approx(-10.0)


def test_no_mape_anywhere_in_decision_path():
    """Honesty guard: MAPE must never be computed in the forecasting
    service. Mentions are allowed only in prose explaining the ban."""
    import inspect
    import forecasting.demand.demand_forecast_service as svc
    src = inspect.getsource(svc).lower().replace("wape", "")
    ban_words = ("never", "banned", "meaningless", "undefined", "unlike")
    for line in src.splitlines():
        if "mape" in line:
            assert any(w in line for w in ban_words), f"unexplained MAPE: {line}"


# ── Routing ───────────────────────────────────────────────────────────────────

def test_classify_products_routes_sparse_to_croston():
    weeks = pd.date_range("2026-01-05", periods=20, freq="W-MON")
    rows = []
    for i, w in enumerate(weeks):
        rows.append({"product_id": "Dense", "buyer_id": "B", "week_start": w,
                     "qty_ordered_kg": 100.0})
        if i % 5 == 0:  # 4 of 20 weeks → 80% zeros
            rows.append({"product_id": "Sparse", "buyer_id": "B",
                         "week_start": w, "qty_ordered_kg": 40.0})
    routes = classify_products(pd.DataFrame(rows))
    assert routes["Dense"] == "lgbm"
    assert routes["Sparse"] == "croston"


# ── Leakage protection ────────────────────────────────────────────────────────

def test_forecasts_depend_only_on_training_slice():
    """Perturbing data after the training cutoff must not change the
    forecast made from the training slice (no lookahead)."""
    conn = _make_db(weeks=30)
    weekly = weekly_orders_from_staging(conn)
    weeks_sorted = sorted(weekly["week_start"].unique())
    cutoff = weeks_sorted[-4]
    train = weekly[weekly["week_start"] < cutoff].copy()

    p1, _, _ = _product_point_forecasts(train, 1, classify_products(train))

    # corrupt the post-cutoff rows wildly; the training slice is identical
    corrupted = weekly.copy()
    corrupted.loc[corrupted["week_start"] >= cutoff, "qty_ordered_kg"] *= 1000
    train2 = corrupted[corrupted["week_start"] < cutoff].copy()
    p2, _, _ = _product_point_forecasts(train2, 1, classify_products(train2))

    for k in p1:
        assert p1[k] == pytest.approx(p2[k], rel=1e-9)


# ── Seasonal naive ────────────────────────────────────────────────────────────

def test_seasonal_naive_uses_year_ago_when_available():
    weeks = pd.date_range("2025-01-06", periods=60, freq="W-MON")
    df = pd.DataFrame({
        "product_id": "P", "buyer_id": "B", "week_start": weeks,
        "qty_ordered_kg": np.arange(60, dtype=float) + 1,
    })
    target = weeks[55] + pd.Timedelta(weeks=0)  # inside history? use future:
    target = weeks[-1] + pd.Timedelta(weeks=1)
    snaive = seasonal_naive_forecast(df, [target])
    year_ago = target - pd.Timedelta(weeks=52)
    expected = float(df[df["week_start"] == year_ago]["qty_ordered_kg"].sum())
    assert snaive[("P", target)] == pytest.approx(expected)


def test_seasonal_naive_falls_back_to_runrate():
    weeks = pd.date_range("2026-01-05", periods=8, freq="W-MON")
    df = pd.DataFrame({
        "product_id": "P", "buyer_id": "B", "week_start": weeks,
        "qty_ordered_kg": [100.0] * 8,
    })
    target = weeks[-1] + pd.Timedelta(weeks=1)
    snaive = seasonal_naive_forecast(df, [target])
    assert snaive[("P", target)] == pytest.approx(100.0)  # 4wk sum / 4


# ── Evaluation gate contract ──────────────────────────────────────────────────

def test_evaluation_returns_gate_contract():
    conn = _make_db(weeks=30)
    ev = evaluate_demand_forecaster(conn, n_folds=2)
    assert ev["status"] == "ok"
    assert "wape_model" in ev and "wape_seasonal_naive" in ev
    assert "oos_mase_ratio" in ev
    assert isinstance(ev["gate_passed"], bool)
    assert "seasonal-naive" in ev["gate_rule"]
    # MAPE policy stated explicitly
    assert "MAPE" in ev["metrics_policy"]


def test_evaluation_insufficient_history_is_honest():
    conn = _make_db(weeks=6)
    ev = evaluate_demand_forecaster(conn)
    assert ev["status"] == "insufficient_history"
    assert ev["gate_passed"] is None


# ── Forecast output ───────────────────────────────────────────────────────────

def test_forecast_demand_distribution_shape():
    conn = _make_db(weeks=30)
    fc = forecast_demand(conn, horizon_weeks=4)
    assert fc.model_info["status"] == "ok"
    assert len(fc.products) == 2
    for p in fc.products:
        qs = p["quantiles_kg"]
        assert qs["q10"] <= qs["q50"] <= qs["q90"]
        assert p["forecast_kg_per_week"] >= 0
        assert p["drivers"]  # never empty


def test_forecast_demand_insufficient_history():
    conn = _make_db(weeks=4)
    fc = forecast_demand(conn)
    assert fc.products == []
    assert fc.model_info["status"] == "insufficient_history"


# ── Scenario generation from forecast ─────────────────────────────────────────

def test_scenarios_from_forecast_shape_and_weights():
    from risk.scenario_generation import demand_scenarios_from_forecast

    conn = _make_db(weeks=30)
    scen = demand_scenarios_from_forecast(conn, n_scenarios=50)
    assert set(scen.columns) == {"scenario_index", "scenario_weight",
                                 "product_id", "week_start", "demand_kg"}
    assert scen["scenario_index"].nunique() == 50
    # weights sum to 1 per product
    per_prod = scen.groupby("product_id")["scenario_weight"].sum()
    for v in per_prod:
        assert v == pytest.approx(1.0)
    assert (scen["demand_kg"] >= 0).all()
    # scenarios vary (distribution, not a constant)
    assert scen.groupby("product_id")["demand_kg"].std().max() > 0


def test_scenarios_fall_back_to_replay_on_short_history():
    from risk.scenario_generation import demand_scenarios_from_forecast

    conn = _make_db(weeks=4)
    scen = demand_scenarios_from_forecast(conn, n_scenarios=20)
    # falls back to historical replay (4 scenarios = 4 delivery dates)
    assert not scen.empty
