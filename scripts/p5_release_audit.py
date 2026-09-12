"""P5 release audit runner: cases R01-R18 (pre-registered in
docs/zaad_full/evidence/p5/release_audit/P5_RELEASE_AUDIT_PREREG.md) on the corrected engine, the planner
path (R09, R18 incl. the pre-P5 runtime) and the workspace API (R16, R17). Writes
docs/zaad_full/evidence/p5/release_audit/p5_release_audit_cases.{json,md}. Engineering evidence only.

usage: PYTHONPATH=. python3 -m scripts.p5_release_audit [--pre-p5-worktree PATH]"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from scripts.p5_benchmark import by_line, invariants
from scripts.p5_integration import planner_i01, planner_i20
from zaad.atp.contracts import ServiceClass
from zaad.atp.fixtures import STD, base, line, order, scene, with_atp
from zaad.atp.fixtures_audit import CASES, _R01_lane, _R06, build
from zaad.atp.fixtures_integration import build as build_integration
from zaad.atp.integration import atp_block

OUT = Path("docs/zaad_full/evidence/p5/release_audit")
TOL = 1e-6
PAT = (r'"(information_hash|request_hash|fingerprint|input_fingerprint)": "[0-9a-f]+"'
       r'|"(solve_seconds|solver_seconds_total|seconds|elapsed_seconds|wall_seconds|plan_wall_s|generated_at|run_id)": [^,}]+')


def engine(req):
    rep = atp_block(req)
    if rep is None:
        raise RuntimeError("no atp block")
    return rep


def refused(fn) -> tuple[bool, str]:
    try:
        fn()
    except (ValidationError, ValueError) as exc:
        return True, str(exc).split("[type=")[0].strip()
    return False, "ACCEPTED"


def check(name: str, req, rep) -> dict[str, Any]:
    s = by_line(rep)
    unmet = {u["line"]: u["quantity"] for u in rep["unfulfilled"]}
    led = rep["ledger"]
    ev: dict[str, Any] = {"shipped": s, "unmet": unmet, "ledger": led}
    if name.startswith("R01"):
        lane = engine(_R01_lane())
        lane_m8 = engine(_R01_lane(margin=8.))
        via = lambda r: sum(p["quantity"] for p in r["promised"] if p["ship_from"] == "central")  # noqa: E731
        ok = (abs(s.get("lb", 0.) - 50.) < TOL and s.get("la", 0.) < TOL and any("lost contribution per unit" in w and "5.00 against 2.00" in w for w in rep["why"])
              and via(lane) < TOL and abs({u["line"]: u["quantity"] for u in lane["unfulfilled"]}.get("l1", 0.) - 50.) < TOL and abs(lane["ledger"]["alternative_ship_from"]) < TOL
              and abs(via(lane_m8) - 50.) < TOL and lane_m8["ledger"]["alternative_ship_from"] > 0)
        ev.update(why=rep["why"], lane_contribution={"via_lane": via(lane), "unmet": lane["unfulfilled"]}, lane_margin_8={"via_lane": via(lane_m8), "ledger": lane_m8["ledger"]})
    elif name.startswith("R02"):
        retained = sum(r["remaining_unreserved"] for r in rep["remaining_supply"])
        ok = (s.get("l1", 0.) < TOL and abs(unmet.get("l1", 0.) - 80.) < TOL and abs(retained - 50.) < TOL and abs(rep["retained_supply_units"] - 50.) < TOL
              and abs(led["lost_contribution"] - 400.) < TOL and abs(led["sla"] - 200.) < TOL and abs(rep["gross_lost_sales_opportunity"] - 800.) < TOL)
        ev.update(retained=retained, gross=rep["gross_lost_sales_opportunity"])
    elif name.startswith("R03"):
        full = [lid for lid, q in s.items() if abs(q - 40.) < TOL]
        retained = sum(r["remaining_unreserved"] for r in rep["remaining_supply"])
        ok = len(full) == 1 and all(q < TOL or abs(q - 40.) < TOL for q in s.values()) and abs(sum(unmet.values()) - 40.) < TOL and abs(retained - 10.) < TOL \
            and abs(led["lost_contribution"] - 40 * 5.) < TOL
        ev.update(retained=retained)
    elif name.startswith("R04"):
        u = sum(unmet.values())
        ok = abs(u - 70.) < TOL and abs(led["sla"] - u * 2.5) < TOL and abs(led["shortage_penalty"]) < TOL and all(d["sla_basis"] is None for d in rep["drivers"].values())
    elif name.startswith("R05"):
        u = sum(unmet.values())
        ok = abs(u - 70.) < TOL and abs(led["shortage_penalty"] - u * 3.) < TOL and abs(led["sla"]) < TOL and all(d["sla_basis"] is None for d in rep["drivers"].values())
    elif name.startswith("R06"):
        u = sum(unmet.values())
        rep2 = engine(_R06("REPLACES_SERVICE_SLA"))
        u2 = sum(x["quantity"] for x in rep2["unfulfilled"])
        ok = (abs(led["sla"] - u * 2.5) < TOL and abs(led["shortage_penalty"] - u * 3.) < TOL and all(d["sla_basis"] == "ADDITIONAL_TO_SERVICE_SLA" for d in rep["drivers"].values())
              and abs(rep2["ledger"]["sla"]) < TOL and abs(rep2["ledger"]["shortage_penalty"] - u2 * 3.) < TOL
              and all(d["sla_basis"] == "REPLACES_SERVICE_SLA" and d["sla_replaced_per_unit"] == 2.5 and d["sla_per_unmet"] == 0. for d in rep2["drivers"].values()))
        ev.update(replaces={"ledger": rep2["ledger"], "drivers": rep2["drivers"]})
    elif name.startswith("R08"):
        ok = rep["verdict"].startswith("NO MATERIAL") and abs(rep["value_of_allocation"]) < TOL and rep["recommended_policy"] == "TIER_PRIORITY"
        ev.update(verdict=rep["verdict"])
    elif name.startswith("R10"):
        row0 = next(r for r in rep["supply_envelope"] if r["period"] == 0)
        ok = row0["reserved"] == 60. and row0["allocatable_atp"] == 40. and abs(sum(s.values()) - 40.) < TOL
        ev.update(envelope=row0)
    elif name.startswith("R11"):
        nf = rep["non_firm_availability"]
        ok = len(nf) == 1 and nf[0]["promised"] == 0. and all(p["lot"] != nf[0]["id"] for p in rep["promised"]) and refused(
            lambda: with_atp(scene(base(), 10.), [order("o", "c1", "std", [line("l", 1.)])], STD, include_inbound=True, inbound_confidence=.8))[0]
        ev.update(non_firm=nf)
    elif name.startswith("R12"):
        firm = [p for p in rep["promised"] if p["lot"].startswith("transfer:")]
        h = engine(build_integration("I08_firm_vs_uncertain_inbound"))
        ok = bool(firm) and all(p["promise_period"] >= 2 for p in firm) and all(p["promise_period"] == 2 for p in firm) and abs(led["backorder_carry"] - 100.) < TOL \
            and all(p["promise_period"] >= 1 for p in h["promised"] if p["lot"].startswith("transfer:"))
        ev.update(firm=[(p["lot"], p["promise_period"], p["quantity"]) for p in firm])
    elif name.startswith("R13"):
        alt = rep["fulfilment"]["alternative_ship_from"]
        ok = rep["fulfilment"]["p2_transfers_created"] == 0 and alt and all(p["lane"] and p["fulfilment"] == "ALTERNATIVE_SHIP_FROM" for p in alt) \
            and "transfer" not in led and '"transfer_actions"' not in json.dumps(rep) and '"transfers":' not in json.dumps(rep)
        ev.update(alternative=alt[:3])
    elif name.startswith("R14"):
        old = sum(p["quantity"] for p in rep["promised"] if p["lot"] == "stock:north_old")
        ok = abs(old - 60.) < TOL and abs(s.get("l1", 0.) - 100.) < TOL
        ev.update(old=old)
    elif name.startswith("R15"):
        ok = abs(s.get("l1", 0.) - 40.) < TOL and all(p["ship_from"] == "north" and p["lane"] is None for p in rep["promised"]) and any("storage state" in b["reason"] for b in rep["blocked_supply"])
        ev.update(blocked=rep["blocked_supply"])
    else:
        ok = False
    return {"pass": bool(ok), "evidence": ev}


def r07() -> dict[str, Any]:
    req = scene(base(), 10.)
    o = [order("o1", "c1", "k", [line("l1", 10.)])]
    cases = {
        "a_equal_amount_no_basis": refused(lambda: with_atp(req, o, [ServiceClass(id="k", shortage_penalty_per_unit=2.5)])),
        "b_any_amount_no_basis": refused(lambda: with_atp(req, o, [ServiceClass(id="k", shortage_penalty_per_unit=3.)])),
        "c_additional_on_assumption": refused(lambda: ServiceClass(id="k", shortage_penalty_per_unit=3., shortage_penalty_basis="ADDITIONAL_TO_SERVICE_SLA", provenance="CONFIGURED_ASSUMPTION", reference="x")),
        "d_additional_without_reference": refused(lambda: ServiceClass(id="k", shortage_penalty_per_unit=3., shortage_penalty_basis="ADDITIONAL_TO_SERVICE_SLA")),
    }
    ok = all(v[0] and ("twice" in v[1] or "double declaration" in v[1]) for v in cases.values())
    return {"pass": ok, "evidence": {k: v[1] for k, v in cases.items()}}


def r09() -> dict[str, Any]:
    r = planner_i01(build_integration("I01_p0_protection_scarcity"))
    rows = {(x["sku"], x["location"]): x for x in r["evidence"]["overlay"]}
    n = rows.get(("A", "north"), {})
    ok = r["pass"] and n.get("promised_from_on_hand") == 150. and n.get("below_protection_units", 0) > 0 and n.get("hard_reservation") is False
    return {"pass": ok, "evidence": {"north": n, "frozen_identical": r["evidence"]["frozen_report_identical"]}}


def workspace_cases() -> dict[str, dict[str, Any]]:
    import duckdb
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from api.dependencies import get_conn, require_operator
    from api.routers import zaad_full
    from api.routers.zaad import bounded_rate
    from scripts.setup_db import setup_db
    from tests.unit.test_zaad_sourcing_workspace import make_network_vault
    vault = duckdb.connect(":memory:")
    setup_db(vault)
    make_network_vault(vault, seed=7)
    vault.execute("INSERT INTO stg_recourse_spec (operator_id, enabled, review_periods, observables, actions, demand_grid, continuations, provenance) "
                  "VALUES ('tenant_n', TRUE, '[3]', '[\"demand\"]', '[\"purchase\", \"transfer\"]', 5.0, 2, 'OPERATOR_DECLARED')")
    app = FastAPI()
    app.include_router(zaad_full.router)

    def conn_override():
        yield vault
    app.dependency_overrides[get_conn] = conn_override
    app.dependency_overrides[require_operator] = lambda: "tenant_n"
    app.dependency_overrides[bounded_rate] = lambda: None
    client = TestClient(app)
    strip = lambda d: re.sub(PAT, "", json.dumps(d, sort_keys=True, default=str))  # noqa: E731
    base_q = {"max_solve_seconds": 5, "shape": "network"}
    out: dict[str, dict[str, Any]] = {}
    # R16
    t = time.perf_counter()
    r_none = client.post("/api/zaad/network/plan/from-workspace", params=base_q)
    r_false = client.post("/api/zaad/network/plan/from-workspace", params={**base_q, "recourse": "false"})
    r_true = client.post("/api/zaad/network/plan/from-workspace", params={**base_q, "recourse": "true"})
    req_true = client.get("/api/zaad/network/request/from-workspace", params={"max_solve_seconds": 5, "recourse": "true"})
    rn, rf, rt = r_none.json(), r_false.json(), r_true.json()
    ok16 = (r_none.status_code == r_false.status_code == r_true.status_code == 200 and "recourse" not in rn["report"] and "recourse" not in rf["report"]
            and strip(rn["report"]) == strip(rf["report"]) and "recourse" in rt["report"] and rt["build"]["recourse"]["enabled"] and rt["build"]["recourse"]["review_periods"] == [3]
            and req_true.status_code == 200 and req_true.json()["request"]["recourse"]["enabled"] is True and req_true.json()["request"]["recourse"]["review_periods"] == [3])
    out["R16_p4_workspace_recourse_flag"] = {"pass": ok16, "evidence": {"codes": [r_none.status_code, r_false.status_code, r_true.status_code], "false_identical_to_none": strip(rn["report"]) == strip(rf["report"]),
                                                                          "true_has_block": "recourse" in rt["report"], "verdict": (rt["report"].get("recourse") or {}).get("verdict"),
                                                                          "review_periods": rt["build"]["recourse"].get("review_periods"), "seconds": round(time.perf_counter() - t, 1)}}
    # R17: P4 + P5 together
    req0 = req_true.json()["request"]
    sku = req0["skus"][0]["id"]
    customer = req0["customers"][0]["id"]
    vault.execute("insert into stg_atp_service_classes (operator_id, class_id, provenance, reference, shortage_penalty_per_unit, shortage_penalty_basis) values ('tenant_n', 'hi', 'OPERATOR_DECLARED', 'policy-hi', 20.0, 'ADDITIONAL_TO_SERVICE_SLA')")
    vault.execute("insert into stg_atp_customer_orders (operator_id, order_id, line_id, customer_id, service_class, sku, quantity, requested_period, order_period) "
                  f"values ('tenant_n', 'o1', 'l1', '{customer}', 'hi', '{sku}', 5.0, 0, 0)")
    saved = os.environ.get("ZAAD_ATP_ENABLED")
    os.environ["ZAAD_ATP_ENABLED"] = "1"
    try:
        both_req = client.get("/api/zaad/network/request/from-workspace", params={"max_solve_seconds": 5, "recourse": "true", "atp": "true"})
        both = client.post("/api/zaad/network/plan/from-workspace", params={**base_q, "recourse": "true", "atp": "true"})
        only_p4 = client.post("/api/zaad/network/plan/from-workspace", params={**base_q, "recourse": "true", "atp": "false"})
        only_p5 = client.post("/api/zaad/network/plan/from-workspace", params={**base_q, "atp": "true"})
    finally:
        if saved is None:
            os.environ.pop("ZAAD_ATP_ENABLED", None)
        else:
            os.environ["ZAAD_ATP_ENABLED"] = saved
    br, bq = both.json(), both_req.json()
    ok17 = (both_req.status_code == 200 and bq["request"]["recourse"]["enabled"] is True and bq["request"]["atp"]["enabled"] is True
            and both.status_code == 200 and "recourse" in br["report"] and "atp" in br["report"] and br["report"]["atp"]["path"] == "planner"
            and only_p4.status_code == 200 and "recourse" in only_p4.json()["report"] and "atp" not in only_p4.json()["report"]
            and only_p5.status_code == 200 and "atp" in only_p5.json()["report"] and "recourse" not in only_p5.json()["report"])
    out["R17_p4_p5_workspace_together"] = {"pass": ok17, "evidence": {"codes": [both_req.status_code, both.status_code, only_p4.status_code, only_p5.status_code],
                                                                     "both_blocks": ["recourse" in br["report"], "atp" in br["report"]], "atp_verdict": (br["report"].get("atp") or {}).get("verdict"),
                                                                     "p4_only": ["recourse" in only_p4.json()["report"], "atp" in only_p4.json()["report"]],
                                                                     "p5_only": ["atp" in only_p5.json()["report"], "recourse" in only_p5.json()["report"]]}}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pre-p5-worktree", default=None)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []

    def add(name, res, extra=None):
        rec = {"case": name, **(extra or {}), "pass": res["pass"], "evidence": res["evidence"]}
        records.append(rec)
        print(f"{name:40s} {'PASS' if res['pass'] else 'FAIL'}", flush=True)

    for name in CASES:
        req = build(name)
        reps = [engine(req) for _ in range(3)]
        rep = reps[0]
        res = check(name, req, rep)
        inv = invariants(req, rep)
        inv["17_deterministic_ties"] = all(json.dumps(r["promised"], sort_keys=True) == json.dumps(rep["promised"], sort_keys=True) for r in reps[1:])
        res["pass"] = res["pass"] and all(inv.values())
        add(name, res, {"verdict": rep["verdict"], "incumbent_cost": rep["incumbent_cost"], "optimised_cost": rep["optimised_cost"], "invariants": inv})
        if name == "R06_both_distinct":
            add("R07_duplicate_declaration_fails_closed", r07())
        if name == "R08_incumbent_optimal":
            add("R09_p0_overlay_non_binding", r09())
    for name, res in workspace_cases().items():
        add(name, res)
    r18 = planner_i20(build_integration("I20_disabled_exact_pre_p5"), a.pre_p5_worktree)
    add("R18_atp_disabled_pre_p5_identity", r18)
    passed = sum(1 for r in records if r["pass"])
    (OUT / "p5_release_audit_cases.json").write_text(json.dumps(records, indent=1, default=str))
    md = ["# P5 release-audit cases\n", f"{passed} / {len(records)} PASS\n", "| case | verdict | incumbent | optimised | result |", "|---|---|---|---|---|"]
    for r in records:
        md.append(f"| {r['case']} | {str(r.get('verdict', ''))[:40]} | {r.get('incumbent_cost', '-')} | {r.get('optimised_cost', '-')} | {'PASS' if r['pass'] else 'FAIL'} |")
    (OUT / "p5_release_audit_cases.md").write_text("\n".join(md) + "\n")
    print(f"{passed} / {len(records)} release-audit cases PASS")
    return 0 if passed == len(records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
