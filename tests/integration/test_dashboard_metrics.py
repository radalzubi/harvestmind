"""Integration tests for dashboard.lib.metrics.

Exercise every metric function against the real schema, populated with a
small synthetic dataset, to confirm queries are valid and shapes are
correct. Streamlit is NOT imported (we only touch pure-function helpers).
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def populated_conn():
    import sys
    sys.path.insert(0, str(ROOT))
    from scripts.setup_db import setup_db
    from synthetic.generator import SyntheticGenerator

    conn = duckdb.connect(":memory:")
    setup_db(conn, load_seeds=True)
    SyntheticGenerator(n_weeks=20, seed=11).generate_all(conn)
    yield conn
    conn.close()


def test_header_context(populated_conn):
    from dashboard.lib.metrics import header_context
    ctx = header_context(populated_conn, partner_name="Test Partner")
    assert ctx.partner_name == "Test Partner"
    assert ctx.rows_used > 0
    assert ctx.period_start is not None
    assert ctx.period_end is not None


def test_executive_kpis_returns_finite_or_none(populated_conn):
    from dashboard.lib.metrics import executive_kpis
    kpis = executive_kpis(populated_conn, partner_gmv_usd=3_000_000)
    # Either None (insufficient data) or finite positive numbers
    for v in (
        kpis.estimated_annual_savings_usd,
        kpis.spot_premium_savings_usd,
        kpis.waste_cost_reduction_usd,
    ):
        assert v is None or (v >= 0 and v == v)  # not NaN
    assert 0 <= kpis.data_quality_score <= 1


def test_data_quality_breakdown_covers_all_required_tables(populated_conn):
    from dashboard.lib.metrics import data_quality_breakdown
    rows = data_quality_breakdown(populated_conn)
    assert len(rows) >= 10
    statuses = {r.status for r in rows}
    # Must use one of the four canonical statuses
    assert statuses.issubset({"Strong", "Usable with caveats", "Weak", "Not enough data"})


def test_waste_by_product(populated_conn):
    from dashboard.lib.metrics import waste_by_product
    df = waste_by_product(populated_conn)
    assert {"product", "product_id", "waste_kg", "waste_usd"}.issubset(df.columns)
    # All rows non-negative
    assert (df["waste_kg"] >= 0).all()
    assert (df["waste_usd"] >= 0).all()


def test_spot_by_product(populated_conn):
    from dashboard.lib.metrics import spot_by_product
    df = spot_by_product(populated_conn)
    assert {"product", "spot_cost_usd", "spot_kg", "total_kg"}.issubset(df.columns)
    assert (df["spot_kg"] <= df["total_kg"] + 1e-6).all()


def test_recommendation_table_returns_actionable(populated_conn):
    from dashboard.lib.metrics import recommendation_table
    df = recommendation_table(populated_conn)
    if df.empty:
        pytest.skip("no recommendations generated for short history")
    required = {
        "product", "product_id", "recommended_commit_kg",
        "historical_avg_kg", "shortage_risk", "waste_risk", "explanation",
    }
    assert required.issubset(df.columns)
    # Risk values must be canonical
    assert df["shortage_risk"].isin(["Low", "Medium", "High", "Critical"]).all()
    # Recommendations are non-negative
    assert (df["recommended_commit_kg"] >= 0).all()


def test_supplier_reliability(populated_conn):
    from dashboard.lib.metrics import supplier_reliability
    df = supplier_reliability(populated_conn)
    if df.empty:
        return
    assert "risk_tier" in df.columns
    assert df["risk_tier"].isin(["Low", "Medium", "High", "Critical"]).all()
    # Fill reliability bounded
    fills = df["fill_reliability"].dropna()
    assert ((fills >= 0) & (fills <= 1)).all()


def test_buyer_demand_variability(populated_conn):
    from dashboard.lib.metrics import buyer_demand_variability
    df = buyer_demand_variability(populated_conn)
    if df.empty:
        return
    assert "risk_tier" in df.columns
    assert df["risk_tier"].isin(["Low", "Medium", "High", "Critical"]).all()


def test_loss_attribution_has_action(populated_conn):
    from dashboard.lib.metrics import loss_attribution
    df = loss_attribution(populated_conn)
    if df.empty:
        return
    assert "recommended_action" in df.columns
    assert df["recommended_action"].notna().all()


def test_top_risk_drivers_returns_at_most_n(populated_conn):
    from dashboard.lib.metrics import top_risk_drivers
    df = top_risk_drivers(populated_conn, n=5)
    assert len(df) <= 5
    if not df.empty:
        # Sorted descending by total loss
        assert (df["loss_usd"].diff().dropna() <= 1e-6).all()


def test_product_risk_heatmap_bounded(populated_conn):
    from dashboard.lib.metrics import product_risk_heatmap
    df = product_risk_heatmap(populated_conn, weeks=8)
    if df.empty:
        return
    assert "risk" in df.columns
    assert ((df["risk"] >= 0) & (df["risk"] <= 1)).all()


def test_no_negative_quantities_anywhere(populated_conn):
    """Sanity: every metric that returns kg/usd values must be non-negative."""
    from dashboard.lib.metrics import (
        spot_by_product, waste_by_product, supplier_concentration,
    )
    for fn in (spot_by_product, waste_by_product, supplier_concentration):
        df = fn(populated_conn)
        for col in df.select_dtypes("number").columns:
            assert (df[col] >= -1e-6).all(), f"{fn.__name__} has negatives in {col}"
