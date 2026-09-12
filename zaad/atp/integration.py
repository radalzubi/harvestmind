"""P5 shared-core orchestration: the one entry point every path uses (planner hook, `/jobs`, the
standalone endpoint, the workspace path).

It runs the P5 engine on the request's allocatable-supply envelope (state.py) and prices both the
incumbent rule and the exact allocation on the P5 ledger (economics.py). When the planner calls it,
the planner's own P0 protection profile is passed in and reported as an OVERLAY: P0 protection is a
service-level construct sized against forecast demand inside the planner's candidate solves; the
frozen contract has no reservation of units for it, a firm customer order is realised demand that
protection exists to serve, and P0's next review sees the reduced position. Nothing here changes a
P0-P4 decision: the block is attached after the frozen report is complete, and a refused declaration
fails closed to a report-level refusal (no recommendation), never to a crash of the plan.
"""
from __future__ import annotations

from typing import Any

from zaad.atp.contracts import Atp, resolve
from zaad.atp.promise import promise_with
from zaad.atp.validation import AtpRefused

REFUSED = "REFUSED (declared input the engine must not reinterpret)"


def protection_overlay(req, atp: Atp, report: dict[str, Any], protection: list[dict] | None) -> list[dict[str, Any]]:
    """Per (SKU, location) the planner's P0 protection row against what P5 promises from on-hand stock."""
    if not protection:
        return []
    drawn: dict[tuple[str, str], float] = {}
    on_hand: dict[tuple[str, str], float] = {}
    for row in report["remaining_supply"]:
        if row["tier"] != "on_hand":
            continue
        key = (row["sku"], row["location"])
        on_hand[key] = on_hand.get(key, 0.) + row["remaining_unreserved"] + row["promised_now"]
        drawn[key] = drawn.get(key, 0.) + row["promised_now"]
    out = []
    for row in protection:
        key = (row["sku"], row["location"])
        if key not in on_hand:
            continue
        units = float(row.get("protection_units") or 0.)
        lean = float((row.get("state") or {}).get("lean_baseline_units") or 0.)
        remaining = on_hand[key] - drawn[key]
        out.append({"sku": row["sku"], "location": row["location"], "protection_units": round(units, 3), "lean_baseline_units": round(lean, 3),
                    "regime": (row.get("state") or {}).get("regime"), "allocatable_on_hand": round(on_hand[key], 3), "promised_from_on_hand": round(drawn[key], 3),
                    "remaining_after_promises": round(remaining, 3), "below_protection_units": round(max(0., units - remaining), 3),
                    "hard_reservation": False,
                    "note": "P0 protection reserves no units (service-level construct in the planner's own solves); a firm customer order is realised demand; "
                            "the next P0 review plans from the position these promises leave"})
    return out


def refused_block(reason: str) -> dict[str, Any]:
    return {"version": "zaad.atp.0.2", "verdict": REFUSED, "reason": reason, "promised": [], "reservations": [], "unfulfilled": [], "refused": [],
            "approval_required": True, "executable_promise": False}


def atp_block(req, atp: Atp | None = None, *, protection: list[dict] | None = None, seconds: float | None = None, planner_path: bool = False) -> dict[str, Any] | None:
    """The P5 report for a request with an enabled `atp` block (None for a frozen request)."""
    atp = atp if atp is not None else resolve(req)
    if atp is None:
        return None
    budget = float(seconds if seconds is not None else min(30., float(req.max_solve_seconds)))
    try:
        rep = promise_with(req, atp, budget)
    except AtpRefused as exc:
        return refused_block(str(exc))
    rep["protection_overlay"] = protection_overlay(req, atp, rep, protection)
    rep["protection_overlay_available"] = bool(protection)
    rep["path"] = "planner" if planner_path else "standalone"
    if not protection:
        rep["assumptions"].append("P0 protection overlay not available on this path (the planner's protection profile is reported only when P5 runs inside plan())")
    return rep
