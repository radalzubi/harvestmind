"""P5 performance profile: the engine alone on a grid of declaration sizes, recording rows, columns,
binaries, build time, solve time, first incumbent, proof time, nodes and peak memory. Read before any
performance work is attempted; nothing here changes the engine.

usage: PYTHONPATH=. python3 -m scripts.p5_profile [--tag P5_PROFILE]"""
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

import numpy as np

from zaad.atp import allocation
from zaad.atp.contracts import resolve
from zaad.atp.fixtures import SKU, base, cls, customer, inbound, line, order, service, stock, with_atp, with_state
from zaad.atp.promise import promise
from zaad.atp.state import build_state

OUT = Path("docs/zaad_full/evidence/p5/integration")


def declaration(orders: int, lines_per_order: int, horizon: int, locations: int, firm_inbound: bool, partial_forbidden_share: float = .2, minimum_share: float = .2):
    req = base()
    n = orders
    cs = [customer(req, f"c{i}") for i in range(1, n + 1)]
    ss = [service(req, f"s{i}", f"c{i}") for i in range(1, n + 1)]
    demand = n * lines_per_order * 40.
    st = [stock(req, "north_stock", SKU, "north", demand * .35)]
    if locations > 1:
        st.append(stock(req, "central_stock", SKU, "central", demand * .35))
    inbound_rows = [inbound(req, "in1", SKU, "north", 2, demand * .15)] if firm_inbound else []
    req = with_state(req, stock_rows=st, customers=cs, services=ss, inbound_rows=inbound_rows)
    classes = [cls("a", shortage_penalty_per_unit=5., late_penalty_per_unit_period=1.), cls("b", late_penalty_per_unit_period=.5), cls("c", contractual_service_floor=.3, provenance="CONTRACT", reference="MSA")]
    rows = []
    rng = np.random.default_rng(7)
    for i in range(1, n + 1):
        ls = []
        for j in range(lines_per_order):
            kw: dict[str, Any] = {}
            if rng.random() < minimum_share:
                kw["minimum_ship_quantity"] = 10.
            ls.append(line(f"l{i}_{j}", 40., requested=int(rng.integers(0, min(3, horizon) + 1)), **kw))
        rows.append(order(f"o{i}", f"c{i}", ["a", "b", "c"][i % 3], ls, order_period=-int(rng.integers(0, 3)), backorder_allowed=True, max_backorder_periods=2,
                          partial_fulfillment_allowed=rng.random() > partial_forbidden_share))
    return with_atp(req, rows, classes, promise_horizon=horizon, include_inbound=firm_inbound, cross_location=locations > 1)


def _parse(log: str) -> dict[str, Any]:
    out: dict[str, Any] = {"nodes": None, "first_incumbent_s": None, "proof_s": None, "lp_iterations": None}
    m = re.search(r"Nodes\s+(\d+)", log)
    if m:
        out["nodes"] = int(m.group(1))
    m = re.search(r"LP iterations\s+(\d+)", log)
    if m:
        out["lp_iterations"] = int(m.group(1))
    m = re.search(r"Timing\s+([0-9.]+)", log)
    if m:
        out["proof_s"] = float(m.group(1))
    # first row of the branch-and-bound table with a finite primal bound: its last column is the time
    for ln in log.splitlines():
        cells = ln.split()
        if len(cells) < 12 or not cells[-1].endswith("s"):
            continue
        if cells[0].isalpha() and len(cells[0]) <= 2:
            cells = cells[1:]
        if not (cells[0].isdigit() and cells[1].isdigit() and cells[2].isdigit()):
            continue
        try:
            primal = cells[-8]
            if primal.lower() not in ("inf", "-inf"):
                float(primal)
                out["first_incumbent_s"] = float(cells[-1][:-1])
                break
        except ValueError:
            continue
    return out


def profile_cell(req, seconds: float = 60.) -> dict[str, Any]:
    atp = resolve(req)
    t0 = time.perf_counter()
    state = build_state(req, atp)
    chans, drv, meta = allocation.channels(req, atp, state)
    build_s = time.perf_counter() - t0
    # capture HiGHS's own log (C-level stdout) through a temporary file
    fd = os.dup(1)
    with tempfile.TemporaryFile(mode="w+") as tmp:
        os.dup2(tmp.fileno(), 1)
        try:
            orig = allocation.milp
            def milp_disp(*a, **kw):
                kw = dict(kw)
                kw["options"] = {**kw.get("options", {}), "disp": True}
                return orig(*a, **kw)
            allocation.milp = milp_disp
            t1 = time.perf_counter()
            alloc = allocation.solve(req, atp, state, seconds=seconds)
            solve_s = time.perf_counter() - t1
        finally:
            allocation.milp = orig
            os.dup2(fd, 1)
            os.close(fd)
        tmp.seek(0)
        log = tmp.read()
    parsed = _parse(log)
    t2 = time.perf_counter()
    rep = promise(req, seconds=seconds)
    wall = time.perf_counter() - t2
    return {"orders": len(atp.spec.orders), "lines": sum(len(o.lines) for o in atp.spec.orders), "horizon": atp.spec.promise_horizon, "lots": len(state.lots), "lanes": len(state.lanes),
            "channels": len(chans), "rows": alloc.engine["rows"], "columns": alloc.engine["columns"], "binaries": alloc.engine["binaries"],
            "build_s": round(build_s, 4), "solve_s": round(solve_s, 4), "status": alloc.status, "objective": alloc.engine.get("objective"), "mip_gap": alloc.engine.get("mip_gap"),
            **parsed, "promise_wall_s": round(wall, 3), "verdict": rep["verdict"],
            "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 ** 2), 1)}


GRID = [(5, 1, 8, 1, False), (20, 2, 8, 1, False), (50, 2, 8, 2, True), (100, 3, 12, 2, True), (200, 2, 26, 2, True), (100, 5, 26, 2, True)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="P5_PROFILE")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for orders, lpo, horizon, locs, firm in GRID:
        req = declaration(orders, lpo, horizon, locs, firm)
        row = {"cell": f"{orders}x{lpo} lines, horizon {horizon}, {locs} location(s), firm inbound {firm}", **profile_cell(req)}
        rows.append(row)
        print(json.dumps(row), flush=True)
    (OUT / f"{a.tag}.json").write_text(json.dumps(rows, indent=1))
    md = [f"# P5 performance profile `{a.tag}` (engine alone, scipy HiGHS)\n",
          "| cell | rows | columns | binaries | channels | build s | solve s | first incumbent s | proof s | nodes | LP iterations | status | gap | promise wall s | peak RSS MB |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['cell']} | {r['rows']} | {r['columns']} | {r['binaries']} | {r['channels']} | {r['build_s']} | {r['solve_s']} | {r['first_incumbent_s']} | {r['proof_s']} | {r['nodes']} | {r['lp_iterations']} | {r['status']} | {r['mip_gap']} | {r['promise_wall_s']} | {r['peak_rss_mb']} |")
    (OUT / f"{a.tag}.md").write_text("\n".join(md) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
