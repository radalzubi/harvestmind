"""Fixture P forensics under product defaults (final P1 closure, sections B-D).
Writes docs/zaad_full/evidence/p1/closure/p_forensics.json."""
from __future__ import annotations
import json, sys, time
from statistics import mean
import zaad.full.planner as P
import zaad.full.replay as R
from zaad.full.contracts import Request
from zaad.full.replay import replay
from zaad.full.worlds import draw, forecast_all
from zaad.full.economics import cost_breakdown
from scripts.p1_fixtures import build, REVIEWS, SEEDS

def product_defaults(req):
    return req.model_copy(update={k: Request.model_fields[k].default for k in ("stratified_scenarios", "timing_tiebreak")})

def run_gated(seed, capture=False):
    req = product_defaults(build("P_high_opening_stock", seed)); truth = draw(req, seed + 10000, 1)[0]
    traces = []
    orig = P.plan
    def traced(r):
        P.TRACE = {}
        rep = orig(r)
        t = dict(P.TRACE); P.TRACE = None
        t["on_hand"] = sum(x.usable for x in r.stock); t["inbound"] = [(p.id[-12:], round(p.expected_accepted_remaining, 1), next(o.due_in for o in p.options if o.action == "keep")) for p in r.pipeline]
        fits = forecast_all(r); t["forecast_mean"] = fits[r.services[0].id]["mean"]; t["forecast_sd"] = fits[r.services[0].id].get("sd")
        t["solve_quality"] = {k: (v["status"], v["achieved_gap"], v["solve_seconds"]) for k, v in rep["solve_quality"]["candidates"].items()}
        t["orders"] = [{"q": o["quantity"], "need": o["economic_need"], "attribution": o["attribution"]} for o in rep["economics"]["orders"]]
        t["materiality"] = (rep["economics"]["materiality"] or {}).get("reason")
        traces.append(t)
        return rep
    if capture:
        P.plan = traced; R.plan = traced
    t0 = time.perf_counter()
    out = replay(req, truth, REVIEWS, "gated")
    wall = time.perf_counter() - t0
    P.plan = orig; R.plan = orig
    return req, truth, out, traces, wall

def main():
    result = {}
    for seed in SEEDS:
        # B: reproduce three times
        costs = []
        for k in range(3):
            _, _, out, _, _ = run_gated(seed)
            costs.append((out["economic_cost"], tuple(round(sum(p["quantity"] for p in r["purchases"]), 6) for r in out["reviews"])))
        req, truth, out, traces, wall = run_gated(seed, capture=True)
        base = replay(req, truth, REVIEWS, "reorder_point")
        sid = req.services[0].id
        reviews = []
        for i, (t, rg, rb) in enumerate(zip(traces, out["reviews"], base["reviews"])):
            sg, sb = rg["settlement"], rb["settlement"]
            reviews.append({
                "review": i, "state": t["state"], "lean_review": t["lean_review"], "recovery_mode": t["recovery_mode"],
                "on_hand": t["on_hand"], "inbound": t["inbound"], "forecast_mean": t["forecast_mean"], "forecast_sd": t["forecast_sd"],
                "worlds": [{"w": w["weight"], "d": [round(x, 1) for x in list(w["demand"].values())[0][:6]]} for w in t["worlds"]],
                "candidates": {n: {"p0": round(sum(c["p0_purchases"].values()), 3), "svc": c["service_stat"], "svc_by_world": c["service_by_world"],
                                   "cost": c["hedged_cost"], "exposure": c["exposure"], "burden": c["burden"], "feasible": c["feasible"], "status": c["status"],
                                   "purchases": c["purchases"]} for n, c in t["candidates"].items()},
                "feasible": t["feasible"], "chosen": t["chosen"], "accepted": t["accepted"], "status": t["status"], "gates": t["candidate_gates"], "reasons": t["reasons"],
                "solve_quality": t["solve_quality"], "orders": t["orders"], "materiality": t["materiality"],
                "zaad_p0_order": round(sum(t["final_p0_purchases"].values()), 3), "base_p0_order": round(sum(p["quantity"] for p in rb["purchases"]), 3),
                "truth_demand": truth.demand[sid][i],
                "zaad": {"unmet": sum(x["demand"] - x["served"] for x in sg["service_by_period"]), "end_stock": sum(x["quantity"] for x in sg["end_stock"]), "cost": sg["economic_cost"], "ledger": sg["ledger"]},
                "base": {"unmet": sum(x["demand"] - x["served"] for x in sb["service_by_period"]), "end_stock": sum(x["quantity"] for x in sb["end_stock"]), "cost": sb["economic_cost"], "ledger": sb["ledger"]},
            })
        result[seed] = {"repeat_costs": costs, "deterministic": len({c[0] for c in costs}) == 1 and len({c[1] for c in costs}) == 1,
                        "gated_total": out["economic_cost"], "base_total": base["economic_cost"], "gated_ledger": out["ledger"], "base_ledger": base["ledger"],
                        "wall_seconds": wall, "reviews": reviews}
    json.dump(result, open("docs/zaad_full/evidence/p1/closure/p_forensics.json", "w"), indent=1, default=float)
    for seed, r in result.items():
        print(f"seed {seed}: deterministic across 3 repeats: {r['deterministic']}  costs {[round(c[0], 6) for c in r['repeat_costs']]}  gated {r['gated_total']:.4f} base {r['base_total']:.4f} gap {100*(r['gated_total']-r['base_total'])/r['base_total']:+.4f}%")
        first = next((x["review"] for x in r["reviews"] if abs(x["zaad_p0_order"] - x["base_p0_order"]) > 1e-6), None)
        print(f"   first divergence in period-0 order: review {first}")
        for x in r["reviews"]:
            flag = "<<" if x["review"] == first else ""
            print(f"   r{x['review']:2d} {x['state'][:10]:10s} hand {x['on_hand']:6.1f} mu {x['forecast_mean']:6.1f} sd {x['forecast_sd']:4.1f} | zaad {x['zaad_p0_order']:6.1f} ({x['chosen'][:14]:14s} {x['status'][:6]}) base {x['base_p0_order']:6.1f} | truth d {x['truth_demand']:6.1f} | unmet z/b {x['zaad']['unmet']:5.1f}/{x['base']['unmet']:5.1f} end {x['zaad']['end_stock']:6.1f}/{x['base']['end_stock']:6.1f} cost {x['zaad']['cost']:7.1f}/{x['base']['cost']:7.1f} {flag}")
    # D: reconciliation (means)
    g = [result[s]["gated_ledger"] for s in SEEDS]; b = [result[s]["base_ledger"] for s in SEEDS]
    keys = sorted(set(k for l in g + b for k in l))
    print("\nD. cost reconciliation, mean over seeds (ZAAD - baseline):")
    tot_g = tot_b = 0.
    for k in keys:
        vg, vb = mean(l.get(k, 0.) for l in g), mean(l.get(k, 0.) for l in b); tot_g += vg; tot_b += vb
        if abs(vg) > 1e-9 or abs(vb) > 1e-9:
            print(f"   {k:24s} {vg:10.4f} {vb:10.4f} {vg-vb:+10.4f}")
    print(f"   {'TOTAL':24s} {tot_g:10.4f} {tot_b:10.4f} {tot_g-tot_b:+10.4f}   check vs economic_cost: {mean(result[s]['gated_total'] for s in SEEDS)-tot_g:+.6f} / {mean(result[s]['base_total'] for s in SEEDS)-tot_b:+.6f}")

if __name__ == "__main__":
    main()
