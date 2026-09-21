"""Diagnostic V3.1 — profile the rolling optimizer replay end to end, from outside the optimizer.

Runs `zaad.full.historical.run_historical_replay` on a synthetic vault with the benchmark Recorder
(`scripts.production_solve_benchmark.Recorder`) installed, so every MILP the planner solves during the
ZAAD leg is attributed (planner stage, lexicographic phase, dimensions, integer columns, non-zeros,
nodes, gap, wall and CPU time) and every non-solver stage of the replay is timed: truth reconstruction,
request construction, the actual-orders and rule legs, per-review snapshot construction, forecasting /
statistics, world draws, settlement. Nothing under zaad/ runs differently.

Usage:
  python -m scripts.replay_profile --vault demo --skus 5,10 --reviews 4 [--seconds 15] [--fefo network|all|certified]
                                   [--budget 3600] [--out artifacts/replay_profile] [--label NAME] [--seed 41001]
The demo vault is the synthetic DEMO company (36 products); the sample vault is the synthetic FMCG
distributor (150 products). Neither is customer data.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from scripts.production_solve_benchmark import Recorder


def _rss_mb() -> float:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / (1024 * 1024) if sys.platform == "darwin" else rss / 1024


def make_vault(kind: str, seed: int):
    from scripts.setup_db import setup_db
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    if kind == "demo":
        from synthetic.fmcg.demo_company import load_demo_company_into
        load_demo_company_into(conn, "profile", seed=seed)
    else:
        from api.routers.intake import load_fmcg_sample_into
        load_fmcg_sample_into(conn, seed=seed)
    return conn


class ReplayTimer:
    """Times the replay's own stages by wrapping the module-level names `historical.py` binds."""

    def __init__(self) -> None:
        self.stages: dict[str, float] = {}
        self.calls: dict[str, int] = {}
        self.review_walls: list[dict] = []
        self._orig: list[tuple] = []

    def add(self, name: str, seconds: float) -> None:
        self.stages[name] = self.stages.get(name, 0.) + seconds
        self.calls[name] = self.calls.get(name, 0) + 1

    def install(self) -> None:
        import zaad.full.historical as H
        import zaad.full.replay as R
        import zaad.full.planner as P
        timer = self
        for module, name in ((H, "build_truth"), (H, "build_request"), (H, "actual_orders_by_review"), (H, "attest"),
                             (R, "forecast_all"), (R, "settle"), (R, "Request"), (P, "forecast_all"), (P, "supply_profiles"),
                             (P, "protection_profile"), (P, "draw"), (P, "targets"), (P, "screen"), (P, "evaluate")):
            fn = getattr(module, name, None)
            if fn is None:
                continue
            if name == "Request":
                validate = fn.model_validate

                def timed_validate(*a, _fn=validate, **k):
                    t = time.perf_counter()
                    try:
                        return _fn(*a, **k)
                    finally:
                        timer.add("request_validate", time.perf_counter() - t)
                self._orig.append((fn, "model_validate", validate))
                fn.model_validate = timed_validate     # type: ignore[method-assign]
                continue

            def timed(*a, _fn=fn, _name=f"{module.__name__.rsplit('.', 1)[-1]}.{name}", **k):
                t = time.perf_counter()
                try:
                    return _fn(*a, **k)
                finally:
                    timer.add(_name, time.perf_counter() - t)
            setattr(module, name, timed)
            self._orig.append((module, name, fn))
        # the replay legs themselves
        orig_replay = H.replay

        def timed_replay(initial, truth, reviews, method, *a, **k):
            t = time.perf_counter()
            try:
                return orig_replay(initial, truth, reviews, method, *a, **k)
            finally:
                timer.add("replay_leg:" + ("zaad" if method.endswith(":zaad") else "zaad_recorded" if method.endswith(":zaad_recorded")
                                           else "actual" if method.endswith(":actual") else method), time.perf_counter() - t)
        H.replay = timed_replay
        self._orig.append((H, "replay", orig_replay))
        # per-review wall of the ZAAD leg's planner call, from the leg method itself
        orig_zaad = H._LegMethods.zaad

        def timed_zaad(self_, req):
            t, c = time.perf_counter(), time.process_time()
            out = orig_zaad(self_, req)
            timer.review_walls.append({"as_of": req.as_of.isoformat(), "plan_wall_s": time.perf_counter() - t,
                                       "plan_cpu_s": time.process_time() - c, "status": out.warnings[0] if out.warnings else out.status,
                                       "skus": len(req.skus), "sources": len(req.sources), "history_periods": len({r.period for r in req.history}),
                                       "rss_mb": _rss_mb()})
            return out
        H._LegMethods.zaad = timed_zaad    # type: ignore[method-assign]
        self._orig.append((H._LegMethods, "zaad", orig_zaad))

    def uninstall(self) -> None:
        for obj, name, orig in reversed(self._orig):
            setattr(obj, name, orig)
        self._orig.clear()


def run_one(conn, n: int, reviews: int, seconds: float, fefo: str, budget: float, seed: int, out_dir: Path, label: str, vault: str) -> dict:
    import zaad.full.historical as H
    from zaad.full import workspace as W
    # the replay's requests carry the diagnostic's own solve cap; the FEFO scope is the experiment variable
    orig_build = W.build_request

    def build_request(conn_, operator_id, **kw):
        req, build = orig_build(conn_, operator_id, max_solve_seconds=seconds, **kw)
        if fefo != "network":
            req = req.model_copy(update={"fefo_symmetry_scope": fefo})
        return req, build
    H.build_request = build_request
    rec, timer = Recorder(), ReplayTimer()
    rec.install()
    timer.install()
    t0, c0 = time.perf_counter(), time.process_time()
    rec.t_start = t0
    try:
        out = H.run_historical_replay(conn, "profile", skus=n, reviews=reviews, horizon=12, budget_s=budget, seed=seed)
    finally:
        timer.uninstall()
        rec.uninstall()
        H.build_request = orig_build
    wall, cpu = time.perf_counter() - t0, time.process_time() - c0
    solves = rec.solves
    milp_wall = sum(s["wall_s"] for s in solves)
    by_stage: dict[str, dict] = {}
    for s in solves:
        row = by_stage.setdefault(s["stage"], {"milps": 0, "wall_s": 0., "lex1_s": 0., "lex2_s": 0., "time_limited": 0, "max_integer": 0})
        row["milps"] += 1
        row["wall_s"] += s["wall_s"]
        row["lex1_s" if s["phase"] == "lex1" else "lex2_s" if s["phase"] == "lex2" else "wall_s"] += 0. if s["phase"] == "single" else s["wall_s"]
        row["time_limited"] += int(s["highs_status"] == 1)
        row["max_integer"] = max(row["max_integer"], s["integer"])
    for row in by_stage.values():
        for k in ("wall_s", "lex1_s", "lex2_s"):
            row[k] = round(row[k], 3)
    walls = sorted(r["plan_wall_s"] for r in timer.review_walls)

    def pct(p: float) -> float | None:
        return round(walls[min(len(walls) - 1, int(p * len(walls)))], 2) if walls else None
    zaad_log = out.get("zaad_reviews") or []
    result = {
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "host": {"platform": platform.platform(), "machine": platform.machine(), "python": platform.python_version(), "cpus": os.cpu_count()},
        "vault": vault, "skus_requested": n, "reviews_requested": reviews, "max_solve_seconds": seconds, "fefo_symmetry_scope": fefo, "seed": seed,
        "replay": {"status": out.get("status"), "reason": out.get("reason"), "coverage": out.get("coverage"), "scope": {k: v for k, v in (out.get("scope") or {}).items() if k != "skus"},
                   "performance": out.get("performance"), "confidence": (out.get("confidence") or {}).get("level")},
        "zaad_reviews": [{k: e.get(k) for k in ("review", "as_of", "status", "selected_policy", "fallback_to_rule", "solve_seconds")} for e in zaad_log],
        "timings_s": {"total_wall": round(wall, 3), "total_cpu": round(cpu, 3), "milp_wall_total": round(milp_wall, 3),
                      "solver_core_total": round(rec.solver_core_s, 3), "settlement_total": round(rec.settle_s, 3), "settlement_calls": rec.settle_calls,
                      "non_solver_wall": round(wall - milp_wall, 3),
                      **{k: round(v, 3) for k, v in sorted(timer.stages.items())}},
        "stage_calls": dict(sorted(timer.calls.items())),
        "shares": {"milp_of_total": round(milp_wall / wall, 4) if wall else None, "cpu_utilisation": round(cpu / wall, 3) if wall else None},
        "per_review_plan_wall_s": {"n": len(walls), "min": pct(0.), "median": pct(.5), "p90": pct(.9), "max": pct(1.), "mean": round(sum(walls) / len(walls), 2) if walls else None},
        "review_walls": timer.review_walls,
        "milp_by_stage": by_stage,
        "milp_summary": {"count": len(solves), "time_limited": sum(1 for s in solves if s["highs_status"] == 1),
                         "max_cols": max((s["cols"] for s in solves), default=0), "max_rows": max((s["rows"] for s in solves), default=0),
                         "max_integer": max((s["integer"] for s in solves), default=0), "max_nnz": max((s["nnz"] for s in solves), default=0),
                         "budget_total_s": round(sum(s["budget_s"] for s in solves), 1)},
        "milps": solves,
        "memory_mb_high_water": round(_rss_mb(), 1),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / (f"replay_{vault}_{n:02d}x{reviews:02d}_{fefo}" + (f"_{label}" if label else "") + ".json")
    path.write_text(json.dumps(result, indent=1, default=str))
    (out_dir / (f"result_{vault}_{n:02d}x{reviews:02d}_{fefo}" + (f"_{label}" if label else "") + ".json")).write_text(json.dumps(out, indent=1, default=str))
    t = result["timings_s"]
    print(f"{vault} skus={n} reviews={reviews} fefo={fefo}: total {t['total_wall']:.1f}s, MILP {t['milp_wall_total']:.1f}s "
          f"({100 * (result['shares']['milp_of_total'] or 0):.0f}%), non-solver {t['non_solver_wall']:.1f}s, {len(solves)} MILPs, "
          f"time-limited {result['milp_summary']['time_limited']}, plan wall median {result['per_review_plan_wall_s']['median']} "
          f"p90 {result['per_review_plan_wall_s']['p90']} max {result['per_review_plan_wall_s']['max']}, "
          f"coverage {(out.get('coverage') or {}).get('reviews_completed')}/{reviews}, rss {result['memory_mb_high_water']} MB -> {path}", flush=True)
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", choices=("demo", "sample"), default="demo")
    ap.add_argument("--skus", default="5")
    ap.add_argument("--reviews", type=int, default=4)
    ap.add_argument("--seconds", type=float, default=15.)
    ap.add_argument("--fefo", choices=("network", "all", "certified"), default="network")
    ap.add_argument("--budget", type=float, default=36000.)
    ap.add_argument("--seed", type=int, default=41001)
    ap.add_argument("--out", default="artifacts/replay_profile")
    ap.add_argument("--label", default="")
    args = ap.parse_args()
    conn = make_vault(args.vault, 7)
    for n in [int(x) for x in args.skus.split(",") if x]:
        run_one(conn, n, args.reviews, args.seconds, args.fefo, args.budget, args.seed, Path(args.out), args.label, args.vault)


if __name__ == "__main__":
    main()
