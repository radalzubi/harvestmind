"""Identifiers must never become filesystem paths (SEC-004), and malformed ids stay harmless everywhere."""
from __future__ import annotations

import pytest

from tests.security.conftest import Tenants

NASTY = ["../../x", "..", "%2e%2e%2f", "a/b", "ext-" + "z" * 12, "ext-0000000000zz", "ext-<script>", "x' OR 1=1 --", "😀"]
BODY_ONLY = ["ext-\n0000000000", "ext-0000000000ab\x00", "../../../etc/passwd"]


@pytest.mark.parametrize("sid", NASTY + BODY_ONLY)
def test_session_id_traversal_is_refused(tenants: Tenants, sid):
    c, a = tenants.client, tenants.a
    if sid in NASTY:
        r = c.get(f"/intake/session/{sid}", headers=a.h("BUYER"))
        assert r.status_code in (404, 422), (sid, r.status_code)
    r = c.post("/intake/confirm", headers=a.h("BUYER"), json={"session_id": sid, "rows": [], "corrections": [], "actioned_flag_indices": []})
    assert r.status_code in (404, 422), (sid, r.status_code, r.text[:200])
    # nothing was created outside the session root
    assert not (tenants.sessions_root.parent / "x").exists()
    assert not (tenants.sessions_root.parent / "confirmation.json").exists()
    assert not (tenants.sessions_root.parent / "session_snapshot.json").exists()


def test_session_storage_helpers_refuse_bad_ids(tmp_path):
    import ingestion.extraction_sessions as es
    for bad in ("..", "../x", "a/b", "", "abc", "a.b", "x" * 65, "ext-<x>", "ext 1", "ext-\n1"):
        with pytest.raises(ValueError):
            es._session_dir(bad, tmp_path)
        assert es.load_session(bad, tmp_path) is None
    assert es._session_dir("ext-0123456789ab", tmp_path) == tmp_path / "ext-0123456789ab"


@pytest.mark.parametrize("ident", [n for n in NASTY if n not in ("..", "%2e%2e%2f")])   # the client resolves those two to "/" before sending
def test_malformed_resource_ids_are_plain_404s(tenants: Tenants, ident):
    c, a = tenants.client, tenants.a
    for path in (f"/api/zaad/orders/{ident}", f"/api/zaad/analytics/analyses/{ident}", f"/api/zaad/analytics/dashboards/{ident}",
                 f"/jobs/{ident}", f"/api/zaad/network/jobs/{ident}", f"/api/zaad/workspace/suppliers/{ident}",
                 f"/api/zaad/workspace/inventory/{ident}", f"/api/zaad/workspace/purchase-orders/{ident}"):
        r = c.get(path, headers=a.h("ADMIN"))
        assert r.status_code in (404, 422, 400), (path, r.status_code, r.text[:200])
        assert "Traceback" not in r.text and "duckdb" not in r.text.lower()
