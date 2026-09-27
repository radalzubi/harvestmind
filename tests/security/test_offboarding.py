"""Tenant offboarding (security closure 2026-09, SEC-039): one workspace's data leaves every store, the other
workspace's does not move.

Two real tenants with the same synthetic sample (identical SKU, supplier and PO ids). Tenant A is populated in every
store the inventory names; B holds the same-looking records. The module-scoped `tenants` fixture gives this module
its own registry, so offboarding A here touches nothing another test module uses.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest

from tests.security.conftest import Tenants

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


# ── population ────────────────────────────────────────────────────────────────

def _populate(tenants: Tenants, t, tag: str, roots: dict) -> dict:
    """Put one row of everything in each store for tenant `t`. Returns the ids created (for later checks)."""
    c = tenants.client
    ids: dict = {}
    # uploads (raw copy under the vault) and an extraction session (audit root + owner.json)
    csv = f"supplier_id,supplier_name,lead_time_days\nSUP-X01,{tag} Supplier,7\n".encode()
    r = c.post("/intake/upload/stg_fmcg_suppliers", headers=t.h("BUYER"), files={"file": (f"{tag}_suppliers.csv", csv, "text/csv")})
    assert r.status_code in (200, 201), r.text[:200]
    r = c.post("/intake/extract", headers=t.h("BUYER"), files={"files": (f"{tag}.csv", b"sku,quantity\nSKU-0001,1\n", "text/csv")})
    assert r.status_code == 200, r.text[:200]
    ids["session"] = r.json()["session_id"]
    # analytics: a saved analysis and a dashboard (vault tables)
    r = c.post("/api/zaad/analytics/analyses", headers=t.h("ADMIN"), json={
        "name": f"{tag} analysis", "visibility": "workspace",
        "visual": {"visual_type": "line", "title": {"en": "t", "ar": "t"}, "description": {"en": "d", "ar": "d"},
                   "query": {"measures": [{"metric_id": "ordered_units"}], "dimensions": [{"dimension_id": "category"}], "time": {"grain": "month"}}}})
    assert r.status_code == 201, r.text[:200]
    ids["analysis"] = r.json()["analysis_id"]
    r = c.post("/api/zaad/analytics/dashboards", headers=t.h("ADMIN"), json={"name": f"{tag} board", "visibility": "workspace",
                                                                            "spec": {"tiles": [{"tile_id": "t", "analysis_id": ids["analysis"]}]}})
    assert r.status_code == 201, r.text[:200]
    ids["dashboard"] = r.json()["dashboard_id"]
    # a planning job row (no solve: the store is written directly, as the runner would)
    from zaad.full.demo import example
    from zaad.full.jobs import JobStore
    store = JobStore(Path(os.environ["ZAAD_JOB_STORE"]))
    req = example("normal", seed=1).model_copy(update={"operator_id": t.operator_id})
    ids["job"] = store.create(t.operator_id, req, timeout_s=30)
    store.update(ids["job"], status="DONE", report_json="{}")
    # a shadow-ledger decision with one event (the ledger checks the tenant and the information hash)
    import hashlib
    from zaad.full.shadow import ShadowLedger
    ledger = ShadowLedger(Path(os.environ["ZAAD_SHADOW_LEDGER"]))
    fingerprint = hashlib.sha256(req.model_dump_json().encode()).hexdigest()
    ids["decision"] = ledger.save(req, {"operator_id": t.operator_id, "information_hash": fingerprint, "status": "PENDING_REVIEW", "actions": [], "version": "test"}, t.operator_id)
    # an optimizer run record
    from optimization.audit_trail import record_run
    import pandas as pd
    rec = record_run(domain="test", config={}, inputs={"x": pd.DataFrame({"a": [1]})}, result={"status": "ok", "usable": True},
                     operator_id=t.operator_id, data_root=tenants.data_root)
    ids["run"] = rec.run_id
    # a diagnostic report file under the vault
    reports = tenants.registry.vault_dir(t.operator_id) / "reports"
    reports.mkdir(exist_ok=True)
    (reports / f"job_{tag}0001.json").write_text(json.dumps({"operator_id": t.operator_id, "summary": {"n": 1}}))
    # an approved access request carrying contact details
    ar = tenants.registry.registry_dir / "access_requests.json"
    rows = json.loads(ar.read_text()) if ar.exists() else []
    rows.append({"id": f"req_{tag}", "company": f"{tag} Ltd", "contact_name": f"{tag} Person", "email": f"{tag}@example.test",
                 "country": "JO", "sector": "commercial", "erp": "", "sku_count": 1, "note": "hello", "status": "approved",
                 "operator_id": t.operator_id, "created_at": "2026-09-26T00:00:00+00:00"})
    ar.write_text(json.dumps(rows, indent=1))
    # pool signals and the contribution log (operator-attributed rows), and a corpus line for the session
    sig = roots["pool"] / "signals" / "demand_patterns"
    sig.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"operator_id": [t.operator_id, t.operator_id], "contribution_id": [f"c_{tag}1", f"c_{tag}2"], "v": [1.0, 2.0]}).to_parquet(sig / f"c_{tag}.parquet", index=False)
    logd = roots["pool"] / "contributions"
    logd.mkdir(parents=True, exist_ok=True)
    with (logd / "contribution_log.jsonl").open("a") as f:
        f.write(json.dumps({"at": "2026-09-26", "operator_id": t.operator_id, "event": "contributed", "contribution_id": f"c_{tag}1"}) + "\n")
    roots["corpus"].parent.mkdir(parents=True, exist_ok=True)
    with roots["corpus"].open("a") as f:
        f.write(json.dumps({"session_id": ids["session"], "operator_id": "default", "rows": [{"sku": "SKU-0001"}]}) + "\n")
    return ids


def _shared_signal(roots: dict, a_id: str, b_id: str) -> None:
    """One parquet file holding rows of both tenants: A's rows must go, B's must stay in the same file."""
    import pandas as pd
    sig = roots["pool"] / "signals" / "waste_profiles"
    sig.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"operator_id": [a_id, b_id, b_id], "contribution_id": ["c_s1", "c_s2", "c_s3"], "v": [1.0, 2.0, 3.0]}).to_parquet(sig / "shared.parquet", index=False)


def _snapshot(tenants: Tenants, t, roots: dict) -> dict:
    """Counts of everything tenant `t` has, for a before/after comparison."""
    from infrastructure.db_manager import DBManager
    out: dict = {}
    dbm = DBManager(tenants.registry)
    conn = dbm.get_operator_connection(t.operator_id)
    try:
        for table in ("stg_fmcg_suppliers", "stg_fmcg_skus", "zaad_analytics_analyses", "zaad_analytics_dashboards"):
            out[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        dbm.close_all()
    vault = tenants.registry.vault_dir(t.operator_id)
    out["vault_files"] = sum(1 for _ in vault.rglob("*") if _.is_file())
    out["sessions"] = sum(1 for o in tenants.sessions_root.glob("*/owner.json") if json.loads(o.read_text()).get("operator_id") == t.operator_id)
    js = sqlite3.connect(os.environ["ZAAD_JOB_STORE"])
    out["jobs"] = js.execute("SELECT COUNT(*) FROM jobs WHERE operator=?", (t.operator_id,)).fetchone()[0]
    js.close()
    sl = sqlite3.connect(os.environ["ZAAD_SHADOW_LEDGER"])
    out["decisions"] = sl.execute("SELECT COUNT(*) FROM decisions WHERE operator=?", (t.operator_id,)).fetchone()[0]
    out["events"] = sl.execute("SELECT COUNT(*) FROM events WHERE operator=?", (t.operator_id,)).fetchone()[0]
    sl.close()
    out["runs"] = sum(1 for f in (tenants.data_root / "runs").glob("*.json") if json.loads(f.read_text()).get("operator_id") == t.operator_id)
    import pandas as pd
    rows = 0
    for f in (roots["pool"] / "signals").glob("*/*.parquet"):
        df = pd.read_parquet(f)
        rows += int((df["operator_id"] == t.operator_id).sum())
    out["pool_rows"] = rows
    out["pool_log"] = sum(1 for line in (roots["pool"] / "contributions" / "contribution_log.jsonl").read_text().splitlines() if json.loads(line).get("operator_id") == t.operator_id)
    return out


@pytest.fixture(scope="module")
def world(tenants: Tenants, tmp_path_factory):
    roots = {"pool": tmp_path_factory.mktemp("pool"), "corpus": tmp_path_factory.mktemp("corpus") / "corpus_v1.jsonl"}
    a_ids = _populate(tenants, tenants.a, "alpha", roots)
    b_ids = _populate(tenants, tenants.b, "beta", roots)
    _shared_signal(roots, tenants.a.operator_id, tenants.b.operator_id)
    return {"roots": roots, "a": a_ids, "b": b_ids, "b_before": _snapshot(tenants, tenants.b, roots), "a_before": _snapshot(tenants, tenants.a, roots)}


def _offboarding(tenants: Tenants, world, **kw):
    from infrastructure.offboarding import Offboarding
    return Offboarding(tenants.registry, pool_root=world["roots"]["pool"], corpus_file=world["roots"]["corpus"],
                       sessions_root=tenants.sessions_root, **kw)


def _stage(res, name):
    return next(s for s in res.stages if s.store == name)


# ── tests, in order ───────────────────────────────────────────────────────────

def test_01_every_store_is_populated_for_both_tenants(tenants: Tenants, world):
    for who in ("a_before", "b_before"):
        snap = world[who]
        assert snap["vault_files"] > 0 and snap["sessions"] == 1 and snap["jobs"] == 1 and snap["decisions"] == 1
        assert snap["events"] >= 1 and snap["runs"] == 1 and snap["pool_rows"] >= 2 and snap["pool_log"] == 1
        assert snap["zaad_analytics_analyses"] >= 1 and snap["zaad_analytics_dashboards"] >= 1


def test_02_dry_run_identifies_a_and_never_b(tenants: Tenants, world):
    a, b = tenants.a, tenants.b
    res = _offboarding(tenants, world).plan(a.operator_id)
    assert res.mode == "dry-run" and res.status == "complete"
    by = {s.store: s for s in res.stages}
    for store in ("credentials", "vault", "extraction_sessions", "training_corpus", "job_store", "shadow_ledger", "run_records", "access_requests", "pool_signals"):
        assert by[store].status == "would_remove", (store, by[store])
        assert by[store].count >= 1, store
    assert by["registry_tombstone"].status == "retained"
    assert by["process_caches"].status == "not_configured"
    paths = " ".join(p for s in res.stages for p in s.paths)
    assert a.operator_id in paths and b.operator_id not in paths
    assert world["b"]["session"] not in paths and world["a"]["session"] in paths
    assert by["pool_signals"].count == 4          # 2 own rows + 1 row in the shared file + the log line
    # nothing moved: a dry run is a read
    assert _snapshot(tenants, a, world["roots"]) == world["a_before"]
    assert _snapshot(tenants, b, world["roots"]) == world["b_before"]
    assert tenants.client.get("/me", headers=a.h()).status_code == 200
    # the plan never carries a customer record
    text = json.dumps(res.to_dict())
    assert "alpha Supplier" not in text and "alpha@example.test" not in text and "alpha Ltd" not in text


def test_03_refusals_fail_closed(tenants: Tenants, world):
    from infrastructure.offboarding import Refused
    off = _offboarding(tenants, world)
    for bad in ("op_ZZZZZZZZ", "op_1234567", "../op_abcdef12", "", "Tenant A", "op_abcdef12; rm -rf /"):
        with pytest.raises(Refused):
            off.plan(bad)
    with pytest.raises(Refused):
        off.plan("op_00000000")                                 # well-formed, unknown, no receipt
    with pytest.raises(Refused):
        off.execute(tenants.a.operator_id, "op_00000000")       # confirmation must repeat the id
    with pytest.raises(Refused):
        off.execute(tenants.a.operator_id, tenants.b.operator_id)
    assert _snapshot(tenants, tenants.a, world["roots"]) == world["a_before"]


def test_04_symlinks_are_never_followed(tenants: Tenants, world, tmp_path):
    """A link inside A's vault to B's vault, and a session directory replaced by a link: B's files survive."""
    a, b = tenants.a, tenants.b
    a_vault, b_vault = tenants.registry.vault_dir(a.operator_id), tenants.registry.vault_dir(b.operator_id)
    (a_vault / "uploads" / "to_b").symlink_to(b_vault / "uploads", target_is_directory=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("keep")
    (a_vault / "escape").symlink_to(outside, target_is_directory=True)
    off = _offboarding(tenants, world)
    plan = off.plan(a.operator_id)
    assert _stage(plan, "vault").status == "would_remove"
    # a whole vault directory that is itself a symlink is refused outright
    fake = tenants.registry.operators_dir / "op_feedfeed"
    try:
        fake.symlink_to(b_vault, target_is_directory=True)
        from infrastructure.offboarding import Offboarding
        st = Offboarding(tenants.registry, pool_root=world["roots"]["pool"], corpus_file=world["roots"]["corpus"], sessions_root=tenants.sessions_root)._vault("op_feedfeed", execute=True)  # noqa: SLF001
        assert st.status == "failed" and "symlink" in st.detail
        assert (b_vault / "harvestmind.db").exists()
    finally:
        fake.unlink()
    # the links inside A's vault are removed as links when A is offboarded (test_05); B and `outside` are checked there
    world["outside"] = outside


def test_05_execute_removes_a_everywhere_and_leaves_b_untouched(tenants: Tenants, world):
    a, b = tenants.a, tenants.b
    c = tenants.client
    off = _offboarding(tenants, world)
    res = off.execute(a.operator_id, a.operator_id, actor="test")
    assert res.status == "complete", [(s.store, s.status, s.detail) for s in res.stages]
    assert res.receipt and Path(res.receipt).exists()
    by = {s.store: s for s in res.stages}
    for store in ("credentials", "vault", "extraction_sessions", "training_corpus", "job_store", "shadow_ledger", "run_records", "access_requests", "pool_signals"):
        assert by[store].status == "removed", (store, by[store])
    # A: authentication fails for the workspace token and every role
    assert c.get("/me", headers=a.h()).status_code == 401
    for role in a.actors:
        assert c.get("/me", headers=a.h(role)).status_code == 401
    # A: nothing on disk
    assert not (tenants.registry.operators_dir / a.operator_id).exists()
    assert not (tenants.sessions_root / world["a"]["session"]).exists()
    assert (world["outside"] / "keep.txt").exists(), "a symlink out of the vault was unlinked, never followed"
    assert (tenants.registry.vault_dir(b.operator_id) / "uploads").exists(), "the link into B's vault was unlinked, never followed"
    js = sqlite3.connect(os.environ["ZAAD_JOB_STORE"])
    assert js.execute("SELECT COUNT(*) FROM jobs WHERE operator=?", (a.operator_id,)).fetchone()[0] == 0
    js.close()
    sl = sqlite3.connect(os.environ["ZAAD_SHADOW_LEDGER"])
    assert sl.execute("SELECT COUNT(*) FROM decisions WHERE operator=?", (a.operator_id,)).fetchone()[0] == 0
    assert sl.execute("SELECT COUNT(*) FROM events WHERE operator=?", (a.operator_id,)).fetchone()[0] == 0
    sl.close()
    assert not any(json.loads(f.read_text()).get("operator_id") == a.operator_id for f in (tenants.data_root / "runs").glob("*.json"))
    rows = json.loads((tenants.registry.registry_dir / "access_requests.json").read_text())
    mine = [r for r in rows if r.get("operator_id") == a.operator_id]
    assert mine and all(r["email"] == "" and r["company"] == "" and r["contact_name"] == "" and r.get("offboarded_at") for r in mine)
    assert all(r["email"] for r in rows if r.get("operator_id") == b.operator_id)
    import pandas as pd
    shared = pd.read_parquet(world["roots"]["pool"] / "signals" / "waste_profiles" / "shared.parquet")
    assert list(shared["operator_id"]) == [b.operator_id, b.operator_id]
    assert not (world["roots"]["pool"] / "signals" / "demand_patterns" / "c_alpha.parquet").exists()
    assert world["a"]["session"] not in world["roots"]["corpus"].read_text()
    assert world["b"]["session"] in world["roots"]["corpus"].read_text()
    # A: the registry keeps a tombstone without any secret
    raw = json.loads(tenants.registry.registry_file.read_text())[a.operator_id]
    assert raw["status"] == "deleted" and raw["token_hash"] is None and raw["access_code_hash"] is None and raw["actors"] == {}
    assert raw["anon_secret"] is None and raw["logo_url"] is None and raw["display_name"] is None
    assert raw["operator_id"] == a.operator_id and raw["name"] and raw["created_at"]
    # A: every API family answers as for an unknown tenant
    for path in (f"/api/zaad/analytics/analyses/{world['a']['analysis']}", f"/api/zaad/analytics/dashboards/{world['a']['dashboard']}",
                 "/jobs/latest", f"/intake/session/{world['a']['session']}", "/api/zaad/workspace/summary"):
        assert c.get(path, headers=a.h()).status_code == 401, path
    # B: identical before and after, still signed in, still served (the refusals above tripped the per-address
    # failed-auth throttle, which is the test client's single address, not B's standing)
    from api import dependencies
    dependencies._FAILED_AUTH.clear()  # noqa: SLF001
    dependencies._FAILED_AUTH_GLOBAL = []  # noqa: SLF001
    assert _snapshot(tenants, b, world["roots"]) == world["b_before"]
    assert c.get("/me", headers=b.h()).status_code == 200
    assert c.get(f"/api/zaad/analytics/analyses/{world['b']['analysis']}", headers=b.h("ADMIN")).status_code == 200
    assert c.get(f"/intake/session/{world['b']['session']}", headers=b.h("ADMIN")).status_code == 200
    r = c.get("/api/zaad/network/jobs/" + world["b"]["job"], headers=b.h("ADMIN"))
    assert r.status_code in (200, 404)   # the job store route may be scoped differently; the row itself is checked in the snapshot
    # the receipt names counts and stores, not records
    receipt = Path(res.receipt).read_text()
    assert "alpha Supplier" not in receipt and "alpha@example.test" not in receipt and a.operator_id in receipt


def test_06_second_run_is_a_safe_no_op(tenants: Tenants, world):
    a, b = tenants.a, tenants.b
    off = _offboarding(tenants, world)
    again = off.execute(a.operator_id, a.operator_id, actor="test")
    assert again.status == "nothing-to-do", [(s.store, s.status) for s in again.stages]
    assert not again.failed
    assert _snapshot(tenants, b, world["roots"]) == world["b_before"]
    runs = json.loads(Path(again.receipt).read_text())["runs"]
    assert [r["status"] for r in runs] == ["complete", "nothing-to-do"]
    # and a plan after the fact is honest too
    assert off.plan(a.operator_id).status == "nothing-to-do"


def test_07_partial_failure_is_reported_and_rerunnable(tenants: Tenants, world, monkeypatch):
    """B is offboarded here in two steps: the ledger stage fails first, the rerun finishes it."""
    b = tenants.b
    from infrastructure import offboarding as mod
    off = _offboarding(tenants, world)
    real = mod.Offboarding._ledger
    monkeypatch.setattr(mod.Offboarding, "_ledger", lambda self, op, execute: (_ for _ in ()).throw(OSError("disk full")))
    first = off.execute(b.operator_id, b.operator_id, actor="test")
    assert first.status == "partial"
    assert [s.store for s in first.failed] == ["shadow_ledger"]
    assert "OSError" in _stage(first, "shadow_ledger").detail
    assert _stage(first, "vault").status == "removed"
    # what remains is exactly what the report says
    sl = sqlite3.connect(os.environ["ZAAD_SHADOW_LEDGER"])
    assert sl.execute("SELECT COUNT(*) FROM decisions WHERE operator=?", (b.operator_id,)).fetchone()[0] == 1
    sl.close()
    assert tenants.client.get("/me", headers=b.h()).status_code == 401
    monkeypatch.setattr(mod.Offboarding, "_ledger", real)
    second = off.execute(b.operator_id, b.operator_id, actor="test")
    assert second.status == "complete" and _stage(second, "shadow_ledger").status == "removed"
    sl = sqlite3.connect(os.environ["ZAAD_SHADOW_LEDGER"])
    assert sl.execute("SELECT COUNT(*) FROM decisions WHERE operator=?", (b.operator_id,)).fetchone()[0] == 0
    sl.close()
    runs = json.loads(Path(second.receipt).read_text())["runs"]
    assert [r["status"] for r in runs] == ["partial", "complete"]


def test_08_cli_dry_run_by_default_and_admin_route(tenants: Tenants, world, monkeypatch, tmp_path_factory):
    """The command line plans unless told to execute with the id repeated; the admin route follows the same rules."""
    import importlib
    cli = importlib.import_module("scripts.offboard_operator")
    # a third tenant so the earlier assertions stay valid
    rec = tenants.registry.create_operator("Tenant C", region="test", sector="commercial")
    tok = tenants.registry.issue_token(rec.operator_id)
    assert cli.main(["--operator-id", rec.operator_id, "--data-root", str(tenants.data_root)]) == 0
    assert tenants.client.get("/me", headers={"Authorization": f"Bearer {tok}"}).status_code == 200, "a plan removes nothing"
    assert cli.main(["--operator-id", rec.operator_id, "--data-root", str(tenants.data_root), "--execute"]) == 3
    assert cli.main(["--operator-id", rec.operator_id, "--data-root", str(tenants.data_root), "--execute", "--confirm-operator-id", "op_00000000"]) == 3
    assert cli.main(["--operator-id", "not-an-id", "--data-root", str(tenants.data_root)]) == 3
    # admin route: 404 without a key, 401 with the wrong one, plan by default, execute only with the confirmation
    c = tenants.client
    rec2 = tenants.registry.create_operator("Tenant D", region="test", sector="commercial")
    tok2 = tenants.registry.issue_token(rec2.operator_id)
    monkeypatch.delenv("HARVESTMIND_ADMIN_KEY", raising=False)
    assert c.post(f"/admin/operators/{rec2.operator_id}/offboard", json={}).status_code == 404
    monkeypatch.setenv("HARVESTMIND_ADMIN_KEY", "admin-test-key")
    assert c.post(f"/admin/operators/{rec2.operator_id}/offboard", headers={"X-Admin-Key": "wrong"}, json={}).status_code == 401
    r = c.post(f"/admin/operators/{rec2.operator_id}/offboard", headers={"X-Admin-Key": "admin-test-key"}, json={})
    assert r.status_code == 200 and r.json()["mode"] == "dry-run"
    assert c.get("/me", headers={"Authorization": f"Bearer {tok2}"}).status_code == 200
    r = c.post(f"/admin/operators/{rec2.operator_id}/offboard", headers={"X-Admin-Key": "admin-test-key"}, json={"execute": True, "confirm_operator_id": "op_00000000"})
    assert r.status_code == 409
    r = c.post(f"/admin/operators/{rec2.operator_id}/offboard", headers={"X-Admin-Key": "admin-test-key"}, json={"execute": True, "confirm_operator_id": rec2.operator_id})
    assert r.status_code == 200 and r.json()["status"] == "complete", r.text[:300]
    assert {s["store"]: s["status"] for s in r.json()["stages"]}["process_caches"] == "removed"
    assert c.get("/me", headers={"Authorization": f"Bearer {tok2}"}).status_code == 401
    assert not (tenants.registry.operators_dir / rec2.operator_id).exists()
    assert c.post(f"/admin/operators/{rec2.operator_id}/offboard", headers={"X-Admin-Key": "admin-test-key"}, json={"execute": True, "confirm_operator_id": rec2.operator_id}).json()["status"] == "nothing-to-do"
    # a workspace bearer can never reach the route
    assert c.post(f"/admin/operators/{rec.operator_id}/offboard", headers={"Authorization": f"Bearer {tok}"}, json={}).status_code == 401
