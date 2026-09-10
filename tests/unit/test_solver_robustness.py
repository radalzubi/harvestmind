"""The solver can say no. The engine must report it, never disguise it."""
from __future__ import annotations

import pandas as pd
import pyomo.environ as pyo
import pytest

from optimization.solve_status import run_solver
from optimization.two_stage_sp import TwoStageStochasticLP


def _infeasible():
    m = pyo.ConcreteModel()
    m.x = pyo.Var(domain=pyo.NonNegativeReals)
    m.c = pyo.Constraint(expr=m.x <= -1)
    m.o = pyo.Objective(expr=m.x)
    return m


def _unbounded():
    m = pyo.ConcreteModel()
    m.x = pyo.Var(domain=pyo.Reals)
    m.o = pyo.Objective(expr=m.x)
    return m


def _fine():
    m = pyo.ConcreteModel()
    m.x = pyo.Var(domain=pyo.NonNegativeReals, bounds=(0, 10))
    m.c = pyo.Constraint(expr=m.x >= 3)
    m.o = pyo.Objective(expr=2 * m.x)
    return m


class TestRunSolver:
    def test_infeasible_is_a_status_not_an_exception(self):
        out = run_solver(_infeasible())
        assert out.status == "infeasible" and not out.usable and out.objective is None

    def test_unbounded_reported_with_warning(self):
        out = run_solver(_unbounded())
        assert out.status in ("unbounded", "infeasible", "error")
        assert not out.usable
        assert out.warnings

    def test_optimal_loads_solution_and_objective(self):
        m = _fine()
        out = run_solver(m)
        assert out.status == "optimal" and out.usable
        assert out.objective == pytest.approx(6.0)
        assert pyo.value(m.x) == pytest.approx(3.0)
        assert out.runtime_s >= 0

    def test_unknown_solver_is_an_error_not_a_crash(self):
        out = run_solver(_fine(), solver="no_such_solver_xyz")
        assert out.status == "error" and not out.usable and out.warnings


class TestTwoStageFailureModes:
    def _inputs(self):
        scen = pd.DataFrame([
            {"scenario_index": w, "scenario_weight": 0.5, "product_id": "A",
             "week_start": "2026-01-05", "demand_kg": 100.0 + 50 * w} for w in (0, 1)])
        sup = pd.DataFrame([{"supplier_id": "S1", "product_id": "A",
                             "week_start": "2026-01-05", "capacity_kg": 20.0,
                             "price_per_kg": 2.0}])
        return scen, sup

    def test_unattainable_service_floor_returns_unusable_and_empty(self):
        """Capacity 20 cannot serve 99% of demand 100-150 with spot capped at 0:
        infeasible. The result must say so and carry no decision."""
        scen, sup = self._inputs()
        r = TwoStageStochasticLP(service_level_floor=0.99, spot_capacity_factor=0.0,
                                 newsvendor_objective=True,
                                 unmet_cost_by_product={"A": 1.0},
                                 waste_cost_by_product={"A": 1.0}).solve(scen, sup)
        assert r["usable"] is False
        assert r["status"] == "infeasible"
        assert r["x"] == {} and r["objective"] is None

    def test_feasible_run_is_marked_usable(self):
        scen, sup = self._inputs()
        r = TwoStageStochasticLP(newsvendor_objective=True,
                                 unmet_cost_by_product={"A": 1.0},
                                 waste_cost_by_product={"A": 1.0}).solve(scen, sup)
        assert r["usable"] is True and r["status"] == "optimal"
        assert r["runtime_s"] >= 0 and r["warnings"] == []
