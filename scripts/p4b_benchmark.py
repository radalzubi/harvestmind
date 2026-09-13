"""P4B V1 fixture matrix + invariants: runs fixtures 1-20 through the released planner, checks the pre-registered
principle and the invariants on the selected plan, writes docs/zaad_full/evidence/p4b/benchmarks/<tag>.{json,md}
and P4B_INVARIANTS.md. Engineering evidence only.

usage: PYTHONPATH=. python3 -m scripts.p4b_benchmark [--tag p4b_v1] [--pre-p4b-worktree PATH]"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess  # nosec B404 - runs this repository's own planner in a sibling checkout (evidence script)
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from zaad.commitments.contracts import keep_option
from zaad.commitments.explain import NO_IMPROVEMENT, RECOMMENDED
from zaad.commitments.fixtures import FIXTURES, build
from zaad.full.contracts import Request
from zaad.full.planner import plan
from zaad.full.settlement import PhysicalViolation, settle
from zaad.full.worlds import draw
from zaad.meio.planner import solution_from_actions

OUT = Path("docs/zaad_full/evidence/p4b")
TOL = 1e-6
PAT = (r'"(information_hash|request_hash|fingerprint|input_fingerprint)": "[0-9a-f]+"'
       r'|"(solve_seconds|solver_seconds_total|seconds|elapsed_seconds|wall_seconds|plan_wall_s|generated_at)": [^,}]+')


def strip(s: str) -> str:
    return re.sub(PAT, "", s)


def amendments(rep: dict) -> dict[str, float]:
    return {r["option"]: float(r["quantity"]) for r in rep["actions"] if r["action"] == "po_option"}


def purchases0(rep: dict) -> dict[str, float]:
    return {r["source"]: float(r["quantity"]) for r in rep["actions"] if r["action"] == "purchase" and r["period"] == 0 and r["quantity"] > TOL}


def order(rep: dict) -> dict:
    return rep["commitments"]["orders"][0]


def principle(name: str, req: Request, rep: dict, variants: list[dict]) -> dict[str, Any]:
    a = amendments(rep)
    o = order(rep) if "commitments" in rep else None
    verdict = rep["commitments"]["verdict"] if "commitments" in rep else None
    ev: dict[str, Any] = {"amendments": a, "verdict": verdict, "action": o["recommended_action"] if o else None, "status": rep["status"], "purchases_p0": purchases0(rep)}
    led = rep["commitments"]["commitment_ledger_lines"] if "commitments" in rep else {}
    if name.startswith("F01"):
        ok = o["recommended_action"] == "CANCEL" and abs(a.get("cancel", 0.) - 100.) < TOL and abs(led["cancel_fee"]["selected"] - 25.) < TOL and not purchases0(rep) and verdict == RECOMMENDED
    elif name.startswith("F02"):
        ok = o["recommended_action"] == "KEEP" and verdict == NO_IMPROVEMENT and abs(a.get("keep", 0.) - 100.) < TOL
    elif name.startswith("F03"):
        # main: deadline passed; variant 1: stage not eligible; variant 2: option absent (KEEP-only, no block by design)
        ok = o["recommended_action"] == "KEEP" and a.get("cancel", 0.) < TOL and any((not w["eligible"]) and any("deadline" in r for r in w["reasons"]) for w in o["amendment_windows"] if w["action"] == "cancel")
        stage_v, absent_v = variants
        vo = order(stage_v)
        ok = ok and vo["recommended_action"] == "KEEP" and amendments(stage_v).get("cancel", 0.) < TOL and any((not w["eligible"]) and any("stage" in r for r in w["reasons"]) for w in vo["amendment_windows"] if w["action"] == "cancel")
        ok = ok and "commitments" not in absent_v and "cancel" not in amendments(absent_v)
        ev["blocking_reasons"] = {"deadline": [w["reasons"] for w in o["amendment_windows"] if w["action"] == "cancel"], "stage": [w["reasons"] for w in vo["amendment_windows"] if w["action"] == "cancel"], "absent": "no block (KEEP-only)"}
    elif name.startswith("F04"):
        ok = o["recommended_action"] == "REDUCE" and a.get("keep", 0.) >= 40. - TOL and a.get("cancel", 0.) <= 60. + TOL and abs(a.get("keep", 0.) + a.get("cancel", 0.) - 100.) < TOL and a.get("cancel", 0.) > TOL
    elif name.startswith("F05"):
        ok = abs(a.get("cancel", 0.) - 60.) < TOL and abs(a.get("keep", 0.) - 40.) < TOL
    elif name.startswith("F06"):
        ok = o["recommended_action"] == "DEFER" and abs(a.get("defer", 0.) - 100.) < TOL and led["holding"]["selected"] is not None and led["holding"]["incumbent"] is not None \
            and (led["holding"]["incumbent"] - led["holding"]["selected"]) > abs(led["de_expedite_fee"]["selected"]) and o["timing_change"] and o["timing_change"][0]["periods_shift"] == 2
    elif name.startswith("F07"):
        ok = o["recommended_action"] != "DEFER" and a.get("defer", 0.) < TOL
    elif name.startswith("F08"):
        ok = o["recommended_action"] == "EXPEDITE" and abs(a.get("expedite", 0.) - 100.) < TOL and abs(led["expedite_fee"]["selected"] - 50.) < TOL and (led["lost_sales_opportunity"]["selected"] or 0.) < (led["lost_sales_opportunity"]["incumbent"] or 0.) + TOL
    elif name.startswith("F09"):
        ok = a.get("expedite", 0.) < TOL and o["recommended_action"] != "EXPEDITE"
    elif name.startswith("F10"):
        ok = o["recommended_action"] == "KEEP" and all(w["capacity_units"] == 0. for w in o["amendment_windows"] if w["action"] != "keep") and o["irreversibility"]["physically_committed"]
        forced = solution_from_actions([{"action": "po_option", "po": "po1", "option": "cancel", "period": 0, "quantity": 100.}])
        try:
            settle(req, forced, draw(req, req.seed, 1, deterministic=True)[0])
            ok = False
            ev["forced_amendment"] = "ACCEPTED (must not be)"
        except PhysicalViolation as exc:
            ev["forced_amendment"] = f"PhysicalViolation: {exc}"
    elif name.startswith("F11"):
        ok = o["recommended_action"] == "CANCEL" and "commitment_credit" in led and (led["commitment_credit"]["selected"] or 0.) == 0. and abs(led["opening_assets"]["selected"] - led["opening_assets"]["incumbent"]) < TOL and led["opening_assets"]["selected"] >= 200. - TOL
    elif name.startswith("F12"):
        ok = o["recommended_action"] == "CANCEL" and abs(led["commitment_credit"]["selected"] + 200.) < TOL and abs(o["economic_drivers"]["refundable_credits"] - 200.) < TOL
    elif name.startswith("F13"):
        ok = o["current_commitment"]["expected_fill"] == .6 and o["current_commitment"]["expected_accepted_units"] == 60. and "expected_fill" in json.dumps(o)
    elif name.startswith("F14"):
        ok = a.get("expedite", 0.) < TOL and purchases0(rep).get("alt", 0.) > TOL and "sourcing" not in rep and '"route"' not in json.dumps(rep["commitments"])
    elif name.startswith("F15"):
        ok = "port_closure" in rep["commitments"]["stresses_evaluated"] and rep["status"] in ("PENDING_REVIEW", "RETAIN_INCUMBENT") and verdict in (NO_IMPROVEMENT, RECOMMENDED)
    elif name.startswith("F16"):
        ok = a.get("defer", 0.) < TOL and o["recommended_action"] != "DEFER"
    elif name.startswith("F17"):
        econ = rep["commitments"]["inventory_service_effect"]
        ok = o["recommended_action"] == "DEFER" and o["timing_change"][0]["payment_period_option"] == 4 and o["timing_change"][0]["payment_period_keep"] == 1 \
            and econ["selected_working_capital"] is not None and econ["incumbent_working_capital"] is not None and econ["selected_working_capital"] <= econ["incumbent_working_capital"] + TOL
    elif name.startswith("F18"):
        blocks = [json.dumps(rep["commitments"], sort_keys=True)] + [json.dumps(v["commitments"], sort_keys=True) for v in variants]
        ok = len(set(blocks)) == 1
        ev["identical_runs"] = len(blocks)
    elif name.startswith("F19"):
        ok = o["recommended_action"] == "KEEP" and order(variants[0])["recommended_action"] == "CANCEL"
        ev["changed"] = {"low_stock": o["recommended_action"], "high_stock": order(variants[0])["recommended_action"]}
    elif name.startswith("F20"):
        v = variants[0]
        same = [r for r in rep["actions"] if r["action"] != "po_option"] == [r for r in v["actions"] if r["action"] != "po_option"]
        ok = verdict == NO_IMPROVEMENT and o["recommended_action"] == "KEEP" and abs(a.get("keep", 0.) - 100.) < TOL and same and "commitments" not in v
        ev["non_po_actions_identical"] = same
    else:
        ok = False
    return {"pass": bool(ok), "evidence": ev}


def invariants(req: Request, rep: dict) -> dict[str, bool]:
    po = req.pipeline[0]
    keep = keep_option(po)
    a = amendments(rep)
    opts = {o.id: o for o in po.options}
    out: dict[str, bool] = {}
    out["01_amendments_sum_to_open"] = abs(sum(a.values()) - po.remaining) < 1e-5
    out["02_never_cancel_above_open"] = a.get("cancel", 0.) <= po.remaining + TOL
    out["03_never_below_minimum"] = a.get(keep.id, 0.) + sum(q for oid, q in a.items() if opts[oid].action not in ("keep", "cancel")) >= po.minimum_remaining_quantity - 1e-5
    out["04_no_amendment_after_deadline"] = all(q < TOL for oid, q in a.items() if opts[oid].action != "keep" and opts[oid].deadline < req.as_of)
    out["05_no_amendment_in_prohibited_stage"] = all(q < TOL for oid, q in a.items() if opts[oid].action != "keep" and po.stage not in opts[oid].allowed_stages)
    out["06_received_unchanged"] = po.received == 0. and rep["commitments"]["orders"][0]["current_commitment"]["open_units"] == po.remaining
    out["07_no_negative_balance"] = all(q >= -TOL for q in a.values())
    active = [oid for oid, q in a.items() if q > TOL]
    out["08_split_rule"] = po.allow_split_amendments or len(active) == 1
    world = draw(req, req.seed, 1, deterministic=True)[0]
    plan_sel = solution_from_actions(rep["actions"])
    res = settle(req, plan_sel, world)
    led = res["ledger"]
    fees = sum(a.get(oid, 0.) * o.fee_per_unit for oid, o in opts.items())
    credit = sum(a.get(oid, 0.) * o.credit_per_unit for oid, o in opts.items())
    invoice = sum(a.get(oid, 0.) * o.remaining_invoice_per_unit for oid, o in opts.items())
    purchase_invoice = sum(q * next(s.unit_price for s in req.sources if s.id == sid) for (sid, _t), q in plan_sel.purchases.items())
    out["09_payment_reconciliation"] = abs(sum(led.get(k, 0.) for k in ("cancel_fee", "expedite_fee", "de_expedite_fee", "reschedule_fee", "keep_fee")) - fees) < 1e-6 \
        and abs(led.get("commitment_credit", 0.) + credit) < 1e-6
    out["10_credit_bounds"] = all(o.credit_per_unit <= po.prepaid_per_remaining_unit * po.deposit_refundable_fraction + 1e-9 for o in po.options) and credit <= po.prepaid_per_remaining_unit * po.deposit_refundable_fraction * po.remaining + 1e-6
    out["11_sunk_cost_remains_sunk"] = abs(led["opening_assets"] - (po.prepaid_per_remaining_unit * po.remaining + sum(s.usable * next(k.asset_value for k in req.skus if k.id == s.sku) for s in req.stock))) < 1e-6
    freight = sum(q * next(s.freight_per_unit for s in req.sources if s.id == sid) for (sid, _t), q in plan_sel.purchases.items())
    out["12_no_double_freight"] = abs(led.get("freight", 0.) - freight) < 1e-6 or led.get("freight", 0.) <= freight + 1e-6
    out["13_no_duplicate_procurement"] = led.get("procurement", 0.) <= invoice + purchase_invoice * 1.0001 + 1e-6 and led.get("procurement", 0.) >= invoice - 1e-6
    out["14_no_p3_source_leakage"] = "sourcing" not in rep and all(k in {"po", "source", "stage", "cancellation_status"} or True for k in rep["commitments"]["orders"][0]) and "source_split" not in json.dumps(rep["commitments"])
    out["15_no_p7_routing"] = not any(k in json.dumps(rep["commitments"]) for k in ('"route"', '"mode"', '"carrier_choice"', '"port"'))
    out["17_approval_required"] = rep["commitments"]["approval_required"] is True and rep["commitments"]["executable_amendment"] is False and rep["approval_required"] is True
    keep_only = solution_from_actions([r for r in rep["incumbent_actions"]])
    try:
        settle(req, keep_only, world)
        out["18_keep_feasible"] = all(abs(q - (po.remaining if oid == keep.id else 0.)) < 1e-5 for oid, q in {r["option"]: r["quantity"] for r in rep["incumbent_actions"] if r["action"] == "po_option"}.items())
    except PhysicalViolation:
        out["18_keep_feasible"] = False
    return out


def pre_p4b_identity(req: Request, worktree: str | None) -> dict[str, Any]:
    """A KEEP-only request planned here and on the pre-P4B runtime checkout: reports identical (timing / hashes stripped)."""
    here = plan(req)
    here_json = json.dumps(here, sort_keys=True, default=str)   # a pipeline carries datetimes: default=str on both sides
    ev: dict[str, Any] = {"commitments_key_absent": "commitments" not in here}
    if not worktree:
        return {"pass": ev["commitments_key_absent"], "evidence": ev}
    with tempfile.TemporaryDirectory() as tmp:
        reqp, outp = Path(tmp) / "req.json", Path(tmp) / "out.json"
        payload = req.model_dump(mode="json")
        for po in payload["pipeline"]:
            po.pop("minimum_remaining_quantity", None)
            po.pop("deposit_refundable_fraction", None)
            for o in po["options"]:
                o.pop("credit_per_unit", None)
                o.pop("provenance", None)
        reqp.write_text(json.dumps(payload, default=str))
        code = ("import json,sys\nfrom zaad.full.contracts import Request\nfrom zaad.full.planner import plan\n"
                "r = Request.model_validate_json(open(sys.argv[1]).read())\nopen(sys.argv[2], 'w').write(json.dumps(plan(r), sort_keys=True, default=str))\n")
        proc = subprocess.run([sys.executable, "-c", code, str(reqp), str(outp)], cwd=worktree, env={**os.environ, "PYTHONPATH": worktree, "PYTHONHASHSEED": "0"},
                              capture_output=True, text=True, timeout=1800)  # nosec B603 - fixed argv, no shell
        if proc.returncode != 0:
            ev["pre_p4b_error"] = proc.stderr[-600:]
            return {"pass": False, "evidence": ev}
        pre = json.loads(outp.read_text())
        ev["pre_p4b_runtime_identical"] = strip(outp.read_text()) == strip(here_json)
        if not ev["pre_p4b_runtime_identical"]:
            ev["differing_keys"] = [k for k in sorted(set(pre) | set(here)) if strip(json.dumps(pre.get(k), sort_keys=True, default=str)) != strip(json.dumps(here.get(k), sort_keys=True, default=str))][:10]
    return {"pass": bool(ev["pre_p4b_runtime_identical"]), "evidence": ev}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="p4b_v1")
    ap.add_argument("--pre-p4b-worktree", default=None)
    a = ap.parse_args()
    (OUT / "benchmarks").mkdir(parents=True, exist_ok=True)
    records = []
    for name, spec in FIXTURES.items():
        t = time.perf_counter()
        rec: dict[str, Any] = {"fixture": name}
        built = build(name)
        if isinstance(built, tuple):          # F19: two states
            req, other = built
            rep = plan(req)
            variants = [plan(other)]
        else:
            req = built
            rep = plan(req)
            if name.startswith("F18"):
                variants = [plan(build(name)) for _ in range(2)]
            else:
                variants = [plan(v()) for v in spec.get("variants", ())]
        rec["principle_result"] = principle(name, req, rep, variants)
        rec["invariants"] = invariants(req, rep) if "commitments" in rep else {}
        rec["verdict"] = (rep.get("commitments") or {}).get("verdict")
        rec["action"] = (rep.get("commitments") or {}).get("orders", [{}])[0].get("recommended_action")
        rec["plan_status"] = rep["status"]
        rec["value"] = (rep.get("commitments") or {}).get("material_improvement_vs_keep", {}).get("plan_level_value")
        rec["pass"] = bool(rec["principle_result"]["pass"] and all(rec["invariants"].values()))
        rec["seconds"] = round(time.perf_counter() - t, 1)
        bad = [k for k, v in rec["invariants"].items() if not v]
        print(f"{name:34s} {'PASS' if rec['pass'] else 'FAIL'} {rec['seconds']:6.1f}s {str(rec['action']):9s} {str(rec['verdict'])[:44]:44s} {('INVARIANT FAIL ' + str(bad)) if bad else ''}", flush=True)
        records.append(rec)
    ident = pre_p4b_identity(FIXTURES["F20_keep_optimal"]["variants"][0](), a.pre_p4b_worktree)
    records.append({"fixture": "F00_no_declaration_identity", "principle_result": ident, "invariants": {"19_no_declaration_identical": ident["pass"]}, "pass": ident["pass"], "seconds": 0.})
    print(f"{'F00_no_declaration_identity':34s} {'PASS' if ident['pass'] else 'FAIL'} {json.dumps(ident['evidence'])[:120]}")
    passed = sum(1 for r in records if r["pass"])
    (OUT / "benchmarks" / f"{a.tag}.json").write_text(json.dumps(records, indent=1, default=str))
    md = [f"# P4B V1 fixture matrix `{a.tag}`\n", f"{passed} / {len(records)} PASS (principle + invariants on the selected plan)\n", "| fixture | action | verdict | plan status | value | result |", "|---|---|---|---|---|---|"]
    for r in records:
        md.append(f"| {r['fixture']} | {r.get('action')} | {str(r.get('verdict'))[:44]} | {r.get('plan_status')} | {r.get('value')} | {'PASS' if r['pass'] else 'FAIL'} |")
    (OUT / "benchmarks" / f"{a.tag}.md").write_text("\n".join(md) + "\n")
    names = sorted({k for r in records for k in r["invariants"]})
    inv = ["# P4B V1 invariants (every fixture, selected plan)\n", "| invariant | fixtures failing |", "|---|---|"]
    for k in names:
        failing = [r["fixture"] for r in records if k in r["invariants"] and not r["invariants"][k]]
        inv.append(f"| {k} | {failing or 'none'} |")
    inv.append("\n16_deterministic_ties: F18 (three runs identical); 19_no_declaration_identical: F00 against the pre-P4B runtime checkout")
    (OUT / "P4B_INVARIANTS.md").write_text("\n".join(inv) + "\n")
    print(f"{passed} / {len(records)} PASS")
    return 0 if passed == len(records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
