"""Open-Meteo historical weather fetcher (archive API).

Replaces the two-station NOAA CDO limitation: Open-Meteo's archive API
serves daily reanalysis weather for ANY lat/lon back to 1940, with no
API key and generous rate limits. This makes county-level weather for
every supplier location a one-call fetch.

Endpoint: https://archive-api.open-meteo.com/v1/archive

Derived agronomy features (computed here, stored on fact_weather_obs):
    heat_stress_flag  tmax > 32 C (vegetable heat-stress threshold,
                      matching the NOAA fetcher's convention)
    gdd_base10        growing degree days, base 10 C, from tavg

Geocoding helper uses https://geocoding-api.open-meteo.com (also
keyless) so a supplier's town or county name resolves to coordinates.

All functions gracefully return empty frames / zero counts when the
network is unavailable — same posture as the other connectors.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"

# County centroids for the current Indiana pilot footprint. Extend as
# operators are onboarded, or resolve arbitrary places via geocode().
COUNTY_CENTROIDS: dict[str, tuple[float, float, str]] = {
    "18157": (40.3888, -86.8942, "Tippecanoe County, IN"),
    "18097": (39.7817, -86.1478, "Marion County, IN"),
    "18059": (39.8236, -85.7735, "Hancock County, IN"),
    "17031": (41.8398, -87.8168, "Cook County, IL"),
}

HEAT_STRESS_TMAX_C = 32.0
GDD_BASE_C = 10.0


def geocode(name: str, timeout: int = 20) -> tuple[float, float] | None:
    """Resolve a place name to (latitude, longitude), or None."""
    import requests

    try:
        resp = requests.get(
            GEOCODE_URL,
            params={"name": name, "count": 1, "language": "en", "format": "json"},
            timeout=timeout,
        )
        resp.raise_for_status()
        results = resp.json().get("results") or []
    except Exception:
        return None
    if not results:
        return None
    return float(results[0]["latitude"]), float(results[0]["longitude"])


def fetch_history(
    latitude: float,
    longitude: float,
    county_fips: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    timeout: int = 60,
) -> pd.DataFrame:
    """Fetch daily historical weather. Returns rows for fact_weather_obs.

    Defaults to ten years ending five days ago (the archive lags a few
    days behind real time). Gracefully returns an empty DataFrame if the
    API is unavailable.
    """
    import requests

    end = end_date or (date.today() - timedelta(days=5))
    start = start_date or (end - timedelta(days=3653))

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": "auto",
    }
    try:
        resp = requests.get(ARCHIVE_URL, params=params, timeout=timeout)
        resp.raise_for_status()
        daily = resp.json().get("daily") or {}
    except Exception:
        return pd.DataFrame()

    dates = daily.get("time") or []
    if not dates:
        return pd.DataFrame()

    df = pd.DataFrame({
        "obs_date": pd.to_datetime(dates).date,
        "tmax_c": daily.get("temperature_2m_max"),
        "tmin_c": daily.get("temperature_2m_min"),
        "precip_mm": daily.get("precipitation_sum"),
    })
    df = df.dropna(subset=["tmax_c", "tmin_c"], how="all")
    df["tavg_c"] = (df["tmax_c"] + df["tmin_c"]) / 2.0
    df["heat_stress_flag"] = df["tmax_c"] > HEAT_STRESS_TMAX_C
    df["gdd_base10"] = (df["tavg_c"] - GDD_BASE_C).clip(lower=0.0)

    loc_key = county_fips or f"{latitude:.2f}_{longitude:.2f}"
    df["obs_id"] = [f"OM-{loc_key}-{d}" for d in df["obs_date"]]
    df["location_id"] = None
    df["county_fips"] = county_fips
    df["station_id"] = None
    df["source"] = "open_meteo"
    df["drought_monitor_cat"] = None
    df["enso_oni_index"] = None
    return df


def fetch_forecast(
    latitude: float,
    longitude: float,
    county_fips: str | None = None,
    forecast_days: int = 16,
    timeout: int = 30,
) -> pd.DataFrame:
    """Fetch the daily weather FORECAST (up to 16 days, keyless).

    Same row shape as fetch_history but source='open_meteo_forecast'.
    Purpose: live safe-commit windows extend into the future, and the
    decision path reads weather from the database only — forecast rows
    must be pre-loaded by ingestion, exactly like observations. Re-runs
    overwrite nothing (INSERT OR IGNORE keys on obs_id/date), and archive
    rows later supersede forecasts only by their later fetch being a
    distinct source row — keep obs_id distinct per source.
    """
    import requests

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "forecast_days": min(max(forecast_days, 1), 16),
        "timezone": "auto",
    }
    try:
        resp = requests.get(FORECAST_URL, params=params, timeout=timeout)
        resp.raise_for_status()
        daily = resp.json().get("daily") or {}
    except Exception:
        return pd.DataFrame()

    dates = daily.get("time") or []
    if not dates:
        return pd.DataFrame()

    df = pd.DataFrame({
        "obs_date": pd.to_datetime(dates).date,
        "tmax_c": daily.get("temperature_2m_max"),
        "tmin_c": daily.get("temperature_2m_min"),
        "precip_mm": daily.get("precipitation_sum"),
    })
    df = df.dropna(subset=["tmax_c", "tmin_c"], how="all")
    df["tavg_c"] = (df["tmax_c"] + df["tmin_c"]) / 2.0
    df["heat_stress_flag"] = df["tmax_c"] > HEAT_STRESS_TMAX_C
    df["gdd_base10"] = (df["tavg_c"] - GDD_BASE_C).clip(lower=0.0)

    loc_key = county_fips or f"{latitude:.2f}_{longitude:.2f}"
    df["obs_id"] = [f"OMF-{loc_key}-{d}" for d in df["obs_date"]]
    df["location_id"] = None
    df["county_fips"] = county_fips
    df["station_id"] = None
    df["source"] = "open_meteo_forecast"
    df["drought_monitor_cat"] = None
    df["enso_oni_index"] = None
    return df


def fetch_and_store_forecast(
    conn,
    county_fips: str = "18157",
    latitude: float | None = None,
    longitude: float | None = None,
    forecast_days: int = 16,
) -> int:
    """Fetch the 16-day forecast for a county and insert into
    fact_weather_obs (source='open_meteo_forecast')."""
    if latitude is None or longitude is None:
        centroid = COUNTY_CENTROIDS.get(county_fips)
        if centroid is None:
            return 0
        latitude, longitude = centroid[0], centroid[1]

    df = fetch_forecast(latitude, longitude, county_fips, forecast_days)
    if df.empty:
        return 0
    cols = (
        "obs_id, obs_date, location_id, county_fips, station_id, source, "
        "tmax_c, tmin_c, tavg_c, precip_mm, heat_stress_flag, "
        "drought_monitor_cat, enso_oni_index, gdd_base10"
    )
    conn.execute(
        f"INSERT OR IGNORE INTO fact_weather_obs ({cols}) SELECT {cols} FROM df"  # nosec B608 - cols from schema constant
    )
    return len(df)


def fetch_and_store(
    conn,
    county_fips: str = "18157",
    latitude: float | None = None,
    longitude: float | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> int:
    """Fetch history for a county (or explicit coordinates) and insert
    into fact_weather_obs. Returns rows inserted (0 on network failure).
    """
    if latitude is None or longitude is None:
        centroid = COUNTY_CENTROIDS.get(county_fips)
        if centroid is None:
            return 0
        latitude, longitude = centroid[0], centroid[1]

    df = fetch_history(latitude, longitude, county_fips, start_date, end_date)
    if df.empty:
        return 0
    # Enumerate columns explicitly: fact_weather_obs has a created_at
    # column (defaulted) that the frame does not — positional SELECT *
    # fails the binder. Same convention as the NOAA/USDA connectors.
    cols = (
        "obs_id, obs_date, location_id, county_fips, station_id, source, "
        "tmax_c, tmin_c, tavg_c, precip_mm, heat_stress_flag, "
        "drought_monitor_cat, enso_oni_index, gdd_base10"
    )
    conn.execute(
        f"INSERT OR IGNORE INTO fact_weather_obs ({cols}) SELECT {cols} FROM df"  # nosec B608 - cols from schema constant
    )
    return len(df)
