"""Compare planning under baseline conditions against a named disruption.

Never prints a single recommended number. Always the comparison, the
assumption that drove it, and what happens if that assumption is wrong.

    python3 scripts/run_disruption_overlay.py --scenario aqaba_congestion
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backtesting.benchmark_suite import run_benchmark  # noqa: E402
from risk.disruption_scenarios import (  # noqa: E402
    PRESETS, benchmark_overrides, get_scenario,
)
from scripts.setup_db import setup_db  # noqa: E402
from synthetic.indiana_operator_sim import (  # noqa: E402
    IndianaSimulationConfig, build_indiana_dataset,
)


def compare(conn, scenario_name: str, folds: int = 52,
            train_weeks: int = 52) -> dict:
    base = get_scenario("baseline")
    scen = get_scenario(scenario_name)
    common = dict(n_folds=folds, train_weeks=train_weeks,
                  capacity_headroom=1.5, capacity_basis="max_ordered")
    out = {}
    for tag, s in (("baseline", base), (scenario_name, scen)):
        r = run_benchmark(conn, **common, **benchmark_overrides(s))
        pol = r["policies"]["two_sided_sp"]
        out[tag] = {
            "cost_per_week": pol["cost_per_origin"],
            "service_pct": pol["service_pct"],
            "waste_kg_per_week": pol["waste_kg_per_origin"],
            "edge_vs_mean_value_pct": r["sp_vs_mean_value_sp"]["edge_pct"],
        }
    b, d = out["baseline"], out[scenario_name]
    out["delta"] = {
        "cost_per_week": round(d["cost_per_week"] - b["cost_per_week"], 0),
        "cost_pct": round((d["cost_per_week"] / b["cost_per_week"] - 1) * 100, 1)
        if b["cost_per_week"] else None,
        "service_points": round((d["service_pct"] or 0) - (b["service_pct"] or 0), 1),
    }
    out["scenario"] = scen.describe()
    out["assumed"] = True
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scenario", default="aqaba_congestion",
                   choices=sorted(PRESETS))
    p.add_argument("--seed", type=int, default=11)
    p.add_argument("--weeks", type=int, default=160)
    p.add_argument("--folds", type=int, default=52)
    p.add_argument("--output", type=Path)
    a = p.parse_args()

    conn = duckdb.connect(":memory:")
    setup_db(conn)
    build_indiana_dataset(conn, IndianaSimulationConfig(
        seed=a.seed, weeks=a.weeks, mean_supplier_fill_rate=0.85))
    res = compare(conn, a.scenario, folds=a.folds)

    print(f"\n{res['scenario']}\n")
    print(f"{'':26}{'baseline':>12}{a.scenario:>22}")
    for k, lab in [("cost_per_week", "cost per week"),
                   ("service_pct", "service level %"),
                   ("waste_kg_per_week", "waste kg per week"),
                   ("edge_vs_mean_value_pct", "edge vs deterministic %")]:
        print(f"  {lab:24}{res['baseline'][k]:>12}{res[a.scenario][k]:>22}")
    d = res["delta"]
    print(f"\n  cost change: {d['cost_per_week']:+,.0f} per week "
          f"({d['cost_pct']:+.1f}%)   service change: {d['service_points']:+.1f} pts")
    print("\n  EVERY NUMBER IN THE SCENARIO IS AN ASSUMPTION, NOT A FORECAST.")
    print("  This model has no time dimension, so it treats a delay as a")
    print("  shortfall. It cannot recommend ordering EARLIER, only ordering")
    print("  MORE. If rescheduling is your real lever, this understates it.\n")

    if a.output:
        a.output.write_text(json.dumps(res, indent=2))
        print(f"  wrote {a.output}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
