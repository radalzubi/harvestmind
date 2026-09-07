"""Uncertainty-responsive protection per SKU and location, with the reasons attached.

Protection is the stock that has to be on hand or inbound, beyond the mean demand until the
next feasible replenishment can land, for the customers at that location to be served at
their own targets. It is built from named drivers rather than one buffer factor:

    demand spread     calibrated one-step residual spread over the replenishment window
    forecast level    standard error of the level, larger while a regime change is young
    lead-time spread  the cheapest usable source's own lead tail (censored history or declared)
    fill spread       that source's accepted-ratio spread and partial-delivery probability
    inbound ETA risk  open POs to this SKU/location weighted by their late probability
    correlation       the capacity-weighted number of independent sources; shared ports and
                      suppliers reduce the credit alternates earn
    substitution      approved substitute stock already at the location
    replenishment     the number of periods until the next feasible receipt

The quantile is the demand- and priority-weighted service target of the customers served, so
a 99% strategic customer pulls protection up where it matters and a 90% spot customer does
not. The optimizer itself protects through the scenario constraints; this profile drives the
projected base-stock proxy, explains the plan, and reports where protection is unnecessary.
"""
from __future__ import annotations

from typing import Any

import math

from zaad.full.contracts import Request
from zaad.full.uncertainty import (SupplyProfile, demand_state, diversification, periods_to_lean_demand, protection_activity,
                                   resilience, supply_state, z_for)
from zaad.full.worlds import dates

# A detected level change is a confirmed decline once it has held for this many observations and
# the new level is at or below this share of the old one. Below one observation is noise; the
# change-point detector itself supplies the persistence, this is the corroboration on top of it.
DECLINE_CONFIRMATION = 3
DECLINE_RATIO = .85


def _weighted_target(services, customers, fits) -> tuple[float, float, float]:
    """Priority- and demand-weighted target, the top target, and the top priority."""
    weights = [(customers[s.customer].priority * max(fits[s.id]["mean"], 1e-9), s.target, customers[s.customer].priority)
               for s in services]
    total = sum(w for w, _, _ in weights)
    weighted = sum(w * target for w, target, _ in weights) / total if total > 0 else max(s.target for s in services)
    return weighted, max(s.target for s in services), max(p for _, _, p in weights)


def protection_profile(req: Request, fits: dict, supply: dict[str, SupplyProfile]) -> list[dict]:
    customers = {c.id: c for c in req.customers}
    skus = {s.id: s for s in req.skus}
    sources = {s.id: s for s in req.sources}
    reliability = req.engine_profile == "reliability"
    pairs = sorted({(s.sku, s.location) for s in req.services})
    # Echelon origins (v7): a central DC with no customers of its own never appeared here, so the
    # location that carries most of the network's inventory had no lean baseline, no regime, no
    # recovery exit and no excess charge. It is given a row whose service obligation is the demand
    # of the branches it feeds, capped by what its arcs can actually carry. The row is marked
    # `echelon_origin` and the projected base-stock proxy ignores it, so the incumbent and the
    # base-stock comparator are unchanged.
    direct = {(s.sku, s.destination) for s in req.sources if s.approved and s.compliance == "cleared"}
    fed_from: dict[tuple[str, str], list] = {}
    if req.protection_v7:
        for arc in req.transfers:
            if arc.approved and (arc.sku, arc.destination) not in direct and (arc.sku, arc.origin) in direct:
                fed_from.setdefault((arc.sku, arc.origin), []).append(arc)
        pairs = sorted(set(pairs) | set(fed_from))
    rows = []
    for sku, location in pairs:
        services = [s for s in req.services if s.sku == sku and s.location == location]
        origin_arcs = fed_from.get((sku, location), [])
        echelon_origin = bool(origin_arcs) and not services
        if echelon_origin:
            # The origin's obligation is its branches' demand, but only as much of it as the arcs
            # can deliver: buying for demand a constrained arc cannot move only piles stock here.
            services = []
            for arc in origin_arcs:
                services += [s for s in req.services if s.sku == sku and s.location == arc.destination]
            services = sorted({s.id: s for s in services}.values(), key=lambda s: s.id)
        if not services:
            continue
        weighted_target, top_target, top_priority = _weighted_target(services, customers, fits)
        z = z_for(weighted_target)
        mu = sum(fits[s.id]["mean"] for s in services)
        if echelon_origin:
            for s in services:
                capacity = max((a.capacity for a in origin_arcs if a.destination == s.location), default=float("inf"))
                mu -= max(0., fits[s.id]["mean"] - capacity)
            mu = max(mu, 0.)
        if reliability:
            sd = math.sqrt(sum(fits[s.id]["uncertainty"]["sd_effective"] ** 2 for s in services))
            level_se = math.sqrt(sum(fits[s.id]["uncertainty"]["level_se"] ** 2 for s in services))
            calibration = max(fits[s.id]["uncertainty"]["calibration_ratio"] for s in services)
            thin = any(fits[s.id]["uncertainty"]["data_sufficiency"] == "thin" for s in services)
        else:
            sd = math.sqrt(sum(fits[s.id]["sd"] ** 2 for s in services))
            level_se, calibration, thin = 0., 1., False
        eligible = sorted((s for s in req.sources if s.sku == sku and s.destination == location
                           and s.approved and s.compliance == "cleared"),
                          key=lambda s: (s.unit_price + s.freight_per_unit + s.handling_per_unit, s.id))
        # Replenishment arc (v7): a branch with no direct source but an approved inbound transfer from
        # a stocked origin is refilled by that arc, not never. V6 gave it a replenishment window of
        # the whole horizon, so a branch one review away from its central DC was protected as if it
        # could never be restocked - the single largest source of local safety stock on fed branches.
        # The supplier's own lead and fill risk is carried by the origin's row, not counted twice here.
        refill_arc = None
        if req.protection_v7 and not eligible and not echelon_origin:
            for arc in sorted((a for a in req.transfers if a.approved and a.sku == sku and a.destination == location),
                              key=lambda a: (a.lead_periods, -a.capacity, a.id)):
                origin_stock = sum(x.usable for x in req.stock if x.sku == sku and x.location == arc.origin)
                origin_buys = any(x.sku == sku and x.destination == arc.origin and x.approved and x.compliance == "cleared"
                                  for x in req.sources)
                if arc.capacity >= mu and (origin_buys or origin_stock > mu):
                    refill_arc = arc
                    break
        if eligible:
            leads = {s.id: dates(req, s, 0)[1] for s in eligible}
            replenishment = min(leads.values()) + 1     # review period plus the earliest receipt
            primary = eligible[0]
            profile = supply.get(primary.id)
        elif refill_arc is not None:
            replenishment, primary, profile = refill_arc.lead_periods + 1, None, None
        else:
            replenishment, primary, profile = req.horizon, None, None
        window = max(1, replenishment)
        # Demand over the window: independent period noise plus a perfectly correlated level error.
        var_demand = window * sd ** 2
        var_level = (window * level_se) ** 2
        # Supply spread of the cheapest usable source, expressed in units of demand at risk.
        if profile is not None:
            lead_sd_periods = (profile.lead_sd_days if profile.scope == "declared" else max(profile.tail_days / 1.2816, profile.lead_sd_days)) / req.period_days
            fill_sd = profile.fill_sd
            late_probability = profile.late_probability
            supply_scope = profile.scope
        elif primary is not None:
            lead_sd_periods, fill_sd, late_probability, supply_scope = primary.lead_sd_days / req.period_days, primary.fill_sd, 0., "declared"
        elif refill_arc is not None:
            # The arc's declared loss stands in for fill spread; the supplier tail belongs upstream.
            lead_sd_periods, fill_sd, late_probability, supply_scope = 0., refill_arc.loss_fraction, 0., "transfer_arc"
        else:
            lead_sd_periods, fill_sd, late_probability, supply_scope = 0., 0., 0., "none"
        var_lead = (mu * lead_sd_periods) ** 2
        var_fill = (mu * window * fill_sd) ** 2
        diversity = diversification(req, sku, location, req.engine_profile)
        effective = max(1., diversity["effective_independent_sources"]) if eligible else 1.
        # Flexibility credit (v5): an alternate source counts only if it can land inside the
        # service window with meaningful capacity; otherwise it is a theoretical alternative.
        alternate_inside = None
        if req.protection_v5 and len(eligible) > 1 and primary is not None:
            window_guess = min(leads.values()) + 1
            others = [s for s in eligible if s.id != primary.id]
            alternate_inside = any(leads[s.id] + 1 <= window_guess + 1 and min(s.maximum, s.capacity_by_period[0]) >= .5 * mu * window_guess for s in others)
        # Alternates earn credit against supply spread only to the extent they are independent.
        var_supply = (var_lead + var_fill) / effective
        inbound_at_risk = 0.
        for po in req.pipeline:
            source = sources[po.source]
            if source.sku == sku and source.destination == location:
                p = supply[po.source].late_probability if po.source in supply else 0.
                inbound_at_risk += po.expected_accepted_remaining * p
        substitute_cover = 0.
        for rule in req.substitutions:
            if rule.approved and rule.requested_sku == sku:
                stock = sum(x.usable for x in req.stock if x.sku == rule.supplied_sku and x.location == location)
                substitute_cover += stock * rule.service_equivalence / rule.input_per_output
        total_sd = math.sqrt(var_demand + var_level + var_supply)
        raw = z * total_sd + inbound_at_risk
        protection = max(0., raw - substitute_cover)
        on_hand = sum(x.usable for x in req.stock if x.sku == sku and x.location == location)
        # Risk state: how active each driver is, how resilient the SKU is, and the lean baseline
        # (demand-only protection at the fitted spread with every other driver calm).
        demand_score = max((demand_state(fits[s.id]["uncertainty"]) for s in services), default=0.) if reliability else 0.
        supply_score = supply_state(profile, recency=req.protection_v5, exit_rules=req.protection_v6,
                                    source_specific=req.protection_v7) if profile is not None else 0.
        resilient = resilience(window, effective, substitute_cover, mu * window, alternate_inside) if (eligible or refill_arc is not None) else 0.
        activity = protection_activity(demand_score, supply_score, resilient) if (reliability and req.protection_decay) else 1.
        # Lean baseline: protection with every active driver removed, i.e. the fitted demand spread
        # and the source's declared (not observed) lead and fill spread, nothing for calibration
        # widening, young regimes, observed tails or open orders at risk.
        sd_fitted = math.sqrt(sum(fits[s.id]["sd"] ** 2 for s in services))
        declared_lead_sd = (primary.lead_sd_days / req.period_days) if primary is not None else 0.
        declared_fill_sd = primary.fill_sd if primary is not None else 0.
        var_supply_declared = ((mu * declared_lead_sd) ** 2 + (mu * window * declared_fill_sd) ** 2) / effective
        lean_baseline = max(0., z * math.sqrt(window * sd_fitted ** 2 + var_supply_declared) - substitute_cover)
        active_drivers: list[dict[str, Any]] = []
        if demand_score > 0:
            reasons = []
            for s in services:
                u = fits[s.id]["uncertainty"] if reliability else {}
                if u.get("calibration_ratio_raw", 1.) > 1.25:
                    reasons.append(f"{s.id}: realized errors {u['calibration_ratio_raw']:.2f}x the fitted spread")
                if u.get("regime_age") is not None and u["regime_age"] < 8:
                    reasons.append(f"{s.id}: level change {u['regime_age']} observation(s) old")
            active_drivers.append({"driver": "demand", "score": demand_score, "reasons": reasons})
        if supply_score > 0:
            active_drivers.append({"driver": "supply", "score": supply_score,
                                   "reasons": [f"late probability {late_probability:.0%}", f"partial-delivery probability {profile.partial_probability:.0%}" if profile is not None else "declared"]})
        if inbound_at_risk > 0:
            active_drivers.append({"driver": "inbound_eta", "score": min(1., inbound_at_risk / max(mu, 1e-9)), "reasons": [f"{inbound_at_risk:.0f} units of open orders at late risk"]})
        demand_wait = max((periods_to_lean_demand(fits[s.id]["uncertainty"]) for s in services), default=0) if reliability else 0
        supply_wait = 0
        if supply_score > 0 and profile is not None:
            # A clean run of receipts as long as the minimum record set retires the supply driver.
            supply_wait = 6 if profile.scope == "observed" else window
            if req.protection_v7 and profile.scope == "observed":
                # Source-specific: what this kind of trouble actually needs, less what has arrived.
                supply_wait = max(0, profile.exit_receipts_needed - profile.recent_clean_run)
        if req.protection_v7 and demand_wait > 0:
            # A declared event that has ended retires its own demand protection at once, unless
            # demand stayed up after it: the event is the reason, and the reason is over.
            events = [e for e in req.events for s in services if e.service == s.id]
            ended = [e for e in events if e.end < 0]
            still_elevated = any(fits[s.id]["uncertainty"].get("pre_change_level") is not None
                                 and fits[s.id]["mean"] > 1.15 * (fits[s.id]["uncertainty"]["pre_change_level"] or 0.)
                                 for s in services)
            if ended and not still_elevated and all(e.end < 0 for e in events):
                demand_wait = 0
        periods_to_lean = max(demand_wait, supply_wait) if activity > .05 else 0
        recent_quiet = all((fits[s.id]["uncertainty"].get("last_outlier_age") is None or fits[s.id]["uncertainty"]["last_outlier_age"] >= 2)
                           for s in services) if reliability else True
        decaying = activity > .05 and recent_quiet and supply_score < .5
        # Placement: the share of protection that must sit locally (transfer lead time of demand
        # spread) versus what can pool upstream when a transfer arc feeds this location.
        feeders = [a for a in req.transfers if a.approved and a.sku == sku and a.destination == location]
        transfer_lead = min((a.lead_periods for a in feeders), default=None)
        local_units = z * math.sqrt((transfer_lead + 1) if req.protection_v6 else max(1, transfer_lead)) * sd_fitted if transfer_lead is not None else protection
        pooled_units = max(0., protection - local_units) if transfer_lead is not None else 0.
        upstream_protection = 0.
        if feeders:
            upstream_protection = sum(x.usable for x in req.stock if x.sku == sku and x.location in {a.origin for a in feeders})
        duplicated = bool(feeders and transfer_lead is not None and transfer_lead <= 2 and on_hand > local_units + mu and upstream_protection > pooled_units + mu)
        # Duplicated buffer (v6): the same demand spread buffered at the branch and again upstream,
        # counted only when the transfer can physically land inside the service window with enough
        # capacity; otherwise the branch stock is local by necessity, not duplication.
        transfer_capacity = max((a.capacity for a in feeders), default=0.)
        # A fed branch has no direct source, so its replenishment window is the horizon; the service
        # window that matters for pooling is the review cadence: pooled stock can stand in for
        # branch stock only when the arc lands within two reviews (the same bound as the v4 flag).
        inside_window = transfer_lead is not None and transfer_lead <= 2
        duplicated_units = 0.
        duplicated_explanation = ""
        if req.protection_v6 and feeders and inside_window and transfer_capacity >= mu and on_hand > local_units and upstream_protection > pooled_units:
            duplicated_units = max(0., min(on_hand - local_units, upstream_protection - pooled_units))
            origin_ids = sorted({a.origin for a in feeders})
            duplicated_explanation = (f"{duplicated_units:.0f} units buffer the same demand spread twice: {location} holds {on_hand:.0f} against a local need of "
                                      f"{local_units:.0f} while {', '.join(origin_ids)} holds {upstream_protection:.0f} against a pooled need of {pooled_units:.0f}; "
                                      f"the transfer lead of {transfer_lead} review(s) is inside the {window}-period service window with capacity {transfer_capacity:.0f} per period")
        # Confirmed demand decline (v7). One low observation is noise; a detected level change that
        # has held for three observations and sits materially below the old level is a decline, and
        # the stock bought for the old level is now excess. No forecast of further decline is made:
        # the new level is the fitted level, and only what exceeds a lean base stock at that level
        # is treated as liquidation stock.
        declining, decline_ratio = False, None
        if req.protection_v7 and reliability and mu > 0:
            ratios = []
            for s in services:
                u = fits[s.id]["uncertainty"]
                pre, age = u.get("pre_change_level"), u.get("regime_age")
                if pre and pre > 0 and age is not None and age >= DECLINE_CONFIRMATION:
                    ratios.append(fits[s.id]["mean"] / pre)
            if ratios and len(ratios) == len(services) and max(ratios) <= DECLINE_RATIO:
                declining, decline_ratio = True, float(max(ratios))
        lean_base_stock = lean_baseline + mu * max(1., window)
        # Regime with hysteresis: entering PROTECT needs a materially active driver; leaving needs
        # the driver to have gone quiet for two observations; RECOVER is the unwinding phase.
        if declining and on_hand > lean_base_stock and activity < .3:
            regime = "RECOVER"
        elif activity >= .3:
            regime = "PROTECT"
        elif activity > .05 and decaying and on_hand > lean_baseline + mu:
            regime = "RECOVER"
        elif activity > .05:
            regime = "PROTECT"
        else:
            regime = "LEAN"
        flags = []
        if activity <= .05 and protection > lean_baseline * 1.25 + 1.:
            flags.append("FALSE_PROTECTION_RISK")
        if thin or any(fits[s.id]["uncertainty"].get("calibration_ratio_raw", 1.) > 1.5 and fits[s.id]["uncertainty"].get("segment_count", 99) < 8 for s in services) if reliability else False:
            flags.append("INSUFFICIENT_CALIBRATION")
        inter = [fits[s.id]["uncertainty"].get("intermittent") for s in services if reliability and fits[s.id]["uncertainty"].get("intermittent")]
        if inter and any(i["historical_spikes"] > 0 or i["size_robust_sd"] > i["size_median"] for i in inter):
            flags.append("INTERMITTENT_TAIL_RISK")
        if duplicated:
            flags.append("DUPLICATED_NETWORK_BUFFER")
        if declining:
            flags.append("DEMAND_DECLINE_CONFIRMED")
        if regime == "RECOVER":
            flags.append("RECOVERY_IN_PROGRESS")
        # Echelon accounting (v5): every unit of recommended protection is local service stock,
        # pooled network stock, source/pipeline protection or temporary risk protection.
        source_units = z * math.sqrt(var_supply_declared) if req.protection_v5 else 0.
        temporary_units = max(0., protection - lean_baseline) if activity > .05 else 0.
        local_service = min(protection, local_units)
        pooled_network = max(0., min(protection - local_service, pooled_units)) if transfer_lead is not None else 0.
        accounted = local_service + pooled_network + min(source_units, max(0., protection - local_service - pooled_network))
        echelon = {"local_service_units": local_service, "pooled_network_units": pooled_network,
                   "source_protection_units": min(source_units, max(0., protection - local_service - pooled_network)),
                   "temporary_risk_units": min(temporary_units, max(0., protection - accounted)) if temporary_units else 0.,
                   "scope": "partition of recommended protection; local = transfer-lead demand spread at the branch, pooled = the remainder that can sit upstream, source = declared lead/fill spread, temporary = active-driver increment"}
        if regime == "PROTECT":
            if supply_score >= demand_score:
                transition = f"LEAN -> PROTECT: supply risk active ({', '.join(d['reasons'][0] for d in active_drivers if d['driver'] == 'supply') or 'lateness or partial deliveries'})" + ("; no alternative can arrive inside the service window" if resilient < .5 else "")
            else:
                transition = "LEAN -> PROTECT: demand risk active (" + ", ".join(r for d in active_drivers if d["driver"] == "demand" for r in d["reasons"]) + ")"
        elif regime == "RECOVER" and declining:
            transition = (f"LEAN -> RECOVER: demand stepped down to {decline_ratio:.0%} of its previous level and has held there for "
                          f"{min((fits[s.id]['uncertainty'].get('regime_age') or 0) for s in services)} observation(s); "
                          f"{max(0., on_hand - lean_base_stock):.0f} units above a lean base stock at the new level are to be run down, "
                          f"transferred, cancelled or left unreplenished")
        elif regime == "RECOVER":
            transition = f"PROTECT -> RECOVER: the risk driver has gone quiet (activity {activity:.2f}) and {max(0., on_hand - lean_baseline):.0f} units above the lean baseline remain to be consumed, transferred or left unreplenished"
        else:
            transition = "LEAN: no active driver; protection is the lean baseline" if activity <= .05 else "LEAN"
        exit_info = {"active_risk_source": (primary.id if (primary is not None and profile is not None and supply_score >= demand_score and supply_score > .05) else ("demand" if demand_score > .05 else None)),
                     "driver_kind": (profile.driver_kind if profile is not None else None),
                     "last_evidence": (profile.last_adverse_known_at if profile is not None else None),
                     "recovery_evidence_receipts": (profile.recent_clean_run if profile is not None else 0),
                     "receipts_needed": (profile.exit_receipts_needed if profile is not None else 0),
                     "backlog_open": bool(profile is not None and profile.backlog_open),
                     "reviews_remaining_until_lean_eligible": (max(0, profile.exit_receipts_needed - profile.recent_clean_run) if (profile is not None and supply_score > .05) else periods_to_lean),
                     "risk_recovery_confidence": (None if profile is None or profile.exit_receipts_needed == 0 else
                                                  round(min(1., profile.recent_clean_run / profile.exit_receipts_needed), 3)),
                     "recovery_evidence_count": (profile.recent_clean_run if profile is not None else 0),
                     "reviews_to_exit_protect": periods_to_lean,
                     "reason_not_lean": (
                         "an open order is overdue and its arrival is still unresolved" if (profile is not None and profile.backlog_open) else
                         f"{max(0, profile.exit_receipts_needed - profile.recent_clean_run)} more clean receipt(s) needed after {profile.driver_kind} trouble"
                         if (profile is not None and supply_score > .05 and profile.driver_kind) else
                         f"demand level change {demand_wait} review(s) from confirmation" if demand_score > .05 and demand_wait > 0 else
                         "stock above the lean baseline is still being consumed" if regime == "RECOVER" else
                         None if activity <= .05 else "an active risk driver has not yet gone quiet")}
        state = {"activity": activity, "demand_score": demand_score, "supply_score": supply_score, "resilience": resilient,
                 "demand_decline_confirmed": declining, "demand_decline_ratio": decline_ratio,
                 "lean_base_stock_units": lean_base_stock, "liquidation_units": (max(0., on_hand - lean_base_stock) if declining else 0.),
                 "duplicated_buffer_units": duplicated_units, "duplicated_buffer_explanation": duplicated_explanation, "exit": exit_info,
                 "alternate_inside_window": alternate_inside, "echelon": echelon, "transition": transition,
                 "risk_active": activity > .05, "decaying": bool(decaying), "periods_to_lean": periods_to_lean,
                 "lean_baseline_units": lean_baseline, "incremental_protection_units": max(0., protection - lean_baseline),
                 "active_drivers": active_drivers, "regime": regime, "flags": flags,
                 "placement": {"local_service_units": local_units, "pooled_network_units": pooled_units, "transfer_lead_periods": transfer_lead,
                               "upstream_stock_units": upstream_protection},
                 "false_protection_flag": "FALSE_PROTECTION_RISK" in flags,
                 "scope": "activity scales the optimizer's quantile protection and the stress hedge; zero is lean"}
        drivers = {"demand_spread": z * math.sqrt(var_demand), "forecast_level": z * math.sqrt(var_level),
                   "lead_time_spread": z * math.sqrt(var_lead / effective), "fill_spread": z * math.sqrt(var_fill / effective),
                   "inbound_eta_risk": inbound_at_risk, "substitution_credit": -min(substitute_cover, raw),
                   "correlation_penalty": z * (math.sqrt(var_lead + var_fill) - math.sqrt((var_lead + var_fill) / effective))}
        criticality = max((s.selling_price + s.sla_per_unmet - skus[sku].asset_value) / skus[sku].asset_value for s in services)
        stance = "lean" if protection <= .25 * mu * window else "protect"
        if reliability and req.protection_decay and activity <= .05:
            stance = "lean"
        if not eligible and refill_arc is None:
            stance = "no_replenishment"
        rows.append({"sku": sku, "location": location, "services": [s.id for s in services],
                     "echelon_origin": echelon_origin,
                     "weighted_target": weighted_target, "top_target": top_target, "top_priority": top_priority,
                     "quantile_z": z, "mean_demand_per_period": mu, "replenishment_periods": window,
                     "protection_units": protection, "protection_periods_of_demand": protection / mu if mu > 0 else None,
                     "replenished_by_transfer_arc": (refill_arc.id if refill_arc is not None else None),
                     "on_hand_units": on_hand, "drivers_units": drivers,
                     "calibration_ratio": calibration, "supply_scope": supply_scope,
                     "late_probability": late_probability, "effective_independent_sources": effective,
                     "shared_domains": diversity["shared_domains"], "substitute_cover_units": substitute_cover,
                     "criticality_margin_ratio": criticality, "data_sufficiency": "thin" if thin else "adequate",
                     "stance": stance, "state": state,
                     "explanation": explain(sku, location, protection, mu, window, drivers, effective,
                                            diversity["shared_domains"], substitute_cover, supply_scope, late_probability, thin, eligible)
                                    + state_sentence(state)})
    return rows


def state_sentence(state: dict) -> str:
    if not state["risk_active"]:
        return " Risk state: lean (no active driver)."
    names = ", ".join(d["driver"] for d in state["active_drivers"]) or "none"
    trend = "decaying" if state["decaying"] else "active"
    return f" Risk state: {trend} ({names}, activity {state['activity']:.2f}); expected return to lean in {state['periods_to_lean']} period(s) if nothing new happens."


def explain(sku, location, protection, mu, window, drivers, effective, shared, substitute_cover, supply_scope, late_probability, thin, eligible) -> str:
    name = f"{sku} at {location}"
    if not eligible:
        return f"{name} has no approved cleared source; protection cannot be replenished, only allocated."
    positive = sorted(((k, v) for k, v in drivers.items() if v > 0), key=lambda kv: -kv[1])
    top = positive[0] if positive else None
    labels = {"demand_spread": "demand variability", "forecast_level": "forecast level uncertainty",
              "lead_time_spread": "the supplier lead-time tail", "fill_spread": "supplier fill variability",
              "inbound_eta_risk": "late-risk on open purchase orders", "correlation_penalty": "correlated supply exposure"}
    if protection <= .25 * mu * window:
        reason = f"replenishment lands within {window} period(s)"
        if effective > 1.5:
            reason += f" from {effective:.1f} effectively independent sources"
        if substitute_cover > 0:
            reason += f" and approved substitute stock covers {substitute_cover:.0f} units"
        text = f"{name} does not need extra inventory: {reason}."
    else:
        detail = f"{labels.get(top[0], top[0])} contributes {top[1]:.0f} of {protection:.0f} units" if top else f"{protection:.0f} units"
        text = f"{name} needs more protection: {detail}"
        if supply_scope == "observed" and late_probability > .2:
            text += f"; its observed supply tail widened (late probability {late_probability:.0%})"
        if shared:
            text += f"; sources share {', '.join(shared)} so they count as {effective:.1f} independent source(s)"
        text += "."
    if thin:
        text += " Demand history is thin; the spread is provisional."
    return text
