"""Exports stay inert (SEC-013 / SEC-014); customer-facing errors and headers carry no internals (SEC-024/25/26/27)."""
from __future__ import annotations

import json

from tests.security.conftest import Tenants


def test_pdf_escapes_markup_in_customer_fields(monkeypatch):
    from api.product import exporting
    seen: list[str] = []
    import reportlab.platypus as platypus
    real = platypus.Paragraph

    class Spy(real):  # type: ignore[misc]
        def __init__(self, text, *a, **k):
            seen.append(str(text))
            super().__init__(text, *a, **k)
    monkeypatch.setattr(platypus, "Paragraph", Spy)
    draft = {"draft_id": "d1", "reference": '<img src="file:///etc/passwd"/>PO-1', "supplier_id": "<b>SUP</b>&", "destination_id": "DC<1>",
             "notes": '<img src="http://169.254.169.254/latest/meta-data"/> note', "revision": 1, "lines": [{"sku": "SKU-1", "quantity": 1, "unit_price": 1.0}],
             "status": "APPROVED", "created_at": "2026-09-25T00:00:00"}
    profile = {"columns": [{"header": "SKU", "field": "sku"}, {"header": "Qty", "field": "quantity"}], "name": "p"}
    out = exporting.to_pdf(draft, profile, workspace="<W>")
    assert out[:4] == b"%PDF"
    joined = "\n".join(seen)
    assert "<img" not in joined and "&lt;img" in joined
    assert "<b>SUP</b>" not in joined


def test_server_csv_export_is_formula_safe():
    from api.product.exporting import safe_cell
    for cell in ("=HYPERLINK(\"x\")", "+1", "-1", "@SUM(A1)", "\tx", "\rx"):
        assert not safe_cell(cell).startswith(cell[0]) or safe_cell(cell).startswith("'"), safe_cell(cell)


def test_tenant_responses_are_never_cacheable_and_ids_are_bounded(tenants: Tenants):
    c, a = tenants.client, tenants.a
    r = c.get("/api/zaad/workspace/summary", headers=a.h())
    assert r.headers.get("cache-control") == "no-store"
    assert r.headers["x-request-id"]
    r = c.get("/health", headers={"X-Request-ID": "a" * 500})
    assert r.headers["x-request-id"] != "a" * 500 and len(r.headers["x-request-id"]) <= 64
    r = c.get("/health", headers={"X-Request-ID": "trace-abc.123_x"})
    assert r.headers["x-request-id"] == "trace-abc.123_x"
    r = c.get("/health", headers={"X-Request-ID": "<script>alert(1)</script>"})
    assert "<" not in r.headers["x-request-id"]


def test_schema_and_docs_are_not_published_when_auth_is_enforced(tenants: Tenants):
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert tenants.client.get(path).status_code == 404, path


def test_broken_requests_do_not_expose_internals(tenants: Tenants):
    c, a = tenants.client, tenants.a
    probes = [
        c.post("/api/zaad/analytics/query", headers={**a.h("ADMIN"), "Content-Type": "application/json"}, content=b"{not json"),
        c.post("/api/zaad/analytics/query", headers=a.h("ADMIN"), json={"measures": [{"metric_id": "no_such_metric"}]}),
        c.post("/api/zaad/analytics/query", headers=a.h("ADMIN"), json={"measures": [{"metric_id": "ordered_units"}], "filters": [{"dimension_id": "supplier", "op": "in", "values": ["' OR 1=1 --"]}]}),
        c.get("/api/zaad/analytics/dimensions/'; DROP TABLE x; --/members", headers=a.h("ADMIN")),
        c.get("/api/zaad/workspace/datasets/../../etc/passwd", headers=a.h("ADMIN")),
        c.post("/intake/upload/not_a_table", headers=a.h("BUYER"), files={"file": ("x.csv", b"a\n1\n", "text/csv")}),
        c.post("/api/zaad/orders", headers={**a.h("BUYER"), "Content-Type": "application/json"}, content=b'{"lines": ' + b"[" * 3000 + b"]" * 3000 + b"}"),
        c.get("/ready"),
        c.get("/api/zaad/analytics/metrics/%00", headers=a.h("ADMIN")),
    ]
    for r in probes:
        body = r.text
        assert r.status_code < 500 or r.status_code == 503, (r.status_code, body[:200])
        for marker in ("Traceback", "/app/", "/Users/", "duckdb.", "site-packages", "File \"", "ANTHROPIC", "HARVESTMIND_"):
            assert marker not in body, (marker, body[:300])


def test_reports_carry_no_tokens_or_paths(tenants: Tenants):
    """A finished job's report and PDF never embed a credential or a server path."""
    from api.routers import jobs as jobs_router
    c, a = tenants.client, tenants.a
    job = {"id": "job_reportprobe1", "operator_id": a.operator_id, "kind": "diagnostic", "sector": "commercial", "status": "done",
           "stage": "reporting", "progress": "report ready", "created_at": jobs_router._now(), "finished_at": jobs_router._now(),
           "summary": {"headline": "probe", "company": "Tenant A"}, "report": None, "runner": "thread"}
    with jobs_router._LOCK:
        jobs_router._JOBS[job["id"]] = job
    r = c.get(f"/jobs/{job['id']}", headers=a.h())
    assert r.status_code == 200
    text = json.dumps(r.json())
    assert a.token not in text and "operator_id" not in r.json() and "/var/lib" not in text and str(tenants.data_root) not in text
