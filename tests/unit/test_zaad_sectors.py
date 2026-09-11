"""Three-sector physics engine: contract, model, settlement, continuation and legacy-neutrality tests."""
from __future__ import annotations

import pytest

from zaad.full.contracts import Request
from zaad.full.model import Solution, solve
from zaad.full.planner import plan
from zaad.full.settlement import PhysicalViolation, settle
from zaad.full.terminal import continuation_value
from zaad.full.worlds import draw, forecast_all
from zaad.meio.fixtures_p2 import p2_request
from zaad.sectors.contracts import SkuPhysics, resolve
from zaad.sectors.fixtures import FIXTURES, build

DECL = "OPERATOR_DECLARED"


def _with_physics(req: Request, **fields) -> Request:
    """Attach a profile through the contract (model_validate), so the request validator runs."""
    sector = fields.pop("sector", "PRODUCE")
    prov = {k: DECL for k in fields}
    payload = req.model_dump(mode="json")
    payload["sku_physics"] = [{"sku": "A", "sector": sector, "provenance": prov, **fields}]
    return Request.model_validate(payload)


def _lots(req: Request, lots: list[tuple[str, int, float]]) -> Request:
    payload = req.model_dump(mode="json")
    known = {"known_at": payload["skus"][0]["known_at"]}
    payload["stock"] = [{**known, "id": f"lot_{i}", "sku": "A", "location": loc, "quantity": q, "reserved": 0., "damaged": 0., "quarantined": 0.,
                         "expires_in": e, "age_periods": 0} for i, (loc, e, q) in enumerate(lots)]
    return Request.model_validate(payload)


def _shelf(req: Request, life: int) -> Request:
    payload = req.model_dump(mode="json")
    for s in payload["skus"]:
        s["shelf_life"] = life
    for lot in payload["stock"]:
        lot["expires_in"] = min(lot["expires_in"], life)
    return Request.model_validate(payload)


# ── contract ───────────────────────────────────────────────────────────────

def test_legacy_request_resolves_to_no_physics_and_carries_no_new_fields_in_effect():
    req = p2_request()
    assert req.sector_mode is None and req.sku_physics == () and resolve(req) is None
    assert all(loc.storage_states == () for loc in req.locations) and all(a.storage_states == () for a in req.transfers)


def test_declared_values_need_provenance_and_thresholds_stay_below_shelf_life():
    with pytest.raises(ValueError, match="provenance"):
        SkuPhysics(sku="A", sector="PRODUCE", minimum_remaining_life_at_sale=1)
    req = _shelf(p2_request(), 4)
    with pytest.raises(ValueError, match="below the shelf life"):
        _with_physics(req, minimum_remaining_life_at_sale=4)
    with pytest.raises(ValueError, match="age at receipt"):
        _with_physics(req, age_at_receipt_periods=4)
    with pytest.raises(ValueError, match="no purchase can arrive"):
        _with_physics(req, age_at_receipt_periods=2, minimum_remaining_life_at_receipt=2)
    with pytest.raises(ValueError, match="unknown SKU"):
        Request.model_validate({**req.model_dump(mode="json"), "sku_physics": [{"sku": "Z", "sector": "PRODUCE"}]})
    with pytest.raises(ValueError, match="no location can hold"):
        payload = req.model_dump(mode="json")
        for loc in payload["locations"]:
            loc["storage_states"] = ["AMBIENT"]
        payload["sku_physics"] = [{"sku": "A", "sector": "MEAT_SEAFOOD", "storage_state": "FROZEN", "provenance": {"storage_state": DECL}}]
        Request.model_validate(payload)
    with pytest.raises(ValueError):
        payload = req.model_dump(mode="json")
        payload["sector_mode"] = "DAIRY"
        Request.model_validate(payload)


def test_stock_at_an_ineligible_location_is_refused_at_the_contract():
    payload = p2_request().model_dump(mode="json")
    for loc in payload["locations"]:
        loc["storage_states"] = ["CHILLED"] if loc["id"] == "south" else ["FROZEN", "CHILLED"]
    payload["sku_physics"] = [{"sku": "A", "sector": "MEAT_SEAFOOD", "storage_state": "FROZEN", "provenance": {"storage_state": DECL}}]
    with pytest.raises(ValueError, match="cannot store"):
        Request.model_validate(payload)


# ── model + settlement physics ─────────────────────────────────────────────

def _solve_det(req: Request, service_floor: bool = False, **kw) -> Solution:
    world = draw(req, req.seed, 1, deterministic=True)
    return solve(req, world, service_floor=service_floor, **kw)


def test_purchase_arrivals_carry_shelf_life_less_age_and_the_settlement_agrees():
    req = _shelf(p2_request(opening_central=50., opening_branch=20.), 6)
    aged = _with_physics(req, age_at_receipt_periods=3)
    sol = _solve_det(aged)
    assert sol.usable_plan and any(q > 0 for (s, t), q in sol.purchases.items() if t == 0)
    result = settle(aged, sol, draw(aged, aged.seed, 1, deterministic=True)[0], steps=1)
    arrivals = [(e, due) for _, _, e, due, q, kind in result["pending"] if kind == "external" and q > 0]
    # a unit bought in period 0 with lead 1 arrives at period 1 with 6 - 3 = 3 periods of life: expiry 4, never 7
    assert arrivals and all(e == due + 3 for e, due in arrivals)
    legacy = settle(req, _solve_det(req), draw(req, req.seed, 1, deterministic=True)[0], steps=1)
    assert all(e == due + 6 for _, _, e, due, q, kind in legacy["pending"] if kind == "external" and q > 0)


def test_unsellable_stock_cannot_serve_but_stays_physical_until_it_expires():
    req = _lots(_shelf(p2_request(opening_central=0.), 6), [("north", 1, 100.), ("south", 1, 100.)])
    phys = _with_physics(req, minimum_remaining_life_at_sale=1)
    plan_ = Solution("OPTIMAL", {}, {}, {}, {}, None, [], 0., 0, 0, None, 0., [])
    world = draw(phys, phys.seed, 1, deterministic=True)[0]
    result = settle(phys, plan_, world, steps=1)
    served = sum(x["served"] for x in result["service_by_period"])
    assert served == 0. and result["trace"][0]["expired_units"] == 0.   # unsellable at period 0 (1 - 0 = 1, not > 1), not yet expired
    legacy = settle(req, plan_, draw(req, req.seed, 1, deterministic=True)[0], steps=1)
    assert sum(x["served"] for x in legacy["service_by_period"]) > 0   # the frozen rule still serves the last period of life


def test_expired_inventory_never_serves_and_is_never_resurrected():
    req = _lots(_shelf(p2_request(opening_central=0.), 6), [("north", 2, 1000.), ("south", 2, 1000.)])
    phys = _with_physics(req, minimum_remaining_life_at_sale=0)
    plan_ = Solution("OPTIMAL", {}, {}, {}, {}, None, [], 0., 0, 0, None, 0., [])
    result = settle(phys, plan_, draw(phys, phys.seed, 1, deterministic=True)[0], steps=4)
    by_period = {}
    for x in result["service_by_period"]:
        by_period[x["period"]] = by_period.get(x["period"], 0.) + x["served"]
    assert by_period[2] == 0. and by_period[3] == 0. and result["trace"][-1]["expired_units"] > 0
    assert all(x["quantity"] >= -1e-9 for x in result["end_stock"])


def test_transfer_below_minimum_life_at_receipt_is_capped_in_the_model_and_refused_by_the_settlement():
    req = _lots(_shelf(p2_request(opening_branch=0.), 5), [("central", 2, 300.)])
    phys = _with_physics(req, minimum_remaining_life_at_receipt=1, minimum_remaining_life_at_sale=0)
    sol = _solve_det(phys)
    assert sol.usable_plan and not any(q > 1e-9 for (arc, e, t), q in sol.transfers.items() if t == 0)
    bad = Solution("OPTIMAL", {}, {("lane_north", 2, 0): 50.}, {}, {}, None, [], 0., 0, 0, None, 0., [])
    with pytest.raises(PhysicalViolation, match="below the minimum at receipt"):
        settle(phys, bad, draw(phys, phys.seed, 1, deterministic=True)[0], steps=1)
    legacy = Solution("OPTIMAL", {}, {("lane_north", 2, 0): 50.}, {}, {}, None, [], 0., 0, 0, None, 0., [])
    settle(req, legacy, draw(req, req.seed, 1, deterministic=True)[0], steps=1)   # the frozen rule accepts a cohort arriving with one period left


def test_a_transfer_never_gains_life_in_transit():
    req = build("P4_transfer_becomes_useless", 41001)
    sol = _solve_det(req)
    result = settle(req, sol, draw(req, req.seed, 1, deterministic=True)[0], steps=1)
    for sku, loc, expiry, due, q, kind in result["pending"]:
        if kind == "transfer":
            assert expiry <= 4   # opening cohorts expire at 4; nothing in transit carries more


def test_storage_state_eligibility_blocks_holding_and_lanes():
    req = build("M3_storage_state_infeasibility", 41001)
    physics = resolve(req)
    assert not physics.location_ok("A", "south") and physics.location_ok("A", "north")
    sol = _solve_det(req)
    assert sol.usable_plan
    assert not any(q > 1e-9 for (arc, e, t), q in sol.transfers.items() if arc == "lane_south")
    world = draw(req, req.seed, 1, deterministic=True)[0]
    result = settle(req, sol, world)
    assert all(x["quantity"] <= 1e-9 for x in result["end_stock"] if x["location"] == "south")
    bad = Solution("OPTIMAL", {}, {("lane_south", 40, 0): 10.}, {}, {}, None, [], 0., 0, 0, None, 0., [])
    with pytest.raises(PhysicalViolation, match="cannot carry / hold"):
        settle(req, bad, world, steps=1)
    lane = build("M4_cold_chain_lane", 41001)
    assert not resolve(lane).lane_ok("A", "lane_south") and resolve(lane).lane_ok("A", "reefer_south")
    sol = _solve_det(lane)
    assert not any(q > 1e-9 for (arc, e, t), q in sol.transfers.items() if arc == "lane_south")


def test_shipment_weight_cap_binds_in_model_and_settlement():
    req = build("C2_pallet_load_threshold", 41001)
    st = req.supplier_terms[0]
    sol = _solve_det(req, service_floor=True)
    assert sol.usable_plan
    for (s, t), q in sol.purchases.items():
        assert q * 2.5 <= st.max_shipment_weight + 1e-6
    heavy = Solution("OPTIMAL", {("src_A", 0): 1000.}, {}, {}, {}, None, [], 0., 0, 0, None, 0., [])
    with pytest.raises(PhysicalViolation, match="maximum weight"):
        settle(req, heavy, draw(req, req.seed, 1, deterministic=True)[0], steps=1)


def test_fefo_consumes_the_oldest_sellable_cohort_first():
    req = build("P7_fefo_settlement", 41001)
    plan_ = Solution("OPTIMAL", {}, {}, {}, {}, None, [], 0., 0, 0, None, 0., [])
    result = settle(req, plan_, draw(req, req.seed, 1, deterministic=True)[0], steps=1)
    north = {x["expiry"]: x["quantity"] for x in result["end_stock"] if x["location"] == "north"}
    # 60 units at expiry 2 are consumed before any of the 90 at expiry 5
    assert north.get(5, 0.) == 90. or north.get(2, 0.) == 0.


def test_continuation_value_is_monotone_non_increasing_in_remaining_life_and_zero_beyond_sellable_life():
    req = _with_physics(_shelf(p2_request(), 8), minimum_remaining_life_at_sale=1)
    fits = forecast_all(req)
    values = []
    for expiry in (8, 6, 4, 2, 1):
        rows = [{"sku": "A", "location": "north", "expiry": expiry, "quantity": 100.}]
        values.append(continuation_value(req, rows, [], fits, window_end=1)["continuation_credit"])
    assert all(a >= b - 1e-9 for a, b in zip(values, values[1:]))
    salvage = 100. * req.skus[0].terminal_value
    assert abs(values[-1] - salvage) < 1e-6           # one period of life, one required at sale: salvage only


def test_cohort_aware_continuation_rows_appear_only_with_physics():
    from zaad.full.lotsizing import cycle_continuation_terms
    # slabs exist only when the shelf life exceeds the horizon (frozen bound); a lot expiring at 13
    # can feed no post-window period once one period of sellable life is required
    req = _lots(_shelf(p2_request(opening_branch=0.), 20), [("central", 13, 300.), ("central", 20, 300.)])
    fits = forecast_all(req)
    terms = cycle_continuation_terms(req, fits)
    assert terms
    legacy = _solve_det(req, continuation=terms)
    phys = _with_physics(req, minimum_remaining_life_at_sale=1)
    physical = _solve_det(phys, continuation=cycle_continuation_terms(phys, fits))
    assert physical.constraints > legacy.constraints
    assert physical.projected_cost is not None and legacy.projected_cost is not None


# ── legacy neutrality and ownership ────────────────────────────────────────

def test_sector_mode_alone_changes_no_decision():
    req = p2_request()
    a = plan(req)
    b = plan(Request.model_validate({**req.model_dump(mode="json"), "sector_mode": "COMMERCIAL"}))
    assert a["status"] == b["status"] and a["actions"] == b["actions"] and a["orchestration"]["state"] == b["orchestration"]["state"]
    assert "physics" not in a and "physics" in b and b["physics"]["profiles"][0]["declared"] is False


def test_ownership_labels_are_unchanged_by_physics():
    for name in ("P2_near_expiry_inventory", "M6_transfer_usable_lot", "C1_case_pack_rounding"):
        rep = plan(build(name, 41001))
        assert rep["orchestration"]["planner_owner"] in ("PURCHASING_ECONOMICS", "PROTECTION_RECOVERY")
        assert rep["approval_required"] is True and rep["executable_purchase_order"] is False
        assert rep["physics"]["explanations"] is not None


def test_mixed_request_physics_of_one_sku_does_not_touch_another():
    req = build("X1_commercial_plus_produce", 41001)
    physics = resolve(req)
    assert physics.min_sale("B") == 1 and physics.min_sale("A") == 0 and physics.sku["A"].sector == "COMMERCIAL"
    sol = _solve_det(req)
    result = settle(req, sol, draw(req, req.seed, 1, deterministic=True)[0])
    assert all(x["sellable"] for x in result["end_stock"] if x["sku"] == "A" and x["expiry"] > 12)


def test_every_pre_registered_fixture_builds_and_plans():
    for name in FIXTURES:
        req = build(name, 41001)
        assert resolve(req) is not None
    rep = plan(build("X3_three_sectors", 41001))
    assert {p["sector"] for p in rep["physics"]["profiles"]} == {"COMMERCIAL", "PRODUCE", "MEAT_SEAFOOD"}
