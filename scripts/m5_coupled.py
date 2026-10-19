"""Walmart M5, Experiment B: coupled purchasing commitments per store group.

    python -m scripts.m5_coupled --stage smoke|all [--windows val1,val2,final] [--scenarios stable,mild_lead,fill_only] [--coupling coupled]

One run per (store group, window, scenario, policy). Policies: the production planner with `economic_lot` as its declared
incumbent (`gated`), and the projected rules `economic_lot`, `reorder_point`, `periodic:1` (each applies the minimum order
value, the pallet cap and the cash cap in its projection). A breach of a shared constraint is a settlement failure
(status PHYSICAL_FAILURE), recorded as a constraint violation of that policy. Results under data/public/m5/results/
coupled_<coupling>/ (git-ignored).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import time
import traceback
from typing import Any

import numpy as np

from zaad.full.evaluation import endpoint
from zaad.full.replay import replay
from zaad.public.m5 import coupled as C, loader, request_builder as RB
from zaad.public.m5.declaration import WINDOWS
from scripts.m5_pilot import _peak_rss_mb, decision_provenance

POLICIES = ("gated", "economic_lot", "reorder_point", "periodic:1")
RESULTS_ROOT = Path("data/public/m5/results")
MANIFEST = Path("docs/remodel/evidence/m5/SELECTION_MANIFEST.json")


def _commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001 - informational
        return "unknown"


def _seed(group: list[str], window: str, scenario: str) -> int:
    return int(hashlib.sha256(("|".join(group) + f"|{window}|{scenario}|m5-coupled").encode()).hexdigest()[:8], 16) % (2 ** 31)


def group_metrics(out: dict[str, Any], req) -> dict[str, Any]:
    rows = out["reviews"]
    orders_by_review = [sum(p["quantity"] for p in r["purchases"]) for r in rows]
    order_weeks = sum(1 for b in orders_by_review if b > 1e-9)
    lines = [sum(1 for p in r["purchases"] if p["quantity"] > 1e-9) for r in rows]
    end_stock = [sum(x["quantity"] for x in r["settlement"]["end_stock"]) for r in rows]
    unmet = [sum(x["demand"] - x["served"] for x in r["settlement"]["service_by_period"]) for r in rows]
    per_service: dict[str, dict[str, float]] = {}
    for r in rows:
        for x in r["settlement"]["service_by_period"]:
            d = per_service.setdefault(x["service"], {"demand": 0., "served": 0.})
            d["demand"] += x["demand"]
            d["served"] += x["served"]
    fills = {k: (v["served"] / v["demand"] if v["demand"] > 0 else None) for k, v in per_service.items()}
    target = req.services[0].target
    residuals = [r["settlement"].get("conservation_residual") for r in rows]
    cash = [(r.get("capital") or {}) for r in rows]
    return {"reviews_completed": len(rows), "order_weeks": order_weeks, "lines_per_order_week": float(np.mean([n for n in lines if n])) if any(lines) else 0.,
            "units_ordered": float(sum(orders_by_review)), "end_stock_mean": float(np.mean(end_stock)), "end_stock_sd": float(np.std(end_stock)),
            "unmet_total": float(sum(unmet)), "stockout_reviews": sum(1 for u in unmet if u > 1e-9), "fill_by_item": fills,
            "items_below_target": sum(1 for f in fills.values() if f is not None and f < target - 1e-9), "min_item_fill": min((f for f in fills.values() if f is not None), default=None),
            "conservation_residual_max": max((abs(float(x)) for x in residuals if isinstance(x, (int, float))), default=None),
            "wall_seconds_by_review": [r.get("wall_seconds") for r in rows], "capital_notes": [c for c in cash if c][:2],
            "warnings": [str(w) for r in rows for w in (r.get("warnings") or [])][:30]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("smoke", "all"), required=True)
    ap.add_argument("--windows", default="val1,val2,final")
    ap.add_argument("--scenarios", default="stable,mild_lead,fill_only")
    ap.add_argument("--policies", default=",".join(POLICIES))
    ap.add_argument("--coupling", default="coupled", choices=sorted(C.VARIANTS))
    ap.add_argument("--out", default=str(RESULTS_ROOT))
    args = ap.parse_args()
    coupling = C.VARIANTS[args.coupling]
    windows = [w for w in args.windows.split(",") if w]
    scenarios = [s for s in args.scenarios.split(",") if s]
    policies = [p for p in args.policies.split(",") if p]
    manifest = json.loads(MANIFEST.read_text())
    groups = C.groups(manifest["series"], max_group=coupling.max_group)
    if args.stage == "smoke":
        groups, windows, scenarios = groups[:1], windows[:1], scenarios[:1]
    stage_dir = Path(args.out) / f"{'coupled_smoke' if args.stage == 'smoke' else 'coupled'}_{args.coupling}"
    stage_dir.mkdir(parents=True, exist_ok=True)
    runs_path = stage_dir / "runs.jsonl"
    if runs_path.exists():
        runs_path.unlink()
    conn = loader.connect()
    started = time.time()
    counts = {"runs": 0, "complete": 0, "failed": 0}
    with open(runs_path, "a") as sink:
        for gi, group in enumerate(groups, 1):
            series = [RB.load_series(conn, sid) for sid in group]
            for window_name in windows:
                window = WINDOWS[window_name]
                for scenario in scenarios:
                    try:
                        req, record = C.build_group_request(series, window["origin"], scenario=scenario, coupling=coupling)
                        periods = window["reviews"] - 1 + req.horizon
                        seed = _seed(group, window_name, scenario)
                        world, world_record = C.truth_world(req, series, window["origin"], periods=periods, seed=seed)
                    except Exception as exc:  # noqa: BLE001 - recorded
                        for policy in policies:
                            sink.write(json.dumps({"group": group, "window": window_name, "scenario": scenario, "policy": policy, "status": "BUILD_FAILED",
                                                   "error": f"{type(exc).__name__}: {exc}"}) + "\n")
                            counts["runs"] += 1
                            counts["failed"] += 1
                        continue
                    for policy in policies:
                        r = req if policy == "gated" else req.model_copy(update={"incumbent_rule": None})
                        base = {"group": group, "store_id": record["store_id"], "group_size": record["group_size"], "window": window_name, "origin": window["origin"].isoformat(),
                                "reviews": window["reviews"], "scenario": scenario, "policy": policy, "request": record, "coupling": args.coupling, "coupling_hash": coupling.hash(),
                                "truth": world_record, "evidence": "modelled comparison on public observed sales under SYNTHETIC coupled supplier terms; not a realized outcome"}
                        t0, c0 = time.perf_counter(), time.process_time()
                        try:
                            out = replay(r, world, window["reviews"], policy, rolling=True)
                        except Exception as exc:  # noqa: BLE001 - recorded
                            row = {**base, "status": "EXCEPTION", "error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()[-1500:],
                                   "wall_seconds": time.perf_counter() - t0, "cpu_seconds": time.process_time() - c0}
                        else:
                            rows = out.get("reviews", [])
                            row = {**base, "status": out.get("status", "UNKNOWN"), "failure": out.get("failure"), "wall_seconds": time.perf_counter() - t0, "cpu_seconds": time.process_time() - c0}
                            if rows:
                                row["derived"] = group_metrics(out, r)
                                if policy == "gated":
                                    row["provenance"] = decision_provenance(rows)
                                try:
                                    e = endpoint(r, rows, len(rows))
                                    row["endpoint"] = {k: v for k, v in e.items() if k != "ledger"}
                                    row["ledger"] = e["ledger"]
                                except Exception as exc:  # noqa: BLE001
                                    row["endpoint_error"] = f"{type(exc).__name__}: {exc}"
                        sink.write(json.dumps(row, default=str) + "\n")
                        sink.flush()
                        counts["runs"] += 1
                        counts["complete" if row["status"] == "COMPLETE" else "failed"] += 1
            print(f"[{gi}/{len(groups)}] store {series[0].store_id} ({len(series)} items) done; runs {counts['runs']} complete {counts['complete']} failed {counts['failed']} elapsed {time.time() - started:.0f}s", flush=True)
    conn.close()
    run_manifest = {"stage": args.stage, "coupling": args.coupling, "commit": _commit(), "declaration": C.coupling_record(coupling), "selection_hash": manifest["selection_hash"],
                    "groups": groups, "windows": {w: {**WINDOWS[w], "origin": WINDOWS[w]["origin"].isoformat()} for w in windows}, "scenarios": scenarios, "policies": policies,
                    "python": platform.python_version(), "platform": platform.platform(), "wall_seconds": time.time() - started, "cpu_seconds_process": time.process_time(),
                    "peak_rss_mb": _peak_rss_mb(), **counts}
    (stage_dir / "run_manifest.json").write_text(json.dumps(run_manifest, indent=2, default=str) + "\n")
    print(json.dumps({k: run_manifest[k] for k in ("stage", "coupling", "runs", "complete", "failed", "wall_seconds", "peak_rss_mb")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
