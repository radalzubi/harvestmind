"""Tier-1 model: gradient-boosted quantile regression + conformal calibration.

Fits one LightGBM regressor per quantile level under the pinball objective,
then calibrates the interval with split-conformal (CQR). LightGBM is
optional at import time — the module degrades to a linear quantile
regressor rather than failing, so the minimal test suite has no heavy
dependency.

WHY QUANTILE REGRESSION RATHER THAN A FITTED DISTRIBUTION
---------------------------------------------------------
Crop-supply outcomes are skewed, bounded below at zero, heteroscedastic
(variance grows with volume) and occasionally bimodal when a crop either
makes it or fails. A single parametric family fitted to all of that will
misfit somewhere, and it usually misfits in the lower tail — precisely the
region the optimizer is most exposed to. Quantile regression assumes no
distributional shape at all and estimates each level directly.

Direct evidence for this class on crop yield: Gyamerah, S.A., Ngare, P. &
Ikpe, D. (2019), "Probabilistic forecasting of crop yields via quantile
random forest and Epanechnikov kernel function," *Agricultural and Forest
Meteorology* 280:107808. doi:10.1016/j.agrformet.2019.107808 — quantile
forests applied to exactly this problem. Boosted quantile regression is
the same idea with a different base learner and generally sharper fits on
tabular features; the quantile-forest variant is retained as a challenger.

QUANTILE CROSSING
-----------------
Independently fitted quantile models can cross. This class does NOT sort
silently. It detects crossing, records it in the forecast's warnings, and
applies the Chernozhukov-Fernández-Val-Galichon rearrangement — a
principled estimator that provably does not increase error — so the repair
is explicit and auditable.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import numpy as np

from forecasting.supply_uncertainty.baseline import classify_data_tier
from forecasting.supply_uncertainty.conformal import (
    MondrianConformalCalibrator,
    split_time_aware,
)
from forecasting.supply_uncertainty.contract import (
    QUANTILE_LEVELS,
    ProbabilisticForecast,
    QuantityKind,
    confidence_for_tier,
    rearrange,
)


def _lightgbm_available() -> bool:
    try:
        import lightgbm  # noqa: F401
        return True
    except Exception:
        return False


class _LinearQuantileRegressor:
    """Pinball-loss linear regression by subgradient descent.

    The dependency-free fallback. Deliberately simple: its role is to keep
    the pipeline runnable and testable without LightGBM, not to compete.
    """

    def __init__(self, level: float, n_iter: int = 600, lr: float = 0.05, seed: int = 0):
        self.level = level
        self.n_iter = n_iter
        self.lr = lr
        self.seed = seed
        self.coef_: np.ndarray | None = None
        self.intercept_: float = 0.0
        self._mu: np.ndarray | None = None
        self._sd: np.ndarray | None = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "_LinearQuantileRegressor":
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        self._mu = X.mean(axis=0)
        self._sd = np.where(X.std(axis=0) > 1e-9, X.std(axis=0), 1.0)
        Xs = (X - self._mu) / self._sd
        n, p = Xs.shape
        self.coef_ = np.zeros(p)
        self.intercept_ = float(np.quantile(y, self.level))
        for it in range(self.n_iter):
            pred = Xs @ self.coef_ + self.intercept_
            resid = y - pred
            # Pinball subgradient: tau where under-predicting, tau-1 over.
            g = np.where(resid >= 0, self.level, self.level - 1.0)
            lr = self.lr / (1.0 + it / 100.0)
            self.coef_ += lr * (Xs.T @ g) / n
            self.intercept_ += lr * float(g.mean())
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        Xs = (X - self._mu) / self._sd
        return Xs @ self.coef_ + self.intercept_


class GradientBoostedQuantileModel:
    """Quantile regression across a grid, with conformal calibration."""

    model_family = "lgbm_quantile_cqr"
    model_version = "1.0"

    def __init__(
        self,
        quantile_levels: tuple[float, ...] = QUANTILE_LEVELS,
        alpha: float = 0.10,
        n_estimators: int = 200,
        learning_rate: float = 0.05,
        num_leaves: int = 15,
        min_child_samples: int = 5,
        calibration_fraction: float = 0.3,
        seed: int = 42,
        force_linear: bool = False,
    ):
        self.quantile_levels = tuple(sorted(quantile_levels))
        self.alpha = alpha
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.num_leaves = num_leaves
        self.min_child_samples = min_child_samples
        self.calibration_fraction = calibration_fraction
        self.seed = seed
        self.use_lgbm = (not force_linear) and _lightgbm_available()

        self.models: dict[float, object] = {}
        self.calibrator: MondrianConformalCalibrator | None = None
        self.feature_names: list[str] = []
        self.training_cutoff: date | None = None
        self.n_train: int = 0
        self.fit_warnings: list[str] = []

    # -- fitting ---------------------------------------------------------
    def _make_model(self, level: float):
        if self.use_lgbm:
            import lightgbm as lgb
            return lgb.LGBMRegressor(
                objective="quantile", alpha=level,
                n_estimators=self.n_estimators,
                learning_rate=self.learning_rate,
                num_leaves=self.num_leaves,
                min_child_samples=self.min_child_samples,
                random_state=self.seed, verbose=-1,
            )
        return _LinearQuantileRegressor(level=level, seed=self.seed)

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: list[str] | None = None,
        calibration_groups: np.ndarray | None = None,
        training_cutoff: date | None = None,
        sorted_by_time: bool = True,
    ) -> "GradientBoostedQuantileModel":
        """Fit quantile models, then calibrate on a held-out recent block.

        ``sorted_by_time`` must be True and the rows genuinely ordered
        oldest-first: the calibration split is chronological, and applying
        it to unsorted rows would silently calibrate on a random subset —
        leaking the future and voiding the point of the exercise.
        """
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        if not sorted_by_time:
            raise ValueError(
                "rows must be sorted oldest-first: conformal calibration "
                "uses a chronological split and an unsorted frame would "
                "calibrate on future data")

        self.feature_names = feature_names or [f"f{i}" for i in range(X.shape[1])]
        self.training_cutoff = training_cutoff
        self.n_train = int(len(y))
        self.fit_warnings = []

        train_idx, cal_idx = split_time_aware(len(y), self.calibration_fraction)
        if cal_idx.size == 0:
            self.fit_warnings.append(
                "too few rows to hold out a calibration set; intervals are "
                "uncalibrated")

        Xtr, ytr = X[train_idx], y[train_idx]
        for lv in self.quantile_levels:
            self.models[lv] = self._make_model(lv).fit(Xtr, ytr)

        if cal_idx.size > 0:
            lo_lv, hi_lv = self.alpha / 2.0, 1.0 - self.alpha / 2.0
            lo_lv = min(self.quantile_levels, key=lambda q: abs(q - lo_lv))
            hi_lv = min(self.quantile_levels, key=lambda q: abs(q - hi_lv))
            q_lo = np.asarray(self.models[lo_lv].predict(X[cal_idx]), dtype=float)
            q_hi = np.asarray(self.models[hi_lv].predict(X[cal_idx]), dtype=float)
            groups = (np.asarray(calibration_groups)[cal_idx]
                      if calibration_groups is not None
                      else np.zeros(cal_idx.size, dtype=int))
            cal = MondrianConformalCalibrator(alpha=self.alpha)
            cal.fit(y[cal_idx], q_lo, q_hi, groups)
            self.calibrator = cal if cal.is_usable else None
            if self.calibrator is None:
                self.fit_warnings.append(
                    f"calibration set of {cal_idx.size} rows is too small for "
                    f"alpha={self.alpha}; intervals are uncalibrated")
        return self

    # -- prediction ------------------------------------------------------
    def predict_quantiles(
        self, X: np.ndarray, calibration_groups: np.ndarray | None = None,
    ) -> tuple[dict[float, np.ndarray], list[str]]:
        """Raw quantile grid, rearranged and conformally calibrated."""
        if not self.models:
            raise RuntimeError("model not fitted")
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)

        preds = {lv: np.maximum(
            np.asarray(self.models[lv].predict(X), dtype=float), 0.0)
            for lv in self.quantile_levels}

        warnings: list[str] = []
        # Detect crossing BEFORE repairing it, so it is reported.
        levels = list(self.quantile_levels)
        stacked = np.vstack([preds[lv] for lv in levels])
        n_crossed = int(np.sum(np.diff(stacked, axis=0) < -1e-9))
        if n_crossed:
            warnings.append(
                f"quantile crossing at {n_crossed} point(s); monotone "
                "rearrangement applied (Chernozhukov et al. 2010)")
            fixed = np.sort(stacked, axis=0)
            preds = {lv: fixed[i] for i, lv in enumerate(levels)}

        if self.calibrator is not None:
            lo_lv, hi_lv = levels[0], levels[-1]
            groups = (np.asarray(calibration_groups)
                      if calibration_groups is not None
                      else np.zeros(X.shape[0], dtype=int))
            lo, hi = self.calibrator.apply(preds[lo_lv], preds[hi_lv], groups)
            # Widen the outermost pair, then re-monotonise so the interior
            # levels stay inside the calibrated envelope.
            preds[lo_lv], preds[hi_lv] = lo, hi
            stacked = np.sort(np.vstack([preds[lv] for lv in levels]), axis=0)
            preds = {lv: stacked[i] for i, lv in enumerate(levels)}
        return preds, warnings

    def predict_one(
        self,
        x: np.ndarray,
        entity_key: dict,
        target_start: date,
        target_end: date,
        information_cutoff: datetime,
        issued_at: datetime | None = None,
        unit: str = "kg",
        quantity_kind: QuantityKind = QuantityKind.AVAILABLE_SUPPLY,
        n_observations: int = 0,
        n_seasons: int | None = None,
        calibration_group=None,
    ) -> ProbabilisticForecast:
        """A single validated ProbabilisticForecast."""
        groups = (np.array([calibration_group])
                  if calibration_group is not None else None)
        preds, warns = self.predict_quantiles(
            np.asarray(x, dtype=float).reshape(1, -1), groups)
        q = rearrange({lv: float(v[0]) for lv, v in preds.items()})

        tier = classify_data_tier(n_observations, n_seasons)
        calibrated = self.calibrator is not None
        fc = ProbabilisticForecast(
            forecast_id=str(uuid.uuid4()),
            issued_at=issued_at or datetime.now(timezone.utc),
            information_cutoff=information_cutoff,
            target_start=target_start,
            target_end=target_end,
            entity_key=entity_key,
            quantity_kind=quantity_kind,
            unit=unit,
            quantiles=q,
            mean=q[0.50],
            model_family=self.model_family,
            model_version=self.model_version,
            training_cutoff=self.training_cutoff,
            random_seed=self.seed,
            data_tier=tier,
            confidence=confidence_for_tier(tier),
            calibrated=calibrated,
            calibration_method=("split-conformal CQR (Romano et al. 2019), "
                                "Mondrian by group") if calibrated else None,
            calibration_group=(str(calibration_group)
                               if calibration_group is not None else None),
            n_observations=n_observations,
            warnings=list(warns) + list(self.fit_warnings),
            drivers=self._drivers(),
        )
        fc.validate()
        return fc

    def _drivers(self) -> list[str]:
        out = [f"{'LightGBM' if self.use_lgbm else 'linear'} quantile "
               f"regression on {self.n_train} rows"]
        if self.use_lgbm and self.models:
            m = self.models.get(0.50)
            imp = getattr(m, "feature_importances_", None)
            if imp is not None and len(imp) == len(self.feature_names):
                top = sorted(zip(self.feature_names, imp),
                             key=lambda t: -t[1])[:3]
                names = [n for n, v in top if v > 0]
                if names:
                    out.append("top drivers: " + ", ".join(names))
        if self.calibrator is not None:
            out.append(f"intervals conformally calibrated at "
                       f"alpha={self.alpha}")
        return out
