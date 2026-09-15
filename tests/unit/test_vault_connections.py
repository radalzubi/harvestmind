"""One database instance per vault file, for the life of the process.

Every request used to open its own ``duckdb.connect(path)``; when the last open connection closed
while another request was connecting to the same file, DuckDB's instance cache missed and the new
instance failed with ``Unique file handle conflict``. That was a 500 on an ordinary page load
whenever two requests to one workspace overlapped — observed three times in one browsing session
of the operating product, and reproduced at 712 failures in ten seconds with two writers and six
readers. These tests hold the fix: a cursor on one anchor per file, no re-attach, ever.
"""
from __future__ import annotations

import threading
import time

import duckdb
import pytest

import infrastructure.db_manager as dbm
import infrastructure.operator_registry as orm


@pytest.fixture()
def registry(tmp_path, monkeypatch):
    monkeypatch.setattr(orm, "DEFAULT_DATA_ROOT", tmp_path / "data")
    reg = orm.OperatorRegistry(data_root=tmp_path / "data")
    return reg


def _prepare(reg: orm.OperatorRegistry, operator_id: str) -> None:
    conn = duckdb.connect(str(reg.get_db_path(operator_id)))
    conn.execute("CREATE TABLE IF NOT EXISTS t (i INTEGER)")
    conn.execute("INSERT INTO t SELECT range FROM range(100)")
    conn.close()


def test_two_writers_and_six_readers_on_one_vault_never_conflict(registry):
    """The storm that produced 712 'Unique file handle conflict' errors before the anchor."""
    op = registry.create_operator("Storm").operator_id
    _prepare(registry, op)
    errors: list[str] = []
    done = [0, 0]
    stop = time.time() + 3.0

    def writer():
        while time.time() < stop:
            m = dbm.DBManager(registry)
            try:
                c = m.get_operator_connection(op)
                c.execute("INSERT INTO t SELECT range FROM range(200)")
                done[1] += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(f"W {type(exc).__name__}: {exc}"[:120])
            finally:
                m.close_all()

    def reader():
        while time.time() < stop:
            m = dbm.DBManager(registry)
            try:
                c = m.get_operator_connection(op)
                c.execute("SELECT count(*) FROM t").fetchone()
                done[0] += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(f"R {type(exc).__name__}: {exc}"[:120])
            finally:
                m.close_all()

    threads = [threading.Thread(target=writer) for _ in range(2)] + [threading.Thread(target=reader) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert done[0] > 100 and done[1] > 10, "the storm did not run"
    assert errors == [], errors[:5]


def test_one_anchor_per_file_and_cursors_are_independent_transactions(registry):
    op = registry.create_operator("Anchor").operator_id
    _prepare(registry, op)
    a, b = dbm.DBManager(registry), dbm.DBManager(registry)
    ca, cb = a.get_operator_connection(op), b.get_operator_connection(op)
    key = str(registry.get_db_path(op).resolve())
    assert dbm.anchored_files().count(key) == 1
    assert dbm._LIVE[key] == 2
    ca.begin()
    ca.execute("INSERT INTO t VALUES (-1)")
    assert cb.execute("SELECT count(*) FROM t WHERE i = -1").fetchone()[0] == 0, "an uncommitted write leaked to another request"
    ca.rollback()
    a.close_all()
    b.close_all()
    assert dbm._LIVE[key] == 0
    # and the file stays attached: the next request is a cursor on the same anchor, not a re-attach
    c = dbm.DBManager(registry)
    c.get_operator_connection(op).execute("SELECT 1").fetchone()
    c.close_all()
    assert dbm.anchored_files().count(key) == 1


def test_read_only_requests_share_the_anchor(registry):
    """DuckDB refuses a read-only open beside a read-write one; the read-only path must not try."""
    op = registry.create_operator("ReadOnly").operator_id
    _prepare(registry, op)
    rw, ro = dbm.DBManager(registry), dbm.DBManager(registry)
    rw.get_operator_connection(op)
    ro.get_read_only_connection(op).execute("SELECT count(*) FROM t").fetchone()
    rw.close_all()
    ro.close_all()


def test_idle_anchors_are_evicted_at_the_bound_but_live_ones_are_kept(registry, monkeypatch):
    monkeypatch.setattr(dbm, "MAX_ANCHORS", 2)
    ops = [registry.create_operator(f"Bound {i}").operator_id for i in range(3)]
    for op in ops:
        _prepare(registry, op)
    keys = [str(registry.get_db_path(op).resolve()) for op in ops]
    first = dbm.DBManager(registry)
    first.get_operator_connection(ops[0])          # live cursor: must never be evicted
    second = dbm.DBManager(registry)
    second.get_operator_connection(ops[1])
    second.close_all()                             # idle: eligible
    third = dbm.DBManager(registry)
    third.get_operator_connection(ops[2])          # forces eviction
    anchored = dbm.anchored_files()
    assert keys[0] in anchored, "an anchor with an open cursor was closed"
    assert keys[2] in anchored
    assert keys[1] not in anchored, "the idle anchor should have been evicted at the bound"
    first.close_all()
    third.close_all()
