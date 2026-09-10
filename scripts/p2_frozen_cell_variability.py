"""Development evidence for the P2 P0 isolation: a wall-clock-limited P0 cell replayed on the FROZEN code
(run from the canonical `main` worktree) and compared with the recorded router_cycle arm and with the P2
arm on the decision keys, so a divergence between P2 and the record can be attributed to run-to-run
variability of time-limited solves rather than to P2. usage: PYTHONPATH=. python3 scripts/p2_frozen_cell_variability.py [cell]"""
import json
import sys
sys.path.insert(0, "scripts")
from scripts.p1_p0_arms import run_cells
KEYS = ("state", "requested", "built", "selected", "status", "recovery_mode", "feasible", "chosen")
CELL = int(sys.argv[1]) if len(sys.argv) > 1 else 21
got = run_cells("router_cycle", [CELL], write=False)[CELL]["per_review"]
ref = json.load(open("docs/zaad_full/evidence/p1/closure/p0_arm_router_cycle.json"))[str(CELL)]["per_review"]
p2 = json.load(open("/Users/radalzubi/Desktop/harvestmind-p2/docs/zaad_full/evidence/p2/p0_arm_p2_meio_run1.json"))[str(CELL)]["per_review"]
def norm(v): return {k: (round(x, 6) if isinstance(x, float) else x) for k, x in v.items()} if isinstance(v, dict) else v
def same(a, b): return all(a.get(k) == b.get(k) for k in KEYS) and norm(a.get("final_p0")) == norm(b.get("final_p0"))
print("frozen-now vs recorded reference: identical reviews", sum(same(a, b) for a, b in zip(got, ref)), "/", len(ref))
print("frozen-now vs P2 run1:            identical reviews", sum(same(a, b) for a, b in zip(got, p2)), "/", len(p2))
for i, (a, b) in enumerate(zip(got, ref)):
    if not same(a, b):
        print("  first frozen-vs-reference divergence at review", i, {k: (a.get(k), b.get(k)) for k in KEYS if a.get(k) != b.get(k)}, "final_p0", (norm(a.get("final_p0")), norm(b.get("final_p0"))))
        break
print("cost frozen-now", round(sum(r.get("cost", 0) or 0 for r in got), 1) if got and "cost" in got[0] else "n/a")
