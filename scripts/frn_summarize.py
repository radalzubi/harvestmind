"""Summarise a FreshRetailNet pilot stage: policy tables, paired series-level comparisons, strata, failures.

    python -m scripts.frn_summarize --stage five|fifty [--out docs/remodel/evidence/frn]

The unit of replication is the SERIES (store-product), never the store-product-day: days inside a window are dependent
and the three windows of one series share its demand regime, so every interval is a bootstrap over series of the
per-series difference (ZAAD minus baseline) within one (window, track, scenario). With 50 series the intervals are
wide by construction; the summary says so rather than pooling days. Nothing here is a realized saving: every number
is a modelled index under declared synthetic supply and economics.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics
from typing import Any

import numpy as np

RESULTS_ROOT = Path("data/public/freshretailnet/results")
BASELINES = ("reorder_point", "periodic:1", "base_stock", "order_up_to")
ZAAD = "gated"
#: primary cost: `continuation` credits residual stock at the purchase it avoids less carrying (floored at salvage, capped at
#: asset value) with one rule for every policy; `realized` credits it at salvage and is reported beside it as the bound that
#: penalises any policy holding stock when a short window ends (PR #114 used realized only: EXPERIMENT_DESIGN finding)
COST = "continuation"


def load_rows(stage: str) -> list[dict[str, Any]]:
    path = RESULTS_ROOT / stage / "runs.jsonl"                   # `stage` is the results directory name (e.g. fifty_corrected)
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _m(row: dict[str, Any], key: str, default=None):
    e = row.get("endpoint") or {}
    d = row.get("derived") or {}
    if key in e:
        return e[key]
    if key in d:
        return d[key]
    comps = e.get("components") or {}
    return comps.get(key, default)


def policy_table(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Mean and median per (window, track, scenario, policy) over completed series, plus failure counts."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        groups[(r["window"], r["track"], r["scenario"], r["policy"])].append(r)
    out: dict[str, Any] = {}
    for key in sorted(groups):
        g = groups[key]
        ok = [r for r in g if r.get("status") == "COMPLETE" and r.get("endpoint")]
        metric = {}
        for name, getter in (("continuation_cost", lambda r: _m(r, "continuation")), ("realized_cost", lambda r: _m(r, "realized")),
                             ("zaad_own_share", lambda r: (r.get("provenance") or {}).get("own_share")),
                             ("zaad_retained_reviews", lambda r: (r.get("provenance") or {}).get("RETAINED_INCUMBENT")),
                             ("zaad_own_reviews", lambda r: (r.get("provenance") or {}).get("OWN_CANDIDATE")),
                             ("purchase", lambda r: _m(r, "PURCHASE", 0.)), ("carrying", lambda r: _m(r, "CARRYING", 0.)),
                             ("shortage", lambda r: _m(r, "SHORTAGE", 0.)), ("inventory_value_change", lambda r: _m(r, "INVENTORY_VALUE_CHANGE", 0.)),
                             ("service_unit_fill", lambda r: _m(r, "service")), ("unmet_units", lambda r: _m(r, "unmet")),
                             ("breach_reviews", lambda r: _m(r, "breaches")), ("avg_inventory_units", lambda r: _m(r, "avg_inventory_units")),
                             ("end_stock_sd", lambda r: _m(r, "end_stock_sd")), ("stockout_reviews", lambda r: _m(r, "stockout_reviews")),
                             ("orders_placed", lambda r: _m(r, "orders_placed")), ("total_ordered", lambda r: _m(r, "total_ordered")),
                             ("mean_order_when_placed", lambda r: _m(r, "mean_order_when_placed")), ("expired_units", lambda r: _m(r, "expired_total")),
                             ("retained_incumbent_reviews", lambda r: _m(r, "retained_incumbent_reviews")),
                             ("service_infeasible_reviews", lambda r: _m(r, "service_infeasible_reviews")),
                             ("conservation_residual_max", lambda r: _m(r, "conservation_residual_max")),
                             ("wall_seconds", lambda r: r.get("wall_seconds")), ("cpu_seconds", lambda r: r.get("cpu_seconds"))):
            values = [getter(r) for r in ok]
            values = [float(v) for v in values if v is not None]
            metric[name] = {"mean": statistics.fmean(values), "median": statistics.median(values), "max": max(values), "n": len(values)} if values else None
        out["|".join(key)] = {"window": key[0], "track": key[1], "scenario": key[2], "policy": key[3], "runs": len(g), "complete": len(ok),
                              "failed": len(g) - len(ok), "statuses": dict(_count(r.get("status") for r in g)), **metric}
    return out


def _count(items):
    c: dict[Any, int] = defaultdict(int)
    for i in items:
        c[str(i)] += 1
    return c


def paired(rows: list[dict[str, Any]], *, reps: int = 4000, seed: int = 0) -> dict[str, Any]:
    """ZAAD minus baseline per series inside one (window, track, scenario): mean difference with a series bootstrap
    80 % and 95 % interval, median, win rate, and the exact sign-test p-value. Series missing either policy are excluded and counted."""
    rng = np.random.default_rng(seed)
    by_cell: dict[tuple, dict[tuple, dict[str, dict]]] = defaultdict(lambda: defaultdict(dict))
    for r in rows:
        if r.get("status") == "COMPLETE" and r.get("endpoint"):
            by_cell[(r["window"], r["track"], r["scenario"])][(r["store_id"], r["product_id"])][r["policy"]] = r
    out: dict[str, Any] = {}
    for cell in sorted(by_cell):
        series = by_cell[cell]
        for base in BASELINES:
            for metric, getter in (("continuation_cost", lambda r: _m(r, "continuation")), ("realized_cost", lambda r: _m(r, "realized")), ("shortage", lambda r: _m(r, "SHORTAGE", 0.)),
                                   ("avg_inventory_units", lambda r: _m(r, "avg_inventory_units")), ("service_unit_fill", lambda r: _m(r, "service")),
                                   ("unmet_units", lambda r: _m(r, "unmet"))):
                diffs = []
                for key, pol in series.items():
                    if ZAAD in pol and base in pol:
                        a, b = getter(pol[ZAAD]), getter(pol[base])
                        if a is not None and b is not None:
                            diffs.append(float(a) - float(b))
                if len(diffs) < 2:
                    continue
                d = np.asarray(diffs)
                boots = np.asarray([rng.choice(d, len(d), replace=True).mean() for _ in range(reps)])
                wins = int(np.sum(d < -1e-9)) if metric != "service_unit_fill" else int(np.sum(d > 1e-9))
                losses = int(np.sum(d > 1e-9)) if metric != "service_unit_fill" else int(np.sum(d < -1e-9))
                ties = len(d) - wins - losses
                out["|".join([*cell, base, metric])] = {
                    "window": cell[0], "track": cell[1], "scenario": cell[2], "baseline": base, "metric": metric, "series": len(d),
                    "mean_difference_zaad_minus_baseline": float(d.mean()), "median_difference": float(np.median(d)),
                    "bootstrap_80": [float(np.quantile(boots, .10)), float(np.quantile(boots, .90))],
                    "bootstrap_95": [float(np.quantile(boots, .025)), float(np.quantile(boots, .975))],
                    "zaad_better": wins, "zaad_worse": losses, "ties": ties, "sign_test_p": _sign_test(wins, losses),
                    "note": "difference of modelled indices per series under declared synthetic supply; series are the replication unit"}
    return out


def _sign_test(wins: int, losses: int) -> float | None:
    n = wins + losses
    if n == 0:
        return None
    from math import comb
    k = min(wins, losses)
    p = sum(comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return float(min(1., 2 * p))


def strata(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """ZAAD minus each baseline on realized cost by selection class, final window, per track and scenario."""
    out: dict[str, Any] = {}
    by = defaultdict(lambda: defaultdict(dict))
    for r in rows:
        if r.get("status") == "COMPLETE" and r.get("endpoint"):
            by[(r["window"], r["track"], r["scenario"])][(r["store_id"], r["product_id"])][r["policy"]] = r
    for cell, series in sorted(by.items()):
        for cls in ("volume_class", "stockout_class", "regularity_class", "promo_class"):
            for base in BASELINES:
                buckets: dict[str, list[float]] = defaultdict(list)
                for pol in series.values():
                    if ZAAD in pol and base in pol:
                        buckets[pol[ZAAD][cls]].append(float(_m(pol[ZAAD], COST)) - float(_m(pol[base], COST)))
                out["|".join([*cell, cls, base])] = {k: {"series": len(v), "mean_diff": float(np.mean(v)), "zaad_better": int(np.sum(np.asarray(v) < -1e-9))}
                                                     for k, v in sorted(buckets.items())}
    return out


def failures(rows: list[dict[str, Any]]) -> dict[str, Any]:
    bad = [r for r in rows if r.get("status") != "COMPLETE"]
    retained = [r for r in rows if r.get("policy") == ZAAD and r.get("derived") and r["derived"].get("retained_incumbent_reviews")]
    infeasible = [r for r in rows if r.get("derived") and r["derived"].get("service_infeasible_reviews")]
    slow = sorted((r for r in rows if r.get("wall_seconds") is not None), key=lambda r: -r["wall_seconds"])[:10]
    worst = []
    by = defaultdict(dict)
    for r in rows:
        if r.get("status") == "COMPLETE" and r.get("endpoint"):
            by[(r["window"], r["track"], r["scenario"], r["store_id"], r["product_id"])][r["policy"]] = r
    for key, pol in by.items():
        if ZAAD in pol:
            best_base = min((b for b in BASELINES if b in pol), key=lambda b: _m(pol[b], COST), default=None)
            if best_base is not None:
                gap = float(_m(pol[ZAAD], COST)) - float(_m(pol[best_base], COST))
                worst.append({"window": key[0], "track": key[1], "scenario": key[2], "store_id": key[3], "product_id": key[4], "best_baseline": best_base,
                              "zaad_minus_best_baseline": gap, "zaad_service": _m(pol[ZAAD], "service"), "baseline_service": _m(pol[best_base], "service"),
                              "zaad_inventory": _m(pol[ZAAD], "avg_inventory_units"), "baseline_inventory": _m(pol[best_base], "avg_inventory_units"),
                              "zaad_retained_incumbent_reviews": _m(pol[ZAAD], "retained_incumbent_reviews"), "zaad_states": (pol[ZAAD].get("derived") or {}).get("planner_states")})
    worst.sort(key=lambda w: -w["zaad_minus_best_baseline"])
    completion = defaultdict(lambda: {"runs": 0, "complete": 0, "INFEASIBLE": 0, "ABSTAIN": 0, "other": 0})
    for r in rows:
        c = completion[r["policy"]]
        c["runs"] += 1
        st = r.get("status")
        c["complete" if st == "COMPLETE" else st if st in ("INFEASIBLE", "ABSTAIN") else "other"] += 1
    return {"completion_by_policy": dict(completion),
            "non_complete_runs": [{**{k: r.get(k) for k in ("window", "track", "scenario", "policy", "store_id", "product_id", "status", "error")},
                                   "failure": (r.get("failure") or [None])[:3] if isinstance(r.get("failure"), list) else r.get("failure"),
                                   "reviews_completed_before_stop": (r.get("derived") or {}).get("reviews_completed", 0)} for r in bad],
            "zaad_retained_incumbent": {"runs": len(retained), "reviews": int(sum(r["derived"]["retained_incumbent_reviews"] for r in retained)),
                                        "of_zaad_runs": sum(1 for r in rows if r.get("policy") == ZAAD)},
            "service_infeasible_recovery_runs": [{k: r.get(k) for k in ("window", "track", "scenario", "policy", "store_id", "product_id")} | {"reviews": r["derived"]["service_infeasible_reviews"]} for r in infeasible][:50],
            "slowest_runs": [{k: r.get(k) for k in ("window", "track", "scenario", "policy", "store_id", "product_id", "wall_seconds")} for r in slow],
            "largest_zaad_losses": worst[:15], "largest_zaad_wins": sorted(worst, key=lambda w: w["zaad_minus_best_baseline"])[:15]}


def markdown(stage: str, table: dict[str, Any], pairs: dict[str, Any], fails: dict[str, Any], manifest: dict[str, Any]) -> str:
    lines = [f"# FreshRetailNet pilot results: stage `{stage}`", "",
             f"Commit `{manifest.get('commit')}`, declaration `{manifest.get('declaration', {}).get('hash', '')[:12]}`, selection `{manifest.get('selection_hash', '')[:12]}`; "
             f"{manifest.get('runs')} runs, {manifest.get('complete')} complete, {manifest.get('failed')} not complete; wall {manifest.get('wall_seconds', 0):.0f} s, "
             f"peak RSS {manifest.get('peak_rss_mb', 0):.0f} MB. Every figure is a modelled index under declared SYNTHETIC supply and normalized-unit economics; "
             "none is a realized saving.", "", "## Policy table (mean over completed series)", "",
             "| window | track | scenario | policy | n | continuation cost | realized cost | purchase | carrying | shortage | fill | unmet | avg inv | stockout rev | orders | ZAAD own share | wall s |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for key, g in table.items():
        def f(name, nd=3):
            m = g.get(name)
            return "" if not m else f"{m['mean']:.{nd}f}"
        lines.append(f"| {g['window']} | {g['track']} | {g['scenario']} | {g['policy']} | {g['complete']}/{g['runs']} | {f('continuation_cost')} | {f('realized_cost')} | {f('purchase')} | {f('carrying', 4)} | "
                     f"{f('shortage')} | {f('service_unit_fill')} | {f('unmet_units')} | {f('avg_inventory_units')} | {f('stockout_reviews', 1)} | {f('orders_placed', 1)} | "
                     f"{f('zaad_own_share', 2)} | {f('wall_seconds', 2)} |")
    lines += ["", "## Paired comparison, ZAAD minus baseline per series (continuation cost; negative favours ZAAD)", "",
              "| window | track | scenario | baseline | series | mean diff | 80 % bootstrap | 95 % bootstrap | ZAAD better / worse / ties | sign p |", "|---|---|---|---|---|---|---|---|---|---|"]
    for key, p in pairs.items():
        if p["metric"] != COST:
            continue
        lines.append(f"| {p['window']} | {p['track']} | {p['scenario']} | {p['baseline']} | {p['series']} | {p['mean_difference_zaad_minus_baseline']:+.3f} | "
                     f"[{p['bootstrap_80'][0]:+.3f}, {p['bootstrap_80'][1]:+.3f}] | [{p['bootstrap_95'][0]:+.3f}, {p['bootstrap_95'][1]:+.3f}] | "
                     f"{p['zaad_better']} / {p['zaad_worse']} / {p['ties']} | {p['sign_test_p'] if p['sign_test_p'] is None else round(p['sign_test_p'], 3)} |")
    lines += ["", "## Paired comparison on service and inventory (ZAAD minus baseline)", "",
              "| window | track | scenario | baseline | metric | series | mean diff | 95 % bootstrap | ZAAD better / worse |", "|---|---|---|---|---|---|---|---|---|"]
    for key, p in pairs.items():
        if p["metric"] in ("service_unit_fill", "avg_inventory_units", "shortage"):
            lines.append(f"| {p['window']} | {p['track']} | {p['scenario']} | {p['baseline']} | {p['metric']} | {p['series']} | {p['mean_difference_zaad_minus_baseline']:+.4f} | "
                         f"[{p['bootstrap_95'][0]:+.4f}, {p['bootstrap_95'][1]:+.4f}] | {p['zaad_better']} / {p['zaad_worse']} |")
    lines += ["", "## Failures, abstentions and the largest ZAAD losses", "",
              "Completion by policy (a run stops at the first review whose solve is INFEASIBLE or on which ZAAD abstains; the engine's replay never fabricates a plan): "
              + "; ".join(f"{p}: {c['complete']}/{c['runs']} complete, {c['INFEASIBLE']} infeasible, {c['ABSTAIN']} abstained" for p, c in sorted(fails["completion_by_policy"].items())), "",
              f"- Runs not COMPLETE: {len(fails['non_complete_runs'])}", f"- ZAAD runs that retained the incumbent proxy on at least one review: {fails['zaad_retained_incumbent']['runs']} of "
              f"{fails['zaad_retained_incumbent']['of_zaad_runs']} ({fails['zaad_retained_incumbent']['reviews']} reviews)",
              f"- Runs with a REQUESTED_SERVICE_INFEASIBLE recovery solve: {len(fails['service_infeasible_recovery_runs'])}", ""]
    for w in fails["largest_zaad_losses"][:10]:
        lines.append(f"- {w['window']}/{w['track']}/{w['scenario']} store {w['store_id']} product {w['product_id']}: ZAAD minus {w['best_baseline']} = {w['zaad_minus_best_baseline']:+.3f} "
                     f"(fill {w['zaad_service']:.3f} vs {w['baseline_service']:.3f}, inventory {w['zaad_inventory']:.2f} vs {w['baseline_inventory']:.2f}, retained incumbent on {w['zaad_retained_incumbent_reviews']} reviews)")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--out", default="docs/remodel/evidence/frn")
    args = ap.parse_args()
    rows = load_rows(args.stage)
    manifest = json.loads((RESULTS_ROOT / args.stage / "run_manifest.json").read_text())
    table, pairs, strat, fails = policy_table(rows), paired(rows), strata(rows), failures(rows)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"RESULTS_{args.stage}.json").write_text(json.dumps({"run_manifest": manifest, "policy_table": table, "paired": pairs, "strata": strat, "failures": fails},
                                                                indent=1, default=str) + "\n")
    (out / f"RESULTS_{args.stage}.md").write_text(markdown(args.stage, table, pairs, fails, manifest))
    print(f"wrote {out / f'RESULTS_{args.stage}.md'}: {len(rows)} rows, {sum(1 for r in rows if r.get('status') == 'COMPLETE')} complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
