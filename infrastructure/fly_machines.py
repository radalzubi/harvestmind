"""Ephemeral solver machines on Fly.

The API stays on a small always-on VM. Each diagnostic that needs real CPU
is run on a dedicated machine created through the Fly Machines API from the
API's own image, sized by env, and destroyed when its process exits. The
worker talks back to the API over Fly's private network (6PN), never over
the public internet.

Enabled when FLY_API_TOKEN, FLY_APP_NAME and FLY_IMAGE_REF are present
(Fly injects the latter two) and HARVESTMIND_WORKER_MACHINES is not "false".
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

log = logging.getLogger("harvestmind.fly")
MACHINES_API = os.environ.get("FLY_MACHINES_API", "https://api.machines.dev/v1")


def enabled() -> bool:
    if os.environ.get("HARVESTMIND_WORKER_MACHINES", "true").lower() == "false":
        return False
    return all(os.environ.get(k) for k in ("FLY_API_TOKEN", "FLY_APP_NAME", "FLY_IMAGE_REF"))


def _request(method: str, path: str, body: dict | None = None, timeout: float = 30.0) -> dict:
    app = os.environ["FLY_APP_NAME"]
    req = urllib.request.Request(f"{MACHINES_API}/apps/{app}{path}", method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {os.environ['FLY_API_TOKEN']}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - fixed https host
        raw = resp.read()
    return json.loads(raw) if raw else {}


def launch_worker(job_id: str, env: dict[str, str]) -> str:
    """Create a one-shot machine running ``python -m api.worker`` and return its id."""
    cpus = int(os.environ.get("HARVESTMIND_WORKER_CPUS", "4"))
    memory = int(os.environ.get("HARVESTMIND_WORKER_MEMORY_MB", "8192"))
    kind = os.environ.get("HARVESTMIND_WORKER_CPU_KIND", "performance")
    passthrough = {k: v for k, v in os.environ.items()
                   if k.startswith("HARVESTMIND_") and k not in ("HARVESTMIND_SOLVER_THREADS", "HARVESTMIND_WORKER_MACHINES")}
    config = {
        "image": os.environ["FLY_IMAGE_REF"],
        "guest": {"cpu_kind": kind, "cpus": cpus, "memory_mb": memory},
        "auto_destroy": True,
        "restart": {"policy": "no"},
        "env": {**passthrough, "HARVESTMIND_SOLVER_THREADS": "1", "HARVESTMIND_ROLE": "worker", **env},
        "init": {"cmd": ["python", "-m", "api.worker"]},
        "metadata": {"zaad_role": "worker", "zaad_job": job_id},
    }
    body = {"name": f"worker-{job_id.replace('job_', '')}", "region": os.environ.get("FLY_REGION", "fra"), "config": config}
    out = _request("POST", "/machines", body)
    mid = out.get("id")
    if not mid:
        raise RuntimeError(f"machine create returned no id: {out}")
    log.info("launched worker machine %s for %s (%s x%d, %d MB)", mid, job_id, kind, cpus, memory)
    return str(mid)


def destroy_machine(machine_id: str) -> None:
    try:
        _request("DELETE", f"/machines/{machine_id}?force=true")
    except (urllib.error.URLError, RuntimeError, OSError) as exc:  # best effort: auto_destroy is the normal path
        log.warning("could not destroy machine %s: %s", machine_id, exc)
