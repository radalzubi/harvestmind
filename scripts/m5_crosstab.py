"""Cross-variant table and the frozen verdict for M5 Experiment A, from the RESULTS_fifty_<variant>.json summaries.

    python -m scripts.m5_crosstab [--variants corrected,no_incumbent,...] [--baseline reorder_point] [--out docs/remodel/evidence/m5]

Verdict per (variant, window, scenario), from M5_DESIGN_FREEZE.md section 5: SUCCESS when ZAAD's mean paired continuation cost
is lower with the 95 % series bootstrap excluding zero and its mean fill is not lower by more than 0.01; FAILURE when the mean is
higher with the interval excluding zero, or the fill is lower by more than 0.01 with cost not lower; INCONCLUSIVE otherwise. Only
the `final` window is the holdout; val1 and val2 are shown for the same reading. Modelled indices under SYNTHETIC supply; no saving.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def verdict(p: dict | None, fill_diff: float | None) -> str:
    if p is None or fill_diff is None:
        return "n/a"
    if p["series"] < 10:
        return f"UNDERPOWERED ({p['series']} pairs)"      # a cash-starved variant completes a handful of series; no verdict is read from them
    lo, hi = p["bootstrap_95"]
    mean = p["mean_difference_zaad_minus_baseline"]
    if mean < 0 and hi < 0 and fill_diff >= -0.01:
        return "SUCCESS"
    if (mean > 0 and lo > 0) or (fill_diff < -0.01 and mean >= 0):
        return "FAILURE"
    return "INCONCLUSIVE"


def rows_for(variant: str, data: dict, baseline: str) -> list[dict]:
    out = []
    table, pairs = data["policy_table"], data["paired"]
    cells = sorted({(g["window"], g["scenario"]) for g in table.values()})
    for window, scenario in cells:
        z = table.get(f"{window}|observed|{scenario}|gated") or {}
        b = table.get(f"{window}|observed|{scenario}|{baseline}") or {}
        p = pairs.get(f"{window}|observed|{scenario}|{baseline}|continuation_cost")
        pf = pairs.get(f"{window}|observed|{scenario}|{baseline}|service_unit_fill")
        pi = pairs.get(f"{window}|observed|{scenario}|{baseline}|avg_inventory_units")
        fill_diff = pf["mean_difference_zaad_minus_baseline"] if pf else None
        m = lambda g, k: (g.get(k) or {}).get("mean")  # noqa: E731
        out.append({"variant": variant, "window": window, "scenario": scenario, "zaad_complete": f"{z.get('complete', 0)}/{z.get('runs', 0)}",
                    "zaad_cost": m(z, "continuation_cost"), "baseline_cost": m(b, "continuation_cost"), "zaad_fill": m(z, "service_unit_fill"), "baseline_fill": m(b, "service_unit_fill"),
                    "zaad_inventory": m(z, "avg_inventory_units"), "baseline_inventory": m(b, "avg_inventory_units"), "own_share": m(z, "zaad_own_share"),
                    "paired_mean": p and p["mean_difference_zaad_minus_baseline"], "ci95": p and p["bootstrap_95"], "better_worse": p and f"{p['zaad_better']}/{p['zaad_worse']}",
                    "fill_diff": fill_diff, "inventory_diff": pi and pi["mean_difference_zaad_minus_baseline"], "verdict": verdict(p, fill_diff)})
    return out


def markdown(rows: list[dict], baseline: str) -> str:
    def f(v, nd=2):
        return "" if v is None else f"{v:.{nd}f}"
    lines = [f"# M5 Experiment A: cross-variant table against `{baseline}` (series-paired continuation cost)", "",
             "Verdicts follow the frozen criteria (M5_DESIGN_FREEZE.md section 5); only `final` is the holdout. Modelled indices under declared SYNTHETIC supply on OBSERVED sales; nothing is a realized saving.", "",
             "| variant | window | scenario | ZAAD complete | ZAAD cost | base cost | paired mean | 95 % bootstrap | better/worse | ZAAD fill | base fill | fill diff | inv diff (units) | ZAAD own share | verdict |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        ci = "" if not r["ci95"] else f"[{r['ci95'][0]:+.2f}, {r['ci95'][1]:+.2f}]"
        pm = "" if r["paired_mean"] is None else f"{r['paired_mean']:+.2f}"
        fd = "" if r["fill_diff"] is None else f"{r['fill_diff']:+.3f}"
        idf = "" if r["inventory_diff"] is None else f"{r['inventory_diff']:+.1f}"
        lines.append(f"| {r['variant']} | {r['window']} | {r['scenario']} | {r['zaad_complete']} | {f(r['zaad_cost'])} | {f(r['baseline_cost'])} | {pm} | {ci} | {r['better_worse'] or ''} | "
                     f"{f(r['zaad_fill'], 3)} | {f(r['baseline_fill'], 3)} | {fd} | {idf} | {f(r['own_share'])} | {r['verdict']} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", default="corrected,no_incumbent,target_90,holding_x2,cash_4w,cash_4w_revenue")
    ap.add_argument("--baseline", default="reorder_point")
    ap.add_argument("--out", default="docs/remodel/evidence/m5")
    args = ap.parse_args()
    out = Path(args.out)
    rows: list[dict] = []
    for v in args.variants.split(","):
        path = out / f"RESULTS_fifty_{v}.json"
        if not path.exists():
            print(f"skip {v}: {path} missing")
            continue
        rows += rows_for(v, json.loads(path.read_text()), args.baseline)
    (out / "M5_CROSSTAB.json").write_text(json.dumps(rows, indent=1) + "\n")
    (out / "M5_CROSSTAB.md").write_text(markdown(rows, args.baseline))
    print(f"wrote {out / 'M5_CROSSTAB.md'}: {len(rows)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
