"""Step I targeted rerun: C, O, P plus regression controls, all policies, three seeds, 11 reviews.
usage: PYTHONPATH=. python3 -m scripts.p1_targeted [--tag NAME]"""
from __future__ import annotations
import argparse, json, time
from concurrent.futures import ProcessPoolExecutor
from statistics import mean
from scripts.p1_fixtures import FIXTURES, POLICIES, SEEDS
from scripts.run_p1_fixtures import run_cell, check

TARGET = ["C_moq_four_weeks", "O_low_opening_stock", "P_high_opening_stock", "I_max_pallets_ftl_cap",
          "T_combined_realistic", "A_no_terms_good_incumbent", "G_freight_tiers", "Q_volatile_demand_high_target"]

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="targeted"); ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--scenarios", type=int, default=0, help="diagnostic world-count override (0 = fixture's own)")
    ap.add_argument("--fixtures", default="")
    ap.add_argument("--product-defaults", action="store_true")
    ap.add_argument("--terminal", default="salvage", choices=("salvage", "continuation"))
    a = ap.parse_args()
    import scripts.run_p1_fixtures as R
    names = [n for n in a.fixtures.split(",") if n] or TARGET
    jobs = [(n, p, s) for n in names for p in POLICIES for s in SEEDS]
    t0 = time.time(); cells = []
    with ProcessPoolExecutor(a.workers, initializer=R._init, initargs=("none", "default", 0., a.scenarios, a.product_defaults, a.terminal)) as pool:
        for c in pool.map(run_cell, *zip(*jobs)):
            cells.append(c)
    json.dump(cells, open(f"docs/zaad_full/evidence/p1/closure/{a.tag}.json", "w"), indent=1, default=float)
    results = [r for r in check(cells) if r["fixture"] in names]
    for r in results:
        c = r["costs"]; bb = min(v for k, v in c.items() if k != "gated")
        g = [x for x in cells if x["fixture"] == r["fixture"] and x["policy"] == "gated"]
        print(f"{r['fixture'][:28]:28s} {'PASS' if r['pass'] else 'FAIL'} zaad {c['gated']:7.0f} best-base {bb:7.0f} delta {100*(c['gated']-bb)/bb:+5.2f}% "
              f"svc {mean(x['service'] for x in g):.3f} breaches {mean(x['breaches'] for x in g):.1f} unmet {mean(x['unmet_units'] for x in g):.1f} inv {mean(x['avg_inventory_units'] for x in g):.0f} "
              f"actions {sum(x['actions'] for x in g)}/{11*len(g)} abst {sum(x['abstentions'] for x in g)} cats {sorted({k for x in g for k in x['categories']})} "
              f"fails {[k for k, v in r['checks'].items() if not v]} "
              f"realised {mean(x['total_realized_cost'] for x in g):.0f} continuation {mean(x['total_continuation_cost'] for x in g):.0f} (eval {g[0].get('terminal_evaluation')}) "
              f"owners P1 {sum(x.get('planner_owners', []).count('PURCHASING_ECONOMICS') for x in g)}/P0 {sum(x.get('planner_owners', []).count('PROTECTION_RECOVERY') for x in g)} "
              f"p1_added {sum(x.get('p1_classes_added', 0) for x in g)} milps {sum(x.get('milps_attempted', 0) for x in g)} wall {sum(x['seconds'] for x in g):.0f}s")
    print("seconds", round(time.time() - t0))
