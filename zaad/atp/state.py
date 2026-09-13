"""P5 supply state: the allocatable-supply envelope built from the frozen request records.

Envelope per (SKU, location, period), in the order the shared-core integration contract fixes:

    physical                 Stock.quantity
    -> physically usable     minus Stock.damaged and Stock.quarantined
    -> sellable              minus cohorts the sector physics declare unsellable at the promise period
                             (`Physics.sellable`) and locations the SKU's storage state may not occupy
    -> unreserved            minus Stock.reserved, the frozen contract's ONLY hard reservation (the
                             frozen model and settlement plan on `Stock.usable`, which excludes it)
    -> hard commitments      none exist in the frozen contract: P0 protection is a service-level
                             construct inside the planner's own candidate solves (quantile floors,
                             protection profile), never a reservation of units, so nothing is
                             subtracted here and the planner path reports an overlay instead
    = allocatable ATP        on-hand lots P5 may promise

Future availability is split by the frozen semantics of the record it comes from:

    FIRM        `InboundTransfer` (accepted quantity in flight, dated `due_in`): the frozen model fixes it
                as a variable with lower = upper = accepted_quantity and the settlement lands it at
                `due_in` unconditionally -> promisable at or after arrival when `include_inbound`;
    NON-FIRM    `OpenPO.expected_accepted_remaining`: the frozen worlds draw its fill and lead -> never
                promised; reported as non-firm availability (capable only if received).

No confidence weighting exists: the contract refuses `inbound_confidence` other than 1 (fail closed).
Nothing here decides; nothing here increases supply (no purchase, no transfer is created).
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any

from zaad.atp.contracts import Atp

INF = 10 ** 6
ON_HAND = "on_hand"
FIRM_INBOUND = "firm_inbound"
NON_FIRM_INBOUND = "non_firm_inbound"


@dataclass(frozen=True)
class Lot:
    """A dated, located quantity of usable, unreserved supply P5 may promise."""
    id: str
    sku: str
    location: str
    available_from: int          # first period the units can be shipped
    expiry: int                  # first period the units are no longer sellable (INF = never)
    quantity: float              # allocatable units (usable, unreserved)
    kind: str                    # on_hand | firm_inbound
    physical: float = 0.         # the physical quantity the lot came from (reporting)
    reserved: float = 0.         # Stock.reserved excluded from `quantity`
    unusable: float = 0.         # damaged + quarantined excluded from `quantity`
    tier: str = ON_HAND          # on_hand | firm_inbound
    record: str = ""             # the frozen record the lot came from


@dataclass(frozen=True)
class NonFirm:
    """Supply P5 knows about but may not promise: an open purchase order's expected remaining receipt."""
    id: str
    sku: str
    location: str
    expected_period: int
    quantity: float
    record: str
    reason: str


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
    non_firm: list[NonFirm] = field(default_factory=list)
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
        """The envelope per (SKU, location, period): physical -> usable -> sellable -> unreserved = allocatable
        ATP (on hand), then firm inbound by arrival, then non-firm (never promisable) by expected arrival."""
        keys = sorted({(lot.sku, lot.location) for lot in self.lots} | {(n.sku, n.location) for n in self.non_firm})
        rows = []
        for sku, location in keys:
            for t in range(self.horizon + 1):
                on_hand = [lot for lot in self.lots if lot.sku == sku and lot.location == location and lot.tier == ON_HAND]
                firm = [lot for lot in self.lots if lot.sku == sku and lot.location == location and lot.tier == FIRM_INBOUND and lot.available_from <= t]
                physical = sum(lot.physical for lot in on_hand)
                usable = sum(lot.physical - lot.unusable for lot in on_hand)
                sellable = sum(lot.physical - lot.unusable for lot in on_hand if self.sellable(lot, t))
                allocatable = sum(lot.quantity for lot in on_hand if self.sellable(lot, t))
                rows.append({"sku": sku, "location": location, "period": t,
                             "physical": round(physical, 3), "usable": round(usable, 3), "sellable": round(sellable, 3),
                             "reserved": round(sum(lot.reserved for lot in on_hand), 3),
                             "allocatable_atp": round(allocatable, 3),
                             "firm_inbound_by_period": round(sum(lot.quantity for lot in firm), 3),
                             "non_firm_by_period": round(sum(n.quantity for n in self.non_firm if n.sku == sku and n.location == location and n.expected_period <= t), 3)})
        return rows


def _lot_from_stock(stock) -> Lot:
    usable = max(0., stock.quantity - stock.damaged - stock.quarantined)
    unreserved = max(0., usable - stock.reserved)
    return Lot(id=f"stock:{stock.id}", sku=stock.sku, location=stock.location, available_from=0,
               expiry=int(stock.expires_in) if stock.expires_in < INF else INF, quantity=unreserved, kind=ON_HAND,
               physical=stock.quantity, reserved=min(stock.reserved, usable), unusable=stock.quantity - usable, tier=ON_HAND, record=f"Stock:{stock.id}")


def build_state(req, atp: Atp) -> SupplyState:
    """The allocatable-supply envelope from the frozen request (module docstring)."""
    spec = atp.spec
    from zaad.sectors.contracts import resolve as resolve_physics
    physics = resolve_physics(req)
    state = SupplyState(horizon=spec.promise_horizon, physics=physics)
    for stock in req.stock:
        state.lots.append(_lot_from_stock(stock))
    state.assumptions.append("allocatable supply = physical - damaged - quarantined - sector-unsellable - Stock.reserved (the frozen contract's only hard reservation); "
                             "P0 protection is a service-level construct inside the planner and reserves no units")
    # non-firm availability is always classified, never promised
    sources = {s.id: s for s in req.sources}
    for po in req.pipeline:
        src = sources.get(po.source)
        if src is None or po.expected_accepted_remaining <= 0:
            continue
        days = (po.current_eta - req.as_of).days
        due = max(0, math.ceil(days / max(1, req.period_days)))
        state.non_firm.append(NonFirm(id=f"po:{po.id}", sku=src.sku, location=src.destination, expected_period=due, quantity=float(po.expected_accepted_remaining),
                                      record=f"OpenPO:{po.id}", reason="open purchase order: fill and arrival are uncertain in the frozen semantics (drawn per world); never promised"))
    if spec.include_inbound:
        for inbound in req.inbound_transfers:
            state.lots.append(Lot(id=f"transfer:{inbound.id}", sku=inbound.sku, location=inbound.destination, available_from=int(inbound.due_in),
                                  expiry=int(inbound.expires_in) if inbound.expires_in < INF else INF, quantity=float(inbound.accepted_quantity), kind=FIRM_INBOUND,
                                  physical=float(inbound.accepted_quantity), tier=FIRM_INBOUND, record=f"InboundTransfer:{inbound.id}"))
        state.assumptions.append("firm inbound (accepted in-flight transfers, dated) is promisable at or after its arrival period; open purchase orders are non-firm and never promised")
    else:
        state.assumptions.append("available-to-promise from on-hand stock only (firm inbound not counted)")
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
