"""Insights at scale: time every aggregation on the QA scale workspaces (10,000 and 50,000 products).

Builds the scale fixture from `scripts/zaad_qa_workspaces.build_scale` (a year of customer orders and a
purchase-order history per product — millions of rows at 50k), then times each Insights function in
process: median and p95 of five runs each, plus payload size, so the "no raw datasets to the browser"
rule is measured rather than assumed. The budget the brief names is ~800 ms median for an ordinary query.

Usage: python3 -m scripts.insights_scale_qa [--skus 10000,50000] [--runs 5] [--out artifacts/insights_scale.json]
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import date
from pathlib import Path

import duckdb


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skus", default="10000,50000")
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--out", default="artifacts/insights_scale.json")
    args = ap.parse_args()
    from api.product import insights
    from scripts.setup_db import setup_db
    from scripts.zaad_qa_workspaces import build_scale

    results = []
    for n in (int(x) for x in args.skus.split(",") if x.strip()):
        conn = duckdb.connect(":memory:")
        setup_db(conn)
        t = time.perf_counter()
        built = build_scale(conn, skus=n, seed=23, as_of=date(2026, 9, 15))
        build_s = time.perf_counter() - t
        rows = {tbl: conn.execute(f"SELECT count(*) FROM {tbl}").fetchone()[0] for tbl in  # noqa: S608  # nosec B608 - literals
                ("stg_fmcg_skus", "stg_fmcg_orders", "stg_fmcg_inventory", "stg_fmcg_purchase_orders", "stg_fmcg_receipts")}
        op = "QA_OPERATOR"
        scope_w = insights.scope_from("week")
        scope_m = insights.scope_from("month")
        cases = {
            "summary": lambda: insights.overview(conn, insights.scope_from("week", end="2026-09-15"), op),
            "demand_week": lambda: insights.demand(conn, scope_w),
            "demand_month_category": lambda: insights.demand(conn, insights.scope_from("month", category="Beverages")),
            "demand_period": lambda: insights.demand_period(conn, scope_w, date(2026, 8, 3)),
            "inventory_month": lambda: insights.inventory(conn, scope_m),
            "inventory_week_site": lambda: insights.inventory(conn, insights.scope_from("week", location="QA-DC-AMMAN")),
            "supply_week": lambda: insights.supply(conn, insights.scope_from("week", end="2026-09-15")),
            "suppliers_month": lambda: insights.suppliers(conn, scope_m, op),
            "service_month": lambda: insights.service(conn, scope_m, op),
            "decisions": lambda: insights.decisions(conn, op),
            "value": lambda: insights.value(conn, op),
            "connectivity": lambda: insights.connectivity(conn, op),
        }
        timings = {}
        for name, fn in cases.items():
            samples, size = [], 0
            for _ in range(args.runs):
                t = time.perf_counter()
                out = fn()
                samples.append((time.perf_counter() - t) * 1000)
                size = len(json.dumps(out, default=str))
            timings[name] = {"median_ms": round(statistics.median(samples), 1), "p95_ms": round(sorted(samples)[max(0, int(0.95 * (len(samples) - 1)))], 1),
                             "max_ms": round(max(samples), 1), "payload_bytes": size}
            print(f"{n:>6} products  {name:24s} median {timings[name]['median_ms']:8.1f} ms  p95 {timings[name]['p95_ms']:8.1f} ms  payload {size:8d} B", flush=True)
        results.append({"products": n, "build_seconds": round(build_s, 1), "rows": rows, "fixture": built, "timings": timings,
                        "budget_ms": 800, "over_budget": [k for k, v in timings.items() if v["median_ms"] > 800]})
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(results, indent=2, default=str))
    print(json.dumps([{k: r[k] for k in ("products", "rows", "over_budget")} for r in results], indent=2))


if __name__ == "__main__":
    main()
