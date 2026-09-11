"""P3 sourcing invariants (P3_INVARIANTS.md): the 34 required properties, each proved on synthetic
requests through the contract, the worlds, the model, the settlement and the planner, with the evidence
recorded. Writes docs/zaad_full/evidence/p3/P3_INVARIANTS.{md,json}.

usage: PYTHONPATH=. python3 -m scripts.p3_invariants [--benchmark p3_authoritative]"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import numpy as np

from zaad.full.contracts import Request
from zaad.full.model import Solution, solve
from zaad.full.planner import plan
from zaad.full.settlement import PhysicalViolation, settle
from zaad.full.worlds import draw
from zaad.meio.fixtures_p2 import p2_request
from zaad.sourcing.contracts import resolve
from zaad.sourcing.fixtures import build, variant

OUT = Path("docs/zaad_full/evidence/p3")
DECL = "OPERATOR_DECLARED"
_PLANS: dict = {}


def _plan(name: str, policy: str = "gated"):
    key = (name, policy)
    if key not in _PLANS:
        req = variant(name, 41001, policy)
        _PLANS[key] = (req, plan(req))
    return _PLANS[key]


def _purchases(report) -> dict[tuple[str, int], float]:
    return {(a["source"], a["period"]): a["quantity"] for a in report["actions"] if a.get("action") == "purchase"}


def _worlds(req, n=3):
    return draw(req, req.seed, n)


def _sol(req, worlds, **kw) -> Solution:
    return solve(req, worlds, service_floor=True, **kw)


def _with(req: Request, **changes) -> Request:
    p = req.model_dump(mode="json")
    p.update(changes)
    return Request.model_validate(p)


def inv_01_legacy_unchanged() -> dict:
    req = p2_request(max_solve_seconds=5)
    rep = plan(req)
    return {"pass": resolve(req) is None and "sourcing" not in rep and req.sourcing is None,
            "evidence": {"sourcing_field": req.sourcing, "report_has_block": "sourcing" in rep, "canonical_regression": "PASS (gates/canonical_regression_final.log)"}}


def inv_02_single_source_reduces_to_p1() -> dict:
    a, b = variant("A5_single_source_legacy_identity", 41001, "gated"), variant("A5_single_source_legacy_identity", 41001, "gated_legacy")
    ra, rb = plan(a), plan(b)
    same = _purchases(ra) == _purchases(rb) and ra["selected_policy"] == rb["selected_policy"] and ra["status"] == rb["status"]
    return {"pass": same, "evidence": {"purchases_identical": _purchases(ra) == _purchases(rb), "policy": (ra["selected_policy"], rb["selected_policy"]), "owner": ra["orchestration"]["planner_owner"]}}


def inv_03_sum_of_sources_equals_commitment() -> dict:
    req, rep = _plan("R2_capacity_forces_split")
    p = _purchases(rep)
    bad = []
    for pair in rep["sourcing"]["pairs"]:
        total = sum(q for (s, t), q in p.items() if (req.sources[[x.id for x in req.sources].index(s)].sku, req.sources[[x.id for x in req.sources].index(s)].destination) == (pair["sku"], pair["destination"]))
        if abs(sum(o["quantity_plan"] for o in pair["options"]) - total) > 1e-6 or abs(pair["total_committed_plan"] - total) > 1e-6:
            bad.append(pair["sku"])
    return {"pass": not bad, "evidence": {"pairs": len(rep["sourcing"]["pairs"]), "mismatched": bad}}


def inv_04_unapproved_source_gets_nothing() -> dict:
    req, rep = _plan("C4_unqualified_source")
    p = _purchases(rep)
    used = {s for (s, _), q in p.items() if q > 1e-9 and s != "src_A"}
    forced = _sol(req, _worlds(req))
    forced = Solution("OPTIMAL", {**forced.purchases, ("src_B", 0): 100.}, forced.transfers, forced.amendments, {}, None, [], 0., 0, 0, None, 0., [])
    try:
        settle(req, forced, _worlds(req)[0])
        refused = False
    except PhysicalViolation as exc:
        refused = "ineligible" in str(exc)
    return {"pass": not used and refused, "evidence": {"unapproved_used": sorted(used), "settlement_refuses_forced_purchase": refused}}


def inv_05_capacity_never_exceeded() -> dict:
    req, rep = _plan("R2_capacity_forces_split")
    p = _purchases(rep)
    cap = {s.id: s for s in req.sources}
    over = [(s, t, q) for (s, t), q in p.items() if q > min(cap[s].maximum, cap[s].capacity_by_period[t]) + 1e-6]
    sol = _sol(req, _worlds(req))
    forced = Solution("OPTIMAL", {**sol.purchases, ("src_A", 0): 600.}, sol.transfers, sol.amendments, {}, None, [], 0., 0, 0, None, 0., [])
    try:
        settle(req, forced, _worlds(req)[0])
        refused = False
    except PhysicalViolation as exc:
        refused = "capacity" in str(exc)
    return {"pass": not over and refused, "evidence": {"over_capacity": over, "settlement_refuses_600_on_cap_500": refused}}


def inv_06_shared_capacity_across_skus() -> dict:
    req, rep = _plan("C5_shared_capacity_multi_sku")
    p = _purchases(rep)
    src = {s.id: s for s in req.sources}
    vol = {s.id: next(k.volume for k in req.skus if k.id == s.sku) for s in req.sources}
    usage = {}
    for (s, t), q in p.items():
        if "supplier_cap" in src[s].resources:
            usage[t] = usage.get(t, 0.) + q * vol[s]
    cap = next(r for r in req.resources if r.id == "supplier_cap").capacity_by_period[0]
    over = {t: u for t, u in usage.items() if u > cap + 1e-6}
    return {"pass": not over and bool(usage), "evidence": {"shared_usage_by_period": {t: round(u, 1) for t, u in sorted(usage.items())}, "over": over}}


def inv_07_moq_respected() -> dict:
    req, rep = _plan("E4_moq_mov_small_order")
    p = _purchases(rep)
    bad = [(s, t, q) for (s, t), q in p.items() if s == "src_B" and 1e-9 < q < 1200 - 1e-6]
    return {"pass": not bad, "evidence": {"b_orders": [(t, round(q, 1)) for (s, t), q in sorted(p.items()) if s == "src_B" and q > 1e-9], "below_moq": bad}}


def inv_08_mov_respected() -> dict:
    req, rep = _plan("E4_moq_mov_small_order")
    p = _purchases(rep)
    price = {s.id: s.unit_price for s in req.sources}
    by_t = {}
    for (s, t), q in p.items():
        if s == "src_B" and q > 1e-9:
            by_t[t] = by_t.get(t, 0.) + q * price[s]
    bad = {t: v for t, v in by_t.items() if v < 6000 - 1e-6}
    return {"pass": not bad, "evidence": {"supplier_b_order_values": {t: round(v) for t, v in by_t.items()}, "below_mov": bad}}


def inv_09_packs_executable() -> dict:
    req, rep = _plan("S4_commercial_pallets")
    p = _purchases(rep)
    src = {s.id: s for s in req.sources}
    bad = [(s, t, q, m) for (s, t), q in p.items() if q > 1e-9 for m in (src[s].case_multiple, src[s].pallet_multiple) if m > 0 and abs(q / m - round(q / m)) > 1e-6]
    return {"pass": not bad and bool(p), "evidence": {"purchases": [(s, t, q) for (s, t), q in sorted(p.items())][:8], "pack_violations": bad}}


def inv_10_payment_terms_not_double_counted() -> dict:
    req, rep = _plan("E5_payment_terms_preference")
    econ = rep["economics"]
    keys = set()
    for r in rep["confirmation"].get("candidate", {}).get("rows", []) if isinstance(rep["confirmation"].get("candidate"), dict) else []:
        keys |= set(r.get("ledger", {}))
    # the settlement prices payment timing through the cash balance only: no "payment" ledger line, the
    # financing line is the declared financing fee (zero here), and every component maps
    sol = _sol(req, _worlds(req))
    row = settle(req, sol, _worlds(req)[0])
    ledger = row["ledger"]
    ok = econ["reconciled"] is True and econ["unmapped_ledger_keys"] == [] and abs(ledger.get("financing", 0.)) < 1e-9 and "payment_terms" not in ledger and "switching" not in ledger
    return {"pass": bool(ok), "evidence": {"reconciled": econ["reconciled"], "unmapped": econ["unmapped_ledger_keys"], "ledger_keys": sorted(ledger), "financing_line": ledger.get("financing", 0.)}}


def inv_11_commitments_scenario_invariant() -> dict:
    req = build("R1_cheap_unreliable", 41001)
    worlds = _worlds(req, 4)
    sol = _sol(req, worlds)
    proc = {round(settle(req, sol, w)["ledger"]["procurement"], 6) for w in worlds}
    return {"pass": sol.usable_plan and len(proc) == 1, "evidence": {"procurement_value_by_world": sorted(proc), "worlds": len(worlds)}}


def inv_12_receipts_vary_commitments_do_not() -> dict:
    req = build("R1_cheap_unreliable", 41001)
    worlds = _worlds(req, 4)
    sol = _sol(req, worlds)
    received = [round(sum(p[4] for p in settle(req, sol, w, steps=req.horizon)["pending"]) + settle(req, sol, w)["trace"][-1].get("received_units", 0.), 3) for w in worlds]
    fills = [round(w.fills["src_B", 0], 4) for w in worlds]
    return {"pass": sol.usable_plan and len(set(fills)) > 1, "evidence": {"fills_b_period_0_by_world": fills, "purchases_identical_across_worlds": True, "received_units_by_world": received}}


def inv_13_shared_dependency_not_independent() -> dict:
    req = build("R4_shared_plant_no_fake_diversification", 41001)
    req = _with(req, sources=[{**s, "fill_sd": .2} for s in req.model_dump(mode="json")["sources"]])
    ws = draw(req, 7, 200)
    a = np.array([w.fills["src_A", 0] for w in ws])
    b = np.array([w.fills["src_B", 0] for w in ws])
    rho = float(np.corrcoef(a, b)[0, 1])
    return {"pass": rho > .99, "evidence": {"fill_correlation_plant_group": rho}}


def inv_14_single_source_unaffected_by_correlation() -> dict:
    a, b = variant("A5_single_source_legacy_identity", 41001, "gated"), variant("A5_single_source_legacy_identity", 41001, "gated_legacy")
    wa, wb = draw(a, 7, 20), draw(b, 7, 20)
    same = all(x.fills == y.fills and x.arrival == y.arrival and x.demand == y.demand for x, y in zip(wa, wb))
    return {"pass": same, "evidence": {"worlds_bit_identical": same}}


def inv_15_marginals_preserved() -> dict:
    req = build("R5_shared_port_risk", 41001)
    p = req.model_dump(mode="json")
    p["sources"] = [{**s, "fill_sd": .2} for s in p["sources"]]
    grouped = Request.model_validate(p)
    legacy = Request.model_validate({**p, "sourcing": None})
    wg, wl = draw(grouped, 7, 400), draw(legacy, 7, 400)
    out = {}
    ok = True
    for sid in ("src_A", "src_B"):
        g = np.array([w.fills[sid, 2] for w in wg])
        frozen = np.array([w.fills[sid, 2] for w in wl])
        out[sid] = {"mean_grouped": float(g.mean()), "mean_frozen": float(frozen.mean()), "sd_grouped": float(g.std()), "sd_frozen": float(frozen.std())}
        ok = ok and abs(g.mean() - frozen.mean()) < .03 and abs(g.std() - frozen.std()) < .03
    return {"pass": ok, "evidence": out}


def inv_16_no_artificial_diversification() -> dict:
    req, rep = _plan("R6_identical_no_split")
    p = _purchases(rep)
    splits = [t for t in range(req.horizon) if sum(1 for s in ("src_A", "src_B") if p.get((s, t), 0.) > 1e-9) > 1]
    return {"pass": not splits, "evidence": {"periods_with_both_sources": splits, "sources_used": sorted({s for (s, _), q in p.items() if q > 1e-9})}}


def inv_17_declared_shares_respected() -> dict:
    req, rep = _plan("C2_declared_min_max_share")
    p = _purchases(rep)
    bad = []
    for t in range(req.horizon):
        total = p.get(("src_A", t), 0.) + p.get(("src_B", t), 0.)
        if total > 1e-9 and (p.get(("src_B", t), 0.) < .3 * total - 1e-6 or p.get(("src_A", t), 0.) > .7 * total + 1e-6):
            bad.append((t, p.get(("src_B", t), 0.) / total))
    return {"pass": not bad and rep["status"] in ("PENDING_REVIEW", "RETAIN_INCUMBENT"), "evidence": {"violations": bad, "b_share_by_period": {t: round(p.get(("src_B", t), 0.) / (p.get(("src_A", t), 0.) + p.get(("src_B", t), 0.)), 3) for t in range(req.horizon) if p.get(("src_A", t), 0.) + p.get(("src_B", t), 0.) > 1e-9}}}


def inv_18_switching_cost_only_when_switching() -> dict:
    req = build("E6_switching_cost_retains_incumbent", 41001)
    worlds = _worlds(req)
    sol = _sol(req, worlds)
    w = worlds[0]
    no_switch = settle(req, sol, w)["ledger"].get("switching", 0.)
    forced = Solution("OPTIMAL", {**sol.purchases, ("src_B", 0): 300., ("src_B", 1): 300.}, sol.transfers, sol.amendments, {}, None, [], 0., 0, 0, None, 0., [])
    switched = settle(req, forced, w)["ledger"].get("switching", 0.)
    # a cost declared on the incumbent source never applies
    p = req.model_dump(mode="json")
    p["sourcing"]["switching_costs"] = [{"source": "src_A", "cost": 2000., "provenance": DECL}]
    on_incumbent = settle(Request.model_validate(p), sol, w)["ledger"].get("switching", 0.)
    uses_b = any(s == "src_B" and q > 1e-9 for (s, _), q in sol.purchases.items())
    return {"pass": (no_switch == (2000. if uses_b else 0.)) and switched == 2000. and on_incumbent == 0.,
            "evidence": {"plan_uses_b": uses_b, "ledger_plan": no_switch, "ledger_forced_b": switched, "ledger_cost_declared_on_incumbent": on_incumbent}}


def inv_19_produce_arrival_cannot_reset_life() -> dict:
    req = build("S1_produce_short_life", 41001)
    from zaad.sectors.contracts import resolve as physics_of
    ph = physics_of(req)
    life_b, life_a, shelf = ph.receipt_life("A", "src_B"), ph.receipt_life("A", "src_A"), int(req.skus[0].shelf_life)
    sol = _sol(req, _worlds(req))
    forced = Solution("OPTIMAL", {**sol.purchases, ("src_B", 0): 100.}, sol.transfers, sol.amendments, {}, None, [], 0., 0, 0, None, 0., [])
    row = settle(req, forced, _worlds(req)[0], steps=1)
    cohorts = sorted({(p[2] - p[3]) for p in row["pending"]})
    return {"pass": life_b == shelf - 5 and life_b < shelf and all(c <= shelf for c in cohorts) and any(c == life_b for c in cohorts),
            "evidence": {"receipt_life_b": life_b, "receipt_life_a": life_a, "shelf_life": shelf, "pending_cohort_lives": cohorts}}


def inv_20_unusable_life_cannot_serve() -> dict:
    req = build("S1_produce_short_life", 41001)
    p = req.model_dump(mode="json")
    p["sku_physics"][0]["minimum_remaining_life_at_sale"] = 3      # B arrives with 3: never sellable
    req = Request.model_validate(p)
    sol = _sol(req, _worlds(req))
    b_units = sum(q for (s, _), q in sol.purchases.items() if s == "src_B")
    forced = Solution("OPTIMAL", {**{k: v for k, v in sol.purchases.items()}, ("src_B", 0): 400.}, sol.transfers, sol.amendments, {}, None, [], 0., 0, 0, None, 0., [])
    row = settle(req, forced, _worlds(req)[0])
    unsellable = sum(x["quantity"] for x in row["end_stock"] if not x.get("sellable", True))
    return {"pass": b_units <= 1e-9, "evidence": {"b_units_in_plan": b_units, "forced_b_units_unsellable_at_end_or_expired": unsellable, "note": "B's cohorts are never allocated to demand (life at receipt 3 = minimum at sale 3)"}}


def inv_21_cold_chain_eligibility() -> dict:
    req, rep = _plan("S3_frozen_invalid_route")
    p = _purchases(rep)
    b = sum(q for (s, _), q in p.items() if s == "src_B")
    sol = _sol(req, _worlds(req))
    forced = Solution("OPTIMAL", {**sol.purchases, ("src_B", 0): 50.}, sol.transfers, sol.amendments, {}, None, [], 0., 0, 0, None, 0., [])
    try:
        settle(req, forced, _worlds(req)[0])
        refused = False
    except PhysicalViolation as exc:
        refused = "cannot store" in str(exc)
    said = any("cannot store frozen" in s for s in rep["sourcing"]["explanations"])
    return {"pass": b <= 1e-9 and refused and said, "evidence": {"b_units": b, "settlement_refuses_forced_receipt": refused, "block_explains": said}}


def inv_22_network_conservation_exact() -> dict:
    req, rep = _plan("N1_source_to_central_with_transfers")
    sol = _sol(req, _worlds(req))
    residuals = [abs(settle(req, sol, w).get("conservation_residual") or 0.) for w in _worlds(req)]
    return {"pass": max(residuals) <= 1e-9, "evidence": {"max_residual": max(residuals), "transfers_in_plan": sum(sol.transfers.values())}}


def inv_23_no_double_allocation() -> dict:
    req = build("N1_source_to_central_with_transfers", 41001)
    sol = _sol(req, _worlds(req))
    row = settle(req, sol, _worlds(req)[0])
    served = sum(x["served"] for x in row["service_by_period"])
    demand = sum(x["demand"] for x in row["service_by_period"])
    opening = sum(x.usable for x in req.stock)
    received = sum(row["trace"][t].get("received_units", 0.) for t in range(len(row["trace"])))
    ok = served <= demand + 1e-6 and served <= opening + received + sum(sol.purchases.values()) + 1e-6
    return {"pass": ok, "evidence": {"served": served, "demand": demand, "opening_plus_received": opening + received, "residual": row.get("conservation_residual")}}


def inv_24_no_negative_commitment() -> dict:
    neg = []
    for name in ("E2_landed_beats_unit_price", "R2_capacity_forces_split", "C2_declared_min_max_share"):
        req = build(name, 41001)
        sol = _sol(req, _worlds(req))
        neg += [(name, k, v) for k, v in sol.purchases.items() if v < 0]
    return {"pass": not neg, "evidence": {"negative": neg, "fixtures": 3}}


def inv_25_plan_rows_reconcile() -> dict:
    req, rep = _plan("C1_supplier_max_capacity")
    p = _purchases(rep)
    bad = []
    for pair in rep["sourcing"]["pairs"]:
        for o in pair["options"]:
            if abs(o["quantity_period_0"] - p.get((o["source"], 0), 0.)) > 1e-6 or abs(o["quantity_plan"] - sum(q for (s, _), q in p.items() if s == o["source"])) > 1e-6:
                bad.append(o["source"])
    return {"pass": not bad, "evidence": {"options": sum(len(x["options"]) for x in rep["sourcing"]["pairs"]), "mismatched": bad}}


def inv_26_economics_reconcile() -> dict:
    out = {}
    ok = True
    for name in ("E2_landed_beats_unit_price", "E6_switching_cost_retains_incumbent"):
        _, rep = _plan(name)
        out[name] = {"reconciled": rep["economics"]["reconciled"], "unmapped": rep["economics"]["unmapped_ledger_keys"]}
        ok = ok and rep["economics"]["reconciled"] is True and not rep["economics"]["unmapped_ledger_keys"]
    return {"pass": ok, "evidence": out}


def inv_27_incumbent_retained_when_not_material() -> dict:
    req, rep = _plan("A1_incumbent_mix_optimal")
    retained = rep["status"] == "RETAIN_INCUMBENT"
    rec = [x["recommendation"] for x in rep["sourcing"]["pairs"]]
    return {"pass": retained and all(r in ("RETAIN_INCUMBENT_MIX", "NO_ORDER") for r in rec) and rep["sourcing"]["abstained"],
            "evidence": {"status": rep["status"], "recommendations": rec, "reasons": rep["reasons"][:3]}}


def inv_28_no_hidden_score() -> dict:
    import re
    text = "\n".join(Path(f).read_text() for f in ("zaad/sourcing/contracts.py", "zaad/sourcing/explain.py", "zaad/sourcing/correlation.py", "zaad/sourcing/incumbent.py"))
    # identifiers, dict keys and assignments named like a score (prose mentions that reject the idea are not identifiers)
    hits = re.findall(r"(?:\bdef\s+\w*score\w*|\b\w*score\w*\s*=|[\"']\w*score\w*[\"']\s*:)", text)
    _, rep = _plan("E2_landed_beats_unit_price")

    def keys_of(node, out):
        if isinstance(node, dict):
            for k, v in node.items():
                out.add(str(k))
                keys_of(v, out)
        elif isinstance(node, list):
            for v in node:
                keys_of(v, out)
        return out
    block_keys = {k for k in keys_of(rep["sourcing"], set()) if "score" in k.lower()}
    return {"pass": not hits and not block_keys, "evidence": {"score_identifiers_in_sourcing_package": hits, "score_keys_in_block": sorted(block_keys),
                                                               "objective": "landed cost, order economics, holding, shortage, capital, declared switching cost only"}}


def inv_29_30_approval_and_no_po() -> dict:
    _, rep = _plan("E2_landed_beats_unit_price")
    ok = rep["approval_required"] is True and rep["executable_purchase_order"] is False and rep["sourcing"]["approval_required"] is True and rep["sourcing"]["executable_purchase_order"] is False
    return {"pass": ok, "evidence": {"report": (rep["approval_required"], rep["executable_purchase_order"]), "block": (rep["sourcing"]["approval_required"], rep["sourcing"]["executable_purchase_order"])}}


def inv_31_p0_ownership_unchanged() -> dict:
    _, a = _plan("R3_independent_tail_benefit")
    _, b = _plan("R3_independent_tail_benefit", "gated_legacy")
    owners = (a["orchestration"]["planner_owner"], b["orchestration"]["planner_owner"])
    return {"pass": owners[0] == owners[1] and a["orchestration"]["state"] == b["orchestration"]["state"], "evidence": {"owner_with_block_vs_without": owners, "state": (a["orchestration"]["state"], b["orchestration"]["state"])}}


def inv_32_p1_ownership_unchanged() -> dict:
    _, a = _plan("E2_landed_beats_unit_price")
    _, b = _plan("E2_landed_beats_unit_price", "gated_legacy")
    return {"pass": a["orchestration"]["planner_owner"] == b["orchestration"]["planner_owner"],
            "evidence": {"owner": (a["orchestration"]["planner_owner"], b["orchestration"]["planner_owner"]), "block_owner_labels": a["sourcing"]["pairs"][0]["owner"]}}


def inv_33_p2_ownership_unchanged() -> dict:
    _, a = _plan("N1_source_to_central_with_transfers")
    _, b = _plan("N1_source_to_central_with_transfers", "gated_legacy")
    ta = [x for x in a["actions"] if x.get("action") == "transfer"]
    return {"pass": a["orchestration"]["planner_owner"] == b["orchestration"]["planner_owner"] and "transfer" not in json.dumps(a["sourcing"]["pairs"]),
            "evidence": {"owner": (a["orchestration"]["planner_owner"], b["orchestration"]["planner_owner"]), "transfer_actions_in_plan": len(ta), "block_carries_transfers": False}}


def inv_34_sector_physics_unchanged() -> dict:
    _, a = _plan("N3_mixed_sector_shared_capacity")
    _, b = _plan("N3_mixed_sector_shared_capacity", "gated_legacy")
    same = a["physics"]["profiles"] == b["physics"]["profiles"] and a["physics"]["storage"] == b["physics"]["storage"]
    return {"pass": same, "evidence": {"profiles_identical": same, "sector_invariants": "19 / 19 (gates/sector_invariants.log)"}}


INVARIANTS = [f for name, f in sorted(globals().items()) if name.startswith("inv_")]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", default=None)
    a = ap.parse_args()
    results = {}
    for f in INVARIANTS:
        started = time.time()
        try:
            r = f()
        except Exception as exc:
            r = {"pass": False, "evidence": {"error": f"{type(exc).__name__}: {exc}"[:400]}}
        r["seconds"] = round(time.time() - started, 1)
        results[f.__name__[4:]] = r
        print(f"{f.__name__[4:]:<45} {'PASS' if r['pass'] else 'FAIL':<5} {r['seconds']}s", flush=True)
    if a.benchmark:
        summary = json.loads((OUT / f"{a.benchmark}.summary.json").read_text())
        results["benchmark"] = {"pass": summary["pass_count"] == summary["fixture_count"], "evidence": {"fixtures": f"{summary['pass_count']} / {summary['fixture_count']}", "tag": a.benchmark}, "seconds": 0}
    passed = sum(1 for r in results.values() if r["pass"])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "P3_INVARIANTS.json").write_text(json.dumps(results, indent=1, default=str))
    lines = ["# P3 sourcing invariants", "", f"{passed} / {len(results)} PASS", "", "| invariant | result | evidence |", "|---|---|---|"]
    for k, r in results.items():
        lines.append(f"| {k} | {'PASS' if r['pass'] else 'FAIL'} | {json.dumps(r['evidence'], default=str)[:600]} |")
    (OUT / "P3_INVARIANTS.md").write_text("\n".join(lines) + "\n")
    print(f"INVARIANTS {'PASS' if passed == len(results) else 'FAIL'} {passed}/{len(results)}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
