"""Pickle the per-review Request objects of one cell/arm replay so single reviews can be re-solved.
usage: capture8.py <cell> <arm>"""
import sys, pickle
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import run_zaad_full_benchmark as B
import zaad.full.planner as P
import zaad.full.replay as R
from zaad.full.replay import replay
cid, arm = int(sys.argv[1]), sys.argv[2]
cell = next(c for c in B.cells("v7") if c["cell"] == cid)
req = B.request_for(cell, 38001).model_copy(update={"adaptive_escalation": arm != "V7_full", "adaptive_solve_budget": True})
truth = B.truth_for(req, cell, 38001)
reqs = []
orig = P.plan
def cap(r):
    reqs.append(r.model_copy(deep=True)); return orig(r)
P.plan = cap; R.plan = cap
replay(req, truth, cell["horizon"], "gated")
out = f"/private/tmp/claude-501/-Users-radalzubi-Desktop-harvestmind/ff795fbd-41f4-4af5-afd4-b87ad517d896/scratchpad/reqs_{cid}_{arm}.pkl"
pickle.dump(reqs, open(out, "wb"))
print(f"captured {len(reqs)} review requests -> {out}")
