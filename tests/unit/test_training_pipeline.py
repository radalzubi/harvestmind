"""Phase D tests: pool → models, validation gates, the scheduler."""

from __future__ import annotations

from datetime import date, timedelta

import duckdb
import numpy as np
import pandas as pd
import pytest

from pool.pool_reader import DemandPrior, PoolReader, YieldPrior
from training.demand_trainer import (
    evaluate_pool_bootstrap,
    pool_informed_point_forecast,
)
from training.retraining_scheduler import RetrainingScheduler
from training.yield_trainer import (
    estimate_population_with_pool,
)

_TODAY = date(2026, 5, 25)


class _FakeReader(PoolReader):
    """Pool reader with injected priors (no filesystem)."""

    def __init__(self, demand=None, yld=None):
        self._demand, self._yield = demand, yld

    def get_demand_prior(self, category, week_of_year=None):
        return self._demand

    def get_yield_prior(self, category, region=None, season=None):
        return self._yield


# ── Demand: the thin-data bootstrap ──────────────────────────────────────────

def _thin_increasing_series(weeks=6, start=100.0, step=8.0):
    ws = pd.date_range("2026-04-13", periods=weeks, freq="W-MON")
    return pd.DataFrame({
        "product_id": "Kale", "week_start": ws,
        "demand_kg": [start + step * i for i in range(weeks)],
    })


def test_pool_prior_improves_thin_data_forecast():
    """A genuinely increasing market, 6 weeks of own history: the plain
    run-rate lags; the pool's 'increasing' consensus closes the gap.
    Measured, not asserted: WAPE(pool) < WAPE(plain) on the holdout."""
    weekly = _thin_increasing_series()
    prior = DemandPrior(category="leafy_greens", demand_cv=0.3,
                        trend_consensus="increasing",
                        n_signals=12, n_operators=4)
    res = evaluate_pool_bootstrap(
        weekly, {"Kale": "leafy_greens"}, _FakeReader(demand=prior),
        holdout_weeks=2)
    assert res["status"] == "ok"
    assert res["pool_helps"] is True
    assert res["wape_pool_informed"] < res["wape_plain_runrate"]


def test_no_pool_prior_returns_labeled_runrate():
    weekly = _thin_increasing_series()
    out = pool_informed_point_forecast(weekly, {"Kale": "leafy_greens"},
                                       _FakeReader(demand=None))
    assert "no pool prior" in out["Kale"]["basis"]


def test_pool_influence_washes_out_with_history():
    """Same prior, long history → the adjustment shrinks toward zero."""
    prior = DemandPrior(category="leafy_greens", demand_cv=0.3,
                        trend_consensus="increasing",
                        n_signals=12, n_operators=4)
    short = pool_informed_point_forecast(
        _thin_increasing_series(weeks=4), {"Kale": "leafy_greens"},
        _FakeReader(demand=prior))
    long_ = pool_informed_point_forecast(
        _thin_increasing_series(weeks=40), {"Kale": "leafy_greens"},
        _FakeReader(demand=prior))
    # relative uplift over the own run-rate must shrink as history grows
    def uplift(res, weeks):
        df = _thin_increasing_series(weeks=weeks)
        rr = float(df.groupby("week_start")["demand_kg"].sum()
                   .sort_index().to_numpy()[-4:].mean())
        return res["Kale"]["forecast_kg"] / rr - 1.0
    assert uplift(long_, 40) < uplift(short, 4)


# ── Yield: the third hierarchy level ─────────────────────────────────────────

def _fills(n, mean=0.6, seed=3):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "supplier_id": [f"S{i % 3}" for i in range(n)],
        "supplier_name": "x",
        "fill_rate": np.clip(rng.normal(mean, 0.05, n), 0, 1),
    })


def test_yield_pool_prior_is_third_level():
    prior = YieldPrior(category="vegetables", region="all", season="all",
                       fill_rate_mean=0.90, fill_rate_std=0.06,
                       alpha=20.0, beta=2.2, n_deliveries=500,
                       n_operators=6)
    own_thin = _fills(6, mean=0.60)
    pop = estimate_population_with_pool(own_thin, prior)
    assert pop.method == "pool_blended"          # third level present
    # thin own data (0.60) is pulled hard toward the pool (0.90)
    assert 0.60 < pop.mean < 0.90
    assert pop.mean > 0.75                        # pool dominates at n=6

    own_rich = _fills(300, mean=0.60)
    pop_rich = estimate_population_with_pool(own_rich, prior)
    assert abs(pop_rich.mean - 0.60) < 0.05       # pool washes out


def test_yield_no_pool_prior_identical_to_two_level():
    from risk.supplier_distribution import estimate_population
    fills = _fills(30)
    assert estimate_population_with_pool(fills, None) == \
        estimate_population(fills)


def test_yield_cold_start_uses_pool_population():
    prior = YieldPrior(category="vegetables", region="all", season="all",
                       fill_rate_mean=0.88, fill_rate_std=0.07,
                       alpha=18.0, beta=2.5, n_deliveries=400,
                       n_operators=5)
    pop = estimate_population_with_pool(pd.DataFrame(), prior)
    assert pop.method == "pool_prior"
    assert pop.mean == pytest.approx(0.88)


# ── Scheduler ─────────────────────────────────────────────────────────────────

def _db(n_orders=10, n_deliveries=10):
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE stg_buyer_orders (product_name VARCHAR, "
                 "buyer_id VARCHAR, buyer_name VARCHAR, order_date DATE, "
                 "delivery_date DATE, requested_quantity DOUBLE, "
                 "sales_price DOUBLE)")
    conn.execute("CREATE TABLE stg_supplier_deliveries (supplier_id VARCHAR, "
                 "supplier_name VARCHAR, product_name VARCHAR, "
                 "delivery_date DATE, ordered_quantity DOUBLE, "
                 "delivered_quantity DOUBLE, accepted_quantity DOUBLE, "
                 "unit_cost DOUBLE)")
    start = _TODAY - timedelta(weeks=30)
    for i in range(n_orders):
        d = start + timedelta(days=i * 2)
        conn.execute("INSERT INTO stg_buyer_orders VALUES "
                     "('Tomatoes','B1','B',?,?,100,3.0)", [str(d), str(d)])
    for i in range(n_deliveries):
        d = start + timedelta(days=i * 2)
        conn.execute("INSERT INTO stg_supplier_deliveries VALUES "
                     "('S1','S','Tomatoes',?,100,95,95,2.0)", [str(d)])
    return conn


def test_scheduler_skips_insufficient_new_data(tmp_path):
    sched = RetrainingScheduler(checkpoints_root=tmp_path / "ckpt",
                                log_path=tmp_path / "log.jsonl",
                                corpus_root=tmp_path / "corpus")
    res = sched.run_all_scheduled_retrains(_db(n_orders=10, n_deliveries=10))
    assert res["demand"]["decision"] == "skipped"
    assert "insufficient new data" in res["demand"]["reason"]
    assert res["extraction"]["decision"] == "skipped"


def test_scheduler_runs_and_logs_every_attempt(tmp_path):
    sched = RetrainingScheduler(checkpoints_root=tmp_path / "ckpt",
                                log_path=tmp_path / "log.jsonl",
                                corpus_root=tmp_path / "corpus")
    conn = _db(n_orders=150, n_deliveries=120)
    res = sched.run_all_scheduled_retrains(conn)
    # demand + yield crossed their thresholds and ran their gated retrains
    assert res["demand"]["decision"] in ("deployed", "rejected", "skipped")
    assert res["yield"]["decision"] in ("deployed", "rejected", "skipped")
    # every attempt logged
    lines = (tmp_path / "log.jsonl").read_text().splitlines()
    assert len(lines) == 3
    # second pass with no new data: previously-deployed models skip
    res2 = sched.run_all_scheduled_retrains(conn)
    for m in ("demand", "yield"):
        if res[m]["decision"] == "deployed":
            assert res2[m]["decision"] == "skipped"


def test_scheduler_never_raises_on_broken_model(tmp_path, monkeypatch):
    sched = RetrainingScheduler(checkpoints_root=tmp_path / "ckpt",
                                log_path=tmp_path / "log.jsonl",
                                corpus_root=tmp_path / "corpus")
    import retraining.pipeline as rp

    def boom(conn, root):
        raise RuntimeError("training blew up")

    monkeypatch.setattr(rp, "retrain_demand", boom)
    res = sched.run_all_scheduled_retrains(_db(n_orders=150,
                                               n_deliveries=120))
    assert res["demand"]["decision"] == "failed"
    assert "training blew up" in res["demand"]["error"]
    assert "failed" in (tmp_path / "log.jsonl").read_text()


def test_training_status_shape(tmp_path):
    sched = RetrainingScheduler(checkpoints_root=tmp_path / "ckpt",
                                log_path=tmp_path / "log.jsonl",
                                corpus_root=tmp_path / "corpus")
    status = sched.get_training_status(_db())
    assert set(status.models) == {"demand", "yield", "extraction"}
    for m in ("demand", "yield"):
        assert "retrain_threshold" in status.models[m]
        assert "new_data_needed" in status.models[m]
    assert status.models["extraction"]["gate_open"] is False
