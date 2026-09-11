"""Pre-registered sector fixtures (docs/zaad_full/evidence/sectors/SECTOR_PHYSICS_FIXTURE_SPEC.md).

Every fixture is the P2 network frame (`zaad.meio.fixtures_p2.p2_request`: one supplier into a
central DC, two branches, one lane each, weekly periods, horizon 12) with sector physics attached
after the frozen request is built: SKU profiles, shelf lives, opening lots with their own expiry,
storage-state eligibility on locations and lanes, supplier load terms, and extra SKUs for the
mixed-sector families. Synthetic throughout (`evidence_label = SYNTHETIC`)."""
from __future__ import annotations

from typing import Any

from zaad.full.contracts import Request
from zaad.meio.fixtures_p2 import p2_request

DECLARED = "OPERATOR_DECLARED"


def _prov(fields: dict[str, Any]) -> dict[str, str]:
    return {k: DECLARED for k in fields}


def _profile(sku: str, sector: str, **fields: Any) -> dict[str, Any]:
    return {"sku": sku, "sector": sector, **fields, "provenance": _prov(fields)}


def _clone_sku(payload: dict, new: str, *, shelf_life: int, demand_scale: float = 1., price: float | None = None,
               lane_cost: float | None = None) -> None:
    """Add a second SKU with its own source, lanes, services, history and opening stock (mixed sectors)."""
    base_sku = next(s for s in payload["skus"] if s["id"] == "A")
    payload["skus"].append({**base_sku, "id": new, "shelf_life": shelf_life, **({"asset_value": price, "terminal_value": price * .8} if price else {})})
    for src in [s for s in payload["sources"] if s["sku"] == "A"]:
        payload["sources"].append({**src, "id": f"{src['id']}_{new}", "sku": new, **({"unit_price": price} if price else {})})
    for arc in [a for a in payload["transfers"] if a["sku"] == "A"]:
        payload["transfers"].append({**arc, "id": f"{arc['id']}_{new}", "sku": new, **({"cost_per_unit": lane_cost} if lane_cost is not None else {})})
    for svc in [s for s in payload["services"] if s["sku"] == "A"]:
        payload["services"].append({**svc, "id": f"{svc['id']}_{new}", "sku": new, **({"selling_price": price * 2} if price else {})})
        for row in [h for h in payload["history"] if h["service"] == svc["id"]]:
            payload["history"].append({**row, "service": f"{svc['id']}_{new}", "quantity": row["quantity"] * demand_scale})
    for lot in [x for x in payload["stock"] if x["sku"] == "A"]:
        payload["stock"].append({**lot, "id": f"{lot['id']}_{new}", "sku": new, "quantity": lot["quantity"] * demand_scale, "expires_in": shelf_life})


def sector_request(spec: dict[str, Any], seed: int, **overrides: Any) -> Request:
    """Build the frozen request, then attach the fixture's physics."""
    args = {**spec["args"], **overrides}
    req = p2_request(seed=seed, **args)
    payload = req.model_dump(mode="json")
    physics = spec.get("physics", {})
    # extra SKUs first, so per-SKU physics below can address them
    for new, kw in physics.get("extra_skus", {}).items():
        _clone_sku(payload, new, **kw)
    for sku, life in physics.get("shelf_life", {}).items():
        for s in payload["skus"]:
            if s["id"] == sku:
                s["shelf_life"] = life
        for lot in payload["stock"]:
            if lot["sku"] == sku and lot["expires_in"] > life:
                lot["expires_in"] = life
    if "lots" in physics:
        # explicit opening lots: (sku, location, expiry, quantity); replaces the builder's lots for those SKUs
        replaced = {lot[0] for lot in physics["lots"]}
        payload["stock"] = [x for x in payload["stock"] if x["sku"] not in replaced]
        known = {"known_at": payload["skus"][0]["known_at"]}
        for i, (sku, location, expiry, qty) in enumerate(physics["lots"]):
            payload["stock"].append({**known, "id": f"lot_{sku}_{location}_{i}", "sku": sku, "location": location, "quantity": float(qty), "reserved": 0., "damaged": 0.,
                                     "quarantined": 0., "expires_in": int(expiry), "age_periods": 0})
    for loc_id, states in physics.get("location_states", {}).items():
        for loc in payload["locations"]:
            if loc["id"] == loc_id:
                loc["storage_states"] = list(states)
    for lane_id, states in physics.get("lane_states", {}).items():
        for arc in payload["transfers"]:
            if arc["id"] == lane_id:
                arc["storage_states"] = list(states)
    for lane in physics.get("extra_lanes", []):
        base = next(a for a in payload["transfers"] if a["sku"] == lane.get("sku", "A"))
        payload["transfers"].append({**base, **lane})
    for src_id, fields in physics.get("source_overrides", {}).items():
        for src in payload["sources"]:
            if src["id"] == src_id:
                src.update(fields)
    for loc_id, fields in physics.get("location_overrides", {}).items():
        for loc in payload["locations"]:
            if loc["id"] == loc_id:
                loc.update(fields)
    if "supplier_terms" in physics:
        known = {"known_at": payload["skus"][0]["known_at"]}
        payload["supplier_terms"] = [{**known, "id": "supplier_terms", "supplier": "supplier", **physics["supplier_terms"],
                                      "provenance": {k: "CONFIGURED_ASSUMPTION" for k in physics["supplier_terms"] if k != "units_per_pallet"}}]
    if "mode" in physics:
        payload["sector_mode"] = physics["mode"]
    payload["sku_physics"] = [_profile(sku, kw.pop("sector", physics.get("mode", "COMMERCIAL")), **kw) for sku, kw in
                              {k: dict(v) for k, v in physics.get("skus", {}).items()}.items()]
    return Request.model_validate(payload)


ALL_CHILLED = {"central": ["CHILLED", "FROZEN", "AMBIENT"], "north": ["CHILLED", "FROZEN", "AMBIENT"], "south": ["CHILLED", "FROZEN", "AMBIENT"]}

FIXTURES: dict[str, dict[str, Any]] = {
    # ── COMMERCIAL ─────────────────────────────────────────────────────────────
    "C1_case_pack_rounding": {"sector": "COMMERCIAL", "tolerance": .02,
        "args": {}, "physics": {"mode": "COMMERCIAL", "source_overrides": {"src_A": {"case_multiple": 12.}}},
        "principle": "case_multiples"},
    "C2_pallet_load_threshold": {"sector": "COMMERCIAL", "tolerance": .02,
        "args": {}, "physics": {"mode": "COMMERCIAL", "skus": {"A": {"weight_per_unit": 2.5}},
                                "supplier_terms": {"units_per_pallet": {"A": 120.}, "freight_per_pallet": 40., "max_pallets": 8., "max_shipment_weight": 2200.}},
        "principle": "load_limits"},
    "C3_moq_mov_economics": {"sector": "COMMERCIAL", "tolerance": .02,
        "args": {"minimum": 240.}, "physics": {"mode": "COMMERCIAL", "supplier_terms": {"minimum_order_value": 1800., "fixed_order_cost": 60.}},
        "principle": "moq_mov"},
    "C4_long_import_lead": {"sector": "COMMERCIAL", "tolerance": .02,
        "args": {"supplier_lead_days": 35, "opening_central": 700., "opening_branch": 250.}, "physics": {"mode": "COMMERCIAL"},
        "principle": "not_worse"},
    "C5_variable_supplier_arrival": {"sector": "COMMERCIAL", "tolerance": .03,
        "args": {"supplier_fill": .95, "supplier_fill_sd": .03}, "physics": {"mode": "COMMERCIAL", "source_overrides": {"src_A": {"lead_sd_days": 7.}}},
        "principle": "not_worse"},
    "C6_storage_capacity": {"sector": "COMMERCIAL", "tolerance": .02,
        "args": {}, "physics": {"mode": "COMMERCIAL", "location_overrides": {"north": {"capacity_volume": 320.}, "south": {"capacity_volume": 320.}}},
        "principle": "capacity"},
    "C7_no_material_improvement": {"sector": "COMMERCIAL", "tolerance": .02,
        "args": {"demand_sd_hint": .1, "opening_branch": 200.}, "physics": {"mode": "COMMERCIAL"},
        "principle": "abstains", "abstain_at_least": 6},
    # ── PRODUCE ────────────────────────────────────────────────────────────────
    "P1_fresh_no_unnecessary_purchase": {"sector": "PRODUCE", "tolerance": .02,
        "args": {"opening_central": 400., "opening_branch": 250.},
        "physics": {"mode": "PRODUCE", "shelf_life": {"A": 6}, "skus": {"A": {"minimum_remaining_life_at_sale": 1}},
                    "lots": [("A", "central", 6, 400.), ("A", "north", 6, 250.), ("A", "south", 6, 250.)]},
        "principle": "no_purchase_first_two_reviews"},
    "P2_near_expiry_inventory": {"sector": "PRODUCE", "tolerance": .03,
        "args": {"opening_central": 300., "opening_branch": 150.},
        "physics": {"mode": "PRODUCE", "shelf_life": {"A": 6}, "skus": {"A": {"minimum_remaining_life_at_sale": 1}},
                    "lots": [("A", "central", 6, 300.), ("A", "north", 2, 150.), ("A", "south", 2, 150.)]},
        "principle": "acts_on_near_expiry"},
    "P3_age_at_receipt": {"sector": "PRODUCE", "tolerance": .03,
        "args": {"local_sources": {"north": {"price_premium": .2}, "south": {"price_premium": .2}}, "opening_central": 200., "opening_branch": 120.},
        "physics": {"mode": "PRODUCE", "shelf_life": {"A": 6}, "skus": {"A": {"minimum_remaining_life_at_sale": 1, "age_at_receipt_by_source": {"src_A": 3}}},
                    "lots": [("A", "central", 3, 200.), ("A", "north", 4, 120.), ("A", "south", 4, 120.)]},
        "principle": "uses_fresh_source"},
    "P4_transfer_becomes_useless": {"sector": "PRODUCE", "tolerance": .03,
        "args": {"lane_lead_periods": {"north": 1, "south": 3}, "opening_central": 300., "opening_branch": 150.,
                 "local_sources": {"south": {"price_premium": .15}}},
        "physics": {"mode": "PRODUCE", "shelf_life": {"A": 4}, "skus": {"A": {"minimum_remaining_life_at_sale": 1}},
                    "lots": [("A", "central", 4, 300.), ("A", "north", 4, 150.), ("A", "south", 4, 150.)]},
        "principle": "no_useless_transfer"},
    "P5_spoilage_vs_service": {"sector": "PRODUCE", "tolerance": .03,
        "args": {"demand_sd_hint": .3, "opening_central": 250., "opening_branch": 120.},
        "physics": {"mode": "PRODUCE", "shelf_life": {"A": 3}, "skus": {"A": {"minimum_remaining_life_at_sale": 0}},
                    "lots": [("A", "central", 3, 250.), ("A", "north", 3, 120.), ("A", "south", 3, 120.)]},
        "principle": "not_worse"},
    "P6_uncertain_usable_yield": {"sector": "PRODUCE", "tolerance": .03,
        "args": {"supplier_fill": .85, "supplier_fill_sd": .08, "opening_central": 300., "opening_branch": 150.},
        "physics": {"mode": "PRODUCE", "shelf_life": {"A": 5}, "skus": {"A": {"minimum_remaining_life_at_sale": 1}},
                    "lots": [("A", "central", 5, 300.), ("A", "north", 5, 150.), ("A", "south", 5, 150.)]},
        "principle": "service_under_yield"},
    "P7_fefo_settlement": {"sector": "PRODUCE", "tolerance": .03,
        "args": {"opening_central": 300.},
        "physics": {"mode": "PRODUCE", "shelf_life": {"A": 6}, "skus": {"A": {"minimum_remaining_life_at_sale": 1}},
                    "lots": [("A", "central", 6, 300.), ("A", "north", 2, 60.), ("A", "north", 5, 90.), ("A", "south", 2, 60.), ("A", "south", 5, 90.)]},
        "principle": "fefo"},
    "P8_no_material_improvement": {"sector": "PRODUCE", "tolerance": .02,
        "args": {"demand_sd_hint": .1, "opening_central": 350., "opening_branch": 220.},
        "physics": {"mode": "PRODUCE", "shelf_life": {"A": 6}, "skus": {"A": {"minimum_remaining_life_at_sale": 1}},
                    "lots": [("A", "central", 6, 350.), ("A", "north", 6, 220.), ("A", "south", 6, 220.)]},
        "principle": "abstains", "abstain_at_least": 5},
    # ── MEAT & SEAFOOD ─────────────────────────────────────────────────────────
    "M1_chilled_shelf_life": {"sector": "MEAT_SEAFOOD", "tolerance": .03,
        "args": {"opening_central": 250., "opening_branch": 120.},
        "physics": {"mode": "MEAT_SEAFOOD", "shelf_life": {"A": 3}, "skus": {"A": {"storage_state": "CHILLED", "minimum_remaining_life_at_sale": 1}},
                    "location_states": ALL_CHILLED, "lots": [("A", "central", 3, 250.), ("A", "north", 3, 120.), ("A", "south", 3, 120.)]},
        "principle": "not_worse"},
    "M2_frozen_shelf_life": {"sector": "MEAT_SEAFOOD", "tolerance": .02,
        "args": {},
        "physics": {"mode": "MEAT_SEAFOOD", "shelf_life": {"A": 40}, "skus": {"A": {"storage_state": "FROZEN"}}, "location_states": ALL_CHILLED},
        "principle": "not_worse"},
    "M3_storage_state_infeasibility": {"sector": "MEAT_SEAFOOD", "tolerance": .03, "service_mode": "floor",
        "args": {"opening_branch": {"north": 150., "south": 0.}},
        "physics": {"mode": "MEAT_SEAFOOD", "shelf_life": {"A": 40}, "skus": {"A": {"storage_state": "FROZEN"}},
                    "location_states": {"central": ["FROZEN", "CHILLED"], "north": ["FROZEN", "CHILLED"], "south": ["CHILLED"]}},
        "principle": "never_at_ineligible_location"},
    "M4_cold_chain_lane": {"sector": "MEAT_SEAFOOD", "tolerance": .03,
        "args": {},
        "physics": {"mode": "MEAT_SEAFOOD", "shelf_life": {"A": 6}, "skus": {"A": {"storage_state": "CHILLED", "minimum_remaining_life_at_sale": 1}},
                    "location_states": ALL_CHILLED, "lane_states": {"lane_north": ["CHILLED"], "lane_south": ["AMBIENT"]},
                    "extra_lanes": [{"id": "reefer_south", "origin": "central", "destination": "south", "cost_per_unit": .6, "storage_states": ["CHILLED"]}]},
        "principle": "eligible_lane_only"},
    "M5_aging_vs_service": {"sector": "MEAT_SEAFOOD", "tolerance": .03,
        "args": {"demand_sd_hint": .25, "target": .97, "opening_central": 250., "opening_branch": 120.},
        "physics": {"mode": "MEAT_SEAFOOD", "shelf_life": {"A": 3}, "skus": {"A": {"storage_state": "CHILLED", "minimum_remaining_life_at_sale": 0}},
                    "location_states": ALL_CHILLED, "lots": [("A", "central", 3, 250.), ("A", "north", 3, 120.), ("A", "south", 3, 120.)]},
        "principle": "not_worse"},
    "M6_transfer_usable_lot": {"sector": "MEAT_SEAFOOD", "tolerance": .03,
        "args": {"opening_central": 300., "opening_branch": {"north": 20., "south": 150.}},
        "physics": {"mode": "MEAT_SEAFOOD", "shelf_life": {"A": 5}, "skus": {"A": {"storage_state": "CHILLED", "minimum_remaining_life_at_sale": 1, "minimum_remaining_life_at_receipt": 1}},
                    "location_states": ALL_CHILLED, "lots": [("A", "central", 4, 300.), ("A", "north", 4, 20.), ("A", "south", 4, 150.)]},
        "principle": "moves_usable_lot"},
    "M7_transfer_rejected_by_expiry": {"sector": "MEAT_SEAFOOD", "tolerance": .03,
        "args": {"opening_central": 300., "opening_branch": {"north": 20., "south": 150.}},
        "physics": {"mode": "MEAT_SEAFOOD", "shelf_life": {"A": 5}, "skus": {"A": {"storage_state": "CHILLED", "minimum_remaining_life_at_sale": 1, "minimum_remaining_life_at_receipt": 1}},
                    "location_states": ALL_CHILLED, "lots": [("A", "central", 2, 300.), ("A", "north", 4, 20.), ("A", "south", 4, 150.)]},
        "principle": "expiring_lot_not_moved"},
    "M8_no_material_improvement": {"sector": "MEAT_SEAFOOD", "tolerance": .02,
        "args": {"demand_sd_hint": .1, "opening_branch": 200.},
        "physics": {"mode": "MEAT_SEAFOOD", "shelf_life": {"A": 40}, "skus": {"A": {"storage_state": "FROZEN"}}, "location_states": ALL_CHILLED},
        "principle": "abstains", "abstain_at_least": 6},
    # ── MIXED ──────────────────────────────────────────────────────────────────
    "X1_commercial_plus_produce": {"sector": "MIXED", "tolerance": .03,
        "args": {},
        "physics": {"extra_skus": {"B": {"shelf_life": 4, "price": 3.}},
                    "skus": {"A": {"sector": "COMMERCIAL"}, "B": {"sector": "PRODUCE", "minimum_remaining_life_at_sale": 1}},
                    "location_overrides": {"north": {"capacity_volume": 400.}, "south": {"capacity_volume": 400.}}},
        "principle": "isolation_and_capacity"},
    "X2_produce_plus_frozen_seafood": {"sector": "MIXED", "tolerance": .03,
        "args": {},
        "physics": {"extra_skus": {"B": {"shelf_life": 40, "price": 12.}},
                    "shelf_life": {"A": 4},
                    "skus": {"A": {"sector": "PRODUCE", "storage_state": "CHILLED", "minimum_remaining_life_at_sale": 1},
                             "B": {"sector": "MEAT_SEAFOOD", "storage_state": "FROZEN"}},
                    "location_states": ALL_CHILLED, "location_overrides": {"north": {"capacity_volume": 400.}, "south": {"capacity_volume": 400.}}},
        "principle": "shared_capacity_no_cross_expiry"},
    "X3_three_sectors": {"sector": "MIXED", "tolerance": .03,
        "args": {"opening_branch": {"north": 150., "south": 150.}},
        "physics": {"extra_skus": {"B": {"shelf_life": 4, "price": 3.}, "C": {"shelf_life": 40, "price": 12.}},
                    "skus": {"A": {"sector": "COMMERCIAL"}, "B": {"sector": "PRODUCE", "storage_state": "CHILLED", "minimum_remaining_life_at_sale": 1},
                             "C": {"sector": "MEAT_SEAFOOD", "storage_state": "FROZEN"}},
                    "location_states": {"central": ["AMBIENT", "CHILLED", "FROZEN"], "north": ["AMBIENT", "CHILLED", "FROZEN"], "south": ["AMBIENT", "CHILLED"]},
                    "lots": [("C", "central", 40, 300.), ("C", "north", 40, 150.)]},
        "principle": "no_cross_physics"},
}

SEEDS = (41001, 41002)
REVIEWS = 8


def build(name: str, seed: int, **overrides: Any) -> Request:
    return sector_request(FIXTURES[name], seed, **overrides)
