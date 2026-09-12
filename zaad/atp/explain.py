"""P5 operator report: what was promised, shipped now, backordered, substituted, unfulfilled,
refused; why A before B (the declared driver, in numbers); remaining and reserved supply; when the
remaining demand can be promised; the assumptions. No aggregate priority score anywhere."""
from __future__ import annotations

from typing import Any

from zaad.atp.contracts import Atp
from zaad.atp.economics import Allocation, Drivers
from zaad.atp.state import SupplyState

PRINCIPLE = ("Scarce available supply goes where the declared economics and contracts say it must; every promise is dated, "
             "physically feasible and reserved once; the operator's own rule is the comparator; approval stays with the operator.")


def _why(a_id: str, b_id: str, da: Drivers, db: Drivers, la, lb) -> str:
    """The first declared driver that separates line a (served first) from line b, in numbers."""
    checks: list[tuple[str, float, float, str]] = [
        ("contractual floor", da.floor, db.floor, "{:.0%}"),
        ("shortage penalty per unit", da.shortage_penalty, db.shortage_penalty, "{:,.2f}"),
        ("late penalty per unit per period", da.late_penalty, db.late_penalty, "{:,.2f}"),
        ("lost margin per unit", da.lost_margin, db.lost_margin, "{:,.2f}"),
        ("service SLA per unmet unit", da.sla, db.sla, "{:,.2f}"),
        ("refusal cost per unit", da.refusal_cost, db.refusal_cost, "{:,.2f}"),
    ]
    for label, va, vb, fmt in checks:
        if abs(va - vb) > 1e-9:
            return f"{a_id} before {b_id}: {label} {fmt.format(va)} against {fmt.format(vb)}"
    if da.strategic != db.strategic:
        return f"{a_id} before {b_id}: declared strategic account ({da.reference or db.reference}) - effective only through its declared economics above"
    if la.requested_period != lb.requested_period:
        return f"{a_id} before {b_id}: requested period {la.requested_period} against {lb.requested_period}"
    return f"{a_id} before {b_id}: economically indifferent; documented tie (order period, then line id) or the declared proportional rule"


def report(req, atp: Atp, state: SupplyState, optimised: Allocation, incumbent: Allocation, priced: dict[str, Any], priced_incumbent: dict[str, Any],
           drv: dict[str, Drivers], verdict: str, value: float | None, material: bool, recommended: Allocation) -> dict[str, Any]:
    spec = atp.spec
    lines = {line.id: (order, line) for order in spec.orders for line in order.lines}
    ships = sorted(recommended.shipments, key=lambda s: (s.promise_period, s.order, s.line, s.lot))
    promised: list[dict[str, Any]] = [{"order": s.order, "line": s.line, "customer": s.customer, "sku": s.sku_requested, "supplied_sku": s.sku_supplied, "substitution": s.substitution,
                 "quantity": round(s.quantity, 3), "promise_period": s.promise_period, "requested_period": s.requested_period, "periods_late": max(0, s.promise_period - s.requested_period),
                 "ship_from": s.ship_from, "lane": s.lane, "lot": s.lot} for s in ships]
    shipped_now = [p for p in promised if p["promise_period"] == 0]
    backordered = [p for p in promised if p["periods_late"] > 0]
    substituted = [p for p in promised if p["substitution"]]
    unfulfilled = [{"order": lines[lid][0].id, "line": lid, "customer": lines[lid][0].customer, "sku": lines[lid][1].sku, "quantity": round(q, 3),
                    "driver": f"lost margin {drv[lid].lost_margin:,.2f} + SLA {drv[lid].sla:,.2f} + shortage penalty {drv[lid].shortage_penalty:,.2f} per unit; no feasible supply at a lower total cost"}
                   for lid, q in sorted(recommended.unmet.items())]
    refused = [{"order": lines[lid][0].id, "line": lid, "customer": lines[lid][0].customer, "sku": lines[lid][1].sku, "quantity": round(q, 3),
                "driver": f"CANCEL_IF_LATE: nothing promisable by period {lines[lid][1].requested_period}; refusal cost {drv[lid].refusal_cost:,.2f} + lost margin {drv[lid].lost_margin:,.2f} per unit"}
               for lid, q in sorted(recommended.refused.items())]
    # why A before B: for every scarce (sku, home location) pair, the served-first line against a line that received less of its request
    order_of = {}
    for o in spec.orders:
        for line in o.lines:
            got = sum(s.quantity for s in recommended.shipments if s.line == line.id)
            order_of[line.id] = got / line.quantity if line.quantity else 1.
    whys: list[str] = []
    ranked = sorted(lines, key=lambda lid: (-order_of[lid], lid))
    for i, a in enumerate(ranked):
        for b in ranked[i + 1:]:
            if order_of[a] > order_of[b] + 1e-9 and lines[a][1].sku == lines[b][1].sku:
                whys.append(_why(a, b, drv[a], drv[b], lines[a][1], lines[b][1]))
    # remaining and reserved supply; when the remaining demand can be promised
    drawn: dict[str, float] = {}
    for s in recommended.shipments:
        drawn[s.lot] = drawn.get(s.lot, 0.) + s.physical_units
    remaining = [{"lot": lot.id, "sku": lot.sku, "location": lot.location, "available_from": lot.available_from, "kind": lot.kind,
                  "physical": round(lot.physical, 3), "reserved_before": round(lot.reserved, 3), "unusable": round(lot.unusable, 3),
                  "promised_now": round(drawn.get(lot.id, 0.), 3), "remaining_unreserved": round(lot.quantity - drawn.get(lot.id, 0.), 3)} for lot in state.lots]
    next_promise: dict[str, Any] = {}
    for lid, q in list(recommended.unmet.items()) + list(recommended.refused.items()):
        order, line = lines[lid]
        arrivals = sorted({lot.available_from for lot in state.lots if lot.sku == line.sku and (lot.quantity - drawn.get(lot.id, 0.)) > 1e-9
                           and lot.available_from > line.requested_period})
        next_promise[lid] = {"quantity": round(q, 3), "earliest_period_with_supply": arrivals[0] if arrivals else None,
                             "note": "outside the order's backorder window or beyond the promise horizon" if arrivals else "no further supply declared within the promise horizon"}
    classes = {c.id: {"provenance": c.provenance, "reference": c.reference, "contractual_service_floor": c.contractual_service_floor, "shortage_penalty_per_unit": c.shortage_penalty_per_unit,
                      "late_penalty_per_unit_period": c.late_penalty_per_unit_period, "refusal_cost_per_unit": c.refusal_cost_per_unit, "lost_margin_per_unit": c.lost_margin_per_unit,
                      "strategic": c.strategic, "tier": c.tier} for c in spec.service_classes}
    return {"version": "zaad.atp.0.1", "principle": PRINCIPLE, "verdict": verdict, "recommended_policy": recommended.policy,
            "incumbent_policy": spec.incumbent_policy, "fairness": spec.fairness,
            "incumbent_cost": priced_incumbent["total"], "optimised_cost": priced["total"], "value_of_allocation": value, "material": material,
            "materiality_cost_fraction": atp.materiality_cost_fraction,
            "engine_status": optimised.status, "incumbent_status": incumbent.status,
            "promised": promised, "shipped_now": shipped_now, "backordered": backordered, "substituted": substituted, "unfulfilled": unfulfilled, "refused": refused,
            "why": whys, "service_classes": classes, "remaining_supply": remaining, "next_promise": next_promise,
            "ledger": priced["ledger"], "incumbent_ledger": priced_incumbent["ledger"], "unit_states": priced["units"],
            "assumptions": list(state.assumptions) + list(recommended.notes),
            "approval_required": True, "executable_promise": False,
            "engineering": {"optimised": optimised.engine, "incumbent": incumbent.engine, "solve_seconds": optimised.solve_seconds,
                            "lots": len(state.lots), "lanes": len(state.lanes), "orders": len(spec.orders), "lines": len(lines)}}
