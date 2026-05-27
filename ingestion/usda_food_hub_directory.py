"""USDA Local Food Portal — food-hub directory fetcher.

Pulls active food-hub listings from the USDA's Local Food Portal API
(https://www.usdalocalfoodportal.com/api/foodhub/) and loads them into
``dim_prospect_hubs`` for sales / partnership outreach.

Authentication
--------------
The portal API requires an API key passed as a query parameter:

  https://www.usdalocalfoodportal.com/api/foodhub/?apikey=<KEY>&state=Indiana

Set the env var ``USDA_LOCALFOOD_API_KEY``. If unset, all functions return
empty DataFrames so dev / test runs don't crash.

Targets
-------
By default we pull Indiana plus the wider Midwest (IL, OH, MI, KY, WI, MN,
IA) — those are the states within Roy Ballard's network and the most
likely first-pilot candidates.
"""

from __future__ import annotations

import hashlib
import os
from typing import Iterable

import pandas as pd


PORTAL_BASE_URL = "https://www.usdalocalfoodportal.com/api/foodhub/"

DEFAULT_STATES: tuple[str, ...] = (
    "Indiana", "Illinois", "Ohio", "Michigan",
    "Kentucky", "Wisconsin", "Minnesota", "Iowa",
)


def _hub_id(name: str, city: str, state: str, listing_id: str | None) -> str:
    """Stable hub_id from name + location + listing id."""
    if listing_id:
        return f"HUB-{listing_id}"
    payload = f"{(name or '').strip().lower()}|{(city or '').strip().lower()}|{(state or '').strip().lower()}"
    return f"HUB-{hashlib.md5(payload.encode('utf-8')).hexdigest()[:10].upper()}"


def fetch_food_hubs(
    states: Iterable[str] = DEFAULT_STATES,
    api_key: str | None = None,
    timeout_s: int = 30,
) -> pd.DataFrame:
    """Pull food-hub listings for the given states.

    Returns columns matching ``dim_prospect_hubs``:
      hub_id, hub_name, listing_id, address, city, state, zip,
      products, website, email, phone, lat, lng, region, source

    Returns an empty DataFrame if the API key is missing or every state
    request fails.
    """
    import requests

    api_key = api_key or os.getenv("USDA_LOCALFOOD_API_KEY", "")
    if not api_key:
        return pd.DataFrame()

    rows: list[dict] = []
    for state in states:
        params = {"apikey": api_key, "state": state}
        try:
            resp = requests.get(PORTAL_BASE_URL, params=params, timeout=timeout_s)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            continue

        # The portal returns either a list of records or {"data": [...]}.
        records = data if isinstance(data, list) else data.get("data") or []
        for r in records:
            name = (r.get("listing_name") or r.get("name") or "").strip()
            if not name:
                continue
            city = (r.get("location_x") or r.get("city") or "").strip()
            st = (r.get("location_state") or r.get("state") or state).strip()

            try:
                lat = float(r["location_y"]) if r.get("location_y") not in (None, "") else None
                lng = float(r["location_x"]) if r.get("location_x") not in (None, "") else None
            except (TypeError, ValueError):
                lat = lng = None

            rows.append({
                "hub_id": _hub_id(name, city, st, r.get("listing_id")),
                "hub_name": name,
                "listing_id": str(r.get("listing_id") or ""),
                "address": r.get("location_address"),
                "city": city,
                "state": st,
                "zip": r.get("location_zipcode"),
                "products": r.get("products") or r.get("listing_desc"),
                "website": r.get("media_website"),
                "email": r.get("contact_email"),
                "phone": r.get("contact_phone"),
                "lat": lat,
                "lng": lng,
                "region": "IN" if st.lower() == "indiana" else "Midwest",
                "source": "usda_localfoodportal",
            })

    return pd.DataFrame(rows)


def fetch_and_store(
    conn,
    states: Iterable[str] = DEFAULT_STATES,
) -> int:
    """Fetch food hubs and insert into dim_prospect_hubs (idempotent on hub_id)."""
    df = fetch_food_hubs(states=states)
    if df.empty:
        return 0
    conn.register("hm_hubs_df", df)
    try:
        before = conn.execute("SELECT COUNT(*) FROM dim_prospect_hubs").fetchone()[0]
        conn.execute(
            "INSERT INTO dim_prospect_hubs "
            "(hub_id, hub_name, listing_id, address, city, state, zip, "
            "products, website, email, phone, lat, lng, region, source) "
            "SELECT hub_id, hub_name, listing_id, address, city, state, zip, "
            "products, website, email, phone, lat, lng, region, source "
            "FROM hm_hubs_df ON CONFLICT DO NOTHING"
        )
        after = conn.execute("SELECT COUNT(*) FROM dim_prospect_hubs").fetchone()[0]
        return after - before
    finally:
        conn.unregister("hm_hubs_df")
