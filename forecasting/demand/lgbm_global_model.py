"""Global LightGBM demand forecasting model.

Trains a single LightGBM model across all product×buyer series.
Produces point forecasts with conformal prediction intervals.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from forecasting.demand.feature_engineering import (
    FEATURE_COLS,
    OPTIONAL_FEATURE_COLS,
    TARGET_COL,
    build_features,
)


class LGBMDemandModel:
    def __init__(
        self,
        n_estimators: int = 500,
        learning_rate: float = 0.05,
        max_depth: int = 6,
        num_leaves: int = 63,
        min_child_samples: int = 20,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        conformal_alpha: float = 0.80,
        seed: int = 42,
    ) -> None:
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.num_leaves = num_leaves
        self.min_child_samples = min_child_samples
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.conformal_alpha = conformal_alpha
        self.seed = seed
        self._model = None
        self._feature_cols: list[str] = []
        self._calibration_residuals: np.ndarray = np.array([])

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def fit(
        self,
        orders_df: pd.DataFrame,
        weather_df: pd.DataFrame | None = None,
        price_df: pd.DataFrame | None = None,
        val_cutoff: str | pd.Timestamp | None = None,
    ) -> "LGBMDemandModel":
        import lightgbm as lgb

        feature_df = build_features(orders_df, weather_df, price_df)
        feature_df = feature_df.dropna(subset=[TARGET_COL])

        available = FEATURE_COLS + [c for c in OPTIONAL_FEATURE_COLS if c in feature_df.columns]
        self._feature_cols = [c for c in available if c in feature_df.columns]

        train_df = feature_df.dropna(subset=self._feature_cols)

        if val_cutoff is not None:
            cutoff = pd.to_datetime(val_cutoff)
            val_df = train_df[train_df["week_start"] >= cutoff]
            train_df = train_df[train_df["week_start"] < cutoff]
        else:
            cutoff = train_df["week_start"].quantile(0.80)
            val_df = train_df[train_df["week_start"] >= cutoff]
            train_df = train_df[train_df["week_start"] < cutoff]

        X_train = train_df[self._feature_cols]
        y_train = train_df[TARGET_COL]
        X_val = val_df[self._feature_cols]
        y_val = val_df[TARGET_COL]

        params = {
            "objective": "tweedie",
            "tweedie_variance_power": 1.5,
            "n_estimators": self.n_estimators,
            "learning_rate": self.learning_rate,
            "max_depth": self.max_depth,
            "num_leaves": self.num_leaves,
            "min_child_samples": self.min_child_samples,
            "subsample": self.subsample,
            "colsample_bytree": self.colsample_bytree,
            "random_state": self.seed,
            "n_jobs": -1,
            "verbose": -1,
        }

        self._model = lgb.LGBMRegressor(**params)
        self._model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(-1)],
        )

        val_preds = np.maximum(0, self._model.predict(X_val))
        self._calibration_residuals = np.abs(y_val.values - val_preds)
        return self

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict(
        self,
        orders_df: pd.DataFrame,
        forecast_weeks: int = 4,
        weather_df: pd.DataFrame | None = None,
        price_df: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        """Return DataFrame: product_id, buyer_id, week_start, forecast_kg, intervals, model."""
        if self._model is None:
            raise RuntimeError("Model not fitted. Call .fit() first.")

        feature_df = build_features(orders_df, weather_df, price_df)
        feature_df = feature_df.dropna(subset=self._feature_cols)

        X = feature_df[self._feature_cols].fillna(0)
        preds = np.maximum(0, self._model.predict(X))

        q80 = float(np.quantile(self._calibration_residuals, self.conformal_alpha)) if len(self._calibration_residuals) > 0 else 0.0
        q95 = float(np.quantile(self._calibration_residuals, 0.95)) if len(self._calibration_residuals) > 0 else 0.0

        out = feature_df[["product_id", "buyer_id", "week_start"]].copy()
        out["forecast_kg"] = np.round(np.maximum(0, preds), 2)
        out["lower_80"] = np.maximum(0, out["forecast_kg"] - q80).round(2)
        out["upper_80"] = (out["forecast_kg"] + q80).round(2)
        out["lower_95"] = np.maximum(0, out["forecast_kg"] - q95).round(2)
        out["upper_95"] = (out["forecast_kg"] + q95).round(2)
        out["model"] = "lgbm_global"

        last_observed = pd.to_datetime(orders_df["week_start"]).max()
        horizon_rows = out[out["week_start"] > last_observed]
        n_ids = len(out["product_id"].unique()) * len(out["buyer_id"].unique())
        return horizon_rows.head(forecast_weeks * n_ids).reset_index(drop=True)

    # ------------------------------------------------------------------
    # Persistence (LightGBM native format — no pickle)
    # ------------------------------------------------------------------

    def save(self, directory: str | Path) -> None:
        """Save model to directory using LightGBM's native txt format."""
        d = Path(directory)
        d.mkdir(parents=True, exist_ok=True)
        if self._model is not None:
            self._model.booster_.save_model(str(d / "lgbm_model.txt"))
        meta = {
            "feature_cols": self._feature_cols,
            "calibration_residuals": self._calibration_residuals.tolist(),
            "params": {
                "n_estimators": self.n_estimators,
                "learning_rate": self.learning_rate,
                "max_depth": self.max_depth,
                "num_leaves": self.num_leaves,
                "conformal_alpha": self.conformal_alpha,
            },
        }
        (d / "meta.json").write_text(json.dumps(meta))

    @classmethod
    def load(cls, directory: str | Path) -> "LGBMDemandModel":
        import lightgbm as lgb
        d = Path(directory)
        meta = json.loads((d / "meta.json").read_text())
        inst = cls(**meta["params"])
        inst._feature_cols = meta["feature_cols"]
        inst._calibration_residuals = np.array(meta["calibration_residuals"])
        booster = lgb.Booster(model_file=str(d / "lgbm_model.txt"))
        inst._model = lgb.LGBMRegressor()
        inst._model._Booster = booster  # attach pre-loaded booster
        return inst

    @property
    def feature_importance(self) -> pd.DataFrame:
        if self._model is None:
            return pd.DataFrame()
        return pd.DataFrame({
            "feature": self._feature_cols,
            "importance": self._model.feature_importances_,
        }).sort_values("importance", ascending=False).reset_index(drop=True)
