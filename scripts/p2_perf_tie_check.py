"""Explain the first decision difference of every benchmark cell between the pre-performance record and
the performance re-run (P2 performance pass, corrective plan): materialise the exact snapshot of that
review (the predecessors being identical, the snapshot is the one both runs planned on, up to the
labels of interchangeable cohorts), plan it under the frozen formulation and under the new one, and
report whether every candidate's objective is identical (a tie broken differently) or not (a finding).

Policies: gated (ZAAD), echelon_base_stock (one projected solve), independent (each isolated chain
planned by ZAAD). network_rop / central_pool are rule projections and never differ.

usage: PYTHONPATH=. python3 -m scripts.p2_perf_tie_check [--compare p2_perf_decision_compare] [--policy gated] [--out p2_perf_tie_check]"""
from __future__ import annotations

import argparse
import json
import time

from scripts.p2_benchmark import OUT, _branch_truth
from scripts.p2_fixtures import build
from scripts.p2_profile_compare import compare as compare_profiles
import zaad.full.model as model


def _first_differences(compare: dict, policy: str | None) -> list[dict]:
    seen: dict = {}
    for x in compare["differing_reviews"]:
        key = tuple(x["cell"])
        if policy and key[1] != policy:
            continue
        seen.setdefault(key, x)
    return list(seen.values())


def _plan_both(req, worlds_fn=None):
    """Plan (or solve) a request under both formulations through the profiler's instrumentation."""
    from scripts.p2_profile_review import Instrumentation, decision
    from zaad.full.planner import plan
    out = {}
    for flag in (False, True):
        model.FEFO_SYMMETRY_ELIMINATION = flag
        inst = Instrumentation(capture_models=False)
        inst.install()
        started = time.perf_counter()
        try:
            report = plan(req)
        finally:
            inst.uninstall()
        out[flag] = {"wall_seconds": time.perf_counter() - started, "decision": decision(report), "solves": inst.solves, "switches": {"FEFO_SYMMETRY_ELIMINATION": flag}}
    model.FEFO_SYMMETRY_ELIMINATION = True
    return out


def _echelon_both(req):
    from zaad.full.echelon import echelon_targets
    from zaad.full.model import solve
    from zaad.full.worlds import draw
    out = {}
    for flag in (False, True):
        model.FEFO_SYMMETRY_ELIMINATION = flag
        sol = solve(req, draw(req, req.seed, 1, deterministic=True), targets=echelon_targets(req))
        out[flag] = {"status": sol.status, "objective": sol.projected_cost, "purchases_t0": sorted((k[0], round(v, 6)) for k, v in sol.purchases.items() if k[1] == 0),
                     "transfers_t0": sorted((k[0], k[1], round(v, 6)) for k, v in sol.transfers.items() if k[2] == 0)}
    model.FEFO_SYMMETRY_ELIMINATION = True
    return out


def _snapshot(name: str, seed: int, review: int, method: str, part_of: str | None = None):
    """The exact request planned at `review` under the new code (fast), for the network replay or for
    one isolated chain of the independent baseline."""
    from zaad.full.evaluation import long_truth
    from zaad.full.replay import replay
    from zaad.meio.baselines import independent_branch_requests, register_replay_methods
    register_replay_methods()
    initial = build(name, seed)
    H = initial.horizon
    reviews = review + 1
    truth = long_truth(initial, seed + 10000, (-(-(reviews - 1 + H) // H)) * H)
    kept: list = []
    if part_of:
        part = independent_branch_requests(initial)[part_of]
        replay(part, _branch_truth(initial, part, truth), reviews, "gated", keep_requests=kept, rolling=True)
    else:
        replay(initial, truth, reviews, method, keep_requests=kept, rolling=True)
    return kept[review]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare", default="p2_perf_decision_compare")
    ap.add_argument("--policy", default=None)
    ap.add_argument("--out", default="p2_perf_tie_check")
    ap.add_argument("--rel", type=float, default=1e-6, help="objective tolerance; the request's own solver_mip_gap applies where larger (two optima inside the declared gap are the same answer)")
    ap.add_argument("--cells", default="", help="comma-separated fixture letters to restrict to")
    a = ap.parse_args()
    only = {x for x in a.cells.split(",") if x}
    compare = json.loads((OUT / f"{a.compare}.json").read_text())
    before_records = {(r["fixture"], r["policy"], r["seed"]): r for r in (json.loads(line) for line in (OUT / "p2_final.jsonl").read_text().splitlines())}
    after_records = {(r["fixture"], r["policy"], r["seed"]): r for r in (json.loads(line) for line in (OUT / "p2_authoritative_perf.jsonl").read_text().splitlines())}
    results = []
    for x in _first_differences(compare, a.policy):
        name, policy, seed = x["cell"]
        review = x["review"]
        if only and name.split("_")[0] not in only:
            continue
        rb, ra = before_records[name, policy, seed], after_records[name, policy, seed]
        prev_same = True
        if review > 0:
            pb, pa = rb["per_review"][review - 1], ra["per_review"][review - 1]
            prev_same = all(abs(pb["end_stock_by_location"].get(k, 0.) - pa["end_stock_by_location"].get(k, 0.)) <= 1e-6 for k in set(pb["end_stock_by_location"]) | set(pa["end_stock_by_location"]))
        frozen_tl = sorted(c for c, s in (x.get("candidate_status_before") or {}).items() if s == "FEASIBLE_TIME_LIMIT")
        entry = {"cell": [name, policy, seed], "review": review, "key": x["key"], "before": x["before"], "after": x["after"],
                 "predecessor_end_stock_identical": prev_same, "frozen_time_limited_candidates": frozen_tl}
        started = time.time()
        rel = max(a.rel, float(build(name, seed).solver_mip_gap))
        entry["objective_tolerance"] = rel
        if policy == "gated":
            req = _snapshot(name, seed, review, "gated")
            both = _plan_both(req)
            cmp_ = compare_profiles(both[False], both[True], rel)
            entry.update(objective_identical=cmp_["objective_identical"], decision_identical_on_snapshot=cmp_["decision_identical"],
                         decision_keys_on_snapshot=cmp_["decision_keys"], walls=(round(both[False]["wall_seconds"], 1), round(both[True]["wall_seconds"], 1)),
                         candidates=[{k: c[k] for k in ("candidate", "status", "objective", "same_objective", "nodes")} for c in cmp_["candidates"] if "note" not in c])
        elif policy == "echelon_base_stock":
            req = _snapshot(name, seed, review, "echelon_base_stock")
            both = _echelon_both(req)
            same = both[False]["status"] == both[True]["status"] and (both[False]["objective"] is None or abs(both[False]["objective"] - both[True]["objective"]) <= rel * max(1., abs(both[False]["objective"])))
            entry.update(objective_identical=same, decision_identical_on_snapshot=(both[False]["purchases_t0"] == both[True]["purchases_t0"] and both[False]["transfers_t0"] == both[True]["transfers_t0"]),
                         candidates=[{"candidate": "echelon_base_stock", "status": (both[False]["status"], both[True]["status"]), "objective": (both[False]["objective"], both[True]["objective"])}])
        elif policy == "independent":
            from zaad.meio.baselines import independent_branch_requests
            parts = independent_branch_requests(build(name, seed))
            objective_ok, decision_ok, cands = True, True, []
            for part_name in parts:
                req = _snapshot(name, seed, review, "gated", part_of=part_name)
                both = _plan_both(req)
                cmp_ = compare_profiles(both[False], both[True], rel)
                objective_ok &= cmp_["objective_identical"]
                decision_ok &= cmp_["decision_identical"]
                cands += [{"chain": part_name, **{k: c[k] for k in ("candidate", "status", "objective", "same_objective")}} for c in cmp_["candidates"] if "note" not in c]
            entry.update(objective_identical=objective_ok, decision_identical_on_snapshot=decision_ok, candidates=cands)
        else:
            entry.update(note="rule projection: never differs")
        entry["seconds"] = round(time.time() - started, 1)
        results.append(entry)
        print(f"{name.split('_')[0]} {policy:<18} {seed} r{review} {x['key']:<10} predecessor stock identical {prev_same} frozen time-limited {frozen_tl or '-'} "
              f"objective identical {entry.get('objective_identical')} decision on snapshot identical {entry.get('decision_identical_on_snapshot')} ({entry['seconds']}s)", flush=True)
    (OUT / f"{a.out}.json").write_text(json.dumps(results, indent=1, default=str))
    unexplained = [r for r in results if r.get("objective_identical") is False and not r["frozen_time_limited_candidates"]]
    print(f"cells checked {len(results)}; objective identical {sum(1 for r in results if r.get('objective_identical'))}; "
          f"frozen time-limited {sum(1 for r in results if r['frozen_time_limited_candidates'])}; unexplained {len(unexplained)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
