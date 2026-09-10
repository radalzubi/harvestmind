"""Common ex-ante valuation of fixed candidate plans (P1 candidate-comparability pass)."""
from __future__ import annotations

import copy
from statistics import mean

import numpy as np
import pytest

from zaad.full.fixtures_p1 import p1_request
from zaad.full.model import Solution
from zaad.full.planner import evaluate
from zaad.full.settlement import settle
from zaad.full.valuation import common_candidate_value, expected_inventory_path
from zaad.full.worlds import draw, forecast_all


def plan(p):
    return Solution("OPTIMAL", p, {}, {}, {}, None, [], 0., 0, 0, None, 0., [])


def test_propagation_matches_hand_calculation():
    # opening 10, arrivals 0, demand 5 or 15 with equal probability, two periods
    demand = [(np.array([5., 15.]), np.array([.5, .5]))] * 2
    e_short, e_inv, p_short = expected_inventory_path(10., np.zeros(2), demand)
    assert e_short[0] == pytest.approx(.5 * 5.)                    # short 5 with prob .5
    assert e_inv[0] == pytest.approx(.5 * 5.)                      # end 5 with prob .5, else 0
    # period 2: from 5 (p .5): short 0 or 10 -> 5; from 0 (p .5): short 5 or 15 -> 10
    assert e_short[1] == pytest.approx(.5 * 5. + .5 * 10.)
    assert p_short[1] == pytest.approx(.5 * .5 + .5 * 1.)


def test_deterministic_demand_reproduces_the_mean_path_settlement():
    req = p1_request(opening_units=150., demand=100., demand_sd_hint=1e-4)
    fits = forecast_all(req)
    sol = plan({("src_A", t): 100. for t in range(0, 11)})
    v = common_candidate_value(req, sol, fits)
    assert v["total"] == pytest.approx(v["mean_path_total"], abs=2.)       # unit-grid rounding only


def test_common_value_agrees_with_a_broad_expectation_and_ranks_like_it():
    req = p1_request(opening_units=100., demand=100.)
    fits = forecast_all(req)
    worlds = draw(req, 991, 300)
    lean = plan({("src_A", t): 100. for t in range(11)})
    protected = plan({("src_A", 0): 112., **{("src_A", t): 100. for t in range(1, 11)}})
    values, sampled = {}, {}
    for name, sol in (("lean", lean), ("protected", protected)):
        values[name] = common_candidate_value(req, sol, fits)["total"]
        sampled[name] = mean(r["economic_cost"] for r in evaluate(req, sol, worlds))
        assert abs(values[name] - sampled[name]) < .01 * sampled[name]
    assert (values["lean"] > values["protected"]) == (sampled["lean"] > sampled["protected"])


def test_expected_shortage_falls_with_added_units_and_zero_when_stock_is_ample():
    req = p1_request(opening_units=100., demand=100.)
    fits = forecast_all(req)
    base = plan({("src_A", t): 100. for t in range(11)})
    more = plan({("src_A", 0): 115., **{("src_A", t): 100. for t in range(1, 11)}})
    a, b = common_candidate_value(req, base, fits), common_candidate_value(req, more, fits)
    assert b["components"]["expected_shortage_units"] < a["components"]["expected_shortage_units"]
    ample = common_candidate_value(p1_request(opening_units=3000., demand=100.), plan({}), forecast_all(p1_request(opening_units=3000., demand=100.)))
    assert ample["components"]["expected_shortage_units"] < 1e-6


def test_valuation_mutates_nothing():
    req = p1_request(opening_units=100., demand=100.)
    fits = forecast_all(req)
    sol = plan({("src_A", t): 100. for t in range(11)})
    before = copy.deepcopy(sol)
    world = draw(req, req.seed, 1, deterministic=True)[0]
    ledger_before = dict(settle(req, sol, world)["ledger"])
    common_candidate_value(req, sol, fits)
    assert sol.purchases == before.purchases and sol.amendments == before.amendments and sol.transfers == before.transfers
    assert settle(req, sol, world)["ledger"] == ledger_before


def test_components_reconcile_to_the_total():
    req = p1_request(opening_units=100., demand=100.)
    v = common_candidate_value(req, plan({("src_A", t): 100. for t in range(11)}), forecast_all(req))
    c = v["components"]
    rebuilt = (c["purchase"] + c["freight"] + c["ordering"] + c["receiving"] + c["financing"] + c["expected_carrying"] + c["expected_shortage_cost"]
               + c["terminal_on_hand_credit"] + c["terminal_in_transit_credit"] + c["opening_assets"] + c["other"])
    assert rebuilt == pytest.approx(v["total"], abs=1e-6)
