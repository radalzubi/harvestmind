"""Frontier oracle profile and old-vs-new equivalence (frontier decomposition pass).

Builds the workspace request the product builds (sample or demo vault, STUDY-SELECTION scope of N products,
optionally the genuinely coupled stress economics of `scripts.formulation_audit`) and either

  --oracle   runs the per-service frontier oracle alone in the chosen mode (`monolithic` = the released loop,
             one full build and phase-one solve per service; `component` = one build, the exact connected
             components, one solve per unproven service) with the benchmark Recorder installed, and writes
             every frontier solve (dimensions, status, gap, nodes, wall), the values per service, the
             partition (components, sizes) and the peak RSS; or
  --plan     runs the whole released planner (`zaad.full.planner.plan`) in the chosen mode and writes the
             report (for `scripts.plan_report_compare`), the frontier's share of the plan and the same solve
             attribution.

  --compare A.json B.json   compares two outputs: service ids, every frontier value (exact and at 1e-9),
             statuses, and - for plan outputs - the reports' decision identity (`plan_report_compare`) and
             the executed orders. Exit 1 on any difference that is not a time-limited old solve.

Nothing under zaad/ runs differently: the mode is the planner's own `FRONTIER_MODE` switch.

Usage: python -m scripts.frontier_profile --vault sample --products 5,10,25 --mode component --oracle [--stress]
                                          [--seconds 15] [--seed 41001] [--out DIR] [--label NAME]
       python -m scripts.frontier_profile --compare A.json B.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import platform
import resource
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _rss_mb() -> float:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / (1024 * 1024) if sys.platform == "darwin" else rss / 1024


def _pct(values: list[float], p: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    k = min(len(s) - 1, max(0, math.ceil(p * len(s)) - 1))
    return s[k]


def _summary(solves: list[dict]) -> dict:
    walls = [s["wall_s"] for s in solves]
    return {"count": len(solves), "total_s": round(sum(walls), 3), "median_s": round(statistics.median(walls), 3) if walls else None,
            "p90_s": round(_pct(walls, .9), 3) if walls else None, "max_s": round(max(walls), 3) if walls else None,
            "time_limited": sum(1 for s in solves if s["highs_status"] == 1),
            "statuses": {k: sum(1 for s in solves if s["highs_status"] == k) for k in sorted({s["highs_status"] for s in solves})},
            "max_cols": max((s["cols"] for s in solves), default=0), "max_rows": max((s["rows"] for s in solves), default=0),
            "max_integer": max((s["integer"] for s in solves), default=0), "max_nnz": max((s["nnz"] for s in solves), default=0),
            "median_cols": statistics.median([s["cols"] for s in solves]) if solves else None,
            "nodes_total": sum(int(s["nodes"] or 0) for s in solves),
            "gap_max": max((s["mip_gap"] for s in solves if s["mip_gap"] is not None), default=None),
            "cpu_s": round(sum(s["cpu_s"] for s in solves), 3)}


def build(kind: str, n: int, seconds: float, stress: bool, seed: int):
    import pandas as pd
    import zaad.full.historical as H
    from scripts.formulation_audit import make_vault
    from zaad.full.workspace import build_request
    conn, as_of = make_vault(kind, 7, stress)
    probe, _ = build_request(conn, "frontier", as_of=as_of, horizon=12)
    sel = H.select_scope(conn, probe, n, origin=pd.Timestamp(as_of.replace(tzinfo=None)), periods=19)
    req, _ = build_request(conn, "frontier", as_of=as_of, horizon=12, skus=sel["skus"], seed=seed, max_solve_seconds=seconds)
    conn.close()
    return req


def run(kind: str, n: int, seconds: float, stress: bool, mode: str, oracle_only: bool, out_dir: Path, label: str, seed: int) -> dict:
    from scripts.production_solve_benchmark import Recorder
    import zaad.full.planner as planner
    from zaad.full.model import solve, solve_budget
    from zaad.full.worlds import draw
    planner.FRONTIER_MODE = mode
    req = build(kind, n, seconds, stress, seed)
    rec = Recorder()
    rec.install()
    t0, c0 = time.perf_counter(), time.process_time()
    rec.t_start = t0
    values: dict[str, float | None] = {}
    statuses: dict[str, str] = {}
    telemetry: dict | None = None
    report: dict | None = None
    t_build = 0.
    try:
        if oracle_only:
            det = draw(req, req.seed, 1, deterministic=True)
            ids = tuple(s.id for s in req.services)
            if mode == "component":
                oracle = solve(req, det, service_first="all", service_only=True, frontier_services=ids)   # no witnesses: every service solved
                values = {s: oracle.projected_service.get(s) for s in ids}
                statuses = {s["service"]: s["status"] for s in oracle.frontier["solves"] if s["service"]}
                telemetry = oracle.frontier
                t_build = oracle.solve_seconds - oracle.frontier["solve_seconds"] - oracle.frontier["extract_seconds"] - oracle.frontier["partition_seconds"]
            else:
                for s in ids:
                    t1 = time.perf_counter()
                    one = solve(req, det, service_first=s, service_only=True)
                    values[s] = one.projected_service.get(s)
                    statuses[s] = one.status
                    t_build += (time.perf_counter() - t1) - (rec.solves[-1]["wall_s"] if rec.solves else 0.)
        else:
            report = planner.plan(req)
            values = {r["service"]: r["best_modeled_individual_unit_fill"] for r in report["service_frontier"]}
            telemetry = (report.get("orchestration") or {}).get("frontier")
            frontier_rows = [s_ for s_ in rec.solves if s_["stage"] == "service_frontier"]
            if mode == "monolithic" and len(frontier_rows) == len(req.services):
                # the released loop: one solve per service in request order; its HiGHS status says whether the
                # number is a proven optimum or an incumbent at the cap
                statuses = {s_.id: {0: "OPTIMAL", 1: "FEASIBLE_TIME_LIMIT", 2: "INFEASIBLE"}.get(row["highs_status"], "ERROR")
                            for s_, row in zip(req.services, frontier_rows)}
            elif mode == "component":
                statuses = {s_: "OPTIMAL" for s_ in (telemetry or {}).get("skipped_proven", [])}
    finally:
        rec.uninstall()
    wall, cpu = time.perf_counter() - t0, time.process_time() - c0
    frontier_solves = [s for s in rec.solves if s["stage"] == "service_frontier" or oracle_only]
    out = {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "host": platform.platform(), "python": platform.python_version(),
           "vault": kind, "products": n, "stress": stress, "mode": mode, "oracle_only": oracle_only, "seconds": seconds, "seed": seed,
           "request": {"skus": len(req.skus), "services": len(req.services), "sources": len(req.sources), "supplier_terms": len(req.supplier_terms),
                       "opening_cash": req.liquidity.opening_cash, "capacity_volume": [loc.capacity_volume for loc in req.locations],
                       "budget_s": solve_budget(req), "solver": req.solver},
           "wall_s": round(wall, 3), "cpu_s": round(cpu, 3), "rss_mb": round(_rss_mb(), 1),
           "frontier": {"values": values, "statuses": statuses, "summary": _summary(frontier_solves),
                        "build_s_outside_solves": round(t_build, 3), "share_of_wall": round(sum(s["wall_s"] for s in frontier_solves) / wall, 4) if wall else None,
                        "telemetry": ({k: v for k, v in telemetry.items() if k != "solves"} if telemetry else None),
                        "solves": frontier_solves},
           "plan": ({"status": report["status"], "selected_policy": report["selected_policy"], "wall_s": round(wall, 3),
                     "milps": len(rec.solves), "time_limited": sum(1 for s in rec.solves if s["highs_status"] == 1),
                     "milp_by_stage": _by_stage(rec.solves)} if report is not None else None)}
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"frontier_{kind}_{n:03d}_{mode}{'_stress' if stress else ''}{'_oracle' if oracle_only else '_plan'}{('_' + label) if label else ''}"
    (out_dir / (stem + ".json")).write_text(json.dumps(out, indent=1, default=str))
    if report is not None:
        from zaad.full.jobs import report_json
        (out_dir / (stem + "_report.json")).write_text(report_json(report))
    f = out["frontier"]["summary"]
    print(f"{kind} n={n} {mode}{' stress' if stress else ''} {'oracle' if oracle_only else 'plan'}: wall {wall:.1f}s, frontier {f['count']} solves "
          f"{f['total_s']:.1f}s (median {f['median_s']}, p90 {f['p90_s']}, max {f['max_s']}, TL {f['time_limited']}), "
          f"share {out['frontier']['share_of_wall']}, max cols {f['max_cols']}, rss {out['rss_mb']} MB"
          + (f", components {telemetry['components']} largest {telemetry.get('largest_component_columns')} skipped {len(telemetry.get('skipped_proven', []))}" if telemetry else "")
          + (f", plan {report['status']}" if report is not None else "") + f" -> {out_dir / (stem + '.json')}", flush=True)
    return out


def _by_stage(solves: list[dict]) -> dict:
    by: dict[str, dict] = {}
    for s in solves:
        row = by.setdefault(s["stage"], {"milps": 0, "wall_s": 0., "time_limited": 0})
        row["milps"] += 1
        row["wall_s"] += s["wall_s"]
        row["time_limited"] += int(s["highs_status"] == 1)
    for row in by.values():
        row["wall_s"] = round(row["wall_s"], 3)
    return by


def _actions(report: dict) -> list:
    return sorted((x.get("action"), x.get("sku") or x.get("source"), x.get("period"), round(float(x.get("quantity") or 0), 6)) for x in report.get("actions", []))


def compare(a_path: Path, b_path: Path, tol: float = 1e-9) -> int:
    a, b = json.loads(a_path.read_text()), json.loads(b_path.read_text())
    va, vb = a["frontier"]["values"], b["frontier"]["values"]
    sa, sb = a["frontier"].get("statuses", {}), b["frontier"].get("statuses", {})
    for side, values, statuses in ((a, va, sa), (b, vb, sb)):
        rows = side["frontier"].get("solves") or []
        if not statuses and side["mode"] == "monolithic" and len(rows) == len(values):
            # the released loop: one solve per service in request order (the report rows' order)
            statuses.update({s: {0: "OPTIMAL", 1: "FEASIBLE_TIME_LIMIT", 2: "INFEASIBLE"}.get(r["highs_status"], "ERROR") for s, r in zip(values, rows)})
    problems: list[str] = []
    explained: list[str] = []
    if set(va) != set(vb):
        problems.append(f"service ids differ: {sorted(set(va) ^ set(vb))}")
    exact = within = 0
    for s in sorted(set(va) & set(vb)):
        x, y = va[s], vb[s]
        if x == y:
            exact += 1
            continue
        if x is not None and y is not None and abs(x - y) <= tol:
            within += 1
            continue
        old_tl = sa.get(s) in ("FEASIBLE_TIME_LIMIT", "NO_FEASIBLE_SOLUTION")
        msg = f"{s}: A {x} ({sa.get(s)}) vs B {y} ({sb.get(s)})"
        (explained if old_tl and (y is None or x is None or y >= x - tol) else problems).append(msg)
    out = {"services": len(set(va) & set(vb)), "exact": exact, "within_tolerance": within, "explained_by_old_time_limit": explained, "problems": problems}
    if a.get("plan") and b.get("plan"):
        from scripts.plan_report_compare import compare as report_compare
        ra, rb = json.loads(a_path.with_name(a_path.stem + "_report.json").read_text()), json.loads(b_path.with_name(b_path.stem + "_report.json").read_text())
        diffs = report_compare(ra, rb, 1e-6)
        out["report_differences"] = diffs
        out["decision"] = {"A": (ra["status"], ra["selected_policy"]), "B": (rb["status"], rb["selected_policy"])}
        out["actions_identical"] = _actions(ra) == _actions(rb)
        # report rows that read the frontier of a service whose old solve was time-limited are explained by it
        tl = [s for s in sa if sa[s] in ("FEASIBLE_TIME_LIMIT", "NO_FEASIBLE_SOLUTION")]
        ids = [r["service"] for r in ra.get("service_frontier", [])]
        tl_rows = {f"[{ids.index(s)}]" for s in tl if s in ids}
        for d_ in diffs:
            frontier_field = "service_frontier" in d_ or "best_modeled_individual" in d_ or "unavoidable" in d_ or "classification" in d_
            (explained if frontier_field and any(row in d_ for row in tl_rows) else problems).append(d_)
    print(json.dumps(out, indent=1))
    return 1 if problems else 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", choices=("demo", "sample"), default="sample")
    ap.add_argument("--products", default="5")
    ap.add_argument("--seconds", type=float, default=15.)
    ap.add_argument("--seed", type=int, default=41001)
    ap.add_argument("--stress", action="store_true")
    ap.add_argument("--mode", choices=("component", "monolithic"), default="component")
    ap.add_argument("--oracle", action="store_true", help="the frontier oracle alone (no planner)")
    ap.add_argument("--plan", action="store_true", help="the whole planner")
    ap.add_argument("--out", default="artifacts/frontier_profile")
    ap.add_argument("--label", default="")
    ap.add_argument("--compare", nargs=2, default=None)
    args = ap.parse_args()
    if args.compare:
        sys.exit(compare(Path(args.compare[0]), Path(args.compare[1])))
    for n in [int(x) for x in args.products.split(",")]:
        run(args.vault, n, args.seconds, args.stress, args.mode, not args.plan, Path(args.out), args.label, args.seed)


if __name__ == "__main__":
    main()
