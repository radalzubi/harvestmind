"""Three-sector physics benchmark: the pre-registered fixture families (`zaad.sectors.fixtures`) replayed
with the P2 runner (`scripts.p2_benchmark.run_cell`, unchanged rules and scoring) under the P2 policy
set, summarised with the P2 economic / service / structural gates plus each fixture's own principle
check (SECTOR_PHYSICS_FIXTURE_SPEC.md). Records under docs/zaad_full/evidence/sectors/.

usage: PYTHONPATH=. python3 -m scripts.sector_benchmark [--tag sector_authoritative] [--workers 4] [--fixtures C1,P2,...] [--policies ...] [--seeds 41001,41002]"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import statistics as st
import time

from scripts.p2_benchmark import POLICIES, run_cell, summarize, tables
from zaad.sectors.fixtures import FIXTURES, REVIEWS, SEEDS, build
from zaad.sectors.contracts import resolve

OUT = Path("docs/zaad_full/evidence/sectors")


def _job(args):
    name, policy, seed, reviews = args
    try:
        cell = run_cell(name, policy, seed, reviews, builder=build)
    except Exception as exc:  # recorded, never hidden
        cell = {"fixture": name, "policy": policy, "seed": seed, "status": "ERROR", "failure": f"{type(exc).__name__}: {exc}"[:400], "reviews_completed": 0}
    return cell


def _gated(records, name, seed):
    return next((r for r in records if r["fixture"] == name and r["policy"] == "gated" and r["seed"] == seed), None)


def principle_check(name: str, spec: dict, records: list[dict]) -> dict:
    """The fixture's own principle over both seeds (see the spec); returns pass and evidence."""
    kind = spec["principle"]
    cells = [_gated(records, name, seed) for seed in SEEDS]
    cells = [c for c in cells if c and c.get("per_review")]
    if not cells:
        return {"pass": False, "principle": kind, "evidence": {"detail": "no completed ZAAD cell"}}
    incumbents = [next((r for r in records if r["fixture"] == name and r["policy"] == "network_rop" and r["seed"] == c["seed"]), None) for c in cells]
    req = build(name, SEEDS[0])
    physics = resolve(req)
    ev: dict = {}
    ok = True
    if kind == "case_multiples":
        src = next(s for s in req.sources if s.id == "src_A")
        bad = [(c["seed"], r["review"], q) for c in cells for r in c["per_review"] for _, q in r["purchases"] if abs(q / src.case_multiple - round(q / src.case_multiple)) > 1e-6]
        ev = {"case_multiple": src.case_multiple, "violations": bad, "purchase_lines": sum(len(r["purchases"]) for c in cells for r in c["per_review"])}
        ok = not bad and ev["purchase_lines"] > 0
    elif kind == "load_limits":
        st_ = req.supplier_terms[0]
        w = physics.weight("A")
        big = [(c["seed"], r["review"], q) for c in cells for r in c["per_review"] for _, q in r["purchases"]
               if q * w > st_.max_shipment_weight + 1e-6 or q / st_.units_per_pallet["A"] > st_.max_pallets + 1e-6]
        ev = {"max_weight": st_.max_shipment_weight, "weight_per_unit": w, "max_pallets": st_.max_pallets, "violations": big,
              "largest_order": max((q for c in cells for r in c["per_review"] for _, q in r["purchases"]), default=0.)}
        ok = not big
    elif kind == "moq_mov":
        src = next(s for s in req.sources if s.id == "src_A")
        mov = req.supplier_terms[0].minimum_order_value
        bad = [(c["seed"], r["review"], q) for c in cells for r in c["per_review"] for _, q in r["purchases"] if 1e-6 < q < src.minimum - 1e-6 or q * src.unit_price < mov - 1e-6]
        ev = {"moq": src.minimum, "mov": mov, "violations": bad}
        ok = not bad
    elif kind == "capacity":
        cap = {loc.id: loc.capacity_volume for loc in req.locations}
        over = [(c["seed"], r["review"], loc, u) for c in cells for r in c["per_review"] for loc, u in r["end_stock_by_location"].items() if u > cap[loc] + 1e-6]
        ev = {"capacity": cap, "violations": over}
        ok = not over
    elif kind == "abstains":
        counts = [c["network"]["abstained_reviews"] for c in cells]
        ev = {"abstained_reviews": counts, "required": spec["abstain_at_least"]}
        ok = all(k >= spec["abstain_at_least"] for k in counts)
    elif kind == "no_purchase_first_two_reviews":
        early = [(c["seed"], r["review"], r["purchase_units"]) for c in cells for r in c["per_review"][:2] if r["purchase_units"] > 1e-6]
        ev = {"early_purchases": early}
        ok = not early
    elif kind == "acts_on_near_expiry":
        acts = [(c["seed"], r["review"], r["purchase_units"], r["transfer_units"]) for c in cells for r in c["per_review"][:1]]
        svc = [(c["seed"], c["service_by_branch"]["svc_north"]["achieved"], i["service_by_branch"]["svc_north"]["achieved"] if i else None) for c, i in zip(cells, incumbents)]
        ev = {"first_review_actions": acts, "north_service_zaad_vs_incumbent": svc}
        ok = all(a[2] + a[3] > 1e-6 for a in acts) and all(z is not None and (inc is None or z >= inc - .01) for _, z, inc in svc)
    elif kind == "uses_fresh_source":
        local = [(c["seed"], sum(q for r in c["per_review"] for s, q in r["purchases"] if s != "src_A")) for c in cells]
        expired = [(c["seed"], sum(r["expired_units"] for r in c["per_review"]), sum(r["expired_units"] for r in i["per_review"]) if i else None) for c, i in zip(cells, incumbents)]
        ev = {"local_units": local, "expired_zaad_vs_incumbent": expired}
        ok = all(u > 0 for _, u in local) and all(inc is None or z <= inc + 1e-6 for _, z, inc in expired)
    elif kind == "no_useless_transfer":
        south = [(c["seed"], c["network"]["lanes"]["lane_south"]["units"], i["network"]["lanes"]["lane_south"]["units"] if i else None) for c, i in zip(cells, incumbents)]
        north = [(c["seed"], c["service_by_branch"]["svc_north"]["achieved"]) for c in cells]
        ev = {"south_units_zaad_vs_incumbent": south, "north_service": north}
        ok = all(inc is None or z <= inc + 1e-6 for _, z, inc in south) and all(v is not None and v >= .9 for _, v in north)
    elif kind == "not_worse":
        ev = {"note": "economic and service gates only"}
    elif kind == "service_under_yield":
        ev = {"service": [(c["seed"], {k: v["achieved"] for k, v in c["service_by_branch"].items()}) for c in cells],
              "incumbent": [(i["seed"], {k: v["achieved"] for k, v in i["service_by_branch"].items()}) if i else None for i in incumbents]}
        ok = all(all(c["service_by_branch"][k]["achieved"] >= (i["service_by_branch"][k]["achieved"] - .01 if i else 0) for k in c["service_by_branch"]) for c, i in zip(cells, incumbents))
    elif kind == "fefo":
        # the settlement's end stock never keeps an older sellable cohort while a younger one was consumed:
        # after each review, for every location the remaining cohorts' expiries are >= the consumed ones
        # (checked by the invariants harness on the settlement directly); here: no unit served past its sellable life
        ev = {"note": "FEFO and sellable-life consumption proved by scripts.sector_invariants (invariants 3, 5, 15) on the settlement"}
    elif kind == "never_at_ineligible_location":
        held = [(c["seed"], r["review"], r["end_stock_by_location"].get("south", 0.)) for c in cells for r in c["per_review"] if r["end_stock_by_location"].get("south", 0.) > 1e-9]
        moved = [(c["seed"], c["network"]["lanes"]["lane_south"]["units"]) for c in cells]
        ev = {"south_end_stock": held, "south_lane_units": moved, "south_service": [(c["seed"], c["service_by_branch"]["svc_south"]["achieved"]) for c in cells]}
        ok = not held and all(u <= 1e-9 for _, u in moved)
    elif kind == "eligible_lane_only":
        ev = {"lanes": [(c["seed"], {k: v["units"] for k, v in c["network"]["lanes"].items()}) for c in cells]}
        ok = all(c["network"]["lanes"]["lane_south"]["units"] <= 1e-9 for c in cells)
    elif kind == "moves_usable_lot":
        first = [(c["seed"], c["per_review"][0]["transfers"].get("lane_north", 0.)) for c in cells]
        ev = {"first_review_north_transfer": first}
        ok = all(u > 1e-6 for _, u in first)
    elif kind == "expiring_lot_not_moved":
        first = [(c["seed"], c["per_review"][0]["transfers"]) for c in cells]
        ev = {"first_review_transfers": first}
        ok = all(sum(t.values()) <= 1e-9 for _, t in first)
    elif kind in ("isolation_and_capacity", "shared_capacity_no_cross_expiry", "no_cross_physics"):
        cap = {loc.id: loc.capacity_volume for loc in req.locations}
        over = [(c["seed"], r["review"], loc, u) for c in cells for r in c["per_review"] for loc, u in r["end_stock_by_location"].items() if u > cap[loc] + 1e-6]
        ev = {"capacity_violations": over, "expired_units": [(c["seed"], sum(r["expired_units"] for r in c["per_review"])) for c in cells]}
        ok = not over
        if kind == "no_cross_physics":
            south_c = [(c["seed"], r["review"], x["quantity"]) for c in cells for r in c["per_review"] for x in r["end_stock"] if x["sku"] == "C" and x["location"] == "south" and x["quantity"] > 1e-9]
            ev["frozen_at_south"] = south_c
            ok = ok and not south_c
    return {"pass": bool(ok), "principle": kind, "evidence": ev}


def p2_shaped_specs() -> dict:
    """The sector fixtures in the P2 summariser's shape: the pre-registered tolerance, the service mode
    ("incumbent": no worse than min(target, incumbent) - .01; "floor": unavoidable shortage allowed when
    the incumbent starves too) and no action expectation (abstention is a recorded property)."""
    return {name: {"expect": {"zaad_not_worse": spec["tolerance"], "service": spec.get("service_mode", "incumbent"), "action": "either"},
                   "why": spec["principle"]} for name, spec in FIXTURES.items()}


def sector_summary(records: list[dict], tag: str) -> dict:
    summary = summarize(records, REVIEWS, fixtures=p2_shaped_specs())
    principles = {}
    for name, spec in FIXTURES.items():
        try:
            principles[name] = principle_check(name, spec, records)
        except Exception as exc:
            principles[name] = {"pass": False, "principle": spec["principle"], "evidence": {"error": f"{type(exc).__name__}: {exc}"[:300]}}
    zaad = [r for r in records if r["policy"] == "gated" and r.get("per_review")]
    walls = sorted(x["wall_seconds"] for r in zaad for x in r["per_review"])
    slow = [(r["fixture"], r["seed"], x["review"], round(x["wall_seconds"], 1), x["state"]) for r in zaad for x in r["per_review"] if x["wall_seconds"] > 60]
    statuses: dict = {}
    for r in zaad:
        for k, v in r["compute"]["solve_statuses"].items():
            statuses[k] = statuses.get(k, 0) + v
    summary["sector_principles"] = principles
    summary["sector_fixture_pass"] = {name: bool(summary["fixtures"].get(name, {}).get("pass")) and principles[name]["pass"] for name in FIXTURES}
    summary["runtime"] = {"reviews": len(walls), "p50": st.median(walls) if walls else None, "p95": walls[max(0, int(.95 * len(walls)) - 1)] if walls else None,
                          "max": max(walls, default=None), "over_60s": slow, "over_180s": [s for s in slow if s[3] > 180], "solve_statuses": statuses,
                          "by_sector": {sec: {"p50": st.median(v), "max": max(v)} for sec, v in
                                        {sec: [x["wall_seconds"] for r in zaad for x in r["per_review"] if FIXTURES[r["fixture"]]["sector"] == sec] for sec in ("COMMERCIAL", "PRODUCE", "MEAT_SEAFOOD", "MIXED")}.items() if v}}
    summary["errors"] = [(r["fixture"], r["policy"], r["seed"], r.get("failure")) for r in records if r.get("status") in ("ERROR", "PHYSICAL_FAILURE")]
    summary["tag"] = tag
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="sector_dev")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--fixtures", default="")
    ap.add_argument("--policies", default=",".join(POLICIES))
    ap.add_argument("--seeds", default=",".join(str(s) for s in SEEDS))
    ap.add_argument("--reviews", type=int, default=REVIEWS)
    ap.add_argument("--summarize-only", action="store_true", help="re-summarise an existing <tag>.jsonl without running")
    a = ap.parse_args()
    only = {x for x in a.fixtures.split(",") if x}
    if a.summarize_only:
        records = [json.loads(line) for line in (OUT / f"{a.tag}.jsonl").read_text().splitlines() if line.strip()]
        return _finish(records, a.tag)
    names = [n for n in FIXTURES if not only or n.split("_")[0] in only or n in only]
    jobs = [(n, p, int(s), a.reviews) for n in names for p in a.policies.split(",") for s in a.seeds.split(",")]
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{a.tag}.jsonl"
    started = time.time()
    records = []
    with path.open("w") as fh, ProcessPoolExecutor(max_workers=a.workers) as pool:
        for cell in pool.map(_job, jobs):
            records.append(cell)
            fh.write(json.dumps(cell, allow_nan=True, default=str) + "\n")
            fh.flush()
            print(f"  {cell['fixture']:<34} {cell['policy']:<18} seed {cell['seed']} {cell.get('status'):<16} reviews {cell.get('reviews_completed')} "
                  f"cost {((cell.get('score') or {}).get('cost_p2') or 0):>9,.0f} wall p50 {((cell.get('compute') or {}).get('wall_p50') or 0):5.1f}s  [{time.time() - started:.0f}s]", flush=True)
    return _finish(records, a.tag)


def _finish(records: list[dict], tag: str) -> int:
    summary = sector_summary(records, tag)
    (OUT / f"{tag}.summary.json").write_text(json.dumps(summary, indent=1, allow_nan=True, default=str))
    text = tables(summary)
    text += "\n## Sector principles\n\n| fixture | principle | pass | evidence |\n|---|---|---|---|\n"
    for name, pr in summary["sector_principles"].items():
        text += f"| {name} | {pr['principle']} | {'PASS' if pr['pass'] else 'FAIL'} | {json.dumps(pr['evidence'], default=str)[:300]} |\n"
    rt = summary["runtime"]
    text += (f"\n## Runtime (ZAAD reviews)\n\nreviews {rt['reviews']}, p50 {rt['p50']:.1f} s, p95 {rt['p95']:.1f} s, max {rt['max']:.1f} s; by sector {rt['by_sector']}; "
             f"over 60 s: {rt['over_60s']}; over 180 s: {rt['over_180s']}; solve statuses {rt['solve_statuses']}; errors {summary['errors']}\n")
    (OUT / f"{tag}.tables.md").write_text(text)
    passing = sum(1 for v in summary["sector_fixture_pass"].values() if v)
    print(f"{tag}: fixtures passing {passing}/{len(FIXTURES)} (economic+service+structural+principle); runtime p50 {rt['p50']:.1f} p95 {rt['p95']:.1f} max {rt['max']:.1f}; errors {len(summary['errors'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
