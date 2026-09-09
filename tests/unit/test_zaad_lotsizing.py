"""Lot-sizing terminal valuation (P1 benchmark / horizon closure pass; `zaad/full/lotsizing.py`)."""
from __future__ import annotations

import pytest

from scripts.p1_fixtures import build
from zaad.full.contracts import Request
from zaad.full.evaluation import long_truth
from zaad.full.lotsizing import landed_unit_costs, reference_lots, terminal_terms
from zaad.full.model import solve
from zaad.full.planner import plan
from zaad.full.replay import replay
from zaad.full.worlds import draw, forecast_all

PRODUCT = {k: Request.model_fields[k].default for k in ("stratified_scenarios", "timing_tiebreak", "analytic_shortage")}


def _req(name, seed=41001):
    return build(name, seed).model_copy(update=PRODUCT)


def test_reference_lot_is_the_full_load_under_a_freight_cap():
    req = _req("I_max_pallets_ftl_cap")
    lots = reference_lots(req, forecast_all(req))
    lot = lots["supplier"]
    assert lot["lot_units"] == pytest.approx(450.)              # nine pallets of fifty
    assert lot["premium_per_unit"] == pytest.approx((1100. + 150.) / 450.)
    landed = landed_unit_costs(req, forecast_all(req))
    assert landed["A"] == pytest.approx(5. + (1100. + 150.) / 450.)


def test_reference_lot_is_the_eoq_without_a_load_limit():
    req = _req("B_fixed_order_cost_replace_sold")
    fits = forecast_all(req)
    lot = reference_lots(req, fits)["supplier"]
    mu = fits[req.services[0].id]["mean"]
    h = 5. * req.locations[0].holding_per_value_period
    assert lot["lot_units"] == pytest.approx((2. * 250. * mu / h) ** .5)
    assert lot["load_cap_units"] is None
    assert landed_unit_costs(req, fits)["A"] == pytest.approx(5. + 250. / lot["lot_units"])


def test_no_order_level_economics_means_no_premium():
    req = _req("A_no_terms_good_incumbent")
    fits = forecast_all(req)
    assert reference_lots(req, fits)["supplier"]["premium_per_unit"] == 0.
    assert landed_unit_costs(req, fits)["A"] == pytest.approx(5.)
    (units, margin), = terminal_terms(req, fits).values()
    assert units == pytest.approx(fits[req.services[0].id]["mean"])
    assert 0. < margin < 5. - 4.          # price less salvage less carrying


def test_terminal_terms_margin_is_landed_less_salvage_less_carrying_and_never_negative():
    req = _req("I_max_pallets_ftl_cap")
    fits = forecast_all(req)
    (units, margin), = terminal_terms(req, fits).values()
    landed = landed_unit_costs(req, fits)["A"]
    tau = 450. / (2. * fits[req.services[0].id]["mean"])
    assert units == pytest.approx(450.)
    assert margin == pytest.approx(landed - 4. - 5. * req.locations[0].holding_per_value_period * tau)
    dear = req.model_copy(update={"skus": [s.model_copy(update={"terminal_value": 40.}) for s in req.skus]})
    assert terminal_terms(dear, fits) == {}


def test_the_term_makes_the_full_load_the_optimum_on_the_review_17_snapshot():
    """The J12 forensic snapshot: without the term the optimizer, allowed a full load, prefers 166
    units now; with it the optimum is 450 now on a 4-5 week cadence."""
    req0 = _req("I_max_pallets_ftl_cap")
    kept: list[Request] = []
    replay(req0, long_truth(req0, 51001, 36), 18, "reorder_point", rolling=True, keep_requests=kept)
    req = kept[17]
    world = draw(req, req.seed, 1, deterministic=True)
    frozen = solve(req, world)
    corrected = solve(req, world, continuation=terminal_terms(req, forecast_all(req)))
    src = req.sources[0].id
    assert frozen.purchases.get((src, 0), 0.) < 300.
    assert corrected.purchases.get((src, 0), 0.) == pytest.approx(450., abs=1.)
    later = sorted(t for (s, t), q in corrected.purchases.items() if q > 1e-6)
    assert later[:3] == [0, 4, 9] or later[:3] == [0, 4, 8] or later[:3] == [0, 5, 9]


def test_p1_owned_review_reports_the_landed_terminal_and_p0_owned_review_does_not():
    rep = plan(_req("I_max_pallets_ftl_cap"))
    assert rep["orchestration"]["planner_owner"] == "PURCHASING_ECONOMICS"
    assert rep["orchestration"]["p1_terminal_landed"] == pytest.approx({"A": 5. + 1250. / 450.})
    off = plan(_req("I_max_pallets_ftl_cap").model_copy(update={"lot_terminal_valuation": False}))
    assert off["orchestration"]["p1_terminal_landed"] is None
    severe = build("I_max_pallets_ftl_cap", 41001, stresses="severe").model_copy(update=PRODUCT)
    rep_p0 = plan(severe)
    assert rep_p0["orchestration"]["planner_owner"] == "PROTECTION_RECOVERY"
    assert rep_p0["orchestration"]["p1_terminal_landed"] is None
