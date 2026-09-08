"""P0-E: joint_recovery becomes REQUIRED only on a material projected service deficit (or thin cover
under an active supply driver), never on the driver alone; the default rule leaves V8 unchanged."""
from __future__ import annotations

from zaad.full.screen import MINIMUM_SAFE, screen


def _rows(activity=.75, drivers=("supply",), on_hand=100., mu=50.):
    return [{"sku": "A", "location": "dc", "on_hand_units": on_hand, "mean_demand_per_period": mu,
             "state": {"activity": activity, "regime": "PROTECT", "active_drivers": [{"driver": d, "score": 1., "reasons": []} for d in drivers],
                       "lean_baseline_units": 40.}}]


def _inc(value, target_service):
    return [{"usable": True, "service_by_period": [{"service": target_service, "period": 0, "demand": 100., "served": 100. * value}]}]


def _req(rule="v8", deficit=.2):
    class Service:  # minimal duck type of the request the screen reads
        def __init__(self): self.id, self.target = "retail_A", .95
    class Req:
        joint_recovery_rule = rule; joint_recovery_deficit = deficit; service_tolerance = .01
        services = [Service()]; transfers = []; stock = []
    return Req()


def test_default_rule_leaves_the_v8_protect_set_unchanged():
    out = screen(_req("v8"), {}, _rows(), _inc(.40, "retail_A"))
    assert out["state"] == "PROTECT"
    assert out["minimum_safe_candidates"] == list(MINIMUM_SAFE["PROTECT"])
    assert out["joint_recovery_required_by_rule"] is False
    assert abs(out["incumbent_service_deficit"] - .55) < 1e-9


def test_material_deficit_makes_joint_recovery_required():
    out = screen(_req("deficit"), {}, _rows(), _inc(.40, "retail_A"))
    assert "joint_recovery" in out["minimum_safe_candidates"] and "joint_recovery" not in out["optional_candidates"]
    assert out["joint_recovery_required_by_rule"] is True
    assert any("required" in r for r in out["reasons"])


def test_small_deficit_or_active_driver_alone_does_not():
    out = screen(_req("deficit"), {}, _rows(), _inc(.88, "retail_A"))   # deficit .07, supply driver active
    assert "joint_recovery" not in out["minimum_safe_candidates"]
    out = screen(_req("deficit_cover"), {}, _rows(on_hand=100., mu=50.), _inc(.88, "retail_A"))
    assert "joint_recovery" not in out["minimum_safe_candidates"]


def test_thin_cover_under_a_supply_driver_requires_it_only_in_the_cover_variant():
    thin = _rows(on_hand=10., mu=50.)
    assert "joint_recovery" not in screen(_req("deficit"), {}, thin, _inc(.9, "retail_A"))["minimum_safe_candidates"]
    assert "joint_recovery" in screen(_req("deficit_cover"), {}, thin, _inc(.9, "retail_A"))["minimum_safe_candidates"]
    # a demand-only driver with thin cover does not trigger the cover clause
    assert "joint_recovery" not in screen(_req("deficit_cover"), {}, _rows(drivers=("demand",), on_hand=10., mu=50.), _inc(.9, "retail_A"))["minimum_safe_candidates"]


def test_unknown_incumbent_outcome_means_no_deficit_claim():
    out = screen(_req("deficit"), {}, _rows(), None)
    assert out["incumbent_service_deficit"] == 0. and out["joint_recovery_required_by_rule"] is False
