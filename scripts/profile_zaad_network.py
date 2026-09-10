#!/usr/bin/env python3
"""Sparse multi-location scale probe; solve failures and elapsed build time retained."""
import argparse
import json
from pathlib import Path
import resource
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from zaad.full.contracts import Request  # noqa: E402
from zaad.full.demo import example  # noqa: E402
from zaad.full.model import solve  # noqa: E402
from zaad.full.worlds import draw  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", nargs="+", type=int, default=[10, 100, 1000, 5000])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("refusing overwrite")
    with args.output.open("x") as file:
        for n in args.sizes:
            start = time.monotonic()
            base = example().model_dump(mode="json")
            data = {**base, "horizon": 4, "scenarios": 1, "max_solve_seconds": 30., "skus": [], "stock": [],
                    "services": [], "sources": [], "history": [], "resources": []}
            data["locations"] = [{**base["locations"][0], "id": f"dc{j}", "capacity_volume": n * 1000.} for j in range(5)]
            data["liquidity"] = {**base["liquidity"], "opening_cash": n * 10000., "credit_limit": 0.}
            for i in range(n):
                sku, location, source, service = f"sku{i}", f"dc{i%5}", f"source{i}", f"service{i}"
                data["skus"].append({**base["skus"][0], "id": sku})
                data["stock"].append({**base["stock"][0], "id": sku, "sku": sku, "location": location})
                data["services"].append({**base["services"][0], "id": service, "sku": sku, "location": location})
                data["resources"].append({**base["resources"][0], "id": source})
                data["sources"].append({**base["sources"][0], "id": source, "sku": sku, "destination": location,
                                         "route": ["supplier", location], "resources": [source], "fill_sd": 0., "lead_sd_days": 0.})
                data["history"].extend({**row, "service": service} for row in base["history"][-16:])
            req = Request.model_validate(data)
            prepared = time.monotonic() - start
            worlds = draw(req, 78001, 1, deterministic=True)
            result = solve(req, worlds, service_floor=True)
            row = {"skus": n, "locations": 5, "sources": n, "horizon": 4, "scenarios": 1,
                   "status": result.status, "prepare_seconds": prepared,
                   "total_seconds": time.monotonic() - start, "build_and_solve_seconds": result.solve_seconds,
                   "variables": result.variables, "constraints": result.constraints,
                   "max_rss_platform_units": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                   "warning": "sparse deterministic sizing probe, not full production stochastic workload; other local jobs may contend"}
            file.write(json.dumps(row) + "\n")
            file.flush()
            print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
