#!/usr/bin/env python3
"""New, version-frozen synthetic network evidence. Never writes v1 evidence.

Development / validation / final are separate seeds. The final command refuses
any source mismatch with its pre-registered manifest and refuses overwriting.
Every failed solve, physical failure, loss, and parameter vector is retained.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import itertools
import json
from pathlib import Path
from statistics import median
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from zaad.full.contracts import Request  # noqa: E402
from zaad.full.demo import example  # noqa: E402
from zaad.full.replay import replay  # noqa: E402
from zaad.full.worlds import World  # noqa: E402

SEEDS = {"development": [14001], "validation": [15001, 15002], "final": [22001, 22002, 22003, 22004, 22005]}
METHODS = ["base_stock", "order_up_to", "deterministic", "stochastic", "robust", "frozen_forecast", "gated"]


def cells(matrix="coverage"):
    values = []
    targets_ = [.9, .93, .95, .97, .98, .99, .995]
    stock = [.1, 1., 2., 4., 7.]
    demands = ["stable", "seasonal", "intermittent", "promotion", "increase", "decrease"]
    supplies = ["stable", "fill", "lead", "long"]
    networks = ["single", "two_locations", "central_branches"]
    suppliers = ["single", "independent", "correlated"]
    if matrix == "full":
        normal = itertools.product(targets_, stock, demands, supplies, networks, suppliers)
    else:
        normal = list(itertools.product(targets_, stock, ["stable"], ["stable"], ["single"], ["single"]))
        normal += [( .95, 2., demand, supply, networks[(i + j) % 3], suppliers[(i + 2*j) % 3])
                   for i, demand in enumerate(demands) for j, supply in enumerate(supplies)]
    for target, cover, demand, supply, network, supplier in normal:
        values.append({"family": "normal", "target": target, "cover": cover, "demand": demand,
                       "supply": supply, "network": network, "suppliers": supplier, "case": "normal"})
    disruption = ["none", "early", "mild", "moderate", "severe", "partial_closure", "supplier_outage",
                  "shared_outage", "alternative", "no_alternative", "delayed_recovery", "false_alarm",
                  "physical_before_news", "news_before_physical", "correlated", "freight_spike", "cash_crisis"]
    for kind in disruption:
        values.append({"family": "disruption", "target": .95, "cover": 2., "demand": "stable", "supply": "stable",
                       "network": "single", "suppliers": "independent" if kind == "alternative" else "single", "case": kind})
    for extra_lead, fill, recovery in [(3, .8, 7), (4, .7, 7), (6, .5, 9), (2, .9, 9), (4, .8, 9)]:
        values.append({"family": "misspecification", "target": .95, "cover": 2., "demand": "stable", "supply": "stable",
                       "network": "single", "suppliers": "correlated", "case": "misspecified",
                       "truth_extra_lead": extra_lead, "truth_fill": fill, "truth_recovery": recovery})
    for kind in ["transfer", "substitution", "recovery", "cash"]:
        values.append({"family": "action", "target": .95, "cover": 2., "demand": "stable", "supply": "stable", "network": "single", "suppliers": "single", "case": kind})
    return [{"cell": i, **value} for i, value in enumerate(values)]


def request_for(cell, seed):
    case = cell["case"] if cell["family"] == "action" else "normal"
    req = example(case, seed)
    data = req.model_dump(mode="json")
    H = 12
    data["horizon"], data["scenarios"], data["max_solve_seconds"] = H, 3, 5.
    data["liquidity"]["known_receivables"] = [0.] * H
    data["liquidity"]["other_payments"] = [0.] * H
    data["liquidity"]["opening_cash"] = 10000. if cell["case"] not in {"cash", "cash_crisis"} else 350.
    if cell["case"] == "cash_crisis":
        data["liquidity"]["credit_limit"] = 0.
        data["terms"][0]["deposit_fraction"] = 1.
    for source in data["sources"]:
        source["capacity_by_period"] = [100.] * H
        source["lead_days"] = 21 if cell["supply"] == "long" else 7
        source["fill_mean"] = .85 if cell["supply"] == "fill" else .97
        source["fill_sd"] = .08 if cell["supply"] == "fill" else .01
        source["lead_sd_days"] = 7. if cell["supply"] == "lead" else 0.
        if cell["case"] == "freight_spike":
            source["freight_per_unit"] = 2.
    for resource in data["resources"]:
        resource["capacity_by_period"] = [100.] * H
    if cell["suppliers"] != "single":
        source = {**data["sources"][0], "id": "alternate", "supplier": "alternate_supplier",
                  "route": ["alternate_supplier", "other_port", "branch"], "unit_price": 5.5,
                  "resources": ["alternate_capacity"], "capacity_by_period": [50.] * H}
        data["sources"].append(source)
        data["resources"].append({"id": "alternate_capacity", "known_at": data["as_of"], "capacity_by_period": [50.] * H,
                                  "failure_domains": ["port"] if cell["suppliers"] == "correlated" else ["other_port"]})
    if cell["network"] != "single":
        data["locations"].append({**data["locations"][0], "id": "central", "kind": "central_dc", "holding_per_value_period": .003})
        data["stock"].append({**data["stock"][0], "id": "central_excess", "location": "central", "quantity": 80.})
        data["transfers"].append({"id": "central_branch", "known_at": data["as_of"], "sku": "A", "origin": "central", "destination": "branch",
                                  "lead_periods": 1, "capacity": 50., "cost_per_unit": .2, "loss_fraction": .01, "approved": True})
        if cell["network"] == "central_branches":
            data["sources"][0]["destination"] = "central"
            data["sources"][0]["route"][-1] = "central"
    if cell["family"] != "action":
        data["stock"][0]["quantity"] = cell["cover"] * 20
    data["services"][0]["target"] = cell["target"]
    rng = np.random.default_rng(seed + 210000)
    history = []
    for period in range(-78, 0):
        mu = 20 * (1 + .3 * np.sin(2 * np.pi * period / 26)) if cell["demand"] == "seasonal" else 20.
        q = max(0., rng.normal(mu, 2))
        if cell["demand"] == "intermittent":
            q = q * 2 if rng.random() < .5 else 0.
        history.append({"known_at": data["as_of"], "service": "retail_A", "period": period, "quantity": q})
    data["history"] = history
    if cell["demand"] == "promotion":
        data["events"] = [{"id": "promotion", "known_at": data["as_of"], "service": "retail_A", "start": 3, "end": 5, "multiplier": 1.8, "label": "known promotion"}]
    # Estimated stress differs deliberately from final realized severity/recovery.
    data["stresses"] = [{"name": "operator_adverse", "fill_multiplier": .7, "extra_lead_days": 28,
                         "demand_multiplier": 1.1, "recovery_period": 9, "shared_failure": True,
                         "affected_resources": ["port_cap"]}]
    return Request.model_validate(data)


def truth_for(req, cell, seed):
    """Separate generator, not the fitted/bootstrap scenario model."""
    rng = np.random.default_rng(seed + 410000)
    H = req.horizon
    demand = []
    for t in range(H):
        mu = 20 * (1 + .3 * np.sin(2 * np.pi * t / 26)) if cell["demand"] == "seasonal" else 20.
        if cell["demand"] == "promotion" and 3 <= t <= 5:
            mu *= 1.8
        if cell["demand"] in {"increase", "decrease"} and t >= 3:
            mu *= 1.8 if cell["demand"] == "increase" else .35
        q = float(rng.poisson(mu))
        if cell["demand"] == "intermittent":
            q = 2 * q if rng.random() < .5 else 0.
        demand.append(q)
    arrivals, fills = {}, {}
    kind = cell["case"]
    shock = kind not in {"normal", "none", "false_alarm", "transfer", "substitution", "recovery", "cash"}
    recovery = cell.get("truth_recovery", 9 if kind == "delayed_recovery" else 7)
    extra = cell.get("truth_extra_lead", 6 if kind in {"severe", "shared_outage"} else 3)
    floor = cell.get("truth_fill", .5 if kind in {"severe", "supplier_outage"} else .8)
    shared = rng.normal(size=H)
    for source in req.sources:
        for t in range(H):
            z = shared[t] if cell["suppliers"] == "correlated" else rng.normal()
            fill = float(np.clip(source.fill_mean + source.fill_sd * z, 0, 1))
            lead = max(1, round(source.lead_days / req.period_days + abs(rng.normal()) * source.lead_sd_days / req.period_days))
            affected = shock and 1 <= t < recovery and (source.id == "main" or kind in {"shared_outage", "correlated"})
            if affected:
                fill *= floor
                lead += extra
            arrivals[source.id, t], fills[source.id, t] = t + lead, fill
    return World(f"independent_truth:{seed}:{cell['cell']}", 1., {"retail_A": tuple(demand)}, arrivals, fills,
                 {p.id: next(o.due_in for o in p.options if o.action == "keep") for p in req.pipeline},
                 {p.id: p.expected_accepted_remaining / p.remaining for p in req.pipeline})


def task(args):
    cell, seed, method = args
    req = request_for(cell, seed)
    truth = truth_for(req, cell, seed)
    started = time.monotonic()
    result = replay(req, truth, req.horizon, method)
    rows = result["reviews"]
    d = sum(s["demand"] for r in rows for s in r["settlement"]["service_by_period"])
    served = sum(s["served"] for r in rows for s in r["settlement"]["service_by_period"])
    return {**cell, "seed": seed, "method": method, "status": result["status"], "cost": result.get("economic_cost"),
            "service": served / d if d else None, "completed_reviews": len(rows), "service_breach": bool(d and served / d < cell["target"] - 1e-6),
            "recovery_solves": sum(bool(r["warnings"]) for r in rows), "failure": result.get("failure"),
            "ledger": result.get("ledger"), "seconds": time.monotonic() - started,
            "forecast_methods": [r["forecast"]["retail_A"]["method"] for r in rows],
            "change_origins": [r["forecast"]["retail_A"]["segment_origin"] for r in rows],
            "min_cash": min((x["cash"] for r in rows for x in r["settlement"]["trace"]), default=None),
            "max_debt": max((x["debt"] for r in rows for x in r["settlement"]["trace"]), default=None),
            "closing_inventory": rows[-1]["settlement"]["trace"][-1]["inventory_value"] if rows else None}


def source_hash():
    paths = sorted((ROOT / "zaad/full").glob("*.py")) + [Path(__file__)]
    return hashlib.sha256(b"".join(p.relative_to(ROOT).as_posix().encode() + p.read_bytes() for p in paths)).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=list(SEEDS), default="development")
    parser.add_argument("--matrix", choices=["coverage", "full"], default="coverage")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    manifest = args.output.parent / "preregistered.json"
    configuration = {"source_hash": source_hash(), "seeds": SEEDS, "methods": METHODS,
                     "matrix": args.matrix, "cells": cells(args.matrix),
                     "gated_controller_included": True,
                     "scope": "rolling policy comparison including gated controller; not real-operator validation"}
    if args.freeze:
        manifest.parent.mkdir(parents=True, exist_ok=True)
        with manifest.open("x") as f:
            json.dump(configuration, f, indent=2)
        print("FROZEN", configuration["source_hash"], flush=True)
        return
    if args.split == "final":
        if args.limit or not manifest.exists() or json.loads(manifest.read_text()) != configuration:
            raise SystemExit("Final requires an exact frozen source/configuration and no run limit")
    if args.output.exists():
        raise SystemExit("Refusing to overwrite evidence")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    selected = configuration["cells"][:args.limit] if args.limit else configuration["cells"]
    tasks = [(c, s, m) for c in selected for s in SEEDS[args.split] for m in METHODS]
    with args.output.open("x") as file, ProcessPoolExecutor(max_workers=args.workers) as pool:
        for i, row in enumerate(pool.map(task, tasks, chunksize=1)):
            file.write(json.dumps(row, allow_nan=False) + "\n")
            file.flush()
            if i % 25 == 0:
                print(f"{i+1}/{len(tasks)} rows; {row['status']}", flush=True)
    rows = [json.loads(line) for line in args.output.read_text().splitlines()]
    summary = {}
    for method in METHODS:
        runs = [r for r in rows if r["method"] == method]
        savings = []
        for r in runs:
            before = next(b for b in rows if b["cell"] == r["cell"] and b["seed"] == r["seed"] and b["method"] == "base_stock")
            if before["cost"] is not None and r["cost"] is not None:
                savings.append(100 * (before["cost"] - r["cost"]) / max(abs(before["cost"]), 1.))
        summary[method] = {"runs": len(runs), "complete": sum(r["status"] == "COMPLETE" for r in runs),
                           "service_breaches": sum(r["service_breach"] for r in runs),
                           "paired_completes": len(savings), "median_vs_base_stock_pct": median(savings) if savings else None,
                           "min": min(savings, default=None), "max": max(savings, default=None), "cost_losses": sum(v < -1e-6 for v in savings)}
    args.output.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
