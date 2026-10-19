"""Before/after comparison of FreshRetailNet pilot stages that share the 50 series, the windows and the supply draws.

    python -m scripts.frn_compare --stages fifty:original,fifty_reference_v1:reference_v1,fifty_corrected:corrected,... \
        [--chain fifty,fifty_reference_v1,fifty_corrected] [--out docs/remodel/evidence/frn]

Two readings per (window, track, scenario): the within-stage paired ZAAD-minus-reorder_point difference (what each
configuration claims), and the cross-stage paired difference of ZAAD's own continuation cost between consecutive stages of
`--chain` on the series both stages completed (what each change did to ZAAD itself). Supply draws are seeded by series,
window and scenario, so a series' truth is identical across stages and the cross-stage pairing is exact. Every number is a
modelled index under declared SYNTHETIC supply; nothing is a realized saving.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics
from typing import Any

import numpy as np

from scripts import frn_summarize as S

BASE = "reorder_point"


def stage_rows(stage: str) -> list[dict[str, Any]]:
    return S.load_rows(stage)


def cell_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Per (window, track, scenario): ZAAD and reorder_point completion and means, plus the within-stage paired difference."""
    by: dict[tuple, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by[(r["window"], r["track"], r["scenario"])][r["policy"]].append(r)
    pairs = S.paired(rows)
    out: dict[str, Any] = {}
    for cell in sorted(by):
        pol = by[cell]

        def mean_of(policy: str, key: str) -> float | None:
            vals = [float(S._m(r, key)) for r in pol.get(policy, []) if r.get("status") == "COMPLETE" and r.get("endpoint") and S._m(r, key) is not None]
            return statistics.fmean(vals) if vals else None
        zaad = pol.get(S.ZAAD, [])
        own = [float((r.get("provenance") or {}).get("own_share")) for r in zaad if (r.get("provenance") or {}).get("own_share") is not None]
        p = pairs.get("|".join([*cell, BASE, "continuation_cost"]))
        out["|".join(cell)] = {"window": cell[0], "track": cell[1], "scenario": cell[2],
                               "zaad_complete": sum(1 for r in zaad if r.get("status") == "COMPLETE"), "zaad_runs": len(zaad),
                               "zaad_statuses": dict(S._count(r.get("status") for r in zaad)),
                               "zaad_continuation": mean_of(S.ZAAD, "continuation"), "zaad_realized": mean_of(S.ZAAD, "realized"), "zaad_fill": mean_of(S.ZAAD, "service"),
                               "zaad_avg_inventory": mean_of(S.ZAAD, "avg_inventory_units"), "zaad_own_share": statistics.fmean(own) if own else None,
                               "baseline_complete": sum(1 for r in pol.get(BASE, []) if r.get("status") == "COMPLETE"),
                               "baseline_continuation": mean_of(BASE, "continuation"), "baseline_fill": mean_of(BASE, "service"), "baseline_avg_inventory": mean_of(BASE, "avg_inventory_units"),
                               "paired": None if p is None else {k: p[k] for k in ("series", "mean_difference_zaad_minus_baseline", "bootstrap_95", "zaad_better", "zaad_worse", "ties", "sign_test_p")}}
    return out


def cross_stage(a_rows: list[dict[str, Any]], b_rows: list[dict[str, Any]], *, reps: int = 4000, seed: int = 0) -> dict[str, Any]:
    """ZAAD(b) minus ZAAD(a) continuation cost per series on the series both stages completed, per cell."""
    rng = np.random.default_rng(seed)

    def index(rows):
        out: dict[tuple, dict[tuple, dict]] = defaultdict(dict)
        for r in rows:
            if r.get("policy") == S.ZAAD and r.get("status") == "COMPLETE" and r.get("endpoint"):
                out[(r["window"], r["track"], r["scenario"])][(r["store_id"], r["product_id"])] = r
        return out
    a, b = index(a_rows), index(b_rows)
    out: dict[str, Any] = {}
    for cell in sorted(set(a) | set(b)):
        common = sorted(set(a.get(cell, {})) & set(b.get(cell, {})))
        diffs = np.asarray([float(S._m(b[cell][k], "continuation")) - float(S._m(a[cell][k], "continuation")) for k in common])
        fill = np.asarray([float(S._m(b[cell][k], "service")) - float(S._m(a[cell][k], "service")) for k in common])
        entry: dict[str, Any] = {"window": cell[0], "track": cell[1], "scenario": cell[2], "series_in_both": len(common),
                                 "only_in_a": len(set(a.get(cell, {})) - set(common)), "only_in_b": len(set(b.get(cell, {})) - set(common))}
        if len(diffs) >= 2:
            boots = np.asarray([rng.choice(diffs, len(diffs), replace=True).mean() for _ in range(reps)])
            entry.update(mean_difference_b_minus_a=float(diffs.mean()), bootstrap_95=[float(np.quantile(boots, .025)), float(np.quantile(boots, .975))],
                         b_better=int(np.sum(diffs < -1e-9)), b_worse=int(np.sum(diffs > 1e-9)), fill_mean_difference_b_minus_a=float(fill.mean()))
        out["|".join(cell)] = entry
    return out


def markdown(stages: list[tuple[str, str]], summaries: dict[str, dict[str, Any]], chain: list[tuple[str, str, dict[str, Any]]]) -> str:
    lines = ["# FreshRetailNet: before/after comparison across pilot stages", "",
             "Same 50 series, windows and supply draws in every stage. `original` is PR #114's frozen run (uncapped history, 1e6 line caps, no incumbent "
             "rule, summarised then on realized cost); the later stages are the corrected benchmark and its predeclared variants. Every figure is a "
             "modelled index under declared SYNTHETIC supply; nothing is a realized saving.", "",
             "## Within-stage: ZAAD vs reorder_point per cell", "",
             "| stage | window | track | scenario | ZAAD complete | ZAAD cont. | ZAAD fill | ZAAD inv | ZAAD own share | RP complete | RP cont. | RP fill | paired mean diff | 95 % bootstrap | better / worse |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]

    def f(v, nd=3):
        return "" if v is None else f"{v:.{nd}f}"
    for stage, label in stages:
        for c in summaries[stage].values():
            p = c["paired"]
            lines.append(f"| {label} | {c['window']} | {c['track']} | {c['scenario']} | {c['zaad_complete']}/{c['zaad_runs']} | {f(c['zaad_continuation'])} | {f(c['zaad_fill'])} | "
                         f"{f(c['zaad_avg_inventory'], 2)} | {f(c['zaad_own_share'], 2)} | {c['baseline_complete']} | {f(c['baseline_continuation'])} | {f(c['baseline_fill'])} | "
                         + ("" if p is None else f"{p['mean_difference_zaad_minus_baseline']:+.3f} ({p['series']}) | [{p['bootstrap_95'][0]:+.3f}, {p['bootstrap_95'][1]:+.3f}] | {p['zaad_better']} / {p['zaad_worse']} |"))
    lines += ["", "## Cross-stage: what each change did to ZAAD's own continuation cost (later minus earlier, series completed in both)", "",
              "| from | to | window | track | scenario | series in both | only earlier | only later | mean diff | 95 % bootstrap | later better / worse | fill diff |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for a, b, cells in chain:
        for c in cells.values():
            if "mean_difference_b_minus_a" in c:
                lines.append(f"| {a} | {b} | {c['window']} | {c['track']} | {c['scenario']} | {c['series_in_both']} | {c['only_in_a']} | {c['only_in_b']} | {c['mean_difference_b_minus_a']:+.3f} | "
                             f"[{c['bootstrap_95'][0]:+.3f}, {c['bootstrap_95'][1]:+.3f}] | {c['b_better']} / {c['b_worse']} | {c['fill_mean_difference_b_minus_a']:+.4f} |")
            else:
                lines.append(f"| {a} | {b} | {c['window']} | {c['track']} | {c['scenario']} | {c['series_in_both']} | {c['only_in_a']} | {c['only_in_b']} | | | | |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", required=True, help="comma-separated stage[:label] in display order")
    ap.add_argument("--chain", default="", help="comma-separated stages whose consecutive pairs get the cross-stage ZAAD comparison")
    ap.add_argument("--out", default="docs/remodel/evidence/frn")
    args = ap.parse_args()
    stages = [(s.split(":")[0], s.split(":")[1] if ":" in s else s) for s in args.stages.split(",") if s]
    rows = {stage: stage_rows(stage) for stage, _ in stages}
    labels = dict(stages)
    summaries = {stage: cell_summary(rows[stage]) for stage, _ in stages}
    chain_stages = [s for s in args.chain.split(",") if s]
    chain = [(labels.get(a, a), labels.get(b, b), cross_stage(rows[a], rows[b])) for a, b in zip(chain_stages, chain_stages[1:])]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "FRN_COMPARISON.json").write_text(json.dumps({"stages": stages, "within_stage": summaries, "cross_stage": [{"from": a, "to": b, "cells": c} for a, b, c in chain]}, indent=1, default=str) + "\n")
    (out / "FRN_COMPARISON.md").write_text(markdown(stages, summaries, chain))
    print(f"wrote {out / 'FRN_COMPARISON.md'}: {len(stages)} stages, {len(chain)} cross-stage pairs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
