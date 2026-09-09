"""Fixture parity under both terminal evaluations from one A-T run (stage 16).
usage: PYTHONPATH=. python3 -m scripts.p1_dual_terminal_table docs/zaad_full/evidence/p1/fixtures_<arm>.jsonl
Every cell carries `total_realized_cost` (ledger, salvage) and `total_continuation_cost` (plus the
finite-horizon continuation adjustment); the pre-registered checks are re-evaluated under each."""
from __future__ import annotations
import json, sys
from statistics import mean
from scripts.run_p1_fixtures import check

path = sys.argv[1]
cells = [json.loads(line) for line in open(path) if line.strip()]
for label, key in (("REALISED LEDGER (declared salvage)", "total_realized_cost"), ("CONTINUATION (finite-horizon adjustment)", "total_continuation_cost")):
    rows = [{**c, "total_modeled_cost": c.get(key, c.get("total_modeled_cost"))} for c in cells]
    results = check(rows)
    print(f"\n## {label}")
    print("| fixture | ZAAD | best baseline | delta | service | breaches | unmet | P1-owned / P0-owned reviews | actions | abstentions | pass | failed checks |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    passes = 0
    for r in results:
        c = r["costs"]; bb = min(v for k, v in c.items() if k != "gated")
        g = [x for x in rows if x["fixture"] == r["fixture"] and x["policy"] == "gated"]
        owners = [o for x in g for o in x.get("planner_owners", [])]
        passes += r["pass"]
        print(f"| {r['fixture']} | {c['gated']:.0f} | {bb:.0f} | {100 * (c['gated'] - bb) / bb:+.2f}% | {mean(x['service'] for x in g):.3f} | {mean(x['breaches'] for x in g):.1f} | {mean(x['unmet_units'] for x in g):.1f} "
              f"| {owners.count('PURCHASING_ECONOMICS')} / {owners.count('PROTECTION_RECOVERY')} | {sum(x['actions'] for x in g)} | {sum(x['abstentions'] for x in g)} | {'PASS' if r['pass'] else 'FAIL'} | {[k for k, v in r['checks'].items() if not v]} |")
    print(f"\n{passes} / {len(results)} pass")
