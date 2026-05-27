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
    spot_capacity: dict[str, float] | None = None,  # {product_id: max_spot_kg}
    lost_sale_per_kg: float = 0.0,                   # margin × price for unmet demand
) -> dict:
    """Simulate what happens when commitments meet realized supply/demand.

    Spot rationing
    --------------
    By default spot is unlimited (back-compat: any gap is closed by spot at premium).
    When `spot_capacity` is provided as a dict {product_id: max_spot_kg}, only that
    much spot is procurable per product — any residual gap becomes a lost sale that
    contributes to lost_sale_kg / lost_sale_cost and reduces service level.

    Returns dict with:
      total_cost, service_level_pct, commit_cost
      spot_kg, spot_cost
      waste_kg, waste_cost
      lost_sale_kg, lost_sale_cost
      detail: DataFrame
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
    total_lost_sale_kg = 0.0
    total_lost_sale_cost = 0.0

    # Pool realized supply by product. A food hub doesn't care which truck
    # the kale arrives on — they care that kale shows up. Per-supplier
    # under-fulfillment is partially offset by another supplier's surplus.
    pooled_supply = (
        realized_supply.groupby("product_id")["actual_available_kg"].sum().to_dict()
        if not realized_supply.empty
        else {}
    )

    for prod_id in products:
        demand_kg = float(realized_demand.loc[realized_demand["product_id"]==prod_id, "demand_kg"].sum())

        # How much was actually available across the product's suppliers
        committed = commitments[commitments["product_id"] == prod_id].copy()
        committed_kg = float(committed["committed_kg"].sum()) if not committed.empty else 0.0
        pooled_actual_cap = float(pooled_supply.get(prod_id, 0.0))
        # Hub absorbs min(planned, what actually arrived).
        actual_available = min(committed_kg, pooled_actual_cap)

        # Allocate commit_cost proportionally across the suppliers we committed to.
        if committed_kg > 0 and not committed.empty:
            for _, row in committed.iterrows():
                sup_share = float(row["committed_kg"]) / committed_kg
                received_share = actual_available * sup_share
                unit_price = float(row.get("price_per_kg") or 2.0)
                total_commit_cost += received_share * unit_price

        gap = demand_kg - actual_available

        spot_qty = 0.0
        lost_qty = 0.0
        if gap > 0:
            # Must buy spot or lose the sale
            if spot_price is not None and prod_id in spot_price["product_id"].values:
                sp = float(spot_price.loc[spot_price["product_id"]==prod_id, "avg_price"].iloc[0])
            else:
                sp = 2.0  # fallback
            cap = spot_capacity.get(prod_id, float("inf")) if spot_capacity is not None else float("inf")
            spot_qty = min(gap, cap)
            lost_qty = max(0.0, gap - cap)

            total_spot_kg += spot_qty
            total_spot_cost += spot_qty * sp * spot_cost_multiplier
            total_lost_sale_kg += lost_qty
            total_lost_sale_cost += lost_qty * lost_sale_per_kg
            total_met += demand_kg - lost_qty
        else:
            surplus = actual_available - demand_kg
            total_waste_kg += surplus
            total_waste_cost += surplus * waste_cost_per_kg
            total_met += demand_kg

        results.append({
            "product_id": prod_id,
            "demand_kg": demand_kg,
            "available_kg": actual_available,
            "spot_kg": spot_qty,
            "lost_sale_kg": lost_qty,
            "waste_kg": max(0.0, -gap),
        })

    total_cost = total_commit_cost + total_spot_cost + total_waste_cost + total_lost_sale_cost
    service_level = (total_met / total_demand * 100) if total_demand > 0 else 100.0

    return {
        "total_cost": round(total_cost, 2),
        "service_level_pct": round(service_level, 2),
        "spot_kg": round(total_spot_kg, 2),
        "spot_cost": round(total_spot_cost, 2),
        "waste_kg": round(total_waste_kg, 2),
        "waste_cost": round(total_waste_cost, 2),
        "lost_sale_kg": round(total_lost_sale_kg, 2),
        "lost_sale_cost": round(total_lost_sale_cost, 2),
        "commit_cost": round(total_commit_cost, 2),
        "detail": pd.DataFrame(results),
    }
