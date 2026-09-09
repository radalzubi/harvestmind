"""One authoritative A-T table from the final-code runs: legacy twelve-week (realised ledger) beside the
declared benchmark (rolling horizon, 52 reviews, landed-cost continuation), with the pre-fix record for
comparison. usage: PYTHONPATH=. python3 -m scripts.p1_final_table"""
from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

from scripts.p1_fixtures import FIXTURES, POLICIES, SEEDS
from scripts.p1_horizon_tables import W_STAR, complete, delta, gated_stats, last_valid, load, stable, verdict

EVID = Path("docs/zaad_full/evidence/p1")
KEY = "continuation_landed"
INVALID_LEGACY = {"N_long_lead_21_days", "R_asymmetric_prices_mov"}


def legacy(tag):
    cells = [json.loads(l) for l in open(EVID / f"fixtures_product_defaults_{tag}.jsonl")]
    res = {r["fixture"]: r for r in json.load(open(EVID / f"P1_EXPECTATIONS_none_product_defaults_{tag}.json"))}
    out = {}
    for name in FIXTURES:
        g = [c for c in cells if c["fixture"] == name and c["policy"] == "gated"]
        base = {p: mean(c["total_realized_cost"] for c in cells if c["fixture"] == name and c["policy"] == p) for p in POLICIES if p != "gated"}
        bp = min(base, key=base.get)
        z = mean(c["total_realized_cost"] for c in g)
        out[name] = {"zaad": z, "best": base[bp], "best_policy": bp, "delta": 100. * (z - base[bp]) / base[bp], "pass": res[name]["pass"],
                     "failed": [k for k, v in res[name]["checks"].items() if not v], "service": mean(c["service"] for c in g),
                     "unmet": mean(c["unmet_units"] for c in g), "actions": sum(c["actions"] for c in g), "abstentions": sum(c["abstentions"] for c in g)}
    return out


def main():
    leg_pre, leg_fin = legacy("terminal_continuation"), legacy("final")
    _, pre = load(EVID / "closure/horizon52.jsonl")
    _, fin = load(EVID / "closure/horizon52_final.jsonl")
    lines = ["# P1 authoritative final result table (final code; pre-fix record beside it, never overwritten)\n",
             "Legacy: eleven rolling reviews of a shrinking twelve-period plan, realised ledger (declared salvage). Declared benchmark: constant rolling "
             "twelve-period planning horizon, 52 reviews, landed-cost continuation of the residual (pre-registered in `P1_BENCHMARK_PREREGISTRATION.md`). "
             "PRE-FIX = `de4e771` product policy; FINAL-CODE = lot-sizing terminal valuation on P1-owned reviews with the consistent ledger key. "
             "Seed means over 41001-41003; ZAAD against the best baseline.\n",
             "| fixture | legacy PRE-FIX delta | legacy FINAL delta | legacy FINAL verdict | declared PRE-FIX delta @52 | **declared FINAL @52** (ZAAD / best baseline) | FINAL verdict | stable (max dev 40..52) | service | unmet | avg inv units | purchases | orders (ZAAD / best base) | freight | carrying | terminal credit (landed) | P1 / P0 owned reviews | actions | abstentions |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    summary = {}
    for name in FIXTURES:
        lp, lf = leg_pre[name], leg_fin[name]
        valid_fin = last_valid(fin, name) >= W_STAR
        valid_pre = last_valid(pre, name) >= W_STAR
        if valid_fin:
            d, bp, z, b = delta(fin, name, W_STAR, KEY)
            st, worst = stable(fin, name, KEY)
            e = [fin[name, "gated", s]["curve"][W_STAR - 1] for s in SEEDS]
            g = gated_stats(fin, name, W_STAR)
            tol = FIXTURES[name]["expect"]["zaad_not_worse"]
            cost_ok = d <= 100. * tol + 1e-9
            floor = FIXTURES[name]["expect"].get("service_floor")
            floor_ok = True if floor is None else all(fin[name, p, s]["curve"][W_STAR - 1]["service"] >= floor for p in POLICIES for s in SEEDS)
            first_ok = not any(k in lf["failed"] for k in ("action", "categories", "attribution_partitions"))
            if name in INVALID_LEGACY:
                v = f"proven invalid (kept); cost {'within' if cost_ok else 'outside'} tolerance"
            else:
                v = "PASS" if (cost_ok and floor_ok and first_ok and st) else ("FAIL" if not cost_ok or not floor_ok or not first_ok else "FAIL (unstable)")
            orders_z = mean(sum(1 for r in fin[name, "gated", s]["per_review"] if r["purchases"]) for s in SEEDS)
            orders_b = mean(sum(1 for r in fin[name, bp, s]["per_review"] if r["purchases"]) for s in SEEDS)
            dpre = f"{delta(pre, name, W_STAR, KEY)[0]:+.2f}%" if valid_pre else "invalid"
            lines.append(f"| {name} | {lp['delta']:+.2f}% | {lf['delta']:+.2f}% | {'PASS' if lf['pass'] else 'FAIL ' + str(lf['failed'])} | {dpre} | **{d:+.2f}%** ({z:,.0f} / {bp} {b:,.0f}) | {v} | {'yes' if st else 'NO'} ({worst:.2f} pp) | "
                         f"{mean(x['service'] for x in e):.3f} | {mean(x['unmet'] for x in e):.1f} | {mean(x['avg_inventory_units'] for x in e):.0f} | {mean(x['components']['PURCHASE'] for x in e):,.0f} | {orders_z:.1f} / {orders_b:.1f} | "
                         f"{mean(x['components']['FREIGHT'] for x in e):,.0f} | {mean(x['components']['CARRYING'] for x in e):,.0f} | {mean(x['continuation_landed_credit'] for x in e):,.0f} | {g['p1']} / {g['p0']} | {g['actions']} | {g['abstentions']} |")
            summary[name] = {"legacy_pre": lp["delta"], "legacy_final": lf["delta"], "legacy_final_pass": lf["pass"], "declared_pre": delta(pre, name, W_STAR, KEY)[0] if valid_pre else None,
                             "declared_final": d, "best_baseline": bp, "verdict": v, "stable": st, "max_dev_pp": worst, "service": mean(x["service"] for x in e),
                             "p1_owned": g["p1"], "p0_owned": g["p0"], "actions": g["actions"], "abstentions": g["abstentions"]}
        else:
            lv = last_valid(fin, name)
            d = delta(fin, name, lv, KEY)[0] if lv else None
            lines.append(f"| {name} | {lp['delta']:+.2f}% | {lf['delta']:+.2f}% | {'PASS' if lf['pass'] else 'FAIL ' + str(lf['failed'])} | invalid | INVALID at 52 (all five policies complete only to W = {lv}; diagnostic there {d:+.2f}%) | PROVEN INVALID at the declared benchmark | - | | | | | | | | | | | |")
            summary[name] = {"legacy_pre": lp["delta"], "legacy_final": lf["delta"], "legacy_final_pass": lf["pass"], "declared_final": None, "verdict": "INVALID_AT_52", "last_valid": lv}
    walls = sorted(r["wall_seconds"] for k, c in fin.items() if k[1] == "gated" for r in c.get("per_review", []))
    lines.append(f"\nRuntime, final rolling run, ZAAD reviews: n {len(walls)}, p50 {walls[len(walls) // 2]:.2f} s, p90 {walls[int(.9 * len(walls))]:.2f} s, p95 {walls[int(.95 * len(walls))]:.2f} s, max {walls[-1]:.1f} s.")
    text = "\n".join(lines)
    (EVID / "P1_FINAL_RESULT_TABLE.md").write_text(text + "\n")
    json.dump(summary, open(EVID / "P1_FINAL_SUMMARY.json", "w"), indent=1, default=float)
    print(text)


if __name__ == "__main__":
    main()
