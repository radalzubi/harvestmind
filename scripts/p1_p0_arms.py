"""P1 closure pass, step B: the proposed P1 defaults against the frozen P0 six-cell focused set.

usage: PYTHONPATH=. python3 -m scripts.p1_p0_arms <arm> [cells...]
arms:
  p0_defaults   P1 code with P0 behaviour: service_gate_basis=incumbent, order_smoothing=.02,
                timing_tiebreak=0, materiality gate off (thresholds so large it never fires)
  gate          p0_defaults + service_gate_basis=target
  smoothing     p0_defaults + the conditional smoothing rule (identical to p0_defaults on cells
                without explicit order economics; the script checks and says so)
  both          gate + smoothing
  final         the P1 defaults exactly as shipped (whatever the request carries by default)
Same cells, seed (38001), truth and replay as docs/zaad_full/evidence/v8/p0/final8.py; per-cell
rows in the same shape, written to docs/zaad_full/evidence/p1/closure/p0_arm_<arm>.json."""
from __future__ import annotations

import collections
import json
import statistics as st
import sys
import time

sys.path.insert(0, "scripts")
import run_zaad_full_benchmark as B  # noqa: E402
import zaad.full.planner as P  # noqa: E402
import zaad.full.replay as R  # noqa: E402
from zaad.full.replay import replay  # noqa: E402

ARMS = {
    "p0_defaults": {"service_gate_basis": "incumbent", "order_smoothing": .02, "timing_tiebreak": 0.,
                    "materiality_cost_fraction": 0., "materiality_inventory_fraction": 0., "materiality_service": 0.},
    "gate": {"service_gate_basis": "target", "order_smoothing": .02, "timing_tiebreak": 0.,
             "materiality_cost_fraction": 0., "materiality_inventory_fraction": 0., "materiality_service": 0.},
    "smoothing": {"service_gate_basis": "incumbent", "order_smoothing": .02, "timing_tiebreak": 0.,
                  "materiality_cost_fraction": 0., "materiality_inventory_fraction": 0., "materiality_service": 0.},
    "both_gate_smoothing": {"service_gate_basis": "target", "order_smoothing": .02, "timing_tiebreak": 0.,   # was a second "both" key, shadowed by the materiality / tie-break arm below
             "materiality_cost_fraction": 0., "materiality_inventory_fraction": 0., "materiality_service": 0.},
    "final": {},
    "final_incgate": {"service_gate_basis": "incumbent"},   # P1 representation + band guard, P0 gate
    # representation + guard alone: P0 gate, no tie-break, materiality gate off
    "representation_only": {"service_gate_basis": "incumbent", "timing_tiebreak": 0., "stratified_scenarios": True,
                            "materiality_cost_fraction": 0., "materiality_inventory_fraction": 0., "materiality_service": 0.},
    # Objective 2: materiality gate and tie-break, separately and together, at product defaults otherwise
    "neither": {},
    "materiality_only": {"materiality_cost_fraction": .01, "materiality_inventory_fraction": .05, "materiality_service": .005},
    "tiebreak_only": {"timing_tiebreak": 1e-4},
    "both": {"materiality_cost_fraction": .01, "materiality_inventory_fraction": .05, "materiality_service": .005, "timing_tiebreak": 1e-4},
    # per-period LHS sampler (P1 final closure): the representation arm above is rerun under it as "lhs"
    "lhs": {"stratified_scenarios": True},
    "analytic_shortage": {"analytic_shortage": True},
    # planner-boundary pass: the clean baseline (product defaults) recorded at decision level, and the router arm
    "clean_reference": {},
    "clean_reference_rerun": {},   # same code as clean_reference: measures run-to-run variability of time-limited solves
    "router": {},
    "router_rerun": {},
    "router_passj": {},
    "router_lot": {},
    "router_lot_rerun21": {},
    "router_lot_off21": {"lot_terminal_valuation": False},
    "router_final": {},
    "router_tA": {},
    "router_tA_rerun108": {},
    "router_tAonly": {},
    "router_final_l": {},
    "p2_meio": {},          # P2 freeze gate: product defaults on the P2 code; every P0 cell must stay decision-identical to router_cycle
    "p2_meio_rerun": {},    # P2 freeze gate: the wall-clock-limited cells (21, 108) rerun alone on a quiet machine
    "p2_meio_quiet": {},    # P2 freeze gate: cell 108 alone with nothing else running
    "p2_perf": {},          # P2 performance pass: product defaults after the exact FEFO symmetry elimination; every P0 cell must stay decision-identical to router_cycle
    "sector_physics": {},   # three-sector physics freeze gate: product defaults with the sector layer present (no profile on the P0 cells); decision-identical to router_cycle
    "p4_recourse": {},   # P4 adaptive recourse: product defaults with the recourse layer present (no recourse block on the P0 cells); P0 cells must stay decision-identical to router_cycle
    "p4_recourse_rerun": {},   # P4: wall-clock-limited cells alone on a quiet machine
    "p3_perf_closure_rerun": {},   # P3 production performance closure: cell 21 alone on a quiet machine (established wall-clock protocol)
    "p3_perf_closure": {},   # P3 production performance closure: exact activation bounds + order-class search; P0 cells must stay decision-identical to router_cycle
    "p3_sourcing_corrective": {},   # P3 corrective audit: the product freeze 9e496ed re-run alongside the sector and P3 matrices (cell 21 wall-clock-limited)
    "p3_sourcing_corrective_rerun": {},   # P3 corrective audit: cell 21 alone on a quiet machine
    "p3_sourcing": {},      # P3 sourcing freeze gate: product defaults with the sourcing layer present (no portfolio on the P0 cells); decision-identical to router_cycle
    "router_cycle": {},     # P1 final closure: cycle continuation + rule P1-S; every P0 review is protection-owned, so the cells must stay decision-identical   # pass L: final code (B-F reverted, mechanical lint / typing fixes only)    # two-blocker closure: final code, rule T-A only (T-B rejected)   # two-blocker closure: cell 108 alone after a hedged-candidate time-out at r5 in the tA arm      # two-blocker closure: after rule T-A (flag not an ownership reason) and T-B (target floor on P1-owned reviews)   # pass J: final code (ledger key on P1 evaluation rows); P0 cells must stay decision-identical   # pass J: cell 21 alone with the lot valuation off (variability independent of the change?)   # pass J: cell 21 rerun alone after a r5 quantity difference in the time-limited hedged solve     # pass J: after the lot-sizing terminal valuation (P1-owned reviews only; P0 cells must stay decision-identical)   # pass J: after the opt-in rolling replay mode (legacy path must be decision-identical)   # same code as router: run-to-run variability of the time-limited solves
}


def run_cells(arm: str, cells: list[int], write: bool = True) -> dict:
    """Replay the P0 cells under an arm and return one row per cell (the six-cell gate record);
    `write` stores it as closure/p0_arm_<arm>.json. The canonical regression calls this with
    write=False to compare one cell against the recorded arm."""
    settings = dict(ARMS[arm])
    switch = settings.pop("_switch", None)
    if switch is not None:
        import zaad.full.worlds as W
        module, name = switch[0].split(".")
        setattr({"planner": P, "worlds": W}[module], name, switch[1])
        print(f"switch {switch[0]} = {switch[1]}", flush=True)
    orig_plan = P.plan
    out = {}
    for cid in cells:
        cell = next(c for c in B.cells("v7") if c["cell"] == cid)
        req = B.request_for(cell, 38001).model_copy(update={"adaptive_escalation": True, "adaptive_solve_budget": True,
                                                            "joint_recovery_rule": "deficit", **settings})
        truth = B.truth_for(req, cell, 38001)
        reps = []

        def timed(r):
            t0 = time.perf_counter()
            P.TRACE = {}
            rep = orig_plan(r)
            trace = dict(P.TRACE)
            P.TRACE = None
            rep["_decision"] = {"chosen": trace.get("chosen"), "feasible": trace.get("feasible"), "recovery_mode": trace.get("recovery_mode"),
                                "lean_review": trace.get("lean_review"), "gates": trace.get("candidate_gates"),
                                "final_p0": trace.get("final_p0_purchases"), "worlds": [w["name"] for w in trace.get("worlds", [])]}
            reps.append((time.perf_counter() - t0, rep))
            return rep
        P.plan = timed
        R.plan = timed
        t0 = time.perf_counter()
        res = replay(req, truth, cell["horizon"], "gated")
        wall = time.perf_counter() - t0
        P.plan = orig_plan
        R.plan = orig_plan
        log = res.get("reviews") or []
        per, unmet, inv = [], [], []
        for r in log:
            d = sum(x["demand"] for x in r["settlement"]["service_by_period"])
            sv = sum(x["served"] for x in r["settlement"]["service_by_period"])
            per.append(sv / d if d else 1.)
            unmet.append(d - sv)
            inv += [x["inventory_value"] for x in r["settlement"]["trace"]]
        d_all = sum(x["demand"] for r in log for x in r["settlement"]["service_by_period"])
        s_all = sum(x["served"] for r in log for x in r["settlement"]["service_by_period"])
        o = [rep["orchestration"] for _, rep in reps]
        lat = sorted(t for t, _ in reps)
        qt = lambda p: lat[min(len(lat) - 1, int(p * (len(lat) - 1)))] if lat else 0.  # noqa: E731
        row = {
            "arm": arm, "cell": cid, "status": res.get("status"),
            "service": s_all / max(d_all, 1e-9), "tail": min(per) if per else None,
            "p10": sorted(per)[max(0, int(.1 * (len(per) - 1)))] if per else None,
            "breach_reviews": sum(1 for x in per if x < cell["target"] - 1e-6), "worst_unmet": max(unmet) if unmet else 0.,
            "total_unmet": sum(unmet), "inventory": st.mean(inv) if inv else 0., "cost": res.get("economic_cost"), "wall": wall,
            "reviews": len(reps),
            "required_requested": sum(x["required_candidate_count"] for x in o),
            "required_completed": sum(x["required_candidate_completed"] for x in o),
            "required_starved": sum(x["required_candidate_starved"] for x in o),
            "required_infeasible": sum(x.get("required_candidate_infeasible", 0) for x in o),
            "joint_required": sum(1 for x in o if (x.get("classification") or {}).get("joint_recovery") == "REQUIRED"),
            "joint_built": sum(1 for x in o if "joint_recovery" in x["candidates_built"]),
            "joint_chosen": sum(1 for _, rep in reps if rep.get("selected_policy") == "joint_recovery"),
            "states": dict(collections.Counter(x["state"] for x in o)),
            "owners": dict(collections.Counter(x.get("planner_owner") or "?" for x in o)),
            "p1_classes_added": sum(len(x.get("p1_classes_added") or []) for x in o),
            "chosen": dict(collections.Counter(rep.get("selected_policy") or "?" for _, rep in reps)),
            "statuses": dict(collections.Counter(rep.get("status") for _, rep in reps)),
            "abstentions": sum(1 for _, rep in reps if any("NO MATERIAL IMPROVEMENT" in str(x) for x in rep.get("reasons", []))),
            "lat_p50": qt(.5), "lat_p90": qt(.9), "lat_p95": qt(.95), "lat_max": lat[-1] if lat else 0.,
            "per_review": [{"state": x["state"], "selected": rep.get("selected_policy"), "status": rep.get("status"), "service": p, "unmet": u,
                            "joint_class": (x.get("classification") or {}).get("joint_recovery"), "starved": x["required_starved_names"], "latency": t,
                            "owner": x.get("planner_owner"), "requested": x.get("candidate_classes_requested"), "built": x.get("candidates_built"),
                            "p1_classes_added": x.get("p1_classes_added"), "materiality": (rep.get("economics") or {}).get("materiality"),
                            "reasons": [str(r)[:120] for r in rep.get("reasons", [])], **rep["_decision"]}
                           for (t, rep), x, p, u in zip(reps, o, per, unmet)],
        }
        out[cid] = row
        print(f"cell {cid:3d} {arm:12s} svc={row['service']:.3f} p10={row['p10']:.3f} tail={row['tail']:.3f} breach={row['breach_reviews']:2d} "
              f"unmet={row['total_unmet']:6.1f} worst={row['worst_unmet']:5.1f} inv={row['inventory']:6.1f} cost={round(row['cost'] or 0)} "
              f"req={row['required_completed']}/{row['required_requested']} starved={row['required_starved']} infeas={row['required_infeasible']} "
              f"joint={row['joint_required']}req/{row['joint_built']}built/{row['joint_chosen']}chosen abst={row['abstentions']} "
              f"owners={row['owners']} p1_added={row['p1_classes_added']} "
              f"lat p50={row['lat_p50']:.2f} p90={row['lat_p90']:.1f} p95={row['lat_p95']:.1f} max={row['lat_max']:.1f} wall={wall:.0f}s", flush=True)
    if write:
        json.dump(out, open(f"docs/zaad_full/evidence/p1/closure/p0_arm_{arm}.json", "w"), indent=1, default=float)
    return out


def main():
    arm = sys.argv[1]
    cells = [int(x) for x in sys.argv[2:]] or [15, 16, 20, 21, 90, 108]
    run_cells(arm, cells)


if __name__ == "__main__":
    main()
