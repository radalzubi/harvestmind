"""P4 adaptive recourse: contract, information sets, non-anticipativity, comparators, neutrality."""
from __future__ import annotations

import re
from dataclasses import replace

import pytest

from zaad.full.contracts import Request
from zaad.full.model import solve
from zaad.full.planner import plan, report_json
from zaad.meio.fixtures_p2 import p2_request
from zaad.recourse.contracts import resolve
from zaad.recourse.fixtures import branches, build, scale_demand, with_recourse
from zaad.recourse.information import information_sets, lookup, node_map, observable_signature
from zaad.recourse.policy import compare, non_anticipativity, world_plan


def test_absent_and_disabled_blocks_are_frozen():
    base = p2_request()
    assert base.recourse is None and resolve(base) is None
    off = Request.model_validate({**base.model_dump(mode="json"), "recourse": {"enabled": False, "review_periods": [3]}})
    assert resolve(off) is None
    def strip(s):
        return re.sub(r'"information_hash": "[0-9a-f]+"|"[a-z_]*seconds(?:_total)?": [0-9.e-]+', "", s)   # hashes and every timing
    r0, r1 = plan(base), plan(off)
    assert "recourse" not in r1 and strip(report_json(r0)) == strip(report_json(r1))


@pytest.mark.parametrize("bad", [{"review_periods": [5, 2]}, {"review_periods": [0]}, {"review_periods": [12]}, {"review_periods": [1, 2, 3]},
                                 {"observables": ["weather"]}, {"actions": ["cancel"]}, {"demand_grid": 0}, {"continuations": 9}])
def test_contract_refuses_bad_declarations(bad):
    base = p2_request().model_dump(mode="json")
    with pytest.raises(ValueError):
        Request.model_validate({**base, "recourse": {"enabled": True, "review_periods": [3], **bad}})


def test_information_sets_use_history_only_and_are_order_independent():
    req, rc, worlds = build("A1_demand_visible_at_epoch")
    e = rc.epochs[0]
    sets = information_sets(req, rc, worlds)
    assert len(sets[e]) == 2 and abs(sum(s.probability for s in sets[e]) - 1) < 1e-12
    w = worlds[0]
    future_only = replace(w, demand={s: tuple(d * (3. if t >= e else 1.) for t, d in enumerate(v)) for s, v in w.demand.items()})
    assert observable_signature(req, rc, w, e) == observable_signature(req, rc, future_only, e)
    rev = information_sets(req, rc, list(reversed(worlds)))
    assert [s.signature for s in sets[e]] == [s.signature for s in rev[e]]


def test_recourse_columns_are_per_node_and_frozen_names_otherwise():
    req, rc, worlds = build("A1_demand_visible_at_epoch")
    nodes = node_map(req, rc, worlds)
    static = solve(req, worlds, service_floor=True)
    adaptive = solve(req, worlds, service_floor=True, nodes=nodes)
    assert static.recourse is None and adaptive.recourse is not None
    assert adaptive.variables > static.variables
    first = rc.epochs[0]
    assert all(k[1] < first for k in adaptive.purchases)          # here-and-now only
    assert set(adaptive.recourse["nodes"]) == {s.id for s in nodes.sets[first]}
    na = non_anticipativity(adaptive, nodes, req)
    assert na["pass"], na


def test_ordering_and_zero_information_neutrality():
    req, rc, worlds = build("D1_demand_recourse")
    out = compare(req, worlds, rc, service_floor=True)
    assert out["ordering_ok"] and out["value_of_adaptation"] > 0
    assert out["perfect_cost"] <= out["adaptive_cost"] + 1e-6 <= out["static_cost"] + 2e-6
    req2, rc2, worlds2 = build("N3_zero_information")
    out2 = compare(req2, worlds2, rc2, perfect=False, service_floor=True)
    assert len(out2["nodes"].sets[rc2.epochs[0]]) == 1 and abs(out2["value_of_adaptation"]) < 1e-6


def test_world_plan_and_lookup_use_history_only():
    req, rc, worlds = build("A1_demand_visible_at_epoch")
    out = compare(req, worlds, rc, perfect=False, service_floor=True)
    nodes = out["nodes"]
    e = rc.epochs[0]
    plans = [world_plan(out["adaptive"], req, rc, nodes, w, index=i) for i, w in enumerate(worlds)]
    for p in plans:
        for k, q in out["adaptive"].purchases.items():
            assert abs(p.purchases.get(k, 0.) - q) < 1e-9
    w = worlds[0]
    a = replace(w, demand={s: tuple(d * (1. if t < e else .5) for t, d in enumerate(v)) for s, v in w.demand.items()})
    b = replace(w, demand={s: tuple(d * (1. if t < e else 2.) for t, d in enumerate(v)) for s, v in w.demand.items()})
    assert lookup(req, rc, nodes.sets, a) == lookup(req, rc, nodes.sets, b)


def test_transfer_only_actions_keep_purchases_static():
    req = with_recourse(p2_request(opening_branch=300.), review_periods=[3], observables=["demand"], actions=["transfer"])
    rc = resolve(req)
    worlds = branches(req, rc, [("normal", .5, None), ("high", .5, scale_demand(1.3))], 3)
    adaptive = solve(req, worlds, service_floor=True, nodes=node_map(req, rc, worlds))
    assert all(not p["purchases"] for p in adaptive.recourse["nodes"].values())
    assert any(k[1] >= 3 for k in adaptive.purchases)


def test_planner_report_block_is_operator_language_and_gated():
    req = build("D1_demand_recourse")[0]
    r = plan(req)
    b = r["recourse"]
    assert r["approval_required"] is True and r["executable_purchase_order"] is False
    assert b["verdict"] in ("ADAPTIVE PLAN SELECTED", "NO MATERIAL ADAPTIVE BENEFIT", "ADAPTIVE PLAN NOT SELECTED (a static candidate passed the gates at lower settled cost)")
    assert b["ordering_ok"] and b["non_anticipativity"]["pass"]
    text = " ".join(s for ep in b["policy"] for br in ep["branches"] for s in br["condition"])
    assert "e3." not in text and "w0" not in text
    assert "never a recommendation" in b["perfect_information_scope"]
