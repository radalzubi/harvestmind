"""P2 multi-echelon layer: contract extensions, correlated worlds, transfer physics, the network
incumbent policy, the network view, accounting and explanations, and the identities that keep the
frozen P0 / P1 behaviour untouched."""
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest
from pydantic import ValidationError

from zaad.full.contracts import IncumbentTransfer, Request, Transfer
from zaad.full.fixtures_p1 import NOW
from zaad.full.model import Solution, solve
from zaad.full.planner import plan
from zaad.full.policies import baseline_plan
from zaad.full.settlement import PhysicalViolation, settle
from zaad.full.worlds import draw
from zaad.meio.accounting import network_accounting
from zaad.meio.baselines import independent_branch_requests, network_rule_plan
from zaad.meio.fixtures_p2 import p2_request
from zaad.meio.planner import network_router, plan_network
from zaad.meio.topology import NETWORK_LIMITS, lane_arrival, network_state, validate_network

KNOWN = {"known_at": NOW}


def world(req):
    return draw(req, req.seed, 1, deterministic=True)


# ---------------------------------------------------------------- contract


def test_transfer_physics_fields_default_to_the_frozen_continuous_lane():
    arc = Transfer(**KNOWN, id="a", sku="A", origin="c", destination="b", lead_periods=1, capacity=10., cost_per_unit=.1, loss_fraction=0., approved=True)
    assert arc.multiple == 0. and arc.fixed_cost_per_dispatch == 0.
    with pytest.raises(ValidationError):
        Transfer(**KNOWN, id="a", sku="A", origin="c", destination="b", lead_periods=1, capacity=10., cost_per_unit=.1, loss_fraction=0., approved=True, multiple=-1)


def test_incumbent_transfers_and_network_rules_are_validated():
    req = p2_request()
    data = req.model_dump(mode="python")
    data["incumbent_transfers"] = [{**KNOWN, "transfer": "no_such_lane", "period": 0, "expiry": 52, "quantity": 10.}]
    with pytest.raises(ValidationError):
        Request.model_validate(data)
    data["incumbent_transfers"] = [{**KNOWN, "transfer": "lane_north", "period": req.horizon, "expiry": 52, "quantity": 10.}]
    with pytest.raises(ValidationError):
        Request.model_validate(data)
    data["incumbent_transfers"] = [{**KNOWN, "transfer": "lane_north", "period": 0, "expiry": 52, "quantity": 10.}]
    assert Request.model_validate(data).incumbent_transfers[0].transfer == "lane_north"
    for rule, ok in (("network:rop", True), ("network:pool", True), ("network:magic", False), ("reorder_point", True)):
        data["incumbent_rule"] = rule
        if ok:
            Request.model_validate(data)
        else:
            with pytest.raises(ValidationError):
                Request.model_validate(data)
    with pytest.raises(ValidationError):
        Request.model_validate({**req.model_dump(mode="python"), "demand_correlation": 1.5})


# ---------------------------------------------------------------- correlated worlds


def test_zero_correlation_is_the_frozen_draw_bit_for_bit_and_a_single_service_never_changes():
    req = p2_request(demand_correlation=0.)
    data = req.model_dump(mode="python")
    data.pop("demand_correlation")
    absent = Request.model_validate(data)
    for a, b in zip(draw(req, req.seed, 3), draw(absent, req.seed, 3)):
        assert a.demand == b.demand and a.fills == b.fills and a.arrival == b.arrival and a.name == b.name
    single = p2_request(branches=("north",), opening_central=100.)
    correlated = single.model_copy(update={"demand_correlation": .9})
    for a, b in zip(draw(single, single.seed, 3), draw(correlated, single.seed, 3)):
        assert a.demand == b.demand and a.name == b.name        # no group of two: the frozen path runs


def test_declared_correlation_changes_dependence_not_marginals():
    stats = {}
    for rho in (0., .6, 1.):
        req = p2_request(demand_correlation=rho)
        worlds = draw(req, req.seed, 150)
        north = np.array([w.demand["svc_north"] for w in worlds])
        south = np.array([w.demand["svc_south"] for w in worlds])
        stats[rho] = (north.mean(), south.mean(), north.std(), float(np.corrcoef(north.ravel(), south.ravel())[0, 1]), (north + south).sum(axis=1).std())
    for rho in (.6, 1.):
        assert abs(stats[rho][0] - stats[0.][0]) < 3. and abs(stats[rho][2] - stats[0.][2]) < 2.   # marginal mean and spread preserved
    assert abs(stats[0.][3]) < .15 and .4 < stats[.6][3] < .8 and stats[1.][3] > .95
    assert stats[0.][4] < stats[.6][4] < stats[1.][4]        # pooled spread grows with correlation: less diversification


# ---------------------------------------------------------------- transfer physics


def test_lane_packs_are_whole_in_the_model_and_enforced_by_settlement():
    req = p2_request(lane_multiple=12., opening_branch=110., opening_central=600., lane_capacity=240.)
    sol = solve(req, world(req), service_floor=True)
    assert sol.usable_plan
    per_period: dict[tuple[str, int], float] = {}
    for (arc, _e, t), q in sol.transfers.items():
        per_period[arc, t] = per_period.get((arc, t), 0.) + q
    assert per_period and all(abs(q / 12. - round(q / 12.)) < 1e-6 for q in per_period.values())
    illegal = Solution("OPTIMAL", {}, {("lane_north", 52, 0): 7.}, {}, {}, None, [], 0., 0, 0, None, 0., [])
    with pytest.raises(PhysicalViolation, match="pack"):
        settle(req, illegal, world(req)[0])
    legal = replace(illegal, transfers={("lane_north", 52, 0): 12.})
    assert settle(req, legal, world(req)[0])["conservation_residual"] == pytest.approx(0., abs=1e-6)


def test_dispatch_cost_is_charged_once_per_used_period_in_model_and_settlement():
    base = p2_request(opening_branch=20., opening_central=400.)
    priced = base.model_copy(update={"transfers": tuple(a.model_copy(update={"fixed_cost_per_dispatch": 50.}) for a in base.transfers)})
    move = Solution("OPTIMAL", {}, {("lane_north", 52, 0): 30., ("lane_north", 52, 1): 30., ("lane_south", 52, 0): 30.}, {}, {}, None, [], 0., 0, 0, None, 0., [])
    a, b = settle(base, move, world(base)[0]), settle(priced, move, world(priced)[0])
    assert b["ledger"]["transfer"] - a["ledger"]["transfer"] == pytest.approx(3 * 50.)
    pinned_a = solve(base, world(base), fixed=move)
    pinned_b = solve(priced, world(priced), fixed=move)
    assert pinned_a.usable_plan and pinned_b.usable_plan
    assert pinned_b.projected_cost - pinned_a.projected_cost == pytest.approx(3 * 50., abs=1e-4)


# ---------------------------------------------------------------- incumbent network policy


def test_network_rule_projects_transfers_the_common_model_accepts_and_settlement_conserves():
    req = p2_request(lane_multiple=12., lane_capacity=300., opening_branch=40.)
    for rule in ("network:rop", "network:pool"):
        proj = baseline_plan(req, rule)
        assert proj.transfers and all(t < req.horizon for (_a, _e, t), _q in proj.transfers.items())
        per_period: dict[tuple[str, int], float] = {}
        for (a, _e, t), q in proj.transfers.items():
            per_period[a, t] = per_period.get((a, t), 0.) + q
        assert all(abs(q / 12. - round(q / 12.)) < 1e-6 for q in per_period.values())
        sol = solve(req, world(req), fixed=replace(proj, status="OPTIMAL"))
        assert sol.status == "OPTIMAL", sol.warnings
        out = settle(req, sol, world(req)[0])
        assert abs(out["conservation_residual"]) < 1e-6
        assert all(s > .9 for s in out["service"].values())
    frozen = baseline_plan(req, "reorder_point")
    assert frozen.transfers == {}                       # the frozen rules never transfer


def test_priority_allocation_under_scarcity_serves_the_higher_priority_branch_first():
    req = p2_request(opening_central=60., opening_branch=0., priority={"north": 3., "south": 1.}, lane_capacity=1e6)
    proj = network_rule_plan(req, "network:rop")
    north = sum(q for (a, _e, t), q in proj.transfers.items() if a == "lane_north" and t == 0)
    south = sum(q for (a, _e, t), q in proj.transfers.items() if a == "lane_south" and t == 0)
    assert north == pytest.approx(60.) and south == pytest.approx(0.)
    equal = p2_request(opening_central=60., opening_branch=0., priority=1., lane_capacity=1e6)
    proj = network_rule_plan(equal, "network:rop")
    north = sum(q for (a, _e, t), q in proj.transfers.items() if a == "lane_north" and t == 0)
    south = sum(q for (a, _e, t), q in proj.transfers.items() if a == "lane_south" and t == 0)
    assert north + south == pytest.approx(60.) and north > 0 and south > 0        # proportional among equals


def test_the_frozen_planner_carries_the_network_incumbent_transfers_and_replay_converts_them():
    req = p2_request(opening_central=120., opening_branch=60., max_solve_seconds=5.)
    report = plan(req)
    assert any(r["action"] == "transfer" for r in report["incumbent_actions"])
    assert report["selected_policy"].startswith("operator_rule:network:rop") or report["status"] == "PENDING_REVIEW"
    from zaad.full.replay import replay
    from zaad.full.evaluation import long_truth
    truth = long_truth(req, req.seed + 10000, 2 * req.horizon)
    kept: list = []
    out = replay(req, truth, 2, "incumbent", keep_requests=kept, rolling=True)
    assert out["status"] not in ("PHYSICAL_FAILURE",)
    assert kept and kept[0].incumbent_transfers and all(isinstance(x, IncumbentTransfer) for x in kept[0].incumbent_transfers)


# ---------------------------------------------------------------- network view


def test_network_view_echelons_reachability_shared_origin_and_stranded_stock():
    req = p2_request(lane_lead_periods={"north": 1, "south": 3}, opening_central=200.)
    state = network_state(req)
    assert state.topology == "central_branches"
    assert {k: v.echelon for k, v in state.nodes.items()} == {"central": 0, "north": 1, "south": 1}
    assert state.reach["A", "north"].local_only_periods == 1 and state.reach["A", "south"].local_only_periods == 3
    assert lane_arrival(req, req.transfers[1], 0) == 3
    assert state.shared["origin"][0]["destinations"] == ["north", "south"] and state.shared["origin"][0]["usable_now"] == 200.
    assert not state.stranded and not state.issues
    # stock at a location nothing can reach: stranded
    data = req.model_dump(mode="python")
    data["locations"] = list(data["locations"]) + [{**KNOWN, "id": "attic", "kind": "warehouse", "capacity_volume": 1e6, "holding_per_value_period": .001, "receiving_calendar": "always"}]
    data["stock"] = list(data["stock"]) + [{**KNOWN, "id": "lost", "sku": "A", "location": "attic", "quantity": 77., "reserved": 0., "damaged": 0., "quarantined": 0., "expires_in": 52, "age_periods": 1}]
    stranded = network_state(Request.model_validate(data)).stranded
    assert stranded and stranded[0]["location"] == "attic" and stranded[0]["units"] == 77.


def test_validate_network_flags_zero_cost_reverse_pairs_isolated_demand_and_bounds():
    req = p2_request(lane_cost=0., extra_lanes=[{"id": "back_north", "origin": "north", "destination": "central", "lead_periods": 1, "capacity": 100., "cost_per_unit": 0.}])
    issues = validate_network(req)
    assert any("zero-cost reverse pair" in i for i in issues)
    data = p2_request().model_dump(mode="python")
    data["transfers"] = [a for a in data["transfers"] if a["destination"] != "south"]
    assert any("isolated" in i for i in validate_network(Request.model_validate(data)))
    assert validate_network(p2_request(), limits={**NETWORK_LIMITS, "transfers": 1})


def test_router_names_the_contested_origin_and_the_competing_branches():
    req = p2_request(opening_central=50., opening_branch=10.)
    state = network_state(req)
    fits = {s.id: {"mean": 100.} for s in req.services}
    router = network_router(req, state, fits)
    assert router["scarce_origins"][0]["scarce"] and set(router["affected_locations"]) == {"central", "north", "south"}
    assert any("allocation decides" in r for r in router["reasons"])
    calm_req = p2_request(opening_central=5000., opening_branch=500.)
    calm = network_router(calm_req, network_state(calm_req), fits)
    assert not calm["scarce_origins"][0]["scarce"] and not calm["reasons"]


# ---------------------------------------------------------------- accounting


def test_network_accounting_conserves_reconciles_and_reports_per_location_service():
    req = p2_request(lane_multiple=12., lane_capacity=300., opening_branch=40., opening_central=150.)
    proj = replace(baseline_plan(req, "network:rop"), status="OPTIMAL")
    sol = solve(req, world(req), fixed=proj)
    accounts = network_accounting(req, sol, draw(req, req.seed + 10000, 3), "test")
    assert accounts["usable_worlds"] == 3 and accounts["conservation"]["holds_on_every_world"]
    assert accounts["economics"]["reconciles_on_every_world"] and not accounts["economics"]["unmapped_ledger_keys"]
    assert set(accounts["economics"]["buckets"]) == {"node", "lane", "upstream", "network"}
    assert abs(sum(accounts["economics"]["buckets"].values()) - accounts["economics"]["economic_cost"]) < 1e-6 * max(1., abs(accounts["economics"]["economic_cost"]))
    for lane in accounts["lanes"].values():
        assert lane["pack_legal"] and lane["capacity_respected"] and lane["ping_pong_units"] == 0.
    assert {s["location"] for s in accounts["services"]} == {"north", "south"}
    assert accounts["network_service"]["demand_weighted"] is not None and accounts["network_service"]["min_location_service"] is not None
    flows = {(f["sku"], f["location"]): f for f in accounts["flows"]}
    assert flows["A", "central"]["transfer_out"] > 0 and flows["A", "north"]["transfer_receipts"] > 0
    assert accounts["stranded_units_at_end"] == 0.


# ---------------------------------------------------------------- P2 planner and identities


def test_single_node_network_reduces_to_the_frozen_planner():
    req = p2_request(branches=("branch",), opening_central=0., opening_branch=150., incumbent_rule="reorder_point", max_solve_seconds=5.,
                     extra={"_single_node": True})
    assert not req.transfers and len(req.locations) == 1
    frozen = plan(req)
    correlated = plan(req.model_copy(update={"demand_correlation": .7}))
    assert frozen["actions"] == correlated["actions"] and frozen["status"] == correlated["status"] and frozen["selected_policy"] == correlated["selected_policy"]
    wrapped = plan_network(req)
    assert wrapped["actions"] == frozen["actions"] and wrapped["status"] == frozen["status"]
    assert wrapped["network"]["state"]["topology"] == "single_node" and wrapped["network"]["router"]["scarce_origins"] == []


def test_plan_network_reports_the_network_block_with_explanations(monkeypatch):
    req = p2_request(opening_central=120., opening_branch={"north": 60., "south": 40.}, priority={"north": 2., "south": 1.}, max_solve_seconds=5.)
    report = plan_network(req)
    net = report["network"]
    assert report["approval_required"] is True and report["executable_purchase_order"] is False
    assert net["selected"]["conservation"]["holds_on_every_world"] and net["selected"]["economics"]["reconciles_on_every_world"]
    assert net["incumbent"]["usable_worlds"] >= 1
    e = net["explanations"]
    assert e["verdict"] and e["transfers"] and e["purchases"] is not None and "summary" in e["do_nothing"]
    assert e["allocation"] and "receives" in e["allocation"][0]["summary"]
    text = " ".join(row["summary"] for row in e["transfers"] + e["purchases"] + e["held_centrally"] + e["allocation"]) + e["verdict"] + e["do_nothing"]["summary"]
    for jargon in ("MILP", "CVaR", "candidate", "solver", "objective"):
        assert jargon not in text
    import json
    json.dumps(report, allow_nan=False)


def test_independent_branch_requests_isolate_every_branch_as_its_own_chain():
    req = p2_request(lane_lead_periods=2, lane_cost=.3, opening_central=100., supplier_capacity=500.)
    parts = independent_branch_requests(req)
    assert set(parts) == {"north", "south"}
    for name, part in parts.items():
        assert {loc.id for loc in part.locations} == {"central", name} and len(part.services) == 1
        assert [a.destination for a in part.transfers] == [name] and part.transfers[0].cost_per_unit == .3
        assert part.sources[0].id == "src_A" and part.sources[0].destination == "central" and part.sources[0].lead_days == 7
        assert 0 < part.sources[0].capacity_by_period[0] < 500.
    assert sum(x.usable for p in parts.values() for x in p.stock if x.location == "central") == pytest.approx(100.)
    assert sum(p.sources[0].capacity_by_period[0] for p in parts.values()) == pytest.approx(500.)


# ---------------------------------------------------------------- network continuation (P2)


def test_origin_residual_is_valued_through_its_lanes_never_above_the_branch_and_never_twice():
    from zaad.full.lotsizing import continuation_feeds, cycle_continuation_terms
    from zaad.full.terminal import continuation_value
    from zaad.full.worlds import forecast_all
    req = p2_request(lane_cost=.4, lane_lead_periods=1, opening_central=0., opening_branch=0.)
    fits = forecast_all(req)
    feeds = continuation_feeds(req, fits)
    assert set(feeds) == {("A", "central")} and {f["branch"] for f in feeds["A", "central"]} == {"north", "south"}
    single = p2_request(branches=("branch",), opening_central=0., extra={"_single_node": True}, incumbent_rule="reorder_point")
    assert continuation_feeds(single, forecast_all(single)) == {}
    at_branch = continuation_value(req, [{"sku": "A", "location": "north", "expiry": 52, "quantity": 100.}], [], fits)
    at_origin = continuation_value(req, [{"sku": "A", "location": "central", "expiry": 52, "quantity": 100.}], [], fits)
    salvage = 100. * req.skus[0].terminal_value
    assert at_branch["continuation_credit"] > salvage and at_origin["continuation_credit"] > salvage       # both above salvage
    assert at_origin["continuation_credit"] < at_branch["continuation_credit"]                            # lane cost and lead are paid
    assert at_branch["continuation_credit"] - at_origin["continuation_credit"] <= 100. * .4 + 100. * req.skus[0].asset_value * .02 + 1e-6
    # no double counting: a branch already holding a full cycle leaves the origin's units nothing but salvage-ish value
    slabs = cycle_continuation_terms(req, fits)["A", "north"]
    cycle_units = sum(d for d, _ in slabs)
    both = continuation_value(req, [{"sku": "A", "location": "north", "expiry": 52, "quantity": cycle_units * 2},
                                    {"sku": "A", "location": "central", "expiry": 52, "quantity": 100.}], [], fits, cap_units={"A": cycle_units})
    branch_only = continuation_value(req, [{"sku": "A", "location": "north", "expiry": 52, "quantity": cycle_units * 2}], [], fits, cap_units={"A": cycle_units})
    assert both["continuation_credit"] - branch_only["continuation_credit"] <= 100. * req.skus[0].terminal_value + 1e-6 + 100. * req.skus[0].asset_value * .5


def test_the_solve_credits_origin_residual_through_feeds_and_shares_the_branch_demand():
    from zaad.full.lotsizing import continuation_feeds, cycle_continuation_terms
    from zaad.full.worlds import forecast_all
    req = p2_request(lane_cost=.4, opening_central=900., opening_branch=200., fixed_order_cost=200.)   # a multi-period cycle: slabs beyond the lane lead
    fits = forecast_all(req)
    slabs = cycle_continuation_terms(req, fits)
    feeds = continuation_feeds(req, fits)
    assert len(slabs["A", "north"]) > 1
    hold = Solution("OPTIMAL", {}, {}, {}, {}, None, [], 0., 0, 0, None, 0., [])   # buy nothing, move nothing: 900 stay at central
    without = solve(req, world(req), fixed=hold, continuation=slabs)
    with_feeds = solve(req, world(req), fixed=hold, continuation=slabs, continuation_feeds=feeds)
    assert without.usable_plan and with_feeds.usable_plan
    assert with_feeds.projected_cost < without.projected_cost - 1.                      # the central residual now earns above salvage
    # bounded by the slabs: the credit cannot exceed one full cycle of branch demand at the net margin
    bound = sum(max(0., m - .4) * d for b in ("north", "south") for d, m in slabs["A", b])
    assert without.projected_cost - with_feeds.projected_cost <= bound + 1e-6
    # single node: the kwarg is never built, so the frozen path is untouched
    single = p2_request(branches=("branch",), opening_central=0., extra={"_single_node": True}, incumbent_rule="reorder_point")
    assert continuation_feeds(single, forecast_all(single)) == {}
