"""Central-plus-branch failure decomposition (v6, phase 10).

For every breached network cell in a benchmark file, classify each review with unmet demand from
the per-review network trace, the review status/mode and the remaining planning horizon:

  insufficient_total_inventory   nothing anywhere in the network when demand went unmet
  inventory_at_wrong_echelon     the central held more than the shortfall while a branch ran short
  transfer_capacity              wrong echelon on a capacity-constrained arc
  transfer_too_late              wrong echelon on an arc of two or more reviews
  order_arrived_too_late         network empty while the review was still buying from a live source
  selector_retained_plan         the incumbent was retained during the shortfall while a candidate was rejected
  jointly_impossible             the selector reported the target vector infeasible (ALLOCATE) at that review
  benchmark_horizon_artifact     remaining planning horizon of four reviews or fewer
  scenario_misspecification      closure or correlated cells with no alternate source (unavoidable in the scenario)

A review can carry more than one label; the cell's primary cause is the most frequent label over
its breach reviews. Heuristic and stated as such; it points the next diagnosis, it does not settle it.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

NETWORKS = {"central_branches", "central_two_branches", "two_locations"}


def classify(row: dict) -> tuple[list[dict], collections.Counter]:
    labels: list[dict] = []
    counter: collections.Counter = collections.Counter()
    trace = row.get("network_trace") or []
    status = row.get("review_status") or []
    mode = row.get("review_mode") or []
    constrained = row.get("alternative") == "transfer_constrained" or float(row.get("transfer_capacity", 50.)) < 20.
    slow = int(row.get("transfer_lead", 1)) >= 2
    no_alternate = row.get("alternative") in ("none", "shared_route") and row.get("supply") in ("closure_recovery", "correlated", "severe")
    for r in trace:
        if r["unmet"] <= 0:
            continue
        on_hand = r["on_hand"]
        branches = {k: v for k, v in on_hand.items() if k != "central"}
        central = on_hand.get("central", 0.)
        total = sum(on_hand.values())
        tags = []
        if total <= r["unmet"] * .1:
            tags.append("insufficient_total_inventory")
            if status[r["review"]] not in (None, "ABSTAIN"):
                tags.append("order_arrived_too_late")
        elif central > r["unmet"] and any(v <= r["unmet"] * .1 for v in branches.values()):
            tags.append("inventory_at_wrong_echelon")
            tags.append("transfer_capacity" if constrained else ("transfer_too_late" if slow else "transfer_timing_or_selection"))
        if r["review"] < len(status) and status[r["review"]] == "RETAIN_INCUMBENT":
            tags.append("selector_retained_plan")
        if r["review"] < len(mode) and mode[r["review"]] == "ALLOCATE":
            tags.append("jointly_impossible")
        if r["remaining_horizon"] <= 4:
            tags.append("benchmark_horizon_artifact")
        if no_alternate:
            tags.append("scenario_misspecification")
        labels.append({"review": r["review"], "unmet": r["unmet"], "on_hand": on_hand, "tags": tags})
        counter.update(tags)
    return labels, counter


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("--method", default="gated")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.jsonl.open()]
    table = []
    for row in rows:
        if row["method"] != args.method or row.get("network") not in NETWORKS or not row.get("service_breach"):
            continue
        labels, counter = classify(row)
        primary = counter.most_common(1)[0][0] if counter else "no_unmet_review_in_trace"
        table.append({"cell": row["cell"], "seed": row["seed"], "network": row["network"], "demand": row["demand"], "supply": row["supply"],
                      "alternative": row["alternative"], "target": row["target"], "service": round(row["service"], 3),
                      "inventory_periods": round(row["inventory_periods"], 2), "primary_cause": primary, "labels": dict(counter),
                      "breach_reviews": len(labels)})
    summary = collections.Counter(t["primary_cause"] for t in table)
    report = {"method": args.method, "network_breaches": len(table), "primary_causes": dict(summary), "cells": table}
    if args.output:
        args.output.write_text(json.dumps(report, indent=1))
    print(json.dumps({"network_breaches": len(table), "primary_causes": dict(summary)}, indent=1))
    for t in table:
        print(f"  cell {t['cell']:3d}/{t['seed']} {t['network']:>20s} {t['demand']:>18s} {t['supply']:>22s} alt={t['alternative']:>19s} "
              f"service {t['service']:.3f} inv {t['inventory_periods']:.2f} -> {t['primary_cause']} {t['labels']}")


if __name__ == "__main__":
    main()
