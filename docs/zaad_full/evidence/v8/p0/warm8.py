"""P0-W6/W8: A/B on captured reviews - frozen scipy path, highspy without seed, highspy + incumbent seed.
usage: warm8.py <reqs.pkl> <arms: frozen,highspy,warm> <review> [review ...]"""
import sys, pickle, time, json
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import zaad.full.planner as P
from zaad.full.contracts import Request
ARMS = {"frozen": {"solver": "highs", "warm_start": False}, "highspy": {"solver": "highspy", "warm_start": False}, "warm": {"solver": "highs", "warm_start": True}}
reqs = pickle.load(open(sys.argv[1], "rb"))
arms = sys.argv[2].split(",")
out = {}
for arg in sys.argv[3:]:
    base = Request.model_validate(reqs[int(arg)].model_dump())
    for arm in arms:
        req = base.model_copy(update={**ARMS[arm], "joint_recovery_rule": "deficit", "adaptive_solve_budget": True})
        t0 = time.perf_counter(); rep = P.plan(req); wall = time.perf_counter() - t0
        o = rep["orchestration"]; q = rep["solve_quality"]["candidates"]
        starved = o["required_starved_names"]; ns = rep["network_service"]
        print(f"=== review {arg} arm={arm:8s} wall={wall:.0f}s state={o['state']} selected={rep.get('selected_policy')} required={o['required_candidate_completed']}/{o['required_candidate_count']} starved={starved} infeasible={o.get('required_candidate_infeasible')}")
        for s in ns:
            print(f"    service {s['service']} target={s['requested']:.3f} expected={s.get('expected_achieved')} incumbent={s.get('incumbent_achieved')}")
        for name, c in q.items():
            if name in ("incumbent", "base_stock"): continue
            w = c.get("warm_start") or {}
            print(f"    {name:22s} {c['status']:20s} secs={round(c['solve_seconds'] or 0,1):6} gap={None if c['achieved_gap'] is None else round(c['achieved_gap'],4)} nodes={c['nodes']} valid={c['physically_validated']} "
                  f"warm={'-' if not w else f'{w.get(chr(97)+'ccepted')}/{w.get('outcome')}/comp={round(w.get('completion_seconds',0),1)}s/solver_ok={w.get('solver_accepted')}'}")
        out[f"{arg}|{arm}"] = {"wall": wall, "state": o["state"], "selected": rep.get("selected_policy"), "starved": starved, "required": o["required_candidate_count"], "done": o["required_candidate_completed"],
                              "candidates": {n: {k: c.get(k) for k in ("status", "solve_seconds", "achieved_gap", "nodes", "physically_validated", "warm_start")} for n, c in q.items()}, "network_service": ns}
        sys.stdout.flush()
json.dump(out, open(sys.argv[1].replace("reqs_", "warm8_").replace(".pkl", f"_{'_'.join(arms)}_{'_'.join(sys.argv[3:])}.json"), "w"), indent=1, default=str)
