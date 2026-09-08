"""P0-C: is joint_recovery the causal driver of the V7 -> V8 inventory difference?

Four arms, same cells, same seed, same (size-scaled) solve budget so starvation does not confound:
  A  V7_full            adaptive_escalation off - every candidate class solved every review
  B  V8_escalated       adaptive_escalation on  - screen decides; joint_recovery only where the
                                                   state lists it or the on-demand frontier fires
  C  V8_forced_joint    B + joint_recovery added to every state's minimum-safe set
  D  V8_no_joint        B with joint_recovery removed everywhere, on-demand escalation included

Per review it captures the P0-B completeness accounting, so the table also serves as the
required/optional starvation confirmation the P0-A brief asks for. usage: ablate8.py [cells...]
"""
import sys, time, collections, statistics as st, json
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import run_zaad_full_benchmark as B
import zaad.full.screen as S
import zaad.full.planner as P
import zaad.full.replay as R
from zaad.full.model import Solution
from zaad.full.replay import replay

ARMS = ("V7_full", "V8_escalated", "V8_forced_joint", "V8_no_joint")
cells = [int(x) for x in sys.argv[1:]] or [15, 16, 20, 21, 90, 108]
orig_min = dict(S.MINIMUM_SAFE); orig_opt = dict(S.OPTIONAL)
orig_solve = P.solve; orig_plan = P.plan
rows = {}


def blocked(*a, **k):
    return Solution("NOT_REQUESTED", {}, {}, {}, {}, None, [], 0., 0, 0, None, None, ["joint_recovery excluded by ablation arm D"])


for cid in cells:
    cell = next(c for c in B.cells("v7") if c["cell"] == cid)
    for arm in ARMS:
        S.MINIMUM_SAFE.clear(); S.MINIMUM_SAFE.update(orig_min)
        S.OPTIONAL.clear(); S.OPTIONAL.update(orig_opt)
        P.solve = orig_solve
        if arm == "V8_forced_joint":
            for s in list(S.MINIMUM_SAFE):
                if "joint_recovery" not in S.MINIMUM_SAFE[s]:
                    S.MINIMUM_SAFE[s] = S.MINIMUM_SAFE[s] + ("joint_recovery",)
                S.OPTIONAL[s] = tuple(c for c in S.OPTIONAL[s] if c != "joint_recovery")
        if arm == "V8_no_joint":
            for s in list(S.MINIMUM_SAFE):
                S.MINIMUM_SAFE[s] = tuple(c for c in S.MINIMUM_SAFE[s] if c != "joint_recovery")
                S.OPTIONAL[s] = tuple(c for c in S.OPTIONAL[s] if c != "joint_recovery")
            # The on-demand frontier escalation also builds joint_recovery (service_first="all" on the
            # combined fitted+stress worlds). Block that solve; the fitted-only frontier reference
            # (same flag, fitted worlds only) is kept because it is a report reference, not a candidate.
            def gated(req, worlds, *a, _o=orig_solve, **k):
                if k.get("service_first") == "all" and (len(worlds) != req.scenarios or not req.stresses):
                    return blocked()
                return _o(req, worlds, *a, **k)
            P.solve = gated
        req = B.request_for(cell, 38001).model_copy(
            update={"adaptive_escalation": arm != "V7_full", "adaptive_solve_budget": True})
        truth = B.truth_for(req, cell, 38001)
        reps = []
        def timed(r, _a=reps):
            t0 = time.perf_counter(); rep = orig_plan(r); _a.append((time.perf_counter() - t0, rep)); return rep
        P.plan = timed; R.plan = timed
        t0 = time.perf_counter()
        res = replay(req, truth, cell["horizon"], "gated")
        wall = time.perf_counter() - t0
        P.plan = orig_plan; R.plan = orig_plan
        log = res.get("reviews") or []
        per = []
        for r in log:
            d = sum(x["demand"] for x in r["settlement"]["service_by_period"])
            sv = sum(x["served"] for x in r["settlement"]["service_by_period"])
            per.append(sv / d if d else 1.)
        unmet = [sum(x["demand"] - x["served"] for x in r["settlement"]["service_by_period"]) for r in log]
        d_all = sum(x["demand"] for r in log for x in r["settlement"]["service_by_period"])
        s_all = sum(x["served"] for r in log for x in r["settlement"]["service_by_period"])
        inv = [x["inventory_value"] for r in log for x in r["settlement"]["trace"]]
        target = cell["target"]
        o = [rep["orchestration"] for _, rep in reps]
        q = [rep["solve_quality"] for _, rep in reps]
        lat = [t for t, _ in reps]
        chosen = collections.Counter(rep.get("selected_policy") or "?" for _, rep in reps)
        joint_present = sum(1 for x in o if "joint_recovery" in x["candidates_built"])
        joint_chosen = sum(1 for _, rep in reps if rep.get("selected_policy") == "joint_recovery")
        rows[(cid, arm)] = {
            "service": s_all / max(d_all, 1e-9), "tail": min(per) if per else None,
            "p10": sorted(per)[max(0, int(.1 * (len(per) - 1)))] if per else None,
            "breach_reviews": sum(1 for x in per if x < target - 1e-6),
            "worst_unmet": max(unmet) if unmet else 0., "total_unmet": sum(unmet),
            "inventory": st.mean(inv) if inv else 0., "cost": res.get("economic_cost"), "wall": wall,
            "reviews": len(reps), "median_lat": st.median(lat) if lat else 0., "max_lat": max(lat) if lat else 0.,
            "required_requested": sum(x["required_candidate_count"] for x in o),
            "required_completed": sum(x["required_candidate_completed"] for x in o),
            "required_starved": sum(x["required_candidate_starved"] for x in o),
            "required_starved_names": collections.Counter(n for x in o for n in x["required_starved_names"]),
            "optional_requested": sum(x["optional_candidate_count"] for x in o),
            "optional_completed": sum(x["optional_candidate_completed"] for x in o),
            "milps_attempted": sum(x["milps_attempted"] for x in o),
            "milps_optimal": sum(x["milps_optimal"] for x in o),
            "milps_ftl": sum(x["milps_feasible_time_limited"] for x in o),
            "milps_no_incumbent": sum(x["milps_no_feasible_solution"] for x in o),
            "milps_infeasible": sum(x["milps_infeasible"] for x in o),
            "timeouts": sum(1 for x in q for c in x["candidates"].values() if c["status"] in ("FEASIBLE_TIME_LIMIT", "NO_FEASIBLE_SOLUTION")),
            "physical_invalid": sum(len(x["physically_invalid_candidates"]) for x in o),
            "joint_built_reviews": joint_present, "joint_chosen_reviews": joint_chosen,
            "states": collections.Counter(x["state"] for x in o), "chosen": chosen,
            "policies": collections.Counter(r["warnings"][1] for r in log if len(r["warnings"]) > 1)}
        x = rows[(cid, arm)]
        rs = x["required_starved"] / max(x["required_requested"], 1)
        print(f"cell {cid:3d} {arm:16s} svc={x['service']:.3f} tail={x['tail']:.3f} p10={x['p10']:.3f} "
              f"breach={x['breach_reviews']:2d} unmet={x['total_unmet']:7.1f} inv={x['inventory']:6.1f} "
              f"cost={x['cost'] if x['cost'] is None else round(x['cost'])} "
              f"req={x['required_completed']}/{x['required_requested']} starved={x['required_starved']} ({100*rs:.1f}%) "
              f"opt={x['optional_completed']}/{x['optional_requested']} FTL={x['milps_ftl']} noinc={x['milps_no_incumbent']} "
              f"phys_bad={x['physical_invalid']} joint={x['joint_built_reviews']}/{x['joint_chosen_reviews']} "
              f"lat med={x['median_lat']:.2f} max={x['max_lat']:.1f} wall={x['wall']:.0f}s", flush=True)
        if x["required_starved_names"]:
            print(f"          starved required: {dict(x['required_starved_names'])}", flush=True)
S.MINIMUM_SAFE.clear(); S.MINIMUM_SAFE.update(orig_min); S.OPTIONAL.clear(); S.OPTIONAL.update(orig_opt); P.solve = orig_solve
print("\n=== P0-C SUMMARY ===")
print(f"{'metric':>22s} " + " ".join(f"{a:>16s}" for a in ARMS))
for label, key, agg in (("median service", "service", st.median), ("median tail service", "tail", st.median),
                        ("median p10", "p10", st.median), ("total breach reviews", "breach_reviews", sum),
                        ("total unmet units", "total_unmet", sum), ("worst single unmet", "worst_unmet", max),
                        ("median inventory", "inventory", st.median), ("required starved", "required_starved", sum),
                        ("required requested", "required_requested", sum), ("no-incumbent solves", "milps_no_incumbent", sum),
                        ("FTL solves", "milps_ftl", sum), ("joint built reviews", "joint_built_reviews", sum),
                        ("joint chosen reviews", "joint_chosen_reviews", sum), ("total wall seconds", "wall", sum)):
    vals = [agg([rows[(c, a)][key] for c in cells if rows[(c, a)][key] is not None]) for a in ARMS]
    print(f"{label:>22s} " + " ".join(f"{v:16.3f}" for v in vals))
json.dump({f"{k[0]}|{k[1]}": {kk: (dict(vv) if isinstance(vv, collections.Counter) else vv) for kk, vv in v.items()}
           for k, v in rows.items()}, open(sys.argv[0].replace(".py", ".json"), "w"), indent=1)
