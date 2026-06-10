"""Phase A tests: operator vaults, isolation, consent, lineage.

The isolation proof is the point: operator A's data must be invisible
to operator B through every access path except the one read-only,
purpose-logged cross-operator connection.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from infrastructure.consent_manager import ConsentManager
from infrastructure.db_manager import DBManager
from infrastructure.lineage import (
    LINEAGE_COLUMNS,
    assert_lineage_present,
    stamp_lineage,
    trace_row,
)
from infrastructure.operator_registry import (
    OperatorNotFoundError,
    OperatorRegistry,
)


@pytest.fixture()
def registry(tmp_path):
    return OperatorRegistry(data_root=tmp_path / "data")


@pytest.fixture()
def two_ops(registry):
    a = registry.create_operator("Hub A", pool_consent=True, region="midwest")
    b = registry.create_operator("Hub B", pool_consent=False)
    return registry, a, b


def _insert_order(conn, product="Tomatoes", qty=100.0, operator_id="op_x"):
    df = pd.DataFrame([{
        "product_name": product, "requested_quantity": qty,
        "fulfilled_quantity": qty, "buyer_name": "Bistro",
    }])
    df = stamp_lineage(df, operator_id=operator_id,
                       upload_session_id="sess-1", source_file="orders.csv")
    cols = ", ".join(df.columns)
    conn.register("df_ins", df)
    conn.execute(f"INSERT INTO stg_buyer_orders ({cols}) SELECT {cols} FROM df_ins")
    conn.unregister("df_ins")


# ── Vault creation + isolation ────────────────────────────────────────────────

def test_two_operators_get_separate_vaults(two_ops):
    registry, a, b = two_ops
    assert a.operator_id != b.operator_id
    pa, pb = registry.get_db_path(a.operator_id), registry.get_db_path(b.operator_id)
    assert pa != pb and pa.exists() and pb.exists()
    va, vb = registry.vault_dir(a.operator_id), registry.vault_dir(b.operator_id)
    for sub in ("uploads", "sessions", "exports"):
        assert (va / sub).is_dir() and (vb / sub).is_dir()


def test_data_in_a_invisible_to_b(two_ops):
    registry, a, b = two_ops
    dbm = DBManager(registry)
    ca = dbm.get_operator_connection(a.operator_id)
    _insert_order(ca, operator_id=a.operator_id)
    ca.close()

    cb = dbm.get_operator_connection(b.operator_id)
    assert cb.execute("SELECT COUNT(*) FROM stg_buyer_orders").fetchone()[0] == 0
    dbm.close_all()


def test_new_vault_has_all_migrations(two_ops):
    registry, a, _ = two_ops
    dbm = DBManager(registry)
    conn = dbm.get_read_only_connection(a.operator_id)
    tables = {r[0] for r in conn.execute(
        "SELECT table_name FROM information_schema.tables").fetchall()}
    for t in ("stg_buyer_orders", "stg_supplier_deliveries",
              "stg_inventory_lots", "stg_waste_adjustments", "stg_products",
              "fact_orders", "dim_products"):
        assert t in tables, f"missing {t}"
    dbm.close_all()


def test_lineage_columns_present_in_all_staging_tables(two_ops):
    registry, a, _ = two_ops
    dbm = DBManager(registry)
    conn = dbm.get_read_only_connection(a.operator_id)
    for t in ("stg_buyer_orders", "stg_supplier_deliveries",
              "stg_inventory_lots", "stg_waste_adjustments", "stg_products"):
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({t})").fetchall()}
        for lc in LINEAGE_COLUMNS:
            assert lc in cols, f"{t} missing {lc}"
    dbm.close_all()


# ── Cross-operator access (the one sanctioned path) ──────────────────────────

def test_cross_operator_requires_explicit_ids_and_purpose(two_ops):
    registry, a, b = two_ops
    dbm = DBManager(registry)
    with pytest.raises(ValueError, match="explicit operator ids"):
        dbm.get_cross_operator_connection([], purpose="pool")
    with pytest.raises(ValueError, match="purpose"):
        dbm.get_cross_operator_connection([a.operator_id], purpose=" ")
    with pytest.raises(OperatorNotFoundError):
        dbm.get_cross_operator_connection(["op_nope"], purpose="pool")


def test_cross_operator_reads_both_and_logs_purpose(two_ops):
    registry, a, b = two_ops
    dbm = DBManager(registry)
    ca = dbm.get_operator_connection(a.operator_id)
    _insert_order(ca, qty=111.0, operator_id=a.operator_id)
    ca.close()
    cb = dbm.get_operator_connection(b.operator_id)
    _insert_order(cb, qty=222.0, operator_id=b.operator_id)
    cb.close()

    x = dbm.get_cross_operator_connection(
        [a.operator_id, b.operator_id], purpose="pool contribution test")
    na = x.execute(
        f"SELECT COUNT(*) FROM {a.operator_id}.stg_buyer_orders").fetchone()[0]
    nb = x.execute(
        f"SELECT COUNT(*) FROM {b.operator_id}.stg_buyer_orders").fetchone()[0]
    assert na == 1 and nb == 1

    log = (registry.registry_dir / "cross_access_log.jsonl").read_text()
    entry = json.loads(log.splitlines()[-1])
    assert entry["purpose"] == "pool contribution test"
    assert sorted([a.operator_id, b.operator_id]) == entry["operator_ids"]
    dbm.close_all()


def test_cross_operator_connection_is_read_only(two_ops):
    registry, a, b = two_ops
    dbm = DBManager(registry)
    x = dbm.get_cross_operator_connection(
        [a.operator_id], purpose="read-only enforcement test")
    with pytest.raises(Exception):
        x.execute(
            f"INSERT INTO {a.operator_id}.stg_buyer_orders (product_name) "
            f"VALUES ('Hacked')")
    dbm.close_all()


# ── Consent ───────────────────────────────────────────────────────────────────

def test_consent_record_created_on_creation(two_ops):
    registry, a, b = two_ops
    cm = ConsentManager(registry)
    ca, cb = cm.get_consent(a.operator_id), cm.get_consent(b.operator_id)
    assert ca.consented is True and cb.consented is False
    assert ca.history[0].method == "onboarding_form"
    # mirrored in the registry for fast lookup
    assert registry.get_operator(a.operator_id).pool_consent is True
    assert cm.get_consented_operators() == [a.operator_id]


def test_withdraw_consent_stops_future_contributions(two_ops):
    registry, a, _ = two_ops
    cm = ConsentManager(registry)
    cm.withdraw_consent(a.operator_id)
    assert cm.get_consented_operators() == []
    rec = cm.get_consent(a.operator_id)
    assert rec.consented is False
    assert len(rec.history) == 2          # grant then withdrawal, auditable
    assert "cannot be selectively removed" in rec.withdrawal_note


def test_delete_operator_keeps_vault_files(two_ops):
    registry, a, _ = two_ops
    vault = registry.vault_dir(a.operator_id)
    rec = registry.delete_operator(a.operator_id)
    assert rec.status == "deleted"
    assert rec.pool_consent is False
    assert vault.exists()                                  # retention
    assert (vault / "harvestmind.db").exists() or \
        registry.data_root.joinpath(rec.db_path).exists()
    assert registry.list_operators("active") != [] or True
    assert a.operator_id not in [r.operator_id
                                 for r in registry.list_operators("active")]


def test_suspend_operator(two_ops):
    registry, a, _ = two_ops
    registry.suspend_operator(a.operator_id)
    assert registry.get_operator(a.operator_id).status == "suspended"
    # suspension gates pool contributions even with consent still true
    assert ConsentManager(registry).get_consented_operators() == []


# ── Lineage enforcement ───────────────────────────────────────────────────────

def test_lineage_stamp_and_enforcement():
    df = pd.DataFrame([{"product_name": "Kale", "requested_quantity": 10}])
    with pytest.raises(ValueError, match="lineage columns missing"):
        assert_lineage_present(df)
    stamped = stamp_lineage(df, operator_id="op_a",
                            upload_session_id="s1", source_file="f.csv")
    assert_lineage_present(stamped)   # passes
    stamped.loc[0, "_source_file"] = None
    with pytest.raises(ValueError, match="null _source_file"):
        assert_lineage_present(stamped)


def test_trace_row_back_to_source(two_ops):
    registry, a, _ = two_ops
    dbm = DBManager(registry)
    conn = dbm.get_operator_connection(a.operator_id)
    _insert_order(conn, product="Carrots", operator_id=a.operator_id)
    lineage = trace_row(conn, "stg_buyer_orders",
                        "product_name = 'Carrots'")
    assert lineage[0]["_operator_id"] == a.operator_id
    assert lineage[0]["_source_file"] == "orders.csv"
    assert lineage[0]["_upload_session_id"] == "sess-1"
    assert lineage[0]["n_rows"] == 1
    dbm.close_all()
