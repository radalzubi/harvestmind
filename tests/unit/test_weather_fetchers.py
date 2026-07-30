"""Unit tests for the external weather/ag data fetchers.

All network calls are mocked; DuckDB is in-memory with the real
migrations applied. No live API access in CI.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import duckdb
import pandas as pd
import pytest

from ingestion.drought_monitor_fetcher import (
    _weekly_category,
    apply_to_weather as drought_apply,
    fetch_drought,
)
from ingestion.enso_oni_fetcher import apply_to_weather as oni_apply, fetch_oni
from ingestion.open_meteo_fetcher import fetch_and_store, fetch_history
from ingestion.weather_features import weekly_weather_frame

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def conn() -> duckdb.DuckDBPyConnection:
    c = duckdb.connect(":memory:")
    for sql in sorted((ROOT / "db" / "migrations").glob("*.sql")):
        c.execute(sql.read_text())
    return c


def _mock_response(payload, text=None):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.text = text or ""
    resp.raise_for_status.return_value = None
    return resp


OPEN_METEO_PAYLOAD = {
    "daily": {
        "time": ["2024-06-01", "2024-06-02", "2024-06-03"],
        "temperature_2m_max": [20.4, 33.5, 28.4],
        "temperature_2m_min": [16.1, 17.3, 14.3],
        "precipitation_sum": [5.0, 0.4, 0.0],
    }
}


class TestOpenMeteo:
    def test_fetch_history_derives_features(self):
        with patch("requests.get", return_value=_mock_response(OPEN_METEO_PAYLOAD)):
            df = fetch_history(40.39, -86.89, county_fips="18157")
        assert len(df) == 3
        # tavg midpoint
        assert df.iloc[0]["tavg_c"] == pytest.approx((20.4 + 16.1) / 2)
        # heat stress only where tmax > 32
        assert list(df["heat_stress_flag"]) == [False, True, False]
        # gdd base 10, floored at zero
        assert df.iloc[0]["gdd_base10"] == pytest.approx((20.4 + 16.1) / 2 - 10.0)
        assert (df["gdd_base10"] >= 0).all()
        assert (df["source"] == "open_meteo").all()

    def test_fetch_history_network_failure_returns_empty(self):
        with patch("requests.get", side_effect=ConnectionError):
            df = fetch_history(40.39, -86.89)
        assert df.empty

    def test_fetch_and_store_inserts(self, conn):
        with patch("requests.get", return_value=_mock_response(OPEN_METEO_PAYLOAD)):
            n = fetch_and_store(conn, county_fips="18157")
        assert n == 3
        stored = conn.execute(
            "SELECT COUNT(*) FROM fact_weather_obs WHERE source='open_meteo'"
        ).fetchone()[0]
        assert stored == 3
        # idempotent: re-insert ignores duplicates
        with patch("requests.get", return_value=_mock_response(OPEN_METEO_PAYLOAD)):
            fetch_and_store(conn, county_fips="18157")
        stored2 = conn.execute(
            "SELECT COUNT(*) FROM fact_weather_obs"
        ).fetchone()[0]
        assert stored2 == 3

    def test_unknown_county_without_coords_is_zero(self, conn):
        assert fetch_and_store(conn, county_fips="99999") == 0


class TestDroughtMonitor:
    def test_weekly_category_majority_rule(self):
        # 60% in D1 or worse -> D1
        row = pd.Series({"D0": 20.0, "D1": 40.0, "D2": 20.0, "D3": 0.0, "D4": 0.0})
        assert _weekly_category(row) == "D1"
        # majority drought-free -> None
        row = pd.Series({"D0": 30.0, "D1": 10.0, "D2": 0.0, "D3": 0.0, "D4": 0.0})
        assert _weekly_category(row) is None
        # deep drought covering half -> D3
        row = pd.Series({"D0": 0.0, "D1": 0.0, "D2": 10.0, "D3": 50.0, "D4": 0.0})
        assert _weekly_category(row) == "D3"

    def test_fetch_drought_parses_csv(self):
        csv = (
            "MapDate,FIPS,County,State,None,D0,D1,D2,D3,D4,ValidStart,ValidEnd,StatisticFormatID\n"
            "20240625,18157,Tippecanoe County,IN,0.00,100.00,0.00,0.00,0.00,0.00,2024-06-25,2024-07-01,1\n"
            "20240611,18157,Tippecanoe County,IN,100.00,0.00,0.00,0.00,0.00,0.00,2024-06-11,2024-06-17,1\n"
        )
        with patch("requests.get", return_value=_mock_response({}, text=csv)):
            df = fetch_drought("18157", date(2024, 6, 1), date(2024, 6, 30))
        assert len(df) == 2
        assert df.iloc[1]["drought_monitor_cat"] == "D0"   # 100% D0 week
        assert df.iloc[0]["drought_monitor_cat"] is None   # 100% drought-free week

    def test_apply_stamps_rows(self, conn):
        conn.execute(
            "INSERT INTO fact_weather_obs (obs_id, obs_date, county_fips, source)"
            " VALUES ('X-1', DATE '2024-06-26', '18157', 'test')"
        )
        drought_df = pd.DataFrame([{
            "valid_start": date(2024, 6, 25),
            "valid_end": date(2024, 7, 1),
            "drought_monitor_cat": "D0",
        }])
        assert drought_apply(conn, "18157", drought_df) == 1
        cat = conn.execute(
            "SELECT drought_monitor_cat FROM fact_weather_obs WHERE obs_id='X-1'"
        ).fetchone()[0]
        assert cat == "D0"


ONI_TEXT = (
    " SEAS  YR   TOTAL   ANOM\n"
    "  DJF 2024  26.62   1.79\n"
    "  JFM 2024  26.87   1.42\n"
)


class TestEnsoOni:
    def test_fetch_oni_parses(self):
        with patch("requests.get", return_value=_mock_response({}, text=ONI_TEXT)):
            df = fetch_oni()
        assert len(df) == 2
        jan = df[(df.year == 2024) & (df.month == 1)].iloc[0]
        assert jan["oni_index"] == pytest.approx(1.79)

    def test_apply_stamps_by_month(self, conn):
        conn.execute(
            "INSERT INTO fact_weather_obs (obs_id, obs_date, county_fips, source)"
            " VALUES ('X-2', DATE '2024-01-15', '18157', 'test')"
        )
        oni_df = pd.DataFrame([{"year": 2024, "month": 1, "oni_index": 1.79}])
        assert oni_apply(conn, oni_df) == 1
        val = conn.execute(
            "SELECT enso_oni_index FROM fact_weather_obs WHERE obs_id='X-2'"
        ).fetchone()[0]
        assert val == pytest.approx(1.79)


class TestWeeklyWeatherFrame:
    def test_aggregates_to_forecaster_shape(self, conn):
        rows = [
            ("W-1", "2024-06-03", 25.0, 2.0, False, 15.0),
            ("W-2", "2024-06-04", 35.0, 0.0, True, 25.0),
            ("W-3", "2024-06-05", 30.0, 4.0, False, 20.0),
        ]
        for obs_id, d, tavg, precip, heat, gdd in rows:
            conn.execute(
                "INSERT INTO fact_weather_obs (obs_id, obs_date, county_fips,"
                " source, tavg_c, precip_mm, heat_stress_flag, gdd_base10)"
                " VALUES (?, ?, '18157', 'test', ?, ?, ?, ?)",
                [obs_id, d, tavg, precip, heat, gdd],
            )
        df = weekly_weather_frame(conn, county_fips="18157")
        assert len(df) == 1
        wk = df.iloc[0]
        assert wk["tavg_c"] == pytest.approx(30.0)
        assert wk["precip_mm"] == pytest.approx(6.0)
        assert bool(wk["heat_stress_flag"]) is True   # any hot day flags the week
        assert wk["gdd_base10"] == pytest.approx(60.0)
        # exactly the optional feature columns the forecaster accepts
        for col in ["week_start", "tavg_c", "precip_mm", "heat_stress_flag",
                    "enso_oni_index"]:
            assert col in df.columns
