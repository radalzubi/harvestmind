"""P5 shared-core integration matrix I01-I20 (pre-registered in docs/zaad_full/p5/P5_PREREGISTRATION.md):
the integrated engine on the frozen records, the planner path (I01, I20 incl. the pre-P5 runtime
comparison), the API path (I19); invariants 1-19 on every recommendation. Writes
docs/zaad_full/evidence/p5/integration/p5_integration.{json,md}. Engineering evidence only.

usage: PYTHONPATH=. python3 -m scripts.p5_integration [--pre-p5-worktree /path/to/checkout-of-6b58764]"""
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

from pydantic import ValidationError

from scripts.p5_benchmark import by_line, invariants
from zaad.atp.contracts import resolve
from zaad.atp.economics import LEDGER_KEYS
from zaad.atp.fixtures_integration import FIXTURES, _identical, build
from zaad.atp.integration import atp_block
from zaad.full.contracts import Request
from zaad.full.planner import plan, report_json

OUT = Path("docs/zaad_full/evidence/p5/integration")
TOL = 1e-6
PAT = (r'"(information_hash|request_hash|fingerprint|input_fingerprint)": "[0-9a-f]+"'
       r'|"(solve_seconds|solver_seconds_total|seconds|elapsed_seconds|wall_seconds|plan_wall_s|generated_at)": [^,}]+')


def _strip(s: str) -> str:
    return re.sub(PAT, "", s)


def _frozen(report: dict) -> str:
    return _strip(json.dumps({k: v for k, v in report.items() if k != "atp"}, sort_keys=True, default=str))


def engine(req) -> dict:
    rep = atp_block(req)
    if rep is None:
        raise RuntimeError("fixture without an enabled atp block")
    return rep


def principle(name: str, req, rep) -> dict[str, Any]:
    s = by_line(rep) if rep.get("promised") is not None else {}
    unmet = {u["line"]: u["quantity"] for u in rep.get("unfulfilled", [])}
    ev: dict[str, Any] = {"shipped": s, "unmet": unmet}
    if name.startswith("I02"):
        ok = (abs(s.get("l1", 0.) - 80.) < TOL and all(p["fulfilment"] == "DIRECT" for p in rep["promised"]) and abs(rep["ledger"]["alternative_ship_from"]) < TOL
              and rep["fulfilment"]["p2_transfers_created"] == 0 and not unmet
              and abs(sum(p["quantity"] for p in rep["promised"] if p["ship_from"] == "central") - 50.) < TOL)
        ev["fulfilment"] = rep["fulfilment"]["direct_units"]
    elif name.startswith("I03"):
        b = engine(FIXTURES[name]["variant"]())
        def check(r):
            sh = by_line(r)
            um = {u["line"]: u["quantity"] for u in r["unfulfilled"]}
            return (abs(sh.get("l1", 0.) - 30.) < TOL and abs(um.get("l1", 0.) - 50.) < TOL and all(p["ship_from"] == "north" for p in r["promised"])
                    and any(b_["lot"] == "stock:central_stock" and "no implicit transfer" in b_["reason"] for b_ in r["blocked_supply"]) and r["fulfilment"]["p2_transfers_created"] == 0)
        ok = check(rep) and check(b)
        ev["blocked"] = rep["blocked_supply"]
        ev["blocked_unapproved_lane"] = b["blocked_supply"]
    elif name.startswith("I04"):
        old = sum(p["quantity"] for p in rep["promised"] if p["lot"] == "stock:north_old")
        new = sum(p["quantity"] for p in rep["promised"] if p["lot"] == "stock:north_new")
        ok = abs(old - 60.) < TOL and abs(new - 40.) < TOL and not unmet
        ev["cohorts"] = {"old": old, "new": new}
    elif name.startswith("I05"):
        ok = (abs(s.get("l1", 0.) - 40.) < TOL and all(p["ship_from"] == "north" and p["lane"] is None for p in rep["promised"])
              and any(b_["lot"] == "stock:central_lot" and "storage state" in b_["reason"] for b_ in rep["blocked_supply"]))
        ev["blocked"] = rep["blocked_supply"]
    elif name.startswith("I06"):
        row0 = next(r for r in rep["supply_envelope"] if r["period"] == 0)
        ok = row0["reserved"] == 60. and row0["allocatable_atp"] == 40. and abs(sum(s.values()) - 40.) < TOL and all(r["physical_units"] <= 40. + TOL for r in rep["reservations"])
        ev["envelope_period_0"] = row0
    elif name.startswith("I07"):
        res = rep["reservations"]
        ids = [r["reservation_id"] for r in res]
        per_lot: dict[str, float] = {}
        per_line: dict[str, float] = {}
        for r in res:
            per_lot[r["lot"]] = per_lot.get(r["lot"], 0.) + r["physical_units"]
            per_line[r["line"]] = per_line.get(r["line"], 0.) + r["quantity"]
        lots = {r["lot"]: r["remaining_unreserved"] + r["promised_now"] for r in rep["remaining_supply"]}
        lines = {line.id: line.quantity for o in req.atp.orders for line in o.lines}
        refused = {u["line"]: u["quantity"] for u in rep["refused"]}
        ok = (len(set(ids)) == len(ids) and all(r["status"] == "PROPOSED" for r in res) and all(q <= lots[lot_id] + TOL for lot_id, q in per_lot.items())
              and all(abs(per_line.get(lid, 0.) + unmet.get(lid, 0.) + refused.get(lid, 0.) - q) < TOL for lid, q in lines.items())
              and all(all(r[k] for k in ("customer", "order", "line", "sku_requested", "lot", "location")) and r["promise_period"] >= 0 for r in res))
        ev["reservations"] = res
    elif name.startswith("I08"):
        firm = [p for p in rep["promised"] if p["lot"] == "transfer:firm1"]
        nf = rep["non_firm_availability"]
        ok = (abs(sum(p["quantity"] for p in firm) - 40.) < TOL and all(p["promise_period"] == 2 for p in firm) and abs(unmet.get("l1", 0.) - 60.) < TOL
              and len(nf) == 1 and nf[0]["id"] == "po:po_uncertain" and nf[0]["promised"] == 0. and nf[0]["quantity"] == 60.
              and rep["next_promise"]["l1"]["earliest_period_with_firm_supply"] is None and rep["next_promise"]["l1"]["earliest_period_with_non_firm_supply"] == 2)
        try:
            Request.model_validate({**req.model_dump(), "atp": {**req.atp.model_dump(), "inbound_confidence": .8}})
            refused_conf = False
        except ValidationError as exc:
            refused_conf = "probabilistic inbound" in str(exc)
        ok = ok and refused_conf
        ev["non_firm"] = nf
        ev["confidence_0.8_refused"] = refused_conf
    elif name.startswith("I09"):
        ok = abs(s.get("l1", 0.) - 50.) < TOL and abs(unmet.get("l1", 0.) - 30.) < TOL and abs(rep["unit_states"]["l1"]["balance_residual"]) < TOL
    elif name.startswith("I10"):
        b = engine(FIXTURES[name]["variant"]())
        sb = by_line(b)
        ok = s.get("l1", 0.) < TOL and abs(unmet.get("l1", 0.) - 80.) < TOL and abs(sb.get("l1", 0.) - 65.) < TOL
        ev["stock_65"] = sb
    elif name.startswith("I11"):
        late = [p for p in rep["promised"] if p["periods_late"] > 0]
        ok = abs(sum(p["quantity"] for p in late) - 50.) < TOL and all(p["promise_period"] == 2 for p in late) and not unmet and abs(rep["ledger"]["backorder_carry"] - 100.) < TOL
        ev["ledger"] = rep["ledger"]
    elif name.startswith("I12"):
        ok = all(p["periods_late"] == 0 for p in rep["promised"]) and abs(s.get("l1", 0.) - 50.) < TOL and abs(unmet.get("l1", 0.) - 50.) < TOL
    elif name.startswith("I13"):
        sub = [p for p in rep["promised"] if p["substitution"]]
        ok = abs(sum(p["quantity"] for p in sub) - 40.) < TOL and all(p["supplied_sku"] == "B" for p in sub) and abs(rep["ledger"]["substitution"] - 20.) < TOL and not unmet
        ev["ledger"] = rep["ledger"]
    elif name.startswith("I14"):
        ok = not any(p["substitution"] for p in rep["promised"]) and abs(s.get("l1", 0.) - 20.) < TOL and abs(unmet.get("l1", 0.) - 40.) < TOL
    elif name.startswith("I15"):
        swapped = engine(_identical(swap=True))
        none_a = engine(_identical(fairness="NONE"))
        none_b = engine(_identical(swap=True, fairness="NONE"))
        ok = (abs(s.get("l1", 0.) - 25.) < TOL and abs(s.get("l2", 0.) - 25.) < TOL and by_line(swapped) == s
              and by_line(none_a) == by_line(none_b) and abs(by_line(none_a).get("l1", 0.) - 50.) < TOL)
        ev["swapped"] = by_line(swapped)
        ev["fairness_none"] = by_line(none_a)
    elif name.startswith("I16"):
        ok = abs(s.get("l2", 0.) - 50.) < TOL and s.get("l1", 0.) < TOL and any("shortage penalty per unit 22.00 against 2.00" in w for w in rep["why"])
        ev["why"] = rep["why"]
    elif name.startswith("I17"):
        led = rep["ledger"]
        units = rep["unit_states"]
        drv = rep["drivers"]
        states = {k: sum(u[k] for u in units.values()) for k in ("on_time", "late", "substituted", "unmet", "refused")}
        alt = rep["fulfilment"]["alternative_ship_from_units"]
        expected = {"sla": sum(u["unmet"] * drv[lid]["sla_per_unmet"] for lid, u in units.items()),
                    "shortage_penalty": sum(u["unmet"] * drv[lid]["shortage_penalty_per_unit"] for lid, u in units.items()),
                    "refusal": sum(u["refused"] * drv[lid]["refusal_cost_per_unit"] for lid, u in units.items()),
                    "lost_contribution": sum((u["unmet"] + u["refused"]) * drv[lid]["lost_contribution_per_unit"] for lid, u in units.items()),
                    "backorder_carry": sum(u["late_unit_periods"] * drv[lid]["late_penalty_per_unit_period"] for lid, u in units.items())}
        ok = (set(led) == set(LEDGER_KEYS) and set(rep["ledger_owner"]) == set(LEDGER_KEYS) and abs(sum(led.values()) - rep["optimised_cost"]) < TOL
              and abs(sum(rep["incumbent_ledger"].values()) - rep["incumbent_cost"]) < TOL
              and all(abs(u["balance_residual"]) < TOL for u in units.values()) and all(abs(led[k] - v) < TOL for k, v in expected.items())
              and all(states[k] > 0 for k in ("on_time", "late", "substituted", "unmet", "refused")) and alt > 0 and led["alternative_ship_from"] > 0 and led["substitution"] > 0)
        ev.update(ledger=led, expected=expected, states=states, alternative_units=alt)
    elif name.startswith("I18"):
        ok = rep["verdict"].startswith("NO MATERIAL") and abs(rep["value_of_allocation"]) < TOL and rep["recommended_policy"] == "TIER_PRIORITY"
        ev["verdict"] = rep["verdict"]
    else:
        ok = False
    return {"pass": bool(ok), "evidence": ev}


def planner_i01(req) -> dict[str, Any]:
    t = time.perf_counter()
    with_block = plan(req)
    without = plan(Request.model_validate({**req.model_dump(), "atp": None}))
    identical = _frozen(with_block) == _frozen(without)
    rep = with_block["atp"]
    rows = rep["protection_overlay"]
    env = {(r["sku"], r["location"]): r for r in rep["supply_envelope"] if r["period"] == 0}
    served = {("A", "north"), ("A", "south")}   # the locations with an order: their whole allocatable stock is promised
    ok_rows = bool(rows) and all(r["hard_reservation"] is False and abs(r["below_protection_units"] - max(0., r["protection_units"] - r["remaining_after_promises"])) < TOL
                                 and ((r["sku"], r["location"]) not in served or abs(r["promised_from_on_hand"] - env[(r["sku"], r["location"])]["allocatable_atp"]) < TOL)
                                 for r in rows if (r["sku"], r["location"]) in env)
    ok = identical and ok_rows and served <= {(r["sku"], r["location"]) for r in rows} and rep["path"] == "planner" and rep["protection_overlay_available"]
    inv = invariants(req, rep)
    return {"pass": ok and all(inv.values()), "evidence": {"frozen_report_identical": identical, "overlay": rows, "verdict": rep["verdict"], "seconds": round(time.perf_counter() - t, 1)}, "invariants": inv}


def planner_i20(req, pre_p5_worktree: str | None) -> dict[str, Any]:
    a = plan(req)
    disabled = Request.model_validate({**req.model_dump(), "atp": {"enabled": False}})
    b = plan(disabled)
    ident = _frozen(a) == _frozen(b) and "atp" not in a and "atp" not in b and resolve(req) is None and resolve(disabled) is None
    ev: dict[str, Any] = {"disabled_identical": ident}
    pre_ok = None
    if pre_p5_worktree:
        with tempfile.TemporaryDirectory() as tmp:
            reqp = Path(tmp) / "req.json"
            outp = Path(tmp) / "out.json"
            payload = req.model_dump(mode="json")
            payload.pop("atp", None)
            reqp.write_text(json.dumps(payload, default=str))
            code = ("import json,sys\nfrom zaad.full.contracts import Request\nfrom zaad.full.planner import plan, report_json\n"
                    "r = Request.model_validate_json(open(sys.argv[1]).read())\nopen(sys.argv[2], 'w').write(report_json(plan(r)))\n")
            env = {**os.environ, "PYTHONPATH": pre_p5_worktree, "PYTHONHASHSEED": "0"}
            proc = subprocess.run([sys.executable, "-c", code, str(reqp), str(outp)], cwd=pre_p5_worktree, env=env, capture_output=True, text=True, timeout=1800)  # nosec B603 - fixed argv, no shell
            if proc.returncode != 0:
                ev["pre_p5_error"] = proc.stderr[-800:]
                pre_ok = False
            else:
                pre = json.loads(outp.read_text())
                pre_ok = _strip(report_json(pre)) == _strip(report_json(a))
                ev["pre_p5_runtime_identical"] = pre_ok
                if not pre_ok:
                    ka = set(a)
                    kp = set(pre)
                    ev["pre_p5_key_diff"] = {"only_now": sorted(ka - kp), "only_pre": sorted(kp - ka),
                                             "differing": [k for k in sorted(ka & kp) if _strip(json.dumps(a[k], sort_keys=True, default=str)) != _strip(json.dumps(pre[k], sort_keys=True, default=str))][:12]}
    return {"pass": bool(ident and (pre_ok is None or pre_ok)), "evidence": ev}


def api_i19(req) -> dict[str, Any]:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from api.dependencies import require_operator
    from api.routers import zaad_atp, zaad_full
    from api.routers.zaad import bounded_rate
    def app(operator):
        a = FastAPI()
        a.include_router(zaad_full.router)
        a.include_router(zaad_atp.router)
        a.dependency_overrides[require_operator] = lambda: operator
        a.dependency_overrides[bounded_rate] = lambda: None
        return a
    body = req.model_dump(mode="json")
    ev: dict[str, Any] = {}
    saved = os.environ.pop("ZAAD_ATP_ENABLED", None)
    try:
        c_off = TestClient(app(req.operator_id))
        r = c_off.post("/api/zaad/network/plan", json=body)
        ev["planner_flag_off"] = (r.status_code, (r.json().get("detail") or {}).get("code") if r.status_code == 422 else None)
        ev["standalone_flag_off"] = c_off.post("/api/zaad/atp/promise", json=body).status_code
        os.environ["ZAAD_ATP_ENABLED"] = "1"
        c_other = TestClient(app("someone_else"))
        ev["planner_other_tenant"] = c_other.post("/api/zaad/network/plan", json=body).status_code
        ev["standalone_other_tenant"] = c_other.post("/api/zaad/atp/promise", json=body).status_code
        ev["jobs_other_tenant"] = c_other.post("/api/zaad/network/jobs", json=body).status_code
    finally:
        if saved is None:
            os.environ.pop("ZAAD_ATP_ENABLED", None)
        else:
            os.environ["ZAAD_ATP_ENABLED"] = saved
    ok = (ev["planner_flag_off"] == (422, "atp_disabled") and ev["standalone_flag_off"] == 404 and ev["planner_other_tenant"] == 403
          and ev["standalone_other_tenant"] == 403 and ev["jobs_other_tenant"] == 403)
    return {"pass": ok, "evidence": ev}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="p5_integration")
    ap.add_argument("--pre-p5-worktree", default=None)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    for name, spec in FIXTURES.items():
        t = time.perf_counter()
        rec: dict[str, Any] = {"fixture": name, "path": spec["path"]}
        req = build(name)
        if spec["path"] == "engine":
            reps = [engine(req) for _ in range(3)]
            rep = reps[0]
            rec["deterministic"] = all(json.dumps(r["promised"], sort_keys=True) == json.dumps(rep["promised"], sort_keys=True) for r in reps[1:])
            rec["verdict"] = rep["verdict"]
            rec["incumbent_cost"] = rep["incumbent_cost"]
            rec["optimised_cost"] = rep["optimised_cost"]
            rec["value"] = rep["value_of_allocation"]
            rec["principle_result"] = principle(name, req, rep)
            rec["invariants"] = invariants(req, rep)
            rec["invariants"]["17_deterministic_ties"] = rec["deterministic"]
            rec["pass"] = bool(rec["principle_result"]["pass"] and all(rec["invariants"].values()))
        elif name.startswith("I01"):
            r = planner_i01(req)
            rec.update(principle_result={"pass": r["pass"], "evidence": r["evidence"]}, invariants=r["invariants"], verdict=r["evidence"]["verdict"], pass_=r["pass"])
            rec["pass"] = rec.pop("pass_")
        elif name.startswith("I20"):
            r = planner_i20(req, a.pre_p5_worktree)
            rec.update(principle_result=r, pass_=r["pass"])
            rec["pass"] = rec.pop("pass_")
        else:
            r = api_i19(req)
            rec.update(principle_result=r, pass_=r["pass"])
            rec["pass"] = rec.pop("pass_")
        rec["seconds"] = round(time.perf_counter() - t, 2)
        bad = [k for k, v in rec.get("invariants", {}).items() if not v]
        print(f"{name:44s} {'PASS' if rec['pass'] else 'FAIL'} {rec['seconds']:6.1f}s {str(rec.get('verdict', ''))[:34]:34s} {('INVARIANT FAIL ' + str(bad)) if bad else ''}", flush=True)
        records.append(rec)
    passed = sum(1 for r in records if r["pass"])
    (OUT / f"{a.tag}.json").write_text(json.dumps(records, indent=1, default=str))
    md = [f"# P5 shared-core integration matrix `{a.tag}`\n", f"{passed} / {len(records)} fixtures PASS (principle + invariants 1-19 on every recommendation; engine fixtures 3 runs identical)\n",
          "| fixture | path | verdict | incumbent | optimised | value | result |", "|---|---|---|---|---|---|---|"]
    for r in records:
        md.append(f"| {r['fixture']} | {r['path']} | {str(r.get('verdict', ''))[:40]} | {r.get('incumbent_cost', '-')} | {r.get('optimised_cost', '-')} | {r.get('value', '-')} | {'PASS' if r['pass'] else 'FAIL'} |")
    (OUT / f"{a.tag}.md").write_text("\n".join(md) + "\n")
    inv_names = sorted({k for r in records for k in r.get("invariants", {})})
    inv_md = ["# P5 invariants on the integration matrix (every recommendation)\n", "| invariant | fixtures failing |", "|---|---|"]
    for k in inv_names:
        failing = [r["fixture"] for r in records if k in r.get("invariants", {}) and not r["invariants"][k]]
        inv_md.append(f"| {k} | {failing or 'none'} |")
    inv_md.append("\n20_disabled_path_identity: I20 (planner, `enabled: false` and the pre-P5 runtime) and `tests/unit/test_zaad_atp.py::test_disabled_path_is_frozen`")
    (OUT / "P5_INTEGRATION_INVARIANTS.md").write_text("\n".join(inv_md) + "\n")
    print(f"{passed} / {len(records)} integration fixtures PASS")
    return 0 if passed == len(records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
