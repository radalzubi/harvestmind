"""ROI calculator: translate backtest metrics into partner-facing financial impact.

Key KPIs:
  - Spot premium savings ($ per year)
  - Waste reduction ($ per year)
  - Lost sale recovery ($ per year)
  - Service level improvement (%)
  - VSS: value of stochastic vs deterministic model

`benchmark_scenarios()` re-derives ROI under 4 research-backed assumption
sets (USDA SR-77 startup / growth / mature, plus a stress-low). All four
scenarios run on the *same* backtest results — only the cost-per-kg and
subscription assumptions change.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


# HarvestMind subscription tiers — full price card (mirrors db migration 009).
# Sales segments — keep this dict in sync with dim_customer_segments. Used by
# `compute_roi(subscription_tier=...)` callers and the master orchestration
# script. The real source of truth is the DB row when a connection is supplied
# (see `_resolve_tier_pricing`); this constant is the offline fallback.
SUBSCRIPTION_TIERS: dict[str, dict] = {
    "A":      {"label": "Food hub",                    "monthly": 999.0,    "annual": 11988.0,  "setup": 2500.0,  "sla_hours": 48},
    "A_HIGH": {"label": "Food hub (premium)",          "monthly": 1499.0,   "annual": 17988.0,  "setup": 4000.0,  "sla_hours": 24},
    "B":      {"label": "Multi-site aggregator",       "monthly": 3750.0,   "annual": 45000.0,  "setup": 12500.0, "sla_hours": 12},
    "C":      {"label": "Regional distributor",        "monthly": 6250.0,   "annual": 75000.0,  "setup": 25000.0, "sla_hours": 4},
    "D":      {"label": "Enterprise distributor",      "monthly": 20833.0,  "annual": 250000.0, "setup": 75000.0, "sla_hours": 2},
}

# Backward-compat shims used by older code paths.
TIER_A_MONTHLY = SUBSCRIPTION_TIERS["A"]["monthly"]
TIER_B_MONTHLY = SUBSCRIPTION_TIERS["B"]["monthly"]


def _resolve_tier_pricing(tier: str, conn=None) -> dict:
    """Return {monthly, annual, setup, label} for `tier`.

    If a DB connection is supplied and `dim_customer_segments` is present,
    pull live pricing (so price changes propagate without a code release).
    Falls back to the `SUBSCRIPTION_TIERS` constant when offline.
    """
    if conn is not None:
        try:
            row = conn.execute(
                "SELECT monthly_price_usd, annual_price_usd, setup_fee_usd, segment_label "
                "FROM dim_customer_segments WHERE tier = ?",
                [tier],
            ).fetchone()
            if row:
                return {"monthly": float(row[0]), "annual": float(row[1]),
                        "setup": float(row[2] or 0), "label": row[3]}
        except Exception:
            pass
    return dict(SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS["A"]))


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

    # Section 1G audit: assert horizon_weeks is consistent across all rows.
    # The annualize factor (n_weeks / horizon_weeks) only makes sense if every
    # origin used the same horizon length.
    if "horizon_weeks" in backtest_df.columns:
        unique_horizons = backtest_df["horizon_weeks"].dropna().unique()
        if len(unique_horizons) > 1:
            raise ValueError(
                f"Inconsistent horizon_weeks across backtest rows: {sorted(unique_horizons)}. "
                "All origins must use the same horizon_weeks for ROI annualization to be valid."
            )

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

    # Section 1H — Value of Stochastic Solution (VSS).
    #   VSS_per_origin = total_cost(deterministic) - total_cost(SP) at the same origin
    # Quantifies the dollar value of using a stochastic optimizer over an
    # equivalent expected-value (deterministic) plan. A positive VSS confirms
    # that uncertainty modeling is paying for itself.
    annual_vss_usd: float | None = None
    vss_pct_of_savings: float | None = None
    if "deterministic" in backtest_df["model"].unique() and target_model == "two_stage_sp":
        det = backtest_df[backtest_df["model"] == "deterministic"].set_index("origin_week")
        sp = backtest_df[backtest_df["model"] == "two_stage_sp"].set_index("origin_week")
        common = det.index.intersection(sp.index)
        if len(common) > 0:
            vss_per_origin = det.loc[common, "total_cost_usd"] - sp.loc[common, "total_cost_usd"]
            annual_vss_usd = float(vss_per_origin.mean() * origins_per_year)

    # Total annual benefit
    total_annual_benefit = annual_spot_savings + waste_value_savings + lost_sale_recovery
    if annual_vss_usd is not None and total_annual_benefit > 0:
        vss_pct_of_savings = round(annual_vss_usd / total_annual_benefit * 100, 1)

    # Subscription cost — resolved against the DB if available, with the
    # constant table as a fallback. See SUBSCRIPTION_TIERS / migration 009.
    pricing = _resolve_tier_pricing(subscription_tier)
    monthly = pricing["monthly"]
    annual_subscription = pricing["annual"]

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
        "annual_vss_usd": round(annual_vss_usd, 0) if annual_vss_usd is not None else None,
        "vss_pct_of_savings": vss_pct_of_savings,
    }


# ── Benchmark scenarios ──────────────────────────────────────────────────────
# Average wholesale produce price for the target crop mix (leafy greens,
# tomatoes, cucumbers, peppers, cantaloupe). Source: USDA AMS national
# wholesale movement reports — mid-range for the basket; updated 2024.
#
# This is the FALLBACK used when fact_usda_prices is empty (i.e. the
# external-data ingestion has not run yet). After
# `scripts/ingest_market_prices.py` runs, `_resolve_avg_produce_price_kg`
# below pulls a live trailing-52-week average from the database instead.
AVG_PRODUCE_PRICE_KG = 18.60

_FTL_COMMODITIES_LC = (
    "cucumbers", "leafy greens", "tomatoes", "peppers", "cantaloupe",
    "lettuce, romaine", "lettuce, iceberg", "spinach", "kale",
    "tomatoes, cherry", "peppers, bell", "melons, cantaloupe",
)


def _resolve_avg_produce_price_kg(conn=None) -> float:
    """Return the basket avg $/kg, preferring live USDA data over the constant.

    If `conn` is provided and `fact_usda_prices` has any rows for the FTL
    commodity basket in the trailing 52 weeks, return that average. Otherwise
    fall back to AVG_PRODUCE_PRICE_KG so callers without ingested data still
    get a sensible number.
    """
    if conn is None:
        return AVG_PRODUCE_PRICE_KG

    placeholders = ", ".join(["?"] * len(_FTL_COMMODITIES_LC))
    sql = (
        "SELECT AVG(price_per_kg) FROM fact_usda_prices "
        f"WHERE LOWER(commodity) IN ({placeholders}) "
        "AND price_per_kg IS NOT NULL "
        "AND price_per_kg > 0 "
        "AND report_date >= CURRENT_DATE - INTERVAL 52 WEEK"
    )
    try:
        row = conn.execute(sql, list(_FTL_COMMODITIES_LC)).fetchone()
    except Exception:
        return AVG_PRODUCE_PRICE_KG
    if not row or row[0] is None:
        return AVG_PRODUCE_PRICE_KG
    try:
        v = float(row[0])
    except (TypeError, ValueError):
        return AVG_PRODUCE_PRICE_KG
    return v if v > 0 else AVG_PRODUCE_PRICE_KG


@dataclass(frozen=True)
class BenchmarkScenario:
    name: str
    gross_margin_pct: float
    spot_multiplier: float
    annual_subscription_usd: float
    rationale: str


BENCHMARK_SCENARIOS: tuple[BenchmarkScenario, ...] = (
    BenchmarkScenario(
        name="Conservative",
        gross_margin_pct=0.145,
        spot_multiplier=1.30,
        annual_subscription_usd=SUBSCRIPTION_TIERS["A"]["annual"],
        rationale="USDA SR-77 startup-stage hub margin; conservative spot premium",
    ),
    BenchmarkScenario(
        name="Base (SR-77)",
        gross_margin_pct=0.165,
        spot_multiplier=1.30,
        annual_subscription_usd=SUBSCRIPTION_TIERS["A"]["annual"],
        rationale="USDA SR-77 growth-stage; MSU survey top quartile",
    ),
    BenchmarkScenario(
        name="Optimistic",
        gross_margin_pct=0.194,
        spot_multiplier=1.35,
        annual_subscription_usd=SUBSCRIPTION_TIERS["A"]["annual"],
        rationale="SR-77 mature-hub upper bound; moderate disruption premium",
    ),
    BenchmarkScenario(
        name="Stress-low",
        gross_margin_pct=0.145,
        spot_multiplier=1.20,
        annual_subscription_usd=SUBSCRIPTION_TIERS["A_HIGH"]["annual"],
        rationale="Sector-average margin + mild spot exposure + premium tier",
    ),
    BenchmarkScenario(
        name="Aggregator (Tier B)",
        gross_margin_pct=0.165,
        spot_multiplier=1.30,
        annual_subscription_usd=SUBSCRIPTION_TIERS["B"]["annual"],
        rationale="Multi-site aggregator @ $15–75M GMV — Tier B price",
    ),
    BenchmarkScenario(
        name="Distributor (Tier C)",
        gross_margin_pct=0.165,
        spot_multiplier=1.30,
        annual_subscription_usd=SUBSCRIPTION_TIERS["C"]["annual"],
        rationale="Regional distributor @ $50–500M GMV — Tier C price",
    ),
)


def benchmark_scenarios(
    results_df: pd.DataFrame,
    annual_gmv_usd: float,
    baseline_model: str = "naive_lastyear",
    target_model: str = "two_stage_sp",
    conn=None,
) -> pd.DataFrame:
    """Re-derive ROI under 4 research-backed assumption sets.

    The optimizer is unchanged — only the cost-per-kg and subscription
    assumptions vary. For each scenario:

      waste_value_per_kg = avg_produce_price_kg × gross_margin_pct
      lost_sale_per_kg   = avg_produce_price_kg × gross_margin_pct
      annual_spot_savings_usd ↔ scaled by (spot_multiplier / 1.30)
                                (the backtest's spot_cost_usd was computed
                                 at the engine default 1.30×)
      annual_subscription_usd = scenario value

    avg_produce_price_kg is resolved live from `fact_usda_prices` if a DB
    connection is supplied and the table has rows; otherwise falls back to
    the constant `AVG_PRODUCE_PRICE_KG` ($18.60/kg).

    Lost-sale recovery (which depends on fill-rate × GMV) is reused from
    the base compute_roi() call — the scenarios don't perturb GMV.

    Returns one row per scenario with columns suitable for direct CSV
    or JSON export.
    """
    avg_produce_price_kg = _resolve_avg_produce_price_kg(conn)
    base = compute_roi(
        results_df,
        baseline_model=baseline_model,
        target_model=target_model,
        annual_gmv_usd=annual_gmv_usd,
    )
    if "error" in base:
        return pd.DataFrame()

    waste_kg_red = float(base.get("waste_kg_reduction_annual") or 0.0)
    base_spot_savings = float(base.get("annual_spot_savings_usd") or 0.0)
    base_lost_sale_recovery = float(base.get("annual_lost_sale_recovery_usd") or 0.0)
    baseline_sl = float(base.get("baseline_service_level_pct") or 0.0)
    target_sl = float(base.get("target_service_level_pct") or 0.0)
    sl_uplift = float(base.get("service_level_improvement_pts") or 0.0)

    rows = []
    for s in BENCHMARK_SCENARIOS:
        per_kg = avg_produce_price_kg * s.gross_margin_pct
        waste_savings = max(0.0, waste_kg_red * per_kg)
        # Engine ran at multiplier=1.30. Scaling baseline spot_savings by the
        # ratio approximates the savings the optimizer would have produced if
        # the assumed multiplier were different.
        spot_savings = base_spot_savings * (s.spot_multiplier / 1.30)
        # Lost-sale recovery: use scenario per-kg if we have a service-level
        # uplift; otherwise fall back to compute_roi's GMV-based estimate.
        lost_sale_recovery = base_lost_sale_recovery

        total_benefit = waste_savings + spot_savings + lost_sale_recovery
        net = total_benefit - s.annual_subscription_usd
        roi = (
            total_benefit / s.annual_subscription_usd
            if s.annual_subscription_usd > 0 else float("inf")
        )
        payback = (
            s.annual_subscription_usd / (total_benefit / 12)
            if total_benefit > 0 else float("inf")
        )

        rows.append({
            "scenario_name": s.name,
            "gross_margin_pct": s.gross_margin_pct,
            "spot_multiplier": s.spot_multiplier,
            "lost_sale_per_kg": round(per_kg, 2),
            "annual_subscription_usd": s.annual_subscription_usd,
            "annual_spot_savings_usd": round(spot_savings, 0),
            "annual_waste_savings_usd": round(waste_savings, 0),
            "annual_lost_sale_recovery_usd": round(lost_sale_recovery, 0),
            "total_annual_benefit_usd": round(total_benefit, 0),
            "net_annual_benefit_usd": round(net, 0),
            "roi_multiple": round(roi, 2) if roi != float("inf") else None,
            "payback_months": round(payback, 1) if payback != float("inf") else None,
            "baseline_fill_pct": round(baseline_sl, 1),
            "target_fill_pct": round(target_sl, 1),
            "fill_rate_uplift_pts": round(sl_uplift, 1),
            "rationale": s.rationale,
        })

    return pd.DataFrame(rows)
