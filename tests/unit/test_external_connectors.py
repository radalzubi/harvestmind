"""Unit tests for the external HTTP connectors.

Targets:
  * ingestion/noaa_weather_fetcher.py  (NWS/NOAA CDO fetch + pivot/parse)
  * ingestion/usda_ams_connector.py    (MARS report-detail parse → $/kg)
  * ingestion/usda_food_hub_directory.py (Local Food Portal parse)

CRITICAL: every connector calls `requests.get` inside the function body
(`import requests` is local). Tests monkeypatch `requests.get` with a fake
that returns canned JSON — NO real network is ever touched. We assert the
PARSING logic: row shape, field extraction, unit conversion, and resilience
to empty / malformed / missing-key responses, plus the graceful-degradation
path when the API key env var is unset.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pandas as pd
import pytest

import ingestion.noaa_weather_fetcher as noaa
import ingestion.usda_ams_connector as ams
import ingestion.usda_food_hub_directory as hubs


# ── Fake HTTP plumbing ───────────────────────────────────────────────────────

class _FakeResp:
    """Minimal stand-in for requests.Response."""

    def __init__(self, payload, *, status_ok=True, raise_on_json=False):
        self._payload = payload
        self._status_ok = status_ok
        self._raise_on_json = raise_on_json

    def raise_for_status(self):
        if not self._status_ok:
            raise RuntimeError("HTTP 500")

    def json(self):
        if self._raise_on_json:
            raise ValueError("not json")
        return self._payload


def _patch_requests_get(monkeypatch, module, response):
    """Patch the `requests` module that `module` imports locally.

    Each connector does `import requests` inside the function, so the real
    `requests` module object is shared. We patch `requests.get` globally for
    the duration of the test, capturing the call args for assertions.
    """
    import requests

    calls = []

    def fake_get(url, **kwargs):
        calls.append({"url": url, **kwargs})
        if isinstance(response, Exception):
            raise response
        if callable(response):
            return response(url, **kwargs)
        return response

    monkeypatch.setattr(requests, "get", fake_get)
    return calls


# ── Schema bootstrap ─────────────────────────────────────────────────────────

def _bootstrap(c) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    for sql in sorted((repo_root / "db" / "migrations").glob("*.sql")):
        c.execute(sql.read_text())


def _seed_product(c, product_id: str) -> None:
    """fact_usda_prices.product_id has a FK to dim_products — seed the row."""
    c.execute(
        "INSERT OR IGNORE INTO dim_products "
        "(product_id, crop_name, crop_category, shelf_life_days) "
        "VALUES (?, ?, ?, ?)",
        [product_id, "Tomatoes", "tomato", 7],
    )


@pytest.fixture
def conn():
    c = duckdb.connect(":memory:")
    _bootstrap(c)
    yield c
    c.close()


# =====================================================================
# NOAA weather fetcher
# =====================================================================

def test_noaa_no_token_returns_empty(monkeypatch):
    """Graceful degradation: missing token → empty df, no HTTP attempted."""
    monkeypatch.delenv("NOAA_CDO_TOKEN", raising=False)
    # If requests.get were called it would explode (network); assert it isn't.
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: pytest.fail("no HTTP expected"))
    df = noaa.fetch_weather(token=None)
    assert df.empty


def test_noaa_parses_pivoted_observations(monkeypatch):
    """TMAX/TMIN/PRCP records pivot to one row per date with derived fields."""
    payload = {
        "results": [
            {"date": "2026-01-10T00:00:00", "datatype": "TMAX", "value": 30.0},
            {"date": "2026-01-10T00:00:00", "datatype": "TMIN", "value": 10.0},
            {"date": "2026-01-10T00:00:00", "datatype": "PRCP", "value": 4.0},
            {"date": "2026-01-11T00:00:00", "datatype": "TMAX", "value": 36.0},
            {"date": "2026-01-11T00:00:00", "datatype": "TMIN", "value": 20.0},
        ],
    }
    _patch_requests_get(monkeypatch, noaa, _FakeResp(payload))

    df = noaa.fetch_weather(
        station_id="GHCND:TEST", county_fips="18057", token="fake-token",
    )

    assert len(df) == 2
    row = df.set_index("obs_date").loc[date(2026, 1, 10)]
    assert row["tmax_c"] == 30.0
    assert row["tmin_c"] == 10.0
    assert row["tavg_c"] == 20.0          # (30 + 10) / 2
    assert row["precip_mm"] == 4.0
    assert row["gdd_base10"] == 10.0      # max(0, 20 - 10)
    assert row["heat_stress_flag"] is False or row["heat_stress_flag"] == False  # 30 !> 32
    assert row["county_fips"] == "18057"
    assert row["source"] == "noaa_cdo"
    assert row["station_id"] == "GHCND:TEST"

    # Heat-stress day: tmax 36 > 32 → flag True.
    hot = df.set_index("obs_date").loc[date(2026, 1, 11)]
    assert bool(hot["heat_stress_flag"]) is True


def test_noaa_passes_token_header(monkeypatch):
    """The CDO token is sent in the `token` header, not the query string."""
    calls = _patch_requests_get(monkeypatch, noaa, _FakeResp({"results": []}))
    noaa.fetch_weather(token="secret-tok")
    assert calls, "requests.get was not called"
    assert calls[0]["headers"]["token"] == "secret-tok"


def test_noaa_empty_results_returns_empty(monkeypatch):
    _patch_requests_get(monkeypatch, noaa, _FakeResp({"results": []}))
    df = noaa.fetch_weather(token="tok")
    assert df.empty


def test_noaa_http_error_returns_empty(monkeypatch):
    """A non-2xx response is swallowed → empty df (no crash)."""
    _patch_requests_get(monkeypatch, noaa, _FakeResp({}, status_ok=False))
    df = noaa.fetch_weather(token="tok")
    assert df.empty


def test_noaa_missing_results_key_returns_empty(monkeypatch):
    """Malformed payload without `results` is tolerated."""
    _patch_requests_get(monkeypatch, noaa, _FakeResp({"unexpected": 1}))
    df = noaa.fetch_weather(token="tok")
    assert df.empty


def test_noaa_uses_env_token_when_arg_none(monkeypatch):
    monkeypatch.setenv("NOAA_CDO_TOKEN", "env-token")
    calls = _patch_requests_get(monkeypatch, noaa, _FakeResp({"results": []}))
    noaa.fetch_weather(token=None)
    assert calls[0]["headers"]["token"] == "env-token"


def test_noaa_fetch_and_store_inserts_rows(conn, monkeypatch):
    """FIXED: fetch_and_store enumerates the 14 columns explicitly, so parsed
    rows persist into fact_weather_obs (created_at defaults)."""
    payload = {
        "results": [
            {"date": "2026-01-10T00:00:00", "datatype": "TMAX", "value": 25.0},
            {"date": "2026-01-10T00:00:00", "datatype": "TMIN", "value": 5.0},
            {"date": "2026-01-10T00:00:00", "datatype": "PRCP", "value": 1.0},
        ],
    }
    _patch_requests_get(monkeypatch, noaa, _FakeResp(payload))
    monkeypatch.setenv("NOAA_CDO_TOKEN", "tok")

    n = noaa.fetch_and_store(conn, days_back=30)
    assert n == 1
    assert conn.execute("SELECT COUNT(*) FROM fact_weather_obs").fetchone()[0] == 1


def test_noaa_fetch_and_store_empty_returns_zero(conn, monkeypatch):
    """No token → empty df → store returns 0 without touching the table."""
    monkeypatch.delenv("NOAA_CDO_TOKEN", raising=False)
    n = noaa.fetch_and_store(conn, days_back=30)
    assert n == 0
    assert conn.execute("SELECT COUNT(*) FROM fact_weather_obs").fetchone()[0] == 0


# =====================================================================
# USDA AMS connector
# =====================================================================

def test_ams_parse_package_lbs():
    assert ams._parse_package_lbs("25 lb cartons") == 25.0
    assert ams._parse_package_lbs("15 LB flats") == 15.0
    assert ams._parse_package_lbs("40 lbs sacks") == 40.0
    assert ams._parse_package_lbs("10 pound bag") == 10.0
    assert ams._parse_package_lbs(None) is None
    assert ams._parse_package_lbs("carton (no weight)") is None
    # Bushel fallback path returns a positive weight, not None.
    assert ams._parse_package_lbs("bushel cartons") == 50.0


def test_ams_to_iso_date():
    assert ams._to_iso_date("2026-01-15") == "2026-01-15"
    assert ams._to_iso_date("1/5/2026") == "2026-01-05"
    assert ams._to_iso_date("12/31/2025") == "2025-12-31"
    assert ams._to_iso_date(None) is None
    assert ams._to_iso_date("") is None
    assert ams._to_iso_date("not a date") is None


def test_ams_no_api_key_returns_empty_list(monkeypatch):
    """fetch_mars_report_details returns [] when key unset (no HTTP)."""
    monkeypatch.delenv("USDA_AMS_API_KEY", raising=False)
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: pytest.fail("no HTTP expected"))
    assert ams.fetch_mars_report_details(slug_id="2291") == []


def test_ams_uses_basic_auth_with_key(monkeypatch):
    """API key is used as HTTP Basic username with blank password."""
    calls = _patch_requests_get(monkeypatch, ams, _FakeResp({"results": []}))
    ams.fetch_mars_report_details(slug_id="2291", api_key="my-key", last_days=30)
    assert calls[0]["auth"] == ("my-key", "")
    assert calls[0]["params"]["lastDays"] == 30


def test_ams_report_details_extracts_results(monkeypatch):
    payload = {"results": [{"commodity": "Tomatoes"}, {"commodity": "Peppers"}]}
    _patch_requests_get(monkeypatch, ams, _FakeResp(payload))
    rows = ams.fetch_mars_report_details(slug_id="2291", api_key="k")
    assert len(rows) == 2


def test_ams_report_details_non_dict_returns_empty(monkeypatch):
    """A list payload (not the {results: ...} shape) yields []."""
    _patch_requests_get(monkeypatch, ams, _FakeResp([1, 2, 3]))
    rows = ams.fetch_mars_report_details(slug_id="2291", api_key="k")
    assert rows == []


def test_ams_report_details_http_error_returns_empty(monkeypatch):
    _patch_requests_get(monkeypatch, ams, _FakeResp({}, status_ok=False))
    rows = ams.fetch_mars_report_details(slug_id="2291", api_key="k")
    assert rows == []


def test_ams_prices_full_parse_to_per_kg(monkeypatch):
    """End-to-end parse: package → $/kg, dates ISO-ised, product resolved."""
    payload = {"results": [{
        "commodity": "Tomatoes",
        "low_price": "10.00",
        "high_price": "20.00",
        "package": "25 lb cartons",
        "report_date": "1/15/2026",
        "grade": "US 1",
        "group": "VEG",
    }]}
    _patch_requests_get(monkeypatch, ams, _FakeResp(payload))

    df = ams.fetch_mymarketnews_prices(market_slug="HX_FV020", api_key="k")

    assert len(df) == 1
    r = df.iloc[0]
    assert r["commodity"] == "Tomatoes"
    assert r["product_id"] == "PRD-003"
    assert r["report_date"] == "2026-01-15"
    assert r["market_id"] == "HX_FV020"
    assert r["unit"] == "kg"
    assert r["currency"] == "USD"
    assert r["source"] == "usda_mars"
    # avg = 15 $/pkg; per kg = round(15/25 * 2.20462, 4) ≈ 1.3228
    assert r["avg_price"] == 15.0
    assert r["price_per_kg"] == round(15.0 / 25.0 * ams.LBS_PER_KG, 4)


def test_ams_prices_unknown_market_returns_empty(monkeypatch):
    df = ams.fetch_mymarketnews_prices(market_slug="NOPE", api_key="k")
    assert df.empty


def test_ams_prices_filters_out_of_basket(monkeypatch):
    """Commodities not in the FTL basket are dropped."""
    payload = {"results": [{
        "commodity": "Quinoa",
        "low_price": "10", "high_price": "20",
        "package": "25 lb", "report_date": "1/1/2026",
    }]}
    _patch_requests_get(monkeypatch, ams, _FakeResp(payload))
    df = ams.fetch_mymarketnews_prices(market_slug="HX_FV020", api_key="k")
    assert df.empty


def test_ams_prices_skips_unparseable_package(monkeypatch):
    """A row whose package weight can't be parsed is skipped (no NULL $/kg)."""
    payload = {"results": [{
        "commodity": "Tomatoes",
        "low_price": "10", "high_price": "20",
        "package": "carton",  # no weight
        "report_date": "1/1/2026",
    }]}
    _patch_requests_get(monkeypatch, ams, _FakeResp(payload))
    df = ams.fetch_mymarketnews_prices(market_slug="HX_FV020", api_key="k")
    assert df.empty


def test_ams_prices_skips_zero_priced_rows(monkeypatch):
    payload = {"results": [{
        "commodity": "Tomatoes",
        "low_price": "0", "high_price": "0",
        "package": "25 lb", "report_date": "1/1/2026",
    }]}
    _patch_requests_get(monkeypatch, ams, _FakeResp(payload))
    df = ams.fetch_mymarketnews_prices(market_slug="HX_FV020", api_key="k")
    assert df.empty


def test_ams_prices_skips_missing_date(monkeypatch):
    payload = {"results": [{
        "commodity": "Tomatoes",
        "low_price": "10", "high_price": "20",
        "package": "25 lb",  # no report_date / report_begin_date
    }]}
    _patch_requests_get(monkeypatch, ams, _FakeResp(payload))
    df = ams.fetch_mymarketnews_prices(market_slug="HX_FV020", api_key="k")
    assert df.empty


def test_ams_prices_single_sided_uses_max(monkeypatch):
    """Only one of low/high present → avg is the non-zero value (max)."""
    payload = {"results": [{
        "commodity": "Tomatoes",
        "low_price": "0", "high_price": "30",
        "package": "30 lb", "report_date": "1/1/2026",
    }]}
    _patch_requests_get(monkeypatch, ams, _FakeResp(payload))
    df = ams.fetch_mymarketnews_prices(market_slug="HX_FV020", api_key="k")
    assert len(df) == 1
    assert df.iloc[0]["avg_price"] == 30.0


def test_ams_fetch_and_store_inserts(conn, monkeypatch):
    """fetch_and_store persists deduped rows into fact_usda_prices."""
    payload = {"results": [{
        "commodity": "Tomatoes",
        "low_price": "10", "high_price": "20",
        "package": "25 lb cartons", "report_date": "1/15/2026",
    }]}
    _patch_requests_get(monkeypatch, ams, _FakeResp(payload))
    monkeypatch.setenv("USDA_AMS_API_KEY", "k")
    _seed_product(conn, "PRD-003")  # Tomatoes → PRD-003 (FK target)

    n = ams.fetch_and_store(conn, markets=("HX_FV020",), weeks_back=4)
    assert n == 1
    assert conn.execute("SELECT COUNT(*) FROM fact_usda_prices").fetchone()[0] == 1


def test_ams_fetch_and_store_idempotent(conn, monkeypatch):
    """Re-running with the same data inserts nothing new (ON CONFLICT)."""
    payload = {"results": [{
        "commodity": "Tomatoes",
        "low_price": "10", "high_price": "20",
        "package": "25 lb cartons", "report_date": "1/15/2026",
    }]}
    _patch_requests_get(monkeypatch, ams, _FakeResp(payload))
    monkeypatch.setenv("USDA_AMS_API_KEY", "k")
    _seed_product(conn, "PRD-003")

    first = ams.fetch_and_store(conn, markets=("HX_FV020",), weeks_back=4)
    second = ams.fetch_and_store(conn, markets=("HX_FV020",), weeks_back=4)
    assert first == 1
    assert second == 0
    assert conn.execute("SELECT COUNT(*) FROM fact_usda_prices").fetchone()[0] == 1


# =====================================================================
# USDA Food Hub directory
# =====================================================================

def test_hub_no_api_key_returns_empty(monkeypatch):
    monkeypatch.delenv("USDA_LOCALFOOD_API_KEY", raising=False)
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: pytest.fail("no HTTP expected"))
    assert hubs.fetch_food_hubs().empty


def test_hub_parses_listing_records(monkeypatch):
    """A list payload of listings parses into dim_prospect_hubs rows."""
    payload = [
        {
            "listing_id": "555",
            "listing_name": "Green Valley Hub",
            "location_address": "1 Main St",
            "location_x": "-86.1",   # NOTE: used as both city and lng in source
            "location_y": "39.7",
            "location_state": "Indiana",
            "location_zipcode": "46038",
            "products": "tomatoes, lettuce",
            "media_website": "http://example.com",
            "contact_email": "a@b.com",
            "contact_phone": "555-1212",
        },
    ]
    _patch_requests_get(monkeypatch, hubs, _FakeResp(payload))

    df = hubs.fetch_food_hubs(states=["Indiana"], api_key="k")

    assert len(df) == 1
    r = df.iloc[0]
    assert r["hub_id"] == "HUB-555"
    assert r["hub_name"] == "Green Valley Hub"
    assert r["state"] == "Indiana"
    assert r["region"] == "IN"          # Indiana → IN
    assert r["lat"] == 39.7
    assert r["source"] == "usda_localfoodportal"


def test_hub_data_envelope_shape(monkeypatch):
    """Payload shaped {"data": [...]} is also supported."""
    payload = {"data": [{"name": "Wrapped Hub", "location_state": "Ohio"}]}
    _patch_requests_get(monkeypatch, hubs, _FakeResp(payload))
    df = hubs.fetch_food_hubs(states=["Ohio"], api_key="k")
    assert len(df) == 1
    assert df.iloc[0]["hub_name"] == "Wrapped Hub"
    assert df.iloc[0]["region"] == "Midwest"   # non-Indiana


def test_hub_skips_nameless_records(monkeypatch):
    payload = [{"listing_id": "1", "location_state": "Indiana"}]  # no name
    _patch_requests_get(monkeypatch, hubs, _FakeResp(payload))
    df = hubs.fetch_food_hubs(states=["Indiana"], api_key="k")
    assert df.empty


def test_hub_bad_coords_become_none(monkeypatch):
    payload = [{
        "listing_name": "Hub", "location_state": "Indiana",
        "location_x": "not-a-number", "location_y": "also-bad",
    }]
    _patch_requests_get(monkeypatch, hubs, _FakeResp(payload))
    df = hubs.fetch_food_hubs(states=["Indiana"], api_key="k")
    assert len(df) == 1
    assert df.iloc[0]["lat"] is None
    assert df.iloc[0]["lng"] is None


def test_hub_http_error_skips_state(monkeypatch):
    """A failing state request is skipped, not fatal → empty df overall."""
    _patch_requests_get(monkeypatch, hubs, _FakeResp({}, status_ok=False))
    df = hubs.fetch_food_hubs(states=["Indiana"], api_key="k")
    assert df.empty


def test_hub_missing_key_resilience(monkeypatch):
    """Records missing most optional keys still produce a row with a hub_id."""
    payload = [{"listing_name": "Sparse Hub"}]
    _patch_requests_get(monkeypatch, hubs, _FakeResp(payload))
    df = hubs.fetch_food_hubs(states=["Iowa"], api_key="k")
    assert len(df) == 1
    r = df.iloc[0]
    assert r["hub_name"] == "Sparse Hub"
    assert r["hub_id"].startswith("HUB-")   # hashed id when listing_id absent
    assert r["state"] == "Iowa"             # falls back to the query state


def test_hub_fetch_and_store_inserts(conn, monkeypatch):
    payload = [{
        "listing_id": "777", "listing_name": "Store Hub",
        "location_state": "Indiana",
    }]
    _patch_requests_get(monkeypatch, hubs, _FakeResp(payload))
    monkeypatch.setenv("USDA_LOCALFOOD_API_KEY", "k")

    n = hubs.fetch_and_store(conn, states=["Indiana"])
    assert n == 1
    assert conn.execute("SELECT COUNT(*) FROM dim_prospect_hubs").fetchone()[0] == 1
