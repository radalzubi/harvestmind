"""Unit tests for risk/supplier_distribution.py.

The headline claim of the hierarchical model is that two suppliers with the
same mean fill rate but different delivery-to-delivery volatility get
different downside quantiles. The seed data is engineered to exercise exactly
that, plus shrinkage of thin-data suppliers and the cold-start path.

In-memory DuckDB, deterministic seed, no randomness.
"""

from __future__ import annotations

import duckdb
import pytest


@pytest.fixture(scope="module")
def dist_db():
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE stg_supplier_deliveries (
            delivery_id VARCHAR, supplier_id VARCHAR, supplier_name VARCHAR,
            product_id VARCHAR, product_name VARCHAR, delivery_date DATE,
            ordered_quantity DOUBLE, delivered_quantity DOUBLE,
            accepted_quantity DOUBLE, rejected_quantity DOUBLE,
            unit_cost DOUBLE, quality_grade VARCHAR, lot_id VARCHAR
        )
    """)

    rows = []

    def add(sid, sname, ordered, accepted, i):
        rows.append((f"{sid}-{i}", sid, sname, "P1", "Tomatoes", "2026-05-01",
                     float(ordered), float(accepted), float(accepted), 0.0,
                     1.0, "A", f"LOT-{sid}-{i}"))

    # STEADY: mean ~0.85, very low variance, 8 deliveries
    for i, acc in enumerate([84, 85, 86, 85, 84, 86, 85, 85]):
        add("S-STEADY", "Steady Farms", 100, acc, i)

    # VOLATILE: mean ~0.85, high variance, 8 deliveries (same mean as STEADY)
    for i, acc in enumerate([70, 100, 72, 99, 71, 100, 70, 98]):
        add("S-VOLATILE", "Swingy Produce", 100, acc, i)

    # THIN: only 2 deliveries, high fill — should shrink toward population
    for i, acc in enumerate([96, 98]):
        add("S-THIN", "New Supplier", 100, acc, i)

    # RICH: 10 deliveries, consistently high — should barely shrink
    for i, acc in enumerate([97, 96, 98, 97, 97, 96, 98, 97, 97, 96]):
        add("S-RICH", "Reliable Co", 100, acc, i)

    conn.executemany("""
        INSERT INTO stg_supplier_deliveries
            (delivery_id, supplier_id, supplier_name, product_id, product_name,
             delivery_date, ordered_quantity, delivered_quantity,
             accepted_quantity, rejected_quantity, unit_cost, quality_grade, lot_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def empty_db():
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE stg_supplier_deliveries (
            delivery_id VARCHAR, supplier_id VARCHAR, supplier_name VARCHAR,
            product_id VARCHAR, product_name VARCHAR, delivery_date DATE,
            ordered_quantity DOUBLE, delivered_quantity DOUBLE,
            accepted_quantity DOUBLE, rejected_quantity DOUBLE,
            unit_cost DOUBLE, quality_grade VARCHAR, lot_id VARCHAR
        )
    """)
    yield conn
    conn.close()


# ── The headline claim: volatility separates suppliers at equal mean ──────────

def test_volatility_lowers_downside_at_equal_mean(dist_db):
    from risk.supplier_distribution import supplier_fill_distributions

    d = supplier_fill_distributions(dist_db, quantile=0.10)
    steady = d["S-STEADY"]
    volatile = d["S-VOLATILE"]

    # Means are close (both seeded to ~0.85).
    assert abs(steady["posterior_mean"] - volatile["posterior_mean"]) < 0.05

    # But the volatile supplier has a materially lower downside quantile.
    assert volatile["downside"] < steady["downside"]
    assert volatile["spread"] > steady["spread"]


def test_observed_means_are_close_but_variance_differs(dist_db):
    from risk.supplier_distribution import supplier_fill_distributions

    d = supplier_fill_distributions(dist_db, quantile=0.10)
    assert abs(d["S-STEADY"]["observed_mean"] - d["S-VOLATILE"]["observed_mean"]) < 0.03
    assert d["S-VOLATILE"]["observed_std"] > d["S-STEADY"]["observed_std"]


# ── Shrinkage ─────────────────────────────────────────────────────────────────

def test_thin_supplier_shrinks_more_than_rich(dist_db):
    from risk.supplier_distribution import supplier_fill_distributions

    d = supplier_fill_distributions(dist_db, quantile=0.10)
    # Thin supplier (2 deliveries) carries more population weight than the
    # data-rich one (10 deliveries).
    assert d["S-THIN"]["shrinkage"] > d["S-RICH"]["shrinkage"]


def test_thin_supplier_mean_pulled_toward_population(dist_db):
    from risk.supplier_distribution import supplier_fill_distributions

    d = supplier_fill_distributions(dist_db, quantile=0.10)
    thin = d["S-THIN"]
    pop_mean = d["_prior"]["mean"]
    # The shrunk mean sits between the supplier's raw mean and the population.
    lo, hi = sorted([thin["observed_mean"], pop_mean])
    assert lo - 1e-9 <= thin["posterior_mean"] <= hi + 1e-9
    # And it is strictly pulled off the raw observation toward the population.
    assert thin["posterior_mean"] < thin["observed_mean"]


# ── Downside is a lower-tail quantile ─────────────────────────────────────────

def test_downside_below_mean_for_all(dist_db):
    from risk.supplier_distribution import supplier_fill_distributions

    d = supplier_fill_distributions(dist_db, quantile=0.10)
    for sid, info in d.items():
        if sid == "_prior":
            continue
        assert info["downside"] <= info["posterior_mean"] + 1e-9


def test_lower_quantile_gives_lower_downside(dist_db):
    from risk.supplier_distribution import supplier_fill_distributions

    d5 = supplier_fill_distributions(dist_db, quantile=0.05)
    d20 = supplier_fill_distributions(dist_db, quantile=0.20)
    # A more conservative quantile (5th) is below a less conservative one (20th).
    assert d5["S-VOLATILE"]["downside"] < d20["S-VOLATILE"]["downside"]


# ── Cold start ────────────────────────────────────────────────────────────────

def test_cold_start_returns_population(dist_db):
    from risk.supplier_distribution import (
        supplier_fill_distributions, estimate_population, supplier_distribution,
        _delivery_fill_rates,
    )

    pop = estimate_population(_delivery_fill_rates(dist_db))
    cold = supplier_distribution(0, None, None, pop, quantile=0.10)
    # A supplier with no deliveries gets the population mean back.
    assert abs(cold["mean"] - pop.mean) < 1e-9


# ── Prior diagnostics + empty path ────────────────────────────────────────────

def test_prior_method_is_empirical_bayes_with_spread(dist_db):
    from risk.supplier_distribution import supplier_fill_distributions

    d = supplier_fill_distributions(dist_db, quantile=0.10)
    assert d["_prior"]["method"] == "empirical_bayes"
    assert d["_prior"]["n_suppliers"] == 4
    assert d["_prior"]["kappa"] > 0


def test_empty_returns_only_prior(empty_db):
    from risk.supplier_distribution import supplier_fill_distributions

    d = supplier_fill_distributions(empty_db, quantile=0.10)
    assert set(d.keys()) == {"_prior"}
    assert d["_prior"]["method"] == "fallback"
