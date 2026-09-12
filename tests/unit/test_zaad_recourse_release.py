"""P4 release-audit tests (blockers A - D of the release brief).

A: the perfect-information diagnostic is a bound only when certified (OPTIMAL); a feasible
time-limited incumbent is never a lower bound, never rejects the adaptive plan, and the solver bound
stays apart from the primal cost. B: information-set lookup is exact or REPLAN_REQUIRED; no nearest
routing; generated worlds map exactly; reorder-invariant; report exposes the rule. C: the jobs store
keeps tenant binding and does not corrupt state on duplicate submission. Plus the release-level
invariants on information-set probabilities and delayed information (sections 8 - 9)."""
from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from zaad.full.model import Solution
from zaad.recourse.explain import recourse_block
from zaad.recourse.fixtures import build
from zaad.recourse.information import information_sets, lookup, node_map, observable_signature
from zaad.recourse.policy import CERTIFIED, NON_CERTIFIED, REPLAN_REQUIRED, UNAVAILABLE, assess, attach_fallback, compare, lookup_exactness, world_plan

REQ = SimpleNamespace(solver_mip_gap=1e-6)


def _sol(status: str, cost: float, bound: float | None = None) -> Solution:
    return Solution(status, {}, {}, {}, {}, cost, [], 0., 0, 0, None, None, [], best_bound=bound)


# ---- blocker A -----------------------------------------------------------------------------------

def test_a1_certified_pi_ordering_holds():
    out = assess(REQ, _sol("OPTIMAL", 100.), _sol("OPTIMAL", 90.), _sol("OPTIMAL", 80.))
    assert out["perfect_status"] == CERTIFIED and out["perfect_cost"] == 80. and out["perfect_feasible_cost"] is None
    assert out["ordering_ok"] is True and out["value_of_adaptation"] == 10. and out["value_certified"]
    # a certified PI dearer than the adaptive plan is a genuine ordering failure
    assert assess(REQ, _sol("OPTIMAL", 100.), _sol("OPTIMAL", 90.), _sol("OPTIMAL", 95.))["ordering_ok"] is False


def test_a2_time_limited_pi_primal_is_not_a_bound():
    out = assess(REQ, _sol("OPTIMAL", 100.), _sol("OPTIMAL", 90.), _sol("FEASIBLE_TIME_LIMIT", 85.))
    assert out["perfect_status"] == NON_CERTIFIED
    assert out["perfect_cost"] is None and out["perfect_feasible_cost"] == 85.


def test_a3_solver_bound_stays_apart_from_the_primal():
    out = assess(REQ, _sol("OPTIMAL", 100.), _sol("OPTIMAL", 90.), _sol("FEASIBLE_TIME_LIMIT", 85., bound=70.))
    assert out["perfect_feasible_cost"] == 85. and out["perfect_solver_bound"] == 70. and out["perfect_cost"] is None
    assert out["time_limited"] == ["perfect"]


def test_a5_non_certified_pi_never_rejects_the_adaptive_plan():
    # the time-limited PI incumbent is dearer than the adaptive plan: no ordering failure may follow
    out = assess(REQ, _sol("OPTIMAL", 100.), _sol("OPTIMAL", 90.), _sol("FEASIBLE_TIME_LIMIT", 95.))
    assert out["ordering_ok"] is True and out["perfect_status"] == NON_CERTIFIED
    assert assess(REQ, _sol("OPTIMAL", 100.), _sol("OPTIMAL", 90.), None)["perfect_status"] == UNAVAILABLE


def test_a4_report_labels_a_bound_only_when_certified():
    req, rc, worlds = build("D1_demand_recourse")
    out = compare(req, worlds, rc, service_floor=True)
    assert out["perfect"].status == "OPTIMAL"
    report = {"selected_policy": "stochastic_network"}
    base = {**out, "material": True, "static_built_as_comparator": True}
    certified = recourse_block(req, rc, base, report, worlds, worlds)
    assert certified["perfect_information_status"] == CERTIFIED and "bound" in certified["perfect_information_scope"]
    assert certified["perfect_information_cost"] == out["perfect_cost"]
    # the same solve reported as a feasible time-limited incumbent
    limited = replace(out["perfect"], status="FEASIBLE_TIME_LIMIT")
    view = {**base, "perfect": limited, **assess(req, out["static"], out["adaptive"], limited)}
    block = recourse_block(req, rc, view, report, worlds, worlds)
    assert block["perfect_information_status"] == NON_CERTIFIED
    assert block["perfect_information_cost"] is None and block["perfect_information_feasible_cost"] == limited.projected_cost
    assert "bound" not in block["perfect_information_scope"] and "never a recommendation" in block["perfect_information_scope"]
    assert "certified perfect-information" not in block["ordering_scope"]
    assert block["engineering"]["perfect_solve"]["certified"] is False
    assert any("not as a bound" in s for s in block["explanations"])
    assert block["approval_required"] is True and block["executable_purchase_order"] is False


# ---- blocker B -----------------------------------------------------------------------------------

def test_b1_generated_worlds_map_exactly_by_membership_and_by_signature():
    for name in ("A1_demand_visible_at_epoch", "T2_tree_two_epochs"):
        req, rc, worlds = build(name)
        nodes = node_map(req, rc, worlds)
        for w, world in enumerate(worlds):
            hit = lookup(req, rc, nodes.sets, world)
            for e in rc.epochs:
                nid, exact = hit[e]
                assert exact and nid == nodes.node(w, e)


def test_b2_reordering_worlds_does_not_change_the_mapping():
    req, rc, worlds = build("T2_tree_two_epochs")
    a = information_sets(req, rc, worlds)
    b = information_sets(req, rc, list(reversed(worlds)))
    for e in rc.epochs:
        assert [s.signature for s in a[e]] == [s.signature for s in b[e]]
        assert [round(s.probability, 12) for s in a[e]] == [round(s.probability, 12) for s in b[e]]
        assert [sorted(worlds[i].name for i in s.members) for s in a[e]] == [sorted(list(reversed(worlds))[i].name for i in s.members) for s in b[e]]


def test_b3_b4_unknown_or_mismatched_history_is_replan_required_not_nearest():
    req, rc, worlds = build("A1_demand_visible_at_epoch")
    out = compare(req, worlds, rc, perfect=False, service_floor=True)
    nodes, adaptive = out["nodes"], out["adaptive"]
    e = rc.epochs[0]
    w = worlds[0]
    # B3: a demand history outside every modelled branch
    far = replace(w, demand={s: tuple(d * 7. for d in v) for s, v in w.demand.items()})
    assert lookup(req, rc, nodes.sets, far) == {e: (None, False)}
    rows = lookup_exactness(req, rc, nodes, [far])
    assert rows[0]["replan_required"] and rows[0][f"epoch_{e}"]["rule"] == REPLAN_REQUIRED
    # the plan that world receives is the attached static fallback for the window, not a branch
    plan = world_plan(adaptive, req, rc, nodes, far)
    static_window = {k: q for k, q in out["static"].purchases.items() if k[1] >= e}
    assert {k: q for k, q in plan.purchases.items() if k[1] >= e} == static_window
    assert {k: q for k, q in plan.purchases.items() if k[1] < e} == {k: q for k, q in adaptive.purchases.items() if k[1] < e}
    # B4: a receipt-status mismatch (an order confirmed late in a fixture observing receipts) is not re-interpreted
    req2, rc2, worlds2 = build("R2_shipment_delay")
    nodes2 = node_map(req2, rc2, worlds2)
    e2 = rc2.epochs[0]
    w2 = worlds2[0]
    delayed = replace(w2, arrival={k: (v + 40 if k[1] < e2 else v) for k, v in w2.arrival.items()})
    assert observable_signature(req2, rc2, delayed, e2) != observable_signature(req2, rc2, w2, e2)
    assert lookup(req2, rc2, nodes2.sets, delayed)[e2] == (None, False)


def test_b5_quantisation_boundary_is_deterministic():
    req, rc, worlds = build("A1_demand_visible_at_epoch")
    e = rc.epochs[0]
    w = worlds[0]
    grid = rc.spec.demand_grid
    edge = replace(w, demand={s: tuple((int(d / grid) + .5) * grid if t < e else d for t, d in enumerate(v)) for s, v in w.demand.items()})
    first = observable_signature(req, rc, edge, e)
    assert all(observable_signature(req, rc, edge, e) == first for _ in range(5))
    assert observable_signature(req, rc, replace(edge, name="other"), e) == first


def test_b6_report_exposes_the_replan_rule_and_counts_worlds_outside_the_branches():
    req, rc, worlds = build("A1_demand_visible_at_epoch")
    out = compare(req, worlds, rc, perfect=False, service_floor=True)
    far = replace(worlds[0], name="far", demand={s: tuple(d * 7. for d in v) for s, v in worlds[0].demand.items()})
    block = recourse_block(req, rc, {**out, "material": True, "static_built_as_comparator": True}, {"selected_policy": "x"}, worlds, worlds + [far])
    assert REPLAN_REQUIRED in block["unseen_observation_rule"] and "nearest" in block["unseen_observation_rule"]
    assert block["replan_required"] == {"worlds": 1, "of": len(worlds) + 1, "fallback": "static commitments"}
    assert any("outside the modelled branches" in s for s in block["explanations"])


def test_b7_a6_fallback_attachment_leaves_a_static_solution_untouched():
    static = _sol("OPTIMAL", 10.)
    assert attach_fallback(static, static) is static
    assert attach_fallback(static, None).recourse is None


# ---- blocker C -----------------------------------------------------------------------------------

def test_c8_duplicate_submission_keeps_the_store_consistent(tmp_path):
    from zaad.full.jobs import JobStore
    req = build("N2_no_epochs_is_static")[0]
    store = JobStore(tmp_path / "jobs.sqlite")
    a = store.create("op_a", req, 60.)
    b = store.create("op_a", req, 60.)
    assert a != b
    ra, rb = store.get(a, "op_a"), store.get(b, "op_a")
    assert ra["config_hash"] == rb["config_hash"] and ra["status"] == rb["status"] == "QUEUED"
    assert [j["id"] for j in store.list("op_a")] == [b, a]
    with pytest.raises(KeyError):
        store.get(a, "op_b")
    assert store.list("op_b") == [] and store.active("op_a") == 2


# ---- sections 8 - 9 --------------------------------------------------------------------------------

def test_information_set_probabilities_sum_to_one_and_to_their_members():
    for name in ("A1_demand_visible_at_epoch", "T2_tree_two_epochs", "I7_correlated_plant"):
        req, rc, worlds = build(name)
        sets = information_sets(req, rc, worlds)
        for e in rc.epochs:
            assert abs(sum(s.probability for s in sets[e]) - 1.) < 1e-9
            seen: set[int] = set()
            for s in sets[e]:
                assert abs(s.probability - sum(worlds[i].weight for i in s.members)) < 1e-12
                assert not (seen & set(s.members))
                seen |= set(s.members)
            assert seen == set(range(len(worlds)))


def test_delayed_information_branches_only_after_confirmation():
    req, rc, worlds = build("A2_delayed_information")
    out = compare(req, worlds, rc, perfect=False, service_floor=True)
    nodes = out["nodes"]
    first, later = rc.epochs[0], rc.epochs[-1]
    assert len(nodes.sets[first]) == 1 and len(nodes.sets[later]) == 2
    plans = [world_plan(out["adaptive"], req, rc, nodes, w, index=i) for i, w in enumerate(worlds)]
    for p in plans[1:]:
        for k, q in plans[0].purchases.items():
            if k[1] < later:
                assert abs(p.purchases.get(k, 0.) - q) < 1e-9
    assert out["non_anticipativity"]["pass"]


def test_a7_verdict_distinguishes_no_comparator_and_time_limited_adaptive():
    req, rc, worlds = build("D1_demand_recourse")
    out = compare(req, worlds, rc, service_floor=True)
    report = {"selected_policy": "stochastic_network"}
    # no static comparator plan: not comparable, never "ordering check failed"
    none = replace(out["static"], status="NO_FEASIBLE_SOLUTION", projected_cost=None)
    view = {**out, "static": none, **assess(req, none, out["adaptive"], out["perfect"]), "material": False, "static_built_as_comparator": True}
    block = recourse_block(req, rc, view, report, worlds, worlds)
    assert block["ordering_ok"] is None and block["verdict"].startswith("ADAPTIVE PLAN NOT COMPARABLE")
    # a time-limited adaptive incumbent dearer than the static plan is not an ordering violation
    dear = replace(out["adaptive"], status="FEASIBLE_TIME_LIMIT", projected_cost=out["static"].projected_cost + 100.)
    view = {**out, "adaptive": dear, **assess(req, out["static"], dear, out["perfect"]), "material": False, "static_built_as_comparator": True}
    block = recourse_block(req, rc, view, report, worlds, worlds)
    assert block["ordering_ok"] is False and "time-limited adaptive solve" in block["verdict"] and "ordering check failed" not in block["verdict"]
    # the same cost from a certified adaptive solve is a genuine ordering failure
    dear2 = replace(dear, status="OPTIMAL")
    view = {**out, "adaptive": dear2, **assess(req, out["static"], dear2, out["perfect"]), "material": False, "static_built_as_comparator": True}
    assert recourse_block(req, rc, view, report, worlds, worlds)["verdict"] == "ADAPTIVE PLAN REJECTED (ordering check failed)"
