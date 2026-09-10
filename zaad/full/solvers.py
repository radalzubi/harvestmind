"""Optional Pyomo solver adapters; missing binaries/licenses fail closed."""
import math

import numpy as np
from scipy.optimize import OptimizeResult


def pyomo_solve(linear, seconds, objective, backend):
    import pyomo.environ as pyo
    from pyomo.opt import TerminationCondition

    if backend not in {"cbc", "glpk", "gurobi", "cplex"}:
        raise ValueError("solver backend not allowlisted")
    solver = pyo.SolverFactory(backend)
    if not solver.available(exception_flag=False):
        return OptimizeResult(status=4, x=None, message=f"SOLVER_UNAVAILABLE: {backend}")
    model = pyo.ConcreteModel()
    model.idx = pyo.RangeSet(0, len(linear.names) - 1)
    def bounds(_model, i):
        return (linear.lower[i] if math.isfinite(linear.lower[i]) else None,
                linear.upper[i] if math.isfinite(linear.upper[i]) else None)
    model.x = pyo.Var(model.idx, bounds=bounds)
    for i, integer in enumerate(linear.integer):
        model.x[i].domain = pyo.Integers if integer else pyo.Reals
    model.constraints = pyo.ConstraintList()
    for coefficients, lo, hi in zip(linear.rows, linear.lo, linear.hi):
        if not coefficients:
            if lo > 0 or hi < 0:
                return OptimizeResult(status=2, x=None, message="infeasible empty row")
            continue
        expr = sum(v * model.x[i] for i, v in coefficients.items())
        if math.isfinite(lo):
            model.constraints.add(expr >= lo)
        if math.isfinite(hi):
            model.constraints.add(expr <= hi)
    coefficients = linear.cost if objective is None else objective
    model.objective = pyo.Objective(expr=sum(v * model.x[i] for i, v in enumerate(coefficients)))
    key = {"cbc": "seconds", "glpk": "tmlim", "gurobi": "TimeLimit", "cplex": "timelimit"}[backend]
    solver.options[key] = max(1, int(seconds))
    result = solver.solve(model, load_solutions=False)
    termination = result.solver.termination_condition
    if termination != TerminationCondition.optimal:
        status = 2 if termination == TerminationCondition.infeasible else 1
        return OptimizeResult(status=status, x=None, message=str(termination))
    model.solutions.load_from(result)
    return OptimizeResult(status=0, x=np.asarray([pyo.value(model.x[i]) for i in model.idx]),
                          message="optimal", mip_gap=0.)
