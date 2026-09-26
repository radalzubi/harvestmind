"""Operating Product V2 governance: roles, policy, concurrency, idempotency, audit, the closed loop.

Every test acts as a named person with a role in one workspace, over a real vault, through the
real routers. Nothing here runs the planner.
"""
from __future__ import annotations

import json

import duckdb
import pytest

from tests.integration.test_operating_product_api import OPERATOR, _client, _create


@pytest.fixture(scope="module")
def vault():
    from scripts.setup_db import setup_db
    from scripts.zaad_network_workspace_smoke import make_network_vault
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    make_network_vault(conn, seed=9)
    return conn


@pytest.fixture(autouse=True)
def _fresh_recommendation_budget():
    from api.routers import zaad as zaad_router
    with zaad_router._lock:
        zaad_router._recent.clear()
        zaad_router._global_recent.clear()
    yield


@pytest.fixture(scope="module")
def skus(vault):
    return [r[0] for r in vault.execute("SELECT sku FROM stg_fmcg_skus ORDER BY sku LIMIT 3").fetchall()]


@pytest.fixture(scope="module")
def admin(vault):
    return _client(vault, role="ADMIN", actor_id="act_admin")


@pytest.fixture(scope="module")
def buyer(vault):
    return _client(vault, role="BUYER", actor_id="act_buyer")


@pytest.fixture(scope="module")
def approver(vault):
    return _client(vault, role="APPROVER", actor_id="act_approver")


@pytest.fixture(scope="module")
def viewer(vault):
    return _client(vault, role="VIEWER", actor_id="act_viewer")


# ── roles ─────────────────────────────────────────────────────────────────────

def test_every_capability_is_checked_somewhere_and_nothing_unchecked_exists():
    """§61: no capability exists that the application never checks."""
    import re
    from pathlib import Path
    from api.product.governance import CAPABILITIES

    source = "".join(Path(p).read_text() for p in ("api/routers/zaad_orders.py", "api/routers/zaad_history.py",
                                                    "api/routers/zaad_workspace.py", "api/routers/intake.py",
                                                    "api/routers/zaad_analytics.py", "api/analytics/saved.py", "api/analytics/handoff.py",
                                                    # security review 2026-09: the solver, diagnostic, legacy and data-sharing routes
                                                    "api/routers/jobs.py", "api/routers/zaad_full.py", "api/routers/fmcg.py", "api/routers/planning.py",
                                                    "api/routers/backtest.py", "api/routers/assistant.py", "api/routers/pool.py", "api/routers/fsma.py"))
    # every string literal that appears inside an allowed(...) or need(...) call, however the
    # call chooses between them
    calls = re.findall(r'(?:allowed|need|permissions\.require|permissions\.check|capability)\((?:[^()]|\([^()]*\))*\)', source)
    checked = {name for call in calls for name in re.findall(r'"(\w+)"', call)}
    checked |= {"view"}   # every authenticated read is a view; the dependency itself is the check
    unchecked = [c for c in CAPABILITIES if c not in checked]
    assert not unchecked, f"capabilities nothing checks: {unchecked}"


def test_a_viewer_can_read_but_not_write(viewer, skus):
    assert viewer.get("/api/zaad/orders").status_code == 200
    r = viewer.post("/api/zaad/orders", json={"origin": "MANUAL", "supplier_id": "SUP-001", "lines": [{"sku": skus[0], "quantity": 1}]})
    assert r.status_code == 403 and r.json()["detail"]["code"] == "forbidden"
    assert "Viewer" in r.json()["detail"]["message"]


def test_a_buyer_cannot_approve_and_an_approver_can(buyer, approver, skus):
    draft = _create(buyer, skus, reference="ROLES-1")
    refused = buyer.post(f"/api/zaad/orders/{draft['draft_id']}/actions/approve", json={"reason": "ok"})
    assert refused.status_code == 403
    assert buyer.get(f"/api/zaad/orders/{draft['draft_id']}").json()["state"] == "DRAFT"
    approved = approver.post(f"/api/zaad/orders/{draft['draft_id']}/actions/approve", json={"reason": "ok"})
    assert approved.status_code == 200 and approved.json()["state"] == "APPROVED"
    assert approved.json()["approved_by"] == "act_approver"


def test_only_an_admin_manages_settings_profiles_and_people(buyer, admin):
    assert buyer.put("/api/zaad/workspace/settings", json={"self_approval": "allowed"}).status_code == 403
    assert buyer.post("/api/zaad/orders/profiles", json={"name": "x", "columns": [{"header": "a", "field": "sku"}]}).status_code == 403
    assert buyer.get("/api/zaad/workspace/actors").status_code == 403
    assert admin.get("/api/zaad/workspace/me").json()["actor"]["role"] == "ADMIN"


def test_actor_tokens_carry_a_role_and_a_revoked_one_never_authenticates(tmp_path, monkeypatch):
    import infrastructure.operator_registry as orm
    monkeypatch.setattr(orm, "DEFAULT_DATA_ROOT", tmp_path / "data")
    reg = orm.OperatorRegistry(data_root=tmp_path / "data")
    op = reg.create_operator("Roles Co")
    pilot = reg.issue_token(op.operator_id)
    actor_id, token = reg.issue_actor_token(op.operator_id, "Layla", "APPROVER")
    assert reg.actor_for_token(pilot)["role"] == "ADMIN", "the workspace token is the pilot administrator"
    who = reg.actor_for_token(token)
    assert who["actor_id"] == actor_id and who["role"] == "APPROVER" and who["name"] == "Layla"
    assert reg.operator_id_for_token(token) == op.operator_id
    listed = reg.list_actors(op.operator_id)
    assert [a["actor_id"] for a in listed] == [actor_id] and all("token" not in k for a in listed for k in a)
    assert reg.revoke_actor(op.operator_id, actor_id)
    assert reg.actor_for_token(token) is None and reg.operator_id_for_token(token) is None
    with pytest.raises(ValueError):
        reg.issue_actor_token(op.operator_id, "   ", "BUYER")


# ── self-approval policy ──────────────────────────────────────────────────────

def test_self_approval_policy_is_configurable_and_audited(admin, approver, skus):
    assert admin.get("/api/zaad/workspace/settings").json()["settings"]["self_approval"] == "allowed"
    mine = _create(admin, skus, reference="SELF-1")
    assert admin.post(f"/api/zaad/orders/{mine['draft_id']}/actions/approve", json={"reason": "ok"}).status_code == 200

    changed = admin.put("/api/zaad/workspace/settings", json={"self_approval": "different_approver"})
    assert changed.status_code == 200 and changed.json()["settings"]["self_approval"] == "different_approver"
    mine2 = _create(admin, skus, reference="SELF-2")
    refused = admin.post(f"/api/zaad/orders/{mine2['draft_id']}/actions/approve", json={"reason": "ok"})
    assert refused.status_code == 422 and refused.json()["detail"]["code"] == "self_approval_not_allowed"
    other = approver.post(f"/api/zaad/orders/{mine2['draft_id']}/actions/approve", json={"reason": "ok"})
    assert other.status_code == 200
    assert any("a different approver was required" in (e["detail"] or "") for e in other.json()["events"] if e["event"] == "approved")
    audit = admin.get("/api/zaad/audit?object_type=setting").json()
    assert any(r["action"] == "setting_changed" and r["after_state"] == "different_approver" for r in audit["rows"])
    assert admin.put("/api/zaad/workspace/settings", json={"self_approval": "allowed"}).status_code == 200
    assert admin.put("/api/zaad/workspace/settings", json={"self_approval": "whatever"}).status_code == 422
    assert admin.put("/api/zaad/workspace/settings", json={"not_a_key": "x"}).status_code == 422


# ── concurrency and idempotency ───────────────────────────────────────────────

def test_two_people_editing_the_same_draft_do_not_overwrite_each_other(buyer, approver, skus):
    draft = _create(buyer, skus, reference="RACE-1")
    v = draft["version"]
    first = approver.patch(f"/api/zaad/orders/{draft['draft_id']}", json={"notes": "approver's note", "expected_version": v})
    assert first.status_code == 200 and first.json()["version"] == v + 1
    second = buyer.patch(f"/api/zaad/orders/{draft['draft_id']}", json={"notes": "buyer's note", "expected_version": v})
    assert second.status_code == 409 and second.json()["detail"]["code"] == "stale_write"
    assert buyer.get(f"/api/zaad/orders/{draft['draft_id']}").json()["notes"] == "approver's note", "the newer work survived"
    # a write that names no version still works (a client that does not care), and a stale approve is refused too
    assert buyer.patch(f"/api/zaad/orders/{draft['draft_id']}", json={"notes": "unversioned"}).status_code == 200
    stale = approver.post(f"/api/zaad/orders/{draft['draft_id']}/actions/approve", json={"reason": "ok", "expected_version": v})
    assert stale.status_code == 409


def test_a_retried_approval_with_an_idempotency_key_acts_once(approver, skus):
    draft = _create(approver, skus, reference="IDEM-1")
    headers = {"Idempotency-Key": "approve-once-abc"}
    first = approver.post(f"/api/zaad/orders/{draft['draft_id']}/actions/approve", json={"reason": "ok"}, headers=headers)
    assert first.status_code == 200
    again = approver.post(f"/api/zaad/orders/{draft['draft_id']}/actions/approve", json={"reason": "ok"}, headers=headers)
    assert again.status_code == 200 and again.headers.get("Idempotent-Replay") == "true"
    assert again.json()["state"] == "APPROVED"
    events = approver.get(f"/api/zaad/orders/{draft['draft_id']}").json()["events"]
    assert sum(1 for e in events if e["event"] == "approved") == 1, "approved once, not twice"
    # without the key the second approve is refused by the lifecycle, as before
    plain = approver.post(f"/api/zaad/orders/{draft['draft_id']}/actions/approve", json={"reason": "ok"})
    assert plain.status_code == 422


def test_a_retried_export_replays_the_same_file(approver, skus):
    draft = _create(approver, skus, reference="IDEM-EXPORT")
    approver.post(f"/api/zaad/orders/{draft['draft_id']}/actions/approve", json={"reason": "ok"})
    headers = {"Idempotency-Key": "export-once-xyz"}
    first = approver.post(f"/api/zaad/orders/{draft['draft_id']}/export", headers=headers)
    second = approver.post(f"/api/zaad/orders/{draft['draft_id']}/export", headers=headers)
    assert first.status_code == 200 and second.status_code == 200
    assert first.content == second.content and second.headers.get("Idempotent-Replay") == "true"
    assert len(approver.get(f"/api/zaad/orders/{draft['draft_id']}").json()["exports"]) == 1


# ── the audit log ─────────────────────────────────────────────────────────────

def test_every_operational_action_writes_an_audit_row_and_nothing_deletes_one(buyer, approver, vault, skus):
    before = vault.execute(f"SELECT count(*) FROM zaad_audit_log WHERE operator_id = '{OPERATOR}'").fetchone()[0]
    draft = _create(buyer, skus, reference="AUDIT-1")
    identity = draft["draft_id"]
    buyer.patch(f"/api/zaad/orders/{identity}", json={"notes": "n"})
    buyer.post(f"/api/zaad/orders/{identity}/actions/submit", json={})
    approver.post(f"/api/zaad/orders/{identity}/actions/approve", json={"reason": "ok"})
    approver.post(f"/api/zaad/orders/{identity}/export")
    approver.post(f"/api/zaad/orders/{identity}/external-status", json={"status": "PLACED_EXTERNALLY", "external_reference": "ERP-77"})
    rows = buyer.get(f"/api/zaad/audit?object_type=draft&object_id={identity}").json()["rows"]
    actions = [r["action"] for r in rows]
    for expected in ("created", "edited", "submitted", "approved", "exported", "external_status"):
        assert expected in actions, (expected, actions)
    approved = next(r for r in rows if r["action"] == "approved")
    assert approved["actor"] == "act_approver" and approved["actor_role"] == "APPROVER"
    assert approved["before_state"] == "READY_FOR_REVIEW" and approved["after_state"] == "APPROVED"
    exported = next(r for r in rows if r["action"] == "exported")
    assert exported["context"]["transmitted"] is False and exported["context"]["adapter"] == "file-export"
    assert vault.execute(f"SELECT count(*) FROM zaad_audit_log WHERE operator_id = '{OPERATOR}'").fetchone()[0] > before
    # nothing in the API deletes audit rows
    import api.main as api_main
    paths = {(getattr(r, "path", ""), m) for r in api_main.app.routes for m in (getattr(r, "methods", None) or [])}
    assert not any("audit" in p and m == "DELETE" for p, m in paths)
    # no line contents, prices or datasets in any context
    for r in rows:
        text = json.dumps(r["context"] or {})
        assert "unit_price" not in text and "quantity" not in text


def test_a_deleted_draft_leaves_its_deletion_in_the_audit_log(buyer, skus):
    draft = _create(buyer, skus, reference="AUDIT-DEL")
    assert buyer.delete(f"/api/zaad/orders/{draft['draft_id']}").status_code == 204
    rows = buyer.get(f"/api/zaad/audit?object_id={draft['draft_id']}").json()["rows"]
    assert [r["action"] for r in rows][0] == "deleted"


# ── the closed loop ───────────────────────────────────────────────────────────

def test_external_status_is_a_ladder_recorded_by_a_person(buyer, approver, skus):
    draft = _create(buyer, skus, reference="LOOP-1")
    identity = draft["draft_id"]
    refused = buyer.post(f"/api/zaad/orders/{identity}/external-status", json={"status": "PLACED_EXTERNALLY"})
    assert refused.status_code == 422, "a draft was never placed"
    approver.post(f"/api/zaad/orders/{identity}/actions/approve", json={"reason": "ok"})
    skip = buyer.post(f"/api/zaad/orders/{identity}/external-status", json={"status": "FULFILLED"})
    assert skip.status_code == 422 and "cannot go straight" in skip.json()["detail"]["message"]
    placed = buyer.post(f"/api/zaad/orders/{identity}/external-status",
                        json={"status": "PLACED_EXTERNALLY", "external_reference": "SAP-4711", "observed_at": "2026-02-01T10:00:00"})
    assert placed.status_code == 200
    body = placed.json()
    assert body["external_status"] == "PLACED_EXTERNALLY" and body["external_reference"] == "SAP-4711"
    assert body["external_updated_by"] == "act_buyer"
    assert any(e["event"] == "external status" and "SAP-4711" in (e["detail"] or "") for e in body["events"])
    future = buyer.post(f"/api/zaad/orders/{identity}/external-status", json={"status": "ACKNOWLEDGED", "observed_at": "2999-01-01T00:00:00"})
    assert future.status_code == 422
    assert buyer.post(f"/api/zaad/orders/{identity}/external-status", json={"status": "ACKNOWLEDGED"}).status_code == 200
    assert buyer.post(f"/api/zaad/orders/{identity}/external-status", json={"status": "FULFILLED"}).status_code == 200
    assert buyer.post(f"/api/zaad/orders/{identity}/external-status", json={"status": "ACKNOWLEDGED"}).status_code == 422, "delivered is terminal"
    assert buyer.post(f"/api/zaad/orders/{identity}/external-status", json={"status": "SENT_BY_ZAAD"}).status_code == 422
    listed = buyer.get("/api/zaad/orders?external_status=FULFILLED").json()["rows"]
    assert identity in {r["draft_id"] for r in listed}
    history = buyer.get(f"/api/zaad/orders/{identity}/history").json()
    assert history["external"]["recorded_by_person"] is True and history["external"]["status"] == "FULFILLED"


def test_a_decision_response_is_recorded_with_an_optional_structured_reason(buyer, monkeypatch, tmp_path):
    monkeypatch.setenv("ZAAD_JOB_STORE", str(tmp_path / "jobs.sqlite"))
    import api.routers.zaad_full as zf
    zf._runner = None
    from zaad.full.demo import example
    job = zf.runner().store.create(OPERATOR, example("normal", seed=3), 30.0)
    zf.runner().store.update(job, status="DONE", report_json='{"information_hash": "abc", "as_of": "2026-01-05T00:00:00+00:00"}')
    r = buyer.post("/api/zaad/decisions/responses", json={"job_id": job, "decision_id": "po:PO-1", "status": "OVERRIDDEN",
                                                          "recommended": "DEFER", "reason_code": "supplier_relationship",
                                                          "reason_text": "we agreed a different date by phone"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "OVERRIDDEN" and body["reason_code"] == "supplier_relationship" and body["information_hash"] == "abc"
    again = buyer.post("/api/zaad/decisions/responses", json={"job_id": job, "decision_id": "po:PO-1", "status": "ACCEPTED"})
    assert again.json()["response_id"] == body["response_id"], "one row per decision, updated in place"
    assert again.json()["status"] == "ACCEPTED" and again.json()["reason_code"] is None
    no_reason = buyer.post("/api/zaad/decisions/responses", json={"job_id": job, "decision_id": "po:PO-2", "status": "REVIEWED"})
    assert no_reason.status_code == 200, "a reason is never forced"
    bad = buyer.post("/api/zaad/decisions/responses", json={"job_id": job, "decision_id": "po:PO-3", "status": "REJECTED", "reason_code": "vibes"})
    assert bad.status_code == 422
    other = buyer.post("/api/zaad/decisions/responses", json={"job_id": "job_of_someone_else", "decision_id": "x", "status": "REVIEWED"})
    assert other.status_code == 404
    assert buyer.get(f"/api/zaad/decisions/responses?job_id={job}").json()["total"] == 2
    zf.runner().shutdown()
    zf._runner = None


def test_outcomes_are_observed_after_action_and_realized_savings_need_a_comparator(buyer, approver, skus):
    draft = _create(buyer, skus, reference="OUTCOME-1")
    identity = draft["draft_id"]
    assert buyer.post(f"/api/zaad/orders/{identity}/outcomes", json={"metric": "received_units", "value": 1100}).status_code == 422, "no action yet"
    approver.post(f"/api/zaad/orders/{identity}/actions/approve", json={"reason": "ok"})
    assert buyer.post(f"/api/zaad/orders/{identity}/outcomes", json={"metric": "profit", "value": 1}).status_code == 422
    r = buyer.post(f"/api/zaad/orders/{identity}/outcomes", json={"metric": "received_units", "value": 1100, "observed_at": "2026-02-20T00:00:00"})
    assert r.status_code == 201 and r.json()["source"] == "recorded"
    no_basis = buyer.post(f"/api/zaad/orders/{identity}/outcomes", json={"metric": "purchase_cost", "value": 5000, "comparator_value": 5400})
    assert no_basis.status_code == 422 and "basis" in no_basis.json()["detail"]["message"]
    listing = buyer.get(f"/api/zaad/outcomes?draft_id={identity}").json()
    assert listing["classification"]["realized_outcome"] is True
    assert listing["classification"]["realized_savings"] == [], "an observation alone is not a saving"
    assert "not attributed to ZAAD" in listing["classification"]["note"]
    with_basis = buyer.post(f"/api/zaad/orders/{identity}/outcomes", json={"metric": "purchase_cost", "value": 5000, "comparator_value": 5400,
                                                                          "comparator_basis": "the price on the superseded order in our ERP"})
    assert with_basis.status_code == 201
    savings = buyer.get(f"/api/zaad/outcomes?draft_id={identity}").json()["classification"]["realized_savings"]
    assert len(savings) == 1 and savings[0]["difference"] == 400 and "ERP" in savings[0]["basis"]
    feed = buyer.get("/api/zaad/history").json()
    assert feed["backtested"]["available"] is False
    assert feed["counts"]["outcomes_recorded"] >= 2


def test_telemetry_stores_only_allowlisted_names_and_keys(buyer, vault):
    r = buyer.post("/api/zaad/telemetry", json={"events": [
        {"name": "sku_opened", "properties": {"sku": "SKU-0001", "unit_price": 9.99, "customer_name": "Acme", "surface": "inventory"}},
        {"name": "steal_everything", "properties": {"sku": "x"}},
    ]})
    assert r.status_code == 202 and r.json()["stored"] == 1 and r.json()["dropped"] == ["steal_everything"]
    stored = vault.execute(f"SELECT properties FROM zaad_telemetry WHERE operator_id = '{OPERATOR}' ORDER BY happened_at DESC LIMIT 1").fetchone()[0]
    props = json.loads(stored)
    assert props == {"sku": "SKU-0001", "surface": "inventory"}, "a price and a customer name never reach the store"
    assert buyer.post("/api/zaad/telemetry", json={"events": [{"name": "sku_opened"}] * 51}).status_code == 422


# ── export profiles ───────────────────────────────────────────────────────────

def test_export_profile_selection_hierarchy_is_declared_and_previewable(admin, skus):
    sup = admin.post("/api/zaad/orders/profiles", json={"name": "Supplier one's format", "supplier_id": "SUP-001", "is_default": True,
                                                        "columns": [{"header": "SKU", "field": "sku"}, {"header": "QTY", "field": "quantity"}]}).json()["profile_id"]
    ws = admin.post("/api/zaad/orders/profiles", json={"name": "House format", "is_default": True,
                                                       "columns": [{"header": "Item", "field": "sku"}]}).json()["profile_id"]
    a = _create(admin, skus, reference="PROF-A", supplier_id="SUP-001")
    b = _create(admin, skus, reference="PROF-B", supplier_id="SUP-009")
    pa = admin.get(f"/api/zaad/orders/{a['draft_id']}/export/preview").json()
    assert pa["reason"] == "supplier_default" and pa["profile"]["profile_id"] == sup and "SUP-001" in pa["detail"]
    pb = admin.get(f"/api/zaad/orders/{b['draft_id']}/export/preview").json()
    assert pb["reason"] == "workspace_default" and pb["profile"]["profile_id"] == ws
    chosen = admin.get(f"/api/zaad/orders/{a['draft_id']}/export/preview?profile_id={ws}").json()
    assert chosen["reason"] == "chosen"
    assert pa["adapter"]["real"] is True and pa["adapter"]["transmits"] is False
    admin.post(f"/api/zaad/orders/{a['draft_id']}/actions/approve", json={"reason": "ok"})
    exported = admin.post(f"/api/zaad/orders/{a['draft_id']}/export")
    assert exported.status_code == 200 and exported.headers["x-zaad-export-choice"] == "supplier_default"
    assert exported.headers["x-zaad-export-profile"] == sup
    assert exported.content.decode("utf-8-sig").splitlines()[0] == "SKU,QTY"
    for pid in (sup, ws):
        admin.delete(f"/api/zaad/orders/profiles/{pid}")
    standard = admin.get(f"/api/zaad/orders/{b['draft_id']}/export/preview").json()
    assert standard["reason"] == "standard"


def test_the_outbound_seam_has_one_real_adapter_and_a_labelled_test_one():
    from api.product.outbound import ADAPTERS, FileExportAdapter, TestConnector
    assert list(ADAPTERS) == ["file-export"] and FileExportAdapter.real is True and FileExportAdapter().describe()["transmits"] is False
    test = TestConnector()
    assert test.real is False and "TEST" in test.describe()["note"]
    draft = {"draft_id": "d1", "state": "APPROVED", "revision": 1, "lines": [{"sku": "S", "quantity": 1, "line_no": 1}]}
    result = test.submit(draft, {"format": "csv", "columns": [{"header": "SKU", "field": "sku"}]})
    assert result.transmitted is False and result.external_reference == "TEST-1"
    assert test.get_status("TEST-1")["known"] is True
    from api.product.inbound import UploadPath, INBOUND_SOURCES
    assert UploadPath().real is True and set(INBOUND_SOURCES) >= {"products", "inventory", "purchase_orders", "receipts", "customer_orders", "suppliers"}


# ── bulk creation: all or none ───────────────────────────────────────────────

def test_bulk_creation_creates_every_proposal_or_none(vault, skus):
    from tests.integration.test_operating_product_api import _client
    client = _client(vault, role="BUYER", actor_id="act_bulk")
    good = {"origin": "ZAAD_RECOMMENDATION", "supplier_id": "SUP-001", "destination_id": "DC", "currency": "USD",
            "source_decision_id": "buy:src_a", "lines": [{"sku": skus[0], "quantity": 24, "unit_price": 1.5}]}
    also = {**good, "supplier_id": "SUP-002", "source_decision_id": "buy:src_b", "lines": [{"sku": skus[1], "quantity": 48}]}
    before = client.get("/api/zaad/orders").json()["total"]
    bad = {**good, "lines": [{"sku": skus[0], "quantity": -1}]}
    refused = client.post("/api/zaad/orders/bulk", json={"drafts": [good, bad]})
    assert refused.status_code == 422 and "Nothing was created" in refused.json()["detail"]["message"]
    assert client.get("/api/zaad/orders").json()["total"] == before, "a refused batch leaves no proposal behind"
    made = client.post("/api/zaad/orders/bulk", json={"drafts": [good, also]}, headers={"Idempotency-Key": "bulk-1"})
    assert made.status_code == 201 and made.json()["created"] == 2
    assert {d["supplier_id"] for d in made.json()["drafts"]} == {"SUP-001", "SUP-002"}
    assert all(d["executable"] is False for d in made.json()["drafts"])
    again = client.post("/api/zaad/orders/bulk", json={"drafts": [good, also]}, headers={"Idempotency-Key": "bulk-1"})
    assert again.headers.get("Idempotent-Replay") == "true"
    assert client.get("/api/zaad/orders").json()["total"] == before + 2
    audit = client.get("/api/zaad/audit", params={"object_id": made.json()["drafts"][0]["draft_id"]}).json()["rows"]
    assert audit and audit[-1]["action"] == "created"


def test_bulk_creation_needs_the_capability_and_a_bounded_batch(vault, skus):
    from tests.integration.test_operating_product_api import _client
    viewer = _client(vault, role="VIEWER", actor_id="act_view")
    body = {"drafts": [{"origin": "MANUAL", "supplier_id": "SUP-001", "lines": [{"sku": skus[0], "quantity": 1}]}]}
    assert viewer.post("/api/zaad/orders/bulk", json=body).status_code == 403
    buyer = _client(vault, role="BUYER", actor_id="act_bulk")
    assert buyer.post("/api/zaad/orders/bulk", json={"drafts": []}).status_code == 422
    assert buyer.post("/api/zaad/orders/bulk", json={"drafts": "x"}).status_code == 400
    too_many = {"drafts": [body["drafts"][0]] * 51}
    assert buyer.post("/api/zaad/orders/bulk", json=too_many).status_code == 422



# ── transfer proposals: a move between the operator's own sites, never a purchase ────────────

def test_a_transfer_proposal_has_two_sites_and_no_supplier(vault, skus):
    from tests.integration.test_operating_product_api import _client
    client = _client(vault, role="BUYER", actor_id="act_move")
    made = client.post("/api/zaad/orders", json={"origin": "ZAAD_RECOMMENDATION", "source_decision_id": "move:dc_north",
                                                 "transfer_origin_id": "DC", "destination_id": "NORTH", "currency": "USD",
                                                 "lines": [{"sku": skus[0], "quantity": 120}]})
    assert made.status_code == 201, made.text
    draft = made.json()
    assert draft["kind"] == "TRANSFER" and draft["transfer_origin_id"] == "DC" and draft["supplier_id"] is None
    assert draft["executable"] is False
    # it exports through the same profiles, with the origin site available as a field
    from api.product.exporting import EXPORT_FIELDS, build_rows, default_profile
    assert "origin_site" in EXPORT_FIELDS
    profile = {**default_profile(), "columns": [{"header": "From", "field": "origin_site"}, {"header": "To", "field": "destination_id"}, {"header": "Qty", "field": "quantity"}]}
    _headers, body = build_rows(draft, profile)
    assert body == [["DC", "NORTH", "120"]]
    # and it is refused an evaluation with the reason, not silently
    refused = client.post(f"/api/zaad/orders/{draft['draft_id']}/evaluate")
    assert refused.status_code == 422 and refused.json()["detail"]["code"] == "transfer_not_evaluated"
    # a purchase is unchanged
    po = client.post("/api/zaad/orders", json={"origin": "MANUAL", "supplier_id": "SUP-001", "lines": [{"sku": skus[0], "quantity": 1}]}).json()
    assert po["kind"] == "PURCHASE" and po["transfer_origin_id"] is None


@pytest.mark.parametrize("body, reason", [
    ({"transfer_origin_id": "DC", "destination_id": "NORTH", "supplier_id": "SUP-001"}, "has no supplier"),
    ({"transfer_origin_id": "DC"}, "which site the stock goes to"),
    ({"transfer_origin_id": "DC", "destination_id": "DC"}, "to itself"),
    ({"transfer_origin_id": "DC", "destination_id": "NORTH", "origin": "IMPORTED_AMENDMENT", "source_po_id": "PO-1", "amendment_action": "DEFER"}, "not imported or amended"),
])
def test_a_transfer_that_is_not_one_is_refused(vault, skus, body, reason):
    from tests.integration.test_operating_product_api import _client
    client = _client(vault, role="BUYER", actor_id="act_move")
    r = client.post("/api/zaad/orders", json={"origin": "MANUAL", "lines": [{"sku": skus[0], "quantity": 5}], **body})
    assert r.status_code == 422 and reason in r.json()["detail"]["message"], r.text
