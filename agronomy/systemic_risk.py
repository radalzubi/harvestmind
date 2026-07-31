"""Correlated weather shocks: why supplier risk does not diversify away.

THE FINDING THAT MOTIVATES THIS MODULE
--------------------------------------
Miranda, M.J. & Glauber, J.W. (1997). "Systemic Risk, Reinsurance, and the
Failure of Crop Insurance Markets." American Journal of Agricultural
Economics 79(1):206-215. doi:10.2307/1243954

They show crop insurers' portfolios are 20 to 50 times riskier than they
would be if farm-level yields were independent, because weather shocks hit
whole regions at once. Their conclusion is that private crop insurance is
"doomed to fail" without reinsurance for precisely this reason.

That number is directly relevant to procurement. A buyer sourcing from
twelve growers in one region does NOT hold twelve independent bets. Heat,
drought and freeze arrive regionally, so shortfalls stack instead of
cancelling. Supporting evidence: 43-56% of large Illinois/Kansas farm
revenue losses were correlated with county-level losses, and the dominant
insured perils are the spatially correlated ones (drought >40% of wheat
indemnities, precipitation >22% of corn) rather than idiosyncratic hail
(~10%) — farmdoc daily (2016) summarizing Zulauf et al. (2013) and RMA
administrative data.

WHY THIS MATTERS FOR OUR OPTIMIZER SPECIFICALLY
-----------------------------------------------
An earlier stress test found the two-stage stochastic program tying the
deterministic LP on synthetic data. The diagnosis was that the mock drew
INDEPENDENT supplier shortfalls, which average out across suppliers, so
the aggregate became tight around its mean and hedging bought nothing.
Correlated weather shocks are the exact opposite regime: the aggregate
stays wide no matter how many suppliers are added, which is when a
stochastic hedge earns its keep. This module quantifies that difference so
the choice of optimizer can be justified from the data rather than assumed.

THE ALGEBRA
-----------
For n suppliers with equal variance sigma^2 and equal pairwise correlation
rho, the variance of the MEAN fill rate is

    Var(mean) = sigma^2 * [ 1/n + (n-1)/n * rho ]

Independence (rho = 0) gives sigma^2/n, which vanishes as n grows. With
rho > 0 the variance floors at sigma^2 * rho no matter how many suppliers
are added: that floor is the non-diversifiable, systemic component. The
risk multiplier relative to independence is therefore

    M(n, rho) = 1 + (n - 1) * rho

which inverts to rho = (M - 1)/(n - 1) — letting the published 20-50x
multiplier be read back as an implied correlation (see
implied_correlation_from_multiplier).
"""

from __future__ import annotations

import numpy as np

# Miranda & Glauber (1997): insurer portfolios 20-50x riskier than under
# independence. Kept as the calibration anchor for implied correlation.
MIRANDA_GLAUBER_MULTIPLIER_RANGE = (20.0, 50.0)


def portfolio_variance(
    sigma: float, n_suppliers: int, rho: float,
) -> dict[str, float]:
    """Variance of the mean fill rate under equicorrelated shocks.

    Returns both the correlated and independent variances, their ratio, and
    the systemic floor that no amount of supplier diversification removes.
    """
    if n_suppliers < 1:
        raise ValueError("n_suppliers must be >= 1")
    n = float(n_suppliers)
    var_ind = sigma ** 2 / n
    var_corr = sigma ** 2 * (1.0 / n + (n - 1.0) / n * rho)
    return {
        "n_suppliers": int(n_suppliers),
        "rho": float(rho),
        "variance_independent": float(var_ind),
        "variance_correlated": float(var_corr),
        "risk_multiplier": float(var_corr / var_ind) if var_ind > 0 else 1.0,
        # The irreducible floor: sigma^2 * rho as n -> infinity.
        "systemic_variance_floor": float(sigma ** 2 * rho),
        "diversifiable_share": float(1.0 - rho) if rho <= 1 else 0.0,
    }


def implied_correlation_from_multiplier(
    multiplier: float, n_suppliers: int,
) -> float:
    """Invert M = 1 + (n-1)*rho to recover the implied correlation.

    Applying this to Miranda & Glauber's 20-50x range at realistic
    portfolio sizes recovers correlations of roughly 0.2-0.5 — a useful
    sanity band for what "regionally correlated" actually means
    numerically, rather than picking a correlation by taste.
    """
    if n_suppliers < 2:
        return 0.0
    return float(np.clip((multiplier - 1.0) / (n_suppliers - 1.0), 0.0, 1.0))


def effective_independent_count(n_suppliers: int, rho: float) -> float:
    """How many INDEPENDENT suppliers the correlated portfolio is worth.

    n_eff = n / (1 + (n-1) rho). The honest headline number for an
    operator: "your twelve growers behave like three independent ones."
    """
    if n_suppliers < 1:
        return 0.0
    n = float(n_suppliers)
    return float(n / (1.0 + (n - 1.0) * rho))


def estimate_shock_correlation(fill_matrix: np.ndarray) -> dict[str, float]:
    """Estimate mean pairwise correlation of supplier fill rates.

    fill_matrix: (n_periods, n_suppliers) observed fill rates.

    Returns the mean off-diagonal correlation and the derived portfolio
    quantities. This is measured from the operator's own delivery history —
    the published multiplier is only a sanity check on the result, never a
    substitute for it.
    """
    arr = np.asarray(fill_matrix, dtype=float)
    if arr.ndim != 2 or arr.shape[0] < 3 or arr.shape[1] < 2:
        return {"status": "insufficient_data",
                "n_periods": int(arr.shape[0]) if arr.ndim == 2 else 0,
                "n_suppliers": int(arr.shape[1]) if arr.ndim == 2 else 0}

    # Drop suppliers with no variation — correlation is undefined for them.
    keep = np.nanstd(arr, axis=0) > 1e-9
    arr = arr[:, keep]
    if arr.shape[1] < 2:
        return {"status": "insufficient_variation",
                "n_suppliers": int(arr.shape[1])}

    corr = np.corrcoef(arr, rowvar=False)
    off = corr[~np.eye(corr.shape[0], dtype=bool)]
    off = off[np.isfinite(off)]
    if off.size == 0:
        return {"status": "insufficient_variation"}

    rho = float(np.mean(off))
    n = int(arr.shape[1])
    sigma = float(np.mean(np.nanstd(arr, axis=0)))
    port = portfolio_variance(sigma, n, max(rho, 0.0))

    return {
        "status": "ok",
        "n_periods": int(arr.shape[0]),
        "n_suppliers": n,
        "mean_pairwise_correlation": round(rho, 4),
        "mean_supplier_sigma": round(sigma, 4),
        "risk_multiplier_vs_independent": round(port["risk_multiplier"], 2),
        "effective_independent_suppliers": round(
            effective_independent_count(n, max(rho, 0.0)), 2),
        "systemic_share_of_variance": round(max(rho, 0.0), 4),
        "interpretation": _interpret(rho, n),
        "reference": "Miranda & Glauber 1997 AJAE 79(1):206-215",
    }


def _interpret(rho: float, n: int) -> str:
    """Plain-language reading, including what it implies for the optimizer."""
    n_eff = effective_independent_count(n, max(rho, 0.0))
    if rho < 0.05:
        return (
            f"Shortfalls look close to independent (rho={rho:.2f}); {n} suppliers "
            f"behave like {n_eff:.1f} independent ones. Aggregate supply is tight "
            "around its mean, so a stochastic hedge should add little over a "
            "deterministic plan — expect low value of the stochastic solution."
        )
    if rho < 0.25:
        return (
            f"Mild correlation (rho={rho:.2f}); {n} suppliers behave like "
            f"{n_eff:.1f} independent ones. Some systemic risk remains after "
            "diversification; a stochastic hedge should add modest value."
        )
    return (
        f"Strongly correlated shortfalls (rho={rho:.2f}); {n} suppliers behave "
        f"like only {n_eff:.1f} independent ones. Adding suppliers in the same "
        "weather region will NOT diversify this away. This is the regime where "
        "stochastic and risk-averse (CVaR) optimization earn their keep."
    )
