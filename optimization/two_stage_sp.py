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
    waste_cost_per_kg: float = 0.50            # flat fallback waste penalty $/kg
    lost_sale_per_kg_usd: float = 2.50         # flat fallback unmet penalty $/kg
    # B6 honest per-product penalties (optional). When provided, override the
    # flat scalars per product: waste = unit cost, unmet = lost margin.
    # Leave as None to reproduce the original flat-penalty behavior.
    waste_cost_by_product: dict | None = None
    unmet_cost_by_product: dict | None = None
    # Phase 0.9 — newsvendor-correct objective. When True, the objective drops
    # the procurement charge on committed-and-sold units (the double-count bug)
    # and uses pure overage/underage recourse economics:
    #   overage (committed-but-wasted) = waste_cost_by_product[j]  (unit cost − salvage)
    #   underage (unmet demand)        = unmet_cost_by_product[j]  (lost margin)
    #   spot covers underage at PREMIUM only: avg_price·(multiplier − 1)
    #   committed-and-sold units carry NO penalty (the neutral, profitable case)
    # Default False reproduces the original flat double-count path exactly.
    newsvendor_objective: bool = False
    spot_capacity_factor: float | None = None  # cap stage-2 spot at ρ × demand_jω; None = unlimited
    # Operator-interpretable constraints (Phase 4). None = off.
    # service_level_floor: per product, expected unmet ≤ (1−floor) × expected
    # demand — "serve at least this fraction of demand in expectation".
    service_level_floor: float | None = None
    # diversification_cap: no supplier may carry more than this share of a
    # product's total commitment (applied only where ≥2 suppliers offer the
    # product and the cap is feasible, i.e. cap ≥ 1/n_suppliers).
    diversification_cap: float | None = None
    solver: str = "highs"
    time_limit_s: float = 300.0
    n_scenarios: int = 100

    def solve(
        self,
        demand_scenarios: pd.DataFrame,   # [scenario_index, scenario_weight, product_id, week_start, demand_kg]
        supply: pd.DataFrame,             # [supplier_id, product_id, week_start, capacity_kg, price_per_kg]
        aggregate_weeks: bool = True,     # collapse multi-week demand to single planning period
        yield_scenarios: dict | None = None,  # (scenario_index, supplier_id) -> fill in [0,1]
    ) -> dict:
        """Solve two-stage SP extensive form. Returns result dict.

        ``yield_scenarios`` makes the model genuinely TWO-SIDED: the
        commitment x_ij is made before BOTH demand and supplier yield
        resolve. Per scenario ω the delivered quantity is fill_ω(i)·x_ij
        (proportional yield draw from the supplier's predictive Beta), so
        the demand balance becomes Σ_i fill_ω(i)·x_ij + s − w + u = d_jω.
        ``None`` keeps the one-sided model (fill ≡ 1), preserving all
        existing behavior. The model remains a pure LP either way — the
        fill draws enter as coefficients, not variables.
        """
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
        model.s = pyo.Var(model.J, model.W, domain=pyo.NonNegativeReals)   # spot
        model.w = pyo.Var(model.J, model.W, domain=pyo.NonNegativeReals)   # waste
        model.u = pyo.Var(model.J, model.W, domain=pyo.NonNegativeReals)   # unmet

        # Per-product penalty lookups (B6). Fall back to the flat scalar when no
        # per-product map is supplied — reproduces the original behavior exactly.
        cw = self.waste_cost_by_product or {}
        cu = self.unmet_cost_by_product or {}
        _cw = lambda j: cw.get(j, self.waste_cost_per_kg)
        _cu = lambda j: cu.get(j, self.lost_sale_per_kg_usd)

        def obj_rule(m):
            if self.newsvendor_objective:
                # Newsvendor recourse economics: no procurement charge on
                # committed units (sold units are neutral); only overage,
                # underage, and the spot PREMIUM are costs.
                return sum(
                    weights.get(omega, 1.0/len(scenarios)) * (
                        sum(avg_price[j] * (self.spot_cost_multiplier - 1.0) * m.s[j,omega] for j in m.J)
                        + sum(_cw(j) * m.w[j,omega] for j in m.J)   # overage = unit cost − salvage
                        + sum(_cu(j) * m.u[j,omega] for j in m.J)   # underage = lost margin
                    )
                    for omega in m.W
                )
            # Original flat / double-count path (preserved behind the flag).
            first_stage = sum(price.get((i,j), 2.0) * m.x[i,j] for (i,j) in m.IJ)
            second_stage = sum(
                weights.get(omega, 1.0/len(scenarios)) * (
                    sum(avg_price[j] * self.spot_cost_multiplier * m.s[j,omega] for j in m.J)
                    + sum(_cw(j) * m.w[j,omega] for j in m.J)
                    + sum(_cu(j) * m.u[j,omega] for j in m.J)
                )
                for omega in m.W
            )
            return first_stage + second_stage

        model.obj = pyo.Objective(rule=obj_rule, sense=pyo.minimize)

        # Per-scenario supplier fill coefficients (two-sided uncertainty).
        # fill defaults to 1.0 — the one-sided model — when no yield
        # scenarios are supplied or a (scenario, supplier) pair is missing.
        ys = yield_scenarios or {}

        def _fill(omega, i) -> float:
            return float(ys.get((omega, i), 1.0))

        # Demand balance per scenario, with unmet slack
        def balance(m, j, omega):
            supply_sum = sum(_fill(omega, ii) * m.x[ii,jj]
                             for (ii,jj) in m.IJ if jj==j)
            return supply_sum + m.s[j,omega] - m.w[j,omega] + m.u[j,omega] == d.get((omega,j), 0.0)

        model.balance = pyo.Constraint(model.J, model.W, rule=balance)

        # Supply capacity (stage-1 variable bounded by available supply)
        def supply_cap(m, i, j):
            return m.x[i,j] <= cap.get((i,j), 0.0)

        model.supply_cap = pyo.Constraint(model.IJ, rule=supply_cap)

        # Service-level floor: expected unmet ≤ (1 − floor) × expected demand,
        # per product. Operator-readable: "serve at least `floor` of demand
        # in expectation."
        if self.service_level_floor is not None:
            floor = float(self.service_level_floor)

            def service_rule(m, j):
                exp_unmet = sum(weights.get(w_, 1.0/len(scenarios)) * m.u[j, w_]
                                for w_ in m.W)
                exp_demand = sum(weights.get(w_, 1.0/len(scenarios))
                                 * d.get((w_, j), 0.0) for w_ in m.W)
                return exp_unmet <= (1.0 - floor) * exp_demand

            model.service_floor = pyo.Constraint(model.J, rule=service_rule)

        # Supplier-diversification cap: x_ij ≤ cap_share × Σ_i' x_i'j.
        # Applied only where the product has ≥2 suppliers AND the cap is
        # feasible (cap ≥ 1/n) — otherwise it would force x to zero or be
        # unsatisfiable, which is not what an operator means by it.
        if self.diversification_cap is not None:
            share = float(self.diversification_cap)
            suppliers_by_product: dict = {}
            for (i, j) in cap:
                suppliers_by_product.setdefault(j, []).append(i)
            constrained = [
                (i, j) for j, sup_list in suppliers_by_product.items()
                if len(sup_list) >= 2 and share >= 1.0 / len(sup_list) - 1e-9
                for i in sup_list
            ]
            if constrained:
                model.DIV = pyo.Set(initialize=constrained, dimen=2)

                def diversify_rule(m, i, j):
                    total = sum(m.x[ii, jj] for (ii, jj) in m.IJ if jj == j)
                    return m.x[i, j] <= share * total

                model.diversify = pyo.Constraint(model.DIV, rule=diversify_rule)

        # Stage-2 spot ration: s_jω ≤ ρ · d_jω
        if self.spot_capacity_factor is not None:
            ρ = float(self.spot_capacity_factor)

            def spot_cap_rule(m, j, omega):
                return m.s[j, omega] <= ρ * d.get((omega, j), 0.0)

            model.spot_cap = pyo.Constraint(model.J, model.W, rule=spot_cap_rule)

        solver_factory = SolverFactory("appsi_highs" if self.solver == "highs" else self.solver)
        solver_factory.options["time_limit"] = self.time_limit_s
        results = solver_factory.solve(model, tee=False)

        status = str(results.solver.termination_condition)
        obj_val = pyo.value(model.obj) if status in ("optimal","locallyOptimal") else None

        x_vals = {k: pyo.value(v) for k, v in model.x.items()}
        s_vals = {(j,w): pyo.value(model.s[j,w]) for j in model.J for w in model.W}
        w_vals = {(j,w): pyo.value(model.w[j,w]) for j in model.J for w in model.W}
        u_vals = {(j,w): pyo.value(model.u[j,w]) for j in model.J for w in model.W}

        # VSS and EVPI approximations
        total_spot = sum(v * weights.get(w, 0) for (j,w), v in s_vals.items() if v and v > 0)
        total_waste = sum(v * weights.get(w, 0) for (j,w), v in w_vals.items() if v and v > 0)
        total_unmet = sum(v * weights.get(w, 0) for (j,w), v in u_vals.items() if v and v > 0)

        return {
            "status": status,
            "objective": obj_val,
            "x": x_vals,
            "spot": s_vals,
            "waste": w_vals,
            "unmet": u_vals,
            "model": model,
            "expected_spot_kg": total_spot,
            "expected_waste_kg": total_waste,
            "expected_unmet_kg": total_unmet,
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
