"""Γ-robust LP under demand uncertainty.

Robust counterpart to the deterministic supply LP that hedges against demand
uncertainty by elevating the demand constraint. As Γ grows, the model commits
to more supply to absorb worst-case demand spikes — paying a robustness premium
in exchange for higher service-level guarantees.

Formulation
-----------
Let d̂_jt = mean demand and d̂_dev_jt = uncertainty radius (a fraction of d̂_jt).
We parameterize Γ as a budget that scales between 0 (nominal demand) and
N (full worst-case demand for every product in every period). Concretely:

    γ_factor(Γ) = min(1, Γ / max(1, J × T))   — the per-period worst-case fraction
    elevated_d_jt = d̂_jt + γ_factor · d̂_dev_jt

The LP then solves the deterministic baseline on `elevated_d_jt`. This is
mathematically equivalent to a Bertsimas-Sim Γ-robust counterpart for
single-uncertainty-per-constraint demand uncertainty, projected to the
nominal-LP feasible set with adjusted RHS.

Properties
- Γ = 0          → identical to deterministic LP
- Γ ≥ J × T      → full worst-case (γ_factor = 1)
- monotone       → cost is non-decreasing in Γ
- no arbitrage   → no auxiliary "free supply" variables
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from optimization.lp_baseline import LPBaseline


@dataclass
class GammaRobustLP:
    gamma: float = 4.0
    demand_uncertainty_pct: float = 0.20
    spot_cost_multiplier: float = 1.30
    waste_cost_per_kg: float = 0.50
    lost_sale_per_kg_usd: float = 2.50
    spot_capacity_factor: float | None = None
    solver: str = "highs"
    time_limit_s: float = 180.0

    def solve(
        self,
        demand: pd.DataFrame,
        supply: pd.DataFrame,
        contracts: pd.DataFrame | None = None,
    ) -> dict:
        """Solve Γ-robust LP via demand-elevation projection."""
        n_products = max(1, demand["product_id"].nunique())
        n_weeks = max(1, demand["week_start"].nunique())
        n_constraints = n_products * n_weeks

        gamma_factor = min(1.0, self.gamma / n_constraints) if self.gamma > 0 else 0.0

        elevated = demand.copy()
        elevated["demand_kg"] = (
            elevated["demand_kg"] * (1.0 + gamma_factor * self.demand_uncertainty_pct)
        )

        det_solver = LPBaseline(
            spot_cost_multiplier=self.spot_cost_multiplier,
            waste_cost_per_kg=self.waste_cost_per_kg,
            lost_sale_per_kg_usd=self.lost_sale_per_kg_usd,
            spot_capacity_factor=self.spot_capacity_factor,
            solver=self.solver,
            time_limit_s=self.time_limit_s,
        )
        result = det_solver.solve(elevated, supply, contracts)
        result["gamma"] = self.gamma
        result["gamma_factor"] = gamma_factor
        return result

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
            total_spot = sum(v for v in result.get("spot", {}).values() if v and v > 0)
            rows.append({
                "gamma": g,
                "objective": result.get("objective"),
                "status": result.get("status"),
                "total_spot_kg": total_spot,
                "gamma_factor": result.get("gamma_factor"),
            })
        return pd.DataFrame(rows)
