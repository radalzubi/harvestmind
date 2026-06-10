"""Calibration tests for the supplier yield model (Phase 3 gate).

Covers: PIT/coverage math on data where the model SHOULD be calibrated
(Beta-distributed fills), the insufficient-history path, the continuity
of variance shrinkage across the old n=2→3 cliff, the cold-start path,
the volatility→wider-interval ordering, the service-linked quantile, and
the Tier-2 covariate admission harness.
"""

from __future__ import annotations

import duckdb
import numpy as np
import pytest
from scipy import stats

from risk.calibration import calibration_report, pit_values
from risk.supplier_distribution import (
    Population,
    estimate_population,
    service_linked_quantile,
    supplier_distribution,
)


def _db_with_beta_fills(n_suppliers=8, n_deliveries=30, seed=11):
    """Suppliers whose per-delivery fills genuinely follow supplier-level
    Beta distributions — the model's own assumption, so it should pass."""
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE stg_supplier_deliveries (
            supplier_id VARCHAR, supplier_name VARCHAR,
            product_name VARCHAR, delivery_date DATE,
            ordered_quantity DOUBLE, delivered_quantity DOUBLE,
            accepted_quantity DOUBLE, unit_cost DOUBLE
        )
    """)
    conn.execute("""
        CREATE TABLE stg_buyer_orders (
            product_name VARCHAR, requested_quantity DOUBLE,
            sales_price DOUBLE
        )
    """)
    rng = np.random.default_rng(seed)
    rows = []
    for s in range(n_suppliers):
        mean = rng.uniform(0.75, 0.97)
        conc = rng.uniform(20, 60)
        a, b = mean * conc, (1 - mean) * conc
        for d in range(n_deliveries):
            fill = float(np.clip(rng.beta(a, b), 0.01, 1.0))
            ordered = 100.0
            rows.append((f"S{s}", f"Supplier {s}", "Tomatoes",
                         f"2026-{(d % 12) + 1:02d}-{(d % 27) + 1:02d}",
                         ordered, ordered * fill, ordered * fill, 2.0))
    conn.executemany(
        "INSERT INTO stg_supplier_deliveries VALUES (?,?,?,?,?,?,?,?)", rows)
    return conn


# ── PIT / coverage gate ───────────────────────────────────────────────────────

def test_calibration_passes_on_model_consistent_data():
    """When fills truly come from supplier Betas, the model must be
    calibrated: 10–90 coverage ≈ 80% and PIT ≈ uniform."""
    conn = _db_with_beta_fills()
    rep = calibration_report(conn)
    assert rep["status"] == "ok"
    assert rep["n_held_out"] >= 200
    assert 0.70 <= rep["coverage_10_90"] <= 0.90
    assert rep["ks_statistic"] <= 0.15
    assert rep["gate_passed"] is True


def test_calibration_insufficient_history_is_honest():
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE stg_supplier_deliveries ("
                 "supplier_id VARCHAR, supplier_name VARCHAR, "
                 "ordered_quantity DOUBLE, delivered_quantity DOUBLE, "
                 "accepted_quantity DOUBLE)")
    rep = calibration_report(conn)
    assert rep["status"] == "insufficient_history"
    assert rep["gate_passed"] is None


def test_pit_values_in_unit_interval():
    conn = _db_with_beta_fills(n_suppliers=3, n_deliveries=10)
    pits = pit_values(conn)
    assert len(pits) == 30
    assert (pits >= 0).all() and (pits <= 1).all()


def test_calibration_report_exposes_failure_numbers():
    """The payload must carry the raw numbers whatever the verdict."""
    conn = _db_with_beta_fills(n_suppliers=4, n_deliveries=12)
    rep = calibration_report(conn)
    for key in ("coverage_10_90", "ks_statistic", "pit_histogram",
                "gate_rule"):
        assert key in rep


# ── Continuity across the old n=3 variance cliff ─────────────────────────────

def test_variance_shrinkage_continuous_across_n2_to_n3():
    """The old rule used the population variance at n=2 and the supplier's
    own variance at n=3 — a cliff. The blended rule must move smoothly:
    the n=2 and n=3 downside quantiles must be close when the underlying
    statistics are identical."""
    pop = Population(mean=0.85, pooled_variance=0.02, within_variance=0.01,
                     kappa=4.0, n_deliveries=100, n_suppliers=10,
                     method="empirical_bayes")
    own_var = 0.002  # much steadier than the population
    d2 = supplier_distribution(2, 0.85, own_var, pop, 0.10)
    d3 = supplier_distribution(3, 0.85, own_var, pop, 0.10)
    # Under the old cliff rule the gap was the full pop-vs-own variance
    # jump; blended, one extra delivery moves the downside only slightly.
    assert abs(d3["downside"] - d2["downside"]) < 0.02


def test_more_data_trusts_own_variance_more():
    pop = Population(mean=0.85, pooled_variance=0.02, within_variance=0.01,
                     kappa=4.0, n_deliveries=100, n_suppliers=10,
                     method="empirical_bayes")
    own_var = 0.001  # very steady supplier
    downsides = [supplier_distribution(n, 0.85, own_var, pop, 0.10)["downside"]
                 for n in (2, 5, 20, 100)]
    # As n grows the blend approaches the steadier own variance, so the
    # downside rises monotonically toward the mean.
    assert downsides == sorted(downsides)


def test_cold_start_uses_population():
    pop = Population(mean=0.85, pooled_variance=0.02, within_variance=0.01,
                     kappa=4.0, n_deliveries=100, n_suppliers=10,
                     method="empirical_bayes")
    d = supplier_distribution(0, None, None, pop, 0.10)
    assert d["mean"] == pytest.approx(0.85)
    # cold start carries the FULL pooled spread, so its downside is the
    # widest of any supplier with the same mean
    d_known = supplier_distribution(10, 0.85, 0.005, pop, 0.10)
    assert d["downside"] <= d_known["downside"]


def test_volatile_supplier_has_wider_interval():
    pop = Population(mean=0.85, pooled_variance=0.02, within_variance=0.01,
                     kappa=4.0, n_deliveries=100, n_suppliers=10,
                     method="empirical_bayes")
    steady = supplier_distribution(20, 0.85, 0.001, pop, 0.10)
    swingy = supplier_distribution(20, 0.85, 0.030, pop, 0.10)
    assert swingy["downside"] < steady["downside"]


# ── Service-linked quantile ───────────────────────────────────────────────────

def test_service_quantile_derived_from_costs():
    conn = _db_with_beta_fills(n_suppliers=2, n_deliveries=5)
    conn.execute("INSERT INTO stg_buyer_orders VALUES ('Tomatoes', 100, 3.6)")
    # avg cost 2.0, avg price 3.6 → margin 1.6, premium 0.6 → q* = 0.6/2.2
    q = service_linked_quantile(conn, spot_cost_multiplier=1.30)
    assert q == pytest.approx(0.6 / 2.2, abs=1e-6)


def test_service_quantile_falls_back_without_prices():
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE stg_supplier_deliveries (unit_cost DOUBLE)")
    conn.execute("CREATE TABLE stg_buyer_orders (sales_price DOUBLE)")
    assert service_linked_quantile(conn) == pytest.approx(0.10)


def test_service_quantile_clamped_to_planning_band():
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE stg_supplier_deliveries (unit_cost DOUBLE)")
    conn.execute("CREATE TABLE stg_buyer_orders (sales_price DOUBLE)")
    conn.execute("INSERT INTO stg_supplier_deliveries VALUES (2.0)")
    conn.execute("INSERT INTO stg_buyer_orders VALUES (2.0)")  # zero margin
    q = service_linked_quantile(conn)
    assert q <= 0.50  # never plan past the median


# ── Tier-2 covariate admission ────────────────────────────────────────────────

def test_weather_signal_not_admitted_without_data():
    """No weather observations → the signal must be rejected with the
    reason stated, never admitted on faith."""
    from risk.yield_covariates import admit_weather_signal

    conn = _db_with_beta_fills(n_suppliers=3, n_deliveries=10)
    res = admit_weather_signal(conn)
    assert res["admitted"] is False
    assert "not admitted on faith" in res["reason"] or "no weather" in res["reason"]


def test_covariate_status_lists_policy():
    from risk.yield_covariates import covariate_status

    conn = _db_with_beta_fills(n_suppliers=3, n_deliveries=10)
    st = covariate_status(conn)
    assert st["signals"][0]["signal"] == "weather_heat_stress"
    assert "measured" in st["policy"]
