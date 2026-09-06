#!/usr/bin/env python3
"""Summarize a complete frozen run without hiding failures or incomplete pairs."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
from statistics import median


def pairs(rows, method, baseline):
    lookup = {(r["cell"], r["seed"], r["method"]): r for r in rows}
    result = []
    for row in rows:
        if row["method"] != method:
            continue
        before = lookup.get((row["cell"], row["seed"], baseline))
        if before and row["status"] == before["status"] == "COMPLETE":
            saving = 100 * (before["cost"] - row["cost"]) / max(abs(before["cost"]), 1.)
            result.append((row, before, saving))
    return result


def spread(values):
    return f"{median(values):+.2f}% [{min(values):+.2f}, {max(values):+.2f}]" if values else "not estimable"


def table(rows, methods, baseline="base_stock"):
    lines = ["| Method | Complete / attempted | Service breaches among complete | Paired complete | Median saving [range] | Cost losses |",
             "|---|---:|---:|---:|---:|---:|"]
    for method in methods:
        all_rows = [r for r in rows if r["method"] == method]
        complete = [r for r in all_rows if r["status"] == "COMPLETE"]
        compared = pairs(rows, method, baseline)
        savings = [p[2] for p in compared]
        lines.append(f"|{method}|{len(complete)}/{len(all_rows)}|{sum(r['service_breach'] for r in complete)}/{len(complete)}|"
                     f"{len(compared)}|{spread(savings)}|{sum(v < -1e-6 for v in savings)}|")
    return lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text().splitlines()]
    manifest = json.loads((args.input.parent / "preregistered.json").read_text())
    methods, seeds, cells = manifest["methods"], manifest["seeds"]["final"], manifest["cells"]
    expected = {(c["cell"], s, m) for c in cells for s in seeds for m in methods}
    actual = [(r["cell"], r["seed"], r["method"]) for r in rows]
    if len(actual) != len(expected) or set(actual) != expected:
        raise ValueError("report requires exactly one row for every registered cell/seed/method")
    relative = args.input.relative_to(args.report.parent)
    lines = ["# ZAAD v2 synthetic benchmark results", "",
             "**Verdict: NEEDS FURTHER ENGINEERING.** These are synthetic engineering measurements, not customer validation, market ROI, or an autonomous-deployment approval.", "",
             f"Frozen engine commit: `488ab4c`; source fingerprint `{manifest['source_hash']}`. "
             f"Seeds: {', '.join(map(str, seeds))}. {len(cells)} coverage cells × {len(seeds)} seeds × {len(methods)} methods = {len(rows):,} rows.", "",
             f"[Every JSONL run]({relative}) and [flat CSV](evidence/final_v2/runs.csv) retain parameters, seeds, failures, service, and costs. "
             "425 matched path cases are not 2,975 independent operators. The 7,560-cell normal Cartesian experiment was not executed.", "",
             "## Against competent projected base-stock", "",
             "Savings use modeled economic cost, not operator turnover. A completed run can still breach its requested service floor. "
             "Incomplete pairs are excluded only from percentages, never erased from attempted/failure counts. This is not an intention-to-treat claim of guaranteed savings.", "",
             *table(rows, methods), "", "## Status audit", "",
             "| Method | Status | Count |", "|---|---|---:|"]
    for (method, status), count in sorted(Counter((r["method"], r["status"]) for r in rows).items()):
        lines.append(f"|{method}|{status}|{count}|")
    for family in ["normal", "disruption", "misspecification", "action"]:
        group = [r for r in rows if r["family"] == family]
        lines += ["", f"## {family.capitalize()} family", "", *table(group, methods)]
    recovery = [r for r in rows if r["case"] == "recovery"]
    lines += ["", "## Recovery PO fixture", "", *table(recovery, ["base_stock", "stochastic", "robust", "gated"])]
    lines += ["", "## Direct comparator checks", "",
              "| Comparison | Paired complete | Median saving [range] | Cost losses |", "|---|---:|---:|---:|"]
    comparisons = [("gated", "deterministic", rows), ("stochastic", "deterministic", rows),
                   ("robust", "stochastic", [r for r in rows if r["family"] == "misspecification"]),
                   ("stochastic", "frozen_forecast", [r for r in rows if r["demand"] == "increase"]),
                   ("stochastic", "frozen_forecast", [r for r in rows if r["demand"] == "decrease"])]
    for method, baseline, selected in comparisons:
        compared = pairs(selected, method, baseline)
        savings = [p[2] for p in compared]
        label = selected[0]["demand"] if selected and selected[0]["demand"] in {"increase", "decrease"} else ("misspecification" if len(selected) < len(rows) else "all")
        lines.append(f"|{method} vs {baseline} ({label})|{len(compared)}|{spread(savings)}|{sum(v < -1e-6 for v in savings)}|")
    lines += ["", "## Service-qualified economic pairs", "",
              "Both policies must complete and meet their requested aggregate fill target. These selected pairs do not rescue the failures outside the subset.", "",
              "| Method vs base-stock | Both meet service | Median saving [range] | Losses |", "|---|---:|---:|---:|"]
    for method in methods[1:]:
        valid = [p for p in pairs(rows, method, "base_stock") if not p[0]["service_breach"] and not p[1]["service_breach"]]
        savings = [p[2] for p in valid]
        lines.append(f"|{method}|{len(valid)}|{spread(savings)}|{sum(v < -1e-6 for v in savings)}|")
    lines += ["", "## Interpretation limits", "",
              "- Requested aggregate service is measured separately from cost. A breach is not automatically an optimizer bug or unavoidable: this experiment does not contain an ex-post joint feasibility certificate for every path.",
              "- Several named disruption cells share the same physical mapping; they do not establish independent news timing, AIS, port, or learned causal effects.",
              "- The base-stock policy is a disclosed fill-aware target projected through common physical and cash constraints. It is stronger than an unconstrained strawman but is not a real operator's observed incumbent.",
              "- `recovery_solves` in raw rows actually counts reviews with any warning, including gate reasons. Do not interpret that field as a count of lexicographic recovery solves.",
              "- The shrinking finite financial horizon, sparse scenario counts and assumed stress envelopes limit extrapolation. Post-horizon invoices remain obligations, not a later-date liquidity guarantee.",
              "- Earlier validation and first final attempt remain available. The first final uncovered unreceived overdue POs funding immediate transfers. A separate corrected preflight was stopped for type-check cleanup without analyzing its outcome metrics. This result uses fresh seeds after both corrections.",
              "", "See [failure analysis](FAILURE_ANALYSIS.md), [feature probes](ABLATIONS.md), [commercial answers](COMMERCIAL_ANSWERS.md), and [verification](VERIFICATION.md).", ""]
    with args.report.open("x") as file:
        file.write("\n".join(lines))
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with (args.input.parent / "runs.csv").open("x", newline="") as file:
        writer = csv.DictWriter(file, fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, allow_nan=False) if isinstance(v, (list, dict)) else v for k, v in row.items()})
    print(json.dumps({"rows": len(rows), "statuses": dict(Counter(r["status"] for r in rows)), "report": str(args.report)}))


if __name__ == "__main__":
    main()
