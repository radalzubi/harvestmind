"""P3 shared-MOV production snapshot under the P4B release-audit tree: no option declared -> the decision record must be
identical to the P4B implementation gate record (itself identical to the P4 closure record), timing / hashes stripped,
no `commitments` key. Planned through zaad.meio.planner.plan_network as the prior gate was; HiGHS calls counted at the highspy.Highs constructor. usage: PYTHONPATH=. python3 <this file>"""
import json, re, time
from pathlib import Path
from zaad.full.contracts import Request
import zaad.full.planner as planner
import zaad.meio.planner as meio

PRIOR = Path("docs/zaad_full/evidence/p4b/release_audit/gates/p3_snapshot_under_p4brel.json")
OUT = Path("docs/zaad_full/evidence/cleanup/gates/p3_snapshot_under_cleanup.json")
TIME = re.compile(r"(seconds|_s$|^wall$|generated_at|hash|fingerprint|elapsed|timestamp)")

def strip(x):
    if isinstance(x, dict):
        return {k: strip(v) for k, v in x.items() if not TIME.search(k)}
    if isinstance(x, list):
        return [strip(v) for v in x]
    return x

prior = json.load(open(PRIOR))
req = Request.model_validate(json.load(open(prior["snapshot"])))
calls = {"n": 0}
import highspy                          # the model imports highspy inside its solve; the constructor is patched on the module
RealHighs = highspy.Highs
class CountedHighs(RealHighs):          # one HiGHS instance per solve call, as the prior gate counted
    def __init__(self, *a, **k):
        calls["n"] += 1
        super().__init__(*a, **k)
highspy.Highs = CountedHighs
t = time.perf_counter()
rep = json.loads(json.dumps(meio.plan_network(req), default=str))   # the prior gate planned through the network planner
wall = round(time.perf_counter() - t, 2)
highspy.Highs = RealHighs
same = strip(rep) == strip(prior["report"])
diff = []
if not same:
    a, b = strip(rep), strip(prior["report"])
    diff = [k for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)][:12]
res = {"snapshot": prior["snapshot"], "wall_s": wall, "n_highs_calls": calls["n"], "prior_n_highs_calls": prior.get("n_highs_calls"), "report_identical_to_prior_gate": same,
       "differing_keys": diff, "commitments_key_absent": "commitments" not in rep, "status": rep["status"], "selected_policy": rep["selected_policy"], "report": rep}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(res, indent=1, default=str))
print(json.dumps({k: v for k, v in res.items() if k != "report"}))
print("P3_SNAPSHOT", "PASS" if same and res["commitments_key_absent"] else "FAIL")
