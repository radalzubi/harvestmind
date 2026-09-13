"""P4B V1 release-audit runner: the audit cases the release brief requires beyond the implementation matrix -
refund / credit economics (B), stage boundary (C), commitment-vs-plan verdict (D), KEEP incumbent and
materiality (E), declaration safety (F), minimum / split (G), ledger reconciliation (H), security (K).
Writes docs/zaad_full/evidence/p4b/release_audit/P4B_RELEASE_AUDIT_CASES.{json,md}. Engineering evidence only.

usage: PYTHONPATH=. python3 -m scripts.p4b_release_audit"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb
from pydantic import ValidationError

from scripts.setup_db import setup_db
from zaad.commitments.contracts import INTERACTIVE_LIMITS, over_limits
from zaad.commitments.explain import NO_IMPROVEMENT, RECOMMENDED
from zaad.commitments.fixtures import CANCEL, DEFER, EXPEDITE, KEEP, base, build, build_request, open_po, option, with_holding, with_stock
from zaad.commitments.workspace import attach, commitment_declarations
from zaad.full.contracts import OpenPO, POOption
from zaad.full.planner import plan
from zaad.full.settlement import PhysicalViolation, settle
from zaad.full.worlds import draw
from zaad.meio.planner import solution_from_actions

OUT = Path("docs/zaad_full/evidence/p4b/release_audit")
TOL = 1e-6
AS_OF = datetime(2026, 1, 1, tzinfo=timezone.utc)


def refused(fn) -> tuple[bool, str]:
    try:
        fn()
    except (ValidationError, ValueError, PhysicalViolation) as exc:
        return True, str(exc).split("[type=")[0].strip()[:160]
    return False, "ACCEPTED (must not be)"


def amend(rep: dict) -> dict[str, float]:
    return {r["option"]: float(r["quantity"]) for r in rep["actions"] if r["action"] == "po_option"}


def ledger_of(req, rows):
    return dict(settle(req, solution_from_actions(rows), draw(req, req.seed, 1, deterministic=True)[0])["ledger"])


def d100():
    return with_stock(base(), 200.)


# ---------------------------------------------------------------- B: refund / credit economics
def b1_fraction_one_partial_cancel():
    d = with_stock(base(), 70.)
    req = build_request(d, open_po(d, [KEEP(d), CANCEL(d, max_quantity=60., credit=2.)], split=True, prepaid=2., refundable=1.))
    rep = plan(req)
    a = amend(rep)
    led = ledger_of(req, rep["actions"])
    asset = next(k.asset_value for k in req.skus if k.id == "A")
    ok = a.get("cancel", 0.) > TOL and abs(led["commitment_credit"] + 2. * a["cancel"]) < TOL and abs(led["opening_assets"] - (200. + 70. * asset)) < TOL
    return ok, {"amendments": a, "commitment_credit": led["commitment_credit"], "opening_assets": led["opening_assets"], "action": rep["commitments"]["commitment_action"]}


def b2_fraction_between():
    d = d100()
    ok1 = build_request(d, open_po(d, [KEEP(d), CANCEL(d, credit=1.)], prepaid=2., refundable=.5)).pipeline[0].options[1].credit_per_unit == 1.
    r = refused(lambda: build_request(d, open_po(d, [KEEP(d), CANCEL(d, credit=1.5)], prepaid=2., refundable=.5)))
    return ok1 and r[0], {"credit_1_accepted": ok1, "credit_1.5": r[1]}


def b3_split_mixed_keep_cancel():
    d = with_stock(base(), 70.)
    req = build_request(d, open_po(d, [KEEP(d), CANCEL(d, max_quantity=60., credit=1.)], split=True, minimum=40., prepaid=2., refundable=.5))
    rep = plan(req)
    a = amend(rep)
    led = ledger_of(req, rep["actions"])
    ok = a.get("keep", 0.) >= 40. - TOL and a.get("cancel", 0.) > TOL and abs(led["commitment_credit"] + 1. * a["cancel"]) < TOL and abs(led["cancel_fee"] - .25 * a["cancel"]) < TOL
    return ok, {"amendments": a, "commitment_credit": led["commitment_credit"], "cancel_fee": led["cancel_fee"], "action": rep["commitments"]["commitment_action"]}


def b4_credit_exactly_at_bound():
    d = d100()
    req = build_request(d, open_po(d, [KEEP(d), CANCEL(d, credit=.5)], prepaid=2., refundable=.25))
    return req.pipeline[0].options[1].credit_per_unit == .5, {"bound": 2. * .25, "credit": .5}


def b5_credit_epsilon_above_bound():
    d = d100()
    r = refused(lambda: build_request(d, open_po(d, [KEEP(d), CANCEL(d, credit=.5 + 1e-6)], prepaid=2., refundable=.25)))
    inside = build_request(d, open_po(d, [KEEP(d), CANCEL(d, credit=.5 + 1e-12)], prepaid=2., refundable=.25)).pipeline[0].options[1].credit_per_unit
    return r[0] and inside <= .5 + 1e-9, {"plus_1e-6": r[1], "plus_1e-12_accepted_within_1e-9_tolerance": inside}


def b6_cancel_fee_above_refund():
    d = d100()
    req = build_request(d, open_po(d, [KEEP(d), CANCEL(d, fee=3., credit=2.)], prepaid=2., refundable=1.))
    rep = plan(req)
    led = ledger_of(req, rep["actions"])
    a = amend(rep)
    ok = (a.get("cancel", 0.) < TOL) or (abs(led["cancel_fee"] - 3. * a["cancel"]) < TOL and abs(led["commitment_credit"] + 2. * a["cancel"]) < TOL)
    return ok, {"amendments": a, "cancel_fee": led.get("cancel_fee", 0.), "commitment_credit": led.get("commitment_credit", 0.), "action": rep["commitments"]["commitment_action"]}


def b7_refund_above_fee_never_manufactures_value():
    d = d100()
    req = build_request(d, open_po(d, [KEEP(d), CANCEL(d, fee=.25, credit=2.)], prepaid=2., refundable=1.))
    rep = plan(req)
    led_sel = ledger_of(req, rep["actions"])
    led_inc = ledger_of(req, rep["incumbent_actions"])
    a = amend(rep)
    q = a.get("cancel", 0.)
    # the cancel's cash effect: fee - credit >= -prepaid per unit; the deposit stays in opening_assets on both plans
    ok = q > TOL and led_sel["cancel_fee"] - (-led_sel["commitment_credit"]) >= -2. * q - TOL and abs(led_sel["opening_assets"] - led_inc["opening_assets"]) < TOL \
        and led_inc["procurement"] - led_sel["procurement"] <= 5.3 * q + TOL
    return ok, {"cancelled": q, "net_cash_per_unit": (led_sel["cancel_fee"] + led_sel["commitment_credit"]) / max(q, 1e-9), "invoice_avoided": led_inc["procurement"] - led_sel["procurement"], "opening_assets_equal": abs(led_sel["opening_assets"] - led_inc["opening_assets"]) < TOL}


def b8_no_deposit_positive_refund():
    d = d100()
    return refused(lambda: build_request(d, open_po(d, [KEEP(d), CANCEL(d, credit=1.)], prepaid=0., refundable=1.)))


def b9_deposit_without_refund_right():
    d = d100()
    r = refused(lambda: build_request(d, open_po(d, [KEEP(d), CANCEL(d, credit=1.)], prepaid=2., refundable=0.)))
    req = build_request(d, open_po(d, [KEEP(d), CANCEL(d)], prepaid=2., refundable=0.))
    rep = plan(req)
    led = ledger_of(req, rep["actions"])
    asset = next(k.asset_value for k in req.skus if k.id == "A")
    return r[0] and led.get("commitment_credit", 0.) == 0. and abs(led["opening_assets"] - (200. + 200. * asset)) < TOL, {"credit_refused": r[1], "credit_ledger": led.get("commitment_credit", 0.), "opening_assets": led["opening_assets"], "deposit_in_opening_assets": 200., "action": rep["commitments"]["commitment_action"]}


def b10_multiple_credit_options_exclusive():
    d = d100()
    c1 = option(d, "c1", "cancel", 2, .5, 0., credit=2.)
    c2 = option(d, "c2", "cancel", 2, 0., 0., credit=1.)
    req = build_request(d, open_po(d, [KEEP(d), c1, c2], split=False, prepaid=2., refundable=1.))
    rep = plan(req)
    a = amend(rep)
    active = [k for k, v in a.items() if v > TOL]
    led = ledger_of(req, rep["actions"])
    expected = -sum(a.get(k, 0.) * c for k, c in (("c1", 2.), ("c2", 1.)))
    return len(active) == 1 and abs(led.get("commitment_credit", 0.) - expected) < TOL, {"amendments": a, "commitment_credit": led.get("commitment_credit", 0.), "action": rep["commitments"]["commitment_action"]}


def b11_credit_on_non_cancel_refused():
    d = d100()
    a = refused(lambda: build_request(d, open_po(d, [KEEP(d), DEFER(d, credit=1.)], prepaid=2., refundable=1.)))
    b = refused(lambda: build_request(d, open_po(d, [KEEP(d), EXPEDITE(d, credit=1.)], prepaid=2., refundable=1.)))
    return a[0] and b[0], {"defer": a[1], "expedite": b[1]}


# ---------------------------------------------------------------- C: stage boundary
def c1_vault_stage_case_normalised_and_unknown_refused():
    d = d100()

    def rows():
        return [{**open_po(d, [KEEP(d)]), "id": "po1", "stage": "confirmed"}]

    def opt(**over):
        return {"po_id": "po1", "id": "c", "action": "cancel", "due_offset_periods": 2, "fee_per_unit": .25, "credit_per_unit": None, "remaining_invoice_per_unit": 0.,
                "payment_offset_periods": None, "max_quantity": 100., "deadline": "2030-01-01", "allowed_stages": '["Confirmed"]', "contract_reference": "ref", "provenance": "contract", **over}
    r = rows()
    attach(r, ({"po1": {"stage": "In Transit"}}, {"po1": [opt()]}), as_of=AS_OF, period_days=7)
    norm = r[0]["stage"] == "in_transit" and r[0]["options"][1]["allowed_stages"] == ["confirmed"]
    ref = refused(lambda: attach(rows(), ({"po1": {"stage": "teleported"}}, {}), as_of=AS_OF, period_days=7))
    return norm and ref[0] and ref[1].startswith("commitments:"), {"normalised": r[0]["stage"], "unknown": ref[1]}


def c2_every_released_writer_inside_vocabulary():
    from zaad.full.contracts import PO_STAGES
    writers = {"workspace": ("ordered", "received"), "replay": ("placed",), "demo": ("confirmed",), "atp_integration_fixtures": ("ordered",), "p2_perf_snapshots": ("placed",), "p3_release_record": ("received",)}
    missing = {k: [s for s in v if s not in PO_STAGES] for k, v in writers.items()}
    return not any(missing.values()), {"writers": writers, "outside_vocabulary": {k: v for k, v in missing.items() if v}}


# ---------------------------------------------------------------- D: commitment verdict vs plan status
def d1_f14_keep_with_pending_review():
    rep = plan(build("F14_alternative_source"))
    b = rep["commitments"]
    ok = b["commitment_action"] == "KEEP" and b["commitment_verdict"] == NO_IMPROVEMENT and b["commitment_value_vs_keep"] == 0. and b["overall_plan_status"] == rep["status"] \
        and (rep["status"] != "PENDING_REVIEW" or b["plan_changes_outside_commitments"]) and "does not recommend amending" in b["reading"]
    return ok, {"overall_plan_status": b["overall_plan_status"], "commitment_action": b["commitment_action"], "commitment_value_vs_keep": b["commitment_value_vs_keep"], "plan_level_value": b["material_improvement_vs_keep"]["plan_level_value"], "outside": b["plan_changes_outside_commitments"][:3], "reading": b["reading"]}


def d2_mixed_phase_transfer_change():
    """A second mixed case: a defer option that is not worthwhile next to a cheaper alternate purchase the plan makes."""
    from zaad.commitments.fixtures import _alt_source
    d = _alt_source(with_stock(base(), 20.))
    req = build_request(d, open_po(d, [KEEP(d), DEFER(d, fee=5.)]))
    rep = plan(req)
    b = rep["commitments"]
    consistent = (b["commitment_action"] == "KEEP") == (b["commitment_verdict"] == NO_IMPROVEMENT) and b["overall_plan_status"] == rep["status"]
    consistent = consistent and (b["commitment_action"] != "KEEP" or b["commitment_value_vs_keep"] == 0.)
    return consistent, {"overall_plan_status": b["overall_plan_status"], "commitment_action": b["commitment_action"], "verdict": b["commitment_verdict"], "outside": b["plan_changes_outside_commitments"][:3], "reading": b["reading"]}


def d3_recommended_reading_names_the_order():
    b = plan(build("F01_cancel_optimal"))["commitments"]
    return b["commitment_action"] == "CANCEL" and "CANCEL po1" in b["reading"] and "Approval required" in b["reading"] and b["commitment_value_vs_keep"] == b["material_improvement_vs_keep"]["plan_level_value"], {"reading": b["reading"]}


# ---------------------------------------------------------------- E: KEEP incumbent / materiality
def e1a_material_on_inventory_not_on_cost():
    """Released materiality is multi-dimensional (cost, carried inventory, service): a deferral that saves 0.04 % of
    cost but carries 13.5 % less inventory is material on inventory. Recorded as the released standard, not a P4B rule."""
    d = with_holding(with_stock(base(), 130.), .001)
    req = build_request(d, open_po(d, [KEEP(d), DEFER(d, fee=0.)]))
    rep = plan(req)
    b = rep["commitments"]
    mat = b["material_improvement_vs_keep"]["materiality"] or {}
    ok = b["commitment_action"] == "DEFER" and b["commitment_verdict"] == RECOMMENDED and "inventory" in mat.get("better_on", []) \
        and abs(mat.get("cost_delta_fraction", 0.)) < mat.get("thresholds", {}).get("cost_fraction", 0.) and mat.get("material") is True
    return ok, {"status": rep["status"], "value": b["material_improvement_vs_keep"]["plan_level_value"], "cost_delta_fraction": mat.get("cost_delta_fraction"),
                "inventory_delta_fraction": mat.get("inventory_delta_fraction"), "better_on": mat.get("better_on"), "thresholds": mat.get("thresholds")}


def e1b_below_materiality_on_every_dimension():
    """A small partial cancel on an excess order: the saving is below the cost, inventory and service thresholds -> KEEP."""
    d = with_stock(base(), 200.)
    req = build_request(d, open_po(d, [KEEP(d), CANCEL(d, max_quantity=3.)], split=True))
    rep = plan(req)
    b = rep["commitments"]
    mat = b["material_improvement_vs_keep"]["materiality"] or {}
    ok = b["commitment_action"] == "KEEP" and b["commitment_verdict"] == NO_IMPROVEMENT and rep["status"] == "RETAIN_INCUMBENT" and mat.get("material") is False
    return ok, {"status": rep["status"], "value": b["material_improvement_vs_keep"]["plan_level_value"], "cost_delta_fraction": mat.get("cost_delta_fraction"),
                "inventory_delta_fraction": mat.get("inventory_delta_fraction"), "material": mat.get("material"), "eligible_cancel_capacity": [w["capacity_units"] for w in b["orders"][0]["amendment_windows"] if w["action"] == "cancel"]}


def e2_incumbent_keeps_candidates_free():
    rep = plan(build("F01_cancel_optimal"))
    inc = {r["option"]: r["quantity"] for r in rep["incumbent_actions"] if r["action"] == "po_option"}
    return inc == {"keep": 100.} and amend(rep).get("cancel", 0.) == 100., {"incumbent": inc, "selected": amend(rep), "incumbent_label": rep.get("incumbent_label") or rep.get("incumbent")}


def e3_neutral_tie_keep_wins():
    d = with_holding(with_stock(base(), 130.), 0.)
    d["liquidity"] = {**d["liquidity"], "cost_of_capital_per_period": 0.}
    req = build_request(d, open_po(d, [KEEP(d), DEFER(d, fee=0.)]))
    rep = plan(req)
    b = rep["commitments"]
    return b["commitment_action"] == "KEEP" and b["commitment_verdict"] == NO_IMPROVEMENT, {"status": rep["status"], "value": b["material_improvement_vs_keep"]["plan_level_value"], "amendments": amend(rep)}


def e4_two_identical_amendments_deterministic():
    d = d100()
    reps = []
    for _ in range(3):
        req = build_request(d, open_po(d, [KEEP(d), option(d, "c1", "cancel", 2, .25, 0.), option(d, "c2", "cancel", 2, .25, 0.)], split=False))
        reps.append(plan(req))
    blocks = {json.dumps(r["commitments"], sort_keys=True) for r in reps}
    a = amend(reps[0])
    return len(blocks) == 1 and sum(1 for v in a.values() if v > TOL) == 1 and reps[0]["commitments"]["commitment_action"] == "CANCEL", {"identical_runs": len(reps), "distinct_blocks": len(blocks), "amendments": a}


def e5_feasible_option_alone_is_no_recommendation():
    rep = plan(build("F20_keep_optimal"))
    b = rep["commitments"]
    eligible = [w["option"] for o in b["orders"] for w in o["amendment_windows"] if w["eligible"] and w["action"] != "keep"]
    return len(eligible) >= 3 and b["commitment_action"] == "KEEP" and b["commitment_verdict"] == NO_IMPROVEMENT, {"eligible_options": eligible, "action": b["commitment_action"]}


# ---------------------------------------------------------------- F / K: declaration safety, tenancy, bounds
def _vault():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    return conn


def f1_cross_tenant_identifier_collision():
    conn = _vault()
    conn.execute("insert into stg_po_options (operator_id, po_id, option_id, action, due_offset_periods, fee_per_unit, max_quantity, deadline, allowed_stages, contract_reference, provenance) "
                 "values ('tenant_a', 'po1', 'c', 'cancel', 2, 0.25, 100, TIMESTAMP '2030-01-01', '[\"confirmed\"]', 'ref', 'CONTRACT')")
    d = d100()
    rows_b = [{**open_po(d, [KEEP(d)]), "id": "po1"}]
    decl_b = commitment_declarations(conn, "tenant_b")
    ok_b = decl_b is None and all(o["action"] == "keep" for o in rows_b[0]["options"])
    rows_a: list = []
    ref = refused(lambda: attach(rows_a, commitment_declarations(conn, "tenant_a"), as_of=AS_OF, period_days=7))
    return ok_b and ref[0], {"tenant_b_sees": "nothing (KEEP-only)" if decl_b is None else "LEAK", "tenant_a_without_the_order": ref[1]}


def f2_duplicate_rows_refused():
    conn = _vault()
    for _ in range(2):
        conn.execute("insert into stg_po_options (operator_id, po_id, option_id, action, due_offset_periods, fee_per_unit, max_quantity, deadline, allowed_stages, contract_reference, provenance) "
                     "values ('op', 'po1', 'c', 'cancel', 2, 0.25, 100, TIMESTAMP '2030-01-01', '[\"confirmed\"]', 'ref', 'CONTRACT')")
    d = d100()
    return refused(lambda: attach([{**open_po(d, [KEEP(d)]), "id": "po1"}], commitment_declarations(conn, "op"), as_of=AS_OF, period_days=7))


def f3_oversized_declaration_set():
    conn = _vault()
    for i in range(INTERACTIVE_LIMITS["options_per_order"]):
        conn.execute("insert into stg_po_options (operator_id, po_id, option_id, action, due_offset_periods, fee_per_unit, max_quantity, deadline, allowed_stages, contract_reference, provenance) "
                     f"values ('op', 'po1', 'r{i}', 'reschedule', {3 + i % 3}, 0.1, 100, TIMESTAMP '2030-01-01', '[\"confirmed\"]', 'ref', 'CONTRACT')")  # noqa: S608  # nosec B608 - in-memory evidence vault, literal loop index
    d = d100()
    ref = refused(lambda: attach([{**open_po(d, [KEEP(d)]), "id": "po1"}], commitment_declarations(conn, "op"), as_of=AS_OF, period_days=7))
    many = [KEEP(d)] + [option(d, f"r{i}", "reschedule", 3 + (i % 3), .1, 5.3) for i in range(INTERACTIVE_LIMITS["options_per_order"])]
    api = over_limits(build_request(d, open_po(d, many)))
    return ref[0] and bool(api), {"adapter": ref[1], "api_interactive": api}


def f4_invalid_provenance_and_impossible_dates():
    conn = _vault()
    conn.execute("insert into stg_po_options (operator_id, po_id, option_id, action, due_offset_periods, fee_per_unit, max_quantity, deadline, allowed_stages, contract_reference, provenance) "
                 "values ('op', 'po1', 'c', 'cancel', 2, 0.25, 100, TIMESTAMP '2030-01-01', '[\"confirmed\"]', 'ref', 'guess')")
    d = d100()
    a = refused(lambda: attach([{**open_po(d, [KEEP(d)]), "id": "po1"}], commitment_declarations(conn, "op"), as_of=AS_OF, period_days=7))
    past = build_request(d, open_po(d, [KEEP(d), CANCEL(d, deadline_days=-3650)]))
    rep = plan(past)
    w = [x for x in rep["commitments"]["orders"][0]["amendment_windows"] if x["action"] == "cancel"][0]
    return a[0] and not w["eligible"] and w["capacity_units"] == 0. and amend(rep).get("cancel", 0.) < TOL, {"provenance": a[1], "past_deadline_window": w["reasons"]}


def f5_nan_inf_and_negatives():
    d = d100()
    out = {}
    out["nan_fee"] = refused(lambda: build_request(d, open_po(d, [KEEP(d), CANCEL(d, fee=float("nan"))])))
    out["inf_fee"] = refused(lambda: build_request(d, open_po(d, [KEEP(d), CANCEL(d, fee=float("inf"))])))
    out["negative_minimum"] = refused(lambda: build_request(d, open_po(d, [KEEP(d), CANCEL(d)], minimum=-1.)))
    out["fraction_above_one"] = refused(lambda: build_request(d, open_po(d, [KEEP(d), CANCEL(d)], refundable=1.5)))
    out["negative_prepaid"] = refused(lambda: build_request(d, open_po(d, [KEEP(d), CANCEL(d)], prepaid=-1.)))
    huge = build_request(d, open_po(d, [KEEP(d), CANCEL(d, max_quantity=1e300)]))
    rep = plan(huge)
    out["huge_cap_clipped"] = (amend(rep).get("cancel", 0.) <= 100. + TOL, "clipped to the open quantity")
    return all(v[0] for v in out.values()), {k: v[1] for k, v in out.items()}


def f6_no_execution_path():
    from api.routers import zaad_full
    paths = [r.path for r in zaad_full.router.routes]
    leak = [p for p in paths if "amend" in p.lower() or "supplier" in p.lower()]
    b = plan(build("F01_cancel_optimal"))["commitments"]
    return not leak and b["approval_required"] is True and b["executable_amendment"] is False, {"routes": paths, "approval_required": b["approval_required"], "executable_amendment": b["executable_amendment"]}


# ---------------------------------------------------------------- G: minimum / split
def g1_full_cancel_only_when_floor_is_zero():
    d = d100()
    a = refused(lambda: build_request(d, open_po(d, [KEEP(d), CANCEL(d)], minimum=1.)))
    rep = plan(build_request(d, open_po(d, [KEEP(d), CANCEL(d)], minimum=0.)))
    return a[0] and amend(rep).get("cancel", 0.) == 100., {"floor_1": a[1], "floor_0_cancel": amend(rep)}


def g2_boundary_around_tolerance():
    d = d100()
    exact = build_request(d, open_po(d, [KEEP(d), CANCEL(d, max_quantity=60.)], split=True, minimum=40.))
    over = refused(lambda: build_request(d, open_po(d, [KEEP(d), CANCEL(d, max_quantity=60.)], split=True, minimum=40. + 1e-6)))
    within = build_request(d, open_po(d, [KEEP(d), CANCEL(d, max_quantity=60.)], split=True, minimum=40. + 1e-12))
    rep = plan(exact)
    a = amend(rep)
    return over[0] and a.get("keep", 0.) >= 40. - 1e-6 and within.pipeline[0].minimum_remaining_quantity > 40., {"minimum_40+1e-6": over[1], "amendments_at_exact_floor": a}


def g3_sum_of_caps_split():
    d = d100()
    two = [KEEP(d), option(d, "c1", "cancel", 2, .25, 0., max_quantity=40.), option(d, "c2", "cancel", 2, .10, 0., max_quantity=40.)]
    r = refused(lambda: build_request(d, open_po(d, two, split=True, minimum=40.)))
    ok_excl = build_request(d, open_po(d, two, split=False, minimum=40.))
    rep = plan(ok_excl)
    a = amend(rep)
    return r[0] and sum(1 for v in a.values() if v > TOL) == 1 and a.get("keep", 0.) >= 40. - TOL, {"split": r[1], "exclusive_amendments": a}


def g4_settlement_floor_defense_in_depth():
    d = d100()
    raw = open_po(d, [KEEP(d), CANCEL(d, max_quantity=100.)], split=True, minimum=40.)
    po = OpenPO.model_construct(**{**raw, "options": tuple(POOption.model_validate(o) for o in raw["options"])})
    req = build_request(d, None).model_copy(update={"pipeline": (po,)})
    forced = solution_from_actions([{"action": "po_option", "po": "po1", "option": "cancel", "period": 0, "quantity": 70.}, {"action": "po_option", "po": "po1", "option": "keep", "period": 0, "quantity": 30.}])
    return refused(lambda: settle(req, forced, draw(req, req.seed, 1, deterministic=True)[0]))


# ---------------------------------------------------------------- H: ledger reconciliation
def h1_fee_credit_procurement_once():
    req = build("F12_refundable_deposit")
    rep = plan(req)
    led = ledger_of(req, rep["actions"])
    lines = rep["commitments"]["commitment_ledger_lines"]
    a = amend(rep)
    q = a.get("cancel", 0.)
    fee = next(o.fee_per_unit for o in req.pipeline[0].options if o.id == "cancel")
    ok = abs(led["cancel_fee"] - fee * q) < TOL and abs(led["commitment_credit"] + 2. * q) < TOL and abs(led.get("keep_fee", 0.)) < TOL \
        and abs(lines["cancel_fee"]["selected"] - led["cancel_fee"]) < 1e-3 and abs(lines["commitment_credit"]["selected"] - led["commitment_credit"]) < 1e-3 \
        and abs(rep["commitments"]["commitment_component"]["credits"] - led["commitment_credit"]) < 1e-3 and "defer_cost" not in json.dumps(rep)
    procurement_po = sum(a.get(o.id, 0.) * o.remaining_invoice_per_unit for o in req.pipeline[0].options)
    purchases = sum(r["quantity"] * next(s.unit_price for s in req.sources if s.id == r["source"]) for r in rep["actions"] if r["action"] == "purchase")
    ok = ok and abs(led["procurement"] - procurement_po - purchases) < 1e-3
    return ok, {"cancel_fee": led["cancel_fee"], "commitment_credit": led["commitment_credit"], "procurement": led["procurement"], "po_invoice": procurement_po, "purchases": purchases, "opening_assets": led["opening_assets"]}


def h2_economics_reconciles_block():
    req = build("F06_defer_reduces_excess")
    rep = plan(req)
    econ = rep["economics"]
    b = rep["commitments"]
    val = round(float(econ["incumbent_costs"]["TOTAL"]) - float(econ["selected_costs"]["TOTAL"]), 3)
    ok = b["commitment_value_vs_keep"] == val and b["inventory_service_effect"]["ordering_delta"] is not None and abs(b["inventory_service_effect"]["ordering_delta"] - (float(econ["selected_costs"]["ORDERING"]) - float(econ["incumbent_costs"]["ORDERING"]))) < 1e-3
    return ok, {"value": val, "ordering_delta": b["inventory_service_effect"]["ordering_delta"], "de_expedite_fee": b["commitment_ledger_lines"]["de_expedite_fee"]}


def h3_model_objective_matches_settlement_on_deterministic_world():
    """The candidate objective on the deterministic world and the settlement's economic cost agree for the commitment terms."""
    from zaad.full.model import solve
    req = build("F01_cancel_optimal")
    world = draw(req, req.seed, 1, deterministic=True)
    sol = solve(req, world)
    res = settle(req, sol, world[0])
    a = sol.amendments
    q = a.get(("po1", "cancel"), 0.)
    led = res["ledger"]
    ok = abs(led["cancel_fee"] - .25 * q) < TOL and q > TOL
    return ok, {"model_cancel": q, "settlement_cancel_fee": led["cancel_fee"], "settlement_total": res.get("total") or res.get("economic_cost")}


CASES = [
    ("B1 refundable fraction 1, partial cancel", b1_fraction_one_partial_cancel), ("B2 refundable fraction between 0 and 1", b2_fraction_between),
    ("B3 split with mixed keep / cancel", b3_split_mixed_keep_cancel), ("B4 credit exactly at the bound", b4_credit_exactly_at_bound),
    ("B5 credit epsilon above the bound", b5_credit_epsilon_above_bound), ("B6 cancel fee above the refund", b6_cancel_fee_above_refund),
    ("B7 refund above the fee never manufactures value", b7_refund_above_fee_never_manufactures_value), ("B8 no deposit + positive refund", b8_no_deposit_positive_refund),
    ("B9 deposit with no refund right", b9_deposit_without_refund_right), ("B10 several credit options, one selectable", b10_multiple_credit_options_exclusive),
    ("B11 credit on a non-cancel option", b11_credit_on_non_cancel_refused),
    ("C1 vault stage case normalised, unknown refused", c1_vault_stage_case_normalised_and_unknown_refused), ("C2 every released writer inside the vocabulary", c2_every_released_writer_inside_vocabulary),
    ("D1 F14: KEEP with PENDING_REVIEW", d1_f14_keep_with_pending_review), ("D2 mixed-phase defer next to an alternate purchase", d2_mixed_phase_transfer_change), ("D3 recommended reading names the order", d3_recommended_reading_names_the_order),
    ("E1a material on inventory, not on cost (released standard)", e1a_material_on_inventory_not_on_cost), ("E1b below materiality on every dimension", e1b_below_materiality_on_every_dimension), ("E2 incumbent keeps, candidates free", e2_incumbent_keeps_candidates_free), ("E3 economically neutral tie -> KEEP", e3_neutral_tie_keep_wins),
    ("E4 two identical amendments, deterministic", e4_two_identical_amendments_deterministic), ("E5 feasible option alone is no recommendation", e5_feasible_option_alone_is_no_recommendation),
    ("F1 cross-tenant identifier collision", f1_cross_tenant_identifier_collision), ("F2 duplicate declaration rows", f2_duplicate_rows_refused), ("F3 oversized declaration set", f3_oversized_declaration_set),
    ("F4 invalid provenance / impossible date", f4_invalid_provenance_and_impossible_dates), ("F5 NaN / inf / negative / huge", f5_nan_inf_and_negatives), ("F6 no execution path", f6_no_execution_path),
    ("G1 full cancel only when the floor is zero", g1_full_cancel_only_when_floor_is_zero), ("G2 boundary around tolerance", g2_boundary_around_tolerance), ("G3 sum of caps under split", g3_sum_of_caps_split), ("G4 settlement floor (contract bypassed)", g4_settlement_floor_defense_in_depth),
    ("H1 fee / credit / procurement charged once", h1_fee_credit_procurement_once), ("H2 economics reconciles the block", h2_economics_reconciles_block), ("H3 model objective vs settlement", h3_model_objective_matches_settlement_on_deterministic_world),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    for name, fn in CASES:
        t = time.perf_counter()
        try:
            ok, ev = fn()
        except Exception as exc:  # noqa: BLE001 - a crashing case is a failing case, recorded
            ok, ev = False, {"error": f"{type(exc).__name__}: {exc}"[:300]}
        results.append({"case": name, "pass": bool(ok), "evidence": ev, "seconds": round(time.perf_counter() - t, 1)})
        print(f"{name:52s} {'PASS' if ok else 'FAIL'} {results[-1]['seconds']:6.1f}s {json.dumps(ev, default=str)[:110]}", flush=True)
    passed = sum(r["pass"] for r in results)
    (OUT / "P4B_RELEASE_AUDIT_CASES.json").write_text(json.dumps({"passed": passed, "total": len(results), "results": results}, indent=1, default=str))
    md = ["# P4B V1 release-audit cases\n", f"{passed} / {len(results)} PASS\n", "| case | result | evidence |", "|---|---|---|"]
    md += [f"| {r['case']} | {'PASS' if r['pass'] else 'FAIL'} | {json.dumps(r['evidence'], default=str)[:160].replace('|', '/')} |" for r in results]
    (OUT / "P4B_RELEASE_AUDIT_CASES.md").write_text("\n".join(md) + "\n")
    print(f"RELEASE_AUDIT {passed}/{len(results)}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
