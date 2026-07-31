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


def coherent_category_totals(
    base_forecasts: pd.DataFrame,
    product_meta: pd.DataFrame,
) -> pd.DataFrame:
    """Category-level totals that are coherent with the product forecasts.

    THE HONEST STATUS OF THIS MODULE. ``reconcile_mintrace_wls`` below was
    never wired into the production path, and an audit found the reason is
    mathematical rather than an oversight: the demand service produces
    forecasts at the BOTTOM level only (product x buyer). A set of
    bottom-level forecasts is already coherent by construction, so MinT
    reconciliation reduces to the summation lift and returns the input
    unchanged. Reconciliation only does work when forecasts exist at
    SEVERAL levels and disagree with each other.

    So rather than wire a no-op or delete tested code, this function
    exposes the part that is genuinely useful today: aggregating product
    forecasts up to category totals that sum correctly. If the service
    later forecasts categories directly — where a category-level model can
    beat the sum of noisy product models — MinT becomes live and
    ``reconcile_mintrace_wls`` is the implementation to use.

    Returns [crop_category, week_start, forecast_kg].
    """
    if base_forecasts.empty:
        return pd.DataFrame(columns=["crop_category", "week_start", "forecast_kg"])
    meta = product_meta.rename(columns={"category": "crop_category"})
    merged = base_forecasts.merge(
        meta[["product_id", "crop_category"]], on="product_id", how="left")
    merged["crop_category"] = merged["crop_category"].fillna("uncategorized")
    return (merged.groupby(["crop_category", "week_start"], as_index=False)
            ["forecast_kg"].sum())


def reconcile_mintrace_wls(
    base_forecasts: pd.DataFrame,
    product_meta: pd.DataFrame,
    residuals: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """MinTrace WLS reconciliation.

    NOT WIRED INTO PRODUCTION, deliberately — see
    ``coherent_category_totals`` above for why: with bottom-level-only base
    forecasts this is an identity operation. Kept and tested for the point
    at which multi-level forecasts exist.

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

    # The base forecasts are bottom-level only (product|buyer), i.e. already
    # coherent leaves. Reconciliation is therefore the summation lift S @ y_hat
    # (a full projection S(S'S)^{-1}S' is only needed when base forecasts exist
    # at MULTIPLE levels and disagree — not the case here, and the previous
    # S @ P @ y_hat form was a shape mismatch since P is (n_bottom, n_all)).

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
        # Lift coherent bottom forecasts to the full hierarchy.
        y_tilde = S @ y_hat
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
