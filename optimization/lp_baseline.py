"""Deterministic LP baseline: minimize cost subject to demand and supply constraints.

This is the benchmark (EV solution) against which stochastic models are measured.

Formulation
-----------
    min  Σ commit_cost · x + Σ spot_cost · s + Σ waste_cost · w + Σ lost_sale_cost · u
    s.t.
      Σ_i x_ijt + s_jt - w_jt + u_jt = d_jt        ∀ j,t   (demand balance with unmet)
      s_jt ≤ ρ · d_jt                                ∀ j,t   (spot ration if ρ < ∞)
      x_ijt ≤ Y_ijt                                  ∀ i,j,t (supply capacity)
      x, s, w, u ≥ 0

The `u` (unmet demand) and spot-cap constraint together force the optimizer to
internalize the cost of poor service: it can no longer over-rely on infinite spot.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import pandas as pd


@dataclass
class LPBaseline:
    spot_cost_multiplier: float = 1.30  # contract price × multiplier for spot buys
    waste_cost_per_kg: float = 0.50            # flat fallback waste penalty $/kg
    lost_sale_per_kg_usd: float = 2.50    # flat fallback unmet penalty $/kg
    # B6 honest per-product penalties (optional; None reproduces flat behavior).
    waste_cost_by_product: dict | None = None
    unmet_cost_by_product: dict | None = None
    # Phase 0.9 newsvendor-correct objective (see TwoStageStochasticLP).
    # Default False reproduces the original flat double-count path exactly.
    newsvendor_objective: bool = False
    spot_capacity_factor: float | None = None  # cap spot at ρ × demand; None = unlimited
    solver: str = "highs"
    time_limit_s: float = 120.0

    def solve(
        self,
        demand: pd.DataFrame,          # [product_id, week_start, demand_kg]
        supply: pd.DataFrame,          # [supplier_id, product_id, week_start, capacity_kg, price_per_kg]
        contracts: pd.DataFrame | None = None,  # [supplier_id, product_id, min_vol_kg, max_vol_kg, contracted_price_per_kg]
    ) -> dict:
        """Solve deterministic LP. Returns dict with objective, variables, status."""
        import pyomo.environ as pyo
        from pyomo.opt import SolverFactory

        demand = demand.copy()
        supply = supply.copy()

        products = list(demand["product_id"].unique())
        weeks = sorted(demand["week_start"].unique())
        suppliers = list(supply["supplier_id"].unique())

        # Index helpers
        d = {(r["product_id"], r["week_start"]): r["demand_kg"]
             for _, r in demand.iterrows()}
        cap = {(r["supplier_id"], r["product_id"], r["week_start"]): r["capacity_kg"]
               for _, r in supply.iterrows()}
        price = {(r["supplier_id"], r["product_id"], r["week_start"]): r["price_per_kg"]
                 for _, r in supply.iterrows()}

        # Reference price per product, used to price SPOT purchases.
        # Previously the spot terms looked up price[(None, j, t)] — a key that
        # can never exist, since the dict is keyed by real supplier ids. Every
        # spot purchase therefore silently priced at the 2.0 fallback. With
        # real contract prices above 2.0 that made spot look cheaper than any
        # contract, so the LP committed nothing and bought everything on spot.
        _by_product: dict[str, list[float]] = {}
        for (_i, j, _t), p in price.items():
            _by_product.setdefault(j, []).append(float(p))
        avg_price = {j: (sum(v) / len(v)) for j, v in _by_product.items()}

        def _spot_price(j) -> float:
            return avg_price.get(j, 2.0)

        # NOTE: the `contracts` argument is currently advisory — the LP does not
        # yet enforce contract min/max volume bounds or contracted prices in the
        # objective. Surface this clearly rather than silently dropping the data.
        if contracts is not None and not contracts.empty:
            warnings.warn(
                "LPBaseline received a `contracts` DataFrame but does not yet enforce "
                "contract min/max volume or contracted prices. Treat the result as a "
                "best-effort baseline; pass contracts=None to silence this warning.",
                UserWarning,
                stacklevel=2,
            )

        model = pyo.ConcreteModel()
        model.I = pyo.Set(initialize=suppliers)
        model.J = pyo.Set(initialize=products)
        model.T = pyo.Set(initialize=weeks)
        model.IJT = pyo.Set(
            initialize=[(i,j,t) for (i,j,t) in cap],
            dimen=3,
        )

        # Decision variables
        model.x = pyo.Var(model.IJT, domain=pyo.NonNegativeReals)         # commit
        model.s = pyo.Var(model.J, model.T, domain=pyo.NonNegativeReals)   # spot
        model.w = pyo.Var(model.J, model.T, domain=pyo.NonNegativeReals)   # waste
        model.u = pyo.Var(model.J, model.T, domain=pyo.NonNegativeReals)   # unmet (lost sale)

        # Objective: commit + spot + waste + unmet penalty
        # Per-product penalty lookups (B6); flat fallback when no map supplied.
        cw = self.waste_cost_by_product or {}
        cu = self.unmet_cost_by_product or {}
        def _cw(j):
            return cw.get(j, self.waste_cost_per_kg)

        def _cu(j):
            return cu.get(j, self.lost_sale_per_kg_usd)

        def obj_rule(m):
            if self.newsvendor_objective:
                # Newsvendor recourse economics: no procurement charge on
                # committed-and-sold units; only overage, underage, spot premium.
                spot_prem = sum(
                    _spot_price(j) * (self.spot_cost_multiplier - 1.0) * m.s[j,t]
                    for j in m.J for t in m.T
                )
                overage = sum(_cw(j) * m.w[j,t] for j in m.J for t in m.T)
                underage = sum(_cu(j) * m.u[j,t] for j in m.J for t in m.T)
                return spot_prem + overage + underage
            # Original flat / double-count path (preserved behind the flag).
            commit_cost = sum(
                price.get((i,j,t), 2.0) * m.x[i,j,t]
                for (i,j,t) in m.IJT
            )
            spot_cost = sum(
                _spot_price(j) * self.spot_cost_multiplier * m.s[j,t]
                for j in m.J for t in m.T
            )
            waste_cost = sum(_cw(j) * m.w[j,t] for j in m.J for t in m.T)
            lost_sale_cost = sum(_cu(j) * m.u[j,t] for j in m.J for t in m.T)
            return commit_cost + spot_cost + waste_cost + lost_sale_cost

        model.obj = pyo.Objective(rule=obj_rule, sense=pyo.minimize)

        # Demand balance with unmet slack
        def demand_balance(m, j, t):
            supply_sum = sum(m.x[i2,j2,t2] for (i2,j2,t2) in m.IJT if j2 == j and t2 == t)
            return supply_sum + m.s[j,t] - m.w[j,t] + m.u[j,t] == d.get((j,t), 0.0)

        model.demand_balance = pyo.Constraint(model.J, model.T, rule=demand_balance)

        # Supply capacity
        def supply_cap(m, i, j, t):
            return m.x[i,j,t] <= cap.get((i,j,t), 0.0)

        model.supply_cap = pyo.Constraint(model.IJT, rule=supply_cap)

        # Spot capacity (when configured): s_jt ≤ ρ · d_jt
        if self.spot_capacity_factor is not None:
            ρ = float(self.spot_capacity_factor)

            def spot_cap_rule(m, j, t):
                return m.s[j,t] <= ρ * d.get((j,t), 0.0)

            model.spot_cap = pyo.Constraint(model.J, model.T, rule=spot_cap_rule)

        solver = SolverFactory("appsi_highs" if self.solver == "highs" else self.solver)
        from optimization.solve_status import highs_options
        results = solver.solve(model, tee=False, options=highs_options() if self.solver == "highs" else {})

        status = str(results.solver.termination_condition)
        obj_val = pyo.value(model.obj) if status in ("optimal","locallyOptimal") else None

        # Extract solution
        x_vals = {k: pyo.value(v) for k, v in model.x.items()}
        s_vals = {(j,t): pyo.value(model.s[j,t]) for j in model.J for t in model.T}
        w_vals = {(j,t): pyo.value(model.w[j,t]) for j in model.J for t in model.T}
        u_vals = {(j,t): pyo.value(model.u[j,t]) for j in model.J for t in model.T}

        return {
            "status": status,
            "objective": obj_val,
            "x": x_vals,
            "spot": s_vals,
            "waste": w_vals,
            "unmet": u_vals,
            "model": model,
        }

    def to_commitments_df(self, result: dict, supply: pd.DataFrame) -> pd.DataFrame:
        """Convert solver result to commitment DataFrame."""
        rows = []
        price_map = {(r["supplier_id"],r["product_id"],r["week_start"]): r["price_per_kg"]
                     for _, r in supply.iterrows()}
        for (i,j,t), qty in result["x"].items():
            if qty is None or qty < 1e-6:
                continue
            rows.append({
                "supplier_id": i, "product_id": j, "week_start": t,
                "committed_kg": round(qty, 2),
                "contract_kg": round(qty, 2),
                "spot_kg": 0.0,
                "wasted_kg": 0.0,
                "price_per_kg": price_map.get((i,j,t)),
                "decision_stage": "first",
            })
        for (j,t), qty in result["spot"].items():
            if qty is None or qty < 1e-6:
                continue
            rows.append({
                "supplier_id": "SPOT", "product_id": j, "week_start": t,
                "committed_kg": round(qty, 2),
                "contract_kg": 0.0,
                "spot_kg": round(qty, 2),
                "wasted_kg": 0.0,
                "price_per_kg": None,
                "decision_stage": "recourse",
            })
        return pd.DataFrame(rows)
