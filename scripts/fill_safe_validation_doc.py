"""Write docs/validation/SAFE_POLICY_VALIDATION.md from
artifacts/safe_policy_validation.json. No number in the report is typed."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
J = ROOT / "artifacts" / "safe_policy_validation.json"
D = ROOT / "docs" / "validation" / "SAFE_POLICY_VALIDATION.md"

STRATA = {
    "easy/slack": ["calm_deep_cover"],
    "stable": ["calm_deep_cover", "calm_thin_cover", "calm_high_carry"],
    "volatile": ["volatile", "volatile_high_carry", "mixed"],
    "binding": ["calm_thin_cover", "constrained", "importer"],
    "disruption": ["disruption"],
    "low carry cost": ["calm_deep_cover", "calm_thin_cover", "volatile", "constrained", "importer", "mixed", "disruption"],
    "high carry cost": ["calm_high_carry", "volatile_high_carry"],
}


def main() -> int:
    if not J.exists():
        print("no artifact yet")
        return 1
    d = json.load(open(J))
    regs = d["regimes"]
    pols = list(next(iter(regs.values()))["policies"])
    fz = d["frozen_design"]
    L = ["# SAFE_SELECTED validation", "",
         "**Classification: SYNTHETIC CALIBRATED.** Every number below is written by "
         "`scripts/fill_safe_validation_doc.py` from `artifacts/safe_policy_validation.json`, "
         "produced by `scripts/run_safe_policy_validation.py`. Nothing here is a realised saving; "
         "no real operator's data has been evaluated.", "",
         "## Question", "",
         "Does SAFE_SELECTED avoid the standalone stochastic optimizer's easy-period downside "
         "while retaining its value when conditions bind?", "",
         "## Methodology", "",
         f"- Frozen design: gates `{fz['safe']}`, scenarios {fz['scenarios']}, review {fz['review']}, "
         f"horizon {fz['horizon']}, train {fz['train']}, run {fz['run_periods']} periods, evaluation seeds "
         f"{fz['eval_seeds']} (never used while building or tuning). Elapsed {d['elapsed_s']} s.",
         "- Closed loop: every policy re-plans every review period with its own state on identical realised paths "
         "through one settlement; supplier capacity binds every policy.",
         "- The incumbent is INFERRED from the simulated operator's own PO log and is the reference for every delta.",
         "- Leakage: each inner selection fold trains on history strictly before its origin (demand AND recorded "
         "supplier events) and is scored on what followed; hold-out folds are used only to confirm a winner "
         "(`tests/unit/test_safe_selector.py`).",
         "- No fold or run is filtered on its outcome. Strata are reported, never removed.",
         "- Inference within the selector is a moving-block bootstrap over overlapping folds.", "",
         "## Results by regime", "",
         "Δ% = (incumbent cost − policy cost) / incumbent cost, median over runs; (worst) = worst single run. "
         "Positive is better than the incumbent.", "",
         "| regime | archetype | cover wk | carry/wk | " + " | ".join(f"{p} Δ% (worst)" for p in pols)
         + " | SAFE fill Δpt | SAFE avg inv / incumbent | SAFE plan change | SAFE selections |",
         "|---|---|---|---|" + "---|" * (len(pols) + 4)]
    for name, r in regs.items():
        cells = []
        for p in pols:
            s_ = r["policies"][p]["delta_vs_incumbent_pct"]
            w = r["policies"][p]["worst_delta_pct"]
            cells.append(f"{s_.get('median', float('nan')):+.1f}% ({(w if w is not None else float('nan')):+.1f}%)")
        sf = r["policies"]["safe_selected"]
        inc = r["policies"]["incumbent"]
        L.append(f"| {name} | {r['archetype']} | {r['cover']} | {r['holding']:.4f} | " + " | ".join(cells)
                 + f" | {sf['fill_diff_vs_incumbent_pt']:+.2f} | {sf['avg_inventory'] / max(inc['avg_inventory'], 1e-9):.2f} "
                 f"| {sf['plan_change']:.2f} | {r['safe_selections']} |")
    L += ["", "## Strata", "", "| stratum | regimes | SP median Δ% | SP worst | SAFE median Δ% | SAFE worst | anchored median Δ% |",
          "|---|---|---|---|---|---|---|"]
    for st_name, members in STRATA.items():
        ms = [m for m in members if m in regs]
        if not ms:
            continue

        def agg(pol, key):
            vals = [regs[m]["policies"][pol]["delta_vs_incumbent_pct"].get("median", float("nan")) for m in ms]
            return sum(vals) / len(vals)

        def worst(pol):
            vals = [regs[m]["policies"][pol]["worst_delta_pct"] for m in ms if regs[m]["policies"][pol]["worst_delta_pct"] is not None]
            return min(vals) if vals else float("nan")
        L.append(f"| {st_name} | {', '.join(ms)} | {agg('stochastic_sp', 'median'):+.1f}% | {worst('stochastic_sp'):+.1f}% | "
                 f"{agg('safe_selected', 'median'):+.1f}% | {worst('safe_selected'):+.1f}% | {agg('anchored_sp', 'median'):+.1f}% |")
    # mode selection frequencies overall
    tot: dict = {}
    for r in regs.values():
        for k, v in r["safe_selections"].items():
            tot[k] = tot.get(k, 0) + v
    L += ["", "## Mode-selection frequency (SAFE_SELECTED, all regimes)", "",
          "| mode run | re-plans |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(tot.items(), key=lambda kv: -kv[1])]
    L += ["", "## Reading the result", "",
          "- The desired behaviour is not 'stochastic always wins'. In easy/slack regimes SAFE_SELECTED should "
          "stay close to or choose the incumbent; where uncertainty has economic value it may activate a "
          "candidate. Judge it by the SAFE worst-run column against the stochastic worst-run column.",
          "- Negative SAFE medians in any regime are reported as they are. They mean the gate let a candidate "
          "through that then lost, or that the incumbent inferred from the PO log is a stronger policy than any "
          "candidate at this carrying cost — both are findings.",
          "- The incumbent here is the simulator's own order-up-to with safety stock, a competent planner. A real "
          "operator's incumbent may be weaker or stronger; that is what the first real-operator backtest measures."]
    D.write_text("\n".join(L) + "\n")
    print("wrote", D)
    return 0


if __name__ == "__main__":
    sys.exit(main())
