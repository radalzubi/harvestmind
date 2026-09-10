"""The P2 network decision layer (`plan_network`).

Architecture (docs/zaad_full/evidence/p2/P2_ARCHITECTURE_DECISION.md): the frozen optimizer already
solves purchasing, central and local inventory, transfers, allocation and service in ONE joint
network MILP per candidate, with exact per-location, per-cohort conservation and scenario-invariant
transfers. P2 therefore adds no second engine. It coordinates and represents:

  1. the network view (`topology.network_state`): roles, echelons, lanes, reachability, stranded
     stock, shared resources, structural issues;
  2. the network router (`network_router`): which shared resources are contested this review, which
     locations compete, whether central stock or shared supply is scarce over the reachable window,
     which stock cannot reach demand - the reasons behind the network decision, decided before the
     frozen planner runs and never overriding it;
  3. the frozen decision (`zaad.full.planner.plan`) on the request as declared - correlated worlds
     when `demand_correlation` is set, lane packs and dispatch costs when declared, the incumbent
     network policy when `incumbent_rule` is `network:...`;
  4. network accounting on the independent settlement (`accounting.network_accounting`) for the
     selected plan and for the incumbent, on the same confirmation worlds the frozen selector uses;
  5. operator-facing explanations (`explain.explain_network`).

Ownership is unchanged: P1 owns ordinary purchasing economics, P0 owns protection and recovery; the
network router only names the shared resources and affected locations those planners act on.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from zaad.full.contracts import Request
from zaad.full.model import Solution
from zaad.full.planner import plan
from zaad.full.worlds import dates, draw
from zaad.meio import VERSION
from zaad.meio.accounting import network_accounting
from zaad.meio.explain import explain_network
from zaad.meio.topology import NetworkState, network_state, validate_network


def solution_from_actions(rows: list[dict], status: str = "OPTIMAL") -> Solution:
    """Rebuild a Solution from the report's action rows (the same mapping the frozen replay uses)."""
    return Solution(status,
                    {(r["source"], r["period"]): r["quantity"] for r in rows if r["action"] == "purchase"},
                    {(r["transfer"], r["expiry_cohort"], r["period"]): r["quantity"] for r in rows if r["action"] == "transfer"},
                    {(r["po"], r["option"]): r["quantity"] for r in rows if r["action"] == "po_option"},
                    {}, None, [], 0., 0, 0, None, None, [])


def network_router(req: Request, state: NetworkState, fits: dict) -> dict[str, Any]:
    """Shared-resource and reachability classification of the review. Read-only.

    For every origin that feeds several branches: each branch's requirement over its reachable window
    (demand until the first period a transfer dispatched now could land, plus one period, less what
    it holds and has in transit) against what the origin holds usable now; scarce when the sum of
    requirements exceeds the origin's usable stock plus what lands there in period 0. For every shared
    supplier resource: the destinations' echelon demand over the supplier lead against the resource
    capacity. Locations whose demand no source and no lane can reach are named."""
    rate: dict[tuple[str, str], float] = defaultdict(float)
    for s in req.services:
        rate[s.sku, s.location] += float(fits.get(s.id, {}).get("mean", 0.))
    reasons: list[str] = []
    scarce_origins: list[dict] = []
    for shared in state.shared["origin"]:
        sku, origin = shared["sku"], shared["origin"]
        requirements = []
        for dest in shared["destinations"]:
            reach = state.reach.get((sku, dest))
            pos = state.positions.get((sku, dest))
            window = (reach.local_only_periods if reach else 1) + 1
            need = rate[sku, dest] * window - ((pos.on_hand_usable + pos.transfer_transit) if pos else 0.)
            requirements.append({"location": dest, "window_periods": window, "requirement": max(0., need), "rate": rate[sku, dest]})
        origin_pos = state.positions.get((sku, origin))
        available = origin_pos.on_hand_usable if origin_pos else 0.
        total = sum(r["requirement"] for r in requirements)
        entry = {"sku": sku, "origin": origin, "destinations": shared["destinations"], "available": available, "requirements": requirements,
                 "total_requirement": total, "scarce": total > available + 1e-6, "competing": [r["location"] for r in requirements if r["requirement"] > 0]}
        scarce_origins.append(entry)
        if entry["scarce"] and len(entry["competing"]) > 1:
            reasons.append(f"{origin} holds {available:,.0f} usable {sku} against a reachable-window need of {total:,.0f} across {', '.join(entry['competing'])}: allocation decides service")
        elif entry["scarce"]:
            reasons.append(f"{origin} holds {available:,.0f} usable {sku} against a need of {total:,.0f} at {', '.join(entry['competing']) or 'its branches'}: the pool is short, purchasing decides")
    supplier_contention: list[dict] = []
    sources = {s.id: s for s in req.sources}
    for shared in state.shared["resource"]:
        resource = next(r for r in req.resources if r.id == shared["resource"])
        users = [sources[s] for s in shared["sources"]]
        need = 0.
        for src in users:
            lead = dates(req, src, 0)[1]
            fed = {a.destination for a in req.transfers if a.approved and a.sku == src.sku and a.origin == src.destination}
            need += (rate[src.sku, src.destination] + sum(rate[src.sku, d] for d in fed)) * (lead + 1)
        contended = need > resource.capacity_by_period[0] * 2 + 1e-6      # two periods of shared capacity against lead-window demand
        supplier_contention.append({"resource": resource.id, "sources": shared["sources"], "capacity_period_0": resource.capacity_by_period[0],
                                    "lead_window_demand": need, "contended": contended})
        if contended:
            reasons.append(f"shared capacity {resource.id} ({resource.capacity_by_period[0]:,.0f} per period) is below the lead-window demand it serves ({need:,.0f}): destinations compete for supply")
    unreachable = [x for x in state.stranded]
    for x in unreachable:
        reasons.append(f"{x['units']:,.0f} of {x['sku']} at {x['location']} cannot reach demand: {x['reason']}")
    for issue in state.issues:
        reasons.append(issue)
    affected = sorted({loc for e in scarce_origins if e["scarce"] for loc in e["competing"]} | {loc for e in scarce_origins if e["scarce"] for loc in [e["origin"]]})
    return {"scarce_origins": scarce_origins, "supplier_contention": supplier_contention, "unreachable": unreachable,
            "affected_locations": affected, "reasons": reasons,
            "scope": "decided before the frozen planner from the request and the fitted demand rate; names the contested resources, never overrides the frozen decision"}


class NetworkRefused(ValueError):
    """The request cannot be planned as a network as declared (a structural defect the economics cannot price)."""


def _native(x: Any) -> Any:
    """Plain Python scalars throughout (numpy floats and bools from the frozen report's arithmetic), so
    the network report serialises through json and the API alike. Values are unchanged."""
    import numpy as np
    if isinstance(x, dict):
        return {k: _native(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_native(v) for v in x]
    if isinstance(x, np.bool_):
        return bool(x)
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.floating):
        return float(x)
    return x


def plan_network(req: Request) -> dict[str, Any]:
    loops = [i for i in validate_network(req) if "zero-cost reverse pair" in i]
    if loops:
        # a free lane in both directions leaves nothing in the economics to separate A->B->A from doing
        # nothing; the operator declares a cost (however small) or removes one direction
        raise NetworkRefused("; ".join(loops))
    report = plan(req)
    fits = report.get("forecasts", {})
    state = network_state(req, rates={sid: float(f.get("mean", 0.)) for sid, f in fits.items()})
    router = network_router(req, state, fits)
    final = solution_from_actions(report["actions"]) if report.get("status") != "ABSTAIN" else None
    incumbent = solution_from_actions(report["incumbent_actions"]) if report.get("incumbent_actions") else None
    # the frozen selector's own confirmation worlds (seed + 10000), so the accounting and the
    # confirmation share one representation
    lean_profile = all(float(row["state"]["activity"]) <= .05 for row in report.get("protection", []))
    req_draw = req if (lean_profile or not req.stratified_scenarios) else req.model_copy(update={"stratified_scenarios": False})
    worlds = draw(req_draw, req.seed + 10000, req.scenarios)
    final_accounts = network_accounting(req, final, worlds, "selected")
    incumbent_accounts = network_accounting(req, incumbent, worlds, "incumbent")
    explanations = explain_network(req, state, final, incumbent, final_accounts, incumbent_accounts, router, report)
    report["network"] = {"version": VERSION, "state": state.summary(), "router": router,
                         "selected": final_accounts, "incumbent": incumbent_accounts, "explanations": explanations,
                         "declared": {"demand_correlation": req.demand_correlation, "incumbent_rule": req.incumbent_rule,
                                      "lanes_with_packs": [a.id for a in req.transfers if a.multiple > 0],
                                      "lanes_with_dispatch_cost": [a.id for a in req.transfers if a.fixed_cost_per_dispatch > 0]},
                         "scope": "P2 network layer around the frozen joint decision; approval stays with the operator; no executable order"}
    return _native(report)
