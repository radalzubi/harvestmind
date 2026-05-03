"""Scenario reduction via Heitsch-Römisch (2003) fast forward selection.

Reduces N SAA scenarios to K representative scenarios while preserving
the Wasserstein distance of the original distribution.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def reduce_scenarios(
    scenarios_df: pd.DataFrame,
    target_k: int = 20,
    value_col: str = "yield_kg",
    group_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Fast-forward scenario reduction (Heitsch-Römisch 2003).

    Parameters
    ----------
    scenarios_df : DataFrame with [scenario_index, scenario_weight, ..., value_col]
    target_k     : number of scenarios to retain
    value_col    : column whose distribution to preserve (or aggregate over group_cols)
    group_cols   : columns to aggregate value_col over (e.g. ['supplier_id','product_id','week_start'])

    Returns
    -------
    DataFrame: subset of scenarios_df with updated scenario_weight summing to 1.
    """
    if group_cols:
        # Aggregate to scenario-level vectors
        pivot = (
            scenarios_df
            .groupby(["scenario_index"] + group_cols)[value_col]
            .sum()
            .unstack(level=group_cols, fill_value=0.0)
        )
        scenario_matrix = pivot.values  # shape (N, n_features)
        scenario_weights = (
            scenarios_df.groupby("scenario_index")["scenario_weight"].first().values
        )
        scenario_indices = pivot.index.tolist()
    else:
        scenario_matrix = scenarios_df.groupby("scenario_index")[value_col].mean().values.reshape(-1, 1)
        scenario_weights = scenarios_df.groupby("scenario_index")["scenario_weight"].first().values
        scenario_indices = scenarios_df.groupby("scenario_index").groups.keys()
        scenario_indices = list(scenario_indices)

    N = len(scenario_indices)
    if N <= target_k:
        return scenarios_df.copy()

    # Pairwise L2 distances
    from scipy.spatial.distance import cdist
    dist_matrix = cdist(scenario_matrix, scenario_matrix, metric="euclidean")

    retained = list(range(N))
    deleted = []

    while len(retained) > target_k:
        # For each retained scenario, find probability-weighted min distance to others
        min_cost = np.inf
        worst_idx = -1
        for r in retained:
            others = [i for i in retained if i != r]
            # Cost of deleting r: redistribute its weight to nearest remaining
            if not others:
                continue
            nearest_dist = min(dist_matrix[r, o] for o in others)
            cost = scenario_weights[r] * nearest_dist
            if cost < min_cost:
                min_cost = cost
                worst_idx = r

        # Find nearest retained scenario to worst_idx
        others = [i for i in retained if i != worst_idx]
        nearest = min(others, key=lambda o: dist_matrix[worst_idx, o])
        scenario_weights[nearest] += scenario_weights[worst_idx]
        scenario_weights[worst_idx] = 0.0
        retained.remove(worst_idx)
        deleted.append(worst_idx)

    kept_original_indices = [scenario_indices[r] for r in retained]
    new_weights = {scenario_indices[r]: scenario_weights[r] for r in retained}

    # Filter original DataFrame
    mask = scenarios_df["scenario_index"].isin(kept_original_indices)
    result = scenarios_df[mask].copy()

    # Re-map scenario_index to 0..K-1 and update weights
    idx_remap = {old: new for new, old in enumerate(kept_original_indices)}
    result["scenario_index"] = result["scenario_index"].map(idx_remap)
    result["scenario_weight"] = result["scenario_index"].map(
        {idx_remap[k]: v for k, v in new_weights.items()}
    )
    # Normalize weights
    total_w = result["scenario_weight"].sum()
    if total_w > 0:
        result["scenario_weight"] = result["scenario_weight"] / total_w

    return result.reset_index(drop=True)
