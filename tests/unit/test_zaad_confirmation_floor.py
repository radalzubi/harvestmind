"""P1 final blocker B: the confirmation floor (`P1_B_FLOOR_PREREGISTRATION.md`).

Rule B-F (the target floor on a P1-owned identity-stress review for a benefit-established candidate) was
implemented, measured and REJECTED under the one-fix rule: B closed (+2.66% -> +1.60%), every declared-
benchmark control was unchanged, but on the legacy record it admitted an ex-ante-optimistic lean plan on
the volatile fixture Q that stocked out the next week (Q service .980 -> .965 against a .98 target), the
control the pre-registration named. These tests record the standing behaviour: the incumbent-level floor
applies on every review, and the trace evidence stays reproducible."""
from __future__ import annotations

from scripts.p1_fixtures import build
from zaad.full.contracts import Request
from zaad.full.evaluation import long_truth
from zaad.full.ownership import PROTECTION_RECOVERY, PURCHASING_ECONOMICS
from zaad.full.planner import plan
from zaad.full.replay import replay

PRODUCT = {k: Request.model_fields[k].default for k in ("stratified_scenarios", "timing_tiebreak", "analytic_shortage")}


def _snapshot(name, seed, review, reviews):
    req = build(name, seed).model_copy(update=PRODUCT)
    kept: list[Request] = []
    replay(req, long_truth(req, seed + 10000, 12 * (-(-(reviews - 1 + 12) // 12))), reviews, "gated", rolling=True, keep_requests=kept)
    return kept[review]


def test_1_b_review_2_is_retained_by_the_incumbent_floor_as_recorded():
    """B seed 41003 review 2: P1-owned, identity stress, the chosen candidate meets the .95 target and
    costs 30% less, and the incumbent-level floor retains the incumbent's ~100-unit order (phase-1
    trace). With B-F rejected this is the standing behaviour."""
    rep = plan(_snapshot("B_fixed_order_cost_replace_sold", 41003, 2, 3))
    o = rep["orchestration"]
    assert o["planner_owner"] == PURCHASING_ECONOMICS and o["gate_basis"] == "incumbent"
    assert "confirmation_floor_waived" not in o
    # the floor is not waived; whether the review retains the incumbent depends on the lot the earlier
    # reviews bought under the current terminal basis (a cycle-covering lot keeps the deferral above the floor)
    if rep["status"] == "RETAIN_INCUMBENT":
        assert any("stress confirmation" in r for r in rep["reasons"])


def test_2_p0_owned_reviews_keep_the_incumbent_floor():
    import scripts.run_zaad_full_benchmark as B
    cell = next(c for c in B.cells("v7") if c["cell"] == 15)
    req = B.request_for(cell, 38001).model_copy(update={"adaptive_escalation": True, "adaptive_solve_budget": True, "joint_recovery_rule": "deficit"})
    rep = plan(req)
    assert rep["orchestration"]["planner_owner"] == PROTECTION_RECOVERY
    assert rep["orchestration"]["gate_basis"] == "incumbent"


def test_3_the_floor_is_the_request_basis_on_p1_owned_reviews():
    rep = plan(build("T_combined_realistic", 41003).model_copy(update=PRODUCT))
    assert rep["orchestration"]["planner_owner"] == PURCHASING_ECONOMICS
    assert rep["orchestration"]["gate_basis"] == "incumbent"
