"""USDA AMS (Agricultural Marketing Service) market price fetcher.

Fetches terminal market prices from the USDA AMS API.
Docs: https://mymarketnews.ams.usda.gov/mars/public
"""

from __future__ import annotations

import os
from datetime import date

import pandas as pd


AMS_BASE_URL = "https://marsapi.ams.usda.gov/services/v1.2/reports"

# Commodity code → product_id mapping (extend as needed)
COMMODITY_MAP: dict[str, str] = {
    "Lettuce, Romaine": "PRD-001",
    "Spinach": "PRD-002",
    "Tomatoes, Cherry": "PRD-003",
    "Peppers, Bell": "PRD-004",
    "Cucumbers": "PRD-005",
    "Squash, Zucchini": "PRD-006",
    "Kale": "PRD-007",
    "Corn, Sweet": "PRD-008",
    "Strawberries": "PRD-009",
    "Onions, Yellow": "PRD-010",
}


def fetch_ams_prices(
    report_id: str = "2627",  # Chicago terminal market
    start_date: date | None = None,
    end_date: date | None = None,
    api_key: str | None = None,
) -> pd.DataFrame:
    """Fetch USDA AMS prices. Returns DataFrame matching fact_market_prices schema.

    Falls back to an empty DataFrame if the API call fails (demo-safe).
    """
    import requests

    api_key = api_key or os.getenv("USDA_AMS_API_KEY", "")
    if not api_key:
        return pd.DataFrame()

    params: dict = {"q": "commodity_name:Lettuce OR Tomatoes OR Peppers"}
    if start_date:
        params["start_date"] = start_date.isoformat()
    if end_date:
        params["end_date"] = end_date.isoformat()

    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Basic {api_key}"

    try:
        resp = requests.get(
            f"{AMS_BASE_URL}/{report_id}/marketdata",
            params=params,
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return pd.DataFrame()

    rows = []
    for item in data.get("results", []):
        commodity = item.get("commodity_name", "")
        prod_id = None
        for key, pid in COMMODITY_MAP.items():
            if key.lower() in commodity.lower():
                prod_id = pid
                break

        try:
            low = float(item.get("low_price", 0)) / 45.36  # lbs→kg conversion
            high = float(item.get("high_price", 0)) / 45.36
            avg = (low + high) / 2.0
        except (TypeError, ValueError):
            continue

        rows.append({
            "price_id": f"AMS-{report_id}-{item.get('record_id','')}",
            "source": "usda_ams",
            "report_date": item.get("report_date"),
            "market_name": item.get("market_location_name"),
            "product_id": prod_id,
            "commodity_code": item.get("commodity_code"),
            "grade": item.get("grade"),
            "unit": "kg",
            "low_price": round(low, 4),
            "high_price": round(high, 4),
            "avg_price": round(avg, 4),
            "volume_units": item.get("mostly_low"),
            "currency": "USD",
        })

    return pd.DataFrame(rows)


def fetch_and_store(conn, report_id: str = "2627", days_back: int = 30) -> int:
    """Fetch recent prices and insert into fact_market_prices."""
    from datetime import timedelta
    end = date.today()
    start = end - timedelta(days=days_back)
    df = fetch_ams_prices(report_id=report_id, start_date=start, end_date=end)
    if df.empty:
        return 0
    conn.execute("INSERT OR IGNORE INTO fact_market_prices SELECT * FROM df")
    return len(df)
