"""P5 entry point (isolated): build the supply state, evaluate the operator's incumbent policy and
the exact allocation on it, price both on the shared ledger, apply the request's materiality
standard, and produce the operator report. Never called by the planner during the parallel phase.
"""
from __future__ import annotations

from typing import Any

from zaad.atp.allocation import FLOOR_INFEASIBLE, apply_fairness, channels, solve
from zaad.atp.contracts import Atp, resolve
from zaad.atp.economics import price
from zaad.atp.explain import report
from zaad.atp.policies import incumbent
from zaad.atp.state import build_state
from zaad.atp.validation import check_state

NO_IMPROVEMENT = "NO MATERIAL ALLOCATION IMPROVEMENT AVAILABLE"
SELECTED = "ALLOCATION CHANGE RECOMMENDED"
NO_RECOMMENDATION = "NO RECOMMENDATION (declared rules infeasible on the available supply)"
TOL = 1e-6


def promise(req, seconds: float = 30.) -> dict[str, Any] | None:
    """The P5 report for a request with an enabled `atp` block; None for a frozen request."""
    atp = resolve(req)
    if atp is None:
        return None
    return promise_with(req, atp, seconds)


def promise_with(req, atp: Atp, seconds: float = 30.) -> dict[str, Any]:
    state = build_state(req, atp)
    check_state(req, atp, state)
    _chans, drv, _meta = channels(req, atp, state)
    base = incumbent(req, atp, state)
    priced_base = price(base, req, atp, state)
    optimised = solve(req, atp, state, seconds=seconds)
    if optimised.status in (FLOOR_INFEASIBLE, "INFEASIBLE", "ERROR"):
        priced_opt = {"ledger": {k: None for k in priced_base["ledger"]}, "total": None, "units": {}, "gross_lost_sales_opportunity": None}
        return report(req, atp, state, optimised, base, priced_opt, priced_base, drv, NO_RECOMMENDATION, None, False, base)
    priced_opt = price(optimised, req, atp, state)
    value = priced_base["total"] - priced_opt["total"]
    material = value > atp.materiality_cost_fraction * abs(priced_base["total"]) + TOL
    if not material:
        recommended = apply_fairness(base, req, atp, state)
        return report(req, atp, state, optimised, base, priced_opt, price(recommended, req, atp, state), drv, NO_IMPROVEMENT, value, False, recommended)
    recommended = apply_fairness(optimised, req, atp, state)
    return report(req, atp, state, optimised, base, price(recommended, req, atp, state), priced_base, drv, SELECTED, value, True, recommended)
