"""Gate-level trace of ZAAD reviews (two-blocker closure, B phase 1): for every review, the state, owner,
gate basis, candidates with their period-0 orders and hedged costs, the chosen candidate, the ordinary
confirmation (incumbent / candidate rows), the declared-stress confirmation with its per-service floor
outcome, the acceptance reasons and the executed action. Read-only. P1 fixtures replay ZAAD in rolling
mode on the benchmark truth; P0 cells replay on the legacy path.

usage: PYTHONPATH=. python3 -m scripts.p1_gate_trace B_fixed_order_cost_replace_sold:41003:10 cell:20:0 ...
(third field: reviews to replay; 0 = the cell's horizon). Output: closure/gate_trace_<tag>.json"""
from __future__ import annotations

import json
import sys

import zaad.full.planner as P
import zaad.full.replay as R
from scripts.p1_fixtures import build
from zaad.full.contracts import Request
from zaad.full.evaluation import long_truth
from zaad.full.replay import replay

PRODUCT = {k: Request.model_fields[k].default for k in ("stratified_scenarios", "timing_tiebreak", "analytic_shortage")}


def main():
    for spec in sys.argv[1:]:
        parts = spec.split(":")
        name, seed, reviews = parts[0], int(parts[1]), int(parts[2])
        legacy = len(parts) > 3 and parts[3] == "legacy"      # shrinking-horizon replay on the fixture's own truth
        traces: list[dict] = []
        orig = P.plan

        def traced(r):
            P.TRACE = {}
            rep = orig(r)
            t = dict(P.TRACE)
            P.TRACE = None
            orch = rep.get("orchestration") or {}
            t = {"state": t.get("state"), "chosen": t.get("chosen"), "feasible": t.get("feasible"), "recovery_mode": t.get("recovery_mode"),
                 "candidates": {n: {"status": c["status"], "p0": c["p0_purchases"], "hedged_cost": c.get("hedged_cost"), "feasible": c.get("feasible"), "burden": c.get("burden")} for n, c in (t.get("candidates") or {}).items()},
                 "owner": orch.get("planner_owner"), "ownership_reasons": orch.get("ownership_reasons"), "ownership_notes": orch.get("ownership_notes"),
                 "gate_basis": orch.get("gate_basis"), "floor_waived": orch.get("confirmation_floor_waived"), "status": rep.get("status"), "selected_policy": rep.get("selected_policy"), "reasons": rep.get("reasons"),
                 "stresses": [s.model_dump() for s in r.stresses],
                 "protection": [{"sku": p["sku"], "regime": p["state"]["regime"], "activity": p["state"]["activity"], "flags": p["state"]["flags"], "decaying": p["state"]["decaying"]} for p in rep["protection"]],
                 "confirmation": rep.get("confirmation"), "stress_confirmation": rep.get("stress_confirmation"), "blocking": rep.get("blocking"),
                 "on_hand": sum(x.usable for x in r.stock), "incumbent_orders": [(o.source, o.period, round(o.quantity, 1)) for o in r.incumbent_orders]}
            traces.append(t)
            return rep

        P.plan = traced
        R.plan = traced
        try:
            if name == "cell":
                import scripts.run_zaad_full_benchmark as B
                cell = next(c for c in B.cells("v7") if c["cell"] == seed)
                req = B.request_for(cell, 38001).model_copy(update={"adaptive_escalation": True, "adaptive_solve_budget": True, "joint_recovery_rule": "deficit"})
                truth = B.truth_for(req, cell, 38001)
                out = replay(req, truth, reviews or cell["horizon"], "gated")
                tag = f"cell{seed}"
            elif legacy:
                from zaad.full.worlds import draw
                req = build(name, seed).model_copy(update=PRODUCT)
                out = replay(req, draw(req, seed + 10000, 1)[0], reviews, "gated")
                tag = f"{name}_{seed}_legacy"
            else:
                req = build(name, seed).model_copy(update=PRODUCT)
                truth = long_truth(req, seed + 10000, 12 * (-(-(reviews - 1 + 12) // 12)))
                out = replay(req, truth, reviews, "gated", rolling=True)
                tag = f"{name}_{seed}"
        finally:
            P.plan = orig
            R.plan = orig
        for t, row in zip(traces, out.get("reviews", [])):
            t["executed"] = [(p["source"], round(p["quantity"], 1)) for p in row["purchases"]]
            t["end_stock"] = sum(x["quantity"] for x in row["settlement"]["end_stock"])
        json.dump({"name": name, "seed": seed, "status": out["status"], "reviews": traces}, open(f"docs/zaad_full/evidence/p1/closure/gate_trace_{tag}.json", "w"), indent=1, default=str)
        print(f"{tag}: {out['status']} reviews {len(traces)}")
        for i, t in enumerate(traces):
            sc = t.get("stress_confirmation") or []
            gate = "; ".join(f"{x['stress']['name']}:{'pass' if x['pass'] else 'REJECT'}({x.get('gate_mode')},phys={x.get('physically_usable')},down={x.get('within_downside')},svc={x.get('service_met')})" for x in sc)
            print(f"  r{i:2d} {t['owner'][:4] if t['owner'] else '-'} {t['state']:22s} basis {t['gate_basis']} waived {t.get('floor_waived')} chosen {str(t['chosen']):22s} status {t['status']:16s} executed {t['executed']} | stress {gate} | reasons {[x[:60] for x in (t['reasons'] or [])][:2]}")


if __name__ == "__main__":
    main()
