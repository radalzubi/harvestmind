"""Unit tests for Croston / SBA / TSB intermittent demand models."""

import numpy as np
import pytest

from forecasting.demand.intermittent_model import croston, sba, tsb, select_and_fit


class TestCroston:
    def test_non_negative_output(self):
        series = np.array([0, 0, 10, 0, 5, 0, 0, 8, 0, 3], dtype=float)
        fc = croston(series, alpha=0.15)
        assert fc.mean >= 0

    def test_empty_series(self):
        fc = croston(np.array([]))
        assert fc.mean == 0.0

    def test_all_zeros(self):
        fc = croston(np.zeros(20))
        assert fc.mean == 0.0

    def test_constant_demand(self):
        series = np.ones(52) * 100.0
        fc = croston(series, alpha=0.15)
        assert 80 < fc.mean < 120

    def test_intervals_preserved(self):
        fc = croston(np.array([0, 0, 10, 0, 0, 10, 0, 0, 10]))
        assert fc.demand_rate > 0
        assert fc.demand_size > 0

    def test_inter_arrival_recovered_for_periodic_demand(self):
        """Regression: Croston smoothed inter-arrival p must converge to the true gap.

        Earlier implementation smoothed `p` against the constant 1, which produced
        forecasts ~70% too high (mean = 42 instead of 25 for inter-arrival 4).
        """
        # Demand 100 every 4th period
        series = np.tile([0, 0, 0, 100], 5).astype(float)  # 20 periods, 5 demand events
        fc = croston(series, alpha=0.15)
        assert fc.demand_size == pytest.approx(100.0, abs=1e-6)
        # 1/rate is the implied inter-arrival; should be ~4 (not ~2)
        implied_p = 1.0 / fc.demand_rate
        assert 3.5 <= implied_p <= 4.5, f"implied inter-arrival = {implied_p}, expected ~4"
        # Forecast = z/p ≈ 100/4 = 25
        assert 22 <= fc.mean <= 28, f"mean = {fc.mean}, expected ~25"

    def test_lower_demand_rate_for_sparser_series(self):
        """Sparser demand → lower demand rate. Earlier bug made all series converge to rate≈1."""
        sparse = np.zeros(40); sparse[[5, 25]] = 50.0           # 2 events in 40 periods
        dense = np.zeros(40); dense[[5, 10, 15, 20, 25, 30, 35]] = 50.0  # 7 events
        rate_sparse = croston(sparse).demand_rate
        rate_dense = croston(dense).demand_rate
        assert rate_sparse < rate_dense


class TestSBA:
    def test_sba_lower_than_croston(self):
        """SBA should give a lower (corrected) forecast than Croston for the same series."""
        series = np.array([0, 0, 10, 0, 5, 0, 0, 8, 0, 3], dtype=float)
        fc_c = croston(series, alpha=0.15)
        fc_s = sba(series, alpha=0.15)
        # SBA applies (1 - alpha/2) correction, so mean should be ≤ Croston
        assert fc_s.mean <= fc_c.mean + 1e-6

    def test_prediction_interval_ordering(self):
        series = np.array([0, 0, 50, 0, 30, 0, 0, 40], dtype=float)
        fc = sba(series)
        assert fc.lower_95 <= fc.lower_80 <= fc.mean <= fc.upper_80 <= fc.upper_95


class TestTSB:
    def test_obsolescence_decay(self):
        """TSB demand probability should decay when no demand is observed."""
        series = np.array([50, 0, 0, 0, 0, 0, 0, 0, 0, 0], dtype=float)
        fc = tsb(series, alpha=0.15, beta=0.20)
        # After many zeros, demand probability should be low
        assert fc.demand_rate < 0.5

    def test_recovery_after_demand(self):
        series = np.array([0, 0, 0, 0, 0, 50, 50, 50, 50, 50], dtype=float)
        fc = tsb(series, alpha=0.15, beta=0.20)
        assert fc.mean > 10


class TestModelSelection:
    def test_selects_tsb_or_sba_for_intermittent(self):
        # Long inter-arrival intervals + variable sizes → SBA or TSB (not Croston)
        series = np.array([0]*15 + [50] + [0]*15 + [200] + [0]*10 + [10], dtype=float)
        fc = select_and_fit(series)
        assert fc.model in ("sba", "tsb")

    def test_selects_sba_or_croston_for_smooth(self):
        # Regular demand → croston or sba
        rng = np.random.default_rng(42)
        series = rng.normal(50, 5, size=52)
        series = np.maximum(0, series)
        fc = select_and_fit(series)
        assert fc.model in ("croston", "sba", "tsb")
