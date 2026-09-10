"""Diagnostic (not the declared evaluation): fixture parity at a doubled window, under both terminal
evaluations, to see whether the residual-stock sensitivity shrinks as the window lengthens.
usage: PYTHONPATH=. python3 -m scripts.p1_horizon_extension_diag C_moq_four_weeks I_max_pallets_ftl_cap ...
Fixture definitions are unchanged for the declared results; here the request horizon is set to 24
periods (23 reviews, the replay's H-1 convention) with every other field as declared."""
from __future__ import annotations
import json, sys, time
from concurrent.futures import ProcessPoolExecutor
from statistics import mean
from scripts.p1_fixtures import build, POLICIES, SEEDS
from zaad.full.contracts import Request
from zaad.full.replay import replay
from zaad.full.worlds import draw

H = 24
PRODUCT = {k: Request.model_fields[k].default for k in ("stratified_scenarios", "timing_tiebreak", "analytic_shortage")}


def one(args):
    name, policy, seed = args
    from scripts.p1_fixtures import FIXTURES
    from zaad.full.fixtures_p1 import p1_request
    args = dict(FIXTURES[name]["args"]); args.pop("extra", None); args["horizon"] = H
    req = p1_request(seed=seed, stresses="none", order_smoothing=0., **args).model_copy(update=PRODUCT)
    truth = draw(req, seed + 10000, 1)[0]
    out = replay(req, truth, H - 1, policy)
    if out["status"] != "COMPLETE":
        return {"fixture": name, "policy": policy, "seed": seed, "status": out["status"], "failure": out.get("failure")}
    return {"fixture": name, "policy": policy, "seed": seed, "status": "COMPLETE", "realized": out["economic_cost"], "continuation": out["economic_cost_continuation"],
            "residual_units": out["terminal_continuation"]["units"]}


if __name__ == "__main__":
    names = sys.argv[1:]
    jobs = [(n, p, s) for n in names for p in POLICIES for s in SEEDS]
    t0 = time.time(); rows = []
    with ProcessPoolExecutor(3) as pool:
        for r in pool.map(one, jobs):
            rows.append(r)
    json.dump(rows, open("docs/zaad_full/evidence/p1/closure/horizon_extension_diag.json", "w"), indent=1, default=float)
    for n in names:
        for key in ("realized", "continuation"):
            deltas = []
            for s in SEEDS:
                rs = [r for r in rows if r["fixture"] == n and r["seed"] == s and r["status"] == "COMPLETE"]
                g = next((r for r in rs if r["policy"] == "gated"), None); base = [r for r in rs if r["policy"] != "gated"]
                if g and base:
                    bb = min(r[key] for r in base); deltas.append(100 * (g[key] - bb) / bb)
            fails = [r for r in rows if r["fixture"] == n and r["status"] != "COMPLETE"]
            print(f"{n[:26]:26s} H={H} {key:12s} parity per seed {[round(d, 2) for d in deltas]} mean {mean(deltas) if deltas else float('nan'):+.2f}% | incomplete {[(r['policy'], r['seed']) for r in fails]}")
    print("seconds", round(time.time() - t0))
