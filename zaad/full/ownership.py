"""Planner ownership (P1 planner-boundary pass).

One review is planned by one of two planners:

  PURCHASING_ECONOMICS   the P1 purchasing planner: what is the economically correct replenishment
                         decision under normal purchasing conditions (whether, when, how much; lot,
                         freight, order-cost, financing and carrying economics; ordinary demand and
                         supplier spread; comparison with the incumbent).
  PROTECTION_RECOVERY    the frozen P0 protection / recovery planner: protect or recover service under
                         a declared or credible stress, or unwind protection earlier decisions created.

Ownership is decided BEFORE candidate assembly from semantic state only, never from a fixture, cell,
seed, cost, service outcome or tuned threshold. The rule is pre-registered in
docs/zaad_full/evidence/p1/P1_PLANNER_OWNERSHIP.md. A P1-owned review is always a lean review (calm
screen state, no risk activity); the P0-owned path is the unchanged frozen path.
"""
from __future__ import annotations

from zaad.full.contracts import Request, Stress

PURCHASING_ECONOMICS = "PURCHASING_ECONOMICS"
PROTECTION_RECOVERY = "PROTECTION_RECOVERY"
CALM_STATES = ("NO_ACTION", "NORMAL_REPLENISHMENT", "CAPITAL_OPTIMIZATION")
# The P1 purchasing frontier for the one calm state whose frozen set lacked the scenario plan. The
# other calm states keep their existing sets (see the pre-registration, section 7).
PURCHASING_MINIMUM = {"NO_ACTION": ("deterministic_network", "stochastic_network")}


def is_protection_mandate(stress: Stress) -> bool:
    """A declared envelope that is not the identity: the operator asks for protection against it."""
    return bool(stress.fill_multiplier < 1. or stress.extra_lead_days > 0 or stress.demand_multiplier != 1.)


def planner_owner(req: Request, protection: list[dict], screen_result: dict) -> dict:
    """Which planner owns this review, with every reason. Pure in its inputs."""
    reasons: list[str] = []
    if any(is_protection_mandate(s) for s in req.stresses):
        names = ", ".join(s.name for s in req.stresses if is_protection_mandate(s))
        reasons.append(f"declared protection mandate: stress envelope(s) {names} are not the identity")
    if not req.adaptive_escalation:
        reasons.append("adaptive escalation is off: the legacy full candidate set is the frozen path")
    state = screen_result.get("state")
    if state not in CALM_STATES:
        reasons.append(f"the screen classified the review as {state}")
    for row in protection:
        st = row["state"]
        loc = f"{row['sku']}@{row['location']}"
        if st.get("risk_active") or float(st.get("activity", 0.)) > .05:
            reasons.append(f"{loc}: a risk driver is active (activity {float(st.get('activity', 0.)):.2f})")
        if st.get("decaying"):
            reasons.append(f"{loc}: a risk driver is decaying, protection is still being unwound")
        if st.get("regime") not in (None, "LEAN"):
            reasons.append(f"{loc}: regime {st.get('regime')}")
        if st.get("demand_decline_confirmed"):
            reasons.append(f"{loc}: a confirmed demand decline is being run down")
        if "FALSE_PROTECTION_RISK" in (st.get("flags") or []):
            reasons.append(f"{loc}: inherited protection under management (FALSE_PROTECTION_RISK)")
    if screen_result.get("joint_recovery_required_by_rule"):
        reasons.append("the service-first joint recovery plan is required by rule")
    if float(screen_result.get("incumbent_service_deficit") or 0.) > 0.:
        reasons.append(f"the incumbent is projected to miss a service target by {float(screen_result['incumbent_service_deficit']):.3f}")
    owner = PROTECTION_RECOVERY if reasons else PURCHASING_ECONOMICS
    if owner == PURCHASING_ECONOMICS:
        reasons.append("no declared protection mandate, calm screen state, no active or decaying driver, every SKU/location lean, no recovery obligation")
    return {"owner": owner, "reasons": reasons,
            "scope": "decided before candidate assembly from the declared stress envelopes, the screen state, the per-SKU/location risk state and the recovery rule; never from a fixture, cell, seed or outcome"}


def purchasing_candidates(state: str, required: list[str], optional: list[str]) -> tuple[list[str], list[str], list[str]]:
    """The P1 purchasing frontier for a P1-owned review: the frozen sets plus the classes the
    purchasing planner needs. Returns (required, optional, added)."""
    added = [c for c in PURCHASING_MINIMUM.get(state, ()) if c not in required and c not in optional]
    return required + added, optional, added
