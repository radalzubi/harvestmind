"""Adversarial / edge-case hardening tests for HarvestMind's high-stakes
money/decision modules.

These exercise the error/edge branches and probe for correctness bugs in:
  - dashboard/lib/diagnostic_metrics.py
  - risk/safe_commit.py
  - infrastructure/lineage.py
  - backtesting/leakage_guard.py
  - pool/pool_contributor.py

Conventions mirror tests/unit/test_diagnostic_metrics.py (in-memory DuckDB
with migration-010 staging DDL), tests/unit/test_safe_commit.py, and
tests/unit/test_data_pool.py (OperatorRegistry/PoolContributor on tmp_path).

Real source bugs are encoded as the CORRECT expectation under
``@pytest.mark.xfail(reason="BUG: ...", strict=True)`` — the source is never
edited and the assertion is never weakened.
"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd
import pytest

_TODAY = date(2026, 5, 27)


# ── Staging-table helpers ─────────────────────────────────────────────────────

_STAGING_DDL = [
    """CREATE TABLE stg_products (
        product_id VARCHAR, product_name VARCHAR, category VARCHAR,
        unit VARCHAR DEFAULT 'kg', default_shelf_life_days INTEGER,
        traceability_required BOOLEAN DEFAULT FALSE)""",
    """CREATE TABLE stg_supplier_deliveries (
        delivery_id VARCHAR, supplier_id VARCHAR, supplier_name VARCHAR,
        product_id VARCHAR, product_name VARCHAR, delivery_date DATE,
        ordered_quantity DOUBLE, delivered_quantity DOUBLE,
        accepted_quantity DOUBLE, rejected_quantity DOUBLE,
        unit_cost DOUBLE, quality_grade VARCHAR, lot_id VARCHAR)""",
    """CREATE TABLE stg_inventory_lots (
        lot_id VARCHAR, product_id VARCHAR, product_name VARCHAR,
        supplier_id VARCHAR, quantity_on_hand DOUBLE, unit VARCHAR DEFAULT 'kg',
        arrival_date DATE, expiration_date DATE, warehouse_location VARCHAR,
        quality_grade VARCHAR, committed_quantity DOUBLE DEFAULT 0)""",
    """CREATE TABLE stg_buyer_orders (
        order_id VARCHAR, buyer_id VARCHAR, buyer_name VARCHAR,
        product_id VARCHAR, product_name VARCHAR, order_date DATE,
        delivery_date DATE, requested_quantity DOUBLE, fulfilled_quantity DOUBLE,
        substituted_quantity DOUBLE DEFAULT 0, sales_price DOUBLE,
        required_quality_grade VARCHAR)""",
    """CREATE TABLE stg_waste_adjustments (
        adjustment_id VARCHAR, date DATE, product_id VARCHAR,
        product_name VARCHAR, lot_id VARCHAR, quantity_lost DOUBLE,
        reason VARCHAR, estimated_value_lost DOUBLE)""",
]


def _fresh_staging() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(":memory:")
    for ddl in _STAGING_DDL:
        conn.execute(ddl)
    return conn


@pytest.fixture()
def empty_db():
    conn = _fresh_staging()
    yield conn
    conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# diagnostic_metrics.py — empty / NULL / zero-denominator edge branches
# ══════════════════════════════════════════════════════════════════════════════

def test_diagnostic_summary_fully_empty_is_well_formed(empty_db):
    """Every staging table empty: summary returns zeroed, non-crashing payload."""
    from dashboard.lib.diagnostic_metrics import diagnostic_summary

    res = diagnostic_summary(empty_db, partner_name="Empty Co", as_of_date=_TODAY)
    assert res["total_waste_loss_usd"] == 0.0
    assert res["total_shortage_loss_usd"] == 0.0
    assert res["n_risky_suppliers"] == 0
    assert res["n_risky_products"] == 0
    assert res["n_risky_buyers"] == 0
    assert res["traceability_completeness_pct"] == 0.0
    assert res["recommendations"] == []
    assert res["top_risks"] == []
    # Empty data must not extrapolate to a non-zero savings ceiling
    assert res["savings"]["addressable_loss_usd"] == 0.0
    # period auto-detect with no dates falls back to the 90-day default
    assert res["period_days_detected"] == 90


def test_waste_loss_all_null_values_counts_unvalued_not_crash(empty_db):
    """Rows with NULL estimated_value_lost AND no unit-cost basis must be
    counted as unvalued and contribute $0 — never silently inflate the total
    and never raise."""
    from dashboard.lib.diagnostic_metrics import waste_loss_usd

    empty_db.executemany("""
        INSERT INTO stg_waste_adjustments
            (adjustment_id, date, product_name, quantity_lost,
             reason, estimated_value_lost)
        VALUES (?, ?, ?, ?, ?, ?)
    """, [
        ("W1", "2026-05-10", "Tomatoes", 10.0, "Spoilage", None),
        ("W2", "2026-05-11", "Lettuce", None, "Overripe", None),  # null qty too
    ])
    res = waste_loss_usd(empty_db)
    assert res["total_usd"] == 0.0
    assert res["n_rows"] == 2
    assert res["n_rows_unvalued"] == 2


def test_waste_loss_null_date_rows_included(empty_db):
    """A waste row with a NULL date must still be counted (the SQL filter is
    ``date >= since OR date IS NULL``) and valued from estimated_value_lost."""
    from dashboard.lib.diagnostic_metrics import waste_loss_usd

    empty_db.execute("""
        INSERT INTO stg_waste_adjustments
            (adjustment_id, date, product_name, quantity_lost,
             reason, estimated_value_lost)
        VALUES ('W1', NULL, 'Tomatoes', 5.0, 'Spoilage', 99.0)
    """)
    res = waste_loss_usd(empty_db)
    assert res["n_rows"] == 1
    assert res["total_usd"] == pytest.approx(99.0)


def test_shortage_loss_unvalued_only_counts_actual_misses(empty_db):
    """A line with no price AND no product avg is counted unvalued only when it
    actually has a miss; a fully-filled unpriced line is not flagged."""
    from dashboard.lib.diagnostic_metrics import shortage_loss_usd

    empty_db.executemany("""
        INSERT INTO stg_buyer_orders
            (order_id, buyer_name, product_name, delivery_date,
             requested_quantity, fulfilled_quantity, substituted_quantity, sales_price)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        # miss=40, no price, no avg available -> unvalued, $0
        ("X1", "B1", "Tomatoes", "2026-05-10", 100, 60, 0, None),
        # fully filled, no price -> NOT counted as unvalued
        ("X2", "B2", "Lettuce", "2026-05-11", 50, 50, 0, None),
    ])
    res = shortage_loss_usd(empty_db)
    assert res["total_usd"] == 0.0
    assert res["n_at_risk"] == 1
    assert res["n_at_risk_unvalued"] == 1


def test_buyer_with_zero_requested_no_divide_by_zero(empty_db):
    """A buyer whose total_requested sums to 0 must yield rate 0.0, not NaN/inf
    or a ZeroDivisionError."""
    from dashboard.lib.diagnostic_metrics import buyer_fulfillment_rates

    empty_db.execute("""
        INSERT INTO stg_buyer_orders
            (order_id, buyer_id, buyer_name, product_name, delivery_date,
             requested_quantity, fulfilled_quantity, substituted_quantity)
        VALUES ('O1', 'B0', 'Zero Buyer', 'Tomatoes', '2026-05-10', 0, 0, 0)
    """)
    res = buyer_fulfillment_rates(empty_db)
    b = next(b for b in res["buyers"] if b["buyer_id"] == "B0")
    assert b["fulfillment_rate"] == 0.0
    assert b["missed_rate"] == 0.0
    assert b["substitution_rate"] == 0.0


def test_supplier_zero_ordered_is_unknown_not_risky(empty_db):
    """A supplier whose total_ordered is 0 (not NULL) must be Unknown and
    excluded from n_risky — a 0/0 fill rate is undefined, not 'High risk'."""
    from dashboard.lib.diagnostic_metrics import supplier_reliability_scores

    empty_db.execute("""
        INSERT INTO stg_supplier_deliveries
            (delivery_id, supplier_id, supplier_name, product_name, delivery_date,
             ordered_quantity, delivered_quantity, accepted_quantity, rejected_quantity)
        VALUES ('D1', 'S0', 'Zero Supplier', 'Tomatoes', '2026-05-01', 0, 0, 0, 0)
    """)
    res = supplier_reliability_scores(empty_db)
    s = next(s for s in res["suppliers"] if s["supplier_id"] == "S0")
    assert s["fill_rate"] is None
    assert s["risk_level"] == "Unknown"
    assert res["n_risky"] == 0
    assert res["n_unknown"] >= 1


def test_supplier_rejection_rate_no_delivered_is_zero(empty_db):
    """rejection_rate denominator (delivered) of zero must not divide by zero."""
    from dashboard.lib.diagnostic_metrics import supplier_reliability_scores

    empty_db.execute("""
        INSERT INTO stg_supplier_deliveries
            (delivery_id, supplier_id, supplier_name, product_name, delivery_date,
             ordered_quantity, delivered_quantity, accepted_quantity, rejected_quantity)
        VALUES ('D1', 'S1', 'Sup', 'Tomatoes', '2026-05-01', 100, 0, 0, 5)
    """)
    res = supplier_reliability_scores(empty_db)
    s = next(s for s in res["suppliers"] if s["supplier_id"] == "S1")
    assert s["rejection_rate"] == 0.0


def test_atp_product_no_lots_absent_no_crash(empty_db):
    """A product present in the catalog but with no inventory lots simply does
    not appear in ATP output; no crash, empty product list."""
    from dashboard.lib.diagnostic_metrics import atp_by_product

    empty_db.execute(
        "INSERT INTO stg_products (product_id, product_name, category) "
        "VALUES ('P1', 'Tomatoes', 'Vegetables')")
    res = atp_by_product(empty_db, as_of_date=_TODAY)
    assert res["products"] == []
    assert res["n_risky"] == 0


def test_atp_null_expiration_treated_fully_usable(empty_db):
    """A lot with NULL expiration is fully usable (weight 1.0) — not zeroed."""
    from dashboard.lib.diagnostic_metrics import atp_by_product

    empty_db.execute("""
        INSERT INTO stg_inventory_lots
            (lot_id, product_id, product_name, quantity_on_hand,
             arrival_date, expiration_date, committed_quantity)
        VALUES ('L1', 'P1', 'Tomatoes', 100.0, '2026-05-01', NULL, 0)
    """)
    res = atp_by_product(empty_db, as_of_date=_TODAY)
    tom = next(p for p in res["products"] if p["product_name"] == "Tomatoes")
    assert tom["weighted_usable_kg"] == pytest.approx(100.0)
    assert tom["atp_kg"] == pytest.approx(100.0)
    assert tom["expired_kg"] == 0.0
    assert tom["near_expiry_kg"] == 0.0


def test_savings_tiny_detected_period_does_not_overextrapolate(empty_db):
    """A single-date data span must clamp the annualization period to >= 7 days
    so a tiny sample doesn't extrapolate by 365x in the diagnostic summary."""
    from dashboard.lib.diagnostic_metrics import diagnostic_summary

    empty_db.execute("""
        INSERT INTO stg_waste_adjustments
            (adjustment_id, date, product_name, quantity_lost,
             reason, estimated_value_lost)
        VALUES ('W1', '2026-05-01', 'Tomatoes', 5.0, 'Spoilage', 100.0)
    """)
    res = diagnostic_summary(empty_db, days=None, as_of_date=_TODAY)
    # span = 1 day -> clamped to min_days=7
    assert res["period_days_detected"] == 7
    assert res["savings"]["period_days"] == 7
    assert res["savings"]["annualization_factor"] == pytest.approx(365.0 / 7, abs=0.01)


def test_atp_identities_hold_on_mixed_lots(empty_db):
    """Identity guards: weighted <= usable, atp <= weighted, expired/near/healthy
    partition on_hand. Exercised with expired + near-expiry + healthy in one
    product."""
    from dashboard.lib.diagnostic_metrics import atp_by_product

    empty_db.executemany("""
        INSERT INTO stg_inventory_lots
            (lot_id, product_id, product_name, quantity_on_hand,
             arrival_date, expiration_date, committed_quantity)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [
        ("L1", "P1", "Tomatoes", 100.0, "2026-05-01", "2026-06-30", 0),   # healthy
        ("L2", "P1", "Tomatoes", 50.0, "2026-05-01", "2026-05-28", 0),    # near (R=1)
        ("L3", "P1", "Tomatoes", 30.0, "2026-05-01", "2026-05-22", 0),    # expired
    ])
    res = atp_by_product(empty_db, as_of_date=_TODAY)
    tom = next(p for p in res["products"] if p["product_name"] == "Tomatoes")
    assert tom["total_on_hand_kg"] == pytest.approx(180.0)
    assert tom["expired_kg"] == pytest.approx(30.0)
    assert tom["near_expiry_kg"] == pytest.approx(50.0)
    assert tom["weighted_usable_kg"] <= tom["usable_kg"] + 1e-6
    assert tom["atp_kg"] <= tom["weighted_usable_kg"] + 1e-6


# ══════════════════════════════════════════════════════════════════════════════
# safe_commit.py — holdback / safe-commit invariants and threshold edges
# ══════════════════════════════════════════════════════════════════════════════

def _seed_safe_commit_db(conn, supplier_accepts, on_hand=100.0, committed=0.0,
                         exp="2026-06-30", buyer_req=100, buyer_ful=100):
    """Seed one product ('Tomatoes') with a supplier accept-quantity series."""
    conn.execute(
        "INSERT INTO stg_products (product_id, product_name, category) "
        "VALUES ('P1', 'Tomatoes', 'Vegetables')")
    rows = []
    for i, acc in enumerate(supplier_accepts):
        rows.append((f"D{i}", "S1", "Sup", "P1", "Tomatoes", "2026-05-01",
                     100.0, float(acc), float(acc), 0.0, 1.0, "A", f"L{i}"))
    conn.executemany("""INSERT INTO stg_supplier_deliveries
        (delivery_id, supplier_id, supplier_name, product_id, product_name,
         delivery_date, ordered_quantity, delivered_quantity, accepted_quantity,
         rejected_quantity, unit_cost, quality_grade, lot_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", rows)
    conn.execute("""INSERT INTO stg_inventory_lots
        (lot_id, product_id, product_name, supplier_id, quantity_on_hand,
         arrival_date, expiration_date, committed_quantity)
        VALUES ('LOT1', 'P1', 'Tomatoes', 'S1', ?, '2026-05-10', ?, ?)""",
                 [on_hand, exp, committed])
    conn.execute("""INSERT INTO stg_buyer_orders
        (order_id, buyer_name, product_name, delivery_date,
         requested_quantity, fulfilled_quantity, substituted_quantity, sales_price)
        VALUES ('O1', 'Buyer', 'Tomatoes', '2026-05-15', ?, ?, 0, 2.5)""",
                 [buyer_req, buyer_ful])


def test_safe_commit_never_negative_and_holdback_bounded(empty_db):
    """safe_commit_kg >= 0, holdback_kg >= 0, and safe + holdback == net_available
    for every product, including a volatile low-downside supplier."""
    from risk.safe_commit import safe_commit_recommendations

    # swingy supplier -> large holdback fraction
    _seed_safe_commit_db(empty_db, [55, 95, 58, 96, 60], on_hand=100.0)
    recs = safe_commit_recommendations(empty_db, as_of_date=_TODAY, lead_time_days=3)
    for r in recs:
        assert r["safe_commit_kg"] >= 0.0
        assert r["holdback_kg"] >= 0.0
        assert r["safe_commit_kg"] <= r["net_available_kg"] + 1e-6
        assert (r["safe_commit_kg"] + r["holdback_kg"]) == pytest.approx(
            r["net_available_kg"], abs=0.2)


def test_safe_commit_committed_exceeds_onhand_clamps_to_zero(empty_db):
    """If committed quantity exceeds shelf-life-weighted availability,
    net_available clamps to 0 and safe_commit is 0 — never negative."""
    from risk.safe_commit import safe_commit_recommendations

    _seed_safe_commit_db(empty_db, [98, 97, 99, 98, 97],
                         on_hand=100.0, committed=250.0)
    recs = safe_commit_recommendations(empty_db, as_of_date=_TODAY, lead_time_days=3)
    tom = next(r for r in recs if r["product_name"] == "Tomatoes")
    assert tom["net_available_kg"] == 0.0
    assert tom["safe_commit_kg"] == 0.0
    assert tom["holdback_kg"] == 0.0
    assert tom["risk_level"] == "High"
    assert "no committable inventory" in tom["recommendation_text"].lower()


def test_safe_commit_empty_db_returns_empty_list(empty_db):
    from risk.safe_commit import safe_commit_recommendations

    recs = safe_commit_recommendations(empty_db, as_of_date=_TODAY)
    assert recs == []


def test_safe_commit_high_downside_threshold_holdback(empty_db):
    """A supplier whose downside sits below the High threshold (0.80) gets the
    0.15 supply holdback; safe_commit is correspondingly reduced."""
    from risk.safe_commit import safe_commit_recommendations
    from risk.supplier_distribution import supplier_fill_distributions

    # A reliably-low supplier: downside well under 0.80
    _seed_safe_commit_db(empty_db, [40, 42, 38, 41, 39], on_hand=100.0,
                         buyer_req=100, buyer_ful=100)
    dists = supplier_fill_distributions(empty_db, quantile=0.10)
    sid = next(k for k in dists if k != "_prior")
    assert dists[sid]["downside"] < 0.80  # precondition for the High branch

    recs = safe_commit_recommendations(empty_db, as_of_date=_TODAY, lead_time_days=3)
    tom = next(r for r in recs if r["product_name"] == "Tomatoes")
    # net_available is full 100 (fresh, no commitment); holdback >= 15%
    assert tom["net_available_kg"] == pytest.approx(100.0, abs=1.0)
    assert tom["holdback_kg"] >= 0.15 * tom["net_available_kg"] - 0.5
    assert tom["risk_level"] in ("High", "Medium")


def test_safe_commit_buyer_risk_adds_holdback(empty_db):
    """A buyer fulfillment below 0.90 adds the 0.05 buyer holdback on top of
    any supply holdback."""
    from risk.safe_commit import safe_commit_recommendations

    # reliable supplier (no supply holdback), but buyer fulfillment 70% < 0.90
    _seed_safe_commit_db(empty_db, [98, 97, 99, 98, 97], on_hand=100.0,
                         buyer_req=100, buyer_ful=70)
    recs = safe_commit_recommendations(empty_db, as_of_date=_TODAY, lead_time_days=3)
    tom = next(r for r in recs if r["product_name"] == "Tomatoes")
    assert any("buyer fulfillment" in f for f in tom["risk_flags"])
    assert tom["holdback_kg"] > 0.0


# ══════════════════════════════════════════════════════════════════════════════
# lineage.py — assert_lineage_present rejects, trace_row round-trips
# ══════════════════════════════════════════════════════════════════════════════

from infrastructure.lineage import (  # noqa: E402
    LINEAGE_COLUMNS,
    assert_lineage_present,
    stamp_lineage,
    trace_row,
)


@pytest.mark.parametrize("drop_col", list(LINEAGE_COLUMNS))
def test_assert_lineage_rejects_each_missing_column(drop_col):
    """Removing ANY single lineage column must raise — an untraceable row may
    never pass the operator-scoped gate."""
    df = pd.DataFrame([{"product_name": "Kale", "requested_quantity": 10}])
    stamped = stamp_lineage(df, operator_id="op_a",
                            upload_session_id="s1", source_file="f.csv")
    broken = stamped.drop(columns=[drop_col])
    with pytest.raises(ValueError, match="lineage columns missing"):
        assert_lineage_present(broken)


@pytest.mark.parametrize("null_col", list(LINEAGE_COLUMNS))
def test_assert_lineage_rejects_each_null_value(null_col):
    """A present-but-NULL lineage value must also raise (provenance gap)."""
    df = pd.DataFrame([{"product_name": "Kale", "requested_quantity": 10}])
    stamped = stamp_lineage(df, operator_id="op_a",
                            upload_session_id="s1", source_file="f.csv")
    stamped.loc[0, null_col] = None
    with pytest.raises(ValueError, match=f"null {null_col}"):
        assert_lineage_present(stamped)


def test_assert_lineage_empty_frame_with_columns_passes():
    """An empty frame that still carries the lineage columns has no null rows
    and must pass (vacuously traceable)."""
    df = pd.DataFrame({c: pd.Series(dtype="object") for c in LINEAGE_COLUMNS})
    assert_lineage_present(df)  # should not raise


def test_trace_row_round_trips_through_duckdb():
    """stamp -> insert -> trace_row returns the exact provenance tuple."""
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE stg_buyer_orders ("
                 "product_name VARCHAR, requested_quantity DOUBLE, "
                 "_upload_session_id VARCHAR, _uploaded_at TIMESTAMP, "
                 "_source_file VARCHAR, _operator_id VARCHAR)")
    df = pd.DataFrame([{"product_name": "Carrots", "requested_quantity": 10.0}])
    stamped = stamp_lineage(df, operator_id="op_a",
                            upload_session_id="sess-1", source_file="orders.csv")
    cols = ", ".join(stamped.columns)
    conn.register("d", stamped)
    conn.execute(f"INSERT INTO stg_buyer_orders ({cols}) SELECT {cols} FROM d")
    conn.unregister("d")

    out = trace_row(conn, "stg_buyer_orders", "product_name = 'Carrots'")
    assert len(out) == 1
    assert out[0]["_operator_id"] == "op_a"
    assert out[0]["_upload_session_id"] == "sess-1"
    assert out[0]["_source_file"] == "orders.csv"
    assert out[0]["n_rows"] == 1
    conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# leakage_guard.py — cutoff boundary correctness + missing-column probe
# ══════════════════════════════════════════════════════════════════════════════

from backtesting.leakage_guard import (  # noqa: E402
    LeakageError,
    LeakageGuard,
    assert_dates_in_window,
    assert_no_future_data,
)


def _cutoff_df():
    # Exactly one row on the cutoff, one before, one after.
    return pd.DataFrame({
        "week_start": pd.to_datetime(["2024-01-01", "2024-01-08", "2024-01-15"]),
        "value": [1, 2, 3],
    })


def test_cutoff_row_included_in_training_inclusive():
    """A row dated exactly on the cutoff is part of the training window
    (inclusive) — no off-by-one dropping it."""
    df = _cutoff_df()
    guard = LeakageGuard(df, "week_start", date(2024, 1, 8), inclusive=True)
    got = guard.get()
    assert len(got) == 2  # Jan 1 and Jan 8
    assert pd.Timestamp("2024-01-08") in set(got["week_start"])


def test_cutoff_row_excluded_when_not_inclusive():
    df = _cutoff_df()
    guard = LeakageGuard(df, "week_start", date(2024, 1, 8), inclusive=False)
    got = guard.get()
    assert len(got) == 1  # only Jan 1
    assert pd.Timestamp("2024-01-08") not in set(got["week_start"])


def test_cutoff_row_excluded_from_realized_window():
    """The realized/horizon window must EXCLUDE the cutoff date: a row on the
    cutoff is not 'future', so assert_no_future_data must not raise, while a
    later row must. This pins the boundary on both sides."""
    df = _cutoff_df()
    cutoff = date(2024, 1, 8)
    # Row exactly on cutoff is not past it.
    on_or_before = df[df["week_start"] <= pd.Timestamp(cutoff)]
    assert_no_future_data(on_or_before, "week_start", cutoff)  # no raise
    # A row after the cutoff is leakage.
    with pytest.raises(LeakageError):
        assert_no_future_data(df, "week_start", cutoff)


def test_assert_dates_in_window_boundary_inclusive_both_ends():
    """Rows exactly on window_start and window_end are inside the window."""
    df = pd.DataFrame({
        "d": pd.to_datetime(["2024-01-08", "2024-01-22"]),
        "v": [1, 2],
    })
    # Both endpoints inclusive -> no raise.
    assert_dates_in_window(df, "d", date(2024, 1, 8), date(2024, 1, 22))


def test_validate_no_leakage_missing_date_column_does_not_silently_pass():
    """FIXED: validate_no_leakage now fails CLOSED — a missing date column
    raises instead of silently disabling the guard. A horizon frame that
    smuggles future data under a differently-named column must not slip
    through.
    """
    df = _cutoff_df()
    guard = LeakageGuard(df, "week_start", date(2024, 1, 8))
    # result has future data but under a column name the guard wasn't told about
    leaky = pd.DataFrame({
        "value": [99],
        "realized_week": pd.to_datetime(["2099-01-01"]),
    })

    # The guard is asked to validate against "week_start", which is absent → raise.
    with pytest.raises(LeakageError):
        guard.validate_no_leakage(leaky, "week_start")


def test_guard_get_missing_date_column_raises():
    """By contrast, get() reads the configured date_col directly, so a missing
    column there raises (fail-closed) — confirming the asymmetry is real."""
    df = pd.DataFrame({"other": pd.to_datetime(["2024-01-01"]), "v": [1]})
    guard = LeakageGuard(df, "week_start", date(2024, 1, 8))
    with pytest.raises(KeyError):
        guard.get()


# ══════════════════════════════════════════════════════════════════════════════
# pool_contributor.py — k-anonymity floor edges + anonymization
# ══════════════════════════════════════════════════════════════════════════════

from infrastructure.db_manager import DBManager  # noqa: E402
from infrastructure.operator_registry import OperatorRegistry  # noqa: E402
from pool.pool_contributor import K_ANONYMITY_FLOOR, PoolContributor  # noqa: E402
from pool.pool_reader import PoolReader  # noqa: E402

_NAMES = ("Good Farms", "Risky Produce", "City Bistro", "Hotel Grand",
          "Roma Tomatoes", "Baby Spinach")


@pytest.fixture()
def pool_env(tmp_path):
    registry = OperatorRegistry(data_root=tmp_path / "data")
    pool_root = tmp_path / "pool"
    contributor = PoolContributor(registry, pool_root)
    reader = PoolReader(pool_root)
    return registry, contributor, reader


def _seed_deliveries(registry, operator_id, n_deliveries, *,
                     accepted=90.0, ordered=100.0):
    """Seed exactly n_deliveries supplier rows in one category ('Vegetables')."""
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
    ]))
    ins("stg_supplier_deliveries", pd.DataFrame([
        {"supplier_id": "S1",
         "supplier_name": "Good Farms" if i % 2 else "Risky Produce",
         "product_id": "P1", "product_name": "Roma Tomatoes",
         "delivery_date": "2026-05-01",
         "ordered_quantity": ordered, "delivered_quantity": accepted,
         "accepted_quantity": accepted, "unit_cost": 2.0}
        for i in range(n_deliveries)
    ]))
    conn.close()
    dbm.close_all()


def test_k_anonymity_exact_floor_is_kept(pool_env):
    """A category with EXACTLY K_ANONYMITY_FLOOR underlying rows is kept
    (the floor is inclusive: len(g) < K drops, == K survives)."""
    registry, contributor, _ = pool_env
    op = registry.create_operator("Hub A", pool_consent=True, region="midwest")
    _seed_deliveries(registry, op.operator_id, K_ANONYMITY_FLOOR)
    res = contributor.contribute_session(op.operator_id)
    assert res.status == "contributed"
    assert "yield_distributions" in res.signals_written


def test_k_anonymity_below_floor_is_dropped(pool_env):
    """K-1 underlying rows -> the signal is dropped and counted."""
    registry, contributor, _ = pool_env
    op = registry.create_operator("Hub A", pool_consent=True, region="midwest")
    _seed_deliveries(registry, op.operator_id, K_ANONYMITY_FLOOR - 1)
    res = contributor.contribute_session(op.operator_id)
    assert res.status == "contributed" or res.status == "skipped"
    assert "yield_distributions" not in res.signals_written
    assert res.signals_dropped_k_anonymity >= 1


def test_demand_k_anon_uses_same_filter_as_signal(pool_env):
    """Recent fix: the demand k-anon COUNT must use the SAME filter as the
    signal query (requested_quantity NOT NULL AND date NOT NULL). NULL-quantity
    rows must NOT inflate the count and let a thin signal slip through.

    Setup: K-1 valid demand rows (below floor) + several NULL-quantity rows.
    If the count counted the NULLs it would pass the floor and wrongly emit a
    demand signal built on only K-1 real rows. Correct behavior: dropped.
    """
    registry, contributor, _ = pool_env
    op = registry.create_operator("Hub A", pool_consent=True, region="midwest")

    dbm = DBManager(registry)
    conn = dbm.get_operator_connection(op.operator_id)

    def ins(table, df):
        df = stamp_lineage(df, operator_id=op.operator_id,
                           upload_session_id="s1", source_file="seed.csv")
        cols = ", ".join(df.columns)
        conn.register("seed_df", df)
        conn.execute(f"INSERT INTO {table} ({cols}) SELECT {cols} FROM seed_df")
        conn.unregister("seed_df")

    ins("stg_products", pd.DataFrame([
        {"product_id": "P1", "product_name": "Roma Tomatoes",
         "category": "Vegetables"},
    ]))
    valid = [
        {"buyer_name": "City Bistro", "product_id": "P1",
         "product_name": "Roma Tomatoes",
         "order_date": f"2026-0{(i % 5) + 1}-{(i % 27) + 1:02d}",
         "delivery_date": f"2026-0{(i % 5) + 1}-{(i % 27) + 1:02d}",
         "requested_quantity": 100.0 + i, "fulfilled_quantity": 95.0,
         "sales_price": 2.5}
        for i in range(K_ANONYMITY_FLOOR - 1)
    ]
    nulls = [
        {"buyer_name": "Hotel Grand", "product_id": "P1",
         "product_name": "Roma Tomatoes",
         "order_date": "2026-05-10", "delivery_date": "2026-05-10",
         "requested_quantity": None, "fulfilled_quantity": 95.0,
         "sales_price": 2.5}
        for _ in range(8)
    ]
    ins("stg_buyer_orders", pd.DataFrame(valid + nulls))
    conn.close()
    dbm.close_all()

    res = contributor.contribute_session(op.operator_id)
    # The Vegetables demand signal must be dropped: only K-1 valid rows.
    assert "demand_patterns" not in res.signals_written
    assert res.signals_dropped_k_anonymity >= 1


def test_anonymized_parquet_contains_no_source_names(pool_env):
    """Mechanical re-assert on a crafted vault: no company/buyer/supplier/
    product name survives into any written pool parquet payload."""
    registry, contributor, _ = pool_env
    op = registry.create_operator("Hub A", pool_consent=True, region="midwest")

    dbm = DBManager(registry)
    conn = dbm.get_operator_connection(op.operator_id)

    def ins(table, df):
        df = stamp_lineage(df, operator_id=op.operator_id,
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
         "order_date": f"2026-0{(i % 5) + 1}-{(i % 27) + 1:02d}",
         "delivery_date": f"2026-0{(i % 5) + 1}-{(i % 27) + 1:02d}",
         "requested_quantity": 100.0 + i, "fulfilled_quantity": 95.0,
         "sales_price": 2.5}
        for i in range(15)
    ]))
    ins("stg_supplier_deliveries", pd.DataFrame([
        {"supplier_id": "S1",
         "supplier_name": "Good Farms" if i % 2 else "Risky Produce",
         "product_id": "P1", "product_name": "Roma Tomatoes",
         "delivery_date": "2026-05-01", "ordered_quantity": 100.0,
         "delivered_quantity": 92.0, "accepted_quantity": 90.0,
         "unit_cost": 2.0}
        for i in range(15)
    ]))
    ins("stg_waste_adjustments", pd.DataFrame([
        {"product_id": "P1", "product_name": "Roma Tomatoes",
         "date": f"2026-0{(i % 5) + 1}-10", "quantity_lost": 5.0,
         "reason": "Overripe surplus" if i % 2 else "Quality reject"}
        for i in range(12)
    ]))
    conn.close()
    dbm.close_all()

    res = contributor.contribute_session(op.operator_id)
    assert res.status == "contributed"
    written = list((contributor.pool_root / "signals").rglob("*.parquet"))
    assert written, "expected at least one signal parquet"
    for pq in written:
        payload = pd.read_parquet(pq).to_json()
        for name in _NAMES + ("Hub A", op.operator_id):
            # operator_id is allowed as an explicit audit column, not as a leak
            if name == op.operator_id:
                continue
            assert name not in payload, f"{name} leaked into {pq.name}"


def test_non_consented_operator_writes_nothing(pool_env):
    """A non-consented operator is skipped: no parquet is written at all."""
    registry, contributor, _ = pool_env
    op = registry.create_operator("Hub B", pool_consent=False, region="midwest")
    _seed_deliveries(registry, op.operator_id, K_ANONYMITY_FLOOR + 5)
    res = contributor.contribute_session(op.operator_id)
    assert res.status == "skipped"
    assert not list((contributor.pool_root / "signals").rglob("*.parquet"))


def test_contribute_session_never_raises_on_missing_vault(pool_env):
    """Defensive contract: a broken vault yields status='error', not an
    exception that would break the upload flow."""
    registry, contributor, _ = pool_env
    op = registry.create_operator("Hub A", pool_consent=True)
    registry.get_db_path(op.operator_id).unlink()
    res = contributor.contribute_session(op.operator_id)
    assert res.status == "error"
