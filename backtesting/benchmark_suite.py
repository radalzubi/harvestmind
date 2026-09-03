"""Benchmark suite: the optimizer against the policies it must beat.

Rolling-origin head-to-head on the operator's staged history, scored with
clean incremental recourse economics (no procurement double-count):

    overage  (committed beyond demand)  → unit cost per kg
    spot     (shortfall covered, ≤ ρ·d) → unit cost × (multiplier − 1)
    unmet    (shortfall beyond spot)    → lost margin per kg

Policies:
    two_sided_sp      newsvendor SP, demand replay scenarios × per-scenario
                      supplier yield draws (fit on the training window
                      only). Yields are drawn INDEPENDENTLY per supplier
                      here: this harness exercises marginal yield
                      uncertainty, not the correlated-shortfall model in
                      risk/correlated_scenarios.py
    deterministic_lp  newsvendor LP on mean training demand
    order_up_to       S = trailing μ + z·σ (z from the service quantile) —
                      the heuristic operators actually use
    naive_runrate     trailing 4-week weekly run-rate

GATE (Phase 4): the SP must beat BOTH the deterministic LP and the naive
out-of-sample under honest penalties — and this module reports the
unflattering verdict in plain words when it does not.

Honest limitations, stated not hidden:
- supplier-blind policies are allocated pro rata by training-window volume;
  that construction is applied identically but remains an assumption
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

POOL_SUPPLIER = "__pool__"


def score_commitment(
    committed: float, demand: float,
    cost: float, margin: float,
    spot_mult: float, spot_cap: float,
) -> tuple[float, float, float]:
    """(incremental cost, served kg, waste kg) for one product-week.

    ``committed`` here is DELIVERED quantity, not ordered quantity. Callers
    must apply supplier fill rates before this point; ``settle`` does.
    """
    over = max(committed - demand, 0.0)
    under = max(demand - committed, 0.0)
    spot = min(under, spot_cap * demand)
    unmet = under - spot
    c = over * cost + spot * cost * (spot_mult - 1.0) + unmet * margin
    return c, min(committed, demand) + spot, over


def atp_commitments(
    mean_demand: dict[str, float],
    shares: dict[str, dict[str, float]],
    supplier_fill: dict[str, float],
    fill_quantile: dict[str, float] | None = None,
    capacity: dict[tuple[str, str], float] | None = None,
) -> dict[tuple[str, str], float]:
    """Order-to-forecast, grossed up for expected supplier shortfall.

    The incumbent-style rule this product must beat. A competent planner
    does not order exactly the demand they forecast: they know a supplier
    filling 90% means ordering 1/0.90 of what they need. This encodes that
    reasoning WITHOUT any distributional optimization.

    ``fill_quantile`` switches it from mean-based (deterministic ATP) to a
    conservative haircut (safety-buffer ATP). Beating deterministic ATP is
    a weak result; beating the buffered version is the real test, because
    a haircut rule is what a good buyer already does in their head.
    """
    alloc: dict[tuple[str, str], float] = {}
    basis = fill_quantile if fill_quantile is not None else supplier_fill
    cap = capacity or {}
    for j, need in mean_demand.items():
        q = float(need)
        if q <= 0:
            continue
        sh = shares.get(str(j))
        if not sh:
            f = max(_safe_mean(basis.values()), 0.05)
            want = q / f
            lim = cap.get((POOL_SUPPLIER, str(j)))
            alloc[(POOL_SUPPLIER, str(j))] = min(want, lim) if lim else want
            continue
        tot = sum(sh.values())
        for i, w in sh.items():
            f = max(float(basis.get(str(i), _safe_mean(basis.values()) or 1.0)), 0.05)
            want = (q * w / tot) / f
            # Cap at what the supplier can actually supply. Without this the
            # heuristic orders volume no supplier could provide and is then
            # credited with delivering it, which is the same class of defect
            # as scoring committed quantity as delivered quantity.
            lim = cap.get((str(i), str(j)))
            if lim is not None:
                want = min(want, float(lim))
            alloc[(str(i), str(j))] = alloc.get((str(i), str(j)), 0.0) + want
    return alloc


def _safe_mean(vals) -> float:
    v = [float(x) for x in vals if x is not None]
    return float(np.mean(v)) if v else 1.0


def supplier_volume_shares(tdel: pd.DataFrame) -> dict[str, dict[str, float]]:
    """{product: {supplier: share}} from TRAINING-window delivered volume.

    The allocation rule for policies that do not choose suppliers
    themselves. Order-up-to and run-rate emit a product quantity only, so
    to settle them against supplier fill rates we must decide who would
    have supplied it. Splitting by each supplier's historical share of that
    product is the neutral choice, and it is applied identically to every
    supplier-blind policy so none is advantaged.

    This is a modelling assumption, not an observation. It is stated here
    rather than buried because it materially affects those policies'
    scores.
    """
    out: dict[str, dict[str, float]] = {}
    if tdel.empty:
        return out
    vol = (tdel.groupby(["product_id", "supplier_id"])["accepted"]
           .sum().reset_index())
    for j, g in vol.groupby("product_id"):
        total = float(g["accepted"].sum())
        if total <= 0:
            continue
        out[str(j)] = {str(r.supplier_id): float(r.accepted) / total
                       for r in g.itertuples() if float(r.accepted) > 0}
    return out


def allocate_to_suppliers(
    product_totals: dict[str, float],
    shares: dict[str, dict[str, float]],
) -> dict[tuple[str, str], float]:
    """Split product-level commitments across suppliers pro rata.

    Conservation is guaranteed: the allocated quantities for a product sum
    to the product total. A product with no training-window supplier
    history is allocated to POOL_SUPPLIER rather than dropped, so no
    quantity silently disappears from a policy's commitment.
    """
    alloc: dict[tuple[str, str], float] = {}
    for j, qty in product_totals.items():
        q = float(qty)
        if q <= 0:
            continue
        sh = shares.get(str(j))
        if not sh:
            alloc[(POOL_SUPPLIER, str(j))] = alloc.get(
                (POOL_SUPPLIER, str(j)), 0.0) + q
            continue
        tot = sum(sh.values())
        for i, w in sh.items():
            alloc[(i, str(j))] = alloc.get((i, str(j)), 0.0) + q * (w / tot)
    return alloc


def realized_fills(
    deliveries: pd.DataFrame, week, fallback: dict[str, float],
    pool_fallback: float,
) -> dict[str, float]:
    """Supplier fill rates ACTUALLY observed in the held-out week.

    This is realized outcome, not lookahead: it settles a decision already
    made, and is never visible to any policy at decision time. Suppliers
    with no delivery that week fall back to their TRAINING-window mean, so
    the fallback itself carries no held-out information.
    """
    fills = dict(fallback)
    fills[POOL_SUPPLIER] = pool_fallback
    if deliveries.empty:
        return fills
    wk = deliveries[deliveries["week_start"] == week]
    wk = wk[wk["ordered"].fillna(0) > 0]
    if wk.empty:
        return fills
    g = wk.groupby("supplier_id").agg(
        ordered=("ordered", "sum"), accepted=("accepted", "sum"))
    for sid, r in g.iterrows():
        o = float(r["ordered"])
        if o > 0:
            fills[str(sid)] = float(np.clip(float(r["accepted"]) / o, 0.0, 1.0))
    return fills


def settle(
    alloc: dict[tuple[str, str], float],
    realized: dict[str, float],
    fills: dict[str, float],
    econ: dict[str, dict[str, float]],
    spot_mult: float, spot_cap: float,
    default_fill: float = 1.0,
) -> tuple[float, float, float, float]:
    """The single settlement path for every policy.

    Applies supplier fill rates to that policy's own supplier allocation,
    then scores the DELIVERED quantity through identical recourse
    economics. Returns (cost, served, waste, delivered).

    Every policy routes through here, so the only thing that differs
    between policies is the allocation they chose.
    """
    delivered: dict[str, float] = {}
    for (i, j), kg in alloc.items():
        f = fills.get(str(i), default_fill)
        delivered[str(j)] = delivered.get(str(j), 0.0) + float(kg) * float(f)

    # Iterate the UNION of demanded and delivered products. Iterating only
    # realized demand let a commitment to a product with zero demand that
    # week escape scoring entirely: the stock arrived, sold nothing, and
    # was charged no waste. Harmless where every product sells every week,
    # but silently forgiving on intermittent real data, which is exactly
    # where a planner most needs to be held to account.
    tot_cost = served = waste = deliv_tot = 0.0
    # Include products with commitments but zero realized demand. Iterating
    # only ``realized`` made overage disappear whenever a product-week was
    # explicitly zero, so a commitment to a product that sold nothing
    # arrived, sold nothing, and was charged no waste. Both branches found
    # this independently; sorted() keeps fold ordering deterministic.
    products = set(map(str, realized)) | set(delivered)
    for j in sorted(products):
        e = econ.get(j, {"cost": 2.0, "margin": 0.5})
        d_real = float(realized.get(j, 0.0))
        dj = delivered.get(str(j), 0.0)
        cst, sv, ov = score_commitment(
            dj, d_real, e["cost"], e["margin"], spot_mult, spot_cap)
        tot_cost += cst
        served += sv
        waste += ov
        deliv_tot += dj
    return tot_cost, served, waste, deliv_tot


# ── The benchmark ────────────────────────────────────────────────────────────

def run_benchmark(
    conn,
    n_folds: int = 8,
    train_weeks: int = 26,
    spot_cost_multiplier: float = 1.30,
    spot_capacity_factor: float = 0.30,
    n_yield_draws_seed: int = 42,
    service_level: float = 0.90,
    force_unit_fills: bool = False,
    supply_risk_policy: Any | None = None,
    underage_overage_ratio: float | None = None,
    capacity_headroom: float = 1.0,
    capacity_basis: str = "mean_ordered",
) -> dict[str, Any]:
    """Rolling-origin benchmark of all policies on staged history.

    ``force_unit_fills`` pins every supplier fill to 1.0. It exists for the
    regression test that proves the fill-replay refactor changed only what
    it was meant to: with delivery perfect, settlement must reproduce the
    old commitment-equals-delivery scoring exactly.
    """
    demand = _weekly_demand(conn)
    deliveries = _deliveries(conn)
    econ = _economics(conn)
    if underage_overage_ratio is not None:
        if underage_overage_ratio <= 0:
            raise ValueError("underage_overage_ratio must be positive")
        econ = {
            j: {**e, "margin": float(e["cost"]) * underage_overage_ratio}
            for j, e in econ.items()
        }
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
                "naive_runrate", "forecast_routed",
                "deterministic_atp", "safety_buffer_atp",
                "mean_value_sp")
    per_fold: dict[str, list[dict]] = {p: [] for p in policies}
    rng = np.random.default_rng(n_yield_draws_seed)
    route_counts = {"croston": 0, "lgbm": 0}
    correlation_diagnostics: dict[str, Any] = {
        "policy_mode": "independent",
        "correlation_source": "independent_by_policy",
    }

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
        beta_params: dict[str, tuple[float, float]] = {}
        for sid, g in tdel.groupby("supplier_id"):
            n = len(g)
            m_s = float(g["fill_rate"].mean())
            v_s = float(g["fill_rate"].var(ddof=0)) if n >= 2 else None
            dd = supplier_distribution(n, m_s, v_s, pop, 0.10)
            beta_params[str(sid)] = (float(dd["alpha"]), float(dd["beta"]))

        yields: dict = {}
        if supply_risk_policy is not None and supply_risk_policy.enabled:
            from risk.correlated_scenarios import (
                CopulaScenarioGenerator, equicorrelation_matrix,
                kendall_to_latent,
            )
            if supply_risk_policy.mode != "equicorrelated":
                raise ValueError(
                    "rolling benchmark supports an explicit "
                    "equicorrelated policy; estimated mode would read "
                    "outside the fold's training window")
            latent = float(kendall_to_latent(
                float(supply_risk_policy.kendall_tau)))
            generator = CopulaScenarioGenerator(
                copula=supply_risk_policy.copula,
                df=supply_risk_policy.df,
                seed=supply_risk_policy.seed + k,
            )
            sampled = generator.sample_beta_marginals(
                beta_params, len(train_wk),
                correlation=equicorrelation_matrix(len(beta_params), latent),
            )
            for sid, draws in sampled.items():
                for omega, value in enumerate(draws):
                    yields[(omega, sid)] = float(value)
            correlation_diagnostics = {
                "policy_mode": supply_risk_policy.mode,
                "correlation_source": "operator_supplied_tau",
                "copula": supply_risk_policy.copula,
                "target_kendall_tau": float(supply_risk_policy.kendall_tau),
                "mean_latent_correlation": round(latent, 4),
                "training_window_only": True,
            }
        else:
            for sid, (alpha, beta) in beta_params.items():
                draws = _st.beta.rvs(alpha, beta, size=len(train_wk),
                                     random_state=rng)
                for omega in range(len(train_wk)):
                    yields[(omega, sid)] = float(np.clip(draws[omega], 0, 1))

        # Supply capacity from the training window.
        #
        # NOTE: the mean of what was ORDERED is not what a supplier could
        # SUPPLY. Using it as a hard ceiling makes capacity bind for every
        # fill-aware policy, which collapses them onto identical
        # commitments and leaves the benchmark unable to distinguish
        # stochastic from deterministic planning at all.
        # `capacity_headroom` scales the ceiling; 1.0 reproduces the old
        # behaviour exactly.
        _cap_agg = {"mean_ordered": "mean", "max_ordered": "max",
                    "p90_ordered": (lambda x: float(np.quantile(x, 0.90)))}
        if capacity_basis not in _cap_agg:
            raise ValueError(
                f"unknown capacity_basis {capacity_basis!r}; use one of "
                f"{sorted(_cap_agg)}")
        cap = (tdel.groupby(["supplier_id", "product_id"])
               .agg(capacity_kg=("ordered", _cap_agg[capacity_basis]),
                    price_per_kg=("unit_cost", "mean")).reset_index())
        cap["capacity_kg"] = cap["capacity_kg"] * float(capacity_headroom)
        cap["week_start"] = None
        cap["price_per_kg"] = cap["price_per_kg"].fillna(2.0)
        if cap.empty:
            continue

        cw = {j: e["cost"] for j, e in econ.items()}
        cu = {j: e["margin"] for j, e in econ.items()}

        commits: dict[str, dict] = {}

        sp_res = TwoStageStochasticLP(
            newsvendor_objective=True, waste_cost_by_product=cw,
            unmet_cost_by_product=cu,
            spot_cost_multiplier=spot_cost_multiplier,
            spot_capacity_factor=spot_capacity_factor,
            n_scenarios=len(train_wk),
        ).solve(scen, cap, yield_scenarios=yields)
        c: dict[tuple[str, str], float] = {}
        for (i, j), v in sp_res["x"].items():
            if v:
                c[(str(i), str(j))] = c.get((str(i), str(j)), 0.0) + float(v)
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
                c[(str(i), str(j))] = c.get((str(i), str(j)), 0.0) + float(v)
        commits["deterministic_lp"] = c

        # Supplier-blind policies emit product quantities only. Split them
        # across suppliers by training-window volume share, identically for
        # both, so neither is advantaged by the settlement change.
        shares = supplier_volume_shares(tdel)
        commits["order_up_to"] = allocate_to_suppliers(
            order_up_to_commitments(train, service_level=service_level),
            shares)
        runrate = (train[train["week_start"].isin(train_wk[-4:])]
                   .groupby("product_id")["demand_kg"].sum() / 4.0).to_dict()
        commits["naive_runrate"] = allocate_to_suppliers(runrate, shares)

        # Incumbent-style ATP ladder. Each adds exactly one thing over the
        # last, so a win can be attributed: LP adds cost optimization, ATP
        # adds fill awareness, buffered ATP adds conservatism, the SP adds
        # the full distribution. Beating buffered ATP is the real test.
        mean_dem = (train.groupby("product_id")["demand_kg"].mean().to_dict())
        if not tdel.empty:
            fill_mean = {str(k): float(v) for k, v in
                         tdel.groupby("supplier_id")["fill_rate"].mean().items()}
            fill_low = {str(k): float(v) for k, v in
                        tdel.groupby("supplier_id")["fill_rate"]
                        .quantile(0.10).items()}
        else:
            fill_mean, fill_low = {}, {}
        cap_lookup = {(str(r.supplier_id), str(r.product_id)):
                      float(r.capacity_kg) for r in cap.itertuples()}
        commits["deterministic_atp"] = atp_commitments(
            mean_dem, shares, fill_mean, capacity=cap_lookup)
        commits["safety_buffer_atp"] = atp_commitments(
            mean_dem, shares, fill_mean, fill_quantile=fill_low,
            capacity=cap_lookup)

        # THE baseline that matters: a fill-aware DETERMINISTIC optimizer,
        # identical to the SP in every respect except that it sees a point
        # estimate of supplier fill instead of a distribution. Same solver,
        # same capacity constraints, same recourse economics, same training
        # information, same settlement path.
        #
        # This is the mean-value problem of the SP, so SP-versus-this is a
        # true value of the stochastic solution rather than a comparison
        # against a differently-specified model. If the SP cannot beat it,
        # the distribution is not what creates the value.
        mv_scen = pd.DataFrame([
            {"scenario_index": 0, "scenario_weight": 1.0, "product_id": j,
             "week_start": origin, "demand_kg": float(d)}
            for j, d in mean_dem.items()])
        mv_yields = {(0, str(sid)): float(f) for sid, f in fill_mean.items()}
        mv_res = TwoStageStochasticLP(
            newsvendor_objective=True, waste_cost_by_product=cw,
            unmet_cost_by_product=cu,
            spot_cost_multiplier=spot_cost_multiplier,
            spot_capacity_factor=spot_capacity_factor,
            n_scenarios=1,
        ).solve(mv_scen, cap, yield_scenarios=mv_yields)
        c = {}
        for (i, j), v in (mv_res.get("x") or {}).items():
            if v:
                c[(str(i), str(j))] = c.get((str(i), str(j)), 0.0) + float(v)
        commits["mean_value_sp"] = c

        # Exercise the production demand router in intermittent cells. This
        # baseline uses Croston-family forecasts for sparse products and a
        # trailing run-rate for dense ones; it is diagnostic and does not
        # change the commercial gate definition.
        from forecasting.demand.demand_forecast_service import classify_products
        from forecasting.demand.intermittent_model import select_and_fit
        routing_frame = train.rename(columns={"demand_kg": "qty_ordered_kg"})
        routes = classify_products(routing_frame)
        routed_totals: dict[str, float] = {}
        for product_id, route in routes.items():
            product_train = train[train["product_id"] == product_id]
            series = (product_train.set_index("week_start")["demand_kg"]
                      .reindex(train_wk, fill_value=0.0).to_numpy(float))
            if route == "croston":
                routed_totals[str(product_id)] = float(
                    max(select_and_fit(series, horizon=1).mean, 0.0))
            else:
                routed_totals[str(product_id)] = float(series[-4:].sum() / 4.0)
            route_counts[route] += 1
        commits["forecast_routed"] = allocate_to_suppliers(
            routed_totals, shares)

        # Held-out fills settle the decision; the fallback is training-only
        # so no held-out information can leak into a missing supplier.
        train_fill = (tdel.groupby("supplier_id")["fill_rate"].mean()
                      .to_dict() if not tdel.empty else {})
        train_fill = {str(k): float(v) for k, v in train_fill.items()}
        pool_fill = (float(np.mean(list(train_fill.values())))
                     if train_fill else 1.0)
        fills = (
            {s_: 1.0 for s_ in list(train_fill) + [POOL_SUPPLIER]}
            if force_unit_fills else
            realized_fills(deliveries, origin, train_fill, pool_fill)
        )

        dem_tot = float(sum(float(v) for v in realized.values()))
        for pol in policies:
            tot_cost, served, waste, delivered = settle(
                commits[pol], realized, fills, econ,
                spot_cost_multiplier, spot_capacity_factor)
            per_fold[pol].append({
                "origin": str(pd.Timestamp(origin).date()),
                "cost": tot_cost, "served": served,
                "demand": dem_tot, "waste": waste,
                "committed": float(sum(commits[pol].values())),
                "delivered": delivered,
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
    fr_c = np.array([r["cost"] for r in per_fold["forecast_routed"]])

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

    atp_c = np.array([r["cost"] for r in per_fold["deterministic_atp"]])
    buf_c = np.array([r["cost"] for r in per_fold["safety_buffer_atp"]])
    mv_c = np.array([r["cost"] for r in per_fold["mean_value_sp"]])
    vs_lp = _edge(lp_c)
    vs_naive = _edge(nv_c)
    vs_sS = _edge(ss_c)
    vs_routed = _edge(fr_c)
    beats_lp = (vs_lp["edge_pct"] or 0) > 0
    beats_naive = (vs_naive["edge_pct"] or 0) > 0
    sp_service_pct = table["two_sided_sp"]["service_pct"]
    service_floor_met = bool(
        sp_service_pct is not None
        and float(sp_service_pct) >= float(service_level) * 100.0
    )
    # A run scored with force_unit_fills can never open the gate. That mode
    # exists only to prove the settlement refactor is behaviour-preserving;
    # it assumes every supplier delivers in full, which is the exact
    # assumption that made the previous benchmark unable to express the
    # value of hedging yield. Passing on synthetic perfect delivery is not
    # evidence of anything.
    gate = bool(
        beats_lp and beats_naive and service_floor_met
        and not force_unit_fills
    )

    return {
        "status": "ok",
        "policies": table,
        "sp_vs_deterministic_lp": vs_lp,
        "sp_vs_mean_value_sp": _edge(mv_c),
        "sp_vs_deterministic_atp": _edge(atp_c),
        "sp_vs_safety_buffer_atp": _edge(buf_c),
        "sp_vs_naive": vs_naive,
        "sp_vs_order_up_to": vs_sS,
        "sp_vs_forecast_routed": vs_routed,
        "gate_passed": gate,
        "service_floor": {
            "required_pct": round(float(service_level) * 100.0, 1),
            "sp_service_pct": sp_service_pct,
            "met": service_floor_met,
        },
        "verdict": (
            "stochastic SP beats both the deterministic LP and the naive "
            "baseline out-of-sample under honest penalties while meeting "
            "the configured service floor"
            if gate else
            "HONEST VERDICT: the stochastic SP does NOT beat the simple "
            "baselines while meeting the configured service floor on this "
            "data — the deterministic LP (or the "
            "order-up-to heuristic) is the honest planning recommendation "
            "here; do not ship the stochastic layer as if it added value"
        ),
        "spot_economics": {
            "spot_cost_multiplier": spot_cost_multiplier,
            "spot_capacity_factor": spot_capacity_factor,
            "note": "the SP edge is sensitive to these; sweep before "
                    "believing one number",
        },
        "scoring": (
            "supplier-level fill replay then product-level clean "
            "incremental recourse (overage at cost, spot at premium, unmet "
            "at margin); every policy settles through one function. "
            "Supplier-blind policies are allocated pro rata by "
            "training-window volume share, a stated modelling assumption."
            + (" FORCED UNIT FILLS: diagnostic mode, gate forced closed."
               if force_unit_fills else "")
        ),
        "settlement": {
            "fills_replayed": not force_unit_fills,
            "missing_fill_fallback": "supplier training-window mean",
            "supplier_blind_allocation": "pro rata by training volume share",
        },
        "demand_routing": route_counts,
        "supply_risk": correlation_diagnostics,
        "underage_overage_ratio": underage_overage_ratio,
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
