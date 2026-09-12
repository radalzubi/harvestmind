"""P5 pre-registered fixture matrix A-V (docs/zaad_full/p5/P5_PREREGISTRATION.md).

Every fixture is a frozen `Request` (built from the P2 / sector bases of the recourse fixtures so
customers, services, stock, lanes and physics are the released records) plus a P5 declaration.
Definitions are frozen at registration; corrections are logged in P5_DEV_LOG.md.
"""
from __future__ import annotations

from typing import Any

from zaad.atp.contracts import CustomerOrder, PromiseLine, ServiceClass
from zaad.full.contracts import Customer, Request, Service, Stock, Substitute
from zaad.recourse.fixtures import p2_base, sector_base

SKU = "A"


def base() -> Request:
    return p2_base()


def _known(req):
    return req.as_of


def customer(req, cid: str, priority: float = 1., channel: str = "retail") -> Customer:
    return Customer(known_at=_known(req), id=cid, channel=channel, priority=priority)


def service(req, sid: str, cid: str, sku: str = SKU, location: str = "north", selling: float = 10., sla: float = 2.5) -> Service:
    return Service(known_at=_known(req), id=sid, sku=sku, location=location, customer=cid, target=.95, selling_price=selling, sla_per_unmet=sla)


def stock(req, sid: str, sku: str, location: str, quantity: float, reserved: float = 0., expires_in: int = 52, damaged: float = 0., quarantined: float = 0.) -> Stock:
    return Stock(known_at=_known(req), id=sid, sku=sku, location=location, quantity=quantity, reserved=reserved, damaged=damaged, quarantined=quarantined,
                 expires_in=expires_in, age_periods=0)


def inbound(req, iid: str, sku: str, destination: str, due_in: int, quantity: float, expires_in: int = 52):
    from zaad.full.contracts import InboundTransfer
    return InboundTransfer(known_at=_known(req), id=iid, sku=sku, origin="central", destination=destination, accepted_quantity=quantity, due_in=due_in, expires_in=expires_in)


def with_state(req: Request, *, stock_rows=None, customers=None, services=None, substitutions=None, inbound_rows=None, locations=None, transfers=None, skus=None) -> Request:
    d = req.model_dump()
    if stock_rows is not None:
        d["stock"] = [s.model_dump() for s in stock_rows]
    # customers and services are ADDED to the base records (the base's demand history references its services)
    if customers is not None:
        have = {c["id"] for c in d["customers"]}
        d["customers"] = list(d["customers"]) + [c.model_dump() for c in customers if c.id not in have]
    if services is not None:
        have = {s["id"] for s in d["services"]}
        d["services"] = list(d["services"]) + [s.model_dump() for s in services if s.id not in have]
    if substitutions is not None:
        d["substitutions"] = [s.model_dump() for s in substitutions]
    if inbound_rows is not None:
        d["inbound_transfers"] = [i.model_dump() for i in inbound_rows]
    if locations is not None:
        d["locations"] = [loc.model_dump() for loc in locations]
    if transfers is not None:
        d["transfers"] = [t.model_dump() for t in transfers]
    if skus is not None:
        d["skus"] = [k.model_dump() for k in skus]
    return Request.model_validate(d)


def cls(cid: str, **kw) -> ServiceClass:
    return ServiceClass(id=cid, **kw)


def line(lid: str, quantity: float, requested: int = 0, sku: str = SKU, **kw) -> PromiseLine:
    return PromiseLine(id=lid, sku=sku, quantity=quantity, requested_period=requested, **kw)


def order(oid: str, cid: str, sclass: str, lines, **kw) -> CustomerOrder:
    return CustomerOrder(id=oid, customer=cid, service_class=sclass, lines=tuple(lines), **kw)


def with_atp(req: Request, orders, classes, **spec) -> Request:
    d = req.model_dump()
    d["atp"] = {"enabled": True, "orders": [o.model_dump() for o in orders], "service_classes": [c.model_dump() for c in classes], **spec}
    return Request.model_validate(d)


# ---- the standard two-customer north scene ------------------------------------------------------
def scene(req: Request, north_stock: float, customers_n: int = 2, **stock_kw) -> Request:
    """Customers c1..cn on SKU A at north with the frozen economics (price 10, SLA 2.5)."""
    cs = [customer(req, f"c{i}", priority=1.) for i in range(1, customers_n + 1)]
    ss = [service(req, f"s{i}", f"c{i}") for i in range(1, customers_n + 1)]
    st = [stock(req, "north_stock", SKU, "north", north_stock, **stock_kw)]
    return with_state(req, stock_rows=st, customers=cs, services=ss, inbound_rows=[])


STD = [cls("std")]


def _A():
    req = scene(base(), 100.)
    return with_atp(req, [order("o1", "c1", "std", [line("l1", 40.)]), order("o2", "c2", "std", [line("l2", 30.)])], STD)


def _B():
    req = scene(base(), 60.)
    classes = [cls("hi", shortage_penalty_per_unit=20.), cls("lo")]
    orders = [order("oX", "c1", "hi", [line("lX", 50.)]), order("oY", "c2", "lo", [line("lY", 50.)], order_period=-1)]
    return with_atp(req, orders, classes, incumbent_policy="FCFS_ORDER_DATE")


def _C():
    req = scene(base(), 50.)
    classes = [cls("X", shortage_penalty_per_unit=40., lost_margin_per_unit=5.), cls("Y", lost_margin_per_unit=30.)]
    orders = [order("oX", "c1", "X", [line("lX", 50.)]), order("oY", "c2", "Y", [line("lY", 50.)])]
    return with_atp(req, orders, classes, incumbent_policy="PROPORTIONAL")


def _D():
    req = scene(base(), 60., customers_n=3)
    orders = [order(f"o{i}", f"c{i}", "std", [line(f"l{i}", 40.)]) for i in (1, 2, 3)]
    return with_atp(req, orders, STD, fairness="PROPORTIONAL_WHEN_INDIFFERENT")


def _E():
    req = scene(base(), 60., customers_n=3)
    orders = [order("o1", "c1", "std", [line("l1", 40.)], partial_fulfillment_allowed=False),
              order("o2", "c2", "std", [line("l2", 40.)], partial_fulfillment_allowed=False),
              order("o3", "c3", "std", [line("l3", 40.)])]
    return with_atp(req, orders, STD)


def _F():
    req = scene(base(), 50.)
    req = with_state(req, inbound_rows=[inbound(req, "in1", SKU, "north", 2, 50.)])
    classes = [cls("std", late_penalty_per_unit_period=1.)]
    orders = [order("o1", "c1", "std", [line("l1", 100.)], backorder_allowed=True, max_backorder_periods=3)]
    return with_atp(req, orders, classes, include_inbound=True, inbound_confidence=1.)


def _G():
    req = scene(base(), 50.)
    req = with_state(req, inbound_rows=[inbound(req, "in1", SKU, "north", 2, 50.)])
    orders = [order("o1", "c1", "std", [line("l1", 100.)])]
    return with_atp(req, orders, STD, include_inbound=True, inbound_confidence=1.)


def _H():
    req = scene(base(), 40.)
    req = with_state(req, inbound_rows=[inbound(req, "in1", SKU, "north", 3, 40.)])
    orders = [order("oa", "c1", "std", [line("la", 40., requested=0)]), order("ob", "c2", "std", [line("lb", 40., requested=3)])]
    return with_atp(req, orders, STD, include_inbound=True, inbound_confidence=1.)


def _I():
    req = scene(base(), 0.)
    req = with_state(req, inbound_rows=[inbound(req, "in1", SKU, "north", 1, 60.)])
    orders = [order("o1", "c1", "std", [line("l1", 60., requested=2)])]
    return with_atp(req, orders, STD, include_inbound=True, inbound_confidence=1.)


def _J():
    req = scene(base(), 0.)
    req = with_state(req, inbound_rows=[inbound(req, "in1", SKU, "north", 4, 60.)])
    orders = [order("o1", "c1", "std", [line("l1", 60., requested=2)])]
    return with_atp(req, orders, STD, include_inbound=True, inbound_confidence=1.)


def _K():
    req = base()
    cs = [customer(req, "c1")]
    ss = [service(req, "s1", "c1")]
    st = [stock(req, "north_stock", SKU, "north", 30.), stock(req, "central_stock", SKU, "central", 200.)]
    req = with_state(req, stock_rows=st, customers=cs, services=ss, inbound_rows=[])
    orders = [order("o1", "c1", "std", [line("l1", 80., requested=1)])]
    return with_atp(req, orders, STD, cross_location=True)


def _L():
    req = base()
    cs = [customer(req, "c1")]
    ss = [service(req, "s1", "c1")]
    st = [stock(req, "north_stock", SKU, "north", 30.), stock(req, "central_stock", SKU, "central", 200.)]
    req = with_state(req, stock_rows=st, customers=cs, services=ss, inbound_rows=[])
    orders = [order("o1", "c1", "std", [line("l1", 80., requested=0)]),]
    return with_atp(req, orders, STD, cross_location=True)


def _L2():
    req = base()
    cs = [customer(req, "c1")]
    ss = [service(req, "s1", "c1")]
    st = [stock(req, "north_stock", SKU, "north", 30.), stock(req, "central_stock", SKU, "central", 200.)]
    req = with_state(req, stock_rows=st, customers=cs, services=ss, inbound_rows=[])
    orders = [order("o1", "c1", "std", [line("l1", 80., requested=0)], backorder_allowed=True, max_backorder_periods=2)]
    return with_atp(req, orders, [cls("std", late_penalty_per_unit_period=.5)], cross_location=True)


def _M():
    req = sector_base("P2_near_expiry_inventory")
    cs = [customer(req, "c1")]
    ss = [service(req, "s1", "c1")]
    st = [stock(req, "north_lot", SKU, "north", 150., expires_in=2), stock(req, "central_lot", SKU, "central", 300., expires_in=6)]
    req = with_state(req, stock_rows=st, customers=cs, services=ss, inbound_rows=[])
    orders = [order("o1", "c1", "std", [line("l1", 100., requested=2)])]
    return with_atp(req, orders, STD, cross_location=True)


def _N():
    """Cold chain: the frozen contract refuses chilled stock at a non-chilled location outright (adversarial
    evidence), so the fixture keeps every location chilled-capable and declares the central -> north lane
    AMBIENT only: the chilled SKU may not travel on it, so central supply can never reach north."""
    req = sector_base("M1_chilled_shelf_life")
    cs = [customer(req, "c1")]
    ss = [service(req, "s1", "c1")]
    st = [stock(req, "north_lot", SKU, "north", 40., expires_in=3), stock(req, "central_lot", SKU, "central", 200., expires_in=3)]
    lanes = [a if a.id != "lane_north" else a.model_copy(update={"storage_states": ("AMBIENT",)}) for a in req.transfers]
    req = with_state(req, stock_rows=st, customers=cs, services=ss, inbound_rows=[], transfers=lanes)
    orders = [order("o1", "c1", "std", [line("l1", 100., requested=1)], backorder_allowed=True, max_backorder_periods=1)]
    return with_atp(req, orders, STD, cross_location=True)


def _O():
    req = scene(base(), 60.)
    classes = [cls("F", contractual_service_floor=.8, provenance="CONTRACT", reference="MSA-7"), cls("Z", shortage_penalty_per_unit=5.)]
    orders = [order("oF", "c1", "F", [line("lF", 50.)]), order("oZ", "c2", "Z", [line("lZ", 50.)])]
    return with_atp(req, orders, classes)


def _P1():
    req = scene(base(), 50.)
    orders = [order("o1", "c1", "std", [line("l1", 50.)]), order("o2", "c2", "std", [line("l2", 50.)])]
    return with_atp(req, orders, STD, fairness="NONE")


def _P2():
    req = scene(base(), 50.)
    orders = [order("o1", "c1", "std", [line("l1", 50.)]), order("o2", "c2", "std", [line("l2", 50.)])]
    return with_atp(req, orders, STD, fairness="PROPORTIONAL_WHEN_INDIFFERENT")


def _Q():
    req = scene(base(), 60.)
    cs = [customer(req, "c1", priority=2.), customer(req, "c2", priority=1.)]
    req = with_state(req, customers=cs)
    classes = [cls("hi", shortage_penalty_per_unit=20.), cls("lo")]
    orders = [order("oX", "c1", "hi", [line("lX", 50.)]), order("oY", "c2", "lo", [line("lY", 50.)])]
    return with_atp(req, orders, classes, incumbent_policy="TIER_PRIORITY")


def _R():
    req = scene(base(), 60.)
    classes = [cls("key", strategic=True, provenance="OPERATOR_DECLARED", reference="board-2026-09", shortage_penalty_per_unit=15.), cls("std")]
    orders = [order("oK", "c1", "key", [line("lK", 50.)]), order("oS", "c2", "std", [line("lS", 50.)], order_period=-1)]
    return with_atp(req, orders, classes, incumbent_policy="FCFS_ORDER_DATE")


def _R_flag_only():
    req = scene(base(), 60.)
    classes = [cls("key", strategic=True, provenance="OPERATOR_DECLARED", reference="board-2026-09"), cls("std")]
    orders = [order("oK", "c1", "key", [line("lK", 50.)]), order("oS", "c2", "std", [line("lS", 50.)], order_period=-1)]
    return with_atp(req, orders, classes, incumbent_policy="FCFS_ORDER_DATE")


def _S():
    """Malformed provenance: refused at the contract (built lazily by the benchmark; raises)."""
    req = scene(base(), 60.)
    classes = [cls("key", strategic=True, provenance="CONFIGURED_ASSUMPTION"), cls("std")]
    return with_atp(req, [order("oK", "c1", "key", [line("lK", 50.)])], classes)


def _T():
    req = scene(base(), 100., reserved=60.)
    orders = [order("o1", "c1", "std", [line("l1", 30.)]), order("o2", "c2", "std", [line("l2", 30.)])]
    return with_atp(req, orders, STD)


def _U():
    req = base()
    sku_b = req.skus[0].model_copy(update={"id": "B"})
    cs = [customer(req, "c1")]
    ss = [service(req, "s1", "c1")]
    st = [stock(req, "a_stock", SKU, "north", 20.), stock(req, "b_stock", "B", "north", 100.)]
    sub = Substitute(known_at=_known(req), id="A_by_B", supplied_sku="B", requested_sku=SKU, customers=("c1",), channels=("retail",), input_per_output=1.,
                     penalty_per_output=.5, service_equivalence=1., approved=True, brand_approval_reference="BRAND-1", cannibalization_assumption="none declared")
    req = with_state(req, stock_rows=st, customers=cs, services=ss, substitutions=[sub], inbound_rows=[], skus=[req.skus[0], sku_b])
    orders = [order("o1", "c1", "std", [line("l1", 60.)], substitution_allowed=True)]
    return with_atp(req, orders, STD)


def _U_not_allowed():
    req = _U()
    d = req.model_dump()
    d["atp"]["orders"][0]["substitution_allowed"] = False
    return Request.model_validate(d)


def _V():
    req = sector_base("X1_commercial_plus_produce")
    cs = [customer(req, "c1")]
    ss = [service(req, "s1", "c1", sku="A"), service(req, "s2", "c1", sku="B")]
    st = [stock(req, "a_north", "A", "north", 30., expires_in=52), stock(req, "b_north_old", "B", "north", 40., expires_in=1), stock(req, "b_north_new", "B", "north", 40., expires_in=4)]
    req = with_state(req, stock_rows=st, customers=cs, services=ss, inbound_rows=[])
    orders = [order("o1", "c1", "std", [line("la", 50., sku="A"), line("lb", 60., sku="B", requested=1)])]
    return with_atp(req, orders, STD)


FIXTURES: dict[str, dict[str, Any]] = {
    "A_enough_for_everyone": {"build": _A, "principle": "incumbent_retained"},
    "B_true_scarcity": {"build": _B, "principle": "higher_penalty_first"},
    "C_penalty_vs_margin": {"build": _C, "principle": "higher_total_driver_first"},
    "D_partial_allowed": {"build": _D, "principle": "every_line_share"},
    "E_partial_forbidden": {"build": _E, "principle": "all_or_nothing"},
    "F_backorder_allowed": {"build": _F, "principle": "backordered_at_arrival"},
    "G_backorder_forbidden": {"build": _G, "principle": "no_late_promise"},
    "H_different_dates": {"build": _H, "principle": "own_dates"},
    "I_inbound_in_time": {"build": _I, "principle": "inbound_counts"},
    "J_inbound_too_late": {"build": _J, "principle": "inbound_excluded"},
    "K_multiple_locations": {"build": _K, "principle": "alternative_priced"},
    "L_transfer_lead": {"build": _L, "principle": "lead_respected_unmet"},
    "L2_transfer_lead_backorder": {"build": _L2, "principle": "lead_respected_backorder"},
    "M_produce_remaining_life": {"build": _M, "principle": "no_expiring_cohort"},
    "N_cold_chain": {"build": _N, "principle": "no_ineligible_state"},
    "O_service_floor": {"build": _O, "principle": "floor_met"},
    "P1_indifferent_lexical": {"build": _P1, "principle": "deterministic_tie"},
    "P2_indifferent_proportional": {"build": _P2, "principle": "proportional_tie"},
    "Q_optimal_incumbent": {"build": _Q, "principle": "incumbent_retained_zero_value"},
    "R_strategic_declared": {"build": _R, "principle": "strategic_through_economics"},
    "S_malformed_provenance": {"build": _S, "principle": "refused_at_contract"},
    "T_double_reservation": {"build": _T, "principle": "reserved_never_promised"},
    "U_substitution": {"build": _U, "principle": "declared_substitute_used"},
    "V_mixed_sectors": {"build": _V, "principle": "each_line_own_physics"},
}


def build(name: str) -> Request:
    return FIXTURES[name]["build"]()
