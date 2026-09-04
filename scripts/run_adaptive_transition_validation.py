"""Transition validation for the adaptive decision engine.

Does the engine detect a regime change with a short lag, respond
proportionately, avoid thrashing on a false alarm, distinguish a
demand-only shock from a supply problem, unwind after recovery, and leave
an easy/slack operation alone? Six transition tests (A-F) plus the easy
case, every policy closed-loop on identical realised paths through one
settlement, evaluation seeds unseen during development. FROZEN: nothing
below was tuned against the evaluation seeds; negative results stay.

  A progressive_disruption   fill 1.0 -> 0.6 over 8 weeks, trough, recovery
  B sudden_shock             fill 0.5 for 6 weeks with no warning
  C false_alarm              one bad week, then normal
  D demand_only_shock        demand x1.6 for 6 weeks, supply untouched
  E recovery                 disruption ends 2 weeks before the run starts
  F asymmetric_suppliers     one of the suppliers disrupted, the rest normal
  easy_slack                 A_stable, deep cover, nothing happens

Output: artifacts/adaptive_transition_validation.json,
        docs/validation/evidence/adaptive_transition_validation.md
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adaptive.engine import estimate, in_recovery_by_route, p_disruptive_by_route  # noqa: E402
from adaptive.state_estimator import TrackerBank  # noqa: E402
from backtesting.counterfactual import (  # noqa: E402
    EXTRA_CANDIDATES, policy_anchored_sp, policy_stochastic_sp, summarize,
)
from backtesting.safe_selector import SafeSelectionConfig, safe_select  # noqa: E402
from scripts.run_fmcg_counterfactuals import fold_from_history  # noqa: E402
from synthetic.fmcg.distributor_sim import ARCHETYPES, build_history  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TRAIN, HORIZON, REVIEW, RUN = 52, 12, 2, 32
START = TRAIN + 8                       # run begins at absolute week 60
FROZEN: dict[str, Any] = {
    "safe": dict(n_folds=4, n_holdout_folds=2, holdout=4, min_history=26, min_rel_improvement=0.03,
                 service_tolerance=0.01, max_regret_share=0.10, confidence=0.80, block_length=2, n_boot=300),
    "scenarios": 20, "review": REVIEW, "horizon": HORIZON, "train": TRAIN, "run_periods": RUN, "start": START,
    "eval_seeds": [100, 101, 102],
    "tests": {
        "A_progressive_disruption": dict(base="C_constrained_supplier", cover=2.0, share=0.5,
                                         profile=[(62, 1.0, 1.0), (66, 0.8, 1.3), (70, 0.6, 2.0), (76, 0.6, 2.0),
                                                  (80, 0.85, 1.3), (84, 1.0, 1.0)], onset=62),
        "B_sudden_shock": dict(base="C_constrained_supplier", cover=2.0, share=0.5,
                               profile=[(66, 1.0, 1.0), (67, 0.5, 2.5), (72, 0.5, 2.5), (73, 1.0, 1.0)], onset=66),
        "C_false_alarm": dict(base="C_constrained_supplier", cover=2.0, share=0.5,
                              profile=[(66, 1.0, 1.0), (67, 0.55, 2.0), (68, 1.0, 1.0)], onset=None),
        "D_demand_only_shock": dict(base="B_volatile_retail", cover=2.0, share=0.0, profile=[],
                                    demand_shock=(66, 6, 1.6), onset=None),
        "E_recovery": dict(base="C_constrained_supplier", cover=2.0, share=0.5,
                           profile=[(44, 1.0, 1.0), (46, 0.6, 2.0), (54, 0.6, 2.0), (58, 1.0, 1.0)], onset=None),
        "F_asymmetric_suppliers": dict(base="E_mixed_portfolio", cover=2.0, suppliers=("SUP-001",),
                                       profile=[(64, 1.0, 1.0), (66, 0.55, 2.0), (74, 0.55, 2.0), (78, 1.0, 1.0)],
                                       onset=64),
        "easy_slack": dict(base="A_stable", cover=5.0, share=0.0, profile=[], onset=None),
    },
}
POLICIES = ("incumbent", "stochastic_sp", "anchored_sp", "safe_selected", "adaptive_sp", "adaptive_safe")


def spec_for(name: str, cfg: dict):
    base = ARCHETYPES[cfg["base"]]
    return replace(base, name=f"{base.name}+{name}", disruption_week=None,
                   disruption_profile=list(cfg.get("profile", [])),
                   disrupted_supplier_share=float(cfg.get("share", 0.0)),
                   disrupted_suppliers=tuple(cfg.get("suppliers", ())),
                   demand_shock=cfg.get("demand_shock"))


def rolling(policy, h, cfg_safe, cover, rng, cap_weeks=8.0):
    """Closed loop; the adaptive policies carry a StateTracker and the
    previously published schedule across reviews. Returns settlement
    totals, selection log, churn and the state trajectory."""
    fi0, _ = fold_from_history(h, START, HORIZON, TRAIN, cover, 0.95, 0.02 / 4.33)
    products, sup_of, lead_of = fi0.products, fi0.supplier_of, fi0.lead_of
    horizon = max(HORIZON, 2 * max(lead_of.values()) + REVIEW)
    ol = h.order_lines.copy()
    ol["week"] = ol["order_id"].str[4:8].astype(int)
    dem = ol.groupby(["sku", "week"])["qty_ordered"].sum()
    po = h.purchase_orders.copy()
    po["week"] = (pd.to_datetime(po["po_date"]) - pd.to_datetime(h.purchase_orders["po_date"].min())).dt.days // 7
    rec = h.receipts.groupby("po_id")["qty_received"].sum()
    po = po.join(rec, on="po_id").fillna({"qty_received": 0.0})
    po["fill"] = (po["qty_received"] / po["qty_ordered"]).clip(0, 1)
    truth_f, truth_l = {}, {}
    for s_ in set(sup_of.values()):
        sub = po[po["supplier_id"] == s_]
        base = float(sub[sub["week"] < START]["fill"].mean()) if len(sub[sub["week"] < START]) else 0.95
        for t in range(RUN + horizon):
            row = sub[sub["week"] == START + t]
            truth_f[(s_, t)] = float(row["fill"].mean()) if len(row) else base
            truth_l[(s_, t)] = int(round(row["lead_weeks"].mean())) if len(row) and "lead_weeks" in row else int(lead_of[s_])
    cap_total = sum(st.mean(fi0.train_demand[j]) for j in products) * cap_weeks
    carry = fi0.policy.cost_config.holding_rate_per_period
    on_hand = dict(fi0.opening)
    arrivals: dict = {}
    holding_c = shortage = 0.0
    served = demanded = inv_sum = 0.0
    selections: dict = {}
    changes, solve_t, traj = [], [], []
    prev_sched = None
    tracker = TrackerBank()
    affected = set(h.suppliers[h.suppliers["disrupted"]]["supplier_id"]) if "disrupted" in h.suppliers else set()
    t = 0
    while t < RUN:
        pipeline = {(j, tt - t): q for (j, tt), q in arrivals.items() if tt >= t and tt - t < horizon}
        fi, _ = fold_from_history(h, START + t, horizon, TRAIN, cover, 0.95, 0.02 / 4.33)
        fi.opening = dict(on_hand)
        fi.pipeline = dict(pipeline)
        t0 = time.perf_counter()
        if policy.startswith("adaptive"):
            est = estimate(fi, None, tracker=tracker)
            est.posture.p_disruptive_by_route = p_disruptive_by_route(est, fi)  # type: ignore[attr-defined]
            est.posture.in_recovery_by_route = in_recovery_by_route(est, fi)    # type: ignore[attr-defined]
            fi.posture = est.posture
            fi.previous_schedule = ({(i, j, tt - REVIEW): q for (i, j, tt), q in prev_sched.items() if tt >= REVIEW}
                                    if prev_sched else None)
            aff = [est.sku[j].p_disruptive() for j in products if sup_of[j] in affected]
            unaff = [est.sku[j].p_disruptive() for j in products if sup_of[j] not in affected]
            traj.append({"t": START + t, "p_disruptive": est.portfolio.p_disruptive(), "dominant": est.portfolio.dominant,
                         "p_affected": float(np.mean(aff)) if aff else None,
                         "p_unaffected": float(np.mean(unaff)) if unaff else None,
                         "value_share_disrupted": est.portfolio.features.get("value_share_disrupted", 0.0),
                         "stress": est.portfolio.stress, "posture_disrupted": tracker.get("*").posture_disrupted,
                         "sku_flags": sum(1 for j in products if tracker.get(j).posture_disrupted),
                         "commit_window": est.posture.commit_window, "autonomy": est.posture.autonomy,
                         "cvar_lambda": est.posture.cvar_lambda,
                         "trust_mean": float(np.mean(list(est.posture.trust_region.values()))) if est.posture.trust_region else 0.0})
        if policy == "incumbent":
            sched, mode = fi.incumbent.build_schedule(fi), "incumbent"
        elif policy == "stochastic_sp":
            sched, _m = policy_stochastic_sp(fi, cap_total, rng, FROZEN["scenarios"])
            mode = policy
        elif policy == "anchored_sp":
            sched, _m = policy_anchored_sp(fi, cap_total, rng, FROZEN["scenarios"])
            mode = policy
        elif policy == "adaptive_sp":
            sched, _m = EXTRA_CANDIDATES["adaptive_sp"](fi, cap_total, rng, FROZEN["scenarios"])
            mode = policy
        elif policy == "safe_selected":
            d = safe_select(fi, cap_total, rng, cfg_safe, extra_candidates={"anchored_sp": policy_anchored_sp})
            sched, mode = d.schedule, d.mode_run
        else:   # adaptive_safe
            d = safe_select(fi, cap_total, rng, cfg_safe, posture=fi.posture,
                            extra_candidates={"anchored_sp": policy_anchored_sp,
                                              "adaptive_sp": EXTRA_CANDIDATES["adaptive_sp"]})
            sched, mode = d.schedule, d.mode_run
        solve_t.append(time.perf_counter() - t0)
        if sched is None:
            sched, mode = fi.incumbent.build_schedule(fi), "incumbent(fallback)"
        selections[mode] = selections.get(mode, 0) + 1
        if prev_sched is not None:
            tot = sum(v for (i, j, tt), v in sched.items() if tt < REVIEW) or 1.0
            changes.append(sum(abs(sched.get(k, 0.0) - prev_sched.get(k, 0.0))
                               for k in set(sched) | set(prev_sched) if k[2] < REVIEW) / tot)
        prev_sched = sched
        for (sup, sku, rel_t), q in sched.items():
            if rel_t >= REVIEW or q <= 0:
                continue
            q = min(float(q), float(fi.capacity.get(sku, q)))
            key = (sku, t + rel_t + int(truth_l.get((sup, t + rel_t), lead_of[sup])))
            arrivals[key] = arrivals.get(key, 0.0) + q * float(truth_f.get((sup, t + rel_t), 1.0))
        for step in range(REVIEW):
            at = t + step
            if at >= RUN:
                break
            stock = 0.0
            for j in products:
                dm = float(dem.get((j, START + at), 0.0))
                have = on_hand.get(j, 0.0) + arrivals.pop((j, at), 0.0)
                got = min(have, dm)
                short = max(dm - have, 0.0)
                shortage += short * fi0.margin[j]
                left = max(have - dm, 0.0)
                on_hand[j] = left
                stock += left
                served += got
                demanded += dm
            if stock > cap_total > 0:
                scale = cap_total / stock
                for j in on_hand:
                    on_hand[j] *= scale
            for j in products:
                holding_c += on_hand[j] * fi0.unit_cost[j] * carry
                inv_sum += on_hand[j]
        t += REVIEW
    return {"total": holding_c + shortage, "holding": holding_c, "shortage": shortage,
            "fill": served / demanded if demanded else 1.0, "avg_inventory": inv_sum / max(RUN, 1),
            "selections": selections, "plan_change": float(np.mean(changes)) if changes else 0.0,
            "solve_p50": float(np.median(solve_t)) if solve_t else 0.0, "trajectory": traj}


def transition_metrics(traj: list, onset: int | None) -> dict:
    """Detection lag (reviews from onset to p_disruptive > 0.5), peak
    p_disruptive, number of posture flips, and whether the engine
    unwound (last p_disruptive below 0.35) when the episode ended."""
    if not traj:
        return {}
    p = [x["p_disruptive"] for x in traj]
    pa = [x["p_affected"] if x["p_affected"] is not None else x["p_disruptive"] for x in traj]
    pu = [x["p_unaffected"] for x in traj if x["p_unaffected"] is not None]
    flips = sum(1 for a, b in zip(traj, traj[1:]) if a["sku_flags"] != b["sku_flags"])
    first = next((x["t"] for x, v in zip(traj, pa) if v > 0.5), None)
    lag = (first - onset) if (onset is not None and first is not None and first >= onset) else None
    return {"peak_p_disruptive": max(p), "min_p_disruptive": min(p), "final_p_disruptive": p[-1],
            "peak_p_affected": max(pa), "final_p_affected": pa[-1],
            "peak_p_unaffected": max(pu) if pu else None,
            "detection_week": first, "detection_lag_weeks": lag, "posture_flips": flips,
            "min_commit_window": min(x["commit_window"] for x in traj),
            "max_commit_window": max(x["commit_window"] for x in traj),
            "weeks_disrupted_posture": sum(1 for x in traj if x["posture_disrupted"]) * REVIEW,
            "trajectory": [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in x.items()} for x in traj]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--tests", default="")
    ap.add_argument("--out", default=str(ROOT / "artifacts" / "adaptive_transition_validation.json"))
    ap.add_argument("--merge", nargs="*", default=None, help="part files to combine into --out")
    a = ap.parse_args()
    if a.merge is not None:
        return merge(a.merge, Path(a.out))
    seeds = FROZEN["eval_seeds"][:1] if a.quick else FROZEN["eval_seeds"]
    tests = [t for t in FROZEN["tests"] if not a.tests or t in a.tests.split(",")]
    policies = POLICIES if not a.quick else ("incumbent", "stochastic_sp", "adaptive_sp", "adaptive_safe")
    cfg_safe = SafeSelectionConfig(**FROZEN["safe"], n_scen=FROZEN["scenarios"])
    results: dict = {"frozen": FROZEN, "policies": list(policies), "runs": [], "started": time.time()}
    for name in tests:
        cfg = FROZEN["tests"][name]
        for seed in seeds:
            h = build_history(cfg["base"], seed=seed, spec=spec_for(name, cfg))
            row: dict = {"test": name, "seed": seed, "policy": {}}
            for pol in policies:
                t0 = time.time()
                r = rolling(pol, h, cfg_safe, cfg["cover"], np.random.default_rng(seed))
                r["wall_s"] = time.time() - t0
                if pol.startswith("adaptive"):
                    r["transition"] = transition_metrics(r.pop("trajectory"), cfg.get("onset"))
                else:
                    r.pop("trajectory", None)
                row["policy"][pol] = r
                print(f"{name:26s} seed {seed} {pol:14s} total {r['total']:12.0f} fill {r['fill']:.3f} "
                      f"churn {r['plan_change']:.2f} {r['selections']}", flush=True)
            results["runs"].append(row)
    finish(results, tests, policies, Path(a.out))
    return 0


def finish(results: dict, tests: list, policies, out: Path) -> None:
    """Summaries (each policy vs incumbent per test) and the artifact."""
    summ: dict = {}
    for name in tests:
        rows = [r for r in results["runs"] if r["test"] == name]
        summ[name] = {}
        for pol in policies:
            if pol == "incumbent":
                continue
            edges = [(r["policy"]["incumbent"]["total"] - r["policy"][pol]["total"]) / r["policy"]["incumbent"]["total"]
                     for r in rows if r["policy"]["incumbent"]["total"] > 0]
            summ[name][pol] = {**summarize(edges), "fill": st.mean(r["policy"][pol]["fill"] for r in rows),
                               "churn": st.mean(r["policy"][pol]["plan_change"] for r in rows)}
        for pol in ("adaptive_sp", "adaptive_safe"):
            if pol in policies:
                tr = [r["policy"][pol]["transition"] for r in rows if r["policy"][pol].get("transition")]
                if tr:
                    summ[name][pol]["transition"] = {
                        "detection_lag_weeks": [x["detection_lag_weeks"] for x in tr],
                        "peak_p_disruptive": st.mean(x["peak_p_disruptive"] for x in tr),
                        "peak_p_affected": st.mean(x.get("peak_p_affected", x["peak_p_disruptive"]) for x in tr),
                        "peak_p_unaffected": st.mean((x.get("peak_p_unaffected") or 0.0) for x in tr),
                        "final_p_disruptive": st.mean(x["final_p_disruptive"] for x in tr),
                        "posture_flips": st.mean(x["posture_flips"] for x in tr),
                        "weeks_disrupted_posture": st.mean(x["weeks_disrupted_posture"] for x in tr),
                        "min_commit_window": min(x["min_commit_window"] for x in tr)}
    results["summary"] = summ
    results["elapsed_s"] = results.get("elapsed_s") or (time.time() - results["started"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=1, default=float))
    print(f"wrote {out} in {results['elapsed_s']:.0f}s")


def merge(parts: list, out: Path) -> int:
    """Combine per-test part files written by parallel workers."""
    runs, elapsed, policies = [], 0.0, None
    for pth in parts:
        d = json.loads(Path(pth).read_text())
        runs += d["runs"]
        elapsed = max(elapsed, d.get("elapsed_s", 0.0))
        policies = policies or d["policies"]
    results = {"frozen": FROZEN, "policies": policies, "runs": runs, "started": time.time(), "elapsed_s": elapsed,
               "parts": [str(p) for p in parts]}
    tests = [t for t in FROZEN["tests"] if any(r["test"] == t for r in runs)]
    finish(results, tests, tuple(policies or ()), out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
