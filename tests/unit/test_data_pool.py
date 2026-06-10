"""Phase C tests: the data pool — consent gating, anonymization,
k-anonymity, priors.

The anonymization test scans the actual parquet payloads for every name
that exists in the source data: if a company, buyer, supplier, or
product name survives into the pool, the test fails.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from infrastructure.consent_manager import ConsentManager
from infrastructure.db_manager import DBManager
from infrastructure.lineage import stamp_lineage
from infrastructure.operator_registry import OperatorRegistry
from pool.pool_contributor import PoolContributor
from pool.pool_reader import PoolReader

NAMES = ("Good Farms", "Risky Produce", "City Bistro", "Hotel Grand",
         "Roma Tomatoes", "Baby Spinach")


@pytest.fixture()
def env(tmp_path):
    registry = OperatorRegistry(data_root=tmp_path / "data")
    pool_root = tmp_path / "pool"
    contributor = PoolContributor(registry, pool_root)
    reader = PoolReader(pool_root)
    return registry, contributor, reader


def _seed_vault(registry, operator_id, n_orders=15, n_deliveries=15,
                n_waste=12):
    """Seed an operator's vault with named, category-tagged data."""
    dbm = DBManager(registry)
    conn = dbm.get_operator_connection(operator_id)

    def ins(table, df):
        df = stamp_lineage(df, operator_id=operator_id,
                           upload_session_id="s1", source_file="seed.csv")
        cols = ", ".join(df.columns)
        conn.register("seed_df", df)
        conn.execute(f"INSERT INTO {table} ({cols}) SELECT {cols} FROM seed_df")
        conn.unregister("seed_df")

    ins("stg_products", pd.DataFrame([
        {"product_id": "P1", "product_name": "Roma Tomatoes",
         "category": "Vegetables"},
        {"product_id": "P2", "product_name": "Baby Spinach",
         "category": "Leafy Greens"},
    ]))
    ins("stg_buyer_orders", pd.DataFrame([
        {"buyer_name": "City Bistro" if i % 2 else "Hotel Grand",
         "product_id": "P1", "product_name": "Roma Tomatoes",
         "order_date": f"2026-{(i % 5) + 1:02d}-{(i % 27) + 1:02d}",
         "delivery_date": f"2026-{(i % 5) + 1:02d}-{(i % 27) + 1:02d}",
         "requested_quantity": 100.0 + i, "fulfilled_quantity": 95.0,
         "sales_price": 2.5}
        for i in range(n_orders)
    ]))
    ins("stg_supplier_deliveries", pd.DataFrame([
        {"supplier_id": "S1",
         "supplier_name": "Good Farms" if i % 2 else "Risky Produce",
         "product_id": "P1", "product_name": "Roma Tomatoes",
         "delivery_date": f"2026-{(i % 5) + 1:02d}-{(i % 27) + 1:02d}",
         "ordered_quantity": 100.0, "delivered_quantity": 92.0,
         "accepted_quantity": 90.0, "unit_cost": 2.0}
        for i in range(n_deliveries)
    ]))
    ins("stg_waste_adjustments", pd.DataFrame([
        {"product_id": "P1", "product_name": "Roma Tomatoes",
         "date": f"2026-0{(i % 5) + 1}-10", "quantity_lost": 5.0,
         "reason": "Overripe surplus" if i % 2 else "Quality reject"}
        for i in range(n_waste)
    ]))
    conn.close()
    dbm.close_all()


# ── Consent gating ────────────────────────────────────────────────────────────

def test_consented_operator_contributes(env):
    registry, contributor, reader = env
    op = registry.create_operator("Hub A", pool_consent=True,
                                  region="midwest")
    _seed_vault(registry, op.operator_id)
    res = contributor.contribute_session(op.operator_id)
    assert res.status == "contributed"
    assert res.signals_written  # at least one signal type landed
    assert registry.get_operator(op.operator_id).pool_contribution_count == 1


def test_non_consented_operator_skipped_and_logged(env):
    registry, contributor, _ = env
    op = registry.create_operator("Hub B", pool_consent=False)
    _seed_vault(registry, op.operator_id)
    res = contributor.contribute_session(op.operator_id)
    assert res.status == "skipped"
    log = (contributor.pool_root / "contributions"
           / "contribution_log.jsonl").read_text()
    assert "skipped" in log and op.operator_id in log


def test_withdrawn_consent_stops_future_keeps_past(env):
    registry, contributor, reader = env
    op = registry.create_operator("Hub A", pool_consent=True)
    _seed_vault(registry, op.operator_id)
    assert contributor.contribute_session(op.operator_id).status == "contributed"
    before = reader.get_pool_stats().n_signals
    assert before > 0

    ConsentManager(registry).withdraw_consent(op.operator_id)
    assert contributor.contribute_session(op.operator_id).status == "skipped"
    # prior anonymized contributions remain
    assert reader.get_pool_stats().n_signals == before


# ── Anonymization ─────────────────────────────────────────────────────────────

def test_pool_signals_contain_no_names(env):
    registry, contributor, _ = env
    op = registry.create_operator("Hub A", pool_consent=True)
    _seed_vault(registry, op.operator_id)
    contributor.contribute_session(op.operator_id)

    for pq in (contributor.pool_root / "signals").rglob("*.parquet"):
        payload = pd.read_parquet(pq).to_json()
        for name in NAMES + ("Hub A",):
            assert name not in payload, f"{name} leaked into {pq.name}"
        # no raw volumes either: demand is normalized to 1.0
        df = pd.read_parquet(pq)
        if "demand_mean_normalized" in df.columns:
            assert (df["demand_mean_normalized"] == 1.0).all()


def test_k_anonymity_floor_drops_thin_signals(env):
    registry, contributor, _ = env
    op = registry.create_operator("Hub A", pool_consent=True)
    _seed_vault(registry, op.operator_id, n_orders=15,
                n_deliveries=5, n_waste=4)   # deliveries + waste below 10
    res = contributor.contribute_session(op.operator_id)
    assert res.status == "contributed"
    assert "yield_distributions" not in res.signals_written
    assert "waste_profiles" not in res.signals_written
    assert res.signals_dropped_k_anonymity >= 2


# ── Reader / priors ───────────────────────────────────────────────────────────

def test_reader_returns_population_prior(env):
    registry, contributor, reader = env
    a = registry.create_operator("Hub A", pool_consent=True, region="midwest")
    b = registry.create_operator("Hub B", pool_consent=True, region="midwest")
    _seed_vault(registry, a.operator_id)
    _seed_vault(registry, b.operator_id)
    contributor.contribute_session(a.operator_id)
    contributor.contribute_session(b.operator_id)

    prior = reader.get_yield_prior("vegetables", region="midwest")
    assert prior is not None
    assert prior.n_operators == 2            # pooled, not one operator
    assert 0 < prior.fill_rate_mean < 1
    assert prior.alpha > 0 and prior.beta > 0

    dp = reader.get_demand_prior("vegetables")
    assert dp is not None and dp.n_operators == 2

    wp = reader.get_waste_prior("vegetables")
    assert wp is not None
    assert wp.primary_reason in ("over_commitment", "supplier_quality",
                                 "demand_miss")


def test_pool_stats_counts(env):
    registry, contributor, reader = env
    a = registry.create_operator("Hub A", pool_consent=True)
    b = registry.create_operator("Hub B", pool_consent=True)
    _seed_vault(registry, a.operator_id)
    _seed_vault(registry, b.operator_id)
    contributor.contribute_session(a.operator_id)
    contributor.contribute_session(b.operator_id)
    stats = reader.get_pool_stats()
    assert stats.n_operators_contributing == 2
    assert stats.n_signals >= 4
    assert "vegetables" in stats.coverage_by_category


def test_reader_empty_pool_returns_none(env):
    _, _, reader = env
    assert reader.get_demand_prior("vegetables") is None
    assert reader.get_yield_prior("vegetables") is None
    assert reader.get_pool_stats().n_signals == 0


def test_contribution_never_raises(env, monkeypatch):
    registry, contributor, _ = env
    op = registry.create_operator("Hub A", pool_consent=True)
    # operator exists in registry but vault db is gone → must not raise
    registry.get_db_path(op.operator_id).unlink()
    res = contributor.contribute_session(op.operator_id)
    assert res.status == "error"
    log = (contributor.pool_root / "contributions"
           / "contribution_log.jsonl").read_text()
    assert "error" in log
