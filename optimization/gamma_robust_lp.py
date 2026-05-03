"""Bertsimas-Sim Γ-robust LP (2004).

Reformulation of the supply commitment LP under demand uncertainty.
For each demand constraint, the worst-case deviation is controlled by Γ.

Original uncertain program:
  min  c'x
  s.t. Σ_i x_ijt + s_jt ≥ d_jt + Σ_k δ_jt,k * z_k   ∀j,t  (demand uncertainty)
       0 ≤ z_k ≤ 1, Σ_k z_k ≤ Γ                        (budget of uncertainty)

Bertsimas-Sim robust counterpart (linear reformulation):
  min  c'x + Γ*β + Σ_jt p_jt
  s.t. Σ_i x_ijt + s_jt - w_jt + Γ*β_jt + p_jt ≥ d_jt + d̂_jt
       p_jt ≥ d̂_jt - β_jt
       β_jt ≥ 0, p_jt ≥ 0

where d̂_jt is the maximum demand deviation (= demand * demand_uncertainty_pct).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class GammaRobustLP:
    gamma: float = 4.0                  # budget of uncertainty Γ ∈ [0, n_constraints]
    demand_uncertainty_pct: float = 0.20  # d̂ as fraction of mean demand
    spot_cost_multiplier: float = 1.30
    waste_cost_per_kg: float = 0.50
    solver: str = "highs"
    time_limit_s: float = 180.0

    def solve(
        self,
        demand: pd.DataFrame,           # [product_id, week_start, demand_kg]
        supply: pd.DataFrame,           # [supplier_id, product_id, week_start, capacity_kg, price_per_kg]
        contracts: pd.DataFrame | None = None,
    ) -> dict:
        """Solve Γ-robust LP. Returns same structure as LPBaseline.solve()."""
        import pyomo.environ as pyo
        from pyomo.opt import SolverFactory

        demand = demand.copy()
        supply = supply.copy()

        products = list(demand["product_id"].unique())
        weeks = sorted(demand["week_start"].unique())
        suppliers = list(supply["supplier_id"].unique())

        d_mean = {(r["product_id"], r["week_start"]): r["demand_kg"]
                  for _, r in demand.iterrows()}
        d_hat = {k: v * self.demand_uncertainty_pct for k, v in d_mean.items()}

        cap = {(r["supplier_id"], r["product_id"], r["week_start"]): r["capacity_kg"]
               for _, r in supply.iterrows()}
        price = {(r["supplier_id"], r["product_id"], r["week_start"]): r["price_per_kg"]
                 for _, r in supply.iterrows()}

        model = pyo.ConcreteModel()
        model.I = pyo.Set(initialize=suppliers)
        model.J = pyo.Set(initialize=products)
        model.T = pyo.Set(initialize=weeks)
        model.IJT = pyo.Set(initialize=list(cap.keys()), dimen=3)

        # Primary variables
        model.x = pyo.Var(model.IJT, domain=pyo.NonNegativeReals)   # commitment
        model.s = pyo.Var(model.J, model.T, domain=pyo.NonNegativeReals)  # spot
        model.w = pyo.Var(model.J, model.T, domain=pyo.NonNegativeReals)  # waste

        # Bertsimas-Sim auxiliary variables
        model.beta = pyo.Var(model.J, model.T, domain=pyo.NonNegativeReals)  # β_jt
        model.p = pyo.Var(model.J, model.T, domain=pyo.NonNegativeReals)     # p_jt

        # Objective: nominal cost + robustness term Γ*β + p
        def obj_rule(m):
            commit_cost = sum(price.get((i,j,t), 2.0) * m.x[i,j,t] for (i,j,t) in m.IJT)
            spot_cost = sum(
                price.get((None,j,t), 2.0) * self.spot_cost_multiplier * m.s[j,t]
                for j in m.J for t in m.T
            )
            waste_cost = sum(self.waste_cost_per_kg * m.w[j,t] for j in m.J for t in m.T)
            robust_cost = sum(
                self.gamma * m.beta[j,t] + m.p[j,t]
                for j in m.J for t in m.T
            )
            return commit_cost + spot_cost + waste_cost + robust_cost

        model.obj = pyo.Objective(rule=obj_rule, sense=pyo.minimize)

        # Robust demand satisfaction: x + s - w + Γ*β + p ≥ d + d̂
        def robust_demand(m, j, t):
            supply_sum = sum(m.x[ii,jj,tt] for (ii,jj,tt) in m.IJT if jj==j and tt==t)
            rhs = d_mean.get((j,t), 0.0) + d_hat.get((j,t), 0.0)
            return supply_sum + m.s[j,t] - m.w[j,t] + m.beta[j,t] * self.gamma + m.p[j,t] >= rhs

        model.robust_demand = pyo.Constraint(model.J, model.T, rule=robust_demand)

        # Dual linking: p_jt ≥ d̂_jt - β_jt
        def dual_link(m, j, t):
            return m.p[j,t] >= d_hat.get((j,t), 0.0) - m.beta[j,t]

        model.dual_link = pyo.Constraint(model.J, model.T, rule=dual_link)

        # Supply capacity
        def supply_cap(m, i, j, t):
            return m.x[i,j,t] <= cap.get((i,j,t), 0.0)

        model.supply_cap = pyo.Constraint(model.IJT, rule=supply_cap)

        solver = SolverFactory("appsi_highs" if self.solver == "highs" else self.solver)
        solver.options["time_limit"] = self.time_limit_s
        results = solver.solve(model, tee=False)

        status = str(results.solver.termination_condition)
        obj_val = pyo.value(model.obj) if status in ("optimal","locallyOptimal") else None

        return {
            "status": status,
            "objective": obj_val,
            "x": {k: pyo.value(v) for k, v in model.x.items()},
            "spot": {(j,t): pyo.value(model.s[j,t]) for j in model.J for t in model.T},
            "waste": {(j,t): pyo.value(model.w[j,t]) for j in model.J for t in model.T},
            "beta": {(j,t): pyo.value(model.beta[j,t]) for j in model.J for t in model.T},
            "model": model,
            "gamma": self.gamma,
        }

    @classmethod
    def gamma_sweep(
        cls,
        gammas: list[float],
        demand: pd.DataFrame,
        supply: pd.DataFrame,
        contracts: pd.DataFrame | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Solve for a range of Γ values. Returns frontier DataFrame."""
        rows = []
        for g in gammas:
            solver = cls(gamma=g, **kwargs)
            result = solver.solve(demand, supply, contracts)
            total_spot = sum(v for v in result["spot"].values() if v and v > 0)
            rows.append({
                "gamma": g,
                "objective": result["objective"],
                "status": result["status"],
                "total_spot_kg": total_spot,
            })
        return pd.DataFrame(rows)
