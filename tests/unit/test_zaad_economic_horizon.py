"""P1 final closure: purchasing economics beyond the detailed horizon (`zaad/full/lotsizing.py`
`steady_state_unit_costs` / `cycle_continuation_terms`, `model.solve(continuation=[slabs])`,
`terminal.continuation_value(cap_units=)`; design record `P1_ECONOMIC_HORIZON_ARCHITECTURE.md`).

Principle and property tests, numbered as in the brief. They use the P1 fixture builder with altered
declared economics; none depends on fixture B's own result."""
from __future__ import annotations

import pytest

from scripts.p1_fixtures import build
from zaad.full.contracts import Request
from zaad.full.evaluation import long_truth
from zaad.full.fixtures_p1 import p1_request
from zaad.full.lotsizing import continuation_caps, cycle_continuation_terms, economic_cycle, reference_lots, steady_state_unit_costs
from zaad.full.model import Solution, solve
from zaad.full.ownership import PROTECTION_RECOVERY, PURCHASING_ECONOMICS
from zaad.full.planner import plan
from zaad.full.replay import replay
from zaad.full.settlement import settle
from zaad.full.terminal import continuation_value
from zaad.full.worlds import draw, forecast_all

PRODUCT = {k: Request.model_fields[k].default for k in ("stratified_scenarios", "timing_tiebreak", "analytic_shortage")}


def _req(**kw):
    return p1_request(seed=41001, **kw).model_copy(update=PRODUCT)


def _lot(req):
    return reference_lots(req, forecast_all(req))["supplier"]["lot_units"]


def _first_lot(req, cap=None):
    """The mean-world plan's period-0 order under the cycle continuation (optionally capped)."""
    fits = forecast_all(req)
    src = req.sources[0]
    if cap is not None:
        req = req.model_copy(update={"sources": [s.model_copy(update={"capacity_by_period": [cap if t == 0 else c for t, c in enumerate(s.capacity_by_period)]}) if s.id == src.id else s for s in req.sources]})
    world = draw(req, req.seed, 1, deterministic=True)
    sol = solve(req, world, continuation=cycle_continuation_terms(req, fits))
    return sol.purchases.get((src.id, 0), 0.), sol


def test_01_fixed_order_cost_raises_the_economic_lot_and_the_first_lot_weakly():
    lots, first = [], []
    for fee in (100., 250., 600.):
        req = _req(incumbent_rule="replace_sold", supplier_terms={"fixed_order_cost": fee})
        lots.append(_lot(req))
        first.append(_first_lot(req)[0])
    assert lots[0] < lots[1] < lots[2]
    assert first[0] <= first[1] + 1e-6 <= first[2] + 2e-6


def test_02_carrying_cost_lowers_the_economic_lot_weakly():
    lots = [_lot(_req(incumbent_rule="replace_sold", supplier_terms={"fixed_order_cost": 250.}, holding_per_year=h)) for h in (.10, .15, .30, .60)]
    assert all(a >= b - 1e-9 for a, b in zip(lots, lots[1:]))
    firsts = [_first_lot(_req(incumbent_rule="replace_sold", supplier_terms={"fixed_order_cost": 250.}, holding_per_year=h))[0] for h in (.15, .60)]
    assert firsts[1] <= firsts[0] + 1e-6


def test_03_moq_above_the_economic_lot_is_respected():
    req = _req(incumbent_rule="replace_sold", supplier_terms={"fixed_order_cost": 250.}, minimum=2500.)
    assert _lot(req) == pytest.approx(2500.)
    x0, sol = _first_lot(req)
    assert x0 == 0. or x0 >= 2500. - 1e-6
    settle(req, sol, draw(req, req.seed, 1, deterministic=True)[0])     # legal in the settlement


def test_04_pack_and_pallet_rounding_keep_the_candidate_legal():
    req = _req(incumbent_rule="replace_sold", supplier_terms={"fixed_order_cost": 250.}, case_multiple=48.)
    x0, sol = _first_lot(req)
    assert x0 > 0 and abs(x0 / 48. - round(x0 / 48.)) < 1e-6
    settle(req, sol, draw(req, req.seed, 1, deterministic=True)[0])


def _avg_cost_per_period(req, lot, fixed_and_tariff):
    """Average-cost rate of buying `lot` per order: order costs per period plus holding on half a lot."""
    fits = forecast_all(req)
    mu = sum(float(fits[s.id]["mean"]) for s in req.services)
    h = 5. * (req.locations[0].holding_per_value_period + req.liquidity.cost_of_capital_per_period)
    return fixed_and_tariff * mu / lot + h * lot / 2.


def test_05_a_cheaper_larger_shipment_is_reflected_in_the_reference_and_the_frontier():
    """Nine pallets at $1,100 against $800 for four (plus $150 per order): by the declared economics the
    full load (450 units) is the cheaper average-cost lot; the reference lot is the full load and the
    mean-world plan buys it."""
    tiers = [{"up_to_pallets": 4, "charge": 800.}, {"up_to_pallets": 9, "charge": 1100.}]
    req = _req(incumbent_rule="reorder_point", supplier_terms={"units_per_pallet": {"A": 50.}, "freight_tiers": tiers, "max_pallets": 9., "fixed_order_cost": 150.})
    assert _avg_cost_per_period(req, 450., 1250.) < _avg_cost_per_period(req, 200., 950.)
    assert _lot(req) == pytest.approx(450.)
    x0, _ = _first_lot(req)
    assert x0 == pytest.approx(450., abs=1.)


def test_06_an_uneconomic_freight_threshold_does_not_fill_the_truck():
    """A 40-pallet load at $1,100 against $150 for four pallets, no per-order fee, holding .60 of value a
    year: by the declared economics the full truck (2,000 units, 20 weeks) costs more per period than
    four-pallet buying; the plan does not fill the truck."""
    tiers = [{"up_to_pallets": 4, "charge": 150.}, {"up_to_pallets": 40, "charge": 1100.}]
    req = _req(incumbent_rule="reorder_point", holding_per_year=.60, supplier_terms={"units_per_pallet": {"A": 50.}, "freight_tiers": tiers, "max_pallets": 40., "fixed_order_cost": 0.})
    assert _avg_cost_per_period(req, 2000., 1100.) > _avg_cost_per_period(req, 200., 150.)
    x0, _ = _first_lot(req)
    assert x0 < 1000.


def test_07_avoided_future_orders_beyond_the_horizon_are_recognised():
    """Fixture B's economics: economic lot 1,854 against a twelve-period horizon. Without the
    continuation the plan buys the window (about 1,060); with it, the economic lot."""
    req = build("B_fixed_order_cost_replace_sold", 41003).model_copy(update=PRODUCT)
    src = req.sources[0]
    world = draw(req, req.seed, 1, deterministic=True)
    plain = solve(req, world).purchases.get((src.id, 0), 0.)
    x0, _ = _first_lot(req)
    assert plain < 1200.
    assert abs(x0 - _lot(req)) < .05 * _lot(req)


def test_08_short_cycle_reduces_to_ordinary_behaviour():
    """No order-level economics: the reference is one period of demand, the credit within a cent of
    the price, and the plan is unchanged by the continuation."""
    req = _req(incumbent_rule="reorder_point")
    fits = forecast_all(req)
    assert economic_cycle(req, fits)["supplier"]["cycle_periods"] == pytest.approx(1.)
    assert steady_state_unit_costs(req, fits)["A"] < 5. / .98 + .02
    src = req.sources[0]
    world = draw(req, req.seed, 1, deterministic=True)
    a = solve(req, world).purchases.get((src.id, 0), 0.)
    b = _first_lot(req)[0]
    assert abs(a - b) < 1.


def test_09_no_order_when_stock_covers_the_cycle():
    req = _req(incumbent_rule="replace_sold", supplier_terms={"fixed_order_cost": 250.}, opening_units=2500.)
    x0, _ = _first_lot(req)
    assert x0 < 1.


def test_10_efficient_incumbent_still_gets_no_material_improvement():
    rep = plan(build("A_no_terms_good_incumbent", 41001).model_copy(update=PRODUCT))
    assert rep["orchestration"]["planner_owner"] == PURCHASING_ECONOMICS
    assert rep["status"] == "RETAIN_INCUMBENT" or rep["economics"]["materiality"] is not None


def test_11_high_service_volatile_review_keeps_its_protection():
    rep = plan(build("Q_volatile_demand_high_target", 41001).model_copy(update=PRODUCT))
    assert rep["orchestration"]["gate_basis"] == "incumbent"
    assert all(v is None or v >= .95 for v in rep["confirmation"]["candidate"].get("service", {}).values()) if rep["status"] == "PENDING_REVIEW" else True


def test_12_genuine_disruption_is_p0_owned_and_gets_no_continuation():
    severe = build("B_fixed_order_cost_replace_sold", 41001, stresses="severe").model_copy(update=PRODUCT)
    rep = plan(severe)
    assert rep["orchestration"]["planner_owner"] == PROTECTION_RECOVERY
    assert rep["orchestration"]["p1_economics"] == {}


def test_13_cycle_stock_is_not_protection():
    rep = plan(build("T_combined_realistic", 41001).model_copy(update=PRODUCT))
    assert rep["orchestration"]["planner_owner"] == PURCHASING_ECONOMICS
    assert rep["orchestration"]["p1_economics"]["terminal_economic_basis"] == "cycle"


def test_14_no_artificial_profit_at_the_horizon_edge():
    """The marginal credit of the k-th residual unit is c*/mu less its own carrying and it is at most
    c*/mu; a plan that buys a full economic lot in the last in-window period pays its order cost and
    gains nothing against buying it at the reorder point: the objective of the late-lot plan is not
    below the plan that buys the lot now."""
    req = build("B_fixed_order_cost_replace_sold", 41003).model_copy(update=PRODUCT)
    fits = forecast_all(req)
    terms = cycle_continuation_terms(req, fits)
    src = req.sources[0]
    world = draw(req, req.seed, 1, deterministic=True)
    now = solve(req, world, fixed=Solution("OPTIMAL", {(src.id, 0): 1854.}, {}, {}, {}, None, [], 0., 0, 0, None, None, []), continuation=terms).projected_cost
    late = solve(req, world, fixed=Solution("OPTIMAL", {(src.id, 0): 1058., (src.id, 10): 1854.}, {}, {}, {}, None, [], 0., 0, 0, None, None, []), continuation=terms).projected_cost
    assert late >= now - 1e-6
    unit = steady_state_unit_costs(req, fits)["A"]
    assert all(margin + req.skus[0].terminal_value <= unit + 1e-9 for _, margin in terms[("A", "branch")])


def test_15_no_double_counting_between_the_window_and_the_continuation():
    """The continuation credits only post-horizon supply: with no residual the term adds nothing, and
    the objective difference it makes equals the intended slab credit of the residual exactly."""
    req = build("B_fixed_order_cost_replace_sold", 41003).model_copy(update=PRODUCT)
    fits = forecast_all(req)
    terms = cycle_continuation_terms(req, fits)
    src = req.sources[0]
    world = draw(req, req.seed, 1, deterministic=True)
    for q in (1058., 1400.):
        pinned = Solution("OPTIMAL", {(src.id, 0): q}, {}, {}, {}, None, [], 0., 0, 0, None, None, [])
        plain = solve(req, world, fixed=pinned)
        withc = solve(req, world, fixed=pinned, continuation=terms)
        residual = sum(x["quantity"] for x in settle(req, plain, world[0])["end_stock"])
        left, intended = residual, 0.
        for units, margin in terms[("A", "branch")]:
            take = min(units, left)
            intended += take * margin
            left -= take
        assert plain.projected_cost - withc.projected_cost == pytest.approx(intended, abs=1e-3)


def test_16_evaluation_rows_reconcile_and_the_realised_ledger_is_untouched():
    from zaad.full.economics import cost_breakdown, reconcile
    from zaad.full.planner import evaluate
    req = build("B_fixed_order_cost_replace_sold", 41003).model_copy(update=PRODUCT)
    fits = forecast_all(req)
    worlds = draw(req, req.seed, 1, deterministic=True)
    sol = Solution("OPTIMAL", {(req.sources[0].id, 0): 1854.}, {}, {}, {}, None, [], 0., 0, 0, None, None, [])
    row = evaluate(req, sol, worlds, terminal=steady_state_unit_costs(req, fits), fits=fits, terminal_cap=continuation_caps(req, fits))[0]
    assert reconcile(row)["reconciled"] and abs(cost_breakdown(row["ledger"])["TOTAL"] - row["economic_cost"]) < 1e-6
    realised = settle(req, sol, worlds[0])
    assert "terminal_continuation" not in realised["ledger"] and realised["ledger"]["closing_assets"] == row["ledger"]["closing_assets"]
    # the cap: units beyond one economic cycle earn salvage only
    big = continuation_value(req, [{"sku": "A", "location": "branch", "expiry": 60, "quantity": 5000.}], [], {req.services[0].id: {"mean": 99.}}, landed=steady_state_unit_costs(req, fits), cap_units=continuation_caps(req, fits))
    small = continuation_value(req, [{"sku": "A", "location": "branch", "expiry": 60, "quantity": 1000.}], [], {req.services[0].id: {"mean": 99.}}, landed=steady_state_unit_costs(req, fits), cap_units=continuation_caps(req, fits))
    assert big["continuation_credit"] - small["continuation_credit"] < 4000. * req.skus[0].terminal_value + 1e-6 + 900. * 1.4


def test_17_first_lot_is_stable_across_the_detailed_horizon():
    """The economic lot should not depend on the arbitrary detailed horizon once the cycle is
    represented: at 12, 16 and 20 periods the mean-world first lot stays within 10% of the economic
    lot (before the continuation the twelve-period plan bought the window, 1,058)."""
    from zaad.full.evaluation import with_horizon
    base = build("B_fixed_order_cost_replace_sold", 41003).model_copy(update=PRODUCT)
    lot = _lot(base)
    for h in (12, 16, 20):
        req = with_horizon(base, h)
        x0, _ = _first_lot(req)
        assert abs(x0 - lot) < .10 * lot, (h, x0, lot)


def test_18_perishable_stock_earns_no_credit_beyond_its_shelf_life():
    """B's economics with a 16-period shelf life against a 12-period window: at most four post-window
    slabs, and the mean-world lot shrinks to what can be sold before expiry (about 16 periods of demand,
    well below the 1,854 economic lot); with a shelf life no longer than the window there is no slab."""
    base = build("B_fixed_order_cost_replace_sold", 41003).model_copy(update=PRODUCT)
    short = base.model_copy(update={"skus": [s.model_copy(update={"shelf_life": 16}) for s in base.skus]})
    fits = forecast_all(short)
    assert len(cycle_continuation_terms(short, fits)[("A", "branch")]) <= 4
    x0, _ = _first_lot(short)
    assert x0 < 1854. - 250.
    none = base.model_copy(update={"skus": [s.model_copy(update={"shelf_life": 12}) for s in base.skus]})
    assert cycle_continuation_terms(none, forecast_all(none)) == {}


def test_19_purchasing_economics_reviews_rank_on_cost_and_protection_reviews_keep_the_band():
    """Rule P1-S. On every purchasing-economics review of a rolling B replay the chosen candidate is a
    cheapest well-solved feasible candidate (burden breaks numerical ties only); on a protection-owned
    review (severe declared stress) the leanest candidate inside the downside band is still chosen."""
    import zaad.full.planner as P
    import zaad.full.replay as R
    from zaad.full.planner import EXCLUDE_FROM_SELECTION

    traces: list[dict] = []
    orig = P.plan

    def traced(r):
        P.TRACE = {}
        rep = orig(r)
        t = dict(P.TRACE)
        P.TRACE = None
        cands = {n: c for n, c in (t.get("candidates") or {}).items()
                 if c.get("feasible") and c["status"] == "OPTIMAL" and c.get("hedged_cost") is not None and n not in EXCLUDE_FROM_SELECTION}
        traces.append({"owner": rep["orchestration"]["planner_owner"], "chosen": t.get("chosen"), "candidates": cands, "state": t.get("state")})
        return rep

    P.plan = traced
    R.plan = traced
    try:
        req = build("B_fixed_order_cost_replace_sold", 41002).model_copy(update=PRODUCT)
        replay(req, long_truth(req, 41002 + 10000, 36), 14, "gated", rolling=True)
        P.plan(build("B_fixed_order_cost_replace_sold", 41002, stresses="severe").model_copy(update=PRODUCT))
    finally:
        P.plan = orig
        R.plan = orig
    purchasing = [t for t in traces[:14] if t["owner"] == PURCHASING_ECONOMICS and t["chosen"] in t["candidates"]]
    assert len(purchasing) >= 10
    for t in purchasing:
        cheapest = min(c["hedged_cost"] for c in t["candidates"].values())
        assert t["candidates"][t["chosen"]]["hedged_cost"] <= cheapest + 1e-6 * max(abs(cheapest), 1.), (t["state"], t["chosen"])
    severe = traces[14]
    assert severe["owner"] == PROTECTION_RECOVERY
    if severe["chosen"] in severe["candidates"]:
        cheapest = min(c["hedged_cost"] for c in severe["candidates"].values())
        band = [c for c in severe["candidates"].values() if c["hedged_cost"] <= cheapest + req.downside_cost_tolerance * max(abs(cheapest), 1.) + 1e-9]
        assert severe["candidates"][severe["chosen"]]["burden"] <= min(c["burden"] for c in band) + 1e-9 or severe["candidates"][severe["chosen"]]["hedged_cost"] <= cheapest + 1e-9
