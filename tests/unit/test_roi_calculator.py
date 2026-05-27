"""Unit tests for backtesting.roi_calculator.

Focus: benchmark_scenarios() — the research-backed assumption sweep.
"""

from __future__ import annotations

import pandas as pd
import pytest

from pathlib import Path

import duckdb

from backtesting.roi_calculator import (
    AVG_PRODUCE_PRICE_KG,
    BENCHMARK_SCENARIOS,
    _resolve_avg_produce_price_kg,
    benchmark_scenarios,
)


# ── Fixture ──────────────────────────────────────────────────────────────────

def _backtest_df() -> pd.DataFrame:
    """Synthetic 3-origin backtest with one naive + one SP row per origin.

    Numbers are chosen so the optimizer wins clearly (lower spot, lower waste,
    higher fill) — making scenario ROI > 0.
    """
    rows: list[dict] = []
    for origin in ("2025-01-06", "2025-02-03", "2025-03-03"):
        rows.append({
            "origin_week": origin, "horizon_weeks": 4, "model": "naive_lastyear",
            "gamma": None, "lambda_cvar": None, "objective": None,
            "service_level_pct": 92.0,
            "waste_kg": 1500.0,
            "spot_kg": 800.0,  "spot_cost_usd": 2080.0,
            "total_cost_usd": 30000.0,
            "solve_time_s": 0.0, "solver_status": "ok",
            "waste_cost_usd": 750.0, "commit_cost_usd": 27000.0,
            "lost_sale_kg": 50.0, "lost_sale_cost_usd": 175.0,
        })
        rows.append({
            "origin_week": origin, "horizon_weeks": 4, "model": "two_stage_sp",
            "gamma": None, "lambda_cvar": None, "objective": 28000.0,
            "service_level_pct": 99.0,
            "waste_kg": 600.0,
            "spot_kg": 250.0,  "spot_cost_usd": 650.0,
            "total_cost_usd": 27500.0,
            "solve_time_s": 0.0, "solver_status": "optimal",
            "waste_cost_usd": 300.0, "commit_cost_usd": 26500.0,
            "lost_sale_kg": 5.0, "lost_sale_cost_usd": 17.5,
        })
    return pd.DataFrame(rows)


# ── Tests ────────────────────────────────────────────────────────────────────

def test_benchmark_scenarios_returns_six_rows():
    """benchmark_scenarios() returns exactly 6 scenario rows after the
    aggregator + distributor tiers were added in migration 009."""
    df = benchmark_scenarios(_backtest_df(), annual_gmv_usd=3_000_000)
    assert len(df) == 6
    names = set(df["scenario_name"].tolist())
    assert names == {
        "Conservative", "Base (SR-77)", "Optimistic", "Stress-low",
        "Aggregator (Tier B)", "Distributor (Tier C)",
    }


def test_benchmark_scenarios_roi_ordering():
    """Within the food-hub tier (same Tier A subscription), Optimistic
    ROI ≥ Base ROI ≥ Conservative ROI."""
    df = benchmark_scenarios(_backtest_df(), annual_gmv_usd=3_000_000)
    by_name = df.set_index("scenario_name")
    cons = by_name.loc["Conservative", "roi_multiple"]
    base = by_name.loc["Base (SR-77)", "roi_multiple"]
    opt = by_name.loc["Optimistic", "roi_multiple"]
    assert cons is not None and base is not None and opt is not None
    assert opt >= base >= cons


def test_benchmark_scenarios_aggregator_lower_roi_than_hub_at_same_savings():
    """Tier B aggregator subscription is 3.75× Tier A → ROI must be lower
    when gross-margin assumptions match."""
    df = benchmark_scenarios(_backtest_df(), annual_gmv_usd=3_000_000)
    by_name = df.set_index("scenario_name")
    base = by_name.loc["Base (SR-77)", "roi_multiple"]
    agg = by_name.loc["Aggregator (Tier B)", "roi_multiple"]
    dist = by_name.loc["Distributor (Tier C)", "roi_multiple"]
    assert base >= agg >= dist


def test_benchmark_scenarios_no_nan():
    """No NaN in any numeric column of the scenario output."""
    df = benchmark_scenarios(_backtest_df(), annual_gmv_usd=3_000_000)
    numeric_cols = [
        "gross_margin_pct", "spot_multiplier", "lost_sale_per_kg",
        "annual_subscription_usd", "annual_spot_savings_usd",
        "annual_waste_savings_usd", "annual_lost_sale_recovery_usd",
        "total_annual_benefit_usd", "net_annual_benefit_usd",
        "baseline_fill_pct", "target_fill_pct", "fill_rate_uplift_pts",
    ]
    for col in numeric_cols:
        assert col in df.columns, f"missing column: {col}"
        assert not df[col].isna().any(), f"NaN found in column {col}"


# ── Smoke test for the BENCHMARK_SCENARIOS constant ──────────────────────────

def test_benchmark_scenarios_constant_shape():
    """Sanity check on the published scenarios constant."""
    assert len(BENCHMARK_SCENARIOS) == 6
    margins = [s.gross_margin_pct for s in BENCHMARK_SCENARIOS]
    # All in [0.10, 0.25] band per USDA SR-77
    assert all(0.10 < m < 0.25 for m in margins)
    # Spot multipliers in [1.0, 2.0]
    spots = [s.spot_multiplier for s in BENCHMARK_SCENARIOS]
    assert all(1.0 <= m <= 2.0 for m in spots)


def _bootstrap_db():
    c = duckdb.connect(":memory:")
    repo_root = Path(__file__).resolve().parents[2]
    for sql in sorted((repo_root / "db" / "migrations").glob("*.sql")):
        c.execute(sql.read_text())
    return c


def test_resolve_avg_produce_price_falls_back_when_table_empty():
    """No rows in fact_usda_prices → constant fallback."""
    c = _bootstrap_db()
    try:
        v = _resolve_avg_produce_price_kg(c)
    finally:
        c.close()
    assert v == AVG_PRODUCE_PRICE_KG


def test_resolve_avg_produce_price_uses_live_data_when_present():
    """Inject a few rows; the function must average them."""
    c = _bootstrap_db()
    try:
        c.execute(
            "INSERT INTO fact_usda_prices (price_id, report_date, market_id, "
            "commodity, price_per_kg) VALUES "
            "('P1', CURRENT_DATE, 'IL_MN250', 'Cucumbers',     5.00), "
            "('P2', CURRENT_DATE, 'IL_MN250', 'Tomatoes',      6.00), "
            "('P3', CURRENT_DATE, 'IL_MN250', 'Leafy Greens',  7.00)"
        )
        v = _resolve_avg_produce_price_kg(c)
    finally:
        c.close()
    assert v == pytest.approx(6.00)


def test_resolve_avg_produce_price_ignores_old_rows():
    """Only trailing-52-week rows count."""
    c = _bootstrap_db()
    try:
        c.execute(
            "INSERT INTO fact_usda_prices (price_id, report_date, market_id, "
            "commodity, price_per_kg) VALUES "
            "('OLD', '2020-01-01', 'IL_MN250', 'Cucumbers', 99.00)"
        )
        v = _resolve_avg_produce_price_kg(c)
    finally:
        c.close()
    assert v == AVG_PRODUCE_PRICE_KG


def test_benchmark_scenarios_uses_live_price_when_conn_provided():
    """benchmark_scenarios picks up live USDA pricing via conn."""
    c = _bootstrap_db()
    try:
        # Insert prices that yield a different basket avg ($10/kg) so the
        # output should differ from the $18.60 fallback.
        c.execute(
            "INSERT INTO fact_usda_prices (price_id, report_date, market_id, "
            "commodity, price_per_kg) VALUES "
            "('P1', CURRENT_DATE, 'IL_MN250', 'Cucumbers',  10.00), "
            "('P2', CURRENT_DATE, 'IL_MN250', 'Tomatoes',   10.00)"
        )
        df = benchmark_scenarios(
            _backtest_df(), annual_gmv_usd=3_000_000, conn=c,
        )
    finally:
        c.close()
    # lost_sale_per_kg = avg_produce_price ($10) × gross_margin (varies)
    cons_lost = df.loc[df["scenario_name"] == "Conservative", "lost_sale_per_kg"].iloc[0]
    assert cons_lost == pytest.approx(10.0 * 0.145, abs=0.01)


def test_benchmark_scenarios_handles_empty_backtest():
    """Empty backtest df → empty scenarios df, no crash."""
    empty = pd.DataFrame(columns=[
        "origin_week", "horizon_weeks", "model", "service_level_pct",
        "waste_kg", "spot_kg", "spot_cost_usd", "total_cost_usd",
    ])
    df = benchmark_scenarios(empty, annual_gmv_usd=3_000_000)
    assert df.empty
