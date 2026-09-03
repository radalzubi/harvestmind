"""Representative workload timings. Environment is recorded with the numbers
so they are read as measurements on one machine, not guarantees.

Output: artifacts/performance_benchmarks.json and
docs/validation/PERFORMANCE_BENCHMARKS.md
"""
from __future__ import annotations

import io
import json
import platform
import statistics as st
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.uom import PackSpec  # noqa: E402
from optimization.multi_period_sp import MultiPeriodStochasticLP  # noqa: E402
from synthetic.fmcg.distributor_sim import ArchetypeSpec, build_history  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def _timeit(fn, n=3):
    ts = []
    for _ in range(n):
        t0 = time.perf_counter(); fn(); ts.append(time.perf_counter() - t0)
    return {"p50": float(np.median(ts)), "min": float(min(ts)), "max": float(max(ts)), "n": n}


def optimizer_case(n_skus, n_scen, horizon, discrete):
    rng = np.random.default_rng(0)
    prods = [f"P{i}" for i in range(n_skus)]
    rows = [{"scenario_index": w, "scenario_weight": 1 / n_scen, "product_id": j, "period": t,
             "demand_kg": float(rng.uniform(50, 150))} for w in range(n_scen) for j in prods for t in range(horizon)]
    sup = pd.DataFrame([{"supplier_id": f"S{i % 5}", "product_id": j, "capacity_kg": 400.0,
                         "price_per_kg": 2.0} for i, j in enumerate(prods)])
    kw = dict(n_periods=horizon, spot_cost_multiplier=1.0, spot_capacity_factor=0.0,
              holding_cost_by_product={j: 0.02 for j in prods}, unmet_cost_by_product={j: 1.0 for j in prods},
              waste_cost_by_product={j: 2.0 for j in prods}, decay_rate_by_product={j: 0.0 for j in prods},
              time_limit_s=120.0)
    if discrete:
        kw["pack_specs"] = {j: PackSpec(units_per_case=12, moq_units=48) for j in prods}
    leads = {(w, f"S{i}"): 1 + (i % 3) for w in range(n_scen) for i in range(5)}

    def run():
        r = MultiPeriodStochasticLP(**kw).solve(pd.DataFrame(rows), sup, lead_times=leads)
        assert r["usable"], r["status"]
    return run


def main() -> int:
    out = {"environment": {"platform": platform.platform(), "python": platform.python_version(),
                           "machine": platform.machine(), "cpu_count": __import__("os").cpu_count()},
           "optimizer": {}, "simulator": {}, "ingestion": {}, "api": {}}
    print("optimizer")
    for n_skus, n_scen, horizon, discrete in ((10, 30, 12, False), (100, 30, 12, False), (100, 30, 12, True),
                                              (1000, 20, 8, False), (500, 20, 8, True)):
        key = f"skus={n_skus},scen={n_scen},H={horizon},{'MILP' if discrete else 'LP'}"
        try:
            out["optimizer"][key] = _timeit(optimizer_case(n_skus, n_scen, horizon, discrete), n=2 if n_skus >= 500 else 3)
        except AssertionError as e:
            out["optimizer"][key] = {"error": str(e)}
        print(f"  {key:<40} {out['optimizer'][key]}", flush=True)
    print("simulator")
    for n_skus, weeks in ((60, 156), (150, 156), (1000, 104)):
        key = f"skus={n_skus},weeks={weeks}"
        out["simulator"][key] = _timeit(lambda: build_history("A_stable", seed=0, spec=ArchetypeSpec(
            "A", n_skus=n_skus, n_suppliers=10, n_customers=25, weeks=weeks)), n=1)
        print(f"  {key:<40} {out['simulator'][key]}", flush=True)
    print("ingestion")
    import duckdb
    from ingestion.validators import validate_staging_df
    for n in (10_000, 100_000):
        df = pd.DataFrame({"product_name": np.random.choice(["A", "B", "C"], n),
                           "requested_quantity": np.random.uniform(1, 500, n).round(1),
                           "order_date": pd.date_range("2024-01-01", periods=n, freq="h").strftime("%Y-%m-%d")})
        out["ingestion"][f"validate_rows={n}"] = _timeit(lambda: validate_staging_df("stg_buyer_orders", df), n=3)
        conn = duckdb.connect()
        conn.register("df_bench", df)
        conn.execute("CREATE TABLE t AS SELECT * FROM df_bench LIMIT 0")
        out["ingestion"][f"duckdb_insert_rows={n}"] = _timeit(
            lambda: conn.execute("INSERT INTO t SELECT * FROM df_bench"), n=3)
        print(f"  rows={n} {out['ingestion'][f'validate_rows={n}']}", flush=True)
    print("api")
    from fastapi.testclient import TestClient
    import api.main as api_main
    client = TestClient(api_main.app)
    for path in ("/health", "/ready", "/"):
        lat = []
        for _ in range(50):
            t0 = time.perf_counter(); client.get(path); lat.append((time.perf_counter() - t0) * 1000)
        out["api"][path] = {"p50_ms": float(np.percentile(lat, 50)), "p95_ms": float(np.percentile(lat, 95)),
                            "p99_ms": float(np.percentile(lat, 99))}
        print(f"  {path:<10} {out['api'][path]}")
    (ROOT / "artifacts").mkdir(exist_ok=True)
    (ROOT / "artifacts" / "performance_benchmarks.json").write_text(json.dumps(out, indent=1))
    md = ["# Performance benchmarks", "", f"Environment: {out['environment']}", "",
          "These are measurements on one developer machine, not guarantees.", "",
          "## Optimizer (MultiPeriodStochasticLP, HiGHS)", "", "| case | p50 s | min s | max s |", "|---|---|---|---|"]
    for k, v in out["optimizer"].items():
        md.append(f"| {k} | {v.get('p50', float('nan')):.2f} | {v.get('min', float('nan')):.2f} | {v.get('max', float('nan')):.2f} |" if "p50" in v else f"| {k} | error: {v['error']} | | |")
    md += ["", "## Simulator", "", "| case | s |", "|---|---|"]
    md += [f"| {k} | {v['p50']:.2f} |" for k, v in out["simulator"].items()]
    md += ["", "## Ingestion", "", "| case | p50 s |", "|---|---|"]
    md += [f"| {k} | {v['p50']:.3f} |" for k, v in out["ingestion"].items()]
    md += ["", "## API (in-process TestClient)", "", "| path | p50 ms | p95 ms | p99 ms |", "|---|---|---|---|"]
    md += [f"| {k} | {v['p50_ms']:.1f} | {v['p95_ms']:.1f} | {v['p99_ms']:.1f} |" for k, v in out["api"].items()]
    (ROOT / "docs" / "validation").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs" / "validation" / "PERFORMANCE_BENCHMARKS.md").write_text("\n".join(md) + "\n")
    print("wrote docs/validation/PERFORMANCE_BENCHMARKS.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
