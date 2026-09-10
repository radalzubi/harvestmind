"""P1 planner-boundary pass: planner ownership is decided before candidate assembly, from semantic
state only; a P0-owned review runs the frozen path bit-identically; a P1-owned review gets the
purchasing frontier (the scenario plan at NO_ACTION) with the existing candidate mathematics."""
from __future__ import annotations

import sys

import pytest

import zaad.full.planner as P
import zaad.full.screen as S
from zaad.full.contracts import Request, Stress
from zaad.full.ownership import (PROTECTION_RECOVERY, PURCHASING_ECONOMICS, is_protection_mandate, planner_owner,
                                 purchasing_candidates)
from zaad.full.planner import plan
from zaad.full.replay import replay
from zaad.full.worlds import draw
from scripts.p1_fixtures import build

sys.path.insert(0, "scripts")
import run_zaad_full_benchmark as B  # noqa: E402

PRODUCT = {k: Request.model_fields[k].default for k in ("stratified_scenarios", "timing_tiebreak", "analytic_shortage")}
NIL = Stress(name="nil", fill_multiplier=1., extra_lead_days=0, demand_multiplier=1., recovery_period=12, shared_failure=True)


def _traced(req):
    P.TRACE = {}
    try:
        rep = plan(req)
        t = dict(P.TRACE)
    finally:
        P.TRACE = None
    return rep, t


def _screened(req):
    """The planner's own risk rows and screen result for a request (the screen needs the incumbent's
    projected outcome to claim NO_ACTION, which only the planner computes)."""
    rep = plan(req)
    return rep["protection"], rep["orchestration"]


@pytest.fixture(scope="module")
def p_requests():
    """Fixture P (nil stress, six weeks of stock) review snapshots at product defaults: review 0 is
    CAPITAL_OPTIMIZATION, review 4 is NO_ACTION (the decisive calm review of pass G / H)."""
    req = build("P_high_opening_stock", 41001).model_copy(update=PRODUCT)
    truth = draw(req, 41001 + 10000, 1)[0]
    kept: list = []
    replay(req, truth, 5, "gated", keep_requests=kept)
    return kept


@pytest.fixture(scope="module")
def cell20():
    cell = next(c for c in B.cells("v7") if c["cell"] == 20)
    return B.request_for(cell, 38001).model_copy(update={"adaptive_escalation": True, "adaptive_solve_budget": True, "joint_recovery_rule": "deficit"})


def _rows(regime="LEAN", activity=0., flags=(), decaying=False, decline=False):
    return [{"sku": "A", "location": "branch", "state": {"regime": regime, "activity": activity, "risk_active": activity > .05,
                                                          "flags": list(flags), "decaying": decaying, "demand_decline_confirmed": decline}}]


def _screen(state="NO_ACTION", joint=False, deficit=0.):
    return {"state": state, "joint_recovery_required_by_rule": joint, "incumbent_service_deficit": deficit}


def test_1_calm_explicit_purchasing_economics_is_p1(p_requests):
    req = build("C_moq_four_weeks", 41001).model_copy(update=PRODUCT)       # 400-unit MOQ: explicit lot economics
    prot, scr = _screened(req)
    assert scr["state"] in ("NO_ACTION", "NORMAL_REPLENISHMENT", "CAPITAL_OPTIMIZATION")
    assert planner_owner(req, prot, scr)["owner"] == PURCHASING_ECONOMICS


def test_2_active_credible_disruption_is_p0(p_requests):
    req = p_requests[4]
    assert planner_owner(req, _rows(regime="PROTECT", activity=.6), _screen("PROTECT"))["owner"] == PROTECTION_RECOVERY
    # the same review with a calm screen but an active driver on a location is still P0
    assert planner_owner(req, _rows(activity=.3), _screen("NO_ACTION"))["owner"] == PROTECTION_RECOVERY


def test_3_recovery_deficit_is_p0(p_requests):
    req = p_requests[4]
    assert planner_owner(req, _rows(), _screen("NO_ACTION", deficit=.12))["owner"] == PROTECTION_RECOVERY
    assert planner_owner(req, _rows(), _screen("NO_ACTION", joint=True))["owner"] == PROTECTION_RECOVERY


def test_4_inherited_protection_unwind_is_p0(p_requests):
    req = p_requests[4]
    assert planner_owner(req, _rows(regime="RECOVER", activity=0.), _screen("RECOVER"))["owner"] == PROTECTION_RECOVERY
    assert planner_owner(req, _rows(regime="LEAN", activity=0., decaying=True), _screen("NO_ACTION"))["owner"] == PROTECTION_RECOVERY


def test_5_false_protection_risk_alone_is_not_p0(p_requests):
    """Rule T-A of the two-blocker closure supersedes the pass-I rule: the flag reads no inventory (it
    is the protection recommendation against the lean baseline, on T the forecast's calibration
    widening), so alone it is a note, not an ownership reason; with any real driver P0 owns."""
    req = p_requests[4]
    out = planner_owner(req, _rows(flags=("FALSE_PROTECTION_RISK",)), _screen("NO_ACTION"))
    assert out["owner"] == PURCHASING_ECONOMICS and any("FALSE_PROTECTION_RISK" in n for n in out["notes"])
    assert planner_owner(req, _rows(flags=("FALSE_PROTECTION_RISK",), activity=.3), _screen("NO_ACTION"))["owner"] == PROTECTION_RECOVERY


def test_6_ordinary_calm_cycle_inventory_is_p1(p_requests):
    req = p_requests[4]
    prot, scr = _screened(req)
    assert scr["state"] == "NO_ACTION"
    out = planner_owner(req, prot, scr)
    assert out["owner"] == PURCHASING_ECONOMICS
    assert planner_owner(req, _rows(), _screen("NORMAL_REPLENISHMENT"))["owner"] == PURCHASING_ECONOMICS
    assert planner_owner(req, _rows(), _screen("CAPITAL_OPTIMIZATION"))["owner"] == PURCHASING_ECONOMICS


def test_7_legacy_full_set_path_stays_p0(p_requests):
    req = p_requests[4].model_copy(update={"adaptive_escalation": False})
    assert planner_owner(req, _rows(), _screen("ESCALATE_UNKNOWN"))["owner"] == PROTECTION_RECOVERY
    rep = plan(req)
    assert rep["orchestration"]["planner_owner"] == PROTECTION_RECOVERY and rep["orchestration"]["p1_classes_added"] == []


def test_8_declared_protection_mandate_available_now_is_p0(cell20):
    """The P0 cells declare `operator_adverse` in the request at review 0: an operator input, not
    fixture truth. On risk state alone review 0 is calm; the declared mandate decides."""
    prot, scr = _screened(cell20)
    assert scr["state"] == "NO_ACTION" and all(not r["state"]["risk_active"] for r in prot)
    out = planner_owner(cell20, prot, scr)
    assert out["owner"] == PROTECTION_RECOVERY and any("mandate" in r for r in out["reasons"])
    assert is_protection_mandate(cell20.stresses[0]) and not is_protection_mandate(NIL)


def test_9_future_truth_cannot_influence_the_router(cell20):
    """The router reads the request, the risk rows and the screen: the same cell-20 request with the
    identity envelope declared routes to P1 at review 0, and nothing about the seed or the truth
    changes the owner."""
    prot, scr = _screened(cell20)
    nil_req = cell20.model_copy(update={"stresses": (NIL,)})
    assert planner_owner(nil_req, prot, scr)["owner"] == PURCHASING_ECONOMICS
    for seed in (1, 38001, 99999):
        assert planner_owner(cell20.model_copy(update={"seed": seed}), prot, scr)["owner"] == PROTECTION_RECOVERY
        assert planner_owner(nil_req.model_copy(update={"seed": seed}), prot, scr)["owner"] == PURCHASING_ECONOMICS
    assert planner_owner(cell20, prot, scr) == planner_owner(cell20, prot, scr)


def test_10_p1_candidate_cannot_alter_a_p0_owned_review(cell20):
    """Cell 20 review 0 under the router is bit-identical to the frozen path: same requested set,
    same built set, same candidates' plans, same band inputs, same choice, same materiality."""
    rep_r, t_r = _traced(cell20)
    rep_f, t_f = _traced(cell20.model_copy(update={"planner_ownership": False}))
    assert rep_r["orchestration"]["planner_owner"] == PROTECTION_RECOVERY
    assert rep_r["orchestration"]["p1_classes_added"] == []
    for key in ("candidate_classes_requested", "candidates_built", "classification"):
        assert rep_r["orchestration"][key] == rep_f["orchestration"][key]
    assert set(t_r["candidates"]) == set(t_f["candidates"]) == {"incumbent", "base_stock", "deterministic_network"}
    for name in t_r["candidates"]:
        assert t_r["candidates"][name]["purchases"] == t_f["candidates"][name]["purchases"]
        assert t_r["candidates"][name]["hedged_cost"] == t_f["candidates"][name]["hedged_cost"]
        assert t_r["candidates"][name]["exposure"] == t_f["candidates"][name]["exposure"]
    assert (t_r["feasible"], t_r["chosen"], t_r["status"], t_r["final_p0_purchases"]) == (t_f["feasible"], t_f["chosen"], t_f["status"], t_f["final_p0_purchases"])
    assert rep_r["economics"]["materiality"] == rep_f["economics"]["materiality"]
    assert rep_r["actions"] == rep_f["actions"] and rep_r["status"] == rep_f["status"]


def test_11_p0_ownership_generates_no_p1_side_effect(p_requests, cell20):
    """On every P0-owned review the router adds nothing and the solve count is the frozen one."""
    rep = plan(cell20)
    assert rep["orchestration"]["planner_owner"] == PROTECTION_RECOVERY
    assert rep["orchestration"]["p1_classes_added"] == []
    assert rep["orchestration"]["milps_attempted"] == plan(cell20.model_copy(update={"planner_ownership": False}))["orchestration"]["milps_attempted"]
    # a P1 fixture review forced to P0 by a declared mandate: no scenario plan at NO_ACTION
    forced = p_requests[4].model_copy(update={"stresses": (Stress(name="late", fill_multiplier=1., extra_lead_days=7, demand_multiplier=1., recovery_period=12, shared_failure=True),)})
    rep_f = plan(forced)
    assert rep_f["orchestration"]["planner_owner"] == PROTECTION_RECOVERY
    assert rep_f["orchestration"]["p1_classes_added"] == []
    assert "stochastic_network" not in rep_f["orchestration"]["candidates_built"] or rep_f["orchestration"]["state"] != "NO_ACTION"


def test_12_p1_candidates_are_bit_identical_to_the_existing_forced_classes(p_requests):
    """At a P1-owned NO_ACTION review the scenario plan the router requests is the existing class,
    identical to the screen requesting it, and the mean-world plan is unchanged. Routing identity is
    tested with the lot-sizing terminal valuation off on both sides: that valuation is the declared
    P1 change of the benchmark / horizon closure pass (`test_zaad_lotsizing`), not part of routing."""
    req = p_requests[4].model_copy(update={"lot_terminal_valuation": False})
    rep, t = _traced(req)
    assert rep["orchestration"]["planner_owner"] == PURCHASING_ECONOMICS
    assert rep["orchestration"]["state"] == "NO_ACTION"
    assert rep["orchestration"]["p1_classes_added"] == ["stochastic_network"]
    assert "stochastic_network" in rep["orchestration"]["candidate_classes_requested"]      # the report reflects the actual set
    assert rep["orchestration"]["classification"]["stochastic_network"] == "REQUIRED"
    saved = dict(S.MINIMUM_SAFE)
    try:
        S.MINIMUM_SAFE["NO_ACTION"] = ("deterministic_network", "stochastic_network")
        rep_ref, t_ref = _traced(req.model_copy(update={"planner_ownership": False}))
    finally:
        S.MINIMUM_SAFE.clear()
        S.MINIMUM_SAFE.update(saved)
    for name in ("deterministic_network", "stochastic_network", "incumbent", "base_stock"):
        assert t["candidates"][name]["status"] == t_ref["candidates"][name]["status"]
        assert t["candidates"][name]["purchases"] == t_ref["candidates"][name]["purchases"]
        assert t["candidates"][name]["cost_by_world"] == t_ref["candidates"][name]["cost_by_world"]
    assert t["worlds"] == t_ref["worlds"]
    assert (t["chosen"], t["status"], t["final_p0_purchases"]) == (t_ref["chosen"], t_ref["status"], t_ref["final_p0_purchases"])
    # routing off reproduces the frozen NO_ACTION set
    rep_off = plan(req.model_copy(update={"planner_ownership": False}))
    assert rep_off["orchestration"]["candidate_classes_requested"] == ["deterministic_network"]


def test_purchasing_frontier_only_touches_no_action():
    assert purchasing_candidates("NO_ACTION", ["deterministic_network"], []) == (["deterministic_network", "stochastic_network"], [], ["stochastic_network"])
    assert purchasing_candidates("NORMAL_REPLENISHMENT", ["deterministic_network", "stochastic_network"], ["cvar_network"]) == (["deterministic_network", "stochastic_network"], ["cvar_network"], [])
    assert purchasing_candidates("CAPITAL_OPTIMIZATION", ["deterministic_network", "stochastic_network", "cvar_network"], ["protected_network", "joint_recovery"])[2] == []
    assert purchasing_candidates("NO_ACTION", ["deterministic_network", "stochastic_network"], [])[2] == []


def test_router_output_is_pure_and_explains_itself(p_requests):
    req = p_requests[4]
    out = planner_owner(req, _rows(), _screen("NO_ACTION"))
    assert out["owner"] == PURCHASING_ECONOMICS and out["reasons"] and out["scope"]
    out2 = planner_owner(req, _rows(regime="PROTECT", activity=.4, flags=("FALSE_PROTECTION_RISK",)), _screen("PROTECT", joint=True, deficit=.2))
    assert out2["owner"] == PROTECTION_RECOVERY and len(out2["reasons"]) >= 4
