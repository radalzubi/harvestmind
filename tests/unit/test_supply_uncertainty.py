"""Tests for the probabilistic supply-forecast layer.

Where possible these assert STATISTICAL PROPERTIES on controlled synthetic
data — conformal coverage actually reaching its nominal level, shrinkage
actually pulling sparse groups toward the population, copulas actually
preserving marginals — rather than pinning outputs to magic numbers.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import numpy as np
import pytest
from scipy import stats

from forecasting.supply_uncertainty import (
    ClimatologyModel,
    ConformalCalibrator,
    DataTier,
    ForecastValidationError,
    GradientBoostedQuantileModel,
    MondrianConformalCalibrator,
    PooledEmpiricalModel,
    ProbabilisticForecast,
    QuantityKind,
    classify_data_tier,
    conformal_quantile,
    conformity_scores,
    crps_sample,
    empirical_coverage,
    evaluate_forecasts,
    min_calibration_size,
    pinball_loss,
    pit_uniformity,
    rearrange,
    shrinkage_weight,
    split_time_aware,
    weighted_interval_score,
)
from risk.correlated_scenarios import (
    DEFAULT_SUPPLY_RISK_POLICY,
    CopulaScenarioGenerator,
    SupplyRiskPolicy,
    equicorrelation_matrix,
    estimate_rank_correlation,
    nearest_positive_semidefinite,
    pearson_to_spearman,
    recommended_shrinkage,
    shrink_correlation,
    spearman_to_pearson,
    validate_correlation_matrix,
)

NOW = datetime(2025, 6, 1, tzinfo=timezone.utc)
T0, T1 = date(2025, 6, 10), date(2025, 6, 16)


def _forecast(**over) -> ProbabilisticForecast:
    kw = dict(
        forecast_id="F1", issued_at=NOW, information_cutoff=NOW,
        target_start=T0, target_end=T1,
        entity_key={"supplier_id": "S1"},
        quantity_kind=QuantityKind.AVAILABLE_SUPPLY, unit="kg",
        quantiles={0.05: 50.0, 0.10: 60.0, 0.25: 80.0, 0.50: 100.0,
                   0.75: 120.0, 0.90: 140.0, 0.95: 150.0},
    )
    kw.update(over)
    return ProbabilisticForecast(**kw)


# ── Contract ────────────────────────────────────────────────────────────

class TestForecastContract:
    def test_valid_forecast_passes(self):
        _forecast().validate()

    def test_rejects_quantile_crossing(self):
        fc = _forecast(quantiles={0.10: 140.0, 0.50: 100.0, 0.90: 60.0})
        with pytest.raises(ForecastValidationError, match="crossing"):
            fc.validate()

    def test_rejects_negative_quantity(self):
        with pytest.raises(ForecastValidationError, match="negative"):
            _forecast(quantiles={0.10: -1.0, 0.50: 10.0, 0.90: 20.0}).validate()

    def test_rejects_nan_and_inf(self):
        for bad in (float("nan"), float("inf")):
            with pytest.raises(ForecastValidationError, match="finite"):
                _forecast(quantiles={0.10: 1.0, 0.50: bad, 0.90: 3.0}).validate()

    def test_rejects_cutoff_after_issue(self):
        """The core leakage invariant at contract level."""
        with pytest.raises(ForecastValidationError, match="after"):
            _forecast(information_cutoff=NOW + timedelta(days=1)).validate()

    def test_rejects_training_cutoff_after_information_cutoff(self):
        with pytest.raises(ForecastValidationError, match="training_cutoff"):
            _forecast(training_cutoff=date(2025, 12, 31)).validate()

    def test_rejects_inverted_target_window(self):
        with pytest.raises(ForecastValidationError, match="precedes"):
            _forecast(target_start=T1, target_end=T0).validate()

    def test_uncalibrated_forecast_is_labelled(self):
        fc = _forecast()
        fc.validate()
        assert any("uncalibrated" in w for w in fc.warnings)

    def test_horizon_and_interval_helpers(self):
        fc = _forecast()
        assert fc.horizon_days == (T0 - NOW.date()).days
        lo, hi = fc.interval(0.80)
        assert (lo, hi) == (60.0, 140.0)
        assert fc.median == 100.0
        assert fc.relative_width == pytest.approx(0.8)

    def test_serialization_is_deterministic_and_json_safe(self):
        import json
        d1 = _forecast().to_dict()
        d2 = _forecast().to_dict()
        assert json.dumps(d1) == json.dumps(d2)
        assert list(d1) == sorted(d1)
        assert d1["quantiles"]["q50"] == 100.0

    def test_rearrange_fixes_crossing_and_preserves_values(self):
        out = rearrange({0.1: 140.0, 0.5: 100.0, 0.9: 60.0})
        assert list(out.values()) == [60.0, 100.0, 140.0]
        assert sorted(out.values()) == sorted([140.0, 100.0, 60.0])

    def test_rejects_negative_samples(self):
        with pytest.raises(ForecastValidationError, match="negative"):
            _forecast(samples=[1.0, -2.0]).validate()


# ── Data tiers and pooling ──────────────────────────────────────────────

class TestDataTiers:
    def test_seasons_drive_the_tier(self):
        assert classify_data_tier(1000, n_seasons=0) == DataTier.NONE
        assert classify_data_tier(1000, n_seasons=1) == DataTier.SINGLE_SEASON
        assert classify_data_tier(1000, n_seasons=3) == DataTier.SPARSE
        assert classify_data_tier(1000, n_seasons=5) == DataTier.ADEQUATE
        assert classify_data_tier(1000, n_seasons=10) == DataTier.RICH

    def test_row_count_alone_never_claims_more_than_sparse(self):
        """200 rows from one season say nothing about year-to-year variation."""
        assert classify_data_tier(200, n_seasons=None) == DataTier.SPARSE

    def test_shrinkage_weight_bounds(self):
        assert shrinkage_weight(0, 1.0, 1.0) == 0.0
        assert 0 < shrinkage_weight(3, 1.0, 1.0) < 1
        assert shrinkage_weight(1000, 1.0, 1.0) > 0.99

    def test_zero_between_variance_gives_no_weight_to_group(self):
        assert shrinkage_weight(10, 1.0, 0.0) == 0.0


class TestPooledEmpiricalModel:
    @staticmethod
    def _groups():
        rng = np.random.default_rng(0)
        g = {f"S{i}": rng.normal(0.85 + 0.02 * i, 0.08, size=40)
             for i in range(6)}
        g["SPARSE"] = np.array([0.90, 0.905, 0.895])   # 3 near-identical obs
        return g

    def test_sparse_group_is_not_given_a_narrow_interval(self):
        """The trap this model exists to avoid.

        SPARSE has three observations spanning under 1%. A naive empirical
        quantile would hand back a ~1%-wide interval and the optimizer
        would commit against it. Pooling must keep it comparably wide to
        the data-rich groups.
        """
        m = PooledEmpiricalModel().fit(self._groups())
        sparse = m.predict("SPARSE", {"k": "SPARSE"}, T0, T1)
        rich = m.predict("S0", {"k": "S0"}, T0, T1)
        naive_width = 0.905 - 0.895
        sparse_width = sparse.quantiles[0.95] - sparse.quantiles[0.05]
        assert sparse_width > 10 * naive_width
        assert sparse_width >= rich.quantiles[0.95] - rich.quantiles[0.05]

    def test_variance_is_pooled_not_just_the_mean(self):
        """Regression: shrinking only the mean left a real hole.

        A 3-observation group whose points happened to land within 1% got a
        near-zero sample variance, so the classical weight
        n/(n + within/between) read that as high precision and gave the
        group 0.99 weight on its own data — reproducing the exact falsely
        narrow interval the pooling exists to prevent. The variance
        estimate must itself be pooled on its degrees of freedom.
        """
        from forecasting.supply_uncertainty.baseline import pooled_within_variance

        tight = np.array([0.90, 0.905, 0.895])     # sample var ~2.5e-5
        pop_var = 0.0064                            # population var (sd 0.08)
        pooled = pooled_within_variance(tight, pop_var)
        assert pooled > 10 * float(np.var(tight, ddof=1))
        assert pooled < pop_var          # but still moves toward the group
        # A data-rich group keeps its own variance.
        rich = np.random.default_rng(0).normal(0.9, 0.01, 200)
        assert pooled_within_variance(rich, pop_var) < 0.1 * pop_var

    def test_unseen_group_falls_back_to_population(self):
        m = PooledEmpiricalModel().fit(self._groups())
        fc = m.predict("NEVER_SEEN", {"k": "x"}, T0, T1)
        assert fc.data_tier == DataTier.NONE
        assert fc.n_observations == 0
        assert "no history" in (fc.fallback_reason or "")
        fc.validate()

    def test_rich_group_keeps_its_own_mean(self):
        rng = np.random.default_rng(1)
        groups = {f"S{i}": rng.normal(0.80, 0.05, 60) for i in range(5)}
        groups["HIGH"] = rng.normal(0.95, 0.02, 200)
        m = PooledEmpiricalModel().fit(groups)
        fc = m.predict("HIGH", {"k": "HIGH"}, T0, T1)
        # Heavy data -> shrinkage is mild, median stays near its own mean.
        assert fc.median > 0.90

    def test_scale_converts_fraction_to_quantity(self):
        m = PooledEmpiricalModel().fit(self._groups())
        frac = m.predict("S0", {"k": "S0"}, T0, T1)
        qty = m.predict("S0", {"k": "S0"}, T0, T1, scale=1000.0)
        assert qty.median == pytest.approx(frac.median * 1000.0)

    def test_all_outputs_validate(self):
        m = PooledEmpiricalModel().fit(self._groups())
        for k in list(self._groups()) + ["UNSEEN"]:
            m.predict(k, {"k": k}, T0, T1).validate()


class TestClimatology:
    def test_falls_back_when_period_too_thin(self):
        rng = np.random.default_rng(2)
        vals = rng.normal(100, 20, 200)
        periods = rng.integers(1, 53, 200)
        clim = ClimatologyModel().fit(vals, periods)
        q = clim.quantiles_for(999)          # a period never observed
        assert q[0.50] == pytest.approx(float(np.quantile(vals, 0.50)), rel=0.1)


# ── Conformal calibration ───────────────────────────────────────────────

class TestConformal:
    def test_conformity_score_sign(self):
        # inside the interval -> negative; outside -> positive
        s = conformity_scores(np.array([5.0, 15.0]), np.array([0.0, 0.0]),
                              np.array([10.0, 10.0]))
        assert s[0] < 0 and s[1] > 0

    def test_finite_sample_correction_needs_enough_points(self):
        """alpha=0.1 needs n>=9; below that we must refuse, not under-cover."""
        assert min_calibration_size(0.10) == 9
        assert not np.isfinite(conformal_quantile(np.arange(5.0), 0.10))
        assert np.isfinite(conformal_quantile(np.arange(50.0), 0.10))

    def test_calibration_achieves_nominal_coverage(self):
        """The property the whole method exists for.

        Start from a deliberately over-confident interval (far too narrow),
        calibrate, and check coverage climbs to the nominal 90%.
        """
        rng = np.random.default_rng(3)
        y_cal = rng.normal(100, 20, 500)
        lo_cal, hi_cal = np.full(500, 98.0), np.full(500, 102.0)  # ~8% coverage
        cal = ConformalCalibrator(alpha=0.10).fit(y_cal, lo_cal, hi_cal)
        assert cal.fitted

        y_test = rng.normal(100, 20, 2000)
        lo, hi = cal.apply(np.full(2000, 98.0), np.full(2000, 102.0))
        cov = empirical_coverage(y_test, lo, hi)
        assert 0.86 < cov < 0.94, f"coverage {cov} not near nominal 0.90"

    def test_correction_can_tighten_an_overwide_interval(self):
        """A negative correction is correct behaviour, not a bug."""
        rng = np.random.default_rng(4)
        y = rng.normal(100, 5, 400)
        cal = ConformalCalibrator(alpha=0.10).fit(
            y, np.full(400, 0.0), np.full(400, 200.0))
        assert cal.correction < 0

    def test_lower_bound_floored_at_zero(self):
        cal = ConformalCalibrator(alpha=0.10)
        cal.fitted, cal.correction = True, 50.0
        lo, _ = cal.apply(np.array([10.0]), np.array([20.0]))
        assert lo[0] == 0.0

    def test_insufficient_data_is_flagged_not_faked(self):
        cal = ConformalCalibrator(alpha=0.10).fit(
            np.arange(4.0), np.zeros(4), np.ones(4))
        assert cal.insufficient_data and not cal.fitted
        # apply() is then a no-op rather than a wrong correction
        lo, hi = cal.apply(np.array([1.0]), np.array([2.0]))
        assert (lo[0], hi[0]) == (1.0, 2.0)

    def test_mondrian_gives_per_group_corrections(self):
        """Marginal coverage can hide a badly under-covered group."""
        rng = np.random.default_rng(5)
        n = 400
        groups = np.array(["tight"] * n + ["wide"] * n)
        y = np.concatenate([rng.normal(100, 2, n), rng.normal(100, 30, n)])
        lo = np.full(2 * n, 98.0)
        hi = np.full(2 * n, 102.0)
        cal = MondrianConformalCalibrator(alpha=0.10).fit(y, lo, hi, groups)
        assert cal.correction_for("wide") > cal.correction_for("tight")

    def test_small_group_falls_back_to_pooled(self):
        rng = np.random.default_rng(6)
        groups = np.array(["big"] * 100 + ["tiny"] * 3)
        y = rng.normal(10, 2, 103)
        cal = MondrianConformalCalibrator(alpha=0.10).fit(
            y, np.full(103, 9.0), np.full(103, 11.0), groups)
        assert "tiny" in cal.fallback_groups
        assert np.isfinite(cal.correction_for("tiny"))

    def test_time_aware_split_is_chronological(self):
        """A random split would leak the future into calibration."""
        train, cal = split_time_aware(100, 0.3)
        assert train.max() < cal.min()
        assert cal.size == 30


# ── Quantile model ──────────────────────────────────────────────────────

class TestQuantileModel:
    @staticmethod
    def _data(n=400, seed=7):
        rng = np.random.default_rng(seed)
        x = np.linspace(0, 10, n).reshape(-1, 1)
        # Heteroscedastic: spread grows with x, so intervals must widen.
        y = 50 + 5 * x[:, 0] + rng.normal(0, 1 + x[:, 0], n)
        return x, np.maximum(y, 0.0)

    def test_requires_time_sorted_input(self):
        """Guard against silently calibrating on a random subset."""
        x, y = self._data()
        with pytest.raises(ValueError, match="sorted oldest-first"):
            GradientBoostedQuantileModel(force_linear=True).fit(
                x, y, sorted_by_time=False)

    def test_quantiles_are_monotone(self):
        x, y = self._data()
        m = GradientBoostedQuantileModel(force_linear=True).fit(x, y)
        preds, _ = m.predict_quantiles(x)
        levels = sorted(preds)
        stacked = np.vstack([preds[lv] for lv in levels])
        assert np.all(np.diff(stacked, axis=0) >= -1e-9)

    def test_predictions_are_nonnegative(self):
        x, y = self._data()
        m = GradientBoostedQuantileModel(force_linear=True).fit(x, y)
        preds, _ = m.predict_quantiles(x)
        assert all((p >= 0).all() for p in preds.values())

    def test_intervals_widen_with_heteroscedastic_noise(self):
        x, y = self._data(n=600)
        m = GradientBoostedQuantileModel(force_linear=True).fit(x, y)
        preds, _ = m.predict_quantiles(x)
        width = preds[0.95] - preds[0.05]
        assert width[-50:].mean() > width[:50].mean()

    def test_predict_one_returns_valid_contract(self):
        x, y = self._data()
        m = GradientBoostedQuantileModel(force_linear=True).fit(
            x, y, training_cutoff=date(2025, 5, 1))
        fc = m.predict_one(
            x[-1], {"supplier_id": "S1"}, T0, T1,
            information_cutoff=NOW, n_observations=len(y), n_seasons=5)
        fc.validate()
        assert fc.data_tier == DataTier.ADEQUATE
        assert fc.model_family == "lgbm_quantile_cqr"
        assert fc.calibrated is True

    def test_tiny_dataset_reports_uncalibrated_rather_than_lying(self):
        x, y = self._data(n=8)
        m = GradientBoostedQuantileModel(force_linear=True).fit(x, y)
        fc = m.predict_one(x[-1], {"s": 1}, T0, T1, information_cutoff=NOW,
                           n_observations=8, n_seasons=1)
        assert fc.calibrated is False
        assert fc.data_tier == DataTier.SINGLE_SEASON
        assert any("uncalibrated" in w for w in fc.warnings)


# ── Scoring rules ───────────────────────────────────────────────────────

class TestScoringRules:
    def test_pinball_is_minimised_at_the_true_quantile(self):
        """A proper score: optimised by reporting the truth."""
        rng = np.random.default_rng(8)
        y = rng.normal(0, 1, 20000)
        for lv in (0.1, 0.5, 0.9):
            truth = float(np.quantile(y, lv))
            best = pinball_loss(y, np.full(y.size, truth), lv)
            for off in (-0.5, -0.2, 0.2, 0.5):
                assert pinball_loss(y, np.full(y.size, truth + off), lv) >= best

    def test_pinball_asymmetry_matches_level(self):
        y = np.array([10.0])
        # At tau=0.9 under-predicting must hurt more than over-predicting.
        assert pinball_loss(y, np.array([8.0]), 0.9) > pinball_loss(
            y, np.array([12.0]), 0.9)

    def test_crps_zero_for_a_perfect_point_forecast(self):
        assert crps_sample(5.0, np.array([5.0] * 100)) == pytest.approx(0.0)

    def test_crps_rewards_the_better_ensemble(self):
        rng = np.random.default_rng(9)
        good = rng.normal(10, 1, 2000)
        bad = rng.normal(14, 1, 2000)
        assert crps_sample(10.0, good) < crps_sample(10.0, bad)

    def test_fair_crps_is_less_biased_by_ensemble_size(self):
        """The naive 2M^2 form flatters small ensembles."""
        rng = np.random.default_rng(10)
        big = crps_sample(0.0, rng.normal(0, 1, 5000), fair=True)
        small_fair = np.mean([crps_sample(0.0, rng.normal(0, 1, 12), fair=True)
                              for _ in range(400)])
        small_naive = np.mean([crps_sample(0.0, rng.normal(0, 1, 12), fair=False)
                               for _ in range(400)])
        assert abs(small_fair - big) < abs(small_naive - big)

    def test_wis_prefers_calibrated_over_overconfident(self):
        rng = np.random.default_rng(11)
        y = rng.normal(100, 10, 1000)
        good = {0.05: np.full(1000, 100 - 1.645 * 10),
                0.25: np.full(1000, 100 - 0.674 * 10),
                0.50: np.full(1000, 100.0),
                0.75: np.full(1000, 100 + 0.674 * 10),
                0.95: np.full(1000, 100 + 1.645 * 10)}
        narrow = {lv: np.full(1000, 100.0) + (v - 100.0) * 0.15
                  for lv, v in good.items()}
        assert weighted_interval_score(y, good) < weighted_interval_score(y, narrow)

    def test_coverage_and_tail_reported(self):
        rng = np.random.default_rng(12)
        y = rng.normal(0, 1, 4000)
        preds = {lv: np.full(4000, float(stats.norm.ppf(lv)))
                 for lv in (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95)}
        out = evaluate_forecasts(y, preds)
        assert out["coverage"]["90%"] == pytest.approx(0.90, abs=0.03)
        assert out["lower_tail_coverage_p05"] == pytest.approx(0.05, abs=0.02)

    def test_pit_diagnoses_overconfidence(self):
        """A U-shaped PIT means intervals are too narrow."""
        rng = np.random.default_rng(13)
        y = rng.normal(0, 1, 600)
        samples = rng.normal(0, 0.2, size=(600, 200))   # far too sharp
        out = pit_uniformity(
            np.array([float((samples[i] <= y[i]).mean()) for i in range(600)]))
        assert "too narrow" in out["shape"]

    def test_pit_recognises_good_calibration(self):
        rng = np.random.default_rng(14)
        y = rng.normal(0, 1, 800)
        samples = rng.normal(0, 1, size=(800, 300))
        out = pit_uniformity(
            np.array([float((samples[i] <= y[i]).mean()) for i in range(800)]))
        assert "well calibrated" in out["shape"]


# ── Copula scenario generation ──────────────────────────────────────────

class TestCopulaScenarios:
    def test_spearman_pearson_identity_round_trips(self):
        """rho_p = 2 sin(pi rho_s / 6), the Gaussian-copula identity."""
        for rs in (-0.8, -0.3, 0.0, 0.25, 0.6, 0.9):
            assert pearson_to_spearman(spearman_to_pearson(rs)) == pytest.approx(
                rs, abs=1e-9)

    def test_identity_matches_closed_form(self):
        assert spearman_to_pearson(0.5) == pytest.approx(
            2 * np.sin(np.pi * 0.5 / 6), rel=1e-12)

    def test_marginals_preserved_exactly(self):
        """The point of a copula: change dependence, not the marginals."""
        params = {"A": (8.0, 2.0), "B": (5.0, 5.0), "C": (2.0, 8.0)}
        gen = CopulaScenarioGenerator(copula="gaussian", seed=1)
        draws = gen.sample_beta_marginals(params, 20000, latent_rho=0.6)
        for key, (a, b) in params.items():
            assert draws[key].mean() == pytest.approx(a / (a + b), abs=0.02)
            assert float(np.quantile(draws[key], 0.10)) == pytest.approx(
                float(stats.beta.ppf(0.10, a, b)), abs=0.03)

    def test_target_latent_correlation_is_induced(self):
        """Tolerance deliberately tight.

        This assertion previously used abs=0.08 against a Spearman target
        passed straight in as the latent parameter — slack enough that the
        missing rank-to-latent conversion still passed. It now checks the
        LATENT parameter round-trips through the Gaussian identity, at a
        tolerance that would catch that defect.
        """
        params = {"A": (8.0, 2.0), "B": (8.0, 2.0)}
        gen = CopulaScenarioGenerator(copula="gaussian", seed=2)
        for latent in (0.0, 0.5, 0.85):
            d = gen.sample_beta_marginals(
                params, 40000, correlation=equicorrelation_matrix(2, latent))
            got_s, _ = stats.spearmanr(d["A"], d["B"])
            expected_s = float(pearson_to_spearman(latent))
            assert got_s == pytest.approx(expected_s, abs=0.02)

    def test_correlated_draws_do_not_average_away(self):
        """The whole reason this module exists.

        Independent supplier shortfalls cancel across a portfolio, making
        aggregate supply look tight. Correlated ones stack. The aggregate
        standard deviation must therefore be materially larger.
        """
        params = {f"S{i}": (8.0, 2.0) for i in range(10)}
        gen = CopulaScenarioGenerator(copula="gaussian", seed=3)
        indep = gen.sample_beta_marginals(params, 5000, latent_rho=0.0)
        corr = gen.sample_beta_marginals(params, 5000, latent_rho=0.6)
        sd_i = np.mean(np.vstack(list(indep.values())), axis=0).std()
        sd_c = np.mean(np.vstack(list(corr.values())), axis=0).std()
        assert sd_c > 2.0 * sd_i

    def test_t_copula_has_more_joint_tail_mass_than_gaussian(self):
        """Gaussian copulas have ZERO tail dependence; t copulas do not.

        Joint severe shortfalls are exactly the scenario a perishable buyer
        must plan for, so this difference is the reason t is the default.
        """
        params = {"A": (8.0, 2.0), "B": (8.0, 2.0)}
        corr = equicorrelation_matrix(2, 0.6)
        g = CopulaScenarioGenerator(copula="gaussian", seed=4).sample_beta_marginals(
            params, 40000, correlation=corr)
        t = CopulaScenarioGenerator(copula="t", df=3.0, seed=4).sample_beta_marginals(
            params, 40000, correlation=corr)
        qg = np.quantile(g["A"], 0.05), np.quantile(g["B"], 0.05)
        qt = np.quantile(t["A"], 0.05), np.quantile(t["B"], 0.05)
        joint_g = float(((g["A"] <= qg[0]) & (g["B"] <= qg[1])).mean())
        joint_t = float(((t["A"] <= qt[0]) & (t["B"] <= qt[1])).mean())
        assert joint_t > joint_g

    def test_draws_are_deterministic_under_seed(self):
        params = {"A": (8.0, 2.0), "B": (5.0, 5.0)}
        a = CopulaScenarioGenerator(seed=99).sample_beta_marginals(params, 500, latent_rho=0.4)
        b = CopulaScenarioGenerator(seed=99).sample_beta_marginals(params, 500, latent_rho=0.4)
        for k in params:
            assert np.allclose(a[k], b[k])

    def test_draws_are_valid_fractions(self):
        params = {f"S{i}": (2.0, 5.0) for i in range(4)}
        d = CopulaScenarioGenerator(copula="t", df=3, seed=5).sample_beta_marginals(
            params, 3000, latent_rho=0.5)
        for v in d.values():
            assert np.all((v >= 0.0) & (v <= 1.0)) and np.all(np.isfinite(v))

    def test_indefinite_matrix_is_repaired(self):
        bad = np.array([[1.0, 0.99, -0.99], [0.99, 1.0, 0.99], [-0.99, 0.99, 1.0]])
        fixed = nearest_positive_semidefinite(bad)
        assert np.all(np.linalg.eigvalsh(fixed) > 0)
        np.linalg.cholesky(fixed)          # must not raise
        assert np.allclose(np.diag(fixed), 1.0)


class TestCorrelationValidation:
    """Every correlation matrix must be checked before it is used."""

    def test_valid_matrix_passes_all_checks(self):
        v = validate_correlation_matrix(equicorrelation_matrix(4, 0.4))
        assert v["valid"] and v["symmetric"] and v["unit_diagonal"]
        assert v["in_range"] and v["positive_semidefinite"]
        assert v["min_eigenvalue"] > 0

    def test_detects_asymmetry(self):
        m = np.array([[1.0, 0.5], [0.2, 1.0]])
        v = validate_correlation_matrix(m)
        assert not v["symmetric"] and not v["valid"]
        assert v["max_asymmetry"] == pytest.approx(0.3)

    def test_detects_non_unit_diagonal(self):
        m = np.array([[0.9, 0.1], [0.1, 1.0]])
        assert not validate_correlation_matrix(m)["unit_diagonal"]

    def test_detects_indefiniteness(self):
        bad = np.array([[1.0, 0.99, -0.99], [0.99, 1.0, 0.99], [-0.99, 0.99, 1.0]])
        v = validate_correlation_matrix(bad)
        assert not v["positive_semidefinite"] and v["min_eigenvalue"] < 0
        assert validate_correlation_matrix(
            nearest_positive_semidefinite(bad))["valid"]

    def test_detects_out_of_range_and_nonfinite(self):
        assert not validate_correlation_matrix(
            np.array([[1.0, 1.5], [1.5, 1.0]]))["in_range"]
        assert not validate_correlation_matrix(
            np.array([[1.0, np.nan], [np.nan, 1.0]]))["finite"]

    def test_rejects_non_square(self):
        assert not validate_correlation_matrix(np.zeros((2, 3)))["square"]

    def test_shrinkage_moves_toward_target_and_stays_valid(self):
        rng = np.random.default_rng(0)
        noisy = np.clip(rng.uniform(-0.9, 0.9, (5, 5)), -1, 1)
        noisy = (noisy + noisy.T) / 2
        np.fill_diagonal(noisy, 1.0)
        shrunk = shrink_correlation(noisy, target_rho=0.0, weight=0.8)
        off_before = np.abs(noisy[~np.eye(5, dtype=bool)]).mean()
        off_after = np.abs(shrunk[~np.eye(5, dtype=bool)]).mean()
        assert off_after < off_before
        assert np.allclose(np.diag(shrunk), 1.0)

    def test_shrinkage_weight_rises_as_history_thins(self):
        """k suppliers imply k(k-1)/2 correlations from the same n weeks."""
        thin = recommended_shrinkage(n_periods=5, n_entities=8)
        thick = recommended_shrinkage(n_periods=200, n_entities=8)
        assert thin > thick
        assert 0.1 <= thick <= thin <= 0.9
        # 6 suppliers (15 pairs) over 10 weeks -> mostly discard the estimate
        assert recommended_shrinkage(10, 6) == pytest.approx(15 / 25, abs=1e-9)


class TestSupplyRiskPolicy:
    """Correlated sampling must be an explicit, recorded decision."""

    def test_default_policy_is_independent(self):
        """A judgement-based copula must not be the silent default."""
        assert DEFAULT_SUPPLY_RISK_POLICY.mode == "independent"
        assert DEFAULT_SUPPLY_RISK_POLICY.enabled is False
        assert "UNDERSTATED" in DEFAULT_SUPPLY_RISK_POLICY.describe()

    def test_equicorrelated_requires_explicit_rho(self):
        with pytest.raises(ValueError, match="requires an explicit"):
            SupplyRiskPolicy(mode="equicorrelated")

    def test_rejects_unknown_mode_and_copula(self):
        with pytest.raises(ValueError, match="unknown supply-risk mode"):
            SupplyRiskPolicy(mode="magic")
        with pytest.raises(ValueError, match="unknown copula"):
            SupplyRiskPolicy(mode="estimated", copula="clayton")

    def test_enabled_policies_describe_themselves(self):
        p = SupplyRiskPolicy(mode="equicorrelated", kendall_tau=0.4, copula="t")
        assert p.enabled and "t copula" in p.describe()
        q = SupplyRiskPolicy(mode="estimated", copula="gaussian")
        assert q.enabled and "estimated" in q.describe()

    def test_scenario_generation_ignores_policy_when_none(self):
        """Without a policy the sampler must not import the copula path."""
        import inspect

        from risk.scenario_generation import yield_scenarios_from_distributions
        src = inspect.getsource(yield_scenarios_from_distributions)
        assert "supply_risk_policy is not None" in src
        assert "correlated=True" not in src

    def test_thin_overlap_defaults_rather_than_inventing_correlation(self):
        obs = {"A": np.array([0.9, 0.8, np.nan, np.nan]),
               "B": np.array([np.nan, np.nan, 0.7, 0.6])}
        mat, keys, diag = estimate_rank_correlation(obs, min_overlap=4)
        assert mat[0, 1] == 0.0
        assert diag["pairs_defaulted"] == 1

    def test_leakage_guard_fails_closed_on_missing_column(self):
        """Regression: assert_dates_in_window returned early when the date
        column was absent, so a renamed column turned the guard into a
        no-op that REPORTED SUCCESS — the worst failure mode for a leakage
        check, because the caller believes it ran."""
        import pandas as pd

        from backtesting.leakage_guard import LeakageError, assert_dates_in_window

        df = pd.DataFrame({"delivery_week": ["2024-01-08"], "qty": [1.0]})
        with pytest.raises(LeakageError, match="not present"):
            assert_dates_in_window(df, "week_start", date(2024, 1, 1),
                                   date(2024, 1, 31))
        # An empty frame is still fine: no rows to leak differs from being
        # unable to look.
        assert_dates_in_window(pd.DataFrame({"week_start": []}), "week_start",
                               date(2024, 1, 1), date(2024, 1, 31))

    def test_estimates_correlation_when_history_supports_it(self):
        rng = np.random.default_rng(15)
        common = rng.normal(0, 1, 40)
        obs = {"A": 0.9 + 0.05 * common + 0.01 * rng.normal(0, 1, 40),
               "B": 0.9 + 0.05 * common + 0.01 * rng.normal(0, 1, 40)}
        mat, _, diag = estimate_rank_correlation(obs, min_overlap=4)
        assert mat[0, 1] > 0.7
        assert diag["pairs_estimated"] == 1


# ── Policy branches on a real (in-memory) database ──────────────────────

class TestPolicyBranchesEndToEnd:
    """Exercise correlated_yield_scenarios' decision paths against DuckDB.

    Every branch must report WHICH dependence assumption it used, because a
    plan is only auditable if the assumption behind it is recoverable.
    """

    @staticmethod
    def _conn(n_weeks: int = 30, n_suppliers: int = 4, seed: int = 0):
        import duckdb

        root = __import__("pathlib").Path(__file__).resolve().parents[2]
        c = duckdb.connect(":memory:")
        for sql in sorted((root / "db" / "migrations").glob("*.sql")):
            c.execute(sql.read_text())
        import pandas as pd

        rng = np.random.default_rng(seed)
        common = rng.normal(0, 1, n_weeks)
        # Genuinely distinct calendar weeks — packing days into a month
        # collapses them under DATE_TRUNC('week') and the estimator would
        # (correctly) refuse for lack of joint periods.
        weeks = pd.date_range("2024-01-01", periods=n_weeks, freq="7D")
        rows = []
        for s in range(n_suppliers):
            for w in range(n_weeks):
                fill = float(np.clip(0.88 + 0.05 * common[w]
                                     + 0.02 * rng.normal(), 0.2, 1.0))
                ordered = 500.0
                rows.append((f"D-{s}-{w}", f"S{s}", f"S{s}", "P1", "Tomato",
                             weeks[w].date().isoformat(),
                             ordered, ordered * fill, ordered * fill))
        c.executemany(
            "INSERT INTO stg_supplier_deliveries (delivery_id, supplier_id,"
            " supplier_name, product_id, product_name, delivery_date,"
            " ordered_quantity, delivered_quantity, accepted_quantity)"
            " VALUES (?,?,?,?,?,?,?,?,?)", rows)
        return c

    def test_independent_policy_reports_understatement(self):
        from risk.correlated_scenarios import correlated_yield_scenarios

        conn = self._conn()
        draws, diag = correlated_yield_scenarios(
            conn, list(range(20)), policy=SupplyRiskPolicy(mode="independent"))
        assert diag["policy_mode"] == "independent"
        assert "UNDERSTATED" in diag["policy_description"]
        assert diag["mean_latent_correlation"] == 0.0
        assert len(draws) == 20 * 4

    def test_equicorrelated_policy_uses_supplied_rho(self):
        from risk.correlated_scenarios import correlated_yield_scenarios

        conn = self._conn()
        _, diag = correlated_yield_scenarios(
            conn, list(range(20)),
            policy=SupplyRiskPolicy(mode="equicorrelated", kendall_tau=0.5, copula="t"))
        # rho is a target KENDALL'S TAU; the latent parameter must be the
        # converted value sin(pi*tau/2), not tau itself.
        assert diag["correlation_source"] == "operator_supplied_tau"
        assert diag["target_kendall_tau"] == 0.5
        assert diag["mean_latent_correlation"] == pytest.approx(
            float(np.sin(np.pi * 0.5 / 2)), abs=1e-4)
        assert diag["shrinkage_weight"] == 0.0

    def test_estimated_policy_shrinks_and_validates(self):
        from risk.correlated_scenarios import correlated_yield_scenarios

        conn = self._conn(n_weeks=30)
        _, diag = correlated_yield_scenarios(
            conn, list(range(20)), policy=SupplyRiskPolicy(mode="estimated"))
        assert diag["correlation_source"] == "estimated_from_history_shrunk"
        assert diag["rank_scale"] == "kendall_tau"
        assert 0.1 <= diag["shrinkage_weight"] <= 0.9
        # Shrinkage must move the rank estimate toward zero.
        assert abs(diag["shrunk_mean_pairwise_tau"]) < abs(
            diag["raw_mean_pairwise_tau"]) + 1e-9
        assert diag["correlation_validation"]["valid"] is True
        # Genuine pairwise-overlap diagnostics must be present.
        for k in ("n_pairs", "pairs_adequate", "pct_pairs_adequate",
                  "min_pair_overlap", "median_pair_overlap",
                  "max_pair_overlap", "n_joint_periods", "connected"):
            assert k in diag

    def test_estimation_refusal_raises_by_default(self):
        """Below the threshold we must refuse, not guess — and by default
        that refusal RAISES rather than quietly degrading."""
        from risk.correlated_scenarios import (
            CorrelatedScenarioError,
            correlated_yield_scenarios,
        )

        conn = self._conn(n_weeks=5)
        with pytest.raises(CorrelatedScenarioError,
                           match="refused_insufficient_history"):
            correlated_yield_scenarios(
                conn, list(range(10)),
                policy=SupplyRiskPolicy(mode="estimated",
                                        min_periods_for_estimation=12))

    def test_estimation_refusal_falls_back_only_when_permitted(self):
        from risk.correlated_scenarios import correlated_yield_scenarios

        conn = self._conn(n_weeks=5)
        draws, diag = correlated_yield_scenarios(
            conn, list(range(10)),
            policy=SupplyRiskPolicy(mode="estimated",
                                    min_periods_for_estimation=12,
                                    on_failure="independent"))
        assert draws
        assert diag["correlation_source"] == "refused_insufficient_history"
        assert diag["fallback_applied"] == "independent"
        assert diag["mean_latent_correlation"] == 0.0

    def test_no_suppliers_is_reported_not_crashed(self):
        import duckdb

        from risk.correlated_scenarios import correlated_yield_scenarios

        root = __import__("pathlib").Path(__file__).resolve().parents[2]
        c = duckdb.connect(":memory:")
        for sql in sorted((root / "db" / "migrations").glob("*.sql")):
            c.execute(sql.read_text())
        draws, diag = correlated_yield_scenarios(c, [0, 1])
        assert draws == {} and diag["status"] == "no_suppliers"

    def test_correlated_draws_raise_aggregate_spread(self):
        """The substantive claim, measured through the real entry point."""
        from risk.correlated_scenarios import correlated_yield_scenarios

        conn = self._conn(n_weeks=30)
        ids = list(range(400))

        def agg_sd(policy):
            d, _ = correlated_yield_scenarios(conn, ids, policy=policy)
            by_scen: dict = {}
            for (omega, _sid), v in d.items():
                by_scen.setdefault(omega, []).append(v)
            return float(np.std([np.mean(v) for v in by_scen.values()]))

        indep = agg_sd(SupplyRiskPolicy(mode="independent"))
        corr = agg_sd(SupplyRiskPolicy(mode="equicorrelated", kendall_tau=0.7, copula="t"))
        assert corr > indep


class TestRankToLatentConversion:
    """A rank matrix is NOT a latent correlation parameter.

    The production path previously fed a Spearman matrix straight into the
    Cholesky factor, silently targeting the wrong dependence. Existing
    tolerances were loose enough (abs=0.08) that the bug still passed.
    """

    def test_kendall_identity_matches_closed_form(self):
        from risk.correlated_scenarios import kendall_to_latent, latent_to_kendall

        for tau in (-0.8, -0.25, 0.0, 0.3, 0.6, 0.9):
            assert kendall_to_latent(tau) == pytest.approx(
                np.sin(np.pi * tau / 2), rel=1e-12)
            assert latent_to_kendall(kendall_to_latent(tau)) == pytest.approx(
                tau, abs=1e-12)

    def test_conversion_is_not_the_identity_where_it_matters(self):
        """If it were, passing tau as latent would be harmless."""
        from risk.correlated_scenarios import kendall_to_latent

        assert abs(float(kendall_to_latent(0.5)) - 0.5) > 0.15
        assert abs(float(kendall_to_latent(0.8)) - 0.8) > 0.10

    @pytest.mark.parametrize("copula,df", [("gaussian", None), ("t", 6.0)])
    def test_realized_kendall_tau_matches_target_tightly(self, copula, df):
        """The end-to-end check the loose tolerance was hiding.

        Converting the target through kendall_to_latent must reproduce the
        requested rank dependence in the DRAWS, for BOTH copulas — the
        Spearman identity is Gaussian-only, which is why tau is used.
        """
        from risk.correlated_scenarios import (
            equicorrelation_matrix,
            kendall_to_latent,
        )

        params = {"A": (8.0, 2.0), "B": (3.0, 6.0)}   # deliberately unequal
        for target_tau in (0.2, 0.5, 0.75):
            latent = float(kendall_to_latent(target_tau))
            gen = CopulaScenarioGenerator(
                copula=copula, df=(df or 5.0), seed=11)
            d = gen.sample_beta_marginals(
                params, 30000, correlation=equicorrelation_matrix(2, latent))
            got, _ = stats.kendalltau(d["A"], d["B"])
            assert got == pytest.approx(target_tau, abs=0.02), (
                f"{copula}: target tau {target_tau}, realized {got:.4f}")

    def test_passing_tau_unconverted_misses_the_target(self):
        """Demonstrates the defect: the old path under-shoots dependence."""
        from risk.correlated_scenarios import (
            equicorrelation_matrix,
            kendall_to_latent,
        )

        params = {"A": (8.0, 2.0), "B": (8.0, 2.0)}
        target = 0.75
        gen = CopulaScenarioGenerator(copula="gaussian", seed=12)

        wrong = gen.sample_beta_marginals(
            params, 20000, correlation=equicorrelation_matrix(2, target))
        right = gen.sample_beta_marginals(
            params, 20000,
            correlation=equicorrelation_matrix(2, float(kendall_to_latent(target))))
        tau_wrong, _ = stats.kendalltau(wrong["A"], wrong["B"])
        tau_right, _ = stats.kendalltau(right["A"], right["B"])
        assert abs(tau_right - target) < abs(tau_wrong - target)
        assert tau_wrong < target - 0.1          # materially under-shoots


class TestJointCoverage:
    """'How much joint history' must mean pairwise OVERLAP."""

    def test_disjoint_series_report_no_joint_history(self):
        """The exact failure the old max() check missed: two suppliers with
        30 observations each but not one shared week."""
        from risk.correlated_scenarios import joint_coverage

        n = 60
        a = np.full(n, np.nan)
        a[:30] = 1.0
        b = np.full(n, np.nan)
        b[30:] = 1.0
        cov = joint_coverage({"A": a, "B": b}, min_overlap=4)
        assert cov["max_pair_overlap"] == 0
        assert cov["n_joint_periods"] == 0
        assert cov["pairs_adequate"] == 0
        assert cov["connected"] is False

    def test_full_overlap_reports_connected(self):
        from risk.correlated_scenarios import joint_coverage

        obs = {k: np.ones(20) for k in ("A", "B", "C")}
        cov = joint_coverage(obs, min_overlap=4)
        assert cov["n_pairs"] == 3 and cov["pairs_adequate"] == 3
        assert cov["pct_pairs_adequate"] == 100.0
        assert cov["n_joint_periods"] == 20 and cov["connected"] is True

    def test_disconnected_clusters_detected(self):
        """Two overlapping pairs with no bridge cannot support one matrix."""
        from risk.correlated_scenarios import joint_coverage

        n = 40
        a = np.full(n, np.nan)
        a[:20] = 1.0
        b = np.full(n, np.nan)
        b[:20] = 1.0
        c = np.full(n, np.nan)
        c[20:] = 1.0
        d = np.full(n, np.nan)
        d[20:] = 1.0
        cov = joint_coverage({"A": a, "B": b, "C": c, "D": d}, min_overlap=4)
        assert cov["connected"] is False
        assert cov["pairs_adequate"] == 2 and cov["n_pairs"] == 6


class TestFailureHandling:
    """An explicitly requested policy must not fail silently."""

    def test_default_on_failure_is_raise(self):
        assert SupplyRiskPolicy(mode="estimated").on_failure == "raise"

    def test_rejects_unknown_on_failure(self):
        with pytest.raises(ValueError, match="unknown on_failure"):
            SupplyRiskPolicy(mode="estimated", on_failure="shrug")

    def test_raises_when_policy_cannot_be_honoured(self):
        """No suppliers -> no draws. With on_failure='raise' the caller must
        be told, not handed independent scenarios that look normal."""
        import duckdb

        from risk.correlated_scenarios import CorrelatedScenarioError
        from risk.scenario_generation import yield_scenarios_from_distributions

        root = __import__("pathlib").Path(__file__).resolve().parents[2]
        c = duckdb.connect(":memory:")
        for sql in sorted((root / "db" / "migrations").glob("*.sql")):
            c.execute(sql.read_text())
        pol = SupplyRiskPolicy(mode="estimated", on_failure="raise")
        with pytest.raises(CorrelatedScenarioError, match="no draws"):
            yield_scenarios_from_distributions(c, [0, 1], supply_risk_policy=pol)

    def test_insufficient_history_raises_by_default_end_to_end(self):
        """Through the production entry point, not just the internals."""
        from risk.correlated_scenarios import CorrelatedScenarioError
        from risk.scenario_generation import yield_scenarios_from_distributions

        conn = TestPolicyBranchesEndToEnd._conn(n_weeks=4)
        pol = SupplyRiskPolicy(mode="estimated", min_periods_for_estimation=12,
                               on_failure="raise")
        with pytest.raises(CorrelatedScenarioError):
            yield_scenarios_from_distributions(conn, [0, 1, 2],
                                               supply_risk_policy=pol)

    def test_insufficient_history_falls_back_only_when_permitted(self):
        from risk.scenario_generation import yield_scenarios_from_distributions

        conn = TestPolicyBranchesEndToEnd._conn(n_weeks=4)
        pol = SupplyRiskPolicy(mode="estimated", min_periods_for_estimation=12,
                               on_failure="independent")
        diagnostics: dict = {}
        draws = yield_scenarios_from_distributions(
            conn, [0, 1, 2], supply_risk_policy=pol,
            diagnostics_out=diagnostics)
        assert draws
        assert diagnostics["correlation_source"] == "refused_insufficient_history"
        assert diagnostics["fallback_applied"] == "independent"

    def test_generate_returns_draws_and_provenance_together(self):
        from risk.scenario_generation import generate_yield_scenarios

        conn = TestPolicyBranchesEndToEnd._conn(n_weeks=30)
        pol = SupplyRiskPolicy(mode="equicorrelated", kendall_tau=0.4, copula="t")
        res = generate_yield_scenarios(conn, list(range(10)),
                                       supply_risk_policy=pol)
        assert res.draws and len(res) == len(res.draws)
        assert res.diagnostics["correlation_source"] == "operator_supplied_tau"
        assert res.diagnostics["policy_mode"] == "equicorrelated"

    def test_diagnostics_are_request_scoped_not_shared(self):
        """Regression: diagnostics used to live in module-global state, so
        two concurrent planning calls raced and operator A could read
        operator B's provenance — corrupting audit trails and leaking
        another tenant's policy and failure reason."""
        from risk.scenario_generation import yield_scenarios_from_distributions

        conn = TestPolicyBranchesEndToEnd._conn(n_weeks=30)
        a: dict = {}
        b: dict = {}
        yield_scenarios_from_distributions(
            conn, [0, 1], diagnostics_out=a,
            supply_risk_policy=SupplyRiskPolicy(
                mode="equicorrelated", kendall_tau=0.2, copula="gaussian"))
        yield_scenarios_from_distributions(
            conn, [0, 1], diagnostics_out=b,
            supply_risk_policy=SupplyRiskPolicy(
                mode="equicorrelated", kendall_tau=0.8, copula="t"))
        # The FIRST call's record must survive the second call untouched.
        assert a["target_kendall_tau"] == 0.2
        assert b["target_kendall_tau"] == 0.8
        assert a["copula"] == "gaussian" and b["copula"] == "t"
        assert a is not b

    def test_concurrent_calls_do_not_cross_contaminate(self):
        """The same property under real threads."""
        import threading

        from risk.scenario_generation import generate_yield_scenarios

        conn_a = TestPolicyBranchesEndToEnd._conn(n_weeks=30, seed=1)
        conn_b = TestPolicyBranchesEndToEnd._conn(n_weeks=30, seed=2)
        results: dict = {}
        barrier = threading.Barrier(2)

        def run(name, conn, tau, copula):
            pol = SupplyRiskPolicy(mode="equicorrelated", kendall_tau=tau,
                                   copula=copula)
            barrier.wait()
            for _ in range(6):       # interleave repeatedly
                results[name] = generate_yield_scenarios(
                    conn, list(range(6)), supply_risk_policy=pol)

        t1 = threading.Thread(target=run, args=("A", conn_a, 0.15, "gaussian"))
        t2 = threading.Thread(target=run, args=("B", conn_b, 0.85, "t"))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert results["A"].diagnostics["target_kendall_tau"] == 0.15
        assert results["B"].diagnostics["target_kendall_tau"] == 0.85
        assert results["A"].diagnostics["copula"] == "gaussian"
        assert results["B"].diagnostics["copula"] == "t"

    def test_policy_validates_its_parameters(self):
        with pytest.raises(ValueError, match=r"kendall_tau must lie in"):
            SupplyRiskPolicy(mode="equicorrelated", kendall_tau=1.4)
        with pytest.raises(ValueError, match="degrees of freedom must be"):
            SupplyRiskPolicy(mode="estimated", copula="t", df=0.0)
        with pytest.raises(ValueError, match="percentage"):
            SupplyRiskPolicy(mode="estimated", min_pct_pairs_adequate=150.0)


class TestIndependentPathProvenance:
    """The DEFAULT path must be audited too.

    Regression: _emit was only called inside the enabled-correlated branch,
    so `generate_yield_scenarios(conn, ids)` and an explicit independent
    policy both returned draws with EMPTY diagnostics — leaving the most
    common production route with no record of its dependence assumption,
    which is exactly what the contract promises never to happen.
    """

    def test_no_policy_still_reports_provenance(self):
        from risk.scenario_generation import generate_yield_scenarios

        conn = TestPolicyBranchesEndToEnd._conn(n_weeks=6, n_suppliers=3)
        res = generate_yield_scenarios(conn, [0, 1])
        assert res.draws
        d = res.diagnostics
        assert d, "default path must not return empty diagnostics"
        assert d["correlation_source"] == "independent_by_policy"
        assert d["policy_mode"] == "independent"
        assert d["fallback_applied"] is None
        assert d["copula"] is None
        assert d["mean_latent_correlation"] == 0.0
        assert d["n_suppliers"] == 3
        assert "understated" in d["note"]

    def test_explicit_independent_policy_reports_provenance(self):
        from risk.scenario_generation import generate_yield_scenarios

        conn = TestPolicyBranchesEndToEnd._conn(n_weeks=6, n_suppliers=3)
        res = generate_yield_scenarios(
            conn, [0, 1], supply_risk_policy=SupplyRiskPolicy(mode="independent"))
        assert res.diagnostics["correlation_source"] == "independent_by_policy"
        assert res.diagnostics["n_suppliers"] == 3

    def test_no_suppliers_still_reports_provenance(self):
        import duckdb

        from risk.scenario_generation import generate_yield_scenarios

        root = __import__("pathlib").Path(__file__).resolve().parents[2]
        c = duckdb.connect(":memory:")
        for sql in sorted((root / "db" / "migrations").glob("*.sql")):
            c.execute(sql.read_text())
        res = generate_yield_scenarios(c, [0, 1])
        assert res.draws == {}
        assert res.diagnostics["correlation_source"] == "independent_by_policy"
        assert res.diagnostics["n_suppliers"] == 0

    def test_seed_is_reported_on_the_independent_path(self):
        from risk.scenario_generation import generate_yield_scenarios

        conn = TestPolicyBranchesEndToEnd._conn(n_weeks=6)
        assert generate_yield_scenarios(
            conn, [0, 1], seed=7).diagnostics["seed"] == 7

    def test_policy_seed_is_authoritative_when_correlation_enabled(self):
        """Documented precedence: the policy owns the dependence model, so
        its seed governs once correlation is on."""
        from risk.scenario_generation import generate_yield_scenarios

        conn = TestPolicyBranchesEndToEnd._conn(n_weeks=30)
        pol = SupplyRiskPolicy(mode="equicorrelated", kendall_tau=0.4, seed=123)
        res = generate_yield_scenarios(conn, [0, 1], seed=999,
                                       supply_risk_policy=pol)
        assert res.diagnostics["seed"] == 123      # policy wins, not 999


class TestInfrastructureFaultsPropagate:
    """on_failure governs insufficient EVIDENCE, never broken infrastructure.

    Regression: _weekly_fill_matrix wrapped its query in
    `except Exception: return {}`, so schema errors, closed connections and
    migration defects were all reported as "no delivery history". With
    on_failure="independent" that silently produced independent scenarios;
    with on_failure="raise" it surfaced as a misleading MODELLING refusal
    that hid the database root cause.
    """

    @staticmethod
    def _conn_without_tables():
        import duckdb
        return duckdb.connect(":memory:")

    def test_missing_table_raises_scenario_data_error(self):
        from risk.correlated_scenarios import ScenarioDataError, _weekly_fill_matrix

        with pytest.raises(ScenarioDataError, match="unavailable"):
            _weekly_fill_matrix(self._conn_without_tables(), ["S0"])

    def test_scenario_data_error_is_distinct_from_modelling_refusal(self):
        from risk.correlated_scenarios import (
            CorrelatedScenarioError,
            ScenarioDataError,
        )

        assert not issubclass(ScenarioDataError, CorrelatedScenarioError)
        assert not issubclass(CorrelatedScenarioError, ScenarioDataError)

    def test_infrastructure_fault_is_not_absorbed_by_permitted_fallback(self):
        """Even on_failure="independent" must not swallow a schema fault."""
        import duckdb

        from risk.correlated_scenarios import ScenarioDataError
        from risk.scenario_generation import yield_scenarios_from_distributions

        root = __import__("pathlib").Path(__file__).resolve().parents[2]
        c = duckdb.connect(":memory:")
        for sql in sorted((root / "db" / "migrations").glob("*.sql")):
            c.execute(sql.read_text())
        # Seed suppliers so distributions exist, then remove the table the
        # correlation estimator needs — an infrastructure fault, not thin data.
        import pandas as pd
        wk = pd.date_range("2024-01-01", periods=20, freq="7D")
        rows = [(f"D{a}{w}", f"S{a}", f"S{a}", "P1", "Tom",
                 wk[w].date().isoformat(), 500.0, 450.0, 450.0)
                for a in range(3) for w in range(20)]
        c.executemany(
            "INSERT INTO stg_supplier_deliveries (delivery_id, supplier_id,"
            " supplier_name, product_id, product_name, delivery_date,"
            " ordered_quantity, delivered_quantity, accepted_quantity)"
            " VALUES (?,?,?,?,?,?,?,?,?)", rows)
        # Snapshot the fitted distributions, then remove the table the
        # correlation estimator reads — an infrastructure fault, not thin data.
        from risk.supplier_distribution import supplier_fill_distributions
        assert supplier_fill_distributions(c, quantile=0.10)
        c.execute("DROP TABLE stg_supplier_deliveries")

        pol = SupplyRiskPolicy(mode="estimated", on_failure="independent")
        with pytest.raises((ScenarioDataError, duckdb.CatalogException)) as exc:
            yield_scenarios_from_distributions(c, [0, 1],
                                               supply_risk_policy=pol)
        # The essential property: an infrastructure fault surfaces AS one,
        # and is never converted into a modelling refusal or into a
        # successful-looking independent result.
        from risk.correlated_scenarios import CorrelatedScenarioError
        assert not isinstance(exc.value, CorrelatedScenarioError)
