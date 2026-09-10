"""Two-blocker closure, part T: protection provenance and the stress-gate basis on purchasing reviews
(`P1_TWO_BLOCKER_PREREGISTRATION.md`, rules T-A and T-B)."""
from __future__ import annotations

import pytest

from scripts.p1_fixtures import build
from zaad.full.contracts import Request, Stress
from zaad.full.evaluation import long_truth
from zaad.full.ownership import PROTECTION_RECOVERY, PURCHASING_ECONOMICS, planner_owner
from zaad.full.planner import plan, protection_profile, supply_profiles
from zaad.full.replay import replay
from zaad.full.worlds import forecast_all

PRODUCT = {k: Request.model_fields[k].default for k in ("stratified_scenarios", "timing_tiebreak", "analytic_shortage")}
CALM = {"state": "NO_ACTION", "joint_recovery_required_by_rule": False, "incumbent_service_deficit": 0.}


def _row(**state):
    base = {"activity": 0., "risk_active": False, "decaying": False, "regime": "LEAN", "demand_decline_confirmed": False, "flags": []}
    return {"sku": "A", "location": "branch", "state": {**base, **state}}


def _req():
    return build("T_combined_realistic", 41003).model_copy(update=PRODUCT)


def test_1_economic_cycle_lot_does_not_create_protection_ownership():
    """The flag alone (protection recommendation above the lean baseline, no driver) leaves the review
    with the purchasing planner; the flag is still reported as a note."""
    out = planner_owner(_req(), [_row(flags=["FALSE_PROTECTION_RISK"])], CALM)
    assert out["owner"] == PURCHASING_ECONOMICS
    assert any("FALSE_PROTECTION_RISK" in n for n in out["notes"])
    assert not any("FALSE_PROTECTION_RISK" in r for r in out["reasons"])


def test_2_true_protection_still_routes_to_p0():
    for state in ({"activity": .5, "risk_active": True, "regime": "PROTECT"}, {"activity": .2, "decaying": True, "regime": "RECOVER", "flags": ["RECOVERY_IN_PROGRESS"]},
                  {"demand_decline_confirmed": True}, {"regime": "RECOVER"}):
        out = planner_owner(_req(), [_row(**state)], CALM)
        assert out["owner"] == PROTECTION_RECOVERY, state


def test_3_protection_accounting_is_bounded_on_the_fixture_family():
    """No new provenance state is built (pre-registration T2): the canonical protection state must
    already be bounded. Incremental protection is never negative and the echelon partition never
    exceeds the recommended protection, on every fixture's first review."""
    from scripts.p1_fixtures import FIXTURES
    for name in FIXTURES:
        req = build(name, 41001).model_copy(update=PRODUCT)
        for row in protection_profile(req, forecast_all(req), supply_profiles(req)):
            st = row["state"]
            assert st["incremental_protection_units"] >= -1e-9
            assert sum(v for k, v in st["echelon"].items() if k != "scope") <= row["protection_units"] + 1e-6


def test_4_flag_is_deterministic_from_the_snapshot():
    req = _req()
    a = protection_profile(req, forecast_all(req), supply_profiles(req))
    b = protection_profile(req, forecast_all(req), supply_profiles(req))
    assert [r["state"]["flags"] for r in a] == [r["state"]["flags"] for r in b]


def test_5_p1_owned_review_keeps_the_request_gate_basis():
    """Rule T-B (target basis on every P1-owned review) was rejected: it created a valid failure on A
    (interventions on 36% of reviews against a "mostly abstain" expectation) and a legacy service miss
    on Q. A P1-owned review therefore keeps the request's own basis; the report states it."""
    rep = plan(_req())
    assert rep["orchestration"]["planner_owner"] == PURCHASING_ECONOMICS
    assert rep["orchestration"]["gate_basis"] == "incumbent"
    opted = plan(_req().model_copy(update={"service_gate_basis": "target"}))
    assert opted["orchestration"]["gate_basis"] == "target"


def test_6_p0_owned_review_keeps_the_incumbent_floor():
    severe = build("T_combined_realistic", 41003, stresses="severe").model_copy(update=PRODUCT)
    rep = plan(severe)
    assert rep["orchestration"]["planner_owner"] == PROTECTION_RECOVERY
    assert rep["orchestration"]["gate_basis"] == "incumbent"


def test_7_a_credible_declared_stress_keeps_p0_ownership_and_its_floor():
    req = _req().model_copy(update={"stresses": (Stress(name="late", fill_multiplier=1., extra_lead_days=7, demand_multiplier=1., recovery_period=12, shared_failure=True),)})
    rep = plan(req)
    assert rep["orchestration"]["planner_owner"] == PROTECTION_RECOVERY
    assert rep["orchestration"]["gate_basis"] == "incumbent"


def test_8_routing_and_basis_use_the_snapshot_only():
    """Ownership and the gate basis are pure functions of the review snapshot: the same request gives
    the same owner and basis twice, and a request that opts into the target basis on a P0-owned
    non-lean review still gets the incumbent basis (no leakage through the option)."""
    req = _req()
    a, b = plan(req), plan(req)
    assert (a["orchestration"]["planner_owner"], a["orchestration"]["gate_basis"]) == (b["orchestration"]["planner_owner"], b["orchestration"]["gate_basis"])
    severe = build("T_combined_realistic", 41003, stresses="severe").model_copy(update={**PRODUCT, "service_gate_basis": "target"})
    rep = plan(severe)
    assert rep["orchestration"]["planner_owner"] == PROTECTION_RECOVERY
    # the request's own rule, untouched by ownership: target only when opted in AND the review is lean
    lean = rep["orchestration"]["state"] in ("NO_ACTION", "NORMAL_REPLENISHMENT", "CAPITAL_OPTIMIZATION") and all(float(p["state"]["activity"]) <= .05 for p in rep["protection"])
    assert rep["orchestration"]["gate_basis"] == ("target" if lean else "incumbent")
