"""Fast deterministic state screen (v8).

Before spending MILP compute, decide what kind of problem this review actually is. The screen uses
only arithmetic already available at the review - the forecast, the protection profile, the
incumbent's own projected outcome and the physical topology - and it never prunes a candidate on a
heuristic score. It decides which candidate *classes* are worth solving, and says why in plain
terms that appear in the recommendation.

States, in the order they are tested:

  NO_ACTION            the incumbent is feasible, meets every service target and holds no
                       materially avoidable inventory: nothing expensive can improve it
  NETWORK_ALLOCATION   scarcity across a network - stock has to be placed, not just bought
  PROTECT              a live risk driver with material exposure
  RECOVER              temporary protection or inherited excess to unwind
  CAPITAL_OPTIMIZATION service is safe but the position is materially above a lean base stock
  NORMAL_REPLENISHMENT the ordinary case: buy what is needed
  ESCALATE_UNKNOWN     the screen cannot classify confidently, so nothing is skipped

ESCALATE_UNKNOWN is the safe default and always runs the full candidate set.
"""
from __future__ import annotations

from zaad.full.contracts import Request

# Candidate classes each state must solve before any optional planner may run. The incumbent and
# the projected base-stock proxy are always present; they cost one deterministic solve each and are
# the comparison ZAAD exists to make.
MINIMUM_SAFE: dict[str, tuple[str, ...]] = {
    "NO_ACTION": ("deterministic_network",),
    "NORMAL_REPLENISHMENT": ("deterministic_network", "stochastic_network"),
    "CAPITAL_OPTIMIZATION": ("deterministic_network", "stochastic_network", "cvar_network"),
    "NETWORK_ALLOCATION": ("deterministic_network", "stochastic_network", "joint_recovery"),
    "PROTECT": ("deterministic_network", "stochastic_network", "protected_network"),
    "RECOVER": ("deterministic_network", "stochastic_network", "cvar_network"),
    "ESCALATE_UNKNOWN": ("deterministic_network", "stochastic_network", "cvar_network",
                         "protected_network", "hedged_network", "stress_network", "joint_recovery"),
}

# Optional classes per state, solved only when budget remains and the state's own escalation
# condition is met.
OPTIONAL: dict[str, tuple[str, ...]] = {
    "NO_ACTION": (),
    "NORMAL_REPLENISHMENT": ("cvar_network",),
    "CAPITAL_OPTIMIZATION": ("protected_network", "joint_recovery"),
    "NETWORK_ALLOCATION": ("cvar_network", "protected_network", "stress_network"),
    "PROTECT": ("hedged_network", "stress_network", "cvar_network"),
    "RECOVER": ("joint_recovery", "protected_network"),
    "ESCALATE_UNKNOWN": (),
}


def screen(req: Request, fits: dict, protection: list[dict], incumbent_rows: list[dict] | None) -> dict:
    """Classify the review. `incumbent_rows` is the incumbent's evaluated outcome when available;
    without it the screen refuses to claim NO_ACTION."""
    reasons: list[str] = []
    rows = protection or []
    demand_total = sum(row["mean_demand_per_period"] for row in rows) or 0.

    active = [r for r in rows if r["state"]["activity"] > .05]
    recovering = [r for r in rows if r["state"]["regime"] == "RECOVER"]
    declining = [r for r in rows if r["state"].get("demand_decline_confirmed")]
    networked = any(a.approved for a in req.transfers)
    scarcity = False
    if networked:
        for arc in req.transfers:
            if not arc.approved:
                continue
            origin = sum(x.usable for x in req.stock if x.sku == arc.sku and x.location == arc.origin)
            fed = [r for r in rows if r["sku"] == arc.sku and r["location"] == arc.destination]
            need = sum(r["mean_demand_per_period"] for r in fed)
            if need > 0 and origin < need:
                scarcity = True
                reasons.append(f"{arc.origin} holds {origin:.0f} units against {need:.0f} per period of demand at {arc.destination}")
                break

    above_lean = 0.
    for row in rows:
        lean = row["state"].get("lean_base_stock_units")
        if lean is None:
            lean = row["state"]["lean_baseline_units"] + row["mean_demand_per_period"]
        above_lean += max(0., row["on_hand_units"] - lean)
    material_excess = demand_total > 0 and above_lean > demand_total

    incumbent_ok = None
    if incumbent_rows:
        usable = all(r["usable"] for r in incumbent_rows)
        # Headroom, not a marginal pass. The screen judges the incumbent on the same scenario worlds
        # the selection uses, so its verdict is in-sample; the independent confirmation draw is
        # harsher. Requiring one service tolerance *above* target before declaring NO_ACTION keeps
        # borderline cells in the full candidate set, where V7 correctly acted on them.
        meets = usable and all(
            (value is not None and value >= service.target + req.service_tolerance)
            for service in req.services
            for value in [_service(incumbent_rows, service.id)])
        incumbent_ok = bool(usable and meets)
    # Projected service deficit of the current plan: how far below its target the incumbent lands
    # on the selection worlds (0 when it meets them or its outcome is unknown).
    deficit = 0.
    if incumbent_rows and all(r["usable"] for r in incumbent_rows):
        deficit = max((service.target - value for service in req.services
                       for value in [_service(incumbent_rows, service.id)] if value is not None), default=0.)
    supply_driver = any(d["driver"] in ("supply", "inbound_eta") for r in rows for d in r["state"]["active_drivers"])
    thin_cover = any(r["mean_demand_per_period"] > 0 and r["on_hand_units"] < .5 * r["mean_demand_per_period"] for r in rows)
    joint_required = False
    if req.joint_recovery_rule in ("deficit", "deficit_cover") and deficit >= req.joint_recovery_deficit:
        joint_required = True
        reasons.append(f"the current plan is projected to miss a service target by {deficit:.2f}: the service-first joint plan is required")
    if req.joint_recovery_rule == "deficit_cover" and supply_driver and thin_cover:
        joint_required = True
        reasons.append("a served location holds under half a period of demand while a supply driver is active: the service-first joint plan is required")

    if incumbent_ok and not active and not material_excess and not scarcity and not declining:
        reasons.append("the incumbent plan is physically usable, meets every requested service target, "
                       "carries no active risk driver and holds no materially avoidable inventory")
        return _state("NO_ACTION", reasons, above_lean, demand_total, incumbent_ok, joint_required, deficit)
    if scarcity:
        return _state("NETWORK_ALLOCATION", reasons, above_lean, demand_total, incumbent_ok, joint_required, deficit)
    if any(r["state"]["activity"] >= .3 for r in rows):
        reasons.append("a risk driver is materially active: " + ", ".join(
            sorted({d["driver"] for r in rows for d in r["state"]["active_drivers"]})))
        return _state("PROTECT", reasons, above_lean, demand_total, incumbent_ok, joint_required, deficit)
    if recovering or declining:
        reasons.append("temporary protection or confirmed demand decline is being unwound at "
                       + ", ".join(sorted({r["location"] for r in (recovering + declining)})))
        return _state("RECOVER", reasons, above_lean, demand_total, incumbent_ok, joint_required, deficit)
    if material_excess:
        reasons.append(f"{above_lean:.0f} units sit above a lean base stock against {demand_total:.0f} per period of demand")
        return _state("CAPITAL_OPTIMIZATION", reasons, above_lean, demand_total, incumbent_ok, joint_required, deficit)
    if incumbent_ok is None:
        reasons.append("the incumbent's outcome is not yet known, so nothing is skipped")
        return _state("ESCALATE_UNKNOWN", reasons, above_lean, demand_total, incumbent_ok, joint_required, deficit)
    reasons.append("ordinary replenishment: no active driver, no scarcity, no material excess")
    return _state("NORMAL_REPLENISHMENT", reasons, above_lean, demand_total, incumbent_ok, joint_required, deficit)


def _service(rows: list[dict], service_id: str) -> float | None:
    demand = sum(x["demand"] for r in rows for x in r["service_by_period"] if x["service"] == service_id)
    served = sum(x["served"] for r in rows for x in r["service_by_period"] if x["service"] == service_id)
    return (served / demand) if demand else 1.


def _state(name: str, reasons: list[str], above_lean: float, demand: float, incumbent_ok: bool | None,
           joint_required: bool = False, deficit: float = 0.) -> dict:
    minimum = list(MINIMUM_SAFE[name]); optional = list(OPTIONAL[name])
    if joint_required and "joint_recovery" not in minimum:
        minimum.append("joint_recovery"); optional = [c for c in optional if c != "joint_recovery"]
    return {"state": name, "reasons": reasons,
            "minimum_safe_candidates": minimum, "optional_candidates": optional,
            "incumbent_service_deficit": deficit, "joint_recovery_required_by_rule": joint_required,
            "units_above_lean_base_stock": above_lean,
            "periods_above_lean_base_stock": (above_lean / demand) if demand > 0 else None,
            "incumbent_feasible_and_meeting_service": incumbent_ok,
            "scope": "deterministic classification from the forecast, protection profile, topology and the incumbent's own outcome; it selects candidate classes and never prunes on a score"}
