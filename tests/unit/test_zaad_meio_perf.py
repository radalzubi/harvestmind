"""P2 performance pass: the exact FEFO symmetry elimination (`zaad.full.model.FEFO_SYMMETRY_ELIMINATION`).

Equivalence tests, not speed tests: with and without the elimination the same request must give the
same candidate objective, the same purchases and the same cohort-summed transfers; the rows are
dropped only between cohorts that outlive the window on a network request; a perishable cohort inside
the window keeps its FEFO rule; a single-node request builds the identical model column for column."""
from __future__ import annotations

from collections import Counter
from contextlib import contextmanager

import pytest

import zaad.full.model as model
from zaad.full.model import Linear, solve
from zaad.full.worlds import draw
from zaad.meio.fixtures_p2 import p2_request


@contextmanager
def elimination(enabled: bool):
    saved = model.FEFO_SYMMETRY_ELIMINATION
    model.FEFO_SYMMETRY_ELIMINATION = enabled
    try:
        yield
    finally:
        model.FEFO_SYMMETRY_ELIMINATION = saved


@contextmanager
def captured_columns(store: dict):
    """Record the column names of every model the frozen solve path builds."""
    original = Linear.solve

    def wrapped(self, *args, **kwargs):
        store["names"] = list(self.names)
        store["rows"] = len(self.rows)
        return original(self, *args, **kwargs)
    Linear.solve = wrapped
    try:
        yield
    finally:
        Linear.solve = original


def _solve(req, enabled: bool, worlds=None):
    store: dict = {}
    with elimination(enabled), captured_columns(store):
        sol = solve(req, worlds or draw(req, req.seed, 1, deterministic=True), service_floor=True)
    kinds = Counter(str(n[0]) for n in store["names"])
    return sol, kinds, store


def _summed_transfers(sol) -> dict:
    out: dict = {}
    for (arc, _expiry, t), q in sol.transfers.items():
        out[arc, t] = round(out.get((arc, t), 0.) + q, 6)
    return out


def test_network_request_drops_only_beyond_window_fefo_and_keeps_the_objective():
    req = p2_request(lane_lead_periods=2, seed=41001, scenarios=3)
    frozen, frozen_kinds, _ = _solve(req, False)
    fast, fast_kinds, _ = _solve(req, True)
    assert frozen_kinds["fefo"] > 0 and fast_kinds["fefo"] == 0, (frozen_kinds["fefo"], fast_kinds["fefo"])
    assert frozen_kinds["depleted"] == fast_kinds["depleted"] > 0
    assert frozen.status == fast.status == "OPTIMAL"
    assert fast.projected_cost == pytest.approx(frozen.projected_cost, rel=1e-7)
    assert {k: round(v, 6) for k, v in fast.purchases.items()} == {k: round(v, 6) for k, v in frozen.purchases.items()}
    assert _summed_transfers(fast) == _summed_transfers(frozen)
    assert fast.projected_service == pytest.approx(frozen.projected_service, abs=1e-9)


def test_network_request_on_scenario_worlds_keeps_the_objective():
    req = p2_request(lane_lead_periods=1, seed=41002, scenarios=3)
    worlds = draw(req, req.seed, 3)
    frozen, _, _ = _solve(req, False, worlds)
    fast, kinds, _ = _solve(req, True, worlds)
    assert kinds["fefo"] == 0
    assert fast.status == frozen.status == "OPTIMAL"
    assert fast.projected_cost == pytest.approx(frozen.projected_cost, rel=1e-7)
    assert {k: round(v, 6) for k, v in fast.purchases.items()} == {k: round(v, 6) for k, v in frozen.purchases.items()}


def test_perishable_cohort_inside_the_window_keeps_fefo():
    base = p2_request(lane_lead_periods=1, seed=41001, scenarios=3)
    fresh = base.stock[0]
    perishable = fresh.model_copy(update={"expires_in": 3, "quantity": 40., "age_periods": 49})
    req = base.model_copy(update={"stock": [*base.stock, perishable]})
    frozen, frozen_kinds, _ = _solve(req, False)
    fast, fast_kinds, _ = _solve(req, True)
    # the rows against the perishable cohort survive; the rows between long-lived cohorts do not
    assert 0 < fast_kinds["fefo"] < frozen_kinds["fefo"]
    assert fast.status == frozen.status
    if frozen.status == "OPTIMAL":
        assert fast.projected_cost == pytest.approx(frozen.projected_cost, rel=1e-7)
        assert {k: round(v, 6) for k, v in fast.purchases.items()} == {k: round(v, 6) for k, v in frozen.purchases.items()}


def test_single_node_request_builds_the_identical_model():
    req = p2_request(branches=("branch",), opening_central=0., opening_branch=150., extra={"_single_node": True}, seed=41001, scenarios=3)
    assert not req.transfers
    _, frozen_kinds, frozen_store = _solve(req, False)
    _, fast_kinds, fast_store = _solve(req, True)
    assert frozen_store["names"] == fast_store["names"]
    assert frozen_store["rows"] == fast_store["rows"]
    assert frozen_kinds == fast_kinds


def test_window_follows_the_longest_lane_arrival():
    """A cohort that expires after the horizon but before the longest lane can deliver still matters
    (its transfer is capped by the arrival-before-expiry rule), so its FEFO rows are kept."""
    base = p2_request(lane_lead_periods=4, seed=41001, scenarios=3)
    H = base.horizon
    borderline = base.stock[0].model_copy(update={"expires_in": H + 2, "quantity": 30., "age_periods": 1})
    req = base.model_copy(update={"stock": [*base.stock, borderline]})
    _, kinds, _ = _solve(req, True)
    assert kinds["fefo"] > 0
    far = base.stock[0].model_copy(update={"expires_in": H + 8, "quantity": 30., "age_periods": 1})
    _, kinds_far, _ = _solve(base.model_copy(update={"stock": [*base.stock, far]}), True)
    assert kinds_far["fefo"] == 0
