"""Adaptive policy (P4): the world-specific plan a recourse solution prescribes, the static /
adaptive / perfect-information comparison and the structural non-anticipativity check.

A recourse `Solution` carries the here-and-now columns in `purchases` / `transfers` and one plan per
information-set node in `recourse["nodes"]`. For a world the policy is: at every period at or after
a review epoch, the node that world's observable history selects. Worlds of the solve are mapped by
membership; any other world (a confirmation world) by signature lookup (`information.lookup`).
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from zaad.full.model import Solution, solve
from zaad.recourse.contracts import Recourse
from zaad.recourse.information import NodeMap, lookup, node_map

TOLERANCE = 1e-6


def world_plan(solution: Solution, req, recourse: Recourse, nodes: NodeMap, world, index: int | None = None) -> Solution:
    """The static plan world `world` receives under the adaptive policy: here-and-now columns plus,
    per period, the purchases and transfers of the node the world reads at that period."""
    block = solution.recourse
    if block is None or nodes is None:
        return solution
    if index is not None:
        chosen = {e: next(s.id for s in nodes.sets[e] if index in s.members) for e in recourse.epochs}
    else:
        chosen = {e: nid for e, (nid, _exact) in lookup(req, recourse, nodes.sets, world).items()}
    purchases: dict[Any, float] = dict(solution.purchases)
    transfers: dict[Any, float] = dict(solution.transfers)
    for e, nid in chosen.items():
        plan: dict[str, dict[Any, float]] = block["nodes"].get(nid, {"purchases": {}, "transfers": {}})
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
    """For worlds outside the solve: per world and epoch, whether the policy lookup was exact."""
    rows = []
    for world in worlds:
        hit = lookup(req, recourse, nodes.sets, world)
        rows.append({"world": world.name, **{f"epoch_{e}": {"node": nid, "exact": exact} for e, (nid, exact) in hit.items()}})
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


def compare(req, worlds: list, recourse: Recourse, *, perfect: bool | None = None, **kw) -> dict[str, Any]:
    """Static, adaptive and (optionally) perfect-information solves of the same request on the same
    worlds with the same kwargs, and the ordering check PI <= adaptive <= static."""
    static = solve(req, worlds, **kw)
    nodes = node_map(req, recourse, worlds)
    adaptive = solve(req, worlds, nodes=nodes, **kw)
    want_pi = recourse.spec.perfect_information if perfect is None else perfect
    pi = solve(req, worlds, nodes=node_map(req, recourse, worlds, perfect=True), **kw) if want_pi else None
    out: dict[str, Any] = {"static": static, "adaptive": adaptive, "perfect": pi, "nodes": nodes,
                           "static_cost": static.projected_cost, "adaptive_cost": adaptive.projected_cost,
                           "perfect_cost": pi.projected_cost if pi is not None else None,
                           "value_of_adaptation": None, "ordering_ok": None, "non_anticipativity": None,
                           "static_infeasible": not static.usable_plan, "time_limited": [k for k, v in (("static", static), ("adaptive", adaptive), ("perfect", pi)) if v is not None and v.status == "FEASIBLE_TIME_LIMIT"]}
    if adaptive.usable_plan and nodes is not None:
        out["non_anticipativity"] = non_anticipativity(adaptive, nodes, req)
    if static.usable_plan and adaptive.usable_plan and static.projected_cost is not None and adaptive.projected_cost is not None:
        out["value_of_adaptation"] = static.projected_cost - adaptive.projected_cost
        scale = max(1., abs(static.projected_cost))
        gap = float(req.solver_mip_gap) * scale + TOLERANCE
        ok = adaptive.projected_cost <= static.projected_cost + gap
        if pi is not None and pi.usable_plan and pi.projected_cost is not None:
            ok = ok and pi.projected_cost <= adaptive.projected_cost + gap
        out["ordering_ok"] = ok
    return out
