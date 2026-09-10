"""The final P2 record: the authoritative run for the fixtures its evidence stands on, plus the
corrected re-run (`P2_PREREGISTRATION.md`, Correction 1) for the fixtures it invalidated, summarised
under the same rules (`scripts.p2_benchmark.summarize`) and written as p2_final.jsonl / .summary.json /
.tables.md with the runtime gate read over every ZAAD review of the combined set.

usage: PYTHONPATH=. python3 -m scripts.p2_final_table [--base p2_authoritative] [--corrected p2_authoritative_c1] [--replaced D,M,O,Q]"""
from __future__ import annotations

import argparse
import json
import statistics as st

from scripts.p2_benchmark import OUT, REVIEWS, summarize, tables


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="p2_authoritative")
    ap.add_argument("--corrected", default="p2_authoritative_c1")
    ap.add_argument("--replaced", default="D,M,O,Q")
    ap.add_argument("--p50", type=float, default=60.)
    ap.add_argument("--p95", type=float, default=120.)
    ap.add_argument("--max", type=float, default=180.)
    a = ap.parse_args()
    replaced = set(a.replaced.split(","))
    base = [json.loads(line) for line in (OUT / f"{a.base}.jsonl").read_text().splitlines()]
    corrected = [json.loads(line) for line in (OUT / f"{a.corrected}.jsonl").read_text().splitlines()]
    records = [r for r in base if r["fixture"].split("_")[0] not in replaced] + [r for r in corrected if r["fixture"].split("_")[0] in replaced]
    (OUT / "p2_final.jsonl").write_text("".join(json.dumps(r, allow_nan=True) + "\n" for r in records))
    summary = summarize(records, REVIEWS)
    zaad = [r for r in records if r["policy"] == "gated" and r.get("per_review")]
    walls = sorted(x["wall_seconds"] for r in zaad for x in r["per_review"])
    starved = []
    for r in zaad:
        for x in r["per_review"]:
            for c, status in (x["solve_quality"] or {}).items():
                if status == "NO_FEASIBLE_SOLUTION" and c in ("deterministic_network", "stochastic_network", "joint_recovery", "protected_network", "cvar_network") and x["state"] in ("NO_ACTION", "NORMAL_REPLENISHMENT", "CAPITAL_OPTIMIZATION", "NETWORK_ALLOCATION", "PROTECT", "RECOVER", "ESCALATE_UNKNOWN"):
                    starved.append((r["fixture"], r["seed"], x["review"], c, x["state"]))
    statuses: dict = {}
    for r in zaad:
        for k, v in r["compute"]["solve_statuses"].items():
            statuses[k] = statuses.get(k, 0) + v
    runtime = {"reviews": len(walls), "p50": st.median(walls), "p95": walls[max(0, int(.95 * len(walls)) - 1)], "max": max(walls),
               "gate": {"p50": a.p50, "p95": a.p95, "max": a.max},
               "pass": st.median(walls) <= a.p50 and walls[max(0, int(.95 * len(walls)) - 1)] <= a.p95 and max(walls) <= a.max and not starved,
               "no_feasible_on_candidates": starved, "solve_statuses": statuses,
               "slowest_reviews": [(r["fixture"], r["seed"], x["review"], round(x["wall_seconds"]), x["state"]) for r in zaad for x in r["per_review"] if x["wall_seconds"] > a.p95]}
    summary["runtime_gate"] = runtime
    summary["sources"] = {"base": a.base, "corrected": a.corrected, "replaced_fixtures": sorted(replaced)}
    (OUT / "p2_final.summary.json").write_text(json.dumps(summary, indent=1, allow_nan=True, default=str))
    text = tables(summary)
    text += ("\n## Runtime gate (ZAAD, every review of the final set)\n\n"
             f"| reviews | p50 s | p95 s | max s | gate p50 / p95 / max | required-candidate starvation | pass |\n|---|---|---|---|---|---|---|\n"
             f"| {runtime['reviews']} | {runtime['p50']:.1f} | {runtime['p95']:.1f} | {runtime['max']:.1f} | {a.p50:.0f} / {a.p95:.0f} / {a.max:.0f} | {len(starved)} | {'PASS' if runtime['pass'] else 'FAIL'} |\n\n"
             f"Solve statuses over every ZAAD candidate: {statuses}. Reviews above the p95 gate: {runtime['slowest_reviews']}.\n"
             f"Sources: {a.base} for the sixteen untouched fixtures, {a.corrected} for {sorted(replaced)}.\n")
    (OUT / "p2_final.tables.md").write_text(text)
    print(f"final: valid {summary['valid_fixtures']} passing {summary['passing_fixtures']} principles {summary['principles_passing']}/{summary['principles_total']} "
          f"runtime p50 {runtime['p50']:.1f} p95 {runtime['p95']:.1f} max {runtime['max']:.1f} starved {len(starved)} -> {'PASS' if runtime['pass'] else 'FAIL'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
