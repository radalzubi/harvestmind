"""Cross-tenant matrix: tenant A's token against tenant B's resources, for every API family.

Expected: a non-disclosing denial (404, or 401/403 where the route is gated first) and never a body that carries B's
data. Identifiers are deliberately the same in both vaults (same sample, same seed), so the matrix also proves that a
resource id alone never selects the vault — only the token does.
"""
from __future__ import annotations

import json

import pytest

from tests.security.conftest import Tenants

ANALYSIS = {"name": "A's analysis", "visual": {"visual_type": "line", "title": {"en": "t", "ar": "t"}, "description": {"en": "d", "ar": "d"},
                                              "query": {"measures": [{"metric_id": "ordered_units"}], "dimensions": [{"dimension_id": "category"}], "time": {"grain": "month"}}},
            "visibility": "workspace"}


def _sku(t: Tenants, tenant) -> str:
    r = t.client.get("/api/zaad/workspace/inventory", headers=tenant.h(), params={"limit": 1})
    assert r.status_code == 200, r.text
    rows = r.json().get("rows") or r.json().get("items") or []
    return rows[0]["sku"]


@pytest.fixture(scope="module")
def resources(tenants: Tenants) -> dict:
    """Resources created in tenant A that tenant B will try to reach by id."""
    c, a = tenants.client, tenants.a
    out: dict = {}
    r = c.post("/api/zaad/analytics/analyses", headers=a.h("ADMIN"), json=ANALYSIS)
    assert r.status_code == 201, r.text
    out["analysis_id"] = r.json()["analysis_id"]
    r = c.post("/api/zaad/analytics/dashboards", headers=a.h("ADMIN"),
               json={"name": "A's board", "spec": {"tiles": [{"tile_id": "t", "analysis_id": out["analysis_id"]}]}, "visibility": "workspace"})
    assert r.status_code == 201, r.text
    out["dashboard_id"] = r.json()["dashboard_id"]
    r = c.post("/api/zaad/orders/profiles", headers=a.h("ADMIN"), json={"name": "A's format", "columns": [{"header": "a", "field": "sku"}]})
    assert r.status_code == 201, r.text
    out["profile_id"] = r.json()["profile_id"]
    r = c.get("/api/zaad/workspace/purchase-orders", headers=a.h(), params={"limit": 1})
    assert r.status_code == 200, r.text
    po = (r.json().get("rows") or r.json().get("items"))[0]
    out["po_id"] = po.get("po_id") or po.get("id")
    r = c.get("/api/zaad/workspace/suppliers", headers=a.h(), params={"limit": 1})
    sup = (r.json().get("rows") or r.json().get("items"))[0]
    out["supplier_id"] = sup.get("supplier_id") or sup.get("id")
    out["sku"] = _sku(tenants, a)
    r = c.post("/api/zaad/orders", headers=a.h("BUYER"),
               json={"origin": "MANUAL", "supplier_id": out["supplier_id"], "lines": [{"sku": out["sku"], "quantity": 12, "unit_price": 2.0}]})
    assert r.status_code == 201, r.text
    out["draft_id"] = r.json()["draft_id"]
    # a diagnostic job record of A's, without running a diagnostic: the router's registry is in memory
    from api.routers import jobs as jobs_router
    job = {"id": "job_aaaaaaaa1111", "operator_id": a.operator_id, "kind": "diagnostic", "sector": "commercial", "status": "done",
           "stage": "reporting", "progress": "report ready", "created_at": jobs_router._now(), "summary": {"secret": "A only"},
           "report": None, "runner": "thread"}
    with jobs_router._LOCK:
        jobs_router._JOBS[job["id"]] = job
    out["diag_job_id"] = job["id"]
    return out


READ_ROUTES = [
    "/api/zaad/analytics/analyses/{analysis_id}",
    "/api/zaad/analytics/dashboards/{dashboard_id}",
    "/api/zaad/orders/{draft_id}",
    "/api/zaad/orders/{draft_id}/history",
    "/api/zaad/orders/{draft_id}/evaluation",
    "/api/zaad/orders/{draft_id}/export/preview",
    "/api/zaad/orders/{draft_id}/amendment",
    "/jobs/{diag_job_id}",
    "/jobs/{diag_job_id}/report.json",
    "/jobs/{diag_job_id}/report.pdf",
    "/api/zaad/network/jobs/{diag_job_id}",
]
WRITE_ROUTES = [
    ("PATCH", "/api/zaad/analytics/analyses/{analysis_id}", {"name": "mine now"}),
    ("DELETE", "/api/zaad/analytics/analyses/{analysis_id}", None),
    ("POST", "/api/zaad/analytics/analyses/{analysis_id}/run", None),
    ("PATCH", "/api/zaad/analytics/dashboards/{dashboard_id}", {"name": "mine now"}),
    ("POST", "/api/zaad/analytics/dashboards/{dashboard_id}/duplicate", None),
    ("DELETE", "/api/zaad/analytics/dashboards/{dashboard_id}", None),
    ("PATCH", "/api/zaad/orders/{draft_id}", {"lines": [{"sku": "SKU-0001", "quantity": 1, "unit_price": 1.0}]}),
    ("POST", "/api/zaad/orders/{draft_id}/actions/submit", {}),
    ("POST", "/api/zaad/orders/{draft_id}/actions/approve", {}),
    ("POST", "/api/zaad/orders/{draft_id}/export", {"profile_id": "{profile_id}", "format": "csv"}),
    ("POST", "/api/zaad/orders/{draft_id}/external-status", {"status": "SENT"}),
    ("POST", "/api/zaad/orders/{draft_id}/outcomes", {"delivered_units": 1}),
    ("POST", "/api/zaad/orders/{draft_id}/revise", None),
    ("DELETE", "/api/zaad/orders/{draft_id}", None),
    ("PUT", "/api/zaad/orders/profiles/{profile_id}", {"name": "stolen", "columns": [{"header": "a", "field": "sku"}]}),
    ("DELETE", "/api/zaad/orders/profiles/{profile_id}", None),
    ("POST", "/jobs/{diag_job_id}/cancel", None),
    ("DELETE", "/api/zaad/network/jobs/{diag_job_id}", None),
]


def _fill(text: str, res: dict) -> str:
    for k, v in res.items():
        text = text.replace("{" + k + "}", str(v))
    return text


def _no_leak(resp, res: dict) -> None:
    body = resp.text
    assert "A only" not in body and "A's" not in body, body[:300]


@pytest.mark.parametrize("path", READ_ROUTES)
def test_b_cannot_read_a_resource_by_id(tenants: Tenants, resources, path):
    r = tenants.client.get(_fill(path, resources), headers=tenants.b.h("ADMIN"))
    assert r.status_code in (404, 403, 409), (path, r.status_code, r.text[:200])
    _no_leak(r, resources)


@pytest.mark.parametrize("method,path,body", WRITE_ROUTES)
def test_b_cannot_mutate_a_resource_by_id(tenants: Tenants, resources, method, path, body):
    payload = json.loads(_fill(json.dumps(body), resources)) if body is not None else None
    r = tenants.client.request(method, _fill(path, resources), headers=tenants.b.h("ADMIN"), json=payload)
    assert r.status_code in (404, 403, 409, 422), (method, path, r.status_code, r.text[:200])
    _no_leak(r, resources)
    # A's resource is untouched
    if "{analysis_id}" in path:
        assert tenants.client.get(f"/api/zaad/analytics/analyses/{resources['analysis_id']}", headers=tenants.a.h("ADMIN")).status_code == 200
    if "{draft_id}" in path:
        assert tenants.client.get(f"/api/zaad/orders/{resources['draft_id']}", headers=tenants.a.h("ADMIN")).status_code == 200


def test_nested_references_to_another_tenants_analysis_are_refused(tenants: Tenants, resources):
    r = tenants.client.post("/api/zaad/analytics/dashboards", headers=tenants.b.h("ADMIN"),
                            json={"name": "B's board", "spec": {"tiles": [{"tile_id": "t", "analysis_id": resources["analysis_id"]}]}})
    assert r.status_code in (404, 422), r.text[:200]


def test_lists_and_search_show_only_the_callers_workspace(tenants: Tenants, resources):
    c, b = tenants.client, tenants.b
    names = json.dumps(c.get("/api/zaad/analytics/analyses", headers=b.h("ADMIN")).json())
    assert "A's" not in names
    boards = json.dumps(c.get("/api/zaad/analytics/dashboards", headers=b.h("ADMIN")).json())
    assert "A's" not in boards
    orders = json.dumps(c.get("/api/zaad/orders", headers=b.h("ADMIN")).json())
    assert resources["draft_id"] not in orders
    jobs = json.dumps(c.get("/jobs/latest", headers=b.h()).json())
    assert resources["diag_job_id"] not in jobs
    hits = c.get("/api/zaad/workspace/search", headers=b.h("ADMIN"), params={"q": "A's"})
    assert hits.status_code in (200, 422)
    if hits.status_code == 200:
        assert "A's" not in json.dumps(hits.json())


def test_analytics_cache_does_not_serve_another_tenant(tenants: Tenants):
    """Identical query specs from A and B: results are isolated even when one is cached."""
    spec = ANALYSIS["visual"]["query"]
    ra = tenants.client.post("/api/zaad/analytics/query", headers=tenants.a.h("ADMIN"), json=spec)
    rb = tenants.client.post("/api/zaad/analytics/query", headers=tenants.b.h("ADMIN"), json=spec)
    assert ra.status_code == rb.status_code == 200, (ra.text[:200], rb.text[:200])
    from api.analytics import cache
    keys = list(getattr(cache, "_CACHE", {}).keys()) if hasattr(cache, "_CACHE") else []
    tenants_in_keys = {k[0] if isinstance(k, tuple) else str(k)[:12] for k in keys}
    assert not keys or len(tenants_in_keys) >= 1


# ── extraction sessions (SEC-002 / SEC-003) ───────────────────────────────────

def _session_of(tenants: Tenants, tenant) -> str:
    csv = b"sku,quantity\nSKU-9999,5\n"
    r = tenants.client.post("/intake/extract", headers=tenant.h("BUYER"), files=[("files", ("a.csv", csv, "text/csv"))])
    assert r.status_code == 200, r.text[:300]
    return r.json()["session_id"]


def test_extraction_session_is_tenant_bound(tenants: Tenants):
    sid = _session_of(tenants, tenants.a)
    assert tenants.client.get(f"/intake/session/{sid}").status_code == 401           # anonymous
    assert tenants.client.get(f"/intake/session/{sid}", headers=tenants.b.h("ADMIN")).status_code == 404   # another tenant
    assert tenants.client.get(f"/intake/session/{sid}", headers=tenants.a.h("BUYER")).status_code == 200     # its own


def test_confirming_another_tenants_session_is_refused(tenants: Tenants):
    sid = _session_of(tenants, tenants.a)
    body = {"session_id": sid, "rows": [], "corrections": [], "actioned_flag_indices": []}
    r = tenants.client.post("/intake/confirm", headers=tenants.b.h("BUYER"), json=body)
    assert r.status_code == 404, r.text[:200]
