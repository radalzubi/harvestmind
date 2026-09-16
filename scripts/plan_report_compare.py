"""Decision identity between two plan reports (and optionally two plan shapes): the operational
decision, not the objective scalar. Compares status, the selected policy, every recommended action
(action, SKU/source, period, quantity, first review), the incumbent actions, the executable order,
approval, the economics recommendation and orders, materiality, every candidate gate and reason,
the service frontier and reliability, the network service block, orchestration (classification,
candidates built), the solve-quality statuses, and the plan shape's orders. Numbers compare at a
relative tolerance (default 1e-6); everything else exactly. Exit 0 when identical.

Usage: python -m scripts.plan_report_compare A_report.json B_report.json [--plan A_plan.json B_plan.json] [--tol 1e-6]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

DECISION_KEYS = ("status", "selected_policy", "approval_required", "executable_purchase_order", "actions", "incumbent_actions",
                 "reasons", "candidate_gates", "service_frontier", "service_reliability", "network_service", "alternatives",
                 "joint_service_feasibility", "protection_value", "recovery_guidance", "stress_confirmation", "confirmation",
                 "confirmation_benefit_lower", "false_protection", "procurement_timing", "capital", "mode", "explain")
ECON_KEYS = ("recommendation", "orders", "incumbent_orders", "materiality", "selected_costs", "incumbent_costs", "supplier_orders",
             "selected_working_capital", "incumbent_working_capital", "action_recommended", "reconciled")
ORCH_KEYS = ("classification", "candidates_built", "candidate_classes_requested", "candidate_classes_skipped", "gate_basis",
             "incumbent_feasible_and_meeting_service", "joint_recovery_required_by_rule")
VOLATILE = {"solve_seconds", "solve_time", "seconds", "elapsed", "wall", "nodes", "achieved_gap", "gap", "warm_start", "best_bound",
            "completion_seconds", "run_id", "computed_at", "created_at", "information_hash", "input_fingerprint"}


def diff(a, b, path: str, tol: float, out: list[str]) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k in VOLATILE:
                continue
            if k not in a or k not in b:
                out.append(f"{path}.{k}: only in {'A' if k in a else 'B'}")
                continue
            diff(a[k], b[k], f"{path}.{k}", tol, out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{path}: length {len(a)} vs {len(b)}")
            return
        for i, (x, y) in enumerate(zip(a, b)):
            diff(x, y, f"{path}[{i}]", tol, out)
    elif isinstance(a, bool) or isinstance(b, bool):
        if a != b:
            out.append(f"{path}: {a!r} vs {b!r}")
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if not (math.isclose(float(a), float(b), rel_tol=tol, abs_tol=tol) or (math.isnan(float(a)) and math.isnan(float(b)))):
            out.append(f"{path}: {a!r} vs {b!r}")
    elif a != b:
        out.append(f"{path}: {str(a)[:80]!r} vs {str(b)[:80]!r}")


def compare(a: dict, b: dict, tol: float) -> list[str]:
    out: list[str] = []
    for k in DECISION_KEYS:
        diff(a.get(k), b.get(k), k, tol, out)
    for k in ECON_KEYS:
        diff((a.get("economics") or {}).get(k), (b.get("economics") or {}).get(k), f"economics.{k}", tol, out)
    for k in ORCH_KEYS:
        diff((a.get("orchestration") or {}).get(k), (b.get("orchestration") or {}).get(k), f"orchestration.{k}", tol, out)
    qa = {n: c.get("status") for n, c in ((a.get("solve_quality") or {}).get("candidates") or {}).items()}
    qb = {n: c.get("status") for n, c in ((b.get("solve_quality") or {}).get("candidates") or {}).items()}
    diff(qa, qb, "solve_quality.candidates.status", tol, out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--plan", nargs=2, default=None)
    ap.add_argument("--tol", type=float, default=1e-6)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    a, b = json.loads(Path(args.a).read_text()), json.loads(Path(args.b).read_text())
    out = compare(a, b, args.tol)
    if args.plan:
        pa, pb = json.loads(Path(args.plan[0]).read_text()), json.loads(Path(args.plan[1]).read_text())
        for k in ("solver_status", "approval_required", "executable_purchase_order", "orders", "purchase_value", "planner_owner", "warnings"):
            diff(pa.get(k), pb.get(k), f"plan.{k}", args.tol, out)
    verdict = "IDENTICAL" if not out else f"DIFFERENT ({len(out)} fields)"
    print(f"{verdict}: {Path(args.a).name} vs {Path(args.b).name}")
    if not args.quiet:
        for line in out[:60]:
            print("  " + line)
    return 0 if not out else 1


if __name__ == "__main__":
    sys.exit(main())
