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

from typing import Any

import duckdb
import pandas as pd

from risk.supplier_distribution import supplier_fill_distributions


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
    import numpy as np
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
