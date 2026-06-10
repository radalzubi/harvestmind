"""Phase 4 tests: two-sided SP, constraints, benchmark suite, SAA gap.

Includes the permanent no-double-count regression guard: under the
newsvendor objective the SP must commit at the critical-ratio quantile of
the demand scenarios — not collapse to zero (the old procurement
double-count) and not blanket-cover demand (the old flat penalties).
"""

from __future__ import annotations

from datetime import date, timedelta

import duckdb
import numpy as np
import pandas as pd
import pytest

from optimization.two_stage_sp import TwoStageStochasticLP

_TODAY = date(2026, 5, 25)


def _scen(demands: list[float], product="A") -> pd.DataFrame:
    n = len(demands)
    return pd.DataFrame([
        {"scenario_index": k, "scenario_weight": 1.0 / n,
         "product_id": product, "week_start": "2026-06-01",
         "demand_kg": d}
        for k, d in enumerate(demands)
    ])


def _supply(capacity=10_000.0, price=2.0, suppliers=("s1",), product="A"):
    return pd.DataFrame([
        {"supplier_id": s, "product_id": product, "week_start": "2026-06-01",
         "capacity_kg": capacity, "price_per_kg": price}
        for s in suppliers
    ])


# ── Two-sided yield coefficients ─────────────────────────────────────────────

def test_yield_scenarios_make_sp_overcommit_to_cover_shortfall():
    """Single supplier always fills 50%: to deliver 100 the SP must commit
    ~200 when unmet is expensive (the fill enters the balance)."""
    scen = _scen([100.0, 100.0])
    sup = _supply()
    yields = {(0, "s1"): 0.5, (1, "s1"): 0.5}
    res = TwoStageStochasticLP(
        newsvendor_objective=True,
        waste_cost_by_product={"A": 0.5},
        unmet_cost_by_product={"A": 5.0},   # unmet very expensive
        spot_capacity_factor=0.0,           # no spot escape hatch
        n_scenarios=2,
    ).solve(scen, sup, yield_scenarios=yields)
    commit = sum(v for v in res["x"].values() if v)
    assert commit == pytest.approx(200.0, rel=0.05)


def test_no_yield_scenarios_reproduces_one_sided_model():
    scen = _scen([100.0, 100.0])
    sup = _supply()
    base = TwoStageStochasticLP(
        newsvendor_objective=True,
        waste_cost_by_product={"A": 0.5},
        unmet_cost_by_product={"A": 5.0},
        spot_capacity_factor=0.0, n_scenarios=2,
    )
    r1 = base.solve(scen, sup)
    r2 = base.solve(scen, sup, yield_scenarios={(0, "s1"): 1.0, (1, "s1"): 1.0})
    c1 = sum(v for v in r1["x"].values() if v)
    c2 = sum(v for v in r2["x"].values() if v)
    assert c1 == pytest.approx(c2, rel=1e-6)


# ── No-double-count regression (the Phase 0.9 proof, made permanent) ─────────

def test_newsvendor_sp_commits_at_critical_ratio_quantile():
    """cw=2 (cost), cu=1 (margin) → q* = cu/(cu+cw) = 1/3. With demand
    scenarios uniform on {60..150}, the optimal commit is the q* quantile —
    NOT zero (double-count collapse) and NOT the max (full coverage)."""
    demands = list(np.linspace(60, 150, 10))
    scen = _scen(demands)
    sup = _supply()
    res = TwoStageStochasticLP(
        newsvendor_objective=True,
        waste_cost_by_product={"A": 2.0},
        unmet_cost_by_product={"A": 1.0},
        spot_capacity_factor=0.0,
        n_scenarios=10,
    ).solve(scen, sup)
    commit = sum(v for v in res["x"].values() if v)
    qstar = np.quantile(demands, 1.0 / 3.0)
    assert commit == pytest.approx(qstar, rel=0.10)
    assert commit > min(demands) * 0.5      # not zero-collapse
    assert commit < max(demands) * 0.99     # not full coverage


# ── Operator constraints ─────────────────────────────────────────────────────

def test_service_level_floor_limits_unmet():
    """cw >> cu would normally leave demand unmet; the floor forces
    expected unmet ≤ (1−floor) × expected demand."""
    scen = _scen([100.0, 120.0])
    sup = _supply()
    res = TwoStageStochasticLP(
        newsvendor_objective=True,
        waste_cost_by_product={"A": 5.0},
        unmet_cost_by_product={"A": 0.1},   # unmet nearly free → commit little
        spot_capacity_factor=0.0,
        service_level_floor=0.95,
        n_scenarios=2,
    ).solve(scen, sup)
    exp_unmet = res["expected_unmet_kg"]
    exp_demand = 110.0
    assert exp_unmet <= (1 - 0.95) * exp_demand + 1e-6


def test_diversification_cap_limits_supplier_share():
    scen = _scen([100.0, 100.0])
    sup = _supply(suppliers=("s1", "s2"), price=2.0)
    # make s1 cheaper so unconstrained it would take everything
    sup.loc[sup["supplier_id"] == "s1", "price_per_kg"] = 1.0
    res = TwoStageStochasticLP(
        newsvendor_objective=True,
        waste_cost_by_product={"A": 0.5},
        unmet_cost_by_product={"A": 5.0},
        spot_capacity_factor=0.0,
        diversification_cap=0.60,
        n_scenarios=2,
    ).solve(scen, sup)
    commits = {i: v for (i, j), v in res["x"].items() if v and v > 1e-6}
    total = sum(commits.values())
    assert total > 0
    for v in commits.values():
        assert v <= 0.60 * total + 1e-6


def test_diversification_cap_skipped_for_single_supplier():
    """A sole-supplier product must NOT be zeroed by the cap."""
    scen = _scen([100.0, 100.0])
    sup = _supply(suppliers=("s1",))
    res = TwoStageStochasticLP(
        newsvendor_objective=True,
        waste_cost_by_product={"A": 0.5},
        unmet_cost_by_product={"A": 5.0},
        spot_capacity_factor=0.0,
        diversification_cap=0.40,   # infeasible for one supplier — skip it
        n_scenarios=2,
    ).solve(scen, sup)
    commit = sum(v for v in res["x"].values() if v)
    assert commit > 50.0


# ── Order-up-to baseline ─────────────────────────────────────────────────────

def test_order_up_to_math():
    from optimization.order_up_to_policy import order_up_to_commitments
    from scipy import stats

    weeks = pd.date_range("2026-01-05", periods=13, freq="W-MON")
    rng = np.random.default_rng(3)
    vals = rng.normal(100, 10, size=13)
    df = pd.DataFrame({"product_id": "P", "week_start": weeks,
                       "demand_kg": vals})
    s = order_up_to_commitments(df, service_level=0.90)
    z = stats.norm.ppf(0.90)
    expected = vals.mean() + z * vals.std(ddof=1)
    assert s["P"] == pytest.approx(expected, rel=1e-6)


# ── Benchmark suite contract ─────────────────────────────────────────────────

def _staging_db(weeks=36, seed=5):
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
    o_rows, d_rows = [], []
    for w in range(weeks):
        d = start + timedelta(weeks=w)
        for p, base in (("Tomatoes", 400.0), ("Kale", 150.0)):
            qty = max(base + rng.normal(0, base * 0.15), 10)
            o_rows.append(("B1", "Buyer", p, str(d), str(d), qty, 3.0))
            for s in ("S1", "S2"):
                ordered = qty * 0.6
                fill = float(np.clip(rng.beta(18, 2), 0, 1))
                d_rows.append((s, s, p, str(d), ordered,
                               ordered * fill, ordered * fill, 2.0))
    conn.executemany("INSERT INTO stg_buyer_orders VALUES (?,?,?,?,?,?,?)", o_rows)
    conn.executemany(
        "INSERT INTO stg_supplier_deliveries VALUES (?,?,?,?,?,?,?,?)", d_rows)
    return conn


def test_benchmark_contract_and_gate_reporting():
    from backtesting.benchmark_suite import run_benchmark

    conn = _staging_db()
    res = run_benchmark(conn, n_folds=2, train_weeks=26)
    assert res["status"] == "ok"
    for pol in ("two_sided_sp", "deterministic_lp", "order_up_to",
                "naive_runrate"):
        assert pol in res["policies"]
        assert "cost_per_origin" in res["policies"][pol]
    assert isinstance(res["gate_passed"], bool)
    assert "verdict" in res
    # the unflattering verdict must exist as a code path, not just prose
    if not res["gate_passed"]:
        assert "HONEST VERDICT" in res["verdict"]
    assert "sensitive" in res["spot_economics"]["note"]


def test_benchmark_insufficient_history_is_honest():
    from backtesting.benchmark_suite import run_benchmark

    conn = _staging_db(weeks=10)
    res = run_benchmark(conn, n_folds=4, train_weeks=26)
    assert res["status"] == "insufficient_history"
    assert res["gate_passed"] is None


def test_saa_gap_smoke():
    from backtesting.benchmark_suite import saa_optimality_gap

    conn = _staging_db()
    res = saa_optimality_gap(conn, n_batches=2, batch_size=10,
                             n_eval_scenarios=40)
    assert res["status"] == "ok"
    assert "gap" in res and "lower_bound" in res and "upper_bound" in res
    assert res["n_batches"] == 2
