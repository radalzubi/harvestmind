"""Phase B tests: raw-upload immutability, vault-scoped API flows."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import api.main as api_main
import api.routers.intake as intake_router
import ingestion.extraction_sessions as sessions
from infrastructure.operator_registry import OperatorRegistry
from infrastructure.vault_storage import store_raw_upload


@pytest.fixture()
def registry(tmp_path, monkeypatch):
    reg = OperatorRegistry(data_root=tmp_path / "data")
    # the API constructs OperatorRegistry() with defaults — point it here
    import infrastructure.operator_registry as orm
    monkeypatch.setattr(orm, "DEFAULT_DATA_ROOT", tmp_path / "data")
    monkeypatch.setattr(sessions, "AUDIT_ROOT", tmp_path / "audit")
    import training.data_accumulator as acc
    monkeypatch.setattr(acc, "CORPUS_ROOT", tmp_path / "corpus")
    return reg


# Messy headers exercise the smart-upload (LLM) path; the classic
# per-table endpoint expects near-schema headers.
CSV = (
    "Customer,Item,Order Date,Qty Requested,Shipped,Unit Price\n"
    "City Bistro,Roma Tomatoes,2026-05-04,120,100,2.50\n"
)
CLEAN_CSV = (
    "buyer_name,product_name,order_date,delivery_date,"
    "requested_quantity,fulfilled_quantity,sales_price\n"
    "City Bistro,Roma Tomatoes,2026-05-04,2026-05-04,120,100,2.50\n"
)


# ── Raw upload immutability ───────────────────────────────────────────────────

def test_raw_upload_write_once(registry):
    op = registry.create_operator("Hub A")
    p1 = store_raw_upload(registry, op.operator_id, "orders.csv", b"v1")
    p2 = store_raw_upload(registry, op.operator_id, "orders.csv", b"v2")
    assert p1 != p2                       # never overwrite
    assert p1.read_bytes() == b"v1"       # first copy untouched
    assert p2.read_bytes() == b"v2"
    uploads = list((registry.vault_dir(op.operator_id) / "uploads").iterdir())
    assert len(uploads) == 2
    assert registry.get_operator(op.operator_id).upload_count == 2


def test_raw_filename_sanitized(registry):
    op = registry.create_operator("Hub A")
    p = store_raw_upload(registry, op.operator_id,
                         "../../etc/passwd weird name!.csv", b"x")
    assert ".." not in p.name and "/" not in p.name.replace(p.name, p.name)
    assert p.parent == registry.vault_dir(op.operator_id) / "uploads"


# ── API: vault-scoped upload + extract ───────────────────────────────────────

def test_upload_with_operator_id_lands_in_vault_with_lineage(registry):
    op = registry.create_operator("Hub A")
    client = TestClient(api_main.app)
    r = client.post(
        f"/intake/upload/stg_buyer_orders?operator_id={op.operator_id}",
        files={"file": ("orders.csv", CLEAN_CSV, "text/csv")})
    assert r.status_code == 200, r.text
    assert r.json()["rows_inserted"] == 1, r.json()

    # raw copy in the vault
    uploads = list((registry.vault_dir(op.operator_id) / "uploads").iterdir())
    assert len(uploads) == 1
    assert uploads[0].read_text() == CLEAN_CSV

    # row in the VAULT db with full lineage
    from infrastructure.db_manager import DBManager
    dbm = DBManager(registry)
    conn = dbm.get_read_only_connection(op.operator_id)
    row = conn.execute(
        "SELECT _operator_id, _source_file, _upload_session_id "
        "FROM stg_buyer_orders").fetchone()
    assert row[0] == op.operator_id
    assert row[1] == "orders.csv"
    assert row[2] is not None
    dbm.close_all()


def test_upload_with_invalid_operator_id_404(registry):
    client = TestClient(api_main.app)
    r = client.post(
        "/intake/upload/stg_buyer_orders?operator_id=op_nope",
        files={"file": ("orders.csv", CSV, "text/csv")})
    assert r.status_code == 404


def test_extract_confirm_scoped_to_vault(registry):
    op = registry.create_operator("Hub A")
    client = TestClient(api_main.app)
    r = client.post(f"/intake/extract?operator_id={op.operator_id}",
                    files=[("files", ("orders.csv", CSV, "text/csv"))])
    assert r.status_code == 200
    session = r.json()
    assert session["operator_id"] == op.operator_id
    # raw copy stored
    assert len(list((registry.vault_dir(op.operator_id) / "uploads")
                    .iterdir())) == 1

    rows = []
    for er in session["extracted_rows"]:
        fields = dict(er["fields"])
        fields.setdefault("substituted_quantity", 0)
        rows.append({"row_index": er["row_index"], "table": er["table"],
                     "fields": fields, "accepted": True})
    r2 = client.post("/intake/confirm", json={
        "session_id": session["session_id"],
        "operator_id": op.operator_id,
        "rows": rows, "corrections": [],
        "actioned_flag_indices": [er["row_index"]
                                  for er in session["extracted_rows"]
                                  if er["requires_confirmation"]],
    })
    assert r2.status_code == 200, r2.text

    # rows in the vault DB with lineage; snapshot copied to vault sessions/
    from infrastructure.db_manager import DBManager
    dbm = DBManager(registry)
    conn = dbm.get_read_only_connection(op.operator_id)
    n = conn.execute("SELECT COUNT(*) FROM stg_buyer_orders").fetchone()[0]
    assert n == 1
    lid = conn.execute(
        "SELECT _operator_id FROM stg_buyer_orders").fetchone()[0]
    assert lid == op.operator_id
    dbm.close_all()

    snaps = list((registry.vault_dir(op.operator_id) / "sessions").iterdir())
    assert len(snaps) == 1
    snap = json.loads(snaps[0].read_text())
    assert snap["session_id"] == session["session_id"]


def test_legacy_mode_without_operator_id_still_works(registry, tmp_path,
                                                     monkeypatch):
    """No operator_id → the legacy single-operator root DB (dev mode)."""
    import duckdb
    from pathlib import Path
    from api.dependencies import get_conn

    conn = duckdb.connect(":memory:")
    mig = (Path(api_main.__file__).resolve().parents[1]
           / "db" / "migrations" / "010_diagnostic_staging.sql")
    for stmt in mig.read_text().split(";"):
        if stmt.strip():
            try:
                conn.execute(stmt)
            except Exception:  # noqa: BLE001
                pass
    api_main.app.dependency_overrides[get_conn] = lambda: conn
    try:
        client = TestClient(api_main.app)
        r = client.post("/intake/upload/stg_buyer_orders",
                        files={"file": ("orders.csv", CLEAN_CSV, "text/csv")})
        assert r.status_code == 200
        assert r.json()["rows_inserted"] == 1, r.json()
        # and no vault was touched
        assert not (tmp_path / "data" / "operators").exists() or \
            list((tmp_path / "data" / "operators").iterdir()) == []
    finally:
        api_main.app.dependency_overrides.pop(get_conn, None)
