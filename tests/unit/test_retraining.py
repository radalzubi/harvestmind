"""Phase 5 tests: registry, validation-gated retraining, rollback, pooling hook."""

from __future__ import annotations

from datetime import date, timedelta

import duckdb
import numpy as np
import pytest

from retraining.registry import ModelRegistry

_TODAY = date(2026, 5, 25)


def _orders_db(weeks=30, seed=7, base=500.0):
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE stg_buyer_orders (
            buyer_id VARCHAR, buyer_name VARCHAR, product_name VARCHAR,
            order_date DATE, delivery_date DATE,
            requested_quantity DOUBLE, sales_price DOUBLE
        )
    """)
    conn.execute("""
        CREATE TABLE stg_supplier_deliveries (
            supplier_id VARCHAR, supplier_name VARCHAR, product_name VARCHAR,
            delivery_date DATE, ordered_quantity DOUBLE,
            delivered_quantity DOUBLE, accepted_quantity DOUBLE,
            unit_cost DOUBLE
        )
    """)
    rng = np.random.default_rng(seed)
    start = _TODAY - timedelta(weeks=weeks)
    o, d = [], []
    for w in range(weeks):
        day = start + timedelta(weeks=w)
        qty = max(base + rng.normal(0, 40), 10)
        o.append(("B1", "Buyer", "Tomatoes", str(day), str(day), qty, 3.0))
        for s in ("S1", "S2", "S3"):
            ordered = qty / 2
            fill = float(np.clip(rng.beta(16, 3), 0, 1))
            d.append((s, s, "Tomatoes", str(day), ordered,
                      ordered * fill, ordered * fill, 2.0))
    conn.executemany("INSERT INTO stg_buyer_orders VALUES (?,?,?,?,?,?,?)", o)
    conn.executemany(
        "INSERT INTO stg_supplier_deliveries VALUES (?,?,?,?,?,?,?,?)", d)
    return conn


# ── Registry mechanics ────────────────────────────────────────────────────────

def test_registry_versioning_and_deploy(tmp_path):
    reg = ModelRegistry(tmp_path, "demo")
    assert reg.versions() == []
    assert reg.current is None
    v1 = reg.new_version_dir()
    reg.deploy(v1.name)
    assert reg.current == "v0001"
    v2 = reg.new_version_dir()
    reg.deploy(v2.name)
    assert reg.current == "v0002"
    assert reg.versions() == ["v0001", "v0002"]


def test_registry_rollback(tmp_path):
    reg = ModelRegistry(tmp_path, "demo")
    reg.deploy(reg.new_version_dir().name)
    reg.deploy(reg.new_version_dir().name)
    assert reg.current == "v0002"
    assert reg.rollback() == "v0001"
    assert reg.current == "v0001"
    # nothing earlier to roll back to
    assert reg.rollback() is None
    # the rollback was logged
    events = [e.get("event") for e in reg.log_entries()]
    assert "rollback" in events


def test_registry_metrics_roundtrip(tmp_path):
    reg = ModelRegistry(tmp_path, "demo")
    v = reg.new_version_dir().name
    reg.write_metrics(v, {"wape": 0.21, "decision": "deployed"})
    assert reg.read_metrics(v)["wape"] == 0.21


# ── Retraining end-to-end ─────────────────────────────────────────────────────

def test_demand_retrain_end_to_end_deploys_first_model(tmp_path):
    from retraining.pipeline import retrain_demand

    conn = _orders_db()
    res = retrain_demand(conn, tmp_path)
    assert res["decision"] == "deployed"
    assert res["candidate_wape"] is not None
    reg = ModelRegistry(tmp_path, "demand")
    assert reg.current == res["version"]
    # decision logged with the data window
    log = reg.log_entries()
    assert any(e.get("decision") == "deployed" for e in log)
    assert "window" in res


def test_yield_retrain_end_to_end(tmp_path):
    from retraining.pipeline import retrain_yield

    conn = _orders_db()
    res = retrain_yield(conn, tmp_path)
    assert res["decision"] == "deployed"
    reg = ModelRegistry(tmp_path, "yield")
    assert reg.current is not None
    assert (reg.version_dir(reg.current) / "population.json").exists()


def test_gate_rejects_worse_candidate(tmp_path, monkeypatch):
    """A candidate scoring worse than the incumbent must NOT deploy."""
    from retraining import pipeline

    conn = _orders_db()
    first = pipeline.retrain_demand(conn, tmp_path)
    assert first["decision"] == "deployed"
    reg = ModelRegistry(tmp_path, "demand")
    deployed_before = reg.current

    # Sabotage the candidate scorer: pretend the new fit is much worse.
    real_score = pipeline._score_demand_point_forecasts
    calls = {"n": 0}

    def biased_score(point, holdout):
        calls["n"] += 1
        v = real_score(point, holdout)
        # first call scores the CANDIDATE in this run — inflate it
        return (v + 10.0) if calls["n"] == 1 and v is not None else v

    monkeypatch.setattr(pipeline, "_score_demand_point_forecasts",
                        biased_score)
    second = pipeline.retrain_demand(conn, tmp_path)
    assert second["decision"] == "rejected"
    assert reg.current == deployed_before  # incumbent kept


def test_retrain_skips_on_insufficient_history(tmp_path):
    from retraining.pipeline import retrain_demand

    conn = _orders_db(weeks=6)
    res = retrain_demand(conn, tmp_path)
    assert res["decision"] == "skipped"


def test_retrain_all_runs_both_families(tmp_path):
    from retraining.pipeline import retrain_all

    conn = _orders_db()
    res = retrain_all(conn, tmp_path)
    assert set(res) == {"demand", "yield"}


# ── Pooling hook ──────────────────────────────────────────────────────────────

def test_global_prior_refuses_single_operator():
    from retraining.pooling import global_prior
    from risk.supplier_distribution import Population

    p = Population(mean=0.9, pooled_variance=0.01, within_variance=0.005,
                   kappa=4.0, n_deliveries=50, n_suppliers=5,
                   method="empirical_bayes")
    assert global_prior([p]) is None


def test_global_prior_pools_two_operators():
    from retraining.pooling import global_prior
    from risk.supplier_distribution import Population

    a = Population(mean=0.90, pooled_variance=0.01, within_variance=0.005,
                   kappa=4.0, n_deliveries=100, n_suppliers=10,
                   method="empirical_bayes")
    b = Population(mean=0.80, pooled_variance=0.02, within_variance=0.01,
                   kappa=6.0, n_deliveries=300, n_suppliers=20,
                   method="empirical_bayes")
    g = global_prior([a, b])
    assert g is not None
    assert g.method == "global_pooled"
    # weighted toward the operator with more evidence
    assert g.mean == pytest.approx((0.90 * 100 + 0.80 * 300) / 400)
    assert g.n_suppliers == 30
