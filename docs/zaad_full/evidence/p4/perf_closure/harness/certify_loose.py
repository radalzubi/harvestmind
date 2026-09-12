"""Certify the optima of the LOOSE (as-released) produce tree models with a long budget, to check the tightened-M objectives."""
import json, pickle, sys, time
sys.path.insert(0, ".")
import zaad.full.model as M
from zaad.full.contracts import Request
from zaad.recourse.fixtures import sector_base, with_recourse
M.solve_budget = lambda req: 900.
captured, _, _ = pickle.load(open(sys.argv[1], "rb"))
req = with_recourse(sector_base("P2_near_expiry_inventory"), review_periods=[3, 6], observables=["demand", "receipts"], continuations=2)
req = Request.model_validate(req.model_copy(update={"scenarios": 3}).model_dump())
tree = captured[0][0]
static_kw = next(kw for w, kw in captured if kw.get("nodes") is None)
adapt_kw = next(kw for w, kw in captured if kw.get("nodes") is not None and not kw["nodes"].perfect)
out = {}
for label, kw in (("static_loose_900s", {k: v for k, v in static_kw.items() if k != "seed"}), ("adaptive_loose_900s", adapt_kw)):
    t = time.perf_counter(); sol = M.solve(req, tree, **kw); dt = time.perf_counter() - t
    out[label] = {"status": sol.status, "objective": sol.projected_cost, "wall": round(dt, 1), "nodes": sol.nodes, "gap": sol.gap}
    print(label, out[label], flush=True)
json.dump(out, open(sys.argv[2], "w"), indent=1)
print("CERTIFY_DONE")
