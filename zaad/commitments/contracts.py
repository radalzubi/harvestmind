"""P4B V1 view of a request's declared commitment options.

The mathematics live in the released model (`zaad/full/model.py`, amendment columns per (PO, option)); this
module only reads the declared records: which orders carry a non-keep option, whether each option is
inside its amendment window right now, where the order sits on the irreversibility ladder, and the
refund bound. `resolve()` is None when no non-keep option is declared - then no P4B code is reached and
the released behaviour is bit-identical.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from zaad.full.contracts import OpenPO, POOption, Request
from zaad.full.tolerance import po_closed

NON_KEEP: frozenset[str] = frozenset({"cancel", "expedite", "de_expedite", "reschedule"})
ACTION_LABEL = {"keep": "KEEP", "cancel": "CANCEL", "expedite": "EXPEDITE", "de_expedite": "DEFER", "reschedule": "DEFER"}
# Release audit (K): a declared option set is bounded before any model is built. Each option adds columns (and,
# on an exclusive order, one binary); the interactive paths refuse above these, the batch path above four times.
INTERACTIVE_LIMITS = {"options_per_order": 12, "non_keep_options": 200}


def over_limits(req: Request, factor: int = 1) -> str:
    """The reason a request's declared option set is over the bound, or an empty string."""
    per_order = max((len(po.options) for po in req.pipeline), default=0)
    if per_order > INTERACTIVE_LIMITS["options_per_order"] * factor:
        return f"an order declares {per_order} options, over the limit {INTERACTIVE_LIMITS['options_per_order'] * factor}"
    non_keep = sum(1 for po in req.pipeline for o in po.options if o.action != "keep")
    if non_keep > INTERACTIVE_LIMITS["non_keep_options"] * factor:
        return f"{non_keep} non-keep options declared, over the limit {INTERACTIVE_LIMITS['non_keep_options'] * factor}"
    return ""


@dataclass(frozen=True)
class Commitments:
    orders: tuple[OpenPO, ...]            # open orders with at least one non-keep option
    non_keep_actions: frozenset[str]      # the actions declared somewhere in the request

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(po.id for po in self.orders)


def resolve(req: Request) -> Commitments | None:
    """The request's declared commitment options, or None when every open order is KEEP-only."""
    sources = {s.id: s for s in req.sources}
    orders = tuple(po for po in req.pipeline if not po_closed(po, sources[po.source]) and any(o.action != "keep" for o in po.options))
    if not orders:
        return None
    return Commitments(orders=orders, non_keep_actions=frozenset(o.action for po in orders for o in po.options if o.action != "keep"))


def keep_option(po: OpenPO) -> POOption:
    return next(o for o in po.options if o.action == "keep")


def window(req: Request, po: OpenPO, option: POOption) -> dict[str, Any]:
    """Is the option inside its amendment window right now, and if not, which declared rule closes it?"""
    reasons: list[str] = []
    if option.action != "keep":
        if option.deadline < req.as_of:
            reasons.append(f"deadline {option.deadline.date().isoformat()} has passed (as of {req.as_of.date().isoformat()})")
        if po.stage not in option.allowed_stages:
            reasons.append(f"order stage '{po.stage}' is not among the option's eligible stages {list(option.allowed_stages)}")
    cap = min(po.remaining, option.max_quantity)
    if option.action == "cancel":
        cap = min(cap, po.remaining - po.minimum_remaining_quantity)
    if cap <= 0 and option.action != "keep":
        reasons.append("no modifiable quantity under the option's cap and the order's minimum remaining quantity")
    if reasons:
        cap = 0.   # a closed window has no modifiable quantity (the model gives the column capacity 0 as well)
    return {"option": option.id, "action": option.action, "label": ACTION_LABEL[option.action], "eligible": not reasons, "reasons": reasons,
            "capacity_units": round(max(0., cap), 6), "deadline": option.deadline.isoformat(), "allowed_stages": list(option.allowed_stages),
            "contract_reference": option.contract_reference, "provenance": option.provenance,
            "due_in": option.due_in, "fee_per_unit": option.fee_per_unit, "credit_per_unit": option.credit_per_unit,
            "remaining_invoice_per_unit": option.remaining_invoice_per_unit, "payment_due_in": option.payment_due_in}


def ladder(req: Request, po: OpenPO) -> dict[str, Any]:
    """Where the order sits on the irreversibility ladder, from declared fields only."""
    non_keep = [o for o in po.options if o.action != "keep"]
    open_windows = [o for o in non_keep if window(req, po, o)["eligible"]]
    partially = po.allow_split_amendments and any(min(o.max_quantity, po.remaining) < po.remaining - 1e-9 for o in open_windows)
    financially = po.prepaid_per_remaining_unit > 0
    physically = po.departed_at is not None or po.stage in ("shipped", "in_transit", "arrived", "delivered")
    cancellable = any(o.action == "cancel" for o in open_windows)
    if physically and not open_windows:
        state = "shipped: no declared option applies"
    elif not non_keep:
        state = "non-cancellable: no declared option"
    elif not open_windows:
        state = "non-cancellable: every declared window is closed"
    elif partially:
        state = "partially editable"
    else:
        state = "editable"
    return {"state": state, "editable": bool(open_windows), "partially_editable": partially, "financially_committed": financially,
            "physically_committed": physically, "cancellable_now": cancellable,
            "deposit_per_unit": po.prepaid_per_remaining_unit, "deposit_refundable_fraction": po.deposit_refundable_fraction,
            "refundable_per_unit": po.prepaid_per_remaining_unit * po.deposit_refundable_fraction,
            "sunk_per_unit": po.prepaid_per_remaining_unit * (1. - po.deposit_refundable_fraction),
            "minimum_remaining_quantity": po.minimum_remaining_quantity, "allow_split_amendments": po.allow_split_amendments}
