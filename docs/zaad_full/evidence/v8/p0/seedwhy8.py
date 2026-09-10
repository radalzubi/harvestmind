"""Why is the incumbent seed infeasible for a candidate? Try pinning subsets of its controls.
usage: seedwhy8.py <reqs.pkl> <review> [review...]"""
import sys, pickle, time
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import zaad.full.model as M
import zaad.full.planner as P
from zaad.full.contracts import Request
reqs = pickle.load(open(sys.argv[1], "rb"))
orig = M.warm_start_vector
def probe(m, seed, seconds):
    groups = {"purchase": {}, "amend": {}, "transfer": {}}
    for i, name in enumerate(m.names):
        k = name[0]
        if k == "purchase": groups[k][i] = seed.purchases.get((name[1], name[2]), 0.)
        elif k == "amend": groups[k][i] = seed.amendments.get((name[1], name[2]), 0.)
        elif k == "transfer": groups[k][i] = seed.transfers.get((name[1], name[2], name[3]), 0.)
    nz = {k: sum(1 for v in g.values() if abs(v) > 1e-9) for k, g in groups.items()}
    line = [f"    [seed probe] vars={len(m.names)} controls purchase={len(groups['purchase'])}({nz['purchase']} nonzero) amend={len(groups['amend'])}({nz['amend']}) transfer={len(groups['transfer'])}({nz['transfer']})"]
    for label, keys in (("all", ("purchase", "amend", "transfer")), ("purchase+transfer", ("purchase", "transfer")), ("purchase", ("purchase",)), ("nonzero purchases only", ("purchase",))):
        controls = {}
        for k in keys:
            for i, v in groups[k].items():
                if label.startswith("nonzero") and abs(v) < 1e-9: continue
                controls[i] = 0. if abs(v) < 1e-9 else float(v)
        t0 = time.perf_counter(); done = m.complete(controls, 10.); dt = time.perf_counter() - t0
        line.append(f"      pin {label:24s} n={len(controls):5d} -> {'ACCEPTED' if done['accepted'] else 'rejected'} ({done['completion_status'].replace('highspy HighsModelStatus.','')}, {dt:.1f}s)")
    print("\n".join(line), flush=True)
    return orig(m, seed, seconds)
M.warm_start_vector = probe
for arg in sys.argv[2:]:
    req = Request.model_validate(reqs[int(arg)].model_dump()).model_copy(update={"joint_recovery_rule": "deficit", "adaptive_solve_budget": True, "warm_start": True, "max_solve_seconds": 1.0, "adaptive_solve_budget": False})
    print(f"=== review {arg} (main solves capped at 1 s; only the completion probes matter here)", flush=True)
    rep = P.plan(req)
    print("    outcomes:", {n: v["outcome"] for n, v in rep["orchestration"]["outcomes"].items()}, flush=True)
