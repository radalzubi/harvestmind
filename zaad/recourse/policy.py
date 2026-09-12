"""Adaptive policy (P4): the world-specific plan a recourse solution prescribes, the static /
adaptive / perfect-information comparison and the structural non-anticipativity check.

A recourse `Solution` carries the here-and-now columns in `purchases` / `transfers` and one plan per
information-set node in `recourse["nodes"]`. For a world the policy is: at every period at or after
a review epoch, the node that world's observable history selects. Worlds of the solve are mapped by
membership; any other world (a confirmation world, a live observation) by exact signature lookup
(`information.lookup`). Release rules (P4 release audit):

* Blocker B - no nearest-signature routing. An observation outside the modelled branches selects no
  branch action: the world receives the declared fallback for that review window, the static
  commitments attached to the solution (`recourse["fallback"]`), and the lookup is reported as
  REPLAN_REQUIRED. Settlement therefore evaluates exactly the policy the operator may execute.
* Blocker A - the perfect-information diagnostic is a bound only when its solve is proven OPTIMAL.
  A feasible time-limited perfect-information incumbent is reported as a feasible cost, never as a
  lower bound, and never enters the ordering check; the solver's own dual bound is kept apart from
  the executable primal cost and is never represented as a policy cost.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from zaad.full.model import Solution, solve
from zaad.recourse.contracts import Recourse
from zaad.recourse.information import NodeMap, lookup, node_map

TOLERANCE = 1e-6
REPLAN_REQUIRED = "REPLAN_REQUIRED"
CERTIFIED, NON_CERTIFIED, UNAVAILABLE = "CERTIFIED", "NON_CERTIFIED", "UNAVAILABLE"


def attach_fallback(adaptive: Solution, static: Solution | None) -> Solution:
    """Attach the declared fallback (the static comparator's commitments) to an adaptive solution so
    that a world outside the modelled branches receives an evaluated plan instead of a nearest node."""
    if adaptive.recourse is None:
        return adaptive
    if static is not None and static.usable_plan:
        fallback = {"purchases": dict(static.purchases), "transfers": dict(static.transfers), "available": True}
    else:
        fallback = {"purchases": {}, "transfers": {}, "available": False}
    return replace(adaptive, recourse={**adaptive.recourse, "fallback": fallback})


def resolve_nodes(solution: Solution, req, recourse: Recourse, nodes: NodeMap, world, index: int | None = None) -> dict[int, tuple[str | None, bool]]:
    """Per epoch, the node a world reads and whether the match is exact (membership for a world of
    the solve; exact signature lookup otherwise; `(None, False)` = outside the modelled branches)."""
    if index is not None:
        return {e: (next(s.id for s in nodes.sets[e] if index in s.members), True) for e in recourse.epochs}
    return lookup(req, recourse, nodes.sets, world)


def world_plan(solution: Solution, req, recourse: Recourse, nodes: NodeMap, world, index: int | None = None) -> Solution:
    """The static plan world `world` receives under the adaptive policy: here-and-now columns plus,
    per period, the purchases and transfers of the node the world reads at that period. For a review
    epoch whose observation matches no modelled branch the window receives the attached fallback
    (the static commitments) - never a nearest branch."""
    block = solution.recourse
    if block is None or nodes is None:
        return solution
    chosen = resolve_nodes(solution, req, recourse, nodes, world, index)
    fallback = block.get("fallback") or {"purchases": {}, "transfers": {}, "available": False}
    purchases: dict[Any, float] = dict(solution.purchases)
    transfers: dict[Any, float] = dict(solution.transfers)
    for e, (nid, _exact) in chosen.items():
        plan: dict[str, dict[Any, float]] = (block["nodes"].get(nid, {"purchases": {}, "transfers": {}}) if nid is not None else fallback)
        if nodes.adapts("purchase"):
            for pkey, q in plan["purchases"].items():
                if recourse.epoch_for(pkey[1]) == e:
                    purchases[pkey] = q
        if nodes.adapts("transfer"):
            for tkey, q in plan["transfers"].items():
                if recourse.epoch_for(tkey[2]) == e:
                    transfers[tkey] = q
    return replace(solution, purchases=purchases, transfers=transfers, recourse=None)


def lookup_exactness(req, recourse: Recourse, nodes: NodeMap, worlds: list) -> list[dict[str, Any]]:
    """For worlds outside the solve: per world and epoch, the branch matched exactly or REPLAN_REQUIRED."""
    rows = []
    for world in worlds:
        hit = lookup(req, recourse, nodes.sets, world)
        rows.append({"world": world.name, "replan_required": any(not exact for _nid, exact in hit.values()),
                     **{f"epoch_{e}": {"node": nid, "exact": exact, "rule": None if exact else REPLAN_REQUIRED} for e, (nid, exact) in hit.items()}})
    return rows


def non_anticipativity(solution: Solution, nodes: NodeMap, req) -> dict[str, Any]:
    """Structural check on a solved adaptive plan: worlds sharing a node at an epoch read one column,
    so their plans for that epoch's periods are identical; and no world's plan for a period before
    the first epoch differs from the here-and-now plan. Returns the evidence."""
    recourse = nodes.recourse
    assert recourse is not None
    violations: list[str] = []
    checked = 0
    for e, sets in nodes.sets.items():
        for info in sets:
            plans = [world_plan(solution, req, recourse, nodes, None, index=w) for w in info.members]
            for a in plans[1:]:
                checked += 1
                for t in range(req.horizon):
                    if recourse.epoch_for(t) != e:
                        continue
                    for pkey, q in plans[0].purchases.items():
                        if pkey[1] == t and abs(a.purchases.get(pkey, 0.) - q) > TOLERANCE:
                            violations.append(f"epoch {e} set {info.id}: purchase {pkey} differs across members")
                    for tkey, q2 in plans[0].transfers.items():
                        if tkey[2] == t and abs(a.transfers.get(tkey, 0.) - q2) > TOLERANCE:
                            violations.append(f"epoch {e} set {info.id}: transfer {tkey} differs across members")
    first = recourse.first_epoch
    for w in range(nodes.world_count):
        plan = world_plan(solution, req, recourse, nodes, None, index=w)
        for (sid, t), q in plan.purchases.items():
            if first is not None and t < first and abs(q - solution.purchases.get((sid, t), 0.)) > TOLERANCE:
                violations.append(f"world {w}: here-and-now purchase {(sid, t)} differs from the committed plan")
    return {"pass": not violations, "violations": violations, "pairs_checked": checked,
            "sets_per_epoch": {e: len(s) for e, s in nodes.sets.items()}}


def assess(req, static: Solution, adaptive: Solution, perfect: Solution | None) -> dict[str, Any]:
    """Comparator semantics shared by `compare` and the planner.

    value_of_adaptation = static - adaptive expected cost on the same worlds (None unless both plans
    are usable). Ordering: adaptive <= static within the solver tolerance, and perfect <= adaptive
    only when the perfect-information solve is CERTIFIED (status OPTIMAL). A NON_CERTIFIED
    (feasible time-limited) perfect-information incumbent is reported as `perfect_feasible_cost`
    and never as a bound; the solver's dual bound, when HiGHS returned one, is reported apart as
    `perfect_solver_bound` in solver-objective units (the ledger cost plus objective-only terms), so
    it is not comparable with the projected costs and is never a policy cost."""
    status = {"static": static.status, "adaptive": adaptive.status, "perfect": perfect.status if perfect is not None else None}
    if perfect is None or not perfect.usable_plan or perfect.projected_cost is None:
        perfect_status = UNAVAILABLE
    elif perfect.status == "OPTIMAL":
        perfect_status = CERTIFIED
    else:
        perfect_status = NON_CERTIFIED
    out: dict[str, Any] = {
        "static_cost": static.projected_cost, "adaptive_cost": adaptive.projected_cost,
        "perfect_status": perfect_status,
        "perfect_cost": perfect.projected_cost if (perfect is not None and perfect_status == CERTIFIED) else None,
        "perfect_feasible_cost": perfect.projected_cost if (perfect is not None and perfect_status == NON_CERTIFIED) else None,
        "perfect_solver_bound": perfect.best_bound if perfect is not None else None,
        "value_of_adaptation": None, "ordering_ok": None,
        "value_certified": static.status == "OPTIMAL" and adaptive.status == "OPTIMAL",
        "solve_status": status, "static_infeasible": not static.usable_plan,
        "time_limited": [k for k, v in (("static", static), ("adaptive", adaptive), ("perfect", perfect)) if v is not None and v.status == "FEASIBLE_TIME_LIMIT"]}
    if static.usable_plan and adaptive.usable_plan and static.projected_cost is not None and adaptive.projected_cost is not None:
        out["value_of_adaptation"] = static.projected_cost - adaptive.projected_cost
        scale = max(1., abs(static.projected_cost))
        gap = float(req.solver_mip_gap) * scale + TOLERANCE
        ok = adaptive.projected_cost <= static.projected_cost + gap
        if perfect_status == CERTIFIED and perfect is not None and perfect.projected_cost is not None:
            ok = ok and perfect.projected_cost <= adaptive.projected_cost + gap
        out["ordering_ok"] = ok
    return out


def compare(req, worlds: list, recourse: Recourse, *, perfect: bool | None = None, **kw) -> dict[str, Any]:
    """Static, adaptive and (optionally) perfect-information solves of the same request on the same
    worlds with the same kwargs, the ordering check (see `assess`) and the fallback attachment."""
    static = solve(req, worlds, **kw)
    nodes = node_map(req, recourse, worlds)
    adaptive = attach_fallback(solve(req, worlds, nodes=nodes, **kw), static)
    want_pi = recourse.spec.perfect_information if perfect is None else perfect
    pi = solve(req, worlds, nodes=node_map(req, recourse, worlds, perfect=True), **kw) if want_pi else None
    out: dict[str, Any] = {"static": static, "adaptive": adaptive, "perfect": pi, "nodes": nodes, "non_anticipativity": None,
                           **assess(req, static, adaptive, pi)}
    if adaptive.usable_plan and nodes is not None:
        out["non_anticipativity"] = non_anticipativity(adaptive, nodes, req)
    return out
