"""P0-B corrected accounting: every candidate class is REQUIRED, OPTIONAL or NOT_APPLICABLE and
carries one outcome; only genuine solver failures on required classes count as starvation."""
from __future__ import annotations

from zaad.full.model import Solution
from zaad.full.planner import STARVED_OUTCOMES, _completeness, candidate_outcome


def sol(status: str) -> Solution:
    return Solution(status, {}, {}, {}, {}, None, [], 0.1, 1, 1, None, None, [])


def rows(usable: bool, reason: str = "inventory conservation residual 3.0"):
    return [{"world": "w0", "usable": True}, {"world": "w1", "usable": usable, **({} if usable else {"reason": reason})}]


def compute(required, optional, not_applicable=(), attempts=None):
    omissions = [{"candidate": n, "outcome": "not_applicable", "reason": "no credible stress"} for n in not_applicable]
    return {"required": list(required), "optional": list(optional), "not_applicable": list(not_applicable),
            "omissions": omissions, "attempts": attempts or {}, "skipped": [], "requested": list(required) + list(optional)}


def test_outcomes_cover_every_way_a_candidate_can_end():
    cands = {"a": sol("OPTIMAL"), "b": sol("FEASIBLE_TIME_LIMIT"), "c": sol("FEASIBLE_TIME_LIMIT"), "d": sol("INFEASIBLE"),
             "e": sol("NO_FEASIBLE_SOLUTION"), "f": sol("ERROR"), "g": sol("OPTIMAL")}
    sel = {"a": rows(True), "b": rows(True), "c": rows(False), "g": rows(False, "pack violation")}
    comp = compute(["a", "b", "c", "d", "e", "f", "g", "h", "i"], [], not_applicable=["i"])
    out = {n: candidate_outcome(n, cands, sel, comp)[0] for n in "abcdefghi"}
    assert out == {"a": "SOLVED", "b": "PHYSICALLY_VALID_FTL", "c": "TIME_LIMIT_NO_USABLE_PLAN", "d": "INFEASIBLE",
                   "e": "NO_INCUMBENT", "f": "ERROR", "g": "OPTIMAL_PHYSICALLY_INVALID", "h": "SKIPPED", "i": "NOT_APPLICABLE"}
    # the physical reason travels with the outcome
    assert candidate_outcome("g", cands, sel, comp)[1] == "pack violation"


def test_required_starvation_counts_only_real_failures():
    cands = {"det": sol("OPTIMAL"), "sto": sol("NO_FEASIBLE_SOLUTION"), "cvar": sol("INFEASIBLE"), "ftl": sol("FEASIBLE_TIME_LIMIT")}
    sel = {"det": rows(True), "ftl": rows(False)}
    comp = compute(["det", "sto", "cvar", "ftl", "hedged", "stress"], ["prot"], not_applicable=["hedged", "stress"])
    c = _completeness(None, cands, sel, comp)
    assert c["classification"] == {"det": "REQUIRED", "sto": "REQUIRED", "cvar": "REQUIRED", "ftl": "REQUIRED",
                                   "prot": "OPTIONAL", "hedged": "NOT_APPLICABLE", "stress": "NOT_APPLICABLE"}
    assert c["required_candidate_count"] == 4              # hedged/stress are not required when they cannot exist
    assert c["required_candidate_completed"] == 1          # det
    assert c["required_candidate_starved"] == 2            # sto (no incumbent) and ftl (time-limited, physically invalid)
    assert c["required_candidate_infeasible"] == 1         # cvar: a definitive answer, not starvation
    assert c["not_applicable_count"] == 2
    assert c["optional_candidate_count"] == 1 and c["optional_candidate_skipped"] == 1 and c["optional_candidate_completed"] == 0
    assert set(c["required_starved_names"]) == {"sto", "ftl"}
    assert abs(c["required_candidate_starvation_rate"] - 0.5) < 1e-9
    kinds = {(o["candidate"], o["outcome"]) for o in c["omissions"]}
    assert ("hedged", "not_applicable") in kinds and ("sto", "required_starved") in kinds and ("cvar", "required_infeasible") in kinds
    # nothing is silent: every class named by the screen has an outcome
    assert set(c["outcomes"]) == {"det", "sto", "cvar", "ftl", "prot", "hedged", "stress"}


def test_an_attempted_but_unusable_joint_recovery_is_not_reported_as_never_built():
    comp = compute(["joint_recovery"], [], attempts={"joint_recovery": sol("NO_FEASIBLE_SOLUTION")})
    outcome, why = candidate_outcome("joint_recovery", {}, {}, comp)
    assert outcome == "NO_INCUMBENT" and "budget" in why
    assert "SKIPPED" in STARVED_OUTCOMES and "INFEASIBLE" not in STARVED_OUTCOMES and "NOT_APPLICABLE" not in STARVED_OUTCOMES
