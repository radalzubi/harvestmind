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

import math

from zaad.full.contracts import Request
from zaad.full.uncertainty import SupplyProfile, diversification, z_for
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
        drivers = {"demand_spread": z * math.sqrt(var_demand), "forecast_level": z * math.sqrt(var_level),
                   "lead_time_spread": z * math.sqrt(var_lead / effective), "fill_spread": z * math.sqrt(var_fill / effective),
                   "inbound_eta_risk": inbound_at_risk, "substitution_credit": -min(substitute_cover, raw),
                   "correlation_penalty": z * (math.sqrt(var_lead + var_fill) - math.sqrt((var_lead + var_fill) / effective))}
        criticality = max((s.selling_price + s.sla_per_unmet - skus[sku].asset_value) / skus[sku].asset_value for s in services)
        stance = "lean" if protection <= .25 * mu * window else "protect"
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
                     "stance": stance, "explanation": explain(sku, location, protection, mu, window, drivers, effective,
                                                              diversity["shared_domains"], substitute_cover, supply_scope, late_probability, thin, eligible)})
    return rows


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
