"""P5 supply state: the ATP ladder built from the frozen request records.

physical -> usable -> unreserved -> ATP -> CTP, per (SKU, location, period), as a list of dated
supply lots the allocation engine and the incumbent policies consume. Nothing here decides; nothing
here increases supply (no purchase, no transfer is created): P5 reads what P0-P3 and the vault
declare and prices alternatives with P2's lane data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any

from zaad.atp.contracts import Atp

INF = 10 ** 6


@dataclass(frozen=True)
class Lot:
    """A dated, located quantity of usable, unreserved supply."""
    id: str
    sku: str
    location: str
    available_from: int          # first period the units can be shipped
    expiry: int                  # first period the units are no longer sellable (INF = never)
    quantity: float              # usable, unreserved units (already confidence-weighted for inbound)
    kind: str                    # on_hand | inbound_transfer | inbound_po
    confidence: float = 1.
    physical: float = 0.         # the physical quantity the lot came from (reporting)
    reserved: float = 0.
    unusable: float = 0.         # damaged + quarantined + unsellable


@dataclass(frozen=True)
class Lane:
    """An approved lane P5 may PRICE (never move stock on): origin -> destination, lead, unit cost, capacity per period."""
    id: str
    sku: str
    origin: str
    destination: str
    lead: int
    cost_per_unit: float
    capacity: float
    loss_fraction: float


@dataclass
class SupplyState:
    horizon: int
    lots: list[Lot] = field(default_factory=list)
    lanes: list[Lane] = field(default_factory=list)
    physics: Any = None
    assumptions: list[str] = field(default_factory=list)

    def sellable(self, lot: Lot, t: int) -> bool:
        """Can a unit of `lot` be sold at period t (life and, under sector physics, the sector's rule)?"""
        if t < lot.available_from or t >= lot.expiry:
            return False
        if self.physics is not None and not self.physics.sellable(lot.sku, lot.expiry, t):
            return False
        return True

    def location_ok(self, sku: str, location: str) -> bool:
        return self.physics is None or self.physics.location_ok(sku, location)

    def lane_ok(self, lane: Lane) -> bool:
        return self.physics is None or self.physics.lane_ok(lane.sku, lane.id)

    def ladder(self) -> list[dict[str, Any]]:
        """Per (SKU, location, period): physical, usable, unreserved supply available by then (cumulative)."""
        keys = sorted({(lot.sku, lot.location) for lot in self.lots})
        rows = []
        for sku, location in keys:
            for t in range(self.horizon + 1):
                lots = [lot for lot in self.lots if lot.sku == sku and lot.location == location and lot.available_from <= t]
                rows.append({"sku": sku, "location": location, "period": t,
                             "physical": round(sum(lot.physical for lot in lots), 3),
                             "usable": round(sum(lot.physical - lot.unusable for lot in lots), 3),
                             "unreserved": round(sum(lot.quantity for lot in lots if lot.kind == "on_hand"), 3),
                             "capable_with_inbound": round(sum(lot.quantity for lot in lots), 3),
                             "sellable_now": round(sum(lot.quantity for lot in lots if self.sellable(lot, t)), 3)})
        return rows


def build_state(req, atp: Atp) -> SupplyState:
    """The supply ladder from the frozen request: on-hand stock (usable, unreserved, sellable),
    in-flight transfers by arrival period, open purchase orders by expected arrival period at the
    declared confidence (when `include_inbound`), and the approved lanes for pricing alternatives."""
    spec = atp.spec
    physics = None
    from zaad.sectors.contracts import resolve as resolve_physics
    physics = resolve_physics(req)
    state = SupplyState(horizon=spec.promise_horizon, physics=physics)
    for stock in req.stock:
        usable = max(0., stock.quantity - stock.damaged - stock.quarantined)
        unreserved = max(0., usable - stock.reserved)
        state.lots.append(Lot(id=f"stock:{stock.id}", sku=stock.sku, location=stock.location, available_from=0,
                              expiry=int(stock.expires_in) if stock.expires_in < INF else INF, quantity=unreserved, kind="on_hand",
                              physical=stock.quantity, reserved=min(stock.reserved, usable), unusable=stock.quantity - usable))
    if spec.include_inbound:
        for inbound in req.inbound_transfers:
            q = inbound.accepted_quantity * spec.inbound_confidence
            state.lots.append(Lot(id=f"transfer:{inbound.id}", sku=inbound.sku, location=inbound.destination, available_from=int(inbound.due_in),
                                  expiry=int(inbound.expires_in) if inbound.expires_in < INF else INF, quantity=q, kind="inbound_transfer",
                                  confidence=spec.inbound_confidence, physical=inbound.accepted_quantity))
        sources = {s.id: s for s in req.sources}
        for po in req.pipeline:
            src = sources.get(po.source)
            if src is None or po.expected_accepted_remaining <= 0:
                continue
            days = (po.current_eta - req.as_of).days
            due = max(0, math.ceil(days / max(1, req.period_days)))
            life = INF
            if physics is not None:
                try:
                    life = int(physics.receipt_life(src.sku, src.id))
                except Exception:  # noqa: BLE001
                    life = INF
            state.lots.append(Lot(id=f"po:{po.id}", sku=src.sku, location=src.destination, available_from=due,
                                  expiry=(due + life) if life < INF else INF, quantity=po.expected_accepted_remaining * spec.inbound_confidence,
                                  kind="inbound_po", confidence=spec.inbound_confidence, physical=po.expected_accepted_remaining))
        state.assumptions.append(f"inbound supply counted at {spec.inbound_confidence:.0%} of the expected remaining quantity by its expected arrival period (declared assumption)")
    else:
        state.assumptions.append("available-to-promise from on-hand stock only (inbound not counted)")
    if spec.cross_location:
        for arc in req.transfers:
            if not arc.approved:
                continue
            lane = Lane(id=arc.id, sku=arc.sku, origin=arc.origin, destination=arc.destination, lead=int(arc.lead_periods),
                        cost_per_unit=float(arc.cost_per_unit), capacity=float(arc.capacity), loss_fraction=float(arc.loss_fraction))
            if state.lane_ok(lane):
                state.lanes.append(lane)
        state.assumptions.append("an eligible alternative ship-from location is priced with the approved lane's unit cost, lead and capacity; P5 emits no transfer")
    if physics is not None:
        state.assumptions.append("sector physics: only cohorts sellable at the promise period and locations / lanes eligible for the SKU's state are promisable")
    return state
