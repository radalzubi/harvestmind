#!/usr/bin/env python3
"""Run the live benchmark repeatedly on Indiana-calibrated synthetic histories."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backtesting.benchmark_suite import run_benchmark  # noqa: E402
from scripts.setup_db import setup_db  # noqa: E402
from synthetic.indiana_operator_sim import (  # noqa: E402
    IndianaSimulationConfig,
    build_indiana_dataset,
)


SPOT_GRID = (
    (1.15, 0.15), (1.15, 0.30),
    (1.30, 0.15), (1.30, 0.30),
    (1.60, 0.15), (1.60, 0.30),
)


def run_matrix(seeds: list[int], weeks: int = 80, folds: int = 12) -> dict:
    rows = []
    simulations = []
    for seed in seeds:
        conn = duckdb.connect(":memory:")
        try:
            setup_db(conn)
            metadata = build_indiana_dataset(
                conn, IndianaSimulationConfig(seed=seed, weeks=weeks)
            )
            simulations.append(metadata)
            for spot_multiplier, spot_capacity in SPOT_GRID:
                result = run_benchmark(
                    conn,
                    n_folds=folds,
                    train_weeks=52,
                    spot_cost_multiplier=spot_multiplier,
                    spot_capacity_factor=spot_capacity,
                    n_yield_draws_seed=seed + 10_000,
                )
                rows.append({
                    "seed": seed,
                    "spot_cost_multiplier": spot_multiplier,
                    "spot_capacity_factor": spot_capacity,
                    "status": result.get("status"),
                    "gate_passed": result.get("gate_passed"),
                    "sp_vs_deterministic_lp_edge_pct": (result.get("sp_vs_deterministic_lp") or {}).get("edge_pct"),
                    "sp_vs_naive_edge_pct": (result.get("sp_vs_naive") or {}).get("edge_pct"),
                    "sp_vs_order_up_to_edge_pct": (result.get("sp_vs_order_up_to") or {}).get("edge_pct"),
                    "sp_service_pct": (result.get("policies") or {}).get("two_sided_sp", {}).get("service_pct"),
                    "deterministic_service_pct": (result.get("policies") or {}).get("deterministic_lp", {}).get("service_pct"),
                    "verdict": result.get("verdict"),
                })
        finally:
            conn.close()

    completed = [row for row in rows if row["status"] == "ok"]
    passed = [row for row in completed if row["gate_passed"]]
    lp_edges = [row["sp_vs_deterministic_lp_edge_pct"] for row in completed if row["sp_vs_deterministic_lp_edge_pct"] is not None]
    naive_edges = [row["sp_vs_naive_edge_pct"] for row in completed if row["sp_vs_naive_edge_pct"] is not None]
    return {
        "label": "SYNTHETIC — not operator validation or a savings claim",
        "configuration": {"seeds": seeds, "weeks": weeks, "folds": folds, "spot_grid": SPOT_GRID},
        "simulations": simulations,
        "summary": {
            "runs": len(rows),
            "completed_runs": len(completed),
            "gate_passes": len(passed),
            "gate_pass_rate_pct": round(100 * len(passed) / len(completed), 1) if completed else None,
            "median_sp_vs_lp_edge_pct": round(sorted(lp_edges)[len(lp_edges) // 2], 2) if lp_edges else None,
            "min_sp_vs_lp_edge_pct": round(min(lp_edges), 2) if lp_edges else None,
            "max_sp_vs_lp_edge_pct": round(max(lp_edges), 2) if lp_edges else None,
            "median_sp_vs_naive_edge_pct": round(sorted(naive_edges)[len(naive_edges) // 2], 2) if naive_edges else None,
        },
        "runs": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", default="11,23,42,67,101")
    parser.add_argument("--weeks", type=int, default=80)
    parser.add_argument("--folds", type=int, default=12)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    seeds = [int(value) for value in args.seeds.split(",") if value.strip()]
    result = run_matrix(seeds, weeks=args.weeks, folds=args.folds)
    payload = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n")
    print(payload)


if __name__ == "__main__":
    main()
