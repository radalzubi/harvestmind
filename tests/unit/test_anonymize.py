from __future__ import annotations

import pandas as pd
import pytest

from ingestion.anonymize import anonymize_csv_bytes, anonymize_frame, hash_id, looks_anonymized


def test_ids_hashed_consistently_names_dropped_numbers_untouched():
    po = pd.DataFrame({"po_id": ["PO1", "PO2"], "supplier_id": ["S1", "S2"], "supplier_name": ["Acme", "Beta"],
                       "sku": ["A", "B"], "qty_ordered": [10, 20], "po_date": ["2026-01-01", "2026-01-02"]})
    rec = pd.DataFrame({"po_id": ["PO1", "PO2"], "sku": ["A", "B"], "qty_received": [9, 20], "notes": ["late", ""]})
    a, ra = anonymize_frame(po, "s3cret-passphrase")
    b, rb = anonymize_frame(rec, "s3cret-passphrase")
    assert "notes" not in b.columns
    assert a["supplier_name"][0] != "Acme" and len(a["supplier_name"][0]) == 16   # key-like names are hashed
    assert list(a["po_id"]) == list(b["po_id"])                  # joins survive
    assert a["po_id"][0] != "PO1" and len(a["po_id"][0]) == 16
    assert list(a["qty_ordered"]) == [10, 20] and list(a["po_date"]) == ["2026-01-01", "2026-01-02"]
    assert set(ra.hashed_columns) == {"po_id", "supplier_id", "sku", "supplier_name"} and ra.dropped_columns == []
    assert looks_anonymized(a) and looks_anonymized(b) and not looks_anonymized(po)


def test_different_secret_different_hash_and_secret_required():
    assert hash_id("A", "one-secret-here") != hash_id("A", "two-secret-here")
    with pytest.raises(ValueError):
        anonymize_frame(pd.DataFrame({"sku": ["A"]}), "")


def test_csv_roundtrip_bytes():
    raw = b"sku,customer_id,customer_name,qty\nA,C1,Alice,5\n"
    out, rep = anonymize_csv_bytes(raw, "s3cret-passphrase")
    df = pd.read_csv(pd.io.common.BytesIO(out))
    assert df["customer_name"][0] != "Alice" and df["qty"][0] == 5 and len(df["sku"][0]) == 16
