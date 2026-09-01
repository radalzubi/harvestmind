"""Demand forecasting service: wires the System A models over staging data.

This is the single entry point the API and the scenario generator use. It
does four things, all on the operator's own order history:

1. Aggregates ``stg_buyer_orders`` to a weekly product×buyer grid.
2. Routes each product to the right model: the global LightGBM model for
   dense series, Croston-family for intermittent ones (mostly-zero weeks).
3. Evaluates honestly: rolling-origin, out-of-sample, WAPE / MASE-ratio /
   bias ONLY (never MAPE — division by near-zero actuals makes MAPE
   meaningless on intermittent grocery demand). The headline gate is
   model-vs-seasonal-naive on held-out weeks: if the model does not beat
   the naive, ``gate_passed`` is False and callers must say so.
4. Produces a per-product demand DISTRIBUTION (median + conformal
   quantiles from held-out residuals), not just a point forecast, so the
   stochastic optimizer downstream sees forecast uncertainty.

What "learning" means here: the model is fit to historical data when
``fit``/``evaluate`` is called, and improves only when retrained on new
data. Nothing learns autonomously online.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

# A product is treated as intermittent when more than this fraction of its
# weekly buckets are zero — Croston-family models exist for exactly this.
INTERMITTENT_ZERO_FRACTION = 0.60

# Quantiles exposed on the forecast distribution.
QUANTILES = (0.10, 0.25, 0.50, 0.75, 0.90)


# ── Data access ──────────────────────────────────────────────────────────────

def weekly_orders_from_staging(conn) -> pd.DataFrame:
    """Weekly product×buyer demand grid from stg_buyer_orders.

    Columns: product_id (carries product NAME — the reliably populated
    key), buyer_id, week_start (Monday), qty_ordered_kg. Missing weeks are
    NOT zero-filled here; feature engineering builds the complete grid.
    """
    df = conn.execute("""
        SELECT product_name,
               COALESCE(buyer_id, buyer_name, 'unknown') AS buyer_id,
               COALESCE(delivery_date, order_date)        AS d,
               SUM(requested_quantity)                    AS qty
        FROM stg_buyer_orders
        WHERE product_name IS NOT NULL
          AND requested_quantity IS NOT NULL
          AND COALESCE(delivery_date, order_date) IS NOT NULL
        GROUP BY 1, 2, 3
    """).df()
    if df.empty:
        return pd.DataFrame(columns=["product_id", "buyer_id", "week_start",
                                     "qty_ordered_kg"])
    df["week_start"] = (
        pd.to_datetime(df["d"]).dt.to_period("W-SUN").dt.start_time
    )
    out = (
        df.groupby(["product_name", "buyer_id", "week_start"])["qty"]
        .sum().reset_index()
        .rename(columns={"product_name": "product_id", "qty": "qty_ordered_kg"})
    )
    return out


# ── Baselines (the yardsticks the model must beat) ───────────────────────────

def seasonal_naive_forecast(
    history: pd.DataFrame, target_weeks: list[pd.Timestamp],
) -> dict[tuple, float]:
    """Seasonal-naive per product: same ISO week one year earlier; falls
    back to the trailing 4-week weekly run-rate when no year-ago data
    exists (the fair fallback — never the mean delivery size)."""
    hist = history.groupby(["product_id", "week_start"])["qty_ordered_kg"].sum()
    out: dict[tuple, float] = {}
    products = history["product_id"].unique()
    last_week = pd.Timestamp(history["week_start"].max())
    trailing = history[history["week_start"] > last_week - pd.DateOffset(weeks=4)]
    runrate = (trailing.groupby("product_id")["qty_ordered_kg"].sum() / 4.0)
    for p in products:
        for raw_week in target_weeks:
            w = pd.Timestamp(raw_week)
            year_ago = w - pd.DateOffset(weeks=52)
            val = hist.get((p, year_ago))
            if val is None or pd.isna(val):
                val = float(runrate.get(p, 0.0))
            out[(p, w)] = float(val)
    return out


# ── Metrics (WAPE / MASE-ratio / bias — never MAPE) ──────────────────────────

def wape(actual: np.ndarray, forecast: np.ndarray) -> float:
    """Weighted absolute percentage error: Σ|e| / Σ|y|. Scale-free and
    well-defined on intermittent series, unlike MAPE."""
    actual = np.asarray(actual, float)
    forecast = np.asarray(forecast, float)
    denom = np.abs(actual).sum()
    if denom == 0:
        return float("nan")
    return float(np.abs(actual - forecast).sum() / denom)


def bias_pct(actual: np.ndarray, forecast: np.ndarray) -> float:
    actual = np.asarray(actual, float)
    forecast = np.asarray(forecast, float)
    denom = actual.sum()
    if denom == 0:
        return float("nan")
    return float((forecast - actual).sum() / denom * 100.0)


# ── Model routing ────────────────────────────────────────────────────────────

def classify_products(weekly: pd.DataFrame) -> dict[str, str]:
    """Route each product to 'lgbm' (dense) or 'croston' (intermittent)."""
    routes: dict[str, str] = {}
    prod = weekly.groupby(["product_id", "week_start"])["qty_ordered_kg"].sum()
    for p, series in prod.groupby(level=0):
        # zero-fill over the product's own observed span
        weeks = pd.date_range(series.index.get_level_values(1).min(),
                              series.index.get_level_values(1).max(), freq="W-MON")
        vals = series.droplevel(0).reindex(weeks, fill_value=0.0).values
        zero_frac = float((vals == 0).mean()) if len(vals) else 1.0
        routes[p] = "croston" if zero_frac >= INTERMITTENT_ZERO_FRACTION else "lgbm"
    return routes


# ── Forecast result ──────────────────────────────────────────────────────────

@dataclass
class DemandForecast:
    """Per-product forecast distribution for the coming horizon."""
    as_of: str
    horizon_weeks: int
    products: list[dict] = field(default_factory=list)   # per-product dicts
    model_info: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "as_of": self.as_of,
            "horizon_weeks": self.horizon_weeks,
            "products": self.products,
            "model_info": self.model_info,
        }


def _weather_frame(conn) -> pd.DataFrame | None:
    """Weekly weather features from fact_weather_obs, or None.

    Weather is an OPTIONAL feature set: when no observations are loaded
    the forecaster runs exactly as before. The frame covers all loaded
    counties aggregated; per-county weighting becomes worth building once
    an operator's supplier locations are known.
    """
    try:
        from ingestion.weather_features import weekly_weather_frame
        df = weekly_weather_frame(conn)
        return df if not df.empty else None
    except Exception:
        return None


def _fit_lgbm(weekly: pd.DataFrame, weather_df: pd.DataFrame | None = None):
    from forecasting.demand.lgbm_global_model import LGBMDemandModel
    model = LGBMDemandModel(n_estimators=300)
    model.fit(weekly, weather_df=weather_df)
    return model


def _product_point_forecasts(
    weekly: pd.DataFrame,
    horizon_weeks: int,
    routes: dict[str, str],
    weather_df: pd.DataFrame | None = None,
) -> tuple[dict[str, float], dict[str, str], Any]:
    """Weekly point forecast per product and the model used per product.

    The LGBM model forecasts one week ahead; the weekly rate is held flat
    across deeper horizons (stated, not hidden). Returns
    (point, model_used, lgbm_model); any LGBM failure is recorded in
    model_used as a named fallback, never swallowed silently.

    When ``weather_df`` is provided its columns join the feature grid
    (build_features), so the trees can split on temperature, heat stress,
    precipitation, and ENSO where they carry signal. The target week's
    weather row acts as the weather forecast for that week — a stated
    assumption, reasonable one week out.
    """
    point: dict[str, float] = {}
    model_used: dict[str, str] = {}
    lgbm_model = None
    lgbm_error: str | None = None

    dense_products = [p for p, r in routes.items() if r == "lgbm"]
    if dense_products:
        dense = weekly[weekly["product_id"].isin(dense_products)]
        try:
            lgbm_model = _fit_lgbm(dense, weather_df)
            preds = lgbm_model.predict(dense, forecast_weeks=horizon_weeks,
                                       weather_df=weather_df)
            if not preds.empty:
                per_prod = (preds.groupby(["product_id", "week_start"])["forecast_kg"]
                            .sum().groupby(level=0).mean())
                for p, v in per_prod.items():
                    point[p] = float(v)
                    model_used[p] = "lgbm_global"
        except Exception as e:  # noqa: BLE001
            lgbm_model = None
            lgbm_error = f"{type(e).__name__}: {e}"

    # Croston-family for intermittent products
    from forecasting.demand.intermittent_model import select_and_fit
    prod_series = weekly.groupby(["product_id", "week_start"])["qty_ordered_kg"].sum()
    for p, r in routes.items():
        if p in point:
            continue
        series = prod_series.loc[p]
        weeks = pd.date_range(series.index.min(), series.index.max(), freq="W-MON")
        vals = series.reindex(weeks, fill_value=0.0).values
        if r == "croston" or lgbm_model is None:
            try:
                fc = select_and_fit(np.asarray(vals, float), horizon=1)
                point[p] = float(max(fc.point, 0.0))
                model_used[p] = f"intermittent_{fc.model}"
                continue
            except Exception:
                pass
        # last resort: trailing 4-week run-rate; carry the reason
        point[p] = float(np.asarray(vals[-4:], float).sum() / min(len(vals), 4))
        model_used[p] = (f"runrate_fallback ({lgbm_error})"
                         if lgbm_error else "runrate_fallback")
    return point, model_used, lgbm_model


def _drivers_for_product(
    p: str,
    forecast_val: float,
    weekly: pd.DataFrame,
    lgbm_model,
    model_used: str,
) -> list[str]:
    """Plain-language drivers, described as the arithmetic they are."""
    drivers: list[str] = []
    prod = (weekly[weekly["product_id"] == p]
            .groupby("week_start")["qty_ordered_kg"].sum().sort_index())
    if len(prod) >= 4:
        recent = float(prod.tail(4).mean())
        if recent > 0:
            delta = (forecast_val - recent) / recent * 100.0
            if abs(delta) >= 5:
                drivers.append(
                    f"forecast {delta:+.0f}% vs trailing 4-week average "
                    f"({recent:,.0f} kg/wk)"
                )
    if len(prod) >= 52:
        year_ago = float(prod.iloc[-52:-48].mean())
        if year_ago > 0:
            yoy = (forecast_val - year_ago) / year_ago * 100.0
            if abs(yoy) >= 5:
                drivers.append(f"{yoy:+.0f}% vs same weeks last year")
    if model_used == "lgbm_global" and lgbm_model is not None:
        top = lgbm_model.feature_importance.head(3)["feature"].tolist()
        if top:
            drivers.append(f"model signals: {', '.join(top)}")
    elif model_used.startswith("intermittent"):
        drivers.append("intermittent series — demand-interval model "
                       f"({model_used.split('_', 1)[1]})")
    if not drivers:
        drivers.append("stable recent demand; forecast tracks the run-rate")
    return drivers


def forecast_demand(
    conn,
    horizon_weeks: int = 4,
) -> DemandForecast:
    """Fit on all staged history and forecast the next horizon, with a
    conformal residual distribution per product from a held-out tail."""
    weekly = weekly_orders_from_staging(conn)
    as_of = str(weekly["week_start"].max().date()) if not weekly.empty else None
    if weekly.empty or weekly["week_start"].nunique() < 8:
        return DemandForecast(as_of=as_of or "", horizon_weeks=horizon_weeks,
                              products=[],
                              model_info={"status": "insufficient_history",
                                          "min_weeks_required": 8})

    routes = classify_products(weekly)
    weather_df = _weather_frame(conn)

    # Held-out residuals for the distribution: forecast the last 4 observed
    # weeks from the history before them, residual = actual − forecast.
    weeks_sorted = sorted(weekly["week_start"].unique())
    cut = weeks_sorted[-4]
    train = weekly[weekly["week_start"] < cut]
    holdout = weekly[weekly["week_start"] >= cut]
    resid: dict[str, list[float]] = {}
    if not train.empty and train["week_start"].nunique() >= 8:
        h_point, _, _ = _product_point_forecasts(train, 4, classify_products(train),
                                                 weather_df)
        actual = holdout.groupby(["product_id", "week_start"])["qty_ordered_kg"].sum()
        for (p, w), a in actual.items():
            if p in h_point:
                resid.setdefault(p, []).append(float(a) - h_point[p])

    point, model_used, lgbm_model = _product_point_forecasts(
        weekly, horizon_weeks, routes, weather_df)

    products = []
    for p in sorted(point):
        med = point[p]
        r = np.asarray(resid.get(p, [0.0]), float)
        qs = {f"q{int(q * 100)}": float(max(med + np.quantile(r, q), 0.0))
              for q in QUANTILES}
        products.append({
            "product_name": p,
            "model": model_used[p],
            "forecast_kg_per_week": round(med, 1),
            "quantiles_kg": {k: round(v, 1) for k, v in qs.items()},
            "n_holdout_residuals": int(len(resid.get(p, []))),
            "drivers": _drivers_for_product(p, med, weekly, lgbm_model,
                                            model_used[p]),
        })

    return DemandForecast(
        as_of=as_of, horizon_weeks=horizon_weeks, products=products,
        model_info={
            "status": "ok",
            "n_products": len(products),
            "models_used": {
                m: sum(1 for v in model_used.values() if v.split(" ")[0] == m or
                       v.startswith(m))
                for m in sorted({v.split(" ")[0] for v in model_used.values()})
            },
            "uncertainty": "conformal residuals from a 4-week holdout",
            "weather_features_used": weather_df is not None,
            "weather_weeks_available": (int(len(weather_df))
                                        if weather_df is not None else 0),
        },
    )


# ── Rolling-origin evaluation (the gate) ─────────────────────────────────────

def evaluate_demand_forecaster(
    conn,
    n_folds: int = 4,
    horizon_weeks: int = 1,
) -> dict[str, Any]:
    """Rolling-origin out-of-sample evaluation against seasonal-naive.

    For each fold: train on weeks < origin, forecast the next
    ``horizon_weeks``, score vs actuals. Metrics: WAPE, bias, and the
    MASE-style ratio WAPE(model)/WAPE(seasonal-naive) computed strictly
    out-of-sample.

    GATE: ``gate_passed`` is True only when the model's pooled OOS WAPE
    beats seasonal-naive (ratio < 1). When False, the honest verdict is
    that the naive is the better forecaster on this data — say so, do not
    ship the model output as if it added value.
    """
    weekly = weekly_orders_from_staging(conn)
    if weekly.empty or weekly["week_start"].nunique() < 16:
        return {"status": "insufficient_history",
                "weeks_available": int(weekly["week_start"].nunique())
                if not weekly.empty else 0,
                "gate_passed": None}

    weather_df = _weather_frame(conn)
    weeks_sorted = sorted(weekly["week_start"].unique())
    fold_rows = []
    model_abs_err = naive_abs_err = actual_total = 0.0
    model_sum = actual_sum = 0.0

    for k in range(n_folds):
        origin_idx = len(weeks_sorted) - (n_folds - k) * horizon_weeks
        if origin_idx < 12:
            continue
        origin = weeks_sorted[origin_idx]
        target_weeks = weeks_sorted[origin_idx: origin_idx + horizon_weeks]
        train = weekly[weekly["week_start"] < origin]
        test = weekly[weekly["week_start"].isin(target_weeks)]
        if train.empty or test.empty:
            continue

        # Leakage guard: the fold's model may see weather only up to the
        # end of its target window (the target week's weather stands in
        # for a 1-week-ahead weather forecast — a stated assumption).
        fold_weather = None
        if weather_df is not None:
            fold_weather = weather_df[
                weather_df["week_start"] <= max(target_weeks)]
            if fold_weather.empty:
                fold_weather = None

        point, _, _ = _product_point_forecasts(
            train, horizon_weeks, classify_products(train), fold_weather)
        snaive = seasonal_naive_forecast(train, list(target_weeks))

        actual = test.groupby(["product_id", "week_start"])["qty_ordered_kg"].sum()
        y, yhat, ynaive = [], [], []
        for (p, w), a in actual.items():
            if p not in point:
                continue
            y.append(float(a))
            yhat.append(point[p])
            ynaive.append(snaive.get((p, w), 0.0))
        if not y:
            continue
        y_arr, m_arr, n_arr = map(np.asarray, (y, yhat, ynaive))
        fold_rows.append({
            "fold": k, "origin": str(pd.Timestamp(origin).date()),
            "n_series": len(y),
            "wape_model": round(wape(y_arr, m_arr), 4),
            "wape_seasonal_naive": round(wape(y_arr, n_arr), 4),
            "bias_pct_model": round(bias_pct(y_arr, m_arr), 2),
        })
        model_abs_err += float(np.abs(y_arr - m_arr).sum())
        naive_abs_err += float(np.abs(y_arr - n_arr).sum())
        actual_total += float(np.abs(y_arr).sum())
        model_sum += float(m_arr.sum())
        actual_sum += float(y_arr.sum())

    if not fold_rows or actual_total == 0:
        return {"status": "insufficient_history", "gate_passed": None}

    wape_model = model_abs_err / actual_total
    wape_naive = naive_abs_err / actual_total if naive_abs_err else float("nan")
    ratio = wape_model / wape_naive if wape_naive and not np.isnan(wape_naive) \
        else float("nan")

    return {
        "status": "ok",
        "folds": fold_rows,
        "wape_model": round(wape_model, 4),
        "wape_seasonal_naive": round(wape_naive, 4),
        "oos_mase_ratio": round(ratio, 4) if not np.isnan(ratio) else None,
        "bias_pct_model": round((model_sum - actual_sum) / actual_sum * 100, 2)
        if actual_sum else None,
        "gate_passed": bool(ratio < 1.0) if not np.isnan(ratio) else None,
        "gate_rule": "model must beat seasonal-naive out-of-sample "
                     "(WAPE ratio < 1); otherwise the naive is the honest "
                     "forecaster for this data",
        "metrics_policy": "WAPE / OOS-MASE-ratio / bias only; MAPE is never "
                          "used (undefined on intermittent demand)",
        "weather_features_used": weather_df is not None,
    }
