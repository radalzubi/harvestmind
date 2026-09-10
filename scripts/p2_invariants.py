"""P2 network invariants: the twenty network principles of the brief, each checked directly on the
frozen model, the independent settlement or the P2 layer, on declared development fixtures. A
violation is a defect, not a benchmark result. Written to docs/zaad_full/evidence/p2/P2_INVARIANTS.json
and P2_INVARIANTS.md.

usage: PYTHONPATH=. python3 -m scripts.p2_invariants [--benchmark <tag>]   (the tag supplies invariant 18)"""
from __future__ import annotations

import argparse
import json
import time
from dataclasses import replace
from pathlib import Path

from zaad.full.model import Solution, solve
from zaad.full.settlement import PhysicalViolation, settle
from zaad.full.worlds import draw
from zaad.meio.accounting import network_accounting
from zaad.meio.fixtures_p2 import p2_request

OUT = Path("docs/zaad_full/evidence/p2")


def det(req):
    return draw(req, req.seed, 1, deterministic=True)


def fixed_plan(purchases=None, transfers=None) -> Solution:
    return Solution("OPTIMAL", purchases or {}, transfers or {}, {}, {}, None, [], 0., 0, 0, None, 0., [])


def period_transfers(sol: Solution) -> dict[tuple[str, int], float]:
    out: dict[tuple[str, int], float] = {}
    for (arc, _e, t), q in sol.transfers.items():
        out[arc, t] = out.get((arc, t), 0.) + q
    return out


def total_transfers(sol: Solution) -> float:
    return sum(sol.transfers.values())


def inv_01_conservation() -> dict:
    req = p2_request(opening_central=300., opening_branch=50.)
    sol = solve(req, det(req), service_floor=True)
    out = settle(req, sol, det(req)[0])
    accounts = network_accounting(req, sol, draw(req, req.seed + 10000, 3))
    return {"pass": abs(out["conservation_residual"]) < 1e-6 and accounts["conservation"]["holds_on_every_world"],
            "settlement_residual": out["conservation_residual"], "max_flow_row_residual": accounts["conservation"]["max_row_residual"],
            "transfers_units": total_transfers(sol), "principle": "a transfer moves units, never creates them: opening + receipts - served - out - expired = closing at every location"}


def inv_02_no_double_count() -> dict:
    req = p2_request(opening_central=100., opening_branch=0., lane_capacity=1e6)
    sol = solve(req, det(req), service_floor=False)
    first = sum(q for (a, e, t), q in sol.transfers.items() if t == 0)
    illegal = fixed_plan(transfers={("lane_north", 52, 0): 100., ("lane_south", 52, 0): 100.})
    refused = False
    try:
        settle(req, illegal, det(req)[0])
    except PhysicalViolation:
        refused = True
    return {"pass": first <= 100. + 1e-6 and refused, "period_0_outbound": first, "central_usable": 100., "settlement_refuses_200_from_100": refused,
            "principle": "one unit protects one place: both branches cannot draw the same central unit"}


def inv_03_unreachable_inventory() -> dict:
    req = p2_request(lane_lead_periods=4, opening_branch=0., opening_central=1000.)
    sol = solve(req, det(req), service_floor=False)
    out = settle(req, sol, det(req)[0])
    early = [x for x in out["service_by_period"] if x["period"] < 4]
    served_early = sum(x["served"] for x in early)
    return {"pass": served_early <= 1e-6 and sol.usable_plan, "served_in_periods_0_to_3": served_early, "demand_in_periods_0_to_3": sum(x["demand"] for x in early),
            "central_units": 1000., "lane_lead": 4, "principle": "stock four periods away serves nothing in the next four periods, in the plan and in the settlement"}


def inv_04_05_transfer_cost_monotone() -> dict:
    worlds = None
    totals = {}
    for cost in (0., .2, 5.):
        req = p2_request(lane_cost=cost, opening_central=600., opening_branch=60.)
        worlds = det(req)
        totals[cost] = total_transfers(solve(req, worlds, service_floor=True))
    return {"pass": totals[0.] >= totals[.2] - 1e-6 >= totals[5.] - 2e-6, "transfer_units_by_lane_cost": totals,
            "principle": "all else equal, a cheaper lane is used weakly more and a dearer lane weakly less"}


def inv_06_shorter_lead_more_useful() -> dict:
    costs = {}
    for lead in (1, 3):
        req = p2_request(lane_lead_periods=lead, opening_central=600., opening_branch=120.)
        sol = solve(req, det(req), service_floor=False)
        costs[lead] = sol.projected_cost
    return {"pass": costs[1] <= costs[3] + 1e-6, "projected_cost_by_lead": costs, "principle": "reachable pooled stock is weakly more useful when the lane is shorter"}


def inv_07_capacity() -> dict:
    req = p2_request(lane_capacity=60., opening_central=800., opening_branch=20.)
    sol = solve(req, det(req), service_floor=False)
    peak = max(period_transfers(sol).values(), default=0.)
    refused = False
    try:
        settle(req, fixed_plan(transfers={("lane_north", 52, 0): 61.}), det(req)[0])
    except PhysicalViolation:
        refused = True
    return {"pass": peak <= 60. + 1e-6 and refused, "peak_lane_period_units": peak, "capacity": 60., "settlement_refuses_61": refused,
            "principle": "transfers never exceed lane capacity"}


def inv_08_pack_rounding() -> dict:
    req = p2_request(lane_multiple=24., opening_central=800., opening_branch=110., lane_capacity=240.)
    sol = solve(req, det(req), service_floor=True)
    legal = all(abs(q / 24. - round(q / 24.)) < 1e-6 for q in period_transfers(sol).values())
    refused = False
    try:
        settle(req, fixed_plan(transfers={("lane_north", 52, 0): 30.}), det(req)[0])
    except PhysicalViolation:
        refused = True
    return {"pass": legal and refused and total_transfers(sol) > 0, "period_units": {f"{a}@{t}": q for (a, t), q in period_transfers(sol).items()}, "settlement_refuses_30_of_24s": refused,
            "principle": "transfer quantities stay legal packs"}


def inv_09_shared_central_inventory() -> dict:
    req = p2_request(opening_central=150., opening_branch=0.)
    sol = solve(req, det(req), service_floor=False)
    first = sum(q for (a, e, t), q in sol.transfers.items() if t == 0)
    return {"pass": first <= 150. + 1e-6, "period_0_allocations": first, "central_usable": 150., "principle": "total allocations cannot exceed the stock the origin holds"}


def inv_10_supply_cap() -> dict:
    req = p2_request(supplier_capacity=90., opening_central=0., opening_branch=0.,
                     local_sources={"north": {"price_premium": .1, "supplier": "supplier", "capacity": 1e6}})
    # the local source shares the supplier's capacity resource: make it explicit
    data = req.model_dump(mode="python")
    for s in data["sources"]:
        s["resources"] = ["supplier_cap"]
    data["resources"] = [r for r in data["resources"] if r["id"] == "supplier_cap"]
    from zaad.full.contracts import Request
    req = Request.model_validate(data)
    sol = solve(req, det(req), service_floor=False)
    by_period: dict[int, float] = {}
    for (s, t), q in sol.purchases.items():
        by_period[t] = by_period.get(t, 0.) + q
    peak = max(by_period.values(), default=0.)
    refused = False
    try:
        settle(req, fixed_plan(purchases={("src_A", 0): 60., ("src_A_north", 0): 60.}), det(req)[0])
    except PhysicalViolation:
        refused = True
    return {"pass": peak <= 90. + 1e-6 and refused, "peak_period_purchases": peak, "shared_capacity": 90., "settlement_refuses_120": refused,
            "principle": "a shared supplier capacity cannot be allocated twice across destinations"}


def inv_11_single_node_identity() -> dict:
    from zaad.full.planner import plan
    req = p2_request(branches=("branch",), opening_central=0., opening_branch=150., incumbent_rule="reorder_point", max_solve_seconds=5., extra={"_single_node": True})
    a = plan(req)
    b = plan(req.model_copy(update={"demand_correlation": .8}))
    return {"pass": a["actions"] == b["actions"] and a["status"] == b["status"], "status": a["status"], "selected": a["selected_policy"],
            "principle": "one node, no lane: the P2 fields change nothing; the canonical regression proves the frozen fixtures separately"}


def inv_12_zero_lane_identity() -> dict:
    req = p2_request(opening_central=500., opening_branch=0.)
    data = req.model_dump(mode="python")
    data["transfers"] = []
    from zaad.full.contracts import Request
    cut = Request.model_validate(data)
    sol = solve(cut, det(cut), service_floor=False)
    out = settle(cut, sol, det(cut)[0])
    return {"pass": not sol.transfers and all(v < .5 for v in out["service"].values() if v is not None), "transfers": len(sol.transfers), "service": out["service"],
            "central_units_stranded": 500., "principle": "disconnected nodes cannot exchange inventory: central stock serves nobody"}


def inv_13_14_pooling_and_correlation() -> dict:
    """13: pooling can reduce the inventory needed for the same service under independent demand;
    14: the model does not invent diversification under perfect correlation. Two readings: the
    scenario worlds themselves (the 95th percentile of pooled demand over a two-period window against
    the sum of the branch percentiles: strictly less when independent, equal when comonotone) and the
    joint solve on the same copula draws (pooled network vs isolated branches; pooled inventory rises
    with correlation and the pooling gain does not)."""
    import numpy as np
    from zaad.full.contracts import Request
    stats = {}
    for rho in (1e-6, 1.):
        req = p2_request(demand_correlation=rho, demand_sd_hint=.3)
        worlds = draw(req, req.seed, 400)
        north = np.array([w.demand["svc_north"][:2] for w in worlds]).sum(axis=1)
        south = np.array([w.demand["svc_south"][:2] for w in worlds]).sum(axis=1)
        pooled_q = float(np.quantile(north + south, .95))
        separate_q = float(np.quantile(north, .95) + np.quantile(south, .95))
        stats[rho] = {"pooled_p95": pooled_q, "sum_of_branch_p95": separate_q, "ratio": pooled_q / separate_q}
    worlds_ok13 = stats[1e-6]["ratio"] < .97
    worlds_ok14 = stats[1.]["ratio"] > .98
    results = {}
    for rho in (1e-6, 1.):
        pooled = p2_request(demand_correlation=rho, lane_cost=0., opening_central=300., opening_branch=150., demand_sd_hint=.3, scenarios=3, target=.9, max_solve_seconds=60.)
        worlds = draw(pooled, pooled.seed, pooled.scenarios)
        sol_p = solve(pooled, worlds, service_floor=True, per_world_service=True)
        data = pooled.model_dump(mode="python")
        data["transfers"] = []
        data["stock"] = [s for s in data["stock"] if s["location"] != "central"] + [
            {**next(s for s in data["stock"] if s["location"] == "north"), "id": "split_n", "quantity": 150.},
            {**next(s for s in data["stock"] if s["location"] == "south"), "id": "split_s", "quantity": 150.}]
        data["sources"] = [{**s, "destination": "north", "route": [*list(s["route"])[:-1], "north"]} for s in data["sources"]]
        data["sources"].append({**data["sources"][0], "id": "src_A_south", "destination": "south", "route": ["supplier", "south"]})
        isolated = Request.model_validate(data)
        sol_i = solve(isolated, draw(isolated, isolated.seed, isolated.scenarios), service_floor=True, per_world_service=True)

        def mean_inventory(req, sol):
            rows = [settle(req, sol, w, future_guidance=True) for w in draw(req, req.seed + 10000, 3)]
            return sum(sum(x["inventory_value"] for x in r["trace"]) / len(r["trace"]) for r in rows) / len(rows)
        results[rho] = {"pooled_status": sol_p.status, "isolated_status": sol_i.status,
                        "pooled_inventory_value": mean_inventory(pooled, sol_p) if sol_p.usable_plan else None,
                        "isolated_inventory_value": mean_inventory(isolated, sol_i) if sol_i.usable_plan else None}
    a, b = results[1e-6], results[1.]
    complete = all(x[k] is not None for x in (a, b) for k in ("pooled_inventory_value", "isolated_inventory_value"))
    model_ok13 = complete and a["pooled_inventory_value"] <= a["isolated_inventory_value"] * 1.02
    model_ok14 = complete and b["pooled_inventory_value"] >= a["pooled_inventory_value"] * .98
    return {"pass": worlds_ok13 and worlds_ok14 and model_ok13 and model_ok14,
            "worlds": {"independent": stats[1e-6], "correlated": stats[1.]}, "worlds_pass": {"13": worlds_ok13, "14": worlds_ok14},
            "model": {"independent": a, "correlated": b}, "model_pass": {"13_pooled_leq_isolated": model_ok13, "14_pooled_inventory_rises_with_correlation": model_ok14},
            "principle": "13: pooling can reduce the inventory needed for the same service under independent demand; 14: the scenario worlds and the solve invent no diversification under perfect correlation"}


def inv_15_no_action() -> dict:
    from zaad.meio.planner import plan_network
    req = p2_request(opening_central=400., opening_branch=250., max_solve_seconds=10.)
    rep = plan_network(req)
    a = rep["network"]["selected"]["actions"]
    return {"pass": rep["status"] == "RETAIN_INCUMBENT" or (a.get("transfers_period_0", 0.) <= 1e-6 and a.get("purchases_period_0", 0.) <= 1e-6) or rep["status"] == "PENDING_REVIEW" and rep["orchestration"]["state"] in ("NO_ACTION", "CAPITAL_OPTIMIZATION"),
            "status": rep["status"], "state": rep["orchestration"]["state"], "selected": rep["selected_policy"], "period_0": a,
            "principle": "an efficient state produces no unnecessary transfer or purchase"}


def inv_16_service_not_overridden() -> dict:
    req = p2_request(lane_cost=0., opening_central=600., opening_branch=120., target={"north": .99, "south": .95})
    sol = solve(req, det(req), service_floor=True)
    ok = sol.usable_plan and all(sol.projected_service[s.id] >= s.target - 1e-6 for s in req.services)
    return {"pass": bool(ok), "projected_service": sol.projected_service, "targets": {s.id: s.target for s in req.services},
            "principle": "a free lane never buys one branch's service with another's: every floor holds in the solve"}


def inv_17_allocation() -> dict:
    from zaad.meio.planner import plan_network
    req = p2_request(opening_central=80., opening_branch=0., priority={"north": 3., "south": 1.}, supplier_capacity=50., max_solve_seconds=10.)
    rep = plan_network(req)
    final = rep["network"]["selected"]
    north = sum(r["units"] for r in rep["network"]["explanations"]["transfers"] if r["destination"] == "north")
    south = sum(r["units"] for r in rep["network"]["explanations"]["transfers"] if r["destination"] == "south")
    alloc = rep["network"]["explanations"]["allocation"]
    return {"pass": final["usable_worlds"] > 0 and north >= south - 1e-6 and bool(alloc) and "receives" in alloc[0]["summary"],
            "north_units": north, "south_units": south, "explanation": alloc[0]["summary"] if alloc else None, "status": rep["status"],
            "principle": "scarce stock goes first to the higher-priority branch and the reason is stated"}


def inv_18_recovery(tag: str | None) -> dict:
    path = OUT / f"{tag}.jsonl" if tag else None
    if not path or not path.exists():
        return {"pass": None, "principle": "temporary protection is removed after the risk decays (read from the benchmark record of fixture S)", "note": "no benchmark record supplied"}
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    cells = [r for r in rows if r["fixture"] == "S_recovery_after_imbalance" and r["policy"] == "gated" and r.get("per_review")]
    if not cells:
        return {"pass": None, "principle": "recovery", "note": "fixture S not in the record"}
    checks = []
    for c in cells:
        per = c["per_review"]
        early = sum(r["transfer_units"] for r in per[:2])
        late = sum(r["transfer_units"] for r in per[-2:])
        demand_late = sum(sum(r["demand"].values()) for r in per[-2:])
        checks.append({"seed": c["seed"], "early_transfers": early, "late_transfers": late, "late_demand": demand_late, "reverse": c["network"]["reverse_pair_units"]})
    ok = all(x["late_transfers"] <= x["late_demand"] * 1.25 + 1e-6 and x["reverse"] <= 1e-6 for x in checks)
    return {"pass": ok, "cells": checks, "principle": "after the imbalance is recovered, transfers settle to what demand needs and never reverse"}


def inv_19_terminal_edge() -> dict:
    from zaad.full.lotsizing import continuation_feeds, cycle_continuation_terms
    from zaad.full.worlds import forecast_all
    req = p2_request(opening_central=500., opening_branch=150., fixed_order_cost=200.)
    fits = forecast_all(req)
    slabs, feeds = cycle_continuation_terms(req, fits), continuation_feeds(req, fits)
    sol = solve(req, det(req), service_floor=True, continuation=slabs, continuation_feeds=feeds)
    per = period_transfers(sol)
    H = req.horizon
    last = sum(q for (a, t), q in per.items() if t == H - 1)
    mid = max((sum(q for (a, t2), q in per.items() if t2 == t) for t in range(1, H - 1)), default=0.)
    rate = sum(f["mean"] for f in fits.values())
    # a reverse pair at a real cost: no loop appears
    loop_req = p2_request(opening_central=300., opening_branch=300., extra_lanes=[{"id": "back_north", "origin": "north", "destination": "central", "lead_periods": 1, "capacity": 1e6, "cost_per_unit": .2}])
    loop_sol = solve(loop_req, det(loop_req), service_floor=True)
    back = sum(q for (a, e, t), q in loop_sol.transfers.items() if a == "back_north")
    forward = sum(q for (a, e, t), q in loop_sol.transfers.items() if a == "lane_north")
    return {"pass": last <= mid + rate + 1e-6 and min(back, forward) <= 1e-6, "last_period_transfers": last, "max_mid_period_transfers": mid, "demand_rate": rate,
            "reverse_pair_forward": forward, "reverse_pair_back": back, "principle": "no horizon-edge transfer spike and no loop through a priced reverse lane"}


def inv_20_accounting() -> dict:
    req = p2_request(opening_central=300., opening_branch=50., fixed_order_cost=100., lane_fixed_cost=10.)
    sol = solve(req, det(req), service_floor=True)
    accounts = network_accounting(req, sol, draw(req, req.seed + 10000, 3))
    e = accounts["economics"]
    return {"pass": e["reconciles_on_every_world"] and not e["unmapped_ledger_keys"], "buckets": e["buckets"], "economic_cost": e["economic_cost"], "worst_check": e["worst_check"],
            "principle": "node + lane + upstream + network economics reconcile to the settlement total"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", default=None)
    a = ap.parse_args()
    checks = [("01_conservation", inv_01_conservation), ("02_no_double_count", inv_02_no_double_count), ("03_unreachable_inventory", inv_03_unreachable_inventory),
              ("04_05_transfer_cost_monotone", inv_04_05_transfer_cost_monotone), ("06_shorter_lead_more_useful", inv_06_shorter_lead_more_useful),
              ("07_capacity", inv_07_capacity), ("08_pack_rounding", inv_08_pack_rounding), ("09_shared_central_inventory", inv_09_shared_central_inventory),
              ("10_supply_cap", inv_10_supply_cap), ("11_single_node_identity", inv_11_single_node_identity), ("12_zero_lane_identity", inv_12_zero_lane_identity),
              ("13_14_pooling_and_correlation", inv_13_14_pooling_and_correlation), ("15_no_action", inv_15_no_action), ("16_service_not_overridden", inv_16_service_not_overridden),
              ("17_allocation", inv_17_allocation), ("18_recovery", lambda: inv_18_recovery(a.benchmark)), ("19_terminal_edge_and_loops", inv_19_terminal_edge),
              ("20_accounting", inv_20_accounting)]
    results = {}
    for name, fn in checks:
        started = time.time()
        try:
            results[name] = {**fn(), "seconds": round(time.time() - started, 1)}
        except Exception as exc:   # a crashed invariant is a failure with its reason
            results[name] = {"pass": False, "error": repr(exc), "seconds": round(time.time() - started, 1)}
        print(f"{name:34s} {'PASS' if results[name]['pass'] else ('n/a' if results[name]['pass'] is None else 'FAIL'):5s} {results[name]['seconds']:6.1f}s", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "P2_INVARIANTS.json").write_text(json.dumps(results, indent=1, default=str))
    lines = ["# P2 invariants", "", "| invariant | result | numbers |", "|---|---|---|"]
    for name, r in results.items():
        nums = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items() if k not in ("pass", "principle", "seconds")}
        lines.append(f"| {name} | {'PASS' if r['pass'] else ('n/a' if r['pass'] is None else 'FAIL')} | {json.dumps(nums, default=str)[:400]} |")
    (OUT / "P2_INVARIANTS.md").write_text("\n".join(lines) + "\n")
    failed = [n for n, r in results.items() if r["pass"] is False]
    print("INVARIANTS", "PASS" if not failed else f"FAIL {failed}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
