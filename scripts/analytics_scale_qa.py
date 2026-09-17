"""Analytics engine at scale: time representative governed queries on QA workspaces of 150, 10,000
and 50,000 products (the 50k fixture carries millions of order rows).

Builds each fixture in process (`scripts.zaad_qa_workspaces.build_scale`, or the DEMO company at
150), then runs every case through the real pipeline — validation, planning, the DuckDB adapter,
result assembly — and records median and p95 of `runs` executions, the payload size and the row
count, so the "server-driven, bounded, no raw datasets to the browser" rule is measured rather
than assumed.

Usage: python3 -m scripts.analytics_scale_qa [--skus 150,10000,50000] [--runs 5] [--out artifacts/analytics_scale.json]
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import date
from pathlib import Path

import duckdb


def cases() -> dict[str, dict]:
    return {
        "time_series_demand_week": {"measures": [{"metric_id": "ordered_units"}, {"metric_id": "shipped_units"}], "time": {"grain": "week"}},
        "time_series_demand_month_category": {"measures": [{"metric_id": "ordered_units"}], "dimensions": [{"dimension_id": "category"}], "time": {"grain": "month"}},
        "supplier_ranking": {"measures": [{"metric_id": "supplier_fill_rate"}, {"metric_id": "supplier_late_rate"}, {"metric_id": "matched_orders"}], "dimensions": [{"dimension_id": "supplier"}], "top_n": {"dimension_id": "supplier", "n": 20}},
        "supplier_trend_month": {"measures": [{"metric_id": "supplier_fill_rate"}], "dimensions": [{"dimension_id": "supplier"}], "time": {"grain": "month", "range": {"last": 12, "unit": "month"}}, "top_n": {"dimension_id": "supplier", "n": 10}},
        "sku_inventory_cover_top": {"measures": [{"metric_id": "weeks_of_cover"}, {"metric_id": "inventory_units"}], "dimensions": [{"dimension_id": "sku"}], "top_n": {"dimension_id": "sku", "n": 50, "by": "inventory_units"}},
        "inventory_by_site_month": {"measures": [{"metric_id": "inventory_units"}, {"metric_id": "inventory_value"}], "dimensions": [{"dimension_id": "location"}], "time": {"grain": "month"}},
        "customer_service": {"measures": [{"metric_id": "fill_rate"}, {"metric_id": "ordered_units"}], "dimensions": [{"dimension_id": "customer"}], "top_n": {"dimension_id": "customer", "n": 25}},
        "multi_dimension_group": {"measures": [{"metric_id": "ordered_units"}], "dimensions": [{"dimension_id": "category"}, {"dimension_id": "location"}], "time": {"grain": "quarter"}},
        "drilldown_category_to_sku": {"measures": [{"metric_id": "ordered_units"}], "dimensions": [{"dimension_id": "sku"}], "filters": [{"dimension_id": "category", "op": "eq", "values": ["Beverages"]}], "time": {"grain": "month", "range": {"last": 6, "unit": "month"}}, "top_n": {"dimension_id": "sku", "n": 20}},
        "open_po_by_supplier": {"measures": [{"metric_id": "open_po_units"}, {"metric_id": "open_po_value"}, {"metric_id": "open_po_count"}], "dimensions": [{"dimension_id": "supplier"}]},
        "kpi_fill_rate": {"measures": [{"metric_id": "fill_rate"}, {"metric_id": "ordered_units"}, {"metric_id": "unfulfilled_units"}]},
        "period_over_period": {"measures": [{"metric_id": "ordered_units"}], "time": {"grain": "month", "range": {"last": 12, "unit": "month"}}, "comparison": {"kind": "period_over_period", "lag": 1}},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skus", default="150,10000,50000")
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--out", default="artifacts/analytics_scale.json")
    args = ap.parse_args()
    from api.analytics import cache, query
    from api.analytics.contracts import AnalyticsQuerySpec
    from scripts.setup_db import setup_db

    results = []
    for n in (int(x) for x in args.skus.split(",") if x.strip()):
        conn = duckdb.connect(":memory:")
        setup_db(conn)
        t = time.perf_counter()
        if n <= 150:
            from synthetic.fmcg.demo_company import load_demo_company_into
            load_demo_company_into(conn, "QA_OPERATOR", as_of=date(2026, 9, 15))
        else:
            from scripts.zaad_qa_workspaces import build_scale
            build_scale(conn, skus=n, seed=23, as_of=date(2026, 9, 15))
        build_s = time.perf_counter() - t
        rows = {tbl: conn.execute(f"SELECT count(*) FROM {tbl}").fetchone()[0] for tbl in  # noqa: S608  # nosec B608 - literals
                ("stg_fmcg_skus", "stg_fmcg_orders", "stg_fmcg_inventory", "stg_fmcg_purchase_orders", "stg_fmcg_receipts")}
        timings: dict[str, dict] = {}
        for name, raw in cases().items():
            spec = AnalyticsQuerySpec.model_validate(raw)
            samples, planned, executed, payload, nrows, truncated = [], [], [], 0, 0, False
            for _ in range(args.runs):
                cache.clear()
                t0 = time.perf_counter()
                out = query.run(conn, "QA_OPERATOR", None, spec, use_cache=False)
                samples.append((time.perf_counter() - t0) * 1000)
                planned.append(out["timing"]["planned_ms"])
                executed.append(out["timing"]["executed_ms"])
                payload = len(json.dumps(out, default=str))
                nrows = out["bounds"]["rows"]
                truncated = out["bounds"]["truncated"]
            ordered = sorted(samples)
            timings[name] = {"median_ms": round(statistics.median(samples), 1), "p95_ms": round(ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))], 1),
                             "planned_median_ms": round(statistics.median(planned), 1), "executed_median_ms": round(statistics.median(executed), 1),
                             "payload_bytes": payload, "rows": nrows, "truncated": truncated, "empty": out["empty"]}
            print(f"{n:>6} products  {name:36s} median {timings[name]['median_ms']:8.1f} ms  p95 {timings[name]['p95_ms']:8.1f} ms  rows {nrows:4d}  payload {payload / 1024:7.1f} KB{'  TRUNCATED' if truncated else ''}", flush=True)
        results.append({"products": n, "rows": rows, "build_s": round(build_s, 1), "runs": args.runs, "queries": timings,
                        "worst_median_ms": max(t["median_ms"] for t in timings.values())})
        conn.close()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "results": results}, indent=2))
    print(f"written {args.out}")


if __name__ == "__main__":
    main()
