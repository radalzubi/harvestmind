"""Profile one review of a P3 sourcing fixture exactly as the benchmark planned it (the P2 profiling harness
on the P3 builder): replay to the review with `keep_requests`, plan the snapshot through
`zaad.full.planner.plan` with the in-process instrumentation of `scripts.p2_profile_review`, and record
per-candidate class, build / completion / solve time, variables, binaries, rows, nonzeros, status,
nodes and the decision. Writes docs/zaad_full/evidence/p3/profiles/<fixture>_<seed>_r<k>.json.

usage: PYTHONPATH=. python3 -m scripts.p3_profile FIXTURE SEED REVIEW [--deep]"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

from scripts.p2_profile_review import Instrumentation, decision, deep_resolve, machine
from zaad.sourcing.fixtures import FIXTURES, build

OUT = Path("docs/zaad_full/evidence/p3/profiles")


def snapshot(name: str, seed: int, review: int):
    from zaad.full.evaluation import long_truth
    from zaad.full.replay import replay
    from zaad.meio.baselines import register_replay_methods
    register_replay_methods()
    initial = build(name, seed)
    H = initial.horizon
    reviews = review + 1
    truth = long_truth(initial, seed + 10000, (-(-(reviews - 1 + H) // H)) * H)
    kept: list = []
    out = replay(initial, truth, reviews, "gated", keep_requests=kept, rolling=True)
    return kept[review], out["reviews"][review].get("wall_seconds") if out.get("reviews") and len(out["reviews"]) > review else None


def profile(name: str, seed: int, review: int, deep: bool) -> dict:
    from zaad.full.planner import plan
    full = next(n for n in FIXTURES if n == name or n.split("_")[0] == name)
    req, recorded_wall = snapshot(full, seed, review)
    inst = Instrumentation(capture_models=deep)
    inst.install()
    started = time.perf_counter()
    try:
        report = plan(req)
    finally:
        inst.uninstall()
    wall = time.perf_counter() - started
    out = {"fixture": full, "seed": seed, "review": review, "replay_wall_seconds": recorded_wall, "wall_seconds": wall, "machine": machine(),
           "request": {"horizon": req.horizon, "scenarios": req.scenarios, "max_solve_seconds": req.max_solve_seconds, "skus": len(req.skus),
                       "locations": len(req.locations), "transfers": len(req.transfers), "sector_mode": req.sector_mode, "sources": len(req.sources), "sourcing": req.sourcing is not None,
                       "physics": [p.model_dump() for p in req.sku_physics]},
           "decision": decision(report),
           "phases": {"solve_total": sum(s.get("total_seconds", 0.) for s in inst.solves), "milp_total": sum(e["seconds"] for s in inst.solves for e in s.get("linear", [])),
                      "completion_total": sum(s.get("completion_seconds", 0.) for s in inst.solves), "construction_total": sum(s.get("construction_seconds", 0.) for s in inst.solves),
                      "evaluate_total": sum(e["seconds"] for e in inst.evaluate), "settle_calls": inst.settle["calls"], "settle_total": inst.settle["seconds"]},
           "solves": inst.solves}
    name_out = f"{full.split('_')[0]}_{seed}_r{review}"
    OUT.mkdir(parents=True, exist_ok=True)
    if deep:
        out["deep"] = deep_resolve(inst.models, OUT / f"{name_out}.highs")
    (OUT / f"{name_out}.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"{name_out}: wall {wall:.1f}s (replay {recorded_wall}) solves {len(inst.solves)} milp {out['phases']['milp_total']:.1f}s completion {out['phases']['completion_total']:.1f}s "
          f"build {out['phases']['construction_total']:.1f}s state {out['decision']['state']} {out['decision']['status']}")
    for s in inst.solves:
        if "total_seconds" not in s:
            continue
        print(f"  {s['index']:02d} {s['label']:<24} W{s['worlds']} {s['status']:<20} total {s['total_seconds']:6.1f}s build {s['construction_seconds']:4.1f}s compl {s['completion_seconds']:5.1f}s milp {s['linear_seconds']:6.1f}s "
              f"vars {s['variables']} rows {s['constraints']} nodes {s['nodes']} " + " ".join(f"[{e['phase']} b{e['budget_seconds']:.0f}s {e['seconds']:.1f}s int {e['integer']} bin {e['binary']} st {e['status']} kinds {dict(sorted(((k, v) for k, v in e['variable_kinds'].items() if k in ('fefo', 'depleted', 'case', 'packs', 'pallets', 'order', 'active', 'priority')), key=lambda kv: -kv[1]))}]" for e in s["linear"]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("fixture")
    ap.add_argument("seed", type=int)
    ap.add_argument("review", type=int)
    ap.add_argument("--deep", action="store_true")
    a = ap.parse_args()
    profile(a.fixture, a.seed, a.review, a.deep)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
