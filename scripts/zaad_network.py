#!/usr/bin/env python3
"""Offline planner/templates; dedicated output only, never training database ingestion."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from zaad.full.contracts import Request  # noqa: E402
from zaad.full.demo import example  # noqa: E402
from zaad.full.intake import export_bundle  # noqa: E402
from zaad.full.planner import plan, report_json  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path)
    parser.add_argument("--fixture", default="normal", choices=["normal", "transfer", "substitution", "recovery", "cash", "understock"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--templates", action="store_true")
    args = parser.parse_args()
    req = Request.model_validate_json(args.request.read_text()) if args.request else example(args.fixture)
    if args.templates:
        args.output.mkdir(parents=True, exist_ok=False)
        for name, contents in export_bundle(req).items():
            (args.output / name).write_text(contents)
        (args.output / "example.json").write_text(req.model_dump_json(indent=2))
        print("Explicit JSON-valued CSV bundle and canonical schema written.")
    else:
        report = plan(req)
        with args.output.open("x") as output:
            output.write(report_json(report))
        print(json.dumps({k: report[k] for k in ("status", "selected_policy", "reasons")}))


if __name__ == "__main__":
    main()
