"""Heat exposure metrics from daily Tmin/Tmax — the Schlenker-Roberts construction.

Why not just use daily mean temperature: the canonical result in this
literature is that crop yield responds to temperature NONLINEARLY and
ASYMMETRICALLY — yields rise gently with heat up to a threshold and fall
steeply above it. Schlenker & Roberts (2009) estimate those thresholds at
29 C for corn, 30 C for soybeans, 32 C for cotton. A daily MEAN of 25 C
hides whether the day peaked at 26 C (harmless) or 34 C (damaging), so the
mean systematically understates damage.

Their fix, reimplemented here: approximate the within-day temperature
trajectory as a sinusoid between that day's Tmin and Tmax, then measure how
much TIME the crop spent at each temperature. Everything else (growing
degree days, extreme degree days, time-in-bin exposure vectors) is a
functional of that within-day distribution.

The sinusoid has an exact closed form. If
    T(t) = M + A*sin(2*pi*t),  M = (Tmax+Tmin)/2,  A = (Tmax-Tmin)/2
then over a full period T is distributed as the arcsine law, so the
fraction of the day spent at or below h is

    F(h) = 1/2 + arcsin((h - M)/A) / pi        for Tmin <= h <= Tmax

and the degree-days above a threshold h integrate in closed form to

    DD(h) = (1/pi) * [ (M - h)*(pi/2 - theta) + A*cos(theta) ],
    theta = arcsin((h - M)/A)

This is the classical "single sine" degree-day method (Baskerville & Emin
1969, Ecology 50:514-517). Both formulas are derived from the sinusoid
directly and are verified against numerical integration in the tests, so
they stand on their own arithmetic regardless of citation.

References
----------
Schlenker, W. & Roberts, M.J. (2009). "Nonlinear temperature effects
    indicate severe damages to U.S. crop yields under climate change."
    PNAS 106(37):15594-15598. doi:10.1073/pnas.0906865106
    - thresholds 29/30/32 C; sinusoidal within-day interpolation; 1 C bin
      exposure vectors; degree days as the piecewise-linear special case.
    - magnitude anchor: substituting one day at 40 C for one day at 29 C
      predicts roughly a 7% corn yield decline.
McMaster, G.S. & Wilhelm, W.W. (1997). "Growing degree-days: one equation,
    two interpretations." Agricultural and Forest Meteorology 87(4):291-300.
    doi:10.1016/S0168-1923(97)00027-0
    - the two GDD conventions below, and why they disagree.
Lobell, D.B. et al. (2013). "The critical role of extreme heat for maize
    production in the United States." Nature Climate Change 3:497-501.
    doi:10.1038/nclimate1832
    - extreme degree days (>30 C) dominate seasonal rainfall in explanatory
      power; the mechanism is largely VPD-driven water stress.
Hatfield, J.L. & Prueger, J.H. (2015). "Temperature extremes: Effect on
    plant growth and development." Weather and Climate Extremes 10:4-10.
    doi:10.1016/j.wace.2015.08.001
    - source of the VPD (Magnus/Tetens) coefficients used below, and of the
      horticultural thresholds in CROP_THRESHOLDS_C.

Honesty note on specialty crops: there is no vegetable-crop equivalent of
Schlenker & Roberts. The METHOD here transfers (nothing about it is
corn-specific), but vegetable thresholds come from controlled-environment
horticultural studies and are ranges, not regression breakpoints with
standard errors. CROP_THRESHOLDS_C records that distinction explicitly.
"""

from __future__ import annotations

import numpy as np

# Damage thresholds, C. `source` distinguishes econometrically ESTIMATED
# breakpoints from horticultural OBSERVED ranges — a real difference in
# evidential strength that callers should be able to see.
CROP_THRESHOLDS_C: dict[str, dict] = {
    "corn": {"base": 10.0, "damage": 29.0, "source": "estimated",
             "ref": "Schlenker & Roberts 2009 PNAS"},
    "soybean": {"base": 10.0, "damage": 30.0, "source": "estimated",
                "ref": "Schlenker & Roberts 2009 PNAS"},
    "cotton": {"base": 15.6, "damage": 32.0, "source": "estimated",
               "ref": "Schlenker & Roberts 2009 PNAS"},
    # Horticultural: observed critical points, cultivar- and system-
    # dependent. Treat as midpoints of real ranges, not point estimates.
    "tomato": {"base": 10.0, "damage": 32.0, "source": "observed",
               "range_c": (32.0, 35.0), "night_damage": 21.0,
               "ref": "Hatfield & Prueger 2015; Sato et al. 2000"},
    "lettuce": {"base": 4.4, "damage": 30.0, "source": "observed",
                "range_c": (30.0, 33.0),
                "ref": "Hatfield & Prueger 2015; Dufault et al. 2009"},
    "pepper": {"base": 10.0, "damage": 32.0, "source": "observed_weak",
               "ref": "qualitative horticultural literature only"},
    "cucumber": {"base": 10.0, "damage": 32.0, "source": "observed_weak",
                 "ref": "qualitative horticultural literature only"},
}

# Generic vegetable heat-stress threshold used when the crop is unknown.
# Matches the flag already used by the weather fetchers.
DEFAULT_HEAT_STRESS_C = 32.0


def _sinusoid_params(tmin: np.ndarray, tmax: np.ndarray):
    """Midpoint and amplitude of the within-day sinusoid."""
    tmin = np.asarray(tmin, dtype=float)
    tmax = np.asarray(tmax, dtype=float)
    mid = (tmax + tmin) / 2.0
    amp = (tmax - tmin) / 2.0
    return mid, amp


def fraction_of_day_below(
    tmin: np.ndarray, tmax: np.ndarray, threshold_c: float,
) -> np.ndarray:
    """Fraction of the day spent at or below ``threshold_c``.

    Arcsine-law CDF of the within-day sinusoid. Returns 0 when the whole
    day is above the threshold, 1 when the whole day is below it.
    """
    mid, amp = _sinusoid_params(tmin, tmax)
    out = np.where(threshold_c >= mid + amp, 1.0, 0.0)
    # Only the strictly-crossing days need the arcsine; guard amp == 0
    # (isothermal day) which the two constant branches already cover.
    crossing = (amp > 0) & (threshold_c > mid - amp) & (threshold_c < mid + amp)
    if np.any(crossing):
        ratio = np.clip((threshold_c - mid[crossing]) / amp[crossing], -1.0, 1.0)
        out = np.asarray(out, dtype=float)
        out[crossing] = 0.5 + np.arcsin(ratio) / np.pi
    return np.asarray(out, dtype=float)


def time_in_bins(
    tmin: np.ndarray, tmax: np.ndarray,
    lower_c: float = -5.0, upper_c: float = 50.0, width_c: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Schlenker-Roberts exposure vector: days spent in each 1 C bin.

    This is the empirical distribution phi(h) of equation (2) in the paper,
    summed over the supplied days. Returns (bin_edges, days_per_bin) where
    days_per_bin sums to the number of days supplied.
    """
    edges = np.arange(lower_c, upper_c + width_c, width_c, dtype=float)
    cdf = np.stack([fraction_of_day_below(tmin, tmax, e) for e in edges])
    per_day = np.diff(cdf, axis=0)          # (n_bins, n_days)
    return edges, per_day.sum(axis=1)


def degree_days_above(
    tmin: np.ndarray, tmax: np.ndarray, threshold_c: float,
) -> np.ndarray:
    """Degree-days accumulated ABOVE a threshold, per day (single sine).

    With threshold = the crop's damage threshold this is "extreme degree
    days" (EDD) / "killing degree days" (KDD) — the variable that carries
    most of the yield damage signal in Schlenker & Roberts (2009) and
    Lobell et al. (2013).
    """
    mid, amp = _sinusoid_params(tmin, tmax)
    out = np.zeros_like(mid, dtype=float)

    # Whole day above threshold: reduces to the daily mean excess.
    fully_above = threshold_c <= mid - amp
    out[fully_above] = mid[fully_above] - threshold_c

    crossing = (amp > 0) & (threshold_c > mid - amp) & (threshold_c < mid + amp)
    if np.any(crossing):
        m, a = mid[crossing], amp[crossing]
        theta = np.arcsin(np.clip((threshold_c - m) / a, -1.0, 1.0))
        out[crossing] = (
            (m - threshold_c) * (np.pi / 2 - theta) + a * np.cos(theta)
        ) / np.pi
    # Whole day below threshold stays 0.
    return out


def growing_degree_days(
    tmin: np.ndarray, tmax: np.ndarray,
    base_c: float = 10.0, cap_c: float | None = 30.0,
    method: str = "cap_then_average",
) -> np.ndarray:
    """Growing degree days, per day.

    McMaster & Wilhelm (1997) showed the same GDD equation is computed two
    incompatible ways in practice; results diverge whenever Tmin < base but
    Tmax is well above it (common in spring and in continental climates).
    Both are provided; the caller must choose, and the choice is recorded.

    method="cap_then_average" (USDA / extension convention, the default):
        clamp Tmin and Tmax into [base, cap] FIRST, then average and
        subtract base. Still credits warm daytime hours on a cold-night day.
    method="average_then_floor":
        average raw Tmin/Tmax first, subtract base, floor at zero. Can zero
        out a day that had genuinely warm afternoon hours.
    method="single_sine":
        the sinusoid-integrated version — degree-days above base minus
        degree-days above cap. The most physically faithful of the three
        and consistent with degree_days_above() used elsewhere here.
    """
    tmin = np.asarray(tmin, dtype=float)
    tmax = np.asarray(tmax, dtype=float)

    if method == "single_sine":
        gdd = degree_days_above(tmin, tmax, base_c)
        if cap_c is not None:
            gdd = gdd - degree_days_above(tmin, tmax, cap_c)
        return np.maximum(gdd, 0.0)

    if method == "cap_then_average":
        hi = np.minimum(tmax, cap_c) if cap_c is not None else tmax
        hi = np.maximum(hi, base_c)
        lo = np.clip(tmin, base_c, cap_c if cap_c is not None else np.inf)
        return np.maximum((hi + lo) / 2.0 - base_c, 0.0)

    if method == "average_then_floor":
        return np.maximum((tmax + tmin) / 2.0 - base_c, 0.0)

    raise ValueError(f"unknown GDD method: {method!r}")


def saturation_vapor_pressure_kpa(temp_c: np.ndarray) -> np.ndarray:
    """Saturation vapour pressure, kPa (Magnus/Tetens form).

    Coefficients as given in Hatfield & Prueger (2015):
        e*(T) = 0.61121 * exp(17.502 T / (T + 240.97))
    """
    t = np.asarray(temp_c, dtype=float)
    return 0.61121 * np.exp(17.502 * t / (t + 240.97))


def vapor_pressure_deficit_kpa(
    temp_c: np.ndarray, relative_humidity_pct: np.ndarray,
) -> np.ndarray:
    """Vapour pressure deficit, kPa.

    VPD = e*(T) * (1 - RH/100). Saturation vapour pressure rises
    EXPONENTIALLY with temperature, so atmospheric water demand and heat
    stress compound nonlinearly — the mechanism Lobell et al. (2013)
    identify behind most of the extreme-degree-day yield effect.
    """
    rh = np.clip(np.asarray(relative_humidity_pct, dtype=float), 0.0, 100.0)
    return saturation_vapor_pressure_kpa(temp_c) * (1.0 - rh / 100.0)


def season_exposure(
    tmin: np.ndarray, tmax: np.ndarray, crop: str = "tomato",
) -> dict[str, float]:
    """Season-level exposure summary for one crop.

    Returns the two regressors of the canonical Schlenker-Roberts
    specification (beneficial degree days below the damage threshold, and
    harmful degree days above it) plus diagnostic counts. The evidence
    grade of the threshold travels with the result so downstream callers
    cannot silently treat a horticultural range as an estimated breakpoint.
    """
    spec = CROP_THRESHOLDS_C.get(crop)
    if spec is None:
        spec = {"base": 10.0, "damage": DEFAULT_HEAT_STRESS_C,
                "source": "default", "ref": "generic vegetable default"}

    base, damage = spec["base"], spec["damage"]
    dd_base = degree_days_above(tmin, tmax, base)
    dd_damage = degree_days_above(tmin, tmax, damage)
    beneficial = np.maximum(dd_base - dd_damage, 0.0)

    return {
        "crop": crop,
        "base_c": base,
        "damage_threshold_c": damage,
        "threshold_evidence": spec["source"],
        "threshold_reference": spec["ref"],
        "n_days": int(np.size(tmin)),
        # The two exposure regressors.
        "beneficial_degree_days": float(beneficial.sum()),
        "extreme_degree_days": float(dd_damage.sum()),
        # Diagnostics.
        "days_with_any_heat_stress": int((np.asarray(tmax) > damage).sum()),
        "max_tmax_c": float(np.max(tmax)) if np.size(tmax) else float("nan"),
    }
