"""Operator-facing adaptive recourse block (P4): comparators, value of adaptation, the information
sets in operator language and the policy per review epoch. No world names, node ids or column names
in the operator part; they live in the engineering part."""
from __future__ import annotations

from typing import Any

from zaad.recourse.contracts import Recourse
from zaad.recourse.information import PENDING
from zaad.recourse.policy import CERTIFIED, NON_CERTIFIED, REPLAN_REQUIRED, lookup_exactness

PRINCIPLE = ("Commit only what must be committed now; keep flexibility where waiting has economic value; adapt to "
             "observed information, never to scenario labels.")
UNSEEN_OBSERVATION_RULE = (f"{REPLAN_REQUIRED}: an observation at a review period that matches none of the modelled branches "
                           "executes no adaptive action; the static commitments stand for that window and a replan is required "
                           "before any change. There is no nearest-branch routing.")
PI_SCOPE = {CERTIFIED: "certified lower bound (proven optimal): every world acts with full foresight; never a recommendation",
            NON_CERTIFIED: ("feasible time-limited perfect-information plan: not proven optimal, reported as a feasible cost only "
                            "and excluded from the ordering check; never a recommendation"),
            "UNAVAILABLE": "perfect-information diagnostic not available (not solved or no usable plan); never a recommendation"}


def _condition(req, recourse: Recourse, signature: tuple, epoch: int) -> list[str]:
    """The observable condition of an information set in operator language."""
    spec = recourse.spec
    sentences: list[str] = []
    for part in signature:
        if part[0] == "demand":
            _, service, cells = part
            total = sum(cells) * spec.demand_grid
            sentences.append(f"confirmed demand for {service} through period {epoch - 1} of about {total:,.0f} units")
        elif part[0] == "receipt":
            _, source, placed, *rest = part
            if rest and rest[0] == PENDING:
                sentences.append(f"the {source} order of period {placed} not yet received")
            elif rest:
                due, fill = rest
                sentences.append(f"the {source} order of period {placed} received in period {due} at about {fill * spec.fill_grid:.0%} fill")
        elif part[0] == "po":
            _, order, *rest = part
            if rest and rest[0] == PENDING:
                sentences.append(f"open order {order} not yet received")
            elif rest:
                due, fill = rest
                sentences.append(f"open order {order} received in period {due} at about {fill * spec.fill_grid:.0%} fill")
    # collapse identical receipt sentences for readability
    seen: list[str] = []
    for x in sentences:
        if x not in seen:
            seen.append(x)
    return seen


def _window(recourse: Recourse, epoch: int, H: int) -> list[int]:
    later = [e for e in recourse.epochs if e > epoch]
    return list(range(epoch, later[0] if later else H))


def _totals(plan: dict, keys: list, window: list[int]) -> dict[str, float]:
    out: dict[str, float] = {}
    for key in keys:
        if key[-1] in window:
            label = key[0]
            out[label] = out.get(label, 0.) + plan.get(key, 0.)
    return out


def recourse_block(req, recourse: Recourse, result: dict[str, Any], report: dict, selection: list, confirmation: list) -> dict[str, Any]:
    spec = recourse.spec
    nodes = result["nodes"]
    static, adaptive, perfect = result["static"], result["adaptive"], result["perfect"]
    H = req.horizon
    selected = report.get("selected_policy") == "adaptive_network"
    if not adaptive.usable_plan:
        verdict = "ADAPTIVE PLAN UNAVAILABLE"
    elif result["ordering_ok"] is None:
        # no static comparator plan (infeasible, or none found within the budget): nothing to order against
        verdict = "ADAPTIVE PLAN NOT COMPARABLE (no static comparator plan: infeasible or not found within the time budget)"
    elif not result["ordering_ok"]:
        # a certified violation is a genuine failure; a time-limited adaptive incumbent dearer than the
        # static plan is not an ordering violation, it is a solve that did not improve on the static plan
        verdict = ("ADAPTIVE PLAN REJECTED (ordering check failed)" if adaptive.status == "OPTIMAL"
                   else "ADAPTIVE PLAN NOT SELECTED (time-limited adaptive solve did not improve on the static plan)")
    elif not result["material"]:
        verdict = "NO MATERIAL ADAPTIVE BENEFIT"
    elif selected:
        verdict = "ADAPTIVE PLAN SELECTED"
    else:
        verdict = "ADAPTIVE PLAN NOT SELECTED (a static candidate passed the gates at lower settled cost)"
    pi_status = result.get("perfect_status", "UNAVAILABLE")
    committed_periods = list(range(0, recourse.first_epoch if recourse.first_epoch is not None else H))
    committed = {"periods": committed_periods,
                 "purchases": [{"source": k[0], "period": k[1], "quantity": round(q, 3)} for k, q in sorted(adaptive.purchases.items()) if q > 1e-9],
                 "transfers": [{"lane": k[0], "period": k[2], "quantity": round(q, 3)} for k, q in sorted(adaptive.transfers.items()) if q > 1e-9]}
    epochs_out: list[dict[str, Any]] = []
    static_purchases = dict(static.purchases) if static.usable_plan else {}
    for epoch in recourse.epochs:
        window = _window(recourse, epoch, H)
        sets_out = []
        for info in nodes.sets[epoch]:
            plan = adaptive.recourse["nodes"].get(info.id, {"purchases": {}, "transfers": {}}) if adaptive.recourse else {"purchases": {}, "transfers": {}}
            buys = _totals(plan["purchases"], list(plan["purchases"]), window)
            moves = _totals({k: v for k, v in plan["transfers"].items()}, [(k[0], k[2]) for k in plan["transfers"]], window) if plan["transfers"] else {}
            moves = {}
            for (arc, _e, t), q in plan["transfers"].items():
                if t in window:
                    moves[arc] = moves.get(arc, 0.) + q
            static_buys = _totals(static_purchases, [k for k in static_purchases], window)
            why = []
            for source, q in sorted(buys.items()):
                base = static_buys.get(source, 0.)
                if abs(q - base) > 1e-6:
                    why.append(f"buys {q:,.0f} units from {source} over periods {window[0]}-{window[-1]} against {base:,.0f} in the static plan")
            for source, base in sorted(static_buys.items()):
                if source not in buys and base > 1e-6:
                    why.append(f"places no {source} order over periods {window[0]}-{window[-1]} against {base:,.0f} in the static plan")
            sets_out.append({"probability": round(info.probability, 6), "condition": _condition(req, recourse, info.signature, epoch),
                             "purchases": {k: round(v, 3) for k, v in sorted(buys.items())}, "transfers": {k: round(v, 3) for k, v in sorted(moves.items())},
                             "difference_from_static": why or ["same commitments as the static plan in this branch"]})
        epochs_out.append({"review_period": epoch, "window": [window[0], window[-1]], "information_sets": len(nodes.sets[epoch]),
                           "observed_before_review": [o for o in spec.observables], "branches": sets_out})
    sentences: list[str] = []
    if recourse.first_epoch is not None:
        sentences.append(f"Commit periods 0-{recourse.first_epoch - 1} now; reassess at period {', '.join(str(e) for e in recourse.epochs)} "
                         f"on {' and '.join(spec.observables)} confirmed by then.")
    if result["value_of_adaptation"] is not None and static.projected_cost:
        sentences.append(f"Keeping the later periods flexible is worth {result['value_of_adaptation']:,.0f} against the best static plan on the same worlds "
                         f"({result['value_of_adaptation'] / abs(static.projected_cost):.2%} of its expected cost), "
                         f"{'above' if result['material'] else 'below'} the declared materiality of {req.materiality_cost_fraction:.1%}.")
    if verdict == "NO MATERIAL ADAPTIVE BENEFIT":
        sentences.append("The static plan stands: adapting later would not change the economics materially.")
    lookups = lookup_exactness(req, recourse, nodes, confirmation) if nodes is not None else []
    replan = [row["world"] for row in lookups if row["replan_required"]]
    if replan:
        sentences.append(f"{len(replan)} of {len(lookups)} evaluation worlds carry an observation outside the modelled branches: "
                         "they were evaluated under the static commitments (no adaptive action; replan required).")
    if pi_status == NON_CERTIFIED:
        sentences.append("The perfect-information solve was not proven optimal within the time budget: its cost is reported as a "
                         "feasible plan cost, not as a bound.")
    if not result.get("value_certified", True) and result["value_of_adaptation"] is not None:
        sentences.append("The value of adaptation compares plans that were not both proven optimal (time-limited solve); it is a "
                         "diagnostic against the best static plan found, not a certified difference.")
    return {"version": "zaad.recourse.1.1", "principle": PRINCIPLE, "verdict": verdict, "selected": selected,
            "static_expected_cost": static.projected_cost, "adaptive_expected_cost": adaptive.projected_cost,
            "perfect_information_status": pi_status,
            "perfect_information_cost": result.get("perfect_cost"),
            "perfect_information_feasible_cost": result.get("perfect_feasible_cost"),
            "perfect_information_scope": PI_SCOPE.get(pi_status, PI_SCOPE["UNAVAILABLE"]),
            "value_of_adaptation": result["value_of_adaptation"], "value_of_adaptation_certified": result.get("value_certified"),
            "material": result["material"],
            "materiality_cost_fraction": req.materiality_cost_fraction, "ordering_ok": result["ordering_ok"],
            "ordering_scope": ("adaptive <= static" + (" and certified perfect-information <= adaptive" if pi_status == CERTIFIED else "")
                               + " within the solver tolerance"),
            "non_anticipativity": result["non_anticipativity"],
            "review_periods": list(recourse.epochs), "observables": list(spec.observables), "actions": list(spec.actions),
            "committed_now": committed, "policy": epochs_out, "explanations": sentences,
            "unseen_observation_rule": UNSEEN_OBSERVATION_RULE,
            "replan_required": {"worlds": len(replan), "of": len(lookups), "fallback": "static commitments" if (adaptive.recourse or {}).get("fallback", {}).get("available") else "none available (static plan infeasible)"},
            "approval_required": True, "executable_purchase_order": False,
            "engineering": {"worlds": len(selection), "information_sets": {e: [{"id": s.id, "members": list(s.members), "probability": s.probability} for s in v] for e, v in nodes.sets.items()},
                            "policy_lookup_on_evaluation_worlds": lookups,
                            "solve_status": result.get("solve_status"),
                            "adaptive_solve": {"status": adaptive.status, "variables": adaptive.variables, "constraints": adaptive.constraints, "seconds": adaptive.solve_seconds, "nodes": adaptive.nodes, "gap": adaptive.gap},
                            "static_solve": {"status": static.status, "variables": static.variables, "constraints": static.constraints, "seconds": static.solve_seconds, "built_as_comparator": result["static_built_as_comparator"]},
                            "perfect_solve": ({"status": perfect.status, "certified": pi_status == CERTIFIED, "variables": perfect.variables, "seconds": perfect.solve_seconds,
                                               "gap": perfect.gap,
                                               "solver_objective_bound": result.get("perfect_solver_bound"),
                                               "solver_objective_bound_units": "HiGHS dual bound on the solver objective (ledger cost plus objective-only terms); not comparable with the expected costs above and never a policy cost"}
                                              if perfect is not None else None)}}
