"""Incumbent-first continuous optimizer portfolio, held-out AND misspecification gates.

Selection order is LEAN -> PROTECT -> ALLOCATE -> RECOVER -> LEAN: the cheapest plan that
meets every service target is chosen when the targets are achievable; a plan that meets a
target the incumbent misses is accepted within the economic downside cap even when it is not
cheaper; when the targets are jointly impossible the best priority-weighted recovery is
ranked; and protection is expected to disappear when the scenario spread tightens again.
"""
from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import json
from statistics import mean
from typing import Any

import numpy as np

from zaad.full import VERSION
from zaad.full.contracts import Request
from zaad.full.eta import conditional_eta
from zaad.full.model import Solution, solve
from zaad.full.protection import protection_profile
from zaad.full.settlement import PhysicalViolation, settle
from zaad.full.uncertainty import profile_dict, stress_credibility, supply_profiles
from zaad.full.worlds import dates, draw, forecast_all


def targets(req: Request, buffer: float = 1.645) -> dict:
    """Projected base-stock proxy. Under the reliability profile the buffer is the per-SKU/location
    protection quantile with calibrated demand spread, level error and lead-time spread; the
    frozen profile keeps the universal 1.645 factor. A zero buffer stays zero in both."""
    fits = forecast_all(req)
    reliability = req.engine_profile == "reliability" and buffer > 0
    profile = {(row["sku"], row["location"]): row for row in protection_profile(req, fits, supply_profiles(req))} if reliability else {}
    stock = {(s.id, location_key.id): sum(x.usable for x in req.stock if x.sku == s.id and x.location == location_key.id)
             for s in req.skus for location_key in req.locations}
    pending, orders = [], {}
    sources = {s.id: s for s in req.sources}
    for po in req.pipeline:
        source = sources[po.source]
        pending.append((source.sku, source.destination, next(o.due_in for o in po.options if o.action == "keep"), po.expected_accepted_remaining))
    # Echelon demand: a location with no direct source but an approved inbound transfer arc is
    # supplied through its origin, so the proxy orders that demand upstream (and the fixed
    # solve moves it down). Otherwise a central DC with no customers of its own buys nothing
    # and every branch starves, which is what the frozen proxy did on central-plus-branch cells.
    direct = {(s.sku, s.destination) for s in req.sources if s.approved and s.compliance == "cleared"}
    upstream: dict[tuple[str, str], list[str]] = {}
    for arc in req.transfers:
        if arc.approved and (arc.sku, arc.destination) not in direct and (arc.sku, arc.origin) in direct:
            upstream.setdefault((arc.sku, arc.destination), []).append(arc.origin)
    for t in range(req.horizon):
        for sku, location in stock:
            stock[sku, location] += sum(q for k, location_key, due, q in pending if k == sku and location_key == location and due == t)
            services = [s for s in req.services if s.sku == sku and s.location == location]
            fed = [s for (k, dest), origins in upstream.items() for s in req.services if k == sku and s.sku == sku and s.location == dest and location in origins]
            services = services + [s for s in fed if s not in services]
            mu = sum(fits[s.id]["mean"] for s in services)
            if req.protection_v6:
                # Fed demand counts at the origin only up to what the arc can carry per period;
                # buying for demand a constrained arc cannot deliver only piles stock at the origin.
                for s in fed:
                    arc_capacity = max((a.capacity for a in req.transfers if a.approved and a.sku == sku and a.destination == s.location and a.origin == location), default=float("inf"))
                    mu -= max(0., fits[s.id]["mean"] - arc_capacity)
            row = profile.get((sku, location))
            if row is not None:
                z = row["quantile_z"]
                sd = sum(fits[s.id]["uncertainty"]["sd_effective"] ** 2 for s in services) ** .5
                level_se = sum(fits[s.id]["uncertainty"]["level_se"] ** 2 for s in services) ** .5
            else:
                z = buffer
                sd = sum(fits[s.id]["sd"] ** 2 for s in services) ** .5
                level_se = 0.
            eligible = sorted((s for s in req.sources if s.sku == sku and s.destination == location and s.approved and s.compliance == "cleared"),
                              key=lambda s: (s.unit_price + s.freight_per_unit + s.handling_per_unit, s.id))
            for source in eligible:
                lead = dates(req, source, t)[1] - t
                window = lead + 1
                if row is not None:
                    lead_sd = source.lead_sd_days / req.period_days
                    spread = (window * sd ** 2 + (window * level_se) ** 2 + (mu * lead_sd) ** 2) ** .5
                    target = mu * window + z * spread
                else:
                    target = mu * window + z * sd * window ** .5
                book = sum(q for k, location_key, due, q in pending if k == sku and location_key == location and t < due <= t + lead + 1)
                q = max(0., target - stock[sku, location] - book) / source.fill_mean
                q = min(source.capacity_by_period[t], source.maximum, q)
                orders[source.id, t] = q
                pending.append((sku, location, t + lead, q * source.fill_mean))
            stock[sku, location] = max(0., stock[sku, location] - mu)
    for source in req.sources:
        for t in range(req.horizon):
            orders.setdefault((source.id, t), 0.)
    if req.protection_v6 and reliability:
        # Placement (v6): the projected operator policy keeps every transfer-fed branch at a local
        # base stock over the transfer lead plus one review at its own quantile, instead of leaving
        # transfers to a just-in-time deterministic projection that parks every safety unit at the
        # central location one transfer lead away from the demand it protects.
        from zaad.full.echelon import local_transfer_targets
        spread = {s.id: fits[s.id]["uncertainty"]["sd_effective"] for s in req.services}
        # Only the first four periods are pinned: period 0 is what executes, the next three keep the
        # branch base stock in the projection, and pinning every period made the proxy MILP time out.
        orders.update({k: v for k, v in local_transfer_targets(req, fits, spread, purchases=orders).items() if k[2] <= 3})
    return orders


def evaluate(req, solution, worlds):
    """Gate evaluation on a world set. Later-period transfers are guidance: on a world where the
    feeding receipt lands late they are reduced to available stock and the reduction is
    recorded, rather than failing a plan whose period-zero actions are perfectly legal."""
    rows = []
    for world in worlds:
        try:
            result = settle(req, solution, world, future_guidance=True)
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


def _shortage_exposure(rows: list[dict]) -> tuple[float | None, float | None]:
    """Mean and worst modeled shortage exposure (lost contribution plus SLA) across usable worlds."""
    values = [r["ledger"].get("lost_sales_opportunity", 0.) + r["ledger"].get("sla", 0.) for r in rows if r["usable"]]
    return (mean(values), max(values)) if values else (None, None)


def alternative_value(req: Request, reference: Solution, worlds: list, reference_rows: list[dict], service_risk: str,
                      risk_levels: dict[str, float] | None = None) -> dict:
    """Value of approved alternates, transfers and substitutions: the same solve with each option
    removed, compared on the selection worlds. Extra cost against expected and worst-world
    shortage avoided; nothing is assumed, every number comes from a solve and a settlement."""
    result: dict = {}
    if reference.status != "OPTIMAL":
        return result
    eligible = [s for s in req.sources if s.approved and s.compliance == "cleared"]
    pairs = {(s.sku, s.destination) for s in eligible}
    structure = {"alternates": any(sum(1 for s in eligible if (s.sku, s.destination) == pair) > 1 for pair in pairs),
                 "transfers": any(a.approved for a in req.transfers),
                 "substitutions": any(r.approved for r in req.substitutions)}
    ref_cost = mean(r["economic_cost"] for r in reference_rows if r["usable"]) if any(r["usable"] for r in reference_rows) else None
    ref_mean_short, ref_worst_short = _shortage_exposure(reference_rows)
    for name, present in structure.items():
        if not present:
            continue
        restricted = solve(req, worlds, service_floor=True, service_risk=service_risk, disabled=frozenset({name}), service_risk_levels=risk_levels)
        entry: dict = {"option": name, "status": restricted.status}
        if restricted.status != "OPTIMAL":
            entry["sentence"] = f"Without the approved {name} the service targets cannot be met on the selection worlds; the option is structurally necessary."
            entry["verdict"] = "necessary"
            result[name] = entry
            continue
        rows = evaluate(req, restricted, worlds)
        cost = mean(r["economic_cost"] for r in rows if r["usable"]) if any(r["usable"] for r in rows) else None
        mean_short, worst_short = _shortage_exposure(rows)
        if ref_cost is None or cost is None or mean_short is None or ref_mean_short is None:
            entry["verdict"] = "unevaluable"
            result[name] = entry
            continue
        extra = ref_cost - cost                  # positive when using the option costs more in total
        avoided = mean_short - ref_mean_short    # positive when the option removes shortage exposure
        worst_avoided = (worst_short or 0.) - (ref_worst_short or 0.)
        service_change = {}
        for service in req.services:
            a, b = _service_value(req, rows, service), _service_value(req, reference_rows, service)
            if a is not None and b is not None:
                service_change[service.id] = b - a
        used = {"alternates": sum(q for (source_id, _), q in reference.purchases.items()
                                  if any(s.id == source_id for s in eligible)),
                "transfers": sum(reference.transfers.values()),
                "substitutions": None}[name]
        verdict = "justified" if avoided + max(0., worst_avoided) * .5 > max(0., extra) else ("cost_saving" if extra < 0 else "not_justified_on_modeled_evidence")
        if name == "substitutions":
            improves = any(v > req.service_tolerance for v in service_change.values())
            verdict = ("service_and_cost" if improves and extra <= 0 else "service" if improves else "cost_only" if extra < 0 else "no_modeled_benefit")
        entry.update({"total_cost_with_option": ref_cost, "total_cost_without_option": cost,
                      "extra_cost_of_using_option": extra, "expected_shortage_avoided": avoided,
                      "worst_world_shortage_avoided": worst_avoided, "service_change": service_change,
                      "units_through_option": used, "verdict": verdict,
                      "sentence": (f"Using the approved {name} changes modeled total cost by {extra:+,.0f} and reduces expected shortage exposure by "
                                   f"{avoided:,.0f} (worst world {worst_avoided:,.0f}).")})
        result[name] = entry
    return result


def classify_service(req: Request, service, selected: float | None, best_joint: float | None, best_individual: float | None,
                     accepted: bool, chosen_meets: bool, blocking: dict, thin: bool) -> dict:
    """Why a service misses its target, in one of the requested classes. MODEL_FAILURE can only
    be judged after the fact (see replay/benchmark ex-post classification)."""
    tolerance = req.service_tolerance
    if selected is None:
        return {"class": "DATA_INSUFFICIENCY", "reason": "no physically usable evaluation of the selected plan"}
    if selected >= service.target - tolerance:
        return {"class": "MET", "reason": "target met within tolerance under independent confirmation"}
    if best_joint is not None and best_joint < service.target - tolerance:
        pre_existing = best_individual is not None and best_individual < service.target - tolerance
        return {"class": "UNAVOIDABLE", "pre_existing": pre_existing,
                "reason": ("no feasible action meets the target even when this service alone is maximized" if pre_existing
                           else "the target is not jointly achievable with the other services' targets and priorities")
                          + (" (thin data: the bound itself is provisional)" if thin else "")}
    if chosen_meets and not accepted:
        if blocking.get("downside"):
            return {"class": "ECONOMIC_TRADEOFF", "reason": "a plan meeting the target exists but exceeds the operator-approved economic downside tolerance"}
        if blocking.get("stress"):
            return {"class": "UNAVOIDABLE", "pre_existing": False, "under_stress": True,
                    "reason": "a plan meeting the target on fitted worlds fails physical feasibility or service under the declared stress envelope"}
        return {"class": "AVOIDABLE", "reason": "a feasible plan meeting the target was rejected for a non-economic control reason: " + "; ".join(blocking.get("reasons", []))}
    if best_joint is not None and best_joint >= service.target - tolerance:
        return {"class": "AVOIDABLE", "reason": "a jointly feasible plan meets the target but the selected plan does not"}
    return {"class": "DATA_INSUFFICIENCY", "reason": "the joint feasibility bound could not be evaluated"}


def v6_solve_terms(req: Request, fits: dict, protection: list[dict]) -> dict:
    """Per-SKU/location terms the v6 rules add to every candidate solve: an excess penalty where a
    temporary risk driver has gone quiet (orderly run-down of temporary protection above the lean
    baseline, charged at twice the holding rate) and a bounded terminal continuation (post-horizon
    demand over one replenishment lead, from the fitted mean and the declared lead only)."""
    skus = {s.id: s for s in req.skus}
    locs = {location.id: location for location in req.locations}
    direct = {(s.sku, s.destination): s for s in sorted(req.sources, key=lambda s: (s.unit_price + s.freight_per_unit + s.handling_per_unit, s.id))
              if s.approved and s.compliance == "cleared"}
    for source in sorted(req.sources, key=lambda s: (s.unit_price + s.freight_per_unit + s.handling_per_unit, s.id), reverse=True):
        if source.approved and source.compliance == "cleared":
            direct[source.sku, source.destination] = source
    excess: dict[tuple[str, str], tuple[float, float]] = {}
    continuation: dict[tuple[str, str], tuple[float, float]] = {}
    for row in protection:
        sku, location, state = row["sku"], row["location"], row["state"]
        mu = row["mean_demand_per_period"]
        quiet_with_excess = state["activity"] <= .05 and row["on_hand_units"] > state["lean_baseline_units"] + mu
        if state["regime"] == "RECOVER" or (quiet_with_excess and state["incremental_protection_units"] <= 0.):
            rate = skus[sku].asset_value * locs[location].holding_per_value_period * 2.
            excess[sku, location] = (state["lean_baseline_units"] + mu, rate)
        services = [s for s in req.services if s.sku == sku and s.location == location]
        if not services or mu <= 0:
            continue
        buying = direct.get((sku, location))
        if buying is not None:
            lead = dates(req, buying, 0)[1]
        else:
            feeders = [a for a in req.transfers if a.approved and a.sku == sku and a.destination == location]
            if not feeders:
                continue
            arc = min(feeders, key=lambda a: a.lead_periods)
            upstream = direct.get((sku, arc.origin))
            lead = arc.lead_periods + (dates(req, upstream, 0)[1] if upstream is not None else 0)
        margin = max(0., min(s.selling_price for s in services) - skus[sku].terminal_value)
        continuation[sku, location] = (mu * (lead + 1), margin)
    terms: dict = {}
    if excess:
        terms["excess_penalty"] = excess
    if continuation and req.terminal_continuation:
        terms["continuation"] = continuation
    return terms


def procurement_timing(req: Request, fits: dict, solution: Solution | None) -> list[dict]:
    """Timing audit (v6): for every planned purchase, the period it lands, the first period the
    location would otherwise run short (deterministic fitted demand, opening stock, pipeline and
    earlier arrivals), the periods it arrives early and the cash committed that early."""
    if solution is None or not solution.purchases:
        return []
    sources = {s.id: s for s in req.sources}
    position: dict[tuple[str, str], float] = {(s.id, location.id): sum(x.usable for x in req.stock if x.sku == s.id and x.location == location.id)
                                              for s in req.skus for location in req.locations}
    arrivals: dict[tuple[str, str, int], float] = {}
    for po in req.pipeline:
        source = sources[po.source]
        due = next(o.due_in for o in po.options if o.action == "keep")
        arrivals[source.sku, source.destination, due] = arrivals.get((source.sku, source.destination, due), 0.) + po.expected_accepted_remaining
    for row in req.inbound_transfers:
        arrivals[row.sku, row.destination, row.due_in] = arrivals.get((row.sku, row.destination, row.due_in), 0.) + row.accepted_quantity
    for (arc_id, _, t), q in solution.transfers.items():
        arc = next(a for a in req.transfers if a.id == arc_id)
        arrivals[arc.sku, arc.destination, t + arc.lead_periods] = arrivals.get((arc.sku, arc.destination, t + arc.lead_periods), 0.) + q * (1 - arc.loss_fraction)
        arrivals[arc.sku, arc.origin, t] = arrivals.get((arc.sku, arc.origin, t), 0.) - q
    mu = {(s.sku, s.location): 0. for s in req.services}
    for s in req.services:
        mu[s.sku, s.location] += fits[s.id]["mean"]
    planned = sorted(((source_id, t, q) for (source_id, t), q in solution.purchases.items() if q > 0), key=lambda x: dates(req, sources[x[0]], x[1])[1])
    out = []
    for source_id, t, q in planned:
        source = sources[source_id]
        key = (source.sku, source.destination)
        arrival = dates(req, source, t)[1]
        level, needed_by = position[key], None
        for p in range(req.horizon + 1):
            level += arrivals.get((*key, p), 0.)
            level -= mu.get(key, 0.)
            if level < 0 and p >= arrival:
                needed_by = p
                break
        early = 0 if needed_by is None else max(0, needed_by - arrival)
        if needed_by is None:
            early = max(0, req.horizon - arrival)
        landed = source.unit_price + source.freight_per_unit + source.handling_per_unit
        out.append({"source": source_id, "period": t, "quantity": q, "arrival_period": arrival, "needed_by_period": needed_by,
                    "early_periods": early, "cash_committed_early": q * landed * early})
        arrivals[(*key, arrival)] = arrivals.get((*key, arrival), 0.) + q * source.fill_mean
    return out


def plan(req: Request) -> dict:
    reliability = req.engine_profile == "reliability"
    service_risk = "cvar" if reliability else "expected"
    fits = forecast_all(req)
    supply = supply_profiles(req)
    sources_by_id = {s.id: s for s in req.sources}
    protection = protection_profile(req, fits, supply)
    v6 = v6_solve_terms(req, fits, protection) if req.protection_v6 else {}
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
                  "deterministic_network": solve(req, deterministic, service_floor=True, **v6),
                  "stochastic_network": solve(req, selection, service_floor=True, **v6),
                  "cvar_network": solve(req, selection, service_floor=True, cvar_weight=.2, **v6)}
    stress_worlds = []
    for i, stress in enumerate(req.stresses):
        stress_worlds += draw(req, req.seed + 100 + i, 1, stress)
    combined = [replace(w, weight=1 / (len(selection) + len(stress_worlds))) for w in selection + stress_worlds]
    credibility: dict[str, Any] = stress_credibility(req, supply) if reliability else {"credibility": 0., "effective_stress_weight": 0., "drivers": {}}
    stress_weight: float = float(credibility["effective_stress_weight"]) if reliability else 0.
    hedged: list = []
    if stress_worlds and stress_weight > 0:
        hedged = ([replace(w, weight=(1 - stress_weight) / len(selection)) for w in selection]
                  + [replace(w, weight=stress_weight / len(stress_worlds)) for w in stress_worlds])
    # Quantile level per service from its SKU/location risk state: calm and resilient means the
    # expected floor only (lean); an active driver restores the full quantile protection.
    activity = {(row["sku"], row["location"]): row["state"]["activity"] for row in protection}
    risk_levels = ({s.id: (req.service_risk_level * activity.get((s.sku, s.location), 1.) if activity.get((s.sku, s.location), 1.) > .05 else 0.)
                    for s in req.services} if req.protection_decay else None)
    if reliability:
        # Quantile protection: the worst share of scenarios must meet the target too.
        candidates["protected_network"] = solve(req, selection, service_floor=True, service_risk="cvar", service_risk_levels=risk_levels, **v6)
        if hedged:
            # Hedged protection: the declared stress envelopes enter the solve at their probability
            # weight, so protection is sized by how credible and how costly the stress is.
            candidates["hedged_network"] = solve(req, hedged, service_floor=True, service_risk="cvar", service_risk_levels=risk_levels, **v6)
    candidates["stress_network"] = solve(req, combined, service_floor=True, per_world_service=True, **v6)
    recovery = solve(req, combined, service_first="all", **v6)
    if recovery.status == "OPTIMAL":
        candidates["joint_recovery"] = recovery
    # Joint fitted frontier (v6): the best jointly achievable network service on the fitted worlds
    # alone, sharing central stock across branches. The recovery candidate above hedges the declared
    # stress at equal weight, so its fitted-world service understates what the network can do.
    joint_fitted_rows: list[dict] = []
    if req.protection_v6:
        joint_fitted = solve(req, selection, service_first="all", **v6)
        if joint_fitted.status == "OPTIMAL":
            joint_fitted_rows = evaluate(req, joint_fitted, selection)

    selection_rows = {name: evaluate(req, candidate, selection) for name, candidate in candidates.items() if candidate.status == "OPTIMAL"}
    stress_rows = {name: evaluate(req, candidate, stress_worlds) for name, candidate in candidates.items()
                   if candidate.status == "OPTIMAL" and stress_weight > 0}
    feasible = [name for name, rows in selection_rows.items() if service_ok(req, rows)]

    def hedged_cost(name: str) -> float:
        """Expected cost with the declared stress at its evidence-weighted probability (fitted only when zero)."""
        rows = selection_rows[name]
        if not rows or any(not r["usable"] for r in rows):
            return float("inf")
        fitted = mean(r["economic_cost"] for r in rows)
        if stress_weight <= 0 or name not in stress_rows:
            return fitted
        stressed = [r["economic_cost"] for r in stress_rows[name] if r["usable"]]
        if not stressed or len(stressed) < len(stress_rows[name]):
            return float("inf")   # physically unusable under a declared stress is not a cheaper plan
        return (1 - stress_weight) * fitted + stress_weight * mean(stressed)
    joint_rows = selection_rows.get("joint_recovery", [])
    # The target vector is jointly feasible when ANY candidate meets every service on the selection
    # worlds; the joint recovery solve is one more way to show it, not the only one.
    target_jointly_feasible = bool(feasible) or (bool(joint_rows) and service_ok(req, joint_rows))
    recovery_mode = not target_jointly_feasible
    recovery_ranking: list[dict] = []

    def burden(name: str) -> float:
        values = [x["inventory_value"] for r in selection_rows.get(name, []) if r["usable"] for x in r["trace"]]
        return mean(values) if values else float("inf")

    if feasible:
        if req.protection_v5:
            # Marginal value (v5): estimated costs are noisy; among feasible candidates whose hedged
            # cost lies within one downside-tolerance band of the cheapest, prefer the one that
            # carries the least inventory. Protection has to beat the lean plan by more than noise.
            cheapest = min(hedged_cost(n) for n in feasible)
            # The band is one fifth of the downside tolerance on the absolute cost (economic cost can
            # be negative when closing assets exceed spend, so a multiplicative band would be empty).
            band = [n for n in feasible if hedged_cost(n) <= cheapest + req.downside_cost_tolerance / 5. * max(abs(cheapest), 1.) + 1e-9] or list(feasible)
            chosen = min(band, key=lambda name: (burden(name), hedged_cost(name), list(candidates).index(name)))
        else:
            chosen = min(feasible, key=lambda name: (hedged_cost(name), list(candidates).index(name)))
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
            if req.protection_v6:
                # Recovery ranking (v6): among candidates whose shortfall is within the material gap of
                # the best, take the one carrying the least inventory. A stress-hedged recovery plan that
                # buys more than the network can move earns no shortfall it can deliver.
                best_gap = min(r["weighted_service_shortfall"] for r in usable)
                recovery_band = [r for r in usable if r["weighted_service_shortfall"] <= best_gap + material_shortfall_gap(req)]
                best_candidate = min(recovery_band, key=lambda r: (burden(r["candidate"]), r["weighted_service_shortfall"], r["cost_mean"], list(candidates).index(r["candidate"])))
            else:
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
    blocking: dict = {"downside": False, "stress": False, "reasons": []}
    incumbent_meets = bool(incumbent_rows) and service_ok(req, incumbent_rows)
    # If no plan can meet every target under the declared stress (the per-world stress solve is
    # infeasible), demanding the full SLA under stress would reject every candidate and keep an
    # incumbent that fails the same stress. Under the reliability profile the stress gate then
    # asks for "not worse than the incumbent": physically usable, inside the cost cap, no larger
    # weighted shortfall and priority consistent.
    stress_targets_feasible = candidates["stress_network"].status == "OPTIMAL"   # reported; the gate prefers strict, then not-worse

    def _hedged_downside(before, after) -> bool:
        """Cost cap with the declared stress at its evidence weight: a plan that is much cheaper
        on fitted worlds is not vetoed by a stress that carries a small credibility, and a
        credible stress counts in proportion."""
        if not before or not after or len(before) != len(after) or any(not r["usable"] for r in before + after):
            return False
        fitted_gap = mean(b["economic_cost"] for b in candidate_rows) - mean(a["economic_cost"] for a in incumbent_rows) if candidate_rows and incumbent_rows and all(r["usable"] for r in candidate_rows + incumbent_rows) else 0.
        stress_gap = mean(b["economic_cost"] - a["economic_cost"] for a, b in zip(before, after))
        scale = max(abs(mean(a["economic_cost"] for a in before)), 1.)
        return (1 - stress_weight) * fitted_gap + stress_weight * stress_gap <= req.downside_cost_tolerance * scale

    def stress_gate(before, after, physically_ok, downside_ok, service_under_stress) -> tuple[bool, str]:
        """Returns (pass, mode). strict: the full SLA under stress inside the per-world cost cap.
        not_worse: physically usable, no larger priority-weighted shortfall than the incumbent
        under the same stress, priority consistent, inside the hedged cost cap. The strict gate
        is preferred; the not-worse gate stops the selector from keeping an incumbent that
        fails the same stress worse than the candidate."""
        if recovery_mode:
            ok = (physically_ok and _within_downside(req, before, after)
                  and _recovery_not_worse(req, before, after) and _priority_consistent(req, before, after))
            return ok, "recovery"
        if downside_ok and service_under_stress:
            return True, "strict"
        if reliability:
            not_worse = (physically_ok and bool(before) and all(r["usable"] for r in before)
                         and weighted_shortfall(req, after) <= weighted_shortfall(req, before) + material_shortfall_gap(req)
                         and _priority_consistent(req, before, after) and _hedged_downside(before, after))
            return not_worse, ("not_worse" if not_worse else "rejected")
        return False, "rejected"

    def confirm_service_first(rows_before, rows_after, name=None):
        """Cost-first when the incumbent already meets service; service-first when it does not.
        Under the reliability profile the benefit is hedged: the declared stress enters at its
        probability weight, so a plan that costs a little more on fitted worlds but avoids an
        expensive stress outcome shows a positive benefit."""
        difference = np.asarray([a["economic_cost"] - b["economic_cost"] for a, b in zip(rows_before, rows_after)])
        rng = np.random.default_rng(req.seed + 20000)
        lower = float(np.quantile(np.mean(rng.choice(difference, (500, len(difference))), axis=1), .1))
        if stress_weight > 0 and name is not None and name in stress_rows and "incumbent" in stress_rows:
            before_s = [r["economic_cost"] for r in stress_rows["incumbent"] if r["usable"]]
            after_s = [r["economic_cost"] for r in stress_rows[name] if r["usable"]]
            if before_s and after_s and len(before_s) == len(after_s):
                lower = (1 - stress_weight) * lower + stress_weight * float(np.mean(np.asarray(before_s) - np.asarray(after_s)))
        if reliability and not service_ok(req, rows_before):
            ok = _within_downside(req, rows_before, rows_after)
            note = (None if ok else "downside")
            return ok, lower, note
        return lower > 1e-6, lower, (None if lower > 1e-6 else "benefit")

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
            blocking["downside"] = True
            reasons.append("Recovery candidate improves service but exceeds the configured economic downside tolerance.")
    elif recovery_mode:
        accepted = False
        reasons.append("No candidate materially improves priority-weighted service shortfall over the incumbent; incumbent retained.")
    else:
        accepted = chosen != "incumbent" and service_ok(req, candidate_rows) and bool(incumbent_rows) and all(r["usable"] for r in incumbent_rows)
        if accepted:
            accepted, benefit_lower, note = confirm_service_first(incumbent_rows, candidate_rows, chosen)
            if note == "downside":
                blocking["downside"] = True
                reasons.append("Candidate meets a service target the incumbent misses, but exceeds the configured economic downside tolerance.")
            elif note == "benefit":
                reasons.append("Independent fitted-model confirmation does not establish positive benefit.")
            elif reliability and not incumbent_meets:
                reasons.append("Incumbent misses a requested service target under independent confirmation; the candidate meets every target within the economic downside tolerance (service-first acceptance).")

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
        service_under_stress = service_ok(req, after)
        # Under stress a recovery plan must stay usable, within the cost cap, materially better on
        # weighted shortfall, and priority-consistent; the per-service no-worse rule would forbid
        # the very reallocation a priority-weighted recovery exists to make.
        pass_stress, gate_mode = stress_gate(before, after, physically_ok, downside_ok, service_under_stress)
        accepted &= pass_stress
        stress_report.append({"stress": stress.model_dump(), "pass": pass_stress, "gate_mode": gate_mode,
                              "physically_usable": physically_ok, "within_downside": downside_ok, "service_met": service_under_stress,
                              "incumbent": {**summarize(before), "weighted_service_shortfall": weighted_shortfall(req, before),
                                            "service": {s.id: _service_value(req, before, s) for s in req.services}},
                              "candidate": {**summarize(after), "weighted_service_shortfall": weighted_shortfall(req, after),
                                            "service": {s.id: _service_value(req, after, s) for s in req.services}}})
    if any(not x["pass"] for x in stress_report):
        blocking["stress"] = True
        if any(x["physically_usable"] and not x["within_downside"] and x["service_met"] for x in stress_report):
            blocking["downside"] = True
        reasons.append("Out-of-model stress confirmation rejected physical feasibility, downside risk, or required service recovery.")

    candidate_gates = {chosen: {"accepted": bool(accepted), "stress": stress_report,
                                "reason": ("accepted" if accepted else "; ".join(str(r) for r in reasons) or "rejected")}}
    chosen_meets = bool(candidate_rows) and service_ok(req, candidate_rows)
    if not recovery_mode and not accepted:
        for alternative in sorted((n for n in feasible if n not in {chosen, "incumbent"}), key=lambda n: (hedged_cost(n), list(candidates).index(n))):
            rows = evaluate(req, candidates[alternative], confirmation)
            passes = service_ok(req, rows) and bool(incumbent_rows) and all(r["usable"] for r in incumbent_rows)
            lower = None
            if passes:
                passes, lower, _ = confirm_service_first(incumbent_rows, rows, alternative)
            checks: list[dict[str, Any]] = []
            for i, stress in enumerate(req.stresses):
                worlds = draw(req, req.seed + 30000 + i, req.scenarios, stress)
                before = evaluate(req, incumbent, worlds) if incumbent.status == "OPTIMAL" else []
                after = evaluate(req, candidates[alternative], worlds)
                usable_after = bool(after) and all(r["usable"] for r in after)
                valid = usable_after and bool(before) and all(r["usable"] for r in before)
                if valid:
                    for a, b in zip(before, after):
                        if b["economic_cost"] - a["economic_cost"] > req.downside_cost_tolerance * max(abs(a["economic_cost"]), 1.):
                            valid = False
                        for service in req.services:
                            sa, sb = a["service"][service.id], b["service"][service.id]
                            if sa is not None and sb is not None and sb < sa - req.service_tolerance:
                                valid = False
                valid, gate_mode = stress_gate(before, after, usable_after, valid, service_ok(req, after))
                passes &= valid
                checks.append({"stress": stress.model_dump(), "pass": bool(valid), "gate_mode": gate_mode,
                               "incumbent": {**summarize(before), "service": {s.id: _service_value(req, before, s) for s in req.services}},
                               "candidate": {**summarize(after), "service": {s.id: _service_value(req, after, s) for s in req.services}}})
            candidate_gates[alternative] = {"accepted": bool(passes), "stress": checks,
                                            "deltas": {"service": {s.id: ((_service_value(req, rows, s) or 0.) - (_service_value(req, incumbent_rows, s) or 0.)) for s in req.services},
                                                       "cost_fitted": (mean(r["economic_cost"] for r in rows if r["usable"]) - mean(r["economic_cost"] for r in incumbent_rows if r["usable"])) if any(r["usable"] for r in rows) and any(r["usable"] for r in incumbent_rows) else None,
                                                       "inventory": burden(alternative) - burden("incumbent") if burden("incumbent") != float("inf") else None,
                                                       "stress_service": {s.id: (c["candidate"].get("service", {}).get(s.id), c["incumbent"].get("service", {}).get(s.id)) for c in checks for s in req.services}},
                                            "reason": ("accepted" if passes else
                                                       "does not meet every service target under independent confirmation" if not service_ok(req, rows) else
                                                       "no positive hedged benefit against the incumbent" if lower is not None and lower <= 1e-6 else
                                                       "stress gate: " + ", ".join(str(c.get("gate_mode", "rejected")) for c in checks if not c["pass"]))}
            if passes:
                chosen, accepted, candidate_rows, stress_report, benefit_lower = alternative, True, rows, checks, lower
                chosen_meets = True
                reasons = ["Cheaper candidate failed the gate; the next qualified candidate passed independent and stress confirmation."]
                break

    if req.force_unit_fills:
        accepted = False
        blocking["reasons"].append("unit-fill regression control")
        reasons.append("Unit-fill regression control cannot open approval gate.")
    if req.evidence_label == "OPERATOR-SHADOW" and not req.incumbent_orders:
        accepted = False
        blocking["reasons"].append("operator incumbent missing")
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
    final_rows = evaluate(req, final, confirmation) if final is not None else []

    # Service reliability, tracked separately from economics.
    customers = {c.id: c for c in req.customers}
    frontier_best: dict[str, float | None] = {}
    for row in frontier:
        frontier_best[str(row["service"])] = row["best_modeled_individual_unit_fill"] if isinstance(row["best_modeled_individual_unit_fill"], float) else None
    thin = any(fits[s.id].get("uncertainty", {}).get("data_sufficiency") == "thin" for s in req.services) if reliability else False
    per_service: list[dict[str, Any]] = []
    for service in req.services:
        selected_value = _service_value(req, final_rows, service)
        joint_value = _service_value(req, recovery_rows, service)
        incumbent_value = _service_value(req, incumbent_rows, service)
        candidate_value = _service_value(req, candidate_rows, service)
        stress_values = [x["candidate" if accepted else "incumbent"].get("service", {}).get(service.id) for x in stress_report]
        stress_values = [v for v in stress_values if v is not None]
        stockouts = sum(1 for r in final_rows if r["usable"] for x in r["service_by_period"]
                        if x["service"] == service.id and x["served"] < x["demand"] - 1e-9)
        periods = sum(1 for r in final_rows if r["usable"] for x in r["service_by_period"] if x["service"] == service.id)
        best_joint = max((v for v in (joint_value, candidate_value if chosen_meets else None) if v is not None), default=joint_value)
        per_service.append({"service": service.id, "customer": service.customer, "customer_class": customers[service.customer].service_class,
                            "priority": customers[service.customer].priority, "metric": service.metric,
                            "requested_service": service.target, "achieved_service": selected_value,
                            "best_modeled_jointly_feasible_service": best_joint,
                            "best_modeled_individual_service": frontier_best.get(service.id),
                            "incumbent_service": incumbent_value, "zaad_service": candidate_value,
                            "avoidable_service_loss": max(0., min(service.target, best_joint) - selected_value) if best_joint is not None and selected_value is not None else None,
                            "unavoidable_shortfall": max(0., service.target - best_joint) if best_joint is not None else None,
                            "service_regret": max(0., best_joint - selected_value) if best_joint is not None and selected_value is not None else None,
                            "worst_case_stress_service": min(stress_values) if stress_values else None,
                            "stockout_period_share": stockouts / periods if periods else None,
                            "classification": classify_service(req, service, selected_value, best_joint, frontier_best.get(service.id),
                                                               accepted, chosen_meets, blocking, thin)})
    priority_total = sum(customers[s.customer].priority for s in req.services)
    achieved = [(customers[s.customer].priority, row["achieved_service"]) for s, row in zip(req.services, per_service) if row["achieved_service"] is not None]
    by_class: dict[str, dict[str, Any]] = {}
    for s, row in zip(req.services, per_service):
        label = customers[s.customer].service_class or "unclassified"
        cell: dict[str, Any] = by_class.setdefault(label, {"services": 0, "requested_mean": 0., "achieved_mean": 0., "met": 0})
        cell["services"] += 1
        cell["requested_mean"] += s.target
        achieved_value = row["achieved_service"]
        if isinstance(achieved_value, float):
            cell["achieved_mean"] += achieved_value
            cell["met"] += int(achieved_value >= s.target - req.service_tolerance)
    for cell in by_class.values():
        cell["requested_mean"] /= cell["services"]
        cell["achieved_mean"] /= cell["services"]
    service_reliability = {"scope": "independent confirmation worlds; stress values from the declared stress envelopes; not a guarantee",
                           "services": per_service,
                           "weighted_service_shortfall": weighted_shortfall(req, final_rows) if final_rows else None,
                           "customer_priority_weighted_service": sum(p * v for p, v in achieved) / priority_total if achieved and priority_total else None,
                           "by_customer_class": by_class,
                           "services_met": sum(row["classification"]["class"] == "MET" for row in per_service),
                           "classes": {label: sum(row["classification"]["class"] == label for row in per_service)
                                       for label in ("MET", "UNAVOIDABLE", "AVOIDABLE", "ECONOMIC_TRADEOFF", "DATA_INSUFFICIENCY")}}

    alternatives = {}
    if reliability:
        reference_name = "protected_network" if candidates.get("protected_network") is not None and candidates["protected_network"].status == "OPTIMAL" else "stochastic_network"
        alternatives = alternative_value(req, candidates[reference_name], selection, selection_rows.get(reference_name, []), service_risk, risk_levels)
        alternatives["reference_candidate"] = reference_name

    # Marginal value of the chosen plan's protection against the leanest feasible candidate on
    # the selection worlds: extra inventory carried versus shortage exposure avoided, fitted and
    # under the declared stress at its evidence weight.
    def mean_inventory(rows):
        values = [x["inventory_value"] for r in rows if r["usable"] for x in r["trace"]]
        return mean(values) if values else None
    protection_value = None
    if feasible:
        leanest = min(feasible, key=lambda n: (mean_inventory(selection_rows[n]) or float("inf"), list(candidates).index(n)))
        chosen_inv, lean_inv = mean_inventory(selection_rows.get(chosen, [])), mean_inventory(selection_rows[leanest])
        chosen_short, _ = _shortage_exposure(selection_rows.get(chosen, []))
        lean_short, _ = _shortage_exposure(selection_rows[leanest])
        stress_chosen, _ = _shortage_exposure(stress_rows.get(chosen, [])) if chosen in stress_rows else (None, None)
        stress_lean, _ = _shortage_exposure(stress_rows.get(leanest, [])) if leanest in stress_rows else (None, None)
        if chosen_inv is not None and lean_inv is not None and chosen_short is not None and lean_short is not None:
            extra_value = chosen_inv - lean_inv
            holding_rate = mean(location.holding_per_value_period for location in req.locations)
            carrying = max(0., extra_value) * holding_rate * req.horizon
            avoided = (lean_short - chosen_short) * (1 - stress_weight) + ((stress_lean - stress_chosen) * stress_weight if stress_lean is not None and stress_chosen is not None else 0.)
            protection_value = {"leanest_feasible_candidate": leanest, "chosen": chosen,
                                "extra_inventory_value": extra_value, "carrying_cost_over_horizon": carrying,
                                "hedged_shortage_avoided": avoided, "justified": bool(avoided >= carrying - 1e-9),
                                "scope": "selection worlds; stress at its evidence weight; not a guarantee"}
    explain: list[dict[str, Any]] = []
    for row in protection:
        row_any: dict[str, Any] = row
        state: dict[str, Any] = row_any["state"]
        pair_services = [s for s in req.services if s.sku == row["sku"] and s.location == row["location"]]
        rel = {r["service"]: r for r in per_service}
        pipeline_units = sum(po.expected_accepted_remaining for po in req.pipeline if sources_by_id[po.source].sku == row["sku"] and sources_by_id[po.source].destination == row["location"]) if req.pipeline else 0.
        expected = [rel[s.id]["achieved_service"] for s in pair_services if rel[s.id]["achieved_service"] is not None]
        stress_values = [rel[s.id]["worst_case_stress_service"] for s in pair_services if rel[s.id]["worst_case_stress_service"] is not None]
        explain.append({"sku": row["sku"], "location": row["location"],
                        "state": "ALLOCATE" if recovery_mode else state["regime"],
                        "lean_baseline_units": state["lean_baseline_units"], "current_inventory_units": row["on_hand_units"],
                        "current_pipeline_units": pipeline_units, "recommended_protection_units": row["protection_units"],
                        "incremental_protection_units": state["incremental_protection_units"],
                        "active_risk_drivers": state["active_drivers"], "driver_contribution_units": row["drivers_units"],
                        "service_targets": {s.id: s.target for s in pair_services},
                        "expected_service": min(expected) if expected else None, "stress_service": min(stress_values) if stress_values else None,
                        "marginal_value_of_protection": protection_value,
                        "alternatives_available": float(row_any["effective_independent_sources"]) > 1.5,
                        "transfer_available": state["placement"]["transfer_lead_periods"] is not None,
                        "substitution_available": float(row_any["substitute_cover_units"]) > 0,
                        "expected_periods_to_lean": state["periods_to_lean"], "flags": state["flags"],
                        "placement": state["placement"],
                        "intervention": ("ZAAD intervened: " + chosen if accepted else "incumbent retained: " + ("; ".join(reasons) if reasons else "no candidate improved on it")),
                        "explanation": row["explanation"]})
    mode = "ALLOCATE" if recovery_mode else req.mode
    if reliability and not recovery_mode:
        mode = "PROTECT" if any(row["stance"] == "protect" for row in protection) else ("LEAN" if req.mode in ("LEAN", "PROTECT") else req.mode)
    false_protection = {"rows": [{"sku": row["sku"], "location": row["location"], "protection_units": row["protection_units"],
                                  "lean_baseline_units": row["state"]["lean_baseline_units"],
                                  "incremental_protection_units": row["state"]["incremental_protection_units"],
                                  "active_drivers": row["state"]["active_drivers"], "risk_active": row["state"]["risk_active"],
                                  "decaying": row["state"]["decaying"], "periods_to_lean": row["state"]["periods_to_lean"],
                                  "false_protection_flag": row["state"]["false_protection_flag"], "activity": row["state"]["activity"]}
                                 for row in protection],
                        "quantile_levels": risk_levels,
                        "scope": "lean baseline is demand-only protection at the fitted spread; incremental is what active drivers add"}

    return {"schema_version": "zaad.network.report.v2", "brand": "ZAAD", "version": VERSION,
            "operator_id": req.operator_id, "as_of": req.as_of.isoformat(), "information_hash": fingerprint,
            "evidence_label": req.evidence_label, "status": status, "mode": mode, "engine_profile": req.engine_profile,
            "selected_policy": chosen if accepted else incumbent_label,
            "actions": action_rows(final), "incumbent_actions": action_rows(incumbent),
            "approval_required": True, "executable_purchase_order": False,
            "forecasts": fits, "eta": eta, "service_frontier": frontier,
            "protection": protection, "false_protection": false_protection, "explain": explain, "protection_value": protection_value,
            "network_service": [{"service": s.id, "location": s.location, "requested": s.target,
                                 "jointly_feasible": (_service_value(req, joint_fitted_rows, s) if joint_fitted_rows else (_service_value(req, joint_rows, s) if joint_rows else None)),
                                 "expected_achieved": _service_value(req, final_rows, s) if final_rows else None,
                                 "incumbent_achieved": _service_value(req, incumbent_rows, s) if incumbent_rows else None,
                                 "selected_achieved": _service_value(req, candidate_rows, s) if (accepted and candidate_rows) else (_service_value(req, incumbent_rows, s) if incumbent_rows else None)}
                                for s in req.services],
            "procurement_timing": procurement_timing(req, fits, final) if req.protection_v6 else None,
            "supply_profiles": {k: profile_dict(v) for k, v in supply.items()},
            "alternatives": alternatives, "service_reliability": service_reliability,
            "selection_costs": {name: {"fitted": mean(r["economic_cost"] for r in rows) if rows and all(r["usable"] for r in rows) else None,
                                       "hedged": hedged_cost(name) if np.isfinite(hedged_cost(name)) else None}
                                for name, rows in selection_rows.items()},
            "stress_weight": stress_weight, "stress_credibility": credibility, "stress_targets_feasible": stress_targets_feasible,
            "joint_service_feasibility": {"target_vector_feasible": target_jointly_feasible,
                "recovery_mode": recovery_mode, "material_gap": material_shortfall_gap(req),
                "recovery_ranking": recovery_ranking,
                "incumbent_weighted_shortfall": weighted_shortfall(req, incumbent_rows),
                "recovery_weighted_shortfall": weighted_shortfall(req, recovery_rows),
                "selected_weighted_shortfall": weighted_shortfall(req, final_rows) if final else None,
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
