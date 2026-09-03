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
  * no outcome-based fold filtering
  strata are reported, not removed;
  * scenarios from the training window only
  realised shocks only in
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
            "min_max", "order_up_to", "deterministic_sp", "stochastic_sp",
            "selected")


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
    # Planned promotions the operator KNOWS about at the origin:
    # (product, t) -> demand multiplier. A known uplift is an input, not a
    # surprise; scenarios are scaled by it and the deterministic twin sees
    # the same expectation.
    promo_multiplier: dict = field(default_factory=dict)


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
        # Supplier capacity binds every policy identically. The optimizer
        # respects it in the model; a heuristic that ignores it would
        # otherwise be credited with deliveries no supplier could make.
        q = min(float(q), float(fi.capacity.get(sku, q)))
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


def _promo(fi: FoldInputs, j: str, t: int) -> float:
    return float(fi.promo_multiplier.get((j, t), 1.0))


def policy_naive_forecast(fi: FoldInputs) -> dict:
    out = {}
    for j in fi.products:
        s = fi.supplier_of[j]
        f = max(_mean(fi.train_fill[s]), 0.3)
        q = _mean(fi.train_demand[j]) / f
        for t in range(fi.horizon):
            out[(s, j, t)] = _round(fi, j, q * _promo(fi, j, t))
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
            mu_t = mu * _promo(fi, j, t)
            pos -= mu_t
            if pos <= reorder_point(j, mu_t, lead):
                q = max(order_up_to(j, mu_t, lead) - pos, 0.0) / f
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
        service_floor_by_product=(
            {j: fi.policy.service_target.level for j in fi.products}
            if fi.policy.service_target.metric == "unit_fill"
            and fi.policy.service_target.scope == "global" else None),
        time_limit_s=60.0,
    )


def _supply_df(fi: FoldInputs) -> pd.DataFrame:
    return pd.DataFrame([{"supplier_id": fi.supplier_of[j], "product_id": j,
                          "capacity_kg": float(fi.capacity[j]),
                          "price_per_kg": fi.unit_cost[j]} for j in fi.products])


SEASON = 52


def _seasonal_pool(hist: list, h: int, width: int = 2) -> list:
    """Training observations at the same position in the season as horizon
    step ``h``, +/- ``width`` periods, from every past cycle. Falls back to
    the whole history when fewer than one full cycle is available.

    An iid bootstrap over a full year hands the optimizer a distribution
    centred on the annual mean
    a 12-week window sitting on the seasonal
    peak then reads as an 11% upward surprise every fold. Scored on 4,404
    real origin-horizon pairs this seasonal resampling cut the interval
    score by a third relative to the iid version
    it is the default here.
    """
    n = len(hist)
    if n < SEASON:
        return hist
    target = (n + h) % SEASON
    pool = [hist[k] for k in range(n)
            if min((k - target) % SEASON, (target - k) % SEASON) <= width]
    return pool or hist


def _scenarios(fi: FoldInputs, n_scen: int, rng) -> tuple[pd.DataFrame, dict, dict]:
    rows, leads, fills = [], {}, {}
    sups = sorted(set(fi.supplier_of.values()))
    pools = {j: [_seasonal_pool(fi.train_demand[j], h) for h in range(fi.horizon)]
             for j in fi.products}
    for w in range(n_scen):
        for j in fi.products:
            for t in range(fi.horizon):
                pool = pools[j][t]
                d = float(rng.choice(pool)) if pool else 0.0
                d *= float(fi.promo_multiplier.get((j, t), 1.0))
                rows.append({"scenario_index": w, "scenario_weight": 1 / n_scen,
                             "product_id": j, "period": t, "demand_kg": d})
        for s in sups:
            fills[(w, s)] = float(rng.choice(fi.train_fill[s])) if fi.train_fill[s] else 1.0
            leads[(w, s)] = int(fi.lead_of[s])
    return pd.DataFrame(rows), leads, fills


def policy_deterministic_sp(fi: FoldInputs, warehouse_cap, rng, n_scen=1) -> tuple[dict | None, dict]:
    rows = [{"scenario_index": 0, "scenario_weight": 1.0, "product_id": j, "period": t,
             "demand_kg": _mean(_seasonal_pool(fi.train_demand[j], t))
             * float(fi.promo_multiplier.get((j, t), 1.0))}
            for j in fi.products for t in range(fi.horizon)]
    sups = sorted(set(fi.supplier_of.values()))
    kw = _optimizer_kwargs(fi, warehouse_cap)
    args = (pd.DataFrame(rows), _supply_df(fi))
    kws: dict = dict(lead_times={(0, s): int(fi.lead_of[s]) for s in sups},
               yield_scenarios={(0, s): _mean(fi.train_fill[s]) or 1.0 for s in sups},
               opening_inventory=fi.opening)
    r = MultiPeriodStochasticLP(**kw).solve(*args, **kws)
    if not r["usable"] and kw.get("service_floor_by_product"):
        kw["service_floor_by_product"] = None
        r = MultiPeriodStochasticLP(**kw).solve(*args, **kws)
        r["warnings"] = list(r.get("warnings", [])) + ["service floor unattainable; solved without it"]
        r["floor_relaxed"] = True
    return ({k: v for k, v in r["x"].items() if v > 0} if r["usable"] else None), r


def policy_stochastic_sp(fi: FoldInputs, warehouse_cap, rng, n_scen=30) -> tuple[dict | None, dict]:
    scen, leads, fills = _scenarios(fi, n_scen, rng)
    kw = _optimizer_kwargs(fi, warehouse_cap)
    r = MultiPeriodStochasticLP(**kw).solve(
        scen, _supply_df(fi), lead_times=leads, yield_scenarios=fills,
        opening_inventory=fi.opening)
    if not r["usable"] and kw.get("service_floor_by_product"):
        # The floor was unattainable with this capacity: solve without it and
        # say so, rather than silently handing the fold to a heuristic.
        kw["service_floor_by_product"] = None
        r = MultiPeriodStochasticLP(**kw).solve(
            scen, _supply_df(fi), lead_times=leads, yield_scenarios=fills,
            opening_inventory=fi.opening)
        r["warnings"] = list(r.get("warnings", [])) + ["service floor unattainable; solved without it"]
        r["floor_relaxed"] = True
    return ({k: v for k, v in r["x"].items() if v > 0} if r["usable"] else None), r


def _inner_fold(fi: FoldInputs, holdout: int) -> tuple[FoldInputs, FoldTruth]:
    """A backtest fold built ENTIRELY inside the training window: the last
    ``holdout`` training periods become the truth, everything before them
    is the history. Nothing at or after the real origin is touched."""
    train = {j: fi.train_demand[j][:-holdout] for j in fi.products}
    truth_d = {(j, t): fi.train_demand[j][-holdout + t] for j in fi.products for t in range(holdout)}
    sups = set(fi.supplier_of.values())
    mean_fill = {s: (_mean(fi.train_fill[s]) or 1.0) for s in sups}
    truth_f = {(s, t): mean_fill[s] for s in sups for t in range(holdout)}
    truth_l = {(s, t): int(fi.lead_of[s]) for s in sups for t in range(holdout)}
    mean_dem = {j: _mean(train[j]) for j in fi.products}
    opening = {j: mean_dem[j] * (fi.opening[j] / max(_mean(fi.train_demand[j]), 1e-9)) for j in fi.products}
    pipeline = {(j, t): mean_dem[j] for j in fi.products for t in range(int(fi.lead_of[fi.supplier_of[j]]))}
    inner = FoldInputs(origin=fi.origin - holdout, horizon=holdout, products=fi.products,
                       supplier_of=fi.supplier_of, lead_of=fi.lead_of, train_demand=train,
                       train_fill=fi.train_fill, unit_cost=fi.unit_cost, margin=fi.margin,
                       capacity=fi.capacity, opening=opening, pipeline=pipeline, policy=fi.policy)
    return inner, FoldTruth(demand=truth_d, fill=truth_f, lead=truth_l)


def policy_selected(fi: FoldInputs, warehouse_cap, rng, n_scen=30, holdout=None) -> tuple[dict | None, dict]:
    """Choose among a competent order-up-to heuristic, the point-forecast
    optimizer and the stochastic optimizer by backtesting ALL THREE on the
    operator's own trailing history, then run the winner. The heuristic is a
    candidate on purpose: where holding is cheap and demand is stable it can
    beat both optimizers, and a product that ships a worse answer than the
    spreadsheet it replaces has no business being deployed. This is the commercially honest mode: the stochastic model earns
    its keep when conditions bind and loses when they do not, and the
    operator's recent history is the only evidence of which regime they are
    in. The selection uses nothing after the origin."""
    h = holdout or max(4, fi.horizon // 2)
    if min(len(v) for v in fi.train_demand.values()) < h + 8:
        sched, meta = policy_stochastic_sp(fi, warehouse_cap, rng, n_scen)
        meta = dict(meta)
        meta["selected"] = "stochastic_sp (insufficient history)"
        return sched, meta
    inner, itruth = _inner_fold(fi, h)
    inner_cap = None if warehouse_cap is None else warehouse_cap
    costs = {}
    candidates = {
        "order_up_to": lambda f_: (policy_order_up_to(f_), {}),
        "deterministic_sp": lambda f_: policy_deterministic_sp(f_, inner_cap, rng),
        "stochastic_sp": lambda f_: policy_stochastic_sp(f_, inner_cap, rng, n_scen),
    }
    for name, fn in candidates.items():
        sched, _ = fn(inner)
        costs[name] = settle(sched, inner, itruth, inner_cap).total if sched is not None else float("inf")
    winner = min(costs, key=lambda k: costs[k])
    if winner == "order_up_to":
        sched, meta = policy_order_up_to(fi), {"status": "heuristic"}
    elif winner == "deterministic_sp":
        sched, meta = policy_deterministic_sp(fi, warehouse_cap, rng)
    else:
        sched, meta = policy_stochastic_sp(fi, warehouse_cap, rng, n_scen)
    meta = dict(meta)
    meta["selected"] = winner
    meta["selection_costs"] = costs
    return sched, meta


def run_policies(fi: FoldInputs, truth: FoldTruth, warehouse_cap, rng,
                 n_scen: int = 30, policies=POLICIES) -> dict:
    out: dict = {}
    for name in policies:
        meta: dict = {}
        if name == "deterministic_sp":
            sched, meta = policy_deterministic_sp(fi, warehouse_cap, rng)
        elif name == "stochastic_sp":
            sched, meta = policy_stochastic_sp(fi, warehouse_cap, rng, n_scen)
        elif name == "selected":
            sched, meta = policy_selected(fi, warehouse_cap, rng, n_scen)
        else:
            sched = globals()[f"policy_{name}"](fi)
        if sched is None:
            out[name] = {"status": meta.get("status", "error"), "settlement": None}
            continue
        s = settle(sched, fi, truth, warehouse_cap)
        out[name] = {"status": meta.get("status", "heuristic"), "settlement": s,
                     "total_ordered": float(sum(sched.values())),
                     "runtime_s": meta.get("runtime_s", 0.0),
                     "selected": meta.get("selected")}
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


# ── closed-loop rolling evaluation ───────────────────────────────────────────
# Open-loop settlement of a single H-period schedule has an end effect: an
# order that lands after the horizon is free and stock left at the end is
# uncredited, so a policy that orders late and ends lean looks cheap. The
# operator does not live in a 12-week box; they re-plan every review cycle.
# This evaluator does the same for EVERY policy: at each review point it
# rebuilds the inputs from the state the policy itself produced, takes the
# first ``review`` periods of the new schedule, executes them against the
# realised path, and rolls forward. Costs accumulate over the whole run and
# the end effect shrinks to one review cycle in ``n_periods``.

@dataclass
class RollingResult:
    total: float
    holding: float
    shortage: float
    disposal: float
    sla_penalty: float
    fill_rate: float
    avg_inventory: float
    periods: int
    solver_failures: int = 0
    selections: dict = field(default_factory=dict)


def rolling_evaluate(policy_name: str, make_inputs, truth_demand: dict, truth_fill: dict,
                     truth_lead: dict, products: list, supplier_of: dict, lead_of: dict,
                     unit_cost: dict, margin: dict, policy: DomainPolicy,
                     n_periods: int, review: int, horizon: int, warehouse_cap,
                     rng, opening: dict, n_scen: int = 30) -> RollingResult:
    """``make_inputs(t, on_hand, pipeline)`` must return a FoldInputs built
    from history strictly before absolute period ``t``."""
    cc = policy.cost_config
    carry = float(cc.holding_rate_per_period)
    decay = float(policy.decay_rate_per_period)
    on_hand = dict(opening)
    arrivals: dict = {}          # (product, abs_t) -> qty in transit
    holding = shortage = disposal = sla = 0.0
    served = demanded = inv_sum = 0.0
    failures = 0
    selections: dict = {}
    t = 0
    while t < n_periods:
        pipeline = {(j, tt - t): q for (j, tt), q in arrivals.items() if tt >= t and tt - t < horizon}
        fi = make_inputs(t, dict(on_hand), pipeline)
        if policy_name == "deterministic_sp":
            sched, meta = policy_deterministic_sp(fi, warehouse_cap, rng)
        elif policy_name == "stochastic_sp":
            sched, meta = policy_stochastic_sp(fi, warehouse_cap, rng, n_scen)
        elif policy_name == "selected":
            sched, meta = policy_selected(fi, warehouse_cap, rng, n_scen)
            selections[meta.get("selected", "?")] = selections.get(meta.get("selected", "?"), 0) + 1
        else:
            sched, meta = globals()[f"policy_{policy_name}"](fi), {}
        if sched is None:
            failures += 1
            sched = policy_order_up_to(fi)      # safe fallback, counted
        # execute only the first `review` periods of the schedule
        for (sup, sku, rel_t), q in sched.items():
            if rel_t >= review or q <= 0:
                continue
            q = min(float(q), float(fi.capacity.get(sku, q)))   # same cap as settle()
            abs_t = t + rel_t
            lag = int(truth_lead.get((sup, abs_t), lead_of.get(sup, 1)))
            f = float(truth_fill.get((sup, abs_t), 1.0))
            key = (sku, abs_t + lag)
            arrivals[key] = arrivals.get(key, 0.0) + q * f
        for step in range(review):
            at = t + step
            if at >= n_periods:
                break
            pending, stock_total = {}, 0.0
            for j in products:
                d = float(truth_demand.get((j, at), 0.0))
                have = on_hand.get(j, 0.0) + arrivals.pop((j, at), 0.0)
                got = min(have, d)
                short = max(d - have, 0.0)
                shortage += short * margin[j]
                if cc.sla_fill_target is not None and d > 0 and (1 - short / d) < cc.sla_fill_target:
                    sla += short * unit_cost[j] * cc.sla_penalty_rate
                left = max(have - d, 0.0)
                if decay > 0:
                    lost = left * decay
                    disposal += lost * float(cc.waste_cost_per_unit.get(j, unit_cost[j]))
                    left -= lost
                pending[j] = left
                stock_total += left
                served += got
                demanded += d
            if warehouse_cap is not None and stock_total > warehouse_cap > 0:
                scale = warehouse_cap / stock_total
                for j in pending:
                    disposal += pending[j] * (1 - scale) * unit_cost[j]
                    pending[j] *= scale
            for j, left in pending.items():
                holding += left * unit_cost[j] * carry
                on_hand[j] = left
                inv_sum += left
        t += review
    total = holding + shortage + disposal + sla
    return RollingResult(total=total, holding=holding, shortage=shortage, disposal=disposal,
                         sla_penalty=sla, fill_rate=served / demanded if demanded else 1.0,
                         avg_inventory=inv_sum / max(n_periods, 1), periods=n_periods,
                         solver_failures=failures, selections=selections)
