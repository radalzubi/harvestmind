"""The solver worker boundary: what a worker machine receives and what the internal job routes accept (SEC-005 / SEC-006)."""
from __future__ import annotations

from tests.security.conftest import Tenants


def test_worker_env_carries_no_admin_or_customer_secret(monkeypatch):
    from infrastructure import fly_machines
    monkeypatch.setenv("HARVESTMIND_ADMIN_KEY", "admin-secret")
    monkeypatch.setenv("HARVESTMIND_SEED_WORKSPACES", "Customer|commercial|code-secret|")
    monkeypatch.setenv("HARVESTMIND_DEMO_TOKEN", "demo-secret")
    monkeypatch.setenv("HARVESTMIND_WORKER_TOKEN", "worker-secret")
    monkeypatch.setenv("HARVESTMIND_DATA_ROOT", "/var/lib/harvestmind")
    env = fly_machines.worker_env("job_test1234", {"ZAAD_JOB_ID": "job_test1234"})
    joined = " ".join(f"{k}={v}" for k, v in env.items())
    for secret in ("admin-secret", "code-secret", "demo-secret"):
        assert secret not in joined
    assert "HARVESTMIND_ADMIN_KEY" not in env and "HARVESTMIND_SEED_WORKSPACES" not in env and "HARVESTMIND_DEMO_TOKEN" not in env
    # the worker gets a token bound to its job, never the shared worker secret itself
    assert "HARVESTMIND_WORKER_TOKEN" not in env and env.get("ZAAD_JOB_TOKEN") not in (None, "", "worker-secret")


def test_job_token_is_bound_to_its_job(monkeypatch):
    from api.routers import jobs as jobs_router
    monkeypatch.setenv("HARVESTMIND_WORKER_TOKEN", "worker-secret")
    t1, t2 = jobs_router.job_token("job_one"), jobs_router.job_token("job_two")
    assert t1 != t2 and t1 != "worker-secret"
    assert jobs_router.worker_token_ok("job_one", t1) and not jobs_router.worker_token_ok("job_one", t2)
    assert not jobs_router.worker_token_ok("job_one", "worker-secret")   # the shared secret alone is not a job token
    assert not jobs_router.worker_token_ok("job_one", "")


def test_internal_routes_refuse_the_wrong_job_and_public_proxy_traffic(tenants: Tenants, monkeypatch):
    from api.routers import jobs as jobs_router
    monkeypatch.setenv("HARVESTMIND_WORKER_TOKEN", "worker-secret")
    job = {"id": "job_machine0001", "operator_id": tenants.a.operator_id, "kind": "diagnostic", "sector": "commercial", "status": "queued",
           "stage": "preparing", "progress": "", "created_at": jobs_router._now(), "runner": "machine"}
    with jobs_router._LOCK:
        jobs_router._JOBS[job["id"]] = job
    c = tenants.client
    good = {"X-Worker-Token": jobs_router.job_token(job["id"])}
    other = {"X-Worker-Token": jobs_router.job_token("job_machine0002")}
    assert c.post(f"/jobs/internal/{job['id']}/progress", headers=other, json={"progress": "x"}).status_code == 401
    assert c.post(f"/jobs/internal/{job['id']}/progress", headers={"X-Worker-Token": "worker-secret"}, json={"progress": "x"}).status_code == 401
    assert c.post(f"/jobs/internal/{job['id']}/result", headers=other, json={"status": "done", "summary": {"forged": True}}).status_code == 401
    # a request that came through the public proxy (Fly stamps Fly-Client-IP on it) is refused even with the right token
    assert c.post(f"/jobs/internal/{job['id']}/progress", headers={**good, "Fly-Client-IP": "203.0.113.9"}, json={"progress": "x"}).status_code == 404
    # the job's own token over the private network works
    assert c.post(f"/jobs/internal/{job['id']}/progress", headers=good, json={"progress": "x", "stage": "testing"}).status_code == 200
    assert jobs_router._JOBS[job["id"]]["summary"] is None if "summary" in jobs_router._JOBS[job["id"]] else True
