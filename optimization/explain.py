"""Commercial explanation of a recommended order, separate from solver provenance.

A buyer does not want duals. They want to know why 480 cases and not 400:
what demand is expected before the next delivery can land, what is on hand
and on the way, how much the supplier usually short-ships, and how big the
safety buffer is. Every number here is computed from the same inputs the
optimizer saw, so the explanation and the recommendation cannot disagree,
and the arithmetic reconciles to the order in the last line.
"""

from __future__ import annotations

import statistics as st
from dataclasses import dataclass, field

from domain.uom import PackSpec


@dataclass
class OrderExplanation:
    product_id: str
    supplier_id: str
    period: int
    order_units: float
    lot_units: float
    lots: int
    expected_demand_over_lead: float
    on_hand: float
    inbound: float
    expected_fill: float
    lead_periods: int
    service_target: float
    safety_buffer: float
    reasons: list = field(default_factory=list)
    provenance: dict = field(default_factory=dict)

    def as_text(self) -> str:
        unit = "unit" if self.lot_units == 1 else f"{self.lot_units:g}-unit lot"
        head = (f"Order {self.order_units:,.0f} units of {self.product_id} from "
                f"{self.supplier_id} in period {self.period}"
                + (f" ({self.lots} x {unit})" if self.lot_units != 1 else ""))
        body = "\n".join(f"  - {r}" for r in self.reasons)
        return f"{head}\n{body}"


def explain_order(product_id: str, supplier_id: str, period: int, order_units: float, *,
                  demand_history: list, on_hand: float, inbound: float,
                  expected_fill: float, lead_periods: int, service_target: float,
                  pack_spec: PackSpec | None = None, solver_status: str = "optimal",
                  objective: float | None = None, gap: float | None = None) -> OrderExplanation:
    spec = pack_spec or PackSpec()
    mu = float(st.mean(demand_history)) if demand_history else 0.0
    sd = float(st.pstdev(demand_history)) if len(demand_history) > 1 else 0.0
    cover = lead_periods + 1
    exp_dem = mu * cover
    net_need = max(exp_dem - on_hand - inbound, 0.0)
    grossed = net_need / max(expected_fill, 0.05)
    buffer = max(order_units - grossed, 0.0)
    lots = spec.lots(order_units) if spec.lot_units > 1 else int(round(order_units))
    reasons = [
        f"expected demand over lead time + review ({cover} periods): {exp_dem:,.0f} "
        f"(mean {mu:,.0f}/period, sd {sd:,.0f})",
        f"usable stock on hand: {on_hand:,.0f}",
        f"confirmed inbound: {inbound:,.0f}",
        f"net requirement: {net_need:,.0f}",
        f"supplier expected fill: {expected_fill:.0%} -> grossed-up requirement {grossed:,.0f}",
        f"target service level: {service_target:.0%}",
        f"safety buffer chosen by the optimizer: {buffer:,.0f}",
    ]
    if spec.lot_units > 1:
        reasons.append(f"pack: {spec.lot_units:g} units per {spec.order_multiple.value}; "
                       f"{lots} whole {spec.order_multiple.value}s")
    if spec.moq_units:
        reasons.append(f"minimum order: {spec.moq_units:g} units")
    reasons.append(f"reconciles: {grossed:,.0f} + {buffer:,.0f} = {grossed + buffer:,.0f} "
                   f"~ {order_units:,.0f} ordered")
    if solver_status != "optimal":
        reasons.append(f"note: solver status '{solver_status}'"
                       + (f", gap {gap:.1%}" if gap is not None else "")
                       + "; treat as a good solution, not a proven optimum")
    return OrderExplanation(
        product_id=product_id, supplier_id=supplier_id, period=period,
        order_units=float(order_units), lot_units=float(spec.lot_units), lots=int(lots),
        expected_demand_over_lead=exp_dem, on_hand=float(on_hand), inbound=float(inbound),
        expected_fill=float(expected_fill), lead_periods=int(lead_periods),
        service_target=float(service_target), safety_buffer=buffer, reasons=reasons,
        provenance={"solver_status": solver_status, "objective": objective, "gap": gap})


def explain_schedule(schedule: dict, *, demand_history: dict, on_hand: dict, inbound: dict,
                     expected_fill: dict, lead_of: dict, supplier_of: dict,
                     service_target: float, pack_specs: dict | None = None,
                     solver_status: str = "optimal", gap: float | None = None) -> list:
    """One explanation per positive order in a (supplier, product, period) schedule."""
    out = []
    for (i, j, t), q in sorted(schedule.items()):
        if q <= 0:
            continue
        out.append(explain_order(
            j, i, t, q, demand_history=demand_history.get(j, []),
            on_hand=on_hand.get(j, 0.0) if t == 0 else 0.0,
            inbound=sum(v for (jj, tt), v in inbound.items() if jj == j and tt >= t),
            expected_fill=expected_fill.get(i, 1.0), lead_periods=int(lead_of.get(i, 1)),
            service_target=service_target,
            pack_spec=(pack_specs or {}).get(j), solver_status=solver_status, gap=gap))
    return out
