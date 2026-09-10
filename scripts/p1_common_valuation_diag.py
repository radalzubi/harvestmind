"""Stage 3/4: common ex-ante valuation of every generated candidate at every review of the P1 fixtures
(product defaults), ranking agreement with the selector, and a disagreement table.
Writes docs/zaad_full/evidence/p1/closure/common_valuation_diag.json."""
from __future__ import annotations
import json, sys, time
import zaad.full.planner as P
import zaad.full.replay as R
from zaad.full.contracts import Request
from zaad.full.model import Solution
from zaad.full.replay import replay
from zaad.full.settlement import PhysicalViolation
from zaad.full.valuation import common_candidate_value
from zaad.full.worlds import draw, forecast_all
from scripts.p1_fixtures import build, REVIEWS

FIX = {"P": "P_high_opening_stock", "C": "C_moq_four_weeks", "O": "O_low_opening_stock", "I": "I_max_pallets_ftl_cap",
       "A": "A_no_terms_good_incumbent", "G": "G_freight_tiers", "Q": "Q_volatile_demand_high_target", "T": "T_combined_realistic"}
pdf = lambda r: r.model_copy(update={k: Request.model_fields[k].default for k in ("stratified_scenarios", "timing_tiebreak", "analytic_shortage")})

def run(letter, seed):
    req0 = pdf(build(FIX[letter], seed)); truth = draw(req0, seed + 10000, 1)[0]
    traces, kept = [], []
    orig = P.plan
    def traced(r):
        P.TRACE = {}; rep = orig(r); t = dict(P.TRACE); P.TRACE = None; traces.append(t); return rep
    P.plan = traced; R.plan = traced
    replay(req0, truth, REVIEWS, "gated", keep_requests=kept)
    P.plan = orig; R.plan = orig
    rows = []
    timings = []
    for i, (t, req) in enumerate(zip(traces, kept)):
        fits = forecast_all(req)
        cands = {}
        for name, c in t["candidates"].items():
            if c["status"] not in ("OPTIMAL", "FEASIBLE_TIME_LIMIT"):
                continue
            purchases = {(k.rsplit(":", 1)[0], int(k.rsplit(":", 1)[1])): q for k, q in c["purchases"].items()}
            sol = Solution("OPTIMAL", purchases, {}, {}, {}, None, [], 0., 0, 0, None, 0., [])
            for po in req.pipeline:
                sol.amendments[(po.id, next(o.id for o in po.options if o.action == "keep"))] = po.remaining
            t0 = time.perf_counter()
            try:
                v = common_candidate_value(req, sol, fits)
            except PhysicalViolation as exc:
                v = {"total": None, "error": str(exc)}
            timings.append(time.perf_counter() - t0)
            cands[name] = {"p0": round(sum(c["p0_purchases"].values()), 3), "sampled_cost": c["hedged_cost"], "exposure": c["exposure"], "burden": c["burden"],
                           "feasible": c["feasible"], "service": c["service_stat"], "common": v.get("total"),
                           "expected_shortage_units": (v.get("components") or {}).get("expected_shortage_units"),
                           "expected_shortage_cost": (v.get("components") or {}).get("expected_shortage_cost"),
                           "expected_carrying": (v.get("components") or {}).get("expected_carrying")}
        feas = [n for n in cands if cands[n]["feasible"] and cands[n]["common"] is not None]
        common_best = min(feas, key=lambda n: cands[n]["common"]) if feas else None
        sampled_best = min(feas, key=lambda n: cands[n]["sampled_cost"] if cands[n]["sampled_cost"] is not None else float("inf")) if feas else None
        rows.append({"fixture": letter, "seed": seed, "review": i, "state": t["state"], "chosen": t["chosen"], "status": t["status"],
                     "common_best": common_best, "sampled_best": sampled_best, "candidates": cands,
                     "agree_with_chosen": (common_best == t["chosen"]) if common_best else None,
                     "common_gap_vs_chosen": (cands[t["chosen"]]["common"] - cands[common_best]["common"]) if (common_best and t["chosen"] in cands and cands[t["chosen"]]["common"] is not None) else None})
    return rows, timings

def main():
    letters = sys.argv[1:] or list(FIX)
    out, tim = [], []
    for letter in letters:
        seeds = (41001, 41002, 41003) if letter == "P" else (41001,)
        for seed in seeds:
            rows, timings = run(letter, seed); out += rows; tim += timings
    json.dump({"rows": out, "valuation_seconds": {"n": len(tim), "p50": sorted(tim)[len(tim)//2], "p95": sorted(tim)[int(.95*(len(tim)-1))], "max": max(tim)}}, open("docs/zaad_full/evidence/p1/closure/common_valuation_diag.json", "w"), indent=1, default=float)
    print(f"valuations {len(tim)}: p50 {sorted(tim)[len(tim)//2]*1000:.1f} ms p95 {sorted(tim)[int(.95*(len(tim)-1))]*1000:.1f} ms max {max(tim)*1000:.1f} ms")
    for r in out:
        flag = "" if r["agree_with_chosen"] else ("DISAGREE" if r["agree_with_chosen"] is False else "n/a")
        if flag or r["fixture"] == "P":
            c = r["candidates"]
            print(f"{r['fixture']} s{r['seed']} r{r['review']:2d} {r['state'][:10]:10s} chosen {r['chosen'][:14]:14s} {r['status'][:6]} | common best {str(r['common_best'])[:14]:14s} sampled best {str(r['sampled_best'])[:14]:14s} gap {r['common_gap_vs_chosen'] if r['common_gap_vs_chosen'] is None else round(r['common_gap_vs_chosen'],1)} {flag} | " + " ".join(f"{n[:5]}:{c[n]['p0']:.0f}/{round(c[n]['common']) if c[n]['common'] else None}/{round(c[n]['sampled_cost']) if c[n]['sampled_cost'] else None}" for n in c))

if __name__ == "__main__":
    main()
