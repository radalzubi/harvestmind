"""Mathematical invariants of the multi-period stochastic optimizer.

Each test encodes a property that must hold for ANY valid input, phrased so
that a violation is a bug in the model and not a preference. Where a test
checks economics (monotonicity, deterministic equivalence) it does so on
instances small enough that the expected direction is unambiguous.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pyomo.environ as pyo
import pytest

from domain.uom import PackSpec, Unit
from optimization.multi_period_sp import MultiPeriodStochasticLP

T = 4


def _scen(demands_by_scenario, weights=None, products=("A",)):
    rows = []
    n = len(demands_by_scenario)
    for w, path in enumerate(demands_by_scenario):
        wt = (weights[w] if weights else 1.0 / n)
        for j in products:
            for t in range(T):
                rows.append({"scenario_index": w, "scenario_weight": wt,
                             "product_id": j, "period": t,
                             "demand_kg": float(path[t])})
    return pd.DataFrame(rows)


def _supply(cap=400.0, price=2.0, products=("A",), suppliers=("S1",)):
    return pd.DataFrame([{"supplier_id": i, "product_id": j,
                          "capacity_kg": cap, "price_per_kg": price}
                         for i in suppliers for j in products])


def _kw(products=("A",), holding=0.02, unmet=1.0, waste=2.0, decay=0.0, **extra):
    base = dict(n_periods=T, spot_cost_multiplier=1.0, spot_capacity_factor=0.0,
                holding_cost_by_product={j: holding for j in products},
                unmet_cost_by_product={j: unmet for j in products},
                waste_cost_by_product={j: waste for j in products},
                decay_rate_by_product={j: decay for j in products})
    base.update(extra)
    return base


def _leads(sups=("S1",), n_scen=2, lead=1):
    return {(w, i): lead for w in range(n_scen) for i in sups}


def _balance_residuals(model, products, T, opening, fills, leads):
    """Recompute opening + arrivals + spot - served - waste - closing per (j,t,w)."""
    out = []
    for w in model.W:
        for j in products:
            prev = float(opening.get(j, 0.0))
            for t in range(T):
                arrivals = 0.0
                for (i, jj) in model.IJ:
                    if jj != j:
                        continue
                    placed = t - leads.get((w, i), 0)
                    if 0 <= placed < T:
                        arrivals += fills.get((w, i), 1.0) * pyo.value(model.x[i, j, placed])
                d = 0.0
                for (ww, jj, tt), dv in getattr(model, "_d", {}).items():
                    pass
                served = None  # not directly exposed; use balance identity
                inv = pyo.value(model.inv[j, t, w])
                s = pyo.value(model.s[j, t, w])
                wst = pyo.value(model.wst[j, t, w])
                u = pyo.value(model.u[j, t, w])
                out.append((w, j, t, prev, arrivals, s, wst, u, inv))
                prev = inv
    return out


class TestConservationAndSigns:
    def test_inventory_balance_holds_in_every_scenario_and_period(self):
        scen = _scen([[100, 120, 90, 110], [140, 80, 130, 100]])
        sup = _supply()
        opening = {"A": 50.0}
        fills = {(0, "S1"): 0.9, (1, "S1"): 0.8}
        leads = _leads(lead=1)
        r = MultiPeriodStochasticLP(**_kw()).solve(
            scen, sup, lead_times=leads, yield_scenarios=fills,
            opening_inventory=opening)
        assert r["usable"]
        m = r["model"]
        d = {(int(row.scenario_index), row.product_id, int(row.period)): float(row.demand_kg)
             for row in scen.itertuples()}
        for w in m.W:
            prev = opening["A"]
            for t in range(T):
                arr = sum(fills[(w, i)] * pyo.value(m.x[i, "A", t - leads[(w, i)]])
                          for (i, jj) in m.IJ if jj == "A" and 0 <= t - leads[(w, i)] < T)
                served = d[(w, "A", t)] - pyo.value(m.u["A", t, w])
                closing = pyo.value(m.inv["A", t, w])
                lhs = prev + arr + pyo.value(m.s["A", t, w]) - served - pyo.value(m.wst["A", t, w])
                assert lhs == pytest.approx(closing, abs=1e-6), (w, t)
                prev = closing

    def test_no_negative_quantities_anywhere(self):
        scen = _scen([[100, 120, 90, 110], [140, 80, 130, 100]])
        r = MultiPeriodStochasticLP(**_kw()).solve(scen, _supply(), lead_times=_leads())
        m = r["model"]
        for var in (m.x, m.inv, m.s, m.u, m.wst):
            for v in var.values():
                assert pyo.value(v) >= -1e-9

    def test_unmet_never_exceeds_demand(self):
        scen = _scen([[100, 120, 90, 110], [140, 80, 130, 100]])
        r = MultiPeriodStochasticLP(**_kw(unmet=0.0)).solve(scen, _supply(cap=0.0),
                                                           lead_times=_leads())
        m = r["model"]
        d = {(int(x.scenario_index), int(x.period)): float(x.demand_kg) for x in scen.itertuples()}
        for w in m.W:
            for t in range(T):
                assert pyo.value(m.u["A", t, w]) <= d[(w, t)] + 1e-9

    def test_capacity_never_violated(self):
        scen = _scen([[500, 500, 500, 500], [600, 600, 600, 600]])
        r = MultiPeriodStochasticLP(**_kw(unmet=50.0)).solve(scen, _supply(cap=123.0),
                                                            lead_times=_leads())
        for v in r["x"].values():
            assert v <= 123.0 + 1e-9

    def test_inventory_cap_never_violated(self):
        scen = _scen([[100, 100, 100, 100], [100, 100, 100, 100]])
        r = MultiPeriodStochasticLP(**_kw(unmet=50.0), inventory_capacity_total=30.0).solve(
            scen, _supply(cap=1000.0), lead_times=_leads(lead=0))
        m = r["model"]
        for w in m.W:
            for t in range(T):
                assert pyo.value(m.inv["A", t, w]) <= 30.0 + 1e-9


class TestDiscreteOrdering:
    def test_orders_are_whole_cases(self):
        scen = _scen([[100, 120, 90, 110], [140, 80, 130, 100]])
        spec = PackSpec(units_per_case=12)
        r = MultiPeriodStochasticLP(**_kw(unmet=5.0), pack_specs={"A": spec}).solve(
            scen, _supply(), lead_times=_leads())
        assert r["usable"] and r["discrete_products"] == ["A"]
        for v in r["x"].values():
            assert abs(v / 12 - round(v / 12)) < 1e-9, v

    def test_moq_respected_or_zero(self):
        scen = _scen([[30, 30, 30, 30], [30, 30, 30, 30]])
        spec = PackSpec(units_per_case=10, moq_units=100)
        r = MultiPeriodStochasticLP(**_kw(unmet=5.0), pack_specs={"A": spec}).solve(
            scen, _supply(cap=500.0), lead_times=_leads())
        for v in r["x"].values():
            assert v == 0.0 or v >= 100.0 - 1e-9, v

    def test_pallet_multiple_and_max_order(self):
        scen = _scen([[600, 600, 600, 600], [600, 600, 600, 600]])
        spec = PackSpec(units_per_case=12, cases_per_layer=5, layers_per_pallet=4,
                        order_multiple=Unit.PALLET, max_units_per_order=480)
        assert spec.lot_units == 240
        r = MultiPeriodStochasticLP(**_kw(unmet=5.0), pack_specs={"A": spec}).solve(
            scen, _supply(cap=2000.0), lead_times=_leads())
        for v in r["x"].values():
            assert abs(v / 240 - round(v / 240)) < 1e-9 and v <= 480 + 1e-9

    def test_continuous_products_unaffected_by_other_products_specs(self):
        scen = _scen([[100, 100, 100, 100], [110, 110, 110, 110]], products=("A", "B"))
        sup = _supply(products=("A", "B"))
        r_plain = MultiPeriodStochasticLP(**_kw(products=("A", "B"), unmet=5.0)).solve(
            scen, sup, lead_times=_leads())
        r_mixed = MultiPeriodStochasticLP(**_kw(products=("A", "B"), unmet=5.0),
                                          pack_specs={"A": PackSpec(units_per_case=7)}).solve(
            scen, sup, lead_times=_leads())
        b_plain = {k: v for k, v in r_plain["x"].items() if k[1] == "B"}
        b_mixed = {k: v for k, v in r_mixed["x"].items() if k[1] == "B"}
        for k in b_plain:
            assert b_mixed[k] == pytest.approx(b_plain[k], abs=1e-6)


class TestProbabilityAndTiming:
    def test_scenario_weights_normalised_and_nonnegative(self):
        scen = _scen([[100] * T, [200] * T], weights=[3.0, 1.0])  # unnormalised
        r = MultiPeriodStochasticLP(**_kw()).solve(scen, _supply(), lead_times=_leads())
        assert r["usable"]
        # Objective must equal weighted recourse using the NORMALISED weights.
        m = r["model"]
        w_norm = {0: 0.75, 1: 0.25}
        recomputed = sum(
            w_norm[w] * sum(0.02 * pyo.value(m.inv["A", t, w]) + 1.0 * pyo.value(m.u["A", t, w])
                            + 2.0 * pyo.value(m.wst["A", t, w]) for t in range(T))
            for w in m.W)
        assert r["objective"] == pytest.approx(recomputed, rel=1e-6)

    def test_first_stage_is_scenario_invariant(self):
        """x has no scenario index: one schedule faces every scenario."""
        scen = _scen([[100, 120, 90, 110], [140, 80, 130, 100]])
        r = MultiPeriodStochasticLP(**_kw()).solve(scen, _supply(), lead_times=_leads())
        m = r["model"]
        assert m.x.index_set().dimen == 3          # (i, j, t) — no w
        assert m.inv.index_set().dimen == 3        # (j, t, w)

    def test_no_arrivals_before_lead_time(self):
        """An order placed at t arrives at t + L, never earlier."""
        scen = _scen([[0, 0, 100, 100], [0, 0, 100, 100]])
        r = MultiPeriodStochasticLP(**_kw(unmet=50.0)).solve(
            scen, _supply(), lead_times=_leads(lead=2))
        m = r["model"]
        # Period 0-1 have no demand; with L=2 the only way to serve t=2 is
        # ordering at t=0. Inventory at t=0,1 must be zero (no arrivals).
        for w in m.W:
            assert pyo.value(m.inv["A", 0, w]) == pytest.approx(0.0, abs=1e-6)
            assert pyo.value(m.inv["A", 1, w]) == pytest.approx(0.0, abs=1e-6)
        assert sum(v for (i, j, t), v in r["x"].items() if t >= 2) == pytest.approx(0.0, abs=1e-6)


class TestEconomics:
    def test_deterministic_equivalence_single_scenario(self):
        """One scenario: the SP is a deterministic LP and must match one."""
        path = [100, 120, 90, 110]
        scen1 = _scen([path])
        scen2 = _scen([path, path])          # identical duplicated scenario
        r1 = MultiPeriodStochasticLP(**_kw()).solve(scen1, _supply(), lead_times=_leads(n_scen=1))
        r2 = MultiPeriodStochasticLP(**_kw()).solve(scen2, _supply(), lead_times=_leads(n_scen=2))
        assert r1["objective"] == pytest.approx(r2["objective"], rel=1e-6)
        for k in r1["x"]:
            assert r1["x"][k] == pytest.approx(r2["x"][k], abs=1e-6)

    def test_higher_shortage_cost_never_lowers_total_orders(self):
        scen = _scen([[100, 120, 90, 110], [140, 80, 130, 100]])
        totals = []
        for cu in (0.5, 2.0, 8.0):
            r = MultiPeriodStochasticLP(**_kw(unmet=cu)).solve(scen, _supply(), lead_times=_leads())
            totals.append(sum(r["x"].values()))
        assert totals[0] <= totals[1] + 1e-6 <= totals[2] + 2e-6

    def test_free_disposal_exploit_is_closed(self):
        """Zero waste cost + tight inventory cap must not become 'order freely
        and dump'. With waste priced at unit cost the model orders no more
        than it can hold or sell."""
        scen = _scen([[100] * T, [100] * T])
        r = MultiPeriodStochasticLP(**_kw(unmet=5.0, waste=2.0),
                                    inventory_capacity_total=150.0).solve(
            scen, _supply(cap=10_000.0), lead_times=_leads(lead=0))
        m = r["model"]
        total_waste = sum(pyo.value(v) for v in m.wst.values())
        assert total_waste == pytest.approx(0.0, abs=1e-6)
        assert sum(r["x"].values()) <= T * 100 + 150 + 1e-6

    def test_objective_reconciles_to_components(self):
        scen = _scen([[100, 120, 90, 110], [140, 80, 130, 100]])
        r = MultiPeriodStochasticLP(**_kw(holding=0.03, unmet=1.5, waste=2.5, decay=0.1)).solve(
            scen, _supply(), lead_times=_leads())
        m = r["model"]
        comp = 0.0
        for w in m.W:
            comp += 0.5 * sum(0.03 * pyo.value(m.inv["A", t, w]) + 1.5 * pyo.value(m.u["A", t, w])
                              + 2.5 * pyo.value(m.wst["A", t, w]) for t in range(T))
        assert r["objective"] == pytest.approx(comp, rel=1e-6)

    def test_complete_recourse_means_always_feasible(self):
        """Unmet and waste are unbounded slacks, so any valid input is
        feasible: infeasibility can only come from a caller's bug."""
        scen = _scen([[1e6] * T, [0.0] * T])
        r = MultiPeriodStochasticLP(**_kw(), inventory_capacity_total=1.0).solve(
            scen, _supply(cap=0.0), lead_times=_leads(), opening_inventory={"A": 5e5})
        assert r["usable"] and r["status"] == "optimal"


class TestNumericalHygiene:
    def test_result_has_no_nan_or_inf(self):
        scen = _scen([[100, 120, 90, 110], [140, 80, 130, 100]])
        r = MultiPeriodStochasticLP(**_kw()).solve(scen, _supply(), lead_times=_leads())
        assert math.isfinite(r["objective"])
        assert all(math.isfinite(v) for v in r["x"].values())
        assert r["runtime_s"] >= 0.0
