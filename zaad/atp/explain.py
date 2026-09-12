"""P5 operator report: what was promised, shipped now, backordered, substituted, unfulfilled,
refused; why A before B (the declared driver, in numbers); the allocatable-supply envelope, the
non-firm availability that was NOT promised, the proposed reservations (traceable to customer,
order, line, SKU, lot, location, promise period), the supply that was blocked and why (no implicit
transfer); the assumptions. No aggregate priority score anywhere."""
from __future__ import annotations

from typing import Any

from zaad.atp.allocation import blocked_supply
from zaad.atp.contracts import Atp
from zaad.atp.economics import ALTERNATIVE, LEDGER_KEYS, OWNER, Allocation, Drivers
from zaad.atp.state import SupplyState

VERSION = "zaad.atp.0.2"
PRINCIPLE = ("Scarce allocatable supply goes where the declared economics and contracts say it must; every promise is dated, "
             "physically feasible and reserved once; firm supply only; the operator's own rule is the comparator; approval stays with the operator.")
RESERVATION_STATUS = "PROPOSED"
RESERVATION_RELEASE = ("proposed by this report only: nothing is committed or persisted; once the operator approves, the units are recorded as "
                       "Stock.reserved on the vault stock record (the frozen contract's hard reservation) and released by the operator's own order management")


def _basis(d: Drivers) -> str:
    return {"declared_line_margin": "declared line margin", "declared_class_margin": "declared class margin", "frozen_contribution": "selling price less asset value, the frozen allocation-ranking basis"}[d.lost_basis]


def _why(a_id: str, b_id: str, da: Drivers, db: Drivers, la, lb) -> str:
    """The first declared driver that separates line a (served first) from line b, in numbers."""
    checks: list[tuple[str, float, float, str]] = [
        ("contractual floor", da.floor, db.floor, "{:.0%}"),
        ("shortage penalty per unit", da.shortage_penalty, db.shortage_penalty, "{:,.2f}"),
        ("late penalty per unit per period", da.late_penalty, db.late_penalty, "{:,.2f}"),
        (f"lost contribution per unit ({_basis(da)})", da.lost_margin, db.lost_margin, "{:,.2f}"),
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


def reservations(recommended: Allocation, spec) -> list[dict[str, Any]]:
    """One proposed reservation per shipment, traceable to customer, order, line, SKU, quantity, lot, location and promise period."""
    out = []
    for i, s in enumerate(sorted(recommended.shipments, key=lambda s: (s.promise_period, s.order, s.line, s.lot, s.lane or "")), start=1):
        out.append({"reservation_id": f"R{i:04d}:{s.order}:{s.line}:{s.lot}:{s.promise_period}", "customer": s.customer, "order": s.order, "line": s.line,
                    "sku_requested": s.sku_requested, "sku_supplied": s.sku_supplied, "substitution": s.substitution, "quantity": round(s.quantity, 3),
                    "physical_units": round(s.physical_units, 3), "lot": s.lot, "location": s.ship_from, "lane": s.lane, "fulfilment": s.fulfilment,
                    "promise_period": s.promise_period, "requested_period": s.requested_period, "status": RESERVATION_STATUS})
    return out


def report(req, atp: Atp, state: SupplyState, optimised: Allocation, incumbent: Allocation, priced: dict[str, Any], priced_incumbent: dict[str, Any],
           drv: dict[str, Drivers], verdict: str, value: float | None, material: bool, recommended: Allocation) -> dict[str, Any]:
    spec = atp.spec
    lines = {line.id: (order, line) for order in spec.orders for line in order.lines}
    ships = sorted(recommended.shipments, key=lambda s: (s.promise_period, s.order, s.line, s.lot))
    promised: list[dict[str, Any]] = [{"order": s.order, "line": s.line, "customer": s.customer, "sku": s.sku_requested, "supplied_sku": s.sku_supplied, "substitution": s.substitution,
                 "quantity": round(s.quantity, 3), "promise_period": s.promise_period, "requested_period": s.requested_period, "periods_late": max(0, s.promise_period - s.requested_period),
                 "ship_from": s.ship_from, "lane": s.lane, "fulfilment": s.fulfilment, "lot": s.lot} for s in ships]
    shipped_now = [p for p in promised if p["promise_period"] == 0]
    backordered = [p for p in promised if p["periods_late"] > 0]
    substituted = [p for p in promised if p["substitution"]]
    alternative = [p for p in promised if p["fulfilment"] == ALTERNATIVE]
    unfulfilled = [{"order": lines[lid][0].id, "line": lid, "customer": lines[lid][0].customer, "sku": lines[lid][1].sku, "quantity": round(q, 3),
                    "driver": f"lost contribution {drv[lid].lost_margin:,.2f} ({_basis(drv[lid])}) + SLA {drv[lid].sla:,.2f} + shortage penalty {drv[lid].shortage_penalty:,.2f} per unit; no feasible supply at a lower total cost"}
                   for lid, q in sorted(recommended.unmet.items())]
    refused = [{"order": lines[lid][0].id, "line": lid, "customer": lines[lid][0].customer, "sku": lines[lid][1].sku, "quantity": round(q, 3),
                "driver": f"CANCEL_IF_LATE: nothing promisable by period {lines[lid][1].requested_period}; refusal cost {drv[lid].refusal_cost:,.2f} + lost contribution {drv[lid].lost_margin:,.2f} per unit"}
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
    remaining: list[dict[str, Any]] = [{"lot": lot.id, "record": lot.record, "sku": lot.sku, "location": lot.location, "available_from": lot.available_from, "tier": lot.tier,
                  "physical": round(lot.physical, 3), "reserved_before": round(lot.reserved, 3), "unusable": round(lot.unusable, 3),
                  "promised_now": round(drawn.get(lot.id, 0.), 3), "remaining_unreserved": round(lot.quantity - drawn.get(lot.id, 0.), 3)} for lot in state.lots]
    non_firm = [{"id": n.id, "record": n.record, "sku": n.sku, "location": n.location, "expected_period": n.expected_period, "quantity": round(n.quantity, 3),
                 "promised": 0., "reason": n.reason} for n in state.non_firm]
    next_promise: dict[str, Any] = {}
    for lid, q in list(recommended.unmet.items()) + list(recommended.refused.items()):
        order, line = lines[lid]
        arrivals = sorted({lot.available_from for lot in state.lots if lot.sku == line.sku and (lot.quantity - drawn.get(lot.id, 0.)) > 1e-9
                           and lot.available_from > line.requested_period})
        capable = sorted({n.expected_period for n in state.non_firm if n.sku == line.sku})
        next_promise[lid] = {"quantity": round(q, 3), "earliest_period_with_firm_supply": arrivals[0] if arrivals else None,
                             "earliest_period_with_non_firm_supply": capable[0] if capable else None,
                             "note": ("outside the order's backorder window or beyond the promise horizon" if arrivals
                                      else ("only non-firm supply (open purchase orders) is expected; it is never promised" if capable else "no further firm supply declared within the promise horizon"))}
    classes = {c.id: {"provenance": c.provenance, "reference": c.reference, "contractual_service_floor": c.contractual_service_floor, "shortage_penalty_per_unit": c.shortage_penalty_per_unit, "shortage_penalty_basis": c.shortage_penalty_basis,
                      "late_penalty_per_unit_period": c.late_penalty_per_unit_period, "refusal_cost_per_unit": c.refusal_cost_per_unit, "lost_margin_per_unit": c.lost_margin_per_unit,
                      "strategic": c.strategic, "tier": c.tier} for c in spec.service_classes}
    drivers_out = {lid: {"lost_contribution_per_unit": d.lost_margin, "lost_basis": d.lost_basis, "gross_selling_price": d.gross_selling_price,
                         "sla_per_unmet": d.sla, "sla_service_declared": d.sla_service, "sla_basis": d.sla_basis,
                         "sla_replaced_per_unit": (d.sla_service if d.sla_basis == "REPLACES_SERVICE_SLA" else 0.),
                         "shortage_penalty_per_unit": d.shortage_penalty,
                         "late_penalty_per_unit_period": d.late_penalty, "refusal_cost_per_unit": d.refusal_cost, "contractual_floor": d.floor, "provenance": d.provenance}
                   for lid, d in drv.items()}
    return {"version": VERSION, "principle": PRINCIPLE, "verdict": verdict, "recommended_policy": recommended.policy,
            "incumbent_policy": spec.incumbent_policy, "fairness": spec.fairness,
            "incumbent_cost": priced_incumbent["total"], "optimised_cost": priced["total"], "value_of_allocation": value, "material": material,
            "materiality_cost_fraction": atp.materiality_cost_fraction,
            "engine_status": optimised.status, "incumbent_status": incumbent.status,
            "promised": promised, "shipped_now": shipped_now, "backordered": backordered, "substituted": substituted, "unfulfilled": unfulfilled, "refused": refused,
            "fulfilment": {"direct_units": round(sum(p["quantity"] for p in promised if p["fulfilment"] != ALTERNATIVE), 3),
                           "alternative_ship_from_units": round(sum(p["quantity"] for p in alternative), 3),
                           "alternative_ship_from": alternative, "p2_transfers_created": 0,
                           "note": "an alternative ship-from is priced with the approved lane's unit cost, lead and capacity; P5 creates no inventory transfer (P2 owns movement)"},
            "reservations": reservations(recommended, spec), "reservation_release": RESERVATION_RELEASE,
            "why": whys, "service_classes": classes, "drivers": drivers_out,
            "supply_envelope": state.ladder(), "remaining_supply": remaining, "non_firm_availability": non_firm,
            "blocked_supply": blocked_supply(req, atp, state), "next_promise": next_promise,
            "ledger": priced["ledger"], "incumbent_ledger": priced_incumbent["ledger"], "ledger_owner": {k: OWNER[k] for k in LEDGER_KEYS}, "unit_states": priced["units"],
            "gross_lost_sales_opportunity": priced.get("gross_lost_sales_opportunity"), "incumbent_gross_lost_sales_opportunity": priced_incumbent.get("gross_lost_sales_opportunity"),
            "lost_sale_basis_note": "lost contribution (selling price less asset value, the frozen allocation-ranking basis, or a declared margin) enters the objective; "
                                    "the gross selling price (the settlement's lost_sales_opportunity convention) is information only",
            "retained_supply_units": round(sum(r["remaining_unreserved"] for r in remaining if r["tier"] == "on_hand"), 3),
            "assumptions": list(state.assumptions) + list(recommended.notes),
            "approval_required": True, "executable_promise": False,
            "engineering": {"optimised": optimised.engine, "incumbent": incumbent.engine, "solve_seconds": optimised.solve_seconds,
                            "lots": len(state.lots), "non_firm": len(state.non_firm), "lanes": len(state.lanes), "orders": len(spec.orders), "lines": len(lines)}}
