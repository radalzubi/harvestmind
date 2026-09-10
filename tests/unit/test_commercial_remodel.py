"""Regression controls for the commercial audit, including adverse holdouts."""
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from backtesting import safe_selector as ss
from optimization.multi_period_sp import MultiPeriodStochasticLP
from optimization.service_frontier import solve_service_target, stock_service_frontier
from tests.unit.test_safe_selector import _fi


def problem():
    demand = pd.DataFrame([dict(scenario_index=0, scenario_weight=1., product_id="A",
                                period=t, demand_kg=100.) for t in range(4)])
    supply = pd.DataFrame([dict(supplier_id="S", product_id="A", capacity_kg=500., price_per_kg=5.)])
    model = MultiPeriodStochasticLP(n_periods=4, decay_rate_per_period=0.,
                                    holding_cost_per_kg_per_period=.05,
                                    spot_capacity_factor=0., waste_cost_per_kg=5.)
    return model, demand, supply


def test_pipeline_prevents_duplicate_procurement_and_is_not_haircut_twice():
    model, demand, supply = problem()
    old = model.solve(demand, supply, yield_scenarios={(0, "S"): .5})
    corrected = replace(model, pipeline_receipts={("A", t): 100. for t in range(4)})
    result = corrected.solve(demand, supply, yield_scenarios={(0, "S"): .5})
    assert sum(old["x"].values()) == pytest.approx(800.)
    assert sum(result["x"].values()) == pytest.approx(0.)
    assert result["expected_cost"] == pytest.approx(0.)


def test_late_pipeline_cannot_serve_early_demand():
    model, demand, supply = problem()
    result = replace(model, pipeline_receipts={("A", 3): 100.}).solve(demand, supply)
    assert sum(result["x"].values()) == pytest.approx(300.)
    assert result["x"][("S", "A", 0)] == pytest.approx(100.)


@pytest.mark.parametrize("quantity", [float("nan"), float("inf"), -1.])
def test_invalid_pipeline_refused(quantity):
    model, demand, supply = problem()
    with pytest.raises(ValueError, match="pipeline"):
        replace(model, pipeline_receipts={("A", 0): quantity}).solve(demand, supply)


def test_service_candidate_can_run_down_excess_without_new_stock():
    model, demand, supply = problem()
    r = solve_service_target(model, demand, supply, targets={"A": .97}, opening_inventory={"A": 500.})
    assert r["usable"] and sum(r["x"].values()) == pytest.approx(0.)
    assert r["shortage_cost_in_objective"] is False


def test_service_candidate_protects_low_stock_and_reports_infeasibility():
    model, demand, supply = problem()
    r = solve_service_target(model, demand, supply, targets={"A": .97})
    assert r["usable"] and sum(r["x"].values()) >= 388. - 1e-7
    supply["capacity_kg"] = 10.
    r = solve_service_target(model, demand, supply, targets={"A": .97})
    assert not r["usable"] and not r["x"]


def test_frontier_deterministic_and_keeps_failed_targets():
    model, demand, supply = problem()
    supply["capacity_kg"] = 98.
    a = stock_service_frontier(model, demand, supply, [.93, .97, .999])
    b = stock_service_frontier(model, demand, supply, [.93, .97, .999])
    assert a == b
    assert len(a) == 3 and not a[-1]["usable"]


def test_inner_fold_ignores_later_fill_and_lead_and_current_stock():
    fi = _fi()
    clean = ss.inner_folds(fi, 2, 4, offset=4)
    fi.train_fill["S"] = [0.01]
    fi.lead_of["S"] = 50
    fi.opening["A"] = 999999.
    fi.train_demand["A"][-1] = 999999.
    poisoned = ss.inner_folds(fi, 2, 4, offset=4)
    for (a, _, _), (b, _, _) in zip(clean, poisoned):
        assert a.train_fill == b.train_fill
        assert a.lead_of == b.lead_of
        assert a.opening == b.opening and a.pipeline == b.pipeline


def test_no_timestamped_supplier_history_abstains():
    fi = _fi()
    fi.supply_events = {}
    decision = ss.safe_select(fi, None, np.random.default_rng(0))
    assert decision.mode_run == ss.INCUMBENT


@pytest.mark.parametrize("field", ["min_rel_improvement", "service_tolerance", "max_regret_share"])
def test_nan_gate_thresholds_refused(field):
    with pytest.raises(ValueError):
        ss.SafeSelectionConfig(**{field: float("nan")})


@pytest.mark.parametrize("bad", ["service", "regret", "relaxation", "live_relaxation"])
def test_cost_winning_candidate_cannot_bypass_holdout_or_live_gates(monkeypatch, bad):
    from types import SimpleNamespace
    fi = _fi()
    cfg = ss.SafeSelectionConfig(n_boot=50, n_scen=2)

    def run(name, inner, cap, rng, n, extra=None):
        if name == ss.INCUMBENT:
            return {("S", "A", 0): 100.}, {"status": "heuristic"}
        m = {"status": "optimal", "usable": True}
        if ((bad == "relaxation" and inner.origin >= fi.origin - 8)
                or (bad == "live_relaxation" and inner.origin == fi.origin)):
            m["floor_relaxed"] = True
        return {("S", "A", 0): 90.}, m

    def settle(schedule, inner, truth, cap):
        incumbent = next(iter(schedule.values())) == 100.
        cost, fill = (100., .99) if incumbent else (70., .99)
        if not incumbent and inner.origin >= fi.origin - 8:
            if bad == "service":
                fill = .80
            if bad == "regret":
                cost = 120. if inner.origin == fi.origin - 4 else 1.
        return SimpleNamespace(total=cost, fill_rate=fill, inventory_periods=100.)

    monkeypatch.setattr(ss, "run_candidate", run)
    monkeypatch.setattr(ss, "settle", settle)
    d = ss.safe_select(fi, None, np.random.default_rng(0), cfg, candidates=("deterministic_sp",))
    assert d.mode_run == ss.INCUMBENT
    assert d.evidence["deterministic_sp"].passed  # selection succeeded; confirmation or live solve refused


def test_state_bypass_disabled_by_default():
    assert ss.SafeSelectionConfig().allow_state_evidence is False


def test_two_fold_confirmation_does_not_get_zero_width_confidence_interval():
    lower = ss._block_bootstrap_lower([-.1, .3], .8, 2, 1000, np.random.default_rng(11))
    assert lower < .1


def test_inner_events_are_rebased_to_the_inner_origin():
    fi = _fi()
    inner, _, meta = ss.inner_folds(fi, 1, 4)[0]
    for p, value in inner.supply_events["S"].items():
        assert p < 0
        assert value == fi.supply_events["S"][p + meta["start"]]


def test_period_service_floor_cannot_borrow_future_shortage_allowance():
    import pyomo.environ as pyo
    model, demand, supply = problem()
    result = solve_service_target(model, demand, supply, targets={"A": .97}, per_period=True)
    assert result["usable"]
    assert result["service_scope"] == "each_controllable_period"
    assert all(pyo.value(result["model"].u["A", t, 0]) <= 3. + 1e-7 for t in range(4))


def test_missing_heldout_fill_after_zero_training_does_not_turn_into_perfect_fill():
    fi = _fi()
    fi.supply_events = {"S": {t: (0., 1) for t in range(-52, -4)}}
    _, truth, _ = ss.inner_folds(fi, 1, 4)[0]
    assert set(truth.fill.values()) == {0.}


def test_open_po_planning_does_not_read_eventual_delivery_quantity_or_date():
    from scripts.run_commercial_remodel_audit import expected_pipeline
    po = dict(sku="A", placed=10, quantity=100., promised_lead=3, expected_fill=.8,
              actual_arrival=20, actual_fill=.2)
    assert expected_pipeline([po], 12) == {("A", 1): 80.}
    assert expected_pipeline([{**po, "actual_arrival": 99, "actual_fill": .99}], 12) == {("A", 1): 80.}


def test_supply_training_only_contains_received_shipments():
    from scripts.run_commercial_remodel_audit import Cell, history, inputs
    cell = Cell()
    demand, events = history(cell, 99)
    # A future receipt from a placed PO is not observed before this origin.
    events["S1"][59] = (.01, 20)
    fi = inputs(cell, demand, events, 60, 12)
    assert .01 not in fi.train_fill["S1"]


@pytest.mark.parametrize("carry", [0., float("nan"), float("inf")])
def test_service_right_sizing_requires_finite_positive_carry(carry):
    model, demand, supply = problem()
    with pytest.raises(ValueError, match="positive"):
        solve_service_target(replace(model, holding_cost_per_kg_per_period=carry), demand, supply, targets={"A": .97})
