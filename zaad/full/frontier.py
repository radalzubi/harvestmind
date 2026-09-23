"""Per-service frontier oracle on the exact connected components of the built model (frontier
decomposition pass, `docs/zaad_full/FRONTIER_ORACLE_DECOMPOSITION.md`).

The oracle answers, for every service i, one question on the mean world: the least unmet demand of
service i that any feasible plan can leave when nothing else is asked of the plan (`min p_i Σ_t u_i,t`
over the released feasible set). The released oracle rebuilt and solved the whole model once per
service. Here the model is built once, its constraint matrix is partitioned into its connected
components (columns joined by the rows they share), and each service's minimum is solved on the
component that holds its unmet columns: the same rows, bounds, integrality and objective coefficients,
so the same MIP restricted to the only columns the objective and its constraints can reach.

Exactness: every row of the built model lies inside one component and every bound is one column's, so
the feasible set is the cartesian product of the components' feasible sets and the minimum of an
objective supported on one component is that component's minimum (provided every other component is
non-empty, which the oracle checks - §3 of the record). The components are computed from the matrix
the builder produced, never assumed from the data: a declared shared supplier order, capacity resource,
location volume, cash balance, substitution, lane or PO merges the products it couples into one
component, and that component is solved whole.

Exact skips: a physically usable solution of a restriction of the oracle model on the same world (the
incumbent's fixed projection, the base-stock proxy, a deterministic candidate) that serves service i
in full attains the trivial lower bound of the minimisation, so its frontier is 1 with no solve; the
same point proves every component feasible. Without such a witness, service-less components are
solved once for feasibility so a proven-infeasible model reports None for every service, as the
released oracle does. Nothing else is skipped and no value is approximated.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Any

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


@dataclass
class Partition:
    """Connected components of a built model: a label per column and per row, and the rows with
    no column at all (their bounds are checked directly: an empty row that excludes zero makes the
    whole model infeasible)."""
    column_label: np.ndarray
    row_label: np.ndarray
    count: int
    empty_rows: list[int]


def partition(rows: list[dict], ncols: int) -> Partition:
    """Connected components of the column graph (two columns adjacent when a row holds both), via
    the bipartite column-row graph: O(non-zeros)."""
    rr, cc = [], []
    empty: list[int] = []
    for r, terms in enumerate(rows):
        cols = [c for c, v in terms.items() if v]
        if not cols:
            empty.append(r)
            continue
        rr.extend([r] * len(cols))
        cc.extend(cols)
    nrows = len(rows)
    if rr:
        adjacency = coo_matrix((np.ones(len(rr)), (np.asarray(cc), ncols + np.asarray(rr))), shape=(ncols + nrows, ncols + nrows))
        _, labels = connected_components(adjacency, directed=False)
    else:
        labels = np.arange(ncols + nrows)
    column_label = labels[:ncols]
    row_label = labels[ncols:]
    # compact the labels of the columns' components (a row's label is always one of them)
    unique, column_label = np.unique(column_label, return_inverse=True)
    lookup = {int(u): k for k, u in enumerate(unique)}
    row_label = np.asarray([lookup.get(int(x), -1) for x in row_label], dtype=int)
    return Partition(column_label=np.asarray(column_label, dtype=int), row_label=row_label, count=len(unique), empty_rows=empty)


def extract(m, part: Partition, component: int):
    """The sub-model of one component: its columns (bounds, integrality, names) and its rows,
    re-indexed - the released rows verbatim. Returns (Linear, column map old -> new)."""
    from zaad.full.model import Linear
    cols = np.flatnonzero(part.column_label == component)
    col_map = {int(old): new for new, old in enumerate(cols)}
    sub = Linear()
    sub.names = [m.names[i] for i in cols]
    sub.cost = [0.] * len(cols)
    sub.lower = [m.lower[i] for i in cols]
    sub.upper = [m.upper[i] for i in cols]
    sub.integer = [m.integer[i] for i in cols]
    for r in np.flatnonzero(part.row_label == component):
        sub.rows.append({col_map[c]: v for c, v in m.rows[r].items() if v})
        sub.lo.append(m.lo[r])
        sub.hi.append(m.hi[r])
    return sub, col_map


def _state(result, residual: float) -> str:
    usable = result.x is not None and residual <= 1e-5
    if result.status == 0 and usable:
        return "OPTIMAL"
    if result.status == 1 and usable:
        return "FEASIBLE_TIME_LIMIT"
    if result.status == 2:
        return "INFEASIBLE"
    if result.status == 1:
        return "NO_FEASIBLE_SOLUTION"
    return "ERROR"


def frontier_solve(m, unmet: dict, worlds, req, services: tuple[str, ...], budget: float, solver_name: str,
                   options: dict | None, proven: frozenset[str], feasible_witness: bool, started: float) -> tuple[dict[str, float], str, dict]:
    """Solve every requested service's frontier on its own component of the built model `m`.

    Returns (projected service per service with a usable value, the oracle status, telemetry). `proven`
    holds the services a witness already serves in full (frontier 1 exactly, no solve); `feasible_witness`
    says a feasible point of the whole model is known (no feasibility solves of service-less components).
    """
    customers = {c.id: c for c in req.customers}
    services_by_id = {s.id: s for s in req.services}
    H = req.horizon
    t_build = time.monotonic()
    part = partition(m.rows, len(m.names))
    # every unmet column of a service lies in one component (its balance rows join the periods'
    # allocations and stock; disjoint periods can still be separate components in principle, so the
    # objective's columns are collected per component and solved where they are)
    service_components: dict[str, set[int]] = {}
    for service_id in services:
        service_components[service_id] = {int(part.column_label[unmet[service_id, t, w]]) for w in range(len(worlds)) for t in range(H)}
    telemetry: dict[str, Any] = {"components": int(part.count), "component_sizes": {}, "empty_rows": len(part.empty_rows),
                                 "solves": [], "skipped_proven": sorted(s for s in services if s in proven),
                                 "feasibility_solves": 0, "partition_seconds": 0., "extract_seconds": 0., "solve_seconds": 0.}
    sizes = np.bincount(part.column_label, minlength=part.count)
    rows_of = np.bincount(part.row_label[part.row_label >= 0], minlength=part.count) if len(part.row_label) else np.zeros(part.count, dtype=int)
    telemetry["component_sizes"] = {int(k): int(v) for k, v in enumerate(sizes)}
    telemetry["largest_component_columns"] = int(sizes.max()) if part.count else 0
    # components holding a service (the ones the oracle solves) and row-less singletons (a column no row
    # reaches, e.g. a last-period purchase landing after the horizon: feasible iff its bounds are)
    telemetry["service_components"] = len(set().union(*service_components.values())) if service_components else 0
    telemetry["rowless_components"] = int(sum(1 for k in range(part.count) if rows_of[k] == 0))
    telemetry["partition_seconds"] = round(time.monotonic() - t_build, 3)
    # an empty row whose bounds exclude zero: the whole model is infeasible, exactly as the monolithic oracle reports
    for r in part.empty_rows:
        if m.lo[r] > 1e-9 or m.hi[r] < -1e-9:
            telemetry["infeasible_component"] = "empty_row"
            return {}, "INFEASIBLE", telemetry
    values: dict[str, float] = {service_id: 1. for service_id in services if service_id in proven}
    # which components must be solved: every component holding an unproven service, plus (without a
    # feasibility witness) every other component once, for feasibility
    needed: dict[int, list[str]] = {}
    for service_id in services:
        if service_id in proven:
            continue
        for label in service_components[service_id]:
            needed.setdefault(label, []).append(service_id)
    if not feasible_witness:
        for label in range(part.count):
            if label in needed:
                continue
            # a service-less component: feasible by inspection when the point at every column's bound
            # nearest zero satisfies its rows (an exact certificate: a feasible point exhibited); solved
            # for feasibility otherwise
            cols = np.flatnonzero(part.column_label == label)
            if any(m.lower[i] > m.upper[i] + 1e-9 for i in cols):
                telemetry["infeasible_component"] = int(label)
                return {}, "INFEASIBLE", telemetry
            point = {int(i): min(max(0., m.lower[i]), m.upper[i]) for i in cols}
            if all(m.lo[r] - 1e-9 <= sum(v * point[c] for c, v in m.rows[r].items()) <= m.hi[r] + 1e-9
                   for r in np.flatnonzero(part.row_label == label)):
                telemetry["feasible_by_inspection"] = telemetry.get("feasible_by_inspection", 0) + 1
                continue
            needed.setdefault(label, [])
    status = "OPTIMAL"
    infeasible = False
    for label in sorted(needed):
        t0 = time.monotonic()
        sub, col_map = extract(m, part, label)
        telemetry["extract_seconds"] += time.monotonic() - t0
        targets_: list[str | None] = list(needed[label]) or [None]
        for sid in targets_:
            objective = np.zeros(len(sub.names))
            if sid is not None:
                p = customers[services_by_id[sid].customer].priority
                for w, world in enumerate(worlds):
                    for t in range(H):
                        q = col_map.get(unmet[sid, t, w])
                        if q is not None:
                            objective[q] = world.weight * p
            else:
                telemetry["feasibility_solves"] += 1
            t1 = time.monotonic()
            result, residual = sub.solve(budget, objective, solver_name, mip_gap=req.solver_mip_gap, options=options)
            elapsed = time.monotonic() - t1
            telemetry["solve_seconds"] += elapsed
            state = _state(result, residual)
            telemetry["solves"].append({"service": sid, "component": int(label), "columns": len(sub.names), "rows": len(sub.rows),
                                        "integer": int(sum(sub.integer)), "status": state, "seconds": round(elapsed, 3),
                                        "gap": getattr(result, "mip_gap", None), "nodes": getattr(result, "mip_node_count", None)})
            if state == "INFEASIBLE":
                infeasible = True
                telemetry["infeasible_component"] = int(label)
                break
            if state == "FEASIBLE_TIME_LIMIT" and status == "OPTIMAL":
                status = "FEASIBLE_TIME_LIMIT"
            if state in ("NO_FEASIBLE_SOLUTION", "ERROR"):
                status = state if status != "FEASIBLE_TIME_LIMIT" else status
                continue
            if sid is None:
                continue
            x = result.x
            total = sum(world.weight * sum(world.demand[sid]) for world in worlds)
            loss = 0.
            for w, world in enumerate(worlds):
                for t in range(H):
                    q = col_map.get(unmet[sid, t, w])
                    if q is not None:
                        loss += world.weight * float(x[q])
            values[sid] = 1 - loss / total if total else 1.
        del sub
        if infeasible:
            break
    if infeasible:
        return {}, "INFEASIBLE", telemetry
    if status == "OPTIMAL" and any(s["status"] != "OPTIMAL" for s in telemetry["solves"]):
        status = "FEASIBLE_TIME_LIMIT" if any(s["status"] == "FEASIBLE_TIME_LIMIT" for s in telemetry["solves"]) else "NO_FEASIBLE_SOLUTION"
    telemetry["elapsed_seconds"] = round(time.monotonic() - started, 3)
    for k in ("extract_seconds", "solve_seconds"):
        telemetry[k] = round(telemetry[k], 3)
    return values, status, telemetry


def witnesses_prove(services: tuple[str, ...], witnesses: list) -> tuple[frozenset[str], bool]:
    """Which services a witness serves in full on the oracle's own world, and whether any witness
    exists at all (a feasible point of the whole model). A witness is a physically usable Solution
    of a restriction of the oracle model on the same world set - never an adaptive (node-indexed)
    solve, whose columns differ."""
    usable = [w for w in witnesses if w is not None and w.usable_plan and getattr(w, "recourse", None) is None]
    proven = frozenset(s for s in services if any(w.projected_service.get(s) == 1. for w in usable))
    return proven, bool(usable)


def is_finite(value: float | None) -> bool:
    return value is not None and math.isfinite(value)
