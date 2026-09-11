"""The `sourcing` report block (P3): per SKU and destination, the recommended commitment and its split
across approved source options, each option's landed economics, capacity, executability, reliability
provenance, shared-risk groups, incumbent against recommended share, and operator-language reasons.
Reads the frozen report (actions, economics, supply profiles, reasons); adds no decision. Ownership
stays P1 (the total commitment) and P3 (its decomposition); approval stays with the operator."""
from __future__ import annotations

from collections import defaultdict
import math
from typing import Any

from zaad.full.economics import NO_MATERIAL_IMPROVEMENT
from zaad.full.worlds import dates, next_open
from zaad.sectors.contracts import resolve as sector_physics
from zaad.sourcing.contracts import WEAK_PROVENANCE, resolve

PRINCIPLE = "Source where total landed economics and supply resilience are best, not where unit price is lowest."
PRINCIPLE_2 = "Diversification is not the objective. Better decisions under real supply uncertainty are the objective."


def _purchases(solution) -> dict[tuple[str, int], float]:
    return dict(solution.purchases) if solution is not None and solution.usable_plan else {}


def _eligibility(req, source, physics, calendars) -> tuple[bool, str | None]:
    if not source.approved:
        return False, "not qualified: the source is not approved"
    if source.compliance != "cleared":
        return False, f"not qualified: compliance is {source.compliance}"
    order_date = next_open(req.as_of, calendars[source.order_calendar])
    if order_date > source.quote_expires:
        return False, "the quote has expired"
    if physics is not None:
        if not physics.location_ok(source.sku, source.destination):
            return False, f"{source.destination} cannot store {physics.state(source.sku).lower()} goods"
        life = physics.receipt_life(source.sku, source.id)
        if life <= physics.min_receipt(source.sku):
            return False, (f"expected remaining sellable life at receipt ({life} periods) is below the declared requirement "
                           f"({physics.min_receipt(source.sku)} periods)")
    if all(min(source.maximum, c) <= 0 for c in source.capacity_by_period[:req.horizon]):
        return False, "no capacity in any period of the plan"
    return True, None


def _landed(req, source, terms) -> dict[str, Any]:
    term = terms[source.terms]
    price = source.unit_price * term.fx_rate_to_currency
    landed = price + source.freight_per_unit + source.handling_per_unit + price * term.financing_fee_fraction
    departure, arrival = dates(req, source, 0)
    trigger = {"order": 0, "shipment": departure, "arrival": arrival}[term.balance_trigger]
    pay_period = trigger + math.ceil(term.net_days / req.period_days)
    rate = req.liquidity.cost_of_capital_per_period
    # report-only view of the payment timing: the capital the balance ties up until it is paid, at the
    # declared cost of capital (the model prices it through the cash balance, never twice)
    timing_value = rate * price * (1. - term.deposit_fraction) * pay_period
    return {"unit_price": price, "freight_per_unit": source.freight_per_unit, "handling_per_unit": source.handling_per_unit,
            "financing_fee_per_unit": price * term.financing_fee_fraction, "fixed_order_fee": source.fixed_order_fee,
            "landed_unit_cost": landed, "payment_terms": {"deposit_fraction": term.deposit_fraction, "balance_trigger": term.balance_trigger,
                                                          "net_days": term.net_days, "expected_payment_period": pay_period},
            "payment_timing_value_per_unit": timing_value, "landed_unit_cost_after_terms": landed - timing_value,
            "scope": "per unit, report only; the plan's economics come from the settled ledger"}


def _share(q: float, total: float) -> float | None:
    return (q / total) if total > 1e-9 else None


def sourcing_block(req, final, incumbent, report: dict) -> dict[str, Any]:
    sourcing = resolve(req)
    if sourcing is None:
        return {}
    physics = sector_physics(req)
    terms = {t.id: t for t in req.terms}
    calendars = {c.id: c for c in req.calendars}
    supply = report.get("supply_profiles") or {}
    econ_prov = req.economics_provenance or {}
    H = req.horizon
    final_p, inc_p = _purchases(final), _purchases(incumbent)
    abstained = report.get("status") == "RETAIN_INCUMBENT" or any(NO_MATERIAL_IMPROVEMENT in str(r) for r in report.get("reasons", []))
    materiality = (report.get("economics") or {}).get("materiality")
    pairs: dict[tuple[str, str], list] = defaultdict(list)
    for s in req.sources:
        pairs[s.sku, s.destination].append(s)
    rows: list[dict[str, Any]] = []
    sentences: list[str] = []
    for (sku, destination), options in sorted(pairs.items()):
        total0 = sum(final_p.get((s.id, 0), 0.) for s in options)
        totalH = sum(final_p.get((s.id, t), 0.) for s in options for t in range(H))
        inc0 = sum(inc_p.get((s.id, 0), 0.) for s in options)
        incH = sum(inc_p.get((s.id, t), 0.) for s in options for t in range(H))
        declared_mix = sourcing.incumbent_mix.get((sku, destination), {})
        option_rows = []
        for s in sorted(options, key=lambda s: s.id):
            eligible, why = _eligibility(req, s, physics, calendars)
            q0 = final_p.get((s.id, 0), 0.)
            qH = sum(final_p.get((s.id, t), 0.) for t in range(H))
            i0 = inc_p.get((s.id, 0), 0.)
            iH = sum(inc_p.get((s.id, t), 0.) for t in range(H))
            cap0 = min(s.maximum, s.capacity_by_period[0]) if eligible else 0.
            profile = supply.get(s.id) or {}
            groups = [{"id": g.id, "kind": g.kind, "correlation": g.correlation, "provenance": g.provenance,
                       "weak_evidence": g.provenance in WEAK_PROVENANCE, "members": list(g.members)} for g in sourcing.groups_of.get(s.id, ())]
            constraint = [c for c in sourcing.shares.get((sku, destination), ()) if c.source == s.id]
            packs = [m for m in (s.multiple, s.case_multiple, s.pallet_multiple, s.transport_multiple) if m > 0]
            switching = sourcing.switching.get(s.id)
            fill_prov = econ_prov.get(f"source.{s.id}.fill") or econ_prov.get(f"source.{s.supplier}.fill")
            lead_prov = econ_prov.get(f"source.{s.id}.lead") or econ_prov.get(f"source.{s.supplier}.lead")
            option_rows.append({
                "source": s.id, "supplier": s.supplier, "route": list(s.route), "eligible": eligible, "ineligible_reason": why,
                "quantity_period_0": q0, "share_period_0": _share(q0, total0), "quantity_plan": qH, "share_plan": _share(qH, totalH),
                "incumbent_quantity_period_0": i0, "incumbent_share_period_0": _share(i0, inc0), "incumbent_share_plan": _share(iH, incH),
                "declared_incumbent_share": declared_mix.get(s.id), "in_incumbent_mix": s.id in sourcing.incumbent_sources,
                "expected_receipt_period": dates(req, s, 0)[1] if eligible else None, "expected_fill": float(profile.get("fill_mean", s.fill_mean)),
                "lead_days": s.lead_days, "lead_sd_days": s.lead_sd_days,
                "capacity_period_0": cap0, "capacity_binding": bool(eligible and cap0 > 0 and q0 >= cap0 - 1e-6),
                "minimum_order": s.minimum, "packs": packs, "executable": all(abs(q0 / m - round(q0 / m)) <= 1e-6 for m in packs) if q0 > 0 else True,
                "landed": _landed(req, s, terms),
                "reliability": {"scope": profile.get("scope", "declared"), "records": profile.get("records", 0), "fill_mean": profile.get("fill_mean", s.fill_mean),
                                "fill_sd": profile.get("fill_sd", s.fill_sd), "late_probability": profile.get("late_probability"),
                                "fill_provenance": fill_prov, "lead_provenance": lead_prov,
                                "weak_evidence": bool(fill_prov in (None, "NOT_AVAILABLE", "CONFIGURED_ASSUMPTION") and profile.get("scope", "declared") != "observed")},
                "risk_groups": groups, "shared_risk_weak_evidence": sourcing.weak_evidence(s.id),
                "share_constraints": [{"minimum_share": c.minimum_share, "maximum_share": c.maximum_share, "committed_units": c.committed_units,
                                       "scope": c.scope, "provenance": c.provenance} for c in constraint],
                "switching_cost": ({"cost": switching.cost, "kind": switching.kind, "provenance": switching.provenance,
                                    "applies": s.id not in sourcing.incumbent_sources, "charged": bool(qH > 0 and s.id not in sourcing.incumbent_sources)}
                                   if switching is not None else None)})
        used = [r for r in option_rows if r["quantity_plan"] > 0]
        if totalH <= 1e-9:
            recommendation = "NO_ORDER"
        elif abstained:
            recommendation = "RETAIN_INCUMBENT_MIX"
        elif any(abs((r["share_plan"] or 0.) - (r["incumbent_share_plan"] or 0.)) > .05 for r in option_rows):
            recommendation = "CHANGE_SOURCE_MIX"
        else:
            recommendation = "COMMIT_AS_INCUMBENT_MIX"
        rows.append({"sku": sku, "destination": destination, "order_period": 0,
                     "total_committed_period_0": total0, "total_committed_plan": totalH,
                     "incumbent_total_period_0": inc0, "incumbent_total_plan": incH,
                     "sources_used_plan": [r["source"] for r in used], "recommendation": recommendation,
                     "owner": {"total_commitment": "P1 purchasing economics (or P0 protection / recovery when it owns the review)", "source_split": "P3 sourcing portfolio"},
                     "options": option_rows})
        # ── operator-language reasons ──
        by_id = {r["source"]: r for r in option_rows}
        eligible_rows = [r for r in option_rows if r["eligible"]]
        for r in option_rows:
            if not r["eligible"] and r["ineligible_reason"]:
                sentences.append(f"{sku} at {destination}: {r['supplier']} ({r['source']}) was rejected because {r['ineligible_reason']}.")
        for r in used:
            for other in eligible_rows:
                if other is r or other["quantity_plan"] > 0:
                    continue
                if (other["landed"]["unit_price"] < r["landed"]["unit_price"] - 1e-9
                        and other["landed"]["landed_unit_cost_after_terms"] >= r["landed"]["landed_unit_cost_after_terms"] - 1e-9):
                    sentences.append(f"{sku} at {destination}: {other['supplier']} has a lower unit price ({other['landed']['unit_price']:.2f} against "
                                     f"{r['landed']['unit_price']:.2f}), but {r['supplier']} is cheaper on total landed economics after freight, handling and payment terms "
                                     f"({r['landed']['landed_unit_cost_after_terms']:.2f} against {other['landed']['landed_unit_cost_after_terms']:.2f} per unit).")
        for r in used:
            if r["capacity_binding"] and any(o["quantity_period_0"] > 0 for o in used if o is not r):
                others = ", ".join(f"{o['supplier']} ({o['quantity_period_0']:.0f})" for o in used if o is not r and o["quantity_period_0"] > 0)
                sentences.append(f"{sku} at {destination}: {r['supplier']} cannot cover the full recommendation because its declared capacity is "
                                 f"{r['capacity_period_0']:.0f} units this period, so the remaining quantity is assigned to {others}.")
        if recommendation == "RETAIN_INCUMBENT_MIX":
            sentences.append(f"{sku} at {destination}: ZAAD retained your current supplier mix because the modeled improvement from changing it is not material.")
        seen_groups: set[str] = set()
        for r in used:
            for g in r["risk_groups"]:
                if g["id"] in seen_groups:
                    continue
                seen_groups.add(g["id"])
                co = [by_id[m]["supplier"] for m in g["members"] if m in by_id and by_id[m]["quantity_plan"] > 0]
                if len(co) >= 2:
                    shared = " and ".join(sorted(set(co)))
                    what = {"PLANT": "origin plant", "MANUFACTURER": "manufacturer", "PORT": "port", "ROUTE": "route", "CARRIER": "carrier",
                            "3PL": "logistics provider", "PACKAGING": "packaging supplier", "UPSTREAM_FACILITY": "upstream facility"}.get(g["kind"], "physical dependency")
                    degree = "" if g["correlation"] >= .999 else f" (declared correlation {g['correlation']:.2f})"
                    weak = " The evidence for this dependency is weak (" + g["provenance"] + "), so the shared exposure is a stated assumption." if g["weak_evidence"] else ""
                    sentences.append(f"{sku} at {destination}: {shared} share the same {what}{degree}, so ZAAD does not treat the split as independent supply protection.{weak}")
        for r in option_rows:
            for c in r["share_constraints"]:
                if r["share_plan"] is None:
                    continue
                met = c["minimum_share"] - 1e-6 <= r["share_plan"] <= c["maximum_share"] + 1e-6
                if c["minimum_share"] > 0 or c["maximum_share"] < 1:
                    limits = (f"at least {c['minimum_share']:.0%}" if c["minimum_share"] > 0 else "") + (" and " if c["minimum_share"] > 0 and c["maximum_share"] < 1 else "") \
                             + (f"at most {c['maximum_share']:.0%}" if c["maximum_share"] < 1 else "")
                    if met:
                        sentences.append(f"{sku} at {destination}: your declared share limit for {r['supplier']} ({limits}) is honoured (planned share {r['share_plan']:.0%}).")
                    else:
                        sentences.append(f"{sku} at {destination}: the retained plan gives {r['supplier']} {r['share_plan']:.0%}, outside your declared limit ({limits}); "
                                         f"it is the operator's own dated orders, not a ZAAD recommendation.")
        for r in option_rows:
            sc = r["switching_cost"]
            if sc and sc["applies"] and r["quantity_plan"] <= 0 and r["eligible"]:
                sentences.append(f"{sku} at {destination}: {r['supplier']} is not used; starting to buy from it would cost {sc['cost']:,.0f} "
                                 f"({sc['kind'].lower()}), which the modeled saving does not justify.")
            elif sc and sc["charged"]:
                sentences.append(f"{sku} at {destination}: the plan starts buying from {r['supplier']} and carries its declared {sc['kind'].lower()} cost of {sc['cost']:,.0f}.")
        if len(eligible_rows) >= 2 and len(used) == 1 and totalH > 0 and not any(r["risk_groups"] for r in eligible_rows):
            weak = [r for r in eligible_rows if r["reliability"]["weak_evidence"] and r["quantity_plan"] <= 0]
            if weak:
                sentences.append(f"{sku} at {destination}: {', '.join(r['supplier'] for r in weak)} carries no observed fill or lead history; "
                                 f"ZAAD does not credit a second source with resilience it cannot evidence.")
        if any(r["shared_risk_weak_evidence"] for r in used) and len(used) >= 2:
            sentences.append(f"{sku} at {destination}: the shared-risk declaration between the sources used rests on weak evidence; no independence benefit is claimed.")
    return {"version": "zaad.sourcing.1.0", "principles": [PRINCIPLE, PRINCIPLE_2],
            "recommendation_status": report.get("status"), "selected_policy": report.get("selected_policy"),
            "abstained": bool(abstained), "materiality": materiality,
            "risk_groups": [{"id": g.id, "kind": g.kind, "members": list(g.members), "correlation": g.correlation, "provenance": g.provenance,
                             "weak_evidence": g.provenance in WEAK_PROVENANCE, "evidence": g.evidence} for g in sourcing.portfolio.risk_groups],
            "pairs": rows, "explanations": sentences,
            "approval_required": True, "executable_purchase_order": False,
            "scope": ("the frozen joint decision chose the total commitment (P1) and its split across approved sources (P3) under the declared "
                      "economics, capacity, uncertainty and shared risk; no source score, no diversification rule, no autonomous order")}
