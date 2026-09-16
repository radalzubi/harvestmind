"""Production planner benchmark: where the wall clock of one product-shaped plan goes, by product count.

Nothing under zaad/ is changed. The script builds the vault the product's sample path builds
(`load_fmcg_sample_into`, the same synthetic distributor the self-serve workspace loads) or the
three-site network vault, chooses products the way the product's plan button does (every product
with a declared order change first, then the most units still on order, then stock value, then id),
builds the request with every phase asked for — exactly what `fetchWorkspaceStateFor(chosen,
ALL_PHASES)` sends to `POST /api/zaad/network/jobs` — and runs the released planner with the
solver calls observed from outside: every MILP's dimensions, budget, wall and CPU time, and every
candidate's build-and-settle time around them. It then times what the job path does after the
planner: the plan shape, the report serialisation and the job-store write.

Usage: python -m scripts.production_solve_benchmark [--products 1,2,5,8,10] [--vault sample|network]
                                                    [--seconds 15] [--seed 7] [--out DIR] [--label NAME]
                                                    [--dump-mps DIR] [--request-override KEY=JSON ...]
                                                    [--structure-only]

Performance pass (2026-09-16): every MILP is attributed to the planner stage that asked for it and
to its lexicographic phase; the plan's report and shape are written beside the benchmark for
decision-identity comparison (`scripts/plan_report_compare.py`); `--dump-mps` writes each MILP as
HiGHS saw it for `scripts/milp_replay.py`; `--request-override` changes one Request field for an
experiment; `--structure-only` builds every model the plan would solve and records its dimensions
without solving (every solve returns "no feasible solution" instantly) - for sizes that must not be
solved on the benchmark machine.
"""
from __future__ import annotations

import argparse
import json
import linecache
import os
import platform
import resource
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb


def rank_products(request) -> list[str]:
    """The product's scope rule (web/src/lib/zaad/workspace-data.tsx, rankProducts)."""
    by_source = {s.id: s.sku for s in request.sources}
    on_order: dict[str, float] = {}
    for po in request.pipeline:
        sku = by_source.get(po.source)
        if sku:
            on_order[sku] = on_order.get(sku, 0.) + float(po.expected_accepted_remaining)
    unit = {s.id: float(getattr(s, "unit_value", None) or getattr(s, "unit_cost", None) or 0.) for s in request.skus}
    value: dict[str, float] = {}
    for st in request.stock:
        value[st.sku] = value.get(st.sku, 0.) + float(st.quantity) * unit.get(st.sku, 0.)
    return sorted((s.id for s in request.skus), key=lambda s: (-on_order.get(s, 0.), -value.get(s, 0.), s))


class Recorder:
    """Observes the released model and planner from outside: no line of zaad/ runs differently."""

    def __init__(self) -> None:
        self.solves: list[dict] = []
        self.candidates: list[dict] = []
        self.settle_s = 0.
        self.settle_calls = 0
        self.solver_core_s = 0.
        self._orig: list[tuple] = []
        # performance pass: stage attribution from outside (the planner line that asked for the
        # solve), lexicographic phase, and the time of the other planner stages
        self.t_start = time.perf_counter()
        self.stages_s: dict[str, float] = {}
        self.stage_calls: dict[str, int] = {}
        self._last_lex: tuple[int, int] | None = None
        self._current_kw: dict = {}
        # optional: write every MILP the planner solves as an MPS file (the exact arrays HiGHS sees,
        # with the phase's objective) so a solve can be replayed and studied in isolation
        self.dump_dir: Path | None = None
        self.structure_only = False

    @staticmethod
    def stage_of() -> tuple[str, str, int]:
        """(stage, planner function, planner line) of the planner call that owns the running solve."""
        frame = sys._getframe(2)
        while frame is not None:
            if frame.f_code.co_filename.endswith("planner.py"):
                line = frame.f_lineno
                text = linecache.getline(frame.f_code.co_filename, line).strip()
                func = frame.f_code.co_name
                stage = f"{func}:{line}"
                if 'candidates["' in text:
                    stage = text.split('candidates["', 1)[1].split('"', 1)[0]
                elif text.startswith("oracle ="):
                    stage = "service_frontier"
                elif text.startswith("recovery ="):
                    stage = "joint_recovery"
                elif text.startswith("joint_fitted ="):
                    stage = "joint_fitted"
                elif text.startswith("base ="):
                    stage = "base_stock_proxy"
                elif text.startswith("incumbent ="):
                    stage = "incumbent"
                elif text.startswith("restricted ="):
                    stage = "alternative_value"
                elif text.startswith("static_comparator ="):
                    stage = "recourse_static"
                elif text.startswith("adaptive ="):
                    stage = "recourse_adaptive"
                elif text.startswith("perfect ="):
                    stage = "recourse_perfect"
                elif text.startswith("candidates[name] ="):
                    stage = "cadence_candidate"
                return stage, func, line
            frame = frame.f_back
        return "outside_planner", "", 0

    def dump(self, m, objective, stage: str, phase: str, seconds: float, seed, options) -> None:
        """Write the model as HiGHS sees it (cost = the phase objective) plus the solve's settings."""
        import highspy
        import numpy as np
        assert self.dump_dir is not None
        self.dump_dir.mkdir(parents=True, exist_ok=True)
        index = len(self.solves)
        stem = self.dump_dir / f"{index:03d}_{stage}_{phase}"
        matrix = m.matrix()
        h = highspy.Highs()
        h.setOptionValue("output_flag", False)
        lp = highspy.HighsLp()
        lp.num_col_, lp.num_row_ = len(m.names), len(m.rows)
        lp.col_cost_ = np.asarray(m.cost if objective is None else objective, dtype=float)
        lp.col_lower_ = np.asarray(m.lower, dtype=float)
        lp.col_upper_ = np.asarray(m.upper, dtype=float)
        lp.row_lower_ = np.asarray(m.lo, dtype=float)
        lp.row_upper_ = np.asarray(m.hi, dtype=float)
        lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
        lp.a_matrix_.start_ = np.asarray(matrix.indptr, dtype=np.int32)
        lp.a_matrix_.index_ = np.asarray(matrix.indices, dtype=np.int32)
        lp.a_matrix_.value_ = np.asarray(matrix.data, dtype=float)
        lp.integrality_ = [highspy.HighsVarType.kInteger if i else highspy.HighsVarType.kContinuous for i in m.integer]
        h.passModel(lp)
        h.writeModel(str(stem) + ".mps")
        meta = {"stage": stage, "phase": phase, "budget_s": seconds, "seeded": seed is not None, "options": options,
                "cols": len(m.names), "rows": len(m.rows), "integer": int(sum(m.integer)),
                "names": [str(n) for n in m.names]}
        (stem.with_suffix(".json")).write_text(json.dumps(meta))
        if seed is not None:
            np.save(str(stem) + "_seed.npy", np.asarray(seed, dtype=float))

    def add_stage(self, name: str, seconds: float) -> None:
        self.stages_s[name] = self.stages_s.get(name, 0.) + seconds
        self.stage_calls[name] = self.stage_calls.get(name, 0) + 1

    def install(self) -> None:
        import zaad.full.model as model
        import zaad.full.planner as planner
        import zaad.full.settlement as settlement
        rec = self

        orig_model_solve = model.Linear.solve

        def model_solve(self_, seconds, objective=None, solver="highs", mip_gap=1e-6, seed=None, options=None):
            t, c = time.perf_counter(), time.process_time()
            stage, func, line = rec.stage_of()
            # lexicographic phase: a solve with a service objective is phase one; the next solve of
            # the same model without one is phase two (the cost objective under the service optimum)
            key = (id(self_), len(self_.rows))
            if objective is not None:
                phase = "lex1"
                rec._last_lex = (id(self_), len(self_.rows) + 1)
            elif rec._last_lex is not None and rec._last_lex == key:
                phase = "lex2"
                rec._last_lex = None
            else:
                phase = "single"
                rec._last_lex = None
            if rec.dump_dir is not None:
                rec.dump(self_, objective, stage, phase, seconds, seed, options)
            if rec.structure_only:
                from types import SimpleNamespace
                result, residual = SimpleNamespace(x=None, fun=None, status=1, message="structure-only: not solved",
                                                   mip_gap=None, mip_dual_bound=None, mip_node_count=0), float("inf")
            else:
                result, residual = orig_model_solve(self_, seconds, objective, solver, mip_gap, seed, options)
            rec.solves.append({
                "stage": stage, "planner_function": func, "planner_line": line, "phase": phase,
                "service_first": rec._current_kw.get("service_first"), "worlds": rec._current_kw.get("worlds"),
                "t_offset_s": round(t - rec.t_start, 3), "objective": getattr(result, "fun", None),
                "cols": len(self_.names), "rows": len(self_.rows),
                "integer": int(sum(1 for i in self_.integer if i)),
                "binary": int(sum(1 for i, lo, hi in zip(self_.integer, self_.lower, self_.upper) if i and lo == 0 and hi == 1)),
                "nnz": int(sum(len(r) for r in self_.rows)),
                "budget_s": float(seconds), "wall_s": time.perf_counter() - t, "cpu_s": time.process_time() - c,
                "highs_status": int(result.status), "warm_seed": seed is not None,
                "route": "highspy" if (solver == "highspy" or seed is not None) else solver,
                "options": dict(options) if options else None,
                "mip_gap": getattr(result, "mip_gap", None), "nodes": getattr(result, "mip_node_count", None),
            })
            return result, residual

        model.Linear.solve = model_solve
        self._orig.append((model.Linear, "solve", orig_model_solve))

        orig_highspy = model.Linear._highspy_solve

        def highspy_solve(self_, *a, **k):
            t = time.perf_counter()
            try:
                return orig_highspy(self_, *a, **k)
            finally:
                rec.solver_core_s += time.perf_counter() - t

        model.Linear._highspy_solve = highspy_solve
        self._orig.append((model.Linear, "_highspy_solve", orig_highspy))

        orig_milp = model.milp

        def milp(*a, **k):
            t = time.perf_counter()
            try:
                return orig_milp(*a, **k)
            finally:
                rec.solver_core_s += time.perf_counter() - t

        model.milp = milp
        self._orig.append((model, "milp", orig_milp))

        orig_solve = model.solve

        def solve(req, worlds, **kw):
            t, n0 = time.perf_counter(), len(rec.solves)
            rec._current_kw = {"service_first": kw.get("service_first"), "worlds": len(worlds)}
            try:
                out = orig_solve(req, worlds, **kw)
            finally:
                rec._current_kw = {}
            wall = time.perf_counter() - t
            mine = rec.solves[n0:]
            stage = mine[0]["stage"] if mine else "no_milp"
            rec.add_stage("build+milp:" + stage, wall)
            rec.candidates.append({
                "index": len(rec.candidates), "stage": stage, "status": out.status, "wall_s": wall,
                "milp_wall_s": sum(s["wall_s"] for s in mine), "build_and_settle_s": wall - sum(s["wall_s"] for s in mine),
                "milps": len(mine), "worlds": len(worlds), "variables": out.variables, "constraints": out.constraints,
                "solve_seconds_reported": out.solve_seconds, "gap": out.gap,
                "adaptive_nodes": kw.get("nodes") is not None, "fixed": kw.get("fixed") is not None,
                "service_first": kw.get("service_first"), "cvar_weight": kw.get("cvar_weight", 0.),
                "warm_start": (out.warm_start or {}).get("outcome") if getattr(out, "warm_start", None) else None,
            })
            return out

        model.solve = solve
        planner.solve = solve
        self._orig.append((model, "solve", orig_solve))
        self._orig.append((planner, "solve", orig_solve))

        orig_settle = settlement.settle

        def settle(*a, **k):
            t = time.perf_counter()
            try:
                return orig_settle(*a, **k)
            finally:
                rec.settle_s += time.perf_counter() - t
                rec.settle_calls += 1

        settlement.settle = settle
        planner.settle = settle
        self._orig.append((settlement, "settle", orig_settle))
        self._orig.append((planner, "settle", orig_settle))

        # the planner's other stages, timed by name where the planner binds them as module globals
        for name in ("forecast_all", "supply_profiles", "protection_profile", "draw", "targets", "screen",
                     "evaluate", "alternative_value", "procurement_timing", "resolve_commitments"):
            fn = getattr(planner, name, None)
            if fn is None or not callable(fn):
                continue

            def timed(*a, _fn=fn, _name=name, **k):
                t = time.perf_counter()
                try:
                    return _fn(*a, **k)
                finally:
                    rec.add_stage(_name, time.perf_counter() - t)

            setattr(planner, name, timed)
            self._orig.append((planner, name, fn))

    def uninstall(self) -> None:
        for obj, name, orig in reversed(self._orig):
            setattr(obj, name, orig)
        self._orig.clear()


def _maxrss_mb() -> float:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / (1024 * 1024) if sys.platform == "darwin" else rss / 1024


def run_one(n: int, vault: str, seconds: float, seed: int, out_dir: Path, label: str = "", dump_mps: Path | None = None,
            overrides: dict | None = None, structure_only: bool = False) -> dict:
    from scripts.setup_db import setup_db
    from scripts.v2_solve_profile import coupling
    from zaad.full.jobs import JobStore, report_json
    from zaad.full.model import solve_budget
    from zaad.full.workspace import to_purchase_plan
    from zaad.meio.planner import plan_network
    from zaad.meio.workspace import build_network_request, to_network_plan

    conn = duckdb.connect(":memory:")
    setup_db(conn)
    t0 = time.perf_counter()
    if vault == "network":
        from scripts.zaad_network_workspace_smoke import make_network_vault
        make_network_vault(conn, seed=seed)
    else:
        from api.routers.intake import load_fmcg_sample_into
        load_fmcg_sample_into(conn, seed=seed)
    t_vault = time.perf_counter() - t0

    phases = dict(sourcing=True, recourse=True, atp=True, commitments=True)
    t0 = time.perf_counter()
    full, _ = build_network_request(conn, "bench", horizon=12, service_target=.95, max_solve_seconds=seconds, **phases)
    t_full_read = time.perf_counter() - t0
    ranked = rank_products(full)
    chosen = ranked[:n]
    t0 = time.perf_counter()
    request, build = build_network_request(conn, "bench", horizon=12, service_target=.95, max_solve_seconds=seconds,
                                           skus=chosen, **phases)
    t_build = time.perf_counter() - t0
    if overrides:
        # experiment: a request setting changed from outside (e.g. warm_start=false); recorded in the output
        request = request.model_copy(update=overrides)

    rec = Recorder()
    rec.structure_only = structure_only
    if dump_mps is not None:
        rec.dump_dir = dump_mps / f"{vault}_{n:02d}"
    rec.install()
    cpu0, t0 = time.process_time(), time.perf_counter()
    rec.t_start = t0
    try:
        report = plan_network(request)
    finally:
        rec.uninstall()
    t_plan, cpu_plan = time.perf_counter() - t0, time.process_time() - cpu0

    t0 = time.perf_counter()
    if request.transfers or len(request.locations) > 1:
        shape = to_network_plan(request, report, build, commit_window_weeks=4, run_id=str(report.get("input_fingerprint", "")))
    else:
        shape = to_purchase_plan(request, report, build, commit_window_weeks=4, run_id=str(report.get("input_fingerprint", "")))
    t_shape = time.perf_counter() - t0
    shape_bytes = len(json.dumps(shape, default=str))
    t0 = time.perf_counter()
    serialised = report_json(report)
    t_serialise = time.perf_counter() - t0
    with tempfile.TemporaryDirectory() as tmp:
        store = JobStore(Path(tmp) / "jobs.sqlite")
        t0 = time.perf_counter()
        identity = store.create("bench", request, 450.)
        store.update(identity, status="DONE", report_json=serialised)
        t_persist = time.perf_counter() - t0

    quality = report.get("solve_quality") or {}
    milp_wall = sum(s["wall_s"] for s in rec.solves)
    by_stage: dict[str, dict] = {}
    for s_ in rec.solves:
        row = by_stage.setdefault(s_["stage"], {"milps": 0, "wall_s": 0., "cpu_s": 0., "lex1_s": 0., "lex2_s": 0., "time_limited": 0})
        row["milps"] += 1
        row["wall_s"] += s_["wall_s"]
        row["cpu_s"] += s_["cpu_s"]
        if s_["phase"] == "lex1":
            row["lex1_s"] += s_["wall_s"]
        elif s_["phase"] == "lex2":
            row["lex2_s"] += s_["wall_s"]
        row["time_limited"] += int(s_["highs_status"] == 1)
    for row in by_stage.values():
        for k in ("wall_s", "cpu_s", "lex1_s", "lex2_s"):
            row[k] = round(row[k], 3)
        row["share_of_plan"] = round(row["wall_s"] / t_plan, 4) if t_plan else None
    result = {
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "host": {"platform": platform.platform(), "machine": platform.machine(), "cpus": os.cpu_count(),
                 "python": platform.python_version(), "fly_machine": os.environ.get("FLY_MACHINE_ID"),
                 "fly_vm_size": os.environ.get("FLY_VM_SIZE") or os.environ.get("FLY_VM_MEMORY_MB")},
        "vault": vault, "seed": seed, "max_solve_seconds": seconds, "request_overrides": overrides or {}, "structure_only": structure_only,
        "products": {"catalogue": len(full.skus), "requested": n, "planned": len(request.skus), "chosen": chosen},
        "request": {
            "horizon": request.horizon, "scenarios": request.scenarios, "skus": len(request.skus),
            "sources": len(request.sources), "services": len(request.services), "locations": len(request.locations),
            "pipeline_open_pos": len(request.pipeline), "transfers": len(request.transfers), "stock_rows": len(request.stock),
            "phase_blocks": {p: getattr(request, p, None) is not None for p in ("sourcing", "recourse", "atp", "commitments")},
            "network": len(request.locations) > 1 or bool(request.transfers),
            "per_solve_budget_s": solve_budget(request), "solver": request.solver, "solver_mip_gap": request.solver_mip_gap,
            "job_timeout_s": min(1800., max(30., request.max_solve_seconds * (10 + len(request.services)) * 1.5)),
        },
        "timings_s": {
            "vault_load": round(t_vault, 3), "full_workspace_read": round(t_full_read, 3), "request_build": round(t_build, 3),
            "plan_wall": round(t_plan, 3), "plan_cpu": round(cpu_plan, 3),
            "milp_wall_total": round(milp_wall, 3), "solver_core_total": round(rec.solver_core_s, 3),
            "candidate_build_and_settle_total": round(sum(c["build_and_settle_s"] for c in rec.candidates), 3),
            "settlement_total": round(rec.settle_s, 3), "settlement_calls": rec.settle_calls,
            "plan_shape": round(t_shape, 3), "serialise": round(t_serialise, 3), "persist": round(t_persist, 3),
            "end_to_end": round(t_full_read + t_build + t_plan + t_shape + t_serialise + t_persist, 3),
        },
        "shares": {
            "solver_core_of_plan": round(rec.solver_core_s / t_plan, 4) if t_plan else None,
            "milp_of_plan": round(milp_wall / t_plan, 4) if t_plan else None,
            "cpu_utilisation_of_plan": round(cpu_plan / t_plan, 3) if t_plan else None,
        },
        "memory_mb_high_water": round(_maxrss_mb(), 1),
        "report_bytes": len(serialised), "plan_shape_bytes": shape_bytes,
        "status": report.get("status"),
        "solve_quality": {k: v for k, v in quality.items() if k != "candidates"},
        "orchestration": {k: v for k, v in (report.get("orchestration") or {}).items()
                          if k in ("screen_state", "state", "requested", "skipped", "not_applicable", "escalated", "lean_review", "lean_profile")},
        "candidates_reported": {name: {"status": c.get("status"), "solve_seconds": c.get("solve_seconds"),
                                        "achieved_gap": c.get("achieved_gap"), "nodes": c.get("nodes")}
                                for name, c in (quality.get("candidates") or {}).items()},
        "milps": rec.solves,
        "milp_by_stage": by_stage,
        "planner_stages_s": {k: round(v, 3) for k, v in sorted(rec.stages_s.items())},
        "planner_stage_calls": dict(sorted(rec.stage_calls.items())),
        "milp_summary": {
            "count": len(rec.solves), "max_cols": max((s["cols"] for s in rec.solves), default=0),
            "max_rows": max((s["rows"] for s in rec.solves), default=0), "max_integer": max((s["integer"] for s in rec.solves), default=0),
            "max_binary": max((s["binary"] for s in rec.solves), default=0), "max_nnz": max((s["nnz"] for s in rec.solves), default=0),
            "time_limited": sum(1 for s in rec.solves if s["highs_status"] == 1),
            "at_budget": sum(1 for s in rec.solves if s["wall_s"] >= .95 * s["budget_s"]),
            "budget_total_s": round(sum(s["budget_s"] for s in rec.solves), 1),
        },
        "candidate_solves": rec.candidates,
        "coupling": coupling(request),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / (f"bench_{vault}_{n:02d}" + (f"_{label}" if label else "") + ".json")
    path.write_text(json.dumps(result, indent=2, default=str))
    # the full report and the plan shape, for decision-identity comparison between runs
    (out_dir / (f"report_{vault}_{n:02d}" + (f"_{label}" if label else "") + ".json")).write_text(serialised)
    (out_dir / (f"plan_{vault}_{n:02d}" + (f"_{label}" if label else "") + ".json")).write_text(json.dumps(shape, indent=1, default=str))
    t = result["timings_s"]
    print(f"{vault} n={n}: plan {t['plan_wall']:.1f}s (solver core {t['solver_core_total']:.1f}s = "
          f"{100 * (result['shares']['solver_core_of_plan'] or 0):.0f}%), {len(rec.solves)} MILPs, "
          f"max {result['milp_summary']['max_cols']} cols / {result['milp_summary']['max_rows']} rows / "
          f"{result['milp_summary']['max_integer']} int, time-limited {result['milp_summary']['time_limited']}, "
          f"cpu {result['shares']['cpu_utilisation_of_plan']}x, rss {result['memory_mb_high_water']} MB, "
          f"status {report.get('status')}, timeout {result['request']['job_timeout_s']:.0f}s -> {path}", flush=True)
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--products", default="1,2,5,8,10")
    ap.add_argument("--vault", choices=("sample", "network"), default="sample")
    ap.add_argument("--seconds", type=float, default=15.)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="artifacts/solve_benchmark")
    ap.add_argument("--label", default="", help="suffix for the output file names (e.g. baseline, exp1)")
    ap.add_argument("--dump-mps", default=None, help="directory: write every MILP the planner solves as MPS + settings")
    ap.add_argument("--request-override", action="append", default=[], metavar="KEY=JSON",
                    help="experiment: override a Request field, e.g. warm_start=false (JSON value)")
    ap.add_argument("--structure-only", action="store_true", help="build every model, solve none: dimensions only")
    args = ap.parse_args()
    overrides = {}
    for item in args.request_override:
        key, _, value = item.partition("=")
        overrides[key] = json.loads(value)
    for n in (int(x) for x in args.products.split(",") if x.strip()):
        run_one(n, args.vault, args.seconds, args.seed, Path(args.out), label=args.label,
                dump_mps=Path(args.dump_mps) if args.dump_mps else None, overrides=overrides or None,
                structure_only=args.structure_only)


if __name__ == "__main__":
    main()
