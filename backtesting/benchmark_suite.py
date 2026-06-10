"""Benchmark suite: the optimizer against the policies it must beat.

Rolling-origin head-to-head on the operator's staged history, scored with
clean incremental recourse economics (no procurement double-count):

    overage  (committed beyond demand)  → unit cost per kg
    spot     (shortfall covered, ≤ ρ·d) → unit cost × (multiplier − 1)
    unmet    (shortfall beyond spot)    → lost margin per kg

Policies:
    two_sided_sp      newsvendor SP, demand replay scenarios × per-scenario
                      supplier yield draws (fit on the training window only)
    deterministic_lp  newsvendor LP on mean training demand
    order_up_to       S = trailing μ + z·σ (z from the service quantile) —
                      the heuristic operators actually use
    naive_runrate     trailing 4-week weekly run-rate

GATE (Phase 4): the SP must beat BOTH the deterministic LP and the naive
out-of-sample under honest penalties — and this module reports the
unflattering verdict in plain words when it does not.

Honest limitations, stated not hidden:
- scoring is product-level against realized demand; realized supplier
  fills are not replayed into the score (all policies are scored the same
  way, so the comparison is fair, but absolute costs are approximate)
- every result on synthetic data is synthetic; "validated" requires a
  real operator's history
- the SP-vs-LP edge is sensitive to spot economics; run the spot grid
  before believing a single number
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as _st


# ── Data access ──────────────────────────────────────────────────────────────

def _weekly_demand(conn) -> pd.DataFrame:
    df = conn.execute("""
        SELECT product_name AS product_id,
               DATE_TRUNC('week', COALESCE(delivery_date, order_date)) AS week_start,
               SUM(requested_quantity) AS demand_kg
        FROM stg_buyer_orders
        WHERE product_name IS NOT NULL AND requested_quantity IS NOT NULL
          AND COALESCE(delivery_date, order_date) IS NOT NULL
        GROUP BY 1, 2
    """).df()
    if not df.empty:
        df["week_start"] = pd.to_datetime(df["week_start"])
    return df


def _deliveries(conn) -> pd.DataFrame:
    df = conn.execute("""
        SELECT supplier_id,
               COALESCE(supplier_name, supplier_id) AS supplier_name,
               product_name AS product_id,
               DATE_TRUNC('week', delivery_date) AS week_start,
               ordered_quantity AS ordered,
               COALESCE(accepted_quantity, delivered_quantity) AS accepted,
               unit_cost
        FROM stg_supplier_deliveries
        WHERE product_name IS NOT NULL AND delivery_date IS NOT NULL
    """).df()
    if not df.empty:
        df["week_start"] = pd.to_datetime(df["week_start"])
    return df


def _economics(conn) -> dict[str, dict[str, float]]:
    """Per-product avg cost / sell / margin from staging."""
    from risk.scenario_generation import honest_penalties_from_staging
    cw, cu = honest_penalties_from_staging(conn)
    return {j: {"cost": cw.get(j, 2.0), "margin": cu.get(j, 0.5)}
            for j in set(cw) | set(cu)}


# ── Clean recourse scoring (shared by every policy) ──────────────────────────

def score_commitment(
    committed: float, demand: float,
    cost: float, margin: float,
    spot_mult: float, spot_cap: float,
) -> tuple[float, float, float]:
    """(incremental cost, served kg, waste kg) for one product-week."""
    over = max(committed - demand, 0.0)
    under = max(demand - committed, 0.0)
    spot = min(under, spot_cap * demand)
    unmet = under - spot
    c = over * cost + spot * cost * (spot_mult - 1.0) + unmet * margin
    return c, min(committed, demand) + spot, over


# ── The benchmark ────────────────────────────────────────────────────────────

def run_benchmark(
    conn,
    n_folds: int = 8,
    train_weeks: int = 26,
    spot_cost_multiplier: float = 1.30,
    spot_capacity_factor: float = 0.30,
    n_yield_draws_seed: int = 42,
    service_level: float = 0.90,
) -> dict[str, Any]:
    """Rolling-origin benchmark of all policies on staged history."""
    demand = _weekly_demand(conn)
    deliveries = _deliveries(conn)
    econ = _economics(conn)
    if demand.empty or demand["week_start"].nunique() < train_weeks + n_folds:
        return {"status": "insufficient_history",
                "weeks_available": int(demand["week_start"].nunique())
                if not demand.empty else 0,
                "weeks_required": train_weeks + n_folds,
                "gate_passed": None}

    from optimization.lp_baseline import LPBaseline
    from optimization.order_up_to_policy import order_up_to_commitments
    from optimization.two_stage_sp import TwoStageStochasticLP
    from risk.supplier_distribution import (
        estimate_population, supplier_distribution,
    )

    weeks = sorted(demand["week_start"].unique())
    policies = ("two_sided_sp", "deterministic_lp", "order_up_to",
                "naive_runrate")
    per_fold: dict[str, list[dict]] = {p: [] for p in policies}
    rng = np.random.default_rng(n_yield_draws_seed)

    for k in range(n_folds):
        origin_idx = len(weeks) - n_folds + k
        if origin_idx < train_weeks:
            continue
        origin = weeks[origin_idx]
        train_wk = weeks[origin_idx - train_weeks: origin_idx]
        train = demand[demand["week_start"].isin(train_wk)]
        realized = (demand[demand["week_start"] == origin]
                    .groupby("product_id")["demand_kg"].sum().to_dict())
        if not realized:
            continue

        # demand replay scenarios from the training window
        scen = train.rename(columns={"demand_kg": "demand_kg"}).copy()
        widx = {w: i for i, w in enumerate(train_wk)}
        scen["scenario_index"] = scen["week_start"].map(widx)
        scen["scenario_weight"] = 1.0 / len(train_wk)
        scen = scen[["scenario_index", "scenario_weight", "product_id",
                     "week_start", "demand_kg"]]

        # training-window supplier stats → yield draws (leakage-safe)
        tdel = deliveries[deliveries["week_start"].isin(train_wk)].copy()
        tdel = tdel[tdel["ordered"].fillna(0) > 0]
        tdel["fill_rate"] = (tdel["accepted"].fillna(0).astype(float)
                             / tdel["ordered"].astype(float)).clip(0, 1)
        pop = estimate_population(tdel[["supplier_id", "fill_rate"]]
                                  .assign(supplier_name=""))
        yields: dict = {}
        for sid, g in tdel.groupby("supplier_id"):
            n = len(g)
            m_s = float(g["fill_rate"].mean())
            v_s = float(g["fill_rate"].var(ddof=0)) if n >= 2 else None
            dd = supplier_distribution(n, m_s, v_s, pop, 0.10)
            draws = _st.beta.rvs(dd["alpha"], dd["beta"],
                                 size=len(train_wk), random_state=rng)
            for omega in range(len(train_wk)):
                yields[(omega, sid)] = float(np.clip(draws[omega], 0, 1))

        # supply capacity from the training window (full typical order)
        cap = (tdel.groupby(["supplier_id", "product_id"])
               .agg(capacity_kg=("ordered", "mean"),
                    price_per_kg=("unit_cost", "mean")).reset_index())
        cap["week_start"] = None
        cap["price_per_kg"] = cap["price_per_kg"].fillna(2.0)
        if cap.empty:
            continue

        cw = {j: e["cost"] for j, e in econ.items()}
        cu = {j: e["margin"] for j, e in econ.items()}

        commits: dict[str, dict[str, float]] = {}

        sp_res = TwoStageStochasticLP(
            newsvendor_objective=True, waste_cost_by_product=cw,
            unmet_cost_by_product=cu,
            spot_cost_multiplier=spot_cost_multiplier,
            spot_capacity_factor=spot_capacity_factor,
            n_scenarios=len(train_wk),
        ).solve(scen, cap, yield_scenarios=yields)
        c: dict[str, float] = {}
        for (i, j), v in sp_res["x"].items():
            if v:
                c[j] = c.get(j, 0.0) + float(v)
        commits["two_sided_sp"] = c

        meandem = (train.groupby("product_id")["demand_kg"].mean()
                   .reset_index().rename(columns={"demand_kg": "demand_kg"}))
        meandem["week_start"] = origin
        # LPBaseline keys capacity by (supplier, product, week): align the
        # capacity rows to the planning week or the LP can commit nothing.
        lp_cap = cap.assign(week_start=origin)
        lp_res = LPBaseline(
            newsvendor_objective=True, waste_cost_by_product=cw,
            unmet_cost_by_product=cu,
            spot_cost_multiplier=spot_cost_multiplier,
            spot_capacity_factor=spot_capacity_factor,
        ).solve(meandem, lp_cap)
        c = {}
        for (i, j, t), v in lp_res["x"].items():
            if v:
                c[j] = c.get(j, 0.0) + float(v)
        commits["deterministic_lp"] = c

        commits["order_up_to"] = order_up_to_commitments(
            train, service_level=service_level)
        runrate = (train[train["week_start"].isin(train_wk[-4:])]
                   .groupby("product_id")["demand_kg"].sum() / 4.0).to_dict()
        commits["naive_runrate"] = runrate

        for pol in policies:
            tot_cost = served = dem_tot = waste = 0.0
            for j, d_real in realized.items():
                e = econ.get(j, {"cost": 2.0, "margin": 0.5})
                cst, sv, ov = score_commitment(
                    commits[pol].get(j, 0.0), float(d_real),
                    e["cost"], e["margin"],
                    spot_cost_multiplier, spot_capacity_factor)
                tot_cost += cst
                served += sv
                dem_tot += float(d_real)
                waste += ov
            per_fold[pol].append({
                "origin": str(pd.Timestamp(origin).date()),
                "cost": tot_cost, "served": served,
                "demand": dem_tot, "waste": waste,
            })

    if not per_fold["two_sided_sp"]:
        return {"status": "insufficient_history", "gate_passed": None}

    table = {}
    for pol in policies:
        rows = per_fold[pol]
        a = np.array([[r["cost"], r["served"], r["demand"], r["waste"]]
                      for r in rows], dtype=float)
        table[pol] = {
            "cost_per_origin": round(float(a[:, 0].mean()), 0),
            "service_pct": round(float(a[:, 1].sum() / a[:, 2].sum() * 100), 1)
            if a[:, 2].sum() else None,
            "waste_kg_per_origin": round(float(a[:, 3].mean()), 0),
            "n_folds": len(rows),
        }

    sp_c = np.array([r["cost"] for r in per_fold["two_sided_sp"]])
    lp_c = np.array([r["cost"] for r in per_fold["deterministic_lp"]])
    nv_c = np.array([r["cost"] for r in per_fold["naive_runrate"]])
    ss_c = np.array([r["cost"] for r in per_fold["order_up_to"]])

    def _edge(base: np.ndarray) -> dict:
        diff = base - sp_c
        return {
            "edge_pct": round(float((base.sum() - sp_c.sum())
                                    / base.sum() * 100), 2)
            if base.sum() else None,
            "wins": int((diff > 0).sum()),
            "n": len(diff),
            "paired_t": round(float(diff.mean()
                                    / (diff.std(ddof=1)
                                       / np.sqrt(len(diff)) + 1e-12)), 2)
            if len(diff) >= 2 else None,
        }

    vs_lp = _edge(lp_c)
    vs_naive = _edge(nv_c)
    vs_sS = _edge(ss_c)
    beats_lp = (vs_lp["edge_pct"] or 0) > 0
    beats_naive = (vs_naive["edge_pct"] or 0) > 0
    gate = bool(beats_lp and beats_naive)

    return {
        "status": "ok",
        "policies": table,
        "sp_vs_deterministic_lp": vs_lp,
        "sp_vs_naive": vs_naive,
        "sp_vs_order_up_to": vs_sS,
        "gate_passed": gate,
        "verdict": (
            "stochastic SP beats both the deterministic LP and the naive "
            "baseline out-of-sample under honest penalties"
            if gate else
            "HONEST VERDICT: the stochastic SP does NOT beat the simple "
            "baselines on this data — the deterministic LP (or the "
            "order-up-to heuristic) is the honest planning recommendation "
            "here; do not ship the stochastic layer as if it added value"
        ),
        "spot_economics": {
            "spot_cost_multiplier": spot_cost_multiplier,
            "spot_capacity_factor": spot_capacity_factor,
            "note": "the SP edge is sensitive to these; sweep before "
                    "believing one number",
        },
        "scoring": "product-level clean incremental recourse (overage at "
                   "cost, spot at premium, unmet at margin); identical for "
                   "every policy",
        "data_basis": "operator staging history; synthetic if the staged "
                      "data is synthetic",
    }


# ── SAA optimality gap ───────────────────────────────────────────────────────

def saa_optimality_gap(
    conn,
    n_batches: int = 5,
    batch_size: int = 40,
    n_eval_scenarios: int = 400,
    spot_cost_multiplier: float = 1.30,
    spot_capacity_factor: float = 0.30,
    seed: int = 42,
) -> dict[str, Any]:
    """Standard SAA gap estimate for the two-sided newsvendor SP.

    Lower bound: mean optimal objective over ``n_batches`` independent
    scenario batches (each batch's optimum is optimistic, their mean is a
    statistical lower bound on the true optimum).
    Upper bound: the candidate plan from the first batch, evaluated on a
    large fresh scenario set (stage-2 cost is closed-form under the
    newsvendor recourse, so no LP per scenario is needed).
    gap = UB − LB with a t-interval on the batch spread. A small gap means
    the scenario count is adequate; a large one means add scenarios.
    """
    from risk.scenario_generation import (
        demand_scenarios_from_forecast,
        honest_penalties_from_staging,
        supply_capacity_full,
        yield_scenarios_from_distributions,
    )
    from optimization.two_stage_sp import TwoStageStochasticLP

    supply = supply_capacity_full(conn)
    cw, cu = honest_penalties_from_staging(conn)
    if supply.empty:
        return {"status": "no_data"}

    batch_objs: list[float] = []
    candidate_x: dict | None = None
    products: list[str] = []

    for b in range(n_batches):
        scen = demand_scenarios_from_forecast(
            conn, n_scenarios=batch_size, seed=seed + b)
        if scen.empty:
            return {"status": "no_data"}
        ids = sorted(scen["scenario_index"].unique())
        yields = yield_scenarios_from_distributions(conn, ids, seed=seed + b)
        res = TwoStageStochasticLP(
            newsvendor_objective=True, waste_cost_by_product=cw,
            unmet_cost_by_product=cu,
            spot_cost_multiplier=spot_cost_multiplier,
            spot_capacity_factor=spot_capacity_factor,
            n_scenarios=batch_size,
        ).solve(scen, supply, yield_scenarios=yields)
        if res["objective"] is None:
            return {"status": "solver_failed", "batch": b}
        batch_objs.append(float(res["objective"]))
        if candidate_x is None:
            candidate_x = {k: float(v or 0.0) for k, v in res["x"].items()}
            products = sorted(scen["product_id"].unique())

    lb = float(np.mean(batch_objs))
    lb_se = float(np.std(batch_objs, ddof=1) / np.sqrt(n_batches)) \
        if n_batches >= 2 else 0.0

    # Evaluate the candidate on a large fresh set (closed-form stage 2).
    eval_scen = demand_scenarios_from_forecast(
        conn, n_scenarios=n_eval_scenarios, seed=seed + 777)
    ids = sorted(eval_scen["scenario_index"].unique())
    eval_yields = yield_scenarios_from_distributions(conn, ids,
                                                     seed=seed + 777)
    committed_x = candidate_x or {}
    avg_price = supply.groupby("product_id")["price_per_kg"].mean().to_dict()

    costs = []
    for omega, g in eval_scen.groupby("scenario_index"):
        total = 0.0
        delivered: dict[str, float] = {}
        for (i, j), v in committed_x.items():
            if v > 0:
                delivered[j] = delivered.get(j, 0.0) + \
                    eval_yields.get((omega, i), 1.0) * v
        for _, r in g.iterrows():
            j = r["product_id"]
            d_ = float(r["demand_kg"])
            dl = delivered.get(j, 0.0)
            over = max(dl - d_, 0.0)
            under = max(d_ - dl, 0.0)
            spot = min(under, spot_capacity_factor * d_)
            unmet = under - spot
            pj = float(avg_price.get(j, 2.0))
            total += (over * cw.get(j, 0.5)
                      + spot * pj * (spot_cost_multiplier - 1.0)
                      + unmet * cu.get(j, 2.5))
        costs.append(total)
    ub = float(np.mean(costs))
    ub_se = float(np.std(costs, ddof=1) / np.sqrt(len(costs)))

    gap = ub - lb
    denom = abs(ub) if ub else 1.0
    return {
        "status": "ok",
        "lower_bound": round(lb, 2),
        "lower_bound_se": round(lb_se, 2),
        "upper_bound": round(ub, 2),
        "upper_bound_se": round(ub_se, 2),
        "gap": round(gap, 2),
        "gap_pct_of_ub": round(gap / denom * 100, 2),
        "n_batches": n_batches,
        "batch_size": batch_size,
        "n_eval_scenarios": n_eval_scenarios,
        "interpretation": "gap ≲ a few % of the objective means the "
                          "scenario count is adequate; larger means add "
                          "scenarios before trusting the plan",
    }
