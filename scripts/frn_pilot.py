"""FreshRetailNet-50K pilot: the bounded comparative replay (HARDENING follow-on, first public-data run).

    python -m scripts.frn_pilot --stage smoke|five|fifty [--windows val1,val2,final] [--tracks observed,recovered]
                                [--scenarios stable,uncertain,uncertain_fill_only] [--policies gated,order_up_to,base_stock,reorder_point]

Every (series, window, track, scenario, policy) run is one JSON line in data/public/freshretailnet/results/<stage>/runs.jsonl
(git-ignored), successful or not; a run manifest records the code commit, the declaration hash, the selection hash and
the environment. Runs are sequential: one solve at a time, bounded by the declaration's solve budget.

Windows. `val1` and `val2` are chronological internal-validation windows inside the training period (rolling mode,
14 daily reviews, 7-day horizon: 20 truth days each, ending before the evaluation week). `final` is the designated
7-day evaluation week (legacy mode: the horizon shrinks by one day per review because no day after 2024-07-02 exists;
7 reviews). Methodology, assumptions, parameters and the series were frozen before `final` ran (see the evidence note).

Fairness. All policies see the same request (same history, same declared supply and economics, same opening stock),
are settled against the same truth World (one supply draw per series/window/scenario shared by both tracks), and keep
their own stock, open orders and learned fill through `zaad.full.replay.replay`. Nothing dated at or after an origin
reaches a policy before it is settled.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import date
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time
import traceback
from typing import Any

import numpy as np

from zaad.full.evaluation import endpoint
from zaad.full.replay import replay
from zaad.public.freshretailnet import loader, request_builder as RB, truth as T
from zaad.public.freshretailnet.declaration import DEFAULT

POLICIES = ("gated", "order_up_to", "base_stock", "reorder_point")
TRACKS = ("observed", "recovered")
WINDOWS: dict[str, dict[str, Any]] = {
    "val1": {"origin": date(2024, 5, 13), "reviews": 14, "rolling": True, "role": "internal validation (training period)"},
    "val2": {"origin": date(2024, 6, 3), "reviews": 14, "rolling": True, "role": "internal validation (training period)"},
    "final": {"origin": date(2024, 6, 26), "reviews": 7, "rolling": False, "role": "designated evaluation week; horizon shrinks (no later day exists)"},
}
STAGES = {"smoke": 1, "five": 5, "fifty": 50}
RESULTS_ROOT = Path("data/public/freshretailnet/results")
MANIFEST = Path("docs/remodel/evidence/frn/SELECTION_MANIFEST.json")


def _commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001 - the commit is informational
        return "unknown"


def _peak_rss_mb() -> float:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / (1024 ** 2) if sys.platform == "darwin" else rss / 1024


def _truth_periods(window: dict[str, Any], horizon: int) -> int:
    return window["reviews"] - 1 + horizon if window["rolling"] else window["reviews"]


def _supply_seed(store: int, product: int, window: str, scenario: str) -> int:
    """Deterministic across processes (Python's hash() is salted per process; sha256 is not)."""
    import hashlib
    digest = hashlib.sha256(f"{store}|{product}|{window}|{scenario}|{DEFAULT.version}".encode()).hexdigest()
    return int(digest[:8], 16) % (2 ** 31)


def derived_metrics(out: dict[str, Any], req, reviews: int) -> dict[str, Any]:
    rows = out["reviews"]
    buys = [sum(p["quantity"] for p in r["purchases"]) for r in rows]
    end_stock = [sum(x["quantity"] for x in r["settlement"]["end_stock"]) for r in rows]
    unmet_by_review = [sum(x["demand"] - x["served"] for x in r["settlement"]["service_by_period"]) for r in rows]
    demand_by_review = [sum(x["demand"] for x in r["settlement"]["service_by_period"]) for r in rows]
    residuals = [r["settlement"].get("conservation_residual") for r in rows]
    residual_max = max((abs(float(x)) for x in residuals if isinstance(x, (int, float))), default=None)
    expired = sum(sum(v.get("expired", 0.) for v in (r["settlement"].get("flows") or {}).values()) if isinstance(r["settlement"].get("flows"), dict) else 0.
                  for r in rows)
    warnings = [w for r in rows for w in (r.get("warnings") or [])]
    statuses = [str((r.get("solver") or {}).get("status")) for r in rows]
    orchestration = [r.get("orchestration") for r in rows if r.get("orchestration")]
    return {
        "reviews_completed": len(rows), "order_quantities": buys, "orders_placed": sum(1 for b in buys if b > 1e-9),
        "total_ordered": float(sum(buys)), "mean_order_when_placed": float(np.mean([b for b in buys if b > 1e-9])) if any(b > 1e-9 for b in buys) else 0.,
        "end_stock_by_review": end_stock, "end_stock_mean": float(np.mean(end_stock)), "end_stock_sd": float(np.std(end_stock)),
        "stockout_reviews": sum(1 for u, s in zip(unmet_by_review, end_stock) if u > 1e-9 or s <= 1e-9),
        "unmet_reviews": sum(1 for u in unmet_by_review if u > 1e-9),
        "demand_total": float(sum(demand_by_review)), "unmet_total": float(sum(unmet_by_review)), "expired_total": float(expired),
        "conservation_residual_max": residual_max, "solver_statuses": statuses, "warnings": warnings[:50],
        "retained_incumbent_reviews": sum(1 for r in rows if any("RETAIN_INCUMBENT" in str(w) for w in (r.get("warnings") or []))),
        "abstentions": sum(1 for w in warnings if "ABSTAIN" in str(w).upper()),
        "service_infeasible_reviews": sum(1 for r in rows if any("REQUESTED_SERVICE_INFEASIBLE" in str(w) for w in (r.get("warnings") or []))),
        "fallbacks": sum(1 for w in warnings if "FALLBACK" in str(w).upper()),
        "wall_seconds_by_review": [r.get("wall_seconds") for r in rows], "planner_states": [o.get("state") for o in orchestration][:20],
    }


def run_one(series, row, window_name, track, scenario, policy, *, req_by_track, world, stage_dir) -> dict[str, Any]:
    window = WINDOWS[window_name]
    req, record = req_by_track[track]
    base = {"stage_dir": str(stage_dir), "store_id": row["store_id"], "product_id": row["product_id"], "stratum": row["stratum"],
            "volume_class": row["volume_class"], "stockout_class": row["stockout_class"], "regularity_class": row["regularity_class"],
            "promo_class": row["promo_class"], "window": window_name, "origin": window["origin"].isoformat(), "reviews": window["reviews"],
            "rolling": window["rolling"], "track": track, "scenario": scenario, "policy": policy, "request": record,
            "declaration_hash": DEFAULT.hash(), "evidence": "modelled comparison on public observed demand under declared SYNTHETIC supply; not a realized outcome"}
    t0, c0 = time.perf_counter(), time.process_time()
    try:
        out = replay(req, world, window["reviews"], policy, rolling=window["rolling"])
    except Exception as exc:  # noqa: BLE001 - a crashing policy is a result, recorded, never dropped
        return {**base, "status": "EXCEPTION", "error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()[-2000:],
                "wall_seconds": time.perf_counter() - t0, "cpu_seconds": time.process_time() - c0}
    wall, cpu = time.perf_counter() - t0, time.process_time() - c0
    status = out.get("status", "UNKNOWN")
    rows = out.get("reviews", [])
    result: dict[str, Any] = {**base, "status": status, "wall_seconds": wall, "cpu_seconds": cpu, "failure": out.get("failure")}
    if rows:
        result["derived"] = derived_metrics(out, req, window["reviews"])
        try:
            e = endpoint(req, rows, len(rows))
            result["endpoint"] = {k: v for k, v in e.items() if k != "ledger"}
            result["ledger"] = e["ledger"]
        except Exception as exc:  # noqa: BLE001 - scoring failure is itself recorded
            result["endpoint_error"] = f"{type(exc).__name__}: {exc}"
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=sorted(STAGES), required=True)
    ap.add_argument("--windows", default="val1,val2,final")
    ap.add_argument("--tracks", default=",".join(TRACKS))
    ap.add_argument("--scenarios", default=",".join(s.name for s in DEFAULT.supply))
    ap.add_argument("--policies", default=",".join(POLICIES))
    ap.add_argument("--db", default=str(loader.DEFAULT_DB))
    ap.add_argument("--out", default=str(RESULTS_ROOT))
    args = ap.parse_args()
    windows = [w for w in args.windows.split(",") if w]
    tracks = [t for t in args.tracks.split(",") if t]
    scenarios = [s for s in args.scenarios.split(",") if s]
    policies = [p for p in args.policies.split(",") if p]
    if args.stage == "smoke":
        windows, tracks, scenarios = windows[:1], tracks[:1], scenarios[:1]
    manifest = json.loads(MANIFEST.read_text())
    rows = manifest["series"][:STAGES[args.stage]]
    stage_dir = Path(args.out) / args.stage
    stage_dir.mkdir(parents=True, exist_ok=True)
    runs_path = stage_dir / "runs.jsonl"
    if runs_path.exists():
        runs_path.unlink()
    conn = loader.connect(args.db)
    started = time.time()
    run_manifest = {"stage": args.stage, "commit": _commit(), "declaration": DEFAULT.as_dict(), "selection_hash": manifest["selection_hash"],
                    "selection_version": manifest["selection_version"], "series": [(r["store_id"], r["product_id"]) for r in rows],
                    "windows": {w: {**WINDOWS[w], "origin": WINDOWS[w]["origin"].isoformat()} for w in windows}, "tracks": tracks, "scenarios": scenarios,
                    "policies": policies, "dataset_manifest": loader.manifest_record(conn), "python": platform.python_version(),
                    "platform": platform.platform(), "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started))}
    counts = {"runs": 0, "complete": 0, "failed": 0}
    with open(runs_path, "a") as sink:
        for i, row in enumerate(rows, 1):
            series = RB.load_series(conn, row["store_id"], row["product_id"])
            for window_name in windows:
                window = WINDOWS[window_name]
                for scenario in scenarios:
                    try:
                        req_by_track = {t: RB.build_request(series, window["origin"], track=t, scenario=scenario) for t in tracks}
                    except Exception as exc:  # noqa: BLE001 - a series that cannot be built is a recorded failure for every policy
                        for t in tracks:
                            for policy in policies:
                                sink.write(json.dumps({"store_id": row["store_id"], "product_id": row["product_id"], "window": window_name, "track": t,
                                                       "scenario": scenario, "policy": policy, "status": "BUILD_FAILED", "error": f"{type(exc).__name__}: {exc}"}) + "\n")
                                counts["runs"] += 1
                                counts["failed"] += 1
                        continue
                    anchor_req, _ = req_by_track["observed"] if "observed" in req_by_track else next(iter(req_by_track.values()))
                    periods = _truth_periods(window, anchor_req.horizon)
                    seed = _supply_seed(row["store_id"], row["product_id"], window_name, scenario)
                    base_world, world_record = T.truth_world(anchor_req, series, window["origin"], track="observed", periods=periods, seed=seed)
                    for track in tracks:
                        req, _ = req_by_track[track]
                        path, path_record = T.demand_path(series, window["origin"], track=track, periods=periods)
                        world = T.with_demand(base_world, req, path, f"truth-{track}-{window_name}")
                        for policy in policies:
                            result = run_one(series, row, window_name, track, scenario, policy, req_by_track=req_by_track, world=world, stage_dir=stage_dir)
                            result["truth"] = {**world_record, **path_record, "supply_seed": seed}
                            sink.write(json.dumps(result, default=str) + "\n")
                            sink.flush()
                            counts["runs"] += 1
                            counts["complete" if result["status"] == "COMPLETE" else "failed"] += 1
            print(f"[{i}/{len(rows)}] store {row['store_id']} product {row['product_id']} done; runs {counts['runs']} complete {counts['complete']} failed {counts['failed']} "
                  f"elapsed {time.time() - started:.0f}s", flush=True)
    conn.close()
    run_manifest.update({"finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_seconds": time.time() - started,
                         "cpu_seconds_process": time.process_time(), "peak_rss_mb": _peak_rss_mb(), **counts})
    (stage_dir / "run_manifest.json").write_text(json.dumps(run_manifest, indent=2, default=str) + "\n")
    print(json.dumps({k: run_manifest[k] for k in ("stage", "runs", "complete", "failed", "wall_seconds", "peak_rss_mb")}))
    return 0 if counts["runs"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
