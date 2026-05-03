"""CVaR (Conditional Value at Risk) extension to the stochastic program.

Mean-CVaR objective: min λ * E[cost] + (1-λ) * CVaR_α[cost]

Rockafellar-Uryasev (2000) linearization:
  CVaR_α = η + 1/((1-α)|Ω|) * Σ_ω z_ω
  s.t. z_ω ≥ Q_ω - η
       z_ω ≥ 0

where Q_ω is the recourse cost for scenario ω.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class CVaRStochasticLP:
    alpha: float = 0.95             # CVaR confidence level
    lambda_weight: float = 0.50     # 0 = pure CVaR, 1 = pure expected cost
    spot_cost_multiplier: float = 1.30
    waste_cost_per_kg: float = 0.50
    solver: str = "highs"
    time_limit_s: float = 300.0

    def solve(
        self,
        demand_scenarios: pd.DataFrame,
        supply: pd.DataFrame,
    ) -> dict:
        """Solve mean-CVaR stochastic program."""
        import pyomo.environ as pyo
        from pyomo.opt import SolverFactory

        # Aggregate weeks
        dem = (
            demand_scenarios
            .groupby(["scenario_index","scenario_weight","product_id"])["demand_kg"]
            .sum()
            .reset_index()
        )
        sup = (
            supply.groupby(["supplier_id","product_id"])
            .agg(capacity_kg=("capacity_kg","sum"), price_per_kg=("price_per_kg","mean"))
            .reset_index()
        )

        scenarios = sorted(dem["scenario_index"].unique())
        products = list(dem["product_id"].unique())
        suppliers = list(sup["supplier_id"].unique())
        n_scen = len(scenarios)

        weights = {int(r["scenario_index"]): float(r["scenario_weight"])
                   for _, r in dem.drop_duplicates("scenario_index").iterrows()}
        d = {(int(r["scenario_index"]), r["product_id"]): float(r["demand_kg"])
             for _, r in dem.iterrows()}
        cap = {(r["supplier_id"],r["product_id"]): float(r["capacity_kg"])
               for _, r in sup.iterrows()}
        price = {(r["supplier_id"],r["product_id"]): float(r["price_per_kg"])
                 for _, r in sup.iterrows()}
        avg_price = {j: np.mean([v for (i,j2),v in price.items() if j2==j] or [2.0])
                     for j in products}

        model = pyo.ConcreteModel()
        model.I = pyo.Set(initialize=suppliers)
        model.J = pyo.Set(initialize=products)
        model.W = pyo.Set(initialize=scenarios)
        model.IJ = pyo.Set(initialize=list(cap.keys()), dimen=2)

        model.x = pyo.Var(model.IJ, domain=pyo.NonNegativeReals)
        model.s = pyo.Var(model.J, model.W, domain=pyo.NonNegativeReals)
        model.w = pyo.Var(model.J, model.W, domain=pyo.NonNegativeReals)

        # CVaR variables
        model.eta = pyo.Var(domain=pyo.Reals)       # VaR threshold
        model.z = pyo.Var(model.W, domain=pyo.NonNegativeReals)  # excess over VaR

        # Per-scenario recourse cost (auxiliary expression)
        def recourse_cost(m, omega):
            return (
                sum(avg_price[j] * self.spot_cost_multiplier * m.s[j,omega] for j in m.J)
                + sum(self.waste_cost_per_kg * m.w[j,omega] for j in m.J)
            )

        first_stage_cost = sum(price.get((i,j), 2.0) * model.x[i,j] for (i,j) in model.IJ)

        def obj_rule(m):
            exp_cost = first_stage_cost + sum(
                weights.get(omega, 1.0/n_scen) * recourse_cost(m, omega)
                for omega in m.W
            )
            cvar = m.eta + 1.0 / ((1 - self.alpha) * n_scen) * sum(m.z[omega] for omega in m.W)
            return self.lambda_weight * exp_cost + (1 - self.lambda_weight) * cvar

        model.obj = pyo.Objective(rule=obj_rule, sense=pyo.minimize)

        # CVaR linearization: z_ω ≥ Q_ω - η
        def cvar_cut(m, omega):
            return m.z[omega] >= recourse_cost(m, omega) - m.eta

        model.cvar_cut = pyo.Constraint(model.W, rule=cvar_cut)

        # Demand balance
        def balance(m, j, omega):
            supply_sum = sum(m.x[ii,jj] for (ii,jj) in m.IJ if jj==j)
            return supply_sum + m.s[j,omega] - m.w[j,omega] == d.get((omega,j), 0.0)

        model.balance = pyo.Constraint(model.J, model.W, rule=balance)

        def supply_cap(m, i, j):
            return m.x[i,j] <= cap.get((i,j), 0.0)

        model.supply_cap = pyo.Constraint(model.IJ, rule=supply_cap)

        solver_factory = SolverFactory("appsi_highs" if self.solver == "highs" else self.solver)
        solver_factory.options["time_limit"] = self.time_limit_s
        results = solver_factory.solve(model, tee=False)

        status = str(results.solver.termination_condition)
        obj_val = pyo.value(model.obj) if status in ("optimal","locallyOptimal") else None

        return {
            "status": status,
            "objective": obj_val,
            "x": {k: pyo.value(v) for k, v in model.x.items()},
            "spot": {(j,w): pyo.value(model.s[j,w]) for j in model.J for w in model.W},
            "waste": {(j,w): pyo.value(model.w[j,w]) for j in model.J for w in model.W},
            "eta": pyo.value(model.eta),
            "cvar_95": pyo.value(model.eta) + (
                1.0 / ((1-self.alpha)*len(scenarios))
                * sum(pyo.value(model.z[w]) for w in model.W)
            ) if obj_val is not None else None,
            "lambda": self.lambda_weight,
            "alpha": self.alpha,
            "model": model,
        }

    @classmethod
    def lambda_sweep(
        cls,
        lambdas: list[float],
        demand_scenarios: pd.DataFrame,
        supply: pd.DataFrame,
        alpha: float = 0.95,
        **kwargs,
    ) -> pd.DataFrame:
        """Trace the mean-CVaR efficient frontier over λ values."""
        rows = []
        for lam in lambdas:
            solver = cls(lambda_weight=lam, alpha=alpha, **kwargs)
            result = solver.solve(demand_scenarios, supply)
            rows.append({
                "lambda": lam,
                "objective": result["objective"],
                "status": result["status"],
                "cvar_95": result.get("cvar_95"),
            })
        return pd.DataFrame(rows)
