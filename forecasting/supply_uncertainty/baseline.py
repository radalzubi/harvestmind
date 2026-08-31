"""Tier-0 baseline: empirical distributions with partial pooling.

This is the model that runs when there is not enough history to fit
anything else, and the benchmark every fancier model must beat. It is
deliberately transparent: an operator can reconstruct its numbers by hand
from their own records, which matters more than sophistication when the
answer is going to drive a purchase commitment.

THE SPARSE-GROUP TRAP
---------------------
The failure this module exists to prevent: a supplier with three
deliveries that happened to land within 2% of each other looks
extraordinarily reliable, and a naive empirical quantile hands back a
2%-wide interval. The narrowness is an artefact of the sample size, not
evidence of consistency. Any downstream optimizer will then commit
aggressively against a number that was never entitled to that confidence.

The fix is partial pooling: shrink each group's estimate toward the
population, by an amount that depends on how much evidence the group
actually has. With n observations and population variance tau^2 versus
within-group variance sigma^2, the classical shrinkage weight is

    w = n / (n + sigma^2/tau^2)

so w -> 0 for a brand-new group (use the population) and w -> 1 for a
long-established one (trust its own history). This is the James-Stein /
empirical-Bayes result: shrunken estimators dominate the per-group sample
mean in total squared error when pooling several groups.

References
----------
Efron, B. & Morris, C. (1975). "Data Analysis Using Stein's Estimator and
    its Generalizations." *JASA* 70(350):311-319.
Gelman, A. & Hill, J. (2007). *Data Analysis Using Regression and
    Multilevel/Hierarchical Models*, Cambridge — ch. 12 on partial pooling.

The variance is pooled as well as the mean, which is the part usually
forgotten: a sparse group inherits the population's *spread*, so its
interval is wide until its own history earns the right to narrow it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone

import numpy as np

from forecasting.supply_uncertainty.contract import (
    QUANTILE_LEVELS,
    DataTier,
    ProbabilisticForecast,
    QuantityKind,
    confidence_for_tier,
)

# Season counts delimiting the tiers.
TIER_THRESHOLDS: tuple[tuple[int, DataTier], ...] = (
    (0, DataTier.NONE),
    (1, DataTier.SINGLE_SEASON),
    (2, DataTier.SPARSE),
    (4, DataTier.ADEQUATE),
    (8, DataTier.RICH),
)

# Interval inflation applied on top of pooling, by tier. Pooling handles
# the estimate; this covers the model uncertainty pooling cannot express —
# that we are not even sure the population is the right reference class.
TIER_INTERVAL_INFLATION: dict[DataTier, float] = {
    DataTier.NONE: 1.60,
    DataTier.SINGLE_SEASON: 1.40,
    DataTier.SPARSE: 1.20,
    DataTier.ADEQUATE: 1.05,
    DataTier.RICH: 1.00,
}


def classify_data_tier(n_observations: int, n_seasons: int | None = None) -> DataTier:
    """Classify data availability.

    Seasons matter more than raw row count for an annual biological
    process: 200 daily records from one season still say nothing about
    year-to-year variation. When the season count is unknown, fall back to
    the observation count but never claim better than SPARSE, since row
    count alone cannot evidence multi-season coverage.
    """
    if n_seasons is not None:
        tier = DataTier.NONE
        for threshold, t in TIER_THRESHOLDS:
            if n_seasons >= threshold:
                tier = t
        return tier
    if n_observations <= 0:
        return DataTier.NONE
    if n_observations < 5:
        return DataTier.SINGLE_SEASON
    return DataTier.SPARSE


@dataclass
class PooledPopulation:
    """Population-level reference distribution for partial pooling."""

    mean: float
    sd: float                 # between-group SD of the group means
    within_sd: float          # typical WITHIN-group SD
    n_groups: int
    n_observations: int
    quantiles: dict[float, float]

    @classmethod
    def from_groups(cls, groups: dict[str, np.ndarray]) -> "PooledPopulation":
        """Fit the population from every group's observations."""
        usable = {g: np.asarray(v, dtype=float) for g, v in groups.items()
                  if np.size(v) > 0}
        if not usable:
            raise ValueError("no observations to build a population from")
        allv = np.concatenate(list(usable.values()))
        allv = allv[np.isfinite(allv)]
        if allv.size == 0:
            raise ValueError("no finite observations")

        # Between-group spread of the means is the relevant population
        # variance for shrinkage; fall back to overall spread when there is
        # only one group and between-group variance is undefined.
        means = np.array([v.mean() for v in usable.values() if v.size > 0])
        sd = float(means.std(ddof=1)) if means.size > 1 else float(allv.std(ddof=1) if allv.size > 1 else 0.0)

        # Typical within-group spread, weighted by degrees of freedom. This
        # is the reference a sparse group's own (unreliable) variance is
        # pooled toward — see pooled_within_variance below.
        num = den = 0.0
        for v in usable.values():
            if v.size > 1:
                num += (v.size - 1) * float(v.var(ddof=1))
                den += (v.size - 1)
        within_sd = float(np.sqrt(num / den)) if den > 0 else sd

        return cls(
            mean=float(allv.mean()),
            sd=max(sd, 1e-9),
            within_sd=max(within_sd, 1e-9),
            n_groups=len(usable),
            n_observations=int(allv.size),
            quantiles={q: float(np.quantile(allv, q)) for q in QUANTILE_LEVELS},
        )


# Pseudo-observations of prior weight given to the population's within-group
# variance. A group needs roughly this many degrees of freedom before its own
# observed spread dominates the pooled estimate.
VARIANCE_PRIOR_DF = 8.0


def pooled_within_variance(
    obs: np.ndarray, population_within_var: float, prior_df: float = VARIANCE_PRIOR_DF,
) -> float:
    """Shrink a group's own variance estimate toward the population's.

    THE TRAP THIS CLOSES. Shrinking only the MEAN is not enough. A group
    with three deliveries that happened to land within 1% of each other has
    a near-zero sample variance, and the classical weight
    n/(n + within/between) then reads that as high precision and hands the
    group almost full weight — producing exactly the falsely narrow
    interval the pooling was supposed to prevent. (Observed: weight 0.99
    for a 3-observation group.)

    The error is treating a variance ESTIMATE from 2 degrees of freedom as
    if it were the variance. Three close points do not demonstrate low
    variability; they are equally consistent with a wide distribution
    sampled three times. So the variance is pooled on its own degrees of
    freedom, exactly as the mean is:

        var_pooled = (df_group * var_group + prior_df * var_population)
                     / (df_group + prior_df)

    A group must accumulate observations before its own spread is believed.
    """
    n = int(np.size(obs))
    if n < 2:
        return float(population_within_var)
    df_g = n - 1
    var_g = float(np.var(obs, ddof=1))
    return float((df_g * var_g + prior_df * population_within_var)
                 / (df_g + prior_df))


def shrinkage_weight(n: int, within_var: float, between_var: float) -> float:
    """Classical empirical-Bayes weight on the group's own mean.

        w = n / (n + within_var/between_var)

    Zero observations give w=0 (pure population); large n gives w->1.
    Guarded so a degenerate between-group variance cannot produce w=1 for
    a group with almost no data, which would defeat the whole purpose.
    """
    if n <= 0:
        return 0.0
    if between_var <= 1e-12:
        return 0.0            # population has no spread to shrink toward
    ratio = max(within_var, 1e-12) / between_var
    return float(n / (n + ratio))


class PooledEmpiricalModel:
    """Tier-0 probabilistic model: pooled empirical quantiles.

    Fit on a mapping of group key -> observed values (fill rates, yields,
    packout fractions — anything nonnegative). Predicts a full quantile
    set for any group, including groups never seen during fitting.
    """

    model_family = "pooled_empirical"
    model_version = "1.0"

    def __init__(self, quantile_levels: tuple[float, ...] = QUANTILE_LEVELS):
        self.quantile_levels = quantile_levels
        self.population: PooledPopulation | None = None
        self.groups: dict[str, np.ndarray] = {}
        self.seasons: dict[str, int] = {}
        self.training_cutoff: date | None = None

    def fit(
        self,
        groups: dict[str, np.ndarray],
        seasons_per_group: dict[str, int] | None = None,
        training_cutoff: date | None = None,
    ) -> "PooledEmpiricalModel":
        self.groups = {g: np.asarray(v, dtype=float)[np.isfinite(np.asarray(v, dtype=float))]
                       for g, v in groups.items()}
        self.population = PooledPopulation.from_groups(self.groups)
        self.seasons = seasons_per_group or {}
        self.training_cutoff = training_cutoff
        return self

    def _pooled_quantiles(self, key: str) -> tuple[dict[float, float], float, DataTier, str | None]:
        assert self.population is not None
        pop = self.population
        obs = self.groups.get(key, np.array([], dtype=float))
        n = int(obs.size)
        tier = classify_data_tier(n, self.seasons.get(key))

        if n == 0:
            # Unseen group: the population IS the forecast, widened.
            infl = TIER_INTERVAL_INFLATION[DataTier.NONE]
            centre = pop.mean
            q = {lv: max(centre + (pop.quantiles[lv] - centre) * infl, 0.0)
                 for lv in self.quantile_levels}
            return q, centre, DataTier.NONE, "no history for this group; using pooled population"

        # Pool the VARIANCE as well as the mean — a sparse group's own
        # spread is an estimate from 1-2 degrees of freedom and must not be
        # taken at face value (see pooled_within_variance).
        within_var = pooled_within_variance(obs, pop.within_sd ** 2)
        w = shrinkage_weight(n, within_var, pop.sd ** 2)
        centre = w * float(obs.mean()) + (1.0 - w) * pop.mean

        # Shape from the POOLED spread, not the raw sample spread. The
        # group's own empirical shape is only trusted in proportion to the
        # evidence behind it; the rest comes from the population's shape
        # rescaled to the pooled standard deviation.
        infl = TIER_INTERVAL_INFLATION[tier]
        pooled_sd = float(np.sqrt(max(within_var, 1e-18)))
        pop_within = max(pop.within_sd, 1e-9)
        q: dict[float, float] = {}
        for lv in self.quantile_levels:
            # Population offset expressed in SD units, then rescaled to the
            # group's pooled SD — this is what keeps a 3-observation group's
            # interval honest instead of collapsing it to its sample range.
            pop_off_std = (pop.quantiles[lv] - pop.mean) / pop_within
            shape_off = pop_off_std * pooled_sd
            grp_off = (float(np.quantile(obs, lv)) - float(obs.mean())) if n > 1 else 0.0
            offset = w * grp_off + (1.0 - w) * (pop.quantiles[lv] - pop.mean)
            # Never let the blended offset be narrower than the pooled-SD
            # shape implies: that is precisely the sparse-group failure.
            if abs(shape_off) > abs(offset):
                offset = shape_off
            q[lv] = max(centre + offset * infl, 0.0)
        reason = (None if tier in (DataTier.ADEQUATE, DataTier.RICH)
                  else f"sparse history (n={n}); shrunk toward population "
                       f"(weight {w:.2f} on own data)")
        return q, centre, tier, reason

    def predict(
        self,
        key: str,
        entity_key: dict,
        target_start: date,
        target_end: date,
        issued_at: datetime | None = None,
        information_cutoff: datetime | None = None,
        unit: str = "kg",
        quantity_kind: QuantityKind = QuantityKind.AVAILABLE_SUPPLY,
        scale: float = 1.0,
    ) -> ProbabilisticForecast:
        """Forecast for one group.

        ``scale`` multiplies the (unitless) modelled fraction up to a
        quantity — e.g. a fill-rate distribution times the ordered volume.
        Passing 1.0 returns the fraction itself.
        """
        if self.population is None:
            raise RuntimeError("model not fitted")
        now = issued_at or datetime.now(timezone.utc)
        cutoff = information_cutoff or now

        q, centre, tier, reason = self._pooled_quantiles(key)
        obs = self.groups.get(key, np.array([], dtype=float))

        fc = ProbabilisticForecast(
            forecast_id=str(uuid.uuid4()),
            issued_at=now,
            information_cutoff=cutoff,
            target_start=target_start,
            target_end=target_end,
            entity_key=entity_key,
            quantity_kind=quantity_kind,
            unit=unit,
            quantiles={lv: v * scale for lv, v in q.items()},
            mean=centre * scale,
            model_family=self.model_family,
            model_version=self.model_version,
            training_cutoff=self.training_cutoff,
            data_tier=tier,
            confidence=confidence_for_tier(tier),
            calibrated=False,
            n_observations=int(obs.size),
            fallback_reason=reason,
            drivers=self._drivers(key, obs, tier),
        )
        fc.validate()
        return fc

    def _drivers(self, key: str, obs: np.ndarray, tier: DataTier) -> list[str]:
        assert self.population is not None
        out = []
        if obs.size == 0:
            out.append(f"no history for {key}; pooled across "
                       f"{self.population.n_groups} groups")
        else:
            out.append(f"{obs.size} historical observations for {key} "
                       f"(mean {obs.mean():.3f})")
            out.append(f"population mean {self.population.mean:.3f} across "
                       f"{self.population.n_groups} groups")
        if tier in (DataTier.NONE, DataTier.SINGLE_SEASON, DataTier.SPARSE):
            out.append(f"intervals widened {TIER_INTERVAL_INFLATION[tier]:.0%} "
                       "for sparse data")
        return out


class ClimatologyModel:
    """Season-of-year empirical distribution, ignoring group identity.

    The most conservative fallback: what does this time of year usually
    look like, across everyone. Useful when a group is unseen AND the
    population is heterogeneous enough that its overall mean is unhelpful.
    """

    model_family = "climatology"
    model_version = "1.0"

    def __init__(self, quantile_levels: tuple[float, ...] = QUANTILE_LEVELS):
        self.quantile_levels = quantile_levels
        self.by_period: dict[int, np.ndarray] = {}
        self.overall: np.ndarray = np.array([], dtype=float)

    def fit(self, values: np.ndarray, periods: np.ndarray) -> "ClimatologyModel":
        """``periods`` is any seasonal index — week or month of year."""
        v = np.asarray(values, dtype=float)
        p = np.asarray(periods)
        ok = np.isfinite(v)
        v, p = v[ok], p[ok]
        self.overall = v
        for period in np.unique(p):
            self.by_period[int(period)] = v[p == period]
        return self

    def quantiles_for(self, period: int) -> dict[float, float]:
        vals = self.by_period.get(int(period))
        # A period needs enough observations to speak for itself; below
        # that, use the whole record rather than pretend.
        if vals is None or vals.size < 3:
            vals = self.overall
        if vals.size == 0:
            raise RuntimeError("climatology not fitted")
        return {q: float(np.quantile(vals, q)) for q in self.quantile_levels}
