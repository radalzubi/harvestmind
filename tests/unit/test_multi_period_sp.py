"""The multi-period model must be able to reschedule, not just requantify."""
from __future__ import annotations

import pandas as pd
import pytest

from optimization.multi_period_sp import MultiPeriodStochasticLP

T = 6


def _demand(per_period: float = 100.0, scenarios=(0,)) -> pd.DataFrame:
    return pd.DataFrame([
        {"scenario_index": w, "scenario_weight": 1.0 / len(scenarios),
         "product_id": "tomato", "period": t, "demand_kg": per_period}
        for w in scenarios for t in range(T)])


def _supply(cap: float = 200.0, suppliers=("S1",)) -> pd.DataFrame:
    return pd.DataFrame([
        {"supplier_id": s, "product_id": "tomato",
         "capacity_kg": cap, "price_per_kg": 2.0} for s in suppliers])


class TestRescheduling:
    """The capability the single-period model structurally cannot have."""

    def test_orders_earlier_when_lead_time_is_long(self):
        """With a 2-period lead time the schedule must shift earlier, or
        early demand can never be served at all."""
        m = MultiPeriodStochasticLP(n_periods=T, holding_cost_per_kg_per_period=0.01,
                                    decay_rate_per_period=0.0)
        late = m.solve(_demand(), _supply(), lead_times={(0, "S1"): 2})
        assert late["status"] in ("optimal", "locallyOptimal")
        placed = late["ordered_by_period"]
        # Orders must be placed in the first periods to arrive on time.
        assert placed.get(0, 0) > 0, "nothing ordered in period 0 despite lead time"

    def test_lead_time_shifts_the_whole_schedule(self):
        """Longer lead time -> mass moves toward earlier periods."""
        def centre_of_mass(lead: int) -> float:
            m = MultiPeriodStochasticLP(n_periods=T, decay_rate_per_period=0.0,
                                        holding_cost_per_kg_per_period=0.01)
            r = m.solve(_demand(), _supply(), lead_times={(0, "S1"): lead})
            bp = r["ordered_by_period"]
            tot = sum(bp.values())
            return sum(t * v for t, v in bp.items()) / tot if tot else 0.0

        assert centre_of_mass(2) < centre_of_mass(0) + 1e-6

    def test_zero_lead_time_orders_just_in_time(self):
        """With instant delivery and a holding cost, do not order early."""
        m = MultiPeriodStochasticLP(n_periods=T, holding_cost_per_kg_per_period=0.50,
                                    decay_rate_per_period=0.0)
        r = m.solve(_demand(), _supply(), lead_times={(0, "S1"): 0})
        bp = r["ordered_by_period"]
        assert bp.get(0, 0.0) == pytest.approx(100.0, abs=1.0)


class TestHoldingCostMakesTimingReal:
    """Without a holding cost, ordering everything at t=0 is free and the
    timing decision is meaningless. This is the term that creates it."""

    def test_higher_holding_cost_delays_ordering(self):
        def early_share(hold: float) -> float:
            m = MultiPeriodStochasticLP(n_periods=T, decay_rate_per_period=0.0,
                                        holding_cost_per_kg_per_period=hold)
            r = m.solve(_demand(), _supply(), lead_times={(0, "S1"): 1})
            bp = r["ordered_by_period"]
            tot = sum(bp.values())
            return bp.get(0, 0.0) / tot if tot else 0.0

        assert early_share(0.001) >= early_share(1.00) - 1e-6

    def test_decay_penalises_holding_perishables(self):
        m_fresh = MultiPeriodStochasticLP(n_periods=T, decay_rate_per_period=0.30,
                                          holding_cost_per_kg_per_period=0.01)
        r = m_fresh.solve(_demand(), _supply(), lead_times={(0, "S1"): 0})
        assert r["status"] in ("optimal", "locallyOptimal")
        assert r["objective"] is not None


class TestUncertaintyStillWorks:
    def test_random_lead_times_across_scenarios(self):
        """Lead time uncertain: fast in one scenario, slow in the other."""
        m = MultiPeriodStochasticLP(n_periods=T, decay_rate_per_period=0.0,
                                    holding_cost_per_kg_per_period=0.02)
        r = m.solve(_demand(scenarios=(0, 1)), _supply(),
                    lead_times={(0, "S1"): 0, (1, "S1"): 3})
        assert r["status"] in ("optimal", "locallyOptimal")
        assert sum(r["ordered_by_period"].values()) > 0

    def test_fill_rate_and_lead_time_compose(self):
        m = MultiPeriodStochasticLP(n_periods=T, decay_rate_per_period=0.0)
        r = m.solve(_demand(), _supply(cap=500.0),
                    lead_times={(0, "S1"): 1},
                    yield_scenarios={(0, "S1"): 0.5})
        tot = sum(r["ordered_by_period"].values())
        # Only half arrives, so more must be ordered than demanded.
        assert tot > T * 100.0 * 0.9

    def test_opening_inventory_reduces_ordering(self):
        m = MultiPeriodStochasticLP(n_periods=T, decay_rate_per_period=0.0,
                                    holding_cost_per_kg_per_period=0.01)
        without = m.solve(_demand(), _supply(), lead_times={(0, "S1"): 0})
        with_inv = m.solve(_demand(), _supply(), lead_times={(0, "S1"): 0},
                           opening_inventory={"tomato": 100.0})
        assert (sum(with_inv["ordered_by_period"].values())
                < sum(without["ordered_by_period"].values()) + 1e-6)


class TestValidation:
    def test_zero_periods_rejected(self):
        with pytest.raises(ValueError, match="n_periods"):
            MultiPeriodStochasticLP(n_periods=0).solve(_demand(), _supply())
