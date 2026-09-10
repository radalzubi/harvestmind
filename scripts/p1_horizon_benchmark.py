"""P1 extended-window benchmark: every fixture, policy and seed replayed in rolling mode (constant
twelve-period planning horizon) for W_MAX reviews on one stitched truth, scored at every endpoint under
both terminal rules. Pre-registered in `P1_BENCHMARK_PREREGISTRATION.md` before the first run.

usage: PYTHONPATH=. python3 -m scripts.p1_horizon_benchmark [--fixtures A,B] [--policies ..] [--reviews 52] [--workers 4] [--tag horizon52]
Output: docs/zaad_full/evidence/p1/closure/<tag>.jsonl, one record per cell with the endpoint curve and a
compact per-review log."""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from scripts.p1_fixtures import FIXTURES, POLICIES, SEEDS, build
from zaad.full.contracts import Request

PRODUCT = {k: Request.model_fields[k].default for k in ("stratified_scenarios", "timing_tiebreak", "analytic_shortage")}
W_MAX = 52


def run_cell(name: str, policy: str, seed: int, reviews: int = W_MAX, horizon: int = 0) -> dict:
    from zaad.full.evaluation import curve, long_truth, with_horizon
    from zaad.full.replay import replay
    from zaad.full.tolerance import is_dust
    initial = build(name, seed).model_copy(update=PRODUCT)
    base_h = initial.horizon
    # diagnostic planning-horizon override for ZAAD cells only (B sweep); the truth is the benchmark's
    # own stitched path (twelve-period segments), long enough for the longer plan
    planning = with_horizon(initial, horizon) if (horizon and policy == "gated") else initial
    segments = -(-(reviews - 1 + planning.horizon) // base_h)
    truth = long_truth(initial, seed + 10000, segments * base_h)
    started = time.time()
    out = replay(planning, truth, reviews, policy, rolling=True)
    seconds = time.time() - started
    log = out.get("reviews", [])
    cell = {"fixture": name, "policy": policy, "seed": seed, "status": out["status"], "failure": out.get("failure"),
            "reviews_completed": len(log), "reviews_requested": reviews, "seconds": seconds}
    if log:
        cell["curve"] = curve(initial, log)
        cell["planning_horizon"] = planning.horizon
        cell["per_review"] = []
        for row in log:
            st = row["settlement"]
            orch = row.get("orchestration") or {}
            warn = row["warnings"]
            cell["per_review"].append({
                "review": row["review"], "ledger": st["ledger"],
                "demand": sum(x["demand"] for x in st["service_by_period"]), "served": sum(x["served"] for x in st["service_by_period"]),
                "end_stock_units": sum(x["quantity"] for x in st["end_stock"]), "end_stock": st["end_stock"],
                "pending": [list(p) for p in st["pending"]],
                "purchases": [(p["source"], p["quantity"]) for p in row["purchases"] if not is_dust(p["quantity"])],
                "forecast_mean": {k: v["mean"] for k, v in row["forecast"].items()},
                "cash": st["trace"][0]["cash"], "debt": st["trace"][0]["debt"],
                "status": warn[0] if warn else None,
                "abstained": any("NO MATERIAL IMPROVEMENT" in str(w) for w in warn),
                "owner": orch.get("planner_owner"), "state": orch.get("state"), "p1_classes_added": orch.get("p1_classes_added"),
                "milps_attempted": orch.get("milps_attempted"), "wall_seconds": row.get("wall_seconds", 0.)})
    return cell


def _job(args):
    name, policy, seed, reviews, horizon = args
    try:
        return run_cell(name, policy, seed, reviews, horizon)
    except Exception as exc:     # a crashed cell is a recorded failure, not a lost run
        return {"fixture": name, "policy": policy, "seed": seed, "status": "ERROR", "failure": repr(exc), "reviews_completed": 0, "reviews_requested": reviews, "planning_horizon": horizon}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", default="")
    ap.add_argument("--policies", default=",".join(POLICIES))
    ap.add_argument("--reviews", type=int, default=W_MAX)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--tag", default="horizon52")
    ap.add_argument("--horizon", type=int, default=0, help="diagnostic: planning horizon for ZAAD cells (0 = the fixture's own)")
    a = ap.parse_args()
    names = [n for n in a.fixtures.split(",") if n] or list(FIXTURES)
    policies = [p for p in a.policies.split(",") if p]
    # ZAAD cells first, largest fixtures first, so the slow solves do not trail the pool.
    order = {"D_case_multiple": 0, "H_per_pallet_freight": 1, "F_mov_two_skus": 2, "E_pallet_multiple": 3, "T_combined_realistic": 4, "I_max_pallets_ftl_cap": 5, "G_freight_tiers": 6}
    jobs = sorted([(n, p, s, a.reviews, a.horizon) for n in names for p in policies for s in SEEDS], key=lambda j: (j[1] != "gated", order.get(j[0], 9)))
    out = Path("docs/zaad_full/evidence/p1/closure") / f"{a.tag}.jsonl"
    started = time.time()
    with ProcessPoolExecutor(a.workers) as pool, out.open("w") as f:
        for cell in pool.map(_job, jobs):
            f.write(json.dumps(cell, default=float) + "\n")
            f.flush()
            end = (cell.get("curve") or [{}])[-1]
            print(f"{cell['fixture']:32s} {cell['policy']:14s} {cell['seed']} {cell['status']:10s} reviews {cell['reviews_completed']:3d}/{cell['reviews_requested']} "
                  f"realised {end.get('realized', float('nan')):10,.0f} continuation {end.get('continuation', float('nan')):10,.0f} {cell.get('seconds', 0.):7.1f}s", flush=True)
    print("seconds", round(time.time() - started))
