"""P5 release-audit cases R01-R18 (docs/zaad_full/evidence/p5/release_audit/P5_RELEASE_AUDIT_PREREG.md).
Engine-level states here; R09, R16-R18 run through the planner / API in scripts/p5_release_audit.py."""
from __future__ import annotations

from typing import Any

from zaad.atp.contracts import ServiceClass, ShortageBasis
from zaad.atp.fixtures import SKU, STD, base, customer, line, order, scene, service, stock, with_atp, with_state
from zaad.atp.fixtures_integration import build as build_integration
from zaad.full.contracts import Request


def _R01():
    """Declared line margin 2 against the frozen contribution 5 on the same SKU."""
    req = scene(base(), 50.)
    return with_atp(req, [order("oa", "c1", "std", [line("la", 50., unit_margin=2.)]), order("ob", "c2", "std", [line("lb", 50.)])], STD)


def _R01_lane(margin: float | None = None):
    """Lane at 9 per unit against an unmet cost of contribution 5 + SLA 2.5 = 7.5 (the gross basis would read
    10 + 2.5 = 12.5 and ship; a declared margin 8 reads 10.5 and ships). The line requests period 1 so the lane
    (lead 1) is time-feasible. Run 1 requested period 0 (lane unreachable for any economics) and runs 1-2 priced
    the lane at 6, below both bases once the SLA is counted: two documented pre-registration defects
    (P5_RELEASE_AUDIT.md)."""
    req = base()
    st = [stock(req, "north_stock", SKU, "north", 30.), stock(req, "central_stock", SKU, "central", 200.)]
    lanes = [a.model_copy(update={"cost_per_unit": 9.}) if a.id == "lane_north" else a for a in req.transfers]
    req = with_state(req, stock_rows=st, customers=[customer(req, "c1")], services=[service(req, "s1", "c1")], inbound_rows=[], transfers=lanes)
    kw: dict[str, Any] = {} if margin is None else {"unit_margin": margin}
    return with_atp(req, [order("o1", "c1", "std", [line("l1", 80., requested=1, **kw)])], STD, cross_location=True)


def _R02():
    req = scene(base(), 50.)
    return with_atp(req, [order("o1", "c1", "std", [line("l1", 80., minimum_ship_quantity=60.)])], STD)


def _R03():
    req = scene(base(), 50.)
    return with_atp(req, [order("o1", "c1", "std", [line("l1", 40.)], partial_fulfillment_allowed=False),
                          order("o2", "c2", "std", [line("l2", 40.)], partial_fulfillment_allowed=False)], STD)


def _R04():
    req = scene(base(), 30.)
    return with_atp(req, [order("o1", "c1", "sla_only", [line("l1", 50.)]), order("o2", "c2", "sla_only", [line("l2", 50.)])], [ServiceClass(id="sla_only")])


def _R05():
    req = base()
    cs = [customer(req, "c1"), customer(req, "c2")]
    ss = [service(req, "s1", "c1", sla=0.), service(req, "s2", "c2", sla=0.)]
    req = with_state(req, stock_rows=[stock(req, "north_stock", SKU, "north", 30.)], customers=cs, services=ss, inbound_rows=[])
    return with_atp(req, [order("o1", "c1", "pen", [line("l1", 50.)]), order("o2", "c2", "pen", [line("l2", 50.)])], [ServiceClass(id="pen", shortage_penalty_per_unit=3.)])


def _R06(basis: ShortageBasis = "ADDITIONAL_TO_SERVICE_SLA"):
    req = scene(base(), 30.)
    k = ServiceClass(id="both", shortage_penalty_per_unit=3., shortage_penalty_basis=basis, provenance="CONTRACT", reference="MSA-9")
    return with_atp(req, [order("o1", "c1", "both", [line("l1", 50.)]), order("o2", "c2", "both", [line("l2", 50.)])], [k])


def _R08():
    return build_integration("I18_incumbent_wins")


CASES: dict[str, dict[str, Any]] = {
    "R01_basis_ranking": {"build": _R01},
    "R02_minimum_ship_retained": {"build": _R02},
    "R03_all_or_nothing": {"build": _R03},
    "R04_sla_only": {"build": _R04},
    "R05_shortage_only": {"build": _R05},
    "R06_both_distinct": {"build": _R06},
    "R08_incumbent_optimal": {"build": _R08},
    "R10_reservations_excluded": {"build": lambda: build_integration("I06_existing_reservation_excluded")},
    "R11_openpo_never_firm": {"build": lambda: build_integration("I08_firm_vs_uncertain_inbound")},
    "R12_firm_inbound_timing": {"build": lambda: build_integration("I11_backorder_allowed")},
    "R13_alternative_no_transfer": {"build": lambda: build_integration("I17_ledger_reconciliation")},
    "R14_fefo": {"build": lambda: build_integration("I04_perishable_fefo")},
    "R15_cold_chain": {"build": lambda: build_integration("I05_cold_chain_eligibility")},
}


def build(name: str) -> Request:
    return CASES[name]["build"]()
