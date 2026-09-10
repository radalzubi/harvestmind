"""Finite-horizon continuation value of residual stock (evaluation only, `zaad/full/terminal.py`)."""
from __future__ import annotations

import pytest

from zaad.full.contracts import Request
from zaad.full.fixtures_p1 import p1_request
from zaad.full.replay import replay
from zaad.full.terminal import continuation_value
from zaad.full.worlds import draw
from scripts.p1_fixtures import build

PRODUCT = {k: Request.model_fields[k].default for k in ("stratified_scenarios", "timing_tiebreak", "analytic_shortage")}


def _req(**kw):
    return p1_request(seed=1, **kw)


def _fits(req, mean):
    return {s.id: {"mean": mean} for s in req.services}


def _stock(q, expiry=100):
    return [{"sku": "A", "location": "branch", "expiry": expiry, "quantity": q}]


def test_1_zero_remaining_demand_gets_salvage_only():
    req = _req()
    out = continuation_value(req, _stock(200.), [], _fits(req, 0.))
    assert out["continuation_credit"] == pytest.approx(out["salvage_credit"]) == pytest.approx(200. * req.skus[0].terminal_value)
    assert out["adjustment"] == pytest.approx(0.)


def test_2_residual_consumed_next_period_is_worth_nearly_the_purchase_it_avoids():
    req = _req()
    price, salvage = req.skus[0].asset_value, req.skus[0].terminal_value
    out = continuation_value(req, _stock(10.), [], _fits(req, 1000.))     # consumed within a hundredth of a period
    per_unit = out["continuation_credit"] / 10.
    assert salvage < per_unit <= price and per_unit == pytest.approx(price, rel=1e-3)
    assert out["adjustment"] < 0.


def test_3_slow_consumption_and_carrying_reduce_the_value_monotonically():
    req = _req()
    values = [continuation_value(req, _stock(100.), [], _fits(req, mu))["continuation_credit"] for mu in (100., 20., 5., 1., .2)]
    assert all(a >= b - 1e-9 for a, b in zip(values, values[1:]))
    assert values[-1] >= 100. * req.skus[0].terminal_value - 1e-9          # never below salvage
    # a declared cost of capital lowers the value further at the same consumption rate
    dear = req.model_copy(update={"liquidity": req.liquidity.model_copy(update={"cost_of_capital_per_period": .01})})
    assert continuation_value(dear, _stock(100.), [], _fits(dear, 5.))["continuation_credit"] < continuation_value(req, _stock(100.), [], _fits(req, 5.))["continuation_credit"]


def test_4_units_expiring_before_consumption_are_worth_salvage():
    req = _req()
    fresh = continuation_value(req, _stock(100., expiry=100), [], _fits(req, 10.))["continuation_credit"]
    short = continuation_value(req, _stock(100., expiry=4), [], _fits(req, 10.))["continuation_credit"]    # 3 post-window periods: 30 units consumed, 70 expire
    none = continuation_value(req, _stock(100., expiry=1), [], _fits(req, 10.))["continuation_credit"]     # expires at the window end
    assert fresh > short > none
    assert none == pytest.approx(100. * req.skus[0].terminal_value)
    assert continuation_value(req, _stock(100., expiry=4), [], _fits(req, 10.))["detail"]["A@branch"]["consumed_before_expiry"] == pytest.approx(30.)


def test_5_in_transit_arrival_timing_matters():
    req = _req()
    on_hand = continuation_value(req, _stock(100.), [], _fits(req, 10.))["continuation_credit"]
    soon = continuation_value(req, [], [("A", "branch", 100, 1, 100., "external")], _fits(req, 10.))["continuation_credit"]
    late = continuation_value(req, [], [("A", "branch", 100, 6, 100., "external")], _fits(req, 10.))["continuation_credit"]
    assert on_hand == pytest.approx(soon)        # due 1 = the first post-window period
    assert soon > late >= 100. * req.skus[0].terminal_value


def test_6_moq_lot_straddling_the_horizon_has_no_artificial_cliff():
    req = _req(minimum=400.)
    price, salvage = req.skus[0].asset_value, req.skus[0].terminal_value
    lot = continuation_value(req, _stock(50.), [("A", "branch", 100, 2, 400., "external")], _fits(req, 100.))
    per_unit = lot["continuation_credit"] / 450.
    assert salvage < per_unit < price
    assert lot["detail"]["A@branch"]["periods_to_consume"] == pytest.approx(4.5)
    # the same lot one period later is worth a little less, continuously
    later = continuation_value(req, _stock(50.), [("A", "branch", 100, 3, 400., "external")], _fits(req, 100.))
    assert 0. < lot["continuation_credit"] - later["continuation_credit"] < 0.02 * lot["continuation_credit"]


def test_7_derived_value_agrees_with_extended_horizon_consumption_on_fixture_c():
    """Fixture C at 11 reviews: the derived continuation of the residual agrees with drawing twelve
    further truth periods from the same fitted distribution and consuming the residual at price
    (carrying charged, remainder at salvage), within one per cent of the residual's value."""
    req = build("C_moq_four_weeks", 41001).model_copy(update=PRODUCT)
    truth = draw(req, 41001 + 10000, 1)[0]
    out = replay(req, truth, 11, "reorder_point")
    term = out["terminal_continuation"]
    sku = req.skus[0]
    price, salvage = sku.asset_value, sku.terminal_value
    h = req.locations[0].holding_per_value_period + req.liquidity.cost_of_capital_per_period
    ext = draw(req.model_copy(update={"horizon": 12}), 41001 + 20000, 1)[0]
    stock, consumed, held = term["units"], 0., 0.
    for t in range(12):
        d = ext.demand[req.services[0].id][t]
        take = min(stock, d)
        consumed += take
        stock -= take
        held += stock
    empirical = consumed * price - held * h * price + stock * salvage
    assert term["units"] > 0
    assert abs(term["continuation_credit"] - empirical) <= .01 * term["salvage_credit"] + 5.


def test_8_same_policy_under_a_longer_window_moves_continuously():
    """Lengthening the window by one review changes the continuation-valued cost by about one
    period of operating cost, not by a lot's salvage haircut."""
    req = build("C_moq_four_weeks", 41001).model_copy(update=PRODUCT)
    truth = draw(req, 41001 + 10000, 1)[0]
    a = replay(req, truth, 10, "reorder_point")
    b = replay(req, truth, 11, "reorder_point")
    price = req.skus[0].asset_value
    step_continuation = b["economic_cost_continuation"] - a["economic_cost_continuation"]
    step_salvage = b["economic_cost"] - a["economic_cost"]
    one_period = 100. * price
    assert abs(step_continuation - one_period) < .5 * one_period
    assert abs(step_continuation - one_period) <= abs(step_salvage - one_period) + 1e-9


def test_9_ledger_is_not_falsified():
    req = build("P_high_opening_stock", 41001).model_copy(update=PRODUCT)
    truth = draw(req, 41001 + 10000, 1)[0]
    out = replay(req, truth, 4, "reorder_point")
    assert out["economic_cost"] == pytest.approx(sum(out["ledger"].values()))
    assert out["ledger"]["closing_assets"] == pytest.approx(-out["terminal_continuation"]["salvage_credit"])
    assert out["economic_cost_continuation"] == pytest.approx(out["economic_cost"] + out["terminal_continuation"]["adjustment"])
    assert "adjustment" not in out["ledger"] and "continuation" not in " ".join(out["ledger"])
