"""P0-E / P0-F final comparison with corrected accounting and physically validated FTL.
usage: final8.py <arm> <cells...>   arms: always_joint never_joint v8_current rule_supply rule_supply_cover v7_full
Writes final8_<arm>.json (one entry per cell) with per-review detail."""
import sys, time, json, collections, statistics as st
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import run_zaad_full_benchmark as B
import zaad.full.screen as S
import zaad.full.planner as P
import zaad.full.replay as R
from zaad.full.model import Solution
from zaad.full.replay import replay

arm = sys.argv[1]; cells = [int(x) for x in sys.argv[2:]]
orig_min, orig_opt, orig_solve, orig_plan = dict(S.MINIMUM_SAFE), dict(S.OPTIONAL), P.solve, P.plan
if arm == "always_joint":
    for s in list(S.MINIMUM_SAFE):
        if "joint_recovery" not in S.MINIMUM_SAFE[s]: S.MINIMUM_SAFE[s] = S.MINIMUM_SAFE[s] + ("joint_recovery",)
        S.OPTIONAL[s] = tuple(c for c in S.OPTIONAL[s] if c != "joint_recovery")
if arm == "never_joint":
    for s in list(S.MINIMUM_SAFE):
        S.MINIMUM_SAFE[s] = tuple(c for c in S.MINIMUM_SAFE[s] if c != "joint_recovery")
        S.OPTIONAL[s] = tuple(c for c in S.OPTIONAL[s] if c != "joint_recovery")
    def gated(req, worlds, *a, _o=orig_solve, **k):
        if k.get("service_first") == "all" and (len(worlds) != req.scenarios or not req.stresses):
            return Solution("NOT_REQUESTED", {}, {}, {}, {}, None, [], 0., 0, 0, None, None, ["excluded by never_joint"])
        return _o(req, worlds, *a, **k)
    P.solve = gated
rule = {"rule_deficit": "deficit", "rule_deficit_cover": "deficit_cover"}.get(arm, "v8")
out = {}
for cid in cells:
    cell = next(c for c in B.cells("v7") if c["cell"] == cid)
    req = B.request_for(cell, 38001).model_copy(update={"adaptive_escalation": arm != "v7_full", "adaptive_solve_budget": True, "joint_recovery_rule": rule})
    truth = B.truth_for(req, cell, 38001)
    reps = []
    def timed(r):
        t0 = time.perf_counter(); rep = orig_plan(r); reps.append((time.perf_counter() - t0, rep)); return rep
    P.plan = timed; R.plan = timed
    t0 = time.perf_counter(); res = replay(req, truth, cell["horizon"], "gated"); wall = time.perf_counter() - t0
    P.plan = orig_plan; R.plan = orig_plan
    log = res.get("reviews") or []
    per, unmet, inv = [], [], []
    for r in log:
        d = sum(x["demand"] for x in r["settlement"]["service_by_period"]); sv = sum(x["served"] for x in r["settlement"]["service_by_period"])
        per.append(sv / d if d else 1.); unmet.append(d - sv); inv += [x["inventory_value"] for x in r["settlement"]["trace"]]
    d_all = sum(x["demand"] for r in log for x in r["settlement"]["service_by_period"]); s_all = sum(x["served"] for r in log for x in r["settlement"]["service_by_period"])
    o = [rep["orchestration"] for _, rep in reps]; q = [rep["solve_quality"] for _, rep in reps]
    lat = sorted(t for t, _ in reps)
    qt = lambda p: lat[min(len(lat) - 1, int(p * (len(lat) - 1)))] if lat else 0.
    row = {
        "service": s_all / max(d_all, 1e-9), "tail": min(per) if per else None, "p10": sorted(per)[max(0, int(.1 * (len(per) - 1)))] if per else None,
        "breach_reviews": sum(1 for x in per if x < cell["target"] - 1e-6), "worst_unmet": max(unmet) if unmet else 0., "total_unmet": sum(unmet),
        "inventory": st.mean(inv) if inv else 0., "cost": res.get("economic_cost"), "wall": wall, "reviews": len(reps),
        "required_requested": sum(x["required_candidate_count"] for x in o), "required_completed": sum(x["required_candidate_completed"] for x in o),
        "required_starved": sum(x["required_candidate_starved"] for x in o), "required_infeasible": sum(x.get("required_candidate_infeasible", 0) for x in o),
        "required_starved_names": dict(collections.Counter(n for x in o for n in x["required_starved_names"])),
        "optional_requested": sum(x["optional_candidate_count"] for x in o), "optional_completed": sum(x["optional_candidate_completed"] for x in o),
        "optional_skipped": sum(x["optional_candidate_skipped"] for x in o), "not_applicable": sum(x.get("not_applicable_count", 0) for x in o),
        "milps_attempted": sum(x["milps_attempted"] for x in o), "ftl_valid": sum(1 for x in q for c in x["candidates"].values() if c["status"] == "FEASIBLE_TIME_LIMIT" and c["physically_validated"]),
        "ftl_invalid": sum(1 for x in q for c in x["candidates"].values() if c["status"] == "FEASIBLE_TIME_LIMIT" and not c["physically_validated"]),
        "no_incumbent": sum(x["milps_no_feasible_solution"] for x in o), "physical_invalid": sum(len(x["physically_invalid_candidates"]) for x in o),
        "joint_built": sum(1 for x in o if "joint_recovery" in x["candidates_built"]), "joint_chosen": sum(1 for _, rep in reps if rep.get("selected_policy") == "joint_recovery"),
        "joint_required": sum(1 for x in o if (x.get("classification") or {}).get("joint_recovery") == "REQUIRED"),
        "lat_p50": qt(.5), "lat_p90": qt(.9), "lat_p95": qt(.95), "lat_max": lat[-1] if lat else 0.,
        "states": dict(collections.Counter(x["state"] for x in o)), "chosen": dict(collections.Counter(rep.get("selected_policy") or "?" for _, rep in reps)),
        "per_review": [{"state": x["state"], "selected": rep.get("selected_policy"), "service": p, "unmet": u, "joint": "joint_recovery" in x["candidates_built"],
                        "joint_class": (x.get("classification") or {}).get("joint_recovery"), "starved": x["required_starved_names"], "latency": t}
                       for (t, rep), x, p, u in zip(reps, o, per, unmet)],
    }
    out[cid] = row
    rs = row["required_starved"] / max(row["required_requested"], 1)
    print(f"cell {cid:3d} {arm:18s} svc={row['service']:.3f} p10={row['p10']:.3f} tail={row['tail']:.3f} breach={row['breach_reviews']:2d} unmet={row['total_unmet']:6.1f} worst={row['worst_unmet']:5.1f} inv={row['inventory']:6.1f} cost={round(row['cost'])} "
          f"req={row['required_completed']}/{row['required_requested']} starved={row['required_starved']} ({100*rs:.1f}%) infeas={row['required_infeasible']} NA={row['not_applicable']} opt={row['optional_completed']}/{row['optional_requested']} "
          f"FTLok={row['ftl_valid']} FTLbad={row['ftl_invalid']} noinc={row['no_incumbent']} joint={row['joint_required']}req/{row['joint_built']}built/{row['joint_chosen']}chosen lat p50={row['lat_p50']:.2f} p90={row['lat_p90']:.1f} p95={row['lat_p95']:.1f} max={row['lat_max']:.1f} wall={wall:.0f}s", flush=True)
    json.dump(out, open(f"/private/tmp/claude-501/-Users-radalzubi-Desktop-harvestmind/ff795fbd-41f4-4af5-afd4-b87ad517d896/scratchpad/final8_{arm}.json", "w"), indent=1)
S.MINIMUM_SAFE.clear(); S.MINIMUM_SAFE.update(orig_min); S.OPTIONAL.clear(); S.OPTIONAL.update(orig_opt); P.solve = orig_solve
