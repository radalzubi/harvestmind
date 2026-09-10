"""Canonical customer-data path smoke (post-P1 integration, brief section 27): a SYNTHETIC but
schema-realistic distributor workspace -> validated tenant storage (every migration applied to a fresh
DuckDB) -> the workspace adapter -> the frozen P1 optimizer -> the purchase-plan report. Prints the raw
row counts against the compact optimizer dimensions. Not a customer validation.

usage: PYTHONPATH=. python3 -m scripts.zaad_workspace_smoke [seed] [archetype] [first N SKUs]"""
from __future__ import annotations

import json
import sys
import time

import duckdb

from api.routers.intake import load_fmcg_sample_into
from scripts.setup_db import setup_db
from zaad.full.planner import plan
from zaad.full.workspace import build_request, to_purchase_plan


def main() -> dict:
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    archetype = sys.argv[2] if len(sys.argv) > 2 else "A_stable"
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    loaded = load_fmcg_sample_into(conn, seed=seed, archetype=archetype)
    started = time.time()
    first_n = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    subset = [r[0] for r in conn.execute("SELECT DISTINCT sku FROM stg_fmcg_skus ORDER BY sku").fetchall()][:first_n] if first_n else None
    request, build = build_request(conn, "smoke_tenant", horizon=12, skus=subset)
    built = time.time() - started
    report = plan(request)
    planned = time.time() - started - built
    purchase_plan = to_purchase_plan(request, report, build, run_id="smoke")
    out = {"loaded": loaded["tables"], "raw_rows": loaded["total_rows"], "compact": build["compact"], "fits": build["fits"],
           "incumbent_rule": build["incumbent_rule"], "warnings": build["warnings"], "leakage_guard": build["leakage_guard"],
           "request_bytes": len(request.model_dump_json()), "build_seconds": round(built, 2), "plan_seconds": round(planned, 2),
           "status": report["status"], "state": report["orchestration"].get("state"), "planner_owner": report["orchestration"]["planner_owner"],
           "ownership_reasons": report["orchestration"].get("ownership_reasons"), "reasons": report.get("reasons"), "selected": report.get("selected_policy"),
           "actions": report.get("actions"),
           "orders_in_commit_window": len(purchase_plan["orders"]), "purchase_value": purchase_plan["purchase_value"],
           "approval_required": report["approval_required"], "executable_purchase_order": report["executable_purchase_order"]}
    print(json.dumps(out, indent=1, default=str))
    return out


if __name__ == "__main__":
    main()
