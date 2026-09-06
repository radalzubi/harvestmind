#!/usr/bin/env python3
"""Paired comparison of demand-adaptation modes from run_zaad_full_benchmark JSONL files.

For every (cell, seed, method) present in all files, reports the modeled-cost change of each
mode relative to the reference mode (default: symmetric, the frozen PR23 rule) and service
breaches, split by demand pattern. Every loss is counted; nothing is dropped.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median


def load(path: Path) -> dict:
    rows = {}
    for line in path.read_text().splitlines():
        r = json.loads(line)
        rows[r["cell"], r["seed"], r["method"]] = r
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path, help="name=path.jsonl pairs")
    parser.add_argument("--reference", default="symmetric")
    parser.add_argument("--methods", nargs="+", default=["gated", "stochastic", "frozen_forecast"])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = {}
    for item in args.files:
        name, path = str(item).split("=", 1)
        data[name] = load(Path(path))
    ref = data[args.reference]
    report = {}
    for name, rows in data.items():
        for method in args.methods:
            keys = [k for k in rows if k[2] == method and k in ref]
            by_demand: dict[str, dict] = {}
            for k in keys:
                a, b = ref[k], rows[k]
                d = a["demand"]
                cell = by_demand.setdefault(d, {"pairs": 0, "cost_change_pct": [], "losses": 0, "breaches_ref": 0, "breaches": 0,
                                                "service_ref": [], "service": [], "incomplete": 0})
                cell["pairs"] += 1
                cell["breaches_ref"] += int(bool(a.get("service_breach")))
                cell["breaches"] += int(bool(b.get("service_breach")))
                if a.get("service") is not None:
                    cell["service_ref"].append(a["service"])
                if b.get("service") is not None:
                    cell["service"].append(b["service"])
                if a["cost"] is None or b["cost"] is None:
                    cell["incomplete"] += 1
                    continue
                change = 100 * (b["cost"] - a["cost"]) / max(abs(a["cost"]), 1.)
                cell["cost_change_pct"].append(change)
                cell["losses"] += int(change > 1e-6)
            for d, cell in by_demand.items():
                cell["median_cost_change_pct"] = median(cell["cost_change_pct"]) if cell["cost_change_pct"] else None
                cell["worst_cost_change_pct"] = max(cell["cost_change_pct"], default=None)
                cell["best_cost_change_pct"] = min(cell["cost_change_pct"], default=None)
                cell["median_service_ref"] = median(cell["service_ref"]) if cell["service_ref"] else None
                cell["median_service"] = median(cell["service"]) if cell["service"] else None
                del cell["cost_change_pct"], cell["service_ref"], cell["service"]
            report[f"{name}/{method}"] = by_demand
    text = json.dumps(report, indent=1, sort_keys=True)
    if args.output:
        args.output.write_text(text)
    for key, by_demand in sorted(report.items()):
        for d, c in sorted(by_demand.items()):
            print(f"{key:28s} {d:10s} pairs={c['pairs']:2d} cost_change_median={c['median_cost_change_pct']!s:>8} worst={c['worst_cost_change_pct']!s:>8} losses={c['losses']} breaches {c['breaches_ref']}->{c['breaches']} service {c['median_service_ref']}->{c['median_service']}")


if __name__ == "__main__":
    main()
