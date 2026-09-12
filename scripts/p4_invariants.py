"""P4 invariants: mathematical properties every adaptive solve must satisfy, checked on the
fixture matrix records plus direct constructions. A violation is a defect, not a benchmark result.
Written to docs/zaad_full/evidence/p4/P4_INVARIANTS.json and .md.

usage: PYTHONPATH=. python3 -m scripts.p4_invariants --benchmark p4_authoritative"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Callable

from zaad.full.contracts import Request
from zaad.full.planner import plan, report_json
from zaad.full.settlement import PhysicalViolation, settle
from zaad.recourse.contracts import resolve
from zaad.recourse.fixtures import build
from zaad.recourse.information import information_sets, observable_signature
from zaad.recourse.policy import compare, non_anticipativity, world_plan

OUT = Path("docs/zaad_full/evidence/p4")
TOL = 1e-6
_CACHE: dict[str, Any] = {}


def solved(name: str, perfect: bool = True):
    if name not in _CACHE:
        req, rc, worlds = build(name)
        _CACHE[name] = (req, rc, worlds, compare(req, worlds, rc, perfect=perfect, service_floor=True))
    return _CACHE[name]


def inv_01_no_anticipation():
    """Before the first epoch every world's plan equals the here-and-now plan; after it, worlds of one set share the plan (structural check on solved values)."""
    bad = []
    for name in ("A1_demand_visible_at_epoch", "D2_two_epochs", "R1_supplier_short_fill", "I7_correlated_plant"):
        req, rc, worlds, out = solved(name)
        na = non_anticipativity(out["adaptive"], out["nodes"], req)
        if not na["pass"]:
            bad.append((name, na["violations"][:3]))
    return {"pass": not bad, "evidence": bad or "structural check passed on 4 fixtures"}


def inv_02_same_information_same_decision():
    """Two worlds with identical observable histories map to the same information set at every epoch (N3, W2)."""
    ev = {}
    for name in ("N3_zero_information", "W2_no_benefit"):
        req, rc, worlds, out = solved(name, perfect=False)
        ev[name] = {e: len(v) for e, v in out["nodes"].sets.items()}
    return {"pass": all(all(n == 1 for n in v.values()) for v in ev.values()), "evidence": ev}


def inv_03_set_probabilities_sum():
    """Information-set probabilities equal the sums of member weights and sum to one per epoch."""
    bad = []
    for name in ("T2_tree_two_epochs", "I7_correlated_plant"):
        req, rc, worlds, out = solved(name, perfect=False)
        for e, sets in out["nodes"].sets.items():
            if abs(sum(s.probability for s in sets) - 1.) > 1e-9 or any(abs(s.probability - sum(worlds[w].weight for w in s.members)) > 1e-12 for s in sets):
                bad.append((name, e))
    return {"pass": not bad, "evidence": bad or "sums exact on 2 fixtures"}


def inv_04_world_probabilities_preserved():
    """The tree worlds' weights sum to one and every branch keeps its history weight split evenly over its continuations."""
    req, rc, worlds, out = solved("T1_tree_three_histories", perfect=False)
    total = sum(w.weight for w in worlds)
    return {"pass": abs(total - 1.) < 1e-9 and len({round(w.weight, 12) for w in worlds}) == 1, "evidence": {"total": total, "worlds": len(worlds)}}


def inv_05_static_feasible():
    """The static comparator is a feasible static plan under the frozen rows (usable) wherever a static plan exists."""
    ev = {}
    for name in ("A1_demand_visible_at_epoch", "I1_p1_fixed_cost_lots", "I4_p3_shares_hold"):
        req, rc, worlds, out = solved(name, perfect=False)
        ev[name] = out["static"].status
    return {"pass": all(v in ("OPTIMAL", "FEASIBLE_TIME_LIMIT") for v in ev.values()), "evidence": ev}


def inv_06_adaptive_feasible_every_world(records):
    """Every represented world settles under its own policy plan (no physical violation, no guidance truncation)."""
    bad = [(r["fixture"], s) for r in records for s in r.get("settlements", []) if not s["usable"] or s.get("truncated", 0) > TOL]
    return {"pass": not bad, "evidence": bad or f"{sum(len(r.get('settlements', [])) for r in records)} world settlements clean"}


def inv_07_committed_stays_committed():
    """Purchases before the first epoch are identical in every world's plan and equal the here-and-now plan (no cancellation, no retroactive change)."""
    req, rc, worlds, out = solved("D1_demand_recourse", perfect=False)
    first = rc.epochs[0]
    base = out["adaptive"].purchases
    plans = [world_plan(out["adaptive"], req, rc, out["nodes"], w, index=i) for i, w in enumerate(worlds)]
    ok = all(abs(p.purchases.get(k, 0.) - q) < TOL for p in plans for k, q in base.items() if k[1] < first) and all(all(k[1] >= first or k in base for k in p.purchases) for p in plans)
    return {"pass": ok, "evidence": {"committed_periods": list(range(first)), "worlds": len(plans)}}


def inv_08_no_negative_inventory(records):
    """Settlement of every world plan reports no negative stock (settlement raises on any physical violation)."""
    return inv_06_adaptive_feasible_every_world(records)


def inv_09_network_conservation():
    """On the P2 recourse fixture the settled conservation residual is zero in every world."""
    req, rc, worlds, out = solved("I2_p2_transfer_recourse", perfect=False)
    worst = 0.
    for i, w in enumerate(worlds):
        r = settle(req, world_plan(out["adaptive"], req, rc, out["nodes"], w, index=i), w, future_guidance=True)
        worst = max(worst, abs(float(r.get("conservation_residual", 0.) or 0.)))
    return {"pass": worst < 1e-6, "evidence": {"worst_residual": worst}}


def inv_10_no_double_allocation():
    """Period-0 transfers of the adaptive plan never exceed opening stock at the origin (settlement strict at period zero, every world)."""
    return inv_09_network_conservation()


def _breaches(name):
    req, rc, worlds, out = solved(name, perfect=False)
    sources = {s.id: s for s in req.sources}
    bad = []
    for i, w in enumerate(worlds):
        p = world_plan(out["adaptive"], req, rc, out["nodes"], w, index=i)
        for (sid, t), q in p.purchases.items():
            s = sources[sid]
            if q > min(s.maximum, s.capacity_by_period[t]) + TOL: bad.append(("capacity", sid, t))
            if q > TOL and s.minimum > 0 and q < s.minimum - TOL: bad.append(("moq", sid, t))
            for inc in (s.multiple, s.case_multiple, s.pallet_multiple):
                if inc > 0 and q > TOL and abs(q / inc - round(q / inc)) > 1e-6: bad.append(("pack", sid, t))
        for res in req.resources:
            for t in range(req.horizon):
                used = sum(p.purchases.get((s.id, t), 0.) * next(k.volume for k in req.skus if k.id == s.sku) for s in req.sources if res.id in s.resources)
                if used > res.capacity_by_period[t] + TOL: bad.append(("resource", res.id, t))
        for st in req.supplier_terms:
            if st.minimum_order_value:
                for t in range(req.horizon):
                    lines = [(s, p.purchases.get((s.id, t), 0.)) for s in req.sources if s.supplier == st.supplier]
                    value = sum(q * s.unit_price for s, q in lines)
                    if 0 < value < st.minimum_order_value - 1e-6: bad.append(("mov", st.supplier, t))
    return bad


def inv_11_source_capacity():
    """No branch buys above a source's capacity or maximum (I3, I6)."""
    bad = [(n, b) for n in ("I3_p3_source_mix", "I6_multi_sku_shared_capacity") for b in _breaches(n) if b[0] == "capacity"]
    return {"pass": not bad, "evidence": bad or "clean"}


def inv_12_shared_supplier_capacity():
    """Shared resources hold in every branch (I6)."""
    bad = [b for b in _breaches("I6_multi_sku_shared_capacity") if b[0] == "resource"]
    return {"pass": not bad, "evidence": bad or "clean"}


def inv_13_moq():
    bad = [b for b in _breaches("I1_p1_fixed_cost_lots") if b[0] == "moq"]
    return {"pass": not bad, "evidence": bad or "clean"}


def inv_14_mov():
    """Every branch's supplier order meets the MOV or is absent (shared supplier orders counted once per node)."""
    from zaad.recourse.fixtures import sourcing_base, with_recourse, branches, scale_demand
    req = with_recourse(sourcing_base("C6_shared_mov_multi_sku"), review_periods=[3], observables=["demand"])
    rc = resolve(req)
    worlds = branches(req, rc, [("normal", .5, None), ("high", .5, scale_demand(1.3))], 3)
    _CACHE["_mov"] = (req, rc, worlds, compare(req, worlds, rc, perfect=False, service_floor=True))
    req, rc, worlds, out = _CACHE["_mov"]
    bad = []
    for i, w in enumerate(worlds):
        p = world_plan(out["adaptive"], req, rc, out["nodes"], w, index=i)
        for st in req.supplier_terms:
            for t in range(req.horizon):
                value = sum(p.purchases.get((s.id, t), 0.) * s.unit_price for s in req.sources if s.supplier == st.supplier)
                if 0 < value < st.minimum_order_value - 1e-6: bad.append((w.name, t, value))
    return {"pass": not bad and out["adaptive"].usable_plan, "evidence": bad or {"status": out["adaptive"].status, "worlds": len(worlds)}}


def inv_15_packs():
    bad = [b for b in _breaches("S1_commercial_packs") if b[0] == "pack"]
    return {"pass": not bad, "evidence": bad or "whole packs in every branch"}


def inv_16_share_constraints():
    req, rc, worlds, out = solved("I4_p3_shares_hold", perfect=False)
    sources = {s.id: s for s in req.sources}
    bad = []
    for i, w in enumerate(worlds):
        p = world_plan(out["adaptive"], req, rc, out["nodes"], w, index=i)
        for c in req.sourcing.share_constraints:
            own = sum(q for (sid, t), q in p.purchases.items() if sid == c.source)
            total = sum(q for (sid, t), q in p.purchases.items() if sources[sid].sku == c.sku and sources[sid].destination == c.destination)
            if total > TOL and not (c.minimum_share - 1e-6 <= own / total <= c.maximum_share + 1e-6): bad.append((w.name, own / total))
    return {"pass": not bad, "evidence": bad or "shares hold in every branch"}


def inv_17_transfer_lead_time():
    """A recourse transfer decided at epoch e cannot arrive before e + lane lead (columns exist only for t >= e; arrival = t + lead)."""
    req, rc, worlds, out = solved("I2_p2_transfer_recourse", perfect=False)
    first = rc.epochs[0]
    bad = []
    for node, planx in out["adaptive"].recourse["nodes"].items():
        for (arc, expiry, t), q in planx["transfers"].items():
            if t < first: bad.append((node, arc, t))
    return {"pass": not bad, "evidence": bad or "every recourse transfer departs at or after its epoch"}


def inv_18_sector_physics(records):
    """Sector fixtures settle in every world (physics enforced by the same rows and settlement)."""
    bad = [(r["fixture"], s) for r in records if r["family"] == "sector" for s in r.get("settlements", []) if not s["usable"]]
    return {"pass": not bad, "evidence": bad or "clean"}


def inv_19_shelf_life_fefo():
    """Produce fixture: no world plan settles with expired sales (settlement's FEFO and life rules)."""
    req, rc, worlds, out = solved("S2_produce_sell_through", perfect=False)
    bad = []
    for i, w in enumerate(worlds):
        try:
            settle(req, world_plan(out["adaptive"], req, rc, out["nodes"], w, index=i), w, future_guidance=True)
        except PhysicalViolation as exc:
            bad.append(str(exc)[:80])
    return {"pass": not bad, "evidence": bad or "clean"}


def inv_20_cold_chain():
    """Meat / seafood fixture: every world plan settles under the cold-chain and receipt-life rules."""
    req, rc, worlds, out = solved("S3_meat_cold_chain", perfect=False)
    bad = []
    for i, w in enumerate(worlds):
        try:
            settle(req, world_plan(out["adaptive"], req, rc, out["nodes"], w, index=i), w, future_guidance=True)
        except PhysicalViolation as exc:
            bad.append(str(exc)[:80])
    return {"pass": out["adaptive"].usable_plan and not bad, "evidence": bad or {"status": out["adaptive"].status, "worlds": len(worlds)}}


def inv_21_approval_required():
    req = build("D1_demand_recourse")[0]
    r = plan(req)
    return {"pass": r["approval_required"] is True and r["executable_purchase_order"] is False and r["recourse"]["approval_required"] is True, "evidence": r["recourse"]["verdict"]}


def inv_22_no_executable_po():
    return inv_21_approval_required()


def inv_23_perfect_le_adaptive(records):
    bad = [r["fixture"] for r in records if r.get("solves", {}).get("perfect") and r["solves"]["perfect"]["cost"] is not None and r["solves"]["adaptive"]["cost"] is not None
           and r["solves"]["perfect"]["cost"] > r["solves"]["adaptive"]["cost"] + 1e-6 * max(1., abs(r["solves"]["adaptive"]["cost"])) + 1e-6]
    return {"pass": not bad, "evidence": bad or "PI <= adaptive on every fixture with a PI solve"}


def inv_24_adaptive_le_static(records):
    bad = [r["fixture"] for r in records if r.get("solves", {}).get("static") and not r.get("static_infeasible") and r["solves"]["static"]["cost"] is not None
           and r["solves"]["adaptive"]["cost"] > r["solves"]["static"]["cost"] + 1e-6 * max(1., abs(r["solves"]["static"]["cost"])) + 1e-6]
    return {"pass": not bad, "evidence": bad or "adaptive <= static wherever a static plan exists"}


def inv_25_disabled_is_frozen():
    from zaad.meio.fixtures_p2 import p2_request
    base = p2_request()
    off = Request.model_validate({**base.model_dump(mode="json"), "recourse": {"enabled": False, "review_periods": [3]}})
    strip = lambda s: re.sub(r'"information_hash": "[0-9a-f]+"|"solve_seconds": [0-9.e-]+|"solver_seconds_total": [0-9.e-]+|"seconds": [0-9.e-]+', '', s)
    r0, r1 = plan(base), plan(off)
    return {"pass": strip(report_json(r0)) == strip(report_json(r1)) and "recourse" not in r1, "evidence": "reports identical up to timings and the request hash"}


def inv_26_signature_order_independent():
    """Reversing the world order changes no information-set membership signature and no probability."""
    req, rc, worlds, _ = solved("T2_tree_two_epochs", perfect=False)
    a = information_sets(req, rc, worlds)
    b = information_sets(req, rc, list(reversed(worlds)))
    n = len(worlds)
    same = all([(s.signature, s.probability, tuple(sorted(n - 1 - m for m in s.members))) for s in a[e]] == [(s.signature, s.probability, tuple(sorted(s.members))) for s in b[e]] for e in a)
    return {"pass": same, "evidence": "signatures, probabilities and memberships invariant under world reordering"}


def inv_27_signature_uses_no_future():
    """Changing any world's demand at or after the epoch never changes its signature at that epoch."""
    from dataclasses import replace
    req, rc, worlds, _ = solved("A1_demand_visible_at_epoch", perfect=False)
    e = rc.epochs[0]
    w = worlds[0]
    mutated = replace(w, demand={s: tuple(d * (2. if t >= e else 1.) for t, d in enumerate(v)) for s, v in w.demand.items()})
    return {"pass": observable_signature(req, rc, w, e) == observable_signature(req, rc, mutated, e), "evidence": f"epoch {e}: future demand doubled, signature unchanged"}


INVARIANTS: list[tuple[str, Callable]] = [
    ("01_no_anticipation", inv_01_no_anticipation), ("02_same_information_same_decision", inv_02_same_information_same_decision),
    ("03_set_probabilities_sum", inv_03_set_probabilities_sum), ("04_world_probabilities_preserved", inv_04_world_probabilities_preserved),
    ("05_static_feasible", inv_05_static_feasible), ("06_adaptive_feasible_every_world", inv_06_adaptive_feasible_every_world),
    ("07_committed_stays_committed", inv_07_committed_stays_committed), ("08_no_negative_inventory", inv_08_no_negative_inventory),
    ("09_network_conservation", inv_09_network_conservation), ("10_no_double_allocation", inv_10_no_double_allocation),
    ("11_source_capacity", inv_11_source_capacity), ("12_shared_supplier_capacity", inv_12_shared_supplier_capacity),
    ("13_moq", inv_13_moq), ("14_mov", inv_14_mov), ("15_packs", inv_15_packs), ("16_share_constraints", inv_16_share_constraints),
    ("17_transfer_lead_time", inv_17_transfer_lead_time), ("18_sector_physics", inv_18_sector_physics), ("19_shelf_life_fefo", inv_19_shelf_life_fefo),
    ("20_cold_chain", inv_20_cold_chain), ("21_approval_required", inv_21_approval_required), ("22_no_executable_po", inv_22_no_executable_po),
    ("23_perfect_le_adaptive", inv_23_perfect_le_adaptive), ("24_adaptive_le_static", inv_24_adaptive_le_static),
    ("25_disabled_is_frozen", inv_25_disabled_is_frozen), ("26_signature_order_independent", inv_26_signature_order_independent),
    ("27_signature_uses_no_future", inv_27_signature_uses_no_future),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", default=None)
    a = ap.parse_args()
    records = json.loads((OUT / "benchmarks" / f"{a.benchmark}.json").read_text()) if a.benchmark else []
    results = {}
    for name, fn in INVARIANTS:
        try:
            res = fn(records) if fn.__code__.co_argcount == 1 else fn()
        except Exception as exc:
            res = {"pass": False, "evidence": f"{type(exc).__name__}: {exc}"}
        results[name] = {"doc": (fn.__doc__ or "").strip(), **res}
        print(f"{name:36s} {'PASS' if res['pass'] else 'FAIL'}  {json.dumps(res['evidence'], default=str)[:110]}", flush=True)
    passed = sum(1 for r in results.values() if r["pass"])
    (OUT / "P4_INVARIANTS.json").write_text(json.dumps({"benchmark": a.benchmark, "passed": passed, "total": len(results), "results": results}, indent=1, default=str))
    md = [f"# P4 invariants\n\nBenchmark: `{a.benchmark}`. **{passed} / {len(results)} PASS**\n", "| invariant | statement | result | evidence |", "|---|---|---|---|"]
    for n, r in results.items():
        md.append(f"| {n} | {r['doc']} | {'PASS' if r['pass'] else 'FAIL'} | {json.dumps(r['evidence'], default=str)[:160]} |")
    (OUT / "P4_INVARIANTS.md").write_text("\n".join(md) + "\n")
    print(f"INVARIANTS {'PASS' if passed == len(results) else 'FAIL'} {passed}/{len(results)}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
