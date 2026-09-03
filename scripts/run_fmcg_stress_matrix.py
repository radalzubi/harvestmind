"""Commercial stress matrix (section 15): demand CV x supplier fill x
lead-time CV x forecast bias x service target, plus edge cases.

Each cell builds a small calibrated history with the named parameters,
walks a few origins and settles every policy identically. The point is not
a headline but a MAP: where the stochastic optimizer wins, loses, and is
indifferent, and whether it ever fails unsafely. Cells where a policy
returns an unusable solver status are counted, not hidden.

Forecast bias is injected by scaling the TRAINING demand the policies see
(the truth is untouched), which is what a biased forecast does to a
planner.

Output: artifacts/fmcg_stress_matrix.json, docs/validation/evidence/fmcg_stress_matrix.md
"""
from __future__ import annotations

import argparse
import itertools
import json
import statistics as st
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backtesting.counterfactual import run_policies, summarize  # noqa: E402
from scripts.run_fmcg_counterfactuals import fold_from_history  # noqa: E402
from synthetic.fmcg.distributor_sim import ArchetypeSpec, build_history  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GRID = {
    "demand_cv": [0.05, 0.15, 0.30, 0.50, 0.80, 1.20],
    "fill": [0.99, 0.95, 0.90, 0.80, 0.60],
    "lead_cv": [0.05, 0.30, 0.60],
    "bias": [-0.30, -0.15, 0.0, 0.15, 0.30],
    "service": [0.90, 0.95, 0.97, 0.98, 0.99],
    "cover": [0.5, 1.0, 2.0, 3.0, 5.4],
}


def cell(demand_cv, fill, lead_cv, bias, service, seeds, folds, scen, n_skus, cover=38 / 7):
    edges_det, edges_out, edges_sel, fills_sp, statuses, worst = [], [], [], [], {}, 0.0
    for seed in range(seeds):
        spec = ArchetypeSpec(name="stress", n_skus=n_skus, n_suppliers=3, n_customers=6,
                             weeks=110, demand_cv=demand_cv, fill_mean=fill, fill_sd=0.03,
                             lead_mean_weeks=2.0, lead_cv=lead_cv, service_target=service)
        h = build_history("stress", seed=seed, spec=spec)
        rng = np.random.default_rng(seed + 77)
        for oi in np.linspace(54, 110 - 12 - 1, folds).astype(int):
            fi, truth = fold_from_history(h, int(oi), 12, 52, cover, service)
            if bias:
                for j in fi.train_demand:
                    fi.train_demand[j] = [x * (1 + bias) for x in fi.train_demand[j]]
            cap = sum(st.mean(fi.train_demand[j]) for j in fi.products) * 8.0
            res = run_policies(fi, truth, cap, rng, n_scen=scen,
                               policies=("order_up_to", "deterministic_sp", "stochastic_sp", "selected"))
            for pol, r in res.items():
                statuses[pol] = statuses.get(pol, {}); statuses[pol][r["status"]] = statuses[pol].get(r["status"], 0) + 1
            sp = res["stochastic_sp"]["settlement"]; det = res["deterministic_sp"]["settlement"]
            out = res["order_up_to"]["settlement"]; sel = res["selected"]["settlement"]
            if sel and det and det.total > 0:
                edges_sel.append((det.total - sel.total) / det.total * 100)
            if sp is None:
                continue
            fills_sp.append(sp.fill_rate)
            if det and det.total > 0:
                e = (det.total - sp.total) / det.total * 100; edges_det.append(e); worst = min(worst, e)
            if out and out.total > 0:
                edges_out.append((out.total - sp.total) / out.total * 100)
    return {"vs_deterministic": summarize(edges_det, boot=300), "vs_order_up_to": summarize(edges_out, boot=300),
            "selected_vs_deterministic": summarize(edges_sel, boot=300),
            "sp_service": st.mean(fills_sp) if fills_sp else None, "solver_status": statuses}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seeds", type=int, default=2)
    p.add_argument("--folds", type=int, default=2)
    p.add_argument("--scenarios", type=int, default=15)
    p.add_argument("--skus", type=int, default=12)
    p.add_argument("--axes", default="demand_cv,fill", help="which axes to sweep jointly; others at base")
    a = p.parse_args()
    axes = a.axes.split(",")
    base = {"demand_cv": 0.30, "fill": 0.95, "lead_cv": 0.30, "bias": 0.0, "service": 0.97, "cover": 38 / 7}
    t0 = time.time(); cells = []
    combos = list(itertools.product(*[GRID[ax] for ax in axes]))
    for combo in combos:
        params = dict(base); params.update(dict(zip(axes, combo)))
        r = cell(params["demand_cv"], params["fill"], params["lead_cv"], params["bias"],
                 params["service"], a.seeds, a.folds, a.scenarios, a.skus, params["cover"])
        cells.append({"params": params, **r})
        v = r["vs_deterministic"]
        print(f"  {params}  vs det {v.get('median', float('nan')):+6.2f}%  win {v.get('win_rate', 0):.0%}  "
              f"worst {v.get('worst', float('nan')):+6.1f}%  service {r['sp_service'] or 0:.1%}", flush=True)
    out = {"classification": "SYNTHETIC CALIBRATED", "axes": axes, "base": base,
           "config": vars(a), "elapsed_s": round(time.time() - t0, 1), "cells": cells}
    (ROOT / "artifacts").mkdir(exist_ok=True)
    (ROOT / "artifacts" / f"fmcg_stress_{'_'.join(axes)}.json").write_text(json.dumps(out, indent=1))
    md = ROOT / "docs" / "validation" / "evidence"; md.mkdir(parents=True, exist_ok=True)
    lines = [f"# FMCG stress matrix over {axes} (SYNTHETIC CALIBRATED)", "",
             f"base {base}; seeds {a.seeds}, folds {a.folds}, scenarios {a.scenarios}, skus {a.skus}", "",
             "| " + " | ".join(axes) + " | SP vs deterministic (median) | win | worst | SELECTED vs deterministic | vs order-up-to | SP service | unusable solves |",
             "|" + "---|" * (len(axes) + 7)]
    for c in cells:
        v = c["vs_deterministic"]; o = c["vs_order_up_to"]; sl = c["selected_vs_deterministic"]
        bad = sum(n for pol, d in c["solver_status"].items() for s_, n in d.items() if s_ not in ("optimal", "feasible", "heuristic"))
        lines.append("| " + " | ".join(str(c["params"][ax]) for ax in axes) +
                     f" | {v.get('median', float('nan')):+.2f}% | {v.get('win_rate', 0):.0%} | {v.get('worst', float('nan')):+.1f}% | "
                     f"{sl.get('median', float('nan')):+.2f}% (win {sl.get('win_rate', 0):.0%}) | "
                     f"{o.get('median', float('nan')):+.2f}% | {(c['sp_service'] or 0):.1%} | {bad} |")
    (md / f"fmcg_stress_{'_'.join(axes)}.md").write_text("\n".join(lines) + "\n")
    print(f"wrote stress matrix ({out['elapsed_s']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
