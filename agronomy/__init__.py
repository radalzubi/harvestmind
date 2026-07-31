"""Agronomic and meteorological math, each formula tied to its source.

Modules
-------
heat_exposure        Schlenker-Roberts within-day exposure, GDD, extreme
                     degree days, VPD.
forecast_skill       Skill decay by lead time; attenuation of a measured
                     weather effect to what a forecast can actually support.
drought_index        SPI (gamma fit + normal transform), USDM percentile
                     bands.
shelf_life_kinetics  Q10 / Arrhenius temperature dependence of produce
                     deterioration.
systemic_risk        Correlated weather shocks and non-diversifiable
                     supplier risk.

Every module documents its primary references inline. The research note
behind them, including what the literature does NOT support, is in
docs/research/weather_agriculture_math.md.
"""
