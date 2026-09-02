"""Guardrails for the full synthetic mechanism sweep."""

from __future__ import annotations

import duckdb
import pytest

from backtesting.benchmark_suite import settle
from risk.correlated_scenarios import SupplyRiskPolicy
from scripts.setup_db import setup_db
from synthetic.indiana_operator_sim import (
    IndianaSimulationConfig,
    build_indiana_dataset,
)


def _dataset(config: IndianaSimulationConfig):
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    metadata = build_indiana_dataset(conn, config)
    return conn, metadata


def test_zero_demand_commitment_is_charged_as_overage():
    econ = {"tomato": {"cost": 2.0, "margin": 6.0}}
    cost, served, waste, delivered = settle(
        {("S1", "tomato"): 100.0}, {}, {"S1": 0.8}, econ, 1.3, 0.3)
    assert delivered == pytest.approx(80.0)
    assert waste == pytest.approx(80.0)
    assert cost == pytest.approx(160.0)
    assert served == 0.0


@pytest.mark.parametrize("target", [0.99, 0.95, 0.85, 0.70])
def test_controlled_fill_hits_named_factor(target):
    conn, metadata = _dataset(IndianaSimulationConfig(
        seed=11, weeks=30, mean_supplier_fill_rate=target))
    try:
        assert metadata["observed_weighted_supplier_fill_rate"] == pytest.approx(
            target, abs=0.003)
    finally:
        conn.close()


def test_intermittency_cell_is_auditable_and_routes_sparse_products():
    from backtesting.benchmark_suite import run_benchmark

    conn, metadata = _dataset(IndianaSimulationConfig(
        seed=23, weeks=60, mean_supplier_fill_rate=0.85,
        demand_zero_rate=0.50))
    try:
        result = run_benchmark(conn, n_folds=2, train_weeks=52)
        assert metadata["observed_demand_zero_rate"] == pytest.approx(0.50, abs=0.04)
        assert result["demand_routing"]["croston"] > 0
    finally:
        conn.close()


def test_correlated_policy_is_wired_without_estimation_leakage():
    from backtesting.benchmark_suite import run_benchmark

    conn, _ = _dataset(IndianaSimulationConfig(
        seed=42, weeks=60, mean_supplier_fill_rate=0.85,
        supplier_kendall_tau=0.3))
    try:
        result = run_benchmark(
            conn, n_folds=2, train_weeks=52,
            supply_risk_policy=SupplyRiskPolicy(
                mode="equicorrelated", copula="gaussian",
                kendall_tau=0.3, seed=42),
        )
        assert result["supply_risk"]["correlation_source"] == "operator_supplied_tau"
        assert result["supply_risk"]["training_window_only"] is True
        assert result["supply_risk"]["target_kendall_tau"] == pytest.approx(0.3)
    finally:
        conn.close()


def test_invalid_cost_ratio_fails_closed():
    from backtesting.benchmark_suite import run_benchmark

    conn, _ = _dataset(IndianaSimulationConfig(seed=11, weeks=30))
    try:
        with pytest.raises(ValueError, match="must be positive"):
            run_benchmark(conn, underage_overage_ratio=0)
    finally:
        conn.close()


def test_commercial_gate_requires_service_floor():
    from backtesting.benchmark_suite import run_benchmark

    conn, _ = _dataset(IndianaSimulationConfig(
        seed=42, weeks=80, mean_supplier_fill_rate=0.85,
        demand_zero_rate=0.50))
    try:
        result = run_benchmark(conn, n_folds=4, train_weeks=52)
        assert result["sp_vs_deterministic_lp"]["edge_pct"] > 0
        assert result["service_floor"]["met"] is False
        assert result["gate_passed"] is False
    finally:
        conn.close()
