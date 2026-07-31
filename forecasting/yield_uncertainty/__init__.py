"""Probabilistic supply-forecast layer.

A tiered design, chosen by how much history an operator actually has
rather than by which model is most interesting:

    Tier 0  PooledEmpiricalModel / ClimatologyModel
            Empirical quantiles with empirical-Bayes partial pooling.
            Runs for unseen or sparse groups, and is the benchmark every
            other model must beat.

    Tier 1  GradientBoostedQuantileModel
            Per-level quantile regression (LightGBM, or a dependency-free
            linear fallback) wrapped in split-conformal calibration.

Both emit the same ``ProbabilisticForecast`` contract, so downstream code
never needs to know which tier produced a number — but the tier, the
confidence and any fallback reason travel with the forecast so the
operator can.

See docs/research/crop_yield_uncertainty_review.md for the method review
and the decision record behind this design.
"""

from forecasting.yield_uncertainty.baseline import (
    ClimatologyModel,
    PooledEmpiricalModel,
    PooledPopulation,
    classify_data_tier,
    shrinkage_weight,
)
from forecasting.yield_uncertainty.conformal import (
    ConformalCalibrator,
    MondrianConformalCalibrator,
    conformal_quantile,
    conformity_scores,
    empirical_coverage,
    min_calibration_size,
    split_time_aware,
)
from forecasting.yield_uncertainty.contract import (
    QUANTILE_LEVELS,
    Confidence,
    DataTier,
    ForecastValidationError,
    ProbabilisticForecast,
    QuantityKind,
    confidence_for_tier,
    rearrange,
)
from forecasting.yield_uncertainty.evaluation import (
    coverage_by_level,
    crps_ensemble,
    crps_sample,
    evaluate_forecasts,
    interval_score,
    mean_pinball,
    pinball_loss,
    pit_uniformity,
    pit_values,
    sharpness,
    tail_coverage,
    weighted_interval_score,
)
from forecasting.yield_uncertainty.quantile_model import (
    GradientBoostedQuantileModel,
)

__all__ = [
    "QUANTILE_LEVELS",
    "ClimatologyModel",
    "Confidence",
    "ConformalCalibrator",
    "DataTier",
    "ForecastValidationError",
    "GradientBoostedQuantileModel",
    "MondrianConformalCalibrator",
    "PooledEmpiricalModel",
    "PooledPopulation",
    "ProbabilisticForecast",
    "QuantityKind",
    "classify_data_tier",
    "confidence_for_tier",
    "conformal_quantile",
    "conformity_scores",
    "coverage_by_level",
    "crps_ensemble",
    "crps_sample",
    "empirical_coverage",
    "evaluate_forecasts",
    "interval_score",
    "mean_pinball",
    "min_calibration_size",
    "pinball_loss",
    "pit_uniformity",
    "pit_values",
    "rearrange",
    "sharpness",
    "shrinkage_weight",
    "split_time_aware",
    "tail_coverage",
    "weighted_interval_score",
]
