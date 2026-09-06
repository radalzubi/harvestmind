"""Incumbent-first continuous optimizer portfolio, held-out AND misspecification gates."""
from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import json
from statistics import mean

import numpy as np

from zaad.full import VERSION
from zaad.full.contracts import Request
from zaad.full.eta import conditional_eta
from zaad.full.model import Solution, solve
from zaad.full.settlement import PhysicalViolation, settle
from zaad.full.worlds import dates, draw, forecast_all


def targets(req: Request, buffer: float = 1.645) -> dict:
    fits = forecast_all(req)
    stock = {(s.id, location_key.id): sum(x.usable for x in req.stock if x.sku == s.id and x.location == location_key.id)
             for s in req.skus for location_key in req.locations}
    pending, orders = [], {}
    sources = {s.id: s for s in req.sources}
    for po in req.pipeline:
        source = sources[po.source]
        pending.append((source.sku, source.destination, next(o.due_in for o in po.options if o.action == "keep"), po.expected_accepted_remaining))
    for t in range(req.horizon):
        for sku, location in stock:
            stock[sku, location] += sum(q for k, location_key, due, q in pending if k == sku and location_key == location and due == t)
            services = [s for s in req.services if s.sku == sku and s.location == location]
            mu = sum(fits[s.id]["mean"] for s in services)
            sd = sum(fits[s.id]["sd"] ** 2 for s in services) ** .5
            eligible = sorted((s for s in req.sources if s.sku == sku and s.destination == location and s.approved and s.compliance == "cleared"),
                              key=lambda s: (s.unit_price + s.freight_per_unit + s.handling_per_unit, s.id))
            for source in eligible:
                lead = dates(req, source, t)[1] - t
                target = mu * (lead + 1) + buffer * sd * (lead + 1) ** .5
                book = sum(q for k, location_key, due, q in pending if k == sku and location_key == location and t < due <= t + lead + 1)
                q = max(0., target - stock[sku, location] - book) / source.fill_mean
                q = min(source.capacity_by_period[t], source.maximum, q)
                orders[source.id, t] = q
                pending.append((sku, location, t + lead, q * source.fill_mean))
            stock[sku, location] = max(0., stock[sku, location] - mu)
    for source in req.sources:
        for t in range(req.horizon):
            orders.setdefault((source.id, t), 0.)
    return orders


def evaluate(req, solution, worlds):
    rows = []
    for world in worlds:
        try:
            result = settle(req, solution, world)
            rows.append({"world": world.name, "usable": True, **result})
        except PhysicalViolation as exc:
            rows.append({"world": world.name, "usable": False, "reason": str(exc)})
    return rows


def _service_value(req: Request, rows: list[dict], service) -> float | None:
    if not rows or any(not row["usable"] for row in rows):
        return None
    if service.metric != "unit_fill":
        values = [r["order_metrics"][service.id].get(service.metric) for r in rows]
        if any(v is None for v in values):
            return None
        return mean(values)
    demand = sum(x["demand"] for r in rows for x in r["service_by_period"] if x["service"] == service.id)
    served = sum(x["served"] for r in rows for x in r["service_by_period"] if x["service"] == service.id)
    return served / demand if demand else 1.0


def service_ok(req, rows):
    if not rows or any(not row["usable"] for row in rows):
        return False
    for service in req.services:
        value = _service_value(req, rows, service)
        if value is None or value < service.target - 1e-6:
            return False
    return True


def weighted_shortfall(req: Request, rows: list[dict]) -> float:
    """Priority-weighted normalized SLA shortfall; infinity means physically unusable."""
    if not rows or any(not row["usable"] for row in rows):
        return float("inf")
    priorities = {c.id: c.priority for c in req.customers}
    total = 0.0
    for service in req.services:
        value = _service_value(req, rows, service)
        if value is None:
            return float("inf")
        total += priorities[service.customer] * max(0.0, service.target - value)
    return total


def material_shortfall_gap(req: Request) -> float:
    """The smallest weighted-shortfall reduction that counts as a real improvement: the
    configured service tolerance applied across every priority-weighted service."""
    priorities = {c.id: c.priority for c in req.customers}
    return max(1e-6, req.service_tolerance * sum(priorities[s.customer] for s in req.services))


def _recovery_not_worse(req: Request, before: list[dict], after: list[dict]) -> bool:
    """Recovery may miss an impossible SLA, but must reduce the aggregate weighted shortfall by a
    material amount on every physically usable world set. Infinite (unusable) never qualifies."""
    before_gap, after_gap = weighted_shortfall(req, before), weighted_shortfall(req, after)
    return bool(np.isfinite(after_gap)) and after_gap + material_shortfall_gap(req) <= before_gap


def _priority_consistent(req: Request, before: list[dict], after: list[dict]) -> bool:
    """A recovery may lower a service only to raise a strictly higher-priority one. Any service
    that falls by more than the tolerance without such a beneficiary is a hidden sacrifice."""
    if not before or not after or len(before) != len(after):
        return False
    priorities = {c.id: c.priority for c in req.customers}
    worsened, improved = set(), set()
    for service in req.services:
        a = _service_value(req, before, service)
        b = _service_value(req, after, service)
        if a is None or b is None:
            continue
        if b < a - req.service_tolerance:
            worsened.add(service.id)
        elif b > a + req.service_tolerance:
            improved.add(service.id)
    best_improved = max((priorities[s.customer] for s in req.services if s.id in improved), default=None)
    for service in req.services:
        if service.id in worsened and (best_improved is None or priorities[service.customer] >= best_improved):
            return False
    return True


def _within_downside(req: Request, before: list[dict], after: list[dict]) -> bool:
    """Per-world economic downside cap against the incumbent, on usable worlds only."""
    if not before or not after or len(before) != len(after):
        return False
    for a, b in zip(before, after):
        if not a["usable"] or not b["usable"]:
            return False
        if b["economic_cost"] - a["economic_cost"] > req.downside_cost_tolerance * max(abs(a["economic_cost"]), 1.):
            return False
    return True


def summarize(rows):
    valid = [r for r in rows if r["usable"]]
    return {"runs": len(rows), "physical_failures": len(rows) - len(valid),
            "cost_mean": mean(r["economic_cost"] for r in valid) if valid else None,
            "cost_min": min((r["economic_cost"] for r in valid), default=None),
            "cost_max": max((r["economic_cost"] for r in valid), default=None),
            "weighted_service_shortfall": None,
            "failures": [r for r in rows if not r["usable"]]}


def action_rows(solution):
    if solution is None:
        return []
    rows = [{"action": "purchase", "source": source, "period": t, "quantity": q, "first_review": t == 0}
            for (source, t), q in solution.purchases.items()]
    rows += [{"action": "transfer", "transfer": arc, "expiry_cohort": expiry, "period": t, "quantity": q, "first_review": t == 0}
             for (arc, expiry, t), q in solution.transfers.items()]
    rows += [{"action": "po_option", "po": po, "option": option, "period": 0, "quantity": q, "first_review": True}
             for (po, option), q in solution.amendments.items()]
    return rows


def plan(req: Request) -> dict:
    fits = forecast_all(req)
    selection = draw(req, req.seed, req.scenarios)
    deterministic = draw(req, req.seed, 1, deterministic=True)
    baseline_targets = targets(req)
    base = solve(req, deterministic, targets=baseline_targets)
    incumbent = base
    incumbent_label = "projected_base_stock_proxy"
    if req.incumbent_orders:
        declared = replace(base, status="OPTIMAL", purchases={(x.source, x.period): x.quantity for x in req.incumbent_orders},
                           transfers={}, amendments={(p.id, next(o.id for o in p.options if o.action == "keep")): p.remaining for p in req.pipeline})
        incumbent = solve(req, deterministic, fixed=declared)
        incumbent_label = "operator_declared"
    candidates = {"incumbent": incumbent, "base_stock": base,
                  "deterministic_network": solve(req, deterministic, service_floor=True),
                  "stochastic_network": solve(req, selection, service_floor=True),
                  "cvar_network": solve(req, selection, service_floor=True, cvar_weight=.2)}
    stress_worlds = []
    for i, stress in enumerate(req.stresses):
        stress_worlds += draw(req, req.seed + 100 + i, 1, stress)
    combined = [replace(w, weight=1 / (len(selection) + len(stress_worlds))) for w in selection + stress_worlds]
    candidates["stress_network"] = solve(req, combined, service_floor=True, per_world_service=True)
    recovery = solve(req, combined, service_first="all")
    if recovery.status == "OPTIMAL":
        candidates["joint_recovery"] = recovery

    selection_rows = {name: evaluate(req, candidate, selection) for name, candidate in candidates.items() if candidate.status == "OPTIMAL"}
    feasible = [name for name, rows in selection_rows.items() if service_ok(req, rows)]
    joint_rows = selection_rows.get("joint_recovery", [])
    # The target vector is jointly feasible when ANY candidate meets every service on the selection
    # worlds; the joint recovery solve is one more way to show it, not the only one.
    target_jointly_feasible = bool(feasible) or (bool(joint_rows) and service_ok(req, joint_rows))
    recovery_mode = not target_jointly_feasible
    recovery_ranking: list[dict] = []

    if feasible:
        chosen = min(feasible, key=lambda name: (mean(r["economic_cost"] for r in selection_rows[name]), list(candidates).index(name)))
    elif incumbent.status == "OPTIMAL":
        # Impossible SLA: rank every usable candidate by priority-weighted shortfall (cost breaks ties)
        # and take the best one only if it beats the incumbent by a material margin.
        incumbent_selection = selection_rows.get("incumbent", evaluate(req, incumbent, selection))
        for name, rows in selection_rows.items():
            if name == "incumbent":
                continue
            gap = weighted_shortfall(req, rows)
            recovery_ranking.append({"candidate": name, "weighted_service_shortfall": gap if np.isfinite(gap) else None,
                                     "cost_mean": mean(r["economic_cost"] for r in rows if r["usable"]) if any(r["usable"] for r in rows) else None,
                                     "materially_better_than_incumbent": _recovery_not_worse(req, incumbent_selection, rows)})
        usable = [r for r in recovery_ranking if r["weighted_service_shortfall"] is not None and r["materially_better_than_incumbent"]]
        if usable:
            best_candidate = min(usable, key=lambda r: (r["weighted_service_shortfall"], r["cost_mean"], list(candidates).index(r["candidate"])))
            chosen = best_candidate["candidate"]
        else:
            chosen = "incumbent"
    else:
        chosen = "incumbent"

    confirmation = draw(req, req.seed + 10000, req.scenarios)
    incumbent_rows = evaluate(req, incumbent, confirmation) if incumbent.status == "OPTIMAL" else []
    candidate_rows = evaluate(req, candidates[chosen], confirmation) if candidates[chosen].status == "OPTIMAL" else []
    reasons, stress_report = [], []
    benefit_lower = None

    if recovery_mode and chosen != "incumbent":
        # Independent confirmation of a recovery plan: physically usable on every world, a material
        # weighted-shortfall improvement, no hidden low-for-high service sacrifice, and inside the
        # economic downside cap. Absolute SLA gating does not apply to an impossible target.
        accepted = _recovery_not_worse(req, incumbent_rows, candidate_rows)
        if not accepted:
            reasons.append("Recovery candidate does not materially improve weighted service shortfall versus the incumbent under independent confirmation.")
        elif not _priority_consistent(req, incumbent_rows, candidate_rows):
            accepted = False
            reasons.append("Recovery candidate lowers a service without raising a higher-priority one; priority-weighted recovery rejected.")
        elif not _within_downside(req, incumbent_rows, candidate_rows):
            accepted = False
            reasons.append("Recovery candidate improves service but exceeds the configured economic downside tolerance.")
    elif recovery_mode:
        accepted = False
        reasons.append("No candidate materially improves priority-weighted service shortfall over the incumbent; incumbent retained.")
    else:
        accepted = chosen != "incumbent" and service_ok(req, candidate_rows) and bool(incumbent_rows) and all(r["usable"] for r in incumbent_rows)
        if accepted:
            difference = np.asarray([a["economic_cost"] - b["economic_cost"] for a, b in zip(incumbent_rows, candidate_rows)])
            rng = np.random.default_rng(req.seed + 20000)
            benefit_lower = float(np.quantile(np.mean(rng.choice(difference, (500, len(difference))), axis=1), .1))
            accepted = benefit_lower > 1e-6
            if not accepted:
                reasons.append("Independent fitted-model confirmation does not establish positive benefit.")

    for i, stress in enumerate(req.stresses):
        adversaries = draw(req, req.seed + 30000 + i, req.scenarios, stress)
        before = evaluate(req, incumbent, adversaries) if incumbent.status == "OPTIMAL" else []
        after = evaluate(req, candidates[chosen], adversaries) if candidates[chosen].status == "OPTIMAL" else []
        physically_ok = bool(after) and all(r["usable"] for r in after)
        downside_ok = physically_ok and bool(before) and all(r["usable"] for r in before)
        if downside_ok:
            for a, b in zip(before, after):
                scale = max(abs(a["economic_cost"]), 1.)
                if b["economic_cost"] - a["economic_cost"] > req.downside_cost_tolerance * scale:
                    downside_ok = False
                for s in req.services:
                    if a["service"][s.id] is not None and b["service"][s.id] is not None and b["service"][s.id] < a["service"][s.id] - req.service_tolerance:
                        downside_ok = False
        if recovery_mode:
            # Under stress a recovery plan must stay usable, within the cost cap, materially better on
            # weighted shortfall, and priority-consistent; the per-service no-worse rule would forbid
            # the very reallocation a priority-weighted recovery exists to make.
            pass_stress = (physically_ok and _within_downside(req, before, after)
                           and _recovery_not_worse(req, before, after) and _priority_consistent(req, before, after))
        else:
            pass_stress = downside_ok and service_ok(req, after)
        accepted &= pass_stress
        stress_report.append({"stress": stress.model_dump(), "pass": pass_stress,
                              "incumbent": {**summarize(before), "weighted_service_shortfall": weighted_shortfall(req, before)},
                              "candidate": {**summarize(after), "weighted_service_shortfall": weighted_shortfall(req, after)}})
    if any(not x["pass"] for x in stress_report):
        reasons.append("Out-of-model stress confirmation rejected physical feasibility, downside risk, or required service recovery.")

    candidate_gates = {chosen: {"accepted": bool(accepted), "stress": stress_report}}
    if not recovery_mode and not accepted:
        for alternative in sorted((n for n in feasible if n not in {chosen, "incumbent"}),
                                  key=lambda n: mean(r["economic_cost"] for r in selection_rows[n])):
            rows = evaluate(req, candidates[alternative], confirmation)
            passes = service_ok(req, rows) and bool(incumbent_rows) and all(r["usable"] for r in incumbent_rows)
            lower = None
            if passes:
                diff = np.asarray([a["economic_cost"] - b["economic_cost"] for a, b in zip(incumbent_rows, rows)])
                rng = np.random.default_rng(req.seed + 20000)
                lower = float(np.quantile(np.mean(rng.choice(diff, (500, len(diff))), axis=1), .1))
                passes = lower > 1e-6
            checks = []
            for i, stress in enumerate(req.stresses):
                worlds = draw(req, req.seed + 30000 + i, req.scenarios, stress)
                before = evaluate(req, incumbent, worlds) if incumbent.status == "OPTIMAL" else []
                after = evaluate(req, candidates[alternative], worlds)
                valid = service_ok(req, after) and bool(before) and all(r["usable"] for r in before)
                if valid:
                    for a, b in zip(before, after):
                        if b["economic_cost"] - a["economic_cost"] > req.downside_cost_tolerance * max(abs(a["economic_cost"]), 1.):
                            valid = False
                        for service in req.services:
                            sa, sb = a["service"][service.id], b["service"][service.id]
                            if sa is not None and sb is not None and sb < sa - req.service_tolerance:
                                valid = False
                passes &= valid
                checks.append({"stress": stress.model_dump(), "pass": bool(valid), "incumbent": summarize(before), "candidate": summarize(after)})
            candidate_gates[alternative] = {"accepted": bool(passes), "stress": checks}
            if passes:
                chosen, accepted, candidate_rows, stress_report, benefit_lower = alternative, True, rows, checks, lower
                reasons = ["Cheaper candidate failed the gate; the next qualified candidate passed independent and stress confirmation."]
                break

    if req.force_unit_fills:
        accepted = False
        reasons.append("Unit-fill regression control cannot open approval gate.")
    if req.evidence_label == "OPERATOR-SHADOW" and not req.incumbent_orders:
        accepted = False
        reasons.append("Operator incumbent is missing; a synthetic proxy is not evidence against the customer's policy.")

    status = "PENDING_REVIEW" if accepted else "RETAIN_INCUMBENT"
    final: Solution | None = candidates[chosen] if accepted else incumbent
    if incumbent.status != "OPTIMAL":
        status, final = "ABSTAIN", None
        reasons.append("Incumbent itself has no verified feasible projection; no executable fallback is fabricated.")
    if recovery_mode:
        reasons.append("Requested service targets are not jointly achievable under the modeled state; selector evaluated best joint recovery instead of requiring an impossible SLA.")
    elif not feasible:
        reasons.append("No selection candidate achieves every requested service metric.")

    frontier = []
    for service in req.services:
        oracle = solve(req, deterministic, service_first=service.id)
        best = oracle.projected_service.get(service.id)
        frontier.append({"service": service.id, "requested": service.target, "metric": service.metric,
                         "best_modeled_individual_unit_fill": best,
                         "selected_modeled_unit_fill": final.projected_service.get(service.id) if final else None,
                         "unavoidable_gap_under_mean_world": max(0., service.target - best) if best is not None and service.metric == "unit_fill" else None,
                         "bound_scope": "single-service physical/financial optimum under mean world, not a guarantee or simultaneous bound"})

    eta = {p.id: asdict(conditional_eta(req.shipment_history, p.source, max(0, (req.as_of - p.placed_at).days), p.stage, p.carrier)) for p in req.pipeline}
    fingerprint = hashlib.sha256(req.model_dump_json().encode()).hexdigest()
    recovery_rows = evaluate(req, recovery, confirmation) if recovery.status == "OPTIMAL" else []
    return {"schema_version": "zaad.network.report.v2", "brand": "ZAAD", "version": VERSION,
            "operator_id": req.operator_id, "as_of": req.as_of.isoformat(), "information_hash": fingerprint,
            "evidence_label": req.evidence_label, "status": status, "mode": "ALLOCATE" if recovery_mode else req.mode,
            "selected_policy": chosen if accepted else incumbent_label,
            "actions": action_rows(final), "incumbent_actions": action_rows(incumbent),
            "approval_required": True, "executable_purchase_order": False,
            "forecasts": fits, "eta": eta, "service_frontier": frontier,
            "joint_service_feasibility": {"target_vector_feasible": target_jointly_feasible,
                "recovery_mode": recovery_mode, "material_gap": material_shortfall_gap(req),
                "recovery_ranking": recovery_ranking,
                "incumbent_weighted_shortfall": weighted_shortfall(req, incumbent_rows),
                "recovery_weighted_shortfall": weighted_shortfall(req, recovery_rows),
                "selected_weighted_shortfall": weighted_shortfall(req, evaluate(req, final, confirmation)) if final else None,
                "scope": "joint priority-weighted modeled shortfall under independent confirmation; not a guaranteed ex-post frontier"},
            "cash": final.cash if final else [], "reasons": reasons,
            "confirmation_benefit_lower": benefit_lower,
            "confirmation": {"incumbent": {**summarize(incumbent_rows), "weighted_service_shortfall": weighted_shortfall(req, incumbent_rows)},
                             "candidate": {**summarize(candidate_rows), "weighted_service_shortfall": weighted_shortfall(req, candidate_rows)}},
            "stress_confirmation": stress_report,
            "candidate_gates": candidate_gates,
            "recovery_guidance": {"status": recovery.status, "actions": action_rows(recovery),
                                  "projected_unit_fill": recovery.projected_service,
                                  "weighted_service_shortfall": weighted_shortfall(req, recovery_rows),
                                  "warning": "Best priority-weighted modeled service with minimum-cost tie-break; approval still depends on independent and stress confirmation."} if recovery.status == "OPTIMAL" else None,
            "candidates": {name: {"status": c.status, "solve_seconds": c.solve_seconds, "variables": c.variables,
                "constraints": c.constraints, "gap": c.gap, "residual": c.residual,
                "selection": summarize(selection_rows.get(name, []))} for name, c in candidates.items()},
            "limitations": ["Synthetic evidence is not customer validation.", "Stress envelopes are assumptions, not calibrated guarantees.",
                "Only period-zero actions may be reviewed; future actions are replanning guidance.",
                "Cash excludes forecast sales receipts; enter only dated known receivables.",
                "A retained incumbent is not certified safe when it also fails the reported stress tests."]}


def report_json(report: dict) -> str:
    return json.dumps(report, sort_keys=True, allow_nan=False)