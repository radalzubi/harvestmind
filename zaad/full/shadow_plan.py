"""Shadow evaluation of fixed plans on the planner's own worlds (HARDENING V1, H3b).

Two plans are compared under identical assumptions: the operator's captured plan and ZAAD's recommended
actions are both settled as fixed solutions on the same scenario worlds the planner drew for the request
(same fits, same seed, same draw), through the same settlement, with no terminal credit on either side.
Nothing here changes how the planner decides; it only scores two given plans the same way. The result is a
modelled difference on simulated worlds, never a realized outcome.
"""
from __future__ import annotations

from typing import Any

from zaad.full.contracts import Request
from zaad.full.economics import mean_breakdown
from zaad.full.model import Solution
from zaad.full.planner import _service_value, evaluate
from zaad.full.policies import _keep_amendments
from zaad.full.protection import protection_profile
from zaad.full.uncertainty import supply_profiles
from zaad.full.worlds import draw, forecast_all

BASIS = "both plans settled as fixed solutions on the planner's selection worlds (same fits, seed and draw as the recommendation), no terminal credit; simulated, not observed"


def fixed_solution(req: Request, purchases: dict[tuple[str, int], float], note: str) -> Solution:
    """A fixed order set as a settleable plan: the purchases as given and every open order kept."""
    return Solution("OPTIMAL", {k: float(q) for k, q in purchases.items() if q > 0 and 0 <= k[1] < req.horizon}, {}, _keep_amendments(req), {}, None, [], 0.0, 0, 0, None, None, [note])


def selection_worlds(req: Request):
    """The planner's selection worlds for this request, drawn exactly as `planner.plan` draws them."""
    fits = forecast_all(req)
    protection = protection_profile(req, fits, supply_profiles(req))
    lean_profile = all(float(row["state"]["activity"]) <= .05 for row in protection)
    req_draw = req if (lean_profile or not req.stratified_scenarios) else req.model_copy(update={"stratified_scenarios": False})
    return fits, draw(req_draw, req.seed, req.scenarios)


def evaluate_plans(req: Request, plans: dict[str, dict[tuple[str, int], float]]) -> dict[str, Any]:
    """Settle each named plan on the same worlds. Returns per plan the cost breakdown (None when any world
    is unusable), the expected service per service line, the purchases, and the shared basis."""
    fits, worlds = selection_worlds(req)
    out: dict[str, Any] = {"basis": BASIS, "worlds": len(worlds), "seed": req.seed, "plans": {}}
    for name, purchases in plans.items():
        solution = fixed_solution(req, purchases, f"shadow:{name}")
        rows = evaluate(req, solution, worlds, fits=fits)
        usable = [r for r in rows if r.get("usable")]
        out["plans"][name] = {
            "costs": mean_breakdown(rows),
            "usable_worlds": len(usable), "unusable_reasons": sorted({str(r.get("reason")) for r in rows if not r.get("usable")}),
            "service": {s.id: _service_value(req, rows, s) for s in req.services},
            "purchases": {f"{src}|{t}": q for (src, t), q in sorted(solution.purchases.items())},
            "units": float(sum(solution.purchases.values())),
        }
    return out
