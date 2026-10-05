"""Demonstration, not a test: what the causal attestation (zaad/full/causal.py) reports for the workspace
builder on the synthetic sample at one decision time.

    python3 scripts/demo_causal_attestation.py [--as-of 2025-09-01] [--skus SKU-0009,SKU-0030,SKU-0143]

Loads the sample into an in-memory database, builds the request, perturbs receipts that were not available
at the decision time on orders placed before it (every change is rolled back), and prints the report.
Availability is the labelled date-only test assumption (a receipt is known from its receipt date): the
vault has no source knowledge time for receipts.
Exit code 0 when the report is PASS, 1 when it is FAIL, 2 when nothing was checked."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--as-of", default="2025-09-01")
    parser.add_argument("--skus", default="SKU-0009,SKU-0030,SKU-0143")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--archetype", default="E_mixed_portfolio")
    args = parser.parse_args()
    import duckdb

    from api.routers.intake import load_fmcg_sample_into
    from scripts.setup_db import setup_db
    from zaad.full import causal
    from zaad.full.workspace import build_request

    conn = duckdb.connect()
    setup_db(conn=conn)
    load_fmcg_sample_into(conn, seed=args.seed, archetype=args.archetype)
    as_of = datetime.fromisoformat(args.as_of).replace(tzinfo=timezone.utc)
    skus = [s for s in args.skus.split(",") if s] or None

    def build(c):
        return build_request(c, "causal_demo_operator", as_of=as_of, horizon=12, skus=skus)[0]
    base = build(conn)
    report = causal.run_causal_checks(build, conn, causal.receipt_perturbations(base.as_of, is_available_at=causal.legacy_date_only_receipt_availability))
    print(json.dumps({"builder": "zaad.full.workspace.build_request", "skus": skus, "open_orders_in_request": [p.id for p in base.pipeline], **report}, indent=1))
    return {"PASS": 0, "FAIL": 1}.get(report["status"], 2)


if __name__ == "__main__":
    raise SystemExit(main())
