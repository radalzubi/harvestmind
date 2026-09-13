"""Sparse continuous/mixed-integer, age-indexed network MPC.

All order/transfer/amendment schedules are scenario invariant. Only inventory,
customer fulfillment and borrowing react to a scenario. Future schedules are
guidance, not commitments. No service-floor relaxation is hidden in this model.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
import math
import time
from typing import Any, TYPE_CHECKING

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

from zaad.full.contracts import Request, SupplierTerms
from zaad.sectors.contracts import resolve as sector_physics
from zaad.sourcing.contracts import resolve as sourcing_view
from zaad.full.tolerance import is_dust, po_closed, source_pack
from zaad.full.worlds import World, dates, next_open

if TYPE_CHECKING:
    from zaad.recourse.information import NodeMap


# P2 performance pass: exact symmetry elimination of the FEFO indicators (see
# docs/zaad_full/evidence/p2/perf/P2_PERF_DIAGNOSIS.md). A cohort that outlives the horizon and every
# transfer arrival the plan can schedule is economically interchangeable with every other such cohort
# of its SKU: no disposal, the same terminal and continuation value, the same lane eligibility. The
# FEFO rule between two interchangeable cohorts constrains only which label is consumed, never a cost
# or a quantity, so the indicator and its two rows are omitted (the FEFO rule against every cohort that
# CAN matter inside the window is kept exactly). Objective and executable decisions are unchanged; the
# settlement applies FEFO itself. It applies to network requests (a declared transfer lane): the
# frozen single-node P1 formulation is kept verbatim so its recorded decision path is reproduced
# bit for bit (on the P1 fixture T the elimination is objective-exact to 1e-15 but breaks a tie
# between two equal-cost source splits differently; a frozen path is not re-tuned for speed it does
# not need). False restores the frozen formulation everywhere (diagnostic / equivalence runs).
FEFO_SYMMETRY_ELIMINATION = True


class Linear:
    def __init__(self):
        self.names, self.cost, self.lower, self.upper, self.integer = [], [], [], [], []
        self.rows, self.lo, self.hi = [], [], []

    def var(self, name, cost=0., upper=np.inf, integer=False, lower=0.):
        n = len(self.names)
        self.names.append(name)
        self.cost.append(cost)
        self.lower.append(lower)
        self.upper.append(upper)
        self.integer.append(int(integer))
        return n

    def row(self, coefficients, lower=-np.inf, upper=np.inf):
        self.rows.append(dict(coefficients))
        self.lo.append(lower)
        self.hi.append(upper)

    def matrix(self):
        rr, cc, vv = [], [], []
        for r, terms in enumerate(self.rows):
            for c, v in terms.items():
                if v:
                    rr.append(r)
                    cc.append(c)
                    vv.append(v)
        return coo_matrix((vv, (rr, cc)), shape=(len(self.rows), len(self.names))).tocsc()

    def solve(self, seconds, objective=None, solver="highs", mip_gap: float = 1e-6, seed=None, options: dict | None = None):
        """Solve with scipy's bundled HiGHS (the frozen path) or, when `seed` is given or
        solver == "highspy", through highspy on the identical cost / bounds / integrality /
        constraint arrays, so a known feasible vector can be handed to HiGHS as its starting
        incumbent (v8, P0-W2). Warm starting changes the search only, never the problem.
        `options` are HiGHS search settings (P3 performance closure); they are honoured on the
        highspy route only and never change the model or its optimality tolerance."""
        matrix = self.matrix()
        if solver == "highspy" or seed is not None:
            result = self._highspy_solve(matrix, self.cost if objective is None else objective, seconds, mip_gap, seed, options=options)
        elif solver != "highs":
            from zaad.full.solvers import pyomo_solve
            result = pyomo_solve(self, seconds, objective, solver)
        else:
            result = milp(np.asarray(self.cost if objective is None else objective),
                      integrality=np.asarray(self.integer),
                      bounds=Bounds(self.lower, self.upper),
                      constraints=LinearConstraint(matrix, self.lo, self.hi),
                      options={"time_limit": seconds, "mip_rel_gap": mip_gap})
        if result.x is not None:
            activity = matrix @ result.x
            residual = max(float(np.max(np.asarray(self.lo) - activity, initial=0)),
                           float(np.max(activity - np.asarray(self.hi), initial=0)),
                           float(np.max(np.asarray(self.lower) - result.x, initial=0)),
                           float(np.max(result.x - np.asarray(self.upper), initial=0)))
            ints = np.asarray(self.integer, dtype=bool)
            residual = max(residual, float(np.max(abs(result.x[ints] - np.rint(result.x[ints])), initial=0)))
        else:
            residual = math.inf
        return result, residual

    def _highspy_solve(self, matrix, cost, seconds, mip_gap, seed=None, first_feasible: bool = False, options: dict | None = None):
        """The same model through highspy. Returns an object with scipy-milp-shaped attributes
        (x, fun, status, message, mip_gap, mip_dual_bound, mip_node_count) plus HiGHS's own
        residuals and whether a starting solution was supplied and accepted."""
        import highspy
        from types import SimpleNamespace
        h = highspy.Highs()
        h.setOptionValue("output_flag", False)
        h.setOptionValue("time_limit", float(max(seconds, 1e-3)))
        h.setOptionValue("mip_rel_gap", float(mip_gap))
        for key, value in (options or {}).items():
            h.setOptionValue(key, value)
        if first_feasible:
            # a completion needs one feasible point, not a proof: stop at the first incumbent
            h.setOptionValue("mip_max_improving_sols", 1)
        lp = highspy.HighsLp()
        lp.num_col_, lp.num_row_ = len(self.names), len(self.rows)
        lp.col_cost_ = np.asarray(cost, dtype=float)
        lp.col_lower_ = np.asarray(self.lower, dtype=float)
        lp.col_upper_ = np.asarray(self.upper, dtype=float)
        lp.row_lower_ = np.asarray(self.lo, dtype=float)
        lp.row_upper_ = np.asarray(self.hi, dtype=float)
        lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
        lp.a_matrix_.start_ = np.asarray(matrix.indptr, dtype=np.int32)
        lp.a_matrix_.index_ = np.asarray(matrix.indices, dtype=np.int32)
        lp.a_matrix_.value_ = np.asarray(matrix.data, dtype=float)
        lp.integrality_ = [highspy.HighsVarType.kInteger if i else highspy.HighsVarType.kContinuous for i in self.integer]
        h.passModel(lp)
        seed_status = None
        seed_objective = None
        if seed is not None:
            start = highspy.HighsSolution()
            start.col_value = np.asarray(seed, dtype=float)
            seed_status = str(h.setSolution(start))
            seed_objective = float(np.dot(np.asarray(cost, dtype=float), np.asarray(seed, dtype=float)))
        h.run()
        model_status = h.getModelStatus()
        info = h.getInfo()
        has_x = int(info.primal_solution_status) == int(highspy.kSolutionStatusFeasible)
        x = np.asarray(h.getSolution().col_value, dtype=float) if has_x else None
        S = highspy.HighsModelStatus
        # highspy 1.15 dropped the deprecated alias kHighsInterrupt (same status as kInterrupt);
        # 1.14 carries both. Read it defensively so a non-optimal status never raises.
        interrupt_alias = getattr(S, "kHighsInterrupt", S.kInterrupt)
        if model_status == S.kOptimal:
            status = 0
        elif model_status in (S.kTimeLimit, S.kIterationLimit, S.kSolutionLimit, S.kInterrupt, interrupt_alias):
            status = 1
        elif model_status == S.kInfeasible:
            status = 2
        elif model_status in (S.kUnbounded, S.kUnboundedOrInfeasible):
            status = 3
        else:
            status = 4
        fun = float(info.objective_function_value) if has_x else None
        return SimpleNamespace(
            x=x, fun=fun, status=status, message=f"highspy {model_status}",
            mip_gap=float(info.mip_gap) if has_x and math.isfinite(info.mip_gap) else None,
            mip_dual_bound=float(info.mip_dual_bound) if math.isfinite(info.mip_dual_bound) else None,
            mip_node_count=int(info.mip_node_count),
            max_integrality_violation=float(info.max_integrality_violation) if has_x else None,
            max_primal_infeasibility=float(info.max_primal_infeasibility) if has_x else None,
            seed_status=seed_status, seed_objective=seed_objective,
            # HiGHS held at least the seed as an incumbent when it ends with a solution no worse than it
            seed_accepted=(seed is not None and has_x and fun is not None and seed_objective is not None
                           and fun <= seed_objective + 1e-6 * max(1., abs(seed_objective))))

    def complete(self, controls: dict, seconds: float, mode: str = "equal") -> dict:
        """Complete a partial seed (v8, P0-W3): pin the given columns inside this model's own
        bounds and solve the remaining problem, so every other variable is derived by the
        formulation itself rather than invented. mode="equal" pins each control to its value;
        mode="floor" pins it as a lower bound - the add-only repair: everything the seed plan
        does is kept and the formulation may add supply on top where its own floors need it.
        Returns the full vector when the pinned values are feasible for this formulation, and
        the reason when they are not."""
        started = time.monotonic()
        for i, v in controls.items():
            if v < self.lower[i] - 1e-9 or v > self.upper[i] + 1e-9:
                return {"accepted": False, "reason": f"seed value {v:.6g} outside bounds [{self.lower[i]:.6g}, {self.upper[i]:.6g}] of {self.names[i]}",
                        "completion_seconds": 0., "completion_status": "bounds", "mode": mode}
        saved = (list(self.lower), list(self.upper))
        try:
            for i, v in controls.items():
                value = max(v, 0.) if abs(v) < 1e-9 else v
                self.lower[i] = value
                if mode == "equal":
                    self.upper[i] = value
            result = self._highspy_solve(self.matrix(), self.cost, seconds, 1e-4, first_feasible=True)
        finally:
            self.lower, self.upper = saved
        elapsed = time.monotonic() - started
        if result.x is None:
            return {"accepted": False, "reason": f"{mode}-pinned controls are not feasible for this formulation within {seconds:.0f} s ({result.message})",
                    "completion_seconds": elapsed, "completion_status": result.message, "mode": mode}
        return {"accepted": True, "reason": f"completed by the formulation ({mode} pins)", "completion_seconds": elapsed,
                "completion_status": result.message, "mode": mode, "x": result.x}


@dataclass
class Solution:
    status: str
    purchases: dict[tuple[str, int], float]
    transfers: dict[tuple[str, int, int], float]
    amendments: dict[tuple[str, str], float]
    projected_service: dict[str, float]
    projected_cost: float | None
    cash: list[dict]
    solve_seconds: float
    variables: int
    constraints: int
    gap: float | None
    residual: float | None
    warnings: list[str]
    protection_state: list[dict] | None = None
    procurement_timing: list[dict] | None = None
    capital: dict | None = None
    solve_quality: dict | None = None
    # Solve telemetry (v8). `status` is one of OPTIMAL, FEASIBLE_TIME_LIMIT, INFEASIBLE,
    # NO_FEASIBLE_SOLUTION or ERROR. A FEASIBLE_TIME_LIMIT solution is a real, usable plan whose
    # optimality was never proved; it is never labelled optimal and never silently discarded.
    best_bound: float | None = None
    nodes: int | None = None
    # Warm start telemetry (v8, P0-W4): whether a starting incumbent was supplied, whether the
    # formulation accepted it, and whether the solver improved on it or returned it.
    warm_start: dict | None = None
    # Planning surrogate telemetry (P1 final closure): analytic expected shortage priced in the
    # objective of a mean-world solve, in units and in the declared penalty; None when not used.
    planning_surrogate: dict | None = None
    # Adaptive recourse (P4): {"nodes": {node id: {"purchases": {(source, t): q}, "transfers":
    # {(arc, expiry, t): q}}}, "perfect": bool} for an information-set-indexed solve; None for a
    # static plan. `purchases` / `transfers` above then hold the here-and-now columns only.
    recourse: dict | None = None
    # the node map and the world names of the adaptive solve (settlement maps a solve world to its
    # node by membership and any other world by observable-signature lookup)
    recourse_nodes: Any = None
    recourse_worlds: tuple[str, ...] | None = None
    # instrumentation (P4): integer columns of the model
    binaries: int | None = None

    @property
    def usable_plan(self) -> bool:
        """Does this solution carry actions that may be acted on, subject to physical validation?"""
        return self.status in ("OPTIMAL", "FEASIBLE_TIME_LIMIT")


def compatible(req, service):
    """(supplied SKU, physical input per service-equivalent unit, penalty)."""
    rows = [(service.sku, 1., 0.)]
    customer = next(c for c in req.customers if c.id == service.customer)
    for rule in req.substitutions:
        if (rule.approved and rule.requested_sku == service.sku
                and service.customer in rule.customers and customer.channel in rule.channels):
            rows.append((rule.supplied_sku, rule.input_per_output / rule.service_equivalence,
                         rule.penalty_per_output / rule.service_equivalence))
    return rows


def explicit_order_economics(req: Request) -> bool:
    """Does the request declare order-level economics that price lumpiness themselves: supplier
    terms (fixed order cost, MOV, receiving, freight tariff) or a per-line fixed order fee?"""
    return bool(req.supplier_terms) or any(s.fixed_order_fee > 0 for s in req.sources)


def effective_smoothing(req: Request) -> float:
    """Order-smoothing charge actually applied (P1 closure). The V6 smoothing term is a proxy for
    unmodelled order costs; once explicit order economics are declared the proxy would double-
    count lumpiness and act as an undeclared fixed order cost (about 2% of landed cost per unit of
    change), so it is switched off. Without explicit economics the P0 default stands unchanged."""
    return 0. if explicit_order_economics(req) else req.order_smoothing


def solve_budget(req: Request) -> float:
    """Per-solve wall-clock budget (v8).

    Measured time-to-proof on this model class, seed 38001, stochastic_network solve:

        H=12 single location          under 1 s
        H=12 central + two branches   5.4 s
        H=20 single location         10.1 s
        H=30 single location         38.0 s

    and below each threshold the solver returns NO_FEASIBLE_SOLUTION rather than a usable
    incumbent - there is no "good plan early, proof later" region to exploit. Solve time tracks
    the square of the horizon with a factor for network breadth, which is what this reproduces.
    `adaptive_solve_budget=False` keeps the flat historical cap so V7 behaviour is reproducible.
    """
    if not req.adaptive_solve_budget:
        return req.max_solve_seconds
    locations = max(1, len({(a.sku, a.destination) for a in req.transfers if a.approved})
                    + len({(s.sku, s.destination) for s in req.sources if s.approved}))
    breadth = 1. + .6 * (locations - 1)
    scaled = req.max_solve_seconds * (req.horizon / 12.) ** 2 * breadth * req.solve_budget_margin
    return float(min(req.solve_budget_ceiling_seconds, max(req.max_solve_seconds, scaled)))


def supplier_orders(req: Request) -> list[tuple[str, list, "SupplierTerms"]]:
    """(supplier, its sources, its terms) for every supplier that carries order-level economics (P1)."""
    by_supplier: dict[str, list] = defaultdict(list)
    for source in req.sources:
        by_supplier[source.supplier].append(source)
    out = []
    for st in req.supplier_terms:
        if (st.minimum_order_value or st.fixed_order_cost or st.receiving_fee_per_receipt or st.receiving_per_pallet
                or st.freight_tiers or st.freight_per_pallet or st.max_pallets is not None):
            out.append((st.supplier, by_supplier.get(st.supplier, []), st))
    return out


def pallet_units(st, srcs) -> dict[str, float] | None:
    """Units per pallet per source for the shipment tariff, or None when any line's pallet size is
    unknown - pallet economics are then disabled for that supplier rather than guessed (P1)."""
    if not (st.freight_tiers or st.freight_per_pallet or st.receiving_per_pallet or st.max_pallets is not None):
        return None
    upp = {}
    for s in srcs:
        units = st.units_per_pallet.get(s.sku) or (s.pallet_multiple if s.pallet_multiple > 0 else 0.)
        if units <= 0:
            return None
        upp[s.id] = float(units)
    return upp


def warm_start_vector(m: Linear, seed: Solution, seconds: float) -> tuple[dict, np.ndarray | None]:
    """Map a known feasible plan's controls - purchases, PO amendments, transfers - onto this
    model's columns by name, and let the model complete the rest (v8, P0-W3). Nothing that is
    not legitimately known is invented: every other variable comes from the formulation."""
    controls: dict[int, float] = {}
    for i, name in enumerate(m.names):
        kind = name[0]
        if kind == "purchase":
            v = seed.purchases.get((name[1], name[2]), 0.)
        elif kind == "amend":
            v = seed.amendments.get((name[1], name[2]), 0.)
        elif kind == "transfer":
            v = seed.transfers.get((name[1], name[2], name[3]), 0.)
        else:
            continue
        controls[i] = 0. if abs(v) < 1e-9 else float(v)
    # Cascade: the plan itself first; if this formulation proves that infeasible (its floors need
    # more supply than the plan carries), the add-only repair - the plan's orders as lower bounds,
    # the formulation adding what it must. Both completions are real feasible plans of THIS
    # candidate; a seed that fails both is rejected with the reason.
    done = m.complete(controls, seconds)
    attempts = [dict(done, x=None) if "x" in done else done]
    remaining = seconds - done["completion_seconds"]
    if not done["accepted"] and "kInfeasible" in str(done.get("completion_status")) and remaining > 0.5:
        floor_controls = {i: v for i, v in controls.items() if m.names[i][0] == "purchase" and v > 0}
        done = m.complete(floor_controls, remaining, mode="floor")
        attempts.append(dict(done, x=None) if "x" in done else done)
    telemetry = {"supplied": True, "source": seed.status, "controls_seeded": len(controls),
                 "accepted": done["accepted"], "reason": done["reason"], "mode": done.get("mode"),
                 "completion_seconds": sum(a["completion_seconds"] for a in attempts),
                 "completion_status": done["completion_status"], "attempts": [{k: v for k, v in a.items() if k != "x"} for a in attempts]}
    return telemetry, done.get("x")


def _cohort_slab_rows(m: "Linear", physics, sku: str, H: int, slabs: list[tuple[int, int]], supply: dict[int, float], expiry_of: dict[int, int]) -> None:
    """Cohort-aware continuation (sector physics): the units served in post-window period j or later
    can only come from residual cohorts still sellable at period H + j. One cumulative row per slab
    whose eligible supply is smaller than the full residual; a request whose cohorts all outlive the
    slabs adds nothing (the frozen aggregate row already binds)."""
    threshold = physics.min_sale(sku)
    for j, _ in slabs:
        eligible = {q: coef for q, coef in supply.items() if expiry_of.get(q, math.inf) - (H + j) > threshold}
        if len(eligible) == len(supply):
            continue
        later = [var for jj, var in slabs if jj >= j]
        m.row({**{q: -coef for q, coef in eligible.items()}, **{var: 1. for var in later}}, upper=0)


# HiGHS search settings for the shared-supplier-order class - a supplier order (MOV / fixed cost /
# tariff) linking purchase lines of several SKUs (P3 production performance closure). Measured on the exact
# production shared-MOV snapshot after the activation bounds were tightened: HiGHS's root restart
# (re-presolve after the root cut loop) doubled the time of every 3-world solve and of the
# mean-world solve for no change in the optimum - deterministic_network 1.9 -> 1.0 s,
# stochastic_network 3.7 -> 1.4 s, cadence_2 2.3 -> 1.4 s, identical objectives to 1e-4. Heuristic
# effort, scaling, pricing, cut pool and LP-age settings changed nothing. The option is a search
# setting: the model, its bounds and the optimality tolerance are untouched, so the optimal set
# is the same; only the path to it is shorter.
ORDER_CLASS_SEARCH: dict[str, object] = {"mip_allow_restart": False}


def shared_supplier_orders(req: Request) -> bool:
    """The P3 shared-supplier-order class (P3 production performance closure): a sourcing review
    (`req.sourcing` declared) in which at least one supplier carrying order-level economics (MOV,
    fixed order cost, receiving, freight tariff) serves more than one SKU, so one order binary per
    period links purchase lines of several SKUs. This is the class of the 218 s production case and
    the only class this closure changes: every frozen P0 / P1 / P2 / sector request, and every P3
    review outside the class, keeps the released formulation and solver route bit for bit."""
    if getattr(req, "sourcing", None) is None:
        return False
    return any(len({s.sku for s in srcs}) > 1 for _, srcs, _ in supplier_orders(req))


def search_options(req: Request) -> dict | None:
    """HiGHS search settings for this request, or None for the frozen default search."""
    return dict(ORDER_CLASS_SEARCH) if shared_supplier_orders(req) else None


def activation_bounds(req: Request, worlds: list[World], *, targets=None, continuation=None, continuation_feeds=None,
                      fixed: "Solution | None" = None, sourcing=None,
                      expected_shortage: dict | None = None) -> dict[tuple[str, int], float]:
    """Exact activation bound per (source, period) for the supplier-order and MOQ linking rows
    (P3 production performance closure).

    The rows `purchase <= M * order` and `purchase <= M * active` used the declared line capacity
    as M. A declared "unbounded" capacity (a million units against a few hundred units of demand)
    lets the linear relaxation set order = purchase / M, near zero, so a minimum order value or a
    fixed order cost is never priced by the relaxation and HiGHS must branch to recover it. The
    bound returned here is the largest quantity of the line that any UNDOMINATED plan can carry:
    everything a purchase placed at t can still do - serve the demand of every service the SKU may
    supply, from t+1 to the end of the horizon, in the most demanding world (or on the analytic
    surrogate's demand support), through the lossiest lane, earn every continuation slab, satisfy
    its own MOQ, the supplier's MOV on its own and its base-stock target - rounded up to the
    line's pack lattice. A unit above it is never consumed nor credited, costs its landed
    price and earns at most salvage, which the guard keeps below landed cost, so no optimum carries
    it: the optimal set, the objective and every economic quantity are unchanged; only the search
    is shorter. Lines for which the argument does not close keep the declared capacity: a fixed
    plan, a SKU whose salvage could reach its landed cost or whose lane loses everything, a pair
    under declared share rows, or a pack lattice that is not integral. Requests outside the
    shared-supplier-order class (`shared_supplier_orders`) get no bounds at all: their released
    formulation is untouched.
    """
    if fixed is not None or not worlds or not shared_supplier_orders(req):
        return {}
    H = req.horizon
    skus = {s.id: s for s in req.skus}
    terms = {p.id: p for p in req.terms}
    landed_floor: dict[str, float] = {}
    for s in req.sources:
        term = terms[s.terms]
        landed = s.unit_price * term.fx_rate_to_currency + s.freight_per_unit + s.handling_per_unit
        landed_floor[s.sku] = min(landed_floor.get(s.sku, math.inf), landed)
    per_period: dict[str, list[float]] = {k: [0.] * H for k in skus}
    for service in req.services:
        peak = [max(w.demand[service.id][t] for w in worlds) for t in range(H)]
        fit = expected_shortage.get(service.id) if (expected_shortage is not None and len(worlds) == 1) else None
        if fit:
            from zaad.full.shortage import demand_atoms
            for t in range(H):
                multiplier = 1.
                for event in req.events:
                    if event.service == service.id and event.start <= t <= event.end:
                        multiplier *= event.multiplier
                atoms, _ = demand_atoms(fit, multiplier)
                if len(atoms):
                    peak[t] = max(peak[t], float(atoms[-1]))
        for sku, ratio, _ in compatible(req, service):
            if sku in per_period:
                for t in range(H):
                    per_period[sku][t] += peak[t] * ratio
    need: dict[str, list[float]] = {}
    for k in skus:
        running, to_go = 0., [0.] * H
        for t in range(H - 1, -1, -1):
            to_go[t] = running            # an order placed at t lands at t + 1 or later
            running += per_period[k][t]
        need[k] = to_go
    credited = {k: 0. for k in skus}
    for (sku, _), value in (continuation or {}).items():
        slabs = value if isinstance(value, list) else [value]
        credited[sku] = credited.get(sku, 0.) + sum(float(u) for u, _ in slabs if u > 0)
    for (sku, _), feeds in (continuation_feeds or {}).items():
        for feed in feeds:
            entry = (continuation or {}).get((sku, feed["branch"]))
            if entry:
                slabs = entry if isinstance(entry, list) else [entry]
                credited[sku] = credited.get(sku, 0.) + sum(float(u) for u, _ in slabs if u > 0)
    loss = {k: max([a.loss_fraction for a in req.transfers if a.sku == k and a.approved] or [0.]) for k in skus}
    shares = sourcing.shares if sourcing is not None else {}
    mov: dict[str, float] = {}
    for st in req.supplier_terms:
        mov[st.supplier] = max(mov.get(st.supplier, 0.), float(st.minimum_order_value or 0.))
    bounds: dict[tuple[str, int], float] = {}
    for source in req.sources:
        k = source.sku
        if k not in skus or skus[k].terminal_value >= landed_floor[k] or loss[k] >= 1.:
            continue
        if shares.get((k, source.destination)):
            continue
        increments = [v for v in (source.multiple, source.case_multiple, source.pallet_multiple, source.transport_multiple) if v and v > 0]
        if any(not float(v).is_integer() for v in increments):
            continue
        lattice = math.lcm(*[int(v) for v in increments]) if increments else 0
        price = source.unit_price * terms[source.terms].fx_rate_to_currency
        floor = max(float(source.minimum), mov.get(source.supplier, 0.) / price if price > 0 else 0.)
        for t in range(H):
            quantity = max((need[k][t] + credited[k]) / (1. - loss[k]), floor)
            if targets is not None:
                quantity = max(quantity, float(targets.get((source.id, t), 0.)))
            if lattice:
                quantity = math.ceil(quantity / lattice - 1e-9) * lattice
            bounds[source.id, t] = float(quantity)
    return bounds


def solve(req: Request, worlds: list[World], *, service_floor: bool = False,
          service_first: str | None = None, cvar_weight: float = 0.,
          fixed: Solution | None = None, disabled: frozenset[str] = frozenset(),
          targets: dict[tuple[str, int], float] | None = None,
          per_world_service: bool = False, service_risk: str = "expected",
          service_risk_levels: dict[str, float] | None = None,
          excess_penalty: dict[tuple[str, str], tuple[float, float]] | None = None,
          continuation: dict[tuple[str, str], tuple[float, float]] | None = None,
          seed: Solution | None = None,
          allowed_periods: frozenset[int] | None = None,
          expected_shortage: dict | None = None,
          continuation_feeds: dict[tuple[str, str], list[dict]] | None = None,
          nodes: "NodeMap | None" = None) -> Solution:
    """excess_penalty (v6): {(sku, location): (baseline_units, cost_per_unit_period)} charges inventory
    held above the lean baseline while a temporary risk driver is gone, so the plan runs temporary
    protection down through demand rather than replenishing it. continuation (v6): {(sku, location):
    (post_horizon_demand_units, margin_per_unit)} lets end-of-horizon stock and post-horizon arrivals
    earn the service margin on demand expected during the next replenishment lead instead of only
    salvage, so late-horizon decisions are not artificially idle. Both use information available
    at the review only (fitted mean demand, declared lead). nodes (P4): the information-set node
    map of an adaptive solve - purchase and transfer columns of a period at or after a review epoch
    exist once per information set and every world reads its own set's column (non-anticipativity
    by construction); None = the frozen builder path, bit for bit."""
    started = time.monotonic()
    if not worlds or abs(sum(w.weight for w in worlds) - 1) > 1e-8 or any(w.weight <= 0 for w in worlds):
        raise ValueError("positive scenario weights must sum to one")
    H = req.horizon
    if any(len(w.demand[s.id]) != H for w in worlds for s in req.services):
        raise ValueError("world dimensions do not match request")
    skus = {s.id: s for s in req.skus}
    locs = {location_key.id: location_key for location_key in req.locations}
    sources = {s.id: s for s in req.sources}
    terms = {p.id: p for p in req.terms}
    customers = {c.id: c for c in req.customers}
    calendars = {c.id: c for c in req.calendars}
    # Sector operating physics (three-sector engine): None on a legacy request, and then no branch
    # below reads it. Physics changes the decision environment - which cohorts may be received,
    # held, moved or sold, and what a residual unit is worth - never the objective's ownership.
    physics = sector_physics(req)
    # Sourcing portfolio (P3): None on a frozen request. Adds declared share rows, one first-stage
    # switching binary per declared non-incumbent source, and skips the binaries of a source-period
    # that can carry nothing (exact). Never a new objective of its own.
    sourcing = sourcing_view(req)
    m = Linear()
    x: dict[tuple, int] = {}
    tr: dict[tuple, int] = {}
    po, inv, use, unmet, cash, debt = {}, {}, {}, {}, {}, {}
    # P4 node indexing. `nodes_at(t)` lists the information-set nodes whose columns exist at period
    # t (`(None,)` = the single here-and-now column, the frozen naming); `node_of(w, t)` is the
    # node world w reads; `name_at(base, node)` appends the node id to a column name only when the
    # column is a recourse column, so a frozen solve produces exactly the frozen names.
    def nodes_at(t: int, kind: str = "purchase") -> tuple:
        return (None,) if nodes is None else nodes.nodes(t, kind)

    def node_of(w: int, t: int, kind: str = "purchase"):
        return None if nodes is None else nodes.node(w, t, kind)

    def members_of(t: int, node, kind: str = "purchase") -> tuple[int, ...]:
        return tuple(range(len(worlds))) if nodes is None else nodes.members(t, node, kind)

    def name_at(base: tuple, node) -> tuple:
        return base if node is None else base + (node,)

    def xw(w: int, sid: str, t: int) -> int:
        return x[sid, t, node_of(w, t)]

    def paths() -> list[tuple]:
        """Distinct node paths through the horizon (one per world when nodes differ; one path on the frozen builder)."""
        seen: dict[tuple, int] = {}
        for w in range(len(worlds)):
            seen.setdefault(tuple(node_of(w, t) for t in range(H)), w)
        return list(seen)
    use_by_stock = defaultdict(list)
    stock_indices = defaultdict(list)
    use_for_service: dict[tuple, dict[int, float]] = defaultdict(dict)
    ordered_services = sorted(req.services, key=lambda s: (-customers[s.customer].priority,
        -(s.selling_price - skus[s.sku].asset_value), s.id))
    service_rank = {s.id: n for n, s in enumerate(ordered_services)}
    service_for_stock = defaultdict(list)
    for service in ordered_services:
        for sku, _, _ in compatible(req, service):
            service_for_stock[sku, service.location].append(service)
    costs: list[dict[int, float]] = [defaultdict(float) for _ in worlds]
    tiebreak: list[dict[int, float]] = [defaultdict(float) for _ in worlds]   # objective only (P1)
    # Analytic expected shortage (P1 final closure): a planning surrogate for a single mean-world
    # solve. `expected_shortage` is the forecast dict; for every service and period the objective
    # charges the declared shortage penalty on E[(D - available)^+] under the fitted mixture in
    # place of the mean world's own (mean - available)^+, through an exact cut envelope. Objective
    # only: never the ledger, never the projected cost, never a stochastic solve.
    surrogate: list[dict[int, float]] = [defaultdict(float) for _ in worlds]
    shortage_terms: list[tuple] = []
    if expected_shortage is not None and len(worlds) == 1:
        from zaad.full.shortage import demand_atoms, loss_cuts
        for service in req.services:
            fit = expected_shortage.get(service.id)
            if not fit:
                continue
            for t in range(H):
                multiplier = 1.
                for event in req.events:
                    if event.service == service.id and event.start <= t <= event.end:
                        multiplier *= event.multiplier
                atoms, zero = demand_atoms(fit, multiplier)
                cuts = loss_cuts(atoms, zero)
                if cuts:
                    shortage_terms.append((service, t, cuts))
    # Post-horizon supply per (sku, location): arrivals due at or after H and end-of-horizon stock (v6 continuation).
    post: list[dict[tuple[str, str], dict[int, float]]] = [defaultdict(lambda: defaultdict(float)) for _ in worlds]
    post_expiry: dict[int, int] = {}      # supply variable -> its cohort's expiry period (sector physics continuation)
    payments: list[list[dict[int, float]]] = [[defaultdict(float) for _ in range(H)] for _ in worlds]
    arrivals: list[dict[tuple, dict[int, float]]] = [defaultdict(lambda: defaultdict(float)) for _ in worlds]
    outbound: dict[tuple, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    cohorts = defaultdict(set)
    locked: dict[str, float] = defaultdict(float)
    initial: dict[tuple, float] = defaultdict(float)
    constant = req.liquidity.opening_debt * req.liquidity.interest_per_period
    quote_groups = defaultdict(list)
    for lot in req.stock:
        cohorts[lot.sku].add(lot.expires_in)
        initial[lot.sku, lot.location, lot.expires_in] += lot.usable
        locked[lot.location] += (lot.quantity - lot.usable) * skus[lot.sku].volume
        constant += lot.usable * skus[lot.sku].asset_value
        if lot.expires_in == 0:
            constant += lot.usable * skus[lot.sku].disposal_fee
    for inbound in req.inbound_transfers:
        cohorts[inbound.sku].add(inbound.expires_in)
        q = m.var(("inbound_transfer", inbound.id), lower=inbound.accepted_quantity, upper=inbound.accepted_quantity)
        constant += inbound.accepted_quantity * skus[inbound.sku].asset_value
        for w in range(len(worlds)):
            arrivals[w][inbound.sku, inbound.destination, inbound.expires_in, inbound.due_in][q] += 1
            if inbound.due_in >= H:
                costs[w][q] -= skus[inbound.sku].terminal_value
                post[w][inbound.sku, inbound.destination][q] += 1.
                post_expiry[q] = int(inbound.expires_in)
    tail: list[dict[int, float]] = [defaultdict(float) for _ in worlds]

    def expense(index, amount, w, when):
        costs[w][index] += amount
        if 0 <= when < H:
            payments[w][when][index] += amount
        elif when >= H:
            # Committed after the horizon: not paid inside the plan, but it must be financeable at the end.
            tail[w][index] += amount
    # "alternates" disabled keeps only the cheapest approved source per SKU and destination, so the
    # value of the other approved suppliers and routes can be measured rather than assumed.
    cheapest: dict[tuple[str, str], tuple[float, str]] = {}
    for source in req.sources:
        if source.approved and source.compliance == "cleared":
            term = terms[source.terms]
            landed = source.unit_price * term.fx_rate_to_currency + source.freight_per_unit + source.handling_per_unit
            pair = (source.sku, source.destination)
            if pair not in cheapest or (landed, source.id) < cheapest[pair]:
                cheapest[pair] = (landed, source.id)
    primary_id = {key: value[1] for key, value in cheapest.items()}
    # Exact activation bounds for the order / MOQ linking rows (P3 performance closure); the
    # purchase column itself keeps the declared capacity as its bound.
    tight = activation_bounds(req, worlds, targets=targets, continuation=continuation, continuation_feeds=continuation_feeds,
                              fixed=fixed, sourcing=sourcing, expected_shortage=expected_shortage)
    # Purchase variables and fixed costs, continuous unless actual pack/MOQ needs MILP.
    for source in req.sources:
        term = terms[source.terms]
        price = source.unit_price * term.fx_rate_to_currency
        landed = price + source.freight_per_unit + source.handling_per_unit
        for t in range(H):
            origin = req.as_of + timedelta(days=req.period_days * t)
            order_date = next_open(origin, calendars[source.order_calendar])
            eligible = source.approved and source.compliance == "cleared" and order_date <= source.quote_expires
            if "alternates" in disabled and primary_id.get((source.sku, source.destination)) != source.id:
                eligible = False
            if physics is not None and (not physics.location_ok(source.sku, source.destination)
                                        or physics.receipt_life(source.sku, source.id) <= physics.min_receipt(source.sku)):
                # the destination cannot store the SKU's state, or every arrival lands below the
                # minimum remaining life at receipt: the source is not usable (sector physics)
                eligible = False
            cap = min(source.maximum, source.capacity_by_period[t]) if eligible else 0.
            if allowed_periods is not None and t not in allowed_periods:
                cap = 0.   # cadence candidate (P1): no order is placed outside the cadence
            departure = dates(req, source, t)[0]
            for node in nodes_at(t):
              q = m.var(name_at(("purchase", source.id, t), node), upper=cap)
              x[source.id, t, node] = q
              # Zero-capability pruning (P3, exact): a column bounded at zero needs no pack, activation or
              # quote-group binary; their only value was 0 (or a cost-free tie inside a quote group).
              pruned = sourcing is not None and sourcing.portfolio.prune_zero_capability and cap <= 0
              multiple = source.multiple if "continuous" not in disabled else max(source.multiple, 10.)
              if multiple > 0 and not pruned:
                units = m.var(name_at(("packs", source.id, t), node), upper=math.floor(cap / multiple), integer=True)
                m.row({q: 1, units: -multiple}, 0, 0)
              for label, increment in (("case", source.case_multiple), ("pallet", source.pallet_multiple), ("transport", source.transport_multiple)):
                if increment and not pruned:
                    units = m.var(name_at((label, source.id, t), node), upper=math.floor(cap / increment), integer=True)
                    m.row({q: 1, units: -increment}, 0, 0)
              if (source.minimum or source.fixed_order_fee or source.exclusive_quote_group) and not pruned:
                active = m.var(name_at(("active", source.id, t), node), upper=1, integer=True)
                m.row({q: 1, active: -min(cap, tight.get((source.id, t), cap))}, upper=0)
                m.row({q: 1, active: -source.minimum}, lower=0)
                for w in members_of(t, node):
                    expense(active, source.fixed_order_fee, w, t)
                if source.exclusive_quote_group:
                    quote_groups[source.exclusive_quote_group, t, node].append(active)
              if fixed is not None:
                quantity = fixed.purchases.get((source.id, t), 0.)
                m.row({q: 1}, quantity, quantity)
              for w in members_of(t, node):
                world = worlds[w]
                due, fill = world.arrival[source.id, t], world.fills[source.id, t]
                if not 0 <= fill <= 1 or due <= t:
                    raise ValueError("invalid physical fill or arrival chronology")
                expiry = due + (skus[source.sku].shelf_life if physics is None else physics.receipt_life(source.sku, source.id))
                cohorts[source.sku].add(expiry)
                arrivals[w][source.sku, source.destination, expiry, due][q] += fill
                trigger = {"order": t, "shipment": departure, "arrival": due}[term.balance_trigger]
                net = math.ceil(term.net_days / req.period_days)
                # Total contract invoice is cost regardless of whether payment is beyond horizon.
                costs[w][q] += landed + price * term.financing_fee_fraction
                # Timing tie-break (P1): a purchase committed earlier carries a token objective
                # penalty so that, when nothing else separates two timings, the later one wins.
                # It goes to the solver objective only, never to the plan's projected economics.
                # Scaled by the horizon so its total can never exceed `timing_tiebreak` times the
                # plan's purchase value (1e-4 of spend at the default), whatever the horizon.
                tiebreak[w][q] += req.timing_tiebreak * price * (H - 1 - t) / max(1, H - 1)
                payments[w][t][q] += price * term.deposit_fraction
                payment_t = trigger + net
                if payment_t < H:
                    payments[w][payment_t][q] += price * (1 - term.deposit_fraction)
                if departure < H:
                    payments[w][departure][q] += source.freight_per_unit + source.handling_per_unit
                payments[w][t][q] += price * term.financing_fee_fraction
                if due >= H:
                    costs[w][q] -= fill * skus[source.sku].terminal_value
                    post_expiry.setdefault(q, expiry)
                    # New purchases landing after the horizon earn salvage only: continuation demand
                    # may be served by stock held to the end and by orders already committed, never
                    # by a plan to buy late for it (that incentive deferred buying into a closure).
    for group in quote_groups.values():
        m.row({v: 1 for v in group}, upper=1)
    if sourcing is not None:
        # Declared share limits (P3): linear rows on the pair's commitment. A fixed plan (the incumbent
        # or a projected policy being evaluated) is not re-chosen, so the rows do not apply to it.
        pair_sources: dict[tuple[str, str], list[str]] = defaultdict(list)
        for source in req.sources:
            pair_sources[source.sku, source.destination].append(source.id)
        if fixed is None:
            for (sku, destination), rows in sourcing.shares.items():
                members = pair_sources[sku, destination]
                for c in rows:
                  windows = [list(range(H))] if c.scope == "horizon" else [[t] for t in range(H)]
                  for path in paths():   # one row set per distinct node path (P4); the frozen builder has one path
                    for ts in windows:
                        own_cols = {x[c.source, t, path[t]]: 1. for t in ts}
                        if c.minimum_share > 0:
                            share_row: dict[int, float] = {x[s, t, path[t]]: -c.minimum_share for s in members for t in ts}
                            for k, v in own_cols.items():
                                share_row[k] = share_row.get(k, 0.) + v
                            m.row(share_row, lower=0)
                        if c.maximum_share < 1:
                            share_row = {x[s, t, path[t]]: -c.maximum_share for s in members for t in ts}
                            for k, v in own_cols.items():
                                share_row[k] = share_row.get(k, 0.) + v
                            m.row(share_row, upper=0)
                    if c.committed_units > 0 and c.scope == "horizon":
                        m.row({x[c.source, t, path[t]]: 1. for t in range(H)}, lower=c.committed_units)
        # Declared switching / qualification cost (P3): one first-stage binary per declared source
        # outside the incumbent mix, charged once when the source receives any quantity in the plan.
        for sid, row_cost in sourcing.switching.items():
            cost = sourcing.switching_cost(sid)
            if cost <= 0:
                continue
            total_cap = sum(m.upper[x[sid, t, node]] for t in range(H) for node in nodes_at(t))
            if total_cap <= 0:
                continue
            switch = m.var(("switch", sid), upper=1, integer=True)
            for path in paths():
                m.row({**{x[sid, t, path[t]]: 1. for t in range(H)}, switch: -total_cap}, upper=0)
            for w in range(len(worlds)):
                expense(switch, cost, w, 0)
    # Supplier-order economics (P1). One order per supplier and period: minimum order value across
    # its lines, a fixed order cost charged once, a receipt fee charged once on arrival, and the
    # shipment priced as a whole - integer pallets, a stepped tariff (exactly one tier when an
    # order exists), per-pallet freight and receiving. The same rows are re-checked in settlement.
    for supplier, srcs, st in supplier_orders(req):
        upp = pallet_units(st, srcs)
        for t in range(H):
            caps = {s.id: min(s.maximum, s.capacity_by_period[t], tight.get((s.id, t), math.inf)) for s in srcs}
            if allowed_periods is not None and t not in allowed_periods:
                caps = {k: 0. for k in caps}
            departure = min(dates(req, s, t)[0] for s in srcs)
            for node in nodes_at(t):
              order = m.var(name_at(("order", supplier, t), node), upper=1, integer=True)
              for s in srcs:
                m.row({x[s.id, t, node]: 1, order: -caps[s.id]}, upper=0)
              if st.minimum_order_value:
                m.row({**{x[s.id, t, node]: s.unit_price * terms[s.terms].fx_rate_to_currency for s in srcs}, order: -st.minimum_order_value}, lower=0)
              if st.max_shipment_weight is not None and physics is not None:
                # shipment weight cap (sector physics): like the pallet cap, one continuous row per order
                m.row({**{x[s.id, t, node]: float(physics.weight(s.sku) or 0.) for s in srcs}, order: -st.max_shipment_weight}, upper=0)
              for w in members_of(t, node):
                world = worlds[w]
                arrival = min(world.arrival[s.id, t] for s in srcs)
                if st.fixed_order_cost:
                    expense(order, st.fixed_order_cost, w, t)
                if st.receiving_fee_per_receipt:
                    expense(order, st.receiving_fee_per_receipt, w, arrival)
              if upp is None:
                continue
              pallets = m.var(name_at(("pallets", supplier, t), node), upper=math.ceil(sum(caps[s.id] / upp[s.id] for s in srcs)) + 1, integer=True)
              m.row({pallets: 1, **{x[s.id, t, node]: -1. / upp[s.id] for s in srcs}}, lower=0)
              top = st.max_pallets if st.max_pallets is not None else (st.freight_tiers[-1].up_to_pallets if st.freight_tiers else None)
              if top is not None:
                m.row({pallets: 1, order: -top}, upper=0)
              if st.freight_tiers:
                tiers = [m.var(name_at(("freight_tier", supplier, t, k), node), upper=1, integer=True) for k in range(len(st.freight_tiers))]
                m.row({**{v: 1 for v in tiers}, order: -1}, 0, 0)
                m.row({pallets: 1, **{v: -tier.up_to_pallets for v, tier in zip(tiers, st.freight_tiers)}}, upper=0)
              for w in members_of(t, node):
                world = worlds[w]
                arrival = min(world.arrival[s.id, t] for s in srcs)
                if st.freight_tiers:
                    for v, tier in zip(tiers, st.freight_tiers):
                        expense(v, tier.charge, w, departure)
                if st.freight_per_pallet:
                    expense(pallets, st.freight_per_pallet, w, departure)
                if st.receiving_per_pallet:
                    expense(pallets, st.receiving_per_pallet, w, arrival)
    if req.engine_profile == "reliability" and effective_smoothing(req) > 0 and fixed is None:
        # Stability: |x_t - x_{t-1}| per source charged at a small fraction of landed cost.
        for source in req.sources:
            term = terms[source.terms]
            landed = source.unit_price * term.fx_rate_to_currency + source.freight_per_unit + source.handling_per_unit
            charge = effective_smoothing(req) * landed
            for path in paths():
              for t in range(1, H):
                up = m.var(name_at(("smooth_up", source.id, t), path[t]), cost=charge)
                down = m.var(name_at(("smooth_down", source.id, t), path[t]), cost=charge)
                m.row({x[source.id, t, path[t]]: 1, x[source.id, t - 1, path[t - 1]]: -1, up: -1, down: 1}, 0, 0)
    # Outstanding PO amendments: only explicit contractual options, no invented permission.
    for order in req.pipeline:
        source = sources[order.source]
        if po_closed(order, source):
            # Residue from an earlier solve, not an obligation: no variables, no exclusivity row.
            continue
        constant += order.prepaid_per_remaining_unit * order.remaining
        quantities, switches = [], []
        for option in order.options:
            allowed = (option.action == "keep" or (option.deadline >= req.as_of and order.stage in option.allowed_stages))
            if option.action in disabled:
                allowed = False
            capacity = min(order.remaining, option.max_quantity) if allowed else 0.
            q = m.var(("amend", order.id, option.id), upper=capacity)
            po[order.id, option.id] = q
            quantities.append(q)
            if not order.allow_split_amendments:
                flag = m.var(("po_option", order.id, option.id), upper=1, integer=True)
                m.row({q: 1, flag: -order.remaining}, 0, 0)
                switches.append(flag)
            if fixed is not None:
                amount = fixed.amendments.get((order.id, option.id), 0.)
                m.row({q: 1}, amount, amount)
            for w, world in enumerate(worlds):
                expense(q, option.fee_per_unit, w, 0)
                if option.credit_per_unit > 0:
                    # P4B V1: a declared refund / credit note per amended unit, bounded at the contract by the
                    # PO's refundable deposit (cash in at period 0). Absent (0) the frozen build is untouched.
                    expense(q, -option.credit_per_unit, w, 0)
                expense(q, option.remaining_invoice_per_unit, w, option.payment_due_in)
                if option.action == "cancel":
                    continue
                due = world.po_due[order.id] if option.action == "keep" else option.due_in
                # Changed ETA is a contractual target, subject to the world's PO ETA error.
                if option.action != "keep":
                    keep = next(o for o in order.options if o.action == "keep")
                    due += max(0, world.po_due[order.id] - keep.due_in)
                expiry = due + (skus[source.sku].shelf_life if physics is None else physics.receipt_life(source.sku, source.id))
                cohorts[source.sku].add(expiry)
                arrivals[w][source.sku, source.destination, expiry, due][q] += world.po_fill[order.id]
                if due >= H:
                    costs[w][q] -= world.po_fill[order.id] * skus[source.sku].terminal_value
                    post[w][source.sku, source.destination][q] += world.po_fill[order.id]
                    post_expiry.setdefault(q, expiry)
        m.row({q: 1 for q in quantities}, order.remaining, order.remaining)
        if switches:
            m.row({q: 1 for q in switches}, 1, 1)
    # Reachable SKU/location pairs only, not a dense Cartesian network.
    pairs = {(location_key.sku, location_key.location) for location_key in req.stock} | {(s.sku, s.destination) for s in req.sources}
    pairs |= {(s.sku, s.location) for s in req.services}
    for arc in req.transfers:
        pairs.update(((arc.sku, arc.origin), (arc.sku, arc.destination)))
    for service in req.services:
        for sku, _, _ in compatible(req, service):
            pairs.add((sku, service.location))
    latest_due: dict[str, int] = defaultdict(int)   # latest transfer arrival the plan can schedule, per SKU
    for arc in req.transfers:
        for t in range(H):
            ids = []
            # Receiving calendar, rather than silently unloading on closed days.
            when = req.as_of + timedelta(days=(t + arc.lead_periods) * req.period_days)
            actual = next_open(when, calendars[locs[arc.destination].receiving_calendar])
            due = math.ceil((actual - req.as_of).total_seconds() / (86400 * req.period_days))
            latest_due[arc.sku] = max(latest_due[arc.sku], due)
            for expiry in sorted(cohorts[arc.sku]):
                if expiry <= t + arc.lead_periods:
                    continue
                cap = arc.capacity if arc.approved and "transfers" not in disabled else 0.
                if due >= expiry:
                    cap = 0.
                if physics is not None and (not physics.lane_ok(arc.sku, arc.id) or not physics.location_ok(arc.sku, arc.destination)
                                            or not physics.receivable(arc.sku, expiry, due)):
                    # the lane or the destination cannot carry / hold the SKU's state, or the cohort
                    # would arrive below the minimum remaining life at receipt (sector physics)
                    cap = 0.
                for node in nodes_at(t, "transfer"):
                  q = m.var(name_at(("transfer", arc.id, expiry, t), node), upper=cap)
                  tr[arc.id, expiry, t, node] = q
                  ids.append((node, q))
                  outbound[arc.sku, arc.origin, expiry, t, node][q] += 1
                  if fixed is not None:
                    amount = fixed.transfers.get((arc.id, expiry, t), 0.)
                    m.row({q: 1}, amount, amount)
                  for w in members_of(t, node, "transfer"):
                    arrivals[w][arc.sku, arc.destination, expiry, due][q] += 1 - arc.loss_fraction
                    expense(q, arc.cost_per_unit, w, t)
                    if due >= H:
                        costs[w][q] -= (1 - arc.loss_fraction) * skus[arc.sku].terminal_value
                        post[w][arc.sku, arc.destination][q] += 1 - arc.loss_fraction
                        post_expiry.setdefault(q, expiry)
            for node in nodes_at(t, "transfer"):
              node_ids = [q for n, q in ids if n == node]
              if node_ids:
                m.row({q: 1 for q in node_ids}, upper=arc.capacity)
                lane_cap = arc.capacity if arc.approved and "transfers" not in disabled else 0.
                if arc.multiple > 0 and lane_cap > 0 and t == 0:
                    # Transfer packs (P2): the executable movement over the lane is a whole number of
                    # packs across cohorts. Later periods are replanning guidance (the settlement judges
                    # packs on period zero, the only period an operator executes), so they stay
                    # continuous and the model does not carry a general integer per lane-period. A lane
                    # without a declared pack is continuous, as before.
                    packs = m.var(name_at(("transfer_packs", arc.id, t), node), upper=math.floor(lane_cap / arc.multiple), integer=True)
                    m.row({**{q: 1 for q in node_ids}, packs: -arc.multiple}, 0, 0)
                if arc.fixed_cost_per_dispatch > 0 and lane_cap > 0:
                    # Per-dispatch cost (P2): charged once in any period the lane carries anything.
                    dispatch = m.var(name_at(("transfer_dispatch", arc.id, t), node), upper=1, integer=True)
                    m.row({**{q: 1 for q in node_ids}, dispatch: -lane_cap}, upper=0)
                    for w in members_of(t, node, "transfer"):
                        expense(dispatch, arc.fixed_cost_per_dispatch, w, t)
    # Executable transfers share observed opening inventory across all arcs.
    # Expected PO receipts, including overdue ones, cannot fund today's action.
    confirmed: dict[tuple[str, str, int], float] = defaultdict(float)
    for inbound in req.inbound_transfers:
        if inbound.due_in == 0:
            confirmed[inbound.sku, inbound.destination, inbound.expires_in] += inbound.accepted_quantity
    for (sku, origin, expiry, t, _node), transfer_terms in outbound.items():
        if t == 0:
            m.row(transfer_terms, upper=initial[sku, origin, expiry] + confirmed[sku, origin, expiry])
    for resource in req.resources:
        for t in range(H):
            for node in nodes_at(t):
                row = {x[s.id, t, node]: skus[s.sku].volume for s in req.sources if resource.id in s.resources}
                if row:
                    m.row(row, upper=resource.capacity_by_period[t])
    for w, world in enumerate(worlds):
        for t in range(H):
            for sku, location in sorted(pairs):
                for expiry in sorted(cohorts[sku]):
                    if expiry <= t:
                        continue
                    index = m.var(("inventory", sku, location, expiry, t, w),
                                  upper=(0. if physics is not None and not physics.location_ok(sku, location)
                                         else max(0., (locs[location].capacity_volume - locked[location]) / skus[sku].volume)))
                    inv[sku, location, expiry, t, w] = index
                    stock_indices[sku, location, t, w].append(index)
                    costs[w][index] += skus[sku].asset_value * locs[location].holding_per_value_period
                    if expiry == t + 1 and t < H - 1:
                        costs[w][index] += skus[sku].disposal_fee
                    if t == H - 1:
                        costs[w][index] -= skus[sku].terminal_value if expiry > H else 0.
                        if expiry > H:
                            post[w][sku, location][index] += 1.
                            post_expiry[index] = expiry
            if excess_penalty:
                for (sku, location), (baseline, rate) in excess_penalty.items():
                    held = stock_indices.get((sku, location, t, w), [])
                    if held and rate > 0:
                        excess = m.var(("excess", sku, location, t, w))
                        m.row({**{i: 1. for i in held}, excess: -1.}, upper=max(0., baseline))
                        costs[w][excess] += rate
            for service in req.services:
                d = world.demand[service.id][t]
                if d < 0 or not math.isfinite(d):
                    raise ValueError("invalid world demand")
                u = m.var(("unmet", service.id, t, w), upper=d)
                unmet[service.id, t, w] = u
                costs[w][u] += service.selling_price + service.sla_per_unmet
                payments[w][t][u] += service.sla_per_unmet
                balance = {u: 1.}
                for sku, conversion, fee in compatible(req, service):
                    if "substitutions" in disabled and sku != service.sku:
                        continue
                    consumptions = []
                    stocks = []
                    for expiry in sorted(cohorts[sku]):
                        key = (sku, service.location, expiry, t, w)
                        if key not in inv:
                            continue
                        if physics is not None and not physics.sellable(sku, expiry, t):
                            # below the minimum remaining life at sale: physical stock, not sellable stock
                            continue
                        q = m.var(("allocate", sku, service.id, expiry, t, w), upper=d)
                        use[sku, service.id, expiry, t, w] = (q, conversion)
                        use_by_stock[sku, service.location, expiry, t, w].append((q, conversion))
                        use_for_service[service.id, sku, t, w][q] = conversion
                        balance[q] = 1.
                        costs[w][q] += fee
                        if fee:
                            payments[w][t][q] += fee
                        consumptions.append((expiry, q))
                        stocks.append(inv[key])
                    if d > 0 and stocks:
                        # Available compatible stock cannot be hoarded while demand is lost.
                        empty = m.var(("depleted", sku, service.id, t, w), upper=1, integer=True)
                        m.row({u: 1, empty: -d}, upper=0)
                        cap = locs[service.location].capacity_volume / skus[sku].volume
                        m.row({**{i: 1 for i in stocks}, empty: cap}, upper=cap)
                        # FEFO: consumption of younger cohorts requires older remaining stock zero.
                        # An older cohort beyond the window (outlives the horizon and every schedulable
                        # transfer arrival) is interchangeable with the younger one: omitted exactly.
                        window = max(H, latest_due[sku]) if (FEFO_SYMMETRY_ELIMINATION and req.transfers) else math.inf
                        for expiry, q in consumptions:
                            older = [inv[sku, service.location, e, t, w] for e in cohorts[sku]
                                     if t < e < expiry and e <= window and (sku, service.location, e, t, w) in inv
                                     and (physics is None or physics.sellable(sku, e, t))]
                            if older:
                                active = m.var(("fefo", sku, service.id, expiry, t, w), upper=1, integer=True)
                                m.row({q: 1, active: -d}, upper=0)
                                m.row({**{i: 1 for i in older}, active: cap}, upper=cap)
                m.row(balance, d, d)
            # Same current-review customer priority and direct-before-substitution
            # semantics as settlement; later demand cannot steal today's stock.
            for rank, high in enumerate(ordered_services):
                high_demand = world.demand[high.id][t]
                if not high_demand:
                    continue
                eligible_skus = {sku for sku, _, _ in compatible(req, high)}
                lower_candidates = {s.id: s for sku in eligible_skus for s in service_for_stock[sku, high.location]
                                    if service_rank[s.id] > rank}
                for low in lower_candidates.values():
                    for sku, ratio, _ in compatible(req, low):
                        if sku not in eligible_skus:
                            continue
                        lower_units = use_for_service[low.id, sku, t, w]
                        if lower_units:
                            active = m.var(("priority", high.id, low.id, sku, t, w), upper=1, integer=True)
                            m.row({unmet[high.id, t, w]: 1, active: -high_demand}, upper=0)
                            cap = locs[high.location].capacity_volume / skus[sku].volume
                            m.row({**lower_units, active: cap}, upper=cap)
                direct_remaining = stock_indices[high.sku, high.location, t, w]
                substitute_units = {q: 1 for sku in eligible_skus if sku != high.sku
                                    for q in use_for_service[high.id, sku, t, w]}
                if direct_remaining and substitute_units:
                    active = m.var(("direct_first", high.id, t, w), upper=1, integer=True)
                    cap = locs[high.location].capacity_volume / skus[high.sku].volume
                    m.row({**substitute_units, active: -high_demand}, upper=0)
                    m.row({**{i: 1 for i in direct_remaining}, active: cap}, upper=cap)
            for sku, location in sorted(pairs):
                for expiry in sorted(cohorts[sku]):
                    key = (sku, location, expiry, t, w)
                    if key not in inv:
                        continue
                    row = defaultdict(float, {inv[key]: 1})
                    prior = inv.get((sku, location, expiry, t - 1, w))
                    if prior is not None:
                        row[prior] -= 1
                    for q, coefficient in arrivals[w][sku, location, expiry, t].items():
                        row[q] -= coefficient
                    for q, coefficient in outbound[sku, location, expiry, t, node_of(w, t, "transfer")].items():
                        row[q] += coefficient
                    for used_q, used_conversion in use_by_stock[key]:
                        row[used_q] += used_conversion
                    opening = initial[sku, location, expiry] if t == 0 else 0.
                    m.row(row, opening, opening)
            for warehouse in req.locations:
                row = {index: skus[sku].volume for (sku, location_key, _, period, scenario), index in inv.items()
                       if location_key == warehouse.id and period == t and scenario == w}
                if row:
                    m.row(row, upper=warehouse.capacity_volume - locked[warehouse.id])
                # Capacity applies before serving demand too, not just end-of-period stock.
                before: dict[int, float] = defaultdict(float)
                for (sku, location_key, expiry, period, scenario), index in inv.items():
                    if location_key == warehouse.id and period == t - 1 and scenario == w and expiry > t:
                        before[index] += skus[sku].volume
                for (sku, location_key, _, period), flows in arrivals[w].items():
                    if location_key == warehouse.id and period == t:
                        for index, factor in flows.items():
                            before[index] += factor * skus[sku].volume
                initial_volume = sum(v * skus[k].volume for (k, location_key, e), v in initial.items()
                                     if location_key == warehouse.id and e > 0) if t == 0 else 0.
                if before or initial_volume + locked[warehouse.id] > warehouse.capacity_volume:
                    m.row(before, upper=warehouse.capacity_volume - locked[warehouse.id] - initial_volume)
            # Cash balance: contractual payments, explicit debt and interest, no forecast sales receipts.
            liquidity = req.liquidity
            c = m.var(("cash", t, w), lower=liquidity.minimum_cash)
            b = m.var(("debt", t, w), upper=liquidity.credit_limit)
            cash[t, w], debt[t, w] = c, b
            # Working capital (P1): the operator's own cash below its opening balance earns the
            # cost of capital elsewhere; charging -rate x cash is that charge up to a constant
            # shared by every candidate. Drawn debt pays interest instead (never both).
            costs[w][c] -= liquidity.cost_of_capital_per_period
            row = defaultdict(float, {c: 1, b: -1})
            prior_cash, prior_debt = cash.get((t - 1, w)), debt.get((t - 1, w))
            rhs = liquidity.known_receivables[t] - liquidity.other_payments[t]
            if prior_cash is not None:
                assert prior_debt is not None
                row[prior_cash] -= 1
                row[prior_debt] += 1 + liquidity.interest_per_period
                costs[w][prior_debt] += liquidity.interest_per_period
            else:
                rhs += liquidity.opening_cash - liquidity.opening_debt * (1 + liquidity.interest_per_period)
            for q, amount in payments[w][t].items():
                row[q] += amount
            m.row(row, rhs, rhs)
            # Letters of credit reserve liquidity until receipt, separately from expense.
            reserve = defaultdict(float, {c: -1})
            for source in req.sources:
                term = terms[source.terms]
                for placed in range(t + 1):
                    if world.arrival[source.id, placed] > t:
                        reserve[xw(w, source.id, placed)] += source.unit_price * term.fx_rate_to_currency * term.letter_of_credit_fraction
            m.row(reserve, upper=-liquidity.minimum_cash)
            if t == H - 1 and tail[w]:
                # Terminal solvency: closing cash above the floor plus unused credit must cover every
                # invoice this plan commits to after the horizon. No forecast receipts are counted.
                terminal = defaultdict(float, {c: -1, b: 1})
                for q, amount in tail[w].items():
                    terminal[q] += amount
                m.row(terminal, upper=liquidity.credit_limit - liquidity.minimum_cash)
    order_vars: dict = {}
    counted_orders: set = set()
    if service_floor:
        for service in req.services:
            if service.metric != "unit_fill":
                lines = [line for line in req.order_lines if line.service == service.id
                         and line.due_in < H and line.open_quantity > 0]
                if not lines:
                    raise ValueError("order-level service requires outstanding lines in the horizon")
                metric_terms = {}
                denominator = 0.
                for w, world in enumerate(worlds):
                    complete: dict = {}
                    for line in lines:
                        qty = line.open_quantity
                        full = m.var(("line_full", line.id, w), upper=1, integer=True)
                        complete[line.id] = full
                        allocated = m.var(("line_units", line.id, w), upper=qty)
                        m.row({allocated: 1, full: -qty}, lower=0)
                        complete[(line.id, "units")] = allocated
                        if service.metric in ("otif", "order_otif"):
                            delivery = req.as_of + timedelta(days=line.due_in * req.period_days)
                            if delivery > line.promised_at:
                                m.row({full: 1}, 0, 0)
                    for t in {line.due_in for line in lines}:
                        row = {complete[line.id, "units"]: 1 for line in lines if line.due_in == t}
                        row[unmet[service.id, t, w]] = 1
                        m.row(row, upper=world.demand[service.id][t])
                    if service.metric in ("order_fill", "order_otif"):
                        # One completeness variable per order and world, shared by every service the
                        # order touches: a multi-SKU order is complete only when all its lines are.
                        for order_id in {line.order_id for line in lines}:
                            order_key = ("order_full", order_id, w)
                            full = order_vars.get(order_key)
                            if full is None:
                                full = order_vars[order_key] = m.var(order_key, upper=1, integer=True)
                            for line in lines:
                                if line.order_id == order_id:
                                    m.row({full: 1, complete[line.id]: -1}, upper=0)
                            if order_key not in counted_orders:
                                counted_orders.add(order_key)
                                metric_terms[full] = world.weight
                                denominator += world.weight
                    else:
                        for line in lines:
                            metric_terms[complete[line.id]] = world.weight
                            denominator += world.weight
                m.row(metric_terms, lower=service.target * denominator)
                continue
            row, demand = {}, 0.
            for w, world in enumerate(worlds):
                for t in range(H):
                    row[unmet[service.id, t, w]] = world.weight
                    demand += world.weight * world.demand[service.id][t]
            m.row(row, upper=(1 - service.target) * demand)
            risk_level = (service_risk_levels or {}).get(service.id, req.service_risk_level)
            if service_risk == "cvar" and len(worlds) > 1 and risk_level > 0:
                # Quantile protection (Rockafellar-Uryasev): the mean unmet fraction over the worst
                # (1 - level) share of scenarios must also respect the target. Protection then scales
                # with the spread of the scenarios and vanishes when they are tight, or when the
                # SKU/location risk state is calm (level scaled by protection activity).
                eta = m.var(("service_eta", service.id))
                tail_terms: dict[int, float] = {eta: 1.}
                for w, world in enumerate(worlds):
                    total_w = sum(world.demand[service.id])
                    if total_w <= 0:
                        continue
                    zeta = m.var(("service_tail", service.id, w))
                    tail_terms[zeta] = world.weight / (1 - risk_level)
                    m.row({**{unmet[service.id, t, w]: 1 / total_w for t in range(H)}, eta: -1, zeta: -1}, upper=0)
                m.row(tail_terms, upper=1 - service.target)
            if per_world_service:
                for w, world in enumerate(worlds):
                    m.row({unmet[service.id, t, w]: 1 for t in range(H)},
                          upper=(1 - service.target) * sum(world.demand[service.id]))
    if continuation:
        for w in range(len(worlds)):
            slab_vars: dict[tuple[str, str, int], tuple[int, float]] = {}     # (sku, location, slab) -> (served var, demand units)
            for (sku, location), value in continuation.items():
                # one (units, margin) pair, or a list of slabs sharing the post-horizon supply (P1 final
                # closure: the steady-state relative value, concave in the residual); P0 passes neither
                slabs = value if isinstance(value, list) else [value]
                supply_terms = post[w].get((sku, location), {})
                served_vars = []
                served_slabs: list[tuple[int, int]] = []
                for j, (demand_units, margin) in enumerate(slabs):
                    if demand_units > 0 and margin > 0 and supply_terms:
                        served = m.var(("continuation", sku, location, w, j), upper=demand_units)
                        costs[w][served] -= margin
                        served_vars.append(served)
                        served_slabs.append((j, served))
                        slab_vars[sku, location, j] = (served, demand_units)
                if served_vars:
                    m.row({**{q: -coef for q, coef in supply_terms.items()}, **{s: 1. for s in served_vars}}, upper=0)
                    if physics is not None:
                        _cohort_slab_rows(m, physics, sku, H, served_slabs, supply_terms, post_expiry)
            # Network continuation (P2): an origin without customers of its own may earn a fed location's
            # slab margin less the lane cost, from the slab its lane lead can reach, sharing that
            # location's post-window demand with the location's own residual (one row per slab), and
            # bounded by the origin's own post-horizon supply. Absent feeds: nothing is added.
            for (sku, feed_origin), feeds in (continuation_feeds or {}).items():
                supply_terms = post[w].get((sku, feed_origin), {})
                if not supply_terms:
                    continue
                via_vars = []
                via_slabs: list[tuple[int, int]] = []
                shared: dict[tuple[str, str, int], list[int]] = defaultdict(list)
                for feed in feeds:
                    fed_entry = continuation.get((sku, feed["branch"]))
                    if not fed_entry:
                        continue
                    fed_slabs: list = list(fed_entry) if isinstance(fed_entry, list) else [fed_entry]
                    for j, (demand_units, margin) in enumerate(fed_slabs):
                        net = margin - feed["cost"]
                        if j < feed["lead"] or demand_units <= 0 or net <= 0:
                            continue
                        via = m.var(("continuation_via", sku, feed_origin, feed.get("lane", feed["branch"]), w, j), upper=demand_units)
                        costs[w][via] -= net
                        via_vars.append(via)
                        via_slabs.append((j, via))
                        shared[sku, feed["branch"], j].append(via)
                if via_vars:
                    m.row({**{q: -coef for q, coef in supply_terms.items()}, **{v: 1. for v in via_vars}}, upper=0)
                    if physics is not None:
                        _cohort_slab_rows(m, physics, sku, H, via_slabs, supply_terms, post_expiry)
                    for slab_key, vias in shared.items():
                        own = slab_vars.get(slab_key)
                        row = {v: 1. for v in vias}
                        if own is not None:
                            row[own[0]] = 1.
                            demand_units = own[1]
                        else:
                            entry = continuation[slab_key[0], slab_key[1]]
                            branch_slabs: list = list(entry) if isinstance(entry, list) else [entry]
                            demand_units = float(branch_slabs[slab_key[2]][0])
                        m.row(row, upper=demand_units)
    es_vars: dict[tuple[str, int], int] = {}
    for service, t, cuts in shortage_terms:
        # Availability for the service in period t on the single world: what it served plus what
        # its SKU still holds at the location at the end of the period. The epigraph variable is at
        # least the mean world's own unmet units, so the surrogate only ever adds the part of the
        # expected shortage the mean path cannot see.
        u = unmet[service.id, t, 0]
        held = stock_indices.get((service.sku, service.location, t, 0), [])
        d = worlds[0].demand[service.id][t]
        es = m.var(("expected_shortage", service.id, t))
        es_vars[service.id, t] = es
        m.row({es: 1., u: -1.}, lower=0.)
        for a_k, l_k, slope_k in cuts:
            # es >= l_k + slope_k * (d - u + sum(held) - a_k)
            row = {es: 1., u: slope_k}
            for i in held:
                row[i] = row.get(i, 0.) - slope_k
            m.row(row, lower=l_k + slope_k * (d - a_k))
        penalty = service.selling_price + service.sla_per_unmet
        surrogate[0][es] += penalty
        surrogate[0][u] -= penalty
    for w, world in enumerate(worlds):
        for q, amount in costs[w].items():
            m.cost[q] += world.weight * amount
        for q, amount in tiebreak[w].items():
            m.cost[q] += world.weight * amount
        for q, amount in surrogate[w].items():
            m.cost[q] += world.weight * amount
    if cvar_weight:
        threshold = m.var(("cvar_threshold",), cost=cvar_weight, lower=-np.inf)
        for w, world in enumerate(worlds):
            tail_var = m.var(("cvar_tail", w), cost=cvar_weight * world.weight / .1)
            row = dict(costs[w])
            row[threshold], row[tail_var] = -1, -1
            m.row(row, upper=0)
    if targets is not None:
        # Operational projection of a heuristic target into COMMON constraints.
        # It remains labelled a projected baseline, not an unconstrained strawman.
        assert nodes is None, "a projected base-stock target is a static plan; it is never solved on recourse nodes"
        penalty = 1000 * max(s.selling_price + s.sla_per_unmet for s in req.services)
        for target_key, quantity in targets.items():
            plus, minus = m.var(("target_above", *target_key), cost=penalty), m.var(("target_below", *target_key), cost=penalty)
            if len(target_key) == 3 and target_key[0] == "transfer":
                # Transfer target (echelon base stock): the period's total across expiry cohorts.
                _, arc_id, t_key = target_key
                terms_ = {q: 1. for (a_id, _, t_, _n), q in tr.items() if a_id == arc_id and t_ == t_key}
                if not terms_:
                    continue
                m.row({**terms_, plus: -1, minus: 1}, quantity, quantity)
                continue
            m.row({x[target_key[0], target_key[1], None]: 1, plus: -1, minus: 1}, quantity, quantity)
    objective = None
    if service_first:
        objective = np.zeros(len(m.names))
        for service in req.services:
            if service_first not in {"all", service.id}:
                continue
            for w, world in enumerate(worlds):
                for t in range(H):
                    objective[unmet[service.id, t, w]] = world.weight * customers[service.customer].priority
    budget = solve_budget(req)
    # Warm start (v8, P0-W2/W3). A known feasible plan - the incumbent - seeds the solver's search
    # on large models where HiGHS's own heuristics fail to find any incumbent inside the budget.
    # The seed is the plan's controls mapped by column name into THIS formulation and completed by
    # this formulation's own constraints; a plan that does not satisfy this candidate's floors or
    # packs is rejected here, never labelled feasible. The completion time counts against the
    # budget. The optimisation problem is unchanged; only the starting point is.
    warm: dict | None = None
    seed_x = None
    if (seed is not None and req.warm_start and seed.usable_plan
            and len(m.names) >= req.warm_start_min_variables):
        above = [(k, v, tight[k]) for k, v in seed.purchases.items() if k in tight and v > tight[k] + 1e-6]
        if above:
            # The seed buys more on a line than any undominated plan of this formulation can carry
            # (P3 performance closure): pinning it, equal or as a floor, is infeasible against the
            # activation bound, so it is rejected here with the reason instead of after two
            # completion solves. Nothing is labelled feasible that is not.
            seed_key, seed_value, seed_limit = above[0]
            warm = {"supplied": True, "source": seed.status, "controls_seeded": 0, "accepted": False,
                    "reason": f"seed value {seed_value:.6g} exceeds the activation bound {seed_limit:.6g} of {seed_key} (dominated plan)",
                    "mode": None, "completion_seconds": 0., "completion_status": "activation_bound", "attempts": []}
        else:
            warm, seed_x = warm_start_vector(m, seed, min(req.warm_start_completion_seconds, req.warm_start_completion_share * budget))
            budget = max(1., budget - warm["completion_seconds"])
    # Search settings (P3 performance closure): a model with activation binaries solves through
    # highspy with the order-class search settings; every other model keeps the frozen route.
    options = search_options(req)
    solver_name = "highspy" if (seed_x is not None or req.solver == "highspy" or (options is not None and req.solver == "highs")) else req.solver
    result, residual = m.solve(budget, objective, solver_name, mip_gap=req.solver_mip_gap, seed=seed_x, options=options)
    if warm is not None:
        warm.update(seed_status=getattr(result, "seed_status", None),
                    seed_objective=getattr(result, "seed_objective", None),
                    solver_accepted=bool(getattr(result, "seed_accepted", False)),
                    phase1_objective=result.fun, phase1_status=int(result.status))
    if objective is not None and result.status == 0 and result.x is not None:
        optimum = float(np.dot(objective, result.x))
        m.row({i: float(v) for i, v in enumerate(objective) if v}, upper=optimum + 1e-7)
        remaining = budget - (time.monotonic() - started)
        if remaining > 0:
            # the phase-one optimum satisfies the new row exactly, so it seeds phase two
            result, residual = m.solve(remaining, solver=solver_name, mip_gap=req.solver_mip_gap,
                                       seed=(result.x if solver_name == "highspy" else None), options=options)
    # Solve states (v8). scipy's milp reports status 1 for "iteration or time limit reached", and in
    # that case `result.x` frequently holds a genuine feasible incumbent. V7 threw that away and
    # returned an empty plan, so on long cells whole candidate classes silently vanished from the
    # selector's choice set - 79 candidate slots on one 30-review cell. A feasible-but-unproved plan
    # is now returned as FEASIBLE_TIME_LIMIT, with its bound and gap, for the caller to validate
    # physically and weigh according to its solve quality. It is never called OPTIMAL.
    elapsed = time.monotonic() - started
    gap = getattr(result, "mip_gap", None)
    bound = getattr(result, "mip_dual_bound", None)
    nodes_count = getattr(result, "mip_node_count", None)
    physically_usable = result.x is not None and residual <= 1e-5
    if warm is not None:
        seed_objective = warm.get("seed_objective")
        final = result.fun
        if not warm["accepted"]:
            outcome = "rejected"
        elif result.x is None:
            outcome = "no_incumbent_despite_seed"
        elif not physically_usable:
            outcome = "final_invalid"
        elif seed_objective is not None and final is not None and objective is None and final < seed_objective - 1e-6 * max(1., abs(seed_objective)):
            outcome = "improved"
        elif objective is not None:
            outcome = "improved" if warm.get("solver_accepted") else "retained_or_replaced"
        else:
            outcome = "retained"
        warm.update(outcome=outcome, final_objective=final, model_variables=len(m.names), solve_seconds=time.monotonic() - started,
                    highs_integrality_violation=getattr(result, "max_integrality_violation", None),
                    highs_primal_infeasibility=getattr(result, "max_primal_infeasibility", None))
        warm.pop("x", None)
    if result.status == 0 and physically_usable:
        state = "OPTIMAL"
    elif result.status == 1 and physically_usable:
        state = "FEASIBLE_TIME_LIMIT"
    elif result.status == 2:
        state = "INFEASIBLE"
    elif result.status == 1:
        state = "NO_FEASIBLE_SOLUTION"
    else:
        state = "ERROR"
    if not physically_usable:
        return Solution(state, {}, {}, {}, {}, None, [], elapsed,
                        len(m.names), len(m.rows), gap, residual if math.isfinite(residual) else None, [str(result.message)],
                        best_bound=bound, nodes=nodes_count, warm_start=warm)
    values = result.x
    service_result = {}
    for service in req.services:
        total = sum(world.weight * sum(world.demand[service.id]) for world in worlds)
        loss = sum(world.weight * values[unmet[service.id, t, w]] for w, world in enumerate(worlds) for t in range(H))
        service_result[service.id] = 1 - loss / total if total else 1.
    economic = constant + sum(world.weight * sum(values[q] * v for q, v in costs[w].items()) for w, world in enumerate(worlds))
    pack_of = {source.id: source_pack(source) for source in req.sources}
    po_pack = {order.id: pack_of[order.source] for order in req.pipeline}
    telemetry = None
    if shortage_terms:
        es_units = {(service.id, t): float(values[es_vars[service.id, t]]) for service, t, _ in shortage_terms}
        mean_unmet = {(service.id, t): float(values[unmet[service.id, t, 0]]) for service, t, _ in shortage_terms}
        telemetry = {"expected_shortage_units": sum(es_units.values()), "mean_world_unmet_units": sum(mean_unmet.values()),
                     "surrogate_cost": sum((es_units[k] - mean_unmet[k]) * (next(s_ for s_ in req.services if s_.id == k[0]).selling_price + next(s_ for s_ in req.services if s_.id == k[0]).sla_per_unmet) for k in es_units),
                     "scope": "planning objective of the mean-world candidate only; not in the ledger or the projected cost"}
    # P4: here-and-now columns make the plan; recourse columns make the policy (per node), read by
    # `zaad.recourse.policy.world_plan` for each world's own path.
    recourse_block: dict | None = None
    if nodes is not None:
        node_plans: dict[str, dict[str, dict]] = {}
        for (sid, t, node), q in x.items():
            if node is not None and not is_dust(values[q], pack_of[sid]):
                node_plans.setdefault(node, {"purchases": {}, "transfers": {}})["purchases"][sid, t] = float(max(0, values[q]))
        for (arc_id, expiry, t, node), q in tr.items():
            if node is not None and not is_dust(values[q]):
                node_plans.setdefault(node, {"purchases": {}, "transfers": {}})["transfers"][arc_id, expiry, t] = float(max(0, values[q]))
        recourse_block = {"nodes": node_plans, "perfect": nodes.perfect}
    return Solution(state, {k[:2]: float(max(0, values[q])) for k, q in x.items() if k[2] is None and not is_dust(values[q], pack_of[k[0]])},
                    {k[:3]: float(max(0, values[q])) for k, q in tr.items() if k[3] is None and not is_dust(values[q])},
                    {k: float(max(0, values[q])) for k, q in po.items() if not is_dust(values[q], po_pack[k[0]])},
                    service_result, float(economic),
                    [{"period": t, "scenario": w, "cash": float(values[cash[t, w]]), "debt": float(values[debt[t, w]])} for w in range(len(worlds)) for t in range(H)],
                    elapsed, len(m.names), len(m.rows), gap, residual,
                    ([] if state == "OPTIMAL" else [f"{state}: feasible plan returned without a proof of optimality"]),
                    best_bound=bound, nodes=nodes_count, warm_start=warm, planning_surrogate=telemetry, recourse=recourse_block,
                    binaries=int(sum(m.integer)))
