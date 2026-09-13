"""P4B V1 operator report: for every declared commitment, the current commitment, the recommended action
against the KEEP incumbent, quantity, timing, window, contractual basis, economic drivers, fees, credits,
payment timing, inventory / service effect, materiality, approval. Nothing here decides: the selected plan
comes from the released planner; this block reads its action rows and prices the commitment lines by
settling the selected and the incumbent plans on the deterministic world."""
from __future__ import annotations

from typing import Any

from zaad.commitments.contracts import ACTION_LABEL, Commitments, keep_option, ladder, window
from zaad.full.contracts import Request
from zaad.full.settlement import settle
from zaad.full.worlds import draw

NO_IMPROVEMENT = "NO MATERIAL COMMITMENT IMPROVEMENT AVAILABLE"
RECOMMENDED = "COMMITMENT CHANGE RECOMMENDED"
FEE_KEYS = ("cancel_fee", "expedite_fee", "de_expedite_fee", "reschedule_fee")


def _amendments(rows: list[dict]) -> dict[tuple[str, str], float]:
    return {(r["po"], r["option"]): float(r["quantity"]) for r in rows if r.get("action") == "po_option"}


def _classify(po, chosen: dict[str, float]) -> str:
    """KEEP / CANCEL / REDUCE / DEFER / EXPEDITE / SPLIT from the chosen quantities per option."""
    active = {oid: q for oid, q in chosen.items() if q > 1e-6}
    keep_id = keep_option(po).id
    non_keep = {oid: q for oid, q in active.items() if oid != keep_id}
    if not non_keep:
        return "KEEP"
    if len(non_keep) > 1 or (keep_id in active and any(o.action != "cancel" for o in po.options if o.id in non_keep)):
        return "SPLIT"
    oid, q = next(iter(non_keep.items()))
    action = next(o.action for o in po.options if o.id == oid)
    if action == "cancel":
        return "CANCEL" if q >= po.remaining - 1e-6 else "REDUCE"
    return ACTION_LABEL[action]


def _changes_outside(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Purchase / transfer rows where the selected plan differs from the incumbent (the part of the plan that is
    not a commitment decision), so a PENDING_REVIEW plan next to a KEEP verdict reads unambiguously."""
    def key(r: dict) -> tuple:
        return (r["action"], r.get("source") or r.get("transfer"), r.get("period"), r.get("expiry_cohort"))
    sel = {key(r): float(r["quantity"]) for r in (report.get("actions") or []) if r.get("action") != "po_option"}
    inc = {key(r): float(r["quantity"]) for r in (report.get("incumbent_actions") or []) if r.get("action") != "po_option"}
    out = []
    for k in sorted(set(sel) | set(inc), key=str):
        a, b = inc.get(k, 0.), sel.get(k, 0.)
        if abs(a - b) > 1e-6:
            out.append({"kind": k[0], "id": k[1], "period": k[2], "incumbent_quantity": round(a, 3), "selected_quantity": round(b, 3)})
    return out[:50]


def _settle_ledger(req: Request, rows: list[dict]) -> dict[str, float] | None:
    from zaad.meio.planner import solution_from_actions
    try:
        world = draw(req, req.seed, 1, deterministic=True)[0]
        return dict(settle(req, solution_from_actions(rows), world)["ledger"])
    except Exception:  # noqa: BLE001 - a plan the settlement refuses is reported as unpriceable, never as free
        return None


def commitment_block(req: Request, view: Commitments, report: dict[str, Any]) -> dict[str, Any]:
    selected = _amendments(report.get("actions") or [])
    incumbent = _amendments(report.get("incumbent_actions") or [])
    retained = report.get("status") == "RETAIN_INCUMBENT"
    econ = report.get("economics") or {}
    inc_costs, sel_costs = econ.get("incumbent_costs") or {}, econ.get("selected_costs") or {}
    materiality = econ.get("materiality")
    sel_ledger = _settle_ledger(req, report.get("actions") or [])
    inc_ledger = _settle_ledger(req, report.get("incumbent_actions") or [])
    orders = []
    any_change = False
    for po in view.orders:
        keep = keep_option(po)
        chosen = {o.id: selected.get((po.id, o.id), 0.) for o in po.options}
        chosen_inc = {o.id: incumbent.get((po.id, o.id), 0.) for o in po.options}
        action = "KEEP" if retained else _classify(po, chosen)
        if action != "KEEP":
            any_change = True
        windows = [window(req, po, o) for o in po.options]
        opts = {o.id: o for o in po.options}
        affected = [(oid, q) for oid, q in chosen.items() if q > 1e-6 and oid != keep.id] if action != "KEEP" else []
        fees = sum(q * opts[oid].fee_per_unit for oid, q in affected)
        credits = sum(q * opts[oid].credit_per_unit for oid, q in affected)
        timing = [{"option": oid, "quantity": round(q, 3), "arrival_period_keep": keep.due_in, "arrival_period_option": opts[oid].due_in,
                   "periods_shift": opts[oid].due_in - keep.due_in if opts[oid].action != "cancel" else None,
                   "payment_period_keep": keep.payment_due_in, "payment_period_option": opts[oid].payment_due_in,
                   "invoice_keep_per_unit": keep.remaining_invoice_per_unit, "invoice_option_per_unit": opts[oid].remaining_invoice_per_unit} for oid, q in affected]
        invoice_keep = po.remaining * keep.remaining_invoice_per_unit
        invoice_after = sum(q * opts[oid].remaining_invoice_per_unit for oid, q in chosen.items() if q > 1e-6) if action != "KEEP" else invoice_keep
        orders.append({
            "po": po.id, "source": po.source, "stage": po.stage, "cancellation_status": po.cancellation_status,
            "current_commitment": {"open_units": po.remaining, "expected_accepted_units": po.expected_accepted_remaining,
                                   "expected_fill": round(po.expected_accepted_remaining / po.remaining, 4) if po.remaining else None,
                                   "arrival_period": keep.due_in, "remaining_invoice_per_unit": keep.remaining_invoice_per_unit, "payment_period": keep.payment_due_in,
                                   "deposit_paid": round(po.prepaid_per_remaining_unit * po.remaining, 3), "contract_reference": keep.contract_reference},
            "irreversibility": ladder(req, po),
            "amendment_windows": windows,
            "incumbent": {"action": "KEEP", "quantities": {oid: round(q, 3) for oid, q in chosen_inc.items() if q > 1e-6} or {keep.id: po.remaining}},
            "recommended_action": action,
            "quantities": {oid: round(q, 3) for oid, q in chosen.items() if q > 1e-6} if action != "KEEP" else {keep.id: po.remaining},
            "quantity_affected": round(sum(q for _, q in affected), 3),
            "timing_change": timing,
            "contractual_basis": [{"option": oid, "contract_reference": opts[oid].contract_reference, "provenance": opts[oid].provenance} for oid, _ in affected],
            "economic_drivers": {"amendment_fees": round(fees, 3), "refundable_credits": round(credits, 3),
                                 "remaining_invoice_keep": round(invoice_keep, 3), "remaining_invoice_after": round(invoice_after, 3),
                                 "invoice_avoided": round(invoice_keep - invoice_after, 3),
                                 "deposit_sunk": round(po.prepaid_per_remaining_unit * (1. - po.deposit_refundable_fraction) * sum(q for oid, q in affected if opts[oid].action == "cancel"), 3),
                                 "note": "defer / expedite act only through the arrival timing, holding, service and payment dates the plan already prices; no separate defer cost exists"},
            "approval_required": True, "executable_amendment": False,
        })
    verdict = NO_IMPROVEMENT if (retained or not any_change) else RECOMMENDED
    value = None
    if inc_costs.get("TOTAL") is not None and sel_costs.get("TOTAL") is not None:
        value = round(float(inc_costs["TOTAL"]) - float(sel_costs["TOTAL"]), 3)
    # release audit (D): the commitment verdict is stated apart from the overall plan status. A plan can be
    # PENDING_REVIEW for purchases or transfers while every declared order is KEEP; the value attributed to
    # the commitment is then exactly 0 and the changes outside the commitments are listed.
    actions: list[str] = [str(o["recommended_action"]) for o in orders]
    changed: list[str] = sorted({a for a in actions if a != "KEEP"})
    commitment_action = "KEEP" if not changed else (changed[0] if len(changed) == 1 else "MIXED")
    outside = _changes_outside(report)
    plan_status = report.get("status")
    if commitment_action == "KEEP":
        reading = (f"Commitment verdict: KEEP every declared order ({NO_IMPROVEMENT}). "
                   + (f"The overall plan status {plan_status} refers to {len(outside)} purchase / transfer row(s) outside the commitments; ZAAD does not recommend amending any order."
                      if outside and plan_status != "RETAIN_INCUMBENT" else "The plan is retained as a whole; no order is amended."))
    else:
        named = ", ".join(f"{o['recommended_action']} {o['po']} ({o['quantity_affected']} units)" for o in orders if o["recommended_action"] != "KEEP")
        reading = (f"Commitment verdict: {RECOMMENDED} - {named}; the value is the whole plan's against the KEEP incumbent"
                   + (f" and {len(outside)} purchase / transfer row(s) also differ" if outside else "") + ". Approval required; nothing executes.")
    def _delta(name: str):
        if inc_costs.get(name) is None or sel_costs.get(name) is None:
            return None
        return round(float(sel_costs[name]) - float(inc_costs[name]), 3)
    ledger_lines = {k: {"selected": round(sel_ledger.get(k, 0.), 3) if sel_ledger else None, "incumbent": round(inc_ledger.get(k, 0.), 3) if inc_ledger else None}
                    for k in (*FEE_KEYS, "commitment_credit", "procurement", "holding", "lost_sales_opportunity", "sla", "opening_assets")}
    return {"version": "zaad.commitments.1.1", "verdict": verdict,
            "commitment_action": commitment_action, "commitment_verdict": verdict,
            "commitment_value_vs_keep": 0. if commitment_action == "KEEP" else value,
            "overall_plan_status": plan_status, "plan_changes_outside_commitments": outside, "reading": reading,
            "incumbent": "KEEP every declared commitment (the projected base-stock proxy or the declared incumbent keeps all)",
            "plan_status": plan_status, "selected_policy": report.get("selected_policy"),
            "material_improvement_vs_keep": {"plan_level_value": value, "materiality": materiality, "note": "materiality is the released plan-level gate against the KEEP incumbent; the value is the whole plan's, purchases included"},
            "orders": orders,
            "inventory_service_effect": {"carrying_delta": _delta("CARRYING"), "shortage_delta": _delta("SHORTAGE"), "ordering_delta": _delta("ORDERING"),
                                         "financing_delta": _delta("FINANCING"), "inventory_value_change_delta": _delta("INVENTORY_VALUE_CHANGE"),
                                         "selected_working_capital": econ.get("selected_working_capital"), "incumbent_working_capital": econ.get("incumbent_working_capital")},
            "commitment_ledger_lines": ledger_lines,
            "commitment_component": {"fees": round(sum(sel_ledger.get(k, 0.) for k in FEE_KEYS), 3) if sel_ledger else None,
                                     "credits": round(sel_ledger.get("commitment_credit", 0.), 3) if sel_ledger else None,
                                     "mapped_to": "ORDERING (order-level commercial charges, with the fixed order and switching costs)"},
            "stresses_evaluated": [s.name for s in req.stresses],
            "assumptions": ["amendment rights come only from declared options (action, deadline, eligible stages, cap, split permission, provenance); nothing is inferred",
                            "a credit never exceeds the refundable share of the deposit already paid; the rest of the deposit is sunk",
                            "the decision is here-and-now: no amendment is conditional on future observations (P4B V2 not built)",
                            "route / mode / carrier changes are not commitment decisions (P7)"],
            "approval_required": True, "executable_amendment": False}
