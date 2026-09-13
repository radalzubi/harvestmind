"""P5 shared-core integration fixtures I01-I20 (docs/zaad_full/p5/P5_PREREGISTRATION.md, integration
section). Built on the released P2 / sector request bases plus a P5 declaration; I01 and I20 run through
the planner, I19 through the API (scripts/p5_integration.py)."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from zaad.atp.fixtures import SKU, STD, base, cls, customer, inbound, line, order, scene, service, stock, with_atp, with_state
from zaad.full.contracts import OpenPO, POOption, Request, Substitute
from zaad.recourse.fixtures import sector_base


def open_po(req: Request, pid: str, source: str, remaining: float, eta_periods: int) -> OpenPO:
    known = req.as_of - timedelta(seconds=1)
    keep = POOption(known_at=known, id=f"{pid}:keep", action="keep", due_in=eta_periods, fee_per_unit=0., remaining_invoice_per_unit=0., payment_due_in=eta_periods,
                    max_quantity=remaining, deadline=req.as_of + timedelta(days=req.period_days * req.horizon), allowed_stages=("ordered",), contract_reference=pid)
    return OpenPO(known_at=known, id=pid, source=source, revision=1, ordered=remaining, confirmed=remaining, shipped=0., received=0., rejected=0.,
                  expected_accepted_remaining=remaining, placed_at=known, confirmed_at=None, departed_at=None,
                  current_eta=req.as_of + timedelta(days=req.period_days * eta_periods), stage="ordered", carrier="unknown", cancellation_status="none",
                  prepaid_per_remaining_unit=0., allow_split_amendments=False, options=(keep,))


def with_pipeline(req: Request, pos: list[OpenPO]) -> Request:
    d = req.model_dump()
    d["pipeline"] = [p.model_dump() for p in pos]
    return Request.model_validate(d)


def _two_locations(req: Request | None = None) -> Request:
    req = req or base()
    st = [stock(req, "north_stock", SKU, "north", 30.), stock(req, "central_stock", SKU, "central", 200.)]
    return with_state(req, stock_rows=st, customers=[customer(req, "c1")], services=[service(req, "s1", "c1")], inbound_rows=[])


def _I01():
    """Planner path: the released P2 request's own customers order more than each location holds."""
    req = base()
    orders = [order("oN", "customer_north", "std", [line("lN", 200.)]), order("oS", "customer_south", "std", [line("lS", 200.)])]
    return with_atp(req, orders, STD)


def _I02():
    req = _two_locations()
    return with_atp(req, [order("o1", "c1", "std", [line("l1", 80., ship_from=("north", "central"))])], STD)


def _I03():
    req = _two_locations()
    return with_atp(req, [order("o1", "c1", "std", [line("l1", 80.)])], STD, cross_location=False)


def _I03b():
    req = _two_locations()
    lanes = [a.model_copy(update={"approved": False}) if a.id == "lane_north" else a for a in req.transfers]
    req = with_state(req, transfers=lanes)
    return with_atp(req, [order("o1", "c1", "std", [line("l1", 80.)])], STD, cross_location=True)


def _I04():
    req = sector_base("P2_near_expiry_inventory")
    st = [stock(req, "north_old", SKU, "north", 60., expires_in=3), stock(req, "north_new", SKU, "north", 100., expires_in=8)]
    req = with_state(req, stock_rows=st, customers=[customer(req, "c1")], services=[service(req, "s1", "c1")], inbound_rows=[])
    return with_atp(req, [order("o1", "c1", "std", [line("l1", 100.)])], STD)


def _I05():
    req = sector_base("M1_chilled_shelf_life")
    st = [stock(req, "north_lot", SKU, "north", 40., expires_in=3), stock(req, "central_lot", SKU, "central", 200., expires_in=3)]
    lanes = [a if a.id != "lane_north" else a.model_copy(update={"storage_states": ("AMBIENT",)}) for a in req.transfers]
    req = with_state(req, stock_rows=st, customers=[customer(req, "c1")], services=[service(req, "s1", "c1")], inbound_rows=[], transfers=lanes)
    return with_atp(req, [order("o1", "c1", "std", [line("l1", 100., requested=1)], backorder_allowed=True, max_backorder_periods=1)], STD, cross_location=True)


def _I06():
    req = scene(base(), 100., reserved=60.)
    return with_atp(req, [order("o1", "c1", "std", [line("l1", 30.)]), order("o2", "c2", "std", [line("l2", 30.)])], STD)


def _I07():
    req = scene(base(), 70., customers_n=3)
    return with_atp(req, [order("o1", "c1", "std", [line("l1", 50.)]), order("o2", "c2", "std", [line("l2", 30.)]), order("o3", "c3", "std", [line("l3", 20.)])], STD)


def _I08():
    req = scene(base(), 0.)
    req = with_state(req, inbound_rows=[inbound(req, "firm1", SKU, "north", 1, 40.)])
    src = next(s for s in req.sources if s.sku == SKU)
    # the open purchase order lands at the source's own destination; the line is served from there
    req = with_pipeline(req, [open_po(req, "po_uncertain", src.id, 60., 2)])
    svc = [service(req, "s1", "c1", location=src.destination)]
    req = with_state(req, services=svc, stock_rows=[], inbound_rows=[inbound(req, "firm1", SKU, src.destination, 1, 40.)])
    return with_atp(req, [order("o1", "c1", "std", [line("l1", 100., requested=2, ship_from=(src.destination,))])], STD, include_inbound=True)


def _I09():
    req = scene(base(), 50.)
    return with_atp(req, [order("o1", "c1", "std", [line("l1", 80.)])], STD)


def _I10():
    req = scene(base(), 50.)
    return with_atp(req, [order("o1", "c1", "std", [line("l1", 80., minimum_ship_quantity=60.)])], STD)


def _I10b():
    req = scene(base(), 65.)
    return with_atp(req, [order("o1", "c1", "std", [line("l1", 80., minimum_ship_quantity=60.)])], STD)


def _I11():
    req = scene(base(), 50.)
    req = with_state(req, inbound_rows=[inbound(req, "in1", SKU, "north", 2, 50.)])
    return with_atp(req, [order("o1", "c1", "std", [line("l1", 100.)], backorder_allowed=True, max_backorder_periods=3)], [cls("std", late_penalty_per_unit_period=1.)], include_inbound=True)


def _I12():
    req = scene(base(), 50.)
    req = with_state(req, inbound_rows=[inbound(req, "in1", SKU, "north", 2, 50.)])
    return with_atp(req, [order("o1", "c1", "std", [line("l1", 100.)])], STD, include_inbound=True)


def _sub_state():
    req = base()
    sku_b = req.skus[0].model_copy(update={"id": "B"})
    st = [stock(req, "a_stock", SKU, "north", 20.), stock(req, "b_stock", "B", "north", 100.)]
    sub = Substitute(known_at=req.as_of, id="A_by_B", supplied_sku="B", requested_sku=SKU, customers=("c1",), channels=("retail",), input_per_output=1.,
                     penalty_per_output=.5, service_equivalence=1., approved=True, brand_approval_reference="BRAND-1", cannibalization_assumption="none declared")
    return with_state(req, stock_rows=st, customers=[customer(req, "c1")], services=[service(req, "s1", "c1")], substitutions=[sub], inbound_rows=[], skus=[req.skus[0], sku_b])


def _I13():
    return with_atp(_sub_state(), [order("o1", "c1", "std", [line("l1", 60.)], substitution_allowed=True)], STD)


def _I14():
    return with_atp(_sub_state(), [order("o1", "c1", "std", [line("l1", 60.)], substitution_allowed=False)], STD)


def _identical(swap: bool = False, fairness: str = "PROPORTIONAL_WHEN_INDIFFERENT"):
    req = scene(base(), 50.)
    classes = [cls("gold", tier="G", shortage_penalty_per_unit=2., late_penalty_per_unit_period=1.), cls("silver", tier="S", shortage_penalty_per_unit=2., late_penalty_per_unit_period=1.)]
    a, b = ("silver", "gold") if swap else ("gold", "silver")
    return with_atp(req, [order("o1", "c1", a, [line("l1", 50.)]), order("o2", "c2", b, [line("l2", 50.)])], classes, fairness=fairness)


def _I15():
    return _identical()


def _I16():
    req = scene(base(), 50.)
    classes = [cls("gold", tier="G", shortage_penalty_per_unit=2.), cls("silver", tier="S", shortage_penalty_per_unit=22.)]
    return with_atp(req, [order("o1", "c1", "gold", [line("l1", 50.)]), order("o2", "c2", "silver", [line("l2", 50.)])], classes)


def _I17():
    """Every unit state at once: on time, late, substituted, alternative ship-from, unmet, refused."""
    req = _sub_state()
    st = [stock(req, "a_north", SKU, "north", 60.), stock(req, "b_north", "B", "north", 30.), stock(req, "a_central", SKU, "central", 40.)]
    req = with_state(req, stock_rows=st, customers=[customer(req, "c2")], services=[service(req, "s2", "c2")],
                     inbound_rows=[inbound(req, "firm1", SKU, "north", 2, 20.)])
    classes = [cls("mix", shortage_penalty_per_unit=3., late_penalty_per_unit_period=1., refusal_cost_per_unit=2.)]
    orders = [order("o1", "c1", "mix", [line("l1", 170.)], backorder_allowed=True, max_backorder_periods=2, substitution_allowed=True),
              order("o2", "c2", "mix", [line("l2", 50.)], late_semantics="CANCEL_IF_LATE")]
    return with_atp(req, orders, classes, include_inbound=True, cross_location=True)


def _I18():
    req = scene(base(), 60.)
    req = with_state(req, customers=[customer(req, "c1", priority=2.), customer(req, "c2", priority=1.)])
    classes = [cls("hi", shortage_penalty_per_unit=20.), cls("lo")]
    return with_atp(req, [order("oX", "c1", "hi", [line("lX", 50.)]), order("oY", "c2", "lo", [line("lY", 50.)])], classes, incumbent_policy="TIER_PRIORITY")


def _I19():
    """API tenant mismatch: the request of operator A (any scarce declaration) inside the interactive solver-time envelope."""
    return _I07().model_copy(update={"max_solve_seconds": 5.})


def _I20():
    """Disabled path: the released P2 request as is (no atp) - compared against `enabled: false` and the pre-P5 runtime."""
    return base()


FIXTURES: dict[str, dict[str, Any]] = {
    "I01_p0_protection_scarcity": {"build": _I01, "path": "planner"},
    "I02_network_direct_ship_from": {"build": _I02, "path": "engine"},
    "I03_implicit_transfer_rejected": {"build": _I03, "path": "engine", "variant": _I03b},
    "I04_perishable_fefo": {"build": _I04, "path": "engine"},
    "I05_cold_chain_eligibility": {"build": _I05, "path": "engine"},
    "I06_existing_reservation_excluded": {"build": _I06, "path": "engine"},
    "I07_order_bound_reservation_conservation": {"build": _I07, "path": "engine"},
    "I08_firm_vs_uncertain_inbound": {"build": _I08, "path": "engine"},
    "I09_partial_shipment": {"build": _I09, "path": "engine"},
    "I10_minimum_ship": {"build": _I10, "path": "engine", "variant": _I10b},
    "I11_backorder_allowed": {"build": _I11, "path": "engine"},
    "I12_backorder_prohibited": {"build": _I12, "path": "engine"},
    "I13_substitution_allowed": {"build": _I13, "path": "engine"},
    "I14_substitution_prohibited": {"build": _I14, "path": "engine"},
    "I15_identical_economics_identical_treatment": {"build": _I15, "path": "engine"},
    "I16_declared_priority_changes_allocation": {"build": _I16, "path": "engine"},
    "I17_ledger_reconciliation": {"build": _I17, "path": "engine"},
    "I18_incumbent_wins": {"build": _I18, "path": "engine"},
    "I19_tenant_mismatch_api": {"build": _I19, "path": "api"},
    "I20_disabled_exact_pre_p5": {"build": _I20, "path": "planner"},
}


def build(name: str) -> Request:
    return FIXTURES[name]["build"]()
