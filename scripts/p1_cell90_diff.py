"""First-divergence table between two cell-90 traces (objective 1).
usage: PYTHONPATH=. python3 -m scripts.p1_cell90_diff p0_defaults representation_only"""
from __future__ import annotations
import json, sys
P = "docs/zaad_full/evidence/p1/closure"
a_name, b_name = sys.argv[1], sys.argv[2]
CELL = sys.argv[3] if len(sys.argv) > 3 else "90"
A = json.load(open(f"{P}/cell{CELL}_trace_{a_name}.json")); B = json.load(open(f"{P}/cell{CELL}_trace_{b_name}.json"))
print(f"A={a_name} cost {A['economic_cost']:.0f} | B={b_name} cost {B['economic_cost']:.0f}")
first = None
for i, (x, y) in enumerate(zip(A["reviews"], B["reviews"])):
    same = (x["chosen"] == y["chosen"] and x["status"] == y["status"]
            and {k: round(v, 3) for k, v in x["final_p0_purchases"].items()} == {k: round(v, 3) for k, v in y["final_p0_purchases"].items()})
    diverged = not same
    if diverged and first is None:
        first = i
    flag = "<<< FIRST DIVERGENCE" if i == first else ("  divergent" if diverged else "")
    print(f"r{i:2d} state A {x['state'][:12]:12s} B {y['state'][:12]:12s} lean B {str(y['lean_review'])[:1]} | chosen A {x['chosen'][:18]:18s} B {y['chosen'][:18]:18s} | status A {x['status'][:6]} B {y['status'][:6]} "
          f"| p0 order A {round(sum(x['final_p0_purchases'].values()))} B {round(sum(y['final_p0_purchases'].values()))} | hand {x['on_hand']:.0f}/{y['on_hand']:.0f} "
          f"| unmet {x['settlement']['unmet']:.1f}/{y['settlement']['unmet']:.1f} end {x['settlement']['end_stock']:.0f}/{y['settlement']['end_stock']:.0f} {flag}")
if first is None:
    print("no divergence in chosen/status/period-0 order"); sys.exit()
for label, t in (("A", A["reviews"][first]), ("B", B["reviews"][first])):
    print(f"\n=== {label} at review {first}: state {t['state']} lean_review {t['lean_review']} lean_profile {t['lean_profile']} recovery_mode {t['recovery_mode']}")
    print("  on hand", round(t["on_hand"]), "pipeline", [(p[0][:14], round(p[1]), p[2]) for p in t["pipeline"]], "protection", t["protection"])
    for w in t["worlds"]:
        d = list(w["demand"].values())[0]
        print(f"  world {w['name'][-10:]:10s} weight {w['weight']:.3f} demand[0:8] {[round(v) for v in d[:8]]} sum {sum(d):.0f} fills {list(w['fills'].values())[:3]} arrival {list(w['arrival'].values())[:3]}")
    print("  feasible", t["feasible"], "chosen", t["chosen"], "accepted", t["accepted"], "status", t["status"])
    for name, c in t["candidates"].items():
        print(f"  cand {name[:22]:22s} {c['status'][:8]:8s} p0 {round(sum(c['p0_purchases'].values()))} svc_stat {c['service_stat'] if c['service_stat'] is None else round(c['service_stat'],3)} svc_by_world {[None if v is None else round(v,3) for v in c['service_by_world']]} "
              f"cost {None if c['hedged_cost'] is None else round(c['hedged_cost'])} exposure {None if c['exposure'] is None else round(c['exposure'],1)} burden {None if c['burden'] is None else round(c['burden'])} feasible {c['feasible']} well_solved {c['well_solved']}")
    print("  gates", t["candidate_gates"], "reasons", [r[:90] for r in t["reasons"]])
    print("  final p0 purchases", {k: round(v) for k, v in t["final_p0_purchases"].items()}, "orders", [(round(o["q"]), round(o["need"] or 0), {k: round(v) for k, v in o["attribution"].items() if v > .5}) for o in t["economics_orders"]])
    print("  settlement", {k: (round(v, 1) if isinstance(v, float) else v) for k, v in t["settlement"].items()})
