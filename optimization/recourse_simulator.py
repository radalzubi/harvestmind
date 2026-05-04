"""Recourse simulator: given first-stage commitments and realized demand/supply,
compute the actual recourse actions and total cost for backtest evaluation.
"""

from __future__ import annotations

import pandas as pd


def simulate_recourse(
    commitments: pd.DataFrame,     # [supplier_id, product_id, committed_kg, price_per_kg]
    realized_demand: pd.DataFrame, # [product_id, demand_kg]
    realized_supply: pd.DataFrame, # [supplier_id, product_id, actual_available_kg]
    spot_price: pd.DataFrame | None = None,      # [product_id, avg_price]
    spot_cost_multiplier: float = 1.30,
    waste_cost_per_kg: float = 0.50,
) -> dict:
    """Simulate what happens when commitments meet realized supply/demand.

    Returns dict with:
      - total_cost
      - service_level_pct (demand met / total demand)
      - spot_kg, spot_cost
      - waste_kg, waste_cost
      - commitment_detail: DataFrame
    """
    products = list(realized_demand["product_id"].unique())
    results = []

    total_demand = realized_demand["demand_kg"].sum()
    total_met = 0.0
    total_spot_kg = 0.0
    total_spot_cost = 0.0
    total_waste_kg = 0.0
    total_waste_cost = 0.0
    total_commit_cost = 0.0

    for prod_id in products:
        demand_kg = float(realized_demand.loc[realized_demand["product_id"]==prod_id, "demand_kg"].sum())

        # How much was actually available from commitments (constrained by realized supply)
        committed = commitments[commitments["product_id"] == prod_id].copy()
        actual_available = 0.0
        for _, row in committed.iterrows():
            sup_id = row["supplier_id"]
            committed_qty = float(row["committed_kg"])
            cap_row = realized_supply[
                (realized_supply["supplier_id"]==sup_id) &
                (realized_supply["product_id"]==prod_id)
            ]
            actual_cap = float(cap_row["actual_available_kg"].iloc[0]) if len(cap_row) > 0 else committed_qty
            recv = min(committed_qty, actual_cap)
            actual_available += recv
            unit_price = float(row.get("price_per_kg") or 2.0)
            total_commit_cost += recv * unit_price

        gap = demand_kg - actual_available

        if gap > 0:
            # Must buy spot or lose the sale
            if spot_price is not None and prod_id in spot_price["product_id"].values:
                sp = float(spot_price.loc[spot_price["product_id"]==prod_id, "avg_price"].iloc[0])
            else:
                sp = 2.0  # fallback
            spot_qty = gap
            total_spot_kg += spot_qty
            total_spot_cost += spot_qty * sp * spot_cost_multiplier
            total_met += demand_kg
        else:
            surplus = actual_available - demand_kg
            total_waste_kg += surplus
            total_waste_cost += surplus * waste_cost_per_kg
            total_met += demand_kg

        results.append({
            "product_id": prod_id,
            "demand_kg": demand_kg,
            "available_kg": actual_available,
            "spot_kg": max(0.0, gap),
            "waste_kg": max(0.0, -gap),
        })

    total_cost = total_commit_cost + total_spot_cost + total_waste_cost
    service_level = (total_met / total_demand * 100) if total_demand > 0 else 100.0

    return {
        "total_cost": round(total_cost, 2),
        "service_level_pct": round(service_level, 2),
        "spot_kg": round(total_spot_kg, 2),
        "spot_cost": round(total_spot_cost, 2),
        "waste_kg": round(total_waste_kg, 2),
        "waste_cost": round(total_waste_cost, 2),
        "commit_cost": round(total_commit_cost, 2),
        "detail": pd.DataFrame(results),
    }
