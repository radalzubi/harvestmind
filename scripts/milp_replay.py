"""Replay one MILP the planner solved (an MPS written by `production_solve_benchmark --dump-mps`)
through highspy in isolation, with the solver's log on, so a solve can be studied and solver
settings tried one variable at a time without running the planner. Prints the root LP bound, the
incumbent and bound over time (from the HiGHS log), the final status, gap, nodes and time.

Nothing under zaad/ is used; the model is the exact arrays the planner passed to HiGHS.

Usage: python -m scripts.milp_replay MODEL.mps [--time-limit 60] [--gap 1e-6] [--threads 1]
         [--option presolve=off --option mip_heuristic_effort=0.1 ...] [--seed-npy X_seed.npy]
         [--log FILE] [--json FILE]
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path


def parse_option(text: str) -> tuple[str, object]:
    key, _, value = text.partition("=")
    for cast in (int, float):
        try:
            return key, cast(value)
        except ValueError:
            continue
    if value.lower() in ("true", "false", "on", "off"):
        return key, value.lower()
    return key, value


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--time-limit", type=float, default=60.)
    ap.add_argument("--gap", type=float, default=1e-6)
    ap.add_argument("--threads", type=int, default=None)
    ap.add_argument("--option", action="append", default=[])
    ap.add_argument("--seed-npy", default=None)
    ap.add_argument("--log", default=None)
    ap.add_argument("--json", default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    import highspy
    import numpy as np

    h = highspy.Highs()
    log_path = Path(args.log) if args.log else Path(args.model).with_suffix(".log")
    if log_path.exists():
        log_path.unlink()
    h.setOptionValue("log_file", str(log_path))
    h.setOptionValue("output_flag", True)
    h.setOptionValue("log_to_console", not args.quiet)
    h.setOptionValue("time_limit", float(args.time_limit))
    h.setOptionValue("mip_rel_gap", float(args.gap))
    if args.threads is not None:
        h.setOptionValue("threads", int(args.threads))
    applied = {}
    for text in args.option:
        key, value = parse_option(text)
        h.setOptionValue(key, value)
        applied[key] = value
    h.readModel(args.model)
    if args.seed_npy:
        start = highspy.HighsSolution()
        start.col_value = np.load(args.seed_npy)
        h.setSolution(start)
    t = time.perf_counter()
    h.run()
    wall = time.perf_counter() - t
    info = h.getInfo()
    status = str(h.getModelStatus())
    text = log_path.read_text() if log_path.exists() else ""
    root = None
    for line in text.splitlines():
        m = re.search(r"Dual bound\s+(-?[\d.eE+]+)", line)
        if m and root is None:
            root = float(m.group(1))
    out = {"model": args.model, "status": status, "wall_s": round(wall, 2), "objective": info.objective_function_value,
           "dual_bound": info.mip_dual_bound, "gap": info.mip_gap, "nodes": info.mip_node_count,
           "lp_iterations": info.simplex_iteration_count, "options": applied, "threads": args.threads, "time_limit": args.time_limit,
           "mip_rel_gap": args.gap, "seeded": bool(args.seed_npy), "log": str(log_path)}
    print(json.dumps(out, default=str))
    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
