"""Tests for the agronomy math.

The important ones verify the CLOSED FORMS against brute-force numerical
integration of the underlying sinusoid. That check is independent of any
citation: if the derivation is wrong, numerical integration disagrees.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy import stats

from agronomy.drought_index import (
    _as_inverse_normal,
    classify_spi,
    drought_severity_weight,
    fit_gamma_thom,
    spi,
    usdm_category_from_percentile,
)
from agronomy.forecast_skill import (
    SKILL_FLOOR,
    attenuate_effect,
    residual_variance_share,
    skill_model_for,
    skill_table,
    unresolved_weather_variance,
)
from agronomy.heat_exposure import (
    degree_days_above,
    fraction_of_day_below,
    growing_degree_days,
    saturation_vapor_pressure_kpa,
    season_exposure,
    time_in_bins,
    vapor_pressure_deficit_kpa,
)
from agronomy.shelf_life_kinetics import (
    heat_exposure_shelf_life_penalty,
    q10_to_activation_energy,
    rate_multiplier,
    shelf_life_at,
)
from agronomy.systemic_risk import (
    effective_independent_count,
    estimate_shock_correlation,
    implied_correlation_from_multiplier,
    portfolio_variance,
)


def _numeric_sinusoid_day(tmin, tmax, n=200_000):
    """Brute-force the within-day temperature trajectory."""
    t = np.linspace(0.0, 1.0, n, endpoint=False)
    mid, amp = (tmax + tmin) / 2.0, (tmax - tmin) / 2.0
    return mid + amp * np.sin(2 * np.pi * t)


class TestSinusoidClosedForms:
    """The closed forms must match numerical integration."""

    @pytest.mark.parametrize("tmin,tmax,thr", [
        (10.0, 30.0, 20.0), (15.0, 35.0, 32.0), (5.0, 25.0, 10.0),
        (20.0, 40.0, 29.0), (-2.0, 12.0, 4.0),
    ])
    def test_fraction_below_matches_numeric(self, tmin, tmax, thr):
        temps = _numeric_sinusoid_day(tmin, tmax)
        expected = float((temps <= thr).mean())
        got = float(fraction_of_day_below(np.array([tmin]), np.array([tmax]), thr)[0])
        assert got == pytest.approx(expected, abs=2e-3)

    @pytest.mark.parametrize("tmin,tmax,thr", [
        (10.0, 30.0, 20.0), (15.0, 35.0, 32.0), (20.0, 40.0, 29.0),
        (25.0, 33.0, 20.0),   # whole day above threshold
        (5.0, 15.0, 30.0),    # whole day below threshold
    ])
    def test_degree_days_above_matches_numeric(self, tmin, tmax, thr):
        temps = _numeric_sinusoid_day(tmin, tmax)
        expected = float(np.maximum(temps - thr, 0.0).mean())
        got = float(degree_days_above(np.array([tmin]), np.array([tmax]), thr)[0])
        assert got == pytest.approx(expected, abs=2e-3)

    def test_whole_day_above_reduces_to_mean_excess(self):
        # Threshold below Tmin: every hour counts, so DD == mean - threshold.
        got = float(degree_days_above(np.array([20.0]), np.array([30.0]), 10.0)[0])
        assert got == pytest.approx(15.0, abs=1e-9)

    def test_whole_day_below_is_zero(self):
        assert float(degree_days_above(np.array([5.0]), np.array([15.0]), 30.0)[0]) == 0.0

    def test_isothermal_day_does_not_divide_by_zero(self):
        # Tmin == Tmax: amplitude 0. Must not produce NaN.
        got = degree_days_above(np.array([20.0]), np.array([20.0]), 15.0)
        assert np.isfinite(got).all() and got[0] == pytest.approx(5.0)
        frac = fraction_of_day_below(np.array([20.0]), np.array([20.0]), 25.0)
        assert np.isfinite(frac).all()


class TestExposureVector:
    def test_time_in_bins_sums_to_number_of_days(self):
        tmin = np.array([10.0, 12.0, 8.0])
        tmax = np.array([30.0, 33.0, 25.0])
        _, days = time_in_bins(tmin, tmax)
        assert days.sum() == pytest.approx(3.0, abs=1e-6)

    def test_hot_day_puts_mass_in_hot_bins(self):
        edges, days = time_in_bins(np.array([25.0]), np.array([40.0]))
        hot = days[edges[:-1] >= 32.0].sum()
        assert hot > 0.1     # a real fraction of the day above 32 C


class TestGrowingDegreeDays:
    def test_two_conventions_diverge_when_tmin_below_base(self):
        """McMaster & Wilhelm's actual point: same equation, different answers."""
        tmin, tmax = np.array([2.0]), np.array([24.0])   # cold night, warm day
        cap_avg = float(growing_degree_days(tmin, tmax, 10.0, 30.0,
                                            "cap_then_average")[0])
        avg_floor = float(growing_degree_days(tmin, tmax, 10.0, 30.0,
                                              "average_then_floor")[0])
        assert cap_avg > avg_floor          # cap-then-average credits warm hours
        assert cap_avg == pytest.approx(7.0)
        assert avg_floor == pytest.approx(3.0)

    def test_conventions_agree_when_tmin_above_base(self):
        tmin, tmax = np.array([15.0]), np.array([25.0])
        a = float(growing_degree_days(tmin, tmax, 10.0, 30.0, "cap_then_average")[0])
        b = float(growing_degree_days(tmin, tmax, 10.0, 30.0, "average_then_floor")[0])
        assert a == pytest.approx(b)

    def test_single_sine_respects_cap(self):
        capped = float(growing_degree_days(np.array([20.0]), np.array([40.0]),
                                           10.0, 30.0, "single_sine")[0])
        uncapped = float(growing_degree_days(np.array([20.0]), np.array([40.0]),
                                             10.0, None, "single_sine")[0])
        assert capped < uncapped

    def test_unknown_method_raises(self):
        with pytest.raises(ValueError):
            growing_degree_days(np.array([10.0]), np.array([20.0]), method="bogus")


class TestVPD:
    def test_saturation_vapor_pressure_known_values(self):
        # Magnus/Tetens at 20 C is ~2.34 kPa; standard reference value.
        assert float(saturation_vapor_pressure_kpa(20.0)) == pytest.approx(2.34, abs=0.02)
        assert float(saturation_vapor_pressure_kpa(0.0)) == pytest.approx(0.611, abs=0.005)

    def test_vpd_zero_at_saturation(self):
        assert float(vapor_pressure_deficit_kpa(25.0, 100.0)) == pytest.approx(0.0)

    def test_vpd_rises_faster_than_linearly_with_temperature(self):
        """The compounding Lobell et al. identify: e* is exponential in T."""
        d20 = float(vapor_pressure_deficit_kpa(20.0, 50.0))
        d30 = float(vapor_pressure_deficit_kpa(30.0, 50.0))
        d40 = float(vapor_pressure_deficit_kpa(40.0, 50.0))
        assert (d40 - d30) > (d30 - d20)


class TestSeasonExposure:
    def test_evidence_grade_travels_with_result(self):
        tmin = np.full(30, 18.0)
        tmax = np.full(30, 34.0)
        corn = season_exposure(tmin, tmax, "corn")
        tomato = season_exposure(tmin, tmax, "tomato")
        assert corn["threshold_evidence"] == "estimated"
        assert tomato["threshold_evidence"] == "observed"
        assert corn["extreme_degree_days"] > 0

    def test_unknown_crop_falls_back_and_says_so(self):
        out = season_exposure(np.array([10.0]), np.array([20.0]), "durian")
        assert out["threshold_evidence"] == "default"

    def test_cool_season_has_no_extreme_degree_days(self):
        out = season_exposure(np.full(10, 8.0), np.full(10, 20.0), "tomato")
        assert out["extreme_degree_days"] == pytest.approx(0.0)
        assert out["beneficial_degree_days"] > 0


class TestForecastSkill:
    def test_rho_is_one_at_lead_zero(self):
        assert float(skill_model_for("temperature").rho(0)) == pytest.approx(1.0)

    def test_rho_hits_floor_at_published_horizon(self):
        m = skill_model_for("temperature")
        assert float(m.rho(m.horizon_days)) == pytest.approx(SKILL_FLOOR, abs=1e-9)

    def test_precipitation_decays_faster_than_temperature(self):
        """Documented asymmetry: precip skill collapses days sooner."""
        assert (float(skill_model_for("precipitation").rho(6))
                < float(skill_model_for("temperature").rho(6)))

    def test_monotonic_decay(self):
        m = skill_model_for("temperature")
        vals = [float(m.rho(d)) for d in range(0, 15)]
        assert all(a >= b for a, b in zip(vals, vals[1:]))

    def test_attenuation_shrinks_effect_toward_zero(self):
        near = attenuate_effect(-0.10, lead_days=1)
        far = attenuate_effect(-0.10, lead_days=7)
        assert abs(near["delta_applied"]) > abs(far["delta_applied"])
        assert abs(far["delta_applied"]) < abs(far["delta_measured"])

    def test_effect_retired_beyond_horizon(self):
        out = attenuate_effect(-0.10, lead_days=20)
        assert out["delta_applied"] == 0.0
        assert out["informative"] is False
        assert "climatology" in out["reason"]

    def test_lead_zero_applies_full_measured_effect(self):
        out = attenuate_effect(-0.0875, lead_days=0)
        assert out["delta_applied"] == pytest.approx(-0.0875)

    def test_sign_is_preserved(self):
        assert attenuate_effect(-0.1, 3)["delta_applied"] < 0
        assert attenuate_effect(0.1, 3)["delta_applied"] > 0

    def test_residual_variance_grows_with_lead(self):
        """Zero unresolved variance when weather is known; rises with lead."""
        assert residual_variance_share(0) == pytest.approx(0.0, abs=1e-9)
        assert residual_variance_share(1) < residual_variance_share(8)
        assert 0.0 <= residual_variance_share(20) <= 1.0

    def test_unresolved_weather_variance_zero_at_lead_zero(self):
        """A backtest replaying known weather adds no forecast uncertainty."""
        assert unresolved_weather_variance(-0.0875, 0) == pytest.approx(0.0, abs=1e-12)

    def test_unresolved_weather_variance_grows_with_lead(self):
        near = unresolved_weather_variance(-0.0875, 1)
        far = unresolved_weather_variance(-0.0875, 9)
        assert 0 < near < far

    def test_unresolved_variance_scales_with_effect_squared(self):
        small = unresolved_weather_variance(-0.05, 5)
        big = unresolved_weather_variance(-0.10, 5)
        assert big == pytest.approx(4.0 * small, rel=1e-9)

    def test_skill_table_covers_all_variables(self):
        rows = skill_table(10)
        assert len(rows) == 11
        assert {"temperature", "precipitation", "ensemble_mean"} <= set(rows[0])


class TestDroughtIndex:
    def test_as_approximation_matches_scipy(self):
        """The A&S constants must reproduce the exact inverse normal."""
        for p in (0.01, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99):
            assert _as_inverse_normal(p) == pytest.approx(
                float(stats.norm.ppf(p)), abs=5e-4)

    def test_gamma_fit_recovers_known_parameters(self):
        rng = np.random.default_rng(0)
        sample = rng.gamma(shape=2.0, scale=30.0, size=4000)
        alpha, beta, q = fit_gamma_thom(sample)
        assert alpha == pytest.approx(2.0, rel=0.15)
        assert beta == pytest.approx(30.0, rel=0.15)
        assert q == 0.0

    def test_spi_is_standardized(self):
        rng = np.random.default_rng(1)
        precip = rng.gamma(shape=2.0, scale=30.0, size=3000)
        z = spi(precip)
        assert float(np.mean(z)) == pytest.approx(0.0, abs=0.1)
        assert float(np.std(z)) == pytest.approx(1.0, abs=0.1)

    def test_dry_period_gives_negative_spi(self):
        rng = np.random.default_rng(2)
        climatology = rng.gamma(shape=2.0, scale=30.0, size=2000)
        dry = np.array([2.0])
        assert float(spi(dry, reference=climatology)[0]) < -1.0

    def test_zero_precipitation_handled(self):
        rng = np.random.default_rng(3)
        ref = np.concatenate([np.zeros(200), rng.gamma(2.0, 30.0, 800)])
        z = spi(np.array([0.0]), reference=ref)
        assert np.isfinite(z).all()

    def test_classification_boundaries(self):
        assert classify_spi(-2.5) == "extremely dry"
        assert classify_spi(-1.7) == "severely dry"
        assert classify_spi(0.0) == "near normal"
        assert classify_spi(2.5) == "extremely wet"

    def test_usdm_percentile_bands(self):
        assert usdm_category_from_percentile(1) == "D4"
        assert usdm_category_from_percentile(4) == "D3"
        assert usdm_category_from_percentile(8) == "D2"
        assert usdm_category_from_percentile(15) == "D1"
        assert usdm_category_from_percentile(25) == "D0"
        assert usdm_category_from_percentile(50) is None

    def test_severity_weight_is_monotone(self):
        cats = [None, "D0", "D1", "D2", "D3", "D4"]
        w = [drought_severity_weight(c) for c in cats]
        assert all(a < b for a, b in zip(w, w[1:]))


class TestSystemicRisk:
    def test_independence_reduces_variance_by_n(self):
        out = portfolio_variance(sigma=0.1, n_suppliers=10, rho=0.0)
        assert out["variance_correlated"] == pytest.approx(out["variance_independent"])
        assert out["risk_multiplier"] == pytest.approx(1.0)

    def test_correlation_creates_irreducible_floor(self):
        """The core claim: adding suppliers cannot remove systemic risk."""
        small = portfolio_variance(0.1, 10, 0.3)
        large = portfolio_variance(0.1, 1000, 0.3)
        assert large["variance_correlated"] < small["variance_correlated"]
        # but both stay above the floor sigma^2 * rho
        assert large["variance_correlated"] >= large["systemic_variance_floor"]
        assert large["variance_correlated"] == pytest.approx(
            large["systemic_variance_floor"], rel=0.05)

    def test_risk_multiplier_formula(self):
        out = portfolio_variance(0.1, 51, 0.2)
        assert out["risk_multiplier"] == pytest.approx(1 + 50 * 0.2)

    def test_miranda_glauber_range_implies_plausible_correlation(self):
        """20-50x at 100 suppliers should back out to a sane rho."""
        lo = implied_correlation_from_multiplier(20.0, 100)
        hi = implied_correlation_from_multiplier(50.0, 100)
        assert 0.15 < lo < 0.25
        assert 0.45 < hi < 0.55

    def test_effective_count_collapses_under_correlation(self):
        assert effective_independent_count(12, 0.0) == pytest.approx(12.0)
        assert effective_independent_count(12, 0.5) < 3.0

    def test_estimator_detects_independent_shocks(self):
        rng = np.random.default_rng(7)
        fills = rng.normal(0.9, 0.05, size=(60, 8))
        out = estimate_shock_correlation(fills)
        assert out["status"] == "ok"
        assert abs(out["mean_pairwise_correlation"]) < 0.2
        assert "little" in out["interpretation"] or "independent" in out["interpretation"]

    def test_estimator_detects_common_shock(self):
        """A shared regional shock must show up as high correlation."""
        rng = np.random.default_rng(8)
        common = rng.normal(0.0, 0.08, size=(60, 1))     # regional weather
        idio = rng.normal(0.0, 0.02, size=(60, 8))
        fills = 0.9 + common + idio
        out = estimate_shock_correlation(fills)
        assert out["mean_pairwise_correlation"] > 0.5
        assert out["effective_independent_suppliers"] < 3.0
        assert "CVaR" in out["interpretation"]

    def test_estimator_refuses_thin_data(self):
        assert estimate_shock_correlation(np.zeros((2, 2)))["status"] != "ok"


class TestShelfLifeKinetics:
    def test_q10_halves_shelf_life_per_10c(self):
        out = shelf_life_at(10.0, "lettuce")
        ref = out["reference_shelf_life_days"]
        # lettuce Q10 0-10 C is 2.65, so life should drop to ~1/2.65 of ref
        assert out["shelf_life_days"] == pytest.approx(ref / 2.65, rel=0.01)

    def test_warmer_is_always_shorter(self):
        cold = shelf_life_at(0.0, "lettuce")["shelf_life_days"]
        warm = shelf_life_at(15.0, "lettuce")["shelf_life_days"]
        assert warm < cold

    def test_shelf_life_strictly_monotonic_across_q10_boundary(self):
        """Regression: picking one Q10 for a span crossing 10 C made shelf
        life at 20 C come out LONGER than at 15 C. Rates must compose
        piecewise across the two tabulated ranges."""
        lives = [shelf_life_at(float(t), "lettuce")["shelf_life_days"]
                 for t in (0, 5, 10, 15, 20, 25)]
        assert all(a > b for a, b in zip(lives, lives[1:])), lives

    def test_piecewise_multiplier_composes_both_ranges(self):
        from agronomy.shelf_life_kinetics import (
            COMMODITY_KINETICS, rate_multiplier_piecewise,
        )
        spec = COMMODITY_KINETICS["lettuce"]
        # 0 -> 20 C crosses both ranges: Q10_cold^1 * Q10_warm^1
        expected = spec["q10_0_10c"] * spec["q10_10_20c"]
        assert rate_multiplier_piecewise(20.0, 0.0, "lettuce") == pytest.approx(expected)

    def test_piecewise_multiplier_inverts_when_cooling(self):
        from agronomy.shelf_life_kinetics import rate_multiplier_piecewise
        warm = rate_multiplier_piecewise(20.0, 0.0, "lettuce")
        cool = rate_multiplier_piecewise(0.0, 20.0, "lettuce")
        assert cool == pytest.approx(1.0 / warm)

    def test_rate_multiplier_identity_at_reference(self):
        assert rate_multiplier(10.0, 10.0, 2.5) == pytest.approx(1.0)

    def test_chilling_sensitive_commodity_warns(self):
        out = shelf_life_at(2.0, "tomato")
        assert "warning" in out

    def test_q10_to_activation_energy_in_published_range(self):
        """Q10 2-2.5 should map into the tens of kJ/mol."""
        ea = q10_to_activation_energy(2.2)
        assert 40_000 < ea < 80_000

    def test_heat_exposure_penalty_increases_with_ambient(self):
        cool = heat_exposure_shelf_life_penalty(np.full(7, 18.0), "lettuce")
        hot = heat_exposure_shelf_life_penalty(np.full(7, 35.0), "lettuce")
        assert hot["relative_deterioration"] > cool["relative_deterioration"]
        assert hot["shelf_life_retained_pct"] < cool["shelf_life_retained_pct"]

    def test_penalty_states_its_assumption(self):
        out = heat_exposure_shelf_life_penalty(np.full(5, 25.0))
        assert "assumption" in out

    def test_penalty_handles_empty_input(self):
        assert heat_exposure_shelf_life_penalty(np.array([]))["status"] == "no_data"
