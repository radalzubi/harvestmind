"""USDA AMS — terminal-market price fetcher (MARS API).

Pulls fruit/vegetable terminal-market wholesale prices from the USDA AMS
MARS API at ``marsapi.ams.usda.gov``. The connector resolves the actual
price-row endpoint shape:

  GET /services/v1.2/reports/{slug_id}/Report%20Details

This returns one row per (commodity × variety × package × origin) per
report date, with raw fields ``low_price`` / ``high_price`` / ``package``.
Prices are *per package*, not per pound — the connector parses the
package string to derive a canonical $/kg.

Authentication
--------------
HTTP Basic auth with the API key as username, blank password. Set
``USDA_AMS_API_KEY``. If unset, all functions return empty DataFrames.

Targets
-------
The default scope matches Indiana's likely procurement footprint —
the closest two active fruit/veg terminal markets to Indianapolis:

  Chicago veg   slug_id=2291  HX_FV020
  Chicago fruit slug_id=2290  HX_FV010
  Detroit veg   slug_id=2303  DU_FV020
  Detroit fruit slug_id=2302  DU_FV010

(Note: there is no Indianapolis terminal market in the MARS catalog —
the legacy "IN_MN035" reference doesn't resolve to an active report.
Detroit is the closest active produce terminal.)

Commodities are filtered to the FTL basket: cucumbers, leafy greens,
tomatoes, peppers, cantaloupe.
"""

from __future__ import annotations

import os
import re
import urllib.parse
from typing import Iterable

import pandas as pd


MARS_BASE_URL = "https://marsapi.ams.usda.gov/services/v1.2/reports"

# Slug-id ↔ market metadata. The MARS API uses numeric slug_id in URLs;
# the slug_name is the human-readable code.
TARGET_MARKETS: dict[str, dict[str, str]] = {
    "HX_FV020": {"slug_id": "2291", "market_name": "Chicago Terminal Market — Vegetables", "region": "IL", "section": "vegetables"},
    "HX_FV010": {"slug_id": "2290", "market_name": "Chicago Terminal Market — Fruits",     "region": "IL", "section": "fruits"},
    "DU_FV020": {"slug_id": "2303", "market_name": "Detroit Terminal Market — Vegetables", "region": "MI", "section": "vegetables"},
    "DU_FV010": {"slug_id": "2302", "market_name": "Detroit Terminal Market — Fruits",     "region": "MI", "section": "fruits"},
}

# Free-text USDA commodity → schema product_id (FTL basket).
COMMODITY_TO_PRODUCT: dict[str, str] = {
    "cucumbers":            "PRD-005",
    "lettuce, romaine":     "PRD-001",
    "lettuce, iceberg":     "PRD-001",
    "lettuce":              "PRD-001",
    "leafy greens":         "PRD-001",
    "spinach":              "PRD-002",
    "kale":                 "PRD-007",
    "tomatoes":             "PRD-003",
    "tomatoes, cherry":     "PRD-003",
    "peppers, bell":        "PRD-004",
    "peppers":              "PRD-004",
    "cantaloupe":           "PRD-008",
    "cantaloups":           "PRD-008",   # USDA uses both spellings
    "melons, cantaloupe":   "PRD-008",
}

TARGET_COMMODITIES: tuple[str, ...] = (
    "cucumbers", "leafy greens", "tomatoes", "peppers", "cantaloupe", "lettuce",
)

LBS_PER_KG = 2.20462

# ── Package-size parsing ─────────────────────────────────────────────────────
# USDA package strings vary widely. Examples seen in real data:
#   "15 lb flats", "25 lb cartons", "1 1/9 bushel cartons",
#   "40 lb cartons 24s", "50 lb sacks", "12-1 lb pack"
#
# We extract the bulk weight in pounds. If a string has multiple numbers
# we take the leading "X lb" match. If it's bushels we use a typical
# bushel weight per commodity (rough but better than dropping the row).

_BUSHEL_LB = 50.0  # generic bushel weight; varies but works as a fallback

_LB_PATTERNS = (
    re.compile(r"(\d+(?:\.\d+)?)\s*lb\b", re.IGNORECASE),
    re.compile(r"(\d+(?:\.\d+)?)\s*lbs\b", re.IGNORECASE),
    re.compile(r"(\d+(?:\.\d+)?)\s*pound", re.IGNORECASE),
)


def _parse_package_lbs(package: str | None) -> float | None:
    """Extract package weight in pounds from the USDA package string.

    Returns None if no weight can be parsed.
    """
    if not package:
        return None
    s = package.strip().lower()

    for pat in _LB_PATTERNS:
        m = pat.search(s)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass

    if "bushel" in s:
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:[/-]\s*\d+\s*)?bushel", s)
        if m:
            try:
                return float(m.group(1)) * _BUSHEL_LB
            except ValueError:
                pass
        return _BUSHEL_LB
    return None


def _to_iso_date(s: str | None) -> str | None:
    """USDA returns 'MM/DD/YYYY'; DuckDB DATE columns want ISO 'YYYY-MM-DD'."""
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    # Already ISO?
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        return s[:10]
    # MM/DD/YYYY
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        mo, d, y = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    return None


def _resolve_product_id(commodity: str) -> str | None:
    if not commodity:
        return None
    lc = commodity.strip().lower()
    if lc in COMMODITY_TO_PRODUCT:
        return COMMODITY_TO_PRODUCT[lc]
    for key, pid in COMMODITY_TO_PRODUCT.items():
        if key in lc:
            return pid
    return None


def _commodity_in_basket(commodity: str, basket: Iterable[str]) -> bool:
    if not commodity:
        return False
    lc = commodity.lower()
    return any(b.lower() in lc for b in basket)


def fetch_mars_report_details(
    slug_id: str,
    last_days: int | None = None,
    api_key: str | None = None,
    timeout_s: int = 30,
) -> list[dict]:
    """Pull raw 'Report Details' rows from MARS for a single slug.

    Returns a list of dict rows from the API, or [] if the call fails
    or the key is unset.
    """
    import requests

    api_key = api_key or os.getenv("USDA_AMS_API_KEY", "")
    if not api_key:
        return []

    url = f"{MARS_BASE_URL}/{slug_id}/{urllib.parse.quote('Report Details')}"
    params: dict = {}
    if last_days is not None:
        params["lastDays"] = last_days

    try:
        resp = requests.get(url, params=params, auth=(api_key, ""), timeout=timeout_s)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []
    return data.get("results", []) if isinstance(data, dict) else []


def fetch_mymarketnews_prices(
    market_slug: str = "HX_FV020",
    commodities: Iterable[str] | None = None,
    last_days: int = 365,
    api_key: str | None = None,
    timeout_s: int = 30,
) -> pd.DataFrame:
    """Pull a slice of MARS terminal-market prices as a DataFrame.

    Returns columns matching ``fact_usda_prices``. ``last_days`` controls
    history depth — pass ``last_days=1825`` for ~5 years.
    """
    market = TARGET_MARKETS.get(market_slug)
    if market is None:
        return pd.DataFrame()

    raw_rows = fetch_mars_report_details(
        slug_id=market["slug_id"],
        last_days=last_days,
        api_key=api_key,
        timeout_s=timeout_s,
    )
    if not raw_rows:
        return pd.DataFrame()

    cmds = list(commodities) if commodities is not None else list(TARGET_COMMODITIES)

    rows: list[dict] = []
    for item in raw_rows:
        commodity = (item.get("commodity") or "").strip()
        if not _commodity_in_basket(commodity, cmds):
            continue

        try:
            low = float(item.get("low_price") or 0.0)
            high = float(item.get("high_price") or 0.0)
        except (TypeError, ValueError):
            continue
        if low <= 0 and high <= 0:
            continue
        avg = (low + high) / 2.0 if (low > 0 and high > 0) else max(low, high)

        package = item.get("package") or ""
        pkg_lbs = _parse_package_lbs(package)
        # Convert $/package → $/kg. If we can't parse weight, skip — emitting
        # a row with NULL price_per_kg would pollute the live-price average.
        if not pkg_lbs or pkg_lbs <= 0:
            continue
        price_per_kg = round(avg / pkg_lbs * LBS_PER_KG, 4)

        # Skip absurd values (parser failure) — anything > $200/kg is wrong.
        if price_per_kg <= 0 or price_per_kg > 200:
            continue

        rd = _to_iso_date(item.get("report_date") or item.get("report_begin_date"))
        if not rd:
            continue

        rows.append({
            "price_id": (
                f"AMS-{market_slug}-{rd}-"
                f"{commodity[:24].replace(' ', '_')}-{package[:16].replace(' ', '_')}"
            ),
            "report_date": rd,
            "market_id": market_slug,
            "market_name": market["market_name"],
            "commodity": commodity,
            "commodity_code": item.get("group"),
            "product_id": _resolve_product_id(commodity),
            "grade": item.get("grade"),
            "package": package,
            "unit": "kg",
            "low_price": round(low, 4),
            "high_price": round(high, 4),
            "avg_price": round(avg, 4),
            "price_per_kg": price_per_kg,
            "currency": "USD",
            "source": "usda_mars",
        })

    return pd.DataFrame(rows)


def fetch_and_store(
    conn,
    markets: Iterable[str] = ("HX_FV020", "HX_FV010", "DU_FV020", "DU_FV010"),
    commodities: Iterable[str] | None = None,
    weeks_back: int = 52,
) -> int:
    """Fetch prices for each market and insert into fact_usda_prices.

    Idempotent — primary-key conflicts skip duplicate rows. Returns the
    total number of newly inserted rows across all markets.
    """
    last_days = max(1, int(weeks_back) * 7)

    inserted = 0
    for slug in markets:
        df = fetch_mymarketnews_prices(
            market_slug=slug,
            commodities=commodities,
            last_days=last_days,
        )
        if df.empty:
            continue

        # Dedupe within this batch (MARS sometimes returns duplicate rows).
        df = df.drop_duplicates(subset=["price_id"])

        conn.register("hm_usda_df", df)
        try:
            before = conn.execute("SELECT COUNT(*) FROM fact_usda_prices").fetchone()[0]
            conn.execute(
                "INSERT INTO fact_usda_prices "
                "(price_id, report_date, market_id, market_name, commodity, "
                "commodity_code, product_id, grade, package, unit, low_price, "
                "high_price, avg_price, price_per_kg, currency, source) "
                "SELECT price_id, report_date, market_id, market_name, commodity, "
                "commodity_code, product_id, grade, package, unit, low_price, "
                "high_price, avg_price, price_per_kg, currency, source "
                "FROM hm_usda_df ON CONFLICT DO NOTHING"
            )
            after = conn.execute("SELECT COUNT(*) FROM fact_usda_prices").fetchone()[0]
            inserted += after - before
        finally:
            conn.unregister("hm_usda_df")
    return inserted
