"""ENSO Oceanic Niño Index (ONI) loader.

Fetches NOAA CPC's official ONI table (free, no key) — one anomaly
value per rolling three-month season since 1950. El Niño / La Niña
phases shift North American growing-season weather, which makes ONI
the one teleconnection cheap enough to always carry: a single small
text file covering the entire historical record.

Source: https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt

Each season (DJF, JFM, ...) is centered on its middle month; the value
is stamped onto fact_weather_obs.enso_oni_index by observation month.
The demand forecaster already expects this column as an optional
feature (forecasting/demand/feature_engineering.OPTIONAL_FEATURE_COLS).
"""

from __future__ import annotations

import pandas as pd

ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"

# Season label -> center month number.
_SEASON_CENTER = {
    "DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
    "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12,
}


def fetch_oni(timeout: int = 30) -> pd.DataFrame:
    """Fetch the ONI table. Returns DataFrame [year, month, oni_index].

    Gracefully returns an empty DataFrame if the API is unavailable.
    """
    import requests

    try:
        resp = requests.get(ONI_URL, timeout=timeout)
        resp.raise_for_status()
        text = resp.text
    except Exception:
        return pd.DataFrame()

    rows = []
    for line in text.splitlines()[1:]:  # skip header
        parts = line.split()
        if len(parts) != 4:
            continue
        season, year_s, _total, anom = parts
        month = _SEASON_CENTER.get(season)
        if month is None:
            continue
        try:
            rows.append({
                "year": int(year_s),
                "month": month,
                "oni_index": float(anom),
            })
        except ValueError:
            continue
    return pd.DataFrame(rows)


def apply_to_weather(conn, oni_df: pd.DataFrame | None = None) -> int:
    """Stamp monthly ONI values onto every fact_weather_obs row in the
    matching year-month. Returns the number of monthly values applied."""
    df = fetch_oni() if oni_df is None else oni_df
    if df is None or df.empty:
        return 0
    applied = 0
    for row in df.itertuples(index=False):
        conn.execute(
            """
            UPDATE fact_weather_obs
            SET enso_oni_index = ?
            WHERE EXTRACT(year FROM obs_date) = ?
              AND EXTRACT(month FROM obs_date) = ?
            """,
            [row.oni_index, row.year, row.month],
        )
        applied += 1
    return applied
