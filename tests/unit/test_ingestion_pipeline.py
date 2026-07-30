"""Unit tests for ingestion/pipeline.py — connector orchestration.

`run_ingestion_pipeline` fans out to the CSV ingestor and the two external
connectors (USDA AMS, NOAA weather). The external connectors are wrapped in
try/except and are network-bound, so here we:

  * exercise the CSV branch end-to-end against a real in-memory DuckDB,
  * stub the external connectors (via sys.modules monkeypatching of the
    imported `fetch_and_store` symbols) so NO network is touched,
  * assert the returned per-source row-count accounting,
  * assert that a raising external connector is swallowed (graceful degrade)
    rather than crashing the whole pipeline.

No real network, no real LLM, deterministic.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from ingestion.pipeline import run_ingestion_pipeline


# ── Schema bootstrap (in-memory test DB) ─────────────────────────────────────

def _bootstrap(c) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    for sql in sorted((repo_root / "db" / "migrations").glob("*.sql")):
        c.execute(sql.read_text())


@pytest.fixture
def conn():
    c = duckdb.connect(":memory:")
    _bootstrap(c)
    yield c
    c.close()


@pytest.fixture
def stub_connectors(monkeypatch):
    """Replace the network connector modules with in-memory stubs.

    `pipeline.run_ingestion_pipeline` imports `fetch_and_store` lazily from
    `ingestion.usda_ams_connector` and `ingestion.noaa_weather_fetcher`
    INSIDE the function body, so patching the module attribute is enough —
    no network module is ever imported.

    The stub functions are configurable: tests set `.return_value` or
    `.side_effect` before calling the pipeline.
    """

    class _Stub:
        def __init__(self, name):
            self.name = name
            self.return_value = 0
            self.side_effect = None
            self.calls = []

        def __call__(self, conn, *args, **kwargs):
            self.calls.append((args, kwargs))
            if self.side_effect is not None:
                raise self.side_effect
            return self.return_value

    usda_stub = _Stub("usda")
    noaa_stub = _Stub("noaa")

    usda_mod = types.ModuleType("ingestion.usda_ams_connector")
    usda_mod.fetch_and_store = usda_stub
    noaa_mod = types.ModuleType("ingestion.noaa_weather_fetcher")
    noaa_mod.fetch_and_store = noaa_stub

    monkeypatch.setitem(sys.modules, "ingestion.usda_ams_connector", usda_mod)
    monkeypatch.setitem(sys.modules, "ingestion.noaa_weather_fetcher", noaa_mod)

    # The newer external connectors (Open-Meteo, Drought Monitor, ENSO ONI,
    # NASS) are stubbed to zero-count no-ops here: these tests exercise
    # pipeline orchestration of the USDA/NOAA pair, and no test may touch
    # the network.
    zero = _Stub("zero")
    om_mod = types.ModuleType("ingestion.open_meteo_fetcher")
    om_mod.fetch_and_store = zero
    usdm_mod = types.ModuleType("ingestion.drought_monitor_fetcher")
    usdm_mod.fetch_and_store = zero
    oni_mod = types.ModuleType("ingestion.enso_oni_fetcher")
    oni_mod.apply_to_weather = zero
    nass_mod = types.ModuleType("ingestion.nass_quickstats_fetcher")
    nass_mod.fetch_and_store = zero
    monkeypatch.setitem(sys.modules, "ingestion.open_meteo_fetcher", om_mod)
    monkeypatch.setitem(sys.modules, "ingestion.drought_monitor_fetcher", usdm_mod)
    monkeypatch.setitem(sys.modules, "ingestion.enso_oni_fetcher", oni_mod)
    monkeypatch.setitem(sys.modules, "ingestion.nass_quickstats_fetcher", nass_mod)

    return usda_stub, noaa_stub


# ── CSV branch ───────────────────────────────────────────────────────────────

def _seed_buyers(conn):
    """fact_orders.buyer_id has a FK to dim_buyers — seed the referenced rows."""
    for bid in ("BUY-001", "BUY-002"):
        conn.execute(
            "INSERT OR IGNORE INTO dim_buyers (buyer_id, buyer_name, buyer_type) "
            "VALUES (?, ?, ?)",
            [bid, f"Buyer {bid}", "restaurant"],
        )


def test_csv_branch_ingests_directory(conn, stub_connectors, tmp_path):
    """data_dir present → CSV files are ingested and counted by table name.

    The CSV ingestor's 'ignore' path does a position-based `SELECT *`, so the
    file must be full-width for fact_orders (7 columns incl. notes/created_at).
    """
    usda_stub, noaa_stub = stub_connectors
    _seed_buyers(conn)

    # A file whose stem starts with "orders" maps to fact_orders. Headers are
    # the post-mapping column names (no COLUMN_MAPS entry collisions here).
    pd.DataFrame({
        "order_id": ["O1", "O2"],
        "buyer_id": ["BUY-001", "BUY-002"],
        "order_date": ["2026-01-01", "2026-01-02"],
        "week_start": ["2025-12-29", "2025-12-29"],
        "status": ["confirmed", "confirmed"],
        "notes": [None, None],
        "created_at": ["2026-01-01 00:00:00", "2026-01-02 00:00:00"],
    }).to_csv(tmp_path / "orders_2026.csv", index=False)

    counts = run_ingestion_pipeline(conn, data_dir=tmp_path, verbose=False)

    assert counts.get("fact_orders") == 2
    assert conn.execute("SELECT COUNT(*) FROM fact_orders").fetchone()[0] == 2


def test_no_data_dir_skips_csv(conn, stub_connectors):
    """data_dir=None → CSV branch is skipped entirely (no fact_orders key)."""
    counts = run_ingestion_pipeline(conn, data_dir=None, verbose=False)
    assert "fact_orders" not in counts


# ── External connector accounting ────────────────────────────────────────────

def test_external_counts_accumulated(conn, stub_connectors):
    """Successful external connectors contribute their row counts."""
    usda_stub, noaa_stub = stub_connectors
    usda_stub.return_value = 7
    noaa_stub.return_value = 3

    counts = run_ingestion_pipeline(conn, data_dir=None, days_back=14, verbose=False)

    assert counts["fact_market_prices"] == 7
    assert counts["fact_weather_obs"] == 3
    # days_back is threaded through to each connector.
    assert noaa_stub.calls[0][1].get("days_back") == 14
    assert usda_stub.calls[0][1].get("days_back") == 14


def test_usda_failure_is_swallowed(conn, stub_connectors):
    """A raising USDA connector must not crash the pipeline; NOAA still runs."""
    usda_stub, noaa_stub = stub_connectors
    usda_stub.side_effect = RuntimeError("network down")
    noaa_stub.return_value = 5

    counts = run_ingestion_pipeline(conn, data_dir=None, verbose=False)

    # USDA contributed nothing but did not propagate the exception.
    assert counts.get("fact_market_prices", 0) == 0
    assert counts["fact_weather_obs"] == 5


def test_noaa_failure_is_swallowed(conn, stub_connectors):
    """A raising NOAA connector is caught; USDA result is preserved."""
    usda_stub, noaa_stub = stub_connectors
    usda_stub.return_value = 4
    noaa_stub.side_effect = RuntimeError("api unavailable")

    counts = run_ingestion_pipeline(conn, data_dir=None, verbose=False)

    assert counts["fact_market_prices"] == 4
    assert counts.get("fact_weather_obs", 0) == 0


def test_both_connectors_fail_returns_empty(conn, stub_connectors):
    """Both external sources down + no CSV → empty-but-valid result dict."""
    usda_stub, noaa_stub = stub_connectors
    usda_stub.side_effect = ConnectionError("x")
    noaa_stub.side_effect = ConnectionError("y")

    counts = run_ingestion_pipeline(conn, data_dir=None, verbose=False)

    assert counts.get("fact_market_prices", 0) == 0
    assert counts.get("fact_weather_obs", 0) == 0


def test_zero_count_connectors_omitted_or_zero(conn, stub_connectors):
    """When connectors return 0, the keys are present but zero-valued."""
    usda_stub, noaa_stub = stub_connectors
    usda_stub.return_value = 0
    noaa_stub.return_value = 0

    counts = run_ingestion_pipeline(conn, data_dir=None, verbose=False)

    assert counts.get("fact_market_prices", 0) == 0
    assert counts.get("fact_weather_obs", 0) == 0


def test_full_pipeline_csv_plus_external(conn, stub_connectors, tmp_path):
    """CSV + both external connectors combine into one accounting dict."""
    usda_stub, noaa_stub = stub_connectors
    usda_stub.return_value = 2
    noaa_stub.return_value = 1
    _seed_buyers(conn)

    pd.DataFrame({
        "order_id": ["O1"],
        "buyer_id": ["BUY-001"],
        "order_date": ["2026-01-01"],
        "week_start": ["2025-12-29"],
        "status": ["confirmed"],
        "notes": [None],
        "created_at": ["2026-01-01 00:00:00"],
    }).to_csv(tmp_path / "orders.csv", index=False)

    counts = run_ingestion_pipeline(conn, data_dir=tmp_path, verbose=False)

    assert counts["fact_orders"] == 1
    assert counts["fact_market_prices"] == 2
    assert counts["fact_weather_obs"] == 1


# =====================================================================
# validators.py — additional edge cases
#   (negatives, reversed dates, magnitude warnings, NULL handling,
#    empty df, unknown-table fail-closed)
# =====================================================================

from datetime import date as _date  # noqa: E402

from ingestion.validators import validate_staging_df  # noqa: E402

_TODAY = _date(2026, 5, 27)


def test_validator_unknown_table_fails_closed():
    """A non-staging table must be rejected, never pass vacuously."""
    df = pd.DataFrame({"x": [1]})
    result = validate_staging_df("fact_orders", df, today=_TODAY)
    assert not result.ok
    assert any("Unknown staging table" in e for e in result.errors)


def test_validator_empty_df_is_ok_with_zero_rows():
    result = validate_staging_df("stg_supplier_deliveries", pd.DataFrame(), today=_TODAY)
    assert result.ok
    assert result.n_rows == 0
    assert result.errors == []


def test_validator_price_magnitude_warning_not_error():
    """price/cost columns use the $10k cap → warn, do not block."""
    df = pd.DataFrame({
        "product_name": ["Tomatoes"],
        "delivery_date": ["2026-05-01"],
        "unit_cost": [50_000.0],   # absurd $/kg but only a warning
    })
    result = validate_staging_df("stg_supplier_deliveries", df, today=_TODAY)
    assert result.ok
    assert any("unit_cost" in w and "10,000" in w for w in result.warnings)


def test_validator_quantity_magnitude_warning_not_error():
    """quantity columns use the 1e6 cap → warn, do not block."""
    df = pd.DataFrame({
        "product_name": ["Tomatoes"],
        "quantity_on_hand": [2_000_000.0],
    })
    result = validate_staging_df("stg_inventory_lots", df, today=_TODAY)
    assert result.ok
    assert any("quantity_on_hand" in w for w in result.warnings)


def test_validator_null_quantities_do_not_trigger_negative_error():
    """NULL/NaN in a quantity column is not negative → no error."""
    df = pd.DataFrame({
        "product_name": ["A", "B"],
        "delivery_date": ["2026-05-01", "2026-05-02"],
        "ordered_quantity": [100.0, None],   # NaN must be tolerated
    })
    result = validate_staging_df("stg_supplier_deliveries", df, today=_TODAY)
    assert result.ok
    assert result.errors == []


def test_validator_null_dates_in_required_col_not_flagged():
    """A genuinely NULL required date (not an unparseable string) is not an
    'unparseable' error — the mask requires the source value to be non-null."""
    df = pd.DataFrame({
        "product_name": ["A"],
        "delivery_date": [None],
        "ordered_quantity": [10.0],
    })
    result = validate_staging_df("stg_supplier_deliveries", df, today=_TODAY)
    assert result.ok


def test_validator_far_future_date_warns_only():
    df = pd.DataFrame({
        "product_name": ["A"],
        "requested_quantity": [10.0],
        "order_date": ["2040-01-01"],   # >2 years out
    })
    result = validate_staging_df("stg_buyer_orders", df, today=_TODAY)
    assert result.ok
    assert any("future" in w for w in result.warnings)


def test_validator_negative_and_reversed_both_reported():
    """Multiple independent violations accumulate in the error list."""
    df = pd.DataFrame({
        "product_name": ["A"],
        "requested_quantity": [-5.0],          # negative → error
        "order_date": ["2026-05-20"],
        "delivery_date": ["2026-05-10"],       # reversed → error
    })
    result = validate_staging_df("stg_buyer_orders", df, today=_TODAY)
    assert not result.ok
    assert len(result.errors) >= 2
