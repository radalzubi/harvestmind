"""P4 production performance closure - profiling harness (TRACK A, diagnosis before any change).

For every cell (request class x histories x epochs x continuations) it runs the three tree solves of
`zaad.recourse.policy.compare` (static / adaptive / perfect information) through highspy with the
HiGHS log captured, and then the whole `plan()`; per solve it records build time (Linear object
creation -> solve entry), matrix assembly, presolve / solve timing and reductions parsed from the
HiGHS log, dimensions by column class and by node, nonzeros, objective / bound / gap / nodes / LP
iterations, time to first incumbent and to proof, and peak process memory. Nothing here changes the
model: the harness only observes. Output: docs/zaad_full/evidence/p4/perf_closure/P4_PERF_PROFILE.json
and the raw HiGHS logs under highs_logs/.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import resource
import tempfile
import time
from pathlib import Path
from typing import Any

import zaad.full.model as M
from zaad.full.contracts import Request
from zaad.full.planner import plan
from zaad.recourse.contracts import resolve
from zaad.recourse.fixtures import sector_base, p2_base, sourcing_base, with_recourse
from zaad.recourse.policy import compare
from zaad.recourse.worlds import draw_tree

OUT = Path("docs/zaad_full/evidence/p4/perf_closure")
LOGS = OUT / "highs_logs"


def _p1():
    from zaad.full.fixtures_p1 import p1_request
    return p1_request(seed=41001, scenarios=3, max_solve_seconds=15.)


CLASSES = {
    "A_single_sku": _p1,
    "B_p2_network": lambda: p2_base(),
    "C_p3_two_sources": lambda: sourcing_base("E2_landed_beats_unit_price"),
    "D_p3_shared_order": lambda: sourcing_base("C6_shared_mov_multi_sku"),
    "E_produce": lambda: sector_base("P2_near_expiry_inventory"),
}
# histories, epochs, continuations -> worlds: 3, 6, 8, 12, 16 with 1 and 2 epochs
GRID = [(3, [3], 1), (3, [3], 2), (4, [3], 2), (8, [3], 1), (3, [3, 6], 2), (4, [3, 6], 2), (8, [3, 6], 1)]

# ---- instrumentation ------------------------------------------------------------------------------
ctx: dict[str, Any] = {"label": "?", "calls": [], "build_start": None, "log_dir": None, "capture": True}
_init, _solve, _hsolve, _matrix = M.Linear.__init__, M.Linear.solve, M.Linear._highspy_solve, M.Linear.matrix


def linear_init(self):
    _init(self)
    ctx["build_start"] = time.perf_counter()


def classify(names, integer, upper) -> dict[str, Any]:
    by_class: dict[str, int] = {}
    node_cols = {"purchase": 0, "transfer": 0}
    binaries = {"order(shared-order)": 0, "active(MOQ/MOV activation)": 0, "packs": 0, "pallets": 0, "freight_tier": 0, "transfer_dispatch": 0, "transfer_packs": 0,
                "switch": 0, "fefo": 0, "depleted": 0, "priority": 0, "direct_first": 0, "line_full": 0, "po_option": 0, "supplier_order(other)": 0, "other": 0}
    for n, i, u in zip(names, integer, upper):
        kind = n[0] if isinstance(n, tuple) else str(n)
        by_class[kind] = by_class.get(kind, 0) + 1
        if isinstance(n, tuple) and kind in ("purchase", "transfer") and isinstance(n[-1], str) and n[-1].startswith("e"):
            node_cols[kind] += 1
        if i and u == 1:
            key = {"order": "order(shared-order)", "active": "active(MOQ/MOV activation)"}.get(kind, kind)
            binaries[key if key in binaries else ("supplier_order(other)" if "order" in str(kind) else "other")] += 1
    return {"columns_by_class": by_class, "node_columns": node_cols, "binaries_by_class": {k: v for k, v in binaries.items() if v}}


def _num(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:
        return None


def parse_log(path: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if not path.exists():
        return out
    txt = path.read_text(errors="ignore")
    m = re.search(r"Presolve reductions: rows (\d+)\(-(\d+)\); columns (\d+)\(-(\d+)\); nonzeros (\d+)\(-(\d+)\)", txt)
    if m:
        out["presolve"] = {"rows": int(m[1]), "rows_removed": int(m[2]), "cols": int(m[3]), "cols_removed": int(m[4]), "nnz": int(m[5]), "nnz_removed": int(m[6])}
    m = re.search(r"Solving MIP model with:\s*(\d+) rows\s*(\d+) cols \((\d+) binary, (\d+) integer, (\d+) implied int\., (\d+) continuous(?:, \d+ domain fixed)?\)\s*(\d+) nonzeros", txt)
    if m:
        out["presolved_model"] = {"rows": int(m[1]), "cols": int(m[2]), "binary": int(m[3]), "integer": int(m[4]), "implied_int": int(m[5]), "continuous": int(m[6]), "nnz": int(m[7])}
    m = re.search(r"Coefficient ranges:\s*Matrix\s*\[([^\]]+)\]\s*Cost\s*\[([^\]]+)\]\s*Bound\s*\[([^\]]+)\]\s*RHS\s*\[([^\]]+)\]", txt)
    if m:
        out["coefficient_ranges"] = {"matrix": m[1], "cost": m[2], "bound": m[3], "rhs": m[4]}
    # B&B table rows: the last column is the elapsed time; the first row with a finite BestSol is the first incumbent
    first = None; root = None; last_t = None
    for line in txt.splitlines():
        cols = line.split()
        if len(cols) < 12 or not re.fullmatch(r"[\d.]+s?", cols[-1]) or not (cols[-6].endswith("%") or cols[-6] in ("inf", "Large")):
            continue
        try:
            t = float(cols[-1].rstrip("s"))
        except ValueError:
            continue
        if root is None:
            root = t
        last_t = t
        best_sol = cols[-7]
        if first is None and best_sol != "inf" and re.fullmatch(r"-?[\d.e+-]+", best_sol):
            first = t
    if root is not None:
        out["time_to_root_s"] = root
    if first is not None:
        out["first_incumbent_s"] = first
    if last_t is not None:
        out["last_table_time_s"] = last_t
    m = re.search(r"Timing\s+([\d.]+)", txt)
    if m:
        out["timing_total_s"] = float(m[1])
    m = re.search(r"LP iterations\s+(\d+)", txt)
    if m:
        out["lp_iterations"] = int(m[1])
    m = re.search(r"Nodes\s+(\d+)", txt)
    if m:
        out["nodes"] = int(m[1])
    m = re.search(r"Gap\s+([\d.e+-]+)%", txt)
    if m:
        out["gap_pct"] = _num(m[1])
    m = re.search(r"Dual bound\s+([-\d.e+]+)", txt)
    if m:
        out["dual_bound"] = _num(m[1])
    m = re.search(r"Primal bound\s+([-\d.e+]+)", txt)
    if m:
        out["primal_bound"] = _num(m[1])
    m = re.search(r"Max sub-MIP depth\s+(\d+)", txt)
    if m:
        out["max_submip_depth"] = int(m[1])
    return out


def hsolve(self, matrix, cost, seconds, mip_gap, seed=None, first_feasible=False, options=None):
    opts = dict(options or {})
    log_path = None
    if ctx["capture"] and ctx["log_dir"] is not None:
        log_path = Path(ctx["log_dir"]) / f"{ctx['label']}_{len(ctx['calls']):02d}.log"
        opts.update({"output_flag": True, "log_to_console": False, "log_file": str(log_path)})
    t = time.perf_counter()
    res = _hsolve(self, matrix, cost, seconds, mip_gap, seed, first_feasible, opts)
    dt = time.perf_counter() - t
    ctx["_last_hs"] = {"highspy_wall": round(dt, 3), "log": str(log_path) if log_path else None, "log_parsed": parse_log(log_path) if log_path else {}}
    return res


def lsolve(self, seconds, objective=None, solver="highs", mip_gap=1e-6, seed=None, options=None):
    build = (time.perf_counter() - ctx["build_start"]) if ctx["build_start"] else None
    t = time.perf_counter()
    mt = time.perf_counter(); matrix = _matrix(self); mtime = time.perf_counter() - mt
    # route through highspy always so the log exists (identical model; the solver, not the problem)
    res = _solve(self, seconds, objective, "highspy" if ctx["capture"] else solver, mip_gap, seed, options)
    dt = time.perf_counter() - t
    r = res[0]
    ints = int(sum(self.integer)); bins = int(sum(1 for i, u in zip(self.integer, self.upper) if i and u == 1))
    rec = {"label": ctx["label"], "kind": "solve" if objective is None else "phase(objective)", "budget": round(seconds, 2), "build_s": round(build, 3) if build else None,
           "matrix_s": round(mtime, 3), "solve_wall_s": round(dt, 3), "seeded": seed is not None, "rows": len(self.rows), "cols": len(self.names),
           "continuous": len(self.names) - ints, "integer": ints, "binary": bins, "nnz": int(matrix.nnz),
           "status": int(r.status), "message": str(getattr(r, "message", ""))[:40], "objective": r.fun, "bound": getattr(r, "mip_dual_bound", None),
           "gap": getattr(r, "mip_gap", None), "bb_nodes": getattr(r, "mip_node_count", None), **classify(self.names, self.integer, self.upper),
           "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 ** 2), 1), **ctx.pop("_last_hs", {})}
    ctx["calls"].append(rec)
    ctx["build_start"] = None
    return res


_complete = M.Linear.complete


def lcomplete(self, controls, seconds, mode="equal"):
    """Warm-start completion solves (v8 P0-W3): recorded as their own kind so build time is not blamed for them."""
    t = time.perf_counter()
    d = _complete(self, controls, seconds, mode)
    dt = time.perf_counter() - t
    ctx["calls"].append({"label": ctx["label"], "kind": f"warm_complete({mode})", "budget": round(seconds, 2), "solve_wall_s": round(dt, 3), "build_s": None, "matrix_s": None,
                         "rows": len(self.rows), "cols": len(self.names), "continuous": None, "integer": int(sum(self.integer)), "binary": None, "nnz": None,
                         "status": d.get("accepted"), "message": str(d.get("completion_status"))[:40], "objective": None, "bound": None, "gap": None, "bb_nodes": None,
                         "columns_by_class": {}, "node_columns": {}, "binaries_by_class": {}, "peak_rss_mb": None})
    ctx["build_start"] = time.perf_counter()   # the builder resumes after the completion
    return d


M.Linear.__init__ = linear_init
M.Linear.solve = lsolve
M.Linear._highspy_solve = hsolve
M.Linear.complete = lcomplete


def cell(cls: str, make, histories: int, epochs: list[int], cont: int, log_dir: Path) -> dict[str, Any]:
    base = make()
    req = with_recourse(base, review_periods=epochs, observables=["demand", "receipts"], continuations=cont)
    req = Request.model_validate(req.model_dump())
    rc = resolve(req)
    worlds = draw_tree(req, rc, req.seed, histories, cont)
    row: dict[str, Any] = {"class": cls, "histories": histories, "epochs": epochs, "continuations": cont, "worlds": len(worlds),
                           "skus": len(req.skus), "sources": len(req.sources), "locations": len(req.locations), "services": len(req.services), "horizon": req.horizon,
                           "budget_s": req.max_solve_seconds}
    ctx["log_dir"] = log_dir; ctx["calls"] = []; ctx["capture"] = True
    ctx["label"] = f"{cls}_h{histories}_e{'-'.join(map(str, epochs))}_c{cont}_compare"
    t = time.perf_counter()
    out = compare(req, worlds, rc, perfect=True, service_floor=True)
    row["compare_wall_s"] = round(time.perf_counter() - t, 2)
    row["information_sets"] = {str(e): len(v) for e, v in out["nodes"].sets.items()} if out["nodes"] is not None else {}
    row["compare_solves"] = ctx["calls"]
    row["comparators"] = {k: {"status": out[k].status, "objective": out[k].projected_cost, "solve_seconds": round(out[k].solve_seconds, 3), "nodes": out[k].nodes, "gap": out[k].gap, "bound": out[k].best_bound}
                          for k in ("static", "adaptive", "perfect") if out.get(k) is not None}
    row["ordering_ok"] = out.get("ordering_ok"); row["perfect_status"] = out.get("perfect_status")
    # whole planner (production path) with the log capture off (the frozen candidate route stays scipy/highspy as released)
    ctx["calls"] = []; ctx["capture"] = False; ctx["label"] = f"{cls}_h{histories}_e{'-'.join(map(str, epochs))}_c{cont}_plan"
    preq = req.model_copy(update={"scenarios": min(histories, 4)}) if req.scenarios != min(histories, 4) else req
    preq = Request.model_validate(preq.model_dump())
    t = time.perf_counter()
    try:
        rep = plan(preq)
        row["planner_wall_s"] = round(time.perf_counter() - t, 2)
        row["planner_verdict"] = (rep.get("recourse") or {}).get("verdict")
        row["planner_selected"] = rep.get("selected_policy")
        row["planner_candidate_solves"] = len(ctx["calls"])
        row["planner_solves"] = [{k: c.get(k) for k in ("label", "kind", "solve_wall_s", "build_s", "rows", "cols", "binary", "status", "bb_nodes", "objective")} for c in ctx["calls"]]
        row["planner_solver_wall_s"] = round(sum(c["solve_wall_s"] for c in ctx["calls"]), 2)
        row["planner_build_wall_s"] = round(sum(c["build_s"] or 0 for c in ctx["calls"]), 2)
    except Exception as exc:  # recorded, never hidden
        row["planner_error"] = f"{type(exc).__name__}: {exc}"[:200]
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--classes", default="")
    ap.add_argument("--grid", default="", help="indices into GRID, comma separated")
    ap.add_argument("--tag", default="P4_PERF_PROFILE")
    a = ap.parse_args()
    classes = [c for c in a.classes.split(",") if c] or list(CLASSES)
    grid = [GRID[int(i)] for i in a.grid.split(",") if i] or GRID
    OUT.mkdir(parents=True, exist_ok=True); LOGS.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for cls in classes:
        for histories, epochs, cont in grid:
            worlds = histories * cont ** len(epochs)
            if worlds > 16:
                continue
            log_dir = LOGS / cls
            log_dir.mkdir(parents=True, exist_ok=True)
            try:
                row = cell(cls, CLASSES[cls], histories, epochs, cont, log_dir)
            except Exception as exc:
                row = {"class": cls, "histories": histories, "epochs": epochs, "continuations": cont, "error": f"{type(exc).__name__}: {exc}"[:200]}
            rows.append(row)
            a_ = next((c for c in row.get("compare_solves", []) if c["label"].endswith("compare") and c["kind"] == "solve"), None)
            print(f"{cls:18s} h={histories} e={epochs} c={cont} worlds={row.get('worlds')} sets={row.get('information_sets')} compare={row.get('compare_wall_s')}s "
                  f"planner={row.get('planner_wall_s')}s solves={row.get('planner_candidate_solves')} {row.get('planner_verdict', row.get('error', ''))}", flush=True)
            (OUT / f"{a.tag}.json").write_text(json.dumps(rows, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
