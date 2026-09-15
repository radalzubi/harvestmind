"""V2 solve orchestration evidence: profile one workspace solve from outside, and map its coupling.

Nothing under zaad/ is instrumented or changed. The script builds a workspace request the way the
product does (`build_network_request` over a fixture vault, sourcing and commitments on), runs the
released planner under cProfile, and reports where the wall time goes. It then reads the request
itself to say how the products are coupled — which of them share a supplier capacity resource, a
supplier's order-level terms, a transfer lane or a customer — and whether solving the components
separately would be the *same* problem. It is the same problem only when nothing global ties the
components together; the released contract carries opening cash and working-capital economics
that span every product, so the honest answer for a workspace with more than one component is
usually "decomposable in the graph, not equivalent in the objective", and that is what is printed.

Usage: python -m scripts.v2_solve_profile [--skus N] [--seconds S] [--seed K]
"""
from __future__ import annotations

import argparse
import cProfile
import io
import json
import pstats
import time
from collections import defaultdict

import duckdb


def coupling(request) -> dict:
    """Connected components of products over the couplings the request declares."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    skus = [s.id for s in request.skus]
    for s in skus:
        find(s)
    edges: dict[str, int] = defaultdict(int)
    by_resource: dict[str, list[str]] = defaultdict(list)
    by_supplier: dict[str, list[str]] = defaultdict(list)
    for src in request.sources:
        for r in src.resources:
            by_resource[r].append(src.sku)
        by_supplier[src.supplier].append(src.sku)
    for group in by_resource.values():
        for a in group[1:]:
            union(group[0], a); edges["shared supplier capacity resource"] += 1
    terms = {t.supplier for t in getattr(request, "supplier_terms", ()) or ()}
    for sup, group in by_supplier.items():
        if sup in terms:
            for a in group[1:]:
                union(group[0], a); edges["order-level supplier terms (minimum order value / fixed order cost)"] += 1
    for t in getattr(request, "transfers", ()) or ():
        pass  # a lane is per product in the released contract; it couples sites, not products
    comps: dict[str, list[str]] = defaultdict(list)
    for s in skus:
        comps[find(s)].append(s)
    sizes = sorted((len(v) for v in comps.values()), reverse=True)
    global_ties = []
    econ = getattr(request, "economics", None)
    if econ is not None and getattr(econ, "opening_cash", None) is not None:
        global_ties.append("opening cash / financing spans every product")
    if getattr(request, "locations", None):
        if any(getattr(loc, "capacity_volume", None) not in (None, float("inf")) and getattr(loc, "capacity_volume", 0) < 1e15 for loc in request.locations):
            global_ties.append("a site's storage capacity is shared by every product held there")
    return {
        "products": len(skus), "components": len(comps), "component_sizes": sizes[:12],
        "couplings": dict(edges), "global_ties": global_ties,
        "decomposition_equivalent": len(comps) > 1 and not global_ties,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skus", type=int, default=10)
    ap.add_argument("--seconds", type=float, default=15.)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    from scripts.setup_db import setup_db
    from scripts.zaad_network_workspace_smoke import make_network_vault
    from zaad.meio.planner import plan_network
    from zaad.meio.workspace import build_network_request

    conn = duckdb.connect(":memory:")
    setup_db(conn)
    make_network_vault(conn, seed=args.seed)
    skus = [r[0] for r in conn.execute("SELECT sku FROM stg_fmcg_skus ORDER BY sku LIMIT ?", [args.skus]).fetchall()]
    t0 = time.perf_counter()
    request, build = build_network_request(conn, "profile", horizon=12, service_target=.95, skus=skus,
                                           max_solve_seconds=args.seconds, sourcing=True, commitments=True)
    t_build = time.perf_counter() - t0
    graph = coupling(request)

    prof = cProfile.Profile()
    t1 = time.perf_counter()
    prof.enable()
    report = plan_network(request)
    prof.disable()
    t_solve = time.perf_counter() - t1
    out = io.StringIO()
    pstats.Stats(prof, stream=out).sort_stats("cumulative").print_stats(28)
    quality = report.get("solve_quality") or {}
    print(json.dumps({
        "products": len(skus), "build_seconds": round(t_build, 2), "solve_seconds": round(t_solve, 2),
        "status": report.get("status"), "candidates": {k: v.get("status") for k, v in (quality.get("candidates") or {}).items()},
        "coupling": graph,
    }, indent=2, default=str))
    print(out.getvalue())


if __name__ == "__main__":
    main()
