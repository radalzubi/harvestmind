"""Decision-time versus truth-time reconciliation for fixtures C, O and P (P1 closure pass, step C).

For every review of every seed: the planner's view (target, projected service of the chosen
candidate on the selection worlds, its spread and lower tail, demand and its uncertainty, position,
raw need, protection, lot effects, final order, cost) against what the truth then did (realised
demand, service, shortage, cost), plus the same for the best rejected candidate, the incumbent and
the best competent baseline. Writes docs/zaad_full/evidence/p1/closure/cop_trace.json."""
from __future__ import annotations

import json
import sys
from statistics import mean, pstdev

from scripts.p1_fixtures import REVIEWS, SEEDS, build
from zaad.full.planner import evaluate, plan
from zaad.full.replay import replay
from zaad.full.worlds import draw, forecast_all

NAMES = {"C": "C_moq_four_weeks", "O": "O_low_opening_stock", "P": "P_high_opening_stock"}
BEST = {"C": "reorder_point", "O": "reorder_point", "P": "reorder_point"}


def service_of(rows, sid):
    d = sum(x["demand"] for r in rows if r["usable"] for x in r["service_by_period"] if x["service"] == sid)
    s = sum(x["served"] for r in rows if r["usable"] for x in r["service_by_period"] if x["service"] == sid)
    return s / d if d else None


def per_world_service(rows, sid):
    out = []
    for r in rows:
        if not r["usable"]:
            out.append(None)
            continue
        d = sum(x["demand"] for x in r["service_by_period"] if x["service"] == sid)
        s = sum(x["served"] for x in r["service_by_period"] if x["service"] == sid)
        out.append(s / d if d else None)
    return out


def trace(letter: str) -> list[dict]:
    name = NAMES[letter]
    rows = []
    for seed in SEEDS:
        req0 = build(name, seed)
        truth = draw(req0, seed + 10000, 1)[0]
        kept: list = []
        gated = replay(req0, truth, REVIEWS, "gated", keep_requests=kept)
        base = replay(req0, truth, REVIEWS, BEST[letter])
        sid = req0.services[0].id
        for t, req in enumerate(kept):
            report = plan(req)
            fits = forecast_all(req)
            selection = draw(req, req.seed, req.scenarios)
            e = report["economics"]
            chosen = report["selected_policy"]
            sel = {k: v["selection"] for k, v in report["candidates"].items()}
            # per-world service of the chosen plan on the selection worlds
            final_name = chosen if chosen in report["candidates"] else "incumbent"
            from zaad.full.model import Solution
            final_plan = Solution("OPTIMAL", {(a["source"], a["period"]): a["quantity"] for a in report["actions"] if a["action"] == "purchase"}, {}, {}, {}, None, [], 0., 0, 0, None, 0., [])
            for p in req.pipeline:
                final_plan.amendments[(p.id, next(o.id for o in p.options if o.action == "keep"))] = p.remaining
            sel_rows = evaluate(req, final_plan, selection)
            svc_worlds = per_world_service(sel_rows, sid)
            usable = [v for v in svc_worlds if v is not None]
            g_review = gated["reviews"][t]["settlement"]
            b_review = base["reviews"][t]["settlement"]
            truth_demand = truth.demand[sid][t]
            gates = report["candidate_gates"]
            rejected = [(k, v) for k, v in gates.items() if not v["accepted"]]
            order = e["orders"][0] if e["orders"] else None
            rows.append({
                "fixture": name, "seed": seed, "review": t, "status": report["status"], "state": report["orchestration"]["state"],
                "chosen": chosen, "target": req.services[0].target,
                "projected_service_selection_mean": service_of(sel_rows, sid),
                "projected_service_worlds": svc_worlds,
                "projected_service_min": min(usable) if usable else None,
                "projected_service_sd": pstdev(usable) if len(usable) > 1 else 0.,
                "forecast_mean": fits[sid]["mean"], "forecast_sd": fits[sid].get("sd"),
                "fill_mean": req.sources[0].fill_mean, "fill_sd": req.sources[0].fill_sd, "lead_sd_days": req.sources[0].lead_sd_days,
                "on_hand": sum(x.usable for x in req.stock), "inbound": sum(p.expected_accepted_remaining for p in req.pipeline),
                "order": (order or {}).get("quantity", 0.), "economic_need": (order or {}).get("economic_need"),
                "protection_units": (order or {}).get("justified_protection_units"), "attribution": (order or {}).get("attribution"),
                "projected_cost_selection": report["selection_costs"].get(final_name, {}).get("fitted"),
                "candidate_costs": {k: v.get("fitted") for k, v in report["selection_costs"].items()},
                "candidate_services": {k: (v.get("service") or {}).get(sid) if isinstance(v, dict) else None for k, v in sel.items()},
                "best_rejected": [(k, v["reason"][:90]) for k, v in rejected][:3],
                "materiality": (e["materiality"] or {}).get("reason"),
                "reasons": [r[:100] for r in report["reasons"]],
                "truth_demand": truth_demand, "truth_fill": truth.fills[req.sources[0].id, t] if (req.sources[0].id, t) in truth.fills else None,
                "truth_arrival": truth.arrival.get((req.sources[0].id, t)),
                "realised_service_gated": service_of([{"usable": True, **g_review}], sid),
                "realised_shortage_gated": sum(x["demand"] - x["served"] for x in g_review["service_by_period"]),
                "realised_cost_gated": g_review["economic_cost"], "end_stock_gated": sum(x["quantity"] for x in g_review["end_stock"]),
                "baseline_buy": [round(p["quantity"], 1) for p in base["reviews"][t]["purchases"]],
                "realised_service_base": service_of([{"usable": True, **b_review}], sid),
                "realised_shortage_base": sum(x["demand"] - x["served"] for x in b_review["service_by_period"]),
                "realised_cost_base": b_review["economic_cost"], "end_stock_base": sum(x["quantity"] for x in b_review["end_stock"]),
            })
        rows.append({"fixture": name, "seed": seed, "review": "TOTAL", "gated_cost": gated["economic_cost"], "base_cost": base["economic_cost"],
                     "gated_ledger": gated["ledger"], "base_ledger": base["ledger"]})
    return rows


if __name__ == "__main__":
    letters = sys.argv[1:] or ["C", "O", "P"]
    out = []
    for letter in letters:
        out += trace(letter)
    json.dump(out, open("docs/zaad_full/evidence/p1/closure/cop_trace.json", "w"), indent=1, default=float)
    for r in out:
        if r["review"] == "TOTAL":
            print(f"{r['fixture'][:12]} seed {r['seed']} TOTAL gated {r['gated_cost']:.0f} base {r['base_cost']:.0f}")
        else:
            a = r["attribution"] or {}
            print(f"{r['fixture'][:12]} s{r['seed']} r{r['review']:2d} {r['status'][:6]} {r['chosen'][:18]:18s} psvc {r['projected_service_selection_mean'] or 0:.3f} min {r['projected_service_min'] or 0:.3f} "
                  f"| mu {r['forecast_mean']:.1f} sd {r['forecast_sd'] or 0:.1f} | hand {r['on_hand']:.0f} inb {r['inbound']:.0f} need {r['economic_need'] or 0:.0f} prot {r['protection_units'] or 0:.0f} order {r['order']:.0f} "
                  f"| truth d {r['truth_demand']:.1f} svc {r['realised_service_gated'] or 0:.3f}/{r['realised_service_base'] or 0:.3f} short {r['realised_shortage_gated']:.1f}/{r['realised_shortage_base']:.1f} cost {r['realised_cost_gated']:.0f}/{r['realised_cost_base']:.0f} "
                  f"| base buy {r['baseline_buy']}")
