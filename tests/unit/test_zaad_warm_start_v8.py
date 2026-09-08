"""P0-W: the highspy warm-start adapter. The seed is the incumbent's controls mapped by column
name and completed by the target formulation; an infeasible seed is rejected, never asserted; the
warm start changes the search only - solve states, physical validation, the FTL gap policy and the
candidate accounting are untouched."""
from __future__ import annotations

import numpy as np
import pytest

from zaad.full.model import Linear, Solution, warm_start_vector
from zaad.full.planner import candidate_outcome

pytest.importorskip("highspy")


def tiny():
    """min x + 2y + z  s.t. x + y >= 1.5, y + z >= 1, x,y,z integer in [0, 3]; optimum (2, 0, 1) = 3."""
    m = Linear()
    x = m.var(("purchase", "s1", 0), cost=1., upper=3, integer=True)
    y = m.var(("purchase", "s2", 0), cost=2., upper=3, integer=True)
    z = m.var(("transfer", "arc", 0, 0), cost=1., upper=3, integer=True)
    m.row({x: 1, y: 1}, lower=1.5)
    m.row({y: 1, z: 1}, lower=1.)
    return m


def test_highspy_and_scipy_agree_on_the_same_arrays():
    a, ra = tiny().solve(5., solver="highs")
    b, rb = tiny().solve(5., solver="highspy")
    assert a.status == 0 and b.status == 0
    assert abs(a.fun - b.fun) < 1e-9 and abs(a.fun - 3.) < 1e-9
    assert ra <= 1e-9 and rb <= 1e-9
    assert np.allclose(a.x, b.x)


def test_incumbent_controls_map_onto_columns_by_name():
    m = tiny()
    plan = Solution("OPTIMAL", {("s1", 0): 2., ("s2", 0): 0.}, {("arc", 0, 0): 1.}, {}, {}, None, [], 0., 3, 2, None, 0., [])
    telemetry, x0 = warm_start_vector(m, plan, 5.)
    assert telemetry["accepted"] and telemetry["controls_seeded"] == 3
    assert np.allclose(x0, [2., 0., 1.])


def test_partial_seed_is_completed_by_the_formulation():
    m = tiny()
    done = m.complete({0: 2.}, 5.)           # pin x only; y and z are derived
    assert done["accepted"]
    assert abs(done["x"][0] - 2.) < 1e-9 and done["x"][1] + done["x"][2] >= 1 - 1e-9


def test_invalid_seed_is_rejected_not_asserted():
    m = tiny()
    out_of_bounds = m.complete({0: 7.}, 5.)
    assert not out_of_bounds["accepted"] and "outside bounds" in out_of_bounds["reason"]
    infeasible = m.complete({0: 0., 1: 0.}, 5.)   # x + y >= 1.5 cannot hold
    assert not infeasible["accepted"] and "not feasible" in infeasible["reason"]
    plan = Solution("OPTIMAL", {("s1", 0): 7.}, {}, {}, {}, None, [], 0., 3, 2, None, 0., [])
    telemetry, x0 = warm_start_vector(m, plan, 5.)
    assert x0 is None and telemetry["accepted"] is False


def test_valid_seed_is_accepted_and_the_solver_may_improve_it():
    m = tiny()
    result, residual = m.solve(5., solver="highspy", seed=np.array([3., 0., 1.]))   # feasible, cost 4
    assert result.seed_status is not None and result.seed_accepted
    assert result.status == 0 and abs(result.fun - 3.) < 1e-9 and residual <= 1e-9    # improved to the optimum


def test_a_warm_started_plan_gets_no_special_acceptance():
    # usability is decided by status and physical validation, whatever the warm-start telemetry says
    seeded = Solution("FEASIBLE_TIME_LIMIT", {}, {}, {}, {}, None, [], 1., 1, 1, .5, 0., [], warm_start={"accepted": True, "outcome": "retained"})
    assert seeded.usable_plan
    rows = [{"world": "w0", "usable": False, "reason": "pack violation"}]
    comp = {"required": ["c"], "optional": [], "not_applicable": [], "omissions": [], "attempts": {}}
    assert candidate_outcome("c", {"c": seeded}, {"c": rows}, comp)[0] == "TIME_LIMIT_NO_USABLE_PLAN"
    starved = Solution("NO_FEASIBLE_SOLUTION", {}, {}, {}, {}, None, [], 1., 1, 1, None, None, [], warm_start={"accepted": True, "outcome": "no_incumbent_despite_seed"})
    assert not starved.usable_plan
    assert candidate_outcome("c", {"c": starved}, {}, comp)[0] == "NO_INCUMBENT"


def test_solve_state_mapping_from_highspy_statuses():
    m = Linear()
    x = m.var(("purchase", "s1", 0), cost=1., upper=1)
    m.row({x: 1}, lower=2.)                   # infeasible
    result, residual = m.solve(5., solver="highspy")
    assert result.status == 2 and result.x is None and residual == float("inf")
