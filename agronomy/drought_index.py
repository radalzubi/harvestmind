"""Standardized Precipitation Index and the USDM category mapping.

SPI turns an accumulated precipitation total into a z-score against that
location's own history: fit a gamma distribution to the accumulation,
evaluate the CDF, then map that probability through the inverse standard
normal. The result is comparable across locations and seasons, which raw
millimetres are not.

Algorithm (McKee, Doesken & Kleist 1993; Guttman 1999; WMO-No. 1090):

1. Accumulate precipitation over an N-month window.
2. Fit a two-parameter gamma by Thom's maximum-likelihood approximation:
       A     = ln(xbar) - mean(ln(x))
       alpha = (1 + sqrt(1 + 4A/3)) / (4A)
       beta  = xbar / alpha
3. Mix in the zero-precipitation atom: H(x) = q + (1-q) G(x), q = P(x=0),
   because the gamma is undefined at zero and dry months are common.
4. Transform to a standard normal. scipy's exact inverse normal is used
   here; the Abramowitz & Stegun 26.2.23 rational approximation from the
   original papers is retained as _as_inverse_normal for reference and is
   checked against the exact value in the tests.

References
----------
McKee, T.B., Doesken, N.J. & Kleist, J. (1993). "The relationship of
    drought frequency and duration to time scales." 8th Conference on
    Applied Climatology, American Meteorological Society, 179-184.
Guttman, N.B. (1999). "Accepting the Standardized Precipitation Index."
    JAWRA 35(2):311-322. doi:10.1111/j.1752-1688.1999.tb03592.x
WMO (2012). Standardized Precipitation Index User Guide. WMO-No. 1090.
Vicente-Serrano, S.M., Beguería, S. & López-Moreno, J.I. (2010). "A
    multiscalar drought index sensitive to global warming: the SPEI."
    Journal of Climate 23(7):1696-1718. doi:10.1175/2009JCLI2909.1
    - SPEI extends SPI to P minus PET with a log-logistic fit; noted here
      because it generally outperforms SPI as a yield predictor, and is the
      natural next step once PET inputs are available.
Svoboda, M. et al. (2002). "The Drought Monitor." BAMS 83(8):1181-1190.
    doi:10.1175/1520-0477(2002)083<1181:TDM>2.3.CO;2
    - source of the USDM percentile bands and SPI cut-offs below.

Yield relevance (for calibration expectations, not hard-coded anywhere):
    Zipper, S.C., Qiu, J. & Kucharik, C.J. (2016) ERL 11:094021,
    doi:10.1088/1748-9326/11/9/094021 — SPEI explains ~12.6% of US national
    maize yield variance and ~12.8% for soybean, rising to county-level R^2
    of 0.57/0.67. Weather is a real but partial driver; cf. Ray et al.
    (2015) Nat. Commun. 6:5989, climate explains roughly a third of global
    yield variability.
"""

from __future__ import annotations

import numpy as np
from scipy import stats

# McKee et al. (1993) classification, as reproduced in WMO-No. 1090.
SPI_CLASSES: list[tuple[float, float, str]] = [
    (2.0, np.inf, "extremely wet"),
    (1.5, 2.0, "very wet"),
    (1.0, 1.5, "moderately wet"),
    (-1.0, 1.0, "near normal"),
    (-1.5, -1.0, "moderately dry"),
    (-2.0, -1.5, "severely dry"),
    (-np.inf, -2.0, "extremely dry"),
]

# US Drought Monitor categories: percentile bands (Svoboda et al. 2002,
# Table 2) with the matching SPI cut-offs from the same table.
USDM_CATEGORIES: list[dict] = [
    {"cat": "D0", "label": "abnormally dry", "pct_lo": 21, "pct_hi": 30,
     "spi_max": -0.5},
    {"cat": "D1", "label": "moderate drought", "pct_lo": 11, "pct_hi": 20,
     "spi_max": -0.8},
    {"cat": "D2", "label": "severe drought", "pct_lo": 6, "pct_hi": 10,
     "spi_max": -1.3},
    {"cat": "D3", "label": "extreme drought", "pct_lo": 3, "pct_hi": 5,
     "spi_max": -1.6},
    {"cat": "D4", "label": "exceptional drought", "pct_lo": 0, "pct_hi": 2,
     "spi_max": -2.0},
]


def _as_inverse_normal(p: float) -> float:
    """Abramowitz & Stegun 26.2.23 rational approximation (reference only).

    The constant c1 is 0.802853; a widely copied secondary source
    transposes it to 0.802583. Kept here so the original papers'
    formulation is reproducible and testable against scipy's exact value.
    """
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308
    upper = p > 0.5
    pp = 1.0 - p if upper else p
    pp = max(pp, 1e-12)
    t = np.sqrt(-2.0 * np.log(pp))
    z = t - (c0 + c1 * t + c2 * t ** 2) / (
        1.0 + d1 * t + d2 * t ** 2 + d3 * t ** 3)
    return float(z if upper else -z)


def fit_gamma_thom(values: np.ndarray) -> tuple[float, float, float]:
    """Fit a gamma to positive precipitation totals (Thom's MLE approx).

    Returns (alpha, beta, q) where q is the probability of a zero total.
    """
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        raise ValueError("no finite values to fit")

    n_zero = int(np.sum(x <= 0.0))
    q = n_zero / x.size
    pos = x[x > 0.0]
    if pos.size < 2:
        raise ValueError("need at least 2 positive values to fit a gamma")

    xbar = float(pos.mean())
    A = float(np.log(xbar) - np.mean(np.log(pos)))
    A = max(A, 1e-9)                       # guard the degenerate constant case
    alpha = (1.0 + np.sqrt(1.0 + 4.0 * A / 3.0)) / (4.0 * A)
    beta = xbar / alpha
    return float(alpha), float(beta), float(q)


def spi(
    accumulations: np.ndarray,
    reference: np.ndarray | None = None,
) -> np.ndarray:
    """Standardized Precipitation Index for each accumulation.

    accumulations: precipitation totals over the chosen window.
    reference: the climatology to fit against; defaults to the
        accumulations themselves. Supplying a longer reference period is
        the correct usage — WMO-No. 1090 recommends at least 30 years, and
        a short reference makes every value look near-normal by
        construction.
    """
    obs = np.asarray(accumulations, dtype=float)
    ref = obs if reference is None else np.asarray(reference, dtype=float)
    alpha, beta, q = fit_gamma_thom(ref)

    g = stats.gamma.cdf(np.maximum(obs, 0.0), a=alpha, scale=beta)
    h = q + (1.0 - q) * g
    h = np.clip(h, 1e-10, 1.0 - 1e-10)
    return stats.norm.ppf(h)


def classify_spi(value: float) -> str:
    """McKee et al. (1993) wet/dry class for an SPI value."""
    for lo, hi, label in SPI_CLASSES:
        if lo <= value < hi:
            return label
    return "near normal"


def usdm_category_from_percentile(percentile: float) -> str | None:
    """Map a climatological percentile to a USDM D0-D4 category.

    Returns None when the location is wetter than the D0 band. Note the
    real USDM is a convergence-of-evidence blend of several indicators plus
    expert adjustment from local reports, not a single percentile lookup
    (Svoboda et al. 2002) — this function reproduces only the percentile
    scaffolding, and is labelled as such wherever it is surfaced.
    """
    p = float(percentile)
    for c in USDM_CATEGORIES:
        if c["pct_lo"] <= p <= c["pct_hi"]:
            return c["cat"]
    return None


def drought_severity_weight(category: str | None) -> float:
    """Monotone 0-1 severity weight for a USDM category.

    A convenience encoding for use as a model feature, so D0 through D4
    enter as an ordered variable rather than as unordered strings. The
    spacing is linear by design and carries no claim about yield impact
    being linear in category.
    """
    order = {None: 0.0, "D0": 0.2, "D1": 0.4, "D2": 0.6, "D3": 0.8, "D4": 1.0}
    return order.get(category, 0.0)
