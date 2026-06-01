"""Empirical-Bayes hierarchical estimation of supplier fill-rate distributions.

We model the predictive distribution of a *single upcoming delivery's* fill
rate for each supplier. That is the quantity the commitment decision needs:
not "what is the supplier's long-run average," but "if I rely on this supplier
for the next delivery, how low could the fill rate realistically come in."

Two sources of spread, both captured
------------------------------------
1. Estimation uncertainty: a supplier with 3 deliveries is less pinned down
   than one with 30. Thin-data suppliers shrink toward the population.
2. Delivery-to-delivery volatility: even with the mean known, a swingy
   supplier's next delivery is less predictable than a steady one's. Two
   suppliers with the same mean but different variance get different downside
   quantiles. The aggregate (totals-only) Beta-Binomial misses this; modeling
   per-delivery fill rates captures it.

The model (one operator)
------------------------
Per-delivery fill rate fr ~ Beta(a_s, b_s) for supplier s. The supplier's
(mean, variance) are estimated by empirical Bayes:

    population:  m0, v0  = pooled mean and variance of every delivery's fill rate
    between:     tau^2   = variance of supplier means (supplier-to-supplier)
    within:      sigma^2 = pooled within-supplier delivery variance
    shrinkage:   kappa   = sigma^2 / tau^2   (prior strength in "pseudo-deliveries")

    mu_s   = (kappa * m0 + n_s * m_s) / (kappa + n_s)        # James-Stein mean
    v_eff  = (kappa * v0 + n_s * v_s) / (kappa + n_s)        # blended variance
    Beta(a_s, b_s) fit from (mu_s, v_eff) by method of moments
    downside = Beta.ppf(q, a_s, b_s)

A supplier with zero deliveries returns the population Beta (cold start).

Why empirical Bayes and not full MCMC: with 3-8 deliveries per supplier, a
fully sampled posterior would be precision theater. Empirical Bayes with
method of moments is the standard, defensible, deployable choice at this data
volume, and it runs in milliseconds with no solver. The hyperparameters are
estimated from the data (kappa is not hand-set), which is what makes it
hierarchical rather than a fixed prior.

Future third level (multi-operator)
-----------------------------------
Today the population is "this operator's suppliers." With multiple operators,
add a global layer: operator populations shrink toward a global prior, so a
new operator with little history borrows strength from the whole network.
That third level is where the cross-operator data moat lives. Everything
downstream depends only on (a_s, b_s), so adding it is isolated to this file.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import duckdb
import pandas as pd
from scipy import stats

# Risk tiers applied to the shrunk mean (same thresholds as the deterministic
# module, so the two are directly comparable).
_HIGH_RISK_FILL_RATE = 0.80
_MEDIUM_RISK_FILL_RATE = 0.90

# A supplier whose downside quantile sits this far below its mean is flagged
# volatile even when the mean looks acceptable.
_VOLATILITY_SPREAD = 0.15

# Shrinkage strength (in pseudo-deliveries) used when between-supplier variance
# cannot be estimated: fewer than 2 suppliers, or degenerate spread.
_FALLBACK_KAPPA = 4.0

# A supplier needs at least this many deliveries before we trust its own
# delivery-to-delivery variance. Below it, we borrow the typical
# within-supplier variance from the population (you cannot estimate spread
# from one or two points).
_MIN_N_FOR_OWN_VARIANCE = 3

# Small absolute floor on any predictive variance, to keep the Beta fit well
# defined without making a steady supplier look uncertain. std ~ 0.02.
_VAR_FLOOR = 0.0004

# Variance used when nothing can be estimated at all (no data anywhere).
_DEFAULT_VARIANCE = 0.02

_EPS = 1e-6


@dataclass(frozen=True)
class Population:
    """Empirical-Bayes population description over per-delivery fill rate."""

    mean: float              # m0, pooled mean fill rate across all deliveries
    pooled_variance: float   # v0, full spread of all deliveries (cold-start prior)
    within_variance: float   # sigma^2, typical within-supplier delivery variance
    kappa: float             # shrinkage strength in pseudo-deliveries (mean)
    n_deliveries: int
    n_suppliers: int
    method: str              # "empirical_bayes" or "fallback"


def _delivery_fill_rates(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """One row per delivery: supplier, name, and that delivery's fill rate.

    fill_rate = min(accepted / ordered, 1.0). accepted_quantity falls back to
    delivered_quantity when accepted is null, matching the deterministic module.
    Deliveries with no ordered quantity are dropped (no fill rate is defined).
    """
    df = conn.execute("""
        SELECT supplier_id,
               supplier_name,
               ordered_quantity AS ordered,
               COALESCE(accepted_quantity, delivered_quantity) AS accepted
        FROM stg_supplier_deliveries
        WHERE ordered_quantity IS NOT NULL AND ordered_quantity > 0
    """).df()

    if df.empty:
        return df

    df["ordered"] = df["ordered"].astype(float)
    df["accepted"] = df["accepted"].fillna(0.0).astype(float)
    df["fill_rate"] = (df["accepted"] / df["ordered"]).clip(upper=1.0, lower=0.0)
    return df


def estimate_population(fills: pd.DataFrame) -> Population:
    """Empirical-Bayes population prior from per-delivery fill rates.

    Estimates the pooled mean/variance, plus the shrinkage strength kappa from
    the ratio of within-supplier to between-supplier variance. Falls back to a
    weak prior when there are too few suppliers to estimate between-variance.
    """
    if fills.empty:
        return Population(mean=0.5, pooled_variance=_DEFAULT_VARIANCE,
                          within_variance=_DEFAULT_VARIANCE, kappa=_FALLBACK_KAPPA,
                          n_deliveries=0, n_suppliers=0, method="fallback")

    m0 = float(fills["fill_rate"].mean())
    m0 = min(max(m0, _EPS), 1 - _EPS)
    v0 = max(float(fills["fill_rate"].var(ddof=0)), _VAR_FLOOR)

    by_supplier = fills.groupby("supplier_id")["fill_rate"]
    supplier_means = by_supplier.mean()
    n_suppliers = int(supplier_means.shape[0])
    n_deliveries = int(fills.shape[0])

    # Typical within-supplier variance: average each supplier's own delivery
    # variance over suppliers that have at least 2 deliveries.
    within = by_supplier.var(ddof=0).dropna()
    sigma2 = max(float(within.mean()), _VAR_FLOOR) if not within.empty else v0

    if n_suppliers < 2:
        return Population(mean=m0, pooled_variance=v0, within_variance=sigma2,
                          kappa=_FALLBACK_KAPPA, n_deliveries=n_deliveries,
                          n_suppliers=n_suppliers, method="fallback")

    tau2 = float(supplier_means.var(ddof=1))  # between-supplier variance
    if tau2 <= _EPS:
        # Suppliers look identical in the mean; nothing to shrink between.
        return Population(mean=m0, pooled_variance=v0, within_variance=sigma2,
                          kappa=_FALLBACK_KAPPA, n_deliveries=n_deliveries,
                          n_suppliers=n_suppliers, method="fallback")

    kappa = max(sigma2 / tau2, _EPS)
    return Population(mean=m0, pooled_variance=v0, within_variance=sigma2,
                      kappa=kappa, n_deliveries=n_deliveries,
                      n_suppliers=n_suppliers, method="empirical_bayes")


def _beta_from_mean_var(mean: float, var: float) -> tuple[float, float]:
    """Method-of-moments Beta parameters from a target mean and variance.

    Clamps variance into the valid open interval (0, mean*(1-mean)) so the
    Beta is always well defined.
    """
    mean = min(max(mean, _EPS), 1 - _EPS)
    max_var = mean * (1 - mean)
    var = min(max(var, _EPS * max_var), (1 - _EPS) * max_var)
    common = (max_var / var) - 1.0
    common = max(common, _EPS)
    return mean * common, (1 - mean) * common


def supplier_distribution(
    n_deliveries: int,
    supplier_mean: float | None,
    supplier_var: float | None,
    pop: Population,
    quantile: float,
) -> dict[str, float]:
    """Predictive Beta for one supplier's next delivery, with shrinkage.

    Returns the shrunk mean, blended-variance Beta parameters, and the downside
    quantile. A supplier with zero deliveries returns the population Beta.
    """
    n = max(int(n_deliveries), 0)
    if n == 0 or supplier_mean is None:
        # Cold start: no data on this supplier. Use the population mean with the
        # full pooled spread (we genuinely do not know how it will perform).
        mu = pop.mean
        v_eff = pop.pooled_variance
    else:
        m_s = min(max(float(supplier_mean), _EPS), 1 - _EPS)
        # Shrink the mean toward the population (James-Stein), weighting by data.
        mu = (pop.kappa * pop.mean + n * m_s) / (pop.kappa + n)
        # Variance: trust the supplier's own delivery consistency once we have
        # enough deliveries to estimate it; otherwise borrow the typical
        # within-supplier variance from the population.
        if n >= _MIN_N_FOR_OWN_VARIANCE and supplier_var is not None:
            v_eff = max(float(supplier_var), _VAR_FLOOR)
        else:
            v_eff = pop.within_variance

    alpha_s, beta_s = _beta_from_mean_var(mu, v_eff)
    downside = float(stats.beta.ppf(quantile, alpha_s, beta_s))
    return {
        "mean": mu,
        "downside": downside,
        "alpha": alpha_s,
        "beta": beta_s,
    }


def _risk_level(mean: float, spread: float) -> str:
    if mean < _HIGH_RISK_FILL_RATE:
        return "High"
    if mean < _MEDIUM_RISK_FILL_RATE or spread >= _VOLATILITY_SPREAD:
        return "Medium"
    return "Low"


def supplier_fill_distributions(
    conn: duckdb.DuckDBPyConnection,
    quantile: float = 0.10,
) -> dict[str, dict[str, Any]]:
    """Per-supplier predictive fill-rate distributions under the hierarchical model.

    Returns a dict keyed by supplier_id. Each entry carries:
        supplier_name    display name
        n_deliveries     number of delivery records
        observed_mean    raw mean of per-delivery fill rates (None if no data)
        observed_std     raw std of per-delivery fill rates (None / 0 if <2)
        posterior_mean   shrunk mean mu_s
        downside         the q-quantile of the predictive Beta (the safe number)
        spread           posterior_mean - downside (volatility signal)
        alpha, beta      predictive Beta parameters
        shrinkage        weight on the population = kappa / (kappa + n_deliveries)
        risk_level       High / Medium / Low on posterior_mean + spread
        data_backed      True if the supplier has at least one delivery

    Also attaches "_prior" with the population diagnostics.
    """
    fills = _delivery_fill_rates(conn)
    pop = estimate_population(fills)

    out: dict[str, dict[str, Any]] = {
        "_prior": {
            "mean": round(pop.mean, 4),
            "pooled_variance": round(pop.pooled_variance, 6),
            "within_variance": round(pop.within_variance, 6),
            "kappa": round(pop.kappa, 4),
            "n_deliveries": pop.n_deliveries,
            "n_suppliers": pop.n_suppliers,
            "method": pop.method,
        }
    }

    if fills.empty:
        return out

    grouped = fills.groupby(["supplier_id", "supplier_name"])
    for (supplier_id, supplier_name), g in grouped:
        n = int(g.shape[0])
        m_s = float(g["fill_rate"].mean())
        v_s = float(g["fill_rate"].var(ddof=0)) if n >= 2 else None
        std_s = float(g["fill_rate"].std(ddof=0)) if n >= 2 else (0.0 if n == 1 else None)

        dist = supplier_distribution(n, m_s, v_s, pop, quantile)
        spread = dist["mean"] - dist["downside"]
        shrinkage = pop.kappa / (pop.kappa + n) if n > 0 else 1.0

        out[supplier_id] = {
            "supplier_name": supplier_name,
            "n_deliveries": n,
            "observed_mean": round(m_s, 4),
            "observed_std": (round(std_s, 4) if std_s is not None else None),
            "posterior_mean": round(dist["mean"], 4),
            "downside": round(dist["downside"], 4),
            "spread": round(spread, 4),
            "alpha": round(dist["alpha"], 4),
            "beta": round(dist["beta"], 4),
            "shrinkage": round(shrinkage, 4),
            "risk_level": _risk_level(dist["mean"], spread),
            "data_backed": True,
        }

    return out
