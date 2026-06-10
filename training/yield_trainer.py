"""Yield model training: the pool prior becomes the third hierarchy level.

The existing model is two-level: supplier ← operator population. With
the pool, a thin-data operator's POPULATION itself shrinks toward the
pooled cross-operator prior — supplier ← operator ← pool. An operator
with three suppliers and twenty deliveries no longer estimates produce
yield behavior from a population of one.

Blend rule (precision-weighted, same algebra as the supplier level):
the operator population's weight grows with its own delivery count; the
pool prior acts as POOL_PSEUDO_DELIVERIES worth of evidence. With rich
operator data the pool's influence vanishes; with none, the prior IS the
pool. Deployment of a retrained yield model still goes through the
existing holdout gate (retraining/pipeline.retrain_yield) — the pool
shapes the prior, it never bypasses validation.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from pool.pool_reader import PoolReader, YieldPrior
from risk.supplier_distribution import Population, estimate_population

# How much evidence the pool prior carries, in pseudo-deliveries. Strong
# enough to anchor a cold operator, weak enough to wash out by ~a season
# of real deliveries.
POOL_PSEUDO_DELIVERIES = 30


def population_from_pool(prior: YieldPrior) -> Population:
    """A Population object built purely from the pool prior (cold start)."""
    var = max(prior.fill_rate_std ** 2, 1e-4)
    return Population(
        mean=prior.fill_rate_mean,
        pooled_variance=var,
        within_variance=var,
        kappa=4.0,
        n_deliveries=prior.n_deliveries,
        n_suppliers=0,
        method="pool_prior",
    )


def estimate_population_with_pool(
    fills: pd.DataFrame,
    pool_prior: Optional[YieldPrior],
) -> Population:
    """Three-level estimate: operator population blended toward the pool.

    No pool prior → identical to the existing two-level estimate (the
    pool never silently changes behavior when it has nothing to say).
    """
    own = estimate_population(fills)
    if pool_prior is None:
        return own
    if own.n_deliveries == 0:
        return population_from_pool(pool_prior)

    n = own.n_deliveries
    w_own = n / (n + POOL_PSEUDO_DELIVERIES)
    w_pool = 1.0 - w_own
    pool_var = max(pool_prior.fill_rate_std ** 2, 1e-4)

    return Population(
        mean=w_own * own.mean + w_pool * pool_prior.fill_rate_mean,
        pooled_variance=w_own * own.pooled_variance + w_pool * pool_var,
        within_variance=w_own * own.within_variance + w_pool * pool_var,
        kappa=own.kappa,
        n_deliveries=own.n_deliveries,
        n_suppliers=own.n_suppliers,
        method="pool_blended",
    )


def yield_population_for_operator(
    conn,
    category: str = "uncategorized",
    region: str | None = None,
    pool_reader: PoolReader | None = None,
) -> Population:
    """Operator's supplier population with the pool as the third level."""
    from risk.supplier_distribution import _delivery_fill_rates

    fills = _delivery_fill_rates(conn)
    reader = pool_reader or PoolReader()
    prior = reader.get_yield_prior(category, region=region)
    return estimate_population_with_pool(fills, prior)
