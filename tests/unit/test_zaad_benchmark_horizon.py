"""P1 benchmark validation tests (Stage 7 of the benchmark / horizon closure pass).

Twelve properties the declared extended-window evaluation must have, pre-registered in
`docs/zaad_full/evidence/p1/P1_BENCHMARK_PREREGISTRATION.md`. Each is tested on the evaluation code
(`zaad/full/evaluation.py`, `zaad/full/terminal.py`) with synthetic residual states or short rolling
replays of the P1 fixtures on baseline policies; none depends on ZAAD's own result. Tests that compare
the salvage rule (A) and the continuation rule (B) record which rule has the property, because the
pre-registered selection rule requires a rule to pass all twelve."""
from __future__ import annotations

from datetime import timedelta

import pytest

from scripts.p1_fixtures import build
from zaad.full.contracts import Request
from zaad.full.evaluation import curve, endpoint, long_truth
from zaad.full.replay import replay
from zaad.full.terminal import continuation_value
from zaad.full.worlds import draw

PRODUCT = {k: Request.model_fields[k].default for k in ("stratified_scenarios", "timing_tiebreak", "analytic_shortage")}


def _fits(req, mean):
    return {s.id: {"mean": mean} for s in req.services}


def _stock(q, expiry=100):
    return [{"sku": "A", "location": "branch", "expiry": expiry, "quantity": q}]


def _rolling(name, policy, reviews, seed=41001, as_of_shift_days=0):
    req = build(name, seed).model_copy(update=PRODUCT)
    if as_of_shift_days:
        req = req.model_copy(update={"as_of": req.as_of + timedelta(days=as_of_shift_days)})
    truth = long_truth(req, seed + 10000, 12 * (-(-(reviews - 1 + 12) // 12)))
    out = replay(req, truth, reviews, policy, rolling=True)
    assert out["status"] == "COMPLETE", out
    return req, out


def _delta(a, b, key):
    return 100. * (a[key] - b[key]) / b[key]


def test_01_identical_policies_offset_by_one_order_period_have_equal_long_run_economics():
    """periodic:4 on fixture C started three weeks later (the cadence counts from a fixed epoch, so
    this shifts its lot phase by one review) buys the same lots one week out of phase on the same
    demand path. The fixture's 150 opening units are an initial condition, not part of either phase,
    so the comparison is the window [4, 52] with symmetric endpoint handling (stock at both ends
    valued by the same rule). The continuation-valued costs agree within one per cent and the
    salvage rule's disagreement is not smaller."""
    req_a, a = _rolling("C_moq_four_weeks", "periodic:4", 52)
    req_b, b = _rolling("C_moq_four_weeks", "periodic:4", 52, as_of_shift_days=21)
    ca, cb = curve(req_a, a["reviews"]), curve(req_b, b["reviews"])
    assert [r["review"] for r in b["reviews"] if r["purchases"]][:3] == [1, 5, 9]
    def window(c, key):
        return c[51][key] - c[3][key]
    gap_cont = abs(100. * (window(ca, "continuation") - window(cb, "continuation")) / window(cb, "continuation"))
    gap_salv = abs(100. * (window(ca, "realized") - window(cb, "realized")) / window(cb, "realized"))
    assert gap_cont < 1.0
    assert gap_cont <= gap_salv + 1e-9


def test_02_residual_consumed_immediately_after_cutoff_is_not_economically_lost():
    req = build("C_moq_four_weeks", 41001).model_copy(update=PRODUCT)
    price, salvage = req.skus[0].asset_value, req.skus[0].terminal_value
    out = continuation_value(req, _stock(100.), [], _fits(req, 100.))     # consumed in one period
    per_unit = out["continuation_credit"] / 100.
    assert per_unit > .99 * price                       # rule B: nearly the purchase it avoids
    assert out["salvage_credit"] / 100. == pytest.approx(salvage)   # rule A: 20% loss regardless


def test_03_residual_never_consumed_is_not_given_full_value():
    req = build("C_moq_four_weeks", 41001).model_copy(update=PRODUCT)
    out = continuation_value(req, _stock(100.), [], _fits(req, 0.))
    assert out["continuation_credit"] == pytest.approx(out["salvage_credit"])
    assert out["continuation_credit"] < 100. * req.skus[0].asset_value


def test_04_in_transit_arriving_after_cutoff_is_valued_consistently():
    req = build("C_moq_four_weeks", 41001).model_copy(update=PRODUCT)
    on_hand = continuation_value(req, _stock(100.), [], _fits(req, 50.))["continuation_credit"]
    transit = continuation_value(req, [], [("A", "branch", 100, 2, 100., "external")], _fits(req, 50.))["continuation_credit"]
    late = continuation_value(req, [], [("A", "branch", 100, 5, 100., "external")], _fits(req, 50.))["continuation_credit"]
    assert on_hand > transit > late > 100. * req.skus[0].terminal_value - 1e-9
    # and the salvage ledger values transit and on-hand units identically (the ledger's own rule)
    assert continuation_value(req, [], [("A", "branch", 100, 2, 100., "external")], _fits(req, 50.))["salvage_credit"] == pytest.approx(100. * req.skus[0].terminal_value)


def test_05_high_carrying_cost_reduces_continuation_value():
    req = build("C_moq_four_weeks", 41001).model_copy(update=PRODUCT)
    dear = build("L_high_holding_rate", 41001).model_copy(update=PRODUCT)     # 30%/yr against 15%/yr
    cheap = continuation_value(req, _stock(400.), [], _fits(req, 50.))["continuation_credit"]
    costly = continuation_value(dear, _stock(400.), [], _fits(dear, 50.))["continuation_credit"]
    assert costly < cheap


def test_06_financing_cost_is_preserved_in_the_terminal_value():
    req = build("C_moq_four_weeks", 41001).model_copy(update=PRODUCT)
    financed = req.model_copy(update={"liquidity": req.liquidity.model_copy(update={"cost_of_capital_per_period": .12 * 7 / 365})})
    assert continuation_value(financed, _stock(400.), [], _fits(financed, 50.))["continuation_credit"] < continuation_value(req, _stock(400.), [], _fits(req, 50.))["continuation_credit"]


def test_07_zero_future_demand_impairs_the_residual_to_salvage():
    req = build("C_moq_four_weeks", 41001).model_copy(update=PRODUCT)
    out = continuation_value(req, _stock(400.), [("A", "branch", 100, 2, 400., "external")], _fits(req, 0.))
    assert out["continuation_credit"] == pytest.approx(800. * req.skus[0].terminal_value)
    assert out["adjustment"] == pytest.approx(0.)


def test_08_complete_lot_cycle_finite_window_and_extended_evaluation_converge():
    """EOQ on fixture I buys 450-unit loads every 4-5 weeks. Two endpoints with the same physical
    state (on hand within five per cent of a load, same in-transit units) enclose a whole number of
    lot cycles. Over such a window the terminal credits cancel, so the salvage and continuation rules
    give the same window cost (within one per cent), and the window's continuation cost per unit
    of demand agrees with the 40-review value within 1.5 per cent: a window closed on a complete
    cycle and the extended evaluation say the same thing. Under the landed-cost continuation rule
    (correction 1); the unit-price rule fails the second property on this freight-heavy fixture."""
    req, a = _rolling("I_max_pallets_ftl_cap", "economic_lot", 40)
    c = curve(req, a["reviews"])
    demand_to = [0.]
    for row in a["reviews"]:
        demand_to.append(demand_to[-1] + sum(x["demand"] for x in row["settlement"]["service_by_period"]))
    pairs = [(x, y) for x in c for y in c if 12 <= x["W"] and x["W"] + 8 <= y["W"]
             and abs(x["terminal_on_hand"] - y["terminal_on_hand"]) < .05 * 450. and abs(x["terminal_in_transit"] - y["terminal_in_transit"]) < 1e-6]
    assert len(pairs) >= 2, "no matched-state endpoint pairs found"
    long_run = c[-1]["continuation_landed"] / demand_to[40]
    long_run_unit_price = c[-1]["continuation"] / demand_to[40]
    for x, y in pairs:
        salv = y["realized"] - x["realized"]
        cont = y["continuation_landed"] - x["continuation_landed"]
        assert abs(salv - cont) / cont < .01, (x["W"], y["W"], salv, cont)     # cancels up to the drift of the policy's own landed premium
        per_unit = cont / (demand_to[y["W"]] - demand_to[x["W"]])
        assert abs(per_unit - long_run) / long_run < .015, (x["W"], y["W"], per_unit, long_run)
        # the unit-price continuation (pre-registered rule B before correction 1) sits further from the
        # window's per-unit cost: the 40-review endpoint follows a load whose freight it charges but
        # whose units it credits at the bare price
        assert abs(per_unit - long_run_unit_price) > abs(per_unit - long_run)


def test_09_increasing_horizon_converges_the_policy_ranking():
    """The pairwise delta between the full-load EOQ baseline and the periodic baseline on fixture I
    varies less over the last twelve endpoints than over the first twelve, under both rules."""
    req, a = _rolling("I_max_pallets_ftl_cap", "economic_lot", 40)
    _, b = _rolling("I_max_pallets_ftl_cap", "periodic:2", 40)
    ca, cb = curve(req, a["reviews"]), curve(req, b["reviews"])
    for key in ("continuation", "realized"):
        deltas = [_delta(x, y, key) for x, y in zip(ca, cb)]
        early = max(deltas[6:18]) - min(deltas[6:18])
        late = max(deltas[28:40]) - min(deltas[28:40])
        assert late < early, (key, early, late)


def test_10_identical_physical_trajectory_gives_the_same_benchmark_result():
    """The endpoint reconstruction of a long rolling run equals a run stopped at that endpoint."""
    req, long = _rolling("C_moq_four_weeks", "reorder_point", 15)
    _, short = _rolling("C_moq_four_weeks", "reorder_point", 6)
    e = endpoint(req, long["reviews"], 6)
    assert e["realized"] == pytest.approx(short["economic_cost"], abs=1e-6)
    assert e["continuation"] == pytest.approx(short["economic_cost_continuation"], abs=1e-6)
    assert e["ledger"]["closing_assets"] == pytest.approx(short["ledger"]["closing_assets"], abs=1e-6)


def test_11_service_after_the_nominal_window_is_not_scored():
    """Service, breaches and unmet at endpoint W come from reviews 0..W-1 only; what happens after W
    never changes them, while the terminal credit is the only channel through which post-window
    consumption enters (at the fitted rate, never as realised service)."""
    req, out = _rolling("O_low_opening_stock", "reorder_point", 15)
    e10 = endpoint(req, out["reviews"], 10)
    trimmed = endpoint(req, out["reviews"][:10], 10)
    assert e10["service"] == pytest.approx(trimmed["service"]) and e10["unmet"] == pytest.approx(trimmed["unmet"]) and e10["breaches"] == trimmed["breaches"]
    demand = sum(x["demand"] for r in out["reviews"][:10] for x in r["settlement"]["service_by_period"])
    served = sum(x["served"] for r in out["reviews"][:10] for x in r["settlement"]["service_by_period"])
    assert e10["service"] == pytest.approx(served / demand)


def test_12_baseline_and_zaad_receive_identical_endpoint_handling():
    """The scorer has no policy argument: two logs with the same physical terminal state get the same
    terminal credit under both rules whatever produced them."""
    req = build("C_moq_four_weeks", 41001).model_copy(update=PRODUCT)
    truth = long_truth(req, 51001, 24)
    a = replay(req, truth, 8, "reorder_point", rolling=True)
    b = replay(req, truth, 8, "periodic:2", rolling=True)
    swapped = [dict(r) for r in b["reviews"]]
    swapped[-1] = {**swapped[-1], "settlement": {**swapped[-1]["settlement"], "end_stock": a["reviews"][-1]["settlement"]["end_stock"],
                                                 "pending": a["reviews"][-1]["settlement"]["pending"],
                                                 "ledger": {**swapped[-1]["settlement"]["ledger"], "closing_assets": a["reviews"][-1]["settlement"]["ledger"]["closing_assets"]}},
                   "forecast": a["reviews"][-1]["forecast"]}
    ea, es = endpoint(req, a["reviews"], 8), endpoint(req, swapped, 8)
    assert ea["salvage_credit"] == pytest.approx(es["salvage_credit"])
    assert ea["continuation_credit"] == pytest.approx(es["continuation_credit"])
    assert ea["ledger"]["closing_assets"] == pytest.approx(es["ledger"]["closing_assets"])
