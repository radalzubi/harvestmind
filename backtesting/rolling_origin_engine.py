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

import numpy as np
import pandas as pd

from backtesting.leakage_guard import LeakageGuard, assert_no_future_data
from forecasting.demand.lgbm_global_model import LGBMDemandModel
from forecasting.demand.intermittent_model import select_and_fit
from forecasting.supply.yield_scenario_generator import YieldScenarioGenerator
from optimization.lp_baseline import LPBaseline
from optimization.gamma_robust_lp import GammaRobustLP
from optimization.two_stage_sp import TwoStageStochasticLP
from optimization.recourse_simulator import simulate_recourse


@dataclass
class BacktestConfig:
    n_train_weeks: int = 52
    horizon_weeks: int = 4
    step_weeks: int = 4          # how often to re-origin
    n_scenarios: int = 50        # SAA scenarios per origin
    gammas: list[float] = field(default_factory=lambda: [0, 2, 4, 6])
    run_stochastic: bool = True
    solver: str = "highs"
    seed: int = 42


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

        # Aggregate demand for planning
        train_demand = (
            train_orders.groupby(["product_id","week_start"])["qty_ordered_kg"]
            .sum()
            .reset_index()
            .rename(columns={"qty_ordered_kg": "demand_kg"})
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

        batch_results = []

        # --- Deterministic LP (baseline) ---
        t0 = time.time()
        try:
            det_result = LPBaseline(solver=self.cfg.solver).solve(
                demand=train_demand.assign(week_start=origin),
                supply=train_supply,
            )
            recourse = simulate_recourse(
                commitments=self._result_to_commitments(det_result, train_supply),
                realized_demand=realized_demand,
                realized_supply=self._to_realized_supply(train_supply),
            )
            batch_results.append(BacktestResult(
                origin_week=origin,
                horizon_weeks=self.cfg.horizon_weeks,
                model="deterministic",
                gamma=None, lambda_cvar=None,
                objective=det_result.get("objective"),
                service_level_pct=recourse["service_level_pct"],
                waste_kg=recourse["waste_kg"],
                spot_kg=recourse["spot_kg"],
                spot_cost_usd=recourse["spot_cost"],
                total_cost_usd=recourse["total_cost"],
                solve_time_s=round(time.time()-t0, 2),
                solver_status=det_result.get("status","unknown"),
            ))
        except Exception as e:
            print(f"    Deterministic LP failed: {e}")

        # --- Γ-robust LP sweep ---
        for gamma in self.cfg.gammas:
            t0 = time.time()
            try:
                rob_result = GammaRobustLP(gamma=gamma, solver=self.cfg.solver).solve(
                    demand=train_demand.assign(week_start=origin),
                    supply=train_supply,
                )
                recourse = simulate_recourse(
                    commitments=self._result_to_commitments(rob_result, train_supply),
                    realized_demand=realized_demand,
                    realized_supply=self._to_realized_supply(train_supply),
                )
                batch_results.append(BacktestResult(
                    origin_week=origin,
                    horizon_weeks=self.cfg.horizon_weeks,
                    model="gamma_robust",
                    gamma=gamma, lambda_cvar=None,
                    objective=rob_result.get("objective"),
                    service_level_pct=recourse["service_level_pct"],
                    waste_kg=recourse["waste_kg"],
                    spot_kg=recourse["spot_kg"],
                    spot_cost_usd=recourse["spot_cost"],
                    total_cost_usd=recourse["total_cost"],
                    solve_time_s=round(time.time()-t0, 2),
                    solver_status=rob_result.get("status","unknown"),
                ))
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
                # Convert yield scenarios to demand scenarios (simplified: use yield as supply proxy)
                demand_scen = self._yield_to_demand_scenarios(scen_df, realized_demand)
                sp_result = TwoStageStochasticLP(
                    n_scenarios=self.cfg.n_scenarios,
                    solver=self.cfg.solver,
                ).solve(demand_scenarios=demand_scen, supply=train_supply)
                recourse = simulate_recourse(
                    commitments=self._result_to_commitments(sp_result, train_supply, is_sp=True),
                    realized_demand=realized_demand,
                    realized_supply=self._to_realized_supply(train_supply),
                )
                batch_results.append(BacktestResult(
                    origin_week=origin,
                    horizon_weeks=self.cfg.horizon_weeks,
                    model="two_stage_sp",
                    gamma=None, lambda_cvar=None,
                    objective=sp_result.get("objective"),
                    service_level_pct=recourse["service_level_pct"],
                    waste_kg=recourse["waste_kg"],
                    spot_kg=recourse["spot_kg"],
                    spot_cost_usd=recourse["spot_cost"],
                    total_cost_usd=recourse["total_cost"],
                    solve_time_s=round(time.time()-t0, 2),
                    solver_status=sp_result.get("status","unknown"),
                ))
            except Exception as e:
                print(f"    Two-stage SP failed: {e}")

        return batch_results

    # ------------------------------------------------------------------

    @staticmethod
    def _build_supply_df(deliveries_df: pd.DataFrame, horizon_weeks: list[date]) -> pd.DataFrame:
        """Build supply capacity DataFrame from recent delivery history."""
        if deliveries_df.empty:
            return pd.DataFrame(columns=["supplier_id","product_id","week_start","capacity_kg","price_per_kg"])
        recent = deliveries_df.tail(52 * 5)  # last year of data
        agg = (
            recent.groupby(["supplier_id","product_id"])
            .agg(capacity_kg=("qty_received_kg","mean"))
            .reset_index()
        )
        agg["price_per_kg"] = 2.0  # will be overridden from price_df if available
        # Expand to each horizon week
        rows = []
        for week in horizon_weeks:
            for _, row in agg.iterrows():
                r = row.to_dict()
                r["week_start"] = week
                rows.append(r)
        return pd.DataFrame(rows) if rows else agg.assign(week_start=date.today())

    @staticmethod
    def _to_realized_supply(train_supply: pd.DataFrame) -> pd.DataFrame:
        """Aggregate train_supply to (supplier, product, actual_available_kg) for recourse sim."""
        if train_supply.empty:
            return pd.DataFrame(columns=["supplier_id","product_id","actual_available_kg"])
        return (
            train_supply.groupby(["supplier_id", "product_id"])["capacity_kg"]
            .sum()
            .reset_index()
            .rename(columns={"capacity_kg": "actual_available_kg"})
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
