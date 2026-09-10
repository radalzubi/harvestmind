"""P0-D1: re-plan one captured review with the solver instrumented, and for every FEASIBLE_TIME_LIMIT
candidate compare the raw incumbent against physical settlement.
usage: ftlprobe.py <reqs.pkl> <review> [budget_seconds ...]"""
import sys, pickle, time, json, math
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import numpy as np
import zaad.full.model as M
import zaad.full.planner as P

reqs = pickle.load(open(sys.argv[1], "rb"))
review = int(sys.argv[2])
budgets = [float(b) for b in sys.argv[3:]] or [None]
req0 = reqs[review]
records = []
orig_solve = M.Linear.solve
def instrumented(self, seconds, objective=None, solver="highs", mip_gap=1e-6):
    t0 = time.perf_counter()
    result, residual = orig_solve(self, seconds, objective, solver, mip_gap)
    rec = {"seconds_budget": seconds, "elapsed": time.perf_counter() - t0, "status": int(result.status), "message": str(result.message)[:80],
           "objective_phase": "service_first" if objective is not None else "cost", "vars": len(self.names), "rows": len(self.rows),
           "fun": None if result.x is None else float(result.fun) if result.fun is not None else None,
           "gap": getattr(result, "mip_gap", None), "bound": getattr(result, "mip_dual_bound", None), "nodes": getattr(result, "mip_node_count", None),
           "residual": None if not math.isfinite(residual) else residual}
    if result.x is not None:
        x = result.x
        ints = np.asarray(self.integer, dtype=bool)
        matrix = self._matrix() if hasattr(self, "_matrix") else None
        rec["max_integrality_violation"] = float(np.max(abs(x[ints] - np.rint(x[ints])), initial=0))
        rec["max_bound_violation"] = float(max(np.max(np.asarray(self.lower) - x, initial=0), np.max(x - np.asarray(self.upper), initial=0)))
        rec["n_fractional_ints_gt_1e-6"] = int(np.sum(abs(x[ints] - np.rint(x[ints])) > 1e-6))
        rec["n_fractional_ints_gt_1e-9"] = int(np.sum(abs(x[ints] - np.rint(x[ints])) > 1e-9))
    records.append(rec)
    return result, residual
M.Linear.solve = instrumented

for b in budgets:
    req = req0 if b is None else req0.model_copy(update={"max_solve_seconds": b, "adaptive_solve_budget": False})
    records.clear()
    t0 = time.perf_counter()
    rep = P.plan(req)
    wall = time.perf_counter() - t0
    q = rep["solve_quality"]["candidates"]; o = rep["orchestration"]
    print(f"\n=== review {review} budget={'scaled' if b is None else b}s wall={wall:.1f}s state={o['state']} selected={rep.get('selected_policy')}")
    for name, c in q.items():
        if c["status"] in ("FEASIBLE_TIME_LIMIT", "NO_FEASIBLE_SOLUTION", "INFEASIBLE") or c["physical_failures"]:
            # match the instrumented solve records by size
            recs = [r for r in records if r["vars"] == c["variables"] and r["rows"] == c["constraints"]]
            print(f"  {name:22s} status={c['status']:20s} secs={c['solve_seconds'] if c['solve_seconds'] is None else round(c['solve_seconds'],1)} gap={c['achieved_gap']} bound={c['best_bound']} nodes={c['nodes']} phys_valid={c['physically_validated']} failures={c['physical_failures']}")
            for r in recs[-2:]:
                print(f"      solve[{r['objective_phase']}] status={r['status']} elapsed={r['elapsed']:.1f}s residual={r['residual']} int_viol={r.get('max_integrality_violation')} bound_viol={r.get('max_bound_violation')} frac_ints>1e-6={r.get('n_fractional_ints_gt_1e-6')} >1e-9={r.get('n_fractional_ints_gt_1e-9')} fun={r['fun']} gap={r['gap']} nodes={r['nodes']}")
    comp = {n: (v["outcome"], v["reason"][:70]) for n, v in o["outcomes"].items() if v["outcome"] not in ("SOLVED",)}
    print("  outcomes:", comp)
