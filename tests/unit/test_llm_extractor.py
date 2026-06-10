"""LLM extraction layer — Phase 1 tests.

Everything here runs in MOCK MODE: no API key, no API calls. Each
non-negotiable safeguard has a direct test.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

import ingestion.extraction_sessions as sessions
from ingestion.llm_extractor import (
    ExtractedRow,
    ExtractionResult,
    FieldMapping,
    FieldMeta,
    apply_confidence_policy,
    extract,
)


@pytest.fixture(autouse=True)
def _audit_to_tmp(tmp_path, monkeypatch):
    """Route the audit log to a temp dir for every test."""
    monkeypatch.setattr(sessions, "AUDIT_ROOT", tmp_path / "audit")
    yield


def _write_csv(tmp_path: Path, name: str, header: str, rows: list[str]) -> Path:
    p = tmp_path / name
    p.write_text(header + "\n" + "\n".join(rows) + "\n")
    return p


# ── Clean + messy mapping ─────────────────────────────────────────────────────

def test_clean_csv_maps_without_flags(tmp_path):
    f = _write_csv(
        tmp_path, "deliveries.csv",
        "supplier_name,product_name,delivery_date,ordered_quantity,"
        "delivered_quantity,accepted_quantity,rejected_quantity,unit_cost",
        ["Good Farms,Tomatoes,2026-05-01,100,100,100,0,2.10",
         "Good Farms,Kale,2026-05-02,50,50,50,0,3.00"],
    )
    res = extract([f])
    assert res.mock_mode is True
    assert res.status == "ok"
    rows = [r for r in res.extracted_rows if not r.rejected]
    assert len(rows) == 2
    assert all(r.table == "stg_supplier_deliveries" for r in rows)
    # exact schema headers → high confidence, no review flags except the
    # generated supplier/product id slugs (rule 2 always confirms ids)
    non_id_flags = [
        (f_, m) for r in rows for f_, m in r.field_metadata.items()
        if m.requires_confirmation and not f_.endswith("_id")
    ]
    assert non_id_flags == []


def test_messy_csv_maps_with_confidence_spread(tmp_path):
    f = _write_csv(
        tmp_path, "weekly orders export.csv",
        "Customer,Item,Order Date,Qty Requested,Shipped,Unit Price",
        ["City Bistro,Roma Tomatoes,2026-05-04,120,100,2.50",
         "Hotel Grand,Baby Spinach,2026-05-04,40,40,4.10"],
    )
    res = extract([f])
    assert res.status == "ok"
    rows = [r for r in res.extracted_rows if not r.rejected]
    assert all(r.table == "stg_buyer_orders" for r in rows)
    by_target = {m.target_field: m for m in res.column_mappings}
    assert by_target["buyer_name"].confidence >= 0.90
    assert by_target["requested_quantity"].confidence >= 0.90
    assert by_target["sales_price"].confidence >= 0.90
    # confidences are recorded per field on every row
    assert all(r.field_metadata for r in rows)


def test_missing_fields_reported_not_hallucinated(tmp_path):
    f = _write_csv(
        tmp_path, "orders.csv",
        "buyer_name,product_name,requested_quantity",
        ["School District,Carrots,200"],
    )
    res = extract([f])
    row = res.extracted_rows[0]
    # absent fields are simply absent / null — never invented
    assert row.fields.get("sales_price") is None
    assert row.fields.get("delivery_date") is None
    # and the thin coverage is surfaced as a sufficiency warning (S3)
    assert any("stg_buyer_orders" in w for w in res.sufficiency_warnings)


def test_unmappable_file_is_skipped_not_invented(tmp_path):
    f = _write_csv(tmp_path, "random.csv", "alpha,beta,gamma",
                   ["1,2,3"])
    res = extract([f])
    assert res.extracted_rows == []
    assert any("no staging table matches" in g for g in res.schema_gaps)
    assert set(res.unmapped_columns) == {"alpha", "beta", "gamma"}


def test_supplier_master_columns_flagged_as_gap(tmp_path):
    f = _write_csv(
        tmp_path, "suppliers.csv",
        "supplier_name,product_name,delivery_date,ordered_quantity,"
        "Contact Email,Payment Terms",
        ["Good Farms,Tomatoes,2026-05-01,100,info@goodfarms.com,Net 30"],
    )
    res = extract([f])
    gaps = " ".join(res.schema_gaps)
    assert "supplier master" in gaps
    assert "Contact Email" in res.unmapped_columns


# ── Rule 7: ambiguous dates ───────────────────────────────────────────────────

def test_ambiguous_date_flagged_with_both_interpretations(tmp_path):
    f = _write_csv(
        tmp_path, "deliveries.csv",
        "supplier_name,product_name,delivery_date,ordered_quantity,"
        "delivered_quantity",
        ["Farm A,Tomatoes,01/02/2026,100,100",
         "Farm A,Tomatoes,2026-05-02,90,90"],
    )
    res = extract([f])
    flagged = [r for r in res.extracted_rows
               if any("ambiguous date" in fl for fl in r.flags)]
    assert len(flagged) == 1
    flag = next(fl for fl in flagged[0].flags if "ambiguous date" in fl)
    assert "2026-01-02" in flag and "2026-02-01" in flag
    assert flagged[0].requires_confirmation


# ── Safeguard 2: consistency checks ──────────────────────────────────────────

def test_quantity_outlier_flagged(tmp_path):
    rows = [f"Farm A,Tomatoes,2026-05-0{i},100,100" for i in range(1, 6)]
    rows.append("Farm A,Tomatoes,2026-05-06,5000,5000")  # 50× the median
    f = _write_csv(
        tmp_path, "deliveries.csv",
        "supplier_name,product_name,delivery_date,ordered_quantity,"
        "delivered_quantity", rows,
    )
    res = extract([f])
    assert any("×" in fl and "median" in fl
               for r in res.extracted_rows for fl in r.flags)


def test_expiration_before_arrival_rejected(tmp_path):
    f = _write_csv(
        tmp_path, "lots.csv",
        "lot_id,product_name,quantity_on_hand,arrival_date,expiration_date",
        ["L1,Tomatoes,100,2026-05-10,2026-05-01",   # reversed → reject
         "L2,Tomatoes,80,2026-05-10,2026-05-20"],
    )
    res = extract([f])
    rejected = [r for r in res.extracted_rows if r.rejected]
    assert len(rejected) == 1
    assert "precedes arrival_date" in rejected[0].rejection_reason
    assert res.summary.rejected == 1


def test_negative_quantity_rejected(tmp_path):
    f = _write_csv(
        tmp_path, "orders.csv",
        "buyer_name,product_name,delivery_date,requested_quantity,"
        "fulfilled_quantity",
        ["Bistro,Tomatoes,2026-05-01,-50,0"],
    )
    res = extract([f])
    assert res.extracted_rows[0].rejected
    assert "negative" in res.extracted_rows[0].rejection_reason


def test_fulfilled_far_over_requested_flagged(tmp_path):
    f = _write_csv(
        tmp_path, "orders.csv",
        "buyer_name,product_name,delivery_date,requested_quantity,"
        "fulfilled_quantity",
        ["Bistro,Tomatoes,2026-05-01,100,150"],   # 1.5× requested
    )
    res = extract([f])
    assert any("unit mismatch" in fl
               for fl in res.extracted_rows[0].flags)


# ── Safeguard 4: confidence floor ────────────────────────────────────────────

def test_low_overall_confidence_rejects_extraction():
    res = ExtractionResult(session_id="t", source_files=["x.csv"])
    res.column_mappings = [
        FieldMapping(source_column=f"c{i}", target_field="product_name",
                     confidence=0.5, reasoning="weak")
        for i in range(4)
    ]
    res.extracted_rows = [ExtractedRow(
        row_index=0, table="stg_buyer_orders",
        fields={"product_name": "x"},
        field_metadata={"product_name": FieldMeta(
            confidence=0.5, inference_source="weak",
            requires_confirmation=True)},
    )]
    res = apply_confidence_policy(res)
    assert res.status == "rejected"
    assert "below" in res.rejection_guidance
    assert "Nothing was loaded" in res.rejection_guidance


def test_uncertain_field_blanked_for_operator():
    res = ExtractionResult(session_id="t", source_files=["x.csv"])
    res.extracted_rows = [ExtractedRow(
        row_index=0, table="stg_buyer_orders",
        fields={"product_name": "Tomatoes", "sales_price": 9.99},
        field_metadata={
            "product_name": FieldMeta(confidence=0.95,
                                      inference_source="alias",
                                      requires_confirmation=False),
            "sales_price": FieldMeta(confidence=0.60,
                                     inference_source="weak fuzzy",
                                     requires_confirmation=False),
        },
    )]
    res = apply_confidence_policy(res)
    row = res.extracted_rows[0]
    assert row.fields["sales_price"] is None          # blanked
    assert row.field_metadata["sales_price"].requires_confirmation
    assert row.requires_confirmation


# ── Rule 5: derivations carry their arithmetic (S1) ──────────────────────────

def test_missed_fulfillment_inference_tagged(tmp_path):
    f = _write_csv(
        tmp_path, "orders.csv",
        "buyer_name,product_name,delivery_date,requested_quantity,"
        "fulfilled_quantity",
        ["Bistro,Tomatoes,2026-05-01,100,80"],
    )
    res = extract([f])
    row = res.extracted_rows[0]
    assert any("missed fulfillment inferred: 20" in fl for fl in row.flags)
    meta = row.field_metadata["_missed_inferred"]
    assert meta.inference_source.startswith("derived:")


def test_accepted_derived_from_delivered_minus_rejected(tmp_path):
    f = _write_csv(
        tmp_path, "deliveries.csv",
        "supplier_name,product_name,delivery_date,ordered_quantity,"
        "delivered_quantity,rejected_quantity",
        ["Farm A,Tomatoes,2026-05-01,100,95,5"],
    )
    res = extract([f])
    row = res.extracted_rows[0]
    assert row.fields["accepted_quantity"] == 90.0
    meta = row.field_metadata["accepted_quantity"]
    assert "derived: delivered_quantity − rejected_quantity" \
        in meta.inference_source
    assert meta.requires_confirmation


# ── Safeguard 8: multi-file reconciliation ───────────────────────────────────

def test_multi_file_reconciliation_flags_unmatched(tmp_path):
    orders = _write_csv(
        tmp_path, "orders.csv",
        "buyer_name,product_name,delivery_date,requested_quantity,"
        "fulfilled_quantity",
        ["Bistro,Tomatoes,2026-05-04,100,100",
         "Bistro,Dragonfruit,2026-05-04,10,10"],   # no matching delivery
    )
    deliveries = _write_csv(
        tmp_path, "deliveries.csv",
        "supplier_name,product_name,delivery_date,ordered_quantity,"
        "delivered_quantity",
        ["Farm A,Tomatoes,2026-05-04,120,120"],
    )
    res = extract([orders, deliveries])
    gaps = " ".join(res.schema_gaps)
    assert "dragonfruit" in gaps
    assert "no matching supplier deliveries" in gaps


# ── Safeguard 6: PII scrubbing ───────────────────────────────────────────────

def test_pii_scrubbed_before_logging(tmp_path):
    f = _write_csv(
        tmp_path, "orders.csv",
        "buyer_name,product_name,delivery_date,requested_quantity,"
        "fulfilled_quantity,notes",
        ["Bistro,Tomatoes,2026-05-01,100,100,"
         "call john@bistro.com or 312-555-1234"],
    )
    res = extract([f])
    d = sessions.AUDIT_ROOT / res.session_id
    logged = (d / "input_samples.json").read_text() + \
        (d / "result.json").read_text()
    assert "john@bistro.com" not in logged
    assert "312-555-1234" not in logged
    assert "[EMAIL_REDACTED]" in logged or "[PHONE_REDACTED]" in logged


def test_taxid_flags_manual_review(tmp_path):
    f = _write_csv(
        tmp_path, "orders.csv",
        "buyer_name,product_name,delivery_date,requested_quantity,"
        "fulfilled_quantity,notes",
        ["Bistro,Tomatoes,2026-05-01,100,100,EIN 12-3456789"],
    )
    res = extract([f])
    meta = json.loads(
        (sessions.AUDIT_ROOT / res.session_id / "meta.json").read_text())
    assert meta["pii_taxid_flag_manual_review"] is True
    assert "12-3456789" not in json.dumps(meta)


# ── Safeguard 5: immutable audit log ─────────────────────────────────────────

def test_audit_log_never_overwrites(tmp_path):
    f = _write_csv(
        tmp_path, "orders.csv",
        "buyer_name,product_name,delivery_date,requested_quantity,"
        "fulfilled_quantity",
        ["Bistro,Tomatoes,2026-05-01,100,100"],
    )
    res1 = extract([f], session_id="ext-fixed")
    res2 = extract([f], session_id="ext-fixed")
    d = sessions.AUDIT_ROOT / "ext-fixed"
    assert (d / "result.json").exists()
    assert (d / "result.rev1.json").exists()   # second write → revision
    assert res1.session_id == res2.session_id


def test_mock_sessions_logged_with_zero_cost(tmp_path):
    f = _write_csv(
        tmp_path, "orders.csv",
        "buyer_name,product_name,delivery_date,requested_quantity,"
        "fulfilled_quantity",
        ["Bistro,Tomatoes,2026-05-01,100,100"],
    )
    res = extract([f])
    meta = json.loads(
        (sessions.AUDIT_ROOT / res.session_id / "meta.json").read_text())
    assert meta["mock_mode"] is True
    assert meta["api_tokens"] == 0
    assert meta["api_cost_usd"] == 0.0


# ── Config: real mode without key fails loudly ───────────────────────────────

def test_real_llm_without_key_raises(monkeypatch):
    monkeypatch.setenv("USE_REAL_LLM", "true")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    import config.llm_config as cfg
    with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY"):
        importlib.reload(cfg)
    # restore module state for the rest of the suite
    monkeypatch.setenv("USE_REAL_LLM", "false")
    importlib.reload(cfg)


def test_mock_mode_flag_present_everywhere(tmp_path):
    f = _write_csv(
        tmp_path, "orders.csv",
        "buyer_name,product_name,delivery_date,requested_quantity,"
        "fulfilled_quantity",
        ["Bistro,Tomatoes,2026-05-01,100,100"],
    )
    res = extract([f])
    assert res.mock_mode is True
    assert res.prompt_version == "EXTRACTION_PROMPT_V1"
    assert res.summary.estimated_api_cost_usd == 0.0


# ── Determinism ──────────────────────────────────────────────────────────────

def test_mock_extraction_is_deterministic(tmp_path):
    f = _write_csv(
        tmp_path, "orders.csv",
        "Customer,Item,Order Date,Qty Requested,Shipped,Unit Price",
        ["City Bistro,Roma Tomatoes,2026-05-04,120,100,2.50"],
    )
    r1 = extract([f], session_id="ext-d1")
    r2 = extract([f], session_id="ext-d1")
    d1 = r1.model_dump(exclude={"extraction_timestamp", "session_id"})
    d2 = r2.model_dump(exclude={"extraction_timestamp", "session_id"})
    assert d1 == d2
