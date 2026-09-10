"""Review-by-review decision comparison of two P2 benchmark records (P2 performance pass).

For every (fixture, policy, seed) cell present in both records the per-review keys are compared:
screen state, planner owner, status, abstention, executed purchases and transfers (period-zero
actions after settlement, dust-tolerant), settled cost, served units and the candidate solve
statuses. The output lists every differing review with the first differing key, the wall-time
change per cell, and a summary suitable for the performance evidence.

usage: PYTHONPATH=. python3 -m scripts.p2_decision_compare BEFORE.jsonl AFTER.jsonl [--policy gated] [--tol 1e-6] [--out name]"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics as st

from scripts.p2_benchmark import OUT

KEYS = ("state", "owner", "status", "abstained", "purchases", "transfers", "cost", "served", "solver_status")


def _norm(value, tol: float):
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, list):
        return sorted((tuple(_norm(v, tol) for v in x) if isinstance(x, (list, tuple)) else _norm(x, tol)) for x in value if not (isinstance(x, (list, tuple)) and len(x) >= 2 and isinstance(x[-1], (int, float)) and abs(x[-1]) < tol))
    if isinstance(value, dict):
        return {k: _norm(v, tol) for k, v in sorted(value.items())}
    return value


def _same(a, b, tol: float) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= tol * max(1., abs(a), abs(b))
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_same(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_same(a[k], b[k], tol) for k in a)
    return a == b


def compare(before: list[dict], after: list[dict], policy: str | None, tol: float) -> dict:
    index = {(r["fixture"], r["policy"], r["seed"]): r for r in before}
    cells = []
    differing = []
    walls_before, walls_after = [], []
    for r in after:
        key = (r["fixture"], r["policy"], r["seed"])
        if policy and r["policy"] != policy:
            continue
        b = index.get(key)
        if b is None:
            cells.append({"cell": key, "note": "absent in BEFORE"})
            continue
        rows_b, rows_a = b.get("per_review") or [], r.get("per_review") or []
        identical = 0
        first_diff = None
        for xb, xa in zip(rows_b, rows_a):
            diff_key = None
            for k in KEYS:
                if not _same(_norm(xb.get(k), tol), _norm(xa.get(k), tol), tol):
                    diff_key = k
                    break
            if diff_key is None:
                identical += 1
            else:
                if first_diff is None:
                    first_diff = xb["review"]
                differing.append({"cell": key, "review": xb["review"], "key": diff_key, "before": _norm(xb.get(diff_key), tol), "after": _norm(xa.get(diff_key), tol),
                                  "state_before": xb.get("state"), "state_after": xa.get("state"),
                                  "candidate_status_before": xb.get("solve_quality"), "candidate_status_after": xa.get("solve_quality"),
                                  "wall_before": xb.get("wall_seconds"), "wall_after": xa.get("wall_seconds")})
        if r["policy"] == "gated":
            walls_before += [x["wall_seconds"] for x in rows_b]
            walls_after += [x["wall_seconds"] for x in rows_a]
        cells.append({"cell": key, "reviews": len(rows_a), "identical": identical, "first_difference": first_diff,
                      "seconds_before": b.get("seconds"), "seconds_after": r.get("seconds"),
                      "cost_before": (b.get("score") or {}).get("p2_cost"), "cost_after": (r.get("score") or {}).get("p2_cost"),
                      "status_before": b.get("status"), "status_after": r.get("status")})

    def q(values, p):
        values = sorted(values)
        return values[max(0, int(p * len(values)) - 1)] if values else None
    return {"cells": cells, "differing_reviews": differing,
            "reviews_compared": sum(c.get("reviews", 0) for c in cells), "reviews_identical": sum(c.get("identical", 0) for c in cells),
            "runtime_before": {"reviews": len(walls_before), "p50": st.median(walls_before) if walls_before else None, "p95": q(walls_before, .95), "max": max(walls_before, default=None)},
            "runtime_after": {"reviews": len(walls_after), "p50": st.median(walls_after) if walls_after else None, "p95": q(walls_after, .95), "max": max(walls_after, default=None)}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--policy", default=None)
    ap.add_argument("--tol", type=float, default=1e-6)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    before = [json.loads(line) for line in Path(a.before).read_text().splitlines() if line.strip()]
    after = [json.loads(line) for line in Path(a.after).read_text().splitlines() if line.strip()]
    result = compare(before, after, a.policy, a.tol)
    if a.out:
        (OUT / f"{a.out}.json").write_text(json.dumps(result, indent=1, default=str))
    print(f"reviews compared {result['reviews_compared']} identical {result['reviews_identical']} differing {len(result['differing_reviews'])}")
    print(f"runtime before {result['runtime_before']}\nruntime after  {result['runtime_after']}")
    for d in result["differing_reviews"][:60]:
        print(f"  {d['cell']} r{d['review']} {d['key']}: {d['before']} -> {d['after']} (state {d['state_before']}->{d['state_after']}, wall {d['wall_before']:.0f}->{d['wall_after']:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
