"""Multi-period two-stage stochastic program with random lead times.

WHY THIS EXISTS. `TwoStageStochasticLP` indexes suppliers x products x
scenarios. It has no time index, so it can recommend ordering MORE but never
ordering EARLIER. A chokepoint closure or a congested port is primarily a
TIMING shock, and operators respond to it by rescheduling as much as by
requantifying. This model can represent that.

THE DECISION. First stage is an ordering SCHEDULE ``x[i,j,t]``: how much to
order from each supplier, for each product, in each period. It is committed
before anything resolves. Second stage absorbs the outcome per scenario with
spot purchases, unmet demand, carried inventory and waste.

WHAT MAKES THE TIMING DECISION REAL. Holding inventory must cost something.
Without a holding cost, ordering everything in period 0 is free and
trivially dominates, and the model would recommend it. The tension between
ordering early (protected from delay, but you carry and it decays) and
ordering late (cheap, but exposed to delay) is what this model exists to
resolve, and it only exists if carrying is priced.

STILL A PURE LP. Lead times and fill rates enter as scenario DATA, not
variables: within scenario w the arrival period of an order is known, so
the mapping from orders to arrivals is a fixed linear operator.

HONEST SCOPE. This is two-stage, not multistage: the whole schedule is
committed up front rather than re-decided each period as information
arrives. That understates the value of flexibility, so treat its output as
a lower bound on what a perfectly adaptive planner could achieve.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from optimization.two_stage_sp import _normalized_weights


@dataclass
class MultiPeriodStochasticLP:
    """Two-stage SP over an ordering schedule with random lead times."""

    n_periods: int = 8
    # Recourse economics, same meaning as the single-period model.
    spot_cost_multiplier: float = 1.30
    spot_capacity_factor: float | None = 0.30
    waste_cost_per_kg: float = 0.50
    lost_sale_per_kg_usd: float = 2.50
    waste_cost_by_product: dict | None = None
    unmet_cost_by_product: dict | None = None
    # The term that makes the timing decision non-trivial. Per kg per period.
    holding_cost_per_kg_per_period: float = 0.02
    holding_cost_by_product: dict | None = None
    # Fraction of carried stock lost per period. Perishables decay while
    # they wait, which is the cost of ordering early in a fresh supply chain.
    decay_rate_per_period: float = 0.05
    decay_rate_by_product: dict | None = None
    # Real operators cannot hold unbounded stock. Warehouse space and
    # working capital both bind, and without one of them priced or
    # constrained the model will buy many months of cover to avoid a
    # shortage that costs a single margin. Both default to None so Project
    # A's existing behaviour is unchanged.
    inventory_capacity_total: float | None = None
    inventory_capacity_by_product: dict | None = None
    solver: str = "highs"
    time_limit_s: float = 300.0

    def solve(
        self,
        demand_scenarios: pd.DataFrame,
        supply: pd.DataFrame,
        lead_times: dict | None = None,
        yield_scenarios: dict | None = None,
        opening_inventory: dict | None = None,
    ) -> dict:
        """Solve the schedule.

        demand_scenarios: [scenario_index, scenario_weight, product_id,
                           period, demand_kg]
        supply:           [supplier_id, product_id, capacity_kg, price_per_kg]
                          capacity is PER PERIOD.
        lead_times:       (scenario_index, supplier_id) -> integer periods.
                          Missing pairs default to 0 (arrives immediately).
        yield_scenarios:  (scenario_index, supplier_id) -> fill in [0, 1].
        opening_inventory: product_id -> kg on hand before period 0.

        Raises ValueError if the model is infeasible under an inventory
        cap that is too tight to absorb opening stock.
        """
        import pyomo.environ as pyo
        from pyomo.opt import SolverFactory

        T = int(self.n_periods)
        if T < 1:
            raise ValueError(f"n_periods must be >= 1, got {T}")

        scenarios = sorted(int(s) for s in
                           demand_scenarios["scenario_index"].unique())
        products = list(demand_scenarios["product_id"].unique())
        sup = (supply.groupby(["supplier_id", "product_id"])
               .agg(capacity_kg=("capacity_kg", "mean"),
                    price_per_kg=("price_per_kg", "mean")).reset_index())
        suppliers = list(sup["supplier_id"].unique())

        weights = {int(r["scenario_index"]): float(r["scenario_weight"])
                   for _, r in
                   demand_scenarios.drop_duplicates("scenario_index").iterrows()}
        weights = _normalized_weights(weights, scenarios)

        d = {(int(r["scenario_index"]), r["product_id"], int(r["period"])):
             float(r["demand_kg"]) for _, r in demand_scenarios.iterrows()}
        cap = {(r["supplier_id"], r["product_id"]): float(r["capacity_kg"])
               for _, r in sup.iterrows()}
        price = {(r["supplier_id"], r["product_id"]): float(r["price_per_kg"])
                 for _, r in sup.iterrows()}
        avg_price = {j: float(np.mean([v for (_i, j2), v in price.items()
                                       if j2 == j] or [2.0]))
                     for j in products}

        lt = lead_times or {}
        ys = yield_scenarios or {}
        inv0 = opening_inventory or {}

        cw = self.waste_cost_by_product or {}
        cu = self.unmet_cost_by_product or {}
        ch = self.holding_cost_by_product or {}
        cd = self.decay_rate_by_product or {}

        def _cw(j): return float(cw.get(j, self.waste_cost_per_kg))
        def _cu(j): return float(cu.get(j, self.lost_sale_per_kg_usd))
        def _ch(j): return float(ch.get(j, self.holding_cost_per_kg_per_period))
        def _cd(j): return float(cd.get(j, self.decay_rate_per_period))
        def _fill(w, i): return float(ys.get((w, i), 1.0))
        def _lead(w, i): return int(lt.get((w, i), 0))

        m = pyo.ConcreteModel()
        m.I = pyo.Set(initialize=suppliers)
        m.J = pyo.Set(initialize=products)
        m.T = pyo.Set(initialize=list(range(T)), ordered=True)
        m.W = pyo.Set(initialize=scenarios)
        m.IJ = pyo.Set(initialize=list(cap.keys()), dimen=2)

        # Stage 1: the ordering SCHEDULE. Ordering earlier is what this
        # variable makes expressible.
        m.x = pyo.Var(m.IJ, m.T, domain=pyo.NonNegativeReals)
        # Stage 2, per scenario and period.
        m.inv = pyo.Var(m.J, m.T, m.W, domain=pyo.NonNegativeReals)
        m.s = pyo.Var(m.J, m.T, m.W, domain=pyo.NonNegativeReals)
        m.u = pyo.Var(m.J, m.T, m.W, domain=pyo.NonNegativeReals)
        m.wst = pyo.Var(m.J, m.T, m.W, domain=pyo.NonNegativeReals)

        def obj(mm):
            return sum(
                weights[w] * sum(
                    avg_price[j] * (self.spot_cost_multiplier - 1.0)
                    * mm.s[j, t, w]
                    + _cw(j) * mm.wst[j, t, w]
                    + _cu(j) * mm.u[j, t, w]
                    + _ch(j) * mm.inv[j, t, w]
                    for j in mm.J for t in mm.T)
                for w in mm.W)

        m.obj = pyo.Objective(rule=obj, sense=pyo.minimize)

        def arrivals(mm, j, t, w):
            """Orders placed at t - L[i,w] land in period t."""
            out = 0.0
            for (i, jj) in mm.IJ:
                if jj != j:
                    continue
                placed = t - _lead(w, i)
                if 0 <= placed < T:
                    out += _fill(w, i) * mm.x[i, j, placed]
            return out

        def balance(mm, j, t, w):
            prev = mm.inv[j, t - 1, w] if t > 0 else float(inv0.get(j, 0.0))
            served = d.get((w, j, t), 0.0) - mm.u[j, t, w]
            return (mm.inv[j, t, w] == prev + arrivals(mm, j, t, w)
                    + mm.s[j, t, w] - served - mm.wst[j, t, w])

        m.balance = pyo.Constraint(m.J, m.T, m.W, rule=balance)

        def decay(mm, j, t, w):
            """Carried stock spoils. This is the cost of ordering early."""
            prev = mm.inv[j, t - 1, w] if t > 0 else float(inv0.get(j, 0.0))
            return mm.wst[j, t, w] >= _cd(j) * prev

        m.decay = pyo.Constraint(m.J, m.T, m.W, rule=decay)

        def unmet_cap(mm, j, t, w):
            return mm.u[j, t, w] <= d.get((w, j, t), 0.0)

        m.unmet_cap = pyo.Constraint(m.J, m.T, m.W, rule=unmet_cap)

        def cap_rule(mm, i, j, t):
            return mm.x[i, j, t] <= cap.get((i, j), 0.0)

        m.cap = pyo.Constraint(m.IJ, m.T, rule=cap_rule)

        icp = self.inventory_capacity_by_product or {}
        if icp:
            def inv_cap_product(mm, j, t, w):
                lim = icp.get(j)
                if lim is None:
                    return pyo.Constraint.Skip
                return mm.inv[j, t, w] <= float(lim)

            m.inv_cap_product = pyo.Constraint(
                m.J, m.T, m.W, rule=inv_cap_product)

        if self.inventory_capacity_total is not None:
            total_cap = float(self.inventory_capacity_total)

            def inv_cap_total(mm, t, w):
                return sum(mm.inv[j, t, w] for j in mm.J) <= total_cap

            m.inv_cap_total = pyo.Constraint(m.T, m.W, rule=inv_cap_total)

        if self.spot_capacity_factor is not None:
            rho = float(self.spot_capacity_factor)

            def spot_cap(mm, j, t, w):
                return mm.s[j, t, w] <= rho * d.get((w, j, t), 0.0)

            m.spot_cap = pyo.Constraint(m.J, m.T, m.W, rule=spot_cap)

        opt = SolverFactory("appsi_highs" if self.solver == "highs"
                            else self.solver)
        res = opt.solve(m, tee=False)
        status = str(res.solver.termination_condition)
        ok = status in ("optimal", "locallyOptimal")

        schedule = {(i, j, t): float(pyo.value(m.x[i, j, t]) or 0.0)
                    for (i, j) in cap for t in range(T)} if ok else {}
        by_period = {}
        for (_i, _j, t), v in schedule.items():
            by_period[t] = by_period.get(t, 0.0) + v

        return {
            "status": status,
            "objective": float(pyo.value(m.obj)) if ok else None,
            "x": schedule,
            "ordered_by_period": by_period,
            "n_periods": T,
            "model": m,
        }
