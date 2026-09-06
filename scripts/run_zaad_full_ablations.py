#!/usr/bin/env python3
"""Paired mechanism probes; adverse and zero-value results retained, not market ROI."""
from dataclasses import replace
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from zaad.full.contracts import Request  # noqa: E402
from zaad.full.demo import example  # noqa: E402
from zaad.full.model import solve  # noqa: E402
from zaad.full.planner import evaluate, plan  # noqa: E402
from zaad.full.worlds import draw  # noqa: E402


def main():
    output = Path(sys.argv[1])
    rows = []
    for seed in [18001, 18002, 18003, 18004, 18005]:
        for feature, case, disabled in [("continuous_quantities", "normal", "continuous"),
                                         ("transfers_and_inventory_placement", "transfer", "transfers"),
                                         ("substitution", "substitution", "substitutions"),
                                         ("cancellation", "recovery", "cancel"),
                                         ("de_expediting", "recovery", "de_expedite")]:
            req = example(case, seed)
            if feature == "de_expediting":
                data = req.model_dump(mode="json")
                data["stock"][0]["quantity"] = 40.
                for option in data["pipeline"][0]["options"]:
                    if option["action"] == "cancel":
                        option["fee_per_unit"] = 6.
                    elif option["action"] == "keep":
                        option["remaining_invoice_per_unit"] = 7.
                req = Request.model_validate(data)
            training = draw(req, seed, 3)
            truth = draw(req, seed + 10000, 1)
            enabled = solve(req, training)
            without = solve(req, training, disabled=frozenset({disabled}))
            a, b = evaluate(req, enabled, truth)[0], evaluate(req, without, truth)[0]
            rows.append({"feature": feature, "case": case, "seed": seed, "enabled": a, "disabled": b,
                         "saving": b["economic_cost"] - a["economic_cost"] if a["usable"] and b["usable"] else None,
                         "note": "paired synthetic fixture; MEIO placement and transfer are the same mechanism here, not two additive benefits"})
        req = example("normal", seed).model_copy(update={"force_unit_fills": True})
        report = plan(req)
        rows.append({"feature": "unit_fill_control", "seed": seed, "gate_status": report["status"],
                     "control_passed": report["status"] != "PENDING_REVIEW"})
        req = example("understock", seed)
        training = draw(req, seed, 3)
        stress = draw(req, seed + 5000, 2, req.stresses[0])
        combined = [replace(w, weight=1 / (len(training) + len(stress))) for w in training + stress]
        a = solve(req, training, service_first="all")
        b = solve(req, combined, service_first="all")
        truth = draw(req, seed + 7000, 1, req.stresses[0])
        before, after = evaluate(req, a, truth)[0], evaluate(req, b, truth)[0]
        rows.append({"feature": "stress_envelope", "seed": seed, "central": before, "robust": after})
    with output.open("x") as f:
        json.dump(rows, f, indent=2, allow_nan=False)
    print({"rows": len(rows), "controls_passed": sum(r.get("control_passed", False) for r in rows)})


if __name__ == "__main__":
    main()
