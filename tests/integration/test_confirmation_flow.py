"""Phase 5 integration tests: extract → confirm → staging, end to end.

Exercises the API surface (FastAPI TestClient, in-memory DuckDB) plus
the bulk-accept rule and the real-LLM fallback path — all in mock mode.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

import ingestion.extraction_sessions as sessions
import ingestion.llm_extractor as llm
from api.dependencies import get_conn
import api.main as api_main


@pytest.fixture(autouse=True)
def _audit_to_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(sessions, "AUDIT_ROOT", tmp_path / "audit")
    import training.data_accumulator as acc
    monkeypatch.setattr(acc, "CORPUS_ROOT", tmp_path / "corpus")
    yield


@pytest.fixture()
def client():
    conn = duckdb.connect(":memory:")
    migration = (Path(__file__).resolve().parents[2]
                 / "db" / "migrations" / "010_diagnostic_staging.sql")
    for stmt in migration.read_text().split(";"):
        if stmt.strip():
            try:
                conn.execute(stmt)
            except Exception:  # noqa: BLE001
                pass
    api_main.app.dependency_overrides[get_conn] = lambda: conn
    try:
        yield TestClient(api_main.app), conn
    finally:
        api_main.app.dependency_overrides.pop(get_conn, None)


CSV = (
    "Customer,Item,Order Date,Qty Requested,Shipped,Unit Price\n"
    "City Bistro,Roma Tomatoes,2026-05-04,120,100,2.50\n"
)


def _extract(client) -> dict:
    c, _ = client
    r = c.post("/intake/extract",
               files=[("files", ("orders.csv", CSV, "text/csv"))])
    assert r.status_code == 200
    return r.json()


def _confirm_payload(session: dict) -> dict:
    rows = []
    for r in session["extracted_rows"]:
        fields = dict(r["fields"])
        fields.setdefault("substituted_quantity", 0)
        rows.append({"row_index": r["row_index"], "table": r["table"],
                     "fields": fields, "accepted": True})
    return {
        "session_id": session["session_id"],
        "rows": rows,
        "corrections": [{"field": "sales_price",
                         "llm_predicted": "unit_cost",
                         "operator_corrected": "sales_price",
                         "correction_type": "column_mapping"}],
        "actioned_flag_indices": [r["row_index"]
                                  for r in session["extracted_rows"]
                                  if r["requires_confirmation"]],
    }


def test_extract_confirm_inserts_into_staging(client):
    c, conn = client
    session = _extract(client)
    r = c.post("/intake/confirm", json=_confirm_payload(session))
    assert r.status_code == 200
    body = r.json()
    assert body["rows_inserted"]["stg_buyer_orders"] == 1
    n = conn.execute("SELECT COUNT(*) FROM stg_buyer_orders").fetchone()[0]
    assert n == 1


def test_unconfirmed_flags_block_insert(client):
    """requires_confirmation rows can never flow downstream unactioned."""
    c, conn = client
    session = _extract(client)
    payload = _confirm_payload(session)
    payload["actioned_flag_indices"] = []   # nothing actioned
    r = c.post("/intake/confirm", json=payload)
    assert r.status_code == 409
    n = conn.execute("SELECT COUNT(*) FROM stg_buyer_orders").fetchone()[0]
    assert n == 0


def test_layer1_validation_still_gates_confirmed_rows(client):
    """The LLM layer never bypasses the hard validators: a negative
    quantity in a confirmed row → 422, nothing inserted."""
    c, conn = client
    session = _extract(client)
    payload = _confirm_payload(session)
    payload["rows"][0]["fields"]["requested_quantity"] = -10
    r = c.post("/intake/confirm", json=payload)
    assert r.status_code == 422
    assert "negative" in json.dumps(r.json())
    n = conn.execute("SELECT COUNT(*) FROM stg_buyer_orders").fetchone()[0]
    assert n == 0


def test_correction_recorded_as_gold_label(client):
    c, _ = client
    session = _extract(client)
    c.post("/intake/confirm", json=_confirm_payload(session))
    from training.data_accumulator import load_corpus
    import training.data_accumulator as acc
    entries = load_corpus(acc.CORPUS_ROOT)
    assert len(entries) == 1
    gold = entries[0]["operator_corrections"][0]
    assert gold["correction_type"] == "column_mapping"
    assert gold["operator_corrected"] == "sales_price"


def test_session_snapshot_saved_and_replayable(client):
    c, _ = client
    session = _extract(client)
    c.post("/intake/confirm", json=_confirm_payload(session))
    snap_file = (sessions.AUDIT_ROOT / session["session_id"]
                 / "session_snapshot.json")
    assert snap_file.exists()
    snap = json.loads(snap_file.read_text())
    # replay: the snapshot carries the exact confirmed rows
    assert snap["session_id"] == session["session_id"]
    assert snap["rows"][0]["fields"]["requested_quantity"] == 120
    assert snap["rows"][0]["table"] == "stg_buyer_orders"


def test_get_session_roundtrip(client):
    c, _ = client
    session = _extract(client)
    r = c.get(f"/intake/session/{session['session_id']}")
    assert r.status_code == 200
    assert r.json()["session_id"] == session["session_id"]
    assert c.get("/intake/session/nope").status_code == 404


def test_corpus_stats_endpoint(client):
    c, _ = client
    session = _extract(client)
    c.post("/intake/confirm", json=_confirm_payload(session))
    import training.data_accumulator as acc
    # stats endpoint reads the default roots; call the functions directly
    # against the test root for determinism
    stats = acc.corpus_stats(acc.CORPUS_ROOT)
    assert stats["total_sessions"] == 1
    assert stats["mock_sessions"] == 1   # mock-mode session, never trains


def test_bulk_accept_only_high_confidence_rows():
    """Bulk accept applies ONLY to flagged rows whose every field is
    ≥ 0.90 confidence."""
    from ingestion.llm_extractor import (
        ExtractedRow, ExtractionResult, FieldMeta, bulk_acceptable_rows,
    )

    def row(idx, conf):
        return ExtractedRow(
            row_index=idx, table="stg_buyer_orders",
            fields={"product_name": "X"},
            field_metadata={"product_name": FieldMeta(
                confidence=conf, inference_source="m",
                requires_confirmation=True)},
            requires_confirmation=True)

    res = ExtractionResult(session_id="t", source_files=[])
    res.extracted_rows = [row(0, 0.95), row(1, 0.75), row(2, 0.92)]
    assert bulk_acceptable_rows(res) == [0, 2]


def test_real_llm_failure_falls_back_loudly(tmp_path, monkeypatch):
    """USE_REAL_LLM=True + API failure → deterministic fallback, marked."""
    monkeypatch.setattr(llm, "USE_REAL_LLM", True)

    def boom(payloads, sid):
        raise RuntimeError("simulated API outage")

    monkeypatch.setattr(llm, "_extract_real", boom)
    f = tmp_path / "orders.csv"
    f.write_text(CSV)
    res = llm.extract([f])
    assert res.fallback_used is True
    assert any("fallback" in g for g in res.schema_gaps)
    assert res.extracted_rows   # the deterministic mapper still delivered
