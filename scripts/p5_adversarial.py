"""P5 adversarial matrix (fail closed): every case must be refused at the contract, refused at the
bounds, or structurally impossible in the isolated engine. Writes docs/zaad_full/evidence/p5/P5_ADVERSARIAL.{md,json}.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from pydantic import ValidationError

from zaad.atp.contracts import Atp, AtpSpec, CustomerOrder, PromiseLine, ServiceClass
from zaad.atp.fixtures import STD, base, cls, line, order, scene, stock, with_atp, with_state
from zaad.atp.promise import promise
from zaad.atp.validation import within_interactive_limits
from zaad.full.contracts import Request

OUT = Path("docs/zaad_full/evidence/p5")


def refused(fn) -> tuple[bool, str]:
    try:
        fn()
    except (ValidationError, ValueError) as exc:
        text = str(exc)
        msg = next((ln.strip() for ln in text.splitlines() if "error" in ln.lower() and "further information" not in ln and not ln.startswith(("1 validation", "2 validation"))), text.splitlines()[0])
        return True, f"REFUSED_AT_CONTRACT: {msg[:90]}"
    return False, "ACCEPTED (must not be)"


def case_duplicate_order_id():
    req = scene(base(), 100.)
    return refused(lambda: with_atp(req, [order("o1", "c1", "std", [line("l1", 10.)]), order("o1", "c2", "std", [line("l2", 10.)])], STD))


def case_negative_demand():
    return refused(lambda: PromiseLine(id="l", sku="A", quantity=-5., requested_period=0))


def case_impossible_requested_date():
    req = scene(base(), 100.)
    a = refused(lambda: with_atp(req, [order("o1", "c1", "std", [line("l1", 10., requested=40)])], STD, promise_horizon=8))
    b = refused(lambda: CustomerOrder(id="o", customer="c1", service_class="std", order_period=0, lines=(PromiseLine(id="l", sku="A", quantity=1., requested_period=0),)).model_copy(update={"order_period": 1}) and AtpSpec(enabled=True, orders=(CustomerOrder(id="o", customer="c1", service_class="std", order_period=-2, lines=(PromiseLine(id="l", sku="A", quantity=1., requested_period=-3),)),), service_classes=(ServiceClass(id="std"),)))
    return a[0] and b[0], f"{a[1]} | {b[1]}"


def case_unknown_sku():
    req = scene(base(), 100.)
    return refused(lambda: with_atp(req, [order("o1", "c1", "std", [line("l1", 10., sku="ZZZ")])], STD))


def case_unknown_customer():
    req = scene(base(), 100.)
    return refused(lambda: with_atp(req, [order("o1", "nobody", "std", [line("l1", 10.)])], STD))


def case_unknown_location():
    req = scene(base(), 100.)
    return refused(lambda: with_atp(req, [order("o1", "c1", "std", [line("l1", 10., ship_from=("mars",))])], STD))


def case_invalid_priority_class():
    req = scene(base(), 100.)
    return refused(lambda: with_atp(req, [order("o1", "c1", "gold", [line("l1", 10.)])], STD))


def case_undeclared_strategic_flag():
    return refused(lambda: ServiceClass(id="k", strategic=True))


def case_conflicting_policies():
    req = scene(base(), 100.)
    a = refused(lambda: with_atp(req, [order("o1", "c1", "std", [line("l1", 10.)])], STD, incumbent_policy="DECLARED_MANUAL"))
    b = refused(lambda: with_atp(req, [order("o1", "c1", "std", [line("l1", 10.)])], STD, incumbent_policy="FIFO_PROMISE", manual_sequence=("o1",)))
    c = refused(lambda: ServiceClass(id="f", contractual_service_floor=1.5))
    d = refused(lambda: CustomerOrder(id="o", customer="c1", service_class="std", lines=(PromiseLine(id="l", sku="A", quantity=1., requested_period=0),), backorder_allowed=False, max_backorder_periods=2))
    return all(x[0] for x in (a, b, c, d)), " | ".join(x[1][:40] for x in (a, b, c, d))


def case_double_reservation():
    req = scene(base(), 100.)
    a = refused(lambda: stock(req, "s", "A", "north", 10., reserved=20.) and with_state(req, stock_rows=[stock(req, "s", "A", "north", 10., reserved=20.)]))
    # and structurally: the engine never promises reserved units (fixture T)
    from zaad.atp.fixtures import build
    rep = promise(build("T_double_reservation"))
    total = sum(p["quantity"] for p in rep["promised"])
    ok = total <= 40. + 1e-6
    if a[0]:
        return ok, f"{a[1][:60]} | STRUCTURALLY_IMPOSSIBLE: {total} of 100 promised (60 reserved)"
    return ok, f"contract accepts reserved > quantity; STRUCTURALLY_IMPOSSIBLE in the engine: {total} of 100 promised (60 reserved)"


def case_expired_produce():
    from zaad.recourse.fixtures import sector_base
    from zaad.atp.fixtures import customer, service
    req = sector_base("P2_near_expiry_inventory")
    req = with_state(req, stock_rows=[stock(req, "old", "A", "north", 100., expires_in=1)], customers=[customer(req, "c1")], services=[service(req, "s1", "c1")], inbound_rows=[])
    req = with_atp(req, [order("o1", "c1", "std", [line("l1", 50., requested=2)])], STD)
    rep = promise(req)
    return not rep["promised"] and abs({u["line"]: u["quantity"] for u in rep["unfulfilled"]}.get("l1", 0.) - 50.) < 1e-6, "STRUCTURALLY_IMPOSSIBLE: expired cohort never promised"


def case_cold_chain_invalid_shipment():
    from zaad.recourse.fixtures import sector_base
    req = sector_base("M1_chilled_shelf_life")
    locs = [loc if loc.id != "south" else loc.model_copy(update={"storage_states": ("AMBIENT",)}) for loc in req.locations]
    a = refused(lambda: with_state(req, locations=locs))
    from zaad.atp.fixtures import build
    rep = promise(build("N_cold_chain"))
    ok = all(p["lane"] is None for p in rep["promised"])
    return a[0] and ok, f"{a[1][:70]} | STRUCTURALLY_IMPOSSIBLE: no shipment on an ineligible lane"


def case_substitution_not_approved():
    from zaad.atp.fixtures import _U
    req = _U()
    d = req.model_dump()
    d["substitutions"][0]["approved"] = False
    rep = promise(Request.model_validate(d))
    return not any(p["substitution"] for p in rep["promised"]), "STRUCTURALLY_IMPOSSIBLE: no column for an unapproved rule"


def case_huge_order_count():
    req = scene(base(), 100.)
    orders = [order(f"o{i}", "c1", "std", [line(f"l{i}", 1.)]) for i in range(201)]
    spec = AtpSpec(enabled=True, orders=tuple(orders), service_classes=(cls("std"),))
    ok, why = within_interactive_limits(Atp(spec=spec, materiality_cost_fraction=.01))
    over = refused(lambda: with_atp(req, [order(f"o{i}", "c1", "std", [line(f"l{i}", 1.)]) for i in range(801)], STD))
    return (not ok) and over[0], f"REFUSED_AT_BOUNDS: {why} | {over[1][:60]}"


def case_malformed_economics():
    a = refused(lambda: ServiceClass(id="x", shortage_penalty_per_unit=-1.))
    b = refused(lambda: PromiseLine(id="l", sku="A", quantity=1., requested_period=0, unit_margin=math.nan))
    c = refused(lambda: ServiceClass(id="y", late_penalty_per_unit_period=math.inf))
    return a[0] and b[0] and c[0], " | ".join(x[1][:35] for x in (a, b, c))


def case_probabilistic_inbound():
    """A confidence factor on inbound would turn uncertain supply into a firm promise: refused at the contract."""
    req = scene(base(), 10.)
    return refused(lambda: with_atp(req, [order("o1", "c1", "std", [line("l1", 10.)])], STD, include_inbound=True, inbound_confidence=.8))


def case_double_shortage_declaration():
    """R07: one shortage consequence declared twice fails closed (equal amount, no basis; any amount, no basis;
    ADDITIONAL on an assumption; ADDITIONAL without a reference)."""
    req = scene(base(), 10.)
    o = [order("o1", "c1", "k", [line("l1", 10.)])]
    a = refused(lambda: with_atp(req, o, [ServiceClass(id="k", shortage_penalty_per_unit=2.5)]))
    b = refused(lambda: with_atp(req, o, [ServiceClass(id="k", shortage_penalty_per_unit=3.)]))
    c = refused(lambda: ServiceClass(id="k", shortage_penalty_per_unit=3., shortage_penalty_basis="ADDITIONAL_TO_SERVICE_SLA", provenance="CONFIGURED_ASSUMPTION", reference="x"))
    d = refused(lambda: ServiceClass(id="k", shortage_penalty_per_unit=3., shortage_penalty_basis="ADDITIONAL_TO_SERVICE_SLA"))
    return all(x[0] for x in (a, b, c, d)), " | ".join(x[1][:60] for x in (a, b, c, d))


def case_cross_tenant_reference():
    req = scene(base(), 100.)
    # a customer id of another operator's vault is simply unknown here: refused at the contract; the API adds the operator match (403)
    return refused(lambda: with_atp(req, [order("o1", "op_other:customer_7", "std", [line("l1", 10.)])], STD))


CASES = [("duplicate customer order id", case_duplicate_order_id), ("negative demand", case_negative_demand), ("impossible requested date", case_impossible_requested_date),
         ("unknown SKU", case_unknown_sku), ("unknown customer", case_unknown_customer), ("unknown location", case_unknown_location),
         ("invalid priority class", case_invalid_priority_class), ("undeclared strategic flag", case_undeclared_strategic_flag),
         ("conflicting service policies", case_conflicting_policies), ("double reservation attempt", case_double_reservation),
         ("expired produce", case_expired_produce), ("cold-chain invalid shipment", case_cold_chain_invalid_shipment),
         ("substitution not approved", case_substitution_not_approved), ("huge order count (resource abuse)", case_huge_order_count),
         ("malformed economics", case_malformed_economics), ("cross-tenant order reference", case_cross_tenant_reference),
         ("probabilistic inbound (confidence factor)", case_probabilistic_inbound), ("double shortage declaration (SLA + class penalty)", case_double_shortage_declaration)]


def main() -> int:
    results = []
    for name, fn in CASES:
        try:
            ok, how = fn()
        except Exception as exc:  # noqa: BLE001  an unexpected exception is a failure, recorded
            ok, how = False, f"UNEXPECTED {type(exc).__name__}: {exc}"[:160]
        results.append({"case": name, "pass": bool(ok), "outcome": how})
        print(f"{name:40s} {'PASS' if ok else 'FAIL'}  {how[:110]}", flush=True)
    passed = sum(1 for r in results if r["pass"])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "P5_ADVERSARIAL.json").write_text(json.dumps({"passed": passed, "total": len(results), "results": results}, indent=1))
    md = ["# P5 adversarial matrix (fail closed)\n", f"{passed} / {len(results)} PASS\n", "| case | outcome | result |", "|---|---|---|"]
    md += [f"| {r['case']} | {r['outcome'][:140]} | {'PASS' if r['pass'] else 'FAIL'} |" for r in results]
    (OUT / "P5_ADVERSARIAL.md").write_text("\n".join(md) + "\n")
    print(f"ADVERSARIAL {passed}/{len(results)}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
