"""Assemble the closure-pass tables from the evidence files (P1 closure, step N/O).
usage: PYTHONPATH=. python3 -m scripts.p1_closure_tables > docs/zaad_full/evidence/p1/closure/TABLES.md"""
from __future__ import annotations

import glob
import json
from statistics import mean

from scripts.p1_fixtures import FIXTURES, POLICIES

P = "docs/zaad_full/evidence/p1"


def arm_table():
    out = ["| fixture | incumbent | best baseline | ZAAD P1 | ZAAD vs incumbent | ZAAD vs best baseline | checks |", "|---|---|---|---|---|---|---|"]
    r = json.load(open(f"{P}/P1_EXPECTATIONS_none.json"))
    passing = 0
    for x in r:
        c = x["costs"]
        bb_name = min((k for k in c if k != "gated"), key=c.get)
        bb, z, inc = c[bb_name], c["gated"], c["incumbent"]
        passing += x["pass"]
        out.append(f"| {x['fixture']} | {inc:,.0f} | {bb:,.0f} ({bb_name}) | {z:,.0f} | {(z - inc) / abs(inc):+.1%} | {(z - bb) / abs(bb):+.1%} | "
                   f"{'PASS' if x['pass'] else 'FAIL: ' + ', '.join(k for k, v in x['checks'].items() if not v)} |")
    return f"{passing} / {len(r)} fixtures pass\n\n" + "\n".join(out)


def metrics_table(arm="none"):
    cells = [json.loads(l) for l in open(f"{P}/fixtures_{arm}.jsonl")]
    by = {}
    for c in cells:
        if c["status"] == "COMPLETE":
            by.setdefault((c["fixture"], c["policy"]), []).append(c)
    cols = ["fixture", "policy", "service", "p10", "breaches", "unmet", "worst", "inv units", "inv value", "orders", "order size",
            "purchase", "freight", "ordering", "receiving", "carrying", "financing", "shortage", "inv value chg", "TOTAL", "working capital",
            "inv delta", "cost delta", "action", "attribution residual"]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for name in FIXTURES:
        base = by.get((name, "incumbent"))
        inc_cost = mean(c["total_modeled_cost"] for c in base) if base else None
        inc_inv = mean(c["avg_inventory_value"] for c in base) if base else None
        for policy in POLICIES:
            rows = by.get((name, policy))
            if not rows:
                out.append(f"| {name} | {policy} | FAILED |" + " |" * (len(cols) - 3))
                continue
            svc = [c["service"] for c in rows if c["service"] is not None]
            comp = {k: mean(c["components"][k] for c in rows) for k in rows[0]["components"]}
            cost = mean(c["total_modeled_cost"] for c in rows)
            inv = mean(c["avg_inventory_value"] for c in rows)
            per = sorted(s for c in rows for s in c["per_review_service"] if s is not None)
            p10 = per[max(0, int(.1 * (len(per) - 1)))] if per else None
            action = "-" if policy != "gated" else f"act {sum(c['actions'] for c in rows)}/{11 * len(rows)}, abstain {sum(c['abstentions'] for c in rows)}"
            resid = "-" if policy != "gated" else ("0 (partitions exact)" if all(c.get("attribution_sums_ok", True) for c in rows) else "NONZERO")
            out.append("| " + " | ".join([name, policy, f"{mean(svc):.3f}" if svc else "n/a", f"{p10:.3f}" if p10 is not None else "n/a",
                                          f"{mean(c['breaches'] for c in rows):.1f}", f"{mean(c['unmet_units'] for c in rows):.1f}", f"{max(c['worst_shortfall'] for c in rows):.1f}",
                                          f"{mean(c['avg_inventory_units'] for c in rows):.0f}", f"{inv:,.0f}", f"{mean(c['order_count'] for c in rows):.1f}", f"{mean(c['avg_order_size'] for c in rows):.0f}",
                                          *[f"{comp[k]:,.0f}" for k in ("PURCHASE", "FREIGHT", "ORDERING", "RECEIVING", "CARRYING", "FINANCING", "SHORTAGE", "INVENTORY_VALUE_CHANGE")],
                                          f"{cost:,.0f}", f"{mean(c['working_capital'] for c in rows):,.0f}",
                                          f"{(inv - inc_inv) / inc_inv:+.1%}" if inc_inv else "n/a", f"{(cost - inc_cost) / abs(inc_cost):+.1%}" if inc_cost else "n/a", action, resid]) + " |")
    return "\n".join(out)


def p0_table():
    arms = {}
    for f in sorted(glob.glob(f"{P}/closure/p0_arm_*.json")):
        arms[f.split("p0_arm_")[1][:-5]] = json.load(open(f))
    out = ["| arm | cell | service | p10 | breaches | unmet | worst | inventory | cost | required done/req | starved | joint req/built/chosen | lat p50 | p95 | max |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for arm, cells in arms.items():
        for cid, r in sorted(cells.items(), key=lambda kv: int(kv[0])):
            out.append(f"| {arm} | {cid} | {r['service']:.3f} | {r['p10']:.3f} | {r['breach_reviews']} | {r['total_unmet']:.1f} | {r['worst_unmet']:.1f} | {r['inventory']:.1f} | {r['cost']:.0f} | "
                       f"{r['required_completed']}/{r['required_requested']} | **{r['required_starved']}** | {r['joint_required']}/{r['joint_built']}/{r['joint_chosen']} | {r['lat_p50']:.2f} | {r['lat_p95']:.1f} | {r['lat_max']:.1f} |")
    return "\n".join(out)


def arms_summary():
    out = ["| arm | passing | C | O | P |", "|---|---|---|---|---|"]
    for f in sorted(glob.glob(f"{P}/P1_EXPECTATIONS_*.json")):
        r = json.load(open(f))
        arm = f.split("EXPECTATIONS_")[1][:-5]
        deltas = {}
        for x in r:
            c = x["costs"]
            bb = min(v for k, v in c.items() if k != "gated")
            deltas[x["fixture"][0]] = f"{(c['gated'] - bb) / bb:+.2%}"
        out.append(f"| {arm} | {sum(x['pass'] for x in r)} / {len(r)} | {deltas.get('C')} | {deltas.get('O')} | {deltas.get('P')} |")
    return "\n".join(out)


if __name__ == "__main__":
    print("# Closure tables\n")
    print("## Primary arm (nil stress, P1 defaults)\n")
    print(arm_table())
    print("\n## Arms\n")
    print(arms_summary())
    print("\n## Runtime\n")
    for f in sorted(glob.glob(f"{P}/P1_RUNTIME_*.json")):
        print("-", f.split("/")[-1], json.load(open(f)))
    print("\n## P0 six-cell arms\n")
    print(p0_table())
    print("\n## Full metrics, primary arm\n")
    print(metrics_table("none"))
