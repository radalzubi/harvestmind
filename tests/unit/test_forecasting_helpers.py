"""Unit tests for under-tested forecasting helper modules.

Covers, with hand-computed expectations on tiny deterministic arrays:

* forecasting/demand/forecast_evaluator.py
  - MASE / RMSSE scaled-error metrics + the model-switch gate they drive.
  - interval_coverage / winkler_score interval metrics.
  - evaluate_forecasts grouping + bias.
  - divide-by-zero / too-short-history guards.
* forecasting/demand/hierarchical_reconciler.py
  - summation matrix structure and bottom-up coherence (category totals == sum
    of their bottom-level reconciled forecasts).
* forecasting/demand/feature_engineering.py
  - lag / rolling columns present with correct values on a small series.
* forecasting/supply/supplier_reliability_scorer.py
  - output shape, fill/rejection math, risk ordering, zero/thin deliveries.

All deterministic, no network, no LLM.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from forecasting.demand.forecast_evaluator import (
    evaluate_forecasts,
    interval_coverage,
    mase,
    rmsse,
    winkler_score,
)
from forecasting.demand.feature_engineering import (
    FEATURE_COLS,
    LAG_WEEKS,
    ROLLING_WINDOWS,
    TARGET_COL,
    build_features,
)
from forecasting.demand.hierarchical_reconciler import (
    build_summation_matrix,
    reconcile_mintrace_wls,
)
from forecasting.supply.supplier_reliability_scorer import (
    FILL_RATE_WEIGHT,
    ONTIME_WEIGHT,
    QUALITY_WEIGHT,
    REJECTION_WEIGHT,
    score_suppliers,
)


# ════════════════════════════════════════════════════════════════════════════
# MASE / RMSSE — scaled error metrics
# ════════════════════════════════════════════════════════════════════════════


class TestMASE:
    def test_mase_one_when_forecast_error_equals_naive_scale(self):
        """MASE == 1 when the model's MAE equals the in-sample naive MAE.

        actual = [1,2,3,4,5,6]; period=1 → naive errors all == 1, scale == 1.
        A forecast that is off by exactly 1 everywhere has MAE == 1, so MASE==1.
        """
        actual = np.array([1, 2, 3, 4, 5, 6], dtype=float)
        forecast = actual + 1.0  # abs error == 1 everywhere
        assert mase(actual, forecast, seasonal_period=1) == pytest.approx(1.0)

    def test_mase_perfect_forecast_is_zero(self):
        actual = np.array([3, 1, 4, 1, 5, 9], dtype=float)
        assert mase(actual, actual.copy(), seasonal_period=1) == pytest.approx(0.0)

    def test_mase_seasonal_baseline_handcomputed(self):
        """Seasonal-naive baseline with period=2 on a known array.

        actual = [10,20,12,24]; period=2 → naive errors = |12-10|, |24-20| = 2,4
        scale = mean(2,4) = 3. forecast off by 3 everywhere → MAE 3 → MASE 1.
        """
        actual = np.array([10, 20, 12, 24], dtype=float)
        forecast = actual + 3.0
        assert mase(actual, forecast, seasonal_period=2) == pytest.approx(1.0)

    def test_mase_nan_when_history_too_short(self):
        # n <= seasonal_period → cannot form a naive baseline.
        actual = np.array([1.0, 2.0])
        assert np.isnan(mase(actual, actual, seasonal_period=2))
        assert np.isnan(mase(actual, actual, seasonal_period=5))

    def test_mase_nan_on_flat_series_zero_scale(self):
        # Constant series → naive errors all 0 → scale 0 → divide-by-zero guard.
        actual = np.full(6, 7.0)
        forecast = np.array([7, 7, 7, 7, 7, 8.0])
        assert np.isnan(mase(actual, forecast, seasonal_period=1))

    def test_mase_accepts_lists(self):
        # np.asarray conversion path.
        assert mase([1, 2, 3, 4], [2, 3, 4, 5], seasonal_period=1) == pytest.approx(1.0)


class TestRMSSE:
    def test_rmsse_one_when_squared_error_matches_naive(self):
        """RMSSE == 1 when MSE equals the in-sample naive MSE.

        actual = [1,2,3,4,5,6]; period=1 → naive sq errors all 1, scale 1.
        forecast off by 1 everywhere → MSE 1 → sqrt(1/1)=1.
        """
        actual = np.array([1, 2, 3, 4, 5, 6], dtype=float)
        forecast = actual + 1.0
        assert rmsse(actual, forecast, seasonal_period=1) == pytest.approx(1.0)

    def test_rmsse_perfect_forecast_zero(self):
        actual = np.array([2, 4, 6, 8, 10], dtype=float)
        assert rmsse(actual, actual.copy(), seasonal_period=1) == pytest.approx(0.0)

    def test_rmsse_handcomputed_value(self):
        """actual=[0,2,4,6]; period=1 → naive sq errs = 4,4,4 → scale 4.

        forecast=[0,2,4,6]+[0,0,0,4] (last point off by 4) →
        sq errs = 0,0,0,16 → MSE = 4 → sqrt(4/4) = 1.0
        """
        actual = np.array([0, 2, 4, 6], dtype=float)
        forecast = np.array([0, 2, 4, 10], dtype=float)
        assert rmsse(actual, forecast, seasonal_period=1) == pytest.approx(1.0)

    def test_rmsse_nan_guards(self):
        assert np.isnan(rmsse([1.0, 2.0], [1.0, 2.0], seasonal_period=2))  # short
        assert np.isnan(rmsse(np.full(5, 3.0), np.full(5, 4.0), seasonal_period=1))  # flat


# ════════════════════════════════════════════════════════════════════════════
# Interval metrics — coverage & Winkler
# ════════════════════════════════════════════════════════════════════════════


class TestIntervalCoverage:
    def test_full_coverage(self):
        actual = np.array([5, 5, 5], dtype=float)
        assert interval_coverage(actual, np.zeros(3), np.full(3, 10.0)) == pytest.approx(1.0)

    def test_partial_coverage_handcomputed(self):
        actual = np.array([1, 5, 11, 5], dtype=float)
        lower = np.zeros(4)
        upper = np.full(4, 10.0)
        # only the 11 falls outside → 3/4 covered
        assert interval_coverage(actual, lower, upper) == pytest.approx(0.75)

    def test_boundary_inclusive(self):
        # Actuals exactly on the bounds count as covered.
        actual = np.array([0.0, 10.0])
        assert interval_coverage(actual, np.zeros(2), np.full(2, 10.0)) == pytest.approx(1.0)


class TestWinklerScore:
    def test_winkler_is_width_when_all_inside(self):
        """No penalties when every actual lies inside → score == mean width."""
        actual = np.array([5, 5, 5], dtype=float)
        lower = np.zeros(3)
        upper = np.full(3, 10.0)
        assert winkler_score(actual, lower, upper, alpha=0.1) == pytest.approx(10.0)

    def test_winkler_penalises_below(self):
        """One actual below lower adds (2/alpha)*(lower-actual)/n.

        single point: actual=-5, lower=0, upper=10, alpha=0.5
        width=10, penalty_low=(2/0.5)*(0-(-5))=4*5=20 → 30.
        """
        actual = np.array([-5.0])
        score = winkler_score(actual, np.array([0.0]), np.array([10.0]), alpha=0.5)
        assert score == pytest.approx(30.0)

    def test_winkler_penalises_above(self):
        # actual=20, upper=10, alpha=0.5 → width 10 + (2/0.5)*(20-10)=40 → 50
        score = winkler_score(np.array([20.0]), np.array([0.0]), np.array([10.0]), alpha=0.5)
        assert score == pytest.approx(50.0)


# ════════════════════════════════════════════════════════════════════════════
# The model-switch gate (driven by the scaled-error metrics above)
# ════════════════════════════════════════════════════════════════════════════


def _gate_passes(actual, challenger, incumbent, period=1) -> bool:
    """The contract from the demand service: a challenger replaces the
    incumbent only when its scaled error is *strictly* below the incumbent's
    (ratio < 1.0). Mirrors evaluate_demand_forecaster's gate_rule.
    """
    ratio = mase(actual, challenger, period) / mase(actual, incumbent, period)
    return bool(ratio < 1.0)


class TestModelSwitchGate:
    def test_switch_when_challenger_strictly_better(self):
        actual = np.array([10, 20, 30, 40, 50], dtype=float)
        incumbent = actual + 4.0  # MAE 4
        challenger = actual + 1.0  # MAE 1 → clearly better
        assert _gate_passes(actual, challenger, incumbent) is True

    def test_no_switch_when_challenger_worse(self):
        actual = np.array([10, 20, 30, 40, 50], dtype=float)
        incumbent = actual + 1.0
        challenger = actual + 5.0
        assert _gate_passes(actual, challenger, incumbent) is False

    def test_no_switch_on_tie(self):
        """Strict inequality: an exact tie does NOT trigger a switch."""
        actual = np.array([10, 20, 30, 40, 50], dtype=float)
        incumbent = actual + 3.0
        challenger = actual - 3.0  # same absolute error magnitude
        assert _gate_passes(actual, challenger, incumbent) is False


# ════════════════════════════════════════════════════════════════════════════
# evaluate_forecasts — grouping, bias, metric wiring
# ════════════════════════════════════════════════════════════════════════════


def _eval_frames(n_weeks=60, off=0.0):
    weeks = pd.date_range("2025-01-06", periods=n_weeks, freq="W-MON")
    qty = np.arange(1, n_weeks + 1, dtype=float)
    actual = pd.DataFrame({
        "product_id": "Tomatoes", "buyer_id": "B1",
        "week_start": weeks, "qty_ordered_kg": qty,
    })
    forecast = pd.DataFrame({
        "product_id": "Tomatoes", "buyer_id": "B1",
        "week_start": weeks, "forecast_kg": qty + off,
        "lower_80": qty - 5, "upper_80": qty + 5,
        "lower_95": qty - 10, "upper_95": qty + 10,
    })
    return actual, forecast


class TestEvaluateForecasts:
    def test_shape_and_columns(self):
        actual, forecast = _eval_frames()
        out = evaluate_forecasts(actual, forecast)
        assert len(out) == 1  # one product group
        for col in ("product_id", "n", "mase", "rmsse", "bias_pct",
                    "coverage_80", "winkler_80", "coverage_95", "winkler_95"):
            assert col in out.columns
        assert out.iloc[0]["n"] == 60

    def test_bias_pct_sign_and_magnitude(self):
        # Forecast over by 2 each of 60 weeks → bias = sum(2)/sum(actual)*100.
        actual, forecast = _eval_frames(off=2.0)
        out = evaluate_forecasts(actual, forecast)
        total = float(actual["qty_ordered_kg"].sum())
        expected = 2.0 * 60 / total * 100
        assert out.iloc[0]["bias_pct"] == pytest.approx(expected, rel=1e-4)

    def test_coverage_within_intervals(self):
        # Perfect point forecast sits inside its own ±5 / ±10 bands → 100% cover.
        actual, forecast = _eval_frames(off=0.0)
        out = evaluate_forecasts(actual, forecast)
        assert out.iloc[0]["coverage_80"] == pytest.approx(1.0)
        assert out.iloc[0]["coverage_95"] == pytest.approx(1.0)

    def test_groups_by_custom_cols(self):
        a1, f1 = _eval_frames()
        a2, f2 = _eval_frames()
        a2["buyer_id"] = "B2"
        f2["buyer_id"] = "B2"
        actual = pd.concat([a1, a2], ignore_index=True)
        forecast = pd.concat([f1, f2], ignore_index=True)
        out = evaluate_forecasts(actual, forecast, group_cols=["product_id", "buyer_id"])
        assert len(out) == 2
        assert set(out["buyer_id"]) == {"B1", "B2"}


# ════════════════════════════════════════════════════════════════════════════
# Hierarchical reconciliation — coherence / summation matrix
# ════════════════════════════════════════════════════════════════════════════


def _hier_frames():
    week = pd.Timestamp("2026-01-05")
    base = pd.DataFrame([
        {"product_id": "Tomatoes", "buyer_id": "B1", "week_start": week, "forecast_kg": 100.0},
        {"product_id": "Tomatoes", "buyer_id": "B2", "week_start": week, "forecast_kg": 50.0},
        {"product_id": "Kale", "buyer_id": "B1", "week_start": week, "forecast_kg": 30.0},
        {"product_id": "Carrots", "buyer_id": "B1", "week_start": week, "forecast_kg": 20.0},
    ])
    meta = pd.DataFrame([
        {"product_id": "Tomatoes", "crop_category": "fruiting"},
        {"product_id": "Kale", "crop_category": "leafy"},
        {"product_id": "Carrots", "crop_category": "root"},
    ])
    return base, meta


class TestSummationMatrix:
    def test_matrix_structure(self):
        base, meta = _hier_frames()
        S, all_names, bottom_names = build_summation_matrix(base, meta)
        # 4 bottom series, 3 categories, 3 products, 1 total → 11 rows.
        assert len(bottom_names) == 4
        assert all_names[0] == "total"
        assert S.shape == (11, 4)
        # Total row sums all bottoms.
        assert S[0].sum() == 4
        # Bottom-level identity block (last 4 rows) is the identity.
        np.testing.assert_array_equal(S[-4:], np.eye(4))

    def test_category_rows_sum_correct_bottoms(self):
        base, meta = _hier_frames()
        S, all_names, bottom_names = build_summation_matrix(base, meta)
        y_bottom = np.array([
            base.set_index(["product_id", "buyer_id"]).loc[
                tuple(n.split("|", 1)), "forecast_kg"
            ]
            for n in bottom_names
        ])
        agg = S @ y_bottom
        total_idx = all_names.index("total")
        assert agg[total_idx] == pytest.approx(200.0)  # 100+50+30+20
        # fruiting category == Tomatoes B1 + B2 = 150
        assert agg[all_names.index("cat:fruiting")] == pytest.approx(150.0)
        assert agg[all_names.index("cat:leafy")] == pytest.approx(30.0)


class TestReconciliation:
    def test_ols_reconciliation_is_coherent(self):
        """Bottom-up totals after reconciliation equal reconciled category totals.

        Base bottom forecasts are already coherent (they are leaf-level), so an
        OLS projection onto the coherent subspace must return them unchanged and
        the category sum must equal the sum of its children.
        """
        base, meta = _hier_frames()
        # Force the OLS fallback (no hierarchicalforecast dependency assumed).
        out = reconcile_mintrace_wls(base, meta)
        assert set(out["model"].unique()) <= {"mintrace_ols", "mintrace_wls"}
        merged = out.merge(
            base, on=["product_id", "buyer_id", "week_start"], suffixes=("_rec", "_base")
        )
        # Coherent base → reconciliation leaves leaf forecasts essentially intact.
        np.testing.assert_allclose(
            merged["forecast_kg_rec"].values,
            merged["forecast_kg_base"].values,
            atol=0.05,
        )
        # Category coherence: sum of reconciled bottoms in fruiting == 150.
        rec_with_cat = out.merge(meta, on="product_id", how="left")
        fruiting_total = rec_with_cat[
            rec_with_cat["crop_category"] == "fruiting"
        ]["forecast_kg"].sum()
        assert fruiting_total == pytest.approx(150.0, abs=0.05)
        # Grand total preserved.
        assert out["forecast_kg"].sum() == pytest.approx(200.0, abs=0.05)

    def test_reconciliation_non_negative(self):
        base, meta = _hier_frames()
        out = reconcile_mintrace_wls(base, meta)
        assert (out["forecast_kg"] >= 0).all()


# ════════════════════════════════════════════════════════════════════════════
# Feature engineering — lag / rolling columns and values
# ════════════════════════════════════════════════════════════════════════════


def _single_series(n_weeks=60):
    weeks = pd.date_range("2025-01-06", periods=n_weeks, freq="W-MON")
    return pd.DataFrame({
        "product_id": "Tomatoes", "buyer_id": "B1",
        "week_start": weeks,
        "qty_ordered_kg": np.arange(1, n_weeks + 1, dtype=float),
    })


class TestFeatureEngineering:
    def test_lag_and_rolling_columns_present(self):
        feats = build_features(_single_series())
        for lag in LAG_WEEKS:
            assert f"lag_{lag}w" in feats.columns
        for win in ROLLING_WINDOWS:
            assert f"roll_mean_{win}w" in feats.columns
            assert f"roll_std_{win}w" in feats.columns
        # Declared FEATURE_COLS must all exist on the output frame.
        for col in FEATURE_COLS:
            assert col in feats.columns
        assert TARGET_COL in feats.columns

    def test_lag_values_correct(self):
        """On a monotonically increasing series 1..60, lag_1w[t] == qty[t]-1.

        The series is contiguous weekly, so lagging by 1 just shifts by one row.
        """
        feats = build_features(_single_series())
        feats = feats.sort_values("week_start").reset_index(drop=True)
        # First row's lag is NaN; from row 1 on, lag_1w == previous qty.
        assert pd.isna(feats.loc[0, "lag_1w"])
        for i in range(1, len(feats)):
            assert feats.loc[i, "lag_1w"] == pytest.approx(
                feats.loc[i - 1, TARGET_COL]
            )

    def test_rolling_mean_handcomputed(self):
        """roll_mean_4w uses shift(1) then a 4-wide window (min_periods=2).

        For the 1..60 ramp, at row i (0-indexed, i>=2) the window covers the
        prior up-to-4 target values ending at i-1.
        """
        feats = build_features(_single_series()).sort_values("week_start").reset_index(drop=True)
        # Row 4 (0-indexed) → window = targets at rows 0..3 = [1,2,3,4] → mean 2.5
        assert feats.loc[4, "roll_mean_4w"] == pytest.approx(2.5)
        # Row 5 → window = rows 1..4 = [2,3,4,5] → mean 3.5
        assert feats.loc[5, "roll_mean_4w"] == pytest.approx(3.5)
        # min_periods=2 → row 0 and row 1 have <2 prior points → NaN at row 0/1.
        assert pd.isna(feats.loc[0, "roll_mean_4w"])
        assert pd.isna(feats.loc[1, "roll_mean_4w"])

    def test_temporal_features_bounded(self):
        feats = build_features(_single_series())
        assert feats["week_sin"].between(-1, 1).all()
        assert feats["week_cos"].between(-1, 1).all()
        assert feats["month"].between(1, 12).all()
        assert feats["quarter"].between(1, 4).all()

    def test_no_lookahead_in_lags(self):
        """Lag/rolling features must not encode the current target (leakage).

        lag_1w at the earliest row is NaN, never the row's own value.
        """
        feats = build_features(_single_series()).sort_values("week_start").reset_index(drop=True)
        # current target never equals lag_1w on the same row except by coincidence
        # of value; on a strictly increasing ramp they must differ where defined.
        defined = feats.dropna(subset=["lag_1w"])
        assert (defined["lag_1w"] != defined[TARGET_COL]).all()


# ════════════════════════════════════════════════════════════════════════════
# Supplier reliability scorer
# ════════════════════════════════════════════════════════════════════════════


def _deliveries(rows):
    return pd.DataFrame(
        rows,
        columns=["supplier_id", "delivery_date", "qty_received_kg",
                 "qty_rejected_kg", "grade_received", "temp_on_arrival_c"],
    )


def _pos(rows):
    return pd.DataFrame(
        rows,
        columns=["supplier_id", "week_start", "qty_committed_kg", "delivery_window_end"],
    )


class TestSupplierScorer:
    def test_output_shape_and_columns(self):
        cutoff = "2026-06-15"
        deliveries = _deliveries([
            ("S1", cutoff, 100.0, 0.0, "A", 4.0),
            ("S2", cutoff, 80.0, 20.0, "B", 6.0),
        ])
        pos = _pos([
            ("S1", cutoff, 100.0, cutoff),
            ("S2", cutoff, 100.0, cutoff),
        ])
        out = score_suppliers(deliveries, pos)
        for col in ("supplier_id", "avg_reliability", "fill_rate",
                    "rejection_rate", "quality_score", "n_deliveries", "as_of_date"):
            assert col in out.columns
        assert len(out) == 2
        # avg_reliability bounded [0,1] and sorted descending.
        assert out["avg_reliability"].between(0, 1).all()
        assert list(out["avg_reliability"]) == sorted(
            out["avg_reliability"], reverse=True
        )

    def test_perfect_supplier_scores_high(self):
        """Full fill, zero rejection → reliability close to the weight ceiling.

        fill=1, rejection=1, quality=1, ontime=0.90 →
        0.40*1 + 0.35*1 + 0.15*1 + 0.10*0.90 = 0.99.
        """
        cutoff = "2026-06-15"
        deliveries = _deliveries([("S1", cutoff, 100.0, 0.0, "A", 4.0)])
        pos = _pos([("S1", cutoff, 100.0, cutoff)])
        out = score_suppliers(deliveries, pos)
        row = out.iloc[0]
        expected = (
            FILL_RATE_WEIGHT * 1.0
            + QUALITY_WEIGHT * 1.0
            + REJECTION_WEIGHT * 1.0
            + ONTIME_WEIGHT * 0.90
        )
        assert row["avg_reliability"] == pytest.approx(round(expected, 4), abs=1e-4)
        assert row["fill_rate"] == pytest.approx(1.0)
        assert row["rejection_rate"] == pytest.approx(0.0)

    def test_high_rejection_lowers_score(self):
        """A supplier with heavy rejection must rank below a clean one."""
        cutoff = "2026-06-15"
        deliveries = _deliveries([
            ("Good", cutoff, 100.0, 0.0, "A", 4.0),
            ("Bad", cutoff, 100.0, 80.0, "C", 9.0),  # 80% rejected
        ])
        pos = _pos([
            ("Good", cutoff, 100.0, cutoff),
            ("Bad", cutoff, 100.0, cutoff),
        ])
        out = score_suppliers(deliveries, pos).set_index("supplier_id")
        assert out.loc["Good", "avg_reliability"] > out.loc["Bad", "avg_reliability"]
        # rejection_rate column reflects the 80% rejection for Bad.
        assert out.loc["Bad", "rejection_rate"] == pytest.approx(0.80, abs=1e-4)
        assert out.loc["Good", "rejection_rate"] == pytest.approx(0.0)

    def test_risk_tier_thresholds(self):
        """Reliability must order suppliers into sane risk tiers.

        high fill+clean → high tier; under-delivery + rejection → low tier.
        """
        cutoff = "2026-06-15"
        deliveries = _deliveries([
            ("Reliable", cutoff, 100.0, 0.0, "A", 4.0),
            ("Risky", cutoff, 30.0, 15.0, "C", 9.0),  # under-fill + 50% rejection
        ])
        pos = _pos([
            ("Reliable", cutoff, 100.0, cutoff),
            ("Risky", cutoff, 100.0, cutoff),
        ])
        out = score_suppliers(deliveries, pos).set_index("supplier_id")
        assert out.loc["Reliable", "avg_reliability"] >= 0.80  # low-risk tier
        assert out.loc["Risky", "avg_reliability"] < 0.60  # elevated-risk tier
        # Risky under-fills: fill = 30/100 = 0.30
        assert out.loc["Risky", "fill_rate"] == pytest.approx(0.30, abs=1e-4)

    def test_empty_deliveries_returns_empty_contract(self):
        deliveries = _deliveries([])
        pos = _pos([("S1", "2026-06-15", 100.0, "2026-06-15")])
        out = score_suppliers(deliveries, pos)
        assert out.empty
        assert "supplier_id" in out.columns
        assert "avg_reliability" in out.columns

    def test_thin_deliveries_outside_window_excluded(self):
        """A single old delivery outside the trailing window yields no scores."""
        # delivery 30 weeks before cutoff; window is 13 weeks → excluded.
        deliveries = _deliveries([
            ("S1", "2026-06-15", 100.0, 0.0, "A", 4.0),   # in window (cutoff)
            ("S2", "2025-10-01", 100.0, 0.0, "A", 4.0),   # >13wk old
        ])
        pos = _pos([
            ("S1", "2026-06-15", 100.0, "2026-06-15"),
            ("S2", "2025-10-01", 100.0, "2025-10-01"),
        ])
        out = score_suppliers(deliveries, pos, n_weeks=13).set_index("supplier_id")
        assert "S1" in out.index
        assert "S2" not in out.index

    def test_no_po_falls_back_to_received_as_committed(self):
        """With no matching PO commitment, fill rate falls back to 1.0
        (committed defaults to received), so a clean delivery still scores well.
        """
        cutoff = "2026-06-15"
        deliveries = _deliveries([("S1", cutoff, 100.0, 0.0, "A", 4.0)])
        pos = _pos([])  # no commitments at all
        out = score_suppliers(deliveries, pos)
        assert len(out) == 1
        assert out.iloc[0]["fill_rate"] == pytest.approx(1.0)
