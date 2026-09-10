"""Order-up-to (s,S-style) baseline policy.

The heuristic operators actually use, formalized: keep enough on order to
cover expected demand plus a safety buffer scaled to demand variability.

    S_j = trailing mean weekly demand + z × trailing std of weekly demand

z comes from the same service quantile the rest of the engine uses (the
cost critical ratio), so the baseline is tuned to the operator's
economics rather than strawmanned. The optimizer must beat THIS, not just
a naive replay, before its complexity is justified.
"""

from __future__ import annotations

import pandas as pd
from scipy import stats


def order_up_to_commitments(
    weekly_demand: pd.DataFrame,   # [product_id, week_start, demand_kg]
    service_level: float = 0.90,
    lookback_weeks: int = 13,
) -> dict[str, float]:
    """Per-product order-up-to level from trailing demand statistics.

    Returns {product_id: S_kg}. Products with < 2 trailing observations
    get their trailing mean (no variance estimate, no buffer — stated by
    construction rather than inventing one).
    """
    z = float(stats.norm.ppf(min(max(service_level, 0.5), 0.999)))
    out: dict[str, float] = {}
    cutoff_weeks = sorted(weekly_demand["week_start"].unique())[-lookback_weeks:]
    recent = weekly_demand[weekly_demand["week_start"].isin(cutoff_weeks)]
    for p, g in recent.groupby("product_id"):
        vals = g.groupby("week_start")["demand_kg"].sum().to_numpy(dtype=float)
        mu = float(vals.mean()) if len(vals) else 0.0
        sigma = float(vals.std(ddof=1)) if len(vals) >= 2 else 0.0
        out[p] = max(mu + z * sigma, 0.0)
    return out
