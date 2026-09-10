"""Fast frozen-behaviour regression for the canonical branch (post-P1 integration, brief section 10).

Detects integration corruption of the frozen optimizer without a benchmark matrix: short rolling
replays of representative P1 fixtures (B, T, Q, A; one seed, the first N reviews) must reproduce, order
for order, the first N reviews of the authoritative P1 freeze record (`closure/horizon52_cycle.jsonl.gz`,
the replay is deterministic and review k never depends on later reviews); one P0 cell (cell 15 of the
six-cell arm) must reproduce the decisions recorded by the P0 isolation arm (`closure/p0_arm_router_cycle.json`).
Runs in a few minutes; exits non-zero on any difference. Nothing is written.

usage: PYTHONPATH=. python3 -m scripts.zaad_canonical_regression [--reviews 12] [--skip-p0]"""
from __future__ import annotations

import argparse
import json
import sys
import time

from scripts.p1_fixtures import build
from scripts.p1_horizon_tables import EVID, load
from zaad.full.contracts import Request
from zaad.full.evaluation import long_truth
from zaad.full.replay import replay
from zaad.full.tolerance import is_dust

PRODUCT = {k: Request.model_fields[k].default for k in ("stratified_scenarios", "timing_tiebreak", "analytic_shortage")}
P1_CONTROLS = ("B_fixed_order_cost_replace_sold", "T_combined_realistic", "Q_volatile_demand_high_target", "A_no_terms_good_incumbent")
SEED = 41001
P0_CELL = 15
P0_ARM = "router_cycle"


def _orders(rows: list[dict]) -> list[tuple[int, str, float]]:
    out = []
    for row in rows:
        for source, quantity in row["purchases"]:
            if not is_dust(quantity):
                out.append((int(row["review"]), str(source), round(float(quantity), 3)))
    return out


def p1_identity(reviews: int) -> list[dict]:
    _, by = load(EVID / "closure" / "horizon52_cycle.jsonl")
    results = []
    for name in P1_CONTROLS:
        expected_rows = by[name, "gated", SEED]["per_review"][:reviews]
        expected = _orders(expected_rows)
        req = build(name, SEED).model_copy(update=PRODUCT)
        truth = long_truth(req, SEED + 10000, 12 * (-(-(reviews - 1 + 12) // 12)))
        started = time.time()
        out = replay(req, truth, reviews, "gated", rolling=True)
        got = _orders([{"review": r["review"], "purchases": [(p["source"], p["quantity"]) for p in r["purchases"]]} for r in out.get("reviews", [])])
        statuses_expected = [str(r["status"]) for r in expected_rows]
        statuses_got = [str((r["warnings"] or [None])[0]) for r in out.get("reviews", [])]
        results.append({"fixture": name, "reviews": reviews, "identical": got == expected and statuses_got == statuses_expected,
                        "orders_expected": expected, "orders_got": got, "seconds": round(time.time() - started, 1)})
    return results


# Decision keys of the frozen P0 semantics (scripts/p1_ownership_compare.py): the review's state, the
# candidate sets requested and built, the outcome status, recovery mode, the feasible set and the final
# P0 purchases must match exactly. The selected candidate's LABEL is compared too, but a label
# difference between candidates that carry the same plan is candidate-timeout variance, not an
# operational decision: on a slower runner a time-limited candidate leaves the cost ranking and one of
# the equal-cost plans wins under another name (the pass-J and pass-M closeouts record this on the
# wall-clock-limited cells). Such a review counts as identical only when its final P0 purchases, state,
# status and feasible set are identical; it is reported as a label variance.
P0_STRICT_KEYS = ("state", "requested", "built", "status", "recovery_mode", "feasible")
P0_LABEL_KEYS = ("selected", "chosen")


def _norm(v):
    if isinstance(v, dict):
        return {k: (round(x, 6) if isinstance(x, float) else x) for k, x in v.items()}
    return v


def p0_identity() -> dict:
    """Cell 15 replayed under the recorded arm's settings and compared review by review with the frozen
    decision semantics above."""
    from scripts.p1_p0_arms import run_cells
    arm = json.load(open(EVID / "closure" / f"p0_arm_{P0_ARM}.json"))
    recorded = arm[str(P0_CELL)]["per_review"]
    started = time.time()
    got = run_cells(P0_ARM, [P0_CELL], write=False)[P0_CELL]["per_review"]
    diffs, label_variance = [], []
    for i, (x, y) in enumerate(zip(recorded, got)):
        strict = all(x.get(k) == y.get(k) for k in P0_STRICT_KEYS) and _norm(x.get("final_p0")) == _norm(y.get("final_p0")) and (y.get("p1_classes_added") or []) == []
        labels = all(x.get(k) == y.get(k) for k in P0_LABEL_KEYS)
        if not strict:
            diffs.append((i, {k: (x.get(k), y.get(k)) for k in P0_STRICT_KEYS if x.get(k) != y.get(k)},
                          {"final_p0": (_norm(x.get("final_p0")), _norm(y.get("final_p0")))} if _norm(x.get("final_p0")) != _norm(y.get("final_p0")) else {}))
        elif not labels:
            label_variance.append((i, {k: (x.get(k), y.get(k)) for k in P0_LABEL_KEYS if x.get(k) != y.get(k)}))
    return {"cell": P0_CELL, "arm": P0_ARM, "identical": not diffs and len(got) == len(recorded), "reviews": len(got),
            "diffs": diffs[:3], "label_variance": label_variance, "seconds": round(time.time() - started, 1),
            "note": "every review protection-owned" if all(r.get("owner") == "PROTECTION_RECOVERY" for r in got) else "a review was not protection-owned"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reviews", type=int, default=12)
    ap.add_argument("--skip-p0", action="store_true")
    a = ap.parse_args()
    ok = True
    for r in p1_identity(a.reviews):
        print(f"P1 {r['fixture']:32s} reviews {r['reviews']:2d} identical {r['identical']} ({r['seconds']} s)")
        if not r["identical"]:
            ok = False
            print("   expected", r["orders_expected"][:8])
            print("   got     ", r["orders_got"][:8])
    if not a.skip_p0:
        try:
            r = p0_identity()
            print(f"P0 cell {r['cell']} ({r['arm']}) identical {r['identical']} reviews {r['reviews']} ({r['seconds']} s) {r['note']}")
            if r["diffs"]:
                print("   decision differences", r["diffs"])
            if r["label_variance"]:
                print("   candidate-label variance under time limits (same plan, state, status, feasible set):", r["label_variance"])
            ok = ok and r["identical"]
        except Exception as exc:  # noqa: BLE001 - report, never mask, a broken P0 anchor
            print(f"P0 check could not run: {exc!r}")
            ok = False
    print("CANONICAL REGRESSION", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
