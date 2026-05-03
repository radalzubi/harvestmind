"""Weekly seasonal index curves for Indiana produce.

Returns a multiplier (centered on 1.0) for each ISO week number 1-52.
Used by the synthetic generator to scale base demand and yield.
"""

import numpy as np


def _sine_wave(peak_week: int, trough_week: int, amplitude: float, n: int = 52) -> np.ndarray:
    """Sinusoidal curve between peak and trough, repeated over n weeks."""
    weeks = np.arange(1, n + 1)
    phase = 2 * np.pi * (weeks - peak_week) / n
    return 1.0 + amplitude * np.cos(phase)


# Pre-computed seasonal indices: dict[seasonality_label -> ndarray shape (52,)]
_CURVES: dict[str, np.ndarray] = {
    # Summer vegetables: high Jun-Aug (weeks 24-35), low Nov-Mar
    "summer_peak": _sine_wave(peak_week=29, trough_week=3, amplitude=0.45),

    # Cool-season crops: spring (wk 14-20) and fall (wk 38-44) peaks
    "spring_fall": (
        _sine_wave(peak_week=17, trough_week=43, amplitude=0.30)
        + _sine_wave(peak_week=41, trough_week=17, amplitude=0.30)
    ) / 2 + 0.5,

    # Storage crops: slight dip in summer (fresh competition), stable otherwise
    "year_round": 1.0 - 0.10 * np.sin(2 * np.pi * (np.arange(1, 53) - 29) / 52),

    # Winter-preferred: root veg / alliums peak Oct-Feb
    "winter_dip": _sine_wave(peak_week=3, trough_week=29, amplitude=0.30),
}

# Normalize so mean == 1.0 over the year
for _k in _CURVES:
    _CURVES[_k] = _CURVES[_k] / _CURVES[_k].mean()


def seasonal_index(seasonality: str, week_number: int) -> float:
    """Return demand/yield multiplier for a given crop seasonality and ISO week (1-52)."""
    curve = _CURVES.get(seasonality, _CURVES["year_round"])
    idx = max(0, min(51, week_number - 1))
    return float(curve[idx])


def enso_yield_adjustment(enso_phase: str | None, crop_category: str) -> float:
    """ENSO-driven yield multiplier (Lobell et al. 2011 approximations for Midwest).

    El Niño → wetter/cooler spring, below-average summer heat stress → mixed effects.
    La Niña → drier, hotter → leafy greens suffer, corn/alliums more resilient.
    """
    table: dict[tuple[str, str], float] = {
        ("el_nino",  "leafy_green"): 1.05,
        ("el_nino",  "tomato"):      0.95,
        ("el_nino",  "pepper"):      0.92,
        ("el_nino",  "squash"):      1.02,
        ("el_nino",  "berry"):       0.98,
        ("el_nino",  "allium"):      1.03,
        ("el_nino",  "other"):       1.00,
        ("la_nina",  "leafy_green"): 0.88,
        ("la_nina",  "tomato"):      0.92,
        ("la_nina",  "pepper"):      0.90,
        ("la_nina",  "squash"):      0.94,
        ("la_nina",  "berry"):       0.85,
        ("la_nina",  "allium"):      1.05,
        ("la_nina",  "other"):       0.95,
        ("neutral",  "leafy_green"): 1.00,
        ("neutral",  "tomato"):      1.00,
        ("neutral",  "pepper"):      1.00,
        ("neutral",  "squash"):      1.00,
        ("neutral",  "berry"):       1.00,
        ("neutral",  "allium"):      1.00,
        ("neutral",  "other"):       1.00,
    }
    if enso_phase is None:
        return 1.0
    return table.get((enso_phase.lower(), crop_category.lower()), 1.0)
