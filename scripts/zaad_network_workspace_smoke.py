"""P2 network workspace smoke: a SYNTHETIC distributor vault re-shaped into one central DC and two
branches -> validated tenant storage (every migration applied to a fresh DuckDB) -> the network
workspace adapter -> the frozen P1 optimizer with the P2 network layer -> the network plan shape.
Prints the compact dimensions, the declared and inferred network inputs, the decision and the
runtime. Not a customer validation; no customer data anywhere.

usage: PYTHONPATH=. python3 -m scripts.zaad_network_workspace_smoke [seed] [first N SKUs] [max_solve_seconds]"""
from __future__ import annotations

import json
import sys
import time

import duckdb

from api.routers.intake import load_fmcg_sample_into
from scripts.setup_db import setup_db
from zaad.meio.planner import plan_network
from zaad.meio.workspace import build_network_request, to_network_plan


def make_network_vault(conn, seed: int = 7, branches: tuple[str, ...] = ("NORTH", "SOUTH"), central: str = "DC") -> dict:
    """Split the synthetic single-site sample across branches: orders and inventory by a stable hash of
    the order / SKU, purchase orders delivered to the DC, declared lanes DC -> branch, and a short
    transfer history so the lane lead is fitted rather than assumed for one lane."""
    loaded = load_fmcg_sample_into(conn, seed=seed)
    n = len(branches)
    case_list = " ".join(f"WHEN {i} THEN '{b}'" for i, b in enumerate(branches))
    conn.execute(f"UPDATE stg_fmcg_orders SET location_id = CASE (abs(hash(coalesce(order_id, sku))) % {n}) {case_list} END")
    conn.execute("DELETE FROM stg_fmcg_inventory WHERE location_id IS NULL OR location_id = 'MAIN' AND FALSE")
    # inventory: the snapshot on hand split across the DC and the branches
    conn.execute("CREATE OR REPLACE TEMP TABLE inv_base AS SELECT * FROM stg_fmcg_inventory")
    conn.execute("DELETE FROM stg_fmcg_inventory")
    conn.execute(f"INSERT INTO stg_fmcg_inventory (snapshot_date, sku, location_id, on_hand, in_transit) SELECT snapshot_date, sku, '{central}', on_hand * 0.5, in_transit FROM inv_base")
    for b in branches:
        conn.execute(f"INSERT INTO stg_fmcg_inventory (snapshot_date, sku, location_id, on_hand, in_transit) SELECT snapshot_date, sku, '{b}', on_hand * {0.5 / n}, 0 FROM inv_base")
    conn.execute(f"UPDATE stg_fmcg_purchase_orders SET destination_id = '{central}'")
    conn.execute(f"INSERT INTO stg_fmcg_locations (location_id, kind, holding_annual) VALUES ('{central}', 'central_dc', 0.10)")
    for b in branches:
        conn.execute(f"INSERT INTO stg_fmcg_locations (location_id, kind) VALUES ('{b}', 'branch')")
    conn.execute(f"INSERT INTO stg_fmcg_lanes (lane_id, origin_id, destination_id, lead_days, cost_per_unit, capacity_per_week) VALUES ('dc_{branches[0].lower()}', '{central}', '{branches[0]}', 3, 0.12, NULL)")
    conn.execute(f"INSERT INTO stg_fmcg_lanes (lane_id, origin_id, destination_id, lead_days, cost_per_unit, capacity_per_week) VALUES ('dc_{branches[1].lower()}', '{central}', '{branches[1]}', NULL, 0.18, NULL)")
    # transfer history for the second lane: thirty closed transfers, dispatch to receipt in 9-11 days,
    # so its lead is fitted from receipts rather than assumed
    sku = conn.execute("SELECT sku FROM stg_fmcg_orders ORDER BY sku LIMIT 1").fetchone()[0]
    for i in range(30):
        conn.execute("INSERT INTO stg_fmcg_transfers (transfer_id, lane_id, origin_id, destination_id, sku, qty, dispatch_date, expected_arrival_date, received_date) "
                     "VALUES (?, ?, ?, ?, ?, 40, DATE '2025-01-06' + INTERVAL (?) DAY, DATE '2025-01-06' + INTERVAL (?) DAY, DATE '2025-01-06' + INTERVAL (?) DAY)",
                     [f"tr_{i}", f"dc_{branches[1].lower()}", central, branches[1], sku, 7 * i, 7 * i + 10, 7 * i + 9 + (i % 3)])
    return loaded


def main() -> int:
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    first = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    max_solve = float(sys.argv[3]) if len(sys.argv) > 3 else 10.
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    loaded = make_network_vault(conn, seed=seed)
    skus = [r[0] for r in conn.execute("SELECT DISTINCT sku FROM stg_fmcg_orders ORDER BY sku LIMIT ?", [first]).fetchall()]
    started = time.time()
    req, build = build_network_request(conn, "smoke_network", skus=skus, max_solve_seconds=max_solve)
    t_build = time.time() - started
    print(json.dumps({"raw_rows": loaded["tables"], "compact": build["compact"], "network": build["network"], "warnings": build["warnings"][:6],
                      "lanes": [(a.id, a.origin, a.destination, a.lead_periods, a.cost_per_unit, round(a.capacity)) for a in req.transfers],
                      "services": [(s.id, s.location) for s in req.services], "build_seconds": round(t_build, 1)}, indent=1, default=str))
    started = time.time()
    report = plan_network(req)
    t_plan = time.time() - started
    print(json.dumps({"status": report["status"], "reasons": report["reasons"][:4], "selected": report["selected_policy"]}, indent=1))
    plan = to_network_plan(req, report, build, run_id="smoke")
    o = report["orchestration"]
    print(json.dumps({"status": report["status"], "selected": report["selected_policy"], "owner": o["planner_owner"], "state": o["state"],
                      "milps": o["milps_attempted"], "solver_seconds": round(o["solver_seconds_total"], 1), "plan_seconds": round(t_plan, 1),
                      "approval_required": plan["approval_required"], "executable_purchase_order": plan["executable_purchase_order"],
                      "mode_run": plan["mode_run"], "orders": len(plan["orders"]), "transfers": len(plan["transfers"]),
                      "verdict": report["network"]["explanations"]["verdict"], "router": report["network"]["router"]["reasons"][:3],
                      "conservation": report["network"]["selected"].get("conservation"), "reconciles": (report["network"]["selected"].get("economics") or {}).get("reconciles_on_every_world"),
                      "network_service": plan["network_service"]}, indent=1, default=str))
    json.dumps(plan, allow_nan=False)
    print("NETWORK WORKSPACE SMOKE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
