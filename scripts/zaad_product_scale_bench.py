#!/usr/bin/env python3
"""Measure what the operating product's queries actually cost at catalogue scale.

The claim this exists to check is narrow and testable: **a workspace holding tens of thousands of
products stays usable, because no request returns or scans more than a page.** A build that is
green proves nothing about that; a 50,000-product catalogue behind a table that takes six seconds
to sort is a broken product with a passing test suite.

Every timing below is the endpoint's own work — the query, the count, the shaping — against a
DuckDB file produced by ``scripts/zaad_qa_workspaces.py``. It is not an HTTP benchmark and makes no
claim about network time.

Usage::

    python3 scripts/zaad_product_scale_bench.py /tmp/zaad_qa_10k.duckdb /tmp/zaad_qa_50k.duckdb
"""
from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.product import catalog, diagnostics, queries  # noqa: E402

#: What a person waiting on a table will accept. Not a hard gate — a slow developer laptop is not a
#: production server — but a number the report is measured against rather than a vague "fast".
BUDGET_MS = 800.0

REPEATS = 3


def timed(label: str, call, repeats: int = REPEATS) -> dict:
    runs = []
    result = None
    for _ in range(repeats):
        started = time.perf_counter()
        result = call()
        runs.append((time.perf_counter() - started) * 1000)
    rows = None
    total = None
    if hasattr(result, "rows"):
        rows, total = len(result.rows), getattr(result, "total", None)
    elif isinstance(result, dict) and "rows" in result:
        rows, total = len(result["rows"]), result.get("total")
    elif isinstance(result, list):
        rows = len(result)
    return {"label": label, "median_ms": round(statistics.median(runs), 1),
            "max_ms": round(max(runs), 1), "rows": rows, "total": total,
            "within_budget": statistics.median(runs) <= BUDGET_MS}


def measure(path: Path) -> list[dict]:
    import duckdb

    conn = duckdb.connect(str(path), read_only=True)
    skus = [r[0] for r in conn.execute("SELECT sku FROM stg_fmcg_skus ORDER BY sku LIMIT 3").fetchall()]
    supplier = conn.execute("SELECT supplier_id FROM stg_fmcg_suppliers LIMIT 1").fetchone()[0]
    out = [
        timed("inventory first page", lambda: catalog.inventory_page(conn, limit=50)),
        timed("inventory sorted by stock value",
              lambda: catalog.inventory_page(conn, sort="inventory_value", direction="desc", limit=50)),
        timed("inventory sorted by weeks of cover",
              lambda: catalog.inventory_page(conn, sort="cover_weeks", direction="asc", limit=50)),
        timed("inventory search", lambda: catalog.inventory_page(conn, search=skus[0][:8], limit=50)),
        timed("inventory filtered to thin cover", lambda: catalog.inventory_page(conn, cover="under2", limit=50)),
        timed("inventory deep page", lambda: catalog.inventory_page(conn, limit=50, offset=5000)),
        timed("one product", lambda: catalog.sku_detail(conn, skus[0])),
        timed("purchase orders, open", lambda: catalog.purchase_order_page(conn, state="open", limit=50)),
        timed("purchase orders search", lambda: catalog.purchase_order_page(conn, search=skus[1], limit=50)),
        timed("supplier diagnostics list", lambda: diagnostics.supplier_page(conn, limit=50)),
        timed("one supplier", lambda: diagnostics.supplier_detail(conn, str(supplier))),
        timed("data explorer: customer orders", lambda: queries.read_page(conn, "customer_orders", limit=50)),
        timed("data explorer: deep page", lambda: queries.read_page(conn, "customer_orders", limit=50, offset=100_000)),
        timed("data explorer: search", lambda: queries.read_page(conn, "customer_orders", search=skus[2], limit=50)),
        timed("dataset catalogue", lambda: queries.catalogue(conn)),
        timed("global search", lambda: catalog.search_everything(conn, skus[0][:6])),
        timed("operating snapshot", lambda: catalog.summary(conn)),
    ]
    conn.close()
    return out


def main() -> int:
    paths = [Path(p) for p in sys.argv[1:]]
    if not paths:
        print(__doc__)
        return 2
    worst = 0.0
    failures = 0
    for path in paths:
        if not path.exists():
            print(f"missing: {path}")
            return 2
        import duckdb
        conn = duckdb.connect(str(path), read_only=True)
        products = conn.execute("SELECT count(*) FROM stg_fmcg_skus").fetchone()[0]
        rows = sum(conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in (  # noqa: S608
            "stg_fmcg_skus", "stg_fmcg_orders", "stg_fmcg_purchase_orders",
            "stg_fmcg_receipts", "stg_fmcg_inventory"))
        conn.close()
        print(f"\n=== {path.name}: {products:,} products, {rows:,} rows ===")
        print(f"{'query':<42}{'median':>10}{'max':>10}{'rows':>8}{'total':>12}")
        for row in measure(path):
            worst = max(worst, row["median_ms"])
            if not row["within_budget"]:
                failures += 1
            flag = "" if row["within_budget"] else "  OVER BUDGET"
            total = f"{row['total']:,}" if isinstance(row["total"], int) else "-"
            print(f"{row['label']:<42}{row['median_ms']:>9.1f}ms{row['max_ms']:>9.1f}ms"
                  f"{row['rows'] if row['rows'] is not None else '-':>8}{total:>12}{flag}")
    print(f"\nslowest median {worst:.1f} ms against a {BUDGET_MS:.0f} ms budget; "
          f"{failures} quer{'y' if failures == 1 else 'ies'} over it")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
