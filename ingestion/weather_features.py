"""Bridge: fact_weather_obs -> weekly feature frame for the forecaster.

forecasting/demand/feature_engineering.build_features accepts an
optional weather_df with columns
    [week_start, tavg_c, precip_mm, heat_stress_flag, enso_oni_index]
but nothing produced that frame until now. This module aggregates the
daily observations the fetchers store into exactly that shape, so
wiring weather into a forecast run is one call:

    weather_df = weekly_weather_frame(conn, county_fips="18157")
    forecaster.fit(orders_df, weather_df=weather_df)

Weekly aggregation: mean temperature, total precipitation, ANY day
heat-stressed flags the week (heat damage is threshold-driven, not
average-driven), mean ONI. Also carries drought_monitor_cat (modal)
and gdd_base10 (sum) for the yield-covariate side.
"""

from __future__ import annotations

import pandas as pd


def weekly_weather_frame(
    conn,
    county_fips: str | None = None,
) -> pd.DataFrame:
    """Aggregate daily fact_weather_obs rows to forecaster-ready weeks."""
    where = "WHERE county_fips = ?" if county_fips else ""
    params = [county_fips] if county_fips else []
    df = conn.execute(
        (  # nosec B608 - filters parameterised
            f"""
        SELECT DATE_TRUNC('week', obs_date)          AS week_start,
               AVG(tavg_c)                           AS tavg_c,
               SUM(precip_mm)                        AS precip_mm,
               MAX(CASE WHEN heat_stress_flag THEN 1 ELSE 0 END) = 1
                                                     AS heat_stress_flag,
               AVG(enso_oni_index)                   AS enso_oni_index,
               SUM(gdd_base10)                       AS gdd_base10,
               MODE(drought_monitor_cat)             AS drought_monitor_cat
        FROM fact_weather_obs
        {where}
        GROUP BY 1
        ORDER BY 1
        """),  # nosec B608 - filters parameterised
        params,
    ).df()
    if df.empty:
        return df
    df["week_start"] = pd.to_datetime(df["week_start"])
    return df
