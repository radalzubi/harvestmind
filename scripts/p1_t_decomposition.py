"""Ownership decomposition of a fixture's gap against its best baseline under the declared benchmark.

usage: PYTHONPATH=. python3 -m scripts.p1_t_decomposition docs/zaad_full/evidence/p1/closure/horizon52_final.jsonl T_combined_realistic

For each seed: the per-review ledger difference (ZAAD minus the best baseline, every settlement component
of that review) is assigned to the owner of ZAAD's review (P1 purchasing or frozen P0), and the terminal
credit difference at the endpoint to TERMINAL/BOUNDARY; the three parts sum to the total gap exactly.
Because the two trajectories are not in the same state at the same review, the per-review differences
are noisy individually; the script also reports the shipment-cost part (freight + ordering + receiving)
by owner, which is where lumpy-lot economics live, and lists every review on which ZAAD ordered a
sub-economic load (below half the reference lot) with its owner, state, status and tier."""
from __future__ import annotations

import json
import sys
from statistics import mean

from scripts.p1_fixtures import POLICIES, SEEDS
from scripts.p1_horizon_tables import W_STAR, delta, load

SHIP = ("freight", "ordering", "order_fees", "receiving", "handling")


def main():
    path, name = sys.argv[1], sys.argv[2]
    _, by = load(path)
    lot = {"T_combined_realistic": 1920., "G_freight_tiers": 2000., "I_max_pallets_ftl_cap": 450., "B_fixed_order_cost_replace_sold": 1854.}.get(name, 400.)
    d, bp, _, _ = delta(by, name, W_STAR, "continuation_landed")
    print(f"{name}: declared delta {d:+.2f}% against {bp}")
    totals = {"P1": 0., "P0": 0., "TERMINAL": 0., "TOTAL": 0., "P1_ship": 0., "P0_ship": 0.}
    for s in SEEDS:
        z, b = by[name, "gated", s], by[name, bp, s]
        parts = {"P1": 0., "P0": 0., "P1_ship": 0., "P0_ship": 0.}
        for rz, rb in zip(z["per_review"][:W_STAR], b["per_review"][:W_STAR]):
            owner = "P1" if rz["owner"] == "PURCHASING_ECONOMICS" else "P0"
            lz = {k: v for k, v in rz["ledger"].items() if k not in ("opening_assets", "closing_assets")}
            lb = {k: v for k, v in rb["ledger"].items() if k not in ("opening_assets", "closing_assets")}
            diff = sum(lz.values()) - sum(lb.values())
            parts[owner] += diff
            parts[owner + "_ship"] += sum(lz.get(k, 0.) for k in SHIP) - sum(lb.get(k, 0.) for k in SHIP)
        ez, eb = z["curve"][W_STAR - 1], b["curve"][W_STAR - 1]
        terminal = -(ez["continuation_landed_credit"] - eb["continuation_landed_credit"]) + (ez["ledger"]["opening_assets"] - eb["ledger"]["opening_assets"])
        total = ez["continuation_landed"] - eb["continuation_landed"]
        recon = parts["P1"] + parts["P0"] + terminal - total
        print(f"  seed {s}: gap {total:+9.1f} ({100 * total / eb['continuation_landed']:+.2f}%) = P1-owned {parts['P1']:+9.1f} + P0-owned {parts['P0']:+9.1f} + terminal/boundary {terminal:+8.1f}  (residual {recon:+.6f}) | shipment-cost part: P1 {parts['P1_ship']:+8.0f} P0 {parts['P0_ship']:+8.0f} "
              f"| ZAAD orders {sum(1 for r in z['per_review'] if r['purchases'])} ({len([r for r in z['per_review'] if r['owner'] == 'PROTECTION_RECOVERY'])} P0-owned reviews) vs {bp} {sum(1 for r in b['per_review'] if r['purchases'])}")
        for r in z["per_review"][:W_STAR]:
            q = sum(x for _, x in r["purchases"])
            if 0 < q < .5 * lot:
                print(f"     r{r['review']:2d} sub-economic order {q:6.0f} units | owner {r['owner'][:4]} state {r['state']} status {r['status']} abstained {r['abstained']} | end stock {r['end_stock_units']:.0f} | ledger ship {sum(r['ledger'].get(k, 0.) for k in SHIP):.0f}")
        for k in ("P1", "P0", "P1_ship", "P0_ship"):
            totals[k] += parts[k] / len(SEEDS)
        totals["TERMINAL"] += terminal / len(SEEDS)
        totals["TOTAL"] += total / len(SEEDS)
    print(f"  seed mean: gap {totals['TOTAL']:+.1f} = P1 {totals['P1']:+.1f} + P0 {totals['P0']:+.1f} + terminal {totals['TERMINAL']:+.1f}; shipment part P1 {totals['P1_ship']:+.0f} P0 {totals['P0_ship']:+.0f}")


if __name__ == "__main__":
    main()
