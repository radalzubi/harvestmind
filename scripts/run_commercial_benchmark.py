"""PROJECT B benchmark: multi-period SP vs deterministic planning under
route-driven episodic disruption.

The question this answers: when transit is the uncertainty and the operator
can reschedule, does modelling the distribution beat a competent planner who
uses average lead times and grosses up for average fill?

Baselines, each adding one thing over the last, matching the Project A
ladder so the comparison is like for like:
  mean_lead      average lead time, average fill  (the deterministic planner)
  buffer_lead    lead time at the 90th percentile (the cautious planner)
  multi_period   the full distribution over lead time and fill
"""
from __future__ import annotations

import argparse
import statistics as st
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from optimization.multi_period_sp import MultiPeriodStochasticLP  # noqa: E402
from synthetic.commercial.jordan_distributor_sim import (  # noqa: E402
    PRODUCTS, JordanSimulationConfig, build_jordan_dataset,
)

HORIZON = 8


def _fold(data, origin_idx: int, train_weeks: int, n_scen: int, rng):
    """Build scenarios from the training window, score on held-out weeks."""
    weeks = data["weeks"]
    dl = pd.DataFrame(data["deliveries"])
    dm = pd.DataFrame(data["demand"])
    train_wk = weeks[origin_idx - train_weeks:origin_idx]
    eval_wk = weeks[origin_idx:origin_idx + HORIZON]
    if len(eval_wk) < HORIZON:
        return None

    tr_d = dl[dl["week_start"].isin(train_wk)]
    tr_m = dm[dm["week_start"].isin(train_wk)]
    if tr_d.empty or tr_m.empty:
        return None

    # Per-supplier training statistics. Leakage-safe: training window only.
    stats = tr_d.groupby("supplier_id").agg(
        lead_mean=("lead_time_weeks", "mean"),
        lead_p90=("lead_time_weeks", lambda x: float(np.quantile(x, 0.90))),
        fill_mean=("fill_rate", "mean")).to_dict("index")
    sup_ids = list(stats)
    mean_dem = tr_m.groupby("product_id")["demand_kg"].mean().to_dict()
    prods = list(mean_dem)

    # Scenarios: resample historical (lead, fill) pairs per supplier.
    scen_rows, leads, yields_ = [], {}, {}
    for w in range(n_scen):
        for j in prods:
            for t in range(HORIZON):
                scen_rows.append({
                    "scenario_index": w, "scenario_weight": 1.0 / n_scen,
                    "product_id": j, "period": t,
                    "demand_kg": float(mean_dem[j])})
        for sid in sup_ids:
            hist = tr_d[tr_d["supplier_id"] == sid]
            r = hist.iloc[int(rng.integers(len(hist)))]
            leads[(w, sid)] = int(round(float(r["lead_time_weeks"])))
            yields_[(w, sid)] = float(r["fill_rate"])
    scen = pd.DataFrame(scen_rows)

    # Capacity with headroom over peak observed demand, shared across
    # suppliers. An arbitrary ceiling made the Project A benchmark
    # degenerate by binding for every policy, so this is set high enough
    # that capacity is not the thing being measured.
    peak = tr_m.groupby("product_id")["demand_kg"].max().to_dict()
    cap = pd.DataFrame([
        {"supplier_id": sid, "product_id": j,
         "capacity_kg": float(peak.get(j, mean_dem[j])) * 2.5
         / max(len(sup_ids), 1),
         "price_per_kg": 2.0}
        for sid in sup_ids for j in prods])

    econ = {p[0]: {"cost": p[1], "margin": p[2], "decay": p[3]}
            for p in PRODUCTS}
    kw = dict(n_periods=HORIZON, spot_cost_multiplier=1.9,
              spot_capacity_factor=0.12,
              waste_cost_by_product={j: e["cost"] for j, e in econ.items()},
              unmet_cost_by_product={j: e["margin"] for j, e in econ.items()},
              holding_cost_by_product={j: e["cost"] * 0.006
                                       for j, e in econ.items()},
              decay_rate_by_product={j: e["decay"] for j, e in econ.items()})

    policies = {}
    # Deterministic: one scenario, mean lead and mean fill.
    det_scen = scen[scen["scenario_index"] == 0].copy()
    det_scen["scenario_weight"] = 1.0
    for tag, leadkey in (("mean_lead", "lead_mean"),
                         ("buffer_lead", "lead_p90")):
        policies[tag] = MultiPeriodStochasticLP(**kw).solve(
            det_scen, cap,
            lead_times={(0, s): int(round(stats[s][leadkey]))
                        for s in sup_ids},
            yield_scenarios={(0, s): stats[s]["fill_mean"] for s in sup_ids})
    policies["multi_period"] = MultiPeriodStochasticLP(**kw).solve(
        scen, cap, lead_times=leads, yield_scenarios=yields_)

    # Score every schedule on the SAME held-out weeks with realized data.
    ev_d = dl[dl["week_start"].isin(eval_wk)]
    ev_m = dm[dm["week_start"].isin(eval_wk)]
    # Per-WEEK realized lead and fill. Collapsing these to a per-supplier
    # mean flattened exactly the timing variation the model exists to
    # exploit, which understated every policy that reasons about timing.
    real_lead: dict[tuple[str, int], float] = {}
    real_fill: dict[tuple[str, int], float] = {}
    for _, r in ev_d.iterrows():
        t = eval_wk.index(r["week_start"])
        real_lead[(r["supplier_id"], t)] = float(r["lead_time_weeks"])
        real_fill[(r["supplier_id"], t)] = float(r["fill_rate"])
    sup_lead_fallback = ev_d.groupby("supplier_id")["lead_time_weeks"].mean().to_dict()
    sup_fill_fallback = ev_d.groupby("supplier_id")["fill_rate"].mean().to_dict()
    # Was this fold disrupted? Reported so the split can be analysed.
    disrupted_share = float(ev_d["route_disrupted"].mean()) if len(ev_d) else 0.0
    real_dem = {(r["product_id"], eval_wk.index(r["week_start"])): r["demand_kg"]
                for _, r in ev_m.iterrows()}

    out = {}
    for tag, res in policies.items():
        if res.get("status") not in ("optimal", "locallyOptimal"):
            return None
        arrivals: dict[tuple[str, int], float] = {}
        for (i, j, t), q in res["x"].items():
            if q <= 0:
                continue
            # Use the lead and fill realized in the week the order was
            # PLACED, not an average over the whole window.
            lag = int(round(real_lead.get((i, t), sup_lead_fallback.get(i, 1.0))))
            f = real_fill.get((i, t), sup_fill_fallback.get(i, 0.9))
            at = t + lag
            if at < HORIZON:
                arrivals[(j, at)] = arrivals.get((j, at), 0.0) + q * f
        cost = inv = 0.0
        carry: dict[str, float] = {}
        for t in range(HORIZON):
            for j in prods:
                e = econ[j]
                have = carry.get(j, 0.0) + arrivals.get((j, t), 0.0)
                d = float(real_dem.get((j, t), 0.0))
                short = max(d - have, 0.0)
                spot = min(short, 0.12 * d)
                unmet = short - spot
                left = max(have - d, 0.0)
                decayed = left * e["decay"]
                cost += (spot * e["cost"] * 0.9 + unmet * e["margin"]
                         + decayed * e["cost"] + left * e["cost"] * 0.006)
                carry[j] = left - decayed
                inv += left
        out[tag] = cost
    out["_disrupted_share"] = disrupted_share
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seeds", default="7,19,31")
    p.add_argument("--weeks", type=int, default=160)
    p.add_argument("--train-weeks", type=int, default=52)
    p.add_argument("--folds", type=int, default=10)
    p.add_argument("--scenarios", type=int, default=12)
    a = p.parse_args()

    all_edges: dict[str, list[float]] = {"mean_lead": [], "buffer_lead": []}
    split: dict[str, list[float]] = {"disrupted": [], "calm": []}
    for seed in [int(s) for s in a.seeds.split(",")]:
        data = build_jordan_dataset(JordanSimulationConfig(
            seed=seed, weeks=a.weeks))
        rng = np.random.default_rng(seed + 5000)
        n = len(data["weeks"])
        for k in range(a.folds):
            oi = n - HORIZON - a.folds + k
            if oi < a.train_weeks:
                continue
            r = _fold(data, oi, a.train_weeks, a.scenarios, rng)
            if not r:
                continue
            mp = r["multi_period"]
            for base in ("mean_lead", "buffer_lead"):
                if r[base] > 0:
                    all_edges[base].append((r[base] - mp) / r[base] * 100)
            # The decisive split: the model should earn its keep when a
            # route is actually disrupted and roughly tie when it is not.
            # If it does not separate here, it is not modelling what we
            # think it is modelling.
            if r["mean_lead"] > 0:
                e = (r["mean_lead"] - mp) / r["mean_lead"] * 100
                bucket = "disrupted" if r["_disrupted_share"] > 0.15 else "calm"
                split[bucket].append(e)

    print("\nPROJECT B — commercial (Jordan), route-driven episodic disruption")
    print(f"  folds scored: {len(all_edges['mean_lead'])}\n")
    for base, lab in (("mean_lead", "vs deterministic (mean lead + fill)"),
                      ("buffer_lead", "vs cautious (p90 lead)")):
        e = all_edges[base]
        if not e:
            print(f"  {lab}: no folds")
            continue
        wins = sum(1 for x in e if x > 0)
        print(f"  {lab:38} median {st.median(e):+7.2f}%   "
              f"wins {wins}/{len(e)}   range {min(e):+.1f} to {max(e):+.1f}")
    print("\n  THE DECISIVE SPLIT (vs deterministic, by fold condition):")
    for bucket in ("disrupted", "calm"):
        e = split[bucket]
        if not e:
            print(f"    {bucket:10} no folds")
            continue
        wins = sum(1 for x in e if x > 0)
        print(f"    {bucket:10} n={len(e):<3} median {st.median(e):+7.2f}%   "
              f"wins {wins}/{len(e)}")
    if split["disrupted"] and split["calm"]:
        gap = st.median(split["disrupted"]) - st.median(split["calm"])
        print(f"    separation: {gap:+.2f} points. Positive means the model "
              f"earns its keep\n    when routes are disrupted, which is the "
              f"only reason to run it.")
    print("\n  Synthetic data. Every parameter is an assumption.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
