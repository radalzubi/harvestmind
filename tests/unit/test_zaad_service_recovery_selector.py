from zaad.full.demo import example
from zaad.full.planner import _recovery_not_worse, plan, weighted_shortfall


def _row(service: float, cost: float = 100.0) -> dict:
    return {
        "usable": True,
        "economic_cost": cost,
        "service": {"retail_A": service},
        "service_by_period": [
            {"service": "retail_A", "demand": 100.0, "served": service * 100.0}
        ],
        "order_metrics": {"retail_A": {}},
    }


def test_weighted_shortfall_prefers_better_recovery_below_absolute_target():
    req = example("understock")
    incumbent = [_row(0.81)]
    recovery = [_row(0.92, 102.0)]
    assert weighted_shortfall(req, recovery) < weighted_shortfall(req, incumbent)
    assert _recovery_not_worse(req, incumbent, recovery)


def test_recovery_must_strictly_improve_shortfall():
    req = example("understock")
    incumbent = [_row(0.81)]
    worse = [_row(0.80, 90.0)]
    tied = [_row(0.81, 90.0)]
    assert not _recovery_not_worse(req, incumbent, worse)
    assert not _recovery_not_worse(req, incumbent, tied)


def test_understock_report_exposes_joint_feasibility_and_allocate_mode():
    report = plan(example("understock", seed=13001))
    assert "joint_service_feasibility" in report
    joint = report["joint_service_feasibility"]
    assert isinstance(joint["target_vector_feasible"], bool)
    if not joint["target_vector_feasible"]:
        assert report["mode"] == "ALLOCATE"
        assert joint["recovery_weighted_shortfall"] is not None
