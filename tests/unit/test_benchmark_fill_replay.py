"""Settlement must apply realized supplier fills, and only change that.

The benchmark previously scored COMMITTED quantity as if it were DELIVERED
quantity. Only the stochastic policy models supplier yield, so only it
inflated commitments to cover expected shortfall, and that inflation was
then charged as pure waste. The comparison was structurally biased against
the one policy managing the risk.

These tests pin the corrected behaviour and prove the refactor did not
change anything else.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtesting.benchmark_suite import (
    POOL_SUPPLIER,
    allocate_to_suppliers,
    realized_fills,
    score_commitment,
    settle,
    supplier_volume_shares,
)

ECON = {"tomato": {"cost": 2.0, "margin": 0.5},
        "lettuce": {"cost": 3.0, "margin": 0.8}}


def _tdel() -> pd.DataFrame:
    """Training-window deliveries: S1 supplies 75% of tomato, S2 25%."""
    return pd.DataFrame([
        {"supplier_id": "S1", "product_id": "tomato", "accepted": 300.0,
         "ordered": 400.0, "fill_rate": 0.75,
         "week_start": pd.Timestamp("2026-01-05")},
        {"supplier_id": "S2", "product_id": "tomato", "accepted": 100.0,
         "ordered": 100.0, "fill_rate": 1.00,
         "week_start": pd.Timestamp("2026-01-05")},
    ])


class TestAllocationConservation:
    def test_pro_rata_split_matches_training_volume_share(self):
        shares = supplier_volume_shares(_tdel())
        assert shares["tomato"]["S1"] == pytest.approx(0.75)
        assert shares["tomato"]["S2"] == pytest.approx(0.25)

    def test_allocation_conserves_total_quantity(self):
        shares = supplier_volume_shares(_tdel())
        alloc = allocate_to_suppliers({"tomato": 1000.0}, shares)
        assert sum(alloc.values()) == pytest.approx(1000.0)
        assert alloc[("S1", "tomato")] == pytest.approx(750.0)
        assert alloc[("S2", "tomato")] == pytest.approx(250.0)

    def test_product_with_no_supplier_history_is_not_dropped(self):
        """Silently losing quantity would flatter that policy's waste."""
        alloc = allocate_to_suppliers({"unknown": 500.0},
                                      supplier_volume_shares(_tdel()))
        assert sum(alloc.values()) == pytest.approx(500.0)
        assert alloc[(POOL_SUPPLIER, "unknown")] == pytest.approx(500.0)

    def test_zero_and_negative_quantities_are_skipped(self):
        shares = supplier_volume_shares(_tdel())
        assert allocate_to_suppliers({"tomato": 0.0}, shares) == {}
        assert allocate_to_suppliers({"tomato": -5.0}, shares) == {}


class TestForcedUnitFillRegression:
    """With perfect delivery, settlement must equal the old scoring."""

    @pytest.mark.parametrize("committed,demand", [
        (1000.0, 800.0), (600.0, 800.0), (800.0, 800.0), (0.0, 500.0),
    ])
    def test_settle_reduces_to_score_commitment(self, committed, demand):
        alloc = {("S1", "tomato"): committed}
        fills = {"S1": 1.0}
        cost, served, waste, delivered = settle(
            alloc, {"tomato": demand}, fills, ECON, 1.30, 0.30)
        exp_c, exp_s, exp_w = score_commitment(
            committed, demand, 2.0, 0.5, 1.30, 0.30)
        assert cost == pytest.approx(exp_c)
        assert served == pytest.approx(exp_s)
        assert waste == pytest.approx(exp_w)
        assert delivered == pytest.approx(committed)

    def test_split_across_suppliers_is_equivalent_at_unit_fill(self):
        """Allocation must not change the score when every fill is 1.0."""
        single = settle({("S1", "tomato"): 1000.0}, {"tomato": 800.0},
                        {"S1": 1.0}, ECON, 1.30, 0.30)
        split = settle({("S1", "tomato"): 750.0, ("S2", "tomato"): 250.0},
                       {"tomato": 800.0}, {"S1": 1.0, "S2": 1.0},
                       ECON, 1.30, 0.30)
        assert single == pytest.approx(split)


class TestFillsActuallyBite:
    def test_shortfall_reduces_delivered_quantity(self):
        _, _, _, delivered = settle(
            {("S1", "tomato"): 1000.0}, {"tomato": 800.0},
            {"S1": 0.6}, ECON, 1.30, 0.30)
        assert delivered == pytest.approx(600.0)

    def test_hedging_is_rewarded_when_suppliers_underdeliver(self):
        """The mechanism the old benchmark could not express.

        Two policies target 800kg. The hedger commits 1000kg knowing the
        supplier fills ~80%; the naive policy commits exactly 800kg. When
        the supplier delivers 80%, the hedger lands on target and the naive
        policy is short. Under commitment-equals-delivery scoring the
        hedger looked wasteful; it should now win.
        """
        realized, fills = {"tomato": 800.0}, {"S1": 0.8}
        hedged, _, _, d_h = settle({("S1", "tomato"): 1000.0}, realized,
                                   fills, ECON, 1.30, 0.30)
        naive, _, _, d_n = settle({("S1", "tomato"): 800.0}, realized,
                                  fills, ECON, 1.30, 0.30)
        assert d_h == pytest.approx(800.0)
        assert d_n == pytest.approx(640.0)
        assert hedged < naive

    def test_unknown_supplier_uses_default_fill(self):
        _, _, _, delivered = settle(
            {("ghost", "tomato"): 500.0}, {"tomato": 500.0}, {},
            ECON, 1.30, 0.30, default_fill=1.0)
        assert delivered == pytest.approx(500.0)


class TestNoLookahead:
    def test_fallback_fill_uses_training_only(self):
        """A supplier absent from the held-out week must fall back to its
        TRAINING mean, never to anything observed in that week."""
        deliveries = pd.DataFrame([
            {"supplier_id": "S1", "product_id": "tomato", "ordered": 100.0,
             "accepted": 50.0, "week_start": pd.Timestamp("2026-02-02")},
        ])
        fills = realized_fills(
            deliveries, pd.Timestamp("2026-02-02"),
            fallback={"S1": 0.75, "S2": 0.90}, pool_fallback=0.80)
        assert fills["S1"] == pytest.approx(0.50)   # observed that week
        assert fills["S2"] == pytest.approx(0.90)   # training fallback
        assert fills[POOL_SUPPLIER] == pytest.approx(0.80)

    def test_empty_history_falls_back_cleanly(self):
        fills = realized_fills(
            pd.DataFrame(columns=["supplier_id", "ordered", "accepted",
                                  "week_start"]),
            pd.Timestamp("2026-02-02"), fallback={"S1": 0.7},
            pool_fallback=0.7)
        assert fills["S1"] == pytest.approx(0.7)

    def test_fills_are_clipped_to_unit_interval(self):
        deliveries = pd.DataFrame([
            {"supplier_id": "S1", "product_id": "tomato", "ordered": 100.0,
             "accepted": 130.0, "week_start": pd.Timestamp("2026-02-02")},
        ])
        fills = realized_fills(deliveries, pd.Timestamp("2026-02-02"),
                               fallback={}, pool_fallback=1.0)
        assert fills["S1"] == pytest.approx(1.0)

    def test_only_the_settled_week_is_read(self):
        """Deliveries from other weeks must not influence this week."""
        deliveries = pd.DataFrame([
            {"supplier_id": "S1", "product_id": "tomato", "ordered": 100.0,
             "accepted": 10.0, "week_start": pd.Timestamp("2026-02-09")},
        ])
        fills = realized_fills(deliveries, pd.Timestamp("2026-02-02"),
                               fallback={"S1": 0.75}, pool_fallback=0.75)
        assert fills["S1"] == pytest.approx(0.75)


def test_settlement_is_deterministic():
    alloc = {("S1", "tomato"): 900.0, ("S2", "lettuce"): 400.0}
    realized = {"tomato": 800.0, "lettuce": 500.0}
    fills = {"S1": 0.85, "S2": 0.95}
    a = settle(alloc, realized, fills, ECON, 1.30, 0.30)
    b = settle(alloc, realized, fills, ECON, 1.30, 0.30)
    assert np.allclose(a, b)


class TestZeroDemandProducts:
    """Committed stock for a product that sold nothing must still be waste.

    Settlement previously iterated only products with positive realized
    demand, so a commitment to a zero-demand product escaped scoring
    entirely: it arrived, sold nothing, and cost the policy nothing. That
    is invisible where every product sells every week, and silently
    forgiving on intermittent real data.
    """

    def test_zero_demand_commitment_is_charged_as_waste(self):
        cost, served, waste, delivered = settle(
            {("S1", "tomato"): 100.0, ("S1", "lettuce"): 500.0},
            {"tomato": 100.0},          # lettuce had NO demand this week
            {"S1": 1.0}, ECON, 1.30, 0.30)
        assert waste == pytest.approx(500.0)
        assert cost == pytest.approx(500.0 * ECON["lettuce"]["cost"])
        assert served == pytest.approx(100.0)
        assert delivered == pytest.approx(600.0)

    def test_zero_demand_waste_scales_with_fill(self):
        """Only what actually ARRIVED can be wasted."""
        _, _, waste, _ = settle(
            {("S1", "lettuce"): 500.0}, {"tomato": 0.0},
            {"S1": 0.4}, ECON, 1.30, 0.30)
        assert waste == pytest.approx(200.0)

    def test_no_commitment_and_no_demand_costs_nothing(self):
        assert settle({}, {}, {}, ECON, 1.30, 0.30) == (0.0, 0.0, 0.0, 0.0)


class TestGateSafety:
    """force_unit_fills is a diagnostic mode and must never open the gate."""

    def test_forced_unit_fills_cannot_pass_the_gate(self):
        import duckdb

        from backtesting.benchmark_suite import run_benchmark
        from scripts.setup_db import setup_db
        from synthetic.indiana_operator_sim import (
            IndianaSimulationConfig, build_indiana_dataset,
        )

        conn = duckdb.connect(":memory:")
        setup_db(conn)
        build_indiana_dataset(conn, IndianaSimulationConfig(seed=11, weeks=80))
        forced = run_benchmark(conn, n_folds=6, train_weeks=52,
                               force_unit_fills=True)
        assert forced["gate_passed"] is False
        assert forced["settlement"]["fills_replayed"] is False
        assert "FORCED UNIT FILLS" in forced["scoring"]

        real = run_benchmark(conn, n_folds=6, train_weeks=52)
        assert real["settlement"]["fills_replayed"] is True
