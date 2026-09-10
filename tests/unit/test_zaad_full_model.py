from dataclasses import replace

import pytest

from zaad.full.demo import example
from zaad.full.model import solve
from zaad.full.settlement import PhysicalViolation, settle
from zaad.full.worlds import draw


@pytest.mark.parametrize("case", ["normal", "transfer", "substitution", "recovery", "cash", "understock"])
def test_network_ledger_and_conservation(case):
    req = example(case)
    world = draw(req, 123, 1, deterministic=True)
    result = solve(req, world)
    assert result.status == "OPTIMAL", result.warnings
    actual = settle(req, result, world[0])
    assert actual["conservation_residual"] == pytest.approx(0, abs=1e-6)
    assert actual["ledger_residual"] == 0
    assert actual["economic_cost"] == pytest.approx(result.projected_cost, abs=1e-4)


def test_true_continuous_and_capacity():
    req = example()
    result = solve(req, draw(req, 3, 1, deterministic=True))
    assert any(abs(q - round(q)) > .01 for q in result.purchases.values())
    assert all(q <= 100 for q in result.purchases.values())


def test_transfer_beats_disabled_on_identical_world():
    req = example("transfer")
    worlds = draw(req, 3, 1, deterministic=True)
    a, b = solve(req, worlds), solve(req, worlds, disabled=frozenset({"transfers"}))
    assert a.transfers
    assert settle(req, a, worlds[0])["economic_cost"] < settle(req, b, worlds[0])["economic_cost"]


def test_unapproved_substitution_and_cancel_cannot_run():
    req = example("recovery")
    worlds = draw(req, 3, 1, deterministic=True)
    result = solve(req, worlds)
    assert result.amendments["open", "cancel"] > 0
    invalid = replace(result, amendments={("open", "cancel"): 101})
    with pytest.raises(PhysicalViolation):
        settle(req, invalid, worlds[0])


def test_impossible_service_is_not_relaxed():
    req = example("understock")
    result = solve(req, draw(req, 3, 1, deterministic=True), service_floor=True)
    assert result.status == "INFEASIBLE"
    assert not result.purchases


def test_same_scenario_work_conserving_not_withholding():
    req = example("normal")
    world = draw(req, 3, 1, deterministic=True)[0]
    world = replace(world, demand={"retail_A": (50., 20., 20., 20., 20., 20.)})
    result = solve(req, [world])
    actual = settle(req, result, world)
    assert actual["service_by_period"][0]["served"] == 50
    assert actual["service"]["retail_A"] == pytest.approx(result.projected_service["retail_A"])
