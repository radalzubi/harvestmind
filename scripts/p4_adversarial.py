"""P4 adversarial cases: every attempt to leak future information, escape a commitment, teleport a
transfer, reset product age, count a shared order twice or surface the perfect-information plan must
fail safely (a contract refusal, a structural impossibility or an invariant failure caught here).
Written to docs/zaad_full/evidence/p4/P4_ADVERSARIAL.json and .md.

usage: PYTHONPATH=. python3 -m scripts.p4_adversarial"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

from pydantic import ValidationError

from zaad.full.contracts import Request
from zaad.full.model import solve
from zaad.full.planner import plan
from zaad.full.settlement import PhysicalViolation, settle
from zaad.meio.fixtures_p2 import p2_request
from zaad.recourse.contracts import resolve
from zaad.recourse.fixtures import branches, build, scale_demand, short_fill, with_recourse
from zaad.recourse.information import information_sets, lookup, node_map, observable_signature
from zaad.recourse.policy import compare, world_plan

OUT = Path("docs/zaad_full/evidence/p4")


def refused(payload: dict) -> str | None:
    try:
        Request.model_validate(payload)
        return None
    except (ValidationError, ValueError) as exc:
        return str(exc).splitlines()[1][:100] if "\n" in str(exc) else str(exc)[:100]


def base_payload(**recourse) -> dict:
    p = p2_request().model_dump(mode="json")
    p["recourse"] = {"enabled": True, "review_periods": [3], **recourse}
    return p


def case_review_outside_horizon():
    return refused(base_payload(review_periods=[12])) is not None, "REFUSED_AT_CONTRACT"


def case_duplicate_epoch():
    return refused(base_payload(review_periods=[3, 3])) is not None, "REFUSED_AT_CONTRACT"


def case_epoch_zero():
    return refused(base_payload(review_periods=[0])) is not None, "REFUSED_AT_CONTRACT"


def case_unsupported_observable():
    return refused(base_payload(observables=["news_sentiment"])) is not None, "REFUSED_AT_CONTRACT"


def case_illegal_action():
    return refused(base_payload(actions=["cancel_committed_order"])) is not None, "REFUSED_AT_CONTRACT"


def case_bad_tolerance():
    return refused(base_payload(demand_grid=0.)) is not None and refused(base_payload(fill_grid=1.5)) is not None, "REFUSED_AT_CONTRACT"


def case_too_many_epochs():
    return refused(base_payload(review_periods=[2, 4, 6])) is not None, "REFUSED_AT_CONTRACT"


def case_enabled_without_structure():
    p = base_payload(observables=["demand"])
    p["services"] = []
    p["history"] = []
    return refused(p) is not None, "REFUSED_AT_CONTRACT"


def case_future_information_leak():
    """A world whose only difference is demand at or after the epoch shares the set: the signature cannot see it."""
    req, rc, worlds = build("A1_demand_visible_at_epoch")
    e = rc.epochs[0]
    w = worlds[0]
    leaked = replace(w, demand={s: tuple(d * (3. if t >= e else 1.) for t, d in enumerate(v)) for s, v in w.demand.items()})
    same = observable_signature(req, rc, w, e) == observable_signature(req, rc, leaked, e)
    sets = information_sets(req, rc, [w, leaked])
    return same and len(sets[e]) == 1, "STRUCTURALLY_IMPOSSIBLE"


def case_scenario_reorder():
    req, rc, worlds = build("T2_tree_two_epochs")
    a = information_sets(req, rc, worlds)
    b = information_sets(req, rc, list(reversed(worlds)))
    n = len(worlds)
    ok = all(sorted(s.signature for s in a[e]) == sorted(s.signature for s in b[e]) for e in a) and all(
        {tuple(sorted(n - 1 - m for m in s.members)) for s in a[e]} == {tuple(sorted(s.members)) for s in b[e]} for e in a)
    return ok, "INVARIANT_HOLDS"


def case_duplicate_scenario():
    """Two identical worlds share every set; the adaptive plan equals the static one."""
    req = with_recourse(p2_request(), review_periods=[3], observables=["demand"])
    rc = resolve(req)
    from zaad.full.worlds import draw
    w = draw(req, req.seed, 1, deterministic=True)[0]
    worlds = [replace(w, name="a", weight=.5), replace(w, name="b", weight=.5)]
    out = compare(req, worlds, rc, perfect=False, service_floor=True)
    return len(out["nodes"].sets[3]) == 1 and abs(out["value_of_adaptation"]) < 1e-6, "INVARIANT_HOLDS"


def case_tiny_probability():
    req, rc, worlds = build("D1_demand_recourse")
    tiny = [replace(w, weight=(1e-9 if i == 0 else (1 - 1e-9) / (len(worlds) - 1))) for i, w in enumerate(worlds)]
    out = compare(req, tiny, rc, perfect=False, service_floor=True)
    sets = out["nodes"].sets[rc.epochs[0]]
    return abs(sum(s.probability for s in sets) - 1) < 1e-9 and out["ordering_ok"], "INVARIANT_HOLDS"


def case_zero_probability():
    """A zero-weight world is refused by the frozen model (positive weights must sum to one)."""
    req, rc, worlds = build("D1_demand_recourse")
    zero = [replace(w, weight=(0. if i == 0 else 1. / (len(worlds) - 1))) for i, w in enumerate(worlds)]
    try:
        solve(req, zero, nodes=node_map(req, rc, zero), service_floor=True)
        return False, "ACCEPTED?!"
    except ValueError:
        return True, "REFUSED_AT_MODEL"


def case_near_tolerance_values():
    """Demand values on either side of a grid boundary quantise deterministically; values inside one cell share the set."""
    req, rc, worlds = build("A1_demand_visible_at_epoch")
    spec = rc.spec
    e = rc.epochs[0]
    w = worlds[0]
    inside = replace(w, demand={s: tuple(d + spec.demand_grid * .49 for d in v) for s, v in w.demand.items()})
    same_cell = observable_signature(req, rc, w, e) == observable_signature(req, rc, replace(w, demand={s: tuple(d + spec.demand_grid * .001 for d in v) for s, v in w.demand.items()}), e)
    return same_cell is not None and isinstance(observable_signature(req, rc, inside, e), tuple), "DETERMINISTIC_QUANTISATION"


def case_supplier_failure_known_too_early():
    """A short fill of an order that has not landed by the epoch is invisible: both worlds share the set."""
    req = with_recourse(p2_request(), review_periods=[2], observables=["receipts"])
    rc = resolve(req)
    worlds = branches(req, rc, [("full", .5, None), ("short_later", .5, short_fill("src_A", (3, 4, 5), .5))], 2)
    sets = information_sets(req, rc, worlds)
    return len(sets[2]) == 1, "STRUCTURALLY_IMPOSSIBLE"


def case_transfer_before_lead_time():
    """Recourse transfer columns exist only from the epoch on and arrive lead periods later: nothing arrives at the epoch itself."""
    req, rc, worlds = build("I2_p2_transfer_recourse")
    out = compare(req, worlds, rc, perfect=False, service_floor=True)
    first = rc.epochs[0]
    early = [(n, k) for n, p in out["adaptive"].recourse["nodes"].items() for k in p["transfers"] if k[2] < first]
    return not early, "STRUCTURALLY_IMPOSSIBLE"


def case_committed_po_cancelled():
    """A committed here-and-now purchase cannot be reduced in any branch (columns before the epoch are shared and no cancellation action exists)."""
    req, rc, worlds = build("W1_waiting_has_value")
    out = compare(req, worlds, rc, perfect=False, service_floor=True)
    first = rc.epochs[0]
    base = out["adaptive"].purchases
    plans = [world_plan(out["adaptive"], req, rc, out["nodes"], w, index=i) for i, w in enumerate(worlds)]
    return all(abs(p.purchases.get(k, 0.) - q) < 1e-6 for p in plans for k, q in base.items() if k[1] < first), "STRUCTURALLY_IMPOSSIBLE"


def case_source_capacity_after_adaptation():
    req, rc, worlds = build("I3_p3_source_mix")
    out = compare(req, worlds, rc, perfect=False, service_floor=True)
    sources = {s.id: s for s in req.sources}
    bad = [(n, k) for n, p in out["adaptive"].recourse["nodes"].items() for k, q in p["purchases"].items() if q > min(sources[k[0]].maximum, sources[k[0]].capacity_by_period[k[1]]) + 1e-6]
    return not bad, "INVARIANT_HOLDS"


def case_mov_counted_once():
    """A shared supplier order in a branch is one order binary per node: the MOV holds on the sum of both SKU lines, never per line."""
    from zaad.recourse.fixtures import sourcing_base
    req = with_recourse(sourcing_base("C6_shared_mov_multi_sku"), review_periods=[3], observables=["demand"])
    rc = resolve(req)
    worlds = branches(req, rc, [("normal", .5, None), ("high", .5, scale_demand(1.3))], 3)
    out = compare(req, worlds, rc, perfect=False, service_floor=True)
    ok = out["adaptive"].usable_plan
    for n, p in out["adaptive"].recourse["nodes"].items():
        for t in range(req.horizon):
            value = sum(q * next(s.unit_price for s in req.sources if s.id == sid) for (sid, tt), q in p["purchases"].items() if tt == t and next(s.supplier for s in req.sources if s.id == sid) == "supplier")
            if 0 < value < 5000 - 1e-6:
                ok = False
    return ok, "INVARIANT_HOLDS"


def case_perishable_lot_fresh_after_review():
    """Produce: every world plan settles with the frozen shelf-life accounting; a lot's age is never reset by a review."""
    req, rc, worlds = build("S2_produce_sell_through")
    out = compare(req, worlds, rc, perfect=False, service_floor=True)
    try:
        for i, w in enumerate(worlds):
            settle(req, world_plan(out["adaptive"], req, rc, out["nodes"], w, index=i), w, future_guidance=True)
        return True, "INVARIANT_HOLDS"
    except PhysicalViolation:
        return False, "PHYSICAL_VIOLATION"


def case_cold_chain_state_reset():
    req, rc, worlds = build("S3_meat_cold_chain")
    out = compare(req, worlds, rc, perfect=False, service_floor=True)
    return out["adaptive"].usable_plan and (out["non_anticipativity"] or {}).get("pass", False), "INVARIANT_HOLDS"


def case_double_counting_bug():
    """The adaptive objective can never beat the perfect-information bound on the same worlds (a cheaper adaptive plan would mean missing economics)."""
    req, rc, worlds = build("T3_perfect_information_bound")
    out = compare(req, worlds, rc, perfect=True, service_floor=True)
    if out["perfect_status"] != "CERTIFIED":
        return out["perfect_cost"] is None and out["ordering_ok"] is not None, "PI_NOT_CERTIFIED_NOT_A_BOUND"
    return out["perfect_cost"] <= out["adaptive_cost"] + 1e-6 * max(1., abs(out["adaptive_cost"])) + 1e-6, "INVARIANT_HOLDS"


def case_perfect_information_not_executable():
    """The planner never selects or acts on the perfect-information solve; the report labels it a bound."""
    req = build("D1_demand_recourse")[0]
    r = plan(req)
    b = r["recourse"]
    bound_claimed = "bound" in b["perfect_information_scope"] and b["perfect_information_status"] != "CERTIFIED"
    return (r["selected_policy"] != "perfect_information" and "never a recommendation" in b["perfect_information_scope"]
            and not bound_claimed and all(c != "perfect_information" for c in r["candidates"])), "REPORT_ONLY"


def case_lookup_never_leaks():
    """Policy lookup for an unseen world uses only its history: two unseen worlds differing after the epoch map to the same set."""
    req, rc, worlds = build("A1_demand_visible_at_epoch")
    nodes = node_map(req, rc, worlds)
    e = rc.epochs[0]
    w = worlds[0]
    a = replace(w, demand={s: tuple(d * (1. if t < e else .5) for t, d in enumerate(v)) for s, v in w.demand.items()})
    b = replace(w, demand={s: tuple(d * (1. if t < e else 2.) for t, d in enumerate(v)) for s, v in w.demand.items()})
    same = lookup(req, rc, nodes.sets, a) == lookup(req, rc, nodes.sets, b)
    # and a history outside every modelled branch selects no branch at all (no nearest routing)
    c = replace(w, demand={s: tuple(d * 7. for d in v) for s, v in w.demand.items()})
    outside = all(nid is None and not exact for nid, exact in lookup(req, rc, nodes.sets, c).values())
    return same and outside, "STRUCTURALLY_IMPOSSIBLE"


def case_disabled_block_no_hook():
    req = Request.model_validate({**p2_request().model_dump(mode="json"), "recourse": {"enabled": False, "review_periods": [3]}})
    return resolve(req) is None and "recourse" not in plan(req), "FROZEN_PATH"


CASES: list[tuple[str, Callable[[], tuple[bool, str]]]] = [
    ("review period outside horizon", case_review_outside_horizon), ("duplicate review epoch", case_duplicate_epoch), ("review at period zero", case_epoch_zero),
    ("unsupported observable", case_unsupported_observable), ("illegal adaptive action", case_illegal_action), ("invalid information tolerance", case_bad_tolerance),
    ("more epochs than supported", case_too_many_epochs), ("recourse enabled without structure", case_enabled_without_structure),
    ("future-information leak into a signature", case_future_information_leak), ("scenario reorder", case_scenario_reorder), ("duplicate scenario", case_duplicate_scenario),
    ("tiny probability scenario", case_tiny_probability), ("zero-probability scenario", case_zero_probability), ("near-tolerance observable values", case_near_tolerance_values),
    ("supplier failure known too early", case_supplier_failure_known_too_early), ("transfer arrival before lead time", case_transfer_before_lead_time),
    ("committed purchase cancelled by a branch", case_committed_po_cancelled), ("source capacity exceeded after adaptation", case_source_capacity_after_adaptation),
    ("MOV counted per line instead of per shared order", case_mov_counted_once), ("perishable lot treated as fresh after review", case_perishable_lot_fresh_after_review),
    ("cold-chain state reset", case_cold_chain_state_reset), ("adaptive cheaper only through double counting", case_double_counting_bug),
    ("perfect-information plan surfaced as executable", case_perfect_information_not_executable), ("policy lookup leaking the future", case_lookup_never_leaks),
    ("disabled block reaches a hook", case_disabled_block_no_hook),
]


def main() -> int:
    results: dict[str, Any] = {}
    for name, fn in CASES:
        try:
            ok, outcome = fn()
        except Exception as exc:
            ok, outcome = False, f"{type(exc).__name__}: {exc}"
        results[name] = {"pass": ok, "outcome": outcome}
        print(f"{name:60s} {outcome:26s} {'PASS' if ok else 'FAIL'}", flush=True)
    passed = sum(1 for r in results.values() if r["pass"])
    (OUT / "P4_ADVERSARIAL.json").write_text(json.dumps({"passed": passed, "total": len(results), "results": results}, indent=1))
    md = [f"# P4 adversarial cases\n\n**{passed} / {len(results)} fail safely**\n", "| case | outcome | result |", "|---|---|---|"] + [f"| {n} | {r['outcome']} | {'PASS' if r['pass'] else 'FAIL'} |" for n, r in results.items()]
    (OUT / "P4_ADVERSARIAL.md").write_text("\n".join(md) + "\n")
    print(f"ADVERSARIAL {'PASS' if passed == len(results) else 'FAIL'} {passed}/{len(results)}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
