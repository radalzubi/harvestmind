"""Does the add-only (floor) repair give the floored classes a feasible start? Completion-only probe.
usage: seedfloor8.py <reqs.pkl> <seconds> <review...>"""
import sys, pickle, time
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import zaad.full.model as M
import zaad.full.planner as P
from zaad.full.contracts import Request
reqs = pickle.load(open(sys.argv[1], "rb")); secs = float(sys.argv[2])
orig = M.warm_start_vector
def probe(m, seed, seconds):
    ctl = {i: seed.purchases.get((n[1], n[2]), 0.) for i, n in enumerate(m.names) if n[0] == "purchase"}
    nz = {i: v for i, v in ctl.items() if v > 0}
    t0 = time.perf_counter(); eq = m.complete(ctl, secs); t1 = time.perf_counter(); fl = m.complete(nz, secs, mode="floor"); t2 = time.perf_counter()
    print(f"    vars={len(m.names):5d} equal:{'ACCEPTED' if eq['accepted'] else 'rejected'}({eq['completion_status'].replace('highspy HighsModelStatus.','')},{t1-t0:.1f}s)  floor:{'ACCEPTED' if fl['accepted'] else 'rejected'}({fl['completion_status'].replace('highspy HighsModelStatus.','')},{t2-t1:.1f}s)", flush=True)
    return {"supplied": True, "accepted": False, "reason": "probe", "completion_seconds": 0., "completion_status": "probe"}, None
M.warm_start_vector = probe
for arg in sys.argv[3:]:
    req = Request.model_validate(reqs[int(arg)].model_dump()).model_copy(update={"joint_recovery_rule": "deficit", "warm_start": True, "max_solve_seconds": 1.0, "adaptive_solve_budget": False})
    print(f"=== review {arg}: candidates in build order stochastic, cvar, protected, hedged, stress, joint(s)", flush=True)
    P.plan(req)
