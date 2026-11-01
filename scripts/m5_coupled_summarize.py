"""Summarise an M5 Experiment B (coupled purchasing) results directory at group level.

    python -m scripts.m5_coupled_summarize --stage coupled_coupled [--out docs/remodel/evidence/m5]

The unit of replication is the store GROUP (at most ten per coupling), so every interval is a bootstrap over groups and is
wide by construction. A policy's constraint breach is a settlement PHYSICAL_FAILURE (the run stops at that review); a
projection that cancelled or cut an order-week to stay legal is counted from the review warnings (`projection:*`). Every
figure is a modelled dollar index under declared SYNTHETIC coupled supplier terms on OBSERVED sales; none is a realized saving.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics
from typing import Any

from scripts import frn_summarize as S

RESULTS_ROOT = Path("data/public/m5/results")
BASELINES = ("economic_lot", "reorder_point", "periodic:1")
ZAAD = "gated"
METRICS = (("continuation_cost", lambda r: S._m(r, "continuation")), ("realized_cost", lambda r: S._m(r, "realized")),
           ("purchase", lambda r: S._m(r, "PURCHASE", 0.)), ("ordering", lambda r: S._m(r, "ORDERING", 0.)), ("carrying", lambda r: S._m(r, "CARRYING", 0.)),
           ("shortage", lambda r: S._m(r, "SHORTAGE", 0.)), ("inventory_value_change", lambda r: S._m(r, "INVENTORY_VALUE_CHANGE", 0.)),
           ("service_unit_fill", lambda r: S._m(r, "service")), ("unmet_units", lambda r: S._m(r, "unmet")), ("avg_inventory_units", lambda r: S._m(r, "avg_inventory_units")),
           ("items_below_target", lambda r: S._m(r, "items_below_target")), ("min_item_fill", lambda r: S._m(r, "min_item_fill")),
           ("order_weeks", lambda r: S._m(r, "order_weeks")), ("lines_per_order_week", lambda r: S._m(r, "lines_per_order_week")),
           ("units_ordered", lambda r: S._m(r, "units_ordered")), ("end_stock_mean", lambda r: S._m(r, "end_stock_mean")),
           ("breach_reviews", lambda r: S._m(r, "breaches")), ("projection_cancelled_order_weeks", lambda r: projection_notes(r)["cancelled"]),
           ("projection_cut_order_weeks", lambda r: projection_notes(r)["cut"]),
           ("zaad_own_share", lambda r: (r.get("provenance") or {}).get("own_share")), ("zaad_retained_reviews", lambda r: (r.get("provenance") or {}).get("RETAINED_INCUMBENT")),
           ("wall_seconds", lambda r: r.get("wall_seconds")))


def load_rows(stage: str) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in (RESULTS_ROOT / stage / "runs.jsonl").read_text().splitlines() if line.strip()]
    for r in rows:                                   # the shared paired/failure helpers key series by (store_id, product_id) and a track
        r.setdefault("track", "group")
        r["product_id"] = "+".join(r.get("group") or [])
        r.setdefault("store_id", r["product_id"].rsplit("_", 1)[-1] if r["product_id"] else None)
        for cls in ("volume_class", "stockout_class", "regularity_class", "promo_class"):
            r.setdefault(cls, "group")
    return rows


def projection_notes(row: dict[str, Any]) -> dict[str, int]:
    """Order-weeks the rule projection cancelled (no legal lot) or cut to the load cap, from the recorded review warnings."""
    warnings = (row.get("derived") or {}).get("warnings") or []
    return {"cancelled": sum(1 for w in warnings if str(w).startswith("projection:cancelled")),
            "cut": sum(1 for w in warnings if str(w).startswith("projection:load_cap"))}


def group_table(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        groups[(r["window"], r["scenario"], r["policy"])].append(r)
    out: dict[str, Any] = {}
    for key in sorted(groups):
        g = groups[key]
        ok = [r for r in g if r.get("status") == "COMPLETE" and r.get("endpoint")]
        metric: dict[str, Any] = {}
        for name, getter in METRICS:
            values = [float(v) for v in (getter(r) for r in ok) if v is not None]
            metric[name] = {"mean": statistics.fmean(values), "median": statistics.median(values), "max": max(values), "n": len(values)} if values else None
        statuses = dict(S._count(r.get("status") for r in g))
        out["|".join(key)] = {"window": key[0], "scenario": key[1], "policy": key[2], "runs": len(g), "complete": len(ok), "failed": len(g) - len(ok), "statuses": statuses,
                              "physical_failures": statuses.get("PHYSICAL_FAILURE", 0), "abstained": statuses.get("ABSTAIN", 0),
                              "breach_reasons": dict(S._count(str(r.get("failure")) for r in g if r.get("status") == "PHYSICAL_FAILURE")), **metric}
    return out


def failures(rows: list[dict[str, Any]]) -> dict[str, Any]:
    bad = [r for r in rows if r.get("status") != "COMPLETE"]
    completion: dict[str, dict[str, int]] = defaultdict(lambda: {"runs": 0, "complete": 0, "PHYSICAL_FAILURE": 0, "ABSTAIN": 0, "INFEASIBLE": 0, "other": 0})
    for r in rows:
        c = completion[r["policy"]]
        c["runs"] += 1
        st = r.get("status")
        c["complete" if st == "COMPLETE" else st if st in ("PHYSICAL_FAILURE", "ABSTAIN", "INFEASIBLE") else "other"] += 1
    return {"completion_by_policy": dict(completion),
            "non_complete_runs": [{**{k: r.get(k) for k in ("window", "scenario", "policy", "store_id", "status", "error")}, "group": r.get("group"),
                                   "failure": (r.get("failure") or [None])[:4] if isinstance(r.get("failure"), list) else r.get("failure"),
                                   "reviews_completed_before_stop": (r.get("derived") or {}).get("reviews_completed", 0)} for r in bad]}


def markdown(stage: str, table: dict[str, Any], pairs: dict[str, Any], fails: dict[str, Any], manifest: dict[str, Any]) -> str:
    decl = manifest.get("declaration") or {}
    lines = [f"# Walmart M5 Experiment B (coupled purchasing) results: `{stage}`", "",
             f"Commit `{manifest.get('commit')}`, coupling `{manifest.get('coupling')}` (hash `{str(decl.get('hash', ''))[:12]}`), selection `{str(manifest.get('selection_hash', ''))[:12]}`; "
             f"{manifest.get('runs')} runs over {len(manifest.get('groups') or [])} store groups, {manifest.get('complete')} complete, {manifest.get('failed')} not complete; "
             f"wall {manifest.get('wall_seconds', 0):.0f} s. Every figure is a modelled dollar index under declared SYNTHETIC coupled supplier terms (fixed order cost, "
             "minimum order value, pallet cap, case lots) on OBSERVED Walmart sales; none is a realized saving. Groups are the replication unit (at most ten), so the "
             "intervals are wide by construction.", "", "## Group table (mean over completed groups)", "",
             "| window | scenario | policy | complete/runs | physical failures | abstained | continuation | realized | purchase | ordering | carrying | shortage | fill | items < target | min item fill | order-weeks | lines/order-week | end stock | cancelled OW | cut OW | ZAAD own share | wall s |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for g in table.values():
        def f(name, nd=2):
            m = g.get(name)
            return "" if not m else f"{m['mean']:.{nd}f}"
        lines.append(f"| {g['window']} | {g['scenario']} | {g['policy']} | {g['complete']}/{g['runs']} | {g['physical_failures']} | {g['abstained']} | {f('continuation_cost')} | {f('realized_cost')} | "
                     f"{f('purchase')} | {f('ordering')} | {f('carrying')} | {f('shortage')} | {f('service_unit_fill', 3)} | {f('items_below_target', 1)} | {f('min_item_fill', 3)} | "
                     f"{f('order_weeks', 1)} | {f('lines_per_order_week', 2)} | {f('end_stock_mean', 1)} | {f('projection_cancelled_order_weeks', 1)} | {f('projection_cut_order_weeks', 1)} | "
                     f"{f('zaad_own_share', 2)} | {f('wall_seconds', 1)} |")
    lines += ["", "## Paired comparison, ZAAD minus baseline per group (continuation cost; negative favours ZAAD; groups where both completed)", "",
              "| window | scenario | baseline | groups | mean diff | 80 % bootstrap | 95 % bootstrap | ZAAD better / worse / ties | sign p |", "|---|---|---|---|---|---|---|---|---|"]
    for p in pairs.values():
        if p["metric"] == "continuation_cost":
            lines.append(f"| {p['window']} | {p['scenario']} | {p['baseline']} | {p['series']} | {p['mean_difference_zaad_minus_baseline']:+.2f} | "
                         f"[{p['bootstrap_80'][0]:+.2f}, {p['bootstrap_80'][1]:+.2f}] | [{p['bootstrap_95'][0]:+.2f}, {p['bootstrap_95'][1]:+.2f}] | "
                         f"{p['zaad_better']} / {p['zaad_worse']} / {p['ties']} | {p['sign_test_p'] if p['sign_test_p'] is None else round(p['sign_test_p'], 3)} |")
    lines += ["", "## Paired comparison on fill and inventory (ZAAD minus baseline)", "", "| window | scenario | baseline | metric | groups | mean diff | 95 % bootstrap | ZAAD better / worse |", "|---|---|---|---|---|---|---|---|"]
    for p in pairs.values():
        if p["metric"] in ("service_unit_fill", "avg_inventory_units", "shortage"):
            lines.append(f"| {p['window']} | {p['scenario']} | {p['baseline']} | {p['metric']} | {p['series']} | {p['mean_difference_zaad_minus_baseline']:+.4f} | "
                         f"[{p['bootstrap_95'][0]:+.4f}, {p['bootstrap_95'][1]:+.4f}] | {p['zaad_better']} / {p['zaad_worse']} |")
    lines += ["", "## Completion and constraint breaches", "",
              "Completion by policy (a run stops at the first review whose order breaks a shared constraint in settlement, PHYSICAL_FAILURE, or on which ZAAD abstains): "
              + "; ".join(f"{p}: {c['complete']}/{c['runs']} complete, {c['PHYSICAL_FAILURE']} physical failures, {c['ABSTAIN']} abstained, {c['INFEASIBLE']} infeasible"
                          for p, c in sorted(fails["completion_by_policy"].items())), ""]
    for r in fails["non_complete_runs"][:40]:
        reason = r["failure"] if not isinstance(r["failure"], list) else "; ".join(str(x) for x in r["failure"][:3])
        lines.append(f"- {r['window']}/{r['scenario']} store {r['store_id']} {r['policy']}: {r['status']} after {r['reviews_completed_before_stop'] or 0} reviews: {str(reason)[:220]}")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--out", default="docs/remodel/evidence/m5")
    args = ap.parse_args()
    S.BASELINES = BASELINES
    rows = load_rows(args.stage)
    manifest_path = RESULTS_ROOT / args.stage / "run_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
    else:                                            # a run stopped before its manifest: summarise the rows it wrote and say so
        manifest = {"stage": "PARTIAL (no run_manifest.json: the run was stopped before completion)", "coupling": args.stage.replace("coupled_", "", 1),
                    "commit": None, "declaration": {}, "selection_hash": "", "groups": sorted({"+".join(r.get("group") or []) for r in rows}),
                    "runs": len(rows), "complete": sum(1 for r in rows if r.get("status") == "COMPLETE"), "failed": sum(1 for r in rows if r.get("status") != "COMPLETE"),
                    "wall_seconds": 0.0}
    table, pairs, fails = group_table(rows), S.paired(rows), failures(rows)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"RESULTS_{args.stage}.json").write_text(json.dumps({"run_manifest": manifest, "group_table": table, "paired": pairs, "failures": fails}, indent=1, default=str) + "\n")
    (out / f"RESULTS_{args.stage}.md").write_text(markdown(args.stage, table, pairs, fails, manifest))
    print(f"wrote {out / f'RESULTS_{args.stage}.md'}: {len(rows)} rows, {sum(1 for r in rows if r.get('status') == 'COMPLETE')} complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
