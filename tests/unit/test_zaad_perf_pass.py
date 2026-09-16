"""Performance pass (2026-09-16): the two planner changes and what they must preserve.

1. `fefo_symmetry_scope`: the default ("network") leaves a single-location request's formulation
   exactly as released; "all" omits the FEFO indicators between cohorts that outlive the horizon
   (the released P2 rule) on a single-location, physics-free request too - the phase-one service
   optimum and the cost optimum are unchanged, only the integer column count falls.
2. `service_only`: a service-first solve may stop after phase one; the projected service of the
   service it optimises is the same number the two-phase oracle reports (phase two is constrained
   to that optimum), so the per-service frontier reads one solve instead of two.
"""
from __future__ import annotations

import pytest

from zaad.full.demo import example
from zaad.full.model import solve
from zaad.full.worlds import draw


def _single_location(case: str = "normal"):
    req = example(case)
    assert not req.transfers, "the fixture must be single-location for this test"
    return req


def test_default_scope_is_the_released_formulation():
    req = _single_location()
    assert req.fefo_symmetry_scope == "network"
    worlds = draw(req, 11, 2)
    released = solve(req, worlds, service_first="all")
    again = solve(req.model_copy(update={"fefo_symmetry_scope": "network"}), worlds, service_first="all")
    assert (released.variables, released.constraints, released.binaries) == (again.variables, again.constraints, again.binaries)
    assert released.projected_service == again.projected_service
    assert released.projected_cost == pytest.approx(again.projected_cost, rel=1e-9)


def test_all_scope_keeps_the_optimum_and_drops_symmetric_indicators():
    req = _single_location()
    worlds = draw(req, 11, 2)
    released = solve(req, worlds, service_first="all")
    reduced = solve(req.model_copy(update={"fefo_symmetry_scope": "all"}), worlds, service_first="all")
    assert released.status == reduced.status == "OPTIMAL"
    # the lexicographic service optimum is exact and identical; the cost optimum agrees within the
    # solver's own relative gap (1e-6); the formulation carries fewer integer columns
    for service_id, value in released.projected_service.items():
        assert reduced.projected_service[service_id] == pytest.approx(value, abs=1e-9)
    assert reduced.projected_cost == pytest.approx(released.projected_cost, rel=2e-6)
    assert reduced.binaries is not None and released.binaries is not None
    assert reduced.binaries <= released.binaries
    assert reduced.variables < released.variables


def test_service_only_reports_the_phase_one_optimum():
    req = _single_location("understock")
    worlds = draw(req, 3, 1, deterministic=True)
    service = req.services[0].id
    two_phase = solve(req, worlds, service_first=service)
    one_phase = solve(req, worlds, service_first=service, service_only=True)
    assert two_phase.status == one_phase.status == "OPTIMAL"
    assert one_phase.projected_service[service] == pytest.approx(two_phase.projected_service[service], abs=1e-7)
    # a phase-one solution is a proven, physically usable plan of the same formulation
    assert one_phase.usable_plan and one_phase.warnings == []
    assert one_phase.variables == two_phase.variables
