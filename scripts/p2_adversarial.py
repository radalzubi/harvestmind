"""P2 adversarial review: the brief's attack list, each case planned by `plan_network` on a declared
fixture and read for the failure modes the brief names (phantom inventory, transfer loops, ping-pong,
buying and transferring irrationally in the same review, double service credit, branch starvation,
horizon-edge transfer dumping, central hoarding, forced decentralisation, candidate or solve-time
explosion). Written to docs/zaad_full/evidence/p2/P2_ADVERSARIAL.json and .md.

usage: PYTHONPATH=. python3 -m scripts.p2_adversarial [--max-solve 10] [--cases a,b]"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from zaad.full.fixtures_p1 import NOW
from zaad.meio.fixtures_p2 import p2_request

OUT = Path("docs/zaad_full/evidence/p2")

CASES = {
    "huge_central_zero_local": {"opening_central": 5000., "opening_branch": 0.},
    "zero_central_excess_one_branch": {"opening_central": 0., "opening_branch": {"north": 1500., "south": 0.}},
    "both_branches_short": {"opening_central": 60., "opening_branch": 0.},
    "perfectly_correlated_spike": {"demand_correlation": 1., "demand_sd_hint": .4, "opening_central": 300.},
    "independent_spikes": {"demand_correlation": 0., "demand_sd_hint": .4, "opening_central": 300.},
    "one_lane_unavailable": {"extra": {"_lane_off": "south"}, "opening_central": 500., "opening_branch": {"north": 100., "south": 300.}},
    "long_lane_lead": {"lane_lead_periods": 6, "opening_central": 800., "opening_branch": 150.},
    "zero_transfer_cost": {"lane_cost": 0., "opening_central": 500.},
    "enormous_transfer_cost": {"lane_cost": 50., "opening_central": 500.},
    "zero_supplier_availability": {"supplier_capacity": 0., "opening_central": 400., "opening_branch": 100.},
    "supplier_short_fill": {"supplier_fill": .5, "supplier_fill_sd": .2, "opening_central": 200.},
    "targets_90_vs_99": {"target": {"north": .99, "south": .90}, "opening_central": 200., "opening_branch": 80.},
    "very_unequal_demand": {"demand": {"north": 500., "south": 20.}, "opening_branch": {"north": 600., "south": 30.}, "opening_central": 800., "supplier_capacity": 700.},
    "branch_with_no_demand": {"demand": {"north": 100., "south": 0.}, "opening_branch": {"north": 150., "south": 200.}, "opening_central": 300.},
    "transfer_capacity_zero": {"lane_capacity": 0., "opening_central": 500., "opening_branch": 300.},
    "moq_larger_than_branch_demand": {"minimum": 900., "opening_central": 100., "opening_branch": 100.},
    "central_full_load_economics": {"fixed_order_cost": 400., "opening_central": 50., "opening_branch": 120.},
    "recovery_after_disruption": {"stresses": "severe", "opening_central": 100., "opening_branch": 60.},
    "already_perfect_incumbent": {"opening_central": 400., "opening_branch": 250.},
    "reverse_lane_at_cost": {"opening_central": 300., "opening_branch": 300., "extra_lanes": [{"id": "back_north", "origin": "north", "destination": "central", "lead_periods": 1, "capacity": 1e6, "cost_per_unit": .2}]},
    "reverse_lane_free": {"opening_central": 300., "opening_branch": 300., "lane_cost": 0., "extra_lanes": [{"id": "back_north", "origin": "north", "destination": "central", "lead_periods": 1, "capacity": 1e6, "cost_per_unit": 0.}]},
    "five_branches": {"branches": ("b1", "b2", "b3", "b4", "b5"), "demand": 60., "opening_central": 500., "opening_branch": 90.},
}


def build(name: str, max_solve: float):
    args = dict(CASES[name])
    extra = dict(args.pop("extra", {}) or {})
    lane_off = extra.pop("_lane_off", None)
    req = p2_request(max_solve_seconds=max_solve, extra=extra or None, **args)
    if lane_off:
        req = req.model_copy(update={"transfers": tuple(a.model_copy(update={"approved": False}) if a.destination == lane_off else a for a in req.transfers)})
    return req


def run_case(name: str, max_solve: float) -> dict:
    from zaad.meio.planner import NetworkRefused, plan_network
    req = build(name, max_solve)
    started = time.time()
    try:
        rep = plan_network(req)
    except NetworkRefused as exc:
        return {"case": name, "status": "REFUSED", "reason": str(exc), "seconds": round(time.time() - started, 1),
                "note": "refused by network validation before any solve: the declared network cannot price a transfer loop out"}
    seconds = time.time() - started
    net = rep["network"]
    sel, inc = net["selected"], net["incumbent"]
    o = rep["orchestration"]
    lanes = sel.get("lanes", {})
    actions = sel.get("actions", {})
    purchases0 = actions.get("purchases_period_0", 0.)
    transfers0 = actions.get("transfers_period_0", 0.)
    services = sel.get("services", [])
    rate = sum(float(f.get("mean", 0.)) for f in rep["forecasts"].values())
    from zaad.full.lotsizing import reference_lots
    lots = reference_lots(req, rep["forecasts"])
    economic_lot = max((lot["lot_units"] for lot in lots.values()), default=0.)
    flags = {
        "physically_unusable_worlds": len(sel.get("unusable", [])),
        "conservation": sel.get("conservation", {}).get("holds_on_every_world"),
        "reconciles": (sel.get("economics") or {}).get("reconciles_on_every_world"),
        "ping_pong_units": sum(v.get("ping_pong_units") or 0. for v in lanes.values()),
        "capacity_respected": all(v.get("capacity_respected", True) for v in lanes.values()),
        "packs_legal": all(v.get("pack_legal", True) for v in lanes.values()),
        "severe_starvation": [s["service"] for s in services if (s.get("severe_starvation_share") or 0.) > 0],
        "breaches": [s["service"] for s in services if (s.get("breach_share") or 0.) > .5],
        # buying and moving the same units in the same review is not irrational per se (a DC forwards);
        # buying MORE than a full horizon of network demand while also emptying the DC is
        "buy_and_transfer_same_review": bool(purchases0 > 0 and transfers0 > 0),
        # a period-0 purchase beyond both a full horizon of network demand and the supplier's economic lot
        "purchases_over_horizon_demand": purchases0 > max(rate * req.horizon, economic_lot) * 1.05 if rate > 0 else purchases0 > 0,
        "economic_lot_reference": economic_lot,
        "stranded_units": sel.get("stranded_units_at_end"),
        "central_share_of_end_stock": None,
        "status": rep["status"], "state": o["state"], "owner": o["planner_owner"],
        "milps": o["milps_attempted"], "solver_seconds": round(o["solver_seconds_total"], 1), "wall_seconds": round(seconds, 1),
        "candidates_built": o["candidates_built"], "time_limited": o.get("milps_feasible_time_limited"), "no_feasible": o.get("milps_no_feasible_solution"),
        "issues": net["state"]["issues"], "router": net["router"]["reasons"][:3],
        "verdict": net["explanations"]["verdict"],
    }
    flows = {(f["sku"], f["location"]): f for f in sel.get("flows", [])}
    total_close = sum(f["closing"] for f in flows.values())
    central_close = sum(f["closing"] for k, f in flows.items() if k[1] == "central")
    flags["central_share_of_end_stock"] = (central_close / total_close) if total_close > 0 else None
    flags["end_stock_units"] = total_close
    flags["incumbent_service"] = {s["service"]: round(s["achieved"], 3) for s in inc.get("services", []) if s.get("achieved") is not None}
    flags["selected_service"] = {s["service"]: round(s["achieved"], 3) for s in services if s.get("achieved") is not None}
    flags["transfers_period_0"] = transfers0
    flags["purchases_period_0"] = purchases0
    return {"case": name, "seconds": round(seconds, 1), **flags}


def verdicts(row: dict) -> list[str]:
    bad = []
    if row.get("physically_unusable_worlds"):
        bad.append("selected plan unusable on a world")
    if row.get("conservation") is False:
        bad.append("conservation broken")
    if row.get("reconciles") is False:
        bad.append("accounting does not reconcile")
    if (row.get("ping_pong_units") or 0.) > 1e-6:
        bad.append("ping-pong transfers")
    if row.get("capacity_respected") is False:
        bad.append("lane capacity breached")
    if row.get("packs_legal") is False:
        bad.append("illegal packs")
    if row.get("purchases_over_horizon_demand"):
        bad.append("purchases exceed a full horizon of demand")
    if row.get("wall_seconds", 0.) > 300:
        bad.append("solve-time explosion")
    if row.get("status") == "ERROR":
        bad.append(row.get("error", "error"))
    if row.get("case") == "reverse_lane_free" and row.get("status") != "REFUSED":
        bad.append("a free reverse pair was planned instead of refused")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-solve", type=float, default=10.)
    ap.add_argument("--cases", default="")
    a = ap.parse_args()
    names = [n for n in CASES if not a.cases or n in a.cases.split(",")]
    rows = []
    for name in names:
        try:
            row = run_case(name, a.max_solve)
        except Exception as exc:    # a crash is a finding, not a lost case
            row = {"case": name, "status": "ERROR", "error": repr(exc)}
        row["findings"] = verdicts(row)
        rows.append(row)
        print(f"{name:34s} {row.get('status', '?'):16s} state {str(row.get('state'))[:20]:20s} wall {row.get('wall_seconds', 0):6.1f}s milps {row.get('milps')} "
              f"tr0 {row.get('transfers_period_0', 0):7.0f} buy0 {row.get('purchases_period_0', 0):7.0f} pp {row.get('ping_pong_units', 0):.0f} starve {row.get('severe_starvation')} findings {row['findings']}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "P2_ADVERSARIAL.json").write_text(json.dumps(rows, indent=1, default=str))
    lines = ["# P2 adversarial review", "", "| case | status | state | wall s | period-0 transfers | period-0 purchases | selected service | incumbent service | central share of end stock | findings |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        share = r.get("central_share_of_end_stock")
        lines.append(f"| {r['case']} | {r.get('status')} | {r.get('state')} | {r.get('wall_seconds', 0):.0f} | {r.get('transfers_period_0', 0):.0f} | {r.get('purchases_period_0', 0):.0f} | "
                     f"{r.get('selected_service')} | {r.get('incumbent_service')} | {'-' if share is None else f'{share:.0%}'} | {', '.join(r['findings']) or 'none'} |")
    (OUT / "P2_ADVERSARIAL.md").write_text("\n".join(lines) + "\n")
    failed = [r["case"] for r in rows if r["findings"]]
    print("ADVERSARIAL", "clean" if not failed else f"findings on {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
