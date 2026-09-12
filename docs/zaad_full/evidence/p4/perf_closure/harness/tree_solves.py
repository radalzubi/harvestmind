"""Replay the planner's three tree solves (static comparator / adaptive / perfect information) of one cell with HiGHS
logs, then try warm-start variants. Usage: tree_solves.py <class> <histories> <e1[,e2]> <cont> <out.json> [variants]"""
import json, sys, time, pathlib
sys.path.insert(0, ".")
import scripts.p4_perf_profile as PP          # instruments Linear.solve / _highspy_solve (log capture)
import zaad.full.planner as P
from zaad.full.model import solve as model_solve
from zaad.full.contracts import Request
from zaad.recourse.fixtures import with_recourse

cls, h, epochs, cont, out = sys.argv[1], int(sys.argv[2]), [int(x) for x in sys.argv[3].split(",")], int(sys.argv[4]), sys.argv[5]
variants = sys.argv[6].split(",") if len(sys.argv) > 6 else ["baseline", "warm_static_to_adaptive", "warm_adaptive_to_pi"]
base = PP.CLASSES[cls]()
req = with_recourse(base, review_periods=epochs, observables=["demand", "receipts"], continuations=cont)
req = Request.model_validate(req.model_copy(update={"scenarios": min(h, 4)}).model_dump())
import pickle, os
cache = out.replace(".json", ".captured.pkl")
captured = []
_solve = P.solve
def spy(req_, worlds, **kw):
    if kw.get("nodes") is not None or ("seed" in kw and len(worlds) >= 6):
        captured.append((worlds, dict(kw)))
    return _solve(req_, worlds, **kw)
if os.path.exists(cache):
    captured, plan_wall, verdict = pickle.load(open(cache, "rb"))
    print("captured tree solves loaded from cache; plan wall (earlier run)", plan_wall, verdict, flush=True)
else:
    P.solve = spy
    PP.ctx["capture"] = False
    t = time.perf_counter(); rep = P.plan(req); plan_wall = time.perf_counter() - t
    P.solve = _solve
    verdict = rep["recourse"]["verdict"]
    pickle.dump((captured, plan_wall, verdict), open(cache, "wb"))
    print("plan wall", round(plan_wall, 1), "verdict", verdict, "captured", len(captured), flush=True)
static_kw = next(kw for w, kw in captured if kw.get("nodes") is None)
adapt_kw = next(kw for w, kw in captured if kw.get("nodes") is not None and not kw["nodes"].perfect)
pi_kw = next((kw for w, kw in captured if kw.get("nodes") is not None and kw["nodes"].perfect), None)
tree = captured[0][0]
logdir = pathlib.Path(PP.LOGS) / f"replay_{cls}_h{h}_e{'-'.join(map(str, epochs))}_c{cont}"; logdir.mkdir(parents=True, exist_ok=True)
PP.ctx["log_dir"] = logdir; PP.ctx["capture"] = True
results = {"cell": {"class": cls, "histories": h, "epochs": epochs, "continuations": cont, "worlds": len(tree)}, "plan_wall": round(plan_wall, 1), "variants": {}}
import numpy as np
from zaad.full.model import Linear, activation_bounds
TIGHT = {"on": False, "M": None, "rewritten": 0}
_lsolve_orig = Linear.solve
def lsolve_tight(self, seconds, objective=None, solver="highs", mip_gap=1e-6, seed=None, options=None):
    if TIGHT["on"] and TIGHT["M"] is not None:
        M = TIGHT["M"]; n = 0
        for r, (terms, hi) in enumerate(zip(self.rows, self.hi)):
            for col, coef in terms.items():
                name = self.names[col]
                if isinstance(name, tuple) and name[0] in ("depleted", "fefo", "priority", "direct_first") and coef > M and abs(coef - hi) < 1e-6:
                    terms[col] = M; self.hi[r] = M; n += 1
        TIGHT["rewritten"] = n
    return _lsolve_orig(self, seconds, objective, solver, mip_gap, seed, options)
Linear.solve = lsolve_tight
def system_bound(req, worlds):
    tight = activation_bounds(req, worlds)
    opening = sum(st.quantity for st in req.stock) + sum(i.accepted_quantity for i in req.inbound_transfers) + sum(p.expected_accepted_remaining for p in req.pipeline)
    return opening + sum(tight.values())
def run(label, kw, seed=None):
    PP.ctx["calls"] = []; PP.ctx["label"] = label
    kw = dict(kw)
    if seed is not None:
        kw["seed"] = seed
    TIGHT["on"] = label.startswith("tightM")
    if TIGHT["on"] and TIGHT["M"] is None:
        TIGHT["M"] = system_bound(req, tree); print("system-wide undominated stock bound M =", round(TIGHT["M"], 1), flush=True)
    t = time.perf_counter(); sol = model_solve(req, tree, **kw); dt = time.perf_counter() - t
    calls = [c for c in PP.ctx["calls"] if c["kind"] == "solve"]
    c = calls[-1] if calls else {}
    view = {"status": sol.status, "objective": sol.projected_cost, "wall": round(dt, 2), "solve_seconds": round(sol.solve_seconds, 2), "nodes": sol.nodes, "gap": sol.gap, "bound": sol.best_bound,
            "rows": c.get("rows"), "cols": c.get("cols"), "binary": c.get("binary"), "first_incumbent_s": c.get("log_parsed", {}).get("first_incumbent_s"), "lp_iterations": c.get("log_parsed", {}).get("lp_iterations"),
            "timing_total": c.get("log_parsed", {}).get("timing_total_s"), "warm": sol.warm_start, "rows_rewritten": TIGHT["rewritten"] if TIGHT["on"] else 0, "all_calls": [{k: x.get(k) for k in ("kind", "solve_wall_s", "status", "bb_nodes", "seeded")} for x in PP.ctx["calls"]]}
    print(label, json.dumps({k: v for k, v in view.items() if k not in ("all_calls", "warm")}, default=str), "| warm:", (sol.warm_start or {}).get("outcome"), flush=True)
    results["variants"][label] = view
    return sol
sols = {}
if "baseline" in variants:
    sols["static"] = run("static_baseline", static_kw)
    sols["adaptive"] = run("adaptive_baseline", adapt_kw)
    if pi_kw is not None:
        sols["pi"] = run("pi_baseline", pi_kw)
if "warm_static_to_adaptive" in variants:
    st = sols.get("static") or run("static_for_seed", static_kw)
    run("adaptive_warm_from_static", {k: v for k, v in adapt_kw.items() if k != "seed"}, seed=st)
if "warm_adaptive_to_pi" in variants and pi_kw is not None:
    ad = sols.get("adaptive") or run("adaptive_for_seed", adapt_kw)
    run("pi_warm_from_adaptive", {k: v for k, v in pi_kw.items() if k != "seed"}, seed=ad)
if "tightM" in variants:
    st = run("tightM_static", static_kw)
    run("tightM_adaptive", adapt_kw)
    ad2 = run("tightM_adaptive_warm", {k: v for k, v in adapt_kw.items() if k != "seed"}, seed=st)
    if pi_kw is not None:
        run("tightM_pi", pi_kw)
        run("tightM_pi_warm", {k: v for k, v in pi_kw.items() if k != "seed"}, seed=ad2)
json.dump(results, open(out, "w"), indent=1, default=str)
print("REPLAY_DONE")
