"""Two-stage stochastic program via Sample Average Approximation (SAA).

Stage 1 (here-and-now): commit volumes x_ij for the planning week
Stage 2 (recourse): after uncertainty resolves, choose spot buys s_ω and waste w_ω

Extensive form:
  min  Σ_{ij} c_ij * x_ij + (1/N) Σ_ω [ Σ_j c_spot_j * s_jω + c_waste * w_jω ]
  s.t.
    Stage 1:
      x_ij ≤ Y_ij          (contracted supply capacity, per supplier×product)
      x_ij ≥ 0
    Stage 2 (per scenario ω):
      Σ_i x_ij + s_jω - w_jω = d_jω    ∀ j  (demand balance)
      s_jω, w_jω ≥ 0
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class TwoStageStochasticLP:
    spot_cost_multiplier: float = 1.30
    waste_cost_per_kg: float = 0.50
    solver: str = "highs"
    time_limit_s: float = 300.0
    n_scenarios: int = 100

    def solve(
        self,
        demand_scenarios: pd.DataFrame,   # [scenario_index, scenario_weight, product_id, week_start, demand_kg]
        supply: pd.DataFrame,             # [supplier_id, product_id, week_start, capacity_kg, price_per_kg]
        aggregate_weeks: bool = True,     # collapse multi-week demand to single planning period
    ) -> dict:
        """Solve two-stage SP extensive form. Returns result dict."""
        import pyomo.environ as pyo
        from pyomo.opt import SolverFactory

        if aggregate_weeks:
            demand_scenarios = (
                demand_scenarios
                .groupby(["scenario_index","scenario_weight","product_id"])["demand_kg"]
                .sum()
                .reset_index()
            )
            supply_agg = (
                supply
                .groupby(["supplier_id","product_id"])
                .agg(capacity_kg=("capacity_kg","sum"), price_per_kg=("price_per_kg","mean"))
                .reset_index()
            )
        else:
            supply_agg = supply.copy()

        scenarios = sorted(demand_scenarios["scenario_index"].unique())
        products = list(demand_scenarios["product_id"].unique())
        suppliers = list(supply_agg["supplier_id"].unique())

        weights = {int(r["scenario_index"]): float(r["scenario_weight"])
                   for _, r in demand_scenarios.drop_duplicates("scenario_index").iterrows()}
        d = {(int(r["scenario_index"]), r["product_id"]): float(r["demand_kg"])
             for _, r in demand_scenarios.iterrows()}
        cap = {(r["supplier_id"], r["product_id"]): float(r["capacity_kg"])
               for _, r in supply_agg.iterrows()}
        price = {(r["supplier_id"], r["product_id"]): float(r["price_per_kg"])
                 for _, r in supply_agg.iterrows()}

        avg_price = {j: np.mean([v for (i,j2),v in price.items() if j2==j] or [2.0])
                     for j in products}

        model = pyo.ConcreteModel()
        model.I = pyo.Set(initialize=suppliers)
        model.J = pyo.Set(initialize=products)
        model.W = pyo.Set(initialize=scenarios)
        model.IJ = pyo.Set(initialize=list(cap.keys()), dimen=2)

        # Stage 1: commitment (here-and-now)
        model.x = pyo.Var(model.IJ, domain=pyo.NonNegativeReals)

        # Stage 2: recourse (per scenario)
        model.s = pyo.Var(model.J, model.W, domain=pyo.NonNegativeReals)  # spot
        model.w = pyo.Var(model.J, model.W, domain=pyo.NonNegativeReals)  # waste

        def obj_rule(m):
            first_stage = sum(price.get((i,j), 2.0) * m.x[i,j] for (i,j) in m.IJ)
            second_stage = sum(
                weights.get(omega, 1.0/len(scenarios)) * (
                    sum(avg_price[j] * self.spot_cost_multiplier * m.s[j,omega] for j in m.J)
                    + sum(self.waste_cost_per_kg * m.w[j,omega] for j in m.J)
                )
                for omega in m.W
            )
            return first_stage + second_stage

        model.obj = pyo.Objective(rule=obj_rule, sense=pyo.minimize)

        # Demand balance per scenario
        def balance(m, j, omega):
            supply_sum = sum(m.x[ii,jj] for (ii,jj) in m.IJ if jj==j)
            return supply_sum + m.s[j,omega] - m.w[j,omega] == d.get((omega,j), 0.0)

        model.balance = pyo.Constraint(model.J, model.W, rule=balance)

        # Supply capacity (stage-1 variable bounded by available supply)
        def supply_cap(m, i, j):
            return m.x[i,j] <= cap.get((i,j), 0.0)

        model.supply_cap = pyo.Constraint(model.IJ, rule=supply_cap)

        solver_factory = SolverFactory("appsi_highs" if self.solver == "highs" else self.solver)
        solver_factory.options["time_limit"] = self.time_limit_s
        results = solver_factory.solve(model, tee=False)

        status = str(results.solver.termination_condition)
        obj_val = pyo.value(model.obj) if status in ("optimal","locallyOptimal") else None

        x_vals = {k: pyo.value(v) for k, v in model.x.items()}
        s_vals = {(j,w): pyo.value(model.s[j,w]) for j in model.J for w in model.W}
        w_vals = {(j,w): pyo.value(model.w[j,w]) for j in model.J for w in model.W}

        # VSS and EVPI approximations
        total_spot = sum(v * weights.get(w, 0) for (j,w), v in s_vals.items() if v and v > 0)
        total_waste = sum(v * weights.get(w, 0) for (j,w), v in w_vals.items() if v and v > 0)

        return {
            "status": status,
            "objective": obj_val,
            "x": x_vals,
            "spot": s_vals,
            "waste": w_vals,
            "model": model,
            "expected_spot_kg": total_spot,
            "expected_waste_kg": total_waste,
        }

    def compute_vss(
        self,
        demand_scenarios: pd.DataFrame,
        supply: pd.DataFrame,
    ) -> float:
        """Value of Stochastic Solution = EV_solution_cost - SP_cost."""
        from optimization.lp_baseline import LPBaseline

        # EV: solve deterministic LP with mean demand
        mean_demand = (
            demand_scenarios.groupby("product_id")["demand_kg"].mean()
            .reset_index()
            .assign(week_start=demand_scenarios["week_start"].min() if "week_start" in demand_scenarios.columns else None)
        )
        ev_result = LPBaseline(
            spot_cost_multiplier=self.spot_cost_multiplier,
            waste_cost_per_kg=self.waste_cost_per_kg,
        ).solve(mean_demand, supply)

        sp_result = self.solve(demand_scenarios, supply)

        ev_obj = ev_result.get("objective") or float("nan")
        sp_obj = sp_result.get("objective") or float("nan")
        return float(ev_obj - sp_obj)
