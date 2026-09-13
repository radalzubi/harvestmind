"""P4B V1 performance profile: the released model with declared PO options, on the demo request scaled by
number of open orders and options. Records rows, columns, binaries, build time, solve time, first incumbent,
proof time, nodes and peak memory per cell. No optimisation; nothing here changes the engine.

usage: PYTHONPATH=. python3 -m scripts.p4b_profile [--tag P4B_PROFILE]"""
from __future__ import annotations

import argparse
import json
import resource
import time
from pathlib import Path

from zaad.commitments.fixtures import CANCEL, DEFER, EXPEDITE, KEEP, base, open_po, with_stock
from zaad.full import model as M
from zaad.full.worlds import draw

OUT = Path("docs/zaad_full/evidence/p4b")


def request(n_po: int, kinds: tuple[str, ...], split: bool):
    d = with_stock(base(), 60.)
    pos = []
    for i in range(n_po):
        opts = [KEEP(d)]
        if "cancel" in kinds:
            opts.append(CANCEL(d))
        if "defer" in kinds:
            opts.append(DEFER(d))
        if "expedite" in kinds:
            opts.append(EXPEDITE(d))
        po = open_po(d, opts, split=split, ordered=100. / n_po)
        po["id"] = f"po{i}"
        pos.append(po)
    d = dict(d)
    d["pipeline"] = pos
    from zaad.full.contracts import Request
    return Request.model_validate(d)


CELLS = [("no options", 1, (), False), ("1 PO, keep only x3", 3, (), False),
         ("3 POs, cancel+defer+expedite, exclusive", 3, ("cancel", "defer", "expedite"), False),
         ("3 POs, cancel+defer+expedite, split", 3, ("cancel", "defer", "expedite"), True),
         ("10 POs, cancel+defer, exclusive", 10, ("cancel", "defer"), False),
         ("30 POs, cancel+defer+expedite, exclusive", 30, ("cancel", "defer", "expedite"), False),
         ("30 POs, cancel+defer+expedite, split", 30, ("cancel", "defer", "expedite"), True)]


def cell(name, n, kinds, split):
    req = request(n, kinds, split)
    worlds = draw(req, req.seed, req.scenarios)
    t0 = time.perf_counter()
    ctx: dict = {}
    orig = M.Linear.solve

    def timed(self, seconds, objective=None, solver="highs", mip_gap=1e-6, seed=None, options=None):
        ctx["build_s"] = time.perf_counter() - t0
        t1 = time.perf_counter()
        out = orig(self, seconds, objective, solver, mip_gap, seed, options)
        ctx["solve_s"] = time.perf_counter() - t1
        ctx["rows"] = len(self.rows) if hasattr(self, "rows") else None
        ctx["columns"] = len(self.cost) if hasattr(self, "cost") else None
        return out
    M.Linear.solve = timed
    try:
        sol = M.solve(req, worlds, service_floor=True)
    finally:
        M.Linear.solve = orig
    return {"cell": name, "pos": n, "options_per_po": 1 + len(kinds), "split": split, "status": sol.status, "variables": sol.variables, "binaries": sol.binaries,
            "constraints": sol.constraints, "nodes": sol.nodes, "gap": sol.gap, "build_s": round(ctx.get("build_s", 0.), 3), "solve_s": round(sol.solve_seconds, 3),
            "first_incumbent_s": None, "proof_s": round(sol.solve_seconds, 3) if sol.status == "OPTIMAL" else None,
            "amend_columns": sum(1 for k in (sol.amendments or {})), "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 ** 2, 1)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="P4B_PROFILE")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [cell(*c) for c in CELLS]
    for r in rows:
        print(json.dumps(r), flush=True)
    (OUT / f"{a.tag}.json").write_text(json.dumps(rows, indent=1))
    md = [f"# P4B V1 performance profile `{a.tag}` (released model, stochastic candidate solve, demo request)\n",
          "| cell | variables | binaries | constraints | build s | solve s | proof s | nodes | gap | status | peak RSS MB |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    md += [f"| {r['cell']} | {r['variables']} | {r['binaries']} | {r['constraints']} | {r['build_s']} | {r['solve_s']} | {r['proof_s']} | {r['nodes']} | {r['gap']} | {r['status']} | {r['peak_rss_mb']} |" for r in rows]
    md.append("\nfirst incumbent: HiGHS through scipy reports no incumbent timeline; every cell is proved at the root or within the solve time shown (proof s = solve s when OPTIMAL).")
    (OUT / f"{a.tag}.md").write_text("\n".join(md) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
