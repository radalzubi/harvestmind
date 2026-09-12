"""P4 performance instrumentation: the engineering matrix of histories x epochs x request class,
recording worlds, epochs, information sets, columns, binaries, rows, HiGHS nodes, per-solve seconds
and the planner wall time. Written to docs/zaad_full/evidence/p4/P4_PERFORMANCE.json / .md.

usage: PYTHONPATH=. python3 -m scripts.p4_profile"""
from __future__ import annotations

import json
import time
from pathlib import Path

from zaad.full.planner import plan
from zaad.recourse.contracts import resolve
from zaad.recourse.fixtures import sector_base, p2_base, sourcing_base, with_recourse
from zaad.recourse.policy import compare
from zaad.recourse.worlds import draw_tree

OUT = Path("docs/zaad_full/evidence/p4")
def _p1():
    from zaad.full.fixtures_p1 import p1_request
    return p1_request(seed=41001, scenarios=3, max_solve_seconds=15.)


CLASSES = {
    "single_sku_single_location": _p1,
    "p2_network": lambda: p2_base(),
    "p3_two_sources": lambda: sourcing_base("E2_landed_beats_unit_price"),
    "p3_multi_sku_shared_order": lambda: sourcing_base("C6_shared_mov_multi_sku"),
    # representative sector request (release audit, section 16): produce with FEFO / sellable-life physics
    "sector_produce": lambda: sector_base("P2_near_expiry_inventory"),
}
GRID = [(3, [3], 2), (3, [3, 6], 2), (4, [3], 2), (4, [3, 6], 2), (8, [3], 1), (8, [3, 6], 1), (2, [3, 6], 3)]   # histories, epochs, continuations


def main() -> int:
    rows = []
    for cls, make in CLASSES.items():
        for histories, epochs, cont in GRID:
            base = make()
            req = with_recourse(base, review_periods=epochs, observables=["demand", "receipts"], continuations=cont)
            rc = resolve(req)
            worlds = draw_tree(req, rc, req.seed, histories, cont)
            if len(worlds) > 16:
                continue
            t0 = time.perf_counter()
            out = compare(req, worlds, rc, perfect=True, service_floor=True)
            wall = time.perf_counter() - t0
            row = {"class": cls, "histories": histories, "epochs": epochs, "continuations": cont, "worlds": len(worlds),
                   "sets": {str(e): len(v) for e, v in out["nodes"].sets.items()}, "wall": round(wall, 2),
                   "ordering_ok": out["ordering_ok"], "value": out["value_of_adaptation"]}
            for k in ("static", "adaptive", "perfect"):
                s = out[k]
                row[k] = {"status": s.status, "vars": s.variables, "binaries": s.binaries, "rows": s.constraints, "nodes": s.nodes, "seconds": round(s.solve_seconds, 2), "gap": s.gap}
            # the planner end to end (its own selection worlds + the tree comparators)
            preq = with_recourse(base, review_periods=epochs, observables=["demand", "receipts"], continuations=cont).model_copy(update={"scenarios": min(histories, 4)})
            t1 = time.perf_counter()
            try:
                rep = plan(Request_validate(preq))
                row["planner_wall"] = round(time.perf_counter() - t1, 2)
                row["planner_verdict"] = rep["recourse"]["verdict"]
                row["planner_solves"] = len(rep["candidates"]) + 3
            except Exception as exc:
                row["planner_wall"] = None
                row["planner_error"] = f"{type(exc).__name__}: {exc}"[:120]
            rows.append(row)
            print(f"{cls:28s} h={histories} e={epochs} c={cont} worlds={len(worlds):2d} sets={row['sets']} adaptive {row['adaptive']['status']:8s} {row['adaptive']['seconds']:6.1f}s vars={row['adaptive']['vars']} bin={row['adaptive']['binaries']} nodes={row['adaptive']['nodes']} | compare wall {wall:6.1f}s | planner {row.get('planner_wall')}s {row.get('planner_error', '')}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "P4_PERFORMANCE.json").write_text(json.dumps(rows, indent=1, default=str))
    md = ["# P4 performance matrix\n", "| class | histories | epochs | cont. | worlds | sets | adaptive status | adaptive s | vars | binaries | rows | HiGHS nodes | static s | PI s | compare wall s | planner wall s | verdict |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        a = r["adaptive"]
        md.append(f"| {r['class']} | {r['histories']} | {r['epochs']} | {r['continuations']} | {r['worlds']} | {r['sets']} | {a['status']} | {a['seconds']} | {a['vars']} | {a['binaries']} | {a['rows']} | {a['nodes']} | {r['static']['seconds']} | {r['perfect']['seconds']} | {r['wall']} | {r.get('planner_wall')} | {r.get('planner_verdict', r.get('planner_error', ''))} |")
    (OUT / "P4_PERFORMANCE.md").write_text("\n".join(md) + "\n")
    return 0


def Request_validate(req):
    from zaad.full.contracts import Request
    return Request.model_validate(req.model_dump(mode="json"))


if __name__ == "__main__":
    raise SystemExit(main())
