#!/usr/bin/env python3
"""Offboard one workspace: remove its data from every ZAAD-controlled store (docs/security/TENANT_OFFBOARDING_RUNBOOK.md).

Dry run by default. Nothing is removed unless `--execute` is given together with `--confirm-operator-id`, which must
repeat the exact operator id. The target is the immutable operator id, never a name. Output is counts, ids and paths —
never a customer record.

    python scripts/offboard_operator.py --operator-id op_xxxxxxxx                     # plan only
    python scripts/offboard_operator.py --operator-id op_xxxxxxxx --execute --confirm-operator-id op_xxxxxxxx

Exit codes: 0 complete or nothing to do, 2 partial (some stores remain; rerun after fixing), 3 refused.
Runs where the data root is mounted (HARVESTMIND_DATA_ROOT, ZAAD_JOB_STORE, ZAAD_SHADOW_LEDGER as in the deployment).
Process-local caches of a running API are not reachable from here: use the admin route, or restart the API afterwards.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from infrastructure.offboarding import Offboarding, Refused  # noqa: E402
from infrastructure.operator_registry import OperatorRegistry  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--operator-id", required=True, help="the immutable operator id (op_ + 8 hex)")
    ap.add_argument("--execute", action="store_true", help="remove the data (default: dry run)")
    ap.add_argument("--confirm-operator-id", default=None, help="required with --execute; must repeat --operator-id exactly")
    ap.add_argument("--data-root", default=None, help="override HARVESTMIND_DATA_ROOT")
    ap.add_argument("--json", action="store_true", help="print the structured result as JSON")
    args = ap.parse_args(argv)

    registry = OperatorRegistry(data_root=args.data_root) if args.data_root else OperatorRegistry()
    off = Offboarding(registry)
    try:
        if args.execute:
            if not args.confirm_operator_id:
                print("refused: --execute needs --confirm-operator-id repeating the operator id", file=sys.stderr)
                return 3
            res = off.execute(args.operator_id, args.confirm_operator_id, actor="cli")
        else:
            res = off.plan(args.operator_id)
    except Refused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 3

    if args.json:
        print(json.dumps(res.to_dict(), indent=1))
    else:
        print(f"{res.mode} for {res.operator_id}: {res.status.upper()}")
        for s in res.stages:
            line = f"  {s.store:<22} {s.status:<13} {s.count:>6}"
            if s.detail:
                line += f"  {s.detail}"
            print(line)
            for p in s.paths[:20]:
                print(f"      {p}")
            if len(s.paths) > 20:
                print(f"      … {len(s.paths) - 20} more")
        for w in res.warnings:
            print(f"  WARNING: {w}")
        print("  retained:", "; ".join(f"{r['store']} ({r['reason']})" for r in res.retained))
        print("  outside ZAAD's control:", "; ".join(res.external))
        if res.receipt:
            print(f"  receipt: {res.receipt}")
    return 2 if res.status == "partial" else 0


if __name__ == "__main__":
    sys.exit(main())
