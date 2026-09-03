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


def _normalized_weights(weights: dict, scenarios: list) -> dict:
    """Complete and normalise scenario probabilities.

    Any scenario absent from the weight map gets the uniform share, and the
    whole vector is rescaled to sum to 1. Without this, two failure modes
    are silent: a missing weight was previously counted as 1/N inside the
    objective but as 0 when reporting expected quantities, and an
    unnormalised vector multiplies the entire "expected cost" by an
    arbitrary constant — which changes the optimal trade-off against the
    first-stage cost, not just the reported number.
    """
    n = max(len(scenarios), 1)
    filled = {int(s): float(weights.get(int(s), 1.0 / n)) for s in scenarios}
    total = sum(filled.values())
    if total <= 0:
        return {s: 1.0 / n for s in filled}
    return {s: w / total for s, w in filled.items()}


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

        # Scenario probabilities. Two things must hold and previously did
        # not: every scenario needs a weight (a missing one was counted at
        # 1/N in the objective but 0 in the reported expectations), and the
        # weights must sum to 1 or the "expected" cost is scaled by an
        # arbitrary constant. Scenario reduction produces non-uniform
        # weights, so neither can be assumed.
        weights = {int(r["scenario_index"]): float(r["scenario_weight"])
                   for _, r in demand_scenarios.drop_duplicates("scenario_index").iterrows()}
        weights = _normalized_weights(weights, scenarios)
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
        def _cw(j):
            return cw.get(j, self.waste_cost_per_kg)

        def _cu(j):
            return cu.get(j, self.lost_sale_per_kg_usd)

        def obj_rule(m):
            if self.newsvendor_objective:
                # Newsvendor recourse economics: no procurement charge on
                # committed units (sold units are neutral); only overage,
                # underage, and the spot PREMIUM are costs.
                return sum(
                    weights[omega] * (
                        sum(avg_price[j] * (self.spot_cost_multiplier - 1.0) * m.s[j,omega] for j in m.J)
                        + sum(_cw(j) * m.w[j,omega] for j in m.J)   # overage = unit cost − salvage
                        + sum(_cu(j) * m.u[j,omega] for j in m.J)   # underage = lost margin
                    )
                    for omega in m.W
                )
            # Original flat / double-count path (preserved behind the flag).
            first_stage = sum(price.get((i,j), 2.0) * m.x[i,j] for (i,j) in m.IJ)
            second_stage = sum(
                weights[omega] * (
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
                exp_unmet = sum(weights[w_] * m.u[j, w_]
                                for w_ in m.W)
                exp_demand = sum(weights[w_] * d.get((w_, j), 0.0)
                                 for w_ in m.W)
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

        # Import duals so binding supply capacities yield shadow prices:
        # the marginal objective value of one more kg of capacity at
        # supplier i for product j — operator-readable "what one more kg
        # from this supplier would be worth".
        model.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)

        from optimization.solve_status import run_solver
        outcome = run_solver(model, solver=self.solver, time_limit_s=self.time_limit_s)
        status = outcome.status
        usable = outcome.usable
        obj_val = float(pyo.value(model.obj)) if usable else None

        # An unsolved model has no decision. Returning zeros here would look
        # exactly like "commit nothing", which is a real recommendation, so
        # the dictionaries are left EMPTY and ``usable`` is False.
        if usable:
            x_vals = {k: pyo.value(v) for k, v in model.x.items()}
            s_vals = {(j,w): pyo.value(model.s[j,w]) for j in model.J for w in model.W}
            w_vals = {(j,w): pyo.value(model.w[j,w]) for j in model.J for w in model.W}
            u_vals = {(j,w): pyo.value(model.u[j,w]) for j in model.J for w in model.W}
        else:
            x_vals, s_vals, w_vals, u_vals = {}, {}, {}, {}

        # Shadow prices on supply capacity (sign-normalized: positive =
        # one more kg of capacity would reduce expected cost by this much).
        shadow_prices: dict = {}
        try:
            for (i, j) in model.IJ:
                dual = model.dual.get(model.supply_cap[i, j])
                if dual is not None and abs(dual) > 1e-9:
                    shadow_prices[(i, j)] = round(abs(float(dual)), 4)
        except Exception:  # noqa: BLE001  duals unavailable on some solvers
            shadow_prices = {}

        # VSS and EVPI approximations
        total_spot = sum(v * weights[w] for (j,w), v in s_vals.items() if v and v > 0)
        total_waste = sum(v * weights[w] for (j,w), v in w_vals.items() if v and v > 0)
        total_unmet = sum(v * weights[w] for (j,w), v in u_vals.items() if v and v > 0)

        return {
            "status": status,
            "usable": usable,
            "runtime_s": outcome.runtime_s,
            "warnings": list(outcome.warnings),
            "objective": obj_val,
            "x": x_vals,
            "spot": s_vals,
            "waste": w_vals,
            "unmet": u_vals,
            "model": model,
            "expected_spot_kg": total_spot,
            "expected_waste_kg": total_waste,
            "expected_unmet_kg": total_unmet,
            # marginal value ($/kg) of one more kg of capacity at (i, j);
            # only binding capacities appear
            "shadow_prices": shadow_prices,
        }

    def solve_with_fixed_first_stage(
        self,
        demand_scenarios: pd.DataFrame,
        supply: pd.DataFrame,
        x_fixed: dict,
        yield_scenarios: dict | None = None,
    ) -> dict:
        """Evaluate a GIVEN first-stage decision against the full scenario set.

        Fixes x to ``x_fixed`` and optimises only the recourse variables, so
        the objective returned is the expected cost of living with that
        commitment across every scenario. This is the machinery EEV needs:
        take the deterministic plan, then make it face reality.
        """
        import pyomo.environ as pyo

        result = self.solve(demand_scenarios, supply,
                            yield_scenarios=yield_scenarios)
        model = result["model"]
        for (i, j) in model.x:
            model.x[i, j].fix(float(x_fixed.get((i, j), 0.0)))

        from optimization.solve_status import run_solver
        outcome = run_solver(model, solver=self.solver, time_limit_s=self.time_limit_s)
        return {
            "status": outcome.status,
            "usable": outcome.usable,
            "warnings": list(outcome.warnings),
            "objective": float(pyo.value(model.obj)) if outcome.usable else None,
            "x": ({k: pyo.value(v) for k, v in model.x.items()}
                  if outcome.usable else {}),
        }

    def compute_vss(
        self,
        demand_scenarios: pd.DataFrame,
        supply: pd.DataFrame,
        yield_scenarios: dict | None = None,
    ) -> dict:
        """Value of the Stochastic Solution, VSS = EEV - RP.

        Definitions follow Birge & Louveaux, *Introduction to Stochastic
        Programming*:

            RP   the recourse problem — solve the full stochastic model.
            EV   the expected-value problem — replace every random variable
                 by its mean and solve that single deterministic problem.
            EEV  the *expected result of using the EV solution* — take the
                 EV problem's first-stage decision, FIX it, and evaluate its
                 expected cost over the full scenario distribution.

        VSS = EEV - RP, and VSS >= 0 always: RP optimises over all
        first-stage decisions, so it cannot be beaten by the particular
        decision EV happened to pick.

        The previous implementation returned ``EV_objective - RP``, which is
        a different and meaningless quantity. EV solves an easier problem
        (one averaged scenario instead of the true distribution), so by
        Jensen's inequality EV <= RP and that difference is typically
        NEGATIVE — it reported a negative "value" for stochastic modelling
        and made the stochastic layer look worthless. Verified on a
        deliberately asymmetric instance before the fix: -5,383.

        Returns the three objective values alongside VSS so the result can
        be audited rather than trusted.
        """
        # --- RP: the full stochastic solution -------------------------------
        rp_result = self.solve(demand_scenarios, supply,
                               yield_scenarios=yield_scenarios)
        rp_obj = rp_result.get("objective")

        # --- EV: mean-value problem, solved inside the SAME model ----------
        # Building the EV problem as a one-scenario instance of this model
        # (rather than delegating to a different LP class) keeps the
        # objective, penalties and constraints identical, so EEV and RP are
        # genuinely comparable. Mixing model classes here was part of what
        # made the old number meaningless.
        mean_demand = (
            demand_scenarios.groupby("product_id", as_index=False)["demand_kg"]
            .mean()
            .assign(scenario_index=0, scenario_weight=1.0)
        )
        if "week_start" in demand_scenarios.columns:
            mean_demand["week_start"] = demand_scenarios["week_start"].min()

        mean_yield = None
        if yield_scenarios:
            by_supplier: dict = {}
            for (_omega, i), v in yield_scenarios.items():
                by_supplier.setdefault(i, []).append(float(v))
            mean_yield = {(0, i): sum(v) / len(v) for i, v in by_supplier.items()}

        ev_result = self.solve(mean_demand, supply, yield_scenarios=mean_yield)
        ev_obj = ev_result.get("objective")

        # --- EEV: the EV decision, evaluated against every scenario --------
        eev_result = self.solve_with_fixed_first_stage(
            demand_scenarios, supply, ev_result.get("x", {}),
            yield_scenarios=yield_scenarios,
        )
        eev_obj = eev_result.get("objective")

        vss = (float(eev_obj - rp_obj)
               if (eev_obj is not None and rp_obj is not None) else None)

        return {
            "vss": vss,
            "rp_objective": rp_obj,
            "ev_objective": ev_obj,
            "eev_objective": eev_obj,
            "vss_pct_of_eev": (round(vss / eev_obj * 100, 2)
                               if vss is not None and eev_obj else None),
            "rp_status": rp_result.get("status"),
            "eev_status": eev_result.get("status"),
            "definition": "VSS = EEV - RP (Birge & Louveaux); nonnegative by construction",
            "interpretation": _interpret_vss(vss, eev_obj),
        }


def _interpret_vss(vss: float | None, eev: float | None) -> str:
    """Plain-language reading of a VSS result, including the null result."""
    if vss is None:
        return "VSS unavailable — a solve did not reach optimality."
    if eev and eev > 0:
        pct = vss / eev * 100
    else:
        pct = 0.0
    if vss < -1e-6:
        return (f"VSS is negative ({vss:,.2f}), which is impossible by "
                "construction — treat this as a modelling or solver defect, "
                "not a finding.")
    if pct < 0.5:
        return (
            f"VSS is essentially zero ({vss:,.2f}, {pct:.2f}% of EEV). The "
            "deterministic plan is already near-optimal here. Typical causes: "
            "near-symmetric overage/underage costs, uncertainty that averages "
            "out across products or suppliers, or cheap recourse (unlimited "
            "spot). Check whether shortfalls are correlated before concluding "
            "the stochastic layer is not worth running."
        )
    if pct < 5:
        return (f"VSS is modest ({vss:,.2f}, {pct:.2f}% of EEV) — the "
                "stochastic layer adds real but small value on this instance.")
    return (f"VSS is substantial ({vss:,.2f}, {pct:.2f}% of EEV) — planning "
            "against the distribution clearly beats planning against the mean.")
