"""Network accounting (P2): what a plan does to every location, lane and service, read from the
frozen independent settlement and nothing else.

`network_accounting(req, plan, worlds)` settles the plan on every world with the frozen evaluator
(`zaad.full.settlement.settle`, `future_guidance=True`, exactly as the frozen selector's own
evaluation does) and folds the settlement's flow telemetry into:

* flows per SKU / location: opening, supplier receipts, transfer receipts, served, transferred out,
  expired, closing, over the horizon and per period, with the conservation identity checked on
  every row (opening + receipts - served - out - expired = closing);
* lanes: units moved, dispatches, capacity utilisation, cost, and the periods used; reverse-pair
  movement (A->B and B->A of the same SKU inside the horizon) is reported as `ping_pong_units`;
* service per service / location on every world: achieved fill, target, breach (below target minus
  the request's service tolerance), severe starvation (below half the target while demand existed),
  demand-weighted network service and customer-priority-weighted service;
* stranded stock at the end: closing units at a location with no demand and no outbound lane, and
  units still in transit that land after the horizon;
* an economic decomposition of the settlement ledger into node (per location), lane, upstream
  (supplier-order level) and network-level buckets that sums back to the ledger total exactly; the
  node holding and lane transfer buckets are recomputed from the flows and compared with the
  ledger's own components as a second check.

Every figure is a scenario-weighted mean over the worlds unless labelled otherwise. A plan that is
physically unusable on a world contributes an `unusable` row, never a fabricated outcome.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from zaad.full.contracts import Request
from zaad.full.model import Solution
from zaad.full.settlement import PhysicalViolation, settle
from zaad.full.worlds import World

SEVERE_STARVATION_FRACTION = .5     # achieved fill below half the target, with demand present


def _wmean(values: list[float], weights: list[float]) -> float | None:
    total = sum(weights)
    return sum(v * w for v, w in zip(values, weights)) / total if total > 0 and values else None


def settle_rows(req: Request, plan: Solution, worlds: list[World], terminal: dict | None = None) -> list[dict]:
    rows = []
    for world in worlds:
        try:
            rows.append({"world": world.name, "weight": world.weight, "usable": True, **settle(req, plan, world, future_guidance=True)})
        except PhysicalViolation as exc:
            rows.append({"world": world.name, "weight": world.weight, "usable": False, "reason": str(exc)})
    return rows


def flows_by_pair(row: dict) -> dict[tuple[str, str], dict[str, float]]:
    out: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for f in row["flows"]:
        cell = out[f["sku"], f["location"]]
        for k in ("external_receipts", "transfer_receipts", "served", "transfer_out", "expired", "holding_cost"):
            cell[k] += f[k]
        if f["period"] == 0:
            cell["opening"] += f["opening"]
        cell["closing"] = f["closing"]      # the last period's closing wins
        cell["periods"] = max(cell["periods"], f["period"] + 1)
    return out


def conservation_check(row: dict) -> dict[str, Any]:
    worst = 0.
    for f in row["flows"]:
        residual = f["opening"] + f["external_receipts"] + f["transfer_receipts"] - f["served"] - f["transfer_out"] - f["expired"] - f["closing"]
        worst = max(worst, abs(residual))
    return {"max_row_residual": worst, "holds": worst <= 1e-6, "settlement_residual": row.get("conservation_residual")}


def lane_usage(req: Request, row: dict) -> dict[str, dict[str, Any]]:
    arcs = {a.id: a for a in req.transfers}
    out: dict[str, dict[str, Any]] = {}
    for a in req.transfers:
        events = [e for e in row["transfer_events"] if e["transfer"] == a.id]
        periods = sorted({e["period"] for e in events})
        units = sum(e["quantity"] for e in events)
        out[a.id] = {"sku": a.sku, "origin": a.origin, "destination": a.destination, "units": units, "received": sum(e["received"] for e in events),
                     "dispatches": len(periods), "periods": periods, "capacity": a.capacity,
                     "peak_utilisation": max((sum(e["quantity"] for e in events if e["period"] == t) / a.capacity for t in periods), default=0.) if a.capacity > 0 else None,
                     "variable_cost": units * a.cost_per_unit, "dispatch_cost": len(periods) * a.fixed_cost_per_dispatch,
                     "lead_periods": a.lead_periods, "multiple": a.multiple,
                     # packs are judged on the executable period-zero movement, as settlement does; later
                     # transfers are guidance the evaluator may have reduced to the stock a world holds
                     "pack_legal": all(a.multiple <= 0 or abs(sum(e["quantity"] for e in events if e["period"] == t) / a.multiple
                                                             - round(sum(e["quantity"] for e in events if e["period"] == t) / a.multiple)) < 1e-6 for t in periods if t == 0)}
    # reverse-pair movement of the same SKU inside the horizon
    for a in req.transfers:
        reverse = [b for b in req.transfers if b.sku == a.sku and b.origin == a.destination and b.destination == a.origin]
        out[a.id]["ping_pong_units"] = min(out[a.id]["units"], sum(out[b.id]["units"] for b in reverse)) if reverse else 0.
        out[a.id]["reverse_lanes"] = [b.id for b in reverse]
    del arcs
    return out


def service_table(req: Request, row: dict) -> list[dict[str, Any]]:
    customers = {c.id: c for c in req.customers}
    out = []
    for s in req.services:
        periods = [x for x in row["service_by_period"] if x["service"] == s.id]
        demand = sum(x["demand"] for x in periods)
        served = sum(x["served"] for x in periods)
        achieved = served / demand if demand > 0 else None
        out.append({"service": s.id, "sku": s.sku, "location": s.location, "customer": s.customer, "priority": customers[s.customer].priority,
                    "target": s.target, "demand": demand, "served": served, "unmet": demand - served, "achieved": achieved,
                    "breach": bool(achieved is not None and achieved < s.target - req.service_tolerance),
                    "severe_starvation": bool(achieved is not None and demand > 0 and achieved < SEVERE_STARVATION_FRACTION * s.target),
                    "stockout_periods": sum(1 for x in periods if x["served"] < x["demand"] - 1e-9),
                    "shortage_cost": (demand - served) * (s.selling_price + s.sla_per_unmet)})
    return out


def stranded_at_end(req: Request, row: dict) -> list[dict[str, Any]]:
    """Closing stock that cannot serve anyone: at a location with no demand and no outbound lane."""
    serving = {(s.sku, s.location) for s in req.services}
    outbound = {(a.sku, a.origin) for a in req.transfers if a.approved}
    out = []
    for lot in row["end_stock"]:
        key = (lot["sku"], lot["location"])
        if lot["quantity"] > 1e-9 and key not in serving and key not in outbound:
            out.append({"sku": lot["sku"], "location": lot["location"], "units": lot["quantity"], "reason": "closing stock with no demand here and no outbound lane"})
    return out


def in_transit_after_horizon(req: Request, row: dict) -> list[dict[str, Any]]:
    """Units still moving when the window closes (continuation supply, not stranded stock)."""
    return [{"sku": sku, "location": location, "units": quantity, "kind": kind, "lands": due}
            for sku, location, expiry, due, quantity, kind in row["pending"] if due >= req.horizon and quantity > 1e-9]


def economic_decomposition(req: Request, plan: Solution, row: dict) -> dict[str, Any]:
    """Partition the settlement ledger into node / lane / upstream / network buckets that sum to the
    ledger total. Holding and shortage are read per location from the flows and services; purchase
    spend per destination from the plan; supplier-order economics (order fees, freight tariff,
    receiving) are upstream; financing, working capital, opening / closing assets and the terminal
    continuation are network level."""
    ledger = dict(row["ledger"])
    sources = {s.id: s for s in req.sources}
    terms = {t.id: t for t in req.terms}
    flows = flows_by_pair(row)
    node: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for (sku, location), cell in flows.items():
        node[location]["holding"] += cell["holding_cost"]
    for s in service_table(req, row):
        node[s["location"]]["shortage"] += s["shortage_cost"]
    skus = {s.id: s for s in req.skus}
    for (sku, location), cell in flows.items():
        node[location]["disposal"] += cell["expired"] * skus[sku].disposal_fee
    for (source_id, t), q in plan.purchases.items():
        src = sources[source_id]
        term = terms[src.terms]
        node[src.destination]["purchase"] += q * src.unit_price * term.fx_rate_to_currency
        node[src.destination]["freight_handling"] += q * (src.freight_per_unit + src.handling_per_unit)
    lane: dict[str, dict[str, float]] = {}
    for arc_id, use in lane_usage(req, row).items():
        lane[arc_id] = {"transfer": use["variable_cost"] + use["dispatch_cost"]}
    node_total = sum(sum(v.values()) for v in node.values())
    lane_total = sum(sum(v.values()) for v in lane.values())
    # the ledger's own components, mapped to the buckets above
    mapped = {"holding": "node", "lost_sales_opportunity": "node", "sla": "node", "disposal": "node", "procurement": "node", "freight": "node", "handling": "node",
              "transfer": "lane", "order_fees": "upstream", "ordering": "upstream", "receiving": "upstream",
              "financing": "network", "working_capital": "network", "substitution": "network", "opening_assets": "network", "closing_assets": "network",
              "terminal_continuation": "network"}
    buckets: dict[str, float] = defaultdict(float)
    unmapped = []
    for k, v in ledger.items():
        b = mapped.get(k)
        if b is None:
            unmapped.append(k)
            b = "network"
        buckets[b] += v
    checks = {"node_holding_vs_ledger": abs(sum(v["holding"] for v in node.values()) - ledger.get("holding", 0.)),
              "node_shortage_vs_ledger": abs(sum(v["shortage"] for v in node.values()) - (ledger.get("lost_sales_opportunity", 0.) + ledger.get("sla", 0.))),
              "lane_vs_ledger": abs(lane_total - ledger.get("transfer", 0.)),
              "node_purchase_vs_ledger": abs(sum(v["purchase"] + v["freight_handling"] for v in node.values()) - (ledger.get("procurement", 0.) + ledger.get("freight", 0.) + ledger.get("handling", 0.)))}
    total = sum(ledger.values())
    return {"node": {k: dict(v) for k, v in node.items()}, "lane": lane, "buckets": dict(buckets),
            "node_total_from_flows": node_total, "lane_total_from_flows": lane_total,
            "ledger_total": total, "economic_cost": row["economic_cost"], "buckets_sum": sum(buckets.values()),
            "reconciles": abs(sum(buckets.values()) - total) <= 1e-6 * max(1., abs(total)) and all(v <= 1e-3 * max(1., abs(total)) for k, v in checks.items() if k != "node_purchase_vs_ledger"),
            "checks": checks, "unmapped_ledger_keys": unmapped,
            "note": "node purchase spend is the plan's committed purchases; the ledger's procurement counts only invoices that fall inside the settled window and PO amendments, so that check is informational"}


def network_accounting(req: Request, plan: Solution | None, worlds: list[World], label: str = "plan") -> dict[str, Any]:
    if plan is None or not plan.usable_plan:
        return {"label": label, "usable_worlds": 0, "worlds": len(worlds), "rows": [], "scope": "no usable plan"}
    rows = settle_rows(req, plan, worlds)
    usable = [r for r in rows if r["usable"]]
    weights = [r["weight"] for r in usable]
    if not usable:
        return {"label": label, "usable_worlds": 0, "worlds": len(worlds), "unusable": [{"world": r["world"], "reason": r["reason"]} for r in rows],
                "flows": [], "lanes": {}, "services": [], "network_service": {}, "economics": {}, "actions": {}, "conservation": {"holds_on_every_world": False},
                "stranded_units_at_end": None, "stranded": [], "in_transit_after_horizon_units": None, "scope": "the plan is physically unusable on every world"}
    customers = {c.id: c for c in req.customers}
    # flows (weighted mean over worlds)
    pair_keys = sorted({k for r in usable for k in flows_by_pair(r)})
    flows = []
    for key in pair_keys:
        cells = [flows_by_pair(r).get(key, defaultdict(float)) for r in usable]
        flows.append({"sku": key[0], "location": key[1],
                      **{k: _wmean([c[k] for c in cells], weights) for k in ("opening", "external_receipts", "transfer_receipts", "served", "transfer_out", "expired", "closing", "holding_cost")}})
    conservation = [conservation_check(r) for r in usable]
    # lanes
    lane_ids = [a.id for a in req.transfers]
    lanes: dict[str, dict[str, Any]] = {}
    for arc_id in lane_ids:
        uses: list[dict[str, Any]] = [lane_usage(req, r)[arc_id] for r in usable]
        lanes[arc_id] = {**{k: uses[0][k] for k in ("sku", "origin", "destination", "capacity", "lead_periods", "multiple", "reverse_lanes")},
                         "units": _wmean([u["units"] for u in uses], weights), "received": _wmean([u["received"] for u in uses], weights),
                         "dispatches": _wmean([u["dispatches"] for u in uses], weights),
                         "periods_used": sorted({t for u in uses for t in u["periods"]}),
                         "peak_utilisation": max((u["peak_utilisation"] or 0.) for u in uses) if uses else None,
                         "cost": _wmean([u["variable_cost"] + u["dispatch_cost"] for u in uses], weights),
                         "pack_legal": all(u["pack_legal"] for u in uses),
                         "capacity_respected": all((u["peak_utilisation"] or 0.) <= 1. + 1e-6 for u in uses),
                         "ping_pong_units": _wmean([u["ping_pong_units"] for u in uses], weights)}
    # services
    services: list[dict[str, Any]] = []
    for s in req.services:
        per: list[dict[str, Any]] = [next(x for x in service_table(req, r) if x["service"] == s.id) for r in usable]
        achieved = [x["achieved"] for x in per if x["achieved"] is not None]
        w_ach = [w for x, w in zip(per, weights) if x["achieved"] is not None]
        services.append({"service": s.id, "sku": s.sku, "location": s.location, "customer": s.customer, "priority": customers[s.customer].priority,
                         "target": s.target, "achieved": _wmean(achieved, w_ach), "worst_world": min(achieved) if achieved else None,
                         "breach_share": _wmean([float(x["breach"]) for x in per], weights),
                         "severe_starvation_share": _wmean([float(x["severe_starvation"]) for x in per], weights),
                         "demand": _wmean([x["demand"] for x in per], weights), "unmet": _wmean([x["unmet"] for x in per], weights),
                         "stockout_periods": _wmean([float(x["stockout_periods"]) for x in per], weights),
                         "shortage_cost": _wmean([x["shortage_cost"] for x in per], weights)})
    demand_total = sum(s["demand"] or 0. for s in services)
    served_total = sum((s["demand"] or 0.) - (s["unmet"] or 0.) for s in services)
    prio_total = sum(s["priority"] for s in services if s["achieved"] is not None)
    network_service: dict[str, Any] = {"demand_weighted": served_total / demand_total if demand_total > 0 else None,
                       "priority_weighted": sum(s["priority"] * s["achieved"] for s in services if s["achieved"] is not None) / prio_total if prio_total else None,
                       "breaches": [s["service"] for s in services if (s["breach_share"] or 0.) > .5],
                       "severe_starvation": [s["service"] for s in services if (s["severe_starvation_share"] or 0.) > 0.],
                       "min_location_service": min((s["achieved"] for s in services if s["achieved"] is not None), default=None)}
    stranded = [stranded_at_end(req, r) for r in usable]
    stranded_units = _wmean([sum(x["units"] for x in s) for s in stranded], weights)
    transit_after = _wmean([sum(x["units"] for x in in_transit_after_horizon(req, r)) for r in usable], weights)
    decomposition = [economic_decomposition(req, plan, r) for r in usable]
    economics: dict[str, Any] = {"economic_cost": _wmean([r["economic_cost"] for r in usable], weights),
                 "ledger": {k: _wmean([r["ledger"].get(k, 0.) for r in usable], weights) for k in sorted({k for r in usable for k in r["ledger"]})},
                 "node": {loc: {k: _wmean([d["node"].get(loc, {}).get(k, 0.) for d in decomposition], weights) for k in ("holding", "shortage", "purchase", "freight_handling", "disposal")}
                          for loc in sorted({loc for d in decomposition for loc in d["node"]})},
                 "lane": {arc: {"transfer": _wmean([d["lane"].get(arc, {}).get("transfer", 0.) for d in decomposition], weights)} for arc in lane_ids},
                 "buckets": {b: _wmean([d["buckets"].get(b, 0.) for d in decomposition], weights) for b in ("node", "lane", "upstream", "network")},
                 "reconciles_on_every_world": all(d["reconciles"] for d in decomposition),
                 "worst_check": max((v for d in decomposition for k, v in d["checks"].items() if k != "node_purchase_vs_ledger"), default=0.),
                 "unmapped_ledger_keys": sorted({k for d in decomposition for k in d["unmapped_ledger_keys"]}),
                 "inventory_value_mean": _wmean([sum(x["inventory_value"] for x in r["trace"]) / max(1, len(r["trace"])) for r in usable], weights)}
    actions = {"purchases_period_0": sum(q for (s, t), q in plan.purchases.items() if t == 0), "purchase_lines": sum(1 for (s, t), q in plan.purchases.items() if q > 0),
               "transfers_period_0": sum(q for (a, e, t), q in plan.transfers.items() if t == 0), "transfer_lines": sum(1 for k, q in plan.transfers.items() if q > 0),
               "no_action": not any(q > 0 for (s, t), q in plan.purchases.items() if t == 0) and not any(q > 0 for (a, e, t), q in plan.transfers.items() if t == 0)}
    return {"label": label, "usable_worlds": len(usable), "worlds": len(worlds),
            "unusable": [{"world": r["world"], "reason": r["reason"]} for r in rows if not r["usable"]],
            "flows": flows, "conservation": {"holds_on_every_world": all(c["holds"] for c in conservation), "max_row_residual": max((c["max_row_residual"] for c in conservation), default=0.)},
            "lanes": lanes, "services": services, "network_service": network_service,
            "stranded_units_at_end": stranded_units, "stranded": stranded[0] if stranded else [],
            "in_transit_after_horizon_units": transit_after,
            "economics": economics, "actions": actions,
            "scope": "frozen independent settlement on the given worlds; scenario-weighted means; nothing here is a solver value"}
