"""Pre-registered P3 sourcing fixtures (docs/zaad_full/evidence/p3/P3_FIXTURE_SPEC.md).

Every fixture is the P2 network frame (`zaad.meio.fixtures_p2.p2_request`) with additional approved
sources into the same destination, cloned from `src_A` with the overrides listed in the spec, an
optional second SKU sharing the same suppliers, optional sector physics, and the sourcing block.
Synthetic throughout (`evidence_label = SYNTHETIC`)."""
from __future__ import annotations

from typing import Any

from zaad.full.contracts import Request
from zaad.meio.fixtures_p2 import p2_request

DECLARED = "OPERATOR_DECLARED"
REVIEWS = 8
SEEDS = (41001, 41002)
TERMS_NET45 = {"id": "net45", "deposit_fraction": 0., "balance_trigger": "order", "net_days": 45, "financing_fee_fraction": 0.,
               "fx_rate_to_currency": 1., "currency": "USD", "fx_basis": "same_currency", "letter_of_credit_fraction": 0.}
TERMS_NET60 = {**TERMS_NET45, "id": "net60", "net_days": 60}
TERMS_PREPAY = {**TERMS_NET45, "id": "prepay", "deposit_fraction": 1., "net_days": 0}


def _profile(sku: str, sector: str, **fields: Any) -> dict[str, Any]:
    return {"sku": sku, "sector": sector, **fields, "provenance": {k: DECLARED for k in fields}}


def _add_source(payload: dict, new_id: str, supplier: str, *, sku: str = "A", destination: str = "central", route_via: tuple[str, ...] = (),
                resource: str | None = None, capacity: float | None = None, **fields: Any) -> None:
    base = next(s for s in payload["sources"] if s["sku"] == sku and s["id"] == ("src_A" if sku == "A" else f"src_A_{sku}"))
    H = payload["horizon"]
    res = resource or f"cap_{supplier}"
    if not any(r["id"] == res for r in payload["resources"]):
        payload["resources"].append({**payload["resources"][0], "id": res, "capacity_by_period": [capacity if capacity is not None else 1e6] * H,
                                     "failure_domains": [supplier]})
    # a cloned source never inherits the base source's own capacity: unlimited unless the spec says otherwise
    src = {**base, "id": new_id, "supplier": supplier, "sku": sku, "destination": destination, "route": [supplier, *route_via, destination],
           "resources": [res], "capacity_by_period": [capacity if capacity is not None else 1e6] * H, **fields}
    payload["sources"].append(src)


def _clone_sku(payload: dict, new: str, *, shelf_life: int = 52, price: float | None = None) -> None:
    """A second SKU with the same suppliers (every source of A cloned), lanes, services, history and stock."""
    base_sku = next(s for s in payload["skus"] if s["id"] == "A")
    payload["skus"].append({**base_sku, "id": new, "shelf_life": shelf_life, **({"asset_value": price, "terminal_value": price * .8} if price else {})})
    for src in [s for s in payload["sources"] if s["sku"] == "A"]:
        payload["sources"].append({**src, "id": f"{src['id']}_{new}", "sku": new, **({"unit_price": price} if price else {})})
    for arc in [a for a in payload["transfers"] if a["sku"] == "A"]:
        payload["transfers"].append({**arc, "id": f"{arc['id']}_{new}", "sku": new})
    for svc in [s for s in payload["services"] if s["sku"] == "A"]:
        payload["services"].append({**svc, "id": f"{svc['id']}_{new}", "sku": new, **({"selling_price": price * 2} if price else {})})
        for row in [h for h in payload["history"] if h["service"] == svc["id"]]:
            payload["history"].append({**row, "service": f"{svc['id']}_{new}"})
    for lot in [x for x in payload["stock"] if x["sku"] == "A"]:
        payload["stock"].append({**lot, "id": f"{lot['id']}_{new}", "sku": new, "expires_in": min(lot["expires_in"], shelf_life)})


def sourcing_request(spec: dict[str, Any], seed: int, **overrides: Any) -> Request:
    args = {**spec.get("args", {}), **overrides}
    req = p2_request(seed=seed, **args)
    payload = req.model_dump(mode="json")
    known = {"known_at": payload["skus"][0]["known_at"]}
    for terms in spec.get("terms", []):
        payload["terms"].append({**known, **terms})
    for src_id, fields in spec.get("source_overrides", {}).items():
        for src in payload["sources"]:
            if src["id"] == src_id:
                src.update(fields)
    for loc in spec.get("extra_locations", []):
        payload["locations"].append({**payload["locations"][0], **loc})
    for lane in spec.get("extra_lanes", []):
        payload["transfers"].append({**payload["transfers"][0], **lane})
    for new_id, kw in spec.get("sources", {}).items():
        _add_source(payload, new_id, **kw)
    for new, kw in spec.get("extra_skus", {}).items():
        _clone_sku(payload, new, **kw)
    for supplier, terms in spec.get("supplier_terms", {}).items():
        payload["supplier_terms"] = [st for st in payload.get("supplier_terms", []) if st["supplier"] != supplier]
        payload["supplier_terms"].append({**known, "id": f"terms_{supplier}", "supplier": supplier, **terms,
                                          "provenance": {k: "CONFIGURED_ASSUMPTION" for k in terms if k != "units_per_pallet"}})
    physics = spec.get("physics")
    if physics:
        for sku, life in physics.get("shelf_life", {}).items():
            for s in payload["skus"]:
                if s["id"] == sku:
                    s["shelf_life"] = life
            for lot in payload["stock"]:
                if lot["sku"] == sku and lot["expires_in"] > life:
                    lot["expires_in"] = life
        for loc_id, states in physics.get("location_states", {}).items():
            for loc in payload["locations"]:
                if loc["id"] == loc_id:
                    loc["storage_states"] = list(states)
        for lane_id, states in physics.get("lane_states", {}).items():
            for arc in payload["transfers"]:
                if arc["id"] == lane_id:
                    arc["storage_states"] = list(states)
        payload["sector_mode"] = physics.get("mode")
        payload["sku_physics"] = [_profile(sku, kw.pop("sector", physics.get("mode", "COMMERCIAL")), **kw)
                                 for sku, kw in {k: dict(v) for k, v in physics.get("skus", {}).items()}.items()]
    for loc_id, fields in spec.get("location_overrides", {}).items():
        for loc in payload["locations"]:
            if loc["id"] == loc_id:
                loc.update(fields)
    if "stresses" in spec:
        payload["stresses"] = spec["stresses"]
    if "sourcing" in spec:
        payload["sourcing"] = spec["sourcing"]
    payload.update(spec.get("request_overrides", {}))
    return Request.model_validate(payload)


def _mix(*rows: tuple[str, float], sku: str = "A", destination: str = "central") -> list[dict[str, Any]]:
    return [{"sku": sku, "destination": destination, "source": sid, "share": share, "provenance": DECLARED} for sid, share in rows]


CENTRAL_ALL = {"central": ["AMBIENT", "CHILLED", "FROZEN"], "north": ["AMBIENT", "CHILLED", "FROZEN"], "south": ["AMBIENT", "CHILLED"]}
FEE = {"fixed_order_fee": 25.}

FIXTURES: dict[str, dict[str, Any]] = {
    # ── ECONOMICS ─────────────────────────────────────────────────────────────
    "E1_dominant_source": {"family": "economics", "tolerance": .02, "args": {},
        "sources": {"src_B": {"supplier": "supplier_b", "unit_price": 5.4, "freight_per_unit": .3, "lead_days": 14, "fill_mean": .95, "capacity": 400.}},
        "sourcing": {"incumbent_shares": _mix(("src_A", 1.))}, "principle": "b_unused"},
    "E2_landed_beats_unit_price": {"family": "economics", "tolerance": .02, "args": {"cost_of_capital_per_year": .12},
        "terms": [TERMS_NET45, TERMS_PREPAY], "source_overrides": {"src_A": {"terms": "net45"}},
        "sources": {"src_B": {"supplier": "supplier_b", "unit_price": 4.6, "freight_per_unit": .6, "handling_per_unit": .1, "terms": "prepay"}},
        "sourcing": {"incumbent_shares": _mix(("src_A", 1.))}, "principle": "a_dominant_share"},
    "E3_price_break_scale": {"family": "economics", "tolerance": .02, "args": {"demand": 150.},
        "sources": {"src_B_tier1": {"supplier": "supplier_b", "unit_price": 5.0, "maximum": 200., "exclusive_quote_group": "b_tiers"},
                    "src_B_tier2": {"supplier": "supplier_b", "unit_price": 4.4, "minimum": 250., "exclusive_quote_group": "b_tiers"}},
        "sourcing": {"incumbent_shares": _mix(("src_A", 1.))}, "principle": "tier2_when_large"},
    "E4_moq_mov_small_order": {"family": "economics", "tolerance": .02, "args": {},
        "sources": {"src_B": {"supplier": "supplier_b", "unit_price": 4.5, "minimum": 1200.}},
        "supplier_terms": {"supplier_b": {"minimum_order_value": 6000., "fixed_order_cost": 60.}},
        "sourcing": {"incumbent_shares": _mix(("src_A", 1.))}, "principle": "b_orders_executable"},
    "E5_payment_terms_preference": {"family": "economics", "tolerance": .02, "args": {"cost_of_capital_per_year": .15},
        "terms": [TERMS_NET60, TERMS_PREPAY], "source_overrides": {"src_A": {"terms": "net60"}},
        "sources": {"src_B": {"supplier": "supplier_b", "terms": "prepay"}},
        "sourcing": {"incumbent_shares": _mix(("src_A", .5), ("src_B", .5))}, "principle": "a_dominant_share"},
    "E6_switching_cost_retains_incumbent": {"family": "economics", "tolerance": .02, "args": {},
        "sources": {"src_B": {"supplier": "supplier_b", "unit_price": 4.925}},
        "sourcing": {"incumbent_shares": _mix(("src_A", 1.)), "switching_costs": [{"source": "src_B", "cost": 2000., "provenance": DECLARED}]},
        "principle": "b_unused"},
    # ── RELIABILITY / PORTFOLIO ───────────────────────────────────────────────
    "R1_cheap_unreliable": {"family": "reliability", "tolerance": .03, "args": {"supplier_fill": .99, "supplier_fill_sd": .01},
        "sources": {"src_B": {"supplier": "supplier_b", "unit_price": 4.6, "fill_mean": .85, "fill_sd": .10, "lead_sd_days": 7.}},
        "sourcing": {"incumbent_shares": _mix(("src_A", 1.))}, "principle": "not_worse"},
    "R2_capacity_forces_split": {"family": "reliability", "tolerance": .03, "args": {"demand": 150., "supplier_capacity": 200.},
        "sources": {"src_B": {"supplier": "supplier_b", "unit_price": 5.3}},
        "sourcing": {"incumbent_shares": _mix(("src_A", 1.))}, "principle": "a_at_capacity_then_b", "service_mode": "floor"},
    "R3_independent_tail_benefit": {"family": "reliability", "tolerance": .03, "args": {},
        "sources": {"src_B": {"supplier": "supplier_b", "unit_price": 5.2}},
        "stresses": [{"name": "supplier_a_closure", "fill_multiplier": .3, "extra_lead_days": 14, "demand_multiplier": 1., "recovery_period": 6,
                      "shared_failure": False, "affected_resources": ["supplier_cap"]}],
        "sourcing": {"incumbent_shares": _mix(("src_A", 1.))}, "principle": "not_worse"},
    "R4_shared_plant_no_fake_diversification": {"family": "reliability", "tolerance": .03, "args": {},
        "source_overrides": {"src_A": FEE}, "sources": {"src_B": {"supplier": "supplier_b", **FEE}},
        "sourcing": {"risk_groups": [{"id": "plant_1", "kind": "PLANT", "members": ["src_A", "src_B"], "correlation": 1., "provenance": DECLARED}],
                     "incumbent_shares": _mix(("src_A", 1.))}, "principle": "no_split"},
    "R5_shared_port_risk": {"family": "reliability", "tolerance": .03, "args": {},
        "source_overrides": {"src_A": {"route": ["supplier", "port_x", "central"]}},
        "sources": {"src_B": {"supplier": "supplier_b", "unit_price": 5.1, "route_via": ("port_x",)}},
        "stresses": [{"name": "port_congestion", "fill_multiplier": .8, "extra_lead_days": 10, "demand_multiplier": 1., "recovery_period": 5,
                      "shared_failure": True}],
        "sourcing": {"risk_groups": [{"id": "port_x", "kind": "PORT", "members": ["src_A", "src_B"], "correlation": .8, "provenance": "PHYSICAL_DEPENDENCY"}],
                     "incumbent_shares": _mix(("src_A", 1.))}, "principle": "group_listed"},
    "R6_identical_no_split": {"family": "reliability", "tolerance": .03, "args": {},
        "source_overrides": {"src_A": FEE}, "sources": {"src_B": {"supplier": "supplier_b", **FEE}},
        "sourcing": {"incumbent_shares": _mix(("src_A", 1.))}, "principle": "no_split"},
    # ── CONSTRAINTS ───────────────────────────────────────────────────────────
    "C1_supplier_max_capacity": {"family": "constraints", "tolerance": .02, "args": {"demand": 250., "supplier_capacity": 300.},
        "sources": {"src_B": {"supplier": "supplier_b", "unit_price": 5.3, "capacity": 300.}},
        "sourcing": {"incumbent_shares": _mix(("src_A", .5), ("src_B", .5))}, "principle": "both_used_within_capacity"},
    "C2_declared_min_max_share": {"family": "constraints", "tolerance": .02, "args": {},
        "sources": {"src_B": {"supplier": "supplier_b", "unit_price": 5.25}},
        "sourcing": {"share_constraints": [{"sku": "A", "destination": "central", "source": "src_B", "minimum_share": .3, "scope": "period", "provenance": DECLARED},
                                           {"sku": "A", "destination": "central", "source": "src_A", "maximum_share": .7, "scope": "period", "provenance": DECLARED}],
                     "incumbent_shares": _mix(("src_A", .7), ("src_B", .3))}, "principle": "min_share_honoured"},
    "C3_source_blackout": {"family": "constraints", "tolerance": .02, "args": {},
        "request_overrides": {"calendars": None},   # filled in build(): weekday-restricted calendar for B
        "sources": {"src_B": {"supplier": "supplier_b", "unit_price": 4.8, "order_calendar": "weekdays_b"}},
        "sourcing": {"incumbent_shares": _mix(("src_A", 1.))}, "principle": "no_purchase_in_blackout"},
    "C4_unqualified_source": {"family": "constraints", "tolerance": .02, "args": {},
        "sources": {"src_B": {"supplier": "supplier_b", "unit_price": 4.5, "approved": False},
                    "src_C": {"supplier": "supplier_c", "unit_price": 4.5, "compliance": "unreviewed"}},
        "sourcing": {"incumbent_shares": _mix(("src_A", 1.))}, "principle": "unqualified_unused"},
    "C5_shared_capacity_multi_sku": {"family": "constraints", "tolerance": .02, "args": {"demand": 150., "supplier_capacity": 450.},
        "sources": {"src_S2": {"supplier": "supplier_s2", "unit_price": 5.4}}, "extra_skus": {"B": {}},
        "sourcing": {"incumbent_shares": _mix(("src_A", 1.)) + _mix(("src_A_B", 1.), sku="B")}, "principle": "shared_resource_respected"},
    "C6_shared_mov_multi_sku": {"family": "constraints", "tolerance": .02, "args": {},
        "sources": {"src_S2": {"supplier": "supplier_s2", "unit_price": 5.4}}, "extra_skus": {"B": {}},
        "supplier_terms": {"supplier": {"minimum_order_value": 5000., "fixed_order_cost": 150.}},
        "sourcing": {"incumbent_shares": _mix(("src_A", 1.)) + _mix(("src_A_B", 1.), sku="B")}, "principle": "shared_mov_respected"},
    # ── SECTOR ────────────────────────────────────────────────────────────────
    "S1_produce_short_life": {"family": "sector", "tolerance": .03, "args": {},
        "sources": {"src_B": {"supplier": "supplier_b", "unit_price": 4.5}},
        "physics": {"mode": "PRODUCE", "shelf_life": {"A": 8}, "skus": {"A": {"minimum_remaining_life_at_receipt": 2, "minimum_remaining_life_at_sale": 2,
                                                                          "age_at_receipt_by_source": {"src_B": 5}}}},
        "sourcing": {"incumbent_shares": _mix(("src_A", 1.))}, "principle": "b_unused"},
    "S2_produce_yield_uncertainty": {"family": "sector", "tolerance": .03, "args": {"supplier_fill_sd": .02},
        "sources": {"src_B": {"supplier": "supplier_b", "unit_price": 4.5, "fill_mean": .7, "fill_sd": .15}},
        "physics": {"mode": "PRODUCE", "shelf_life": {"A": 8}, "skus": {"A": {"minimum_remaining_life_at_sale": 2}}},
        "sourcing": {"incumbent_shares": _mix(("src_A", 1.))}, "principle": "not_worse"},
    "S3_frozen_invalid_route": {"family": "sector", "tolerance": .03, "args": {},
        "extra_locations": [{"id": "cross_dock", "kind": "warehouse", "storage_states": ["CHILLED"]}],
        "sources": {"src_B": {"supplier": "supplier_b", "unit_price": 4.5, "destination": "cross_dock"}},
        "physics": {"mode": "MEAT_SEAFOOD", "shelf_life": {"A": 26}, "skus": {"A": {"storage_state": "FROZEN"}},
                    "location_states": {"central": ["FROZEN", "CHILLED"], "north": ["FROZEN", "CHILLED"], "south": ["FROZEN", "CHILLED"], "cross_dock": ["CHILLED"]}},
        "sourcing": {"incumbent_shares": _mix(("src_A", 1.))}, "principle": "b_unused"},
    "S4_commercial_pallets": {"family": "sector", "tolerance": .03, "args": {},
        "source_overrides": {"src_A": {"case_multiple": 12., "pallet_multiple": 120.}},
        "sources": {"src_B": {"supplier": "supplier_b", "unit_price": 4.95, "case_multiple": 10., "pallet_multiple": 100.}},
        "supplier_terms": {"supplier_b": {"units_per_pallet": {"A": 100.}, "freight_per_pallet": 30.}},
        "physics": {"mode": "COMMERCIAL"}, "sourcing": {"incumbent_shares": _mix(("src_A", 1.))}, "principle": "whole_packs"},
    # ── NETWORK ───────────────────────────────────────────────────────────────
    "N1_source_to_central_with_transfers": {"family": "network", "tolerance": .02, "args": {"lane_lead_periods": 2},
        "sources": {"src_B": {"supplier": "supplier_b", "unit_price": 5.15}},
        "sourcing": {"incumbent_shares": _mix(("src_A", 1.))}, "principle": "conservation"},
    "N2_local_and_central_conserved": {"family": "network", "tolerance": .02, "args": {"supplier_capacity": 400.},
        "sources": {"src_B_north": {"supplier": "supplier_b", "unit_price": 5.4, "destination": "north"}},
        "sourcing": {"incumbent_shares": _mix(("src_A", 1.))}, "principle": "conservation"},
    "N3_mixed_sector_shared_capacity": {"family": "network", "tolerance": .02, "args": {"demand": 150., "supplier_capacity": 450.},
        "sources": {"src_S2": {"supplier": "supplier_s2", "unit_price": 5.4}}, "extra_skus": {"B": {"shelf_life": 8}},
        "physics": {"mode": "COMMERCIAL", "skus": {"B": {"sector": "PRODUCE", "minimum_remaining_life_at_sale": 2}}},
        "sourcing": {"incumbent_shares": _mix(("src_A", 1.)) + _mix(("src_A_B", 1.), sku="B")}, "principle": "shared_resource_respected"},
    # ── ABSTENTION / EDGE ─────────────────────────────────────────────────────
    "A1_incumbent_mix_optimal": {"family": "abstention", "tolerance": .02, "args": {"supplier_capacity": 120.},
        "sources": {"src_B": {"supplier": "supplier_b", "unit_price": 5.1}},
        "sourcing": {"incumbent_shares": _mix(("src_A", .6), ("src_B", .4))}, "principle": "abstains"},
    "A2_weak_evidence_flagged": {"family": "abstention", "tolerance": .03, "args": {},
        "sources": {"src_B": {"supplier": "supplier_b", "unit_price": 5.0}},
        "request_overrides": {"economics_provenance": None},   # filled in build(): B fill NOT_AVAILABLE
        "sourcing": {"risk_groups": [{"id": "maybe_same_plant", "kind": "PLANT", "members": ["src_A", "src_B"], "correlation": .5, "provenance": "FALLBACK"}],
                     "incumbent_shares": _mix(("src_A", 1.))}, "principle": "weak_evidence_flagged"},
    "A3_pruning_identity": {"family": "abstention", "tolerance": .02, "args": {},
        "sources": {"src_B": {"supplier": "supplier_b", "unit_price": 5.2},
                    "src_C": {"supplier": "supplier_c", "unit_price": 4.5, "compliance": "blocked", "minimum": 100., "case_multiple": 12.},
                    "src_D": {"supplier": "supplier_d", "unit_price": 4.5, "quote_expires": "2020-01-01T00:00:00+00:00", "minimum": 100., "exclusive_quote_group": "d"}},
        "sourcing": {"incumbent_shares": _mix(("src_A", 1.))}, "principle": "prune_identity"},
    "A5_single_source_legacy_identity": {"family": "abstention", "tolerance": .02, "args": {},
        "sourcing": {}, "principle": "legacy_identity"},
    "A6_no_order_no_allocation": {"family": "abstention", "tolerance": .02, "args": {"opening_central": 4000., "opening_branch": 800.},
        "sources": {"src_B": {"supplier": "supplier_b", "unit_price": 5.2}},
        "sourcing": {"incumbent_shares": _mix(("src_A", 1.))}, "principle": "no_order_no_allocation"},
}


def build(name: str, seed: int, **overrides: Any) -> Request:
    spec = FIXTURES[name]
    if name.startswith("C3_"):
        req = p2_request(seed=seed, **{**spec["args"], **overrides})
        payload = req.model_dump(mode="json")
        # the P2 calendar plus a weekday-restricted order calendar with a blackout for supplier B
        known = {"known_at": payload["skus"][0]["known_at"]}
        payload["calendars"].append({**known, "id": "weekdays_b", "weekdays": [0, 1, 2], "blackout_dates": []})
        spec = {**spec, "request_overrides": {"calendars": payload["calendars"]}}
        H = payload["horizon"]
        spec = {**spec, "sources": {"src_B": {**spec["sources"]["src_B"], "capacity_by_period": [1e6] + [0.] * 3 + [1e6] * (H - 4)}}}
    if name.startswith("A2_"):
        req = p2_request(seed=seed, **{**spec["args"], **overrides})
        prov = {**req.economics_provenance, "source.src_B.fill": "NOT_AVAILABLE", "source.src_B.lead": "NOT_AVAILABLE", "source.src_A.fill": "CUSTOMER_PROVIDED"}
        spec = {**spec, "request_overrides": {"economics_provenance": prov}}
    return sourcing_request(spec, seed, **overrides)


def variant(name: str, seed: int, policy: str, **overrides: Any) -> Request:
    """Policy-specific request: `single:<source>` keeps one approved source of every pair that source
    belongs to; `gated_noprune` switches pruning off; `gated_legacy` strips the sourcing block;
    `cheapest_landed` strips the incumbent shares (the rule then buys from the cheapest landed source)."""
    req = build(name, seed, **overrides)
    payload = req.model_dump(mode="json")
    if policy.startswith("single:"):
        # one supplier only: every pair that this supplier serves loses its other suppliers' sources
        keep = policy.split(":", 1)[1]
        served = {(s["sku"], s["destination"]) for s in payload["sources"] if s["supplier"] == keep}
        for s in payload["sources"]:
            if (s["sku"], s["destination"]) in served and s["supplier"] != keep:
                s["approved"] = False
        if payload.get("sourcing"):
            # the declared mix and switching costs stay: a single-supplier policy that leaves the operator's
            # mix pays the declared switching cost once, like any other policy; share limits cannot bind
            # a source that is no longer approved, so they are dropped
            payload["sourcing"] = {**payload["sourcing"], "share_constraints": []}
    elif policy == "gated_noprune" and payload.get("sourcing") is not None:
        payload["sourcing"] = {**payload["sourcing"], "prune_zero_capability": False}
    elif policy == "gated_legacy":
        payload["sourcing"] = None
    elif policy == "cheapest_landed" and payload.get("sourcing"):
        # the unconstrained rule: no declared mix, no share limits (it buys everything from the cheapest landed source)
        payload["sourcing"] = {**payload["sourcing"], "incumbent_shares": [], "share_constraints": []}
    return Request.model_validate(payload)
