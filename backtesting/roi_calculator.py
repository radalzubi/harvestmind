"""ROI calculator: translate backtest metrics into partner-facing financial impact.

Key KPIs:
  - Spot premium savings ($ per year)
  - Waste reduction ($ per year)
  - Lost sale recovery ($ per year)
  - Service level improvement (%)
  - VSS: value of stochastic vs deterministic model
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# HarvestMind subscription tiers
TIER_A_MONTHLY = 1_249.0   # Food hub Tier A
TIER_B_MONTHLY = 3_750.0   # Distributor Tier B


def compute_roi(
    backtest_df: pd.DataFrame,
    baseline_model: str = "deterministic",
    target_model: str = "two_stage_sp",
    annual_gmv_usd: float = 3_000_000.0,  # partner's annual GMV
    subscription_tier: str = "A",
    n_weeks: int = 52,
) -> dict:
    """Compute partner ROI from backtest results.

    Parameters
    ----------
    backtest_df  : output of RollingOriginEngine.run()
    baseline_model : model to use as status quo
    target_model : AI-optimized model
    annual_gmv_usd : partner's annual gross merchandise volume
    """
    if backtest_df.empty:
        return {"error": "No backtest data"}

    baseline = backtest_df[backtest_df["model"] == baseline_model]
    target = backtest_df[backtest_df["model"] == target_model]

    if baseline.empty or target.empty:
        return {"error": f"Missing model data: {baseline_model} or {target_model}"}

    # Spot premium savings
    baseline_spot_pct = baseline["spot_kg"].mean() / (baseline["spot_kg"].mean() + baseline["waste_kg"].mean() + 1) * 100
    target_spot_pct = target["spot_kg"].mean() / (target["spot_kg"].mean() + target["waste_kg"].mean() + 1) * 100
    spot_kg_reduction = max(0, baseline["spot_kg"].mean() - target["spot_kg"].mean())
    spot_savings_pct = spot_kg_reduction / (baseline["spot_kg"].mean() + 1e-9) * 100

    # Annualize: extrapolate per-origin metrics to full year
    origins_per_year = n_weeks / backtest_df["horizon_weeks"].iloc[0] if "horizon_weeks" in backtest_df.columns else 13

    avg_baseline_spot_cost = baseline["spot_cost_usd"].mean() * origins_per_year
    avg_target_spot_cost = target["spot_cost_usd"].mean() * origins_per_year
    annual_spot_savings = max(0.0, avg_baseline_spot_cost - avg_target_spot_cost)

    avg_baseline_waste = baseline["waste_kg"].mean() * origins_per_year
    avg_target_waste = target["waste_kg"].mean() * origins_per_year
    waste_kg_reduction = max(0.0, avg_baseline_waste - avg_target_waste)
    # Approximate waste value at $1.50/kg average farm-gate
    waste_value_savings = waste_kg_reduction * 1.50

    # Service level improvement
    baseline_sl = baseline["service_level_pct"].mean()
    target_sl = target["service_level_pct"].mean()
    sl_improvement_pts = target_sl - baseline_sl
    # Lost sale recovery: 1 pt service level ≈ 1% of GMV
    lost_sale_recovery = max(0.0, sl_improvement_pts / 100 * annual_gmv_usd)

    # Total annual benefit
    total_annual_benefit = annual_spot_savings + waste_value_savings + lost_sale_recovery

    # Subscription cost
    monthly = TIER_A_MONTHLY if subscription_tier == "A" else TIER_B_MONTHLY
    annual_subscription = monthly * 12

    net_benefit = total_annual_benefit - annual_subscription
    roi_multiple = total_annual_benefit / annual_subscription if annual_subscription > 0 else float("inf")
    payback_months = annual_subscription / (total_annual_benefit / 12) if total_annual_benefit > 0 else float("inf")

    return {
        "baseline_model": baseline_model,
        "target_model": target_model,
        "annual_gmv_usd": annual_gmv_usd,
        "subscription_tier": subscription_tier,
        "monthly_subscription_usd": monthly,
        "annual_subscription_usd": annual_subscription,
        "annual_spot_savings_usd": round(annual_spot_savings, 0),
        "annual_waste_value_savings_usd": round(waste_value_savings, 0),
        "annual_lost_sale_recovery_usd": round(lost_sale_recovery, 0),
        "total_annual_benefit_usd": round(total_annual_benefit, 0),
        "net_annual_benefit_usd": round(net_benefit, 0),
        "roi_multiple": round(roi_multiple, 1),
        "payback_months": round(payback_months, 1),
        "baseline_service_level_pct": round(baseline_sl, 1),
        "target_service_level_pct": round(target_sl, 1),
        "service_level_improvement_pts": round(sl_improvement_pts, 1),
        "spot_savings_pct": round(spot_savings_pct, 1),
        "waste_kg_reduction_annual": round(waste_kg_reduction, 0),
    }
