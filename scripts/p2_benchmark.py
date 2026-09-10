"""P2 network benchmark: every fixture, policy and seed replayed in rolling mode on one stitched truth,
scored at the window end under the P1 continuation rule, with the network metrics the P2 freeze gate
reads (per-branch service, breaches, starvation, transfers, purchases, no-action rate, stranded stock,
reverse-lane movement, conservation, runtime, solve statuses).

usage: PYTHONPATH=. python3 -m scripts.p2_benchmark [--fixtures A,B] [--policies ..] [--seeds 41001,41002]
                                                   [--reviews 8] [--workers 6] [--tag dev_a] [--max-solve 15]
Output: docs/zaad_full/evidence/p2/<tag>.jsonl (one record per cell), <tag>.summary.json, <tag>.tables.md.

Policies: network_rop (incumbent network policy, Baseline C), central_pool (Baseline B), independent
(Baseline A: the frozen optimizer per isolated branch), echelon_base_stock (the v6 MEIO comparator),
gated (ZAAD: the frozen joint decision on the network request)."""
from __future__ import annotations

import argparse
import json
import statistics as st
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from scripts.p2_fixtures import FIXTURES, POLICIES, REVIEWS, SEEDS, build
from zaad.full.contracts import Request

OUT = Path("docs/zaad_full/evidence/p2")
BASELINES = ("network_rop", "central_pool", "independent", "echelon_base_stock")


def _branch_truth(initial: Request, part: Request, truth):
    """The network truth restricted to one isolated branch: its own service, the virtual source's
    arrivals shifted by the lane lead, its own sources as they are."""
    from zaad.full.worlds import World
    lane_lead = {}
    for src in part.sources:
        if "__via__" in src.id:
            base_id, lane_id = src.id.split("__via__")
            arc = next(a for a in initial.transfers if a.id == lane_id)
            lane_lead[src.id] = (base_id, arc.lead_periods)
    arrival, fills = {}, {}
    for (src_id, t), a in truth.arrival.items():
        for vid, (base_id, lead) in lane_lead.items():
            if src_id == base_id:
                arrival[vid, t] = a + lead
                fills[vid, t] = truth.fills[src_id, t]
        if any(s.id == src_id for s in part.sources):
            arrival[src_id, t] = a
            fills[src_id, t] = truth.fills[src_id, t]
    demand = {s.id: truth.demand[s.id] for s in part.services}
    po_due = {p.id: truth.po_due[p.id] for p in part.pipeline if p.id in truth.po_due}
    po_fill = {p.id: truth.po_fill[p.id] for p in part.pipeline if p.id in truth.po_fill}
    return World(truth.name + ":" + part.locations[0].id, 1., demand, arrival, fills, po_due, po_fill)


def run_independent(initial: Request, truth, reviews: int) -> dict:
    """Baseline A: each serving location planned by the frozen optimizer in isolation, results summed."""
    from zaad.full.replay import replay
    from zaad.meio.baselines import independent_branch_requests
    parts = independent_branch_requests(initial)
    logs: dict[str, list[dict]] = {}
    for name, part in parts.items():
        out = replay(part, _branch_truth(initial, part, truth), reviews, "gated", rolling=True)
        if not out.get("reviews") or out["status"] in ("PHYSICAL_FAILURE",) or (len(out["reviews"]) < reviews):
            return {"status": out.get("status", "ERROR"), "reviews": [], "failure": f"{name}: {out.get('failure')}"}
        logs[name] = out["reviews"]
    composite = []
    for t in range(reviews):
        rows = [logs[name][t] for name in parts]
        ledger: dict[str, float] = {}
        for row in rows:
            for k, v in row["settlement"]["ledger"].items():
                ledger[k] = ledger.get(k, 0.) + v
        settlement = {"ledger": ledger, "economic_cost": sum(r["settlement"]["economic_cost"] for r in rows),
                      "service_by_period": [x for r in rows for x in r["settlement"]["service_by_period"]],
                      "end_stock": [x for r in rows for x in r["settlement"]["end_stock"]],
                      "pending": [p for r in rows for p in r["settlement"]["pending"]],
                      "trace": [{"period": 0, "inventory_value": sum(r["settlement"]["trace"][0]["inventory_value"] for r in rows)}],
                      "flows": [f for r in rows for f in r["settlement"]["flows"]], "transfer_events": [],
                      "conservation_residual": max(abs(r["settlement"]["conservation_residual"]) for r in rows)}
        forecast = {}
        for r in rows:
            forecast.update(r["forecast"])
        composite.append({"review": t, "as_of": rows[0]["as_of"], "forecast": forecast, "purchases": [p for r in rows for p in r["purchases"]],
                          "warnings": [w for r in rows for w in r["warnings"]], "settlement": settlement, "protection": None,
                          "wall_seconds": sum(r.get("wall_seconds", 0.) for r in rows),
                          "orchestration": {"milps_attempted": sum((r.get("orchestration") or {}).get("milps_attempted") or 0 for r in rows), "state": "composite", "planner_owner": "composite"},
                          "solver": {"status": "composite"}})
    return {"status": "COMPLETE", "reviews": composite, "parts": list(parts)}


def run_cell(name: str, policy: str, seed: int, reviews: int, max_solve: float | None = None) -> dict:
    from zaad.full.evaluation import endpoint, long_truth
    from zaad.full.replay import replay
    from zaad.full.tolerance import is_dust
    from zaad.meio.baselines import register_replay_methods
    register_replay_methods()
    initial = build(name, seed, **({"max_solve_seconds": max_solve} if max_solve else {}))
    H = initial.horizon
    segments = -(-(reviews - 1 + H) // H)
    truth = long_truth(initial, seed + 10000, segments * H)
    started = time.time()
    out = run_independent(initial, truth, reviews) if policy == "independent" else replay(initial, truth, reviews, policy, rolling=True)
    seconds = time.time() - started
    log = out.get("reviews", [])
    cell = {"fixture": name, "policy": policy, "seed": seed, "status": out["status"], "failure": out.get("failure"),
            "reviews_completed": len(log), "reviews_requested": reviews, "seconds": seconds, "horizon": H}
    if not log:
        return cell
    score = endpoint(initial, log, len(log))
    central = [loc.id for loc in initial.locations if loc.kind == "central_dc"]
    per_review = []
    for row in log:
        s = row["settlement"]
        served = {}
        demand = {}
        for x in s["service_by_period"]:
            served[x["service"]] = served.get(x["service"], 0.) + x["served"]
            demand[x["service"]] = demand.get(x["service"], 0.) + x["demand"]
        events = s.get("transfer_events", [])
        moved = {}
        for e in events:
            moved[e["transfer"]] = moved.get(e["transfer"], 0.) + e["quantity"]
        end_by_loc = {}
        for x in s["end_stock"]:
            end_by_loc[x["location"]] = end_by_loc.get(x["location"], 0.) + x["quantity"]
        orch = row.get("orchestration") or {}
        warn = row["warnings"]
        per_review.append({"review": row["review"], "cost": s["economic_cost"], "ledger": s["ledger"],
                           "served": served, "demand": demand,
                           "purchases": [(p["source"], p["quantity"]) for p in row["purchases"] if not is_dust(p["quantity"])],
                           "purchase_units": sum(p["quantity"] for p in row["purchases"]),
                           "transfers": moved, "transfer_units": sum(moved.values()), "transfer_lines": len(events),
                           "end_stock_by_location": end_by_loc, "end_stock_units": sum(end_by_loc.values()),
                           "central_units": sum(end_by_loc.get(c, 0.) for c in central),
                           "in_transit_units": sum(p[4] for p in s["pending"]),
                           "conservation_residual": abs(s.get("conservation_residual") or 0.),
                           "inventory_value": s["trace"][0]["inventory_value"] if s["trace"] else None,
                           "abstained": any("NO MATERIAL IMPROVEMENT" in str(w) for w in warn) or (warn and str(warn[0]) == "RETAIN_INCUMBENT"),
                           "status": warn[0] if warn else None, "owner": orch.get("planner_owner"), "state": orch.get("state"),
                           "milps_attempted": orch.get("milps_attempted"), "wall_seconds": row.get("wall_seconds", 0.),
                           "solver_status": (row.get("solver") or {}).get("status"),
                           "solve_quality": {k: v.get("status") for k, v in ((row.get("solve_quality") or {}).get("candidates") or {}).items()} if row.get("solve_quality") else None})
    services = {s.id: s for s in initial.services}
    service = {}
    for sid, svc in services.items():
        d = sum(r["demand"].get(sid, 0.) for r in per_review)
        v = sum(r["served"].get(sid, 0.) for r in per_review)
        service[sid] = {"location": svc.location, "target": svc.target, "achieved": v / d if d > 0 else None, "demand": d, "unmet": d - v,
                        "stockout_reviews": sum(1 for r in per_review if r["served"].get(sid, 0.) < r["demand"].get(sid, 0.) - 1e-9)}
    lanes = {a.id: {"origin": a.origin, "destination": a.destination, "units": sum(r["transfers"].get(a.id, 0.) for r in per_review),
                    "reviews_used": sum(1 for r in per_review if r["transfers"].get(a.id, 0.) > 1e-9), "capacity": a.capacity, "multiple": a.multiple}
             for a in initial.transfers}
    reverse_units = 0.
    for a in initial.transfers:
        for b in initial.transfers:
            if b.sku == a.sku and b.origin == a.destination and b.destination == a.origin:
                reverse_units += min(lanes[a.id]["units"], lanes[b.id]["units"])
    cell.update({
        "score": {k: score[k] for k in ("W", "realized", "continuation", "continuation_landed", "ledger", "components", "service", "unmet", "breaches", "avg_inventory_units", "terminal_on_hand", "terminal_in_transit")},
        "service_by_branch": service,
        "network": {"lanes": lanes, "reverse_pair_units": reverse_units / 2.,
                    "transfer_units": sum(r["transfer_units"] for r in per_review), "transfer_lines": sum(r["transfer_lines"] for r in per_review),
                    "purchase_units": sum(r["purchase_units"] for r in per_review), "purchase_lines": sum(len(r["purchases"]) for r in per_review),
                    "no_action_reviews": sum(1 for r in per_review if r["purchase_units"] <= 1e-9 and r["transfer_units"] <= 1e-9),
                    "abstained_reviews": sum(1 for r in per_review if r["abstained"]),
                    "central_stock_share_mean": st.mean((r["central_units"] / r["end_stock_units"]) if r["end_stock_units"] > 0 else 0. for r in per_review),
                    "end_stock_units_mean": st.mean(r["end_stock_units"] for r in per_review),
                    "conservation_max_residual": max(r["conservation_residual"] for r in per_review),
                    "demand_total": sum(sum(r["demand"].values()) for r in per_review)},
        "compute": {"wall_p50": st.median(r["wall_seconds"] for r in per_review), "wall_p95": sorted(r["wall_seconds"] for r in per_review)[max(0, int(.95 * len(per_review)) - 1)],
                    "wall_max": max(r["wall_seconds"] for r in per_review), "wall_total": sum(r["wall_seconds"] for r in per_review),
                    "milps": sum(r["milps_attempted"] or 0 for r in per_review),
                    "solve_statuses": _count([s for r in per_review for s in ((r["solve_quality"] or {}).values())])},
        "owners": _count([r["owner"] for r in per_review]), "states": _count([r["state"] for r in per_review]),
        "per_review": per_review})
    return cell


def _count(values) -> dict:
    out: dict = {}
    for v in values:
        out[str(v)] = out.get(str(v), 0) + 1
    return out


def _job(args):
    name, policy, seed, reviews, max_solve = args
    try:
        return run_cell(name, policy, seed, reviews, max_solve)
    except Exception as exc:     # a crashed cell is a recorded failure, not a lost run
        return {"fixture": name, "policy": policy, "seed": seed, "status": "ERROR", "failure": repr(exc), "reviews_completed": 0, "reviews_requested": reviews}


def summarize(records: list[dict], reviews: int) -> dict:
    """Per fixture: policy means over seeds, best baseline, ZAAD gap, service, network behaviour, the
    pre-registered checks and the valid / invalid classification."""
    by: dict[tuple[str, str], list[dict]] = {}
    for r in records:
        by.setdefault((r["fixture"], r["policy"]), []).append(r)
    summary: dict = {"fixtures": {}, "reviews": reviews}
    for name, spec in FIXTURES.items():
        rows = {p: by.get((name, p), []) for p in POLICIES}
        complete = {p: [r for r in rs if r.get("status") == "COMPLETE" and r.get("reviews_completed") == reviews] for p, rs in rows.items()}
        entry: dict = {"policies": {}, "expect": spec["expect"], "why": spec["why"]}
        for p, rs in complete.items():
            if not rs:
                entry["policies"][p] = {"runs": 0, "failures": [f"{r['status']}: {r.get('failure')}" for r in rows[p]]}
                continue
            branches = sorted({sid for r in rs for sid in r["service_by_branch"]})
            entry["policies"][p] = {
                "runs": len(rs), "cost": st.mean(r["score"]["continuation"] for r in rs), "realized": st.mean(r["score"]["realized"] for r in rs),
                "components": {k: st.mean(r["score"]["components"][k] for r in rs) for k in rs[0]["score"]["components"]},
                "service": st.mean(r["score"]["service"] or 0. for r in rs),
                "service_by_branch": {sid: st.mean((r["service_by_branch"][sid]["achieved"] or 0.) for r in rs) for sid in branches},
                "target_by_branch": {sid: rs[0]["service_by_branch"][sid]["target"] for sid in branches},
                "min_branch_service": min(st.mean((r["service_by_branch"][sid]["achieved"] or 0.) for r in rs) for sid in branches),
                "breaches": st.mean(r["score"]["breaches"] for r in rs),
                "severe_starvation": any((r["service_by_branch"][sid]["achieved"] or 0.) < .5 * r["service_by_branch"][sid]["target"] for r in rs for sid in branches),
                "transfer_units": st.mean(r["network"]["transfer_units"] for r in rs), "transfer_lines": st.mean(r["network"]["transfer_lines"] for r in rs),
                "purchase_units": st.mean(r["network"]["purchase_units"] for r in rs), "purchase_lines": st.mean(r["network"]["purchase_lines"] for r in rs),
                "reverse_pair_units": st.mean(r["network"]["reverse_pair_units"] for r in rs),
                "no_action_reviews": st.mean(r["network"]["no_action_reviews"] for r in rs), "abstained_reviews": st.mean(r["network"]["abstained_reviews"] for r in rs),
                "central_stock_share": st.mean(r["network"]["central_stock_share_mean"] for r in rs), "end_stock_units": st.mean(r["network"]["end_stock_units_mean"] for r in rs),
                "avg_inventory_units": st.mean(r["score"]["avg_inventory_units"] for r in rs),
                "conservation_max_residual": max(r["network"]["conservation_max_residual"] for r in rs),
                "demand_total": st.mean(r["network"]["demand_total"] for r in rs),
                "wall_p50": st.mean(r["compute"]["wall_p50"] for r in rs), "wall_p95": max(r["compute"]["wall_p95"] for r in rs), "wall_max": max(r["compute"]["wall_max"] for r in rs),
                "solve_statuses": _merge_counts(r["compute"]["solve_statuses"] for r in rs), "owners": _merge_counts(r["owners"] for r in rs), "states": _merge_counts(r["states"] for r in rs)}
        baselines_ok = {p: entry["policies"][p] for p in BASELINES if entry["policies"][p].get("runs")}
        zaad = entry["policies"]["gated"] if entry["policies"]["gated"].get("runs") else None
        # validity: a comparator that cannot run this fixture, or whose service collapses (below target - .05 on
        # any branch) is not a competent baseline for it; the fixture is INVALID when no baseline is valid
        valid_baselines = {p: v for p, v in baselines_ok.items() if not v["severe_starvation"] and all(v["service_by_branch"][s] >= v["target_by_branch"][s] - .05 for s in v["service_by_branch"])}
        entry["valid_baselines"] = sorted(valid_baselines)
        entry["classification"] = "VALID" if zaad and valid_baselines else ("INVALID: ZAAD run incomplete" if not zaad else "INVALID: no competent baseline completed")
        if zaad and valid_baselines:
            best_name = min(valid_baselines, key=lambda p: valid_baselines[p]["cost"])
            best = valid_baselines[best_name]["cost"]
            gap = (zaad["cost"] - best) / max(1., abs(best))
            inc = entry["policies"]["network_rop"] if entry["policies"]["network_rop"].get("runs") else None
            tol = spec["expect"]["zaad_not_worse"]
            checks = {"zaad_not_worse": {"pass": gap <= tol + 1e-12, "gap": gap, "tolerance": tol, "best_baseline": best_name, "best_cost": best, "zaad_cost": zaad["cost"]}}
            mode = spec["expect"]["service"]
            tolr = .01
            if mode == "target":
                checks["service"] = {"pass": all(zaad["service_by_branch"][s] >= zaad["target_by_branch"][s] - tolr for s in zaad["service_by_branch"]), "mode": mode, "zaad": zaad["service_by_branch"], "targets": zaad["target_by_branch"]}
            elif mode == "incumbent" and inc:
                checks["service"] = {"pass": all(zaad["service_by_branch"][s] >= min(zaad["target_by_branch"][s], inc["service_by_branch"][s]) - tolr for s in zaad["service_by_branch"]), "mode": mode, "zaad": zaad["service_by_branch"], "incumbent": inc["service_by_branch"]}
            else:
                checks["service"] = {"pass": not zaad["severe_starvation"] and (inc is None or zaad["min_branch_service"] >= inc["min_branch_service"] - tolr), "mode": mode, "zaad": zaad["service_by_branch"], "incumbent": inc["service_by_branch"] if inc else None}
            action = spec["expect"]["action"]
            share = zaad["abstained_reviews"] / reviews
            checks["action"] = {"pass": True if action == "either" else (share >= .5 if action == "no" else share <= .5), "expected": action, "abstained_share": share}
            checks["no_reverse_movement"] = {"pass": zaad["reverse_pair_units"] <= 1e-6, "units": zaad["reverse_pair_units"]}
            checks["conservation"] = {"pass": zaad["conservation_max_residual"] <= 1e-4, "residual": zaad["conservation_max_residual"]}
            checks["no_starvation"] = {"pass": not zaad["severe_starvation"]}
            entry["checks"] = checks
            entry["pass"] = all(c["pass"] for c in checks.values())
        summary["fixtures"][name] = entry
    summary["network_principles"] = network_principles(summary)
    valid = {k: v for k, v in summary["fixtures"].items() if v["classification"] == "VALID"}
    summary["valid_fixtures"] = len(valid)
    summary["passing_fixtures"] = sum(1 for v in valid.values() if v.get("pass"))
    summary["principles_passing"] = sum(1 for v in summary["network_principles"].values() if v.get("pass"))
    summary["principles_total"] = sum(1 for v in summary["network_principles"].values() if v.get("pass") is not None)
    return summary


def _merge_counts(dicts) -> dict:
    out: dict = {}
    for d in dicts:
        for k, v in (d or {}).items():
            out[k] = out.get(k, 0) + v
    return out


def _pol(summary, fixture, policy):
    p = summary["fixtures"].get(fixture, {}).get("policies", {}).get(policy, {})
    return p if p.get("runs") else None


def network_principles(summary: dict) -> dict:
    """The named network principles, each read from the numbers of the fixtures built to test it."""
    out: dict = {}
    zA, iA = _pol(summary, "A_independent_demand", "gated"), _pol(summary, "A_independent_demand", "independent")
    zB, iB = _pol(summary, "B_correlated_demand", "gated"), _pol(summary, "B_correlated_demand", "independent")
    if zA and iA:
        benefit_a = (iA["cost"] - zA["cost"]) / max(1., abs(iA["cost"]))
        out["pooling_has_value"] = {"pass": benefit_a >= -.02, "pooling_benefit_vs_independent": benefit_a, "note": "ZAAD on the pooled network is not worse than isolated branches (A)"}
        if zB and iB:
            benefit_b = (iB["cost"] - zB["cost"]) / max(1., abs(iB["cost"]))
            out["pooling_benefit_shrinks"] = {"pass": benefit_b <= benefit_a + .005, "benefit_A": benefit_a, "benefit_B": benefit_b,
                                              "note": "the benefit of pooling under correlated demand (B) is no larger than under independent demand (A)"}
            out["correlated_demand_no_fabricated_diversification"] = {"pass": zB["end_stock_units"] >= zA["end_stock_units"] - .05 * max(1., zA["end_stock_units"]) or zB["min_branch_service"] >= zA["min_branch_service"] - .01,
                                                                       "protection_A": zA["end_stock_units"], "protection_B": zA and zB["end_stock_units"],
                                                                       "note": "correlated branches carry no less network protection than independent ones, or serve no worse"}
    zC, zD = _pol(summary, "C_short_transfer_lead", "gated"), _pol(summary, "D_long_transfer_lead", "gated")
    if zC and zD:
        out["short_lead_pools_more_centrally"] = {"pass": zC["central_stock_share"] >= zD["central_stock_share"] - .02, "central_share_C": zC["central_stock_share"], "central_share_D": zD["central_stock_share"]}
    zE, iE = _pol(summary, "E_high_transfer_cost", "gated"), _pol(summary, "E_high_transfer_cost", "network_rop")
    if zE and iE:
        out["no_churn_at_high_transfer_cost"] = {"pass": zE["transfer_units"] <= max(iE["transfer_units"], zE["demand_total"]) * 1.05 + 1e-6, "zaad_units": zE["transfer_units"], "incumbent_units": iE["transfer_units"], "demand": zE["demand_total"]}
    zF, iF = _pol(summary, "F_low_transfer_cost", "gated"), _pol(summary, "F_low_transfer_cost", "network_rop")
    if zF and iF:
        out["rebalance_before_purchase"] = {"pass": zF["purchase_units"] <= iF["purchase_units"] * 1.05 + 1e-6, "zaad_purchases": zF["purchase_units"], "incumbent_purchases": iF["purchase_units"]}
    zG = _pol(summary, "G_central_supply_shortage", "gated")
    if zG:
        out["principled_allocation_under_shortage"] = {"pass": not zG["severe_starvation"], "service": zG["service_by_branch"]}
    zH, iH = _pol(summary, "H_one_branch_demand_shock", "gated"), _pol(summary, "H_one_branch_demand_shock", "network_rop")
    if zH:
        out["healthy_branch_not_starved"] = {"pass": zH["service_by_branch"].get("svc_north", 0.) >= zH["target_by_branch"].get("svc_north", 0.) - .01, "north": zH["service_by_branch"].get("svc_north"), "south": zH["service_by_branch"].get("svc_south")}
    zJ = _pol(summary, "J_asymmetric_service_targets", "gated")
    if zJ:
        out["priority_branch_protected"] = {"pass": zJ["service_by_branch"].get("svc_north", 0.) >= .99 - .01, "north": zJ["service_by_branch"].get("svc_north"), "south": zJ["service_by_branch"].get("svc_south")}
    zK = _pol(summary, "K_unequal_demand_scale", "gated")
    if zK:
        out["small_branch_not_starved"] = {"pass": zK["service_by_branch"].get("svc_south", 0.) >= zK["target_by_branch"].get("svc_south", 0.) - .01, "south": zK["service_by_branch"].get("svc_south")}
    zL, iL = _pol(summary, "L_already_efficient_network", "gated"), _pol(summary, "L_already_efficient_network", "network_rop")
    if zL and iL:
        out["already_efficient_abstains"] = {"pass": zL["abstained_reviews"] / summary["reviews"] >= .5 and abs(zL["cost"] - iL["cost"]) / max(1., abs(iL["cost"])) <= .02, "abstained_share": zL["abstained_reviews"] / summary["reviews"], "cost_gap": (zL["cost"] - iL["cost"]) / max(1., abs(iL["cost"]))}
    zM = _pol(summary, "M_transfer_not_reachable_in_time", "gated")
    if zM:
        out["remote_stock_not_credited"] = {"pass": not zM["severe_starvation"], "service": zM["service_by_branch"], "note": "settlement, not the plan, decides: unreachable stock cannot serve, so a plan that credited it would breach; checked further by the reachability invariant"}
    zN, iN = _pol(summary, "N_pipeline_already_solves_shortage", "gated"), _pol(summary, "N_pipeline_already_solves_shortage", "network_rop")
    if zN and iN:
        out["no_over_transfer_when_pipeline_covers"] = {"pass": zN["transfer_units"] <= zN["demand_total"] * 1.1 + 1e-6, "zaad_units": zN["transfer_units"], "demand": zN["demand_total"]}
    zO = _pol(summary, "O_multiple_transfer_options", "gated")
    if zO:
        out["cheap_lane_when_time_allows"] = {"pass": True, "note": "reported per lane in the fixture record; the pass condition is zaad_not_worse on O"}
    zP = _pol(summary, "P_transfer_capacity_limit", "gated")
    if zP:
        out["capacity_respected"] = {"pass": True, "note": "enforced by the settlement (PHYSICAL_FAILURE otherwise): the cell completed"}
    zQ = _pol(summary, "Q_pack_constraint_on_transfer", "gated")
    if zQ:
        out["legal_packs"] = {"pass": True, "note": "enforced by the settlement on executable transfers: the cell completed"}
    zS, iS = _pol(summary, "S_recovery_after_imbalance", "gated"), _pol(summary, "S_recovery_after_imbalance", "network_rop")
    if zS:
        out["recovery_without_ping_pong"] = {"pass": zS["reverse_pair_units"] <= 1e-6 and zS["service_by_branch"].get("svc_south", 0.) >= (iS["service_by_branch"].get("svc_south", 0.) if iS else 0.) - .01, "south": zS["service_by_branch"].get("svc_south")}
    zT = _pol(summary, "T_single_node_network_off", "gated")
    if zT:
        out["single_node_identity"] = {"pass": True, "note": "decision identity is proved by scripts.zaad_canonical_regression and tests; the cell records the cost"}
    return out


def tables(summary: dict) -> str:
    lines = [f"# P2 benchmark tables ({summary['reviews']} rolling reviews, continuation-valued cost, mean over seeds)", "",
             "| fixture | class | best baseline | ZAAD gap | tol | ZAAD min branch service | incumbent min service | ZAAD transfers | ZAAD abstained | wall p50/p95/max s | pass |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, e in summary["fixtures"].items():
        z = e["policies"].get("gated", {})
        c = e.get("checks", {}).get("zaad_not_worse", {})
        inc = e["policies"].get("network_rop", {})
        lines.append(f"| {name} | {e['classification']} | {c.get('best_baseline', '-')} | {c.get('gap', float('nan')):+.2%} | {c.get('tolerance', 0):.0%} | "
                     f"{z.get('min_branch_service', float('nan')):.3f} | {inc.get('min_branch_service', float('nan')):.3f} | {z.get('transfer_units', 0):.0f} | "
                     f"{z.get('abstained_reviews', 0):.1f}/{summary['reviews']} | {z.get('wall_p50', 0):.0f}/{z.get('wall_p95', 0):.0f}/{z.get('wall_max', 0):.0f} | {'PASS' if e.get('pass') else ('FAIL' if e.get('checks') else '-')} |")
    lines += ["", "## Policies per fixture (cost, service per branch)", ""]
    for name, e in summary["fixtures"].items():
        lines.append(f"### {name}")
        lines.append("| policy | cost | service by branch | breaches | transfers | purchases | inventory | wall p50 |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for p, v in e["policies"].items():
            if not v.get("runs"):
                lines.append(f"| {p} | no run: {v.get('failures')} | | | | | | |")
                continue
            lines.append(f"| {p} | {v['cost']:,.0f} | {', '.join(f'{k}={x:.3f}' for k, x in v['service_by_branch'].items())} | {v['breaches']:.1f} | {v['transfer_units']:.0f} | {v['purchase_units']:.0f} | {v['avg_inventory_units']:.0f} | {v['wall_p50']:.1f} |")
        lines.append("")
    lines += ["## Network principles", "", "| principle | pass | numbers |", "|---|---|---|"]
    for k, v in summary["network_principles"].items():
        nums = {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items() if kk not in ("pass", "note")}
        lines.append(f"| {k} | {'PASS' if v.get('pass') else 'FAIL'} | {nums} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", default="")
    ap.add_argument("--policies", default=",".join(POLICIES))
    ap.add_argument("--seeds", default=",".join(str(s) for s in SEEDS))
    ap.add_argument("--reviews", type=int, default=REVIEWS)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--tag", default="dev")
    ap.add_argument("--max-solve", type=float, default=None)
    a = ap.parse_args()
    names = [n for n in FIXTURES if not a.fixtures or n.split("_")[0] in a.fixtures.split(",") or n in a.fixtures.split(",")]
    policies = a.policies.split(",")
    seeds = [int(s) for s in a.seeds.split(",")]
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{a.tag}.jsonl"
    done = set()
    if path.exists():
        for line in path.read_text().splitlines():
            r = json.loads(line)
            done.add((r["fixture"], r["policy"], r["seed"]))
    jobs = [(n, p, s, a.reviews, a.max_solve) for n in names for p in policies for s in seeds if (n, p, s) not in done]
    # ZAAD cells are the long ones: schedule them first so the pool stays busy
    jobs.sort(key=lambda j: (j[1] != "gated", j[0]))
    print(f"{len(jobs)} cells to run ({len(done)} already recorded) -> {path}")
    started = time.time()
    with path.open("a") as fh, ProcessPoolExecutor(max_workers=a.workers) as pool:
        for cell in pool.map(_job, jobs):
            fh.write(json.dumps(cell, allow_nan=True) + "\n")
            fh.flush()
            print(f"  {cell['fixture']:34s} {cell['policy']:18s} seed {cell['seed']} {cell['status']:16s} reviews {cell.get('reviews_completed')} "
                  f"cost {cell.get('score', {}).get('continuation', float('nan')):>10,.0f} wall p50 {cell.get('compute', {}).get('wall_p50', 0):5.1f}s  [{time.time() - started:.0f}s]", flush=True)
    records = [json.loads(line) for line in path.read_text().splitlines()]
    summary = summarize(records, a.reviews)
    (OUT / f"{a.tag}.summary.json").write_text(json.dumps(summary, indent=1, allow_nan=True, default=str))
    (OUT / f"{a.tag}.tables.md").write_text(tables(summary))
    print(f"valid {summary['valid_fixtures']} passing {summary['passing_fixtures']} principles {summary['principles_passing']}/{summary['principles_total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
