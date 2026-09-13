"""P4B V1 pre-registered fixtures 1-20 (docs/zaad_full/p4b/P4B_PREREGISTRATION.md) on the released demo request
(`zaad/full/demo.py` "normal": one SKU, one branch, demand ~20 / period, horizon 6, source `main` lead 1 period).
Each fixture adds one open order with declared options. Definitions are frozen at registration; corrections are
logged in the evidence (run 2: F06 / F07 / F16 / F17 holding re-registered at 0.4 per value per period so the deferral
saving is material under the fitted demand spread; F17 opening cash 1,000 so the KEEP incumbent is financeable; F14
alternate source route starts with its own supplier as the contract requires)."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from zaad.full.contracts import Request
from zaad.full.demo import example


NIL_STRESS = {"name": "nil", "fill_multiplier": 1., "extra_lead_days": 0, "demand_multiplier": 1., "recovery_period": 6, "shared_failure": True, "affected_resources": []}
TAIL_STRESS = {"name": "tail", "fill_multiplier": .8, "extra_lead_days": 14, "demand_multiplier": 1.1, "recovery_period": 6, "shared_failure": True, "affected_resources": []}


def base(**over) -> dict[str, Any]:
    """The demo request with the neutral declared stress (the P1 workspace convention): the demo's own "tail"
    stress (fill 0.8, +14 days, demand x1.1) is an incidental property outside the registered states and makes
    the released hedged gate reject any later arrival regardless of the commitment economics (run 3 evidence);
    F15 declares its stresses explicitly."""
    req = example("normal")
    d = req.model_dump()
    d["stresses"] = [dict(NIL_STRESS)]
    d.update(over)
    return d


def option(req_d: dict, oid: str, action: str, due: int, fee: float = 0., price: float = 5.3, credit: float = 0., max_quantity: float = 100.,
           deadline_days: int = 3, stages=("confirmed",), payment_due: int | None = None, provenance: str = "CONTRACT", reference: str = "contract-PO-1") -> dict:
    now = req_d["as_of"]
    known = now - timedelta(seconds=1)
    return {"known_at": known, "id": oid, "action": action, "due_in": due, "fee_per_unit": fee, "remaining_invoice_per_unit": price,
            "payment_due_in": due if payment_due is None else payment_due, "max_quantity": max_quantity, "deadline": now + timedelta(days=deadline_days),
            "allowed_stages": list(stages), "contract_reference": reference, "credit_per_unit": credit, "provenance": provenance}


def open_po(req_d: dict, options: list[dict], *, ordered: float = 100., expected: float | None = None, stage: str = "confirmed", split: bool = False,
            prepaid: float = 0., refundable: float = 0., minimum: float = 0., departed: bool = False) -> dict:
    now = req_d["as_of"]
    known = now - timedelta(seconds=1)
    return {"known_at": known, "id": "po1", "source": "main", "revision": 1, "ordered": ordered, "confirmed": ordered, "shipped": ordered if departed else 0.,
            "received": 0., "rejected": 0., "expected_accepted_remaining": ordered if expected is None else expected,
            "placed_at": now - timedelta(days=14), "confirmed_at": now - timedelta(days=10), "departed_at": (now - timedelta(days=2)) if departed else None,
            "current_eta": now + timedelta(days=14), "stage": stage, "carrier": "fixture", "cancellation_status": "declared",
            "prepaid_per_remaining_unit": prepaid, "allow_split_amendments": split, "options": options,
            "minimum_remaining_quantity": minimum, "deposit_refundable_fraction": refundable}


def build_request(d: dict, po: dict | None) -> Request:
    d = dict(d)
    d["pipeline"] = [po] if po is not None else []
    return Request.model_validate(d)


def with_stock(d: dict, quantity: float) -> dict:
    d = dict(d)
    d["stock"] = [{**d["stock"][0], "quantity": quantity}]
    return d


def with_holding(d: dict, holding: float) -> dict:
    d = dict(d)
    d["locations"] = [{**d["locations"][0], "holding_per_value_period": holding}]
    return d


KEEP = lambda d: option(d, "keep", "keep", 2, 0., 5.3, max_quantity=100., stages=("confirmed",))  # noqa: E731
CANCEL = lambda d, **kw: option(d, "cancel", "cancel", 2, kw.pop("fee", .25), 0., **kw)  # noqa: E731
DEFER = lambda d, **kw: option(d, "defer", "de_expedite", kw.pop("due", 4), kw.pop("fee", .10), 5.3, **kw)  # noqa: E731
EXPEDITE = lambda d, **kw: option(d, "expedite", "expedite", kw.pop("due", 0), kw.pop("fee", .50), 5.3, **kw)  # noqa: E731


def _f1():
    d = with_stock(base(), 200.)
    return build_request(d, open_po(d, [KEEP(d), CANCEL(d)]))


def _f2():
    d = with_stock(base(), 20.)
    return build_request(d, open_po(d, [KEEP(d), CANCEL(d)]))


def _f3a():
    d = with_stock(base(), 200.)
    return build_request(d, open_po(d, [KEEP(d)]))


def _f3b():
    d = with_stock(base(), 200.)
    return build_request(d, open_po(d, [KEEP(d), CANCEL(d, deadline_days=-1)]))


def _f3c():
    d = with_stock(base(), 200.)
    return build_request(d, open_po(d, [KEEP(d), CANCEL(d, stages=("placed",))]))


def _f4():
    d = with_stock(base(), 70.)
    return build_request(d, open_po(d, [KEEP(d), CANCEL(d, max_quantity=60.)], split=True, minimum=40.))


def _f5():
    d = with_stock(base(), 200.)
    return build_request(d, open_po(d, [KEEP(d), CANCEL(d, max_quantity=60.)], split=True, minimum=40.))


def _f6():
    d = with_holding(with_stock(base(), 130.), .4)
    return build_request(d, open_po(d, [KEEP(d), DEFER(d)]))


def _f7():
    d = with_holding(with_stock(base(), 10.), .4)
    return build_request(d, open_po(d, [KEEP(d), DEFER(d)]))


def _f8():
    d = with_stock(base(), 0.)
    return build_request(d, open_po(d, [KEEP(d), EXPEDITE(d)]))


def _f9():
    d = with_stock(base(), 0.)
    return build_request(d, open_po(d, [KEEP(d), EXPEDITE(d, fee=5.)]))


def _f10():
    d = with_stock(base(), 200.)
    return build_request(d, open_po(d, [KEEP(d), CANCEL(d), DEFER(d)], stage="shipped", departed=True))


def _f11():
    d = with_stock(base(), 200.)
    return build_request(d, open_po(d, [KEEP(d), CANCEL(d, fee=0.)], prepaid=2.))


def _f12():
    d = with_stock(base(), 200.)
    return build_request(d, open_po(d, [KEEP(d), CANCEL(d, fee=0., credit=2.)], prepaid=2., refundable=1.))


def _f13():
    d = with_stock(base(), 20.)
    return build_request(d, open_po(d, [KEEP(d), EXPEDITE(d), CANCEL(d)], expected=60.))


def _alt_source(d: dict, lead_days: int = 3) -> dict:
    """An approved alternate supplier for the same SKU (P1 / P3 records); 3 days = inside the current period."""
    d = dict(d)
    main = d["sources"][0]
    d["sources"] = [main, {**main, "id": "alt", "supplier": "alt_supplier", "route": ["alt_supplier", *list(main["route"])[1:]], "unit_price": 5.2, "lead_days": lead_days, "quote_reference": "alt-quote"}]
    return d


def _f14():
    # run 3: registered with no stock, where every candidate fails the released downside gate (an unavoidable
    # period-0 shortage); re-registered with 20 on hand and a same-period alternate so the gap is coverable
    d = _alt_source(with_stock(base(), 20.))
    return build_request(d, open_po(d, [KEEP(d), EXPEDITE(d, fee=5.)]))


def _f15():
    d = _alt_source(with_stock(base(), 20.))
    d["stresses"] = [dict(TAIL_STRESS), {"name": "port_closure", "fill_multiplier": 1., "extra_lead_days": 14, "demand_multiplier": 1., "recovery_period": 3,
                                          "shared_failure": True, "affected_resources": ["port_cap"]}]
    return build_request(d, open_po(d, [KEEP(d), EXPEDITE(d, fee=5.), CANCEL(d)]))


def _f16():
    d = with_holding(with_stock(base(), 130.), .4)
    d["sector_mode"] = "PRODUCE"
    d["sku_physics"] = [{"sku": "A", "sector": "PRODUCE", "storage_state": "AMBIENT", "age_at_receipt_periods": 25, "minimum_remaining_life_at_sale": 0,
                         "provenance": {"age_at_receipt_periods": "OPERATOR_DECLARED"}}]
    return build_request(d, open_po(d, [KEEP(d), DEFER(d, due=5)]))


def _f17():
    d = with_holding(with_stock(base(), 130.), .4)
    d["liquidity"] = {**d["liquidity"], "opening_cash": 1000., "credit_limit": 0., "cost_of_capital_per_period": .02}
    return build_request(d, open_po(d, [option(d, "keep", "keep", 2, 0., 5.3, payment_due=1), DEFER(d, payment_due=4)]))


def _f18():
    return _f6()


def _f19():
    return _f2(), _f1()


def _f20():
    # run 3: registered with 60 on hand, where the order is excess and cancel + a smaller purchase is the right
    # answer; re-registered with 20 on hand (20 + 100 = the horizon's demand) so KEEP is the balanced state
    d = with_stock(base(), 20.)
    return build_request(d, open_po(d, [KEEP(d), CANCEL(d), DEFER(d), EXPEDITE(d)]))


def _f20_no_options():
    d = with_stock(base(), 20.)
    return build_request(d, open_po(d, [KEEP(d)]))


FIXTURES: dict[str, dict[str, Any]] = {
    "F01_cancel_optimal": {"build": _f1},
    "F02_cancel_not_worthwhile": {"build": _f2},
    "F03_cancel_prohibited": {"build": _f3b, "variants": (_f3c, _f3a)},   # deadline passed; stage not eligible; option absent (KEEP-only: no block, identity)
    "F04_partial_reduction": {"build": _f4},
    "F05_minimum_remaining": {"build": _f5},
    "F06_defer_reduces_excess": {"build": _f6},
    "F07_defer_stockout": {"build": _f7},
    "F08_expedite_justified": {"build": _f8},
    "F09_expedite_too_expensive": {"build": _f9},
    "F10_already_shipped": {"build": _f10},
    "F11_sunk_deposit": {"build": _f11},
    "F12_refundable_deposit": {"build": _f12},
    "F13_short_fill": {"build": _f13},
    "F14_alternative_source": {"build": _f14},
    "F15_correlated_disruption": {"build": _f15},
    "F16_perishable_delay": {"build": _f16},
    "F17_payment_timing": {"build": _f17},
    "F18_deterministic": {"build": _f18},
    "F19_information_changes_action": {"build": _f19},
    "F20_keep_optimal": {"build": _f20, "variants": (_f20_no_options,)},
}


def build(name: str):
    return FIXTURES[name]["build"]()
