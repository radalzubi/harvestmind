"""Digital-twin counterfactuals: every policy faces the same seeds, the same
demand, the same supplier behaviour and the SAME settlement.

The question this answers is narrow and the only one a distributor cares
about: on identical operating histories, does the stochastic optimizer's
ordering schedule cost less than what a competent planner would have done?
"Cost" is the full economic cost the domain policy prices: holding,
shortage (lost margin), disposal, SLA penalty, emergency premium.

RULES THAT ARE NOT NEGOTIABLE, learned the hard way in this repository:
  * credited with what ARRIVES, not what was ordered;
  * one settlement function for every policy;
  * no outcome-based fold filtering; strata are reported, not removed;
  * scenarios from the training window only; realised shocks only in
    settlement;
  * the naive baselines are competent (safety stock, fill gross-up), not
    straw men.

Baselines (section 14 of the readiness spec):
  naive_forecast     order this period's mean forecast, grossed up by fill
  last_period        order what sold last period
  seasonal_naive     order what sold 52 weeks ago
  static_safety      mean + z*sd every period (fixed safety stock)
  min_max            (s, S) reorder point / order-up-to on inventory position
  order_up_to        periodic review order-up-to over lead + review
  deterministic_sp   the SAME optimizer given a point forecast (fill-aware)
  stochastic_sp      the multi-period SP over bootstrapped scenarios
"""

from __future__ import annotations

import math
import statistics as st
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from domain.model import DomainPolicy
from domain.uom import round_to_pack
from optimization.multi_period_sp import MultiPeriodStochasticLP

POLICIES = ("naive_forecast", "last_period", "seasonal_naive", "static_safety",
            "min_max", "order_up_to", "deterministic_sp", "stochastic_sp")


@dataclass
class FoldInputs:
    """Everything a policy may see at the origin, and nothing after it."""
    origin: int
    horizon: int
    products: list
    supplier_of: dict            # product -> supplier
    lead_of: dict                # supplier -> integer periods (mean)
    train_demand: dict           # product -> list of past periods
    train_fill: dict             # supplier -> list of observed fills
    unit_cost: dict
    margin: dict
    capacity: dict               # product -> per-period supplier capacity
    opening: dict
    pipeline: dict               # (product, t) -> qty already in transit
    policy: DomainPolicy


@dataclass
class FoldTruth:
    """Realised path, used ONLY in settlement."""
    demand: dict                 # (product, t)
    fill: dict                   # (supplier, t)
    lead: dict                   # (supplier, t)


@dataclass
class Settlement:
    total: float
    holding: float
    shortage: float
    disposal: float
    sla_penalty: float
    fill_rate: float
    ending_inventory: float
    inventory_periods: float     # average units on hand, for turns
    components: dict = field(default_factory=dict)


# ── settlement ───────────────────────────────────────────────────────────────
def settle(schedule: dict, fi: FoldInputs, truth: FoldTruth,
           warehouse_cap: float | None) -> Settlement:
    cc = fi.policy.cost_config
    carry = float(cc.holding_rate_per_period)
    decay = float(fi.policy.decay_rate_per_period)
    arrivals: dict = dict(fi.pipeline)
    for (sup, sku, t), q in schedule.items():
        if q <= 0:
            continue
        lag = int(truth.lead.get((sup, t), fi.lead_of.get(sup, 1)))
        f = float(truth.fill.get((sup, t), 1.0))
        at = t + lag
        if at < fi.horizon:
            arrivals[(sku, at)] = arrivals.get((sku, at), 0.0) + q * f
    inv = dict(fi.opening)
    holding = shortage = disposal = sla = 0.0
    served = demanded = 0.0
    inv_sum = 0.0
    for t in range(fi.horizon):
        pending = {}
        stock_total = 0.0
        for j in fi.products:
            d = float(truth.demand.get((j, t), 0.0))
            have = inv.get(j, 0.0) + arrivals.get((j, t), 0.0)
            got = min(have, d)
            short = max(d - have, 0.0)
            shortage += short * fi.margin[j]
            if cc.sla_fill_target is not None and d > 0 and \
                    (1 - short / d) < cc.sla_fill_target:
                sla += short * fi.unit_cost[j] * cc.sla_penalty_rate
            left = max(have - d, 0.0)
            if decay > 0:
                lost = left * decay
                disposal += lost * float(cc.waste_cost_per_unit.get(j, fi.unit_cost[j]))
                left -= lost
            pending[j] = left
            stock_total += left
            served += got
            demanded += d
        if warehouse_cap is not None and stock_total > warehouse_cap > 0:
            scale = warehouse_cap / stock_total
            for j in pending:
                lost = pending[j] * (1 - scale)
                disposal += lost * fi.unit_cost[j]
                pending[j] *= scale
        for j, left in pending.items():
            holding += left * fi.unit_cost[j] * carry
            inv[j] = left
            inv_sum += left
    total = holding + shortage + disposal + sla
    return Settlement(total=total, holding=holding, shortage=shortage, disposal=disposal,
                      sla_penalty=sla, fill_rate=served / demanded if demanded else 1.0,
                      ending_inventory=sum(inv.values()),
                      inventory_periods=inv_sum / max(fi.horizon, 1))


# ── baseline policies ────────────────────────────────────────────────────────
def _round(fi: FoldInputs, j: str, q: float) -> float:
    return round_to_pack(max(q, 0.0), fi.policy.pack_spec_for(j))


def _mean(xs): return float(st.mean(xs)) if xs else 0.0


def _sd(xs): return float(st.pstdev(xs)) if len(xs) > 1 else 0.0


def policy_naive_forecast(fi: FoldInputs) -> dict:
    out = {}
    for j in fi.products:
        s = fi.supplier_of[j]
        f = max(_mean(fi.train_fill[s]), 0.3)
        q = _mean(fi.train_demand[j]) / f
        for t in range(fi.horizon):
            out[(s, j, t)] = _round(fi, j, q)
    return out


def policy_last_period(fi: FoldInputs) -> dict:
    out = {}
    for j in fi.products:
        s = fi.supplier_of[j]
        f = max(_mean(fi.train_fill[s]), 0.3)
        last = fi.train_demand[j][-1] if fi.train_demand[j] else 0.0
        for t in range(fi.horizon):
            out[(s, j, t)] = _round(fi, j, last / f)
    return out


def policy_seasonal_naive(fi: FoldInputs, season: int = 52) -> dict:
    out = {}
    for j in fi.products:
        s = fi.supplier_of[j]
        f = max(_mean(fi.train_fill[s]), 0.3)
        hist = fi.train_demand[j]
        for t in range(fi.horizon):
            k = len(hist) - season + t
            ref = hist[k] if 0 <= k < len(hist) else _mean(hist)
            out[(s, j, t)] = _round(fi, j, ref / f)
    return out


def policy_static_safety(fi: FoldInputs, z: float = 1.64) -> dict:
    out = {}
    for j in fi.products:
        s = fi.supplier_of[j]
        f = max(_mean(fi.train_fill[s]), 0.3)
        mu, sd = _mean(fi.train_demand[j]), _sd(fi.train_demand[j])
        for t in range(fi.horizon):
            out[(s, j, t)] = _round(fi, j, (mu + z * sd) / f)
    return out


def _open_loop_position_policy(fi: FoldInputs, reorder_point, order_up_to) -> dict:
    """Simulate an (s, S) rule against EXPECTED demand — open loop, since the
    schedule must be committed at the origin like every other policy."""
    out = {}
    for j in fi.products:
        s = fi.supplier_of[j]
        f = max(_mean(fi.train_fill[s]), 0.3)
        mu = _mean(fi.train_demand[j])
        lead = int(fi.lead_of[s])
        pos = fi.opening.get(j, 0.0) + sum(q for (jj, t), q in fi.pipeline.items() if jj == j)
        for t in range(fi.horizon):
            pos -= mu
            if pos <= reorder_point(j, mu, lead):
                q = max(order_up_to(j, mu, lead) - pos, 0.0) / f
                q = _round(fi, j, q)
                out[(s, j, t)] = q
                pos += q * f
    return out


def policy_min_max(fi: FoldInputs, z: float = 1.64) -> dict:
    def s_pt(j, mu, lead):
        return mu * lead + z * _sd(fi.train_demand[j]) * math.sqrt(max(lead, 1))

    def big_s(j, mu, lead):
        return s_pt(j, mu, lead) + mu * 2
    return _open_loop_position_policy(fi, s_pt, big_s)


def policy_order_up_to(fi: FoldInputs, z: float = 1.64) -> dict:
    def s_pt(j, mu, lead):
        return float("inf")          # review every period

    def big_s(j, mu, lead):
        cover = lead + 1
        return mu * cover + z * _sd(fi.train_demand[j]) * math.sqrt(cover)
    return _open_loop_position_policy(fi, s_pt, big_s)


# ── optimizer policies ───────────────────────────────────────────────────────
def _optimizer_kwargs(fi: FoldInputs, warehouse_cap):
    cc = fi.policy.cost_config
    return dict(
        n_periods=fi.horizon, spot_cost_multiplier=cc.emergency_cost_multiplier,
        spot_capacity_factor=cc.emergency_capacity_factor if cc.emergency_capacity_factor is not None else 0.0,
        waste_cost_by_product={j: float(cc.waste_cost_per_unit.get(j, fi.unit_cost[j])) for j in fi.products},
        unmet_cost_by_product={j: fi.margin[j] for j in fi.products},
        holding_cost_by_product={j: fi.unit_cost[j] * cc.holding_rate_per_period for j in fi.products},
        decay_rate_by_product={j: fi.policy.decay_rate_per_period for j in fi.products},
        inventory_capacity_total=warehouse_cap,
        pack_specs={j: fi.policy.pack_spec_for(j) for j in fi.products
                    if fi.policy.pack_spec_for(j).is_discrete} or None,
        time_limit_s=60.0,
    )


def _supply_df(fi: FoldInputs) -> pd.DataFrame:
    return pd.DataFrame([{"supplier_id": fi.supplier_of[j], "product_id": j,
                          "capacity_kg": float(fi.capacity[j]),
                          "price_per_kg": fi.unit_cost[j]} for j in fi.products])


def _scenarios(fi: FoldInputs, n_scen: int, rng) -> tuple[pd.DataFrame, dict, dict]:
    rows, leads, fills = [], {}, {}
    sups = sorted(set(fi.supplier_of.values()))
    for w in range(n_scen):
        for j in fi.products:
            hist = fi.train_demand[j]
            for t in range(fi.horizon):
                d = float(rng.choice(hist)) if hist else 0.0
                rows.append({"scenario_index": w, "scenario_weight": 1 / n_scen,
                             "product_id": j, "period": t, "demand_kg": d})
        for s in sups:
            fills[(w, s)] = float(rng.choice(fi.train_fill[s])) if fi.train_fill[s] else 1.0
            leads[(w, s)] = int(fi.lead_of[s])
    return pd.DataFrame(rows), leads, fills


def policy_deterministic_sp(fi: FoldInputs, warehouse_cap, rng, n_scen=1) -> tuple[dict, dict]:
    rows = [{"scenario_index": 0, "scenario_weight": 1.0, "product_id": j, "period": t,
             "demand_kg": _mean(fi.train_demand[j])} for j in fi.products for t in range(fi.horizon)]
    sups = sorted(set(fi.supplier_of.values()))
    r = MultiPeriodStochasticLP(**_optimizer_kwargs(fi, warehouse_cap)).solve(
        pd.DataFrame(rows), _supply_df(fi),
        lead_times={(0, s): int(fi.lead_of[s]) for s in sups},
        yield_scenarios={(0, s): _mean(fi.train_fill[s]) or 1.0 for s in sups},
        opening_inventory=fi.opening)
    return ({k: v for k, v in r["x"].items() if v > 0} if r["usable"] else None), r


def policy_stochastic_sp(fi: FoldInputs, warehouse_cap, rng, n_scen=30) -> tuple[dict, dict]:
    scen, leads, fills = _scenarios(fi, n_scen, rng)
    r = MultiPeriodStochasticLP(**_optimizer_kwargs(fi, warehouse_cap)).solve(
        scen, _supply_df(fi), lead_times=leads, yield_scenarios=fills,
        opening_inventory=fi.opening)
    return ({k: v for k, v in r["x"].items() if v > 0} if r["usable"] else None), r


def run_policies(fi: FoldInputs, truth: FoldTruth, warehouse_cap, rng,
                 n_scen: int = 30, policies=POLICIES) -> dict:
    out = {}
    for name in policies:
        meta = {}
        if name == "deterministic_sp":
            sched, meta = policy_deterministic_sp(fi, warehouse_cap, rng)
        elif name == "stochastic_sp":
            sched, meta = policy_stochastic_sp(fi, warehouse_cap, rng, n_scen)
        else:
            sched = globals()[f"policy_{name}"](fi)
        if sched is None:
            out[name] = {"status": meta.get("status", "error"), "settlement": None}
            continue
        s = settle(sched, fi, truth, warehouse_cap)
        out[name] = {"status": meta.get("status", "heuristic"), "settlement": s,
                     "total_ordered": float(sum(sched.values())),
                     "runtime_s": meta.get("runtime_s", 0.0)}
    return out


# ── statistics over many folds / seeds ───────────────────────────────────────
def summarize(edges: list[float], boot: int = 2000, seed: int = 0) -> dict:
    if not edges:
        return {"n": 0}
    x = np.asarray(edges, dtype=float)
    rng = np.random.default_rng(seed)
    meds = np.array([np.median(rng.choice(x, len(x), replace=True)) for _ in range(boot)])
    return {
        "n": int(len(x)), "mean": float(x.mean()), "median": float(np.median(x)),
        "sd": float(x.std(ddof=1)) if len(x) > 1 else 0.0,
        "p5": float(np.percentile(x, 5)), "p25": float(np.percentile(x, 25)),
        "p75": float(np.percentile(x, 75)), "p95": float(np.percentile(x, 95)),
        "worst": float(x.min()), "best": float(x.max()),
        "win_rate": float((x > 0).mean()),
        "ci95_median": [float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5))],
    }
