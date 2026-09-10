"""API edge-case / error-path tests for the HarvestMind FastAPI backend.

Pins response shapes, status codes, query-param validation, and graceful
behaviour on empty / invalid input across every router. The API has no auth
by design — none of these tests authenticate.

Two database fixtures are used:

``full_client``
    Full schema (all migrations + reference seeds) but *no* operational
    rows — dim_suppliers / fact_deliveries / v_fsma_204_report etc. all
    exist and are empty. This is the realistic "operator just onboarded,
    nothing ingested yet" state, and is where list/summary endpoints must
    return 200 with empty/zero-shaped payloads, not 500.

``staging_client``
    Only migration 010 (the five stg_* tables), matching the convention in
    test_confirmation_flow.py. Used for the intake extract/confirm flow.

Real bugs (a 500 where a 4xx/empty is correct) are encoded as the *correct*
behaviour and marked xfail(strict=True) rather than weakening the assertion
or editing source.
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def full_db(tmp_path_factory):
    """Full schema (all migrations + seeds), no operational data."""
    import sys

    sys.path.insert(0, str(ROOT))
    from scripts.setup_db import setup_db

    db_path = tmp_path_factory.mktemp("edgedb") / "empty.duckdb"
    conn = duckdb.connect(str(db_path))
    setup_db(conn, load_seeds=True)
    conn.close()
    return str(db_path)


@pytest.fixture(scope="module")
def full_client(full_db):
    """TestClient bound (via dependency_overrides) to the empty full-schema DB.

    A single shared connection is reused for the module; the get_conn /
    get_readonly_conn overrides hand it out without closing it so it survives
    across requests.
    """
    import api.main as api_main
    from api.dependencies import get_conn, get_readonly_conn

    conn = duckdb.connect(full_db)

    def _override():
        yield conn

    api_main.app.dependency_overrides[get_conn] = _override
    api_main.app.dependency_overrides[get_readonly_conn] = _override
    # training.py and reports.py roi-cards open their own connection via
    # get_db_path() rather than the dependency — point that at our DB too.
    prev = os.environ.get("DUCKDB_PATH")
    os.environ["DUCKDB_PATH"] = full_db
    try:
        yield TestClient(api_main.app)
    finally:
        api_main.app.dependency_overrides.pop(get_conn, None)
        api_main.app.dependency_overrides.pop(get_readonly_conn, None)
        conn.close()
        if prev is None:
            os.environ.pop("DUCKDB_PATH", None)
        else:
            os.environ["DUCKDB_PATH"] = prev


@pytest.fixture()
def staging_client(tmp_path, monkeypatch):
    """Migration-010-only DB, per the test_confirmation_flow convention.

    Also redirects audit / corpus roots to tmp so the intake flow never
    writes into the repo.
    """
    import api.main as api_main
    import ingestion.extraction_sessions as esessions
    import training.data_accumulator as acc
    from api.dependencies import get_conn

    monkeypatch.setattr(esessions, "AUDIT_ROOT", tmp_path / "audit")
    monkeypatch.setattr(acc, "CORPUS_ROOT", tmp_path / "corpus")

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


# ── Health / root + security headers ──────────────────────────────────────────

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}


def test_health_ok(full_client):
    r = full_client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["service"] == "zaad-api"
    assert {"env", "auth_enforced"} <= set(body)      # security posture is reported


def test_root_ok(full_client):
    r = full_client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Zaad Supply"
    assert body["docs"] == "/docs"


@pytest.mark.parametrize("path", ["/health", "/", "/data/suppliers"])
def test_security_headers_present(full_client, path):
    r = full_client.get(path)
    for name, value in SECURITY_HEADERS.items():
        assert r.headers.get(name) == value


# ── GET list endpoints on an empty (full-schema) DB ───────────────────────────


@pytest.mark.parametrize(
    "path",
    [
        "/data/deliveries/recent",
        "/data/orders/weekly-demand",
        "/data/fsma/lots",
        "/data/fsma/report",
    ],
)
def test_data_fact_endpoints_empty_db(full_client, path):
    """No operational (fact/lot) data → 200 with an empty list, never 500."""
    r = full_client.get(path)
    assert r.status_code == 200, r.text
    assert r.json() == []


@pytest.mark.parametrize("path", ["/data/suppliers", "/data/products"])
def test_data_dimension_endpoints_seeded(full_client, path):
    """dim_suppliers / dim_products are populated by reference seeds — the
    endpoint returns a 200 list of records (not a crash, not empty)."""
    r = full_client.get(path)
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list)
    assert body and isinstance(body[0], dict)


def test_data_quality_empty_db(full_client):
    r = full_client.get("/data/quality")
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, dict)
    assert "score" in body


@pytest.mark.parametrize(
    "path",
    [
        "/diagnostics/summary",
        "/diagnostics/waste",
        "/diagnostics/shortage",
        "/diagnostics/suppliers",
        "/diagnostics/buyers",
        "/diagnostics/traceability",
        "/diagnostics/atp",
        "/diagnostics/recommendations",
    ],
)
def test_diagnostics_endpoints_empty_db(full_client, path):
    """Diagnostics over an empty DB return a sane zero-shaped payload."""
    r = full_client.get(path)
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, (dict, list))


@pytest.mark.parametrize(
    "path",
    [
        "/fsma/coverage",
        "/fsma/ftl-products",
        "/fsma/lots",
        "/fsma/recent-ctes",
    ],
)
def test_fsma_read_endpoints_empty_db(full_client, path):
    r = full_client.get(path)
    assert r.status_code == 200, r.text


def test_planning_recommendations_empty_db(full_client):
    r = full_client.get("/planning/recommendations")
    assert r.status_code == 200
    assert r.json() == []


def test_backtest_results_empty_db(full_client):
    """No cached results → 200 with an explanatory message, not 500."""
    r = full_client.get("/backtest/results")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, (dict, list))


def test_pool_status_no_operator(full_client):
    r = full_client.get("/pool/status")
    assert r.status_code == 200
    body = r.json()
    assert "pool" in body
    assert "operator" not in body  # no operator_id supplied


def test_training_corpus_stats_is_hidden_without_admin_key(full_client):
    r = full_client.get("/training/corpus/stats")
    assert r.status_code == 404


# ── Query-param validation (Query(ge=, le=) → 422) ────────────────────────────


@pytest.mark.parametrize(
    "path",
    [
        "/data/deliveries/recent?weeks=0",
        "/data/deliveries/recent?weeks=53",
        "/data/orders/weekly-demand?weeks=0",
        "/data/orders/weekly-demand?weeks=105",
        "/diagnostics/summary?days=0",
        "/diagnostics/summary?days=99999",
        "/diagnostics/waste?days=0",
        "/diagnostics/shortage?days=99999",
        "/forecasts/demand?weeks=0",
        "/forecasts/demand?weeks=14",
        "/forecasts/demand/evaluation?folds=1",
        "/forecasts/demand/evaluation?folds=9",
        "/fsma/recent-ctes?limit=0",
        "/fsma/recent-ctes?limit=201",
        "/reports/diagnostic?days=0",
        "/reports/diagnostic?days=99999",
    ],
)
def test_query_param_out_of_range_returns_422(full_client, path):
    r = full_client.get(path)
    assert r.status_code == 422, f"{path} -> {r.status_code}: {r.text}"


@pytest.mark.parametrize(
    "path",
    [
        "/data/deliveries/recent?weeks=notanumber",
        "/diagnostics/summary?days=abc",
        "/forecasts/demand?weeks=1.5",
    ],
)
def test_query_param_wrong_type_returns_422(full_client, path):
    r = full_client.get(path)
    assert r.status_code == 422, f"{path} -> {r.status_code}: {r.text}"


def test_fsma_report_invalid_format_returns_422(full_client):
    """format is constrained by a regex pattern → 422 on a bad value."""
    r = full_client.get("/fsma/report?format=xml")
    assert r.status_code == 422


def test_fsma_report_chain_requires_tlc(full_client):
    """tlc is a required query param → 422 when omitted."""
    r = full_client.get("/fsma/report/chain")
    assert r.status_code == 422


# ── Unknown-status / unknown-value filters → 400 where code does so ───────────


def test_planning_recommendations_unknown_status_400(full_client):
    r = full_client.get("/planning/recommendations?status=bogus")
    assert r.status_code == 400
    assert "status must be one of" in r.json()["detail"]


@pytest.mark.parametrize("status", ["open", "actioned", "dismissed", "expired"])
def test_planning_recommendations_known_status_200(full_client, status):
    r = full_client.get(f"/planning/recommendations?status={status}")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ── Unknown path params → sane 404 / empty, not 500 ───────────────────────────


def test_fsma_unknown_tlc_report_chain_empty(full_client):
    """Unknown TLC → empty chain (200, []), not a 500."""
    r = full_client.get("/fsma/report/chain?tlc=NO-SUCH-LOT-XYZ")
    assert r.status_code == 200
    assert r.json() == []


def test_fsma_report_unknown_tlc_no_rows(full_client):
    """JSON report for an unknown TLC → 200 empty list."""
    r = full_client.get("/fsma/report?format=json&tlc=NO-SUCH-LOT-XYZ")
    assert r.status_code == 200
    assert r.json() == []


def test_fsma_report_csv_no_data_returns_204(full_client):
    """CSV report with no data rows → 204 No Content."""
    r = full_client.get("/fsma/report?format=csv")
    assert r.status_code == 204


def test_data_fsma_lots_unknown_product_empty(full_client):
    r = full_client.get("/data/fsma/lots?product_id=NO_SUCH_PRODUCT")
    assert r.status_code == 200
    assert r.json() == []


def test_record_cte_unknown_lot_returns_404(full_client):
    """Recording a CTE against an unknown lot_id → 404, not 500."""
    payload = {
        "lot_id": "LOT-DOES-NOT-EXIST",
        "cte_type": "shipping",
        "event_timestamp": "2026-05-01T12:00:00",
        "location_description": "Dock 3",
        "business_name": "Acme Produce",
    }
    r = full_client.post("/fsma/cte/record", json=payload)
    assert r.status_code == 404


def test_intake_session_unknown_id_returns_404(full_client):
    r = full_client.get("/intake/session/no-such-session-id")
    assert r.status_code == 404


# ── Pydantic body validation on write endpoints (4xx, never 500) ──────────────


def test_record_cte_invalid_cte_type_422(full_client):
    payload = {
        "lot_id": "LOT-X",
        "cte_type": "teleporting",  # not in VALID_CTE_TYPES
        "event_timestamp": "2026-05-01T12:00:00",
        "location_description": "Dock 3",
        "business_name": "Acme",
    }
    r = full_client.post("/fsma/cte/record", json=payload)
    assert r.status_code == 422


def test_create_lot_nonpositive_quantity_422(full_client):
    payload = {
        "traceability_lot_code": "TLC-EDGE-1",
        "product_id": "P1",
        "quantity_kg": 0,  # gt=0 → invalid
        "tlc_source_reference": "ref",
    }
    r = full_client.post("/fsma/lots/create", json=payload)
    assert r.status_code == 422


def test_create_lot_missing_required_field_422(full_client):
    payload = {"product_id": "P1", "quantity_kg": 5}  # no TLC / source ref
    r = full_client.post("/fsma/lots/create", json=payload)
    assert r.status_code == 422


def test_planning_run_missing_week_start_422(full_client):
    r = full_client.post("/planning/run", json={})
    assert r.status_code == 422


def test_planning_run_unknown_model_type_422(full_client):
    """model_type is validated by the Pydantic field_validator → 422."""
    r = full_client.post(
        "/planning/run",
        json={"week_start": "2026-05-04", "model_type": "magic"},
    )
    assert r.status_code == 422


def test_planning_run_out_of_range_gamma_422(full_client):
    r = full_client.post(
        "/planning/run",
        json={"week_start": "2026-05-04", "model_type": "gamma_robust",
              "gamma": 999},
    )
    assert r.status_code == 422


@pytest.mark.parametrize("model_type", ["two_stage_sp", "cvar", "robust_cvar"])
def test_legacy_planning_rejects_stochastic_paths(full_client, model_type):
    """There is one stochastic decision path: staging-first /two-sided."""
    r = full_client.post(
        "/planning/run",
        json={"week_start": "2026-05-04", "model_type": model_type},
    )
    assert r.status_code == 422
    assert "/planning/two-sided" in r.json()["detail"]


def test_planning_run_empty_db_no_demand_422(full_client):
    """Valid request but no demand data → 422 (not 500)."""
    r = full_client.post(
        "/planning/run",
        json={"week_start": "2026-05-04", "model_type": "deterministic"},
    )
    assert r.status_code == 422
    assert "No demand data" in r.json()["detail"]


def test_two_sided_plan_is_blocked_without_backtest_history(full_client):
    r = full_client.post("/planning/two-sided")
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["gate_passed"] is None
    assert "blocked" in detail["message"]


def test_two_sided_plan_validates_spot_inputs(full_client):
    r = full_client.post("/planning/two-sided?spot_cost_multiplier=0.5")
    assert r.status_code == 422


def test_backtest_run_invalid_field_422(full_client):
    """Out-of-range n_train_weeks (ge=12) → 422."""
    r = full_client.post("/backtest/run", json={"n_train_weeks": 1})
    assert r.status_code == 422


def test_backtest_run_wrong_type_422(full_client):
    r = full_client.post("/backtest/run", json={"n_scenarios": "lots"})
    assert r.status_code == 422


def test_backtest_run_empty_db_422(full_client):
    """No order history → 422, not a crash. Valid (default) body."""
    r = full_client.post("/backtest/run", json={})
    assert r.status_code == 422
    assert "No order history" in r.json()["detail"]


# ── intake/upload + extract operator validation, clear, status ────────────────


def test_intake_upload_unknown_table_400(staging_client):
    c, _ = staging_client
    r = c.post(
        "/intake/upload/not_a_real_table",
        files=[("file", ("x.csv", "a,b\n1,2\n", "text/csv"))],
    )
    assert r.status_code == 400


def test_intake_upload_non_csv_400(staging_client):
    c, _ = staging_client
    r = c.post(
        "/intake/upload/stg_products",
        files=[("file", ("x.txt", "product_name\nTomato\n", "text/plain"))],
    )
    assert r.status_code == 400


def test_intake_upload_empty_file_400(staging_client):
    c, _ = staging_client
    r = c.post(
        "/intake/upload/stg_products",
        files=[("file", ("x.csv", "", "text/csv"))],
    )
    assert r.status_code == 400


def test_intake_upload_unknown_operator_404(staging_client):
    """operator_id present but unknown → 404 (vault path)."""
    c, _ = staging_client
    r = c.post(
        "/intake/upload/stg_products?operator_id=ghost-operator",
        files=[("file", ("x.csv", "product_name\nTomato\n", "text/csv"))],
    )
    assert r.status_code == 404


def test_intake_extract_unknown_operator_404(staging_client):
    c, _ = staging_client
    r = c.post(
        "/intake/extract?operator_id=ghost-operator",
        files=[("files", ("orders.csv", "a,b\n1,2\n", "text/csv"))],
    )
    assert r.status_code == 404


def test_intake_clear_unknown_table_400(staging_client):
    c, _ = staging_client
    r = c.post("/intake/clear/not_a_real_table")
    assert r.status_code == 400


def test_intake_clear_valid_table_200(staging_client):
    c, _ = staging_client
    r = c.post("/intake/clear/stg_products")
    assert r.status_code == 200
    assert r.json()["status"] == "cleared"


def test_intake_status_shape(staging_client):
    c, _ = staging_client
    r = c.get("/intake/status")
    assert r.status_code == 200
    body = r.json()
    assert "tables" in body
    assert body["any_data_loaded"] is False
    produce = {"stg_products", "stg_supplier_deliveries", "stg_inventory_lots",
               "stg_buyer_orders", "stg_waste_adjustments"}
    assert produce <= set(body["tables"])
    # FMCG staging tables are listed alongside (migration 013).
    assert {"stg_fmcg_skus", "stg_fmcg_orders"} <= set(body["tables"])


def test_intake_oversized_upload_returns_413(staging_client, monkeypatch):
    """An upload above MAX_UPLOAD_BYTES → 413, enforced in-app."""
    import api.routers.intake as intake

    monkeypatch.setattr(intake, "MAX_UPLOAD_BYTES", 16)
    c, _ = staging_client
    big = "product_name\n" + ("Tomato\n" * 50)  # > 16 bytes
    r = c.post(
        "/intake/upload/stg_products",
        files=[("file", ("x.csv", big, "text/csv"))],
    )
    assert r.status_code == 413


# ── intake/confirm malformed-body handling ────────────────────────────────────


def test_confirm_unknown_session_404(staging_client):
    c, _ = staging_client
    r = c.post(
        "/intake/confirm",
        json={"session_id": "nope", "rows": [], "actioned_flag_indices": []},
    )
    assert r.status_code == 404


def test_confirm_empty_body_404(staging_client):
    """No session_id → load_session(None) is None → 404, not 500."""
    c, _ = staging_client
    r = c.post("/intake/confirm", json={})
    assert r.status_code == 404


def test_confirm_wrong_body_type_422(staging_client):
    """body: dict — sending a JSON list should fail validation, not 500."""
    c, _ = staging_client
    r = c.post("/intake/confirm", json=[1, 2, 3])
    assert r.status_code == 422


def test_confirm_invalid_target_table_after_real_session(staging_client):
    """A confirmed row targeting a non-staging table → 400, not a 500.

    Run a real extract first so the session exists, then poison the table
    field on an accepted row.
    """
    c, _ = staging_client
    csv = (
        "Customer,Item,Order Date,Qty Requested,Shipped,Unit Price\n"
        "City Bistro,Roma Tomatoes,2026-05-04,120,100,2.50\n"
    )
    r = c.post("/intake/extract",
               files=[("files", ("orders.csv", csv, "text/csv"))])
    assert r.status_code == 200
    session = r.json()
    payload = {
        "session_id": session["session_id"],
        "rows": [{"row_index": 0, "table": "fact_orders",  # not a stg_ table
                  "fields": {"product_name": "X"}, "accepted": True}],
        "actioned_flag_indices": [
            row["row_index"] for row in session["extracted_rows"]
            if row["requires_confirmation"]
        ],
    }
    r = c.post("/intake/confirm", json=payload)
    assert r.status_code == 400


# ── pool consent / status round-trip ──────────────────────────────────────────


def test_pool_status_unknown_operator_404(full_client):
    r = full_client.get("/pool/status?operator_id=ghost-operator")
    assert r.status_code == 404


def test_pool_consent_unknown_operator_404(full_client):
    r = full_client.post(
        "/pool/consent?operator_id=ghost-operator&consented=true"
    )
    assert r.status_code == 404


def test_pool_consent_missing_params_422(full_client):
    """operator_id and consented are required query params → 422."""
    r = full_client.post("/pool/consent")
    assert r.status_code == 422
