"""P3 sourcing benchmark: the pre-registered fixtures (`zaad.sourcing.fixtures`) replayed with the P2
runner (`scripts.p2_benchmark.run_cell`, unchanged rules and scoring) under the P3 policy set, scored
with the P2 economic / service / structural gates against the best valid baseline (incumbent mix, cheapest
landed single source, best single supplier) plus each fixture's own principle (P3_FIXTURE_SPEC.md).
Records under docs/zaad_full/evidence/p3/.

usage: PYTHONPATH=. python3 -m scripts.p3_benchmark [--tag p3_authoritative] [--workers 6] [--fixtures E1,R2,...] [--seeds 41001,41002]"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import statistics as st
import time

from scripts.p2_benchmark import run_cell
from zaad.sourcing.fixtures import FIXTURES, REVIEWS, SEEDS, build, variant

OUT = Path("docs/zaad_full/evidence/p3")
BASE_POLICIES = ("incumbent_mix", "cheapest_landed", "gated")
METHOD = {"incumbent_mix": "network_rop", "cheapest_landed": "cheapest_landed", "gated": "gated", "gated_noprune": "gated", "gated_legacy": "gated"}


def register_p3_methods() -> None:
    """`cheapest_landed`: the network reorder-point rule projected as if no incumbent mix and no share limit
    were declared (it buys everything from the cheapest landed source), settled on the fixture's own request
    so a declared switching cost still applies when it leaves the operator's mix."""
    from dataclasses import replace
    from zaad.full.model import solve
    from zaad.full.replay import NETWORK_METHODS
    from zaad.full.worlds import draw
    from zaad.meio.baselines import network_rule_plan, register_replay_methods
    register_replay_methods()

    def method(req):
        stripped = req if req.sourcing is None else req.model_copy(update={"sourcing": req.sourcing.model_copy(update={"incumbent_shares": (), "share_constraints": ()})})
        # the frozen rule's primary source is the cheapest approved and cleared one; an expired quote or a
        # dead capacity is not a source a buyer can order from, so the comparator never projects it
        stripped = stripped.model_copy(update={"sources": tuple(s if _usable(req, s) else s.model_copy(update={"approved": False}) for s in req.sources)})
        projected = network_rule_plan(stripped, "network:rop")
        world = draw(req, req.seed, 1, deterministic=True)
        settled = solve(req, world, fixed=replace(projected, status="OPTIMAL"))
        if not settled.usable_plan:
            return replace(projected, status=settled.status, warnings=["baseline:cheapest_landed", *settled.warnings])
        return replace(settled, warnings=["baseline:cheapest_landed", *settled.warnings])
    NETWORK_METHODS.setdefault("cheapest_landed", method)


def _usable(req, s) -> bool:
    return s.approved and s.compliance == "cleared" and s.quote_expires >= req.as_of and any(min(s.maximum, c) > 0 for c in s.capacity_by_period[:req.horizon])


def policies_for(name: str, seed: int) -> list[str]:
    req = build(name, seed)
    suppliers = sorted({s.supplier for s in req.sources if _usable(req, s)})
    # a single-supplier policy only where it restricts something: a pair the supplier serves with another usable supplier
    pairs_of = {sup: {(s.sku, s.destination) for s in req.sources if s.supplier == sup and _usable(req, s)} for sup in suppliers}
    singles = [sup for sup in suppliers if any(any(o != sup and pair in pairs_of[o] for o in suppliers) for pair in pairs_of[sup])]
    out = list(BASE_POLICIES) + [f"single:{s}" for s in singles]
    if name.startswith("A3_"):
        out.append("gated_noprune")
    if name.startswith("A5_"):
        out.append("gated_legacy")
    return out


def p3_score(initial, log: list[dict], basis=None) -> dict:
    """The P3 continuation basis: residual stock valued at what one received unit from the cheapest
    approved source of the SKU costs (unit price over its fill, plus freight and handling), the lane cost
    a unit at a transfer-fed location avoids, and no policy-specific premium. The P2 basis adds the order-
    level premium the policy itself paid per unit, which credits a dear-freight source's residual at its
    own dearer cost; for a sourcing comparison the basis must not depend on the policy under test."""
    from zaad.full.lotsizing import lane_premiums
    from zaad.full.terminal import continuation_value
    ledger: dict[str, float] = {}
    for row in log:
        for key, value in row["settlement"]["ledger"].items():
            if key not in {"opening_assets", "closing_assets"}:
                ledger[key] = ledger.get(key, 0.) + value
    ledger["opening_assets"] = log[0]["settlement"]["ledger"]["opening_assets"]
    ledger["closing_assets"] = log[-1]["settlement"]["ledger"]["closing_assets"]
    realized = sum(ledger.values())
    basis = basis or initial   # the fixture's own request: a policy variant that unapproves sources must not change the basis
    terms = {t.id: t for t in basis.terms}
    landed = {}
    for sku in basis.skus:
        # the cheapest approved source per RECEIVED unit (landed cost over its expected fill); the P2 basis
        # picks the cheapest by price and then divides by that source's fill, which crowns a cheap
        # low-yield source and credits every policy's residual at its dearer received-unit cost
        options = [s for s in basis.sources if s.sku == sku.id and _usable(basis, s)]
        per_received = [(s.unit_price * terms[s.terms].fx_rate_to_currency + s.freight_per_unit + s.handling_per_unit) / max(s.fill_mean, 1e-6) for s in options]
        landed[sku.id] = max(sku.asset_value, min(per_received)) if per_received else sku.asset_value
    last = log[-1]["settlement"]
    term = continuation_value(initial, last.get("end_stock", []), last.get("pending", []), log[-1]["forecast"], landed=landed, location_premium=lane_premiums(initial) or None)
    return {"cost_p3": realized + term["adjustment"], "p3_credit": term["continuation_credit"], "p3_landed": landed}


def run_p3_cell(name: str, policy: str, seed: int, reviews: int) -> dict:
    register_p3_methods()
    method = "gated" if policy.startswith("single:") else METHOD[policy]
    builder = build if policy == "cheapest_landed" else (lambda n, s, **kw: variant(n, s, policy, **kw))
    basis = build(name, seed)
    cell = run_cell(name, method, seed, reviews, builder=builder, extra_score=lambda initial, log: p3_score(initial, log, basis))
    cell["policy"] = policy
    cell["method"] = method
    return cell


def _job(args):
    name, policy, seed, reviews = args
    try:
        return run_p3_cell(name, policy, seed, reviews)
    except Exception as exc:  # recorded, never hidden
        return {"fixture": name, "policy": policy, "seed": seed, "status": "ERROR", "failure": f"{type(exc).__name__}: {exc}"[:400], "reviews_completed": 0}


# ── principle checks (on the recorded ZAAD reviews; a few read one planned snapshot) ─────────────

def _zaad(records, name):
    return [r for r in records if r["fixture"] == name and r["policy"] == "gated" and r.get("per_review")]


def _executed(cell) -> list[dict[str, float]]:
    """Per review: {source: executed period-0 units}."""
    return [{s: q for s, q in x["purchases"]} for x in cell["per_review"]]


def _transfer_tie(name: str, seed: int, review: int, other: str) -> dict:
    """Objective equality of the stochastic solve on the exact snapshot of `review` under both variants."""
    from zaad.full.evaluation import long_truth
    from zaad.full.model import solve
    from zaad.full.replay import replay
    from zaad.full.worlds import draw
    from zaad.meio.baselines import register_replay_methods
    register_replay_methods()
    initial = build(name, seed)
    H = initial.horizon
    kept: list = []
    truth = long_truth(initial, seed + 10000, (-(-(review + H) // H)) * H)
    replay(initial, truth, review + 1, "gated", keep_requests=kept, rolling=True)
    snap = kept[review]
    alt = variant(name, seed, other).model_copy(update={k: getattr(snap, k) for k in ("stock", "pipeline", "history", "as_of", "liquidity", "incumbent_orders", "incumbent_transfers", "inherited_on_hand", "shipment_history", "inbound_transfers")})
    worlds = draw(snap, snap.seed, snap.scenarios)
    a, b = solve(snap, worlds, service_floor=True), solve(alt, worlds, service_floor=True)
    equal = a.projected_cost is not None and b.projected_cost is not None and abs(a.projected_cost - b.projected_cost) <= 1e-7 * max(1., abs(a.projected_cost))
    return {"equal": bool(equal), "objective_on": a.projected_cost, "objective_off": b.projected_cost, "status": (a.status, b.status)}


def _snapshot_block(name: str, seed: int = SEEDS[0]):
    from zaad.full.planner import plan
    rep = plan(build(name, seed))
    return rep, rep["sourcing"]


def principle_check(name: str, spec: dict, records: list[dict]) -> dict:
    kind = spec["principle"]
    cells = _zaad(records, name)
    if not cells:
        return {"pass": False, "principle": kind, "evidence": "no complete ZAAD run"}
    req = build(name, SEEDS[0])
    src = {s.id: s for s in req.sources}
    price = {s.id: s.unit_price for s in req.sources}
    ev: dict = {}
    ok = True
    execs = [(c["seed"], _executed(c)) for c in cells]
    if kind == "b_unused":
        others = {s for s in src if src[s].supplier != "supplier"}
        used = {(seed, i, s) for seed, rows in execs for i, row in enumerate(rows) for s, q in row.items() if s in others and q > 1e-9}
        ok = not used
        ev = {"other_supplier_purchases": sorted(used)[:10]}
    elif kind == "unqualified_unused":
        bad = {s for s in src if not (src[s].approved and src[s].compliance == "cleared")}
        used = {(seed, i, s) for seed, rows in execs for i, row in enumerate(rows) for s, q in row.items() if s in bad and q > 1e-9}
        _, blk = _snapshot_block(name)
        said = any("not qualified" in s for s in blk["explanations"])
        ok = not used and said
        ev = {"unqualified_purchases": sorted(used), "block_says_not_qualified": said}
    elif kind == "a_dominant_share":
        # on the reviews where ZAAD acts (a retained incumbent keeps the operator's declared mix by design)
        acted = [row for c in cells for x, row in zip(c["per_review"], _executed(c)) if not x["abstained"]]
        total = sum(q for row in acted for q in row.values())
        a = sum(q for row in acted for s, q in row.items() if src[s].supplier == "supplier")
        all_total = sum(q for _, rows in execs for row in rows for q in row.values())
        all_a = sum(q for _, rows in execs for row in rows for s, q in row.items() if src[s].supplier == "supplier")
        ok = total > 0 and a / total >= .9
        ev = {"a_share_on_acted_reviews": a / total if total else None, "acted_reviews": len(acted), "a_share_all_reviews": all_a / all_total if all_total else None}
    elif kind == "tier2_when_large":
        t1 = [(seed, i, q) for seed, rows in execs for i, row in enumerate(rows) for s, q in row.items() if s == "src_B_tier1" and q > 1e-9]
        t2 = [(seed, i, q) for seed, rows in execs for i, row in enumerate(rows) for s, q in row.items() if s == "src_B_tier2" and q > 1e-9]
        ok = all(q <= 200 + 1e-6 for _, _, q in t1) and all(q >= 250 - 1e-6 for _, _, q in t2) and bool(t2)
        ev = {"tier1_orders": len(t1), "tier2_orders": len(t2), "tier2_units": sum(q for _, _, q in t2)}
    elif kind == "b_orders_executable":
        b = [(seed, i, q) for seed, rows in execs for i, row in enumerate(rows) for s, q in row.items() if s == "src_B" and q > 1e-9]
        ok = all(q >= 1200 - 1e-6 and q * price["src_B"] >= 6000 - 1e-6 for _, _, q in b)
        ev = {"b_orders": [(seed, i, round(q, 1)) for seed, i, q in b]}
    elif kind == "a_at_capacity_then_b":
        # on the reviews where ZAAD acts (a retained incumbent keeps the operator's own mix by design)
        cap = min(src["src_A"].maximum, src["src_A"].capacity_by_period[0])
        checks = []
        for c in cells:
            for i, x in enumerate(c["per_review"]):
                row = {s: q for s, q in x["purchases"]}
                total = sum(row.values())
                if total > cap + 1e-6 and not x["abstained"]:
                    checks.append((c["seed"], i, abs(row.get("src_A", 0.) - cap) <= 1e-6 and row.get("src_B", 0.) > 1e-9))
        ok = bool(checks) and all(c[2] for c in checks)
        ev = {"reviews_above_capacity": len(checks), "all_split_correctly": all(c[2] for c in checks) if checks else None}
    elif kind == "no_split":
        splits = [(seed, i) for seed, rows in execs for i, row in enumerate(rows) if sum(1 for q in row.values() if q > 1e-9) > 1]
        ok = not splits
        ev = {"split_reviews": splits}
        if name.startswith("R4_"):
            _, blk = _snapshot_block(name)
            said = any("share the same origin plant" in s for s in blk["explanations"])
            ok = ok and said
            ev["block_says_shared_plant"] = said
    elif kind == "group_listed":
        _, blk = _snapshot_block(name)
        listed = all(any(g["id"] == "port_x" for g in o["risk_groups"]) for p in blk["pairs"] for o in p["options"])
        ok = listed
        ev = {"port_group_on_every_option": listed}
    elif kind == "both_used_within_capacity":
        used = {s for _, rows in execs for row in rows for s, q in row.items() if q > 1e-9}
        over = [(seed, i, s, q) for seed, rows in execs for i, row in enumerate(rows) for s, q in row.items() if q > min(src[s].maximum, src[s].capacity_by_period[0]) + 1e-6]
        ok = used >= {"src_A", "src_B"} and not over
        ev = {"sources_used": sorted(used), "over_capacity": over}
    elif kind == "min_share_honoured":
        bad = []
        for seed, rows in execs:
            for i, row in enumerate(rows):
                total = sum(row.values())
                if total > 1e-9 and row.get("src_B", 0.) < .3 * total - 1e-6:
                    bad.append((seed, i, row.get("src_B", 0.) / total))
        ok = not bad
        ev = {"reviews_below_minimum": bad}
    elif kind == "no_purchase_in_blackout":
        rep, _ = _snapshot_block(name)
        late = [(a["source"], a["period"], a["quantity"]) for a in rep["actions"] if a.get("action") == "purchase" and a["source"] == "src_B" and 1 <= a["period"] <= 3 and a["quantity"] > 1e-9]
        ok = not late
        ev = {"b_purchases_in_shutdown_periods": late}
    elif kind == "shared_resource_respected":
        cap = req.resources[0].capacity_by_period[0]
        vol = {s.id: next(k.volume for k in req.skus if k.id == s.id and False) if False else 1. for s in req.sources}
        over = [(seed, i, sum(q * vol[s] for s, q in row.items() if "supplier_cap" in src[s].resources)) for seed, rows in execs for i, row in enumerate(rows)
                if sum(q * vol[s] for s, q in row.items() if "supplier_cap" in src[s].resources) > cap + 1e-6]
        s2 = sum(q for _, rows in execs for row in rows for s, q in row.items() if src[s].supplier == "supplier_s2")
        ok = not over and s2 > 0
        ev = {"over_shared_capacity": over, "s2_units": s2}
    elif kind == "shared_mov_respected":
        orders = []
        for seed, rows in execs:
            for i, row in enumerate(rows):
                lines = {s: q for s, q in row.items() if src[s].supplier == "supplier" and q > 1e-9}
                if lines:
                    orders.append((seed, i, sum(q * price[s] for s, q in lines.items()), len(lines)))
        ok = all(v >= 5000 - 1e-6 for _, _, v, _ in orders) and any(n >= 2 for _, _, _, n in orders)
        ev = {"s1_orders": len(orders), "below_mov": [o for o in orders if o[2] < 5000 - 1e-6], "combined_orders": sum(1 for o in orders if o[3] >= 2)}
    elif kind == "whole_packs":
        bad = []
        for seed, rows in execs:
            for i, row in enumerate(rows):
                for s, q in row.items():
                    for m in (src[s].multiple, src[s].case_multiple, src[s].pallet_multiple, src[s].transport_multiple):
                        if m > 0 and q > 1e-9 and abs(q / m - round(q / m)) > 1e-6:
                            bad.append((seed, i, s, q, m))
        ok = not bad
        ev = {"pack_violations": bad}
    elif kind == "conservation":
        res = max(c["network"]["conservation_max_residual"] for c in cells)
        ok = res <= 1e-9
        ev = {"max_residual": res}
    elif kind == "abstains":
        counts = [c["network"]["abstained_reviews"] for c in cells]
        ok = all(n >= 5 for n in counts)
        ev = {"abstained_reviews": counts}
    elif kind == "weak_evidence_flagged":
        _, blk = _snapshot_block(name)
        weak_group = all(g["weak_evidence"] for g in blk["risk_groups"])
        b = next(o for p in blk["pairs"] for o in p["options"] if o["source"] == "src_B")
        said = any("weak" in s for s in blk["explanations"])
        ok = weak_group and b["reliability"]["weak_evidence"] and said
        ev = {"group_weak": weak_group, "b_reliability_weak": b["reliability"]["weak_evidence"], "block_states_weak_evidence": said}
    elif kind in ("prune_identity", "legacy_identity"):
        other = "gated_noprune" if kind == "prune_identity" else "gated_legacy"
        pairs = []
        for c in cells:
            o = next((r for r in records if r["fixture"] == name and r["policy"] == other and r["seed"] == c["seed"] and r.get("per_review")), None)
            if o is None:
                pairs.append((c["seed"], False, "missing variant"))
                continue
            same = [{s: round(q, 6) for s, q in x["purchases"]} for x in c["per_review"]] == [{s: round(q, 6) for s, q in x["purchases"]} for x in o["per_review"]]
            t_a = [round(x["transfer_units"], 6) for x in c["per_review"]]
            t_b = [round(x["transfer_units"], 6) for x in o["per_review"]]
            if same and t_a != t_b:
                # executed transfer quantities are degenerate on these fixtures (P2 performance pass): a tie
                # between equal-objective plans, proved by objective equality on the first differing snapshot
                k = next(i for i, (u, v) in enumerate(zip(t_a, t_b)) if u != v)
                tie = _transfer_tie(name, c["seed"], k, other)
                pairs.append((c["seed"], tie["equal"], f"purchases identical; transfers differ at review {k}: objective tie {tie}"))
            else:
                pairs.append((c["seed"], same and t_a == t_b, "identical" if same and t_a == t_b else "differs"))
        ok = bool(pairs) and all(p[1] for p in pairs)
        ev = {"seeds": pairs}
    elif kind == "no_order_no_allocation":
        early = [(seed, i, sum(row.values())) for seed, rows in execs for i, row in enumerate(rows[:3]) if sum(row.values()) > 1e-9]
        _, blk = _snapshot_block(name)
        zero = all(p["recommendation"] == "NO_ORDER" and all(o["quantity_plan"] <= 1e-9 for o in p["options"]) for p in blk["pairs"])
        ok = not early and zero
        ev = {"early_purchases": early, "block_no_order": zero}
    elif kind == "not_worse":
        ok = True
        ev = {"gate": "economic and service gates only"}
    else:
        ok = False
        ev = {"error": f"unknown principle {kind}"}
    return {"pass": bool(ok), "principle": kind, "evidence": ev}


# ── summary ──────────────────────────────────────────────────────────────────

def _policy_stats(rs: list[dict]) -> dict:
    branches = sorted({sid for r in rs for sid in r["service_by_branch"]})
    return {"runs": len(rs), "cost": st.mean(r["score"]["cost_p3"] for r in rs), "cost_p2": st.mean(r["score"]["cost_p2"] for r in rs), "realized": st.mean(r["score"]["realized"] for r in rs),
            "service_by_branch": {sid: st.mean((r["service_by_branch"][sid]["achieved"] or 0.) for r in rs) for sid in branches},
            "target_by_branch": {sid: rs[0]["service_by_branch"][sid]["target"] for sid in branches},
            "min_branch_service": min(st.mean((r["service_by_branch"][sid]["achieved"] or 0.) for r in rs) for sid in branches),
            "severe_starvation": any((r["service_by_branch"][sid]["achieved"] or 0.) < .5 * r["service_by_branch"][sid]["target"] for r in rs for sid in branches),
            "purchase_units": st.mean(r["network"]["purchase_units"] for r in rs), "transfer_units": st.mean(r["network"]["transfer_units"] for r in rs),
            "abstained_reviews": st.mean(r["network"]["abstained_reviews"] for r in rs),
            "reverse_pair_units": st.mean(r["network"]["reverse_pair_units"] for r in rs),
            "conservation_max_residual": max(r["network"]["conservation_max_residual"] for r in rs),
            "wall_p50": st.mean(r["compute"]["wall_p50"] for r in rs), "wall_max": max(r["compute"]["wall_max"] for r in rs),
            "solve_statuses": {k: sum(r["compute"]["solve_statuses"].get(k, 0) for r in rs) for k in {k for r in rs for k in r["compute"]["solve_statuses"]}}}


def p3_summary(records: list[dict], tag: str, reviews: int = REVIEWS) -> dict:
    by: dict[tuple[str, str], list[dict]] = {}
    for r in records:
        by.setdefault((r["fixture"], r["policy"]), []).append(r)
    out: dict = {"tag": tag, "reviews": reviews, "fixtures": {}}
    present = {r["fixture"] for r in records}
    for name, spec in FIXTURES.items():
        if name not in present:
            continue
        pols = sorted({p for (n, p) in by if n == name})
        complete = {p: [r for r in by[name, p] if r.get("status") == "COMPLETE" and r.get("reviews_completed") == reviews] for p in pols}
        entry: dict = {"family": spec["family"], "tolerance": spec["tolerance"], "policies": {}, "failures": {}}
        for p, rs in complete.items():
            if rs:
                entry["policies"][p] = _policy_stats(rs)
            else:
                entry["failures"][p] = [f"{r.get('status')}: {r.get('failure')}" for r in by[name, p]]
        zaad = entry["policies"].get("gated")
        singles = {p: v for p, v in entry["policies"].items() if p.startswith("single:")}
        comparators = {p: v for p, v in entry["policies"].items() if p in ("incumbent_mix", "cheapest_landed")}
        if singles:
            best_single = min(singles, key=lambda p: singles[p]["cost"])
            comparators[best_single] = singles[best_single]
        valid = {p: v for p, v in comparators.items() if zaad is None or all(v["service_by_branch"][s] >= zaad["service_by_branch"][s] - .05 for s in v["service_by_branch"])}
        entry["valid_baselines"] = sorted(valid)
        inc = entry["policies"].get("incumbent_mix")
        checks: dict = {}
        if zaad and valid:
            best = min(valid, key=lambda p: valid[p]["cost"])
            gap = (zaad["cost"] - valid[best]["cost"]) / max(1., abs(valid[best]["cost"]))
            checks["zaad_not_worse"] = {"pass": gap <= spec["tolerance"] + 1e-12, "gap": gap, "tolerance": spec["tolerance"], "best_baseline": best, "best_cost": valid[best]["cost"], "zaad_cost": zaad["cost"],
                                        "basis": "cost_p3 (policy-independent continuation)", "gap_p2_basis": (zaad["cost_p2"] - min(v["cost_p2"] for v in valid.values())) / max(1., abs(min(v["cost_p2"] for v in valid.values())))}
            mode = spec.get("service_mode", "incumbent")
            if mode == "floor" or inc is None:
                unavoidable = bool(inc is not None and inc["severe_starvation"] and zaad["min_branch_service"] >= inc["min_branch_service"] - .01)
                checks["service"] = {"pass": (not zaad["severe_starvation"] or unavoidable) and (inc is None or zaad["min_branch_service"] >= inc["min_branch_service"] - .01), "mode": mode}
            else:
                checks["service"] = {"pass": all(zaad["service_by_branch"][s] >= min(zaad["target_by_branch"][s], inc["service_by_branch"][s]) - .01 for s in zaad["service_by_branch"]),
                                     "mode": mode, "zaad": zaad["service_by_branch"], "incumbent": inc["service_by_branch"]}
            checks["conservation"] = {"pass": zaad["conservation_max_residual"] <= 1e-9, "residual": zaad["conservation_max_residual"]}
            checks["no_reverse_movement"] = {"pass": zaad["reverse_pair_units"] <= 1e-6}
            checks["no_physical_failure"] = {"pass": all(r.get("status") == "COMPLETE" for r in by.get((name, "gated"), []))}
        try:
            checks["principle"] = principle_check(name, spec, records)
        except Exception as exc:
            checks["principle"] = {"pass": False, "principle": spec["principle"], "evidence": {"error": f"{type(exc).__name__}: {exc}"[:300]}}
        entry["checks"] = checks
        entry["pass"] = bool(zaad) and bool(valid) and all(c["pass"] for c in checks.values())
        out["fixtures"][name] = entry
    zaad_cells = [r for r in records if r["policy"] == "gated" and r.get("per_review")]
    walls = sorted(x["wall_seconds"] for r in zaad_cells for x in r["per_review"])
    slow = [(r["fixture"], r["seed"], x["review"], round(x["wall_seconds"], 1), x["state"]) for r in zaad_cells for x in r["per_review"] if x["wall_seconds"] > 60]
    statuses: dict = {}
    for r in zaad_cells:
        for k, v in r["compute"]["solve_statuses"].items():
            statuses[k] = statuses.get(k, 0) + v
    out["runtime"] = {"reviews": len(walls), "p50": st.median(walls) if walls else None, "p95": walls[max(0, int(.95 * len(walls)) - 1)] if walls else None,
                      "max": max(walls, default=None), "over_60s": slow, "over_180s": [s for s in slow if s[3] > 180], "solve_statuses": statuses,
                      "by_family": {fam: {"p50": st.median(v), "max": max(v)} for fam, v in
                                    {fam: [x["wall_seconds"] for r in zaad_cells for x in r["per_review"] if FIXTURES[r["fixture"]]["family"] == fam] for fam in ("economics", "reliability", "constraints", "sector", "network", "abstention")}.items() if v}}
    out["errors"] = [(r["fixture"], r["policy"], r["seed"], r.get("failure")) for r in records if r.get("status") in ("ERROR", "PHYSICAL_FAILURE")]
    out["pass_count"] = sum(1 for e in out["fixtures"].values() if e["pass"])
    out["fixture_count"] = len(out["fixtures"])
    return out


def tables(summary: dict) -> str:
    lines = [f"# P3 benchmark `{summary['tag']}`", "", f"{summary['pass_count']} / {summary['fixture_count']} fixtures PASS", "",
             "| fixture | best baseline | ZAAD gap | tol | ZAAD min branch service | incumbent mix | abstained / 8 | wall p50 / max s | principle |",
             "|---|---|---|---|---|---|---|---|---|"]
    for name, e in summary["fixtures"].items():
        c = e["checks"]
        z = e["policies"].get("gated") or {}
        inc = e["policies"].get("incumbent_mix") or {}
        nw = c.get("zaad_not_worse", {})
        lines.append(f"| {name} | {nw.get('best_baseline', '-')} | {nw.get('gap', float('nan')):+.2%} | {e['tolerance']:.0%} | {z.get('min_branch_service', float('nan')):.3f} | "
                     f"{inc.get('min_branch_service', float('nan')):.3f} | {z.get('abstained_reviews', float('nan')):.1f} | {z.get('wall_p50', float('nan')):.1f} / {z.get('wall_max', float('nan')):.1f} | "
                     f"{c.get('principle', {}).get('principle')} ({'PASS' if c.get('principle', {}).get('pass') else 'FAIL'}) | {'PASS' if e['pass'] else 'FAIL'}")
    rt = summary["runtime"]
    lines += ["", f"Runtime (ZAAD reviews {rt['reviews']}): p50 {rt['p50']}, p95 {rt['p95']}, max {rt['max']}; over 60 s: {len(rt['over_60s'])}; over 180 s: {len(rt['over_180s'])}; solve statuses {rt['solve_statuses']}",
              f"Errors: {summary['errors']}"]
    return "\n".join(lines) + "\n"


def _finish(records: list[dict], tag: str) -> int:
    summary = p3_summary(records, tag)
    (OUT / f"{tag}.summary.json").write_text(json.dumps(summary, indent=1, allow_nan=True, default=str))
    (OUT / f"{tag}.tables.md").write_text(tables(summary))
    print(tables(summary))
    for name, e in summary["fixtures"].items():
        if not e["pass"]:
            print("FAIL", name, {k: v for k, v in e["checks"].items() if not v.get("pass")}, e["failures"])
    return 0 if summary["pass_count"] == summary["fixture_count"] else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="p3_dev")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--fixtures", default="")
    ap.add_argument("--policies", default="")
    ap.add_argument("--seeds", default=",".join(str(s) for s in SEEDS))
    ap.add_argument("--reviews", type=int, default=REVIEWS)
    ap.add_argument("--summarize-only", action="store_true")
    a = ap.parse_args()
    only = {x for x in a.fixtures.split(",") if x}
    OUT.mkdir(parents=True, exist_ok=True)
    if a.summarize_only:
        records = [json.loads(line) for line in (OUT / f"{a.tag}.jsonl").read_text().splitlines() if line.strip()]
        return _finish(records, a.tag)
    names = [n for n in FIXTURES if not only or n.split("_")[0] in only or n in only]
    seeds = [int(s) for s in a.seeds.split(",")]
    jobs = []
    for n in names:
        for s in seeds:
            pols = [p for p in a.policies.split(",") if p] or policies_for(n, s)
            jobs += [(n, p, s, a.reviews) for p in pols]
    path = OUT / f"{a.tag}.jsonl"
    started = time.time()
    records = []
    with path.open("w") as fh, ProcessPoolExecutor(max_workers=a.workers) as pool:
        for cell in pool.map(_job, jobs):
            records.append(cell)
            fh.write(json.dumps(cell, allow_nan=True, default=str) + "\n")
            fh.flush()
            print(f"  {cell['fixture']:<40} {cell['policy']:<20} seed {cell['seed']} {str(cell.get('status')):<16} reviews {cell.get('reviews_completed')} "
                  f"cost {((cell.get('score') or {}).get('cost_p3') or 0):>9,.0f} wall p50 {((cell.get('compute') or {}).get('wall_p50') or 0):5.1f}s  [{time.time() - started:.0f}s]", flush=True)
    return _finish(records, a.tag)


if __name__ == "__main__":
    raise SystemExit(main())
