#!/usr/bin/env python3
"""Decompose where the reliability profile's extra inventory comes from, one switch at a time.

Replays chosen reliability-matrix cells with the gated planner under ablations of the
profile's protection components and reports inventory, service, cost and the policies the
selector picked. Diagnosis only: it monkeypatches module functions in-process and writes a
JSON record; it never changes engine behaviour.

    python scripts/diagnose_zaad_false_protection.py --seed 26001 --cells 1 23 25 --output out.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics as st
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import zaad.full.planner as planner  # noqa: E402
import zaad.full.uncertainty as unc  # noqa: E402
import zaad.full.worlds as worlds  # noqa: E402
from scripts.run_zaad_full_benchmark import cells, request_for, truth_for  # noqa: E402
from zaad.full.replay import replay  # noqa: E402

ORIGINAL_DEMAND_UNCERTAINTY = unc.demand_uncertainty
ORIGINAL_TARGETS = planner.targets


def variant_patches(name: str):
    """Return (request update, patch function, unpatch function) for one ablation."""
    update: dict = {}

    def keep():
        pass

    if name == "frozen_pr24":
        update = {"engine_profile": "pr24"}
    elif name == "pr30":
        update = {"protection_decay": False}
    elif name == "reliability_full":
        pass
    elif name == "no_cvar":
        update = {"service_risk_level": 0.}
    elif name == "no_stress_weight":
        update = {"stress_weight": 0.}
    elif name == "no_calibration_widening":
        def patched(fit, y):
            out = ORIGINAL_DEMAND_UNCERTAINTY(fit, y)
            out["calibration_ratio"] = 1.
            return out
        return update, lambda: setattr(worlds, "demand_uncertainty", patched), lambda: setattr(worlds, "demand_uncertainty", ORIGINAL_DEMAND_UNCERTAINTY)
    elif name == "no_level_uncertainty":
        def patched_level(fit, y):
            out = ORIGINAL_DEMAND_UNCERTAINTY(fit, y)
            out["level_se"] = 0.
            out["regime_uncertainty"] = 0.
            return out
        return update, lambda: setattr(worlds, "demand_uncertainty", patched_level), lambda: setattr(worlds, "demand_uncertainty", ORIGINAL_DEMAND_UNCERTAINTY)
    elif name == "frozen_proxy_buffer":
        def frozen_targets(req, buffer=1.645):
            return ORIGINAL_TARGETS(req.model_copy(update={"engine_profile": "pr24"}), buffer)
        return update, lambda: setattr(planner, "targets", frozen_targets), lambda: setattr(planner, "targets", ORIGINAL_TARGETS)
    elif name == "lean_all":
        update = {"service_risk_level": 0., "stress_weight": 0.}
        def patched_all(fit, y):
            out = ORIGINAL_DEMAND_UNCERTAINTY(fit, y)
            out["calibration_ratio"] = 1.
            out["level_se"] = 0.
            out["regime_uncertainty"] = 0.
            return out
        return update, lambda: setattr(worlds, "demand_uncertainty", patched_all), lambda: setattr(worlds, "demand_uncertainty", ORIGINAL_DEMAND_UNCERTAINTY)
    else:
        raise SystemExit(f"unknown variant {name}")
    return update, keep, keep


VARIANTS = ["frozen_pr24", "pr30", "reliability_full", "no_cvar", "no_stress_weight", "no_calibration_widening",
            "no_level_uncertainty", "frozen_proxy_buffer", "lean_all"]


def run(cell: dict, seed: int, name: str) -> dict:
    update, patch, unpatch = variant_patches(name)
    req = request_for(cell, seed)
    if update:
        req = req.model_copy(update=update)
    truth = truth_for(req, cell, seed)
    patch()
    try:
        result = replay(req, truth, req.horizon, "gated")
    finally:
        unpatch()
    rows = result["reviews"]
    demand = sum(s["demand"] for r in rows for s in r["settlement"]["service_by_period"])
    served = sum(s["served"] for r in rows for s in r["settlement"]["service_by_period"])
    inventory = [x["inventory_value"] for r in rows for x in r["settlement"]["trace"]]
    asset = req.skus[0].asset_value
    return {"variant": name, "status": result["status"], "cost": result.get("economic_cost"),
            "service": served / demand if demand else None,
            "inventory_periods": st.mean(inventory) / (asset * max(1e-9, demand / max(1, len(rows)))) if inventory else None,
            "policies": [r["warnings"][1] if len(r["warnings"]) > 1 else None for r in rows],
            "purchases": [sum(p["quantity"] for p in r["purchases"]) for r in rows]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=26001)
    parser.add_argument("--cells", nargs="+", type=int, default=[1])
    parser.add_argument("--variants", nargs="+", default=VARIANTS)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    grid = {c["cell"]: c for c in cells("reliability")}
    report = []
    for index in args.cells:
        cell = grid[index]
        label = f"cell {index}: inv={cell['inventory']} demand={cell['demand']} supply={cell['supply']} net={cell['network']} alt={cell['alternative']} target={cell['target']}"
        print(label)
        for name in args.variants:
            row = run(cell, args.seed, name)
            row.update({"cell": index, "seed": args.seed})
            report.append(row)
            print(f"  {name:24s} inv {row['inventory_periods']!s:.5} svc {row['service']!s:.5} cost {row['cost']!s:.7} buys {[round(q) for q in row['purchases']]}")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
