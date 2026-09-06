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
    rows = []
    for sku, location in pairs:
        services = [s for s in req.services if s.sku == sku and s.location == location]
        weighted_target, top_target, top_priority = _weighted_target(services, customers, fits)
        z = z_for(weighted_target)
        mu = sum(fits[s.id]["mean"] for s in services)
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
        if eligible:
            leads = {s.id: dates(req, s, 0)[1] for s in eligible}
            replenishment = min(leads.values()) + 1     # review period plus the earliest receipt
            primary = eligible[0]
            profile = supply.get(primary.id)
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
        supply_score = supply_state(profile, recency=req.protection_v5) if profile is not None else 0.
        resilient = resilience(window, effective, substitute_cover, mu * window, alternate_inside) if eligible else 0.
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
        periods_to_lean = max(demand_wait, supply_wait) if activity > .05 else 0
        recent_quiet = all((fits[s.id]["uncertainty"].get("last_outlier_age") is None or fits[s.id]["uncertainty"]["last_outlier_age"] >= 2)
                           for s in services) if reliability else True
        decaying = activity > .05 and recent_quiet and supply_score < .5
        # Placement: the share of protection that must sit locally (transfer lead time of demand
        # spread) versus what can pool upstream when a transfer arc feeds this location.
        feeders = [a for a in req.transfers if a.approved and a.sku == sku and a.destination == location]
        transfer_lead = min((a.lead_periods for a in feeders), default=None)
        local_units = z * math.sqrt(max(1, transfer_lead)) * sd_fitted if transfer_lead is not None else protection
        pooled_units = max(0., protection - local_units) if transfer_lead is not None else 0.
        upstream_protection = 0.
        if feeders:
            upstream_protection = sum(x.usable for x in req.stock if x.sku == sku and x.location in {a.origin for a in feeders})
        duplicated = bool(feeders and transfer_lead is not None and transfer_lead <= 2 and on_hand > local_units + mu and upstream_protection > pooled_units + mu)
        # Regime with hysteresis: entering PROTECT needs a materially active driver; leaving needs
        # the driver to have gone quiet for two observations; RECOVER is the unwinding phase.
        if activity >= .3:
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
        elif regime == "RECOVER":
            transition = f"PROTECT -> RECOVER: the risk driver has gone quiet (activity {activity:.2f}) and {max(0., on_hand - lean_baseline):.0f} units above the lean baseline remain to be consumed, transferred or left unreplenished"
        else:
            transition = "LEAN: no active driver; protection is the lean baseline" if activity <= .05 else "LEAN"
        state = {"activity": activity, "demand_score": demand_score, "supply_score": supply_score, "resilience": resilient,
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
        if not eligible:
            stance = "no_replenishment"
        rows.append({"sku": sku, "location": location, "services": [s.id for s in services],
                     "weighted_target": weighted_target, "top_target": top_target, "top_priority": top_priority,
                     "quantile_z": z, "mean_demand_per_period": mu, "replenishment_periods": window,
                     "protection_units": protection, "protection_periods_of_demand": protection / mu if mu > 0 else None,
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
