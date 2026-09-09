"""Stage 4 on the frozen P0 cells: common valuation of every generated candidate at every review, product defaults."""
from __future__ import annotations
import json, sys, time
sys.path.insert(0, "scripts")
import run_zaad_full_benchmark as B  # noqa: E402
import zaad.full.planner as P  # noqa: E402
import zaad.full.replay as R  # noqa: E402
from zaad.full.model import Solution  # noqa: E402
from zaad.full.replay import replay  # noqa: E402
from zaad.full.settlement import PhysicalViolation  # noqa: E402
from zaad.full.valuation import common_candidate_value  # noqa: E402
from zaad.full.worlds import forecast_all  # noqa: E402

def run(cid):
    cell = next(c for c in B.cells("v7") if c["cell"] == cid)
    req0 = B.request_for(cell, 38001).model_copy(update={"adaptive_escalation": True, "adaptive_solve_budget": True, "joint_recovery_rule": "deficit"})
    truth = B.truth_for(req0, cell, 38001)
    traces, kept = [], []
    orig = P.plan
    def traced(r):
        P.TRACE = {}; rep = orig(r); t = dict(P.TRACE); P.TRACE = None; traces.append(t); return rep
    P.plan = traced; R.plan = traced
    replay(req0, truth, cell["horizon"], "gated", keep_requests=kept)
    P.plan = orig; R.plan = orig
    rows = []
    for i, (t, req) in enumerate(zip(traces, kept)):
        fits = forecast_all(req); cands = {}
        for name, c in t["candidates"].items():
            if c["status"] not in ("OPTIMAL", "FEASIBLE_TIME_LIMIT"):
                continue
            purchases = {(k.rsplit(":", 1)[0], int(k.rsplit(":", 1)[1])): q for k, q in c["purchases"].items()}
            sol = Solution("OPTIMAL", purchases, {}, {}, {}, None, [], 0., 0, 0, None, 0., [])
            for po in req.pipeline:
                sol.amendments[(po.id, next(o.id for o in po.options if o.action == "keep"))] = po.remaining
            try:
                v = common_candidate_value(req, sol, fits); total = v["total"]; es = v["components"]["expected_shortage_units"]
            except PhysicalViolation as exc:
                total, es = None, None
            cands[name] = {"p0": round(sum(c["p0_purchases"].values()), 3), "sampled_cost": c["hedged_cost"], "feasible": c["feasible"], "common": total, "expected_shortage_units": es, "burden": c["burden"]}
        feas = [n for n in cands if cands[n]["feasible"] and cands[n]["common"] is not None]
        best = min(feas, key=lambda n: cands[n]["common"]) if feas else None
        rows.append({"cell": cid, "review": i, "state": t["state"], "recovery_mode": t["recovery_mode"], "chosen": t["chosen"], "status": t["status"], "common_best": best, "candidates": cands,
                     "agree": (best == t["chosen"]) if best else None,
                     "gap": (cands[t["chosen"]]["common"] - cands[best]["common"]) if (best and t["chosen"] in cands and cands[t["chosen"]]["common"] is not None) else None})
    return rows

if __name__ == "__main__":
    cells = [int(x) for x in sys.argv[1:]] or [15, 20, 21, 90, 108]
    out = []
    for cid in cells:
        rows = run(cid); out += rows
        dis = [r for r in rows if r["agree"] is False]
        print(f"cell {cid}: reviews {len(rows)}, common valuation disagrees with the selector on {len(dis)} (material > $10: {sum(1 for r in dis if (r['gap'] or 0) > 10)}); states of disagreements {sorted({r['state'] for r in dis})}", flush=True)
        for r in dis:
            c = r["candidates"]
            print(f"   r{r['review']:2d} {r['state'][:12]:12s} rec {r['recovery_mode']} chosen {r['chosen'][:16]:16s} {r['status'][:6]} common best {r['common_best'][:16]:16s} gap ${r['gap']:.1f} | " + " ".join(f"{n[:5]}:{c[n]['p0']:.0f}/{round(c[n]['common']) if c[n]['common'] else None}" for n in c), flush=True)
    json.dump(out, open("docs/zaad_full/evidence/p1/closure/common_valuation_diag_p0.json", "w"), indent=1, default=float)
    print("P0-DIAG-DONE")
