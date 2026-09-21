"""Diagnostic V3.1 — the certified symmetry reduction (`fefo_symmetry_scope="certified"`).

The reduced formulation (the released P2 window rule applied to a single-location request) is an exact
projection of the released one; the solver's search path is not, so on an objective-flat tie it may return
another optimal solution. The certified path accepts the reduced solution only under the tie certificate
and otherwise solves the released formulation exactly as the default does. These tests pin:

1. the executed decisions of the certified path equal the released path's on the demo requests;
2. an objective-flat tie (two identical sources for one SKU) is detected: the certificate is refused and
   the released formulation decides, so the certified result equals the released result;
3. a fixed, service-only or recourse solve never takes the reduced path;
4. the certificate's telemetry is on the solution, and the default scope is untouched.
"""
from __future__ import annotations

import pytest

from zaad.full.contracts import Request
from zaad.full.demo import example
from zaad.full.model import solve
from zaad.full.worlds import draw


def _decisions(solution):
    return (solution.status, {k: round(v, 6) for k, v in solution.purchases.items()},
            {k: round(v, 6) for k, v in solution.transfers.items()}, {k: round(v, 6) for k, v in solution.amendments.items()})


@pytest.mark.parametrize("case", ["normal", "understock"])
def test_certified_path_returns_the_released_decisions(case):
    req = example(case)
    assert not req.transfers
    worlds = draw(req, 11, 2)
    released = solve(req, worlds, service_floor=True)
    certified = solve(req.model_copy(update={"fefo_symmetry_scope": "certified"}), worlds, service_floor=True)
    assert certified.symmetry_certificate is not None and certified.symmetry_certificate["attempted"]
    if certified.symmetry_certificate["certified"]:
        # a certified solution is the reduced model's: fewer integer columns, the same decisions
        assert certified.binaries is not None and released.binaries is not None and certified.binaries <= released.binaries
        assert certified.projected_cost == pytest.approx(released.projected_cost, rel=2e-6)
    else:
        # not certified: the released formulation decided, exactly as the default path
        assert certified.symmetry_certificate["fallback"] is True
        assert certified.variables == released.variables and certified.constraints == released.constraints
    assert _decisions(certified) == _decisions(released)


def test_an_objective_flat_tie_falls_back_to_the_released_formulation():
    """Two sources of one SKU with identical economics: any split of the order between them is optimal, so the
    certificate must find an alternative and refuse; the released formulation then decides."""
    base = example("normal")
    data = base.model_dump(mode="python")
    twin = dict(next(s for s in data["sources"]))
    twin["id"] = twin["id"] + "_twin"
    data["sources"] = list(data["sources"]) + [twin]
    req = Request.model_validate(data)
    worlds = draw(req, 5, 1, deterministic=True)
    released = solve(req, worlds, service_floor=True)
    certified = solve(req.model_copy(update={"fefo_symmetry_scope": "certified", "tie_certificate_cutoff": "strict"}), worlds, service_floor=True)
    cert = certified.symmetry_certificate
    assert cert is not None and cert["attempted"]
    if released.usable_plan and sum(released.purchases.values()) > 0:
        assert cert["certified"] is False and cert["fallback"] is True, cert
        assert cert["max_deviation_dust_units"] is not None and cert["max_deviation_dust_units"] >= 1.
    assert _decisions(certified) == _decisions(released)


def test_fixed_service_only_and_recourse_solves_keep_the_released_formulation():
    req = example("normal").model_copy(update={"fefo_symmetry_scope": "certified"})
    worlds = draw(req, 3, 1, deterministic=True)
    released = solve(req.model_copy(update={"fefo_symmetry_scope": "network"}), worlds, service_floor=True)
    pinned = solve(req, worlds, fixed=released)
    assert pinned.symmetry_certificate is None and pinned.variables == solve(req.model_copy(update={"fefo_symmetry_scope": "network"}), worlds, fixed=released).variables
    service = req.services[0].id
    oracle = solve(req, worlds, service_first=service, service_only=True)
    frozen_oracle = solve(req.model_copy(update={"fefo_symmetry_scope": "network"}), worlds, service_first=service, service_only=True)
    assert oracle.symmetry_certificate is None and oracle.variables == frozen_oracle.variables
    assert oracle.projected_service[service] == pytest.approx(frozen_oracle.projected_service[service], abs=1e-9)


def test_default_scope_and_telemetry_shape():
    assert Request.model_fields["fefo_symmetry_scope"].default == "network"
    assert Request.model_fields["tie_certificate_cutoff"].default == "tolerance"
    req = example("normal").model_copy(update={"fefo_symmetry_scope": "certified"})
    out = solve(req, draw(req, 7, 1, deterministic=True), service_floor=True)
    cert = out.symmetry_certificate
    assert cert is not None
    for key in ("attempted", "cutoff", "controls", "certified", "fallback", "reason", "certificate_seconds"):
        assert key in cert
    assert cert["cutoff"] == "tolerance"
