"""Operator-facing explanations of a network decision (P2).

Every sentence here is generated from data the report already carries: the plan's own actions, the
incumbent's actions, the reachability view, the origin's stock, the lane physics, the per-location
service outcomes on the confirmation worlds and the frozen selector's reasons. Nothing is inferred
from a fixture or a cell. The customer-facing `summary` avoids optimisation vocabulary; the
`diagnostics` keep the numbers.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from zaad.full.contracts import Request
from zaad.full.model import Solution
from zaad.meio.topology import NetworkState


def _units(x: float) -> str:
    return f"{x:,.0f}"


def _period_0(plan: Solution | None):
    purchases = {k[0]: q for k, q in (plan.purchases.items() if plan else []) if k[1] == 0 and q > 0}
    transfers: dict[str, float] = defaultdict(float)
    for (arc, _e, t), q in (plan.transfers.items() if plan else []):
        if t == 0 and q > 0:
            transfers[arc] += q
    return purchases, dict(transfers)


def explain_network(req: Request, state: NetworkState, final: Solution | None, incumbent: Solution | None,
                    final_accounts: dict, incumbent_accounts: dict, router: dict, report: dict) -> dict[str, Any]:
    sources = {s.id: s for s in req.sources}
    lanes = state.lanes
    fits = report.get("forecasts", {})
    rate = {(s.sku, s.location): 0. for s in req.services}
    for s in req.services:
        rate[s.sku, s.location] += float(fits.get(s.id, {}).get("mean", 0.))
    f_purch, f_tr = _period_0(final)
    i_purch, i_tr = _period_0(incumbent)
    accepted = report.get("status") == "PENDING_REVIEW"
    service_inc = {s["service"]: s for s in incumbent_accounts.get("services", [])}
    by_location: dict[str, list[dict]] = defaultdict(list)
    for s in final_accounts.get("services", []):
        by_location[s["location"]].append(s)

    purchases = []
    for source_id in sorted(set(f_purch) | set(i_purch)):
        src = sources[source_id]
        fed = sorted({lanes[a].destination for a in lanes if lanes[a].origin == src.destination and lanes[a].sku == src.sku and lanes[a].approved})
        covers = [src.destination] + fed if rate.get((src.sku, src.destination), 0.) > 0 else fed or [src.destination]
        demand_covered = sum(rate.get((src.sku, loc), 0.) for loc in covers)
        q_f, q_i = f_purch.get(source_id, 0.), i_purch.get(source_id, 0.)
        if q_f > 0:
            why = (f"Buy {_units(q_f)} of {src.sku} from {src.supplier} into {src.destination}: it covers about "
                   f"{q_f / demand_covered:.1f} weeks of the demand it serves ({', '.join(covers)}) at the current rate of {_units(demand_covered)} per period."
                   if demand_covered > 0 else f"Buy {_units(q_f)} of {src.sku} from {src.supplier} into {src.destination}.")
            if q_i > 0 and abs(q_i - q_f) > 1e-6:
                why += f" Your current policy would buy {_units(q_i)}."
            elif q_i <= 0:
                why += " Your current policy would not buy this period."
        else:
            why = f"No purchase of {src.sku} from {src.supplier} this period" + (f"; your current policy would buy {_units(q_i)}." if q_i > 0 else ".")
        purchases.append({"source": source_id, "sku": src.sku, "supplier": src.supplier, "destination": src.destination, "units": q_f, "incumbent_units": q_i,
                          "serves_locations": covers, "demand_rate_covered": demand_covered, "summary": why})

    transfers = []
    for arc_id in sorted(set(f_tr) | set(i_tr) | {a for a in lanes if lanes[a].approved}):
        lane = lanes[arc_id]
        q_f, q_i = f_tr.get(arc_id, 0.), i_tr.get(arc_id, 0.)
        reach = state.reach.get((lane.sku, lane.destination))
        pos = state.positions.get((lane.sku, lane.destination))
        origin_pos = state.positions.get((lane.sku, lane.origin))
        branch_rate = rate.get((lane.sku, lane.destination), 0.)
        local_cover = (pos.on_hand_usable + pos.transfer_transit) / branch_rate if pos and branch_rate > 0 else None
        own_source = any(s.sku == lane.sku and s.destination == lane.destination and s.approved and s.compliance == "cleared" for s in req.sources)
        if q_f > 0:
            why = (f"Move {_units(q_f)} of {lane.sku} from {lane.origin} to {lane.destination} now; it lands in period {lane.earliest_arrival} "
                   f"and serves demand from then on. {lane.destination} holds about {local_cover:.1f} periods of demand before it arrives."
                   if local_cover is not None else f"Move {_units(q_f)} of {lane.sku} from {lane.origin} to {lane.destination} now; it lands in period {lane.earliest_arrival}.")
            if own_source:
                why += " Moving pooled stock is cheaper than a separate local purchase for this need."
            if origin_pos is not None and origin_pos.on_hand_usable - sum(f_tr.get(a, 0.) for a in lanes if lanes[a].origin == lane.origin and lanes[a].sku == lane.sku) < 1e-6:
                why += f" This empties {lane.origin}'s usable stock of {lane.sku}."
            if lane.capacity > 0 and q_f >= lane.capacity - 1e-6:
                why += " The lane is at capacity."
            if q_i > 0 and abs(q_i - q_f) > 1e-6:
                why += f" Your current policy would move {_units(q_i)}."
            elif q_i <= 0:
                why += " Your current policy would not move stock this period."
        else:
            svc = [s for s in by_location.get(lane.destination, []) if s["sku"] == lane.sku]
            ok = all((s["achieved"] or 0.) >= s["target"] - req.service_tolerance for s in svc) if svc else True
            sent_elsewhere = sum(f_tr.get(a, 0.) for a in lanes if lanes[a].origin == lane.origin and lanes[a].sku == lane.sku and a != arc_id)
            origin_left = (origin_pos.on_hand_usable if origin_pos else 0.) - sent_elsewhere
            why = (f"No transfer from {lane.origin} to {lane.destination} this period: {lane.destination} is served from what it holds"
                   + (f" ({local_cover:.1f} periods of demand on hand or on its way)" if local_cover is not None else "") + "."
                   if ok else f"No transfer from {lane.origin} to {lane.destination} this period although {lane.destination} is projected below target; "
                   + ("the origin holds nothing usable to send." if origin_pos is None or origin_pos.on_hand_usable <= 1e-6 else
                      f"{lane.origin}'s usable stock went to a higher-priority or costlier shortage elsewhere." if origin_left <= 1e-6 else
                      "the plan judged the move not worth its cost or lead."))
            if q_i > 0:
                why += f" Your current policy would move {_units(q_i)}."
        transfers.append({"transfer": arc_id, "sku": lane.sku, "origin": lane.origin, "destination": lane.destination, "units": q_f, "incumbent_units": q_i,
                          "arrives_period": lane.earliest_arrival, "lead_periods": lane.lead_periods, "cost_per_unit": lane.cost_per_unit,
                          "branch_cover_periods_before_arrival": local_cover, "local_only_periods": reach.local_only_periods if reach else None,
                          "origin_usable_now": origin_pos.on_hand_usable if origin_pos else 0., "branch_has_own_source": own_source, "summary": why})

    holds = []
    for (sku, origin), dests in {(lanes[a].sku, lanes[a].origin): sorted({lanes[b].destination for b in lanes if lanes[b].origin == lanes[a].origin and lanes[b].sku == lanes[a].sku and lanes[b].approved}) for a in lanes if lanes[a].approved}.items():
        origin_pos = state.positions.get((sku, origin))
        if origin_pos is None:
            continue
        moved = sum(f_tr.get(a, 0.) for a in lanes if lanes[a].origin == origin and lanes[a].sku == sku)
        left = max(0., origin_pos.on_hand_usable - moved)
        pooled = next((r for r in ((report.get("capital") or {}).get("pooling") or []) if r["sku"] == sku and r["origin"] == origin), None)
        rho = req.demand_correlation
        if left > 1e-6:
            why = (f"Keep {_units(left)} of {sku} at {origin} for now: it can still reach {', '.join(dests)} within "
                   f"{max(lanes[a].earliest_arrival for a in lanes if lanes[a].origin == origin and lanes[a].sku == sku)} period(s), so one pooled stock covers whichever branch runs short first.")
            if rho >= .8:
                why += " The branches' demand moves together, so pooling protects less than it would for independent branches; the plan keeps more locally."
            elif rho > 0:
                why += f" Branch demand is partly correlated ({rho:.0%}), which reduces the pooling benefit accordingly."
        else:
            why = f"{origin} sends out all its usable {sku} this period" + ("." if moved > 0 else " (nothing usable to hold).")
        holds.append({"sku": sku, "origin": origin, "destinations": dests, "held_units": left, "moved_units": moved, "correlation": rho,
                      "pooled_units_reference": pooled["pooled_units"] if pooled else None, "summary": why})

    allocation = []
    for shared in router.get("scarce_origins", []):
        sku, origin = shared["sku"], shared["origin"]
        rows = []
        for dest in shared["destinations"]:
            arc = next((a for a in lanes if lanes[a].origin == origin and lanes[a].destination == dest and lanes[a].sku == sku and lanes[a].approved), None)
            got = f_tr.get(arc, 0.) if arc else 0.
            svc = [s for s in final_accounts.get("services", []) if s["location"] == dest and s["sku"] == sku]
            need = next((r["requirement"] for r in shared["requirements"] if r["location"] == dest), 0.)
            unit_shortage_cost = max((s.selling_price + s.sla_per_unmet for s in req.services if s.sku == sku and s.location == dest), default=0.)
            rows.append({"location": dest, "requested": need, "received": got, "priority": max((s["priority"] for s in svc), default=0.),
                         "target": max((s["target"] for s in svc), default=None), "unit_shortage_cost": unit_shortage_cost,
                         "projected_service": min((s["achieved"] for s in svc if s["achieved"] is not None), default=None),
                         "incumbent_service": min((service_inc[s["service"]]["achieved"] for s in svc if s["service"] in service_inc and service_inc[s["service"]]["achieved"] is not None), default=None)})
        rows.sort(key=lambda r: (-r["priority"], -r["unit_shortage_cost"], r["location"]))
        if len(rows) >= 2 and shared["available"] + 1e-6 < sum(r["requested"] for r in rows):
            first, rest = rows[0], rows[1:]
            reason = (f"{origin} holds {_units(shared['available'])} of {sku} against requests of {_units(sum(r['requested'] for r in rows))}. "
                      f"{first['location']} receives {_units(first['received'])}" + (f" because its customers carry the higher priority ({first['priority']:g})" if first["priority"] > max(r["priority"] for r in rest)
                      else f" because a lost unit there costs more ({first['unit_shortage_cost']:.2f} against {max(r['unit_shortage_cost'] for r in rest):.2f})" if first["unit_shortage_cost"] > max(r["unit_shortage_cost"] for r in rest)
                      else " on equal priority and shortage cost, by the plan's total-cost balance") + "; "
                      + ", ".join(f"{r['location']} receives {_units(r['received'])}" for r in rest) + ".")
        else:
            reason = f"{origin} can cover every request for {sku} this period; no branch is rationed."
        allocation.append({"sku": sku, "origin": origin, "available": shared["available"], "rows": rows, "summary": reason})

    do_nothing: dict[str, Any] = {"incumbent_service": {s["service"]: {"location": s["location"], "achieved": s["achieved"], "target": s["target"], "breach_share": s["breach_share"]} for s in incumbent_accounts.get("services", [])},
                  "incumbent_cost": (incumbent_accounts.get("economics") or {}).get("economic_cost"),
                  "selected_cost": (final_accounts.get("economics") or {}).get("economic_cost"),
                  "summary": ("Doing nothing beyond your current policy keeps every location at target." if not any((s["breach_share"] or 0.) > .5 for s in incumbent_accounts.get("services", []))
                              else "Under your current policy " + ", ".join(f"{s['location']} is projected at {s['achieved']:.1%} against a {s['target']:.0%} target"
                                                                            for s in incumbent_accounts.get("services", []) if (s["breach_share"] or 0.) > .5) + ".")}
    if_rejected = {"summary": ("If this recommendation is rejected the current policy runs: " + do_nothing["summary"].replace("Doing nothing beyond your current policy", "it")
                               if accepted else "Nothing is proposed; the current policy stands."),
                   "alternatives_considered": {k: v.get("reason") for k, v in (report.get("candidate_gates") or {}).items()}}
    verdict = ("ZAAD recommends the changes below for your approval." if accepted else
               "ZAAD recommends no change to your current network policy this period." if report.get("status") == "RETAIN_INCUMBENT" else
               "ZAAD abstains: the current position cannot be projected reliably.")
    drivers = list(router.get("reasons", [])) + [str(r) for r in report.get("reasons", [])][:3]
    return {"verdict": verdict, "drivers": drivers, "purchases": purchases, "transfers": transfers, "held_centrally": holds,
            "allocation": allocation, "do_nothing": do_nothing, "if_rejected": if_rejected,
            "unreachable_stock": state.stranded, "issues": state.issues,
            "scope": "generated from the plan, the incumbent, the network view and the confirmation-world settlement; no fixture knowledge"}
