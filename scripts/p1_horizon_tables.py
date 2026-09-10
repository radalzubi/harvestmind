"""Tables for the P1 benchmark / horizon closure pass from one extended-window run.

usage: PYTHONPATH=. python3 -m scripts.p1_horizon_tables docs/zaad_full/evidence/p1/closure/horizon52.jsonl [--rule continuation|salvage]

Everything here follows `P1_BENCHMARK_PREREGISTRATION.md`: the endpoint grid, the stability criterion
(section 4), the A-E classification (section 5), the boundary-sensitivity index and the selection rule
(section 6), validity at the declared endpoint (section 7) and the Option D / E diagnostics (section 8).
The legacy checks that concern the first review's plan (action, categories, attribution partition) are
unchanged between the legacy and rolling modes, because review 0 plans on the identical declared request,
and are taken from the legacy expectation file."""
from __future__ import annotations

import argparse
import json
from itertools import combinations
from pathlib import Path
from statistics import mean

from scripts.p1_fixtures import FIXTURES, POLICIES, SEEDS

GRID = (11, 13, 15, 17, 19, 23, 35, 47, 52)
W_STAR = 52
STABLE_RANGE = range(40, 53)
RULES = {"salvage": "realized", "continuation": "continuation", "continuation_landed": "continuation_landed"}
INVALID_LEGACY = {"N_long_lead_21_days", "R_asymmetric_prices_mov"}
EVID = Path("docs/zaad_full/evidence/p1")


def load(path):
    import gzip
    path = str(path)
    if not Path(path).exists() and Path(path + ".gz").exists():
        path += ".gz"
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt") as f:
        cells = [json.loads(line) for line in f if line.strip()]
    by = {}
    for c in cells:
        by[c["fixture"], c["policy"], c["seed"]] = c
    return cells, by


def complete(by, name, policy, W):
    return all((name, policy, s) in by and by[name, policy, s]["reviews_completed"] >= W for s in SEEDS)


def valid_at(by, name, W):
    return all(complete(by, name, p, W) for p in POLICIES)


def last_valid(by, name):
    ws = [W for W in range(1, W_STAR + 1) if valid_at(by, name, W)]
    return ws[-1] if ws else 0


def cost(by, name, policy, W, key):
    return mean(by[name, policy, s]["curve"][W - 1][key] for s in SEEDS)


def cost_seed(by, name, policy, seed, W, key):
    return by[name, policy, seed]["curve"][W - 1][key]


def delta(by, name, W, key):
    """ZAAD versus the best baseline (seed-mean costs), and the best baseline's name."""
    base = {p: cost(by, name, p, W, key) for p in POLICIES if p != "gated"}
    bp = min(base, key=base.get)
    z = cost(by, name, "gated", W, key)
    return 100. * (z - base[bp]) / base[bp], bp, z, base[bp]


def verdict(by, name, W, key):
    tol = FIXTURES[name]["expect"]["zaad_not_worse"]
    d = delta(by, name, W, key)[0]
    return d <= 100. * tol + 1e-9


def stable(by, name, key):
    """Section 4: over W in [40, 52] the delta stays within +/-1 pp of its value at 52 and the verdict is identical."""
    d52, v52 = delta(by, name, W_STAR, key)[0], verdict(by, name, W_STAR, key)
    worst = 0.
    for W in STABLE_RANGE:
        d = delta(by, name, W, key)[0]
        worst = max(worst, abs(d - d52))
        if abs(d - d52) > 1. or verdict(by, name, W, key) != v52:
            return False, worst
    return True, worst


def classify(by, name, key):
    """Section 5."""
    st, _ = stable(by, name, key)
    if not st:
        return "E. NON-CONVERGENT"
    v11, v52 = verdict(by, name, 11, key), verdict(by, name, W_STAR, key)
    ds = [delta(by, name, W, key)[0] for W in GRID if W >= 23]
    rng = max(ds) - min(ds)
    if v11 == v52 and rng <= 2.:
        return "A. STABLE PASS" if v52 else "B. STABLE FAIL"
    return "C. BOUNDARY-SENSITIVE -> PASS" if v52 else "D. BOUNDARY-SENSITIVE -> FAIL"


def bsi(by, names, key):
    """Section 4: mean |delta(W+2) - delta(W)| over fixtures, seeds, all ten policy pairs, grid endpoints."""
    values = []
    for name in names:
        for s in SEEDS:
            for a, b in combinations(POLICIES, 2):
                for W in GRID:
                    if W + 2 > W_STAR:
                        continue
                    d0 = 100. * (cost_seed(by, name, a, s, W, key) - cost_seed(by, name, b, s, W, key)) / cost_seed(by, name, b, s, W, key)
                    d2 = 100. * (cost_seed(by, name, a, s, W + 2, key) - cost_seed(by, name, b, s, W + 2, key)) / cost_seed(by, name, b, s, W + 2, key)
                    values.append(abs(d2 - d0))
    return mean(values) if values else float("nan")


def gated_stats(by, name, W):
    g = [by[name, "gated", s] for s in SEEDS]
    rows = [r for c in g for r in c["per_review"][:W]]
    return {"actions": sum(r["status"] == "PENDING_REVIEW" for r in rows), "abstentions": sum(r["abstained"] for r in rows),
            "p1": sum(r["owner"] == "PURCHASING_ECONOMICS" for r in rows), "p0": sum(r["owner"] == "PROTECTION_RECOVERY" for r in rows),
            "reviews": len(rows), "wall": [r["wall_seconds"] for r in rows]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--rule", default=None, help="declared terminal rule; when omitted the selection rule of section 6 is applied")
    ap.add_argument("--out-tag", default="", help="suffix for the output file names, so an earlier record is never overwritten")
    ap.add_argument("--tests-pass", default="salvage:fail,continuation:fail,continuation_landed:pass", help="Stage 7 outcome per rule, from pytest")
    a = ap.parse_args()
    cells, by = load(a.path)
    legacy = {r["fixture"]: r for r in json.load(open(EVID / "P1_EXPECTATIONS_none_product_defaults_terminal_continuation.json"))}
    legacy_cells = [json.loads(l) for l in open(EVID / "fixtures_product_defaults_terminal_continuation.jsonl")]

    def legacy_delta(name, key):
        base = min(mean(c[key] for c in legacy_cells if c["fixture"] == name and c["policy"] == p) for p in POLICIES if p != "gated")
        z = mean(c[key] for c in legacy_cells if c["fixture"] == name and c["policy"] == "gated")
        return 100. * (z - base) / base

    out = []
    P = out.append
    P("# P1 extended-window benchmark: convergence, stability, selection and the declared result\n")
    P(f"Source `{a.path}`: {len(cells)} cells, rolling twelve-period planning horizon, {W_STAR} reviews requested, stitched truth per seed, "
      "scored at every endpoint under both terminal rules. Pre-registered in `P1_BENCHMARK_PREREGISTRATION.md`.\n")
    # completeness / validity
    P("## Completeness and validity at the declared endpoint (section 7)\n")
    P("| fixture | last endpoint with all five policies complete | incomplete cells (policy, seed, reviews, status) |")
    P("|---|---|---|")
    valid = {}
    for name in FIXTURES:
        lv = last_valid(by, name)
        valid[name] = lv >= W_STAR
        inc = [(p, s, by[name, p, s]["reviews_completed"], by[name, p, s]["status"]) for p in POLICIES for s in SEEDS if (name, p, s) in by and by[name, p, s]["reviews_completed"] < W_STAR]
        P(f"| {name} | {lv} | {inc if inc else '-'} |")
    names_valid = [n for n in FIXTURES if valid[n]]
    P("")
    # Stage 3 tables
    P("## Stage 3: endpoint sensitivity (seed means; ZAAD against the best baseline at that endpoint)\n")
    for name in FIXTURES:
        lv = last_valid(by, name)
        P(f"### {name} (valid to W = {lv}; legacy 12-week: salvage {legacy_delta(name, 'total_realized_cost'):+.2f}%, continuation {legacy_delta(name, 'total_continuation_cost'):+.2f}%)\n")
        P("| W | rule | ZAAD | best baseline | delta | ZAAD service | unmet | end on-hand | end in-transit | next lot (periods after W) | ZAAD salvage credit | ZAAD continuation credit (unit / landed) |")
        P("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for W in GRID:
            if W > lv:
                continue
            for rule, key in RULES.items():
                d, bp, z, b = delta(by, name, W, key)
                e = [by[name, "gated", s]["curve"][W - 1] for s in SEEDS]
                P(f"| {W} | {rule} | {z:,.0f} | {bp} {b:,.0f} | {d:+.2f}% | {mean(x['service'] for x in e):.3f} | {mean(x['unmet'] for x in e):.1f} | {mean(x['terminal_on_hand'] for x in e):.0f} | {mean(x['terminal_in_transit'] for x in e):.0f} | "
                  f"{[x['next_arrival_periods_after_window'] for x in e]} | {mean(x['salvage_credit'] for x in e):,.0f} | {mean(x['continuation_credit'] for x in e):,.0f} / {mean(x['continuation_landed_credit'] for x in e):,.0f} |")
        P("")
    # Stage 4 classification, both rules
    P("## Stage 4: convergence classification (section 5), both rules\n")
    P("| fixture | valid at 52 | rule | delta @11 (rolling) | @23 | @35 | @47 | @52 | max |delta(W)-delta(52)| over 40..52 | stable | class |")
    P("|---|---|---|---|---|---|---|---|---|---|---|")
    classes = {}
    for name in FIXTURES:
        for rule, key in RULES.items():
            if not valid[name]:
                lv = last_valid(by, name)
                P(f"| {name} | no (to {lv}) | {rule} | " + " | ".join(f"{delta(by, name, W, key)[0]:+.2f}%" if W <= lv else "-" for W in (11, 23, 35, 47, 52)) + " | - | - | INVALID AT 52 |")
                continue
            st, worst = stable(by, name, key)
            cls = classify(by, name, key)
            classes[name, rule] = cls
            P(f"| {name} | yes | {rule} | " + " | ".join(f"{delta(by, name, W, key)[0]:+.2f}%" for W in (11, 23, 35, 47, 52)) + f" | {worst:.2f} pp | {'yes' if st else 'NO'} | {cls} |")
    P("")
    # BSI and selection
    P("## Section 6: boundary-sensitivity index and the selection rule\n")
    tests = dict(kv.split(":") for kv in a.tests_pass.split(","))
    b = {rule: bsi(by, names_valid, key) for rule, key in RULES.items()}
    P("| rule | Stage 7 tests | BSI (pp per two-review shift, all ten policy pairs, valid fixtures, three seeds) | fixtures stable at 52 |")
    P("|---|---|---|---|")
    for rule, key in RULES.items():
        P(f"| {rule} | {tests.get(rule)} | {b[rule]:.3f} | {sum(stable(by, n, key)[0] for n in names_valid)} / {len(names_valid)} |")
    passing = [r for r in RULES if tests.get(r) == "pass"]
    if a.rule:
        declared = a.rule
        why = "declared on the command line"
    elif len(passing) == 1:
        declared = passing[0]
        why = "the only rule passing the twelve tests"
    else:
        lo = min(passing, key=lambda r: b[r])
        hi = max(passing, key=lambda r: b[r])
        declared = lo if abs(b[lo] - b[hi]) >= .1 * b[hi] else ("continuation_landed" if "continuation_landed" in passing else "continuation")
        why = f"lower BSI ({b[lo]:.3f} against {b[hi]:.3f})" if declared == lo and abs(b[lo] - b[hi]) >= .1 * b[hi] else "BSI within 10%: the monotone rule"
    key = RULES[declared]
    P(f"\n**Declared rule: {declared}** ({why}).\n")
    # BSI split by whether pairs involve gated
    P("BSI per rule restricted to baseline-only pairs (no ZAAD in the pair), as a check that the index is not driven by ZAAD:\n")
    for rule, k in RULES.items():
        vals = []
        for name in names_valid:
            for s in SEEDS:
                for p, q in combinations([p for p in POLICIES if p != "gated"], 2):
                    for W in GRID:
                        if W + 2 <= W_STAR:
                            d0 = 100. * (cost_seed(by, name, p, s, W, k) - cost_seed(by, name, q, s, W, k)) / cost_seed(by, name, q, s, W, k)
                            d2 = 100. * (cost_seed(by, name, p, s, W + 2, k) - cost_seed(by, name, q, s, W + 2, k)) / cost_seed(by, name, q, s, W + 2, k)
                            vals.append(abs(d2 - d0))
        P(f"* {rule}: {mean(vals):.3f} pp")
    P("")
    # Option D start-offset diagnostic
    P("## Section 8, Option D diagnostic: start offset s with symmetric endpoint handling (window [s, 52])\n")
    P("| fixture | rule | s=0 | s=4 | s=8 |")
    P("|---|---|---|---|---|")
    for name in names_valid:
        for rule, k in RULES.items():
            row = []
            for s0 in (0, 4, 8):
                def windowed(policy):
                    vals = []
                    for s in SEEDS:
                        c = by[name, policy, s]["curve"]
                        end = c[W_STAR - 1][k]
                        if s0 == 0:
                            vals.append(end)
                        else:
                            start = c[s0 - 1]
                            # cost of [s0, 52] = cost to 52 - cost to s0 + (opening stock at s0 valued by the rule instead of credited)
                            vals.append(end - start[k])
                    return mean(vals)
                base = {p: windowed(p) for p in POLICIES if p != "gated"}
                bp = min(base, key=base.get)
                row.append(f"{100. * (windowed('gated') - base[bp]) / base[bp]:+.2f}% vs {bp}")
            P(f"| {name} | {rule} | " + " | ".join(row) + " |")
    P("")
    # Option E per-week and cycle-minimum diagnostic
    P("## Section 8, Option E diagnostic: per-week average cost at 52 and each policy at its own cycle-minimum endpoint in [40, 52] (declared rule)\n")
    P("| fixture | ZAAD per week | best baseline per week | delta (same as @52) | cycle-minimum endpoints (policy: W) | delta at own cycle minima, per-week normalised |")
    P("|---|---|---|---|---|---|")
    for name in names_valid:
        d, bp, z, bb = delta(by, name, W_STAR, key)
        mins = {}
        per_week = {}
        for p in POLICIES:
            Wm = min(STABLE_RANGE, key=lambda W: mean(by[name, p, s]["curve"][W - 1]["terminal_on_hand"] + by[name, p, s]["curve"][W - 1]["terminal_in_transit"] for s in SEEDS))
            mins[p] = Wm
            per_week[p] = cost(by, name, p, Wm, key) / Wm
        bbp = min((per_week[p] for p in POLICIES if p != "gated"))
        P(f"| {name} | {z / W_STAR:,.1f} | {bp} {bb / W_STAR:,.1f} | {d:+.2f}% | {mins} | {100. * (per_week['gated'] - bbp) / bbp:+.2f}% |")
    P("")
    # Stage 9 final table under the declared rule
    P(f"## Stage 9: A-T at the declared benchmark (rolling horizon, W* = {W_STAR}, rule {declared}) beside the legacy twelve-week result\n")
    P("| fixture | valid | legacy delta (salvage) | rolling @11 | **declared @52** | verdict | class | service | breaches | unmet | avg inv units | terminal on-hand | in-transit | purchases | freight | ordering | carrying | financing | shortage | inventory value change | terminal credit (rule) | P1 / P0 owned | actions | abstentions | legacy first-review checks |")
    P("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    summary = {}
    for name in FIXTURES:
        lv = last_valid(by, name)
        Wv = W_STAR if valid[name] else lv
        if Wv == 0:
            P(f"| {name} | NO | {legacy_delta(name, 'total_realized_cost'):+.2f}% | - | - | INVALID | - |" + " |" * 18)
            continue
        d, bp, z, bb = delta(by, name, Wv, key)
        e = [by[name, "gated", s]["curve"][Wv - 1] for s in SEEDS]
        comp = {k_: mean(x["components"][k_] for x in e) for k_ in e[0]["components"]}
        g = gated_stats(by, name, Wv)
        tol = FIXTURES[name]["expect"]["zaad_not_worse"]
        lchecks = legacy[name]["checks"]
        first_review_ok = all(lchecks.get(k_, True) for k_ in ("action", "categories", "attribution_partitions"))
        floor = FIXTURES[name]["expect"].get("service_floor")
        floor_ok = True if floor is None else all(by[name, p, s]["curve"][Wv - 1]["service"] >= floor for p in POLICIES for s in SEEDS)
        cost_ok = d <= 100. * tol + 1e-9
        proven_invalid = name in INVALID_LEGACY
        if not valid[name]:
            v = f"INVALID AT 52 (diagnostic @{Wv}: {'within' if cost_ok else 'outside'} tolerance)"
        elif proven_invalid:
            v = f"proven invalid (legacy N/R classification kept); cost {'within' if cost_ok else 'outside'} tolerance"
        else:
            v = "PASS" if (cost_ok and floor_ok and first_review_ok) else "FAIL"
        cls = classes.get((name, declared), "-")
        summary[name] = {"valid_at_52": valid[name], "endpoint": Wv, "delta": d, "best_baseline": bp, "verdict": v, "class": cls, "service": mean(x["service"] for x in e),
                         "legacy_delta_salvage": legacy_delta(name, "total_realized_cost"), "rolling_11": delta(by, name, 11, key)[0] if lv >= 11 else None}
        P(f"| {name} | {'yes' if valid[name] else f'no (to {lv})'} | {legacy_delta(name, 'total_realized_cost'):+.2f}% | {delta(by, name, 11, key)[0]:+.2f}% | **{d:+.2f}%** vs {bp} | {v} | {cls} | "
          f"{mean(x['service'] for x in e):.3f} | {mean(x['breaches'] for x in e):.1f} | {mean(x['unmet'] for x in e):.1f} | {mean(x['avg_inventory_units'] for x in e):.0f} | {mean(x['terminal_on_hand'] for x in e):.0f} | {mean(x['terminal_in_transit'] for x in e):.0f} | "
          f"{comp['PURCHASE']:,.0f} | {comp['FREIGHT']:,.0f} | {comp['ORDERING']:,.0f} | {comp['CARRYING']:,.0f} | {comp['FINANCING']:,.0f} | {comp['SHORTAGE']:,.0f} | {comp['INVENTORY_VALUE_CHANGE']:,.0f} | "
          f"{mean(x[{'salvage': 'salvage_credit', 'continuation': 'continuation_credit', 'continuation_landed': 'continuation_landed_credit'}[declared]] for x in e):,.0f} | {g['p1']} / {g['p0']} | {g['actions']} | {g['abstentions']} | {'ok' if first_review_ok else [k_ for k_ in ('action', 'categories', 'attribution_partitions') if not lchecks.get(k_, True)]} |")
    P("")
    # runtime
    walls = sorted(w for c in cells if c["policy"] == "gated" for r in c.get("per_review", []) for w in [r["wall_seconds"]])
    if walls:
        P(f"Runtime, ZAAD reviews: n {len(walls)}, p50 {walls[len(walls) // 2]:.2f} s, p90 {walls[int(.9 * len(walls))]:.2f} s, p95 {walls[int(.95 * len(walls))]:.2f} s, max {walls[-1]:.1f} s; "
          f"total wall of all cells {sum(c.get('seconds', 0.) for c in cells):,.0f} s.\n")
    text = "\n".join(out)
    suffix = ("_" + a.out_tag) if a.out_tag else ""
    (EVID / f"P1_HORIZON_CONVERGENCE{suffix}.md").write_text(text + "\n")
    json.dump({"declared_rule": declared, "why": why, "bsi": b, "summary": summary, "grid": GRID, "W_star": W_STAR,
               "classes": {f"{n}|{r}": c for (n, r), c in classes.items()}}, open(EVID / f"P1_HORIZON_SUMMARY{suffix}.json", "w"), indent=1, default=float)
    print(text)


if __name__ == "__main__":
    main()
