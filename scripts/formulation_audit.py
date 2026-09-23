"""Sentinel cleanup — formulation audit of the planner's models on a workspace request, from outside the optimizer.

For a request (a synthetic vault at a product count) the released planner runs with `Linear.solve` observed:
every MILP is recorded with its dimensions, coefficient ranges (matrix, bounds, right-hand sides, objective),
a big-M audit per binary family (rows that link a continuous quantity to a 0/1 column: the linking
coefficient's min / median / p95 / max and its source), the objective decomposed by column family for the
returned point, and the solver's own status, gap, nodes, time and integrality / feasibility violations.

`--sentinel` reinstates the released adapter's placeholders on the request (`capacity_volume=1e9`,
`opening_cash=1e9`, `credit_limit=1e9`, declared values, hence the released formulation verbatim), so the
same request is audited BEFORE and AFTER on identical data.

Usage: python -m scripts.formulation_audit --vault demo|sample --products 5 [--sentinel] [--seconds 15]
                                          [--stress] [--out DIR] [--label NAME] [--plan]
`--plan` runs the full planner (plan()); without it only the two joint solves and the incumbent solve run.
Nothing under zaad/ runs differently.
"""
from __future__ import annotations

import argparse
import json
import platform
import resource
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy as np

from scripts.production_solve_benchmark import Recorder

BINARY_FAMILIES = ("depleted", "fefo", "priority", "direct_first", "active", "order", "pallets", "freight_tier", "switch",
                   "transfer_dispatch", "transfer_packs", "po_option", "line_full", "order_full", "packs", "case", "pallet", "transport")


def make_vault(kind: str, seed: int, stress: bool):
    from scripts.setup_db import setup_db
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    if kind == "demo":
        from synthetic.fmcg.demo_company import load_demo_company_into
        load_demo_company_into(conn, "audit", seed=seed)
        as_of = datetime(2026, 6, 8, tzinfo=timezone.utc)
    else:
        from api.routers.intake import load_fmcg_sample_into
        load_fmcg_sample_into(conn, seed=seed)
        as_of = datetime(2025, 8, 11, tzinfo=timezone.utc)
    if stress:
        # genuinely coupled: order-level economics per supplier (a fixed order cost and a minimum order value the
        # operator's own weekly lines clear) and a declared opening cash balance of roughly seven weeks of the
        # 25-product purchase run-rate with a small facility, so capital binds on wide requests without making
        # the operator's own rule infeasible (a rule projection is cash-capped, never MOV-aware)
        suppliers = [r[0] for r in conn.execute("SELECT DISTINCT supplier_id FROM stg_fmcg_purchase_orders").fetchall()]
        rows = [("fixed_order_cost", "150"), ("opening_cash", "3000000"), ("credit_limit", "300000"), ("interest_annual", "0.09")]
        rows += [(f"minimum_order_value_{sid}", "1000") for sid in suppliers]      # the adapter reads MOV per supplier
        for key, value in rows:
            conn.execute("DELETE FROM stg_fmcg_economics WHERE key = ?", [key])
            conn.execute("INSERT INTO stg_fmcg_economics (key, value, provenance) VALUES (?, ?, 'OPERATOR_DECLARED')", [key, value])
    return conn, as_of


def _rss_mb() -> float:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / (1024 * 1024) if sys.platform == "darwin" else rss / 1024


class Audit(Recorder):
    """The benchmark Recorder plus the numerical audit of every model it sees."""

    def install(self) -> None:
        import zaad.full.model as model
        super().install()
        rec = self
        patched = model.Linear.solve

        def audited(self_, seconds, objective=None, solver="highs", mip_gap=1e-6, seed=None, options=None):
            n0 = len(rec.solves)
            result, residual = patched(self_, seconds, objective, solver, mip_gap, seed, options)
            if len(rec.solves) > n0:
                rec.solves[-1]["audit"] = audit_model(self_, objective, getattr(result, "x", None), result)
            return result, residual
        model.Linear.solve = audited
        self._orig.append((model.Linear, "solve", patched))


def audit_model(m, objective, x, result) -> dict:
    names = m.names
    cost = np.asarray(m.cost if objective is None else objective, dtype=float)
    upper = np.asarray(m.upper, dtype=float)
    lo, hi = np.asarray(m.lo, dtype=float), np.asarray(m.hi, dtype=float)
    coef = np.asarray([abs(v) for row in m.rows for v in row.values() if v], dtype=float)
    finite_up = upper[np.isfinite(upper)]
    finite_rhs = np.concatenate([lo[np.isfinite(lo)], hi[np.isfinite(hi)]])
    nz_cost = np.abs(cost[cost != 0])
    ranges = {"matrix_min": float(coef.min()) if coef.size else None, "matrix_max": float(coef.max()) if coef.size else None,
              "bound_max_finite": float(np.abs(finite_up).max()) if finite_up.size else None, "bounds_infinite": int((~np.isfinite(upper)).sum()),
              "rhs_max_finite_abs": float(np.abs(finite_rhs).max()) if finite_rhs.size else None,
              "objective_min_nonzero": float(nz_cost.min()) if nz_cost.size else None, "objective_max": float(nz_cost.max()) if nz_cost.size else None,
              "matrix_ratio": (float(coef.max() / coef.min()) if coef.size and coef.min() > 0 else None)}
    # big-M audit: a row that carries exactly one 0/1 column of a linkage family together with continuous columns
    integer = m.integer
    fam: dict[str, list[float]] = {}
    for row in m.rows:
        bins = [(q, v) for q, v in row.items() if integer[q] and upper[q] == 1 and str(names[q][0]) in BINARY_FAMILIES]
        if len(bins) != 1 or len(row) < 2:
            continue
        q, v = bins[0]
        fam.setdefault(str(names[q][0]), []).append(abs(float(v)))
    bigm = {}
    for f, ms in fam.items():
        ms.sort()
        bigm[f] = {"rows": len(ms), "min": ms[0], "median": statistics.median(ms), "p95": ms[min(len(ms) - 1, int(.95 * len(ms)))], "max": ms[-1]}
    decomposition = None
    if x is not None:
        contrib: dict[str, float] = {}
        for q, c in enumerate(m.cost):
            if c and x[q]:
                key = str(names[q][0])
                contrib[key] = contrib.get(key, 0.) + float(c) * float(x[q])
        decomposition = {k: round(v, 2) for k, v in sorted(contrib.items(), key=lambda kv: -abs(kv[1]))}
    return {"columns": len(names), "rows": len(m.rows), "integer": int(sum(integer)), "ranges": ranges, "big_m": bigm,
            "objective_by_family": decomposition, "objective_value": getattr(result, "fun", None),
            "highs": {"status": int(getattr(result, "status", -1)), "gap": getattr(result, "mip_gap", None), "nodes": getattr(result, "mip_node_count", None),
                      "integrality_violation": getattr(result, "max_integrality_violation", None), "primal_infeasibility": getattr(result, "max_primal_infeasibility", None),
                      "message": str(getattr(result, "message", ""))}}


def run(kind: str, n: int, seconds: float, sentinel: bool, stress: bool, plan: bool, out_dir: Path, label: str, seed: int = 41001) -> dict:
    import pandas as pd
    import zaad.full.historical as H
    from zaad.full.model import solve
    from zaad.full.planner import plan as run_plan
    from zaad.full.workspace import build_request
    from zaad.full.worlds import draw
    conn, as_of = make_vault(kind, 7, stress)
    probe, _ = build_request(conn, "audit", as_of=as_of, horizon=12)
    sel = H.select_scope(conn, probe, n, origin=pd.Timestamp(as_of.replace(tzinfo=None)), periods=19)
    req, build = build_request(conn, "audit", as_of=as_of, horizon=12, skus=sel["skus"], seed=seed, max_solve_seconds=seconds)
    if sentinel:
        data = req.model_dump(mode="python")
        data["locations"] = [{**loc, "capacity_volume": 1e9} for loc in data["locations"]]
        if data["liquidity"]["opening_cash"] is None:
            data["liquidity"].update(opening_cash=1e9, credit_limit=1e9)
        elif data["liquidity"]["credit_limit"] is None:
            data["liquidity"].update(credit_limit=1e9)
        from zaad.full.contracts import Request
        req = Request.model_validate(data)
    rec = Audit()
    rec.install()
    t0, c0 = time.perf_counter(), time.process_time()
    rec.t_start = t0
    status = None
    try:
        if plan:
            report = run_plan(req)
            status = {"status": report["status"], "selected_policy": report["selected_policy"], "state": (report.get("orchestration") or {}).get("state"),
                      "reasons": report.get("reasons"), "candidates": {k: v.get("status") for k, v in (report.get("candidates") or {}).items()}}
        else:
            det = draw(req, req.seed, 1, deterministic=True)
            sel_w = draw(req, req.seed, req.scenarios)
            a = solve(req, det, service_first="all", service_only=True)
            b = solve(req, sel_w, service_first="all")
            status = {"joint_phase_one": a.status, "joint_two_phase": b.status, "projected_cost": b.projected_cost, "binaries": b.binaries}
    finally:
        rec.uninstall()
    wall, cpu = time.perf_counter() - t0, time.process_time() - c0
    solves = rec.solves
    fam_all: dict[str, list[float]] = {}
    for s_ in solves:
        for f, st in (s_.get("audit") or {}).get("big_m", {}).items():
            fam_all.setdefault(f, []).extend([st["min"], st["median"], st["max"]])
    out = {"run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "host": platform.platform(), "vault": kind, "products": n, "stress": stress,
           "sentinel": sentinel, "plan": plan, "seconds": seconds,
           "request": {"skus": len(req.skus), "sources": len(req.sources), "capacity_volume": [loc.capacity_volume for loc in req.locations],
                       "opening_cash": req.liquidity.opening_cash, "credit_limit": req.liquidity.credit_limit,
                       "cost_of_capital_per_period": req.liquidity.cost_of_capital_per_period, "supplier_terms": len(req.supplier_terms),
                       "capacity_provenance": {k: v for k, v in (build.get("provenance") or {}).items() if "capacity" in k}},
           "outcome": status, "wall_s": round(wall, 2), "cpu_s": round(cpu, 2), "rss_mb": round(_rss_mb(), 1),
           "milps": len(solves), "time_limited": sum(1 for s_ in solves if s_["highs_status"] == 1),
           "big_m_families_overall": {f: {"min": min(v), "max": max(v)} for f, v in fam_all.items()},
           "solves": [{k: v for k, v in s_.items() if k != "audit"} | {"audit": s_.get("audit")} for s_ in solves]}
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"audit_{kind}_{n:03d}_{'sentinel' if sentinel else 'clean'}{'_stress' if stress else ''}{'_plan' if plan else ''}{('_' + label) if label else ''}.json"
    path.write_text(json.dumps(out, indent=1, default=str))
    big = max(solves, key=lambda s_: s_["cols"]) if solves else None
    a = (big or {}).get("audit") or {}
    print(f"{kind} n={n} {'SENTINEL' if sentinel else 'clean'}{' stress' if stress else ''}: {status} | wall {wall:.1f}s, {len(solves)} MILPs, TL {out['time_limited']} | "
          f"largest {big['cols'] if big else 0} cols: matrix max {a.get('ranges', {}).get('matrix_max')}, bound max {a.get('ranges', {}).get('bound_max_finite')}, "
          f"rhs max {a.get('ranges', {}).get('rhs_max_finite_abs')}, obj {a.get('objective_value')} | big-M: " +
          ", ".join(f"{f} max {v['max']:.3g}" for f, v in out["big_m_families_overall"].items()) + f" -> {path}", flush=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", choices=("demo", "sample"), default="demo")
    ap.add_argument("--products", default="5")
    ap.add_argument("--seconds", type=float, default=15.)
    ap.add_argument("--sentinel", action="store_true")
    ap.add_argument("--stress", action="store_true")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--out", default="artifacts/formulation_audit")
    ap.add_argument("--label", default="")
    args = ap.parse_args()
    for n in [int(x) for x in args.products.split(",") if x]:
        run(args.vault, n, args.seconds, args.sentinel, args.stress, args.plan, Path(args.out), args.label)


if __name__ == "__main__":
    main()
