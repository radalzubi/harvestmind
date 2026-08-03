"""Γ-robust LP under demand uncertainty (Bertsimas-Sim budget of uncertainty).

Reference
---------
Bertsimas, D. & Sim, M. (2004). "The Price of Robustness."
*Operations Research* 52(1):35-53. doi:10.1287/opre.1030.0065
Soyster, A.L. (1973). "Convex programming with set-inclusive constraints
and applications to inexact linear programming." *Operations Research*
21(5):1154-1157. — the fully-conservative extreme (Γ = |J|).

THE IDEA
--------
Protecting against every uncertain parameter hitting its worst case at once
(Soyster) is far too conservative: in practice not everything goes wrong
simultaneously. Bertsimas and Sim introduce a *budget of uncertainty* Γ —
protect against at most Γ parameters deviating adversarially, with a
fractional allowance for the (Γ+1)-th. Γ = 0 recovers the nominal problem;
Γ = |J| recovers Soyster.

WHAT WAS WRONG BEFORE
---------------------
The previous implementation spread the budget UNIFORMLY across every
product-week:

    gamma_factor = min(1, Γ / (J·T))
    elevated_d = d · (1 + gamma_factor · uncertainty_pct)

and documented itself as "mathematically equivalent to a Bertsimas-Sim
Γ-robust counterpart." It is not. Uniform spreading protects a little
against everything; the Bertsimas-Sim counterpart protects FULLY against
the Γ worst deviations and not at all against the rest. Those differ
whenever deviations are unequal in magnitude — which is the normal case,
since the deviation of each product scales with its own demand. The uniform
version systematically under-protects the large-demand products that
actually drive cost, while spending budget on small ones that do not.

Here Γ is allocated the way the theory says: sort the per-constraint
deviations, elevate the ⌊Γ⌋ largest fully, and give the next one the
fractional remainder Γ − ⌊Γ⌋.

PROBABILISTIC GUARANTEE
-----------------------
Bertsimas & Sim, Theorem 2: if deviations are independent and symmetrically
distributed, the probability that a protected constraint is violated is
bounded by

    Pr(violation) <= exp(-Γ² / (2·n))       n = number of uncertain
                                              parameters in the constraint

``violation_probability_bound`` exposes this so the robustness level can be
chosen from a target risk rather than by taste. Note the assumptions: the
bound needs INDEPENDENT deviations. Regionally correlated weather shocks
violate that, and the true violation probability is then higher than the
bound suggests — see agronomy/systemic_risk.py.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from optimization.lp_baseline import LPBaseline


def violation_probability_bound(gamma: float, n_uncertain: int) -> float:
    """Bertsimas-Sim Theorem 2 bound: Pr(violation) <= exp(-Γ²/(2n)).

    Assumes independent, symmetrically distributed deviations. Correlated
    shocks break the assumption and make the true probability higher.
    """
    if n_uncertain <= 0:
        return 0.0
    return float(min(1.0, math.exp(-(gamma ** 2) / (2.0 * n_uncertain))))


def gamma_for_target_risk(target_risk: float, n_uncertain: int) -> float:
    """Invert the bound: the Γ needed for a target violation probability.

    Γ = sqrt(-2n·ln(risk)). Lets an operator say "I want at most a 5%
    chance of being short" and get the budget, instead of guessing Γ.
    """
    if n_uncertain <= 0 or not (0.0 < target_risk < 1.0):
        return 0.0
    return float(math.sqrt(-2.0 * n_uncertain * math.log(target_risk)))


@dataclass
class GammaRobustLP:
    gamma: float = 4.0
    demand_uncertainty_pct: float = 0.20
    spot_cost_multiplier: float = 1.30
    waste_cost_per_kg: float = 0.50
    lost_sale_per_kg_usd: float = 2.50
    # Pass-throughs that were previously dropped, silently forcing this
    # variant onto the flat double-count cost model while the two-stage
    # model could use per-product penalties. Comparisons across variants
    # were therefore not like-for-like.
    waste_cost_by_product: dict | None = None
    unmet_cost_by_product: dict | None = None
    newsvendor_objective: bool = False
    spot_capacity_factor: float | None = None
    solver: str = "highs"
    time_limit_s: float = 180.0

    def _elevated_demand(self, demand: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
        """Apply the budget to the Γ largest deviations (Bertsimas-Sim)."""
        elevated = demand.copy().reset_index(drop=True)
        deviations = (elevated["demand_kg"].to_numpy(dtype=float)
                      * float(self.demand_uncertainty_pct))
        n = len(deviations)
        gamma = float(np.clip(self.gamma, 0.0, n))

        # Allocation vector: 1.0 for the floor(Γ) largest deviations, the
        # fractional remainder for the next, 0 elsewhere.
        alloc = np.zeros(n, dtype=float)
        if gamma > 0 and n > 0:
            order = np.argsort(-deviations)          # largest deviation first
            full = int(math.floor(gamma))
            alloc[order[:full]] = 1.0
            frac = gamma - full
            if frac > 1e-12 and full < n:
                alloc[order[full]] = frac

        elevated["demand_kg"] = elevated["demand_kg"] + alloc * deviations
        meta = {
            "gamma": self.gamma,
            "gamma_effective": gamma,
            "n_uncertain": n,
            "n_fully_protected": int(np.sum(alloc >= 1.0 - 1e-12)),
            "total_protection_kg": float(np.sum(alloc * deviations)),
            "violation_probability_bound": violation_probability_bound(gamma, n),
        }
        return elevated, meta

    def solve(
        self,
        demand: pd.DataFrame,
        supply: pd.DataFrame,
        contracts: pd.DataFrame | None = None,
    ) -> dict:
        """Solve the Γ-robust LP by elevating the Γ worst-case deviations."""
        elevated, meta = self._elevated_demand(demand)

        det_solver = LPBaseline(
            spot_cost_multiplier=self.spot_cost_multiplier,
            waste_cost_per_kg=self.waste_cost_per_kg,
            lost_sale_per_kg_usd=self.lost_sale_per_kg_usd,
            waste_cost_by_product=self.waste_cost_by_product,
            unmet_cost_by_product=self.unmet_cost_by_product,
            newsvendor_objective=self.newsvendor_objective,
            spot_capacity_factor=self.spot_capacity_factor,
            solver=self.solver,
            time_limit_s=self.time_limit_s,
        )
        result = det_solver.solve(elevated, supply, contracts)
        result.update(meta)
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
        """Solve across Γ values — the price-of-robustness frontier.

        Reports the violation-probability bound alongside cost so the
        trade-off is legible: what does each increment of protection buy,
        and what does it cost.
        """
        rows = []
        for g in gammas:
            solver = cls(gamma=g, **kwargs)
            result = solver.solve(demand, supply, contracts)
            total_spot = sum(v for v in result.get("spot", {}).values()
                             if v and v > 0)
            rows.append({
                "gamma": g,
                "objective": result.get("objective"),
                "status": result.get("status"),
                "total_spot_kg": total_spot,
                "n_fully_protected": result.get("n_fully_protected"),
                "total_protection_kg": result.get("total_protection_kg"),
                "violation_probability_bound": result.get(
                    "violation_probability_bound"),
            })
        return pd.DataFrame(rows)
