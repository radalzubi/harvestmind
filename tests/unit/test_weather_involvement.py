"""Tests that weather is mathematically involved in decisions — not just
stored. Covers the two wires: the shift application to supplier
distributions (supply side) and the weather frame reaching the
forecaster (demand side)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import duckdb
import pytest

import risk.yield_covariates as yc
from ingestion.open_meteo_fetcher import fetch_forecast
from risk.yield_covariates import (
    apply_shift_to_distributions,
    weather_shift_for_window,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def conn() -> duckdb.DuckDBPyConnection:
    c = duckdb.connect(":memory:")
    for sql in sorted((ROOT / "db" / "migrations").glob("*.sql")):
        c.execute(sql.read_text())
    return c


DISTS = {
    "SUP-001": {"posterior_mean": 0.90, "downside": 0.80,
                "alpha": 45.0, "beta": 5.0, "spread": 0.10},
}


class TestApplyShift:
    def test_negative_delta_lowers_mean_and_downside(self):
        out = apply_shift_to_distributions(DISTS, -0.10, quantile=0.10)
        d = out["SUP-001"]
        assert d["posterior_mean"] == pytest.approx(0.80, abs=1e-9)
        assert d["downside"] < 0.80          # worse than the unshifted downside
        assert d["weather_shift"] == -0.10
        # Beta re-fit at the shifted mean
        a, b = d["alpha"], d["beta"]
        assert a / (a + b) == pytest.approx(0.80, abs=1e-6)

    def test_inputs_not_mutated(self):
        apply_shift_to_distributions(DISTS, -0.10)
        assert DISTS["SUP-001"]["posterior_mean"] == 0.90
        assert "weather_shift" not in DISTS["SUP-001"]

    def test_zero_delta_keeps_mean(self):
        out = apply_shift_to_distributions(DISTS, 0.0)
        assert out["SUP-001"]["posterior_mean"] == pytest.approx(0.90)


ADMITTED = {"admitted": True, "measured_effect_delta_fill": -0.0875}
REFUSED = {"admitted": False, "reason": "no weather observations loaded"}


class TestShiftForWindow:
    def _add_weather(self, conn, d: str, heat: bool):
        conn.execute(
            "INSERT INTO fact_weather_obs (obs_id, obs_date, county_fips,"
            " source, heat_stress_flag) VALUES (?, ?, '18157', 'test', ?)",
            [f"X-{d}", d, heat],
        )

    def test_not_admitted_is_inactive(self, conn, monkeypatch):
        monkeypatch.setattr(yc, "admit_weather_signal", lambda c: REFUSED)
        r = weather_shift_for_window(conn, date(2024, 6, 1), date(2024, 6, 7))
        assert r["active"] is False and "not admitted" in r["reason"]

    def test_admitted_but_no_weather_rows(self, conn, monkeypatch):
        monkeypatch.setattr(yc, "admit_weather_signal", lambda c: ADMITTED)
        r = weather_shift_for_window(conn, date(2024, 6, 1), date(2024, 6, 7))
        assert r["active"] is False and "no weather rows" in r["reason"]

    def test_admitted_but_window_cool(self, conn, monkeypatch):
        monkeypatch.setattr(yc, "admit_weather_signal", lambda c: ADMITTED)
        self._add_weather(conn, "2024-06-03", heat=False)
        r = weather_shift_for_window(conn, date(2024, 6, 1), date(2024, 6, 7))
        assert r["active"] is False and "not heat-flagged" in r["reason"]

    def test_admitted_and_hot_window_activates(self, conn, monkeypatch):
        monkeypatch.setattr(yc, "admit_weather_signal", lambda c: ADMITTED)
        self._add_weather(conn, "2024-06-03", heat=True)
        r = weather_shift_for_window(conn, date(2024, 6, 1), date(2024, 6, 7))
        assert r["active"] is True
        assert r["delta"] == pytest.approx(-0.0875)


class TestForecastFetcher:
    def test_forecast_rows_labeled_as_forecast(self):
        payload = {"daily": {
            "time": ["2026-08-01", "2026-08-02"],
            "temperature_2m_max": [33.5, 25.0],
            "temperature_2m_min": [20.0, 15.0],
            "precipitation_sum": [0.0, 4.0],
        }}
        resp = MagicMock()
        resp.json.return_value = payload
        resp.raise_for_status.return_value = None
        with patch("requests.get", return_value=resp):
            df = fetch_forecast(40.39, -86.89, county_fips="18157")
        assert (df["source"] == "open_meteo_forecast").all()
        assert df["obs_id"].str.startswith("OMF-").all()
        assert list(df["heat_stress_flag"]) == [True, False]


class TestDemandServiceWeather:
    def test_weather_frame_none_on_empty_db(self, conn):
        from forecasting.demand.demand_forecast_service import _weather_frame
        assert _weather_frame(conn) is None

    def test_weather_frame_present_with_data(self, conn):
        conn.execute(
            "INSERT INTO fact_weather_obs (obs_id, obs_date, county_fips,"
            " source, tavg_c, precip_mm, heat_stress_flag, gdd_base10)"
            " VALUES ('X-1', DATE '2024-06-03', '18157', 'test',"
            " 25.0, 2.0, FALSE, 15.0)"
        )
        from forecasting.demand.demand_forecast_service import _weather_frame
        df = _weather_frame(conn)
        assert df is not None and len(df) == 1
        assert "tavg_c" in df.columns and "enso_oni_index" in df.columns
