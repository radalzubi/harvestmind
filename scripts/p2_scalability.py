"""P2 scalability diagnostic: one central and N branches, model dimensions and solve time of the
frozen joint solve (deterministic and three-world stochastic) and of a full `plan_network` review.
A runtime / structural diagnostic, not an economic fixture. Written to
docs/zaad_full/evidence/p2/P2_SCALABILITY.json and .md.

usage: PYTHONPATH=. python3 -m scripts.p2_scalability [--branches 2,5,8] [--max-solve 15]"""
from __future__ import annotations

import argparse
import json
import resource
import time
from pathlib import Path

from zaad.full.model import solve
from zaad.full.worlds import draw
from zaad.meio.fixtures_p2 import p2_request

OUT = Path("docs/zaad_full/evidence/p2")


def rss_mb() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return usage / (1024 * 1024) if usage > 1e7 else usage / 1024     # macOS reports bytes, Linux kilobytes


def run(n: int, max_solve: float) -> dict:
    from zaad.meio.planner import plan_network
    branches = tuple(f"b{i}" for i in range(1, n + 1))
    req = p2_request(branches=branches, demand=100., opening_central=150. * n, opening_branch=150., max_solve_seconds=max_solve)
    out: dict = {"branches": n, "locations": len(req.locations), "lanes": len(req.transfers), "services": len(req.services)}
    for label, worlds in (("deterministic", draw(req, req.seed, 1, deterministic=True)), ("stochastic_3_worlds", draw(req, req.seed, 3))):
        started = time.time()
        sol = solve(req, worlds, service_floor=True)
        out[label] = {"status": sol.status, "variables": sol.variables, "constraints": sol.constraints, "solve_seconds": round(sol.solve_seconds, 1),
                      "wall_seconds": round(time.time() - started, 1), "gap": sol.gap, "worlds": len(worlds)}
    started = time.time()
    rep = plan_network(req)
    o = rep["orchestration"]
    out["plan_network"] = {"status": rep["status"], "state": o["state"], "owner": o["planner_owner"], "milps": o["milps_attempted"],
                           "solver_seconds": round(o["solver_seconds_total"], 1), "wall_seconds": round(time.time() - started, 1),
                           "time_limited": o.get("milps_feasible_time_limited"), "no_feasible": o.get("milps_no_feasible_solution"),
                           "candidates": o["candidates_built"]}
    out["max_rss_mb"] = round(rss_mb(), 0)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--branches", default="2,5,8")
    ap.add_argument("--max-solve", type=float, default=15.)
    a = ap.parse_args()
    rows = []
    for n in [int(x) for x in a.branches.split(",")]:
        row = run(n, a.max_solve)
        rows.append(row)
        print(f"branches {n}: det {row['deterministic']['variables']} vars / {row['deterministic']['constraints']} rows {row['deterministic']['solve_seconds']}s | "
              f"stoch {row['stochastic_3_worlds']['variables']} vars {row['stochastic_3_worlds']['solve_seconds']}s {row['stochastic_3_worlds']['status']} | "
              f"plan {row['plan_network']['wall_seconds']}s milps {row['plan_network']['milps']} state {row['plan_network']['state']} | rss {row['max_rss_mb']} MB", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "P2_SCALABILITY.json").write_text(json.dumps(rows, indent=1))
    lines = ["# P2 scalability diagnostic (1 central + N branches, H = 12, weekly)", "",
             "| branches | locations | lanes | det vars / rows / s | stochastic (3 worlds) vars / rows / s / status | plan_network wall s / MILPs / state | max RSS MB |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        d, s, p = r["deterministic"], r["stochastic_3_worlds"], r["plan_network"]
        lines.append(f"| {r['branches']} | {r['locations']} | {r['lanes']} | {d['variables']} / {d['constraints']} / {d['solve_seconds']} | {s['variables']} / {s['constraints']} / {s['solve_seconds']} / {s['status']} | {p['wall_seconds']} / {p['milps']} / {p['state']} | {r['max_rss_mb']} |")
    (OUT / "P2_SCALABILITY.md").write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
