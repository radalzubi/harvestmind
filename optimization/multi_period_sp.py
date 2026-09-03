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

from optimization.solve_status import SolveOutcome, run_solver
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
    # Discrete ordering. product_id -> domain.uom.PackSpec. A product with a
    # spec is ordered in whole lots (cases, layers or pallets) with an
    # optional minimum order; products without one stay continuous. Any
    # spec turns the model from an LP into a MILP, still solved by HiGHS.
    pack_specs: dict | None = None
    mip_rel_gap: float = 0.005
    # Service floors: product_id -> minimum expected unit fill in [0, 1].
    # Enforced in expectation across scenarios and periods, the same
    # semantics as the single-period model. A floor the capacity cannot
    # meet makes the model infeasible, which run_solver reports as such.
    service_floor_by_product: dict | None = None
    # ── Safe / baseline-anchored formulation ─────────────────────────────
    # A FIXED schedule turns the model into a recourse evaluation of that
    # schedule (used for EEV, baseline costs, and scoring any policy on the
    # scenario set). A BASELINE schedule is the incumbent the operator
    # would have run: the objective can add an L1 deviation penalty
    # rho_j * |x - b| (linearised) and a CVaR term on scenario-relative
    # regret cost_w(x) - cost_w(b), plus an optional hard CVaR budget.
    # None of these guarantees anything out of sample; they shape the
    # in-sample decision toward the incumbent where uncertainty is cheap.
    fixed_schedule: dict | None = None
    baseline_schedule: dict | None = None
    anchor_rho_by_product: dict | None = None
    regret_cvar_alpha: float = 0.90
    regret_cvar_lambda: float = 0.0
    regret_cvar_budget: float | None = None
    # Per-scenario baseline costs, if the caller already evaluated them;
    # otherwise computed here by a fixed-schedule solve.
    baseline_scenario_costs: dict | None = None
    # Trust region: product -> fraction; |x - b| <= frac * max(b, one lot) per
    # (supplier, product, period). Inside the MILP, so MOQ, pallet and
    # capacity constraints still hold. Requires baseline_schedule.
    trust_region_by_product: dict | None = None
    trust_region_lower: bool = True      # False keeps only "no more than incumbent + width"
    # Plan stability: cost per unit of change vs the previously published
    # schedule (per unit cost fraction is the caller's choice); linearised.
    previous_schedule: dict | None = None
    change_cost_by_product: dict | None = None
    # Transfers between locations. A "location" is expressed by the caller
    # as a distinct product key (e.g. "SKU-1@WH-A"); an arc
    # (from_key, to_key, cost_per_unit, lead_periods) lets stock move
    # between them as a RECOURSE decision, per scenario and period.
    transfer_arcs: list | None = None
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
        lead_times:       (scenario_index, supplier_id) -> integer periods, or
                          (scenario_index, supplier_id, placement_period) for
                          a lead that varies over the horizon. The
                          period-specific key wins when both are present.
                          Missing pairs default to 0 (arrives immediately).
        yield_scenarios:  (scenario_index, supplier_id[, placement_period])
                          -> fill in [0, 1], same precedence rule.
        opening_inventory: product_id -> kg on hand before period 0.

        Raises ValueError if the model is infeasible under an inventory
        cap that is too tight to absorb opening stock.
        """
        import pyomo.environ as pyo

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
        def _fill(w, i, tp=None):
            if tp is not None and (w, i, tp) in ys:
                return float(ys[(w, i, tp)])
            return float(ys.get((w, i), 1.0))

        def _lead(w, i, tp=None):
            if tp is not None and (w, i, tp) in lt:
                return int(lt[(w, i, tp)])
            return int(lt.get((w, i), 0))

        m = pyo.ConcreteModel()
        m.I = pyo.Set(initialize=suppliers)
        m.J = pyo.Set(initialize=products)
        m.T = pyo.Set(initialize=list(range(T)), ordered=True)
        m.W = pyo.Set(initialize=scenarios)
        m.IJ = pyo.Set(initialize=list(cap.keys()), dimen=2)

        # Stage 1: the ordering SCHEDULE. Ordering earlier is what this
        # variable makes expressible.
        m.x = pyo.Var(m.IJ, m.T, domain=pyo.NonNegativeReals)
        # Discrete lots. x is kept as the quantity the rest of the model
        # sees; for a packed product it is tied to an integer lot count.
        specs = {j: sp for j, sp in (self.pack_specs or {}).items()
                 if j in products and sp.is_discrete}
        m.IJD = pyo.Set(initialize=[(i, j) for (i, j) in cap if j in specs],
                        dimen=2)
        m.n_lots = pyo.Var(m.IJD, m.T, domain=pyo.NonNegativeIntegers)
        m.y_order = pyo.Var(m.IJD, m.T, domain=pyo.Binary)
        arcs = [(str(a), str(b), float(c), int(L)) for (a, b, c, L) in (self.transfer_arcs or [])
                if str(a) in products and str(b) in products and str(a) != str(b)]
        for (a, b, c, L) in arcs:
            if c < 0 or L < 0:
                raise ValueError(f"transfer arc {a}->{b} needs cost >= 0 and lead >= 0")
        m.A = pyo.Set(initialize=list(range(len(arcs))))
        m.z = pyo.Var(m.A, m.T, m.W, domain=pyo.NonNegativeReals)
        # Stage 2, per scenario and period.
        m.inv = pyo.Var(m.J, m.T, m.W, domain=pyo.NonNegativeReals)
        m.s = pyo.Var(m.J, m.T, m.W, domain=pyo.NonNegativeReals)
        m.u = pyo.Var(m.J, m.T, m.W, domain=pyo.NonNegativeReals)
        m.wst = pyo.Var(m.J, m.T, m.W, domain=pyo.NonNegativeReals)

        def scen_cost(mm, w):
            """Recourse cost of scenario w: the quantity every diagnostic
            (VSS, EVPI, regret, CVaR) is built from."""
            return (sum(
                avg_price[j] * (self.spot_cost_multiplier - 1.0) * mm.s[j, t, w]
                + _cw(j) * mm.wst[j, t, w]
                + _cu(j) * mm.u[j, t, w]
                + _ch(j) * mm.inv[j, t, w]
                for j in mm.J for t in mm.T)
                + sum(arcs[a][2] * mm.z[a, t, w] for a in mm.A for t in mm.T))

        base_sched = {(str(i), str(j), int(t)): float(q)
                      for (i, j, t), q in (self.baseline_schedule or {}).items()}
        anchor_rho = {str(j): float(r) for j, r in (self.anchor_rho_by_product or {}).items()
                      if float(r) > 0}
        anchored = bool(base_sched) and bool(anchor_rho)
        base_costs = {int(w): float(c) for w, c in (self.baseline_scenario_costs or {}).items()}
        ref_warnings: list = []
        use_cvar = bool(base_sched) and (self.regret_cvar_lambda > 0
                                         or self.regret_cvar_budget is not None)
        if use_cvar and not base_costs:
            # Evaluate the baseline once on the same scenarios so regret is
            # relative to what the incumbent would actually have cost here.
            # The incumbent is evaluated the way the settlement treats it:
            # orders clipped to supplier capacity, no service floor, no lot
            # integrality (its quantities are what they are), no hard
            # inventory cap (overflow is priced through holding here and as
            # disposal in the settlement). The planner's own constraints
            # still bind the planner; they are not a reason to have no
            # reference.
            cap_ij = {(str(r.supplier_id), str(r.product_id)): float(r.capacity_kg)
                      for r in supply.itertuples()} if "capacity_kg" in supply.columns else {}
            ref_sched = {k: min(q, cap_ij.get((k[0], k[1]), q)) for k, q in base_sched.items()}
            ref = MultiPeriodStochasticLP(**{**self.__dict__, "fixed_schedule": ref_sched,
                                            "baseline_schedule": None, "anchor_rho_by_product": None,
                                            "regret_cvar_lambda": 0.0, "regret_cvar_budget": None,
                                            "baseline_scenario_costs": None,
                                            "service_floor_by_product": None, "pack_specs": None,
                                            "inventory_capacity_total": None,
                                            "inventory_capacity_by_product": None,
                                            "trust_region_by_product": None, "previous_schedule": None,
                                            "change_cost_by_product": None})
            r_ref = ref.solve(demand_scenarios, supply, lead_times=lead_times,
                              yield_scenarios=yield_scenarios,
                              opening_inventory=opening_inventory)
            if not r_ref["usable"]:
                raise ValueError("baseline schedule could not be evaluated on the "
                                 f"scenario set (status {r_ref['status']}); it is "
                                 "not a feasible reference here")
            base_costs = {int(w): float(c) for w, c in r_ref["scenario_costs"].items()}
            if any(ref_sched[k] < base_sched[k] for k in base_sched):
                ref_warnings.append("baseline orders above supplier capacity were clipped for the reference")

        trust = {str(j): float(f) for j, f in (self.trust_region_by_product or {}).items()
                 if str(j) in products and float(f) >= 0}
        if trust and base_sched:
            lot_of = {str(j): (specs[j].lot_units if j in specs else 1.0) for j in products}
            cap_ij_tr = {(str(r.supplier_id), str(r.product_id)): float(r.capacity_kg)
                         for r in supply.itertuples()} if "capacity_kg" in supply.columns else {}

            # Width is at least one lot so pack rounding can never make the
            # region empty: a baseline of 100 units with 12-unit cases and a
            # 3% region still admits 96 and 108. The region is centred on the
            # baseline as it could actually be executed (clipped to supplier
            # capacity), the same reference the regret uses.
            def _centre(i, j, t):
                b = base_sched.get((i, j, t), 0.0)
                return min(b, cap_ij_tr.get((i, j), b))

            def _width(j, b):
                return max(trust[j] * b, lot_of[j])

            def trust_hi(mm, i, j, t):
                if j not in trust:
                    return pyo.Constraint.Skip
                b = _centre(i, j, t)
                return mm.x[i, j, t] <= b + _width(j, b)

            def trust_lo(mm, i, j, t):
                if j not in trust or not self.trust_region_lower:
                    return pyo.Constraint.Skip
                b = _centre(i, j, t)
                return mm.x[i, j, t] >= max(b - _width(j, b), 0.0)

            m.trust_hi = pyo.Constraint(m.IJ, m.T, rule=trust_hi)
            m.trust_lo = pyo.Constraint(m.IJ, m.T, rule=trust_lo)

        prev_sched = {(str(i), str(j), int(t)): float(q)
                      for (i, j, t), q in (self.previous_schedule or {}).items()}
        chg = {str(j): float(c) for j, c in (self.change_cost_by_product or {}).items() if float(c) > 0}
        stabilised = bool(chg) and self.previous_schedule is not None
        if stabilised:
            m.chg_plus = pyo.Var(m.IJ, m.T, domain=pyo.NonNegativeReals)
            m.chg_minus = pyo.Var(m.IJ, m.T, domain=pyo.NonNegativeReals)

            def chg_rule(mm, i, j, t):
                return mm.x[i, j, t] - prev_sched.get((i, j, t), 0.0) == mm.chg_plus[i, j, t] - mm.chg_minus[i, j, t]

            m.chg = pyo.Constraint(m.IJ, m.T, rule=chg_rule)

        if anchored:
            m.dev_plus = pyo.Var(m.IJ, m.T, domain=pyo.NonNegativeReals)
            m.dev_minus = pyo.Var(m.IJ, m.T, domain=pyo.NonNegativeReals)

            def dev_rule(mm, i, j, t):
                return mm.x[i, j, t] - base_sched.get((i, j, t), 0.0) == \
                    mm.dev_plus[i, j, t] - mm.dev_minus[i, j, t]

            m.dev = pyo.Constraint(m.IJ, m.T, rule=dev_rule)

        if use_cvar:
            alpha = float(self.regret_cvar_alpha)
            if not 0.0 < alpha < 1.0:
                raise ValueError("regret_cvar_alpha must be in (0, 1)")
            m.eta = pyo.Var(domain=pyo.Reals)
            m.zr = pyo.Var(m.W, domain=pyo.NonNegativeReals)

            def cvar_rule(mm, w):
                return mm.zr[w] >= scen_cost(mm, w) - base_costs.get(w, 0.0) - mm.eta

            m.cvar_excess = pyo.Constraint(m.W, rule=cvar_rule)

            def cvar_expr(mm):
                return mm.eta + sum(weights[w] * mm.zr[w] for w in mm.W) / (1.0 - alpha)

            if self.regret_cvar_budget is not None:
                m.cvar_budget = pyo.Constraint(expr=cvar_expr(m) <= float(self.regret_cvar_budget))

        def obj(mm):
            total = sum(weights[w] * scen_cost(mm, w) for w in mm.W)
            if anchored:
                total += sum(anchor_rho.get(j, 0.0) * (mm.dev_plus[i, j, t] + mm.dev_minus[i, j, t])
                             for (i, j) in mm.IJ for t in mm.T)
            if use_cvar and self.regret_cvar_lambda > 0:
                total += float(self.regret_cvar_lambda) * cvar_expr(mm)
            if stabilised:
                total += sum(chg.get(j, 0.0) * (mm.chg_plus[i, j, t] + mm.chg_minus[i, j, t])
                             for (i, j) in mm.IJ for t in mm.T)
            return total

        m.obj = pyo.Objective(rule=obj, sense=pyo.minimize)

        if self.fixed_schedule is not None:
            fixed = {(str(i), str(j), int(t)): float(q) for (i, j, t), q in self.fixed_schedule.items()}

            def fix_rule(mm, i, j, t):
                return mm.x[i, j, t] == fixed.get((i, j, t), 0.0)

            m.fix_x = pyo.Constraint(m.IJ, m.T, rule=fix_rule)

        def arrivals(mm, j, t, w):
            """Orders placed at tp land in period tp + L[i,w,tp]."""
            out = 0.0
            for (i, jj) in mm.IJ:
                if jj != j:
                    continue
                for tp in range(T):
                    if tp + _lead(w, i, tp) == t:
                        out += _fill(w, i, tp) * mm.x[i, j, tp]
            return out

        def transfers_net(mm, j, t, w):
            out = 0.0
            for a, (src, dst, _c, L) in enumerate(arcs):
                if src == j:
                    out -= mm.z[a, t, w]
                if dst == j and 0 <= t - L < T:
                    out += mm.z[a, t - L, w]
            return out

        def balance(mm, j, t, w):
            prev = mm.inv[j, t - 1, w] if t > 0 else float(inv0.get(j, 0.0))
            served = d.get((w, j, t), 0.0) - mm.u[j, t, w]
            return (mm.inv[j, t, w] == prev + arrivals(mm, j, t, w)
                    + mm.s[j, t, w] + transfers_net(mm, j, t, w)
                    - served - mm.wst[j, t, w])

        def transfer_from_stock(mm, j, t, w):
            """A location can only ship what it opened the period with."""
            outs = [mm.z[a, t, w] for a, (src, _d, _c, _L) in enumerate(arcs) if src == j]
            if not outs:
                return pyo.Constraint.Skip
            prev = mm.inv[j, t - 1, w] if t > 0 else float(inv0.get(j, 0.0))
            return sum(outs) <= prev

        m.transfer_from_stock = pyo.Constraint(m.J, m.T, m.W, rule=transfer_from_stock)

        m.balance = pyo.Constraint(m.J, m.T, m.W, rule=balance)

        def decay(mm, j, t, w):
            """Carried stock spoils. This is the cost of ordering early."""
            prev = mm.inv[j, t - 1, w] if t > 0 else float(inv0.get(j, 0.0))
            return mm.wst[j, t, w] >= _cd(j) * prev

        m.decay = pyo.Constraint(m.J, m.T, m.W, rule=decay)

        def unmet_cap(mm, j, t, w):
            return mm.u[j, t, w] <= d.get((w, j, t), 0.0)

        m.unmet_cap = pyo.Constraint(m.J, m.T, m.W, rule=unmet_cap)

        def lot_tie(mm, i, j, t):
            return mm.x[i, j, t] == specs[j].lot_units * mm.n_lots[i, j, t]

        m.lot_tie = pyo.Constraint(m.IJD, m.T, rule=lot_tie)

        def lot_big_m(mm, i, j, t):
            # An order exists only if its binary is on. Big-M is the lot
            # count that fills capacity, so it is tight, not arbitrary.
            lots_cap = max(1.0, cap.get((i, j), 0.0) / specs[j].lot_units)
            return mm.n_lots[i, j, t] <= float(np.ceil(lots_cap)) * mm.y_order[i, j, t]

        m.lot_big_m = pyo.Constraint(m.IJD, m.T, rule=lot_big_m)

        def moq_rule(mm, i, j, t):
            sp = specs[j]
            if sp.moq_units <= 0:
                return pyo.Constraint.Skip
            return mm.x[i, j, t] >= sp.moq_units * mm.y_order[i, j, t]

        m.moq = pyo.Constraint(m.IJD, m.T, rule=moq_rule)

        def max_order_rule(mm, i, j, t):
            sp = specs[j]
            if sp.max_units_per_order is None:
                return pyo.Constraint.Skip
            return mm.x[i, j, t] <= sp.max_units_per_order

        m.max_order = pyo.Constraint(m.IJD, m.T, rule=max_order_rule)

        def cap_rule(mm, i, j, t):
            return mm.x[i, j, t] <= cap.get((i, j), 0.0)

        m.cap = pyo.Constraint(m.IJ, m.T, rule=cap_rule)

        floors = {str(j): float(f) for j, f in (self.service_floor_by_product or {}).items()
                  if str(j) in products}
        for j, f in floors.items():
            if not 0.0 <= f <= 1.0:
                raise ValueError(f"service floor for {j} must be in [0, 1], got {f}")
        if floors:
            m.JF = pyo.Set(initialize=sorted(floors))
            # The floor applies to the CONTROLLABLE window: periods an order
            # placed at t=0 can reach. Demand inside the lead-time dead zone
            # is decided by opening stock and pipeline alone, and a floor
            # over it would make every long-lead problem infeasible.
            first_reach = {}
            for j in floors:
                leads_j = [min(_lead(w, i, 0) for w in scenarios) for (i, jj) in cap if jj == j]
                first_reach[j] = min(leads_j) if leads_j else 0

            def service_floor(mm, j):
                t0 = first_reach[j]
                exp_unmet = sum(weights[w] * mm.u[j, t, w] for w in mm.W for t in mm.T if t >= t0)
                exp_dem = sum(weights[w] * d.get((w, j, t), 0.0) for w in mm.W for t in mm.T if t >= t0)
                if exp_dem <= 0:
                    return pyo.Constraint.Skip
                return exp_unmet <= (1.0 - floors[j]) * exp_dem

            m.service_floor = pyo.Constraint(m.JF, rule=service_floor)

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

        outcome: SolveOutcome = run_solver(
            m, solver=self.solver, time_limit_s=self.time_limit_s,
            mip_rel_gap=self.mip_rel_gap if specs else None)
        status = outcome.status
        ok = outcome.usable

        schedule = {(i, j, t): float(pyo.value(m.x[i, j, t]) or 0.0)
                    for (i, j) in cap for t in range(T)} if ok else {}
        if ok and specs:
            # Snap away solver tolerance so a report never shows 11.9999
            # cases. Integer feasibility was enforced by the MILP; this
            # only cleans the float representation.
            for (i, j, t), v in list(schedule.items()):
                if j in specs:
                    lot = specs[j].lot_units
                    schedule[(i, j, t)] = float(round(v / lot)) * lot
        by_period: dict[int, float] = {}
        for (_i, _j, t), v in schedule.items():
            by_period[t] = by_period.get(t, 0.0) + v

        scenario_costs = ({int(w): float(pyo.value(scen_cost(m, w))) for w in scenarios}
                          if ok else {})
        expected_cost = (sum(weights[w] * c for w, c in scenario_costs.items())
                         if ok else None)
        regret = ({w: scenario_costs[w] - base_costs[w] for w in scenario_costs if w in base_costs}
                  if ok and base_costs else {})
        cvar_val: float | None = None
        if ok and use_cvar:
            cvar_val = float(pyo.value(m.eta) + sum(weights[w] * pyo.value(m.zr[w]) for w in m.W)
                             / (1.0 - float(self.regret_cvar_alpha)))
        return {
            "status": status,
            "usable": ok,
            "objective": float(pyo.value(m.obj)) if ok else None,
            "expected_cost": expected_cost,
            "scenario_costs": scenario_costs,
            "scenario_weights": {int(w): float(weights[w]) for w in scenarios},
            "baseline_scenario_costs": base_costs,
            "regret_by_scenario": regret,
            "regret_cvar": cvar_val,
            "anchored": anchored,
            "trust_region": trust,
            "plan_stabilised": stabilised,
            "objective_bound": outcome.bound,
            "gap": outcome.gap,
            "runtime_s": outcome.runtime_s,
            "warnings": list(outcome.warnings) + ref_warnings,
            "discrete_products": sorted(specs),
            "transfers": ({(arcs[a][0], arcs[a][1], t, w): float(pyo.value(m.z[a, t, w]) or 0.0)
                           for a in m.A for t in range(T) for w in scenarios
                           if pyo.value(m.z[a, t, w]) and pyo.value(m.z[a, t, w]) > 1e-9}
                          if ok else {}),
            "service_floors": floors,
            "x": schedule,
            "ordered_by_period": by_period,
            "n_periods": T,
            "model": m,
        }
