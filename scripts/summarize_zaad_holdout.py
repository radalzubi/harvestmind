#!/usr/bin/env python3
"""Full holdout report for a run_zaad_full_benchmark --matrix reliability JSONL file.

Beyond summarize_zaad_reliability (breach classes, paired cost, inventory), this reports
medians and ranges, ledger components (shortage, holding, transfer, amendment fees),
regret against the best method on the same cell, quiet-cell excess protection against the
competent baseline, per-regime breakdowns for every matrix dimension, worst cells, and the
gated selector's regime choices per review. Nothing is dropped or averaged away.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from statistics import median

from summarize_zaad_reliability import classify, summarize  # noqa: E402  (same directory)

SHORTAGE_KEYS = ("lost_sales_opportunity", "sla")
HOLDING_KEYS = ("holding",)
ACTION_KEYS = ("transfer", "expedite_fee", "de_expedite_fee", "cancel_fee", "reschedule_fee", "order_fees", "substitution")


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def rng(values):
    values = [v for v in values if v is not None]
    return {"median": median(values), "min": min(values), "max": max(values), "n": len(values)} if values else None


def holdout_report(rows: list[dict], baseline: str = "base_stock") -> dict:
    base = summarize(rows, reference=baseline)
    by_key: dict[tuple, list[dict]] = {}
    for r in rows:
        by_key.setdefault((r["cell"], r["seed"]), []).append(r)
    methods = list(base["methods"])
    report: dict = {"rows": len(rows), "methods": {}, "regimes": {}, "worst_cells": {}, "selector": {}, "base": base}
    for method in methods:
        runs = [r for r in rows if r["method"] == method and r["status"] == "COMPLETE"]
        ledger = lambda r, keys: sum(r["ledger"].get(k, 0.) for k in keys) if r.get("ledger") else None  # noqa: E731
        regrets, benign_excess, quiet_inv, disruption_inv = [], [], [], []
        for r in runs:
            group = by_key[r["cell"], r["seed"]]
            best = min((p["cost"] for p in group if p["status"] == "COMPLETE" and p["cost"] is not None), default=None)
            if best is not None and r["cost"] is not None:
                regrets.append(100 * (r["cost"] - best) / max(abs(best), 1.))
            ref = next((p for p in group if p["method"] == baseline and p["status"] == "COMPLETE"), None)
            if r.get("benign") and r.get("inventory_periods") is not None:
                quiet_inv.append(r["inventory_periods"])
                if ref is not None and ref.get("inventory_periods") is not None:
                    benign_excess.append(r["inventory_periods"] - ref["inventory_periods"])
            if r.get("supply") in {"severe", "partial", "correlated", "lead", "fill"} and r.get("inventory_periods") is not None:
                disruption_inv.append(r["inventory_periods"])
        report["methods"][method] = {
            **base["methods"][method],
            "service": rng([r["service"] for r in runs]),
            "inventory_periods": rng([r.get("inventory_periods") for r in runs]),
            "working_capital": rng([r.get("working_capital") for r in runs]),
            "quiet_cell_inventory_periods": rng(quiet_inv),
            "quiet_cell_excess_vs_baseline_periods": rng(benign_excess),
            "disruption_cell_inventory_periods": rng(disruption_inv),
            "recovery_periods": rng([r.get("recovery_periods") for r in runs]),
            "stockout_periods": rng([r.get("stockout_periods") for r in runs]),
            "cost": rng([r["cost"] for r in runs]),
            "shortage_cost": rng([ledger(r, SHORTAGE_KEYS) for r in runs]),
            "holding_cost": rng([ledger(r, HOLDING_KEYS) for r in runs]),
            "action_cost": rng([ledger(r, ACTION_KEYS) for r in runs]),
            "regret_vs_best_pct": rng(regrets),
            "unavoidable_breaches": base["methods"][method]["breach_classes"]["UNAVOIDABLE"],
            "model_failure_breaches": base["methods"][method]["breach_classes"]["MODEL_FAILURE"],
            "economic_tradeoff_breaches": base["methods"][method]["breach_classes"]["ECONOMIC_TRADEOFF"],
        }
        # Selector regimes for gated methods.
        statuses = Counter(s for r in runs for s in (r.get("review_status") or []))
        modes = Counter(m for r in runs for m in (r.get("review_mode") or []))
        policies = Counter(p for r in runs for p in (r.get("review_policy") or []))
        if statuses:
            report["selector"][method] = {"review_status": dict(statuses), "review_mode": dict(modes), "review_policy": dict(policies)}
    # Regime breakdowns with medians per method.
    for dimension in ("inventory", "demand", "supply", "network", "alternative", "target"):
        table: dict = {}
        for r in rows:
            if r["status"] != "COMPLETE" or dimension not in r:
                continue
            cell = table.setdefault(str(r[dimension]), {}).setdefault(r["method"], {"runs": 0, "breaches": 0, "avoidable": 0, "service": [], "inventory": [], "cost": []})
            cell["runs"] += 1
            cell["breaches"] += int(bool(r.get("service_breach")))
            peers = [p for p in by_key[r["cell"], r["seed"]] if p["method"] != r["method"]]
            cell["avoidable"] += int(classify(r, peers) == "AVOIDABLE")
            if r["service"] is not None:
                cell["service"].append(r["service"])
            if r.get("inventory_periods") is not None:
                cell["inventory"].append(r["inventory_periods"])
            if r["cost"] is not None:
                cell["cost"].append(r["cost"])
        for level in table.values():
            for cell in level.values():
                cell["median_service"] = median(cell["service"]) if cell["service"] else None
                cell["median_inventory_periods"] = median(cell["inventory"]) if cell["inventory"] else None
                cell["median_cost"] = median(cell["cost"]) if cell["cost"] else None
                for k in ("service", "inventory", "cost"):
                    del cell[k]
        report["regimes"][dimension] = table
    # Worst cells per method: largest service shortfall and largest inventory.
    for method in methods:
        runs = [r for r in rows if r["method"] == method and r["status"] == "COMPLETE" and r["service"] is not None]
        worst_service = sorted(runs, key=lambda r: r["service"] - r["target"])[:5]
        worst_inventory = sorted((r for r in runs if r.get("inventory_periods") is not None), key=lambda r: -r["inventory_periods"])[:5]
        report["worst_cells"][method] = {
            "service": [{"cell": r["cell"], "seed": r["seed"], "demand": r["demand"], "supply": r["supply"], "alternative": r.get("alternative"),
                         "target": r["target"], "service": r["service"], "class": classify(r, [p for p in by_key[r["cell"], r["seed"]] if p["method"] != method])}
                        for r in worst_service],
            "inventory": [{"cell": r["cell"], "seed": r["seed"], "demand": r["demand"], "supply": r["supply"], "alternative": r.get("alternative"),
                           "inventory_periods": r["inventory_periods"], "service": r["service"]} for r in worst_inventory]}
    # Paired comparisons between every pair of interest.
    pairs = {}
    for a, b in (("gated", "gated_pr30"), ("gated", "gated_pr24"), ("gated", baseline), ("gated_pr30", "gated_pr24"),
                 ("robust", "stochastic"), ("protected", "stochastic"), ("gated", "robust")):
        cost_w = cost_l = svc_w = svc_l = inv_lower = inv_higher = 0
        for group in by_key.values():
            ra = next((r for r in group if r["method"] == a and r["status"] == "COMPLETE"), None)
            rb = next((r for r in group if r["method"] == b and r["status"] == "COMPLETE"), None)
            if ra is None or rb is None:
                continue
            if ra["cost"] is not None and rb["cost"] is not None:
                cost_w += int(ra["cost"] < rb["cost"] - 1e-6)
                cost_l += int(ra["cost"] > rb["cost"] + 1e-6)
            if ra["service"] is not None and rb["service"] is not None:
                svc_w += int(ra["service"] > rb["service"] + 1e-6)
                svc_l += int(ra["service"] < rb["service"] - 1e-6)
            if ra.get("inventory_periods") is not None and rb.get("inventory_periods") is not None:
                inv_lower += int(ra["inventory_periods"] < rb["inventory_periods"] - 1e-6)
                inv_higher += int(ra["inventory_periods"] > rb["inventory_periods"] + 1e-6)
        pairs[f"{a}_vs_{b}"] = {"cost_wins": cost_w, "cost_losses": cost_l, "service_wins": svc_w, "service_losses": svc_l,
                                "inventory_lower": inv_lower, "inventory_higher": inv_higher}
    report["pairs"] = pairs
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--baseline", default="base_stock")
    args = parser.parse_args()
    report = holdout_report(load(args.jsonl), args.baseline)
    if args.output:
        args.output.write_text(json.dumps(report, indent=1, sort_keys=True))
    for method, m in report["methods"].items():
        inv = m["inventory_periods"]
        print(f"{method:12s} complete {m['complete']:3d} breaches {m['service_breaches']:3d} avoidable {m['avoidable_breaches']:3d} unavoidable {m['unavoidable_breaches']:3d} "
              f"model_fail {m['model_failure_breaches']:3d} med_service {m['service']['median'] if m['service'] else None!s:.6} "
              f"inv med {inv['median'] if inv else None!s:.5} [{inv['min'] if inv else None!s:.4},{inv['max'] if inv else None!s:.4}] "
              f"quiet {m['quiet_cell_inventory_periods']['median'] if m['quiet_cell_inventory_periods'] else None!s:.5} "
              f"regret_med {m['regret_vs_best_pct']['median'] if m['regret_vs_best_pct'] else None!s:.5} "
              f"saving_vs_base {m['median_saving_vs_reference_pct']!s:.6}")
    print(json.dumps(report["pairs"], indent=1))


if __name__ == "__main__":
    main()
