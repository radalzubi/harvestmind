"""MinTrace WLS hierarchical reconciliation.

Hierarchy: Total → Category → SKU → SKU×Buyer
Uses hierarchicalforecast if available, falls back to OLS reconciliation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


HIERARCHY_LEVELS = ["total", "category", "product_id", "product_buyer"]


def build_summation_matrix(
    base_df: pd.DataFrame,
    product_meta: pd.DataFrame,
) -> tuple[np.ndarray, list[str], list[str]]:
    """Build S matrix (upper-level aggregates × bottom-level series).

    Parameters
    ----------
    base_df : DataFrame with [product_id, buyer_id, week_start, forecast_kg]
    product_meta : DataFrame with [product_id, crop_category]

    Returns
    -------
    S : ndarray shape (n_all_series, n_bottom)
    all_series_names : list of series labels (top → bottom)
    bottom_series_names : list of bottom-level series labels
    """
    bottom_series = (
        base_df.groupby(["product_id", "buyer_id"])
        .size()
        .reset_index()[["product_id", "buyer_id"]]
    )
    bottom_series["series_name"] = bottom_series["product_id"] + "|" + bottom_series["buyer_id"]
    bottom_names = list(bottom_series["series_name"])
    n_bottom = len(bottom_names)

    # Merge category
    bottom_series = bottom_series.merge(product_meta[["product_id","crop_category"]], on="product_id", how="left")

    # All series: 1 total + n_categories + n_products + n_bottom
    categories = sorted(bottom_series["crop_category"].dropna().unique())
    products = sorted(bottom_series["product_id"].unique())

    all_names = ["total"] + [f"cat:{c}" for c in categories] + products + bottom_names
    n_all = len(all_names)

    S = np.zeros((n_all, n_bottom), dtype=float)

    # Total row
    S[0, :] = 1.0

    # Category rows
    for i, cat in enumerate(categories):
        mask = (bottom_series["crop_category"] == cat).values
        S[1 + i, mask] = 1.0

    # Product rows
    offset = 1 + len(categories)
    for i, prod in enumerate(products):
        mask = (bottom_series["product_id"] == prod).values
        S[offset + i, mask] = 1.0

    # Bottom-level identity
    offset2 = offset + len(products)
    for i in range(n_bottom):
        S[offset2 + i, i] = 1.0

    return S, all_names, bottom_names


def reconcile_mintrace_wls(
    base_forecasts: pd.DataFrame,
    product_meta: pd.DataFrame,
    residuals: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """MinTrace WLS reconciliation.

    Parameters
    ----------
    base_forecasts : [product_id, buyer_id, week_start, forecast_kg]
    product_meta   : [product_id, crop_category]
    residuals      : optional [product_id, buyer_id, week_start, residual] for WLS weights;
                     if None, falls back to OLS (equal weights)

    Returns
    -------
    DataFrame matching base_forecasts columns with reconciled forecasts.
    """
    # Try hierarchicalforecast first
    try:
        return _reconcile_hierarchicalforecast(base_forecasts, product_meta, residuals)
    except Exception:
        pass

    # Fallback: OLS (S(S'S)^{-1}S') applied per week
    weeks = sorted(base_forecasts["week_start"].unique())
    results = []
    S, all_names, bottom_names = build_summation_matrix(base_forecasts, product_meta)
    n_bottom = len(bottom_names)

    # OLS projection: P = (S'S)^{-1} S'
    STS = S.T @ S
    try:
        P = np.linalg.solve(STS, S.T)
    except np.linalg.LinAlgError:
        P = np.linalg.lstsq(STS, S.T, rcond=None)[0]

    # Reconciliation matrix is S @ P; we apply it directly per week below.

    for week in weeks:
        wdf = base_forecasts[base_forecasts["week_start"] == week].copy()
        wdf["series_name"] = wdf["product_id"] + "|" + wdf["buyer_id"]
        # Build bottom-level forecast vector in order
        bottom_map = {n: 0.0 for n in bottom_names}
        for _, row in wdf.iterrows():
            sn = row["product_id"] + "|" + row["buyer_id"]
            if sn in bottom_map:
                bottom_map[sn] = row["forecast_kg"]

        y_hat = np.array([bottom_map[n] for n in bottom_names])
        # Coherent bottom-level forecasts
        y_tilde = (S @ P @ y_hat)  # full hierarchy
        # Extract bottom rows
        offset_bottom = len(all_names) - n_bottom
        y_bottom = y_tilde[offset_bottom:]

        for j, bn in enumerate(bottom_names):
            prod_id, buyer_id = bn.split("|", 1)
            results.append({
                "product_id": prod_id,
                "buyer_id": buyer_id,
                "week_start": week,
                "forecast_kg": max(0.0, round(float(y_bottom[j]), 2)),
                "model": "mintrace_ols",
            })

    out = pd.DataFrame(results)
    # Reattach interval columns if present
    interval_cols = [c for c in base_forecasts.columns if c.startswith(("lower_","upper_"))]
    if interval_cols:
        out = out.merge(base_forecasts[["product_id","buyer_id","week_start"] + interval_cols],
                        on=["product_id","buyer_id","week_start"], how="left")
    return out


def _reconcile_hierarchicalforecast(
    base_forecasts: pd.DataFrame,
    product_meta: pd.DataFrame,
    residuals: pd.DataFrame | None,
) -> pd.DataFrame:
    """Use hierarchicalforecast library (MinTrace WLS) if available."""
    from hierarchicalforecast.methods import MinTrace
    from hierarchicalforecast.utils import aggregate

    df = base_forecasts.merge(product_meta[["product_id","crop_category"]], on="product_id", how="left")
    df["product_buyer"] = df["product_id"] + "|" + df["buyer_id"]

    spec = [
        ["product_buyer"],
        ["product_id", "product_buyer"],
        ["crop_category", "product_id", "product_buyer"],
        ["total", "crop_category", "product_id", "product_buyer"],
    ]

    Y_df, S_df, tags = aggregate(df, spec)
    Y_df["ds"] = Y_df["week_start"]
    Y_df["y"] = Y_df["forecast_kg"]

    reconciler = MinTrace(method="wls_var")
    Y_rec = reconciler.reconcile(Y_df, S_df)

    bottom = Y_rec[Y_rec["unique_id"].str.contains(r"\|", na=False)].copy()
    bottom[["product_id","buyer_id"]] = bottom["unique_id"].str.split("|", expand=True)
    return bottom[["product_id","buyer_id","week_start","forecast_kg"]].assign(model="mintrace_wls")
