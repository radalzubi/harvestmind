"""Cell 90 review-level trace (P1 diagnostic pass, objective 1).
usage: PYTHONPATH=. python3 -m scripts.p1_cell90_trace <arm>   (arm from scripts.p1_p0_arms.ARMS)
Writes docs/zaad_full/evidence/p1/closure/cell90_trace_<arm>.json: per review the screen state,
scenario worlds (demand path and weight), every candidate's period-0 order, per-world service and
cost, selector statistic, exposure, burden, feasibility, band outcome, the chosen and accepted
plan, and the settlement of that review (arrivals, unmet, ending inventory)."""
from __future__ import annotations
import json, sys
sys.path.insert(0, "scripts")
import run_zaad_full_benchmark as B  # noqa: E402
import zaad.full.planner as P  # noqa: E402
import zaad.full.replay as R  # noqa: E402
from zaad.full.replay import replay  # noqa: E402
from scripts.p1_p0_arms import ARMS  # noqa: E402

arm = sys.argv[1]
CELL = int(sys.argv[2]) if len(sys.argv) > 2 else 90
settings = dict(ARMS[arm]); switch = settings.pop("_switch", None)
if switch is not None:
    import zaad.full.worlds as W
    module, name = switch[0].split("."); setattr({"planner": P, "worlds": W}[module], name, switch[1])
cell = next(c for c in B.cells("v7") if c["cell"] == CELL)
req = B.request_for(cell, 38001).model_copy(update={"adaptive_escalation": True, "adaptive_solve_budget": True, "joint_recovery_rule": "deficit", **settings})
truth = B.truth_for(req, cell, 38001)
traces = []
orig = P.plan
def traced(r):
    P.TRACE = {}
    rep = orig(r)
    t = dict(P.TRACE); P.TRACE = None
    t["on_hand"] = sum(x.usable for x in r.stock)
    t["pipeline"] = [(p.id, p.expected_accepted_remaining, next(o.due_in for o in p.options if o.action == "keep")) for p in r.pipeline]
    t["protection"] = [{"regime": row["state"]["regime"], "activity": row["state"]["activity"], "protection_units": row["protection_units"], "lean": row["state"]["lean_baseline_units"]} for row in rep["protection"]]
    t["orchestration"] = {k: rep["orchestration"].get(k) for k in ("planner_owner", "ownership_reasons", "p1_classes_added", "candidate_classes_requested", "candidates_built", "reasons")}
    t["selected_policy"] = rep.get("selected_policy")
    t["risk_drivers"] = [{"sku": row["sku"], "location": row["location"], "drivers": row["state"].get("active_drivers"), "flags": row["state"].get("flags"), "regime": row["state"]["regime"]} for row in rep["protection"]]
    t["economics_orders"] = [{"q": o["quantity"], "attribution": o["attribution"], "need": o["economic_need"]} for o in rep["economics"]["orders"]]
    traces.append(t)
    return rep
P.plan = traced; R.plan = traced
res = replay(req, truth, cell["horizon"], "gated")
P.plan = orig; R.plan = orig
for t, r in zip(traces, res["reviews"]):
    st = r["settlement"]
    t["settlement"] = {"unmet": sum(x["demand"] - x["served"] for x in st["service_by_period"]), "demand": sum(x["demand"] for x in st["service_by_period"]),
                       "end_stock": sum(x["quantity"] for x in st["end_stock"]), "received": st.get("received_units"), "cost": st["economic_cost"]}
    t["truth_demand"] = None
json.dump({"arm": arm, "cell": CELL, "reviews": traces, "economic_cost": res["economic_cost"]}, open(f"docs/zaad_full/evidence/p1/closure/cell{CELL}_trace_{arm}.json" if CELL != 90 else f"docs/zaad_full/evidence/p1/closure/cell90_trace_{arm}.json", "w"), indent=1, default=float)
print(arm, "reviews", len(traces), "cost", round(res["economic_cost"]))
