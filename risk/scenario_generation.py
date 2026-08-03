"""Bridge from operator data to the two-stage stochastic optimizer.

The optimizer in optimization/two_stage_sp.py has always expected two inputs
it had no way to produce from real data: demand scenarios and supply capacity.
This module generates both, and is where the hierarchical supplier distribution
enters the optimizer.

Demand scenarios
----------------
Each distinct buyer delivery date in the history is one equally weighted
scenario, with demand per product equal to that date's requested quantity.
This uses real demand variability rather than a synthetic distribution.

Supply capacity
---------------
For each supplier x product, capacity = typical ordered quantity x the
supplier's DOWNSIDE fill-rate quantile from the hierarchical model. A volatile
or unreliable supplier contributes less dependable capacity, so the optimizer
naturally leans on more reliable suppliers and on stage-2 recourse. This is the
robust-style use of the distribution: the optimizer commits against a
conservative read of each supplier's supply.

Honest limitation (worth raising with a researcher): supply uncertainty enters
here only through the downside-quantile capacity, a single conservative number.
A fuller model would treat each supplier's realized fill rate as a stage-2
recourse variable, so the commitment is made before supply resolves and the
shortfall is covered by spot purchases. That extension is the natural next step
and is exactly the modeling question for the technical conversation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from risk.supplier_distribution import supplier_fill_distributions

@dataclass
class ScenarioGenerationResult:
    """Scenario draws together with the dependence assumption behind them.

    WHY THIS REPLACED A MODULE GLOBAL. Diagnostics were previously stashed
    in process-global state and read back through a
    ``last_scenario_diagnostics()`` accessor. That is not request-safe: two
    concurrent planning calls race, and operator A can read operator B's
    diagnostics — corrupting audit provenance and leaking B's policy
    choice, supplier count and failure reason across a tenant boundary.
    The provenance of a plan has to travel WITH that plan, so it is
    returned rather than stored.
    """

    draws: dict
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return bool(self.draws)

    def __len__(self) -> int:
        return len(self.draws)


def _emit(diag: dict[str, Any], sink: dict | None) -> None:
    """Write diagnostics into a caller-owned dict, if one was supplied.

    Per-call, never shared. Nothing is retained between invocations, so
    concurrent callers cannot observe each other's provenance.
    """
    if sink is not None:
        sink.clear()
        sink.update(diag)


def generate_yield_scenarios(
    conn: duckdb.DuckDBPyConnection,
    scenario_indices: list[int],
    seed: int = 42,
    supply_risk_policy=None,
) -> ScenarioGenerationResult:
    """Yield scenarios AND their dependence provenance, returned together.

    The request-safe entry point. Prefer this over calling
    ``yield_scenarios_from_distributions`` and reading diagnostics from
    somewhere else — the whole point is that a plan carries the record of
    which dependence assumption produced it.
    """
    diagnostics: dict[str, Any] = {}
    draws = yield_scenarios_from_distributions(
        conn, scenario_indices, seed=seed,
        supply_risk_policy=supply_risk_policy,
        diagnostics_out=diagnostics)
    return ScenarioGenerationResult(draws=draws, diagnostics=diagnostics)


def demand_scenarios_from_orders(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Demand scenarios for the two-stage SP, one per buyer delivery date.

    Columns: scenario_index, scenario_weight, product_id, week_start, demand_kg.
    product_id carries the product NAME (the reliably populated key); the SP
    treats it as an opaque identifier.
    """
    df = conn.execute("""
        SELECT delivery_date,
               product_name,
               SUM(requested_quantity) AS demand_kg
        FROM stg_buyer_orders
        WHERE product_name IS NOT NULL
          AND requested_quantity IS NOT NULL
          AND delivery_date IS NOT NULL
        GROUP BY delivery_date, product_name
    """).df()

    if df.empty:
        return pd.DataFrame(columns=["scenario_index", "scenario_weight",
                                     "product_id", "week_start", "demand_kg"])

    dates = sorted(df["delivery_date"].unique())
    index_of = {d: i for i, d in enumerate(dates)}
    n = len(dates)

    df = df.copy()
    df["scenario_index"] = df["delivery_date"].map(index_of)
    df["scenario_weight"] = 1.0 / n
    df["week_start"] = df["delivery_date"]
    df["product_id"] = df["product_name"]
    return df[["scenario_index", "scenario_weight", "product_id",
               "week_start", "demand_kg"]]


def demand_scenarios_from_forecast(
    conn: duckdb.DuckDBPyConnection,
    n_scenarios: int = 100,
    horizon_weeks: int = 1,
    seed: int = 42,
) -> pd.DataFrame:
    """Demand scenarios drawn from the demand forecaster's distribution.

    Replaces equal-weight historical replay as the default scenario source:
    instead of treating every past week as equally likely next week, each
    scenario draws per-product demand from the forecast median plus a
    bootstrap of the forecaster's held-out residuals (truncated at zero).
    Falls back to historical replay when history is too short to forecast.

    Columns match demand_scenarios_from_orders: scenario_index,
    scenario_weight, product_id, week_start, demand_kg.
    """
    from forecasting.demand.demand_forecast_service import forecast_demand

    fc = forecast_demand(conn, horizon_weeks=horizon_weeks)
    if not fc.products:
        return demand_scenarios_from_orders(conn)

    rng = pd.Series(range(n_scenarios))  # deterministic index
    gen = np.random.default_rng(seed)

    rows = []
    for prod in fc.products:
        med = float(prod["forecast_kg_per_week"])
        qs = prod["quantiles_kg"]
        # Reconstruct a residual spread from the quantiles (q10..q90); a
        # degenerate spread (no holdout residuals) collapses to the median.
        spread = np.array([qs["q10"], qs["q25"], qs["q50"], qs["q75"], qs["q90"]])
        for s in rng:
            draw = float(gen.choice(spread)) if np.ptp(spread) > 0 else med
            # jitter between adjacent quantiles so 100 scenarios aren't 5 values
            if np.ptp(spread) > 0:
                draw = max(draw + gen.normal(0, max(spread.std(), 1e-9) * 0.25), 0.0)
            rows.append({
                "scenario_index": int(s),
                "scenario_weight": 1.0 / n_scenarios,
                "product_id": prod["product_name"],
                "week_start": fc.as_of,
                "demand_kg": round(draw, 2),
            })
    return pd.DataFrame(rows, columns=["scenario_index", "scenario_weight",
                                       "product_id", "week_start", "demand_kg"])


def supply_from_distributions(
    conn: duckdb.DuckDBPyConnection,
    quantile: float = 0.10,
) -> pd.DataFrame:
    """Supply capacity per supplier x product, discounted by downside fill rate.

    Columns: supplier_id, product_id, week_start, capacity_kg, price_per_kg.
    capacity_kg = average ordered quantity x the supplier's downside fill-rate
    quantile. price_per_kg = average unit cost for that supplier x product.
    """
    dists = supplier_fill_distributions(conn, quantile=quantile)

    agg = conn.execute("""
        SELECT supplier_id,
               product_name,
               AVG(ordered_quantity)        AS avg_ordered,
               AVG(NULLIF(unit_cost, 0))     AS avg_cost
        FROM stg_supplier_deliveries
        WHERE ordered_quantity IS NOT NULL AND ordered_quantity > 0
          AND product_name IS NOT NULL
        GROUP BY supplier_id, product_name
    """).df()

    rows: list[dict[str, Any]] = []
    for _, r in agg.iterrows():
        sid = r["supplier_id"]
        info = dists.get(sid)
        downside = float(info["downside"]) if info else 1.0
        avg_ordered = float(r["avg_ordered"]) if pd.notna(r["avg_ordered"]) else 0.0
        price = float(r["avg_cost"]) if pd.notna(r["avg_cost"]) else 2.0
        rows.append({
            "supplier_id": sid,
            "product_id": r["product_name"],
            "week_start": None,
            "capacity_kg": round(avg_ordered * downside, 4),
            "price_per_kg": round(price, 4),
        })

    return pd.DataFrame(rows, columns=["supplier_id", "product_id", "week_start",
                                       "capacity_kg", "price_per_kg"])


def yield_scenarios_from_distributions(
    conn: duckdb.DuckDBPyConnection,
    scenario_indices: list[int],
    seed: int = 42,
    supply_risk_policy=None,
    diagnostics_out: dict | None = None,
) -> dict:
    """Per-scenario supplier fill draws from the predictive Betas.

    Returns {(scenario_index, supplier_id): fill}. This is how supply
    uncertainty enters the optimizer as a genuine stage-2 outcome — the
    commitment is made before the fill resolves.

    Pass ``diagnostics_out`` (a dict you own) to receive the dependence
    provenance for THIS call. It is an explicit per-call sink rather than
    shared state, so concurrent planning requests cannot read each other's
    diagnostics. ``generate_yield_scenarios`` wraps this and returns both
    together if you would rather not manage the sink.

    Independent draws are the DEFAULT and the historical behaviour. They
    are known to understate aggregate risk when suppliers share a weather
    region — that artefact is what drove the value of the stochastic
    solution to zero in earlier testing — but the correction requires
    choosing a dependence model, and that choice is an operator-visible
    policy rather than a constant. Pass a
    ``risk.correlated_scenarios.SupplyRiskPolicy`` to enable it:

        from risk.correlated_scenarios import SupplyRiskPolicy
        pol = SupplyRiskPolicy(mode="estimated", copula="t", df=5)
        yield_scenarios_from_distributions(conn, ids, supply_risk_policy=pol)

    FAILURE BEHAVIOUR. When a requested dependence model cannot be
    supported — whether by exception or by insufficient statistical
    evidence — the DEFAULT is to raise. Independent fallback happens only
    when the policy sets ``on_failure="independent"``, and is then recorded
    as ``fallback_applied``. Infrastructure faults (``ScenarioDataError``,
    e.g. a missing table) are NOT governed by ``on_failure`` and always
    propagate: a broken migration is not a modelling judgement.

    SEED PRECEDENCE. When a policy is supplied AND enabled, the policy's
    ``seed`` is authoritative, because the policy is the object that
    describes the whole dependence model and its reproducibility. The
    ``seed`` argument applies to the independent path. The seed actually
    used is always reported in diagnostics as ``seed``.
    """
    from risk.correlated_scenarios import (
        DEFAULT_SUPPLY_RISK_POLICY,
        ScenarioDataError,
    )

    policy = supply_risk_policy or DEFAULT_SUPPLY_RISK_POLICY
    # Provenance of a fallback, held until the independent draws exist.
    # Emitting it here and then falling through would have it OVERWRITTEN by
    # the independent sampler's own _emit at the end of this function, so a
    # permitted fallback returned successful-looking draws with the REASON
    # ERASED — the audit contract broken in the one case that most needs it.
    fallback_diagnostics: dict[str, Any] | None = None

    if supply_risk_policy is not None and getattr(
            supply_risk_policy, "enabled", False):
        from risk.correlated_scenarios import (
            CorrelatedScenarioError,
            correlated_yield_scenarios,
        )
        try:
            draws, diag = correlated_yield_scenarios(
                conn, scenario_indices, policy=supply_risk_policy)
        except ScenarioDataError:
            # Infrastructure fault: never governed by on_failure, never
            # degraded into an independent-scenario "result".
            raise
        except (CorrelatedScenarioError, ValueError, np.linalg.LinAlgError) as exc:
            # Only anticipated failures are caught, and only when the policy
            # has explicitly permitted a fallback. A blanket `except
            # Exception: pass` here would let an operator select a
            # correlated policy, have it fail, and receive INDEPENDENT
            # scenarios that look like a normal result — silently changing
            # the dependence assumption behind a commitment recommendation.
            if getattr(supply_risk_policy, "on_failure", "raise") == "raise":
                raise
            fallback_diagnostics = {
                "policy_mode": getattr(supply_risk_policy, "mode", None),
                "correlation_source": "failed_degraded_to_independent",
                "fallback_applied": "independent",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "note": ("the requested correlated policy failed and the "
                         "policy permitted fallback; scenarios are "
                         "INDEPENDENT and aggregate risk is understated"),
            }
        else:
            if draws:
                _emit(diag, diagnostics_out)
                return draws
            if getattr(supply_risk_policy, "on_failure", "raise") == "raise":
                raise CorrelatedScenarioError(
                    "correlated policy produced no draws: "
                    f"{diag.get('correlation_source')} — "
                    f"{diag.get('note', 'no suppliers with fitted distributions')}")
            # Permitted fallback after an empty correlated result. Carry the
            # original reason forward rather than letting it be replaced.
            fallback_diagnostics = {
                **diag,
                "correlation_source": "empty_degraded_to_independent",
                "fallback_applied": "independent",
                "original_correlation_source": diag.get("correlation_source"),
            }
    from scipy import stats as _st

    dists = supplier_fill_distributions(conn, quantile=0.10)
    gen = np.random.default_rng(seed)
    out: dict = {}
    n_suppliers = 0
    for sid, d in dists.items():
        if sid == "_prior":
            continue
        n_suppliers += 1
        a, b = float(d["alpha"]), float(d["beta"])
        draws = _st.beta.rvs(a, b, size=len(scenario_indices),
                             random_state=gen)
        for k, omega in enumerate(scenario_indices):
            out[(int(omega), sid)] = float(min(max(draws[k], 0.0), 1.0))

    # Provenance for the INDEPENDENT path too. This branch was previously
    # silent, so the most common production route — the default — produced
    # plans with no record of the dependence assumption behind them, which
    # is exactly what the contract promises never to do.
    if fallback_diagnostics is not None:
        # A fallback happened: keep WHY, and complete it with the facts only
        # known after sampling.
        fallback_diagnostics.update(
            seed=seed, n_suppliers=n_suppliers, copula=None, df=None,
            mean_latent_correlation=0.0,
            fallback_generated_draws=bool(out),
        )
        if not out:
            # Nothing was produced, so no fallback was actually applied —
            # distinguish "attempted" from "applied" rather than implying
            # independent scenarios exist when they do not.
            fallback_diagnostics["status"] = "no_suppliers"
            fallback_diagnostics["fallback_attempted"] = "independent"
            fallback_diagnostics["fallback_applied"] = None
        _emit(fallback_diagnostics, diagnostics_out)
    else:
        default_diagnostics = {
            "policy_mode": getattr(policy, "mode", "independent"),
            "correlation_source": "independent_by_policy",
            "fallback_applied": None,
            "copula": None,
            "df": None,
            "mean_latent_correlation": 0.0,
            "seed": seed,
            "n_suppliers": n_suppliers,
            "policy_description": getattr(
                policy, "describe", lambda: "independent supplier draws")(),
            "note": ("supplier fills sampled INDEPENDENTLY; aggregate risk "
                     "may be understated when suppliers share regional "
                     "hazards"),
        }
        if not out:
            default_diagnostics["status"] = "no_suppliers"
        _emit(default_diagnostics, diagnostics_out)
    return out


def honest_penalties_from_staging(
    conn: duckdb.DuckDBPyConnection,
) -> tuple[dict, dict]:
    """Per-product honest penalties from the operator's own data.

    waste c_w,j = average unit cost (the cash burned on a wasted kg);
    unmet c_u,j = average lost margin (sell − cost, floored at 0).
    Products missing either side fall back to the optimizer's flat
    defaults via dict-miss.
    """
    costs = conn.execute("""
        SELECT product_name, AVG(NULLIF(unit_cost, 0)) AS c
        FROM stg_supplier_deliveries
        WHERE unit_cost IS NOT NULL AND unit_cost > 0
        GROUP BY product_name
    """).df()
    prices = conn.execute("""
        SELECT product_name, AVG(NULLIF(sales_price, 0)) AS p
        FROM stg_buyer_orders
        WHERE sales_price IS NOT NULL AND sales_price > 0
        GROUP BY product_name
    """).df()
    cost_map = dict(zip(costs["product_name"], costs["c"].astype(float))) \
        if not costs.empty else {}
    price_map = dict(zip(prices["product_name"], prices["p"].astype(float))) \
        if not prices.empty else {}
    cw = {j: float(c) for j, c in cost_map.items()}
    cu = {j: max(float(price_map[j]) - float(cost_map.get(j, price_map[j])), 0.0)
          for j in price_map}
    return cw, cu


def supply_capacity_full(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Supply capacity per supplier × product at the FULL typical order.

    Used with explicit yield scenarios: the uncertainty lives in the fill
    draws, so pre-discounting capacity by the downside (the one-sided
    approach) would double-count conservatism.
    """
    agg = conn.execute("""
        SELECT supplier_id,
               product_name,
               AVG(ordered_quantity)        AS avg_ordered,
               AVG(NULLIF(unit_cost, 0))     AS avg_cost
        FROM stg_supplier_deliveries
        WHERE ordered_quantity IS NOT NULL AND ordered_quantity > 0
          AND product_name IS NOT NULL
        GROUP BY supplier_id, product_name
    """).df()
    rows = []
    for _, r in agg.iterrows():
        rows.append({
            "supplier_id": r["supplier_id"],
            "product_id": r["product_name"],
            "week_start": None,
            "capacity_kg": round(float(r["avg_ordered"]), 4)
            if pd.notna(r["avg_ordered"]) else 0.0,
            "price_per_kg": round(float(r["avg_cost"]), 4)
            if pd.notna(r["avg_cost"]) else 2.0,
        })
    return pd.DataFrame(rows, columns=["supplier_id", "product_id",
                                       "week_start", "capacity_kg",
                                       "price_per_kg"])


# Plausible spot-economics grid used for the sensitivity band when the
# operator has not told us their actual emergency-coverage economics.
SPOT_SENSITIVITY_GRID: list[tuple[float, float]] = [
    (1.30, 0.30), (1.30, 0.15), (1.60, 0.30), (1.60, 0.15), (2.00, 0.10),
]


def run_two_stage_two_sided(
    conn: duckdb.DuckDBPyConnection,
    n_scenarios: int = 100,
    spot_economics: dict | None = None,
    service_level_floor: float | None = None,
    diversification_cap: float | None = None,
    seed: int = 42,
) -> dict[str, Any]:
    """Two-sided stochastic plan: demand AND supplier yield uncertain.

    - demand scenarios from the demand forecaster's distribution
    - supplier fill drawn per scenario from the predictive Betas
    - newsvendor-correct objective with honest per-product penalties
      sourced from the operator's own costs and prices

    ``spot_economics``: {"spot_cost_multiplier": float,
    "spot_capacity_factor": float} as ELICITED from the operator. When
    None, the plan is solved across SPOT_SENSITIVITY_GRID and returned
    with spot_economics_elicited=False — the recommendation carries a
    sensitivity band instead of silently assuming cheap spot. Measuring
    real spot economics is the first job with a new operator.
    """
    demand = demand_scenarios_from_forecast(conn, n_scenarios=n_scenarios)
    supply = supply_capacity_full(conn)
    if demand.empty or supply.empty:
        return {"status": "no_data"}

    scen_ids = sorted(demand["scenario_index"].unique())
    yields = yield_scenarios_from_distributions(conn, scen_ids, seed=seed)
    cw, cu = honest_penalties_from_staging(conn)

    from optimization.two_stage_sp import TwoStageStochasticLP

    def _solve(mult: float, rho: float) -> dict:
        sp = TwoStageStochasticLP(
            newsvendor_objective=True,
            waste_cost_by_product=cw,
            unmet_cost_by_product=cu,
            spot_cost_multiplier=mult,
            spot_capacity_factor=rho,
            service_level_floor=service_level_floor,
            diversification_cap=diversification_cap,
            n_scenarios=len(scen_ids),
        )
        res = sp.solve(demand, supply, yield_scenarios=yields)
        commit_by_product: dict = {}
        for (i, j), v in res["x"].items():
            if v and v > 1e-9:
                commit_by_product[j] = commit_by_product.get(j, 0.0) + float(v)
        return {
            "status": res["status"],
            "objective": res["objective"],
            "x": {f"{i}|{j}": round(float(v), 2)
                  for (i, j), v in res["x"].items() if v and v > 1e-9},
            "commit_by_product": {j: round(v, 1)
                                  for j, v in commit_by_product.items()},
            "total_commit_kg": round(sum(commit_by_product.values()), 1),
            "expected_unmet_kg": round(res["expected_unmet_kg"], 1),
            "expected_waste_kg": round(res["expected_waste_kg"], 1),
            # marginal value ($/kg) of one more kg of capacity at each
            # binding supplier × product — from the LP duals
            "shadow_prices": {f"{i}|{j}": v for (i, j), v
                              in res.get("shadow_prices", {}).items()},
        }

    if spot_economics is not None:
        mult = float(spot_economics["spot_cost_multiplier"])
        rho = float(spot_economics["spot_capacity_factor"])
        plan = _solve(mult, rho)
        return {
            "status": plan["status"],
            "spot_economics_elicited": True,
            "spot_cost_multiplier": mult,
            "spot_capacity_factor": rho,
            "plan": plan,
            "model": "two_sided_newsvendor_sp",
        }

    band = []
    for mult, rho in SPOT_SENSITIVITY_GRID:
        plan = _solve(mult, rho)
        band.append({"spot_cost_multiplier": mult,
                     "spot_capacity_factor": rho, **plan})
    return {
        "status": "ok" if all(b["status"] == "optimal" for b in band)
        else "partial",
        "spot_economics_elicited": False,
        "note": ("spot economics not elicited — plan shown across a "
                 "plausible grid; the recommendation depends on your "
                 "actual emergency-coverage cost, which we measure, not "
                 "assume"),
        "sensitivity_band": band,
        "model": "two_sided_newsvendor_sp",
    }


def run_two_stage(
    conn: duckdb.DuckDBPyConnection,
    quantile: float = 0.10,
    scenario_source: str = "forecast",
    **solver_kwargs: Any,
) -> dict[str, Any]:
    """Generate inputs and solve the two-stage SP on operator data.

    ``scenario_source``: "forecast" (default — demand drawn from the
    forecaster's distribution) or "replay" (equal-weight historical replay,
    kept for comparison and as the fallback for short histories).

    Returns the optimizer result dict plus the generated inputs, or a
    status of "no_data" when there is nothing to solve.
    """
    if scenario_source == "forecast":
        demand = demand_scenarios_from_forecast(conn)
    else:
        demand = demand_scenarios_from_orders(conn)
    supply = supply_from_distributions(conn, quantile=quantile)

    if demand.empty or supply.empty:
        return {"status": "no_data", "demand_scenarios": demand, "supply": supply}

    from optimization.two_stage_sp import TwoStageStochasticLP

    result = TwoStageStochasticLP(**solver_kwargs).solve(demand, supply)
    result["demand_scenarios"] = demand
    result["supply"] = supply
    return result
