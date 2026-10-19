"""Walmart M5, Experiment A: weekly single-SKU replenishment, ZAAD against conventional policies on 50 frozen series.

    python -m scripts.m5_pilot --stage smoke|five|fifty [--windows val1,val2,final] [--scenarios ...] [--policies ...] [--declaration corrected]

Same discipline as the FreshRetailNet runner: one JSON line per (series, window, scenario, policy) run including every
failure, one supply realization per (series, window, scenario) shared by all policies, sequential solves, a run
manifest with commit and hashes. The declared incumbent rule is given to ZAAD only; the baselines never see it; ZAAD's
per-review decision provenance (own candidate / retained incumbent / abstention) is recorded. Results under
data/public/m5/results/<stage>_<declaration>/ (git-ignored).
"""
from __future__ import annotations

import argparse
import hashlib
import json
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
from zaad.public.m5 import loader, request_builder as RB, truth as T
from zaad.public.m5.declaration import DEFAULT, VARIANTS, WINDOWS, Declaration

POLICIES = ("gated", "reorder_point", "periodic:1", "base_stock", "order_up_to")
STAGES = {"smoke": 1, "five": 5, "fifty": 50}
RESULTS_ROOT = Path("data/public/m5/results")
MANIFEST = Path("docs/remodel/evidence/m5/SELECTION_MANIFEST.json")


def _commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001 - informational
        return "unknown"


def _peak_rss_mb() -> float:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / (1024 ** 2) if sys.platform == "darwin" else rss / 1024


def _supply_seed(series_id: str, window: str, scenario: str) -> int:
    return int(hashlib.sha256(f"{series_id}|{window}|{scenario}|m5".encode()).hexdigest()[:8], 16) % (2 ** 31)


def decision_provenance(rows: list[dict]) -> dict[str, Any]:
    kinds, policies, modes = [], [], []
    for r in rows:
        w = [str(x) for x in (r.get("warnings") or [])]
        status = w[0] if w else "UNKNOWN"
        kinds.append({"PENDING_REVIEW": "OWN_CANDIDATE", "RETAIN_INCUMBENT": "RETAINED_INCUMBENT", "ABSTAIN": "ABSTAIN"}.get(status, status))
        policies.append(w[1] if len(w) > 1 else None)
        modes.append(next((x[5:] for x in w if x.startswith("mode=")), None))
    counts = {k: kinds.count(k) for k in ("OWN_CANDIDATE", "RETAINED_INCUMBENT", "ABSTAIN")}
    return {"by_review": kinds, "selected_policy_by_review": policies, "mode_by_review": modes, **counts, "own_share": counts["OWN_CANDIDATE"] / len(kinds) if kinds else None}


def derived_metrics(out: dict[str, Any]) -> dict[str, Any]:
    rows = out["reviews"]
    buys = [sum(p["quantity"] for p in r["purchases"]) for r in rows]
    end_stock = [sum(x["quantity"] for x in r["settlement"]["end_stock"]) for r in rows]
    unmet = [sum(x["demand"] - x["served"] for x in r["settlement"]["service_by_period"]) for r in rows]
    demand = [sum(x["demand"] for x in r["settlement"]["service_by_period"]) for r in rows]
    residuals = [r["settlement"].get("conservation_residual") for r in rows]
    warnings = [str(w) for r in rows for w in (r.get("warnings") or [])]
    orchestration = [r.get("orchestration") for r in rows if r.get("orchestration")]
    cash = [(r.get("capital") or {}) for r in rows]
    return {"reviews_completed": len(rows), "order_quantities": buys, "orders_placed": sum(1 for b in buys if b > 1e-9), "total_ordered": float(sum(buys)),
            "mean_order_when_placed": float(np.mean([b for b in buys if b > 1e-9])) if any(b > 1e-9 for b in buys) else 0.,
            "end_stock_by_review": end_stock, "end_stock_mean": float(np.mean(end_stock)), "end_stock_sd": float(np.std(end_stock)),
            "stockout_reviews": sum(1 for u, s in zip(unmet, end_stock) if u > 1e-9 or s <= 1e-9), "unmet_reviews": sum(1 for u in unmet if u > 1e-9),
            "demand_total": float(sum(demand)), "unmet_total": float(sum(unmet)),
            "conservation_residual_max": max((abs(float(x)) for x in residuals if isinstance(x, (int, float))), default=None),
            "warnings": warnings[:50], "service_infeasible_reviews": sum(1 for r in rows if any("REQUESTED_SERVICE_INFEASIBLE" in str(w) for w in (r.get("warnings") or []))),
            "wall_seconds_by_review": [r.get("wall_seconds") for r in rows],
            "state_counts": {st: sum(1 for o in orchestration if o.get("state") == st) for st in sorted({o.get("state") for o in orchestration if o.get("state")})},
            "capital_notes": [c for c in cash if c][:3]}


def run_one(row, window_name, scenario, policy, *, req, record, world, declaration: Declaration, variant: str) -> dict[str, Any]:
    window = WINDOWS[window_name]
    if policy != "gated" and req.incumbent_rule:
        req = req.model_copy(update={"incumbent_rule": None})
    base = {"series_id": row["id"], "item_id": row["item_id"], "store_id": row["store_id"], "dept_id": row["dept_id"], "cat_id": row["cat_id"], "stratum": row["stratum"],
            "volume_class": row["volume_class"], "volatility_class": row["volatility_class"], "intermittency_class": row["intermittency_class"],
            "window": window_name, "origin": window["origin"].isoformat(), "reviews": window["reviews"], "rolling": window["rolling"], "track": "observed",
            "scenario": scenario, "policy": policy, "request": record, "variant": variant, "declaration_hash": declaration.hash(), "declaration_version": declaration.version,
            "evidence": "modelled comparison on public observed sales under declared SYNTHETIC supply and economics; not a realized outcome"}
    t0, c0 = time.perf_counter(), time.process_time()
    try:
        out = replay(req, world, window["reviews"], policy, rolling=window["rolling"])
    except Exception as exc:  # noqa: BLE001 - a crashing policy is a recorded result
        return {**base, "status": "EXCEPTION", "error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()[-2000:],
                "wall_seconds": time.perf_counter() - t0, "cpu_seconds": time.process_time() - c0}
    wall, cpu = time.perf_counter() - t0, time.process_time() - c0
    rows = out.get("reviews", [])
    result: dict[str, Any] = {**base, "status": out.get("status", "UNKNOWN"), "wall_seconds": wall, "cpu_seconds": cpu, "failure": out.get("failure")}
    if rows:
        result["derived"] = derived_metrics(out)
        if policy == "gated":
            result["provenance"] = decision_provenance(rows)
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
    ap.add_argument("--scenarios", default=",".join(s.name for s in DEFAULT.supply))
    ap.add_argument("--policies", default=",".join(POLICIES))
    ap.add_argument("--declaration", default="corrected", choices=sorted(VARIANTS))
    ap.add_argument("--db", default=str(loader.DEFAULT_DB))
    ap.add_argument("--out", default=str(RESULTS_ROOT))
    ap.add_argument("--label", default=None)
    args = ap.parse_args()
    declaration = VARIANTS[args.declaration]
    windows = [w for w in args.windows.split(",") if w]
    scenarios = [s for s in args.scenarios.split(",") if s]
    policies = [p for p in args.policies.split(",") if p]
    if args.stage == "smoke":
        windows, scenarios = windows[:1], scenarios[:1]
    manifest = json.loads(MANIFEST.read_text())
    rows = manifest["series"][:STAGES[args.stage]]
    stage_dir = Path(args.out) / (args.label or f"{args.stage}_{args.declaration}")
    stage_dir.mkdir(parents=True, exist_ok=True)
    runs_path = stage_dir / "runs.jsonl"
    if runs_path.exists():
        runs_path.unlink()
    conn = loader.connect(args.db)
    started = time.time()
    run_manifest = {"stage": args.stage, "variant": args.declaration, "commit": _commit(), "declaration": declaration.as_dict(), "selection_hash": manifest["selection_hash"],
                    "selection_version": manifest["selection_version"], "series": [r["id"] for r in rows],
                    "windows": {w: {**WINDOWS[w], "origin": WINDOWS[w]["origin"].isoformat()} for w in windows}, "scenarios": scenarios, "policies": policies,
                    "dataset_manifest": loader.manifest_record(conn), "python": platform.python_version(), "platform": platform.platform(),
                    "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started))}
    counts = {"runs": 0, "complete": 0, "failed": 0}
    with open(runs_path, "a") as sink:
        for i, row in enumerate(rows, 1):
            series = RB.load_series(conn, row["id"])
            for window_name in windows:
                window = WINDOWS[window_name]
                for scenario in scenarios:
                    try:
                        req, record = RB.build_request(series, window["origin"], scenario=scenario, declaration=declaration)
                        periods = window["reviews"] - 1 + req.horizon if window["rolling"] else window["reviews"]
                        seed = _supply_seed(row["id"], window_name, scenario)
                        world, world_record = T.truth_world(req, series, window["origin"], periods=periods, seed=seed)
                    except Exception as exc:  # noqa: BLE001 - recorded for every policy
                        for policy in policies:
                            sink.write(json.dumps({"series_id": row["id"], "window": window_name, "scenario": scenario, "policy": policy, "status": "BUILD_FAILED",
                                                   "error": f"{type(exc).__name__}: {exc}"}) + "\n")
                            counts["runs"] += 1
                            counts["failed"] += 1
                        continue
                    for policy in policies:
                        result = run_one(row, window_name, scenario, policy, req=req, record=record, world=world, declaration=declaration, variant=args.declaration)
                        result["truth"] = world_record
                        sink.write(json.dumps(result, default=str) + "\n")
                        sink.flush()
                        counts["runs"] += 1
                        counts["complete" if result["status"] == "COMPLETE" else "failed"] += 1
            print(f"[{i}/{len(rows)}] {row['id']} done; runs {counts['runs']} complete {counts['complete']} failed {counts['failed']} elapsed {time.time() - started:.0f}s", flush=True)
    conn.close()
    run_manifest.update({"finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_seconds": time.time() - started,
                         "cpu_seconds_process": time.process_time(), "peak_rss_mb": _peak_rss_mb(), **counts})
    (stage_dir / "run_manifest.json").write_text(json.dumps(run_manifest, indent=2, default=str) + "\n")
    print(json.dumps({k: run_manifest[k] for k in ("stage", "variant", "runs", "complete", "failed", "wall_seconds", "peak_rss_mb")}))
    return 0 if counts["runs"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
