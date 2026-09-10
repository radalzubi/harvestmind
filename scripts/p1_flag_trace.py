"""Protection-state trace per review (T stage 1 of the two-blocker closure): where FALSE_PROTECTION_RISK
and the other ownership drivers come from, on P1 fixtures (rolling replay of ZAAD, 52 reviews) and on
P0 cells (legacy replay). Read-only: replays ZAAD with kept planning requests, then evaluates
`protection_profile` on every kept request and records the row's protection, lean baseline, driver
spreads, inbound at risk, activity, regime, flags and the inherited stock the replay reports.

usage: PYTHONPATH=. python3 -m scripts.p1_flag_trace T_combined_realistic:41003 G_freight_tiers:41001 cell:15 ...
Output: docs/zaad_full/evidence/p1/closure/flag_trace_<name>_<seed>.json"""
from __future__ import annotations

import json
import sys

from scripts.p1_fixtures import build
from zaad.full.contracts import Request
from zaad.full.evaluation import long_truth
from zaad.full.planner import protection_profile, supply_profiles
from zaad.full.replay import replay
from zaad.full.worlds import forecast_all

PRODUCT = {k: Request.model_fields[k].default for k in ("stratified_scenarios", "timing_tiebreak", "analytic_shortage")}


def rows_for(req: Request) -> list[dict]:
    fits = forecast_all(req)
    out = []
    for row in protection_profile(req, fits, supply_profiles(req)):
        st = row["state"]
        key = f"{row['sku']}|{row['location']}"
        out.append({"sku": row["sku"], "location": row["location"],
                    "on_hand": sum(x.usable for x in req.stock if x.sku == row["sku"] and x.location == row["location"]),
                    "pipeline_units": sum(p.expected_accepted_remaining for p in req.pipeline if next(s for s in req.sources if s.id == p.source).sku == row["sku"]),
                    "inherited_on_hand": (req.inherited_on_hand or {}).get(key),
                    "mu": row["mean_demand_per_period"], "window": row["replenishment_periods"],
                    "protection_units": row["protection_units"], "lean_baseline_units": st["lean_baseline_units"],
                    "incremental_protection_units": st["incremental_protection_units"],
                    "ratio_protection_to_lean": (row["protection_units"] / st["lean_baseline_units"] if st["lean_baseline_units"] > 0 else None),
                    "drivers": {k: round(v, 3) for k, v in (row.get("drivers") or row.get("risk_drivers") or row.get("protection_drivers") or {}).items()},
                    "calibration": {s.id: {k: fits[s.id]["uncertainty"].get(k) for k in ("calibration_ratio", "calibration_ratio_raw", "level_se", "regime_age", "residual_sd")} for s in req.services if s.sku == row["sku"] and req.engine_profile == "reliability"},
                    "sd_fitted": {s.id: fits[s.id].get("sd") for s in req.services if s.sku == row["sku"]},
                    "activity": st["activity"], "demand_score": st["demand_score"], "supply_score": st["supply_score"],
                    "regime": st["regime"], "flags": st["flags"], "risk_active": st["risk_active"], "decaying": st["decaying"],
                    "active_drivers": st["active_drivers"], "lean_base_stock_units": st["lean_base_stock_units"]})
    return out


def main():
    for spec in sys.argv[1:]:
        name, seed = spec.split(":")
        seed = int(seed)
        kept: list[Request] = []
        if name == "cell":
            import scripts.run_zaad_full_benchmark as B
            cell = next(c for c in B.cells("v7") if c["cell"] == seed)
            req = B.request_for(cell, 38001).model_copy(update={"adaptive_escalation": True, "adaptive_solve_budget": True, "joint_recovery_rule": "deficit"})
            truth = B.truth_for(req, cell, 38001)
            out = replay(req, truth, cell["horizon"], "gated", keep_requests=kept)
            tag = f"cell{seed}"
        else:
            req = build(name, seed).model_copy(update=PRODUCT)
            truth = long_truth(req, seed + 10000, 72)
            out = replay(req, truth, 52, "gated", rolling=True, keep_requests=kept)
            tag = f"{name}_{seed}"
        records = []
        for t, r in enumerate(kept):
            rows = rows_for(r)
            records.append({"review": t, "rows": rows,
                            "purchases": [(p["source"], round(p["quantity"], 1)) for p in out["reviews"][t]["purchases"]] if t < len(out["reviews"]) else None,
                            "owner": (out["reviews"][t].get("orchestration") or {}).get("planner_owner") if t < len(out["reviews"]) else None})
        json.dump({"name": name, "seed": seed, "status": out["status"], "reviews": records}, open(f"docs/zaad_full/evidence/p1/closure/flag_trace_{tag}.json", "w"), indent=1, default=str)
        flagged = [(x["review"], r["sku"], round(r["ratio_protection_to_lean"] or 0, 2), r["drivers"], round(r["on_hand"]), round(r["pipeline_units"]), round(r["activity"], 3))
                   for x in records for r in x["rows"] if "FALSE_PROTECTION_RISK" in r["flags"]]
        print(f"{tag}: status {out['status']} reviews {len(records)} | FALSE_PROTECTION_RISK on {len(flagged)} sku-reviews; owners {dict((o, sum(1 for x in records if x['owner'] == o)) for o in set(x['owner'] for x in records))}")
        for f in flagged[:12]:
            print("   ", f)


if __name__ == "__main__":
    main()
