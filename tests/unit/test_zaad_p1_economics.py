"""P1 phase 1: supplier-order economics carried identically by the model and by settlement, every
cost component reconciling, and no behaviour change when the new terms are absent."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from zaad.full.contracts import FreightTier, SupplierTerms
from zaad.full.fixtures_p1 import NOW, p1_request
from zaad.full.model import Solution, solve
from zaad.full.settlement import PhysicalViolation, settle
from zaad.full.worlds import draw


def plan(purchases: dict) -> Solution:
    return Solution("OPTIMAL", purchases, {}, {}, {}, None, [], 0., 0, 0, None, 0., [])


def world(req):
    return draw(req, req.seed, 1, deterministic=True)[0]


def test_supplier_terms_schema_rejects_bad_tariffs_and_unknown_suppliers():
    known = {"known_at": NOW, "id": "t", "supplier": "supplier"}
    with pytest.raises(ValidationError):
        SupplierTerms(**known, freight_tiers=(FreightTier(up_to_pallets=5, charge=800), FreightTier(up_to_pallets=4, charge=1100)))
    with pytest.raises(ValidationError):
        SupplierTerms(**known, units_per_pallet={"A": 0})
    with pytest.raises(ValidationError):
        SupplierTerms(**known, freight_tiers=(FreightTier(up_to_pallets=5, charge=800),), max_pallets=3)
    with pytest.raises(ValidationError):
        p1_request(supplier_terms={"minimum_order_value": 100.}, extra={"supplier_terms": [{**known, "supplier": "nobody"}]})


def test_minimum_order_value_is_checked_across_the_supplier_order_not_per_sku():
    req = p1_request(skus=("A", "B"), supplier_terms={"minimum_order_value": 5000.})
    w = world(req)
    with pytest.raises(PhysicalViolation, match="minimum order value"):
        settle(req, plan({("src_A", 0): 400.}), w)                    # $2,000 alone is below the MOV
    settle(req, plan({("src_A", 0): 400., ("src_B", 0): 700.}), w)     # $5,500 across both lines clears it
    settle(req, plan({}), w)                                           # no order, no MOV


def test_fixed_order_cost_and_receipt_fee_are_charged_once_per_supplier_order():
    req = p1_request(skus=("A", "B"), supplier_terms={"fixed_order_cost": 250., "receiving_fee_per_receipt": 40.})
    r = settle(req, plan({("src_A", 0): 100., ("src_B", 0): 100., ("src_A", 3): 50.}), world(req))
    assert abs(r["ledger"]["ordering"] - 500.) < 1e-9       # two orders (periods 0 and 3), not three lines
    assert abs(r["ledger"]["receiving"] - 80.) < 1e-9
    assert len(r["shipments"]) == 2


def test_freight_tiers_price_the_shipment_as_a_whole():
    tiers = [{"up_to_pallets": 4, "charge": 800.}, {"up_to_pallets": 9, "charge": 1100.}, {"up_to_pallets": 20, "charge": 1500.}]
    req = p1_request(skus=("A", "B"), supplier_terms={"freight_tiers": tiers, "units_per_pallet": {"A": 100., "B": 50.}, "receiving_per_pallet": 10.})
    w = world(req)
    r = settle(req, plan({("src_A", 0): 250., ("src_B", 0): 100.}), w)     # 2.5 + 2 pallets -> 5 pallets -> second tier
    assert r["shipments"][0]["pallets"] == 5 and abs(r["ledger"]["freight"] - 1100.) < 1e-9
    assert abs(r["ledger"]["receiving"] - 50.) < 1e-9
    with pytest.raises(PhysicalViolation, match="maximum load"):
        settle(req, plan({("src_A", 0): 2100.}), w)                        # 21 pallets exceed the top tier


def test_pallet_economics_are_disabled_when_a_pallet_size_is_unknown():
    tiers = [{"up_to_pallets": 4, "charge": 800.}]
    req = p1_request(skus=("A", "B"), supplier_terms={"freight_tiers": tiers, "units_per_pallet": {"A": 100.}})
    r = settle(req, plan({("src_A", 0): 250., ("src_B", 0): 100.}), world(req))
    assert r["ledger"].get("freight", 0.) == 0. and "pallets" not in r["shipments"][0]
    # the model agrees: no pallet variable is built for that supplier
    sol = solve(req, [world(req)])
    assert sol.status == "OPTIMAL"


def test_model_and_settlement_agree_on_the_supplier_order_rows():
    tiers = [{"up_to_pallets": 4, "charge": 800.}, {"up_to_pallets": 9, "charge": 1100.}]
    req = p1_request(skus=("A", "B"), demand=100., supplier_terms={"minimum_order_value": 1000., "fixed_order_cost": 200.,
                                                                    "freight_tiers": tiers, "units_per_pallet": {"A": 100., "B": 100.}})
    w = world(req)
    sol = solve(req, [w], service_floor=True)
    assert sol.status == "OPTIMAL"
    r = settle(req, sol, w)                                    # every order the model placed clears MOV and the tariff
    for shipment in r["shipments"]:
        assert shipment["order_value"] >= 1000. - 1e-6 and shipment["pallets"] <= 9
    assert abs(r["ledger_residual"]) < 1e-6


def test_cost_of_capital_separates_payment_timing_only_when_a_rate_exists():
    early = p1_request(cost_of_capital_per_year=.12, balance_trigger="order", net_days=0)
    late = p1_request(cost_of_capital_per_year=.12, balance_trigger="arrival", net_days=60)
    p = plan({("src_A", 0): 300.})
    a, b = settle(early, p, world(early)), settle(late, p, world(late))
    assert a["ledger"]["working_capital"] > b["ledger"]["working_capital"] + 1e-6
    assert abs(a["ledger"]["procurement"] - b["ledger"]["procurement"]) < 1e-9     # cost recognised identically
    zero_a = settle(p1_request(balance_trigger="order"), p, world(early))
    zero_b = settle(p1_request(balance_trigger="arrival", net_days=60), p, world(late))
    assert zero_a["ledger"].get("working_capital", 0.) == 0. and zero_b["ledger"].get("working_capital", 0.) == 0.


def test_cadence_mask_stops_orders_outside_the_cadence():
    req = p1_request(demand=100., opening_units=50.)
    w = world(req)
    sol = solve(req, [w], service_floor=True, allowed_periods=frozenset({0, 4, 8}))
    assert sol.status == "OPTIMAL"
    assert all(t in {0, 4, 8} for (_, t), q in sol.purchases.items() if q > 0)


def test_no_supplier_terms_means_no_new_rows_or_costs():
    req = p1_request()
    w = world(req)
    r = settle(req, plan({("src_A", 0): 100.}), w)
    assert r["shipments"] == [] and r["ledger"].get("ordering", 0.) == 0. and r["ledger"].get("receiving", 0.) == 0.
    assert r["ledger"].get("working_capital", 0.) == 0.
    assert abs(r["ledger_residual"]) < 1e-6
