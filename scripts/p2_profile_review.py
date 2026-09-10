"""Profile one ZAAD review exactly as the benchmark planned it (P2 performance pass, diagnosis stage).

The review's snapshot (`scripts.p2_snapshots`) is planned through `zaad.full.planner.plan` with the
solve path instrumented IN PROCESS (wrappers around `Linear.matrix`, `Linear.solve`,
`Linear._highspy_solve`, `Linear.complete`, `model.solve`, `planner.evaluate`, `settle`, `draw`); no
source file is modified and nothing about the problem changes. Per candidate solve it records the
class, construction / matrix / completion / solve / evaluation time, dimensions (variables,
continuous, integer, binary, rows, nonzeros, variable kinds), worlds, horizon, budget, status,
objective, bound, gap, nodes and memory. `--deep` additionally re-solves every captured model
through highspy with a log file and parses HiGHS's own presolve reductions, LP iterations,
node count and incumbent timeline (time to first incumbent, time to the final incumbent, proof
time) - the diagnosis of "time to decision" against "time to proof".

usage: PYTHONPATH=. python3 -m scripts.p2_profile_review FIXTURE SEED REVIEW [--deep] [--tag name]
Writes docs/zaad_full/evidence/p2/perf/profiles/<tag or fixture_seed_rK>.json (+ .highs/*.log with --deep)."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
import platform
import re
import resource
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from scripts.p2_snapshots import make_snapshot, snapshot_path

PROFILES = Path("docs/zaad_full/evidence/p2/perf/profiles")


def _label(kw: dict, worlds: list, req) -> str:
    """Candidate class of a `model.solve` call, from its arguments (the planner's own dispatch)."""
    if kw.get("fixed") is not None:
        return "incumbent"
    if kw.get("targets") is not None:
        return "base_stock"
    first = kw.get("service_first")
    if first:
        if first != "all":
            return f"oracle:{first}"
        return "joint_recovery" if len(worlds) > req.scenarios else "joint_fitted"
    if kw.get("disabled"):
        return "restricted:" + ",".join(sorted(kw["disabled"]))
    if kw.get("allowed_periods") is not None:
        periods = sorted(kw["allowed_periods"])
        return f"cadence_{periods[1] - periods[0] if len(periods) > 1 else 0}_network"
    if kw.get("per_world_service"):
        return "stress_network"
    if kw.get("service_risk") == "cvar":
        return "hedged_network" if len(worlds) > req.scenarios else "protected_network"
    if kw.get("cvar_weight"):
        return "cvar_network"
    if kw.get("service_floor"):
        return "deterministic_network" if len(worlds) == 1 else "stochastic_network"
    return "other"


class Instrumentation:
    """Wrappers installed for the duration of one profiled plan(); restored afterwards."""

    def __init__(self, capture_models: bool):
        self.capture = capture_models
        self.solves: list[dict] = []
        self.current: dict | None = None
        self.evaluate: list[dict] = []
        self.settle = {"calls": 0, "seconds": 0.}
        self.draw: list[dict] = []
        self.models: list[dict] = []
        self.saved: list = []

    def install(self) -> None:
        import psutil
        import zaad.full.model as M
        import zaad.full.planner as P
        rec = self
        proc = psutil.Process()

        def patch(obj, name, fn):
            self.saved.append((obj, name, getattr(obj, name)))
            setattr(obj, name, fn)

        orig_matrix = M.Linear.matrix

        def matrix(self_):
            t = time.perf_counter()
            out = orig_matrix(self_)
            if rec.current is not None:
                rec.current["matrix_seconds"] += time.perf_counter() - t
            return out
        patch(M.Linear, "matrix", matrix)

        orig_lsolve = M.Linear.solve

        def lsolve(self_, seconds, objective=None, solver="highs", mip_gap=1e-6, seed=None):
            t = time.perf_counter()
            rss0 = proc.memory_info().rss
            result, residual = orig_lsolve(self_, seconds, objective, solver, mip_gap, seed)
            dt = time.perf_counter() - t
            ints = np.asarray(self_.integer, dtype=bool)
            upper = np.asarray(self_.upper, dtype=float)
            binary = int((ints & (upper <= 1)).sum())
            nnz = sum(1 for r in self_.rows for v in r.values() if v)
            kinds = Counter(str(n[0]) for n in self_.names)
            row_kinds = Counter()
            entry = {"phase": "phase1" if objective is not None else ("phase2" if rec.current and any(e["phase"] == "phase1" for e in rec.current["linear"]) else "solve"),
                     "budget_seconds": float(seconds), "solver": solver, "seeded": seed is not None, "mip_gap": float(mip_gap),
                     "seconds": dt, "variables": len(self_.names), "integer": int(ints.sum()), "binary": binary,
                     "continuous": len(self_.names) - int(ints.sum()), "rows": len(self_.rows), "nonzeros": nnz,
                     "variable_kinds": dict(kinds), "row_count_by_kind": dict(row_kinds),
                     "status": int(result.status), "objective": result.fun, "gap": getattr(result, "mip_gap", None),
                     "bound": getattr(result, "mip_dual_bound", None), "nodes": getattr(result, "mip_node_count", None),
                     "residual": float(residual) if np.isfinite(residual) else None, "message": str(result.message),
                     "rss_delta_mb": (proc.memory_info().rss - rss0) / 2**20, "rss_after_mb": proc.memory_info().rss / 2**20}
            if rec.current is not None:
                rec.current["linear"].append(entry)
                if rec.capture:
                    rec.models.append({"candidate": rec.current["label"], "index": rec.current["index"], "phase": entry["phase"],
                                       "budget_seconds": float(seconds), "mip_gap": float(mip_gap),
                                       "cost": np.asarray(self_.cost if objective is None else objective, dtype=float),
                                       "lower": np.asarray(self_.lower, dtype=float), "upper": upper,
                                       "integer": np.asarray(self_.integer, dtype=np.int8), "lo": np.asarray(self_.lo, dtype=float),
                                       "hi": np.asarray(self_.hi, dtype=float), "matrix": orig_matrix(self_),
                                       "seed": None if seed is None else np.asarray(seed, dtype=float),
                                       "names": [tuple(str(x) for x in n) for n in self_.names]})
            else:
                rec.solves.append({"label": "outside_plan", "linear": [entry]})
            return result, residual
        patch(M.Linear, "solve", lsolve)

        orig_complete = M.Linear.complete

        def complete(self_, controls, seconds, mode="equal"):
            t = time.perf_counter()
            out = orig_complete(self_, controls, seconds, mode)
            if rec.current is not None:
                rec.current["completions"].append({"mode": mode, "budget_seconds": float(seconds), "seconds": time.perf_counter() - t,
                                                   "accepted": out["accepted"], "status": out.get("completion_status"), "controls": len(controls)})
            return out
        patch(M.Linear, "complete", complete)

        orig_solve = M.solve

        def msolve(req, worlds, **kw):
            ctx = {"index": len(rec.solves), "label": _label(kw, worlds, req), "worlds": len(worlds), "horizon": req.horizon,
                   "arguments": {k: (sorted(v) if isinstance(v, frozenset) else (True if k in ("fixed", "targets", "seed", "expected_shortage", "continuation", "continuation_feeds", "excess_penalty", "service_risk_levels") and v is not None else v))
                                 for k, v in kw.items() if v not in (None, False, 0., frozenset())},
                   "linear": [], "completions": [], "matrix_seconds": 0.}
            rec.current = ctx
            rss0 = proc.memory_info().rss
            t = time.perf_counter()
            try:
                sol = orig_solve(req, worlds, **kw)
            finally:
                ctx["total_seconds"] = time.perf_counter() - t
                rec.current = None
            ctx.update(status=sol.status, model_solve_seconds=sol.solve_seconds, variables=sol.variables, constraints=sol.constraints,
                       gap=sol.gap, best_bound=sol.best_bound, nodes=sol.nodes, projected_cost=sol.projected_cost,
                       warm_start={k: v for k, v in (sol.warm_start or {}).items() if k != "attempts"} if sol.warm_start else None,
                       linear_seconds=sum(e["seconds"] for e in ctx["linear"]),
                       completion_seconds=sum(c["seconds"] for c in ctx["completions"]),
                       rss_delta_mb=(proc.memory_info().rss - rss0) / 2**20)
            ctx["construction_seconds"] = ctx["total_seconds"] - ctx["linear_seconds"] - ctx["completion_seconds"]
            rec.solves.append(ctx)
            return sol
        patch(M, "solve", msolve)
        patch(P, "solve", msolve)

        orig_evaluate = P.evaluate

        def evaluate(req, solution, worlds, terminal=None, fits=None, terminal_cap=None):
            t = time.perf_counter()
            rows = orig_evaluate(req, solution, worlds, terminal, fits, terminal_cap)
            rec.evaluate.append({"worlds": len(worlds), "terminal": terminal is not None, "seconds": time.perf_counter() - t,
                                 "usable": sum(1 for r in rows if r["usable"])})
            return rows
        patch(P, "evaluate", evaluate)

        orig_settle = P.settle

        def settle(*a, **k):
            t = time.perf_counter()
            try:
                return orig_settle(*a, **k)
            finally:
                rec.settle["calls"] += 1
                rec.settle["seconds"] += time.perf_counter() - t
        patch(P, "settle", settle)

        orig_draw = P.draw

        def draw(req, seed, n, *a, **k):
            t = time.perf_counter()
            out = orig_draw(req, seed, n, *a, **k)
            rec.draw.append({"n": n, "seconds": time.perf_counter() - t})
            return out
        patch(P, "draw", draw)

    def uninstall(self) -> None:
        for obj, name, value in reversed(self.saved):
            setattr(obj, name, value)
        self.saved.clear()


def decision(report: dict) -> dict:
    """The review's decision keys (what the benchmark and the isolation compare)."""
    orch = report["orchestration"]
    return {"status": report["status"], "selected_policy": report["selected_policy"], "state": orch["state"],
            "owner": orch["planner_owner"], "requested": orch["candidate_classes_requested"], "built": orch["candidates_built"],
            "purchases_t0": sorted((r["source"], round(r["quantity"], 6)) for r in report["actions"] if r["action"] == "purchase" and r["period"] == 0),
            "transfers_t0": sorted((r["transfer"], r["expiry_cohort"], round(r["quantity"], 6)) for r in report["actions"] if r["action"] == "transfer" and r["period"] == 0),
            "actions": sorted((r["action"], r.get("source") or r.get("transfer") or r.get("po"), r.get("period"), round(r["quantity"], 6)) for r in report["actions"]),
            "candidate_status": {k: v["status"] for k, v in report["solve_quality"]["candidates"].items()},
            "candidate_cost": {k: v.get("achieved_gap") for k, v in report["solve_quality"]["candidates"].items()}}


# ---------------------------------------------------------------- HiGHS log analysis (--deep)

_PROGRESS = re.compile(r"^\s*([A-Z ])\s*(\d+)\s+(\d+)\s+(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)s\s*$")


def parse_highs_log(text: str) -> dict:
    out: dict = {"presolve": None, "reduced": None, "timeline": [], "first_incumbent_s": None, "final_incumbent_s": None,
                 "final_incumbent_objective": None, "proof_s": None, "lp_iterations": None, "nodes": None, "status": None,
                 "timing": None, "incumbent_count": 0}
    m = re.search(r"Presolve reductions: rows (\d+)\(-(\d+)\); columns (\d+)\(-(\d+)\); nonzeros (\d+)\(-(\d+)\)", text)
    if m:
        out["presolve"] = {"rows": int(m[1]), "rows_removed": int(m[2]), "columns": int(m[3]), "columns_removed": int(m[4]),
                           "elements": int(m[5]), "elements_removed": int(m[6])}
    elif "Presolve: Reduced to empty" in text or "reduced to empty" in text.lower():
        out["presolve"] = {"note": "reduced to empty"}
    m = re.search(r"Solving MIP model with:\s*\n\s*(\d+) rows\s*\n\s*(\d+) cols \((\d+) binary, (\d+) integer, (\d+) implied int\., (\d+) continuous(?:, \d+ domain fixed)?\)\s*\n\s*(\d+) nonzeros", text)
    if m:
        out["reduced"] = {"rows": int(m[1]), "cols": int(m[2]), "binary": int(m[3]), "integer": int(m[4]), "implied_int": int(m[5]),
                          "continuous": int(m[6]), "nonzeros": int(m[7])}
    best = None
    for line in text.splitlines():
        pm = _PROGRESS.match(line)
        if not pm:
            continue
        tag, _, _, _, _, bound, sol, gap, _, _, _, lp, t = pm.groups()
        try:
            sol_v = float(sol)
        except ValueError:
            sol_v = float("inf")
        entry = {"tag": tag.strip() or "", "t": float(t), "bound": bound, "sol": sol, "gap": gap, "lp_iters": int(lp)}
        out["timeline"].append(entry)
        if np.isfinite(sol_v):
            if out["first_incumbent_s"] is None:
                out["first_incumbent_s"] = float(t)
            if best is None or sol_v < best - 1e-9 * max(1., abs(best)):
                best = sol_v
                out["final_incumbent_s"] = float(t)
                out["final_incumbent_objective"] = sol_v
                out["incumbent_count"] += 1
    m = re.search(r"Status\s+(.*)", text)
    if m:
        out["status"] = m[1].strip()
    m = re.search(r"Timing\s+([\d.]+)", text)
    if m:
        out["timing"] = {"total": float(m[1])}
        if out["status"] and "Optimal" in out["status"]:
            out["proof_s"] = float(m[1])
    m = re.search(r"Gap\s+(\S+)", text)
    if m:
        out["final_gap"] = m[1]
    m = re.search(r"Max sub-MIP depth\s+(\d+)", text)
    if m:
        out["max_submip_depth"] = int(m[1])
    m = re.search(r"(\d+) \(separation\)\s*\n\s*(\d+) \(heuristics\)", text)
    if m:
        out["lp_iterations_separation"] = int(m[1])
        out["lp_iterations_heuristics"] = int(m[2])
    m = re.search(r"Nodes\s+(\d+)", text)
    if m:
        out["nodes"] = int(m[1])
    m = re.search(r"LP iterations\s+(\d+)", text)
    if m:
        out["lp_iterations"] = int(m[1])
    return out


def deep_resolve(models: list[dict], log_dir: Path, threads: int | None = None) -> list[dict]:
    """Re-solve each captured model through highspy with logging. The problem is byte-identical to
    the captured one; the HiGHS build differs from scipy's bundled one on the unseeded path, so
    these timings are the analysis instrument, not the review's own wall time."""
    import highspy
    log_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, mdl in enumerate(models):
        h = highspy.Highs()
        log = log_dir / f"{i:02d}_{mdl['candidate']}_{mdl['phase']}.log"
        if log.exists():
            log.unlink()
        h.setOptionValue("output_flag", True)
        h.setOptionValue("log_to_console", False)
        h.setOptionValue("log_file", str(log))
        h.setOptionValue("time_limit", float(max(mdl["budget_seconds"], 1e-3)))
        h.setOptionValue("mip_rel_gap", float(mdl["mip_gap"]))
        if threads is not None:
            h.setOptionValue("threads", int(threads))
        lp = highspy.HighsLp()
        matrix = mdl["matrix"]
        lp.num_col_, lp.num_row_ = len(mdl["cost"]), len(mdl["lo"])
        lp.col_cost_ = mdl["cost"]
        lp.col_lower_ = mdl["lower"]
        lp.col_upper_ = mdl["upper"]
        lp.row_lower_ = mdl["lo"]
        lp.row_upper_ = mdl["hi"]
        lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
        lp.a_matrix_.start_ = np.asarray(matrix.indptr, dtype=np.int32)
        lp.a_matrix_.index_ = np.asarray(matrix.indices, dtype=np.int32)
        lp.a_matrix_.value_ = np.asarray(matrix.data, dtype=float)
        lp.integrality_ = [highspy.HighsVarType.kInteger if v else highspy.HighsVarType.kContinuous for v in mdl["integer"]]
        h.passModel(lp)
        if mdl["seed"] is not None:
            start = highspy.HighsSolution()
            start.col_value = mdl["seed"]
            h.setSolution(start)
        t = time.perf_counter()
        h.run()
        dt = time.perf_counter() - t
        info = h.getInfo()
        text = log.read_text() if log.exists() else ""
        parsed = parse_highs_log(text)
        rows.append({"index": i, "candidate": mdl["candidate"], "phase": mdl["phase"], "seeded": mdl["seed"] is not None,
                     "budget_seconds": mdl["budget_seconds"], "seconds": dt, "model_status": str(h.getModelStatus()),
                     "objective": float(info.objective_function_value), "bound": float(info.mip_dual_bound) if np.isfinite(info.mip_dual_bound) else None,
                     "gap": float(info.mip_gap) if np.isfinite(info.mip_gap) else None, "nodes": int(info.mip_node_count),
                     "raw": {"cols": len(mdl["cost"]), "rows": len(mdl["lo"]), "nonzeros": int(matrix.nnz),
                             "integer": int(mdl["integer"].sum()), "binary": int(((mdl["integer"] == 1) & (mdl["upper"] <= 1)).sum())},
                     "highs": parsed, "log": str(log)})
        print(f"  deep {i:02d} {mdl['candidate']:<24} {mdl['phase']:<7} {dt:7.1f}s {h.getModelStatus()} nodes {int(info.mip_node_count)} "
              f"first_inc {parsed['first_incumbent_s']} final_inc {parsed['final_incumbent_s']} proof {parsed['proof_s']} "
              f"presolve {parsed['presolve']}", flush=True)
    return rows


def machine() -> dict:
    import scipy
    import highspy
    load = os.getloadavg()
    return {"platform": platform.platform(), "python": sys.version.split()[0], "cpus": os.cpu_count(), "loadavg_1m": load[0],
            "scipy": scipy.__version__, "highspy": highspy.__version__ if hasattr(highspy, "__version__") else "?",
            "other_python_processes": int(subprocess.run(["sh", "-c", "ps -axo comm= | grep -ci python || true"], capture_output=True, text=True).stdout.strip() or 0) - 1}


def profile(fixture: str, seed: int, review: int, deep: bool, tag: str | None, threads: int | None) -> dict:
    from zaad.full.contracts import Request
    from zaad.full.planner import plan
    from zaad.meio.baselines import register_replay_methods
    register_replay_methods()
    path = snapshot_path(fixture, seed, review)
    if not path.exists():
        make_snapshot(fixture, seed, review)
    req = Request.model_validate_json(path.read_text())
    import psutil
    proc = psutil.Process()
    inst = Instrumentation(capture_models=deep)
    inst.install()
    rss0 = proc.memory_info().rss
    started = time.perf_counter()
    try:
        report = plan(req)
    finally:
        inst.uninstall()
    wall = time.perf_counter() - started
    import zaad.full.model as _model
    out = {"fixture": fixture, "seed": seed, "review": review, "snapshot": str(path), "machine": machine(),
           "switches": {k: getattr(_model, k) for k in dir(_model) if k.isupper() and not k.startswith("_")},
           "request": {"horizon": req.horizon, "scenarios": req.scenarios, "max_solve_seconds": req.max_solve_seconds,
                       "solve_budget_ceiling_seconds": req.solve_budget_ceiling_seconds, "solver": req.solver, "solver_mip_gap": req.solver_mip_gap,
                       "warm_start": req.warm_start, "warm_start_min_variables": req.warm_start_min_variables,
                       "locations": len(req.locations), "transfers": len(req.transfers), "sources": len(req.sources), "services": len(req.services),
                       "skus": len(req.skus), "stresses": len(req.stresses), "engine_profile": req.engine_profile},
           "wall_seconds": wall, "decision": decision(report),
           "phases": {"solve_total": sum(s.get("total_seconds", 0.) for s in inst.solves),
                      "milp_total": sum(e["seconds"] for s in inst.solves for e in s.get("linear", [])),
                      "completion_total": sum(s.get("completion_seconds", 0.) for s in inst.solves),
                      "construction_total": sum(s.get("construction_seconds", 0.) for s in inst.solves),
                      "matrix_total": sum(s.get("matrix_seconds", 0.) for s in inst.solves),
                      "evaluate_total": sum(e["seconds"] for e in inst.evaluate), "evaluate_calls": len(inst.evaluate),
                      "settle_calls": inst.settle["calls"], "settle_total": inst.settle["seconds"],
                      "draw_total": sum(d["seconds"] for d in inst.draw)},
           "solves": inst.solves, "evaluate": inst.evaluate,
           "memory": {"rss_before_mb": rss0 / 2**20, "rss_after_mb": proc.memory_info().rss / 2**20,
                      "ru_maxrss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (2**20 if sys.platform == "darwin" else 2**10)}}
    out["phases"]["other"] = wall - out["phases"]["solve_total"] - out["phases"]["evaluate_total"]
    name = tag or f"{fixture}_{seed}_r{review}"
    if deep:
        out["deep"] = deep_resolve(inst.models, PROFILES / f"{name}.highs", threads)
    PROFILES.mkdir(parents=True, exist_ok=True)
    (PROFILES / f"{name}.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"{name}: wall {wall:.1f}s solves {len(inst.solves)} milp {out['phases']['milp_total']:.1f}s construction {out['phases']['construction_total']:.1f}s "
          f"completion {out['phases']['completion_total']:.1f}s evaluate {out['phases']['evaluate_total']:.1f}s other {out['phases']['other']:.1f}s "
          f"state {out['decision']['state']} selected {out['decision']['selected_policy']} status {out['decision']['status']}")
    for s in inst.solves:
        if "total_seconds" not in s:
            continue
        print(f"  {s['index']:02d} {s['label']:<24} W{s['worlds']} H{s['horizon']} {s['status']:<20} total {s['total_seconds']:7.1f}s "
              f"build {s['construction_seconds']:5.1f}s compl {s['completion_seconds']:5.1f}s milp {s['linear_seconds']:6.1f}s "
              f"vars {s['variables']} rows {s['constraints']} gap {s['gap']} nodes {s['nodes']} "
              + " ".join(f"[{e['phase']} {e['solver']} b{e['budget_seconds']:.0f}s {e['seconds']:.1f}s int {e['integer']} bin {e['binary']} nnz {e['nonzeros']} st {e['status']}]" for e in s["linear"]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("fixture")
    ap.add_argument("seed", type=int)
    ap.add_argument("review", type=int)
    ap.add_argument("--deep", action="store_true")
    ap.add_argument("--tag")
    ap.add_argument("--threads", type=int, default=None)
    ap.add_argument("--switch", action="append", default=[], help="module.attr=value (e.g. zaad.full.model.FEFO_SYMMETRY_ELIMINATION=False) for A/B equivalence runs")
    a = ap.parse_args()
    import importlib
    for item in a.switch:
        target, value = item.split("=", 1)
        module, attr = target.rsplit(".", 1)
        setattr(importlib.import_module(module), attr, json.loads(value.lower()) if value.lower() in ("true", "false", "null") else (float(value) if value.replace(".", "", 1).isdigit() else value))
    profile(a.fixture, a.seed, a.review, a.deep, a.tag, a.threads)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
