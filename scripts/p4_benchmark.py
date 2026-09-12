"""P4 fixture matrix: static / adaptive / perfect-information solves per fixture, the pre-registered
principle, per-world settlement of the adaptive policy and instrumentation. Records under
docs/zaad_full/evidence/p4/benchmarks/<tag>.json and .md.

usage: PYTHONPATH=. python3 -m scripts.p4_benchmark --tag p4_dev [--fixtures A,B]"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from zaad.full.planner import plan, report_json
from zaad.full.settlement import PhysicalViolation, settle
from zaad.recourse.fixtures import FIXTURES, build
from zaad.recourse.policy import compare, world_plan

OUT = Path("docs/zaad_full/evidence/p4/benchmarks")
TOL = 1e-6


def _window_totals(plan_purchases: dict, lo: int, hi: int) -> float:
    return sum(q for (sid, t), q in plan_purchases.items() if lo <= t < hi)


def _branch_plans(out: dict, req, rc, worlds) -> dict[str, dict]:
    """World plans keyed by branch name (the part before the first '.')."""
    nodes = out["nodes"]
    plans = {}
    for w, world in enumerate(worlds):
        plans[world.name] = world_plan(out["adaptive"], req, rc, nodes, world, index=w)
    return plans


def principle(name: str, spec: dict, req, rc, worlds, out: dict) -> dict[str, Any]:
    kind = spec["principle"]
    H = req.horizon
    ev: dict[str, Any] = {}
    if kind == "frozen_identity":
        # a disabled block: the planner report equals the frozen report up to timings and the request hash
        import re
        base = spec["request"]()
        r0, r1 = plan(base), plan(req)
        strip = lambda s: re.sub(r'"information_hash": "[0-9a-f]+"|"solve_seconds": [0-9.e-]+|"solver_seconds_total": [0-9.e-]+|"seconds": [0-9.e-]+', '', s)
        ok = strip(report_json(r0)) == strip(report_json(r1)) and "recourse" not in r1
        return {"pass": ok, "evidence": {"recourse_block_absent": "recourse" not in r1}}
    if kind == "equals_static":
        ok = rc is None or not rc.epochs
        ok = ok and abs(out["static_cost"] - out["adaptive_cost"]) <= 1e-6 * max(1., abs(out["static_cost"]))
        return {"pass": ok, "evidence": {"static": out["static_cost"], "adaptive": out["adaptive_cost"]}}
    first = rc.epochs[0]
    plans = _branch_plans(out, req, rc, worlds)
    branch = lambda prefix: [p for n, p in plans.items() if n.startswith(prefix)]
    sets = {e: len(v) for e, v in out["nodes"].sets.items()}
    if kind in ("feasible_every_world",) and out.get("static_infeasible"):
        return {"pass": out["adaptive"].usable_plan, "evidence": {"sets": sets, "static": "INFEASIBLE under the service floors", "adaptive": out["adaptive"].status,
                                                                    "note": "flexibility restores feasibility; ordering not applicable"}}
    if kind == "one_set_equals_static":
        ok = sets[first] == 1 and abs(out["value_of_adaptation"]) <= 1e-6 * max(1., abs(out["static_cost"]))
        return {"pass": ok, "evidence": {"sets": sets, "value": out["value_of_adaptation"]}}
    if kind in ("same_before_diverge_after", "high_branch_buys_more", "waiting_value"):
        a, b = spec["worlds"][0][0], spec["worlds"][1][0]
        pa, pb = branch(a)[0], branch(b)[0]
        before_same = all(abs(pa.purchases.get(k, 0.) - pb.purchases.get(k, 0.)) <= TOL for k in set(pa.purchases) | set(pb.purchases) if k[1] < first)
        after_a, after_b = _window_totals(pa.purchases, first, H), _window_totals(pb.purchases, first, H)
        ev = {"sets": sets, "before_identical": before_same, "after_low": after_a, "after_high": after_b, "value": out["value_of_adaptation"]}
        if kind == "same_before_diverge_after":
            return {"pass": before_same and sets[first] >= 2 and abs(after_a - after_b) > TOL, "evidence": ev}
        if kind == "high_branch_buys_more":
            return {"pass": before_same and after_b >= after_a - TOL and sets[first] >= 2, "evidence": ev}
        static_before = _window_totals(out["static"].purchases, 0, first)
        adaptive_before = _window_totals(out["adaptive"].purchases, 0, first)
        ev.update(static_committed_before=static_before, adaptive_committed_before=adaptive_before)
        return {"pass": before_same and out["value_of_adaptation"] > 0 and adaptive_before <= static_before + TOL, "evidence": ev}
    if kind == "no_branch_until_observed":
        pa, pb = branch(spec["worlds"][0][0])[0], branch(spec["worlds"][1][0])[0]
        e1, e2 = rc.epochs[0], rc.epochs[1]
        same_until_e2 = all(abs(pa.purchases.get(k, 0.) - pb.purchases.get(k, 0.)) <= TOL for k in set(pa.purchases) | set(pb.purchases) if k[1] < e2)
        return {"pass": same_until_e2 and sets[e1] == 1 and sets[e2] == 2, "evidence": {"sets": sets, "same_until_second_epoch": same_until_e2}}
    if kind in ("short_branch_replaces_supply", "late_branch_covers_gap"):
        pa, pb = branch(spec["worlds"][0][0])[0], branch(spec["worlds"][1][0])[0]
        before_same = all(abs(pa.purchases.get(k, 0.) - pb.purchases.get(k, 0.)) <= TOL for k in set(pa.purchases) | set(pb.purchases) if k[1] < first)
        after_a, after_b = _window_totals(pa.purchases, first, H), _window_totals(pb.purchases, first, H)
        moves_a, moves_b = sum(pa.transfers.values()), sum(pb.transfers.values())
        ev = {"sets": sets, "before_identical": before_same, "after_normal": after_a, "after_disrupted": after_b, "transfers_normal": moves_a, "transfers_disrupted": moves_b}
        return {"pass": before_same and sets[first] == 2 and (after_b > after_a - TOL or moves_b > moves_a - TOL), "evidence": ev}
    if kind == "recovered_branch_buys_less":
        pa, pb = branch("recovered")[0], branch("persistent")[0]
        after_a, after_b = _window_totals(pa.purchases, first, H), _window_totals(pb.purchases, first, H)
        return {"pass": sets[first] == 2 and after_a <= after_b + TOL, "evidence": {"sets": sets, "after_recovered": after_a, "after_persistent": after_b}}
    if kind == "no_benefit":
        return {"pass": sets[first] == 1 and abs(out["value_of_adaptation"]) <= 1e-6 * max(1., abs(out["static_cost"])), "evidence": {"sets": sets, "value": out["value_of_adaptation"]}}
    if kind == "ordering_only":
        return {"pass": True, "evidence": {"sets": sets, "value": out["value_of_adaptation"]}}
    if kind == "pi_ordering":
        return {"pass": out["perfect_cost"] is not None and out["perfect_cost"] <= out["adaptive_cost"] + 1e-6 * max(1., abs(out["static_cost"])), "evidence": {"pi": out["perfect_cost"], "adaptive": out["adaptive_cost"], "static": out["static_cost"]}}
    if kind in ("moq_in_every_branch", "capacity_in_every_branch", "shares_in_every_branch", "packs_in_every_branch", "feasible_every_world", "transfers_adapt_conserved", "plant_observed_once"):
        sources = {s.id: s for s in req.sources}
        breaches: list[str] = []
        for wname, p in plans.items():
            for (sid, t), q in p.purchases.items():
                s = sources[sid]
                if q > TOL and s.minimum > 0 and q < s.minimum - 1e-6:
                    breaches.append(f"{wname}: {sid}@{t} below MOQ")
                if q > min(s.maximum, s.capacity_by_period[t]) + 1e-6:
                    breaches.append(f"{wname}: {sid}@{t} above capacity")
                if s.multiple > 0 and abs(q / s.multiple - round(q / s.multiple)) > 1e-6:
                    breaches.append(f"{wname}: {sid}@{t} not a whole pack")
            for r in req.resources:
                for t in range(H):
                    used = sum(p.purchases.get((s.id, t), 0.) * next(k.volume for k in req.skus if k.id == s.sku) for s in req.sources if r.id in s.resources)
                    if used > r.capacity_by_period[t] + 1e-6:
                        breaches.append(f"{wname}: resource {r.id}@{t} over capacity")
        if kind == "shares_in_every_branch" and req.sourcing is not None:
            for c in req.sourcing.share_constraints:
                for wname, p in plans.items():
                    own = sum(q for (sid, t), q in p.purchases.items() if sid == c.source)
                    total = sum(q for (sid, t), q in p.purchases.items() if sources[sid].sku == c.sku and sources[sid].destination == c.destination)
                    if total > TOL and (own / total < c.minimum_share - 1e-6 or own / total > c.maximum_share + 1e-6):
                        breaches.append(f"{wname}: share of {c.source} {own / total:.3f} outside [{c.minimum_share}, {c.maximum_share}]")
        ev = {"sets": sets, "breaches": breaches, "value": out["value_of_adaptation"]}
        if kind == "plant_observed_once":
            # both members of the plant group short-fill together: one set per plant state, never a split by source label
            return {"pass": not breaches and sets[first] == 2, "evidence": ev}
        if kind == "transfers_adapt_conserved":
            pa, pb = branch(spec["worlds"][0][0])[0], branch(spec["worlds"][1][0])[0]
            ev["transfers_normal"], ev["transfers_surge"] = sum(pa.transfers.values()), sum(pb.transfers.values())
            return {"pass": not breaches and sets[first] == 2, "evidence": ev}
        return {"pass": not breaches, "evidence": ev}
    raise ValueError(kind)


def run(name: str) -> dict[str, Any]:
    spec = FIXTURES[name]
    req, rc, worlds = build(name)
    record: dict[str, Any] = {"fixture": name, "family": spec["family"], "principle": spec["principle"], "worlds": len(worlds),
                              "epochs": list(rc.epochs) if rc else [], "seed": req.seed}
    t0 = time.perf_counter()
    if rc is None or not rc.epochs:
        out = compare(req, worlds, rc, perfect=False, service_floor=True) if rc is not None else None
        if out is None:
            # disabled: planner-level identity only
            record.update(principle_result=principle(name, spec, req, rc, worlds, {}), seconds=round(time.perf_counter() - t0, 2))
            record["pass"] = record["principle_result"]["pass"]
            return record
    else:
        out = compare(req, worlds, rc, service_floor=True)
    solves = {}
    for k in ("static", "adaptive", "perfect"):
        s = out.get(k)
        if s is not None:
            solves[k] = {"status": s.status, "cost": s.projected_cost, "variables": s.variables, "binaries": s.binaries, "constraints": s.constraints,
                         "nodes": s.nodes, "seconds": round(s.solve_seconds, 3), "gap": s.gap}
    record["solves"] = solves
    record["information_sets"] = {str(e): [{"id": s.id, "members": list(s.members), "probability": s.probability} for s in v] for e, v in out["nodes"].sets.items()} if out["nodes"] is not None else {}
    record["value_of_adaptation"] = out.get("value_of_adaptation")
    record["ordering_ok"] = out.get("ordering_ok")
    record["non_anticipativity"] = out.get("non_anticipativity")
    # every represented world settles under its own plan (feasibility) with no guidance truncation
    settlements = []
    if out["adaptive"].usable_plan and out["nodes"] is not None:
        for w, world in enumerate(worlds):
            p = world_plan(out["adaptive"], req, rc, out["nodes"], world, index=w)
            try:
                r = settle(req, p, world, future_guidance=True)
                settlements.append({"world": world.name, "usable": True, "cost": r["economic_cost"], "truncated": r.get("guidance_truncated_units", 0.)})
            except PhysicalViolation as exc:
                settlements.append({"world": world.name, "usable": False, "reason": str(exc)})
    record["settlements"] = settlements
    feasible = all(s["usable"] for s in settlements) and bool(settlements)
    record["principle_result"] = principle(name, spec, req, rc, worlds, out)
    record["seconds"] = round(time.perf_counter() - t0, 2)
    # gate: every solve returns a usable plan (optimal, or a feasible time-limited incumbent, which the
    # planner also accepts and which is recorded); the ordering holds whenever a static plan exists;
    # non-anticipativity; every represented world settles; the pre-registered principle
    usable = out["adaptive"].usable_plan and (out["perfect"] is None or out["perfect"].usable_plan)
    ordering = out.get("ordering_ok") if not out.get("static_infeasible") else None
    ordering_ok = True if ordering is None else bool(ordering)
    record["time_limited"] = out.get("time_limited", [])
    record["static_infeasible"] = out.get("static_infeasible")
    record["pass"] = bool(usable and ordering_ok and (out.get("non_anticipativity") or {}).get("pass") and feasible and record["principle_result"]["pass"])
    record["checks"] = {"all_usable": usable, "all_optimal": all(v["status"] == "OPTIMAL" for v in solves.values()), "ordering": ordering,
                        "non_anticipativity": (out.get("non_anticipativity") or {}).get("pass"), "feasible_every_world": feasible, "principle": record["principle_result"]["pass"]}
    return record


def table(records: list[dict]) -> str:
    lines = ["| fixture | family | worlds | sets | static | adaptive | PI | value | ordering | NA | feasible | principle | wall s | result |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in records:
        s = r.get("solves", {})
        f = lambda k: (f"{s[k]['cost']:,.1f}" if k in s and s[k]["cost"] is not None else "-")
        sets = ",".join(str(len(v)) for v in r.get("information_sets", {}).values()) or "-"
        c = r.get("checks", {})
        lines.append(f"| {r['fixture']} | {r['family']} | {r['worlds']} | {sets} | {f('static')} | {f('adaptive')} | {f('perfect')} | "
                     f"{(r.get('value_of_adaptation') or 0):,.1f} | {c.get('ordering', '-')} | {c.get('non_anticipativity', '-')} | {c.get('feasible_every_world', '-')} | "
                     f"{r['principle']} ({'PASS' if r['principle_result']['pass'] else 'FAIL'}) | {r['seconds']} | {'PASS' if r['pass'] else 'FAIL'} |")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="p4_dev")
    ap.add_argument("--fixtures", default="")
    a = ap.parse_args()
    only = [x for x in a.fixtures.split(",") if x]
    names = only or list(FIXTURES)
    records = []
    for name in names:
        t = time.perf_counter()
        try:
            r = run(name)
        except Exception as exc:  # recorded, never hidden
            r = {"fixture": name, "family": FIXTURES[name]["family"], "principle": FIXTURES[name]["principle"], "worlds": 0, "pass": False,
                 "error": f"{type(exc).__name__}: {exc}", "seconds": round(time.perf_counter() - t, 2), "principle_result": {"pass": False}}
        records.append(r)
        print(f"{name:34s} {'PASS' if r['pass'] else 'FAIL'}  {r.get('seconds', 0):6.1f}s  sets={ {k: len(v) for k, v in r.get('information_sets', {}).items()} } value={r.get('value_of_adaptation')} {r.get('error', '')}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{a.tag}.json").write_text(json.dumps(records, indent=1, default=str))
    passed = sum(1 for r in records if r["pass"])
    md = f"# P4 fixture matrix `{a.tag}`\n\n{passed} / {len(records)} fixtures PASS\n\n" + table(records) + "\n"
    (OUT / f"{a.tag}.md").write_text(md)
    print(f"{passed} / {len(records)} fixtures PASS")
    return 0 if passed == len(records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
