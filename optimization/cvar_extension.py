"""Mean-CVaR extension to the stochastic program.

Objective:  min  λ·E[total cost] + (1−λ)·CVaR_α[total cost]

Rockafellar & Uryasev (2000), "Optimization of conditional value-at-risk,"
*Journal of Risk* 2(3):21-42, show CVaR admits an exact LP representation
via an auxiliary variable η (which optimises to the VaR):

    CVaR_α[Z] = min_η { η + 1/(1−α) · E[(Z − η)⁺] }

so with scenario probabilities p_ω and z_ω ≥ Z_ω − η, z_ω ≥ 0:

    CVaR_α[Z] = η + 1/(1−α) · Σ_ω p_ω · z_ω

Three corrections applied to the earlier implementation, each a real defect
rather than a refinement:

1. The CVaR term averaged with a uniform 1/N instead of the scenario
   probabilities p_ω, while the expected-cost term used p_ω. Whenever the
   weights are non-uniform — exactly what `scenario_reduction` produces —
   the risk term was simply the wrong estimator.

2. The first-stage cost sat inside the expectation term but not the CVaR
   term. Since c'x is deterministic, CVaR(c'x + Q) = c'x + CVaR(Q), so
   omitting it under-weighted the procurement cost by a factor λ and biased
   the model toward over-committing whenever λ < 1.

3. There was no unmet-demand variable, so the model could not represent a
   lost sale at all — it was forced to buy spot at any price. The main
   two-stage model has always had one; the risk-averse variant silently did
   not, which made the two incomparable.

The per-product penalties and the newsvendor objective flag are also
supported here now, so switching risk preference no longer silently
switches cost model.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from optimization.two_stage_sp import _normalized_weights


@dataclass
class CVaRStochasticLP:
    alpha: float = 0.95             # CVaR tail level
    lambda_weight: float = 0.50     # 1 = pure expected cost, 0 = pure CVaR
    spot_cost_multiplier: float = 1.30
    waste_cost_per_kg: float = 0.50
    lost_sale_per_kg_usd: float = 2.50
    waste_cost_by_product: dict | None = None
    unmet_cost_by_product: dict | None = None
    newsvendor_objective: bool = False
    spot_capacity_factor: float | None = None
    solver: str = "highs"
    time_limit_s: float = 300.0

    def solve(
        self,
        demand_scenarios: pd.DataFrame,
        supply: pd.DataFrame,
        yield_scenarios: dict | None = None,
    ) -> dict:
        """Solve the mean-CVaR stochastic program."""
        import pyomo.environ as pyo
        from pyomo.opt import SolverFactory

        dem = (
            demand_scenarios
            .groupby(["scenario_index", "scenario_weight", "product_id"])["demand_kg"]
            .sum()
            .reset_index()
        )
        sup = (
            supply.groupby(["supplier_id", "product_id"])
            .agg(capacity_kg=("capacity_kg", "sum"),
                 price_per_kg=("price_per_kg", "mean"))
            .reset_index()
        )

        scenarios = sorted(dem["scenario_index"].unique())
        products = list(dem["product_id"].unique())
        suppliers = list(sup["supplier_id"].unique())

        raw_weights = {int(r["scenario_index"]): float(r["scenario_weight"])
                       for _, r in dem.drop_duplicates("scenario_index").iterrows()}
        weights = _normalized_weights(raw_weights, scenarios)

        d = {(int(r["scenario_index"]), r["product_id"]): float(r["demand_kg"])
             for _, r in dem.iterrows()}
        cap = {(r["supplier_id"], r["product_id"]): float(r["capacity_kg"])
               for _, r in sup.iterrows()}
        price = {(r["supplier_id"], r["product_id"]): float(r["price_per_kg"])
                 for _, r in sup.iterrows()}
        avg_price = {j: float(np.mean([v for (_i, j2), v in price.items() if j2 == j]
                                      or [2.0]))
                     for j in products}

        model = pyo.ConcreteModel()
        model.I = pyo.Set(initialize=suppliers)
        model.J = pyo.Set(initialize=products)
        model.W = pyo.Set(initialize=scenarios)
        model.IJ = pyo.Set(initialize=list(cap.keys()), dimen=2)

        model.x = pyo.Var(model.IJ, domain=pyo.NonNegativeReals)
        model.s = pyo.Var(model.J, model.W, domain=pyo.NonNegativeReals)
        model.w = pyo.Var(model.J, model.W, domain=pyo.NonNegativeReals)
        model.u = pyo.Var(model.J, model.W, domain=pyo.NonNegativeReals)

        # Rockafellar-Uryasev auxiliaries. eta is free: it converges to VaR.
        model.eta = pyo.Var(domain=pyo.Reals)
        model.z = pyo.Var(model.W, domain=pyo.NonNegativeReals)

        cw = self.waste_cost_by_product or {}
        cu = self.unmet_cost_by_product or {}
        _cw = lambda j: cw.get(j, self.waste_cost_per_kg)          # noqa: E731
        _cu = lambda j: cu.get(j, self.lost_sale_per_kg_usd)       # noqa: E731

        # Deterministic first-stage cost. Zero under the newsvendor objective,
        # where committed-and-sold units are economically neutral.
        if self.newsvendor_objective:
            first_stage_cost = 0.0
            spot_rate = {j: avg_price[j] * (self.spot_cost_multiplier - 1.0)
                         for j in products}
        else:
            first_stage_cost = sum(price.get((i, j), 2.0) * model.x[i, j]
                                   for (i, j) in model.IJ)
            spot_rate = {j: avg_price[j] * self.spot_cost_multiplier
                         for j in products}

        def recourse_cost(m, omega):
            """Scenario-dependent (stage-2) cost only."""
            return (
                sum(spot_rate[j] * m.s[j, omega] for j in m.J)
                + sum(_cw(j) * m.w[j, omega] for j in m.J)
                + sum(_cu(j) * m.u[j, omega] for j in m.J)
            )

        def obj_rule(m):
            exp_recourse = sum(weights[omega] * recourse_cost(m, omega)
                               for omega in m.W)
            # Probability-weighted CVaR of the recourse cost.
            cvar_recourse = m.eta + (1.0 / (1.0 - self.alpha)) * sum(
                weights[omega] * m.z[omega] for omega in m.W)
            # first_stage_cost is deterministic, so it enters BOTH terms
            # identically and factors out of the convex combination.
            return (first_stage_cost
                    + self.lambda_weight * exp_recourse
                    + (1.0 - self.lambda_weight) * cvar_recourse)

        model.obj = pyo.Objective(rule=obj_rule, sense=pyo.minimize)

        def cvar_cut(m, omega):
            return m.z[omega] >= recourse_cost(m, omega) - m.eta

        model.cvar_cut = pyo.Constraint(model.W, rule=cvar_cut)

        ys = yield_scenarios or {}

        def _fill(omega, i) -> float:
            return float(ys.get((omega, i), 1.0))

        def balance(m, j, omega):
            supply_sum = sum(_fill(omega, ii) * m.x[ii, jj]
                             for (ii, jj) in m.IJ if jj == j)
            return (supply_sum + m.s[j, omega] - m.w[j, omega] + m.u[j, omega]
                    == d.get((omega, j), 0.0))

        model.balance = pyo.Constraint(model.J, model.W, rule=balance)

        def supply_cap(m, i, j):
            return m.x[i, j] <= cap.get((i, j), 0.0)

        model.supply_cap = pyo.Constraint(model.IJ, rule=supply_cap)

        if self.spot_capacity_factor is not None:
            rho = float(self.spot_capacity_factor)

            def spot_cap_rule(m, j, omega):
                return m.s[j, omega] <= rho * d.get((omega, j), 0.0)

            model.spot_cap = pyo.Constraint(model.J, model.W, rule=spot_cap_rule)

        solver_factory = SolverFactory(
            "appsi_highs" if self.solver == "highs" else self.solver)
        solver_factory.options["time_limit"] = self.time_limit_s
        if self.solver == "highs":
            from optimization.solve_status import highs_options
            solver_factory.options.update(highs_options())
        results = solver_factory.solve(model, tee=False)

        status = str(results.solver.termination_condition)
        solved = status in ("optimal", "locallyOptimal")
        obj_val = pyo.value(model.obj) if solved else None

        cvar_value = None
        expected_cost = None
        if solved:
            cvar_value = float(
                pyo.value(model.eta)
                + (1.0 / (1.0 - self.alpha))
                * sum(weights[w] * pyo.value(model.z[w]) for w in model.W))
            fs = (float(pyo.value(first_stage_cost))
                  if not self.newsvendor_objective else 0.0)
            expected_cost = fs + float(sum(
                weights[w] * pyo.value(recourse_cost(model, w))
                for w in model.W))
            cvar_value += fs

        return {
            "status": status,
            "objective": obj_val,
            "x": {k: pyo.value(v) for k, v in model.x.items()},
            "spot": {(j, w): pyo.value(model.s[j, w])
                     for j in model.J for w in model.W},
            "waste": {(j, w): pyo.value(model.w[j, w])
                      for j in model.J for w in model.W},
            "unmet": {(j, w): pyo.value(model.u[j, w])
                      for j in model.J for w in model.W},
            "eta_var": pyo.value(model.eta) if solved else None,
            # Named for the actual alpha, not a hardcoded 95.
            "cvar": cvar_value,
            "expected_cost": expected_cost,
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
        """Trace the mean-CVaR efficient frontier over λ.

        Reports expected cost and CVaR separately so the trade-off is
        visible: as λ falls the plan should accept higher expected cost in
        exchange for a lighter tail.
        """
        rows = []
        for lam in lambdas:
            solver = cls(lambda_weight=lam, alpha=alpha, **kwargs)
            result = solver.solve(demand_scenarios, supply)
            rows.append({
                "lambda": lam,
                "objective": result["objective"],
                "status": result["status"],
                "expected_cost": result.get("expected_cost"),
                "cvar": result.get("cvar"),
                "var": result.get("eta_var"),
            })
        return pd.DataFrame(rows)
