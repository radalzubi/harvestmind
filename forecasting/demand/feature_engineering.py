"""Feature engineering for LightGBM global demand model.

Builds a cross-sectional time-series feature matrix from order history.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


LAG_WEEKS = [1, 2, 3, 4, 8, 12, 13, 26, 52]
ROLLING_WINDOWS = [4, 8, 13]  # weeks


def build_features(
    orders_df: pd.DataFrame,
    weather_df: pd.DataFrame | None = None,
    price_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build LightGBM feature matrix.

    Parameters
    ----------
    orders_df : DataFrame with columns [product_id, buyer_id, week_start, qty_ordered_kg]
    weather_df : optional DataFrame [week_start, tavg_c, precip_mm, heat_stress_flag, enso_oni_index]
    price_df   : optional DataFrame [week_start, product_id, avg_price]

    Returns
    -------
    DataFrame with one row per (product_id, buyer_id, week_start), target column = qty_ordered_kg.
    """
    df = orders_df.copy()
    df["week_start"] = pd.to_datetime(df["week_start"])
    df = df.sort_values(["product_id", "buyer_id", "week_start"])

    # Create complete grid (fill missing weeks with 0)
    products = df["product_id"].unique()
    buyers = df["buyer_id"].unique()
    weeks = pd.date_range(df["week_start"].min(), df["week_start"].max(), freq="W-MON")

    idx = pd.MultiIndex.from_product([products, buyers, weeks], names=["product_id", "buyer_id", "week_start"])
    full = pd.DataFrame(index=idx).reset_index()
    df = full.merge(df[["product_id","buyer_id","week_start","qty_ordered_kg"]], on=["product_id","buyer_id","week_start"], how="left")
    df["qty_ordered_kg"] = df["qty_ordered_kg"].fillna(0.0)

    # Temporal features
    df["iso_week"] = df["week_start"].dt.isocalendar().week.astype(int)
    df["month"] = df["week_start"].dt.month
    df["quarter"] = df["week_start"].dt.quarter
    df["year"] = df["week_start"].dt.year
    df["week_sin"] = np.sin(2 * np.pi * df["iso_week"] / 52)
    df["week_cos"] = np.cos(2 * np.pi * df["iso_week"] / 52)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

    # Lags and rolling stats per product×buyer series
    grp = df.groupby(["product_id", "buyer_id"])["qty_ordered_kg"]

    for lag in LAG_WEEKS:
        df[f"lag_{lag}w"] = grp.shift(lag)

    for win in ROLLING_WINDOWS:
        df[f"roll_mean_{win}w"] = grp.transform(lambda x: x.shift(1).rolling(win, min_periods=2).mean())
        df[f"roll_std_{win}w"] = grp.transform(lambda x: x.shift(1).rolling(win, min_periods=2).std())

    # Global product-level lags (sum across all buyers, useful signal for supply planning)
    prod_weekly = df.groupby(["product_id", "week_start"])["qty_ordered_kg"].sum().rename("prod_total_kg")
    df = df.merge(prod_weekly.reset_index(), on=["product_id","week_start"], how="left")
    df["prod_lag_1w"] = df.groupby("product_id")["prod_total_kg"].shift(1)
    df["prod_lag_4w"] = df.groupby("product_id")["prod_total_kg"].shift(4)
    df["prod_roll_mean_8w"] = df.groupby("product_id")["prod_total_kg"].transform(
        lambda x: x.shift(1).rolling(8, min_periods=2).mean()
    )

    # Encode categoricals as integer codes
    df["product_code"] = df["product_id"].astype("category").cat.codes
    df["buyer_code"] = df["buyer_id"].astype("category").cat.codes

    # Join weather features
    if weather_df is not None:
        w = weather_df.copy()
        w["week_start"] = pd.to_datetime(w["week_start"])
        w = w[["week_start","tavg_c","precip_mm","heat_stress_flag","enso_oni_index"]].drop_duplicates("week_start")
        df = df.merge(w, on="week_start", how="left")
        df["heat_stress_flag"] = df["heat_stress_flag"].fillna(False).astype(int)

    # Join price features
    if price_df is not None:
        p = price_df.copy()
        p["week_start"] = pd.to_datetime(p["week_start"])
        p = p[["week_start","product_id","avg_price"]].drop_duplicates(["week_start","product_id"])
        df = df.merge(p, on=["week_start","product_id"], how="left")

    return df


FEATURE_COLS = [
    "product_code", "buyer_code",
    "iso_week", "month", "quarter",
    "week_sin", "week_cos", "month_sin", "month_cos",
    *[f"lag_{l}w" for l in LAG_WEEKS],
    *[f"roll_mean_{w}w" for w in ROLLING_WINDOWS],
    *[f"roll_std_{w}w" for w in ROLLING_WINDOWS],
    "prod_lag_1w", "prod_lag_4w", "prod_roll_mean_8w",
]

OPTIONAL_FEATURE_COLS = ["tavg_c", "precip_mm", "heat_stress_flag", "enso_oni_index", "avg_price"]

TARGET_COL = "qty_ordered_kg"
