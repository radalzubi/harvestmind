"""Hostile uploads. The ingestion layer must reject, quarantine or warn —
never silently corrupt, never leak a traceback to the caller."""
from __future__ import annotations

import io

import duckdb
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import api.main as api_main
from api.routers import intake as intake_mod
from ingestion.validators import validate_staging_df


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "root.duckdb"
    monkeypatch.setenv("DUCKDB_PATH", str(db))
    monkeypatch.delenv("HARVESTMIND_AUTH_REQUIRED", raising=False)
    monkeypatch.setenv("HARVESTMIND_ENV", "dev")
    conn = duckdb.connect(str(db))
    from pathlib import Path
    for sql in sorted(Path("db/migrations").glob("*.sql")):
        conn.execute(sql.read_text())
    conn.close()
    return TestClient(api_main.app)


def _upload(client, table, name, content: bytes, ctype="text/csv"):
    return client.post(f"/intake/upload/{table}",
                       files={"file": (name, io.BytesIO(content), ctype)})


GOOD = b"Product Name,Category,Shelf Life (days)\nRomaine,leafy_green,7\nSpinach,leafy_green,5\n"


class TestUploadSurface:
    def test_non_csv_extension_rejected(self, client):
        assert _upload(client, "stg_products", "evil.exe", GOOD).status_code == 400

    def test_unknown_table_rejected_not_500(self, client):
        r = _upload(client, "dim_products; DROP TABLE dim_products", "x.csv", GOOD)
        assert r.status_code in (400, 404, 422)

    def test_empty_file_rejected(self, client):
        assert _upload(client, "stg_products", "x.csv", b"").status_code == 400

    def test_oversize_rejected_with_413(self, client, monkeypatch):
        monkeypatch.setattr(intake_mod, "MAX_UPLOAD_BYTES", 64)
        assert _upload(client, "stg_products", "x.csv", GOOD * 5).status_code == 413

    def test_binary_garbage_is_422_not_500(self, client):
        r = _upload(client, "stg_products", "x.csv", bytes(range(256)) * 4)
        assert r.status_code in (400, 422)
        assert "Traceback" not in r.text and "File \"" not in r.text

    def test_missing_required_column_is_a_clear_rejection(self, client):
        """The upload contract is a rejection REPORT: HTTP 200 with
        rows_inserted == 0 and a named error, so the UI can render it. A
        4xx is also acceptable. What is not acceptable is a load."""
        r = _upload(client, "stg_products", "x.csv", b"Category\nleafy_green\n")
        if r.status_code == 200:
            body = r.json()
            assert body["rows_inserted"] == 0 and body["errors"], body
            assert "product_name" in " ".join(body["errors"]).lower()
        else:
            assert r.status_code in (400, 422)

    def test_traversal_filename_does_not_escape_and_does_not_crash(self, client):
        r = _upload(client, "stg_products", "../../../../etc/passwd.csv", GOOD)
        assert r.status_code in (200, 400, 422)
        assert "Traceback" not in r.text

    def test_unicode_and_bom_are_handled(self, client):
        body = "﻿Product Name,Category\nJalapeño 🌶,pepper\nÇilek,berry\n".encode("utf-8")
        r = _upload(client, "stg_products", "u.csv", body)
        assert r.status_code == 200, r.text
        assert r.json()["rows_inserted"] == 2

    def test_semicolon_delimiter_is_not_silently_one_column(self, client):
        body = b"Product Name;Category\nRomaine;leafy_green\n"
        r = _upload(client, "stg_products", "semi.csv", body)
        # Either parsed correctly, or rejected with the required column named.
        # What must not happen is a load with the header stuffed into one field.
        assert r.status_code in (200, 400, 422)
        if r.status_code == 200:
            b = r.json()
            assert (b["rows_inserted"] >= 1 and not b["errors"]) or \
                   (b["rows_inserted"] == 0 and b["errors"]), b

    def test_unexpected_columns_produce_a_warning_not_an_error(self, client):
        body = b"Product Name,Category,Mystery Column\nRomaine,leafy_green,42\n"
        r = _upload(client, "stg_products", "x.csv", body)
        assert r.status_code == 200
        assert r.json()["rows_inserted"] == 1


class TestValidatorSemantics:
    def test_negative_quantity_is_an_error_with_row_reference(self):
        df = pd.DataFrame({"product_name": ["A", "B"], "requested_quantity": [10, -5],
                           "order_date": ["2026-01-05", "2026-01-05"]})
        res = validate_staging_df("stg_buyer_orders", df)
        assert not res.ok
        assert any("negative" in e.lower() or "-5" in e or ">= 0" in e for e in res.errors), res.errors

    def test_duplicate_rows_are_flagged(self):
        df = pd.DataFrame({"product_name": ["A", "A"], "requested_quantity": [10, 10],
                           "order_date": ["2026-01-05", "2026-01-05"]})
        res = validate_staging_df("stg_buyer_orders", df)
        text = " ".join(res.errors + res.warnings).lower()
        assert "duplicate" in text

    def test_unknown_table_fails_closed(self):
        res = validate_staging_df("dim_products", pd.DataFrame({"a": [1]}))
        assert not res.ok

    def test_future_dated_delivery_is_flagged(self):
        df = pd.DataFrame({"product_name": ["A"], "delivery_date": ["2099-01-01"],
                           "quantity_delivered": [5]})
        res = validate_staging_df("stg_supplier_deliveries", df)
        text = " ".join(res.errors + res.warnings).lower()
        assert "future" in text or "date" in text

    def test_nan_quantities_do_not_pass_as_zero(self):
        df = pd.DataFrame({"product_name": ["A"], "quantity_on_hand": [float("nan")]})
        res = validate_staging_df("stg_inventory_lots", df)
        assert (not res.ok) or res.warnings
