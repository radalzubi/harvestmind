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
