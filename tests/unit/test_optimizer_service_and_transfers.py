"""Service floors and inter-location transfers in the multi-period model."""
from __future__ import annotations

import pandas as pd
import pyomo.environ as pyo
import pytest

from optimization.multi_period_sp import MultiPeriodStochasticLP

T = 4


def _scen(paths, products):
    n = len(paths)
    return pd.DataFrame([{"scenario_index": w, "scenario_weight": 1 / n, "product_id": j,
                          "period": t, "demand_kg": float(paths[w][j][t])}
                         for w in range(n) for j in products for t in range(T)])


def _kw(products, unmet=0.01, holding=0.05, **extra):
    base = dict(n_periods=T, spot_cost_multiplier=1.0, spot_capacity_factor=0.0,
                holding_cost_by_product={j: holding for j in products},
                unmet_cost_by_product={j: unmet for j in products},
                waste_cost_by_product={j: 2.0 for j in products},
                decay_rate_by_product={j: 0.0 for j in products})
    base.update(extra)
    return base


class TestServiceFloor:
    def test_floor_is_honoured_in_expectation(self):
        """With a negligible shortage cost the unconstrained model would let
        demand go unmet; the floor forces it to serve 95% in expectation."""
        prods = ("A",)
        scen = _scen([{"A": [100] * T}, {"A": [140] * T}], prods)
        sup = pd.DataFrame([{"supplier_id": "S", "product_id": "A", "capacity_kg": 500.0, "price_per_kg": 1.0}])
        free = MultiPeriodStochasticLP(**_kw(prods)).solve(scen, sup, lead_times={(0, "S"): 0, (1, "S"): 0})
        floored = MultiPeriodStochasticLP(**_kw(prods), service_floor_by_product={"A": 0.95}).solve(
            scen, sup, lead_times={(0, "S"): 0, (1, "S"): 0})
        m = floored["model"]
        exp_unmet = sum(0.5 * pyo.value(m.u["A", t, w]) for w in m.W for t in range(T))
        assert exp_unmet <= 0.05 * 0.5 * (100 + 140) * T + 1e-6
        assert sum(floored["x"].values()) >= sum(free["x"].values()) - 1e-6

    def test_unattainable_floor_is_reported_infeasible(self):
        prods = ("A",)
        scen = _scen([{"A": [100] * T}], prods)
        sup = pd.DataFrame([{"supplier_id": "S", "product_id": "A", "capacity_kg": 10.0, "price_per_kg": 1.0}])
        r = MultiPeriodStochasticLP(**_kw(prods), service_floor_by_product={"A": 0.99}).solve(
            scen, sup, lead_times={(0, "S"): 0})
        assert r["status"] == "infeasible" and not r["usable"] and r["x"] == {}

    def test_invalid_floor_rejected(self):
        with pytest.raises(ValueError):
            MultiPeriodStochasticLP(**_kw(("A",)), service_floor_by_product={"A": 1.5}).solve(
                _scen([{"A": [1] * T}], ("A",)),
                pd.DataFrame([{"supplier_id": "S", "product_id": "A", "capacity_kg": 1.0, "price_per_kg": 1.0}]))


class TestTransfers:
    def _two_sites(self, transfer_cost=0.1, lead=0):
        prods = ("SKU@A", "SKU@B")
        # A has stock and no demand; B has demand and no supplier.
        scen = _scen([{"SKU@A": [0] * T, "SKU@B": [50] * T}], prods)
        sup = pd.DataFrame([{"supplier_id": "S", "product_id": "SKU@A", "capacity_kg": 0.0, "price_per_kg": 1.0},
                            {"supplier_id": "S", "product_id": "SKU@B", "capacity_kg": 0.0, "price_per_kg": 1.0}])
        r = MultiPeriodStochasticLP(**_kw(prods, unmet=5.0), transfer_arcs=[("SKU@A", "SKU@B", transfer_cost, lead)]).solve(
            scen, sup, lead_times={(0, "S"): 0}, opening_inventory={"SKU@A": 300.0, "SKU@B": 0.0})
        return r

    def test_stock_moves_to_where_demand_is(self):
        r = self._two_sites()
        assert r["usable"]
        moved = sum(q for (a, b, t, w), q in r["transfers"].items())
        assert moved == pytest.approx(200.0, abs=1e-6)          # 4 periods x 50
        m = r["model"]
        assert sum(pyo.value(m.u["SKU@B", t, 0]) for t in range(T)) == pytest.approx(0.0, abs=1e-6)

    def test_conservation_across_locations(self):
        r = self._two_sites(lead=1)
        m = r["model"]
        total_open = 300.0
        served = sum(50 - pyo.value(m.u["SKU@B", t, 0]) for t in range(T))
        ending = sum(pyo.value(m.inv[j, T - 1, 0]) for j in ("SKU@A", "SKU@B"))
        in_transit = sum(q for (a, b, t, w), q in r["transfers"].items() if t + 1 >= T)
        assert total_open == pytest.approx(served + ending + in_transit, abs=1e-6)

    def test_cannot_ship_more_than_opening_stock(self):
        r = self._two_sites(lead=0)
        m = r["model"]
        for t in range(T):
            prev = 300.0 if t == 0 else pyo.value(m.inv["SKU@A", t - 1, 0])
            out = sum(q for (a, b, tt, w), q in r["transfers"].items() if tt == t)
            assert out <= prev + 1e-6

    def test_no_transfer_when_it_costs_more_than_the_shortage(self):
        r = self._two_sites(transfer_cost=50.0)
        assert sum(r["transfers"].values()) == pytest.approx(0.0, abs=1e-6)

    def test_negative_transfer_cost_rejected(self):
        with pytest.raises(ValueError):
            self._two_sites(transfer_cost=-1.0)
