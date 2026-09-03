"""FMCG digital-twin counterfactuals and the commercial stress matrix.

Builds operating histories from the calibrated simulator for each archetype
and seed, walks rolling origins through each, and settles every policy on
identical realised paths. Reports the full distribution of the stochastic
optimizer's edge over each baseline, never a cherry-picked seed.

Outputs (both machine- and human-readable):
  artifacts/fmcg_counterfactuals.json
  docs/validation/evidence/fmcg_counterfactuals.md
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backtesting.counterfactual import (  # noqa: E402
    POLICIES, FoldInputs, FoldTruth, rolling_evaluate, run_policies, summarize,
)
from domain.economics import CostConfig  # noqa: E402
from domain.model import fmcg_policy  # noqa: E402
from synthetic.fmcg.distributor_sim import ARCHETYPES, ArchetypeSpec, build_history  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def fold_from_history(h, origin: int, horizon: int, train: int, cover_weeks: float,
                      sla_target: float | None) -> tuple[FoldInputs, FoldTruth]:
    skus = h.skus[h.skus["abc"].isin(["A", "B"])]
    products = list(skus["sku"])
    sup_of = dict(zip(skus["sku"], skus["supplier_id"]))
    cost = dict(zip(skus["sku"], skus["unit_cost"]))
    margin = {r.sku: r.unit_price - r.unit_cost for r in skus.itertuples()}
    lead_of = {r.supplier_id: max(1, int(round(r.lead_mean_weeks))) for r in h.suppliers.itertuples()}

    ol = h.order_lines.copy()
    ol["week"] = ol["order_id"].str[4:8].astype(int)
    dem = ol.groupby(["sku", "week"])["qty_ordered"].sum()
    train_dem = {j: [float(dem.get((j, w), 0.0)) for w in range(origin - train, origin)] for j in products}

    po = h.purchase_orders.copy()
    po["week"] = (pd.to_datetime(po["po_date"]) - pd.to_datetime(h.purchase_orders["po_date"].min())).dt.days // 7
    rec = h.receipts.groupby("po_id")["qty_received"].sum()
    po = po.join(rec, on="po_id").fillna({"qty_received": 0.0})
    po["fill"] = (po["qty_received"] / po["qty_ordered"]).clip(0, 1)
    tr_po = po[(po["week"] >= origin - train) & (po["week"] < origin)]
    train_fill = {s: list(tr_po[tr_po["supplier_id"] == s]["fill"]) or [0.95] for s in set(sup_of.values())}

    # realised fills by (supplier, t) from POs placed in the evaluation window
    ev_po = po[(po["week"] >= origin) & (po["week"] < origin + horizon)]
    truth_fill, truth_lead = {}, {}
    for s in set(sup_of.values()):
        sub = ev_po[ev_po["supplier_id"] == s]
        for t in range(horizon):
            w = origin + t
            row = sub[sub["week"] == w]
            truth_fill[(s, t)] = float(row["fill"].mean()) if len(row) else float(np.mean(train_fill[s]))
            truth_lead[(s, t)] = lead_of[s]
    truth_dem = {(j, t): float(dem.get((j, origin + t), 0.0)) for j in products for t in range(horizon)}

    mean_dem = {j: st.mean(train_dem[j]) if train_dem[j] else 0.0 for j in products}
    opening = {j: mean_dem[j] * cover_weeks for j in products}
    pipeline = {}
    for j in products:
        for t in range(lead_of[sup_of[j]]):
            pipeline[(j, t)] = mean_dem[j]
    cap = {j: max(mean_dem[j] * 3.0, 1.0) for j in products}

    cc = CostConfig(currency="USD", holding_rate_per_period=0.02 / 4.33,
                    shortage_cost_per_unit=margin, waste_cost_per_unit=cost,
                    emergency_cost_multiplier=1.0, emergency_capacity_factor=0.0,
                    sla_penalty_rate=0.03 if sla_target else 0.0, sla_fill_target=sla_target)
    policy = fmcg_policy(h.pack_specs, cost_config=cc, service_level=0.97)
    fi = FoldInputs(origin=origin, horizon=horizon, products=products, supplier_of=sup_of,
                    lead_of=lead_of, train_demand=train_dem, train_fill=train_fill,
                    unit_cost=cost, margin=margin, capacity=cap, opening=opening,
                    pipeline=pipeline, policy=policy)
    return fi, FoldTruth(demand=truth_dem, fill=truth_fill, lead=truth_lead)


def run_rolling(a) -> int:
    names = list(ARCHETYPES) if a.archetypes == "all" else a.archetypes.split(",")
    results = {}
    t_all = time.time()
    pols = ("naive_forecast", "seasonal_naive", "static_safety", "min_max", "order_up_to",
            "deterministic_sp", "stochastic_sp", "selected")
    for name in names:
        spec = ARCHETYPES[name]
        if a.small:
            spec = ArchetypeSpec(**{**spec.__dict__, "n_skus": 20, "n_suppliers": 4,
                                    "n_customers": 8, "weeks": 130})
        per = {pol: [] for pol in pols}
        edges = {pol: [] for pol in pols if pol != "stochastic_sp"}
        sel_counts: dict = {}
        fails = 0
        for seed in range(a.seeds):
            h = build_history(name, seed=seed, spec=spec)
            start = a.train + 2
            n_run = min(a.run_periods, spec.weeks - start - 1)
            fi0, _ = fold_from_history(h, start, a.horizon, a.train, a.cover_weeks, a.sla_target)
            products, sup_of, lead_of = fi0.products, fi0.supplier_of, fi0.lead_of
            # realised path over the whole run
            ol = h.order_lines.copy()
            ol["week"] = ol["order_id"].str[4:8].astype(int)
            dem = ol.groupby(["sku", "week"])["qty_ordered"].sum()
            truth_d = {(j, t): float(dem.get((j, start + t), 0.0)) for j in products for t in range(n_run + a.horizon)}
            truth_f, truth_l = {}, {}
            for t in range(n_run + a.horizon):
                fi_t, tr = fold_from_history(h, start + t, 1, a.train, a.cover_weeks, a.sla_target) if False else (None, None)
            # per-supplier realised fills by absolute week from the PO log
            po = h.purchase_orders.copy()
            po["week"] = (pd.to_datetime(po["po_date"]) - pd.to_datetime(h.purchase_orders["po_date"].min())).dt.days // 7
            rec = h.receipts.groupby("po_id")["qty_received"].sum()
            po = po.join(rec, on="po_id").fillna({"qty_received": 0.0})
            po["fill"] = (po["qty_received"] / po["qty_ordered"]).clip(0, 1)
            for s_ in set(sup_of.values()):
                sub = po[po["supplier_id"] == s_]
                base = float(sub[sub["week"] < start]["fill"].mean()) if len(sub[sub["week"] < start]) else 0.95
                for t in range(n_run + a.horizon):
                    row = sub[sub["week"] == start + t]
                    truth_f[(s_, t)] = float(row["fill"].mean()) if len(row) else base
                    truth_l[(s_, t)] = lead_of[s_]
            cap_total = sum(st.mean(fi0.train_demand[j]) for j in products) * a.warehouse_cap_weeks

            def make_inputs(t, on_hand, pipeline, _h=h, _start=start):
                fi, _ = fold_from_history(_h, _start + t, a.horizon, a.train, a.cover_weeks, a.sla_target)
                fi.opening = dict(on_hand)
                fi.pipeline = dict(pipeline)
                return fi

            rng = np.random.default_rng(500 + seed)
            res = {}
            for pol in pols:
                res[pol] = rolling_evaluate(pol, make_inputs, truth_d, truth_f, truth_l, products,
                                            sup_of, lead_of, fi0.unit_cost, fi0.margin, fi0.policy,
                                            n_run, a.review, a.horizon, cap_total, rng,
                                            dict(fi0.opening), n_scen=a.scenarios)
                per[pol].append(res[pol])
                fails += res[pol].solver_failures
                for k, v in res[pol].selections.items():
                    sel_counts[k] = sel_counts.get(k, 0) + v
            sp = res["stochastic_sp"].total
            for pol in edges:
                if res[pol].total > 0:
                    edges[pol].append((res[pol].total - sp) / res[pol].total * 100)
        results[name] = {
            "runs": a.seeds, "periods": a.run_periods, "review": a.review,
            "edge_vs": {pol: summarize(v) for pol, v in edges.items()},
            "selected_edge_vs_deterministic": summarize([
                (d.total - s_.total) / d.total * 100
                for d, s_ in zip(per["deterministic_sp"], per["selected"]) if d.total > 0]),
            "mean_cost": {pol: st.mean(r.total for r in v) for pol, v in per.items()},
            "service": {pol: st.mean(r.fill_rate for r in v) for pol, v in per.items()},
            "avg_inventory": {pol: st.mean(r.avg_inventory for r in v) for pol, v in per.items()},
            "solver_failures": fails, "selections": sel_counts,
        }
        e = results[name]["edge_vs"]; sv = results[name]["service"]
        print(f"{name:<24} runs={a.seeds}  SP vs det {e['deterministic_sp'].get('median', float('nan')):+6.2f}% "
              f"(win {e['deterministic_sp'].get('win_rate', 0):.0%})  vs OUT {e['order_up_to'].get('median', float('nan')):+6.2f}%  "
              f"SELECTED vs det {results[name]['selected_edge_vs_deterministic'].get('median', float('nan')):+6.2f}%  "
              f"service sp {sv['stochastic_sp']:.1%} det {sv['deterministic_sp']:.1%} out {sv['order_up_to']:.1%}  "
              f"selections {sel_counts}", flush=True)
    out = {"classification": "SYNTHETIC CALIBRATED", "mode": "closed_loop_rolling", "config": vars(a),
           "elapsed_s": round(time.time() - t_all, 1), "archetypes": results}
    (ROOT / "artifacts").mkdir(exist_ok=True)
    (ROOT / "artifacts" / "fmcg_counterfactuals_rolling.json").write_text(json.dumps(out, indent=1))
    md = ROOT / "docs" / "validation" / "evidence"; md.mkdir(parents=True, exist_ok=True)
    lines = ["# FMCG closed-loop counterfactuals (SYNTHETIC CALIBRATED)", "",
             f"runs (seeds) {a.seeds}, run length {a.run_periods} periods, re-plan every {a.review}, "
             f"horizon {a.horizon}, train {a.train}, scenarios {a.scenarios}, opening cover {a.cover_weeks:.1f} wk, "
             f"warehouse cap {a.warehouse_cap_weeks} wk, SLA {a.sla_target}", "",
             "| archetype | SP vs deterministic | win | SP vs order-up-to | SP vs min/max | SP vs naive | SELECTED vs deterministic | service SP / det / OUT | avg inv SP / det / OUT | selections |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for name, r in results.items():
        e = r["edge_vs"]; sv = r["service"]; ai = r["avg_inventory"]; se = r["selected_edge_vs_deterministic"]
        lines.append(f"| {name} | {e['deterministic_sp'].get('median', 0):+.2f}% | {e['deterministic_sp'].get('win_rate', 0):.0%} | "
                     f"{e['order_up_to'].get('median', 0):+.2f}% | {e['min_max'].get('median', 0):+.2f}% | {e['naive_forecast'].get('median', 0):+.2f}% | "
                     f"{se.get('median', 0):+.2f}% (win {se.get('win_rate', 0):.0%}) | "
                     f"{sv['stochastic_sp']:.1%} / {sv['deterministic_sp']:.1%} / {sv['order_up_to']:.1%} | "
                     f"{ai['stochastic_sp']:,.0f} / {ai['deterministic_sp']:,.0f} / {ai['order_up_to']:,.0f} | {r['selections']} |")
    (md / "fmcg_counterfactuals_rolling.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote artifacts/fmcg_counterfactuals_rolling.json ({out['elapsed_s']}s)")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archetypes", default="all")
    p.add_argument("--seeds", type=int, default=5)
    p.add_argument("--folds-per-seed", type=int, default=6)
    p.add_argument("--horizon", type=int, default=12)
    p.add_argument("--train", type=int, default=52)
    p.add_argument("--scenarios", type=int, default=25)
    p.add_argument("--cover-weeks", type=float, default=38 / 7)
    p.add_argument("--warehouse-cap-weeks", type=float, default=8.0)
    p.add_argument("--sla-target", type=float, default=0.95)
    p.add_argument("--small", action="store_true", help="smaller histories for speed")
    p.add_argument("--rolling", action="store_true",
                   help="closed-loop: re-plan every --review periods over --run-periods, "
                        "each policy carrying its own state; removes the horizon end effect")
    p.add_argument("--review", type=int, default=4)
    p.add_argument("--run-periods", type=int, default=48)
    a = p.parse_args()
    if a.rolling:
        return run_rolling(a)
    names = list(ARCHETYPES) if a.archetypes == "all" else a.archetypes.split(",")
    results = {}
    t_all = time.time()
    for name in names:
        spec = ARCHETYPES[name]
        if a.small:
            spec = ArchetypeSpec(**{**spec.__dict__, "n_skus": 20, "n_suppliers": 4,
                                    "n_customers": 8, "weeks": 130})
        per_pol = {pol: {"total": [], "fill": [], "hold": [], "short": []} for pol in POLICIES}
        edges = {pol: [] for pol in POLICIES if pol != "stochastic_sp"}
        strata = {"binding": [], "slack": []}
        statuses = {pol: {} for pol in POLICIES}
        runtimes = []
        n_folds = 0
        for seed in range(a.seeds):
            h = build_history(name, seed=seed, spec=spec)
            n_weeks = spec.weeks
            origins = np.linspace(a.train + 2, n_weeks - a.horizon - 1, a.folds_per_seed).astype(int)
            rng = np.random.default_rng(1000 + seed)
            for oi in origins:
                fi, truth = fold_from_history(h, int(oi), a.horizon, a.train, a.cover_weeks, a.sla_target)
                cap_total = sum(st.mean(fi.train_demand[j]) for j in fi.products) * a.warehouse_cap_weeks
                res = run_policies(fi, truth, cap_total, rng, n_scen=a.scenarios)
                sp = res["stochastic_sp"]["settlement"]
                if sp is None:
                    statuses["stochastic_sp"][res["stochastic_sp"]["status"]] = \
                        statuses["stochastic_sp"].get(res["stochastic_sp"]["status"], 0) + 1
                    continue
                n_folds += 1
                runtimes.append(res["stochastic_sp"]["runtime_s"])
                for pol, r in res.items():
                    statuses[pol][r["status"]] = statuses[pol].get(r["status"], 0) + 1
                    s = r["settlement"]
                    if s is None:
                        continue
                    per_pol[pol]["total"].append(s.total); per_pol[pol]["fill"].append(s.fill_rate)
                    per_pol[pol]["hold"].append(s.holding); per_pol[pol]["short"].append(s.shortage)
                    if pol != "stochastic_sp" and s.total > 0:
                        edges[pol].append((s.total - sp.total) / s.total * 100)
                det = res["deterministic_sp"]["settlement"]
                if det and det.total > 0:
                    e = (det.total - sp.total) / det.total * 100
                    strata["binding" if det.shortage / det.total > 0.2 else "slack"].append(e)
        results[name] = {
            "folds": n_folds, "seeds": a.seeds,
            "edge_vs": {pol: summarize(v) for pol, v in edges.items()},
            "strata_vs_deterministic": {k: summarize(v) for k, v in strata.items()},
            "service": {pol: (st.mean(v["fill"]) if v["fill"] else None) for pol, v in per_pol.items()},
            "mean_cost": {pol: (st.mean(v["total"]) if v["total"] else None) for pol, v in per_pol.items()},
            "solver_status": statuses,
            "sp_runtime_s": {"p50": float(np.median(runtimes)) if runtimes else None,
                             "p95": float(np.percentile(runtimes, 95)) if runtimes else None},
        }
        e = results[name]["edge_vs"]
        print(f"{name:<24} folds={n_folds:3}  vs det {e['deterministic_sp'].get('median', float('nan')):+6.2f}% "
              f"(win {e['deterministic_sp'].get('win_rate', 0):.0%})  vs order_up_to "
              f"{e['order_up_to'].get('median', float('nan')):+6.2f}%  vs naive "
              f"{e['naive_forecast'].get('median', float('nan')):+6.2f}%  service sp "
              f"{results[name]['service']['stochastic_sp'] or 0:.1%}", flush=True)
    out = {"classification": "SYNTHETIC CALIBRATED", "config": vars(a),
           "elapsed_s": round(time.time() - t_all, 1), "archetypes": results}
    (ROOT / "artifacts").mkdir(exist_ok=True)
    (ROOT / "artifacts" / "fmcg_counterfactuals.json").write_text(json.dumps(out, indent=1))
    md = ROOT / "docs" / "validation" / "evidence"; md.mkdir(parents=True, exist_ok=True)
    lines = ["# FMCG counterfactuals (SYNTHETIC CALIBRATED)", "",
             f"seeds {a.seeds}, folds/seed {a.folds_per_seed}, horizon {a.horizon}, "
             f"train {a.train}, scenarios {a.scenarios}, opening cover {a.cover_weeks:.1f} wk, "
             f"warehouse cap {a.warehouse_cap_weeks} wk, SLA {a.sla_target}", "",
             "| archetype | folds | vs deterministic | win | CI95 median | vs order-up-to | vs naive | vs min/max | binding | slack | service SP / det / OUT |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, r in results.items():
        e = r["edge_vs"]; sdet = e["deterministic_sp"]; sv = r["service"]
        b = r["strata_vs_deterministic"]
        lines.append(
            f"| {name} | {r['folds']} | {sdet.get('median', 0):+.2f}% | {sdet.get('win_rate', 0):.0%} | "
            f"[{sdet.get('ci95_median', [0, 0])[0]:+.2f}, {sdet.get('ci95_median', [0, 0])[1]:+.2f}] | "
            f"{e['order_up_to'].get('median', 0):+.2f}% | {e['naive_forecast'].get('median', 0):+.2f}% | "
            f"{e['min_max'].get('median', 0):+.2f}% | "
            f"{b['binding'].get('median', float('nan')):+.2f}% (n={b['binding'].get('n', 0)}) | "
            f"{b['slack'].get('median', float('nan')):+.2f}% (n={b['slack'].get('n', 0)}) | "
            f"{(sv['stochastic_sp'] or 0):.1%} / {(sv['deterministic_sp'] or 0):.1%} / {(sv['order_up_to'] or 0):.1%} |")
    (md / "fmcg_counterfactuals.md").write_text("\n".join(lines) + "\n")
    print(f"\nwrote artifacts/fmcg_counterfactuals.json and {md / 'fmcg_counterfactuals.md'}  ({out['elapsed_s']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
