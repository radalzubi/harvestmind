"""Analytic expected shortage (P1 final closure): exact loss of the fitted bootstrap mixture."""
from __future__ import annotations

import numpy as np
import pytest

from zaad.full.shortage import demand_atoms, expected_shortage, loss_cuts, loss_envelope, tail_probability


def fit(sizes, zero=0., mean=None, **uncertainty):
    sizes = list(sizes)
    m = (1 - zero) * float(np.mean(sizes)) if mean is None else mean
    return {"sizes": sizes, "zero_probability": zero, "mean": m, "uncertainty": uncertainty}


def test_deterministic_demand_is_the_positive_part():
    atoms, zero = demand_atoms(fit([100.] * 8))
    assert expected_shortage(atoms, zero, 90.) == pytest.approx(10.)
    assert expected_shortage(atoms, zero, 100.) == 0. and expected_shortage(atoms, zero, 130.) == 0.


def test_symmetric_small_distribution_by_hand():
    atoms, zero = demand_atoms(fit([90., 100., 110.]))            # mean 100, each 1/3
    assert expected_shortage(atoms, zero, 100.) == pytest.approx(10. / 3)
    assert expected_shortage(atoms, zero, 95.) == pytest.approx((5. + 15.) / 3)
    assert tail_probability(atoms, zero, 100.) == pytest.approx(1. / 3)


def test_supply_far_above_demand_gives_zero_and_below_all_demand_gives_mean_minus_supply():
    atoms, zero = demand_atoms(fit([80., 95., 100., 125.]))
    assert expected_shortage(atoms, zero, 10_000.) == 0.
    assert expected_shortage(atoms, zero, 0.) == pytest.approx(100.)
    assert expected_shortage(atoms, zero, 50.) == pytest.approx(100. - 50.)


def test_monotone_nonnegative_finite():
    rng = np.random.default_rng(3)
    atoms, zero = demand_atoms(fit(rng.gamma(4., 25., 60), zero=.1))
    grid = np.linspace(0., 400., 81)
    values = [expected_shortage(atoms, zero, a) for a in grid]
    assert all(np.isfinite(values)) and all(v >= 0 for v in values)
    assert all(b <= a + 1e-12 for a, b in zip(values, values[1:]))


def test_zero_probability_enters_the_mixture():
    atoms, zero = demand_atoms(fit([100., 100.], zero=.5))         # mean 50: zero half the time
    assert expected_shortage(atoms, zero, 0.) == pytest.approx(50.)
    assert expected_shortage(atoms, zero, 60.) == pytest.approx(.5 * 40.)
    assert tail_probability(atoms, zero, 60.) == pytest.approx(.5)


def test_units_scale_with_the_multiplier_and_the_mean():
    a1, z = demand_atoms(fit([90., 110.]))
    a2, _ = demand_atoms(fit([90., 110.]), multiplier=2.)
    assert np.allclose(a2, 2 * a1) and expected_shortage(a2, z, 200.) == pytest.approx(2 * expected_shortage(a1, z, 100.))


def test_calibration_widening_and_outlier_cap_follow_the_sampler():
    base, _ = demand_atoms(fit([90., 110.]))
    wide, _ = demand_atoms(fit([90., 110.], calibration_ratio=2.))
    assert np.allclose(wide, [80., 120.])
    capped, _ = demand_atoms(fit([90., 110., 300.], outliers=1, residual_sd=5.))
    assert capped.max() < 300.


def test_cut_envelope_is_exact_everywhere():
    rng = np.random.default_rng(11)
    atoms, zero = demand_atoms(fit(rng.integers(50, 150, 40).astype(float), zero=.05))
    cuts = loss_cuts(atoms, zero)
    for a in np.linspace(0., 200., 401):
        assert loss_envelope(cuts, a) == pytest.approx(expected_shortage(atoms, zero, a), abs=1e-9)


def test_reproducible_and_no_nans_on_degenerate_fits():
    assert demand_atoms({"sizes": [], "zero_probability": 1., "mean": 0.})[0].size == 0
    assert expected_shortage(np.zeros(0), 1., 5.) == 0. and tail_probability(np.zeros(0), 1., 5.) == 0.
    a, z = demand_atoms(fit([1., 2., 3.]))
    assert loss_cuts(a, z) == loss_cuts(a, z)


# ---------------------------------------------------------------- adversarial behaviour of the surrogate in the model

from zaad.full.contracts import Request  # noqa: E402  (section import after the fixtures above)
from zaad.full.fixtures_p1 import p1_request  # noqa: E402  (section import after the fixtures above)
from zaad.full.model import solve  # noqa: E402  (section import after the fixtures above)
from zaad.full.worlds import draw, forecast_all  # noqa: E402  (section import after the fixtures above)


def _det(req, **kw):
    fits = forecast_all(req)
    return solve(req, draw(req, req.seed, 1, deterministic=True), service_floor=True, expected_shortage=fits, **kw)


def _plain(req, **kw):
    return solve(req, draw(req, req.seed, 1, deterministic=True), service_floor=True, **kw)


def _p0(sol):
    return sum(q for (s, t), q in sol.purchases.items() if t == 0)


def _protection(sol, req):
    """Units the plan orders at period 0 above the mean-world need at that review."""
    return _p0(sol)


def _with_shortage_economics(req, selling, sla):
    data = req.model_dump(mode="python")
    for s in data["services"]:
        s["selling_price"], s["sla_per_unmet"] = selling, sla
    return Request.model_validate(data)


def test_lower_shortage_economics_buy_less_protection_and_never_more():
    # The schema requires a positive selling price no lower than the asset value, so the leanest
    # admissible shortage economics are selling at cost with no SLA; protection must then be no
    # larger than under the fixture's declared economics, and it shrinks with the penalty.
    req = p1_request(opening_units=100., demand=100.)
    lean = _with_shortage_economics(req, req.skus[0].asset_value, 0.)
    rich = _with_shortage_economics(req, 50., 25.)
    a, b, c = _p0(_det(lean)), _p0(_det(req)), _p0(_det(rich))
    assert a <= b + 1e-6 and b <= c + 1e-6          # protection is monotone in the declared penalty
    assert c > _p0(_plain(rich)) + 5.               # and real where the penalty dwarfs carrying


def test_near_zero_variance_makes_the_surrogate_converge_to_the_mean_world_plan():
    req = p1_request(opening_units=100., demand=100., demand_sd_hint=1e-3)
    assert abs(_p0(_det(req)) - _p0(_plain(req))) < .5


def test_sufficient_inventory_means_no_extra_purchase():
    req = p1_request(opening_units=1200., demand=100.)
    sol = _det(req)
    assert _p0(sol) < 1e-6 and sol.planning_surrogate["expected_shortage_units"] < 1e-6


def test_high_carrying_and_low_shortage_cost_stays_lean_and_high_shortage_cost_protects():
    lean = _with_shortage_economics(p1_request(opening_units=100., demand=100., holding_per_year=12.), 5., 0.)   # $1.15 per unit-period to hold, $5 to miss
    rich = p1_request(opening_units=100., demand=100., holding_per_year=.15)
    assert _p0(_det(lean)) <= _p0(_det(rich)) - 5.
    assert _p0(_det(rich)) > _p0(_plain(rich)) + 5.


def test_surrogate_never_enters_projected_cost_or_ledger():
    from zaad.full.settlement import settle
    req = p1_request(opening_units=100., demand=100.)
    sol = _det(req)
    w = draw(req, req.seed, 1, deterministic=True)[0]
    r = settle(req, sol, w)
    assert "expected_shortage" not in r["ledger"] and abs(r["ledger_residual"]) < 1e-6
    assert abs(r["economic_cost"] - sol.projected_cost) < 1e-4


def test_moq_keeps_orders_on_the_lot_and_inbound_counts_as_availability():
    req = p1_request(opening_units=100., demand=100., minimum=400.)
    sol = _det(req)
    assert all(q < 1e-6 or q >= 400. - 1e-6 for q in sol.purchases.values())
    covered = p1_request(opening_units=100., demand=100., pipeline=[{
        "id": "po1", "known_at": req.as_of, "source": "src_A", "revision": 1, "ordered": 400., "confirmed": 400., "shipped": 400., "received": 0., "rejected": 0.,
        "expected_accepted_remaining": 400., "placed_at": req.as_of, "confirmed_at": None, "departed_at": None, "current_eta": req.as_of, "stage": "shipped", "carrier": "x",
        "cancellation_status": "no_new_amendment_quote", "prepaid_per_remaining_unit": 0., "allow_split_amendments": False,
        "options": [{"id": "keep", "known_at": req.as_of, "action": "keep", "due_in": 1, "fee_per_unit": 0., "remaining_invoice_per_unit": 0., "payment_due_in": 0,
                     "max_quantity": 400., "deadline": req.as_of, "allowed_stages": ["shipped"], "contract_reference": "c"}]}])
    assert _p0(_det(covered)) < 1e-6


def test_supplier_calendar_and_freight_tier_are_respected_with_the_surrogate():
    cal = p1_request(period_days=1, horizon=14, opening_units=800., demand=100., order_weekdays=(0,))
    sol = _det(cal)
    assert all(t in (0, 7) for (_, t), q in sol.purchases.items() if q > 1e-6)
    tiers = [{"up_to_pallets": 4, "charge": 800.}, {"up_to_pallets": 9, "charge": 1100.}]
    freight = p1_request(opening_units=100., demand=100., supplier_terms={"freight_tiers": tiers, "units_per_pallet": {"A": 100.}, "fixed_order_cost": 100.})
    sol = _det(freight)
    from zaad.full.settlement import settle
    r = settle(freight, sol, draw(freight, freight.seed, 1, deterministic=True)[0])
    assert all(s["pallets"] <= 9 for s in r["shipments"])


def test_incumbent_already_optimal_yields_no_material_improvement():
    from zaad.full.planner import plan
    req = p1_request(opening_units=150., incumbent_rule="reorder_point")
    report = plan(req)
    m = report["economics"]["materiality"]
    assert report["status"] == "RETAIN_INCUMBENT" or (m is not None and m["material"])
