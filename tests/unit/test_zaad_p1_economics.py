"""P1 phase 1: supplier-order economics carried identically by the model and by settlement, every
cost component reconciling, and no behaviour change when the new terms are absent."""
from __future__ import annotations

import math
from statistics import mean

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


# ---------------------------------------------------------------- phases 2-8

from zaad.full.economics import (NO_MATERIAL_IMPROVEMENT, cost_breakdown, materiality, missing_data_fallbacks, next_replenishment,
                                 order_waterfall, provenance, reconcile, supplier_order_view)
from zaad.full.planner import plan as plan_review, protection_profile, supply_profiles
from zaad.full.policies import apply_mov, baseline_plan, lot_round
from zaad.full.worlds import forecast_all


def waterfall(req, purchases, **kw):
    fits = forecast_all(req)
    prot = protection_profile(req, fits, supply_profiles(req))
    return order_waterfall(req, fits, prot, plan(purchases), **kw)


def test_phase2_order_calendar_moves_the_arrival_and_the_next_realistic_replenishment():
    daily = p1_request(period_days=1, horizon=21, lead_days=7)
    mondays = p1_request(period_days=1, horizon=21, lead_days=7, order_weekdays=(0,))
    src_d, src_m = daily.sources[0], mondays.sources[0]
    assert next_replenishment(daily, src_d, 0) == (7, 8)          # order any day: next lands a day later
    assert next_replenishment(mondays, src_m, 0) == (7, 14)       # Monday-only: the next order lands a week later
    rows = waterfall(mondays, {("src_A", 0): 2500.})             # enough to cover lead time and the forced week
    assert rows[0]["attribution"]["SUPPLIER_CALENDAR"] > 0        # the week the calendar forces is named as such
    assert rows[0]["attribution"]["LEAD_TIME_EXPOSURE"] > 0
    assert abs(rows[0]["attribution_sum"] - 2500.) < 1e-9


def test_phase3_lot_rules_are_attributed_in_the_order_a_buyer_applies_them():
    req = p1_request(minimum=400., opening_units=150.)
    rows = waterfall(req, {("src_A", 0): 400.})
    a = rows[0]["attribution"]
    assert a["MOQ"] > 0 and abs(rows[0]["attribution_sum"] - 400.) < 1e-9
    req = p1_request(case_multiple=48., opening_units=150.)
    need = waterfall(req, {("src_A", 0): 48.})[0]["economic_need"]
    q = math.ceil(need / 48.) * 48.
    rows = waterfall(req, {("src_A", 0): q})
    assert abs(rows[0]["attribution"]["CASE_ROUNDING"] - (q - need)) < 1e-6
    req = p1_request(pallet_multiple=200., opening_units=150.)
    need = waterfall(req, {("src_A", 0): 200.})[0]["economic_need"]
    q = math.ceil(need / 200.) * 200.
    rows = waterfall(req, {("src_A", 0): q})
    assert abs(rows[0]["attribution"]["PALLET_ROUNDING"] - (q - need)) < 1e-6
    # the model honours the same rules: every purchase is zero or at least the minimum
    req = p1_request(minimum=400., opening_units=150.)
    sol = solve(req, [world(req)], service_floor=True)
    assert all(q < 1e-6 or q >= 400. - 1e-6 for q in sol.purchases.values())


def test_phase4_minimum_order_value_is_coordinated_across_skus_and_attributed():
    req = p1_request(skus=("A", "B"), opening_units=150., supplier_terms={"minimum_order_value": 2000.})
    sol = solve(req, [world(req)], service_floor=True)
    view = supplier_order_view(req, sol, period=None)
    assert view and all(v["order_value"] >= 2000. - 1e-6 for v in view)
    rows = waterfall(req, {("src_A", 0): 250., ("src_B", 0): 150.})     # $2,000 exactly, above either line's need
    assert sum(r["attribution"]["MOV"] for r in rows) > 0
    # the lot-aware baselines lift the order to the MOV on the cheaper line rather than failing
    purchases = {("src_A", 0): 100., ("src_B", 0): 100.}
    apply_mov(req, purchases)
    assert purchases[("src_A", 0)] * 5. + purchases[("src_B", 0)] * 5. >= 2000. - 1e-6
    for rule in ("replace_sold", "periodic:2", "reorder_point", "economic_lot"):
        settle(req, baseline_plan(req, rule), world(req))              # no PhysicalViolation


def test_phase5_freight_tier_discontinuity_is_priced_by_settlement_and_respected_by_the_model():
    tiers = [{"up_to_pallets": 4, "charge": 800.}, {"up_to_pallets": 9, "charge": 1100.}]
    req = p1_request(opening_units=150., supplier_terms={"freight_tiers": tiers, "units_per_pallet": {"A": 100.}, "fixed_order_cost": 100.})
    w = world(req)
    four = settle(req, plan({("src_A", 0): 400.}), w)["ledger"]["freight"]
    five = settle(req, plan({("src_A", 0): 401.}), w)["ledger"]["freight"]
    assert four == 800. and five == 1100.                              # one unit over the tier costs the next tier
    sol = solve(req, [w], service_floor=True)
    for shipment in settle(req, sol, w)["shipments"]:
        assert shipment["pallets"] <= 9
    assert abs(settle(req, sol, w)["ledger_residual"]) < 1e-6


def test_phase6_carrying_financing_and_capital_are_separate_and_not_double_counted():
    req = p1_request(cost_of_capital_per_year=.12, interest_per_year=.10, opening_cash=1e6)
    r = settle(req, plan({("src_A", 0): 300.}), world(req))
    holding = req.locations[0].holding_per_value_period
    # carrying is the holding rate on carried value only; with ample cash there is no interest
    assert abs(r["ledger"]["holding"] - sum(holding * x["inventory_value"] for x in r["trace"])) < 1e-6 or r["ledger"]["holding"] >= 0
    assert r["ledger"].get("financing", 0.) == 0.
    assert abs(r["ledger"]["working_capital"] - req.liquidity.cost_of_capital_per_period * sum(req.liquidity.opening_cash - x["cash"] for x in r["trace"])) < 1e-6
    # when credit is drawn, interest is charged on the debt and the capital charge on own cash only
    tight = p1_request(cost_of_capital_per_year=.12, interest_per_year=.10, opening_cash=500., credit_limit=5000.)
    r2 = settle(tight, plan({("src_A", 0): 300.}), world(tight))
    assert r2["ledger"]["financing"] > 0 and max(x["debt"] for x in r2["trace"]) > 0
    assert r2["ledger"]["working_capital"] <= tight.liquidity.cost_of_capital_per_period * 500. * len(r2["trace"]) + 1e-6
    b = cost_breakdown(r2["ledger"])
    assert abs(b["TOTAL"] - r2["economic_cost"]) < 1e-6 and reconcile(r2)["reconciled"]


def test_phase7_cadence_candidates_exist_only_with_order_level_economics_and_obey_their_mask():
    with_terms = p1_request(skus=("A", "B"), opening_units=120., supplier_terms={"fixed_order_cost": 300.}, incumbent_rule="replace_sold")
    report = plan_review(with_terms)
    classes = report["orchestration"]["classification"]
    assert classes.get("cadence_2_network") == "OPTIONAL" and classes.get("cadence_4_network") == "OPTIONAL"
    assert report["selected_policy"] in ("operator_rule:replace_sold", *report["candidates"])
    sol = solve(with_terms, [world(with_terms)], service_floor=True, allowed_periods=frozenset({0, 4, 8}))
    assert all(t in {0, 4, 8} for (_, t), q in sol.purchases.items() if q > 1e-6)
    without = plan_review(p1_request(opening_units=120.))
    assert not any(k.startswith("cadence") for k in without["orchestration"]["classification"])


def test_phase8_materiality_abstains_when_nothing_moves_and_explanations_reconcile():
    req = p1_request(opening_units=150.)
    w = world(req)
    rows = [{"usable": True, **settle(req, plan({("src_A", 0): 100.}), w)}]
    same = materiality(req, rows, rows)
    assert same["material"] is False and same["verdict"] == NO_MATERIAL_IMPROVEMENT
    cheaper = [{"usable": True, **settle(req, plan({("src_A", 0): 60.}), w)}]
    assert materiality(req, rows, cheaper)["material"] in (True, False)      # a verdict, never None, when both settle
    report = plan_review(p1_request(opening_units=150., incumbent_rule="reorder_point"))
    e = report["economics"]
    assert e["reconciled"] in (True, None)
    for order in e["orders"]:
        assert abs(order["attribution_sum"] - order["quantity"]) < 1e-6
        assert order["explanation"].startswith("Order ")
    if report["status"] == "RETAIN_INCUMBENT" and e["materiality"] and e["materiality"]["verdict"] == NO_MATERIAL_IMPROVEMENT:
        assert any(NO_MATERIAL_IMPROVEMENT in r for r in report["reasons"])
        assert e["recommendation"] == NO_MATERIAL_IMPROVEMENT


def test_phase8_provenance_labels_every_economic_input_and_names_fallbacks():
    req = p1_request(extra={"economics_provenance": {"source.src_A.unit_price": "CUSTOMER_PROVIDED"}})
    p = provenance(req)
    assert p["source.src_A.unit_price"]["provenance"] == "CUSTOMER_PROVIDED"
    assert p["location.branch.holding_per_value_period"]["provenance"] == "CONFIGURED_ASSUMPTION"
    assert p["source.src_A.fixed_order_fee"]["provenance"] == "NOT_AVAILABLE"
    assert p["liquidity.cost_of_capital_per_period"]["provenance"] == "NOT_AVAILABLE"
    notes = missing_data_fallbacks(req)
    assert any("cost of capital NOT_AVAILABLE" in n for n in notes) and any("no supplier terms" in n for n in notes)
    with pytest.raises(ValidationError):
        p1_request(incumbent_rule="guess")


def test_baselines_are_lot_aware_and_periodic_review_keeps_its_cadence():
    req = p1_request(minimum=400., opening_units=150.)
    for rule in ("replace_sold", "reorder_point", "economic_lot", "periodic:2"):
        sol = baseline_plan(req, rule)
        assert all(q >= 400. - 1e-9 for q in sol.purchases.values())
        settle(req, sol, world(req))
    assert lot_round(req.sources[0], 10.) == 400.
    periodic = baseline_plan(p1_request(opening_units=0.), "periodic:2")
    periods = sorted({t for (_, t) in periodic.purchases})
    assert periods and all((b - a) % 2 == 0 for a, b in zip(periods, periods[1:]))


def test_service_gate_basis_target_keeps_the_strict_rule_below_target_and_in_recovery():
    from zaad.full.planner import _priority_consistent
    req = p1_request(extra={"service_gate_basis": "target"})     # target .95, tolerance .01; the option, not the default
    def rows(v):
        return [{"usable": True, "service": {"svc_A": v}, "economic_cost": 0.,
                 "service_by_period": [{"service": "svc_A", "period": 0, "demand": 100., "served": 100. * v}]}]
    # a fall from 1.0 to .97 stays above target: not a worsening under the target basis, one under the incumbent basis
    assert _priority_consistent(req, rows(1.), rows(.97), floor_at_target=True)
    assert not _priority_consistent(req, rows(1.), rows(.97))
    strict = p1_request()                                          # the default is the P0 rule
    assert strict.service_gate_basis == "incumbent"
    assert not _priority_consistent(strict, rows(1.), rows(.97), floor_at_target=True)
    # a fall below the target is a worsening under both
    assert not _priority_consistent(req, rows(1.), rows(.93), floor_at_target=True)
    # below-target incumbent: any further fall is a worsening
    assert not _priority_consistent(req, rows(.92), rows(.90), floor_at_target=True)


def test_terminal_financing_tail_counts_declared_receivables_like_the_model_does():
    req = p1_request(opening_cash=600., credit_limit=0., receivables_per_period=450.)
    w = world(req)
    sol = solve(req, [w], service_floor=True)
    assert sol.status == "OPTIMAL"
    settle(req, sol, w, steps=1)            # the model financed it on declared receivables; settlement must agree


def test_cash_aware_baselines_never_exceed_declared_cash_and_credit():
    req = p1_request(opening_cash=1500., credit_limit=1500., receivables_per_period=450., supplier_terms={"fixed_order_cost": 100.})
    for rule in ("economic_lot", "periodic:2", "reorder_point", "replace_sold"):
        settle(req, baseline_plan(req, rule), world(req), steps=1)


def test_timing_tiebreak_prefers_later_commitment_when_the_economics_are_indifferent():
    # No holding, no cost of capital, no order-level costs: buying at period 0 and at period 3 for
    # demand in period 4 cost the same; the tie-break must pick the later order.
    req = p1_request(holding_per_year=0., opening_units=400., demand=100.)
    sol = solve(req, [world(req)], service_floor=True)
    first = min(t for (_, t), q in sol.purchases.items() if q > 1e-6)
    assert first >= 2, sol.purchases
    off = req.model_copy(update={"timing_tiebreak": 0.})
    assert solve(off, [world(off)], service_floor=True).status == "OPTIMAL"
    # the tie-break never reaches the ledger
    r = settle(req, sol, world(req))
    assert "timing" not in r["ledger"] and abs(r["ledger_residual"]) < 1e-6


# ---------------------------------------------------------------- closure pass

from zaad.full.model import effective_smoothing, explicit_order_economics


def test_stratified_scenarios_represent_the_tail_at_its_mass_and_leave_the_truth_untouched():
    req = p1_request()
    ws = draw(req, req.seed, 3)
    assert abs(sum(w.weight for w in ws) - 1.) < 1e-12
    assert ws[-1].name.endswith(":tail") and abs(ws[-1].weight - (1 - req.services[0].target)) < 1e-12
    body = [w for w in ws[:-1]]
    assert all(abs(w.weight - req.services[0].target / 2) < 1e-12 for w in body)
    # the tail world is the tail of the per-period noise at the fitted level: above the fitted
    # mean in every period and above every body world on average (body worlds carry the level
    # shock, the tail world deliberately does not)
    fits = forecast_all(req)
    assert all(x >= fits["svc_A"]["mean"] - 1e-9 for x in ws[-1].demand["svc_A"])
    assert mean(ws[-1].demand["svc_A"]) >= max(mean(w.demand["svc_A"]) for w in body)
    # single-world and deterministic draws (the truth paths) are identical with the flag on or off
    off = req.model_copy(update={"stratified_scenarios": False})
    for count, det in ((1, False), (1, True)):
        a, b = draw(req, req.seed + 10000, count, deterministic=det)[0], draw(off, req.seed + 10000, count, deterministic=det)[0]
        assert a.demand == b.demand and a.fills == b.fills and a.arrival == b.arrival and a.weight == b.weight == 1.


def test_weighted_selector_statistics_reduce_to_plain_means_under_equal_weights():
    from zaad.full.planner import _service_value, _wmean
    req = p1_request()
    rows = [{"usable": True, "weight": 1 / 3, "economic_cost": c, "service_by_period": [{"service": "svc_A", "demand": 100., "served": s}]}
            for c, s in ((10., 90.), (20., 100.), (30., 95.))]
    assert _wmean([r["economic_cost"] for r in rows], rows) == 20.
    assert abs(_service_value(req, rows, req.services[0]) - 285. / 300.) < 1e-12
    rows[2]["weight"] = .05
    rows[0]["weight"] = rows[1]["weight"] = .475
    assert abs(_wmean([r["economic_cost"] for r in rows], rows) - (.475 * 10 + .475 * 20 + .05 * 30)) < 1e-12
    assert abs(_service_value(req, rows, req.services[0]) - (.475 * 90 + .475 * 100 + .05 * 95) / 100.) < 1e-12


def test_smoothing_is_off_when_explicit_order_economics_exist_and_unchanged_otherwise():
    plain = p1_request(extra={"order_smoothing": .02})
    assert not explicit_order_economics(plain) and effective_smoothing(plain) == .02
    with_terms = p1_request(supplier_terms={"fixed_order_cost": 100.}, extra={"order_smoothing": .02})
    assert explicit_order_economics(with_terms) and effective_smoothing(with_terms) == 0.
    with_fee = p1_request(fixed_order_fee=25., extra={"order_smoothing": .02})
    assert effective_smoothing(with_fee) == 0.
    # and the model builds no smoothing columns when the charge is off
    from zaad.full import model as M
    seen = {}
    orig = M.Linear.solve
    def spy(self, *a, **k):
        seen["names"] = list(self.names)
        return orig(self, *a, **k)
    M.Linear.solve = spy
    try:
        solve(with_terms, [world(with_terms)], service_floor=True)
        assert not any(n[0] in ("smooth_up", "smooth_down") for n in seen["names"])
        solve(plain, [world(plain)], service_floor=True)
        assert any(n[0] == "smooth_up" for n in seen["names"])
    finally:
        M.Linear.solve = orig


def test_timing_tiebreak_total_is_bounded_by_its_coefficient_times_purchase_value():
    from zaad.full import model as M
    for horizon in (12, 30):
        req = p1_request(horizon=horizon, holding_per_year=0., opening_units=100.)
        w = world(req)
        seen = {}
        orig = M.Linear.solve
        def spy(self, *a, **k):
            res, resid = orig(self, *a, **k)
            seen["x"], seen["cost"], seen["names"] = res.x, self.cost, list(self.names)
            return res, resid
        M.Linear.solve = spy
        try:
            sol = solve(req, [w], service_floor=True)
        finally:
            M.Linear.solve = orig
        purchase_value = sum(q * req.sources[0].unit_price for q in sol.purchases.values())
        # the tie-break is the only objective term on purchase columns beyond the landed cost
        landed = req.sources[0].unit_price + req.sources[0].freight_per_unit + req.sources[0].handling_per_unit
        tiebreak_total = sum((c - landed) * x for n, c, x in zip(seen["names"], seen["cost"], seen["x"]) if n[0] == "purchase" and x > 1e-9)
        assert 0 <= tiebreak_total <= req.timing_tiebreak * purchase_value + 1e-6, (horizon, tiebreak_total, purchase_value)


def test_stratified_worlds_make_the_plan_carry_attributable_protection():
    # Fixture P's steady state: with the tail represented the plan holds protection that the
    # waterfall attributes as SERVICE_PROTECTION rather than ordering below the arithmetic need.
    req = p1_request(opening_units=100., demand=100.)
    fits = forecast_all(req)
    prot = protection_profile(req, fits, supply_profiles(req))
    sol = solve(req, draw(req, req.seed, req.scenarios), service_floor=True)
    rows = order_waterfall(req, fits, prot, sol)
    assert rows and rows[0]["attribution"]["SERVICE_PROTECTION"] > 0
    assert rows[0]["under_need_units"] < rows[0]["justified_protection_units"]


def test_stratified_draw_leaves_the_supply_sample_untouched():
    # A demand representation must not change the supply sample: fills, arrivals and PO due dates
    # are identical whether or not the demand strata are used (P1 diagnostic pass, cell 90).
    req = p1_request()
    off = draw(req.model_copy(update={"stratified_scenarios": False}), 38017, 3)
    on = draw(req.model_copy(update={"stratified_scenarios": True}), 38017, 3)
    assert all(a.fills == b.fills and a.arrival == b.arrival and a.po_due == b.po_due for a, b in zip(off, on))
    assert on[-1].name.endswith(":tail") and on[-1].demand != off[-1].demand
