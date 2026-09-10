"""Fixture P counterfactual diagnostics F1-F8 (final P1 closure). Diagnostics only; nothing here is a default."""
from __future__ import annotations
import json
from statistics import mean
import numpy as np
import zaad.full.planner as P
import zaad.full.screen as S
from zaad.full.contracts import Request
from zaad.full.model import Solution, solve
from zaad.full.planner import evaluate
from zaad.full.replay import replay
from zaad.full.worlds import draw, forecast_all
from zaad.full.policies import baseline_plan
from scripts.p1_fixtures import build, REVIEWS, SEEDS

def pd(req):
    return req.model_copy(update={k: Request.model_fields[k].default for k in ("stratified_scenarios", "timing_tiebreak")})

def arm(label, policy="gated", setup=None, teardown=None):
    costs, svcs, unmet = [], [], []
    for seed in SEEDS:
        req = pd(build("P_high_opening_stock", seed)); truth = draw(req, seed + 10000, 1)[0]
        if setup: setup()
        try:
            out = replay(req, truth, REVIEWS, policy)
        finally:
            if teardown: teardown()
        costs.append(out["economic_cost"])
        d = sum(x["demand"] for r in out["reviews"] for x in r["settlement"]["service_by_period"]); s_ = sum(x["served"] for r in out["reviews"] for x in r["settlement"]["service_by_period"])
        svcs.append(s_ / d); unmet.append(d - s_)
    return {"arm": label, "cost": mean(costs), "service": mean(svcs), "unmet": mean(unmet), "per_seed": costs}

results = []
base = arm("baseline reorder_point (through ZAAD settlement, F8)", "reorder_point"); results.append(base)
results.append(arm("F0 product defaults"))
orig_min = dict(S.MINIMUM_SAFE); orig_opt = dict(S.OPTIONAL)
def no_det():
    for k in S.MINIMUM_SAFE: S.MINIMUM_SAFE[k] = tuple(c for c in S.MINIMUM_SAFE[k] if c != "deterministic_network")
def restore():
    S.MINIMUM_SAFE.clear(); S.MINIMUM_SAFE.update(orig_min); S.OPTIONAL.clear(); S.OPTIONAL.update(orig_opt); P.EXCLUDE_FROM_SELECTION = frozenset()
results.append(arm("F1 deterministic candidate not built", setup=no_det, teardown=restore))
def excl_det(): P.EXCLUDE_FROM_SELECTION = frozenset({"deterministic_network"})
results.append(arm("F2 deterministic built and evaluated but cannot win", setup=excl_det, teardown=restore))
def force_stoch():
    P.EXCLUDE_FROM_SELECTION = frozenset({"deterministic_network", "base_stock", "incumbent"})
    for k in S.MINIMUM_SAFE:
        if "stochastic_network" not in S.MINIMUM_SAFE[k]: S.MINIMUM_SAFE[k] = S.MINIMUM_SAFE[k] + ("stochastic_network",)
results.append(arm("F7 stochastic candidate forced (deterministic, base stock, incumbent unselectable)", setup=force_stoch, teardown=restore))
results.append(arm("F6 incumbent action forced (replace_sold rule)", "incumbent"))
# F5 terminal sensitivity: revalue residual at full value (both policies)
def terminal_full(label, policy):
    out = []
    for seed in SEEDS:
        req = pd(build("P_high_opening_stock", seed)); truth = draw(req, seed + 10000, 1)[0]
        data = req.model_dump(mode="python")
        for s_ in data["skus"]: s_["terminal_value"] = s_["asset_value"]
        out.append(replay(Request.model_validate(data), truth, REVIEWS, policy)["economic_cost"])
    return {"arm": label, "cost": mean(out), "per_seed": out}
results.append(terminal_full("F5 product defaults, residual at full value", "gated"))
results.append(terminal_full("F5 baseline, residual at full value", "reorder_point"))
for r in results:
    print(f"{r['arm']:75s} cost {r['cost']:9.2f}  vs baseline {100*(r['cost']-base['cost'])/base['cost']:+.3f}%" + (f"  service {r['service']:.4f} unmet {r['unmet']:.1f}" if "service" in r else ""))
# F3/F4: the decisive review's plans under sampled (3) versus full (200-world) expectation
print("\nF3/F4: seed 41001, review 8 plans evaluated on the 3 selection worlds versus 200 iid worlds")
req0 = pd(build("P_high_opening_stock", 41001)); truth = draw(req0, 41001 + 10000, 1)[0]
kept = []; replay(req0, truth, 9, "gated", keep_requests=kept); r8 = kept[8]
sel = draw(r8, r8.seed, 3); many = draw(r8, 777, 200)
def plan(p):
    sol = Solution("OPTIMAL", p, {}, {}, {}, None, [], 0., 0, 0, None, 0., [])
    for po in r8.pipeline: sol.amendments[(po.id, next(o.id for o in po.options if o.action == "keep"))] = po.remaining
    return sol
det = solve(r8, draw(r8, r8.seed, 1, deterministic=True), service_floor=True)
bs = baseline_plan(r8, "reorder_point")
fits = forecast_all(r8); mu = fits[r8.services[0].id]["mean"]
for name, sol in (("deterministic candidate", det), ("reorder_point action", bs), ("deterministic + 10 units at t=0", plan({**det.purchases, ("src_A", 0): det.purchases.get(("src_A", 0), 0.) + 10.})), ("deterministic + 17 units at t=0", plan({**det.purchases, ("src_A", 0): det.purchases.get(("src_A", 0), 0.) + 17.}))):
    rows3 = evaluate(r8, sol, sel); rows200 = evaluate(r8, sol, many)
    c3 = mean(r["economic_cost"] for r in rows3); c200 = mean(r["economic_cost"] for r in rows200)
    sh3 = mean(r["ledger"].get("lost_sales_opportunity", 0.) + r["ledger"].get("sla", 0.) for r in rows3); sh200 = mean(r["ledger"].get("lost_sales_opportunity", 0.) + r["ledger"].get("sla", 0.) for r in rows200)
    print(f"   {name:34s} p0 order {sol.purchases.get(('src_A',0),0):6.1f} | 3 worlds: cost {c3:8.2f} shortage {sh3:7.2f} | 200 worlds: cost {c200:8.2f} shortage {sh200:7.2f}  (objective {det.projected_cost:.2f} for the deterministic solve)")
# analytic expected shortage at the mean under the fitted bootstrap mixture
f = fits[r8.services[0].id]; sizes = np.asarray(f["sizes"]); occ = 1 - f["zero_probability"]; scale = f["mean"] / (occ * sizes.mean())
atoms = np.sort(sizes * scale)
def L(a): return occ * np.mean(np.maximum(atoms - a, 0.))
print(f"\n   analytic E[(D-a)+] under the fitted mixture at review 8 (mu {mu:.2f}): a=mu {L(mu):.3f} units; a=mu+5 {L(mu+5):.3f}; a=mu+10 {L(mu+10):.3f}; a=mu+17 {L(mu+17):.3f}; per-unit penalty {r8.services[0].selling_price + r8.services[0].sla_per_unmet:.2f}; holding per unit-period {r8.locations[0].holding_per_value_period * r8.skus[0].asset_value:.4f}")
json.dump({"arms": results}, open("docs/zaad_full/evidence/p1/closure/p_counterfactuals.json", "w"), indent=1, default=float)
