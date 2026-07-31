"""Forecast skill decay, and what it does to a weather-informed decision.

THE PROBLEM THIS SOLVES
-----------------------
The yield-covariate gate (risk/yield_covariates.py) measures a heat-stress
effect on OBSERVED history, where the weather is known exactly. Applying
that same effect to a FUTURE delivery window is a different claim: the
weather then is a forecast, and forecasts decay. Applying the full
historical effect to a day-10 forecast asserts a confidence the atmosphere
does not permit.

The correction is classical attenuation. If the predictor actually used
(forecast heat flag) correlates rho with the predictor the effect was
measured against (realized heat flag), then the expected effect conditional
on the forecast is rho * delta, not delta. As rho -> 0 the shift vanishes
and the decision correctly falls back to climatology. This is the same
regression-dilution algebra as measurement error in a regressor; nothing
exotic, but omitting it is how weather-aware systems become overconfident.

WHAT THE ATMOSPHERE ACTUALLY PERMITS
------------------------------------
Anchors below are from published verification, not invented:

- Practical deterministic limit ~9-10 days; theoretical limit ~2 weeks.
  Zhang, F. et al. (2019). "What is the predictability limit of midlatitude
  weather?" J. Atmos. Sci. 76(4):1077-1091. doi:10.1175/JAS-D-18-0269.1

- Probabilistic (ensemble) skill horizon 16-23 days for instantaneous
  fields, defined as where ensemble CRPS stops beating climatology.
  Buizza, R. & Leutbecher, M. (2015). "The forecast skill horizon."
  ECMWF Tech Memo 754. doi:10.21957/6g2wkoyb6

- Precipitation skill collapses far sooner than temperature: small beyond
  day 7-8, summer convective skill effectively gone by day 8-9.
  ECMWF Newsletter 174, "Scale-dependent verification of precipitation and
  cloudiness"; cf. Skok, G. et al. (2016) QJRMS 142:2599-2615,
  doi:10.1002/qj.2849

- Skill has improved roughly one day per decade over ~40 years.
  Bauer, P., Thorpe, A. & Brunet, G. (2015). "The quiet revolution of
  numerical weather prediction." Nature 525:47-55. doi:10.1038/nature14956

- ENSO: skill is gated by the calendar, not just lead time. NOAA's spring
  predictability barrier — October-initialized forecasts of the following
  Nov-Jan explain ~90% of Nino 3.4 variance, but May-initialized forecasts
  of the SAME season explain only ~50%.
  L'Heureux, M. (2015), NOAA Climate.gov ENSO Blog.

HOW THE DECAY CURVE IS BUILT
----------------------------
An exponential rho(L) = exp(-L / tau) is fitted per variable so the curve
passes through its published horizon: rho reaches SKILL_FLOOR exactly at
the horizon lead time. This is a smooth interpolation ANCHORED on published
endpoints, not a curve fitted to our own verification data — stated plainly
because the distinction matters. Operators running long enough to verify
their own regional skill should replace these with measured values.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# rho at which a forecast is treated as carrying no usable information.
# 0.3 is a deliberately conservative reading of "no longer beats
# climatology": it retires the signal slightly before the published
# horizon rather than after it.
SKILL_FLOOR = 0.30

# Published skill horizons in days: the lead time by which each variable's
# forecast has stopped beating climatology in operational verification.
SKILL_HORIZON_DAYS: dict[str, float] = {
    # Temperature is the most predictable surface field, and heat-stress
    # flags are a temperature threshold, so this is the one that governs
    # our heat covariate.
    "temperature": 10.0,      # Zhang et al. 2019 practical limit
    "precipitation": 8.0,     # ECMWF Newsletter 174; Skok et al. 2016
    "ensemble_mean": 16.0,    # Buizza & Leutbecher 2015, lower bound of 16-23
}


@dataclass(frozen=True)
class SkillModel:
    """Exponential skill decay anchored on a published horizon."""

    variable: str = "temperature"
    horizon_days: float = 10.0
    floor: float = SKILL_FLOOR

    @property
    def tau(self) -> float:
        """Decay constant chosen so rho(horizon) == floor exactly."""
        return self.horizon_days / -np.log(self.floor)

    def rho(self, lead_days: float | np.ndarray) -> np.ndarray:
        """Forecast-vs-realized correlation at a given lead time.

        Lead 0 (the window is already observed, e.g. in a backtest) gives
        rho = 1: no attenuation, because there is no forecast error.
        """
        lead = np.maximum(np.asarray(lead_days, dtype=float), 0.0)
        return np.clip(np.exp(-lead / self.tau), 0.0, 1.0)

    def is_informative(self, lead_days: float) -> bool:
        """Is the forecast still beating climatology at this lead?"""
        return bool(self.rho(lead_days) > self.floor)


def skill_model_for(variable: str = "temperature") -> SkillModel:
    """Skill model for a named variable, defaulting to temperature."""
    horizon = SKILL_HORIZON_DAYS.get(variable, SKILL_HORIZON_DAYS["temperature"])
    return SkillModel(variable=variable, horizon_days=horizon)


def attenuate_effect(
    delta: float,
    lead_days: float,
    variable: str = "temperature",
) -> dict[str, float | bool | str]:
    """Shrink a historically-measured weather effect to its forecast lead.

    delta is the effect measured against KNOWN weather (lead 0). At lead L
    the forecast carries only rho(L) of that information, so the expected
    effect is rho(L) * delta.

    Returns the attenuated delta plus the reasoning, so an operator-facing
    explanation can state the lead time and skill actually used rather than
    presenting a shifted number without provenance.
    """
    model = skill_model_for(variable)
    rho = float(model.rho(lead_days))
    informative = rho > model.floor
    applied = float(delta) * rho if informative else 0.0

    return {
        "delta_measured": float(delta),
        "delta_applied": applied,
        "forecast_skill_rho": round(rho, 4),
        "lead_days": float(lead_days),
        "variable": variable,
        "horizon_days": model.horizon_days,
        "informative": informative,
        "basis": (
            f"exponential decay anchored on a published {model.horizon_days:.0f}-day "
            f"skill horizon for {variable}; effect attenuated to rho*delta"
        ),
        "reason": (
            f"forecast skill {rho:.2f} at {lead_days:.1f}-day lead"
            if informative else
            f"lead {lead_days:.1f} d exceeds usable {variable} forecast skill "
            f"(horizon ~{model.horizon_days:.0f} d) — falling back to climatology"
        ),
    }


def residual_variance_share(
    lead_days: float, variable: str = "temperature",
) -> float:
    """Share of the weather signal's variance still UNRESOLVED at this lead.

    A predictor correlating rho with the target explains rho^2 of its
    variance, leaving 1 - rho^2 unresolved. Zero at lead 0 (weather known),
    rising to 1 once the forecast carries no information.
    """
    rho = float(skill_model_for(variable).rho(lead_days))
    return float(np.clip(1.0 - rho ** 2, 0.0, 1.0))


def unresolved_weather_variance(
    delta: float,
    lead_days: float,
    weather_variance: float = 0.25,
    variable: str = "temperature",
) -> float:
    """Extra outcome variance from not knowing the future weather.

    Decomposing the conditional variance of the fill rate given a forecast:

        Var(fill | forecast) = Var(fill | weather) + delta^2 * (1 - rho^2) * Var(W)

    The second term is returned here. It is ZERO when the weather is known
    (lead 0, e.g. replaying history in a backtest) and grows to its maximum
    once forecast skill is exhausted — the correct direction, and the
    reason a long-lead commitment deserves a wider distribution even after
    the mean shift has been attenuated away.

    weather_variance defaults to 0.25, the variance of a Bernoulli(0.5)
    heat-flag, i.e. the maximum for a binary indicator. Supply the
    empirical variance of the flag when it is known.
    """
    share = residual_variance_share(lead_days, variable)
    return float(delta ** 2 * share * weather_variance)


def skill_table(max_lead_days: int = 16) -> list[dict]:
    """Skill by lead day for every tracked variable — for reports and docs."""
    rows = []
    for lead in range(0, max_lead_days + 1):
        row: dict = {"lead_days": lead}
        for var in SKILL_HORIZON_DAYS:
            row[var] = round(float(skill_model_for(var).rho(lead)), 3)
        rows.append(row)
    return rows
