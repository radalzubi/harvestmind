"""Regression tests for the security-hardening pass.

Each test pins a specific fix so the vulnerability/bug cannot silently
return:

  * security response headers are present
  * /intake/confirm enforces the staging-table allowlist (no writes to
    arbitrary tables; no 500 on a missing table key)
  * uploads above the size cap are rejected with 413
  * validate_staging_df fails closed on an unknown table
  * CSV exports neutralize spreadsheet formula injection
  * the audit-summary HTML escapes the operator-supplied partner name
  * compute_roi guards its annualization / percentage denominators
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import api.main as api_main
import ingestion.extraction_sessions as sessions
from api.dependencies import get_conn

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _audit_to_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(sessions, "AUDIT_ROOT", tmp_path / "audit")
    import training.data_accumulator as acc
    monkeypatch.setattr(acc, "CORPUS_ROOT", tmp_path / "corpus")
    yield


@pytest.fixture()
def client():
    conn = duckdb.connect(":memory:")
    migration = ROOT / "db" / "migrations" / "010_diagnostic_staging.sql"
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


def _extract(c: TestClient) -> dict:
    r = c.post("/intake/extract",
               files=[("files", ("orders.csv", CSV, "text/csv"))])
    assert r.status_code == 200, r.text
    return r.json()


def _rows(session: dict) -> list[dict]:
    out = []
    for r in session["extracted_rows"]:
        fields = dict(r["fields"])
        fields.setdefault("substituted_quantity", 0)
        out.append({"row_index": r["row_index"], "table": r["table"],
                    "fields": fields, "accepted": True})
    return out


# ── security headers ─────────────────────────────────────────────────────────

def test_security_headers_present(client):
    c, _ = client
    r = c.get("/health")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "DENY"
    assert r.headers.get("referrer-policy") == "no-referrer"


# ── /intake/confirm table allowlist ──────────────────────────────────────────

def test_confirm_rejects_non_staging_table(client):
    """A confirmed row may not target a non-staging table (e.g. a master
    or fact table). Previously this inserted into whatever table was named."""
    c, conn = client
    session = _extract(c)
    rows = _rows(session)
    rows[0]["table"] = "dim_products"   # not a staging table
    r = c.post("/intake/confirm", json={
        "session_id": session["session_id"], "rows": rows,
        "corrections": [], "actioned_flag_indices": [
            er["row_index"] for er in session["extracted_rows"]
            if er.get("requires_confirmation")],
    })
    assert r.status_code == 400, r.text
    assert "dim_products" in r.text


def test_confirm_rejects_missing_table_key(client):
    """A row with no 'table' key must yield a clean 400, not a 500."""
    c, _ = client
    session = _extract(c)
    rows = _rows(session)
    rows[0].pop("table")
    r = c.post("/intake/confirm", json={
        "session_id": session["session_id"], "rows": rows,
        "corrections": [], "actioned_flag_indices": [
            er["row_index"] for er in session["extracted_rows"]
            if er.get("requires_confirmation")],
    })
    assert r.status_code == 400, r.text


# ── upload size limit ─────────────────────────────────────────────────────────

def test_upload_rejects_oversize_file(client, monkeypatch):
    c, _ = client
    import api.routers.intake as intake_mod
    monkeypatch.setattr(intake_mod, "MAX_UPLOAD_BYTES", 16)
    big = "product_name\n" + ("x" * 100) + "\n"
    r = c.post("/intake/upload/stg_products",
               files=[("file", ("p.csv", big, "text/csv"))])
    assert r.status_code == 413, r.text


# ── validators fail closed ────────────────────────────────────────────────────

def test_validate_staging_df_unknown_table_fails_closed():
    from ingestion.validators import validate_staging_df

    df = pd.DataFrame({"anything": [1, 2, 3]})
    result = validate_staging_df("dim_products", df)
    assert result.ok is False
    assert any("Unknown staging table" in e for e in result.errors)


# ── CSV formula injection ─────────────────────────────────────────────────────

@pytest.mark.parametrize("payload", ["=cmd()", "+1", "-1", "@SUM(A1)", "\tx"])
def test_grant_csv_safe_neutralizes_formula(payload):
    from reports.grant_export import _csv_safe

    assert _csv_safe(payload).startswith("'")


def test_grant_csv_safe_passes_plain_text():
    from reports.grant_export import _csv_safe

    assert _csv_safe("Northside Grocers") == "Northside Grocers"
    assert _csv_safe(1234) == "1234"


def test_audit_csv_cell_and_html_escape():
    from reports import audit_package

    assert audit_package._csv_safe_cell("=HYPERLINK()").startswith("'")
    assert audit_package._csv_safe_cell("plain") == "plain"

    html = audit_package._summary_html(
        "<script>alert(1)</script>", _FakeAudit(), {})
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


class _FakeAudit:
    label = "Test Audit"
    code = "TEST"
    sections: list[str] = []


# ── ROI denominator guards ────────────────────────────────────────────────────

def _roi_df(horizon: float, baseline_spot: float, target_spot: float) -> pd.DataFrame:
    return pd.DataFrame([
        {"model": "deterministic", "origin_week": "2026-01-05",
         "spot_kg": baseline_spot, "waste_kg": 10.0, "spot_cost_usd": 100.0,
         "service_level_pct": 90.0, "horizon_weeks": horizon,
         "total_cost_usd": 1000.0},
        {"model": "two_stage_sp", "origin_week": "2026-01-05",
         "spot_kg": target_spot, "waste_kg": 5.0, "spot_cost_usd": 50.0,
         "service_level_pct": 95.0, "horizon_weeks": horizon,
         "total_cost_usd": 800.0},
    ])


def test_compute_roi_raises_on_zero_horizon():
    from backtesting.roi_calculator import compute_roi

    with pytest.raises(ValueError):
        compute_roi(_roi_df(horizon=0, baseline_spot=20.0, target_spot=5.0))


def test_compute_roi_guards_subkg_spot_denominator():
    """A sub-1kg baseline spot must not blow the percentage up to absurd
    values via a 1e-9 denominator."""
    from backtesting.roi_calculator import compute_roi

    out = compute_roi(_roi_df(horizon=4, baseline_spot=0.5, target_spot=0.0))
    assert out["spot_savings_pct"] == 0.0


def test_compute_roi_normal_case_still_works():
    from backtesting.roi_calculator import compute_roi

    out = compute_roi(_roi_df(horizon=4, baseline_spot=40.0, target_spot=10.0))
    assert out["spot_savings_pct"] == pytest.approx(75.0, abs=0.6)
    assert out["total_annual_benefit_usd"] >= 0
