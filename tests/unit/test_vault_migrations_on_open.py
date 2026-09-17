"""A vault created before a migration is brought forward the first time this process opens it."""
from __future__ import annotations

from pathlib import Path

import duckdb

from infrastructure import db_manager
from scripts.setup_db import MIGRATIONS_DIR, _exec_statements


def _old_vault(path: Path, upto: str = "017") -> None:
    conn = duckdb.connect(str(path))
    for mf in sorted(Path(MIGRATIONS_DIR).glob("*.sql")):
        if mf.name[:3] > upto:
            break
        _exec_statements(conn, mf.read_text(), mf.name)
    conn.execute("INSERT INTO stg_fmcg_suppliers (supplier_id, supplier_name) VALUES ('S1', 'One')")
    conn.close()


def _columns(conn, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info('{table}')").fetchall()}


def test_an_old_vault_gains_the_later_columns_when_first_opened(tmp_path):
    path = tmp_path / "old.duckdb"
    _old_vault(path)
    probe = duckdb.connect(str(path))
    assert "risk_group" not in _columns(probe, "stg_fmcg_suppliers")
    probe.close()

    conn = db_manager.vault_cursor(path)
    try:
        cols = _columns(conn, "stg_fmcg_suppliers")
        assert "risk_group" in cols and "origin_iso3" in cols
        assert "zaad_audit_log" in {r[0] for r in conn.execute("SHOW TABLES").fetchall()}
        assert conn.execute("SELECT supplier_name FROM stg_fmcg_suppliers").fetchone()[0] == "One"   # data untouched
        assert str(path.resolve()) in db_manager.migrated_files()
    finally:
        conn.close()
    assert db_manager.release_idle_anchor(path)


def test_migration_on_open_is_idempotent_and_once_per_process(tmp_path):
    path = tmp_path / "current.duckdb"
    _old_vault(path, upto="999")
    first = db_manager.vault_cursor(path)
    first.close()
    before = len(db_manager.migrated_files())
    again = db_manager.vault_cursor(path)
    again.close()
    assert len(db_manager.migrated_files()) == before
    assert db_manager.release_idle_anchor(path)


def test_migration_on_open_can_be_switched_off(tmp_path, monkeypatch):
    monkeypatch.setenv("HARVESTMIND_VAULT_MIGRATE_ON_OPEN", "0")
    path = tmp_path / "frozen.duckdb"
    _old_vault(path)
    conn = db_manager.vault_cursor(path)
    try:
        assert "risk_group" not in _columns(conn, "stg_fmcg_suppliers")
    finally:
        conn.close()
    assert db_manager.release_idle_anchor(path)
