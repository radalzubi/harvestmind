#!/usr/bin/env python3
"""Recovery study: does temporary protection unwind, and how fast?

Replays the long-horizon v4 cells (disruption then recovery, surge then normalization,
sustained decrease, supplier deterioration then recovery, route closure then restoration)
with the gated planner under two profiles and reports, per replay:

    peak_protection_units        highest recommended protection over the reviews
    peak_inventory_periods       highest on-hand inventory in periods of demand
    detect_review                first review whose protection state is PROTECT or activity >= .3
    reduce_review                first review after the peak where protection falls by 20%
    half_life_reviews            reviews after the peak until extra inventory halves
    lean_review                  first review after the peak where the state is LEAN
    excess_remaining_units       on-hand minus lean baseline at the last review
    service_during_unwind        unit fill from the peak review to the end
    service_overall              unit fill over the replay

Development4 / validation4 only.

    python scripts/study_zaad_recovery.py --split development4 --output out.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_zaad_full_benchmark import LONG_HORIZON, SEEDS, cells, request_for, truth_for  # noqa: E402
from zaad.full.replay import replay  # noqa: E402

PROFILES = {"gated_pr30": "gated_pr30", "gated_v4": "gated"}


def measure(rows: list[dict], asset: float) -> dict:
    protection = [sum(p["protection_units"] for p in (r.get("protection") or [])) for r in rows]
    lean = [sum(p["lean_baseline_units"] for p in (r.get("protection") or [])) for r in rows]
    on_hand = [sum(p["on_hand_units"] for p in (r.get("protection") or [])) for r in rows]
    regimes = [(r.get("protection") or [{}])[0].get("regime") for r in rows]
    activity = [max((p["activity"] for p in (r.get("protection") or [])), default=0.) for r in rows]
    demand = [sum(s["demand"] for s in r["settlement"]["service_by_period"]) for r in rows]
    served = [sum(s["served"] for s in r["settlement"]["service_by_period"]) for r in rows]
    mean_demand = max(1e-9, sum(demand) / max(1, len(demand)))
    inv_periods = [x["inventory_value"] / (asset * mean_demand) for r in rows for x in r["settlement"]["trace"]]
    if not protection:
        return {}
    peak = max(range(len(protection)), key=lambda i: protection[i])
    detect = next((i for i, (g, a) in enumerate(zip(regimes, activity)) if g == "PROTECT" or a >= .3), None)
    reduce = next((i for i in range(peak + 1, len(protection)) if protection[i] <= .8 * protection[peak]), None)
    extra = [max(0., h - b) for h, b in zip(on_hand, lean)]
    half = next((i - peak for i in range(peak + 1, len(extra)) if extra[i] <= .5 * extra[peak]), None) if extra[peak] > 0 else 0
    lean_review = next((i for i in range(peak + 1, len(regimes)) if regimes[i] == "LEAN"), None)
    unwind_demand = sum(demand[peak:])
    return {"peak_protection_units": protection[peak], "peak_review": peak, "peak_inventory_periods": max(inv_periods),
            "detect_review": detect, "reduce_review": reduce, "half_life_reviews": half, "lean_review": lean_review,
            "excess_remaining_units": extra[-1], "service_during_unwind": sum(served[peak:]) / unwind_demand if unwind_demand else None,
            "service_overall": sum(served) / max(1e-9, sum(demand)), "final_inventory_periods": inv_periods[-1],
            "regimes": regimes, "protection_units": [round(p, 1) for p in protection], "activity": [round(a, 2) for a in activity]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["development4", "validation4"], default="development4")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Refusing to overwrite evidence")
    selected = [c for c in cells("v4") if c["horizon"] == 20 and (c["demand"] in LONG_HORIZON or c["supply"] in LONG_HORIZON)]
    report = []
    for cell in selected:
        for seed in SEEDS[args.split]:
            req = request_for(cell, seed)
            truth = truth_for(req, cell, seed)
            for label, method in PROFILES.items():
                result = replay(req, truth, req.horizon, method)
                row = {"cell": cell["cell"], "seed": seed, "profile": label, "demand": cell["demand"], "supply": cell["supply"],
                       "alternative": cell["alternative"], "network": cell["network"], "status": result["status"]}
                if result["status"] == "COMPLETE":
                    row.update(measure(result["reviews"], req.skus[0].asset_value))
                report.append(row)
                print(f"cell {cell['cell']:2d} seed {seed} {label:10s} {cell['demand']:20s} {cell['supply']:22s} {row['status']:9s} "
                      f"peak {row.get('peak_protection_units', 0):.0f}@{row.get('peak_review')} detect {row.get('detect_review')} reduce {row.get('reduce_review')} "
                      f"half {row.get('half_life_reviews')} lean {row.get('lean_review')} excess {row.get('excess_remaining_units', 0):.0f} "
                      f"svc_unwind {row.get('service_during_unwind') or 0:.3f} inv_final {row.get('final_inventory_periods', 0):.2f}", flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
