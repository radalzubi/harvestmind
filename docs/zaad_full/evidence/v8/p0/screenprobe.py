"""Per-review screen inputs: protection rows (drivers, regime, cover) and the incumbent verdict.
usage: screenprobe.py <cell> [arm]"""
import sys, json
sys.path.insert(0, "scripts"); sys.path.insert(0, ".")
import run_zaad_full_benchmark as B
import zaad.full.planner as P
import zaad.full.replay as R
from zaad.full.replay import replay
cid = int(sys.argv[1]); arm = sys.argv[2] if len(sys.argv) > 2 else "V8_escalated"
cell = next(c for c in B.cells("v7") if c["cell"] == cid)
req = B.request_for(cell, 38001).model_copy(update={"adaptive_escalation": arm != "V7_full", "adaptive_solve_budget": True})
truth = B.truth_for(req, cell, 38001)
log = []
orig_screen = P.screen
def probe(req_, fits, protection, incumbent_rows):
    out = orig_screen(req_, fits, protection, incumbent_rows)
    rows = []
    for r in protection:
        st = r["state"]
        rows.append({"sku": r["sku"], "location": r["location"], "on_hand": r["on_hand_units"], "mu": r["mean_demand_per_period"], "window": r.get("replenishment_periods"),
                     "activity": st["activity"], "supply": st["supply_score"], "demand": st["demand_score"], "regime": st["regime"],
                     "drivers": [d["driver"] for d in st["active_drivers"]], "flags": st.get("flags"),
                     "remaining_until_lean": st.get("reviews_remaining_until_lean_eligible"), "recovery_receipts": st.get("recovery_evidence_receipts"),
                     "lean_base": st.get("lean_base_stock_units"), "lean_baseline": st.get("lean_baseline_units")})
    log.append({"state": out["state"], "incumbent_ok": out["incumbent_feasible_and_meeting_service"], "rows": rows,
                "inc_service": ({s.id: P._service_value(req_, incumbent_rows, s) for s in req_.services} if incumbent_rows else None)})
    return out
P.screen = probe
orig_plan = P.plan
def plan(r):
    rep = orig_plan(r); log[-1]["selected"] = rep.get("selected_policy"); log[-1]["joint_built"] = "joint_recovery" in rep["orchestration"]["candidates_built"]; return rep
P.plan = plan; R.plan = plan
res = replay(req, truth, cell["horizon"], "gated")
for i, (l, rv) in enumerate(zip(log, res.get("reviews") or [])):
    d = sum(x["demand"] for x in rv["settlement"]["service_by_period"]); sv = sum(x["served"] for x in rv["settlement"]["service_by_period"])
    l["service"] = sv / d if d else None; l["unmet"] = d - sv
out = f"/private/tmp/claude-501/-Users-radalzubi-Desktop-harvestmind/ff795fbd-41f4-4af5-afd4-b87ad517d896/scratchpad/screen8_{cid}_{arm}.json"
json.dump(log, open(out, "w"), indent=1, default=str)
print(f"cell {cid} {arm}: {len(log)} reviews -> {out}")
for i, l in enumerate(log):
    worst = min(l["rows"], key=lambda r: (r["on_hand"] / r["mu"]) if r["mu"] else 9e9)
    drivers = sorted({d for r in l["rows"] for d in r["drivers"]})
    print(f"  r{i:02d} {l['state'][:8]:8s} inc_ok={l['incumbent_ok']} inc_svc={ {k: round(v,2) for k,v in (l['inc_service'] or {}).items()} } drivers={drivers} sup={max(r['supply'] for r in l['rows']):.2f} dem={max(r['demand'] for r in l['rows']):.2f} act={max(r['activity'] for r in l['rows']):.2f} regimes={sorted({r['regime'] for r in l['rows']})} rem_lean={max((r['remaining_until_lean'] or 0) for r in l['rows'])} cover={worst['on_hand']/worst['mu'] if worst['mu'] else None:.1f}p sel={l.get('selected')} joint={l.get('joint_built')} svc={l.get('service')} unmet={l.get('unmet')}")
