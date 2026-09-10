"""Local ZAAD review artifact; explicit optional public fetch, never automatic PO or training write."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from zaad.contracts import PlanningRequest  # noqa: E402
from zaad.demo import CASES, demo_request  # noqa: E402
from zaad.engine import plan  # noqa: E402
from zaad.signals import fetch_noaa_alerts  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=CASES, default="balanced")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--fetch-noaa", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Will not overwrite an existing evidence artifact")
    if args.input and args.input.stat().st_size > 2 * 1024 * 1024:
        raise SystemExit("Input exceeds 2 MiB")
    req = (
        PlanningRequest.model_validate_json(args.input.read_text())
        if args.input
        else demo_request(args.case)
    )
    source = []
    if args.fetch_noaa:
        now = datetime.now(timezone.utc)
        source = list(
            fetch_noaa_alerts(
                user_agent="ZAAD-research-prototype (zaadsupply.com)", ingested_at=now
            )
        )
        # Never label a real operator payload synthetic or change its as_of behind the user.
        if args.input:
            raise SystemExit(
                "Live signal example is synthetic-operator only; merge real operator signals explicitly"
            )
        raw = req.model_dump(mode="json")
        raw.update(
            as_of=now.isoformat(),
            signals=[s.model_dump(mode="json") for s in source[:200]],
            evidence_label="REAL-SIGNAL / SYNTHETIC-OPERATOR",
        )
        if len(source) > 200:
            # Do not silently truncate a provider snapshot to fit the planner contract.
            raw["signals"] = []
        req = PlanningRequest.model_validate(raw)
    report = plan(req)
    artifact = {
        "request": req.model_dump(mode="json"),
        "report": report.model_dump(mode="json"),
        "provider_records": [s.model_dump(mode="json") for s in source],
        "source_count": len(source),
        "mapping_note": "Synthetic network has no asserted weather-zone exposure; unmatched alerts must not change it.",
        "overflow_note": "If >200 live records, full normalized snapshot retained here but NOT partially passed to planner.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(artifact, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(
        json.dumps(
            {
                "status": report.status,
                "policy": report.selected_policy,
                "classification": report.evidence_label,
                "source_count": len(source),
                "output": str(args.output),
            }
        )
    )


if __name__ == "__main__":
    main()
