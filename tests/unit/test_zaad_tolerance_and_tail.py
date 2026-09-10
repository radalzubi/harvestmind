"""Unit-aware zero policy, PO dust closure, terminal financing, and selector gates."""
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from zaad.full.contracts import Request
from zaad.full.demo import example
from zaad.full.model import solve
from zaad.full.planner import (_priority_consistent, _recovery_not_worse, _within_downside, material_shortfall_gap,
                               plan, service_ok, weighted_shortfall)
from zaad.full.replay import replay
from zaad.full.settlement import PhysicalViolation, settle
from zaad.full.tolerance import dust_threshold, is_dust, po_closed, source_pack
from zaad.full.worlds import draw


def test_dust_scales_with_pack_and_never_erases_a_real_order():
    assert is_dust(4.139450919715629e-7)                # the recorded rejection
    assert not is_dust(0.5)                              # half a unit of a continuous SKU is real
    assert dust_threshold(1000.0) == pytest.approx(1e-3) # a pallet-sized pack tolerates a millionth of a pallet
    assert is_dust(5e-4, 1000.0) and not is_dust(0.2, 1000.0)
    assert dust_threshold(0.0) == pytest.approx(1e-6)    # continuous quantities keep the absolute floor
    assert not is_dust(2e-6)                             # two microunits are above the floor and are kept


def _with_dust_po(req: Request, remaining: float) -> Request:
    """Shrink the fixture's open PO to ``remaining`` units, as replay does when solver residue is carried forward."""
    data = req.model_dump(mode="json")
    assert data["pipeline"], "fixture needs an open PO"
    po = data["pipeline"][0]
    po.update(id="dust_po", ordered=remaining, confirmed=remaining, shipped=0., received=0., rejected=0.,
              expected_accepted_remaining=remaining * .9, allow_split_amendments=False)
    for option in po["options"]:
        option["max_quantity"] = remaining
    return Request.model_validate(data)


def test_dust_po_is_closed_consistently_across_model_and_settlement():
    req = _with_dust_po(example("recovery", seed=31001), 4.139450919715629e-7)
    source = next(s for s in req.sources if s.id == req.pipeline[-1].source)
    assert po_closed(req.pipeline[-1], source) and source_pack(source) >= 1e-9
    worlds = draw(req, req.seed, 1, deterministic=True)
    solution = solve(req, worlds)   # the recovery fixture's service floor is infeasible by design
    assert solution.status == "OPTIMAL"
    assert all(po_id != "dust_po" for po_id, _ in solution.amendments)
    # settlement no longer demands an active option for a closed PO
    outcome = settle(req, solution, worlds[0])
    assert outcome["conservation_residual"] == pytest.approx(0., abs=1e-4)


def test_real_small_po_still_needs_exactly_one_option():
    req = _with_dust_po(example("recovery", seed=31002), 0.5)
    worlds = draw(req, req.seed, 1, deterministic=True)
    solution = solve(req, worlds)
    assert solution.status == "OPTIMAL"
    empty = replace(solution, amendments={k: v for k, v in solution.amendments.items() if k[0] != "dust_po"})
    with pytest.raises(PhysicalViolation, match="conservation or exclusivity"):
        settle(req, empty, worlds[0])


def test_replay_never_creates_a_pipeline_order_from_dust():
    req = example("normal", seed=31003)
    truth = draw(req, req.seed + 999, 1)[0]
    result = replay(req, truth, 3, "stochastic")
    assert result["status"] == "COMPLETE", result.get("failure")
    for review in result["reviews"]:
        for purchase in review["purchases"]:
            assert not is_dust(purchase["quantity"])


def _tail_request(req: Request, net_days: int, opening_cash: float, credit: float) -> Request:
    data = req.model_dump(mode="json")
    for term in data["terms"]:
        term["net_days"] = net_days
        term["deposit_fraction"] = 0.
        term["balance_trigger"] = "order"
    data["liquidity"]["opening_cash"] = opening_cash
    data["liquidity"]["credit_limit"] = credit
    data["liquidity"]["minimum_cash"] = 0.
    return Request.model_validate(data)


def test_settlement_refuses_unfinanceable_post_horizon_invoices():
    base = example("normal", seed=31004)
    far = base.horizon * base.period_days * 3   # every invoice lands after the horizon
    req = _tail_request(base, far, opening_cash=5.0, credit=0.0)
    worlds = draw(req, req.seed, 1, deterministic=True)
    plan_ = solve(req, worlds, service_floor=True)
    if plan_.status != "OPTIMAL":
        # the model itself refused: the terminal solvency row is binding
        assert plan_.status in {"INFEASIBLE", "ABSTAIN", "TIMEOUT"}
        return
    forced = replace(plan_, purchases={**plan_.purchases, (req.sources[0].id, 0): 40.0})
    with pytest.raises(PhysicalViolation, match="post-horizon obligations"):
        settle(req, forced, worlds[0])


def test_settlement_reports_terminal_reserve_and_headroom():
    req = _tail_request(example("normal", seed=31005), 30, opening_cash=1e6, credit=1e6)
    worlds = draw(req, req.seed, 1, deterministic=True)
    plan_ = solve(req, worlds, service_floor=True)
    assert plan_.status == "OPTIMAL"
    out = settle(req, plan_, worlds[0])
    assert out["terminal_liability_reserve"] >= 0 and out["terminal_financing_headroom"] >= out["terminal_liability_reserve"] - 1e-5
    assert out["unpaid_contractual_payments"] == pytest.approx(out["terminal_liability_reserve"])


def _row(values: dict, cost: float = 100.0) -> dict:
    return {"usable": True, "economic_cost": cost, "service": dict(values),
            "service_by_period": [{"service": k, "demand": 100.0, "served": v * 100.0} for k, v in values.items()],
            "order_metrics": {k: {} for k in values}}


def test_material_gap_scales_with_priority_and_tolerance():
    req = example("understock")
    assert material_shortfall_gap(req) == pytest.approx(max(1e-6, req.service_tolerance * sum(
        next(c.priority for c in req.customers if c.id == s.customer) for s in req.services)))
    before, after = [_row({"retail_A": .81})], [_row({"retail_A": .81 + req.service_tolerance / 2})]
    assert not _recovery_not_worse(req, before, after)          # half a tolerance is not material
    assert _recovery_not_worse(req, before, [_row({"retail_A": .92})])


def test_priority_consistency_blocks_hidden_sacrifice():
    req = example("understock")
    sid = req.services[0].id
    same = [_row({sid: .9})]
    lower = [_row({sid: .9 - 5 * req.service_tolerance})]
    assert _priority_consistent(req, same, same)
    assert not _priority_consistent(req, same, lower)           # worse with nobody raised
    assert _within_downside(req, [_row({sid: .9}, 100.)], [_row({sid: .9}, 100. + req.downside_cost_tolerance * 100.)])
    assert not _within_downside(req, [_row({sid: .9}, 100.)], [_row({sid: .9}, 100. + 2 * req.downside_cost_tolerance * 100. + 1.)])


def test_strict_gate_holds_when_targets_are_feasible_and_ranking_when_not():
    report = plan(example("normal", seed=31006))
    joint = report["joint_service_feasibility"]
    assert joint["recovery_mode"] is (not joint["target_vector_feasible"])
    if not joint["recovery_mode"]:
        assert report["mode"] != "ALLOCATE" and joint["recovery_ranking"] == []
    under = plan(example("understock", seed=31007))
    ju = under["joint_service_feasibility"]
    if ju["recovery_mode"]:
        assert under["mode"] == "ALLOCATE"
        assert all("weighted_service_shortfall" in r for r in ju["recovery_ranking"])
        if under["status"] == "PENDING_REVIEW":
            assert ju["selected_weighted_shortfall"] is not None
            assert ju["selected_weighted_shortfall"] + ju["material_gap"] <= ju["incumbent_weighted_shortfall"] + 1e-9
    assert under["approval_required"] and under["executable_purchase_order"] is False
    # weighted shortfall is zero exactly when every target is met
    rows = [_row({req_service.id: 1.0 for req_service in example("normal").services})]
    assert service_ok(example("normal"), rows) and weighted_shortfall(example("normal"), rows) == 0.0
    assert not np.isfinite(weighted_shortfall(example("normal"), [{"usable": False}]))
