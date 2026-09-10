"""Does SAFE_SELECTED avoid the standalone stochastic optimizer's easy-period
downside while keeping its value when conditions bind?

FROZEN DESIGN. The configuration below was fixed before the evaluation
seeds were run, and the evaluation seeds (100+) were never used while
building or tuning any policy. No fold is filtered on its outcome
strata
are reported. Every policy runs closed-loop (re-plan every review period,
own state carried) on identical realised paths through one settlement.

Output: artifacts/safe_policy_validation.json,
        docs/validation/evidence/safe_policy_validation.md
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backtesting.counterfactual import (  # noqa: E402
    EXTRA_CANDIDATES, policy_deterministic_sp, policy_order_up_to, policy_stochastic_sp, summarize,
)
from backtesting.regime import diagnose, summarize as regime_summary  # noqa: E402
from backtesting.safe_selector import SafeSelectionConfig, safe_select  # noqa: E402
from scripts.run_fmcg_counterfactuals import fold_from_history  # noqa: E402
from synthetic.fmcg.distributor_sim import ARCHETYPES, ArchetypeSpec, build_history  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FROZEN = {
    "safe": dict(n_folds=4, n_holdout_folds=2, holdout=4, min_history=26, min_rel_improvement=0.03,
                 service_tolerance=0.01, max_regret_share=0.10, confidence=0.80, block_length=2, n_boot=400),
    "scenarios": 20, "review": 4, "horizon": 12, "train": 52, "run_periods": 32,
    "regimes": {
        "calm_deep_cover":    {"archetype": "A_stable", "cover": 5.4, "holding": 0.02 / 4.33},
        "calm_thin_cover":    {"archetype": "A_stable", "cover": 0.5, "holding": 0.02 / 4.33},
        "volatile":           {"archetype": "B_volatile_retail", "cover": 2.0, "holding": 0.02 / 4.33},
        "constrained":        {"archetype": "C_constrained_supplier", "cover": 2.0, "holding": 0.02 / 4.33},
        "importer":           {"archetype": "D_importer", "cover": 3.0, "holding": 0.02 / 4.33},
        "mixed":              {"archetype": "E_mixed_portfolio", "cover": 2.0, "holding": 0.02 / 4.33},
        "disruption":         {"archetype": "F_disruption", "cover": 2.0, "holding": 0.02 / 4.33},
        "calm_high_carry":    {"archetype": "A_stable", "cover": 2.0, "holding": 0.046},
        "volatile_high_carry": {"archetype": "B_volatile_retail", "cover": 2.0, "holding": 0.046},
    },
    "eval_seeds": [100, 101, 102],
}
POLICIES = ("incumbent", "order_up_to", "deterministic_sp", "stochastic_sp", "anchored_sp", "safe_selected")


def rolling(policy, h, start, n_run, a, cfg_safe, cover, holding, rng, cap_weeks=8.0, dro=False):
    """Closed loop with a per-policy state; returns settlement totals and
    the selection log. Inlined rather than reusing rolling_evaluate so the
    incumbent and the safe selector can participate."""
    from backtesting.counterfactual import policy_anchored_sp
    fi0, _ = fold_from_history(h, start, a.horizon, a.train, cover, 0.95, holding)
    products, sup_of, lead_of = fi0.products, fi0.supplier_of, fi0.lead_of
    horizon = max(a.horizon, 2 * max(lead_of.values()) + a.review)
    ol = h.order_lines.copy()
    ol["week"] = ol["order_id"].str[4:8].astype(int)
    dem = ol.groupby(["sku", "week"])["qty_ordered"].sum()
    po = h.purchase_orders.copy()
    po["week"] = (pd.to_datetime(po["po_date"]) - pd.to_datetime(h.purchase_orders["po_date"].min())).dt.days // 7
    rec = h.receipts.groupby("po_id")["qty_received"].sum()
    po = po.join(rec, on="po_id").fillna({"qty_received": 0.0})
    po["fill"] = (po["qty_received"] / po["qty_ordered"]).clip(0, 1)
    truth_f = {}
    for s_ in set(sup_of.values()):
        sub = po[po["supplier_id"] == s_]
        base = float(sub[sub["week"] < start]["fill"].mean()) if len(sub[sub["week"] < start]) else 0.95
        for t in range(n_run + horizon):
            row = sub[sub["week"] == start + t]
            truth_f[(s_, t)] = float(row["fill"].mean()) if len(row) else base
    cap_total = sum(st.mean(fi0.train_demand[j]) for j in products) * cap_weeks
    cc = fi0.policy.cost_config
    carry = cc.holding_rate_per_period
    on_hand = dict(fi0.opening)
    arrivals: dict = {}
    holding_c = shortage = 0.0
    served = demanded = inv_sum = 0.0
    selections: dict = {}
    changes = []
    solve_t = []
    prev_sched = None
    t = 0
    while t < n_run:
        pipeline = {(j, tt - t): q for (j, tt), q in arrivals.items() if tt >= t and tt - t < horizon}
        fi, _ = fold_from_history(h, start + t, horizon, a.train, cover, 0.95, holding)
        fi.opening = dict(on_hand)
        fi.pipeline = dict(pipeline)
        t0 = time.perf_counter()
        if policy == "incumbent":
            sched = fi.incumbent.build_schedule(fi)
            mode = "incumbent"
        elif policy == "order_up_to":
            sched = policy_order_up_to(fi)
            mode = policy
        elif policy == "deterministic_sp":
            sched, _m = policy_deterministic_sp(fi, cap_total, rng)
            mode = policy
        elif policy == "stochastic_sp":
            sched, _m = policy_stochastic_sp(fi, cap_total, rng, a.scenarios)
            mode = policy
        elif policy == "anchored_sp":
            sched, _m = policy_anchored_sp(fi, cap_total, rng, a.scenarios)
            mode = policy
        elif policy == "dro":
            sched, _m = EXTRA_CANDIDATES["dro"](fi, cap_total, rng, a.scenarios)
            mode = policy
        else:
            d = safe_select(fi, cap_total, rng, cfg_safe, extra_candidates={"anchored_sp": policy_anchored_sp}
                            if not dro else EXTRA_CANDIDATES)
            sched, mode = d.schedule, d.mode_run
        solve_t.append(time.perf_counter() - t0)
        if sched is None:
            sched = fi.incumbent.build_schedule(fi)
            mode = "incumbent(fallback)"
        selections[mode] = selections.get(mode, 0) + 1
        if prev_sched is not None:
            tot = sum(v for (i, j, tt), v in sched.items() if tt < a.review) or 1.0
            changes.append(sum(abs(sched.get(k, 0.0) - prev_sched.get(k, 0.0))
                               for k in set(sched) | set(prev_sched) if k[2] < a.review) / tot)
        prev_sched = sched
        for (sup, sku, rel_t), q in sched.items():
            if rel_t >= a.review or q <= 0:
                continue
            q = min(float(q), float(fi.capacity.get(sku, q)))
            key = (sku, t + rel_t + int(lead_of[sup]))
            arrivals[key] = arrivals.get(key, 0.0) + q * float(truth_f.get((sup, t + rel_t), 1.0))
        for step in range(a.review):
            at = t + step
            if at >= n_run:
                break
            stock = 0.0
            for j in products:
                dm = float(dem.get((j, start + at), 0.0))
                have = on_hand.get(j, 0.0) + arrivals.pop((j, at), 0.0)
                got = min(have, dm)
                short = max(dm - have, 0.0)
                shortage += short * fi0.margin[j]
                left = max(have - dm, 0.0)
                on_hand[j] = left
                stock += left
                served += got
                demanded += dm
            if stock > cap_total > 0:
                scale = cap_total / stock
                for j in on_hand:
                    on_hand[j] *= scale
            for j in products:
                holding_c += on_hand[j] * fi0.unit_cost[j] * carry
                inv_sum += on_hand[j]
        t += a.review
    return {"total": holding_c + shortage, "holding": holding_c, "shortage": shortage,
            "fill": served / demanded if demanded else 1.0, "avg_inventory": inv_sum / max(n_run, 1),
            "selections": selections, "plan_change": float(np.mean(changes)) if changes else 0.0,
            "solve_p50": float(np.median(solve_t)) if solve_t else 0.0}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--regimes", default="all")
    p.add_argument("--seeds", default=",".join(map(str, FROZEN["eval_seeds"])))
    p.add_argument("--run-periods", type=int, default=FROZEN["run_periods"])
    p.add_argument("--review", type=int, default=FROZEN["review"])
    p.add_argument("--horizon", type=int, default=FROZEN["horizon"])
    p.add_argument("--train", type=int, default=FROZEN["train"])
    p.add_argument("--scenarios", type=int, default=FROZEN["scenarios"])
    p.add_argument("--small", action="store_true")
    p.add_argument("--with-dro", action="store_true")
    a = p.parse_args()
    cfg_safe = SafeSelectionConfig(**FROZEN["safe"], n_scen=a.scenarios)
    names = list(FROZEN["regimes"]) if a.regimes == "all" else a.regimes.split(",")
    pols = list(POLICIES) + (["dro"] if a.with_dro else [])
    results = {}
    t_all = time.time()
    for name in names:
        spec_r = FROZEN["regimes"][name]
        spec = ARCHETYPES[spec_r["archetype"]]
        if a.small:
            spec = ArchetypeSpec(**{**spec.__dict__, "n_skus": 16, "n_suppliers": 3, "n_customers": 6, "weeks": 110})
        runs = {pol: [] for pol in pols}
        sel_all: dict = {}
        regime_counts: dict = {}
        for seed in [int(x) for x in a.seeds.split(",")]:
            h = build_history(spec_r["archetype"], seed=seed, spec=spec)
            start = a.train + 2
            n_run = min(a.run_periods, spec.weeks - start - 1 - a.horizon)
            fi_diag, _ = fold_from_history(h, start, a.horizon, a.train, spec_r["cover"], 0.95, spec_r["holding"])
            for k, v in regime_summary(diagnose(fi_diag))["counts"].items():
                regime_counts[k] = regime_counts.get(k, 0) + v
            for pol in pols:
                r = rolling(pol, h, start, n_run, a, cfg_safe, spec_r["cover"], spec_r["holding"],
                            np.random.default_rng(seed + 7), dro=a.with_dro)
                runs[pol].append(r)
                if pol == "safe_selected":
                    for k, v in r["selections"].items():
                        sel_all[k] = sel_all.get(k, 0) + v
        inc = runs["incumbent"]
        out = {"archetype": spec_r["archetype"], "cover": spec_r["cover"], "holding": spec_r["holding"],
               "n_runs": len(inc), "sku_regimes": regime_counts, "safe_selections": sel_all, "policies": {}}
        for pol in pols:
            deltas = [(b["total"] - c["total"]) / b["total"] * 100 for b, c in zip(inc, runs[pol]) if b["total"] > 0]
            out["policies"][pol] = {
                "delta_vs_incumbent_pct": summarize(deltas, boot=300),
                "mean_cost": st.mean(r["total"] for r in runs[pol]),
                "mean_holding": st.mean(r["holding"] for r in runs[pol]),
                "mean_shortage": st.mean(r["shortage"] for r in runs[pol]),
                "fill": st.mean(r["fill"] for r in runs[pol]),
                "fill_diff_vs_incumbent_pt": st.mean((c["fill"] - b["fill"]) * 100 for b, c in zip(inc, runs[pol])),
                "avg_inventory": st.mean(r["avg_inventory"] for r in runs[pol]),
                "plan_change": st.mean(r["plan_change"] for r in runs[pol]),
                "solve_p50_s": st.mean(r["solve_p50"] for r in runs[pol]),
                "worst_delta_pct": min(deltas) if deltas else None,
            }
        results[name] = out
        s_ = out["policies"]
        print(f"{name:<22} SP {s_['stochastic_sp']['delta_vs_incumbent_pct'].get('median', float('nan')):+6.1f}%  "
              f"SAFE {s_['safe_selected']['delta_vs_incumbent_pct'].get('median', float('nan')):+6.1f}% "
              f"(worst {s_['safe_selected']['worst_delta_pct']:+.1f}%)  ANCH {s_['anchored_sp']['delta_vs_incumbent_pct'].get('median', float('nan')):+6.1f}%  "
              f"OUT {s_['order_up_to']['delta_vs_incumbent_pct'].get('median', float('nan')):+6.1f}%  sel {sel_all}", flush=True)
    art = {"classification": "SYNTHETIC CALIBRATED", "frozen_design": FROZEN, "config": vars(a),
           "elapsed_s": round(time.time() - t_all, 1), "regimes": results}
    (ROOT / "artifacts").mkdir(exist_ok=True)
    (ROOT / "artifacts" / "safe_policy_validation.json").write_text(json.dumps(art, indent=1, default=str))
    md = ROOT / "docs" / "validation" / "evidence"
    md.mkdir(parents=True, exist_ok=True)
    lines = ["# SAFE_SELECTED validation (SYNTHETIC CALIBRATED, frozen design, unseen seeds)", "",
             f"seeds {a.seeds}; run {a.run_periods} periods; re-plan every {a.review}; scenarios {a.scenarios}; "
             f"gates {FROZEN['safe']}", "",
             "Deltas are cost reductions vs the INFERRED incumbent (positive = better), median over runs; "
             "worst is the worst single run.", "",
             "| regime | " + " | ".join(f"{p} Δ% (worst)" for p in pols) + " | SAFE fill Δpt | SAFE selections | SKU regimes |",
             "|---|" + "---|" * (len(pols) + 3)]
    for name, r in results.items():
        cells = []
        for pol in pols:
            d = r["policies"][pol]["delta_vs_incumbent_pct"]
            w = r["policies"][pol]["worst_delta_pct"]
            cells.append(f"{d.get('median', float('nan')):+.1f}% ({(w if w is not None else float('nan')):+.1f}%)")
        lines.append(f"| {name} | " + " | ".join(cells) + f" | {r['policies']['safe_selected']['fill_diff_vs_incumbent_pt']:+.2f} | "
                     f"{r['safe_selections']} | {r['sku_regimes']} |")
    (md / "safe_policy_validation.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote artifacts/safe_policy_validation.json ({art['elapsed_s']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
