"""US Drought Monitor (USDM) county drought-category fetcher.

Pulls weekly county-level drought severity from the USDM data service
at usdmdataservices.unl.edu (free, no key). Each weekly row reports the
percent of the county's area in each class (None, D0..D4).

We reduce that to one category per week: the WORST class covering at
least half the county, i.e. the area-weighted median class. This is
conservative in both directions — a sliver of D2 in a wet county does
not flag the week, and a county mostly in drought is not diluted by a
wet corner.

Categories are written onto fact_weather_obs.drought_monitor_cat for
the matching county and dates, so drought rides alongside temperature
and precipitation as a Tier-2 yield covariate (risk/yield_covariates
decides per-operator whether it earns admission).
"""

from __future__ import annotations

from datetime import date
from io import StringIO

import pandas as pd

USDM_URL = (
    "https://usdmdataservices.unl.edu/api/CountyStatistics/"
    "GetDroughtSeverityStatisticsByAreaPercent"
)

_CLASSES = ["D4", "D3", "D2", "D1", "D0"]  # worst first


def _weekly_category(row: pd.Series) -> str | None:
    """Worst drought class covering >= 50% of the county (cumulative
    from the worst class down), or None if the county is majority
    drought-free."""
    cumulative = 0.0
    for cls in _CLASSES:
        cumulative += float(row.get(cls, 0.0) or 0.0)
        if cumulative >= 50.0:
            return cls
    return None


def fetch_drought(
    county_fips: str,
    start_date: date,
    end_date: date | None = None,
    timeout: int = 30,
) -> pd.DataFrame:
    """Fetch weekly drought categories for a county.

    Returns DataFrame [valid_start, valid_end, drought_monitor_cat].
    Gracefully returns an empty DataFrame if the API is unavailable.
    """
    import requests

    end = end_date or date.today()
    params = {
        "aoi": county_fips,
        "startdate": f"{start_date.month}/{start_date.day}/{start_date.year}",
        "enddate": f"{end.month}/{end.day}/{end.year}",
        "statisticsType": "1",
    }
    try:
        resp = requests.get(USDM_URL, params=params, timeout=timeout)
        resp.raise_for_status()
        df = pd.read_csv(StringIO(resp.text))
    except Exception:
        return pd.DataFrame()
    if df.empty or "ValidStart" not in df.columns:
        return pd.DataFrame()

    out = pd.DataFrame({
        "valid_start": pd.to_datetime(df["ValidStart"]).dt.date,
        "valid_end": pd.to_datetime(df["ValidEnd"]).dt.date,
        "drought_monitor_cat": df.apply(_weekly_category, axis=1),
    })
    return out.sort_values("valid_start").reset_index(drop=True)


def apply_to_weather(conn, county_fips: str, drought_df: pd.DataFrame) -> int:
    """Stamp weekly drought categories onto fact_weather_obs rows for
    the county. Returns the number of weekly rows applied."""
    if drought_df.empty:
        return 0
    applied = 0
    for row in drought_df.itertuples(index=False):
        if row.drought_monitor_cat is None:
            continue
        conn.execute(
            """
            UPDATE fact_weather_obs
            SET drought_monitor_cat = ?
            WHERE county_fips = ? AND obs_date BETWEEN ? AND ?
            """,
            [row.drought_monitor_cat, county_fips, row.valid_start, row.valid_end],
        )
        applied += 1
    return applied


def fetch_and_store(
    conn,
    county_fips: str,
    start_date: date,
    end_date: date | None = None,
) -> int:
    """Fetch drought history and stamp it onto existing weather rows."""
    df = fetch_drought(county_fips, start_date, end_date)
    return apply_to_weather(conn, county_fips, df)
