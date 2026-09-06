#!/usr/bin/env python3
"""Service-reliability summary of a run_zaad_full_benchmark --matrix reliability JSONL file.

Per method: achieved service, breaches, avoidable breaches, weighted shortfall, inventory,
working capital, cost versus base stock, emergency actions, false protection on benign cells
and recovery time. Every breach is classified ex post:

    AVOIDABLE          another method met the target on the same cell and seed at a cost within
                       the downside tolerance of the breaching method
    ECONOMIC_TRADEOFF  another method met the target but only at a cost above that tolerance
    MODEL_FAILURE      no method met the target and realized demand or supply fell far outside
                       the review-time model on at least two reviews
    UNAVOIDABLE        no method met the target and the model was not materially wrong

Nothing is dropped: incomplete and failed rows are counted and listed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median

DOWNSIDE = .05


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def classify(row: dict, peers: list[dict]) -> str:
    if not row.get("service_breach"):
        return "MET"
    met = [p for p in peers if p["status"] == "COMPLETE" and not p.get("service_breach") and p["cost"] is not None]
    if met and row["cost"] is not None:
        cheapest = min(p["cost"] for p in met)
        return "AVOIDABLE" if cheapest <= row["cost"] * (1 + DOWNSIDE) + 1e-9 else "ECONOMIC_TRADEOFF"
    if met:
        return "AVOIDABLE"
    failure = row.get("model_failure") or {}
    if failure.get("demand") or failure.get("supply"):
        return "MODEL_FAILURE"
    return "UNAVOIDABLE"


def summarize(rows: list[dict], reference: str = "base_stock") -> dict:
    by_key: dict[tuple, list[dict]] = {}
    for r in rows:
        by_key.setdefault((r["cell"], r["seed"]), []).append(r)
    methods = sorted({r["method"] for r in rows}, key=lambda m: [x["method"] for x in rows].index(m))
    report: dict = {"rows": len(rows), "methods": {}, "by_dimension": {}}
    for method in methods:
        runs = [r for r in rows if r["method"] == method]
        complete = [r for r in runs if r["status"] == "COMPLETE"]
        classes = {"MET": 0, "AVOIDABLE": 0, "ECONOMIC_TRADEOFF": 0, "MODEL_FAILURE": 0, "UNAVOIDABLE": 0}
        shortfalls, services, inventory, capital, emergencies, recoveries, benign_inventory, costs = [], [], [], [], [], [], [], []
        for r in complete:
            peers = [p for p in by_key[r["cell"], r["seed"]] if p["method"] != method]
            classes[classify(r, peers)] += 1
            if r["service"] is not None:
                services.append(r["service"])
                shortfalls.append(max(0., r["target"] - r["service"]))
            if r.get("inventory_periods") is not None:
                inventory.append(r["inventory_periods"])
                if r.get("benign"):
                    benign_inventory.append(r["inventory_periods"])
            if r.get("working_capital") is not None:
                capital.append(r["working_capital"])
            if r.get("emergency_reviews") is not None:
                emergencies.append(r["emergency_reviews"])
            if r.get("recovery_periods") is not None:
                recoveries.append(r["recovery_periods"])
            base = next((p for p in by_key[r["cell"], r["seed"]] if p["method"] == reference and p["cost"] is not None), None)
            if base is not None and r["cost"] is not None:
                costs.append(100 * (base["cost"] - r["cost"]) / max(abs(base["cost"]), 1.))
        report["methods"][method] = {
            "runs": len(runs), "complete": len(complete), "failed_or_incomplete": [
                {"cell": r["cell"], "seed": r["seed"], "status": r["status"], "failure": r.get("failure")} for r in runs if r["status"] != "COMPLETE"],
            "service_breaches": sum(1 for r in complete if r.get("service_breach")),
            "breach_classes": classes,
            "avoidable_breaches": classes["AVOIDABLE"],
            "median_service": median(services) if services else None,
            "median_weighted_shortfall": median(shortfalls) if shortfalls else None,
            "mean_weighted_shortfall": sum(shortfalls) / len(shortfalls) if shortfalls else None,
            "median_inventory_periods": median(inventory) if inventory else None,
            "median_working_capital": median(capital) if capital else None,
            "false_protection_benign_inventory_periods": median(benign_inventory) if benign_inventory else None,
            "emergency_review_share": sum(emergencies) / (12 * len(emergencies)) if emergencies else None,
            "median_recovery_periods": median(recoveries) if recoveries else None,
            "paired_cost_vs_reference": len(costs),
            "median_saving_vs_reference_pct": median(costs) if costs else None,
            "worst_saving_vs_reference_pct": min(costs, default=None),
            "cost_losses_vs_reference": sum(1 for c in costs if c < -1e-6)}
    for dimension in ("inventory", "demand", "supply", "network", "alternative", "target"):
        table: dict = {}
        for r in rows:
            if r["status"] != "COMPLETE" or dimension not in r:
                continue
            cell = table.setdefault(str(r[dimension]), {}).setdefault(r["method"], {"runs": 0, "breaches": 0, "avoidable": 0, "inventory": []})
            cell["runs"] += 1
            cell["breaches"] += int(bool(r.get("service_breach")))
            if r.get("inventory_periods") is not None:
                cell["inventory"].append(r["inventory_periods"])
            peers = [p for p in by_key[r["cell"], r["seed"]] if p["method"] != r["method"]]
            cell["avoidable"] += int(classify(r, peers) == "AVOIDABLE")
        for level in table.values():
            for cell in level.values():
                cell["median_inventory_periods"] = median(cell["inventory"]) if cell["inventory"] else None
                del cell["inventory"]
        report["by_dimension"][dimension] = table
    # Paired: new gated versus frozen gated and versus protected on the same cell and seed.
    pairs = {}
    for a, b in (("gated", "gated_pr24"), ("gated", "protected"), ("protected", "stochastic")):
        wins = losses = ties = 0
        service_wins = service_losses = 0
        for key, group in by_key.items():
            ra = next((r for r in group if r["method"] == a and r["status"] == "COMPLETE"), None)
            rb = next((r for r in group if r["method"] == b and r["status"] == "COMPLETE"), None)
            if ra is None or rb is None or ra["cost"] is None or rb["cost"] is None:
                continue
            if ra["cost"] < rb["cost"] - 1e-6:
                wins += 1
            elif ra["cost"] > rb["cost"] + 1e-6:
                losses += 1
            else:
                ties += 1
            if ra["service"] is not None and rb["service"] is not None:
                service_wins += int(ra["service"] > rb["service"] + 1e-6)
                service_losses += int(ra["service"] < rb["service"] - 1e-6)
        pairs[f"{a}_vs_{b}"] = {"cost_wins": wins, "cost_losses": losses, "ties": ties,
                                "service_wins": service_wins, "service_losses": service_losses}
    report["pairs"] = pairs
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = summarize(load(args.jsonl))
    text = json.dumps(report, indent=1, sort_keys=True)
    if args.output:
        args.output.write_text(text)
    for method, cell in report["methods"].items():
        print(f"{method:14s} complete {cell['complete']:3d} breaches {cell['service_breaches']:3d} avoidable {cell['avoidable_breaches']:3d} "
              f"classes {cell['breach_classes']} med_service {cell['median_service']!s:.6} inv_periods {cell['median_inventory_periods']!s:.5} "
              f"benign_inv {cell['false_protection_benign_inventory_periods']!s:.5} emergency {cell['emergency_review_share']!s:.5} "
              f"saving_vs_base {cell['median_saving_vs_reference_pct']!s:.6} losses {cell['cost_losses_vs_reference']}")
    print(json.dumps(report["pairs"], indent=1))


if __name__ == "__main__":
    main()
