"""Regression tests for the real-data commercial validation harness.

Each test here corresponds to a defect that was actually found during the
validation, not to a hypothetical one. Three of them silently moved a
headline before they were caught.
"""
from __future__ import annotations

import importlib.util
import statistics as st
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from validation.commercial import real_data as rd  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "_vcrd", ROOT / "scripts" / "validate_commercial_real_data.py")
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)

DATA_PRESENT = (ROOT / "data" / "external" / "fred" /
                f"{rd.DEMAND_SERIES}.csv").exists()
needs_data = pytest.mark.skipif(
    not DATA_PRESENT, reason="run scripts/fetch_real_data.py first")


def _op(n_sku=4, n_sup=2, seed=3):
    return V.build_operator(n_sku, n_sup, seed)


class TestHarnessFailureIsNotAnOutcomeFilter:
    """The defect that mattered most.

    An earlier guard rejected folds where one cost component dominated. It
    threw out 136 of 258 folds whose median edge was -4.21%, against
    +7.33% for those it kept, and so selected the folds where the
    stochastic policy wins. Rejection must depend only on the harness
    being broken, never on how the result came out.
    """

    def test_holding_dominated_fold_is_admitted(self):
        res = {"fill_rate": 1.0, "total": 100.0, "shortage": 0.0,
               "holding": 100.0, "overflow": 0.0}
        assert V._harness_failure(res) is None

    def test_shortage_dominated_fold_is_admitted(self):
        res = {"fill_rate": 0.62, "total": 100.0, "shortage": 99.5,
               "holding": 0.5, "overflow": 0.0}
        assert V._harness_failure(res) is None

    def test_low_service_is_a_result_not_a_failure(self):
        """A policy genuinely achieving poor service is a finding. Dropping
        those folds removes the baseline's worst outcomes."""
        res = {"fill_rate": 0.40, "total": 100.0, "shortage": 90.0,
               "holding": 10.0, "overflow": 0.0}
        assert V._harness_failure(res) is None

    def test_impossible_fill_rate_is_a_failure(self):
        for fr in (-0.01, 1.5):
            res = {"fill_rate": fr, "total": 10.0, "shortage": 5.0,
                   "holding": 5.0, "overflow": 0.0}
            assert V._harness_failure(res) is not None

    def test_overflow_majority_is_a_failure(self):
        """Only reachable if the optimizer and the replay disagree about
        what disposal costs, which is a real bug and not a hard month."""
        res = {"fill_rate": 1.0, "total": 100.0, "shortage": 0.0,
               "holding": 10.0, "overflow": 90.0}
        assert V._harness_failure(res) is not None

    def test_zero_cost_leaves_nothing_to_compare(self):
        res = {"fill_rate": 1.0, "total": 0.0, "shortage": 0.0,
               "holding": 0.0, "overflow": 0.0}
        assert V._harness_failure(res) is not None


class TestWarehouseCap:
    """Stock above the cap must be written off, not silently carried."""

    def test_overflow_is_charged_when_the_cap_binds(self):
        op = _op()
        months = ["2024-01", "2024-02"]
        skus = [s["sku"] for s in op["skus"]]
        demand = {(j, m): 1.0 for j in skus for m in months}
        sup = op["skus"][0]["supplier_id"]
        # A huge single order into a tiny warehouse.
        sched = {(sup, skus[0], 0): 10_000.0}
        real_fill = {(s, t): 1.0 for s in op["suppliers"] for t in (0, 1)}
        real_lead = {(s, t): 0 for s in op["suppliers"] for t in (0, 1)}
        opening = {j: 0.0 for j in skus}
        tight = V.settle(sched, op, months, demand, real_fill, real_lead,
                         opening, warehouse_cap=5.0)
        loose = V.settle(sched, op, months, demand, real_fill, real_lead,
                         opening, warehouse_cap=None)
        assert tight["overflow"] > 0.0
        assert loose["overflow"] == 0.0
        assert tight["ending_inventory"] <= 5.0 + 1e-6

    def test_uncapped_settlement_is_unchanged(self):
        """Project A calls this path with no cap and must not shift."""
        op = _op()
        months = ["2024-01"]
        skus = [s["sku"] for s in op["skus"]]
        demand = {(j, months[0]): 2.0 for j in skus}
        opening = {j: 5.0 for j in skus}
        r = V.settle({}, op, months, demand, {}, {}, opening,
                     warehouse_cap=None)
        assert r["overflow"] == 0.0
        assert r["fill_rate"] == pytest.approx(1.0)


class TestOptimizerInventoryCapIsOptional:
    """Project A must be bit-identical when the cap is not requested."""

    def test_defaults_leave_the_model_unconstrained(self):
        from optimization.multi_period_sp import MultiPeriodStochasticLP
        m = MultiPeriodStochasticLP()
        assert m.inventory_capacity_total is None
        assert m.inventory_capacity_by_product is None


@needs_data
class TestRealSeries:
    def test_demand_index_spans_three_decades(self):
        idx = rd.demand_index()
        assert len(idx) > 380
        assert min(idx) <= "1992-12" and max(idx) >= "2025-12"
        assert st.mean(idx.values()) == pytest.approx(1.0, abs=1e-9)

    def test_demand_series_is_not_seasonally_adjusted(self):
        """Seasonality is the signal being forecast. An adjusted series has
        had it filtered out, and December must still stand out."""
        idx = rd.demand_index()
        by_month: dict[str, list[float]] = {}
        for m, v in idx.items():
            by_month.setdefault(m[5:7], []).append(v)
        means = {k: st.mean(v) for k, v in by_month.items()}
        assert max(means.values()) / min(means.values()) > 1.10

    def test_route_shocks_are_bounded_multipliers(self):
        panel = rd.route_shock_panel()
        for route, series in panel.items():
            assert series, f"{route} produced no observations"
            for m, v in series.items():
                assert 0.0 < v <= 1.0, f"{route} {m} = {v}"

    def test_domestic_routes_are_unexposed_to_a_port_shock(self):
        """Route substitution only has value if some route is spared."""
        panel = rd.route_shock_panel()
        for route in ("local", "air"):
            assert set(panel[route].values()) == {1.0}

    def test_aqaba_is_the_most_disrupted_sea_route_in_the_crisis(self):
        """Aqaba sits inside Bab el-Mandeb; the Cape reroute cannot serve
        it. Its worst months on record should be the war months."""
        s = rd.port_shock_series("Aqaba", relative=False)
        worst = sorted(s.items(), key=lambda kv: kv[1])[:5]
        assert all("2023-12" <= m <= "2024-12" for m, _ in worst)
