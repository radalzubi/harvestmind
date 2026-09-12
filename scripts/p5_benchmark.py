"""P5 fixture matrix + invariants (engine on the allocatable-supply envelope): runs every pre-registered fixture, checks its
principle and the release-level invariants 1-19 on the recommended allocation, writes
docs/zaad_full/evidence/p5/benchmarks/<tag>.{json,md} and P5_INVARIANTS.md. Engineering evidence only.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from zaad.atp.contracts import resolve
from zaad.atp.fixtures import FIXTURES, build
from zaad.atp.promise import promise
from zaad.atp.state import build_state

OUT = Path("docs/zaad_full/evidence/p5")
TOL = 1e-6


def shipped(rep, line):
    return sum(p["quantity"] for p in rep["promised"] if p["line"] == line)


def by_line(rep):
    out: dict[str, float] = {}
    for p in rep["promised"]:
        out[p["line"]] = out.get(p["line"], 0.) + p["quantity"]
    return out


def principle(name: str, kind: str, req, rep) -> dict[str, Any]:
    spec = req.atp
    s = by_line(rep)
    unmet = {u["line"]: u["quantity"] for u in rep["unfulfilled"]}
    if kind == "incumbent_retained":
        ok = rep["verdict"].startswith("NO MATERIAL") and all(abs(s.get(line.id, 0.) - line.quantity) < TOL and any(p["line"] == line.id and p["promise_period"] == line.requested_period for p in rep["promised"]) for o in spec.orders for line in o.lines)
        return {"pass": ok, "evidence": {"verdict": rep["verdict"], "shipped": s}}
    if kind == "higher_penalty_first":
        ok = rep["verdict"].startswith("ALLOCATION CHANGE") and abs(s.get("lX", 0.) - 50.) < TOL and abs(s.get("lY", 0.) - 10.) < TOL and abs(sum(s.values()) - 60.) < TOL and abs(unmet.get("lY", 0.) - 40.) < TOL
        return {"pass": ok, "evidence": {"shipped": s, "unmet": unmet, "why": rep["why"][:1]}}
    if kind == "higher_total_driver_first":
        ok = abs(s.get("lX", 0.) - 50.) < TOL and s.get("lY", 0.) < TOL and any("shortage penalty" in w for w in rep["why"]) and rep["value_of_allocation"] > 0
        return {"pass": ok, "evidence": {"shipped": s, "why": rep["why"][:1], "value": rep["value_of_allocation"]}}
    if kind == "every_line_share":
        ok = all(s.get(line.id, 0.) > TOL for o in spec.orders for line in o.lines) and abs(sum(s.values()) - 60.) < TOL
        return {"pass": ok, "evidence": {"shipped": s}}
    if kind == "all_or_nothing":
        forbidden = [line for o in spec.orders for line in o.lines if not o.partial_fulfillment_allowed]
        ok = all(abs(s.get(line.id, 0.)) < TOL or abs(s.get(line.id, 0.) - line.quantity) < TOL for line in forbidden) and sum(s.values()) <= 60. + TOL
        return {"pass": ok, "evidence": {"shipped": s}}
    if kind == "backordered_at_arrival":
        late = [p for p in rep["promised"] if p["periods_late"] > 0]
        ok = abs(sum(p["quantity"] for p in late) - 50.) < TOL and all(p["promise_period"] == 2 for p in late) and not unmet and abs(rep["ledger"]["backorder_carry"] - 50 * 2 * 1.) < TOL
        return {"pass": ok, "evidence": {"backordered": [(p["quantity"], p["promise_period"]) for p in late], "ledger": rep["ledger"]}}
    if kind == "no_late_promise":
        ok = all(p["periods_late"] == 0 for p in rep["promised"]) and abs(unmet.get("l1", 0.) - 50.) < TOL
        return {"pass": ok, "evidence": {"shipped": s, "unmet": unmet}}
    if kind == "own_dates":
        ok = all(p["promise_period"] == p["requested_period"] for p in rep["promised"]) and abs(s.get("la", 0.) - 40.) < TOL and abs(s.get("lb", 0.) - 40.) < TOL
        return {"pass": ok, "evidence": {"promised": [(p["line"], p["promise_period"]) for p in rep["promised"]]}}
    if kind == "inbound_counts":
        ok = abs(s.get("l1", 0.) - 60.) < TOL and all(p["promise_period"] == 2 for p in rep["promised"]) and not unmet
        return {"pass": ok, "evidence": {"shipped": s}}
    if kind == "inbound_excluded":
        ok = not rep["promised"] and abs(unmet.get("l1", 0.) - 60.) < TOL and rep["next_promise"]["l1"]["earliest_period_with_firm_supply"] == 4
        return {"pass": ok, "evidence": {"unmet": unmet, "next": rep["next_promise"]}}
    if kind == "alternative_priced":
        via = [p for p in rep["promised"] if p["ship_from"] == "central"]
        ok = abs(sum(p["quantity"] for p in via) - 50.) < TOL and all(p["lane"] for p in via) and abs(rep["ledger"]["alternative_ship_from"] - 50 * .2) < TOL and not unmet
        return {"pass": ok, "evidence": {"via_lane": [(p["quantity"], p["lane"], p["promise_period"]) for p in via], "ledger": rep["ledger"]}}
    if kind == "lead_respected_unmet":
        ok = all(p["ship_from"] == "north" for p in rep["promised"]) and abs(unmet.get("l1", 0.) - 50.) < TOL
        return {"pass": ok, "evidence": {"shipped": s, "unmet": unmet}}
    if kind == "lead_respected_backorder":
        via = [p for p in rep["promised"] if p["ship_from"] == "central"]
        ok = abs(sum(p["quantity"] for p in via) - 50.) < TOL and all(p["promise_period"] >= 1 for p in via) and not unmet
        return {"pass": ok, "evidence": {"via_lane": [(p["quantity"], p["promise_period"]) for p in via]}}
    if kind == "no_expiring_cohort":
        ok = all(p["lot"] != "stock:north_lot" for p in rep["promised"]) and abs(s.get("l1", 0.) - 100.) < TOL
        return {"pass": ok, "evidence": {"promised": [(p["lot"], p["quantity"], p["promise_period"]) for p in rep["promised"]]}}
    if kind == "no_ineligible_state":
        ok = all(p["ship_from"] == "north" and p["lane"] is None for p in rep["promised"]) and abs(s.get("l1", 0.) - 40.) < TOL and any("physics" in a for a in rep["assumptions"])
        return {"pass": ok, "evidence": {"promised": [(p["ship_from"], p["quantity"]) for p in rep["promised"]], "unmet": unmet}}
    if kind == "floor_met":
        ok = s.get("lF", 0.) >= .8 * 50. - 1e-6 and abs(sum(s.values()) - 60.) < TOL
        return {"pass": ok, "evidence": {"shipped": s}}
    if kind == "deterministic_tie":
        ok = abs(s.get("l1", 0.) - 50.) < TOL and s.get("l2", 0.) < TOL
        return {"pass": ok, "evidence": {"shipped": s}}
    if kind == "proportional_tie":
        ok = abs(s.get("l1", 0.) - 25.) < TOL and abs(s.get("l2", 0.) - 25.) < TOL
        return {"pass": ok, "evidence": {"shipped": s}}
    if kind == "incumbent_retained_zero_value":
        ok = rep["verdict"].startswith("NO MATERIAL") and abs(rep["value_of_allocation"]) < TOL and rep["recommended_policy"] == "TIER_PRIORITY"
        return {"pass": ok, "evidence": {"value": rep["value_of_allocation"], "policy": rep["recommended_policy"]}}
    if kind == "strategic_through_economics":
        from zaad.atp.fixtures import _R_flag_only
        flag_only = promise(_R_flag_only())
        s2 = by_line(flag_only)
        ok = abs(s.get("lK", 0.) - 50.) < TOL and any("board-2026-09" in json.dumps(rep["service_classes"]) for _ in [0]) and flag_only["verdict"].startswith("NO MATERIAL") and abs(s2.get("lS", 0.) - 50.) < TOL
        return {"pass": ok, "evidence": {"with_penalty": s, "flag_only": s2, "flag_only_verdict": flag_only["verdict"]}}
    if kind == "reserved_never_promised":
        ok = sum(s.values()) <= 40. + TOL and all(r["reserved_before"] == 60. for r in rep["remaining_supply"]) and abs(sum(s.values()) - 40.) < TOL
        return {"pass": ok, "evidence": {"shipped": s, "remaining": rep["remaining_supply"]}}
    if kind == "declared_substitute_used":
        from zaad.atp.fixtures import _U_not_allowed
        sub = [p for p in rep["promised"] if p["substitution"]]
        blocked = promise(_U_not_allowed())
        ok = abs(sum(p["quantity"] for p in sub) - 40.) < TOL and all(p["supplied_sku"] == "B" for p in sub) and abs(rep["ledger"]["substitution"] - 40 * .5) < TOL \
            and not any(p["substitution"] for p in blocked["promised"]) and abs({u["line"]: u["quantity"] for u in blocked["unfulfilled"]}.get("l1", 0.) - 40.) < TOL
        return {"pass": ok, "evidence": {"substituted": [(p["quantity"], p["supplied_sku"], p["substitution"]) for p in sub], "blocked_unmet": blocked["unfulfilled"]}}
    if kind == "each_line_own_physics":
        ok = abs(s.get("la", 0.) - 30.) < TOL and abs(s.get("lb", 0.) - 40.) < TOL and all(p["lot"] != "stock:b_north_old" for p in rep["promised"]) and rep["approval_required"]
        return {"pass": ok, "evidence": {"promised": [(p["line"], p["lot"], p["quantity"], p["promise_period"]) for p in rep["promised"]]}}
    return {"pass": False, "evidence": f"unknown principle {kind}"}


def invariants(req, rep) -> dict[str, Any]:
    """Release-level invariants 1-19 on the recommended allocation."""
    atp = resolve(req)
    spec = atp.spec
    state = build_state(req, atp)
    lots = {lot.id: lot for lot in state.lots}
    lines = {line.id: (o, line) for o in spec.orders for line in o.lines}
    out: dict[str, bool] = {}
    drawn: dict[str, float] = {}
    for p in rep["promised"]:
        ratio = 1.
        if p["substitution"]:
            rule = next(r for r in req.substitutions if r.id == p["substitution"])
            ratio = rule.input_per_output / rule.service_equivalence
        drawn[p["lot"]] = drawn.get(p["lot"], 0.) + p["quantity"] * ratio
    out["01_no_unit_twice"] = all(q <= lots[lot_id].quantity + 1e-6 for lot_id, q in drawn.items())
    out["02_within_usable_unreserved"] = all(lots[lot_id].quantity <= lots[lot_id].physical - lots[lot_id].unusable - lots[lot_id].reserved + 1e-6 for lot_id in drawn)
    units = rep["unit_states"]
    out["03_reservation_conservation"] = all(abs(u["balance_residual"]) < 1e-6 for u in units.values())
    out["04_promise_period_feasible"] = all(p["promise_period"] >= max(lines[p["line"]][0].order_period, 0) and p["promise_period"] >= lots[p["lot"]].available_from + (next(ln.lead for ln in state.lanes if ln.id == p["lane"]) if p["lane"] else 0) for p in rep["promised"])
    services = {(s.customer, s.sku): s for s in req.services}
    out["05_location_feasible"] = all((p["ship_from"] in (set(lines[p["line"]][1].ship_from) or {services[lines[p["line"]][0].customer, lines[p["line"]][1].sku].location}) or p["lane"] is not None) and state.location_ok(p["supplied_sku"], p["ship_from"]) for p in rep["promised"])
    out["06_lane_lead_respected"] = all(p["promise_period"] - next(ln.lead for ln in state.lanes if ln.id == p["lane"]) >= lots[p["lot"]].available_from for p in rep["promised"] if p["lane"])
    tot = {}
    for p in rep["promised"]:
        tot[p["line"]] = tot.get(p["line"], 0.) + p["quantity"]
    out["07_minimum_ship"] = all(tot.get(lid, 0.) < 1e-6 or tot.get(lid, 0.) >= line.minimum_ship_quantity - 1e-6 for lid, (o, line) in lines.items())
    out["08_partial_rule"] = all(o.partial_fulfillment_allowed or tot.get(lid, 0.) < 1e-6 or abs(tot.get(lid, 0.) - line.quantity) < 1e-6 for lid, (o, line) in lines.items())
    out["09_backorder_rule"] = all(p["promise_period"] <= p["requested_period"] + (lines[p["line"]][0].max_backorder_periods if lines[p["line"]][0].backorder_allowed else 0) for p in rep["promised"])
    out["10_provenance_valid"] = all((not c.strategic) or (c.provenance == "OPERATOR_DECLARED" and c.reference) for c in spec.service_classes)
    out["11_no_negative"] = all(p["quantity"] >= 0 for p in rep["promised"]) and all(u["quantity"] >= 0 for u in rep["unfulfilled"] + rep["refused"])
    out["12_sector_rules"] = all(state.sellable(lots[p["lot"]], p["promise_period"]) for p in rep["promised"])
    out["13_ledger_reconciles"] = abs(sum(rep["ledger"].values()) - rep["optimised_cost"]) < 1e-3 and abs(sum(rep["incumbent_ledger"].values()) - rep["incumbent_cost"]) < 1e-3
    out["14_no_source_leakage"] = not any(k in json.dumps(rep) for k in ('"purchase"', '"source_decomposition"', '"supplier_order"'))
    out["15_no_purchase_leakage"] = sum(drawn.values()) <= sum(lot.quantity for lot in state.lots) + 1e-6
    out["16_no_future_information"] = all(lots[p["lot"]].available_from <= p["promise_period"] for p in rep["promised"])
    out["18_approval"] = rep["approval_required"] is True and rep["executable_promise"] is False
    out["19_incumbent_first"] = (rep["recommended_policy"] == spec.incumbent_policy) == (not rep["material"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="p5_dev")
    a = ap.parse_args()
    (OUT / "benchmarks").mkdir(parents=True, exist_ok=True)
    records = []
    for name, spec in FIXTURES.items():
        t = time.perf_counter()
        rec: dict[str, Any] = {"fixture": name, "principle": spec["principle"]}
        try:
            req = build(name)
        except ValidationError as exc:
            rec.update(refused_at_contract=str(exc)[:160], pass_=spec["principle"] == "refused_at_contract", seconds=round(time.perf_counter() - t, 2))
            rec["pass"] = rec.pop("pass_")
            records.append(rec)
            print(f"{name:30s} {'PASS' if rec['pass'] else 'FAIL'} refused at contract", flush=True)
            continue
        reps = [promise(req) for _ in range(3)]
        rep = reps[0]
        rec["deterministic"] = all(json.dumps(r["promised"], sort_keys=True) == json.dumps(rep["promised"], sort_keys=True) for r in reps[1:])
        rec["verdict"] = rep["verdict"]
        rec["incumbent_cost"] = rep["incumbent_cost"]
        rec["optimised_cost"] = rep["optimised_cost"]
        rec["value"] = rep["value_of_allocation"]
        rec["engine"] = rep["engineering"]
        rec["principle_result"] = principle(name, spec["principle"], req, rep)
        rec["invariants"] = invariants(req, rep)
        rec["invariants"]["17_deterministic_ties"] = rec["deterministic"]
        rec["pass"] = bool(rec["principle_result"]["pass"] and all(rec["invariants"].values()))
        rec["seconds"] = round(time.perf_counter() - t, 2)
        bad = [k for k, v in rec["invariants"].items() if not v]
        print(f"{name:30s} {'PASS' if rec['pass'] else 'FAIL'} {rec['seconds']:5.1f}s {rep['verdict'][:32]:32s} value={rep['value_of_allocation']} {('INVARIANT FAIL ' + str(bad)) if bad else ''}", flush=True)
        records.append(rec)
    passed = sum(1 for r in records if r["pass"])
    (OUT / "benchmarks" / f"{a.tag}.json").write_text(json.dumps(records, indent=1, default=str))
    md = [f"# P5 fixture matrix `{a.tag}`\n", f"{passed} / {len(records)} fixtures PASS (principle + invariants 1-19 on the recommended allocation; 3 runs identical)\n",
          "| fixture | principle | verdict | incumbent | optimised | value | result |", "|---|---|---|---|---|---|---|"]
    for r in records:
        md.append(f"| {r['fixture']} | {r['principle']} | {r.get('verdict', r.get('refused_at_contract', ''))[:40]} | {r.get('incumbent_cost', '-')} | {r.get('optimised_cost', '-')} | {r.get('value', '-')} | {'PASS' if r['pass'] else 'FAIL'} |")
    (OUT / "benchmarks" / f"{a.tag}.md").write_text("\n".join(md) + "\n")
    inv_names = sorted({k for r in records for k in r.get("invariants", {})})
    inv_md = ["# P5 invariants (isolated engine, every fixture)\n", "| invariant | fixtures failing |", "|---|---|"]
    for k in inv_names:
        failing = [r["fixture"] for r in records if k in r.get("invariants", {}) and not r["invariants"][k]]
        inv_md.append(f"| {k} | {failing or 'none'} |")
    inv_md.append("\n20_disabled_path_identity: `tests/unit/test_zaad_atp.py::test_disabled_path_is_frozen`")
    (OUT / "P5_INVARIANTS.md").write_text("\n".join(inv_md) + "\n")
    print(f"{passed} / {len(records)} fixtures PASS")
    return 0 if passed == len(records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
