"""Stage 11-13 forensics on a lot-sizing fixture under the declared rolling benchmark.

usage: PYTHONPATH=. python3 -m scripts.p1_i_forensics I_max_pallets_ftl_cap 41001 [--reviews 52] [--frontier 17,19,42,43,50]

For every review of ZAAD's rolling replay (planning horizon 12, same stitched truth as the benchmark) the
script records the snapshot (on hand, inbound, fitted demand), every candidate the planner built (period-0
order, full schedule, hedged cost, burden, feasibility), the chosen candidate, the selector's reasons, and
what the EOQ baseline would have ordered from the identical snapshot. At the requested decisive reviews it
builds the lot-size frontier: for each candidate first-order quantity q on the pack / tier / load grid the
twelve-period plan cost with the first order capped at q (envelope, the optimizer's own preference) and
with the first order pinned at exactly q (the envelope's later schedule kept), each settled on the mean
world for the component breakdown, plus the objective-versus-settlement reconciliation of the chosen
candidate. Read-only: no product code path is changed."""
from __future__ import annotations

import argparse
import json
from dataclasses import replace

import zaad.full.planner as P
import zaad.full.replay as R
from scripts.p1_fixtures import build
from zaad.full.contracts import Request
from zaad.full.economics import cost_breakdown
from zaad.full.evaluation import long_truth
from zaad.full.model import Solution, pallet_units, solve, supplier_orders
from zaad.full.policies import baseline_plan
from zaad.full.replay import replay
from zaad.full.settlement import settle
from zaad.full.worlds import draw

PRODUCT = {k: Request.model_fields[k].default for k in ("stratified_scenarios", "timing_tiebreak", "analytic_shortage")}


def frontier_grid(req: Request) -> list[float]:
    src = req.sources[0]
    grid = {0., src.minimum}
    top = None
    for supplier, srcs, st in supplier_orders(req):
        upp = pallet_units(st, srcs)
        u = upp[src.id] if upp else None
        if u:
            top = st.max_pallets if st.max_pallets is not None else (st.freight_tiers[-1].up_to_pallets if st.freight_tiers else None)
            for k in range(1, int(top or 20) + 1):
                grid.add(k * u)
            for tier in st.freight_tiers:
                grid.add(tier.up_to_pallets * u)
    for m in (src.multiple, src.case_multiple, src.pallet_multiple):
        if m:
            for k in range(1, 40):
                grid.add(k * m)
    mu = 100.
    for k in range(1, 12):
        grid.add(k * mu)
    cap = 2000.
    for supplier, srcs, st in supplier_orders(req):
        upp = pallet_units(st, srcs)
        if upp and top:
            cap = min(cap, top * upp[src.id])
    return sorted(q for q in grid if q <= cap)


def frontier(req: Request, chosen: Solution | None) -> list[dict]:
    src = req.sources[0]
    world = draw(req, req.seed, 1, deterministic=True)
    rows = []
    for q in frontier_grid(req):
        capped = req.model_copy(update={"sources": [s.model_copy(update={"capacity_by_period": [q if t == 0 else c for t, c in enumerate(s.capacity_by_period)]}) if s.id == src.id else s for s in req.sources]})
        env = solve(capped, world)
        row = {"q": q}
        if env.usable_plan:
            x0 = env.purchases.get((src.id, 0), 0.)
            st = settle(req, env, world[0])
            comp = cost_breakdown(st["ledger"])
            row.update({"envelope_x0": x0, "envelope_cost": st["economic_cost"], "envelope_objective": env.projected_cost,
                        "envelope_components": {k: comp[k] for k in ("PURCHASE", "FREIGHT", "ORDERING", "CARRYING", "FINANCING", "SHORTAGE", "INVENTORY_VALUE_CHANGE")},
                        "envelope_schedule": {f"{k[0]}:{k[1]}": v for k, v in env.purchases.items() if v > 1e-9}})
            if abs(x0 - q) > 1e-6 and q > 0:
                pinned = Solution(env.status, {**{k: v for k, v in env.purchases.items() if k[1] != 0}, (src.id, 0): q}, env.transfers, env.amendments, {}, None, [], 0., 0, 0, None, None, [])
                try:
                    ev = solve(req, world, fixed=pinned)
                    if ev.usable_plan:
                        st2 = settle(req, ev, world[0])
                        comp2 = cost_breakdown(st2["ledger"])
                        row.update({"pinned_cost": st2["economic_cost"], "pinned_objective": ev.projected_cost,
                                    "pinned_components": {k: comp2[k] for k in ("PURCHASE", "FREIGHT", "ORDERING", "CARRYING", "FINANCING", "SHORTAGE", "INVENTORY_VALUE_CHANGE")}})
                    else:
                        row["pinned_status"] = ev.status
                except Exception as exc:
                    row["pinned_error"] = repr(exc)
        else:
            row["envelope_status"] = env.status
        rows.append(row)
    if chosen is not None and chosen.usable_plan:
        st = settle(req, chosen, world[0])
        rows.append({"q": "chosen", "x0": chosen.purchases.get((src.id, 0), 0.), "settled_cost_mean_world": st["economic_cost"], "objective": chosen.projected_cost,
                     "components": {k: cost_breakdown(st["ledger"])[k] for k in ("PURCHASE", "FREIGHT", "ORDERING", "CARRYING", "FINANCING", "SHORTAGE", "INVENTORY_VALUE_CHANGE")}})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fixture")
    ap.add_argument("seed", type=int)
    ap.add_argument("--reviews", type=int, default=52)
    ap.add_argument("--frontier", default="")
    a = ap.parse_args()
    initial = build(a.fixture, a.seed).model_copy(update=PRODUCT)
    truth = long_truth(initial, a.seed + 10000, 12 * (-(-(a.reviews - 1 + 12) // 12)))
    traces: list[dict] = []
    kept: list[Request] = []
    orig = P.plan

    def traced(r):
        P.TRACE = {}
        rep = orig(r)
        t = dict(P.TRACE)
        P.TRACE = None
        t["on_hand"] = sum(x.usable for x in r.stock)
        t["pipeline"] = [(p.id, p.expected_accepted_remaining, next(o.due_in for o in p.options if o.action == "keep")) for p in r.pipeline]
        t["forecast_mean"] = {row["sku"]: row["mean_demand_per_period"] for row in rep["protection"]}
        t["orchestration"] = {k: rep["orchestration"].get(k) for k in ("planner_owner", "ownership_reasons", "p1_classes_added", "candidate_classes_requested", "candidates_built", "reasons")}
        t["selected_policy"] = rep.get("selected_policy")
        t["status"] = rep.get("status")
        t["reasons"] = rep.get("reasons")
        t["blocking"] = rep.get("blocking")
        t["stress_confirmation"] = rep.get("stress_confirmation")
        t["candidate_gates"] = rep.get("candidate_gates")
        t["confirmation"] = rep.get("confirmation")
        t["economics_orders"] = [{"q": o["quantity"], "attribution": o["attribution"], "need": o.get("economic_need")} for o in rep["economics"]["orders"]]
        t["incumbent_orders"] = [(o.source, o.period, o.quantity) for o in r.incumbent_orders]
        eoq = baseline_plan(r, "economic_lot")
        t["eoq_from_same_snapshot"] = {f"{k[0]}:{k[1]}": v for k, v in eoq.purchases.items() if v > 1e-9}
        t["chosen_solution"] = None
        traces.append(t)
        kept.append(r)
        return rep

    P.plan = traced
    R.plan = traced
    res = replay(initial, truth, a.reviews, "gated", rolling=True)
    P.plan = orig
    R.plan = orig
    for t, row in zip(traces, res["reviews"]):
        st = row["settlement"]
        t["executed"] = [(p["source"], p["quantity"]) for p in row["purchases"]]
        t["settlement"] = {"demand": sum(x["demand"] for x in st["service_by_period"]), "served": sum(x["served"] for x in st["service_by_period"]),
                           "end_stock": sum(x["quantity"] for x in st["end_stock"]), "ledger": st["ledger"]}
    decisive = [int(x) for x in a.frontier.split(",") if x]
    fronts = {}
    for k in decisive:
        if k < len(kept):
            req_k = kept[k]
            chosen_name = traces[k].get("chosen")
            sched = traces[k]["candidates"].get(chosen_name, {}).get("purchases", {}) if chosen_name else {}
            chosen = Solution("OPTIMAL", {(s.split(":")[0], int(s.split(":")[1])): v for s, v in sched.items()}, {}, {}, {}, None, [], 0., 0, 0, None, None, []) if sched else None
            fronts[k] = frontier(req_k, chosen)
            print(f"review {k}: on hand {traces[k]['on_hand']:.0f} inbound {traces[k]['pipeline']} chosen {chosen_name} executed {traces[k]['executed']} eoq {traces[k]['eoq_from_same_snapshot']}")
            for r in fronts[k]:
                if r["q"] == "chosen":
                    print(f"   chosen x0 {r['x0']:.0f}: settled {r['settled_cost_mean_world']:.1f} objective {r['objective']} {r['components']}")
                elif "envelope_cost" in r:
                    print(f"   q<={r['q']:5.0f}: x0 {r['envelope_x0']:5.0f} cost {r['envelope_cost']:8.1f} obj {r['envelope_objective']} freight {r['envelope_components']['FREIGHT']:6.0f} order {r['envelope_components']['ORDERING']:5.0f} carry {r['envelope_components']['CARRYING']:5.1f} short {r['envelope_components']['SHORTAGE']:5.1f} invchg {r['envelope_components']['INVENTORY_VALUE_CHANGE']:7.1f}"
                          + (f" | pinned {r['pinned_cost']:8.1f} obj {r['pinned_objective']}" if "pinned_cost" in r else (f" | pinned {r.get('pinned_status', r.get('pinned_error', ''))}" if abs(r['envelope_x0'] - r['q']) > 1e-6 and r['q'] > 0 else "")))
                else:
                    print(f"   q<={r['q']}: {r.get('envelope_status')}")
    out = f"docs/zaad_full/evidence/p1/closure/forensics_{a.fixture}_{a.seed}.json"
    json.dump({"fixture": a.fixture, "seed": a.seed, "reviews": traces, "frontiers": fronts, "economic_cost": res.get("economic_cost"), "status": res["status"]}, open(out, "w"), indent=1, default=str)
    print("wrote", out, "status", res["status"], "cost", res.get("economic_cost"))
    print("executed orders:", [(t["executed"]) for t in traces if t["executed"]])


if __name__ == "__main__":
    main()
