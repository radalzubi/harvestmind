"""Rolling-origin backtest engine.

For each origin date in the test window:
1. Slice all data to [start, origin] using LeakageGuard
2. Fit the forecasting model on training data
3. Generate supply scenarios for [origin+1, origin+horizon]
4. Solve the optimization model (deterministic + stochastic variants)
5. Simulate recourse against realized demand/supply
6. Record all metrics

Returns a DataFrame of backtest results for the reporting layer.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

import pandas as pd

from backtesting.leakage_guard import LeakageGuard
from forecasting.supply.yield_scenario_generator import YieldScenarioGenerator
from optimization.lp_baseline import LPBaseline
from optimization.gamma_robust_lp import GammaRobustLP
from optimization.naive_lastyear_policy import (
    NaivePolicyConfig,
    naive_lastyear_commitments,
)
from optimization.two_stage_sp import TwoStageStochasticLP
from optimization.recourse_simulator import simulate_recourse


# ── BENCHMARK SOURCES ─────────────────────────────────────────────────
# The defaults below are calibrated to published research, not aspirational
# targets. Anchors:
#
#   Spot premium 1.30×  : USDA AMS market-news (spot/contract spread);
#                          conservative vs. romaine 2018 disruption study
#                          (Spalding et al. 2023, AJAE proxy: +141–209%
#                          week-1 spot above contract).
#   Gross margin 16–20% : USDA SR-77 Vol III (2016) wholesale-hub pro
#                          forma — startup 14.5% → growth-stage 19.4%.
#                          Wallace Center / MSU Food Hub Benchmarking
#                          Study 2013: 14.49–16.09% sector mean,
#                          high-teens for wholesale-stage hubs.
#   Fill-rate SLA 95–98%: NC State Dining RFP (98%); Wisconsin primary
#                          distributor contract (95%); Iowa school
#                          consortium (98%). Pre-software observed
#                          baseline inferred 89–94%.
#   Lost-sale $/kg      : Derived = avg produce price ($18.60/kg leafy
#                          greens, cucumbers, tomatoes blend) × gross
#                          margin. Mid-range $3.50/kg.
#   Avoidable waste 40% : Internal assumption — no public benchmark.
#   Reactive procurement: 10–20% base, 25–35% stress (no direct food-hub
#                          survey data; inferred from broader produce
#                          industry reports).
# ──────────────────────────────────────────────────────────────────────


@dataclass
class BacktestConfig:
    n_train_weeks: int = 52
    horizon_weeks: int = 4
    step_weeks: int = 4          # how often to re-origin
    n_scenarios: int = 50        # SAA scenarios per origin
    gammas: list[float] = field(default_factory=lambda: [0, 2, 4, 6])
    run_stochastic: bool = True
    run_naive_baseline: bool = True       # include same-week-last-year naive policy
    solver: str = "highs"
    seed: int = 42

    # Cost model (research-backed defaults — see BENCHMARK SOURCES above).
    # These are surfaced on BacktestConfig for visibility / scenario sweeps;
    # they're consumed both by the simulator (recourse stage) and the LP/SP
    # optimizers (when the engine passes them through).
    spot_cost_multiplier: float = 1.30   # spot vs. contract price
    waste_cost_per_kg: float = 2.50      # ~16% margin × $15/kg avg

    # Spot rationing — fraction of horizon-period demand that can be sourced
    # spot. 0.30 = up to 30% of demand procurable via emergency POs; the rest
    # becomes lost sale. Set to None for unlimited spot (back-compat for older
    # tests / quick experiments).
    spot_capacity_factor: float | None = 0.30
    lost_sale_per_kg_usd: float = 3.50
    # Knobs that simulate degraded historical-data quality on the naive baseline.
    # A real food hub does not have a perfect last-year-same-week spreadsheet —
    # so the optimizer's relative advantage grows as these knobs are dialed up.
    naive_missing_rate: float = 0.0
    naive_noise_cv: float = 0.0
    naive_supplier_turnover_rate: float = 0.0


@dataclass
class BacktestResult:
    origin_week: date
    horizon_weeks: int
    model: str
    gamma: Optional[float]
    lambda_cvar: Optional[float]
    objective: Optional[float]
    service_level_pct: Optional[float]
    waste_kg: Optional[float]
    spot_kg: Optional[float]
    spot_cost_usd: Optional[float]
    total_cost_usd: Optional[float]
    solve_time_s: float
    solver_status: str
    waste_cost_usd: Optional[float] = None
    commit_cost_usd: Optional[float] = None
    lost_sale_kg: Optional[float] = None
    lost_sale_cost_usd: Optional[float] = None
    mase: Optional[float] = None
    coverage_80: Optional[float] = None


class RollingOriginEngine:
    def __init__(self, config: BacktestConfig | None = None) -> None:
        self.cfg = config or BacktestConfig()

    def run(
        self,
        orders_df: pd.DataFrame,           # [product_id, buyer_id, week_start, qty_ordered_kg]
        deliveries_df: pd.DataFrame,        # [supplier_id, product_id, delivery_date, qty_received_kg]
        yield_df: pd.DataFrame | None = None,
        weather_df: pd.DataFrame | None = None,
        price_df: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        """Run rolling-origin backtest. Returns DataFrame of BacktestResult rows."""
        orders_df = orders_df.copy()
        orders_df["week_start"] = pd.to_datetime(orders_df["week_start"])
        deliveries_df = deliveries_df.copy()
        deliveries_df["delivery_date"] = pd.to_datetime(deliveries_df["delivery_date"])

        all_weeks = sorted(orders_df["week_start"].dt.date.unique())
        min_origin_idx = self.cfg.n_train_weeks
        max_origin_idx = len(all_weeks) - self.cfg.horizon_weeks - 1

        if max_origin_idx < min_origin_idx:
            raise ValueError(
                f"Not enough data: need {self.cfg.n_train_weeks + self.cfg.horizon_weeks} weeks, "
                f"have {len(all_weeks)}"
            )

        origin_indices = range(min_origin_idx, max_origin_idx + 1, self.cfg.step_weeks)
        results: list[BacktestResult] = []

        for i, origin_idx in enumerate(origin_indices):
            origin = all_weeks[origin_idx]
            print(f"  Backtest origin {i+1}/{len(list(origin_indices))}: {origin}")

            try:
                batch = self._run_origin(
                    origin=origin,
                    orders_df=orders_df,
                    deliveries_df=deliveries_df,
                    yield_df=yield_df,
                    weather_df=weather_df,
                    price_df=price_df,
                    all_weeks=all_weeks,
                    origin_idx=origin_idx,
                )
                results.extend(batch)
            except Exception as e:
                print(f"    Warning: origin {origin} failed: {e}")
                continue

        if not results:
            return pd.DataFrame()

        return pd.DataFrame([vars(r) for r in results])

    def _run_origin(
        self,
        origin: date,
        orders_df: pd.DataFrame,
        deliveries_df: pd.DataFrame,
        yield_df,
        weather_df,
        price_df,
        all_weeks: list[date],
        origin_idx: int,
    ) -> list[BacktestResult]:

        # Strict information cutoff via LeakageGuard
        order_guard = LeakageGuard(orders_df, "week_start", origin)
        train_orders = order_guard.get()

        delivery_guard = LeakageGuard(deliveries_df, "delivery_date", origin)
        train_deliveries = delivery_guard.get()

        # Realized values (only used in recourse simulation, not in model fitting)
        realized_weeks = all_weeks[origin_idx + 1: origin_idx + 1 + self.cfg.horizon_weeks]
        realized_orders = orders_df[
            orders_df["week_start"].dt.date.isin(realized_weeks)
        ]

        # Aggregate demand for planning (PAST only — strictly ≤ origin)
        train_demand = (
            train_orders.groupby(["product_id","week_start"])["qty_ordered_kg"]
            .sum()
            .reset_index()
            .rename(columns={"qty_ordered_kg": "demand_kg"})
        )

        # Per-product *historical* mean — used as the SP's expected-demand
        # base. Earlier code used realized future demand here, which leaked
        # the recourse-period mean back into the planning input.
        train_demand_mean = (
            train_demand.groupby("product_id")["demand_kg"].mean()
            .reset_index()
        )

        # Simple supply proxy from deliveries
        train_supply = self._build_supply_df(train_deliveries, realized_weeks)

        # Build realized demand for recourse simulation
        realized_demand = (
            realized_orders.groupby("product_id")["qty_ordered_kg"]
            .sum()
            .reset_index()
            .rename(columns={"qty_ordered_kg": "demand_kg"})
        )

        # Defensive guard against future leakage of training data (cheap to
        # run; raises LeakageError if anything past the origin sneaks in).
        from backtesting.leakage_guard import assert_dates_in_window, assert_no_future_data
        assert_no_future_data(train_orders, "week_start", origin)
        if not train_deliveries.empty:
            assert_no_future_data(train_deliveries, "delivery_date", origin)

        # Symmetric guard: realized-window slice must not contain training data.
        if realized_weeks and not deliveries_df.empty:
            horizon_start = realized_weeks[0]
            horizon_end = realized_weeks[-1] + timedelta(days=6)
            deliv_dates = pd.to_datetime(deliveries_df["delivery_date"]).dt.date
            horizon_slice = deliveries_df[
                (deliv_dates >= horizon_start) & (deliv_dates <= horizon_end)
            ]
            assert_dates_in_window(horizon_slice, "delivery_date", horizon_start, horizon_end)

        batch_results = []

        # Pre-compute the realized supply once and the spot-capacity dict once,
        # so every model variant scores against the same recourse environment.
        realized_supply = self._to_realized_supply(deliveries_df, realized_weeks)
        spot_capacity = self._build_spot_capacity(realized_demand)

        def _score(commitments_df, model_name, gamma=None, lam_cvar=None,
                   objective=None, status="ok", solve_t0=None):
            rec = simulate_recourse(
                commitments=commitments_df,
                realized_demand=realized_demand,
                realized_supply=realized_supply,
                spot_capacity=spot_capacity,
                lost_sale_per_kg=self.cfg.lost_sale_per_kg_usd,
            )
            batch_results.append(BacktestResult(
                origin_week=origin,
                horizon_weeks=self.cfg.horizon_weeks,
                model=model_name,
                gamma=gamma, lambda_cvar=lam_cvar,
                objective=objective,
                service_level_pct=rec["service_level_pct"],
                waste_kg=rec["waste_kg"],
                spot_kg=rec["spot_kg"],
                spot_cost_usd=rec["spot_cost"],
                total_cost_usd=rec["total_cost"],
                waste_cost_usd=rec["waste_cost"],
                commit_cost_usd=rec["commit_cost"],
                lost_sale_kg=rec["lost_sale_kg"],
                lost_sale_cost_usd=rec["lost_sale_cost"],
                solve_time_s=round(time.time() - solve_t0, 2) if solve_t0 else 0.0,
                solver_status=status,
            ))

        # --- Naive same-week-last-year baseline ---
        if self.cfg.run_naive_baseline:
            t0 = time.time()
            try:
                naive_commit = naive_lastyear_commitments(
                    deliveries_train=train_deliveries,
                    decision_date=origin,
                    horizon_weeks=realized_weeks,
                    config=NaivePolicyConfig(
                        missing_rate=self.cfg.naive_missing_rate,
                        noise_cv=self.cfg.naive_noise_cv,
                        supplier_turnover_rate=self.cfg.naive_supplier_turnover_rate,
                        seed=self.cfg.seed,
                    ),
                )
                _score(naive_commit, "naive_lastyear", solve_t0=t0)
            except Exception as e:
                print(f"    Naive baseline failed: {e}")

        # Build LP demand input: per-product mean demand replicated across each
        # horizon week. The previous engine collapsed all training rows to a
        # single week_start, leaving the LP committing for ~1 week's demand
        # while the recourse simulator scored against H weeks.
        lp_demand = pd.concat([
            train_demand_mean.assign(week_start=w)
            for w in realized_weeks
        ], ignore_index=True)
        # rename for solver schema
        lp_demand = lp_demand.rename(columns={"demand_kg": "demand_kg"})

        # --- Deterministic LP ---
        t0 = time.time()
        try:
            det_result = LPBaseline(
                solver=self.cfg.solver,
                lost_sale_per_kg_usd=self.cfg.lost_sale_per_kg_usd,
                spot_capacity_factor=self.cfg.spot_capacity_factor,
            ).solve(
                demand=lp_demand,
                supply=train_supply,
            )
            _score(
                self._result_to_commitments(det_result, train_supply),
                "deterministic",
                objective=det_result.get("objective"),
                status=det_result.get("status", "unknown"),
                solve_t0=t0,
            )
        except Exception as e:
            print(f"    Deterministic LP failed: {e}")

        # --- Γ-robust LP sweep ---
        for gamma in self.cfg.gammas:
            t0 = time.time()
            try:
                rob_result = GammaRobustLP(
                    gamma=gamma,
                    solver=self.cfg.solver,
                ).solve(
                    demand=lp_demand,
                    supply=train_supply,
                )
                _score(
                    self._result_to_commitments(rob_result, train_supply),
                    "gamma_robust",
                    gamma=gamma,
                    objective=rob_result.get("objective"),
                    status=rob_result.get("status", "unknown"),
                    solve_t0=t0,
                )
            except Exception as e:
                print(f"    Γ={gamma} failed: {e}")

        # --- Two-stage SP ---
        if self.cfg.run_stochastic:
            t0 = time.time()
            try:
                scen_gen = YieldScenarioGenerator(n_scenarios=self.cfg.n_scenarios, seed=self.cfg.seed)
                scen_df = scen_gen.generate(
                    planning_week=origin + timedelta(weeks=1),
                    yield_history=yield_df,
                )
                # Convert yield scenarios to demand scenarios. Base is the
                # *historical* per-product mean (PAST data only); using
                # `realized_demand` here was a backtest lookahead bias.
                # Scale the per-week mean to the full horizon so the SP
                # commits enough supply for H weeks of demand.
                horizon_period_mean = train_demand_mean.copy()
                horizon_period_mean["demand_kg"] = (
                    horizon_period_mean["demand_kg"] * self.cfg.horizon_weeks
                )
                demand_scen = self._yield_to_demand_scenarios(scen_df, horizon_period_mean)
                sp_result = TwoStageStochasticLP(
                    n_scenarios=self.cfg.n_scenarios,
                    solver=self.cfg.solver,
                    lost_sale_per_kg_usd=self.cfg.lost_sale_per_kg_usd,
                    spot_capacity_factor=self.cfg.spot_capacity_factor,
                ).solve(demand_scenarios=demand_scen, supply=train_supply)
                _score(
                    self._result_to_commitments(sp_result, train_supply, is_sp=True),
                    "two_stage_sp",
                    objective=sp_result.get("objective"),
                    status=sp_result.get("status", "unknown"),
                    solve_t0=t0,
                )
            except Exception as e:
                print(f"    Two-stage SP failed: {e}")

        return batch_results

    # ------------------------------------------------------------------

    @staticmethod
    def _build_supply_df(deliveries_df: pd.DataFrame, horizon_weeks: list[date]) -> pd.DataFrame:
        """Build supply capacity DataFrame from recent delivery history.

        The capacity_kg column represents how much each supplier can deliver
        per planning week. We compute it as the trailing 12-week TOTAL kg
        divided by 12 — i.e. the average WEEKLY delivery volume, not the
        average per-delivery quantity. (The previous implementation used
        per-delivery mean, which is a 1.5–2× underestimate of weekly capacity
        and made the LP supply-bound at unrealistically low levels.)
        """
        if deliveries_df.empty:
            return pd.DataFrame(columns=["supplier_id","product_id","week_start","capacity_kg","price_per_kg"])

        df = deliveries_df.copy()
        df["delivery_date"] = pd.to_datetime(df["delivery_date"])
        df["iso_week"] = df["delivery_date"].dt.to_period("W").dt.start_time

        # Trailing 12 weeks of weekly aggregates
        max_date = pd.Timestamp(df["delivery_date"].max())
        cutoff = max_date - pd.DateOffset(weeks=12)
        recent = df[df["delivery_date"] >= cutoff]
        if recent.empty:
            recent = df

        weekly = (
            recent.groupby(["supplier_id", "product_id", "iso_week"])["qty_received_kg"]
            .sum()
            .reset_index()
        )
        # Average weekly capacity per supplier × product
        agg = (
            weekly.groupby(["supplier_id", "product_id"])["qty_received_kg"]
            .mean()
            .reset_index()
            .rename(columns={"qty_received_kg": "capacity_kg"})
        )
        # Add 30% planning headroom: max sustainable commit is above the mean.
        agg["capacity_kg"] = agg["capacity_kg"] * 1.30
        agg["price_per_kg"] = 2.0  # overridden from price_df if available

        rows = []
        for week in horizon_weeks:
            for _, row in agg.iterrows():
                r = row.to_dict()
                r["week_start"] = week
                rows.append(r)
        return pd.DataFrame(rows) if rows else agg.assign(week_start=date.today())

    def _build_spot_capacity(
        self, realized_demand: pd.DataFrame
    ) -> dict[str, float] | None:
        """Build per-product spot procurement caps from cfg.spot_capacity_factor.

        None → unlimited spot (back-compat).
        factor f → each product can source at most f × demand_kg via spot;
        anything beyond becomes a lost sale.
        """
        if self.cfg.spot_capacity_factor is None:
            return None
        if realized_demand.empty:
            return {}
        return {
            row["product_id"]: float(row["demand_kg"]) * self.cfg.spot_capacity_factor
            for _, row in realized_demand.iterrows()
        }

    @staticmethod
    def _to_realized_supply(
        deliveries_df: pd.DataFrame,
        realized_weeks: list[date],
    ) -> pd.DataFrame:
        """Aggregate horizon-window deliveries into realized supply per supplier × product.

        Reads ONLY the rows whose delivery_date falls inside the evaluation
        horizon [realized_weeks[0], end-of-last-week]. This is what the
        recourse simulator must score against — what physically arrived
        during the period being evaluated, not training-window history.

        Returns columns:
          supplier_id, product_id, actual_available_kg

        actual_available_kg = max(0, qty_received_kg - qty_rejected_kg).
        Rejected goods are not usable supply.
        """
        out_cols = ["supplier_id", "product_id", "actual_available_kg"]
        if deliveries_df.empty or not realized_weeks:
            return pd.DataFrame(columns=out_cols)

        horizon_start = pd.Timestamp(realized_weeks[0])
        horizon_end = pd.Timestamp(realized_weeks[-1]) + pd.DateOffset(days=6)

        deliv_dates = pd.to_datetime(deliveries_df["delivery_date"])
        mask = (deliv_dates >= horizon_start) & (deliv_dates <= horizon_end)
        horizon = deliveries_df.loc[mask].copy()
        if horizon.empty:
            return pd.DataFrame(columns=out_cols)

        received = horizon["qty_received_kg"].fillna(0.0)
        if "qty_rejected_kg" in horizon.columns:
            rejected = horizon["qty_rejected_kg"].fillna(0.0)
        else:
            rejected = 0.0
        horizon["qty_accepted_kg"] = (received - rejected).clip(lower=0.0)

        return (
            horizon.groupby(["supplier_id", "product_id"])["qty_accepted_kg"]
            .sum()
            .reset_index()
            .rename(columns={"qty_accepted_kg": "actual_available_kg"})
        )

    @staticmethod
    def _result_to_commitments(result: dict, supply: pd.DataFrame, is_sp: bool = False) -> pd.DataFrame:
        """Convert solver result x-values to commitment DataFrame.

        Handles both 2-tuple keys (supplier, product) from two-stage SP and
        3-tuple keys (supplier, product, week) from LP/robust LP.
        """
        rows = []
        price_map = {(r["supplier_id"], r["product_id"]): r["price_per_kg"]
                     for _, r in supply.iterrows()}
        for key, qty in result.get("x", {}).items():
            if qty is None or float(qty) < 1e-4:
                continue
            if isinstance(key, tuple) and len(key) >= 2:
                sup_id, prod_id = key[0], key[1]
            else:
                continue
            rows.append({
                "supplier_id": sup_id,
                "product_id": prod_id,
                "committed_kg": round(float(qty), 2),
                "price_per_kg": price_map.get((sup_id, prod_id), 2.0),
            })
        return pd.DataFrame(rows) if rows else pd.DataFrame(
            columns=["supplier_id","product_id","committed_kg","price_per_kg"]
        )

    @staticmethod
    def _yield_to_demand_scenarios(
        scen_df: pd.DataFrame,
        realized_demand: pd.DataFrame,
    ) -> pd.DataFrame:
        """Convert yield scenarios to demand uncertainty scenarios.

        Simple approach: demand = realized mean ± yield deviation ratio.
        """
        base = realized_demand.copy()
        n_scen = scen_df["scenario_index"].nunique()
        rows = []
        for scen_idx in range(n_scen):
            scen = scen_df[scen_df["scenario_index"] == scen_idx]
            weight = float(scen["scenario_weight"].iloc[0]) if len(scen) > 0 else 1.0/n_scen
            for _, row in base.iterrows():
                prod_id = row["product_id"]
                mean_demand = float(row["demand_kg"])
                # Modulate demand by ±20% based on supply tightness
                prod_yield = scen[scen["product_id"] == prod_id]["yield_kg"].sum()
                baseline_yield = scen_df[scen_df["product_id"] == prod_id]["yield_kg"].mean()
                ratio = prod_yield / baseline_yield if baseline_yield > 0 else 1.0
                # Tight supply → buyers place more urgent orders (slightly higher demand)
                demand_kg = mean_demand * min(1.3, max(0.7, ratio))
                rows.append({
                    "scenario_index": scen_idx,
                    "scenario_weight": weight,
                    "product_id": prod_id,
                    "week_start": None,
                    "demand_kg": round(demand_kg, 2),
                })
        return pd.DataFrame(rows)
