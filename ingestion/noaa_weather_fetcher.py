"""NOAA Climate Data Online (CDO) weather fetcher.

Fetches GHCND daily weather observations for Indiana counties.
Token: NOAA_CDO_TOKEN env var (free, request at ncdc.noaa.gov).
"""

from __future__ import annotations

import os
from datetime import date, timedelta

import pandas as pd


CDO_BASE = "https://www.ncdc.noaa.gov/cdo-web/api/v2"
INDIANA_STATIONS = {
    "18057": "GHCND:USW00093819",  # Indianapolis (Hancock County)
    "18097": "GHCND:USW00014848",  # Tippecanoe (West Lafayette/Purdue)
}


def fetch_weather(
    station_id: str = "GHCND:USW00093819",
    county_fips: str = "18057",
    start_date: date | None = None,
    end_date: date | None = None,
    token: str | None = None,
) -> pd.DataFrame:
    """Fetch NOAA daily weather. Returns DataFrame for fact_weather_obs.

    Gracefully returns empty DataFrame if API unavailable.
    """
    import requests

    token = token or os.getenv("NOAA_CDO_TOKEN", "")
    if not token:
        return pd.DataFrame()

    end = end_date or date.today()
    start = start_date or (end - timedelta(days=90))

    headers = {"token": token}
    params = {
        "stationid": station_id,
        "datatypeid": "TMAX,TMIN,PRCP",
        "startdate": start.isoformat(),
        "enddate": end.isoformat(),
        "units": "metric",
        "limit": 1000,
        "offset": 1,
    }

    try:
        resp = requests.get(f"{CDO_BASE}/data", headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        records = resp.json().get("results", [])
    except Exception:
        return pd.DataFrame()

    # Pivot wide: date → {TMAX, TMIN, PRCP}
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"]).dt.date
    pivot = df.pivot_table(index="date", columns="datatype", values="value", aggfunc="first")
    pivot.columns.name = None

    rows = []
    for obs_date, row in pivot.iterrows():
        tmax = row.get("TMAX")
        tmin = row.get("TMIN")
        prcp = row.get("PRCP", 0.0)
        tavg = (tmax + tmin) / 2.0 if tmax is not None and tmin is not None else None
        rows.append({
            "obs_id": f"NOAA-{station_id}-{obs_date}",
            "obs_date": obs_date,
            "location_id": None,
            "county_fips": county_fips,
            "station_id": station_id,
            "source": "noaa_cdo",
            "tmax_c": tmax,
            "tmin_c": tmin,
            "tavg_c": tavg,
            "precip_mm": prcp,
            "heat_stress_flag": tmax is not None and tmax > 32.0,
            "drought_monitor_cat": None,
            "enso_oni_index": None,
            "gdd_base10": max(0.0, tavg - 10.0) if tavg is not None else None,
        })

    return pd.DataFrame(rows)


def fetch_and_store(conn, days_back: int = 30) -> int:
    """Fetch recent weather and insert into fact_weather_obs."""
    df = fetch_weather(
        station_id=INDIANA_STATIONS["18057"],
        county_fips="18057",
        start_date=date.today() - timedelta(days=days_back),
    )
    if df.empty:
        return 0
    # Enumerate columns explicitly: fact_weather_obs has a 15th column
    # (created_at, defaulted) that the parsed frame does not, so a positional
    # ``SELECT *`` fails the binder and persists nothing. (The USDA connectors
    # already enumerate for the same reason.)
    cols = (
        "obs_id, obs_date, location_id, county_fips, station_id, source, "
        "tmax_c, tmin_c, tavg_c, precip_mm, heat_stress_flag, "
        "drought_monitor_cat, enso_oni_index, gdd_base10"
    )
    conn.execute(
        f"INSERT OR IGNORE INTO fact_weather_obs ({cols}) SELECT {cols} FROM df"
    )
    return len(df)
