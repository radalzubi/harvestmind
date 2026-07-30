"""USDA NASS QuickStats fetcher — county yields and crop condition.

Two signals from the same free API (key: NASS_QUICKSTATS_KEY, request
at quickstats.nass.usda.gov/api):

county yields
    Annual county-level realized yield per commodity. The ground truth
    for calibrating weather-to-yield response: joined against county
    weather it answers "how much did yield actually move in hot / dry
    years here?" — independent of any single operator's records.

crop condition
    Weekly state-level share of a crop rated in each condition class
    (EXCELLENT/GOOD/FAIR/POOR/VERY POOR). The in-season leading
    indicator: condition deteriorates weeks before harvest shortfalls
    reach a distributor's dock.

Yields are stored in fact_county_yields (migration 012). Condition is
returned as a frame for analysis; it becomes worth persisting once a
pilot operator's commodity mix is known.

Without a key all functions return empty frames — same graceful
posture as the other connectors.
"""

from __future__ import annotations

import os

import pandas as pd

QUICKSTATS_URL = "https://quickstats.nass.usda.gov/api/api_GET/"


def _get(params: dict, timeout: int = 60) -> list[dict]:
    import requests

    key = os.getenv("NASS_QUICKSTATS_KEY", "")
    if not key:
        return []
    try:
        resp = requests.get(
            QUICKSTATS_URL, params={"key": key, "format": "JSON", **params},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json().get("data", [])
    except Exception:
        return []


def fetch_county_yields(
    commodity: str = "TOMATOES",
    state_alpha: str = "IN",
    year_ge: int = 2010,
) -> pd.DataFrame:
    """Annual county-level yields for a commodity.

    Returns DataFrame [year, state_alpha, county_name, county_fips,
    commodity, yield_value, yield_unit].
    """
    records = _get({
        "commodity_desc": commodity,
        "statisticcat_desc": "YIELD",
        "agg_level_desc": "COUNTY",
        "state_alpha": state_alpha,
        "year__GE": str(year_ge),
    })
    rows = []
    for r in records:
        try:
            value = float(str(r.get("Value", "")).replace(",", ""))
        except ValueError:
            continue  # suppressed cells: "(D)", "(Z)"
        state_fips = str(r.get("state_fips_code", "")).zfill(2)
        county_code = str(r.get("county_code", "")).zfill(3)
        rows.append({
            "year": int(r["year"]),
            "state_alpha": r.get("state_alpha"),
            "county_name": r.get("county_name"),
            "county_fips": state_fips + county_code,
            "commodity": r.get("commodity_desc"),
            "yield_value": value,
            "yield_unit": r.get("unit_desc"),
        })
    return pd.DataFrame(rows)


def fetch_crop_condition(
    commodity: str = "TOMATOES",
    state_alpha: str = "IN",
    year_ge: int = 2020,
) -> pd.DataFrame:
    """Weekly state-level crop condition shares.

    Returns DataFrame [year, week_ending, state_alpha, commodity,
    condition_class, pct]."""
    records = _get({
        "commodity_desc": commodity,
        "statisticcat_desc": "CONDITION",
        "agg_level_desc": "STATE",
        "state_alpha": state_alpha,
        "year__GE": str(year_ge),
    })
    rows = []
    for r in records:
        try:
            pct = float(str(r.get("Value", "")).replace(",", ""))
        except ValueError:
            continue
        rows.append({
            "year": int(r["year"]),
            "week_ending": r.get("week_ending"),
            "state_alpha": r.get("state_alpha"),
            "commodity": r.get("commodity_desc"),
            "condition_class": r.get("unit_desc"),  # e.g. 'PCT EXCELLENT'
            "pct": pct,
        })
    return pd.DataFrame(rows)


def fetch_and_store(
    conn,
    commodities: tuple[str, ...] = ("TOMATOES", "SWEET CORN", "CUCUMBERS"),
    state_alpha: str = "IN",
    year_ge: int = 2010,
) -> int:
    """Fetch county yields for a commodity basket into fact_county_yields."""
    total = 0
    for commodity in commodities:
        df = fetch_county_yields(commodity, state_alpha, year_ge)
        if df.empty:
            continue
        df = df.copy()
        df["yield_obs_id"] = (
            df["county_fips"] + "-" + df["commodity"].str.replace(" ", "_")
            + "-" + df["year"].astype(str)
        )
        df["source"] = "nass_quickstats"
        cols = (
            "yield_obs_id, year, state_alpha, county_name, county_fips, "
            "commodity, yield_value, yield_unit, source"
        )
        conn.execute(
            f"INSERT OR IGNORE INTO fact_county_yields ({cols}) "
            f"SELECT {cols} FROM df"
        )
        total += len(df)
    return total
