"""Operator-facing adaptive recourse block (P4): comparators, value of adaptation, the information
sets in operator language and the policy per review epoch. No world names, node ids or column names
in the operator part; they live in the engineering part."""
from __future__ import annotations

from typing import Any

from zaad.recourse.contracts import Recourse
from zaad.recourse.information import PENDING
from zaad.recourse.policy import lookup_exactness

PRINCIPLE = ("Commit only what must be committed now; keep flexibility where waiting has economic value; adapt to "
             "observed information, never to scenario labels.")


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
    elif not result["ordering_ok"]:
        verdict = "ADAPTIVE PLAN REJECTED (ordering check failed)"
    elif not result["material"]:
        verdict = "NO MATERIAL ADAPTIVE BENEFIT"
    elif selected:
        verdict = "ADAPTIVE PLAN SELECTED"
    else:
        verdict = "ADAPTIVE PLAN NOT SELECTED (a static candidate passed the gates at lower settled cost)"
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
    return {"version": "zaad.recourse.1.0", "principle": PRINCIPLE, "verdict": verdict, "selected": selected,
            "static_expected_cost": static.projected_cost, "adaptive_expected_cost": adaptive.projected_cost,
            "perfect_information_cost": (perfect.projected_cost if perfect is not None and perfect.usable_plan else None),
            "perfect_information_scope": "lower bound only: every world acts with full foresight; never a recommendation",
            "value_of_adaptation": result["value_of_adaptation"], "material": result["material"],
            "materiality_cost_fraction": req.materiality_cost_fraction, "ordering_ok": result["ordering_ok"],
            "non_anticipativity": result["non_anticipativity"],
            "review_periods": list(recourse.epochs), "observables": list(spec.observables), "actions": list(spec.actions),
            "committed_now": committed, "policy": epochs_out, "explanations": sentences,
            "approval_required": True, "executable_purchase_order": False,
            "engineering": {"worlds": len(selection), "information_sets": {e: [{"id": s.id, "members": list(s.members), "probability": s.probability} for s in v] for e, v in nodes.sets.items()},
                            "policy_lookup_on_confirmation_worlds": lookups,
                            "adaptive_solve": {"status": adaptive.status, "variables": adaptive.variables, "constraints": adaptive.constraints, "seconds": adaptive.solve_seconds, "nodes": adaptive.nodes, "gap": adaptive.gap},
                            "static_solve": {"status": static.status, "variables": static.variables, "constraints": static.constraints, "seconds": static.solve_seconds, "built_as_comparator": result["static_built_as_comparator"]},
                            "perfect_solve": ({"status": perfect.status, "variables": perfect.variables, "seconds": perfect.solve_seconds} if perfect is not None else None)}}
