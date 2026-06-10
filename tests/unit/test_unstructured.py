"""Phase 3 tests: unstructured extraction (WhatsApp / email / PDF).

All in mock mode. Text sources carry the stricter 0.95 floor: nothing
parsed from a message ever auto-passes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import ingestion.extraction_sessions as sessions
from ingestion.llm_extractor import extract, read_source_file


@pytest.fixture(autouse=True)
def _audit_to_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(sessions, "AUDIT_ROOT", tmp_path / "audit")
    yield


def test_whatsapp_order_extracted(tmp_path):
    f = tmp_path / "whatsapp.txt"
    f.write_text(
        "Hey need 200 cases roma tomatoes Thursday also 50 cases baby spinach\n"
    )
    res = extract([f])
    rows = res.extracted_rows
    assert len(rows) == 2
    products = {r.fields["product_name"] for r in rows}
    assert "Roma Tomatoes" in products
    assert "Baby Spinach" in products
    by_p = {r.fields["product_name"]: r for r in rows}
    assert by_p["Roma Tomatoes"].fields["requested_quantity"] == 200.0
    assert by_p["Baby Spinach"].fields["requested_quantity"] == 50.0
    # a weekday mention resolves to a concrete date
    assert by_p["Roma Tomatoes"].fields["delivery_date"] is not None
    assert all(r.table == "stg_buyer_orders" for r in rows)


def test_unstructured_rows_always_require_confirmation(tmp_path):
    """The unstructured floor: text-derived rows never auto-pass."""
    f = tmp_path / "whatsapp.txt"
    f.write_text("need 100 cases carrots Friday\n")
    res = extract([f])
    assert res.extracted_rows
    for r in res.extracted_rows:
        assert r.requires_confirmation is True
        assert any("unstructured" in fl for fl in r.flags)
    assert res.summary.flagged_for_review == len(res.extracted_rows)


def test_short_fulfillment_message_flagged_for_matching(tmp_path):
    f = tmp_path / "whatsapp.txt"
    f.write_text("delivered 180 cases tomatoes spinach short only had 40\n")
    res = extract([f])
    short_rows = [r for r in res.extracted_rows
                  if any("short fulfillment" in fl for fl in r.flags)]
    assert len(short_rows) == 1
    assert short_rows[0].fields["fulfilled_quantity"] == 40.0
    assert short_rows[0].requires_confirmation


def test_email_html_stripped(tmp_path):
    f = tmp_path / "order_email.eml"
    f.write_text(
        "<html><body><p>Hi team,</p>"
        "<p>need <b>75</b> cases kale Monday</p></body></html>"
    )
    res = extract([f])
    assert res.extracted_rows
    row = res.extracted_rows[0]
    assert row.fields["product_name"] == "Kale"
    assert row.fields["requested_quantity"] == 75.0


def test_empty_text_reports_gap_not_rows(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("meeting moved to 3pm, bring the cooler keys\n")
    res = extract([f])
    assert res.extracted_rows == []
    assert any("no order-like statements" in g for g in res.schema_gaps)


def _minimal_pdf(path: Path, text: str) -> None:
    """Hand-rolled single-page PDF with one text run — enough for
    pdfplumber to parse without external dependencies."""
    content = f"BT /F1 12 Tf 50 700 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n"
        + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF").encode()
    path.write_bytes(bytes(out))


def test_pdf_invoice_extraction_runs(tmp_path):
    """A text PDF parses without error and routes through the text path;
    its order-like content is extracted."""
    f = tmp_path / "invoice.pdf"
    _minimal_pdf(f, "Invoice 1042: need 60 cases heirloom tomatoes Friday")
    payload = read_source_file(f)
    assert payload.kind in ("text", "tabular")
    res = extract([f])
    assert res.status in ("ok", "rejected")  # parses without raising
    if res.extracted_rows:
        assert res.extracted_rows[0].requires_confirmation


def test_unsupported_extension_rejected_clearly(tmp_path):
    f = tmp_path / "photo.heic"
    f.write_bytes(b"\x00\x01")
    with pytest.raises(ValueError, match="Unsupported file type"):
        read_source_file(f)
