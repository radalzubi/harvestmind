"""Edge-case tests for under-tested risk-modeling code.

Targets:
  - risk/yield_covariates.py     (seasonal/regional heat-stress adjustment)
  - risk/scenario_generation.py  (yield_scenarios_from_distributions)
  - risk/shelf_life.py           (decay-weight edge cases, zero/negative buffer)
  - risk/confidence.py           (interval / index helpers)
  - risk/calibration.py          (cold start, thin data, Beta validity)

All tests use in-memory DuckDB with deterministic seeds. No network.

Probes (per prior audit):
  - a suspected NaN-downside path in supplier_distribution (cold start with a
    wide pooled spread, and degenerate population variance);
  - a zero/negative-buffer edge in shelf_life.shelf_life_weight.
"""

from __future__ import annotations

import math
from datetime import date

import duckdb
import numpy as np
import pytest

from risk.calibration import calibration_report, pit_values
from risk.confidence import recommendation_confidence
from risk.scenario_generation import yield_scenarios_from_distributions
from risk.shelf_life import shelf_life_weight, weighted_available_by_product
from risk.supplier_distribution import (
    Population,
    estimate_population,
    supplier_distribution,
    supplier_fill_distributions,
)


# ──────────────────────────────────────────────────────────────────────────────
# Shared DuckDB fixtures
# ──────────────────────────────────────────────────────────────────────────────

_DELIVERIES_DDL = """
    CREATE TABLE stg_supplier_deliveries (
        delivery_id VARCHAR, supplier_id VARCHAR, supplier_name VARCHAR,
        product_id VARCHAR, product_name VARCHAR, delivery_date DATE,
        ordered_quantity DOUBLE, delivered_quantity DOUBLE,
        accepted_quantity DOUBLE, rejected_quantity DOUBLE,
        unit_cost DOUBLE, quality_grade VARCHAR, lot_id VARCHAR
    )
"""

_ORDERS_DDL = """
    CREATE TABLE stg_buyer_orders (
        order_id VARCHAR, buyer_id VARCHAR, buyer_name VARCHAR,
        product_id VARCHAR, product_name VARCHAR, order_date DATE,
        delivery_date DATE, requested_quantity DOUBLE, fulfilled_quantity DOUBLE,
        substituted_quantity DOUBLE, sales_price DOUBLE,
        required_quality_grade VARCHAR
    )
"""

_INSERT_DELIVERY = """
    INSERT INTO stg_supplier_deliveries
        (delivery_id, supplier_id, supplier_name, product_id, product_name,
         delivery_date, ordered_quantity, delivered_quantity,
         accepted_quantity, rejected_quantity, unit_cost, quality_grade, lot_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def _make_delivery_db(supplier_specs):
    """Build a deliveries DB. ``supplier_specs`` maps supplier_id -> list of
    accepted quantities (ordered fixed at 100, so fill = accepted/100)."""
    conn = duckdb.connect(":memory:")
    conn.execute(_DELIVERIES_DDL)
    rows = []
    for sid, accepted_list in supplier_specs.items():
        for i, acc in enumerate(accepted_list):
            rows.append((f"{sid}-{i}", sid, f"Name {sid}", "P1", "Tomatoes",
                         "2026-05-01", 100.0, float(acc), float(acc), 0.0,
                         1.0, "A", f"LOT-{sid}-{i}"))
    if rows:
        conn.executemany(_INSERT_DELIVERY, rows)
    return conn


@pytest.fixture()
def two_supplier_db():
    """One steady supplier, one volatile supplier, same mean ~0.85."""
    conn = _make_delivery_db({
        "S-STEADY": [84, 85, 86, 85, 84, 86, 85, 85],
        "S-VOLATILE": [70, 100, 72, 99, 71, 100, 70, 98],
    })
    yield conn
    conn.close()


def _make_weather_db(seed=7, heat_effect=-0.20):
    """Deliveries spread over many weeks plus a fact_weather_obs table whose
    heat-stress weeks genuinely depress fill rate by ``heat_effect``.

    Returns a DB suitable for risk.yield_covariates.admit_weather_signal.
    """
    conn = duckdb.connect(":memory:")
    conn.execute(_DELIVERIES_DDL)
    conn.execute("""
        CREATE TABLE fact_weather_obs (
            obs_id VARCHAR, station_id VARCHAR, obs_date DATE,
            tmax DOUBLE, tmin DOUBLE, precipitation DOUBLE,
            heat_stress_flag BOOLEAN
        )
    """)
    rng = np.random.default_rng(seed)

    delivery_rows = []
    weather_rows = []
    # 24 distinct weeks; even weeks are heat-stressed.
    for w in range(24):
        d = date(2026, 1, 1).toordinal() + w * 7
        obs_day = date.fromordinal(d)
        heat = (w % 2 == 0)
        weather_rows.append((f"W{w}", "ST1", obs_day.isoformat(),
                             35.0 if heat else 22.0, 18.0, 0.0, heat))
        base = 0.90 + (heat_effect if heat else 0.0)
        # two suppliers, a couple deliveries each per week
        for sid in ("S1", "S2"):
            for k in range(2):
                fr = float(np.clip(base + rng.normal(0, 0.02), 0.01, 1.0))
                acc = round(100.0 * fr, 2)
                delivery_rows.append(
                    (f"{sid}-{w}-{k}", sid, f"Name {sid}", "P1", "Tomatoes",
                     obs_day.isoformat(), 100.0, acc, acc, 0.0, 1.0, "A",
                     f"LOT-{sid}-{w}-{k}"))

    conn.executemany(_INSERT_DELIVERY, delivery_rows)
    conn.executemany("""
        INSERT INTO fact_weather_obs
            (obs_id, station_id, obs_date, tmax, tmin, precipitation, heat_stress_flag)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, weather_rows)
    return conn


def _db_with_beta_fills(n_suppliers=8, n_deliveries=30, seed=11):
    """Suppliers whose per-delivery fills genuinely follow supplier Betas."""
    conn = duckdb.connect(":memory:")
    conn.execute(_DELIVERIES_DDL)
    conn.execute(_ORDERS_DDL)
    rng = np.random.default_rng(seed)
    rows = []
    for s in range(n_suppliers):
        mean = rng.uniform(0.75, 0.97)
        conc = rng.uniform(20, 60)
        a, b = mean * conc, (1 - mean) * conc
        for d in range(n_deliveries):
            fill = float(np.clip(rng.beta(a, b), 0.01, 1.0))
            acc = round(100.0 * fill, 4)
            rows.append((f"S{s}-{d}", f"S{s}", f"Supplier {s}", "P1",
                         "Tomatoes", f"2026-{(d % 12) + 1:02d}-{(d % 27) + 1:02d}",
                         100.0, acc, acc, 0.0, 2.0, "A", f"LOT-{s}-{d}"))
    conn.executemany(_INSERT_DELIVERY, rows)
    return conn


# ──────────────────────────────────────────────────────────────────────────────
# yield_covariates: seasonal/regional adjustment is bounded & sane
# ──────────────────────────────────────────────────────────────────────────────

def test_weather_adjustment_measured_effect_is_bounded_and_negative():
    """The admitted adjustment (the measured heat-stress fill delta) must be
    a finite fill-rate difference in [-1, 1], and for a genuinely harmful heat
    effect it must be negative (stressed weeks fill worse than clear weeks)."""
    from risk.yield_covariates import admit_weather_signal

    conn = _make_weather_db(heat_effect=-0.20)
    res = admit_weather_signal(conn)
    conn.close()

    delta = res["measured_effect_delta_fill"]
    assert math.isfinite(delta)
    assert -1.0 <= delta <= 1.0
    # Heat depressed fills by ~0.20; the measured effect must reflect that sign.
    assert delta < 0.0
    assert delta == pytest.approx(-0.20, abs=0.07)


def test_weather_identity_no_seasonal_shift_is_near_zero():
    """Identity case: when stressed and clear weeks have the SAME fill rate,
    the measured seasonal adjustment must be ~0 (no spurious shift)."""
    from risk.yield_covariates import admit_weather_signal

    conn = _make_weather_db(heat_effect=0.0)  # heat has no real effect
    res = admit_weather_signal(conn)
    conn.close()

    # Either it reports a measured delta near zero, or it declines for lack of
    # signal — both are "no spurious adjustment". When measured, it must be ~0.
    if "measured_effect_delta_fill" in res:
        assert abs(res["measured_effect_delta_fill"]) < 0.05


def test_weather_signal_not_admitted_without_observations():
    """No fact_weather_obs rows loaded → never admitted on faith."""
    from risk.yield_covariates import admit_weather_signal

    conn = _make_delivery_db({"S1": [90, 85, 88, 92, 87, 91]})
    res = admit_weather_signal(conn)
    conn.close()
    assert res["admitted"] is False
    assert "reason" in res


def test_covariate_status_reports_coverage_band():
    from risk.yield_covariates import covariate_status

    conn = _make_weather_db(heat_effect=-0.15)
    st = covariate_status(conn)
    conn.close()
    assert st["signals"][0]["signal"] == "weather_heat_stress"
    band = st["coverage_band"]
    # Band is a sane 0..1 ordered interval bracketing the 0.80 target.
    assert len(band) == 2
    assert 0.0 <= band[0] < band[1] <= 1.0
    assert band[0] <= 0.80 <= band[1]


# ──────────────────────────────────────────────────────────────────────────────
# scenario_generation: yield_scenarios_from_distributions
# ──────────────────────────────────────────────────────────────────────────────

def test_yield_scenarios_shape_and_keys(two_supplier_db):
    scen = [0, 1, 2, 3]
    out = yield_scenarios_from_distributions(two_supplier_db, scen, seed=42)
    suppliers = {"S-STEADY", "S-VOLATILE"}
    # One draw per (scenario, supplier), and "_prior" is never a key.
    assert len(out) == len(scen) * len(suppliers)
    for (omega, sid), val in out.items():
        assert omega in scen
        assert sid in suppliers
    # Every requested scenario index is present for every supplier.
    for sid in suppliers:
        assert {omega for (omega, s) in out if s == sid} == set(scen)


def test_yield_scenarios_respect_scenario_indices(two_supplier_db):
    """Arbitrary (non-contiguous) scenario indices are carried through exactly."""
    scen = [5, 11, 99]
    out = yield_scenarios_from_distributions(two_supplier_db, scen, seed=1)
    omegas = {omega for (omega, _sid) in out}
    assert omegas == set(scen)


def test_yield_scenarios_samples_within_unit_interval(two_supplier_db):
    out = yield_scenarios_from_distributions(two_supplier_db, list(range(50)),
                                             seed=3)
    vals = list(out.values())
    assert all(0.0 <= v <= 1.0 for v in vals)
    assert all(math.isfinite(v) for v in vals)


def test_yield_scenarios_deterministic_under_fixed_seed(two_supplier_db):
    a = yield_scenarios_from_distributions(two_supplier_db, [0, 1, 2], seed=42)
    b = yield_scenarios_from_distributions(two_supplier_db, [0, 1, 2], seed=42)
    assert a == b


def test_yield_scenarios_differ_across_seeds(two_supplier_db):
    a = yield_scenarios_from_distributions(two_supplier_db, list(range(20)), seed=1)
    b = yield_scenarios_from_distributions(two_supplier_db, list(range(20)), seed=2)
    assert a != b


def test_yield_scenarios_empty_index_list(two_supplier_db):
    out = yield_scenarios_from_distributions(two_supplier_db, [], seed=42)
    assert out == {}


# ──────────────────────────────────────────────────────────────────────────────
# shelf_life: decay-weight edge cases incl. zero/negative buffer
# ──────────────────────────────────────────────────────────────────────────────

def test_weight_full_well_before_lead_time():
    # Remaining far exceeds lead + buffer → fully usable.
    assert shelf_life_weight(remaining_days=30, lead_time_days=3, buffer_days=4) == 1.0


def test_weight_zero_past_usable_window():
    # Remaining at or below lead time → expired before delivery.
    assert shelf_life_weight(remaining_days=3, lead_time_days=3, buffer_days=4) == 0.0
    assert shelf_life_weight(remaining_days=1, lead_time_days=3, buffer_days=4) == 0.0


def test_weight_monotonic_non_decreasing_in_remaining():
    weights = [shelf_life_weight(r, lead_time_days=4, buffer_days=6)
               for r in range(0, 20)]
    assert weights == sorted(weights)
    assert weights[0] == 0.0
    assert weights[-1] == 1.0
    # And the ramp segment is strictly increasing where it is partial.
    partial = [w for w in weights if 0.0 < w < 1.0]
    assert partial == sorted(partial)
    assert all(0.0 < w < 1.0 for w in partial)


def test_weight_ramp_is_linear_inside_buffer():
    # Lead 5, buffer 4: remaining 7 → (7-5)/4 = 0.5; remaining 6 → 0.25.
    assert shelf_life_weight(7, 5, 4) == pytest.approx(0.5)
    assert shelf_life_weight(6, 5, 4) == pytest.approx(0.25)


def test_weight_zero_buffer_is_hard_step():
    # B == 0: hard step at the lead time. Above lead → 1.0; at/below → 0.0.
    assert shelf_life_weight(remaining_days=4, lead_time_days=3, buffer_days=0) == 1.0
    assert shelf_life_weight(remaining_days=3, lead_time_days=3, buffer_days=0) == 0.0
    assert shelf_life_weight(remaining_days=2, lead_time_days=3, buffer_days=0) == 0.0


def test_weight_negative_buffer_collapses_to_step_and_stays_in_unit_interval():
    """A negative buffer must NOT produce a weight outside [0, 1] or a negative
    ramp. Past the lead time it collapses to the hard-step 1.0; at/below it is
    0.0. (Probes the zero/negative-buffer edge.)"""
    for B in (-1.0, -5.0):
        above = shelf_life_weight(remaining_days=10, lead_time_days=3, buffer_days=B)
        at = shelf_life_weight(remaining_days=3, lead_time_days=3, buffer_days=B)
        below = shelf_life_weight(remaining_days=1, lead_time_days=3, buffer_days=B)
        assert 0.0 <= above <= 1.0
        assert above == 1.0
        assert at == 0.0
        assert below == 0.0


def test_weight_always_in_unit_interval_over_grid():
    for R in range(-2, 25):
        for L in range(0, 12):
            for B in (-3.0, 0.0, 1.0, 4.0, 10.0):
                w = shelf_life_weight(R, L, B)
                assert 0.0 <= w <= 1.0
                assert math.isfinite(w)


def test_weighted_available_handles_zero_buffer_category():
    """End-to-end: a category whose buffer is zero must not blow up and must
    keep weighted_kg in [0, on_hand_kg]."""
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE stg_products (product_id VARCHAR, "
                 "product_name VARCHAR, category VARCHAR)")
    conn.execute("""
        CREATE TABLE stg_inventory_lots (
            lot_id VARCHAR, product_id VARCHAR, product_name VARCHAR,
            quantity_on_hand DOUBLE, expiration_date DATE, committed_quantity DOUBLE
        )
    """)
    conn.execute("INSERT INTO stg_products VALUES ('P1', 'Sprouts', 'FlashCat')")
    conn.executemany("""
        INSERT INTO stg_inventory_lots
            (lot_id, product_id, product_name, quantity_on_hand,
             expiration_date, committed_quantity)
        VALUES (?, 'P1', 'Sprouts', ?, ?, 0)
    """, [
        ("L1", 100.0, "2026-06-10"),  # well in future
        ("L2", 100.0, "2026-05-28"),  # near
    ])
    result = weighted_available_by_product(
        conn, date(2026, 5, 27), lead_time_days=2,
        buffers={"FlashCat": 0.0})
    conn.close()
    s = result["Sprouts"]
    assert s["on_hand_kg"] == pytest.approx(200.0)
    assert 0.0 <= s["weighted_kg"] <= s["on_hand_kg"] + 1e-9


# ──────────────────────────────────────────────────────────────────────────────
# confidence: index ordering, finiteness, and supplier interval ordering
# ──────────────────────────────────────────────────────────────────────────────

def test_supplier_intervals_are_ordered_and_finite(two_supplier_db):
    """For every supplier: downside <= posterior_mean, spread >= 0, and the
    Beta params are finite and positive (p10 <= p50 ordering analogue)."""
    d = supplier_fill_distributions(two_supplier_db, quantile=0.10)
    for sid, info in d.items():
        if sid == "_prior":
            continue
        assert info["downside"] <= info["posterior_mean"] + 1e-9
        assert info["spread"] >= -1e-9
        for key in ("alpha", "beta", "posterior_mean", "downside"):
            assert math.isfinite(info[key])
        assert info["alpha"] > 0 and info["beta"] > 0
        assert 0.0 <= info["downside"] <= 1.0
        assert 0.0 <= info["posterior_mean"] <= 1.0


def test_quantile_ordering_p10_le_p50_le_p90(two_supplier_db):
    """Lower quantiles give lower downside numbers (p10 <= p50 <= p90)."""
    d10 = supplier_fill_distributions(two_supplier_db, quantile=0.10)
    d50 = supplier_fill_distributions(two_supplier_db, quantile=0.50)
    d90 = supplier_fill_distributions(two_supplier_db, quantile=0.90)
    for sid in d10:
        if sid == "_prior":
            continue
        p10 = d10[sid]["downside"]
        p50 = d50[sid]["downside"]
        p90 = d90[sid]["downside"]
        assert p10 <= p50 + 1e-9 <= p90 + 1e-9
        assert all(math.isfinite(x) for x in (p10, p50, p90))


def test_recommendation_confidence_index_in_range_and_finite():
    """When measurable, the confidence index is a finite 0..100 number;
    otherwise it is None with a stated reason (never a made-up default)."""
    conn = _db_with_beta_fills(n_suppliers=6, n_deliveries=20)
    conn.execute("INSERT INTO stg_buyer_orders (product_name, requested_quantity, "
                 "sales_price) VALUES ('Tomatoes', 100, 3.0)")
    res = recommendation_confidence(conn)
    conn.close()
    if res["index"] is None:
        assert "reason" in res and res["reason"]
    else:
        idx = res["index"]
        assert math.isfinite(idx)
        assert 0 <= idx <= 100
        comp = res["components"]
        assert 0.0 <= comp["avg_supplier_spread"] <= 1.0


def test_recommendation_confidence_insufficient_history_is_none():
    conn = duckdb.connect(":memory:")
    conn.execute(_DELIVERIES_DDL)
    conn.execute(_ORDERS_DDL)
    res = recommendation_confidence(conn)
    conn.close()
    assert res["index"] is None
    assert res["reason"]


# ──────────────────────────────────────────────────────────────────────────────
# calibration: cold start, thin data, Beta validity (NaN probes)
# ──────────────────────────────────────────────────────────────────────────────

def test_brand_new_supplier_falls_back_to_population():
    """Zero deliveries → the predictive distribution IS the population Beta."""
    conn = _db_with_beta_fills(n_suppliers=5, n_deliveries=12)
    from risk.supplier_distribution import _delivery_fill_rates
    pop = estimate_population(_delivery_fill_rates(conn))
    conn.close()

    cold = supplier_distribution(0, None, None, pop, quantile=0.10)
    assert cold["mean"] == pytest.approx(pop.mean)
    # Beta params finite, positive, and the downside is a valid fill rate.
    assert math.isfinite(cold["alpha"]) and cold["alpha"] > 0
    assert math.isfinite(cold["beta"]) and cold["beta"] > 0
    assert math.isfinite(cold["downside"])
    assert 0.0 <= cold["downside"] <= 1.0


def test_cold_start_downside_never_nan_with_wide_or_degenerate_population():
    """Probe the suspected NaN-downside path: cold start (full pooled spread)
    under both a very wide and a degenerate (near-zero) population variance.
    The Beta fit must stay well defined → finite, in-range downside."""
    for pooled_var in (1e-9, 0.001, 0.05, 0.24, 0.49):
        pop = Population(mean=0.85, pooled_variance=pooled_var,
                         within_variance=0.01, kappa=4.0, n_deliveries=100,
                         n_suppliers=10, method="empirical_bayes")
        d = supplier_distribution(0, None, None, pop, quantile=0.10)
        assert math.isfinite(d["downside"]), f"NaN downside at var={pooled_var}"
        assert 0.0 <= d["downside"] <= 1.0
        assert math.isfinite(d["alpha"]) and math.isfinite(d["beta"])
        assert d["alpha"] > 0 and d["beta"] > 0


def test_extreme_population_mean_keeps_beta_valid():
    """Population mean near the 0/1 boundary must not yield NaN Beta params."""
    for m in (1e-7, 0.999999):
        pop = Population(mean=m, pooled_variance=0.02, within_variance=0.01,
                         kappa=4.0, n_deliveries=50, n_suppliers=5,
                         method="empirical_bayes")
        d = supplier_distribution(0, None, None, pop, quantile=0.10)
        assert math.isfinite(d["downside"])
        assert math.isfinite(d["alpha"]) and math.isfinite(d["beta"])
        assert d["alpha"] > 0 and d["beta"] > 0


def test_thin_supplier_shrinks_more_than_rich_and_pulls_to_population():
    """A thin-data supplier carries MORE population weight than a data-rich
    one, and its posterior mean is pulled off its raw observation toward the
    population. (Strength of shrinkage depends on the estimated kappa, so we
    assert the relative ordering and the pull direction, not an absolute.)"""
    conn = _make_delivery_db({
        # population suppliers with similar means → small between-variance →
        # larger kappa → meaningful shrinkage of thin suppliers.
        "S-POP-A": [60, 62, 58, 61, 59, 63, 60, 61],
        "S-POP-B": [61, 59, 62, 60, 58, 63, 61, 60],
        "S-RICH": [98, 97, 99, 98, 97, 99, 98, 97, 99, 98],  # 10 deliveries
        "S-THIN": [99, 98],  # only 2, far above the population mean
    })
    d = supplier_fill_distributions(conn, quantile=0.10)
    conn.close()
    thin = d["S-THIN"]
    rich = d["S-RICH"]
    pop_mean = d["_prior"]["mean"]
    # Thin supplier (n=2) carries strictly more population weight than rich (n=10).
    assert thin["shrinkage"] > rich["shrinkage"]
    # Posterior mean sits between the raw observation and the population mean.
    lo, hi = sorted([thin["observed_mean"], pop_mean])
    assert lo - 1e-9 <= thin["posterior_mean"] <= hi + 1e-9
    # And it is strictly pulled down off the raw ~0.985 observation.
    assert thin["posterior_mean"] < thin["observed_mean"]


def test_all_distributions_never_exceed_unit_fill_or_emit_nan():
    """Across a realistic multi-supplier DB, NO supplier may report a fill
    rate (mean/downside) outside [0, 1] or a NaN Beta parameter."""
    conn = _db_with_beta_fills(n_suppliers=8, n_deliveries=25)
    d = supplier_fill_distributions(conn, quantile=0.10)
    conn.close()
    for sid, info in d.items():
        if sid == "_prior":
            continue
        for key in ("posterior_mean", "downside", "observed_mean"):
            v = info[key]
            assert v is None or (math.isfinite(v) and 0.0 <= v <= 1.0), \
                f"{sid}.{key} = {v}"
        for key in ("alpha", "beta"):
            assert math.isfinite(info[key]) and info[key] > 0


def test_pit_values_strictly_in_unit_interval():
    conn = _db_with_beta_fills(n_suppliers=4, n_deliveries=10)
    pits = pit_values(conn)
    conn.close()
    assert len(pits) > 0
    assert np.all(np.isfinite(pits))
    assert np.all(pits >= 0.0) and np.all(pits <= 1.0)


def test_calibration_report_numbers_finite_when_ok():
    conn = _db_with_beta_fills(n_suppliers=8, n_deliveries=30)
    rep = calibration_report(conn)
    conn.close()
    assert rep["status"] == "ok"
    assert math.isfinite(rep["coverage_10_90"])
    assert 0.0 <= rep["coverage_10_90"] <= 1.0
    assert math.isfinite(rep["ks_statistic"])
    assert rep["ks_statistic"] >= 0.0
