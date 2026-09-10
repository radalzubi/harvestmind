"""Development diagnostic: why the frozen selector retained the incumbent on fixture H's mid-window
reviews. Replays ZAAD on H keeping every snapshot, then plans the third and fourth snapshots and prints
the selector's reasons and gates. Development evidence only."""
from __future__ import annotations
import json
from scripts.p2_fixtures import build
from zaad.full.evaluation import long_truth
from zaad.full.replay import replay
from zaad.meio.planner import plan_network

req = build("H_one_branch_demand_shock", 41001)
truth = long_truth(req, 41001 + 10000, 24)
kept: list = []
replay(req, truth, 5, "gated", keep_requests=kept, rolling=True)
for i in (3, 4):
    rep = plan_network(kept[i])
    o = rep["orchestration"]
    print(json.dumps({"review": i, "status": rep["status"], "selected": rep["selected_policy"], "state": o["state"], "owner": o["planner_owner"],
                      "reasons": rep["reasons"], "gates": {k: v.get("reason") for k, v in rep["candidate_gates"].items()},
                      "feasible_time_limited": o.get("milps_feasible_time_limited"), "no_feasible": o.get("milps_no_feasible_solution"),
                      "stress_targets_feasible": rep.get("stress_targets_feasible"), "recovery_mode": rep["joint_service_feasibility"]["recovery_mode"],
                      "incumbent_service": {k: v for k, v in rep["confirmation"]["incumbent"].items() if "service" in k or "cost" in k},
                      "candidate_service": {k: v for k, v in rep["confirmation"]["candidate"].items() if "service" in k or "cost" in k},
                      "network_service": [(r["location"], r["incumbent_achieved"], r["selected_achieved"]) for r in rep["network_service"]],
                      "explain": rep["network"]["explanations"]["verdict"]}, indent=1, default=str))
