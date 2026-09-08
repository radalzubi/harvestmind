"""Per-review diagnostic replay: everything the planner decided at each review, for one cell/arm.
usage: diag8.py <cell> <arm> [out.json]   arms: V7_full V8_escalated V8_forced_joint V8_no_joint"""
import sys, time, json
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import run_zaad_full_benchmark as B
import zaad.full.screen as S
import zaad.full.planner as P
import zaad.full.replay as R
from zaad.full.model import Solution
from zaad.full.replay import replay

cid, arm = int(sys.argv[1]), sys.argv[2]
out_path = sys.argv[3] if len(sys.argv) > 3 else f"/private/tmp/claude-501/-Users-radalzubi-Desktop-harvestmind/ff795fbd-41f4-4af5-afd4-b87ad517d896/scratchpad/diag8_{cid}_{arm}.json"
cell = next(c for c in B.cells("v7") if c["cell"] == cid)
orig_solve, orig_plan = P.solve, P.plan
if arm == "V8_forced_joint":
    for s in list(S.MINIMUM_SAFE):
        if "joint_recovery" not in S.MINIMUM_SAFE[s]:
            S.MINIMUM_SAFE[s] = S.MINIMUM_SAFE[s] + ("joint_recovery",)
        S.OPTIONAL[s] = tuple(c for c in S.OPTIONAL[s] if c != "joint_recovery")
if arm == "V8_no_joint":
    for s in list(S.MINIMUM_SAFE):
        S.MINIMUM_SAFE[s] = tuple(c for c in S.MINIMUM_SAFE[s] if c != "joint_recovery")
        S.OPTIONAL[s] = tuple(c for c in S.OPTIONAL[s] if c != "joint_recovery")
    def gated(req, worlds, *a, _o=orig_solve, **k):
        if k.get("service_first") == "all" and (len(worlds) != req.scenarios or not req.stresses):
            return Solution("NOT_REQUESTED", {}, {}, {}, {}, None, [], 0., 0, 0, None, None, ["excluded by arm D"])
        return _o(req, worlds, *a, **k)
    P.solve = gated
req = B.request_for(cell, 38001).model_copy(update={"adaptive_escalation": arm != "V7_full", "adaptive_solve_budget": True})
truth = B.truth_for(req, cell, 38001)
reps = []
def timed(r):
    t0 = time.perf_counter(); rep = orig_plan(r); reps.append((time.perf_counter() - t0, rep)); return rep
P.plan = timed; R.plan = timed
t0 = time.perf_counter()
res = replay(req, truth, cell["horizon"], "gated")
wall = time.perf_counter() - t0
P.plan = orig_plan; R.plan = orig_plan; P.solve = orig_solve
log = res.get("reviews") or []
rows = []
for i, ((lat, rep), r) in enumerate(zip(reps, log)):
    o = rep["orchestration"]; q = rep["solve_quality"]
    d = sum(x["demand"] for x in r["settlement"]["service_by_period"]); sv = sum(x["served"] for x in r["settlement"]["service_by_period"])
    inv = [x["inventory_value"] for x in r["settlement"]["trace"]]
    rows.append({
        "review": i, "latency": lat, "state": o["state"], "reasons": o.get("reasons"), "escalated": rep.get("compute", {}).get("escalated") or o.get("escalated"),
        "requested": o.get("candidate_classes_requested"), "classification": o.get("classification"), "outcomes": o.get("outcomes"),
        "required": o["required_candidate_count"], "required_done": o["required_candidate_completed"], "required_starved": o["required_candidate_starved"],
        "required_infeasible": o.get("required_candidate_infeasible"), "optional": o["optional_candidate_count"], "optional_done": o["optional_candidate_completed"],
        "optional_skipped": o["optional_candidate_skipped"], "not_applicable": o.get("not_applicable_count"), "omissions": o["omissions"],
        "candidates": {n: {k: c.get(k) for k in ("status", "achieved_gap", "best_bound", "nodes", "solve_seconds", "variables", "constraints", "physically_validated", "physical_failures", "economically_comparable")} for n, c in q["candidates"].items()},
        "selected": rep.get("selected_policy"), "selection_costs": rep.get("selection_costs"),
        "service": sv / d if d else None, "unmet": d - sv, "inventory": (sum(inv) / len(inv)) if inv else None,
        "warnings": r.get("warnings"),
    })
json.dump({"cell": cid, "arm": arm, "wall": wall, "service": res.get("service"), "cost": res.get("economic_cost"), "reviews": rows}, open(out_path, "w"), indent=1, default=str)
print(f"cell {cid} {arm}: {len(rows)} reviews, wall {wall:.0f}s -> {out_path}")
for x in rows:
    starved = [n for n, oc in (x["outcomes"] or {}).items() if x["classification"].get(n) == "REQUIRED" and oc["outcome"] in ("NO_INCUMBENT", "TIME_LIMIT_NO_USABLE_PLAN", "OPTIMAL_PHYSICALLY_INVALID", "ERROR", "SKIPPED")]
    ftl = {n: c["physical_failures"] for n, c in x["candidates"].items() if c["status"] == "FEASIBLE_TIME_LIMIT"}
    print(f"  r{x['review']:02d} {x['state'][:8]:8s} sel={str(x['selected'])[:20]:20s} svc={x['service'] if x['service'] is None else round(x['service'],3)} inv={x['inventory'] if x['inventory'] is None else round(x['inventory'],1)} req={x['required_done']}/{x['required']} starved={starved} NA={x['not_applicable']} FTL={ftl} lat={x['latency']:.1f}")
