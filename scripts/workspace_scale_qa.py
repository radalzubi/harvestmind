"""Operating-surface reads at scale: time every server-side read the workspace makes, in process,
on the 150-product sample and on the 10,000 / 50,000-product QA fixtures (a year of customer orders
and a purchase-order history per product — millions of rows at 50k). Median / p95 of N runs and the
payload size, so the "bounded, server-side" rule for Home, Inventory, Purchase orders, Data,
Diagnostics and the planner's workspace read is measured rather than assumed.

Usage: python3 -m scripts.workspace_scale_qa [--skus 150,10000,50000] [--runs 5] [--out artifacts/workspace_scale.json]
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
    ap.add_argument("--skus", default="150,10000,50000")
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--out", default="artifacts/workspace_scale.json")
    args = ap.parse_args()
    from api.product import catalog, readiness
    from scripts.setup_db import setup_db
    from zaad.meio.workspace import build_network_request

    results = []
    for n in (int(x) for x in args.skus.split(",") if x.strip()):
        conn = duckdb.connect(":memory:")
        setup_db(conn)
        t = time.perf_counter()
        if n == 150:
            from api.routers.intake import load_fmcg_sample_into
            load_fmcg_sample_into(conn, seed=7)
            fixture = {"sample": True}
        else:
            from scripts.zaad_qa_workspaces import build_scale
            fixture = build_scale(conn, skus=n, seed=23, as_of=date(2026, 9, 15))
        build_s = time.perf_counter() - t
        rows = {tbl: conn.execute(f"SELECT count(*) FROM {tbl}").fetchone()[0] for tbl in  # noqa: S608  # nosec B608 - literals
                ("stg_fmcg_skus", "stg_fmcg_orders", "stg_fmcg_inventory", "stg_fmcg_purchase_orders", "stg_fmcg_receipts")}
        first_sku = conn.execute("SELECT sku FROM stg_fmcg_skus ORDER BY sku LIMIT 1").fetchone()[0]
        category = conn.execute("SELECT category FROM stg_fmcg_skus WHERE category IS NOT NULL LIMIT 1").fetchone()
        category = category[0] if category else None
        first_po = conn.execute("SELECT po_id FROM stg_fmcg_purchase_orders ORDER BY po_date DESC LIMIT 1").fetchone()[0]
        top200 = [r[0] for r in conn.execute("SELECT sku FROM stg_fmcg_skus ORDER BY sku LIMIT 200").fetchall()]
        phases = dict(sourcing=True, recourse=True, atp=True, commitments=True)
        cases = {
            "summary": lambda: catalog.summary(conn),
            "inventory_default": lambda: catalog.inventory_page(conn, limit=50),
            "inventory_sort_value_desc": lambda: catalog.inventory_page(conn, sort="inventory_value", direction="desc", limit=50),
            "inventory_filter_category": lambda: catalog.inventory_page(conn, category=category, limit=50),
            "inventory_search": lambda: catalog.inventory_page(conn, search=first_sku[:6], limit=50),
            "inventory_cover_under2": lambda: catalog.inventory_page(conn, cover="under2", limit=50),
            "inventory_page_20": lambda: catalog.inventory_page(conn, limit=50, offset=1000),
            "inventory_200_by_value": lambda: catalog.inventory_page(conn, sort="inventory_value", direction="desc", limit=200),
            "sku_detail": lambda: catalog.sku_detail(conn, first_sku),
            "purchase_orders_default": lambda: catalog.purchase_order_page(conn, limit=50),
            "purchase_orders_late": lambda: catalog.purchase_order_page(conn, state="late", limit=50),
            "purchase_orders_search": lambda: catalog.purchase_order_page(conn, search=first_sku[:6], limit=50),
            "purchase_order_detail": lambda: catalog.purchase_order_detail(conn, first_po),
            "readiness": lambda: readiness.readiness(conn),
            "search_everything": lambda: catalog.search_everything(conn, first_sku[:5]),
            "locations": lambda: catalog.locations(conn),
            "workspace_request_200": lambda: build_network_request(conn, "qa", horizon=12, service_target=.95, max_solve_seconds=15., skus=top200, **phases)[0],
        }
        if n <= 1000:
            cases["workspace_request_full"] = lambda: build_network_request(conn, "qa", horizon=12, service_target=.95, max_solve_seconds=15., **phases)[0]
        timings = {}
        for name, fn in cases.items():
            samples, size = [], 0
            for _ in range(args.runs):
                t = time.perf_counter()
                out = fn()
                samples.append((time.perf_counter() - t) * 1000)
                try:
                    size = len(json.dumps(out, default=str))
                except TypeError:
                    size = len(out.model_dump_json()) if hasattr(out, "model_dump_json") else -1
            timings[name] = {"median_ms": round(statistics.median(samples), 1),
                             "p95_ms": round(sorted(samples)[max(0, int(0.95 * (len(samples) - 1)))], 1),
                             "max_ms": round(max(samples), 1), "payload_bytes": size}
            print(f"{n:>6} products  {name:28s} median {timings[name]['median_ms']:8.1f} ms  p95 {timings[name]['p95_ms']:8.1f} ms  payload {size:9d} B", flush=True)
        results.append({"products": n, "build_seconds": round(build_s, 1), "rows": rows, "fixture": fixture, "timings": timings,
                        "budget_ms": 800, "over_budget": [k for k, v in timings.items() if v["median_ms"] > 800]})
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(results, indent=2, default=str))
    print(json.dumps([{k: r[k] for k in ("products", "rows", "over_budget")} for r in results], indent=2))


if __name__ == "__main__":
    main()
