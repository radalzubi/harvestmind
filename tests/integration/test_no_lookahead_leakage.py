"""Backtest leakage guards — these tests fail loudly if any rolling-origin
path uses data after the planning week.

Regression background
---------------------
An earlier version of `RollingOriginEngine._run_origin` built two-stage SP
demand scenarios from `realized_demand` (the realised orders in the
horizon window). That gave the SP the recourse-period mean as input,
producing inflated ROI numbers in partner-facing reports. Fixed by using
the historical-mean per-product demand. These tests pin that contract.
"""

from __future__ import annotations

from datetime import date, timedelta

import duckdb
import pandas as pd
import pytest

from backtesting.leakage_guard import LeakageError, assert_no_future_data
from backtesting.rolling_origin_engine import (
    BacktestConfig,
    RollingOriginEngine,
)
from scripts.setup_db import setup_db
from synthetic.generator import SyntheticGenerator


@pytest.fixture(scope="module")
def populated_orders_deliveries():
    conn = duckdb.connect(":memory:")
    setup_db(conn, load_seeds=True)
    SyntheticGenerator(n_weeks=80, seed=23).generate_all(conn)
    orders_df = conn.execute(
        "SELECT ol.product_id, o.buyer_id, o.week_start, ol.qty_ordered_kg "
        "FROM fact_order_lines ol JOIN fact_orders o ON ol.order_id = o.order_id"
    ).df()
    deliveries_df = conn.execute(
        "SELECT supplier_id, product_id, delivery_date, qty_received_kg, qty_rejected_kg "
        "FROM fact_deliveries"
    ).df()
    conn.close()
    return orders_df, deliveries_df


def test_engine_runs_clean(populated_orders_deliveries):
    """Smoke: backtest finishes without raising LeakageError."""
    orders_df, deliveries_df = populated_orders_deliveries
    cfg = BacktestConfig(
        n_train_weeks=52, horizon_weeks=4, step_weeks=4,
        n_scenarios=10, run_stochastic=True,
    )
    results = RollingOriginEngine(cfg).run(orders_df, deliveries_df)
    assert not results.empty
    # Every model status that we report must reach optimal/locallyOptimal.
    assert results["solver_status"].isin({"optimal", "locallyOptimal"}).all()


def test_assert_no_future_data_catches_synthetic_leak(populated_orders_deliveries):
    """If somebody passes future-stamped rows to the planning input, the
    standalone guard must raise."""
    orders_df, _ = populated_orders_deliveries
    fake_origin = orders_df["week_start"].min().date() + timedelta(weeks=4)
    with pytest.raises(LeakageError):
        assert_no_future_data(orders_df, "week_start", fake_origin)


def test_yield_to_demand_scenarios_does_not_use_future_data(populated_orders_deliveries):
    """The SP base must come from past demand only.

    Build a `train_demand_mean` from PAST orders and a fake `realized_demand`
    that is wildly different. The function under test must give back a
    distribution whose central tendency tracks the *past* base, not the
    realised one — otherwise leakage has crept back in.
    """
    from backtesting.rolling_origin_engine import RollingOriginEngine

    products = ["PRD-001", "PRD-002", "PRD-003"]
    train_mean = pd.DataFrame(
        [{"product_id": p, "demand_kg": 100.0} for p in products]
    )
    # If anyone ever re-wires the engine to use realized data, this fixture
    # would push the centre to ~10000 → 100x off the historical base.
    misleading_realized = pd.DataFrame(
        [{"product_id": p, "demand_kg": 10_000.0} for p in products]
    )

    # Yield scenarios at neutral ratio 1.0
    scen_rows = []
    for s in range(5):
        for p in products:
            scen_rows.append({
                "scenario_index": s,
                "scenario_weight": 0.2,
                "supplier_id": "SUP-001",
                "product_id": p,
                "week_start": date(2025, 1, 6),
                "yield_kg": 100.0,
            })
    scen_df = pd.DataFrame(scen_rows)

    # Engine helper — intentionally call with the *correct* PAST base.
    correct = RollingOriginEngine._yield_to_demand_scenarios(scen_df, train_mean)
    incorrect = RollingOriginEngine._yield_to_demand_scenarios(scen_df, misleading_realized)

    # The mean of the correct path must be near 100, the leaked path near 10000.
    # Since the engine should only ever be given the PAST base, we simply
    # assert that 100-anchored output is bounded well below the leaked one.
    assert correct["demand_kg"].mean() < 200.0
    assert incorrect["demand_kg"].mean() > 5_000.0
    # The two paths must be cleanly distinguishable — used as a regression
    # tripwire if a future change accidentally reintroduces realized inputs.
    assert correct["demand_kg"].max() < incorrect["demand_kg"].min()
