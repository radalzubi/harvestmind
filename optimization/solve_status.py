"""One place that talks to the solver, so failure looks the same everywhere.

The solver is an external dependency that can say no. Before this module
both optimizers called ``opt.solve(m)`` directly, which on an infeasible
model raises ``RuntimeError`` out of pyomo's appsi wrapper rather than
returning a status, and on a time limit returned whatever it had with the
same shape as an optimal answer. A recommendation produced from a model
that could not be solved is not a recommendation, and a caller must be
able to tell the two apart without parsing an exception message.

Status vocabulary, deliberately small:
  optimal      proven optimal (LP) or within mip_rel_gap (MILP)
  feasible     a solution exists but optimality was not proven (time limit)
  infeasible   no solution satisfies the constraints
  unbounded    the objective can decrease without limit; a modelling bug
  timeout      time limit reached with NO feasible solution
  error        the solver raised or returned something unrecognised

``usable`` is True only for optimal and feasible, and feasible carries a
warning so it is never mistaken for proven.
"""

from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass, field


@dataclass
class SolveOutcome:
    status: str
    usable: bool
    runtime_s: float
    objective: float | None = None
    bound: float | None = None
    gap: float | None = None
    warnings: list = field(default_factory=list)
    raw_condition: str = ""


def _has_integers(model) -> bool:
    import pyomo.environ as pyo
    for v in model.component_data_objects(pyo.Var, active=True):
        if v.is_integer() or v.is_binary():
            return True
    return False


def _gap(obj: float | None, bound: float | None) -> float | None:
    if obj is None or bound is None:
        return None
    if not (math.isfinite(obj) and math.isfinite(bound)):
        return None
    denom = max(abs(obj), 1e-9)
    return abs(obj - bound) / denom


def run_solver(model, solver: str = "highs", time_limit_s: float = 300.0,
               mip_rel_gap: float | None = None) -> SolveOutcome:
    """Solve a pyomo model and classify the result.

    Solutions are loaded into the model only when the solver reports one.
    The objective value is read back from the model afterwards by the
    caller, because a MILP objective is only meaningful once variables are
    loaded.
    """
    import pyomo.environ as pyo
    from pyomo.opt import SolverFactory, TerminationCondition as TC

    name = "appsi_highs" if solver == "highs" else solver
    opt = SolverFactory(name)
    options: dict = {"time_limit": float(time_limit_s)}
    threads = os.environ.get("HARVESTMIND_SOLVER_THREADS")
    if threads:
        # Several validation workers on one machine: one HiGHS thread each
        # avoids oversubscription, which slowed solves by two orders of
        # magnitude when three processes shared the cores.
        options["threads"] = int(threads)
    if mip_rel_gap is not None:
        options["mip_rel_gap"] = float(mip_rel_gap)
    t0 = time.perf_counter()
    warnings: list = []
    try:
        res = opt.solve(model, tee=False, load_solutions=False, options=options)
    except Exception as exc:  # noqa: BLE001 — the point is to classify, not to crash
        return SolveOutcome(status="error", usable=False,
                            runtime_s=time.perf_counter() - t0,
                            warnings=[f"solver raised {type(exc).__name__}: {exc}"],
                            raw_condition="exception")
    tc = res.solver.termination_condition
    runtime = time.perf_counter() - t0
    raw = str(tc)

    if tc in (TC.optimal, TC.locallyOptimal, TC.globallyOptimal):
        status, usable = "optimal", True
    elif tc in (TC.feasible, TC.maxTimeLimit, TC.maxIterations, TC.maxEvaluations):
        status, usable = "feasible", True
        warnings.append(f"optimality not proven ({raw}); treat as a lower bound "
                        "on what a longer solve could find")
    elif tc in (TC.infeasible, TC.infeasibleOrUnbounded):
        status, usable = "infeasible", False
    elif tc == TC.unbounded:
        status, usable = "unbounded", False
        warnings.append("unbounded objective: a cost term is missing or has the "
                        "wrong sign")
    else:
        status, usable = "error", False
        warnings.append(f"unrecognised termination condition {raw}")

    obj = bound = None
    if usable:
        try:
            wants_duals = hasattr(model, "dual") and not _has_integers(model)
            if wants_duals:
                # An LP that declared a dual Suffix (shadow prices) needs the
                # full solution load. Feasibility is already established, so
                # this second solve cannot raise for infeasibility and costs
                # one cheap LP.
                opt.solve(model, tee=False, load_solutions=True, options=options)
            elif hasattr(opt, "load_vars"):
                opt.load_vars()
            else:
                model.solutions.load_from(res)
        except Exception as exc:  # noqa: BLE001
            return SolveOutcome(status="error", usable=False, runtime_s=runtime,
                                warnings=[f"solution load failed: {exc}"],
                                raw_condition=raw)
        try:
            obj = float(pyo.value(next(iter(model.component_objects(pyo.Objective, active=True)))))
        except Exception:  # noqa: BLE001
            obj = None
        prob = getattr(res, "problem", None)
        for attr in ("lower_bound", "upper_bound"):
            v = getattr(prob, attr, None) if prob is not None else None
            try:
                if v is not None and math.isfinite(float(v)):
                    bound = float(v) if bound is None else bound
            except (TypeError, ValueError):
                pass
        if status == "feasible" and bound is None:
            bound = None
    return SolveOutcome(status=status, usable=usable, runtime_s=runtime,
                        objective=obj, bound=bound, gap=_gap(obj, bound),
                        warnings=warnings, raw_condition=raw)
